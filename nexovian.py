#!/usr/bin/env python3
import os
import sys
import pwd
import time
import threading

import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

import ui_overlay
import audio_engine
import llm_brain
import task_manager
import config_manager

is_running = False
assistant_lock = threading.Lock()

def get_user_name():
    configured_name = config_manager.get_user_name()
    if configured_name:
        return configured_name
    try:
        return pwd.getpwuid(os.getuid())[4].split(',')[0] or os.getlogin()
    except Exception:
        return "User"

def greet_and_read_tasks():
    name = get_user_name()
    
    current_hour = time.localtime().tm_hour
    if current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
        
    audio_engine.speak(f"{greeting} {name}. Your system is ready.")
    
    tasks = task_manager.get_pending_tasks()
    if tasks:
        audio_engine.speak(f"You currently have {len(tasks)} pending tasks.")
    else:
        audio_engine.speak("You have no pending tasks.")
        
    audio_engine.speak("Would you like me to create a new task, review your schedule, or perform any action?")

def process_interaction(initial_prompt=None):
    global is_running
    
    with assistant_lock:
        if is_running:
            return
        is_running = True
        audio_engine.active_conversation = True
        
    try:
        if initial_prompt:
            audio_engine.speak(initial_prompt)
            
        context = None
        while True:
            # Active command mode
            command_text = audio_engine.listen_for_command(timeout=10)
            if not command_text:
                audio_engine.speak("I didn't hear anything. Returning to standby.")
                break
                
            clean_cmd = command_text.lower().strip()
            if any(word in clean_cmd for word in ["goodbye", "bye", "exit", "stop", "thank you", "thanks"]):
                audio_engine.speak(f"You're welcome, {config_manager.get_user_name()}. Returning to standby.")
                break
                
            audio_engine.speak("Processing...")
            response_text, action_result, context = llm_brain.process_intent(command_text, context)
            
            if response_text:
                audio_engine.speak(response_text)
            if action_result:
                audio_engine.speak(action_result)
                
            audio_engine.speak("Anything else you would like me to do?")
            
    finally:
        ui_overlay.hide()
        with assistant_lock:
            is_running = False
            audio_engine.active_conversation = False

def handle_unlock():
    """Interaction flow triggered on unlock."""
    time.sleep(2)
    greet_and_read_tasks()
    process_interaction()

def wake_word_detected():
    print("Wake word callback triggered.", flush=True)
    if not is_running:
        process_interaction(initial_prompt=f"Yes {get_user_name()}, how can I help you?")

def screen_locked(locked):
    if not locked:
        print("Screen unlocked. Triggering assistant.", flush=True)
        threading.Thread(target=handle_unlock, daemon=True).start()
    else:
        print("Screen locked.", flush=True)

def onboarding_flow():
    if not config_manager.get_user_name():
        time.sleep(2) # Wait for UI to initialize
        audio_engine.speak("Hello! I am Nexovian. It looks like this is my first time running. What would you like me to call you?")
        while True:
            name = audio_engine.listen_for_command(timeout=2)
            if name and len(name.strip()) > 1:
                extracted_name = llm_brain.extract_name(name)
                audio_engine.speak(f"Nice to meet you, {extracted_name}. I have saved your profile. I will now run in the background. Just say 'Nexovian' to wake me up.")
                config_manager.set_user_name(extracted_name)
                break
            elif name == "":
                # Heard something unintelligible
                audio_engine.speak("I didn't quite catch that. What is your name?")
            elif name is None:
                # Silence / timeout
                audio_engine.speak("Are you there? What is your name?")

    ui_overlay.hide() # Hide UI when onboarding finishes and enters standby

    # Start wake word listener in background AFTER onboarding
    wake_words = config_manager.get_wake_words()
    wakeword_thread = threading.Thread(target=audio_engine.listen_for_wakeword, args=(wake_word_detected, wake_words), daemon=True)
    wakeword_thread.start()

def main():
    print("Starting Nexovian AI Agent daemon...")
    
    # Start onboarding thread (which then starts the wake word listener)
    threading.Thread(target=onboarding_flow, daemon=True).start()
    
    # Start reminder background checker
    import reminder_manager
    reminder_manager.start_background_checker()
    
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    
    try:
        bus.add_signal_receiver(
            screen_locked,
            dbus_interface='org.gnome.ScreenSaver',
            signal_name='ActiveChanged'
        )
        print("Successfully attached to org.gnome.ScreenSaver D-Bus signals.")
    except Exception as e:
        print(f"Could not attach to ScreenSaver signal: {e}")

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == '__main__':
    main()
