#!/usr/bin/env python3
"""
Custom Wake-Word Trainer for Nexovian AI (openWakeWord format).
Synthesizes phonetic variations of 'Nexovian' and negative phrases,
extracts Google speech embeddings via openWakeWord AudioFeatures,
trains a streaming MLP classifier, and exports a deployable ONNX model.
"""

import os
import sys
import wave
import subprocess
import numpy as np
from scipy.signal import resample
from sklearn.neural_network import MLPClassifier
import onnx
from onnx import helper, TensorProto
import onnxruntime as ort
from openwakeword.model import Model
from openwakeword.utils import AudioFeatures

def generate_wav(text, output_wav, voice="en", speed=150, pitch=50):
    cmd = [
        "espeak",
        "-v", voice,
        "-s", str(speed),
        "-p", str(pitch),
        "-w", output_wav,
        text
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def load_and_resample(wav_path, target_sr=16000):
    with wave.open(wav_path, 'rb') as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        audio_bytes = wf.readframes(n_frames)
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        if sr != target_sr:
            num_samples = int(len(audio) * float(target_sr) / sr)
            audio = resample(audio.astype(np.float32), num_samples).astype(np.int16)
        return audio

def build_onnx_model(weights, biases, output_path):
    W1, W2, W3 = weights
    B1, B2, B3 = biases

    init_W1 = helper.make_tensor('W1', TensorProto.FLOAT, W1.shape, W1.flatten().tolist())
    init_B1 = helper.make_tensor('B1', TensorProto.FLOAT, B1.shape, B1.tolist())
    init_W2 = helper.make_tensor('W2', TensorProto.FLOAT, W2.shape, W2.flatten().tolist())
    init_B2 = helper.make_tensor('B2', TensorProto.FLOAT, B2.shape, B2.tolist())
    init_W3 = helper.make_tensor('W3', TensorProto.FLOAT, W3.shape, W3.flatten().tolist())
    init_B3 = helper.make_tensor('B3', TensorProto.FLOAT, B3.shape, B3.tolist())

    node_flatten = helper.make_node('Flatten', inputs=['input'], outputs=['flat'], axis=1)
    node_gemm1 = helper.make_node('Gemm', inputs=['flat', 'W1', 'B1'], outputs=['h1'], alpha=1.0, beta=1.0)
    node_relu1 = helper.make_node('Relu', inputs=['h1'], outputs=['h1_relu'])

    node_gemm2 = helper.make_node('Gemm', inputs=['h1_relu', 'W2', 'B2'], outputs=['h2'], alpha=1.0, beta=1.0)
    node_relu2 = helper.make_node('Relu', inputs=['h2'], outputs=['h2_relu'])

    node_gemm3 = helper.make_node('Gemm', inputs=['h2_relu', 'W3', 'B3'], outputs=['h3'], alpha=1.0, beta=1.0)
    node_sigmoid = helper.make_node('Sigmoid', inputs=['h3'], outputs=['output'])

    input_tensor = helper.make_tensor_value_info('input', TensorProto.FLOAT, [1, 16, 96])
    output_tensor = helper.make_tensor_value_info('output', TensorProto.FLOAT, [1, 1])

    graph = helper.make_graph(
        [node_flatten, node_gemm1, node_relu1, node_gemm2, node_relu2, node_gemm3, node_sigmoid],
        'nexovian_wakeword',
        [input_tensor],
        [output_tensor],
        [init_W1, init_B1, init_W2, init_B2, init_W3, init_B3]
    )

    model_proto = helper.make_model(graph, producer_name='nexovian_trainer', opset_imports=[helper.make_opsetid('', 17)])
    onnx.checker.check_model(model_proto)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    onnx.save(model_proto, output_path)
    print(f"[Trainer] Successfully exported ONNX model to: {output_path}")

def train(output_path=None):
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_dir, "models", "nexovian.onnx")

    tmp_dir = "/tmp/nexovian_ww_train"
    os.makedirs(tmp_dir, exist_ok=True)

    positive_phrases = [
        "Nexovian",
        "Hey Nexovian",
        "Hello Nexovian",
        "Nexo",
        "Hey Nexo",
        "Hello Nexo",
        "OK Nexovian"
    ]

    negative_phrases = [
        "next",
        "next one",
        "hello next",
        "no the next movie and",
        "the next movie",
        "movie and",
        "maximum number",
        "maximum",
        "number",
        "movie",
        "nexus",
        "mexico",
        "nokia",
        "what time is it",
        "what is the time",
        "what day is today",
        "open visual studio code",
        "open terminal",
        "open browser",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you doing",
        "check the weather",
        "thank you very much",
        "thanks a lot",
        "stop",
        "cancel",
        "exit",
        "quit",
        "pause",
        "alexa",
        "hey siri",
        "ok google",
        "hey jarvis",
        "computer",
        "music",
        "play music",
        "turn up volume",
        "system lock",
        "today is a nice day",
        "hello there",
        "hi how are you",
        "tell me a joke",
        "who made you",
        "can you hear me",
        "yes please",
        "no thank you",
        "sure thing",
        "never mind",
        "shutdown the system"
    ]

    voices = ["en", "en-us", "en-uk", "en+m1", "en+m2", "en+m3", "en+f1", "en+f2", "en+f3"]
    speeds = [130, 150, 175]
    pitches = [35, 50, 65]

    X = []
    y = []

    def reset_af(af_obj):
        af_obj.raw_data_buffer.clear()
        af_obj.melspectrogram_buffer.fill(0)
        af_obj.feature_buffer.fill(0)
        af_obj.accumulated_samples = 0

    af = AudioFeatures()

    print("[Trainer] Generating positive and negative speech samples with streaming feature extraction...")

    # 1. Process Positive Phrases (sliding window streaming)
    p_idx = 0
    for phrase in positive_phrases:
        for v in voices:
            for s in speeds:
                for p in pitches:
                    wav_file = os.path.join(tmp_dir, f"pos_{p_idx}.wav")
                    try:
                        generate_wav(phrase, wav_file, voice=v, speed=s, pitch=p)
                        audio = load_and_resample(wav_file)
                        
                        # Pad trailing silence so the full phrase sits in the 16-frame buffer
                        audio = np.pad(audio, (0, 3200), mode='constant')
                        
                        reset_af(af)
                        n_chunks = len(audio) // 1280
                        for c in range(n_chunks):
                            chunk = audio[c*1280 : (c+1)*1280]
                            af(chunk)
                            feat = af.get_features(16).reshape(1, -1)
                            # The trigger occurs on the last 2 frames of the utterance
                            if c >= n_chunks - 2:
                                X.append(feat)
                                y.append(1)
                            elif c % 2 == 0:
                                X.append(feat)
                                y.append(0)

                        p_idx += 1
                    except Exception:
                        pass

    pos_count = sum(1 for label in y if label == 1)
    print(f"[Trainer] Collected {pos_count} positive trigger frames across {p_idx} utterances.")

    # 2. Process Negative Phrases (sliding window streaming)
    n_idx = 0
    neg_frames = 0
    for phrase in negative_phrases:
        for v in ["en", "en-us", "en-uk", "en+m1", "en+f1"]:
            for s in [135, 160]:
                wav_file = os.path.join(tmp_dir, f"neg_{n_idx}.wav")
                try:
                    generate_wav(phrase, wav_file, voice=v, speed=s, pitch=50)
                    audio = load_and_resample(wav_file)
                    audio = np.pad(audio, (0, 3200), mode='constant')

                    reset_af(af)
                    n_chunks = len(audio) // 1280
                    for c in range(n_chunks):
                        chunk = audio[c*1280 : (c+1)*1280]
                        af(chunk)
                        feat = af.get_features(16).reshape(1, -1)
                        # Every frame of a negative utterance is labeled 0
                        X.append(feat)
                        y.append(0)
                        neg_frames += 1

                    n_idx += 1
                except Exception:
                    pass

    # 3. Add ambient noise and silence frames
    for _ in range(300):
        noise = np.random.randint(-200, 200, 20480, dtype=np.int16)
        reset_af(af)
        af(noise)
        X.append(af.get_features(16).reshape(1, -1))
        y.append(0)
        neg_frames += 1

    print(f"[Trainer] Collected {neg_frames} negative frames across {n_idx} non-wake utterances and noise.")

    X_mat = np.vstack(X).astype(np.float32)
    y_vec = np.array(y, dtype=np.int32)

    print(f"[Trainer] Training classifier on {X_mat.shape[0]} total frames (positive={pos_count}, negative={len(y)-pos_count})...")
    clf = MLPClassifier(
        hidden_layer_sizes=(128, 64),
        activation='relu',
        alpha=0.02,
        max_iter=500,
        random_state=42
    )
    clf.fit(X_mat, y_vec)
    acc = clf.score(X_mat, y_vec)
    print(f"[Trainer] Classifier training complete. Training accuracy: {acc*100:.2f}%")

    # Extract weights
    weights = [
        clf.coefs_[0].astype(np.float32),
        clf.coefs_[1].astype(np.float32),
        clf.coefs_[2].astype(np.float32)
    ]
    biases = [
        clf.intercepts_[0].astype(np.float32),
        clf.intercepts_[1].astype(np.float32),
        clf.intercepts_[2].astype(np.float32)
    ]

    build_onnx_model(weights, biases, output_path)

    # Validate model
    print("[Trainer] Running validation suite...")
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
        ("Open terminal", False),
        ("Good morning Karan", False)
    ]

    oww = Model(wakeword_model_paths=[output_path])
    all_passed = True

    print(f"{'Phrase':<25} | {'Expected':<8} | {'Max Score':<10} | Result")
    print("-" * 55)
    for phrase, expected in test_cases:
        test_wav = os.path.join(tmp_dir, "eval.wav")
        generate_wav(phrase, test_wav, voice="en", speed=150, pitch=50)
        audio = load_and_resample(test_wav)
        audio = np.pad(audio, (0, 3200), mode='constant')

        max_s = 0.0
        oww_eval = Model(wakeword_model_paths=[output_path])
        for c in range(len(audio) // 1280):
            chunk = audio[c*1280 : (c+1)*1280]
            pred = oww_eval.predict(chunk)
            s = pred.get("nexovian", 0.0)
            if s > max_s:
                max_s = s

        passed = (max_s >= 0.5) if expected else (max_s < 0.25)
        if not passed:
            all_passed = False
        print(f"{phrase:<25} | {str(expected):<8} | {max_s:<10.4f} | {'PASS' if passed else 'FAIL'}")

    print("-" * 55)
    if all_passed:
        print("[Trainer] All validation tests passed!")
    else:
        print("[Trainer] Some tests did not meet strict thresholds, but model is saved.")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    train(out)
