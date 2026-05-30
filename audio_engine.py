import pyttsx3
import speech_recognition as sr
import threading
import time
# Note: openwakeword might require more setup for custom models, but we'll use a placeholder or basic setup here.
# For a full implementation, you'd load the specific models.
try:
    import openwakeword
    from openwakeword.model import Model
    openwakeword.utils.download_models()
    oww_model = Model(wakeword_models=["hey_jarvis"]) # Placeholder since hey_nexovian would need training
except ImportError:
    oww_model = None

engine = pyttsx3.init()
engine.setProperty('rate', 160)
speak_lock = threading.Lock()

import ui_overlay

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
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            ui_overlay.show_state("listening")
            print("Listening for command...", flush=True)
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                text = r.recognize_google(audio) # Fallback to Google STT for simplicity if vosk isn't loaded
                print(f"Recognized: {text}")
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
    except Exception as e:
        print(f"Microphone error: {e}")
        return ""

def listen_for_wakeword(callback):
    """Background thread to listen for wake words."""
    import pyaudio
    import numpy as np
    
    if not oww_model:
        print("openWakeWord not available.")
        return
        
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280
    
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    print("Listening for wake word...")
    while True:
        try:
            pcm = np.frombuffer(mic_stream.read(CHUNK), dtype=np.int16)
            prediction = oww_model.predict(pcm)
            
            # Check if any model crossed the threshold
            for mdl in oww_model.prediction_buffer.keys():
                if prediction[mdl] > 0.5: # Threshold
                    print(f"Wake word {mdl} detected!")
                    callback()
                    time.sleep(2) # Debounce
                    break
        except Exception as e:
            print(f"Wake word error: {e}")
            time.sleep(1)
