#!/usr/bin/env python3
"""
Diagnostic CLI tool to test openWakeWord detection for Nexovian AI.
Can test live from the microphone or evaluate specific synthetic phrases.
"""

import os
import sys
import time
import argparse
import numpy as np

# Add repository root to path so config_manager can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_microphone_test(model_path=None, threshold=0.5, vad_threshold=0.0):
    import pyaudio
    from openwakeword.model import Model
    import config_manager

    if model_path is None:
        model_path = config_manager.get_wakeword_model_path()

    print(f"Loading wake word model: {model_path or 'Default openWakeWord models'}")
    if model_path and os.path.exists(model_path):
        oww = Model(wakeword_model_paths=[model_path], vad_threshold=vad_threshold)
    else:
        print("Warning: Custom model not found, loading default pre-trained models.")
        oww = Model(vad_threshold=vad_threshold)

    active_models = list(oww.models.keys())
    print(f"Active detection models: {active_models}")
    print(f"Detection Threshold: {threshold}")
    print("\n--- Listening to microphone (Press Ctrl+C to stop) ---")

    CHUNK = 1280
    RATE = 16000

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            preds = oww.predict(audio)

            for m in active_models:
                score = preds.get(m, 0.0)
                if score >= threshold:
                    bar = "█" * int(score * 20)
                    print(f"\n🔔 [WAKE WORD DETECTED] Model: {m:<15} Score: {score:.4f} |{bar:<20}|")
                elif score >= 0.15:
                    bar = "▒" * int(score * 20)
                    print(f"\rPartial: {m:<15} Score: {score:.4f} |{bar:<20}|", end="", flush=True)

    except KeyboardInterrupt:
        print("\nStopping test...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def run_synthetic_eval(model_path=None):
    import subprocess
    import wave
    from scipy.signal import resample
    from openwakeword.model import Model
    import config_manager

    if model_path is None:
        model_path = config_manager.get_wakeword_model_path()

    if not model_path or not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return

    test_cases = [
        ("Nexovian", True),
        ("Hey Nexovian", True),
        ("Hello Nexovian", True),
        ("Nexo", True),
        ("Hello Nexo", True),
        ("Next", False),
        ("Hello next", False),
        ("No the next movie and", False),
        ("Maximum number", False),
        ("What time is it", False),
        ("Open visual studio code", False),
        ("Good morning Karan", False)
    ]

    print(f"Running evaluation with model: {model_path}")
    print(f"{'Phrase':<25} | {'Expected':<8} | {'Max Score':<10} | Result")
    print("-" * 55)

    tmp_wav = "/tmp/test_eval.wav"
    for phrase, expected in test_cases:
        subprocess.run(["espeak", "-v", "en", "-s", "150", "-w", tmp_wav, phrase],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        with wave.open(tmp_wav, 'rb') as wf:
            audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
            if wf.getframerate() != 16000:
                audio = resample(audio.astype(np.float32), int(len(audio)*16000/wf.getframerate())).astype(np.int16)
            audio = np.pad(audio, (0, 3200), mode='constant')

        oww = Model(wakeword_model_paths=[model_path])
        max_s = 0.0
        for c in range(len(audio) // 1280):
            chunk = audio[c*1280 : (c+1)*1280]
            pred = oww.predict(chunk)
            s = pred.get(os.path.basename(model_path)[:-5], 0.0)
            if s > max_s:
                max_s = s

        passed = (max_s >= 0.5) if expected else (max_s < 0.25)
        print(f"{phrase:<25} | {str(expected):<8} | {max_s:<10.4f} | {'PASS' if passed else 'FAIL'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test openWakeWord detection for Nexovian")
    parser.add_argument("--eval", action="store_true", help="Run synthetic evaluation suite")
    parser.add_argument("--model", type=str, default=None, help="Path to custom ONNX model")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection threshold (0.0 - 1.0)")
    args = parser.parse_args()

    if args.eval:
        run_synthetic_eval(args.model)
    else:
        run_microphone_test(args.model, args.threshold)
