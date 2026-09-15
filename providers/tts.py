"""
providers/tts.py
Concrete implementations of TTSProvider for Cloned Voice, Robotic Voice, and System Voice.
"""

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from providers.base import TTSProvider
import config_manager
import robotic_voice

try:
    import pyttsx3
    _pyttsx3_engine = pyttsx3.init()
    _pyttsx3_engine.setProperty('rate', 160)
except Exception:
    _pyttsx3_engine = None


class RoboticVoiceProvider(TTSProvider):
    """Offline robotic voice using espeak, ring modulation, and paplay."""

    @property
    def name(self) -> str:
        return "robotic"

    def speak(self, text: str) -> bool:
        try:
            robotic_voice.speak_robotic(text)
            return True
        except Exception as e:
            print(f"[tts] Robotic voice error: {e}", flush=True)
            return False

    def cancel(self) -> None:
        robotic_voice.cancel_active_speech()


class SystemVoiceProvider(TTSProvider):
    """Offline system voice fallback via pyttsx3."""

    @property
    def name(self) -> str:
        return "system"

    def speak(self, text: str) -> bool:
        if _pyttsx3_engine is None:
            return False
        try:
            _pyttsx3_engine.say(text)
            _pyttsx3_engine.runAndWait()
            return True
        except Exception as e:
            print(f"[tts] System voice error: {e}", flush=True)
            return False

    def cancel(self) -> None:
        if _pyttsx3_engine:
            try:
                _pyttsx3_engine.stop()
            except Exception:
                pass


class ClonedVoiceProvider(TTSProvider):
    """
    Local voice-cloning TTS provider that speaks in user's cloned voice.
    Automatically falls back to RoboticVoiceProvider if voice reference
    is not yet recorded or backend engine is loading.
    """

    def __init__(self, fallback_provider: Optional[TTSProvider] = None):
        self.fallback = fallback_provider or RoboticVoiceProvider()
        self._active_proc = None
        self._f5_instance = None
        self._init_failed = False

    @property
    def name(self) -> str:
        return "cloned"

    def get_reference_voice_path(self) -> str:
        config = config_manager.load_config()
        configured = config.get("voice_reference_path")
        if configured and os.path.exists(os.path.expanduser(configured)):
            return os.path.expanduser(configured)

        default_path = os.path.expanduser("~/.config/nexovian/voice_reference.wav")
        return default_path

    def get_reference_text(self) -> str:
        ref_txt_path = os.path.expanduser("~/.config/nexovian/voice_reference.txt")
        if os.path.exists(ref_txt_path):
            try:
                with open(ref_txt_path, "r", encoding="utf-8") as f:
                    txt = f.read().strip()
                    if txt:
                        return txt
            except Exception:
                pass
        return "Hello, I am Karan, and this is my voice reference sample for my Nexovian desktop assistant."

    def is_reference_available(self) -> bool:
        ref_path = self.get_reference_voice_path()
        return os.path.exists(ref_path) and os.path.getsize(ref_path) > 1000

    def speak(self, text: str) -> bool:
        ref_path = self.get_reference_voice_path()

        if not self.is_reference_available():
            # Reference voice not recorded yet -> transparent fallback to robotic voice
            return self.fallback.speak(text)

        # When reference is present, attempt local cloned synthesis
        try:
            cloned_success = self._synthesize_and_play_cloned(text, ref_path)
            if cloned_success:
                return True
        except Exception as e:
            print(f"[tts] Cloned voice generation failed, falling back to robotic: {e}", flush=True)

        return self.fallback.speak(text)

    def _get_f5_instance(self):
        if self._init_failed:
            return None
        if self._f5_instance is None:
            try:
                # Ensure torchaudio uses soundfile for robust WAV decoding without libtorchcodec
                try:
                    import torchaudio
                    import soundfile as sf
                    import torch
                    if not getattr(torchaudio, "_nexo_patched", False):
                        _orig_load = torchaudio.load
                        def _safe_load(filepath, *args, **kwargs):
                            try:
                                data, sr = sf.read(filepath)
                                tensor = torch.from_numpy(data).float()
                                if tensor.ndim == 1:
                                    tensor = tensor.unsqueeze(0)
                                elif tensor.ndim == 2:
                                    tensor = tensor.t()
                                return tensor, sr
                            except Exception:
                                return _orig_load(filepath, *args, **kwargs)
                        torchaudio.load = _safe_load
                        torchaudio._nexo_patched = True
                except Exception as pe:
                    print(f"[tts] Audio loader patch notice: {pe}", flush=True)

                from f5_tts.api import F5TTS
                print("[tts] Initializing local F5-TTS zero-shot voice model...", flush=True)
                self._f5_instance = F5TTS()
                print("[tts] F5-TTS model loaded successfully.", flush=True)
            except Exception as e:
                print(f"[tts] Could not initialize F5TTS: {e}", flush=True)
                self._init_failed = True
                return None
        return self._f5_instance

    def _synthesize_and_play_cloned(self, text: str, ref_audio_path: str) -> bool:
        """
        Synthesize text matching the reference audio timbre, then play via paplay.
        Returns True if played successfully, False to trigger fallback.
        """
        output_wav = "/tmp/nexo_cloned.wav"
        ref_text = self.get_reference_text()

        # Try API first
        engine = self._get_f5_instance()
        if engine is not None:
            try:
                engine.infer(
                    ref_file=ref_audio_path,
                    ref_text=ref_text,
                    gen_text=text,
                    nfe_step=16,
                    file_wave=output_wav,
                    remove_silence=False,
                    seed=42,
                )
                if os.path.exists(output_wav) and os.path.getsize(output_wav) > 1000:
                    return self._play_audio(output_wav)
            except Exception as e:
                print(f"[tts] F5TTS API inference error: {e}", flush=True)

        # Try CLI fallback if API failed or CLI is directly available
        cli_bin = shutil.which("f5-tts_infer-cli")
        if cli_bin:
            try:
                cmd = [
                    cli_bin,
                    "--model", "F5-TTS",
                    "--ref_audio", ref_audio_path,
                    "--ref_text", ref_text,
                    "--gen_text", text,
                    "--output_file", output_wav,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if res.returncode == 0 and os.path.exists(output_wav):
                    return self._play_audio(output_wav)
            except Exception as e:
                print(f"[tts] F5TTS CLI inference error: {e}", flush=True)

        return False

    def _play_audio(self, wav_path: str) -> bool:
        player = "paplay" if shutil.which("paplay") else "aplay"
        try:
            self._active_proc = subprocess.Popen([player, wav_path])
            self._active_proc.wait()
            self._active_proc = None
            return True
        except Exception as e:
            print(f"[tts] Audio playback error ({player}): {e}", flush=True)
            self._active_proc = None
            return False

    def cancel(self) -> None:
        if self._active_proc:
            try:
                self._active_proc.terminate()
                self._active_proc.kill()
            except Exception:
                pass
            self._active_proc = None
        self.fallback.cancel()
