#!/usr/bin/env python3
import os
import sys
import pwd
import time
import threading

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

import ui_overlay
import audio_engine
import llm_brain
import task_manager
import config_manager
import text_input_ui

is_running = False
assistant_lock = threading.Lock()

class NexovianDBusService(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName('org.nexovian.Agent', bus=dbus.SessionBus())
        super().__init__(bus_name, '/org/nexovian/Agent')

    @dbus.service.method('org.nexovian.Agent', in_signature='', out_signature='')
    def WakeUp(self):
        log_message("D-Bus WakeUp method called. Triggering voice interaction.")
        threading.Thread(target=wake_word_detected, daemon=True).start()

def log_message(msg):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_dir = os.path.expanduser("~/.config/nexovian")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg, flush=True)
    try:
        with open(log_path, "a") as f:
            f.write(formatted_msg + "\n")
    except Exception:
        pass

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
        
    log_message(f"Speaking unlock greeting to {name}")
    audio_engine.speak(f"{greeting} {name}. Your system is ready.")
    
    tasks = task_manager.get_pending_tasks()
    if tasks:
        audio_engine.speak(f"You currently have {len(tasks)} pending tasks.")
    else:
        audio_engine.speak("You have no pending tasks.")
        
    audio_engine.speak("Have a great day!")

def process_interaction(initial_prompt=None):
    global is_running
    
    with assistant_lock:
        if is_running:
            log_message("process_interaction requested, but already running.")
            return
        is_running = True
        audio_engine.active_conversation = True
        
    try:
        if initial_prompt:
            audio_engine.speak(initial_prompt)
            
        context = None
        while True:
            # If the screen was locked during active interaction, exit immediately
            if audio_engine.is_system_locked:
                log_message("System locked. Aborting interaction loop.")
                break
                
            # Active command mode
            command_text = audio_engine.listen_for_command(timeout=10)
            
            # Recheck lock state after listening block
            if audio_engine.is_system_locked:
                log_message("System locked. Aborting interaction loop post-listen.")
                break
                
            if not command_text:
                audio_engine.speak("I didn't hear anything. Returning to standby.")
                break

            clean_cmd = command_text.lower().strip()
            if any(word in clean_cmd for word in ["goodbye", "bye", "exit", "stop", "thank you", "thanks"]):
                audio_engine.speak(f"You're welcome, {config_manager.get_user_name()}. Returning to standby.")
                break

            # Mirror spoken command in the text bar (if visible)
            text_input_ui.append_spoken("You (voice)", command_text)

            audio_engine.speak("Processing...")
            response_text, action_result, context = llm_brain.process_intent(command_text, context)

            display_action, spoken_action = llm_brain.parse_action_result(action_result)

            if response_text:
                audio_engine.speak(response_text)
            if spoken_action:
                audio_engine.speak(spoken_action)

            # Mirror response + display part of action in the text bar (if visible)
            full_reply_display = ""
            if response_text:
                full_reply_display += response_text
            if display_action:
                full_reply_display += (" " if full_reply_display else "") + display_action

            if full_reply_display:
                text_input_ui.append_spoken("Nexovian", full_reply_display)

            audio_engine.speak("Anything else you would like me to do?")
            
    finally:
        ui_overlay.hide()
        with assistant_lock:
            is_running = False
            audio_engine.active_conversation = False
            log_message("Returned to standby state.")

last_unlock_time = 0

def handle_unlock():
    """Interaction flow triggered on unlock."""
    global last_unlock_time, is_running
    current_time = time.time()
    
    with assistant_lock:
        if is_running or current_time - last_unlock_time < 5:
            log_message(f"handle_unlock skipped. is_running: {is_running}, dt: {current_time - last_unlock_time:.1f}s")
            return
        last_unlock_time = current_time
        is_running = True
        
    try:
        log_message("Triggering unlock flow: waiting 2s...")
        time.sleep(2)
        # Double check that we didn't lock the system again in these 2 seconds
        if audio_engine.is_system_locked:
            log_message("System locked during time.sleep. Aborting unlock greeting.")
            return
            
        greet_and_read_tasks()
    finally:
        ui_overlay.hide()
        with assistant_lock:
            is_running = False
            log_message("Returned to standby state after unlock greeting.")

def wake_word_detected():
    log_message("Wake word callback triggered.")
    if not is_running:
        process_interaction(initial_prompt=f"Yes {get_user_name()}, how can I help you?")

def screen_locked(locked):
    audio_engine.set_system_locked(locked)
    if not locked:
        log_message("Screen unlocked. Triggering assistant.")
        threading.Thread(target=handle_unlock, daemon=True).start()
    else:
        log_message("Screen locked.")

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
    else:
        log_message("Profile exists. Triggering initial startup greeting.")
        time.sleep(2)
        threading.Thread(target=handle_unlock, daemon=True).start()

    ui_overlay.hide() # Hide UI when onboarding finishes and enters standby

    # Start wake word listener in background AFTER onboarding
    wake_words = config_manager.get_wake_words()
    wakeword_thread = threading.Thread(target=audio_engine.listen_for_wakeword, args=(wake_word_detected, wake_words), daemon=True)
    wakeword_thread.start()

def _start_hotkey_listener():
    """Listen for Ctrl+Space globally and toggle the text input bar."""
    try:
        from pynput import keyboard

        def on_activate():
            text_input_ui.toggle_bar()

        with keyboard.GlobalHotKeys({'<ctrl>+<space>': on_activate}) as h:
            print("[nexovian] Global hotkey Ctrl+Space registered.", flush=True)
            h.join()
    except Exception as e:
        print(f"[nexovian] Could not register global hotkey (pynput): {e}", flush=True)
        print("[nexovian] Install pynput: pip3 install pynput", flush=True)


def login1_session_locked():
    screen_locked(True)

def login1_session_unlocked():
    screen_locked(False)

def main():
    # Setup D-Bus main loop and check for existing instance
    DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    
    if session_bus.name_has_owner('org.nexovian.Agent'):
        try:
            remote_object = session_bus.get_object('org.nexovian.Agent', '/org/nexovian/Agent')
            interface = dbus.Interface(remote_object, 'org.nexovian.Agent')
            interface.WakeUp()
            print("Nexovian daemon is already running. Sent WakeUp signal.")
            sys.exit(0)
        except Exception as e:
            print(f"Failed to communicate with running daemon: {e}")
            sys.exit(1)

    print("Starting Nexovian AI Agent daemon...")
    
    # Claim name and register service
    try:
        global dbus_service
        dbus_service = NexovianDBusService()
        print("Successfully registered org.nexovian.Agent D-Bus service.")
    except Exception as e:
        print(f"Could not register D-Bus service: {e}")

    import subprocess
    try:
        subprocess.run(["pkill", "-f", "unlock_assistant.py"], check=False)
    except Exception:
        pass
    
    # Initialise the text input bar widget on the GTK main thread
    GLib.idle_add(lambda: text_input_ui.get_bar() or False)

    # Start global Ctrl+Space hotkey listener
    threading.Thread(target=_start_hotkey_listener, daemon=True).start()

    # Start onboarding thread (which then starts the wake word listener)
    threading.Thread(target=onboarding_flow, daemon=True).start()
    
    # Start reminder background checker
    import reminder_manager
    reminder_manager.start_background_checker()
    
    # Session Bus ScreenSaver listener
    try:
        session_bus.add_signal_receiver(
            screen_locked,
            dbus_interface='org.gnome.ScreenSaver',
            signal_name='ActiveChanged'
        )
        print("Successfully attached to org.gnome.ScreenSaver D-Bus signals.")
    except Exception as e:
        print(f"Could not attach to ScreenSaver signal: {e}")

    # System Bus logind listener for lock/unlock redundancy
    try:
        system_bus = dbus.SystemBus()
        system_bus.add_signal_receiver(
            login1_session_locked,
            dbus_interface='org.freedesktop.login1.Session',
            signal_name='Lock'
        )
        system_bus.add_signal_receiver(
            login1_session_unlocked,
            dbus_interface='org.freedesktop.login1.Session',
            signal_name='Unlock'
        )
        print("Successfully attached to org.freedesktop.login1.Session signals.")
    except Exception as e:
        print(f"Could not attach to logind signals: {e}")

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("Exiting...")
        os._exit(0)

if __name__ == '__main__':
    main()
