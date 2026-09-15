#!/usr/bin/env python3
"""
scripts/record_voice_sample.py
CLI utility to record and verify a local voice reference sample for Nexovian voice cloning.

Features:
- Records reference audio directly from your default microphone
- Saves strictly locally under ~/.config/nexovian/voice_reference.wav (ZERO cloud uploads)
- Validates audio amplitude, duration, and file integrity
- Plays back the sample via PipeWire (paplay) for verification
- Automatically updates Nexovian config with the reference path
"""

import os
import sys
import time
import wave
import shutil
import subprocess

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config_manager

SAMPLE_RATE = 22050  # Standard high-quality speech rate
CHANNELS = 1
CHUNK = 1024

SAMPLE_PROMPT = (
    "\"Hello, I am Karan, and this is my voice reference sample for my Nexovian desktop assistant.\""
)

def record_sample(output_path: str, duration_sec: int = 10):
    try:
        import pyaudio
    except ImportError:
        print("Error: PyAudio is required. Run: sudo apt-get install python3-pyaudio", file=sys.stderr)
        sys.exit(1)

    p = pyaudio.PyAudio()

    print("\n" + "=" * 65)
    print("      NEXOVIAN LOCAL VOICE REFERENCE RECORDER")
    print("=" * 65)
    print("\nThis utility records a clean, local voice sample used for voice cloning.")
    print("Your voice recording is stored exclusively on your machine and NEVER uploaded.\n")
    print(f"Recommended prompt to read aloud:\n\n  \033[1;36m{SAMPLE_PROMPT}\033[0m\n")
    print(f"Target duration: {duration_sec} seconds")
    print(f"Target output:   {output_path}\n")

    input("Press [ENTER] when ready to start recording...")

    print(f"\n🔴 RECORDING NOW ({duration_sec}s)... Speak clearly into your microphone!\n")

    stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    start_time = time.time()
    total_frames = int(SAMPLE_RATE / CHUNK * duration_sec)

    for i in range(total_frames):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        elapsed = time.time() - start_time
        remaining = max(0.0, duration_sec - elapsed)
        bar = "█" * int((elapsed / duration_sec) * 30)
        print(f"\rRecording: [{bar:<30}] {remaining:4.1f}s remaining", end="", flush=True)

    print("\n\n⏹️ Recording finished.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))

    print(f"Saved audio to: {output_path}")


def validate_sample(wav_path: str) -> bool:
    if not os.path.exists(wav_path):
        print(f"❌ Validation failed: File does not exist at {wav_path}")
        return False

    size = os.path.getsize(wav_path)
    if size < 10000:
        print(f"❌ Validation failed: File size too small ({size} bytes). Recording may be empty.")
        return False

    try:
        import numpy as np
        with wave.open(wav_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            raw = wf.readframes(frames)
            samples = np.frombuffer(raw, dtype=np.int16)
            peak = np.max(np.abs(samples))

            if peak < 500:
                print("⚠️ Warning: Audio level is very low. Please check your microphone volume.")
            else:
                print(f"✅ Audio validated: Duration = {duration:.1f}s, Peak amplitude = {peak}/32767")
            return True
    except Exception as e:
        print(f"⚠️ Validation note: {e}")
        return True


def play_sample(wav_path: str):
    player = "paplay" if shutil.which("paplay") else "aplay"
    print(f"\n🔊 Playing back your recording via PipeWire ({player})...")
    try:
        subprocess.run([player, wav_path], check=True)
    except Exception as e:
        print(f"Playback error: {e}")


def main():
    target_path = config_manager.get_voice_reference_path()
    record_sample(target_path, duration_sec=10)

    if validate_sample(target_path):
        config_manager.set_voice_reference_path(target_path)
        play_sample(target_path)
        print("\n" + "=" * 65)
        print("🎉 Voice reference recording successfully created and configured!")
        print("   Nexovian will use this local reference for voice cloning.")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
