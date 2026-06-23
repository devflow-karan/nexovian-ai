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

last_mute_check_time = 0.0
cached_mute_status = False

def is_microphone_muted():
    global last_mute_check_time, cached_mute_status
    now = time.time()
    if now - last_mute_check_time < 2.0:
        return cached_mute_status

    import subprocess
    last_mute_check_time = now
    
    # Method 1: Check using pactl
    try:
        result = subprocess.run(
            ["pactl", "get-source-mute", "@DEFAULT_SOURCE@"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            output = result.stdout.strip().lower()
            if "mute: yes" in output:
                cached_mute_status = True
                return True
            elif "mute: no" in output:
                cached_mute_status = False
                return False
    except Exception:
        pass

    # Method 2: Check using amixer sget Capture as fallback
    try:
        result = subprocess.run(
            ["amixer", "sget", "Capture"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0:
            output = result.stdout.strip().lower()
            if "[off]" in output and "[on]" not in output:
                cached_mute_status = True
                return True
            else:
                cached_mute_status = False
                return False
    except Exception:
        pass

    cached_mute_status = False
    return False

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
    if is_microphone_muted():
        print("[audio_engine] Microphone is muted. Cannot listen for command.", flush=True)
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
            
            has_logged_muted = False
            
            while True:
                import text_input_ui
                bar_visible = False
                if text_input_ui._bar_instance is not None:
                    try:
                        bar_visible = text_input_ui._bar_instance.get_visible()
                    except Exception:
                        pass

                muted = is_microphone_muted()
                if ui_overlay.get_ui().active or is_system_locked or is_speaking or bar_visible or muted:
                    if muted:
                        if not has_logged_muted:
                            print("[audio_engine] Microphone is muted. Pausing wake word listener.", flush=True)
                            has_logged_muted = True
                    else:
                        has_logged_muted = False
                        
                    if stream.is_active():
                        stream.stop_stream()
                    time.sleep(0.5)
                    continue
                else:
                    has_logged_muted = False
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
                        dynamic_wake_words = wake_words + [f"hey {today_day}"]
                        for w in dynamic_wake_words:
                            if w in text:
                                print(f"Wake word '{w}' detected!")
                                callback()
                                time.sleep(2) # Debounce
                                break
        except Exception as e:
            print(f"Wake word engine error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
