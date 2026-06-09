#!/usr/bin/env python3
import os
import sys
import pwd
import json
import queue
import time
import pyttsx3
import vosk
import sounddevice as sd
import threading

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

# Constants
TODO_FILE = os.path.expanduser("~/Documents/todo.txt")
MODEL_DIR = os.path.expanduser("~/.local/share/vosk-models/vosk-model-small-en-us-0.15")

# Initialize TTS
engine = pyttsx3.init()
engine.setProperty('rate', 160)

is_system_locked = False
active_microphone_source = None
microphone_lock = threading.Lock()

def speak(text):
    if is_system_locked:
        return
    print(f"Assistant: {text}", flush=True)
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass
    time.sleep(0.5) # Wait for room echo to dissipate

# Initialize Vosk Model (done lazily to avoid blocking start up if not needed, but better to load once)
try:
    if not os.path.exists(MODEL_DIR):
        print(f"Vosk model not found at {MODEL_DIR}. Please run install_dependencies.sh")
        sys.exit(1)
    vosk.SetLogLevel(-1) # Hide vosk logs
    model = vosk.Model(MODEL_DIR)
except Exception as e:
    print(f"Error loading Vosk model: {e}")
    sys.exit(1)

import speech_recognition as sr

def listen(timeout=10):
    """Listens to the microphone and returns recognized text using SpeechRecognition + Vosk."""
    global active_microphone_source
    if is_system_locked:
        return ""
    print("Listening...", flush=True)
    r = sr.Recognizer()
    try:
        with sr.Microphone(sample_rate=16000) as source:
            with microphone_lock:
                if is_system_locked:
                    return ""
                active_microphone_source = source
            
            try:
                # Briefly adjust for ambient noise
                r.adjust_for_ambient_noise(source, duration=0.5)
                # Listen for a phrase
                try:
                    audio = r.listen(source, timeout=timeout, phrase_time_limit=15)
                except sr.WaitTimeoutError:
                    print("Listening timeout.")
                    return ""
            finally:
                with microphone_lock:
                    active_microphone_source = None
            
            # Feed raw audio data to Vosk
            rec = vosk.KaldiRecognizer(model, 16000)
            rec.AcceptWaveform(audio.get_raw_data())
            res = json.loads(rec.FinalResult())
            text = res.get('text', '')
            print(f"Recognized: {text}")
            return text
            
    except Exception as e:
        print(f"Microphone error: {e}")
        return ""

def get_user_name():
    try:
        return pwd.getpwuid(os.getuid())[4].split(',')[0] or os.getlogin()
    except Exception:
        return "User"

def read_tasks():
    if not os.path.exists(TODO_FILE):
        speak("You have no saved tasks.")
        return
    
    with open(TODO_FILE, "r") as f:
        tasks = [line.strip() for line in f.readlines() if line.strip()]
    
    if not tasks:
        speak("You have no saved tasks.")
        return
        
    speak(f"You have {len(tasks)} tasks.")
    for i, task in enumerate(tasks):
        if is_system_locked:
            return
        speak(f"Task {i+1}: {task}")
    if is_system_locked:
        return
    speak("Finished reading tasks.")

is_running = False
assistant_lock = threading.Lock()

def handle_unlock():
    """Interaction flow triggered on unlock."""
    global is_running
    
    with assistant_lock:
        if is_running:
            return
        is_running = True
        
    try:
        # Add a small delay to ensure audio system is ready after unlock
        time.sleep(2)
        if is_system_locked:
            return
        name = get_user_name()
        speak(f"Welcome {name}. Do you want to create a task, or listen to your saved tasks?")
        if is_system_locked:
            return
        
        response = listen(timeout=7).lower()
        print(f"User replied: {response}")
        if is_system_locked:
            return
        
        if not response:
            speak("I didn't hear anything. Goodbye.")
            return
            
        create_keywords = ["create", "add", "new", "task", "yes", "yeah", "yep", "sure", "ok"]
        read_keywords = ["listen", "read", "saved", "hear"]
        
        if any(w in response for w in create_keywords) and not any(w in response for w in read_keywords):
            speak("What is the task?")
            if is_system_locked:
                return
            task = listen(timeout=10)
            if is_system_locked:
                return
            
            if not task:
                speak("No task heard. Cancelling.")
                return
                
            speak("Do you want to elaborate on this task?")
            if is_system_locked:
                return
            elaborate_resp = listen(timeout=5).lower()
            if is_system_locked:
                return
            
            if "yes" in elaborate_resp or "yeah" in elaborate_resp or "sure" in elaborate_resp or "ok" in elaborate_resp:
                speak("Please elaborate.")
                if is_system_locked:
                    return
                elaboration = listen(timeout=15)
                if is_system_locked:
                    return
                if elaboration:
                    task += f" - {elaboration}"
                    
            with open(TODO_FILE, "a") as f:
                f.write(task + "\n")
                
            speak("Task saved.")
            
        elif "listen" in response or "read" in response or "saved" in response:
            read_tasks()
        else:
            speak("I didn't understand. Goodbye.")
    finally:
        with assistant_lock:
            is_running = False

def screen_locked(locked):
    global is_system_locked, active_microphone_source
    is_system_locked = locked
    if locked:
        print("Screen locked. Cancelling active operations.", flush=True)
        # Cancel active speech
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
        print("Screen unlocked. Triggering assistant.", flush=True)
        # Run interaction in a separate thread to not block D-Bus loop
        threading.Thread(target=handle_unlock, daemon=True).start()

def main():
    print("Starting Ubuntu Unlock Assistant daemon...")
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    
    try:
        # Listen for GNOME ScreenSaver (used by Ubuntu)
        bus.add_signal_receiver(
            screen_locked,
            dbus_interface='org.gnome.ScreenSaver',
            signal_name='ActiveChanged'
        )
        print("Successfully attached to org.gnome.ScreenSaver D-Bus signals.")
    except Exception as e:
        print(f"Could not attach to ScreenSaver signal: {e}")
        sys.exit(1)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == '__main__':
    main()
