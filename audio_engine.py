import pyttsx3
import speech_recognition as sr
import threading
import time
import os
import sys
import json
import ui_overlay

# Try to load the robotic voice engine
try:
    import robotic_voice
    USE_ROBOTIC_VOICE = True
    print("[audio_engine] Robotic voice engine loaded.", flush=True)
except Exception as _e:
    USE_ROBOTIC_VOICE = False
    print(f"[audio_engine] Robotic voice unavailable, using pyttsx3: {_e}", flush=True)

# pyttsx3 fallback engine
engine = pyttsx3.init()
engine.setProperty('rate', 160)
speak_lock = threading.Lock()
active_conversation = False
is_system_locked = False
active_microphone_source = None
microphone_lock = threading.Lock()
is_speaking = False

def _get_user_name():
    try:
        import config_manager
        name = config_manager.get_user_name()
        if name:
            return name
    except Exception:
        pass
    try:
        import pwd
        return pwd.getpwuid(os.getuid())[4].split(',')[0] or os.getlogin()
    except Exception:
        return "User"

def set_system_locked(locked):
    global is_system_locked, active_microphone_source
    is_system_locked = locked
    if locked:
        print("[audio_engine] System locked. Cancelling active operations.", flush=True)
        # Cancel robotic voice
        if USE_ROBOTIC_VOICE:
            try:
                robotic_voice.cancel_active_speech()
            except Exception:
                pass
        # Cancel pyttsx3
        try:
            engine.stop()
        except Exception:
            pass
        # Cancel active microphone
        with microphone_lock:
            if active_microphone_source and active_microphone_source.stream:
                try:
                    active_microphone_source.stream.close()
                except Exception:
                    pass
                active_microphone_source = None
    else:
        # Reset robotic voice cancellation
        if USE_ROBOTIC_VOICE:
            try:
                robotic_voice.reset_cancellation()
            except Exception:
                pass

def speak(text):
    global is_speaking
    if is_system_locked:
        return
    import config_manager
    with speak_lock:
        if is_system_locked:
            return
        is_speaking = True
        try:
            ui_overlay.show_state("speaking")
            print(f"Nexovian: {text}", flush=True)
            if USE_ROBOTIC_VOICE and config_manager.use_robotic_voice():
                robotic_voice.speak_robotic(text)
            else:
                engine.say(text)
                engine.runAndWait()
            time.sleep(0.5)
        finally:
            is_speaking = False
            if not active_conversation:
                try:
                    ui_overlay.hide()
                except Exception:
                    pass

def listen_for_command(timeout=10, phrase_time_limit=15):
    """Listens to the microphone and returns recognized text."""
    global active_microphone_source
    if is_system_locked:
        return None
    r = sr.Recognizer()
    r.energy_threshold = 1000 # Static threshold to avoid recalibration delay
    r.dynamic_energy_threshold = True
    r.pause_threshold = 2.5 # Wait for 2.5 seconds of silence before assuming the user is finished
    try:
        with sr.Microphone() as source:
            with microphone_lock:
                if is_system_locked:
                    return None
                active_microphone_source = source
            try:
                ui_overlay.show_state("listening")
                print("Listening for command...", flush=True)
                try:
                    audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                    text = r.recognize_google(audio)
                    print(f"{_get_user_name()}: {text}")
                    # Reject garbage / very short sounds
                    if len(text.strip()) < 2:
                        return ""
                    return text
                except sr.WaitTimeoutError:
                    return None
                except sr.UnknownValueError:
                    return ""
            finally:
                with microphone_lock:
                    active_microphone_source = None
    except Exception as e:
        print(f"Microphone error: {e}")
        return None

def listen_for_wakeword(callback, wake_words=["nexovian"]):
    """Background thread to listen for wake words using Vosk."""
    try:
        import vosk
        import pyaudio
    except ImportError as err:
        print(f"Missing dependency: {err}")
        return

    model_path = os.path.expanduser("~/.local/share/vosk-models/vosk-model-small-en-us-0.15")
    if not os.path.exists(model_path):
        print(f"Vosk model not found at {model_path}. Run install_dependencies.sh")
        return

    vosk.SetLogLevel(-1)
    try:
        model = vosk.Model(model_path)
    except Exception as model_err:
        print(f"Error loading Vosk model: {model_err}")
        return

    while True:
        try:
            rec = vosk.KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
            stream.start_stream()
            
            print(f"Listening for wake words: {', '.join(wake_words)}...")
            
            while True:
                import text_input_ui
                bar_visible = False
                if text_input_ui._bar_instance is not None:
                    try:
                        bar_visible = text_input_ui._bar_instance.get_visible()
                    except Exception:
                        pass

                if ui_overlay.get_ui().active or is_system_locked or is_speaking or bar_visible:
                    if stream.is_active():
                        stream.stop_stream()
                    time.sleep(0.5)
                    continue
                else:
                    if not stream.is_active():
                        stream.start_stream()
                        
                try:
                    data = stream.read(4000, exception_on_overflow=False)
                    if not data:
                        time.sleep(0.05)
                        continue
                except Exception as stream_err:
                    print(f"[audio_engine] Stream read error: {stream_err}. Retrying in 1s...", flush=True)
                    time.sleep(1.0)
                    continue

                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    text = res.get('text', '')
                    if text:
                        print(f"Vosk heard (standby): '{text}'")
                        import datetime
                        today_day = datetime.datetime.now().strftime("%A").lower()
                        dynamic_wake_words = wake_words + [today_day, f"hey {today_day}"]
                        for w in dynamic_wake_words:
                            if w in text:
                                print(f"Wake word '{w}' detected!")
                                callback()
                                time.sleep(2) # Debounce
                                break
        except Exception as e:
            print(f"Wake word engine error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
