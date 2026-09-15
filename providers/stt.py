"""
providers/stt.py
Concrete implementations of STTProvider for local Vosk and optional Google Speech Recognition.
"""

import json
import os
from typing import Any, Optional
import speech_recognition as sr

from providers.base import STTProvider
import config_manager

_vosk_model = None

def _get_loaded_vosk_model():
    global _vosk_model
    if _vosk_model is not None:
        return _vosk_model

    try:
        import vosk
        vosk.SetLogLevel(-1) # Hide verbose logging
        model_path = config_manager.get_vosk_model_path()
        if model_path and os.path.exists(model_path):
            _vosk_model = vosk.Model(model_path)
            return _vosk_model
    except Exception as e:
        print(f"[stt] Error initializing Vosk model: {e}", flush=True)

    return None


class VoskSTTProvider(STTProvider):
    """Local offline Speech-to-Text provider powered by Vosk."""

    @property
    def name(self) -> str:
        return "vosk"

    def transcribe(self, recognizer: sr.Recognizer, audio_data: sr.AudioData) -> str:
        try:
            import vosk
            model = _get_loaded_vosk_model()
            if model is None:
                print("[stt] Vosk model not available.", flush=True)
                return ""

            raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
            rec = vosk.KaldiRecognizer(model, 16000)
            rec.AcceptWaveform(raw_bytes)
            res = json.loads(rec.FinalResult())
            text = res.get("text", "").strip()
            return text
        except Exception as e:
            print(f"[stt] Vosk transcription error: {e}", flush=True)
            return ""


class GoogleSTTProvider(STTProvider):
    """Cloud Speech-to-Text provider using Google Web Speech API."""

    @property
    def name(self) -> str:
        return "google"

    def transcribe(self, recognizer: sr.Recognizer, audio_data: sr.AudioData) -> str:
        try:
            return recognizer.recognize_google(audio_data).strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as req_err:
            print(f"[stt] Google speech recognition service error: {req_err}", flush=True)
            return ""
        except Exception as e:
            print(f"[stt] Google recognition error: {e}", flush=True)
            return ""
