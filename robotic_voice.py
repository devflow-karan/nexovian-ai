"""
robotic_voice.py
Converts text to a robotic AI-sounding voice using:
  1. espeak (TTS) -> raw WAV
  2. numpy ring modulator + pitch shift -> robotic effect
  3. aplay -> plays back the processed audio

No SoX required. Fully offline.
"""
import os
import wave
import struct
import subprocess
import tempfile
import math
import numpy as np
import threading

active_proc = None
proc_lock = threading.Lock()
is_cancelled = False

def cancel_active_speech():
    global is_cancelled, active_proc
    with proc_lock:
        is_cancelled = True
        if active_proc:
            try:
                active_proc.terminate()
                active_proc.kill()
            except Exception:
                pass
            active_proc = None

def reset_cancellation():
    global is_cancelled
    with proc_lock:
        is_cancelled = False



# ─── Tunable parameters ──────────────────────────────────────────────────────
ESPEAK_VOICE    = "en-us"       # espeak voice
ESPEAK_SPEED    = 155           # words per minute (slower = more robotic feel)
ESPEAK_PITCH    = 25            # 0-99, lower = deeper
ESPEAK_AMPLITUDE = 180          # 0-200
RING_FREQ       = 200.0         # Hz for ring modulator carrier (buzz frequency)
RING_MIX        = 0.12          # 0=dry, 1=full ring-mod (reduced for clarity)
ECHO_DELAY_MS   = 15            # ms of metallic echo
ECHO_DECAY      = 0.05          # echo volume multiplier (reduced for clarity)
# ─────────────────────────────────────────────────────────────────────────────


def _espeak_to_wav(text: str, out_path: str):
    """Run espeak to produce a WAV file."""
    subprocess.run(
        [
            "espeak",
            "-v", ESPEAK_VOICE,
            "-s", str(ESPEAK_SPEED),
            "-p", str(ESPEAK_PITCH),
            "-a", str(ESPEAK_AMPLITUDE),
            "-w", out_path,
            text,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _apply_robot_fx(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Apply ring modulation + short metallic echo to a float32 sample array."""
    t = np.arange(len(samples)) / sample_rate

    # 1. Ring modulator: multiply by carrier sine wave
    carrier = np.sin(2 * math.pi * RING_FREQ * t)
    ring_modded = samples * carrier
    mixed = (1.0 - RING_MIX) * samples + RING_MIX * ring_modded

    # 2. Metallic echo: add a short delayed copy
    delay_samples = int(sample_rate * ECHO_DELAY_MS / 1000)
    echo = np.zeros_like(mixed)
    echo[delay_samples:] = mixed[:-delay_samples] * ECHO_DECAY
    result = mixed + echo

    # 3. Normalize to prevent clipping
    peak = np.max(np.abs(result))
    if peak > 0:
        result = result / peak * 0.92

    return result.astype(np.float32)


def _process_wav(in_path: str, out_path: str):
    """Read WAV, apply FX, write processed WAV."""
    with wave.open(in_path, "rb") as wf:
        n_channels  = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate  = wf.getframerate()
        n_frames     = wf.getnframes()
        raw          = wf.readframes(n_frames)

    # Decode to float32 (supports 8-bit, 16-bit, 32-bit PCM)
    if sample_width == 1:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        # Unsupported — just copy through
        samples = np.frombuffer(raw, dtype=np.float32)

    # Mix down to mono if stereo
    if n_channels == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)

    processed = _apply_robot_fx(samples, sample_rate)

    # Encode back to int16 mono
    out_samples = (processed * 32767).astype(np.int16)

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(out_samples.tobytes())


def speak_robotic(text: str):
    """
    Main entry point. Converts text → robotic audio and plays it.
    Falls back to plain espeak if anything goes wrong.
    """
    global active_proc
    with proc_lock:
        if is_cancelled:
            return

    tmp_dir = tempfile.gettempdir()
    raw_wav  = os.path.join(tmp_dir, "nexo_raw.wav")
    robo_wav = os.path.join(tmp_dir, "nexo_robot.wav")

    try:
        # Step 1: TTS → WAV
        with proc_lock:
            if is_cancelled:
                return
            active_proc = subprocess.Popen(
                [
                    "espeak",
                    "-v", ESPEAK_VOICE,
                    "-s", str(ESPEAK_SPEED),
                    "-p", str(ESPEAK_PITCH),
                    "-a", str(ESPEAK_AMPLITUDE),
                    "-w", raw_wav,
                    text,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        active_proc.wait()
        
        with proc_lock:
            active_proc = None
            if is_cancelled:
                return

        # Step 2: Apply robotic FX
        _process_wav(raw_wav, robo_wav)

        # Step 3: Play
        with proc_lock:
            if is_cancelled:
                return
            active_proc = subprocess.Popen(
                ["aplay", "-q", robo_wav],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        active_proc.wait()

    except Exception as e:
        with proc_lock:
            if is_cancelled:
                return
        print(f"[robotic_voice] Fallback to plain espeak: {e}", flush=True)
        try:
            with proc_lock:
                if is_cancelled:
                    return
                active_proc = subprocess.Popen(
                    ["espeak", "-v", ESPEAK_VOICE, "-s", str(ESPEAK_SPEED),
                     "-p", str(ESPEAK_PITCH), text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            active_proc.wait()
        except Exception:
            pass
    finally:
        with proc_lock:
            active_proc = None
        for f in (raw_wav, robo_wav):
            try:
                os.remove(f)
            except OSError:
                pass
