import pyttsx3
import speech_recognition as sr
import threading
import time
import os
import sys
import json
import ui_overlay

engine = pyttsx3.init()
engine.setProperty('rate', 160)
speak_lock = threading.Lock()

def speak(text):
    with speak_lock:
        ui_overlay.show_state("speaking")
        print(f"Nexovian: {text}", flush=True)
        engine.say(text)
        engine.runAndWait()
        time.sleep(0.5)

def listen_for_command(timeout=10, phrase_time_limit=15):
    """Listens to the microphone and returns recognized text."""
    r = sr.Recognizer()
    r.energy_threshold = 1000 # Static threshold to avoid recalibration delay
    r.dynamic_energy_threshold = True
    r.pause_threshold = 2.5 # Wait for 2.5 seconds of silence before assuming the user is finished
    try:
        with sr.Microphone() as source:
            # We skip adjust_for_ambient_noise here because it eats the first 0.5 seconds of audio
            ui_overlay.show_state("listening")
            print("Listening for command...", flush=True)
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = r.recognize_google(audio)
                print(f"Recognized: {text}")
                # Reject garbage / very short sounds
                if len(text.strip()) < 2:
                    return ""
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return ""
    except Exception as e:
        print(f"Microphone error: {e}")
        return None

def listen_for_wakeword(callback, wake_words=["nexovian"]):
    """Background thread to listen for wake words using Vosk."""
    try:
        import vosk
        import pyaudio
        
        model_path = os.path.expanduser("~/.local/share/vosk-models/vosk-model-small-en-us-0.15")
        if not os.path.exists(model_path):
            print(f"Vosk model not found at {model_path}. Run install_dependencies.sh")
            return
            
        vosk.SetLogLevel(-1)
        model = vosk.Model(model_path)
        rec = vosk.KaldiRecognizer(model, 16000)
        
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
        stream.start_stream()
        
        print(f"Listening for wake words: {', '.join(wake_words)}...")
        
        while True:
            if ui_overlay.get_ui().active:
                if stream.is_active():
                    stream.stop_stream()
                time.sleep(0.5)
                continue
            else:
                if not stream.is_active():
                    stream.start_stream()
                    
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get('text', '')
                if text:
                    print(f"Vosk heard (standby): '{text}'")
                    for w in wake_words:
                        if w in text:
                            print(f"Wake word '{w}' detected!")
                            callback()
                            time.sleep(2) # Debounce
                            break
    except Exception as e:
        print(f"Wake word engine error: {e}")
        time.sleep(5)
