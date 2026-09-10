#!/usr/bin/env python3
import os
import sys

# On Wayland (Ubuntu 24.04 / 26.04 default), GTK windows cannot be positioned or kept above
# without XWayland. Enforce X11 backend if DISPLAY is available.
if os.environ.get("DISPLAY") and "GDK_BACKEND" not in os.environ:
    os.environ["GDK_BACKEND"] = "x11"

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

    @dbus.service.method('org.nexovian.Agent', in_signature='', out_signature='')
    def ToggleBar(self):
        log_message("D-Bus ToggleBar method called.")
        text_input_ui.toggle_bar()

    @dbus.service.method('org.nexovian.Agent', in_signature='', out_signature='')
    def ShowBar(self):
        log_message("D-Bus ShowBar method called.")
        text_input_ui.show_bar()

    @dbus.service.method('org.nexovian.Agent', in_signature='', out_signature='')
    def HideBar(self):
        log_message("D-Bus HideBar method called.")
        text_input_ui.hide_bar()

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
    if audio_engine.is_system_locked:
        return
    
    tasks = task_manager.get_pending_tasks()
    if tasks:
        audio_engine.speak(f"You currently have {len(tasks)} pending tasks.")
    else:
        audio_engine.speak("You have no pending tasks.")
    if audio_engine.is_system_locked:
        return
        
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
            if audio_engine.is_system_locked:
                break
            response_text, action_result, context = llm_brain.process_intent(command_text, context)
            if audio_engine.is_system_locked:
                break

            display_action, spoken_action = llm_brain.parse_action_result(action_result)

            if response_text:
                audio_engine.speak(response_text)
            if audio_engine.is_system_locked:
                break
            if spoken_action:
                audio_engine.speak(spoken_action)
            if audio_engine.is_system_locked:
                break

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
    global last_unlock_time
    audio_engine.set_system_locked(locked)
    if not locked:
        log_message("Screen unlocked. Triggering assistant.")
        threading.Thread(target=handle_unlock, daemon=True).start()
    else:
        log_message("Screen locked.")
        last_unlock_time = 0
        try:
            ui_overlay.hide()
        except Exception:
            pass
        try:
            text_input_ui.hide_bar()
        except Exception:
            pass

def onboarding_flow():
    if not config_manager.get_user_name():
        time.sleep(2) # Wait for UI to initialize
        audio_engine.speak("Hello! I am Nexovian. It looks like this is my first time running. What would you like me to call you?")
        while True:
            name = audio_engine.listen_for_command(timeout=10)
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

def ensure_system_integration():
    """Ensure D-Bus auto-activation, GNOME shortcuts, IBus unbinding, and desktop entries are configured."""
    import shutil
    import subprocess
    import ast

    script_path = os.path.abspath(__file__)
    py_exec = sys.executable or "/usr/bin/python3"

    # 1. Install D-Bus session service for on-demand auto-activation
    try:
        dbus_services_dir = os.path.expanduser("~/.local/share/dbus-1/services")
        os.makedirs(dbus_services_dir, exist_ok=True)
        service_path = os.path.join(dbus_services_dir, "org.nexovian.Agent.service")
        service_content = f"[D-BUS Service]\nName=org.nexovian.Agent\nExec={py_exec} {script_path}\n"
        with open(service_path, "w") as f:
            f.write(service_content)
        log_message(f"D-Bus auto-activation service verified at {service_path}")
    except Exception as e:
        log_message(f"Note on D-Bus service setup: {e}")

    # 2. Setup GNOME global shortcut and resolve IBus conflict
    if shutil.which("gsettings"):
        try:
            # Remove Control+space from IBus trigger hotkey if present to prevent shortcut hijacking
            res = subprocess.run(
                ["gsettings", "get", "org.freedesktop.ibus.general.hotkey", "trigger"],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0 and "Control+space" in res.stdout:
                try:
                    triggers = ast.literal_eval(res.stdout.strip())
                    new_triggers = [t for t in triggers if t != "Control+space"]
                    subprocess.run(
                        ["gsettings", "set", "org.freedesktop.ibus.general.hotkey", "trigger", str(new_triggers)],
                        capture_output=True, check=False
                    )
                    log_message("Removed Control+space from IBus triggers to prevent hotkey conflicts.")
                except Exception as ex:
                    log_message(f"Could not update IBus triggers: {ex}")

            # Register native GNOME media-keys custom keybinding (crucial for Wayland)
            key_path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/"
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                existing = []
                if not val.startswith("@as"):
                    try:
                        existing = ast.literal_eval(val)
                    except Exception:
                        existing = []

                if key_path not in existing:
                    existing.append(key_path)
                    subprocess.run(
                        ["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", str(existing)],
                        capture_output=True, check=False
                    )

                schema_path = f"org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:{key_path}"
                subprocess.run(["gsettings", "set", schema_path, "name", "Nexovian Toggle"], capture_output=True, check=False)
                subprocess.run(
                    ["gsettings", "set", schema_path, "command", "gdbus call --session --dest org.nexovian.Agent --object-path /org/nexovian/Agent --method org.nexovian.Agent.ToggleBar"],
                    capture_output=True, check=False
                )
                subprocess.run(["gsettings", "set", schema_path, "binding", "<Control>space"], capture_output=True, check=False)
                log_message("Verified GNOME global shortcut <Control>space for Nexovian.")
        except Exception as e:
            log_message(f"Note on GNOME keybinding setup: {e}")

    # 3. Ensure desktop autostart entry and applications launcher entry exist
    try:
        repo_desktop = os.path.join(os.path.dirname(script_path), "nexovian.desktop")
        if os.path.exists(repo_desktop):
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_file = os.path.join(autostart_dir, "nexovian.desktop")
            if not os.path.exists(desktop_file):
                shutil.copyfile(repo_desktop, desktop_file)
                log_message(f"Installed autostart entry to {desktop_file}")

            apps_dir = os.path.expanduser("~/.local/share/applications")
            os.makedirs(apps_dir, exist_ok=True)
            app_file = os.path.join(apps_dir, "nexovian.desktop")
            if not os.path.exists(app_file):
                shutil.copyfile(repo_desktop, app_file)
    except Exception as e:
        log_message(f"Note on desktop entry setup: {e}")


def _start_hotkey_listener():
    """Listen for Ctrl+Space globally via pynput (fallback for X11 environments)."""
    try:
        # Authorize Xwayland access for local user if on Wayland
        if os.environ.get("WAYLAND_DISPLAY") and os.environ.get("DISPLAY"):
            try:
                import subprocess
                subprocess.run(["xhost", "+si:localuser:" + (os.environ.get("USER") or "karan-kumar")],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass

        from pynput import keyboard

        def on_activate():
            text_input_ui.toggle_bar()

        with keyboard.GlobalHotKeys({'<ctrl>+<space>': on_activate}) as h:
            print("[nexovian] Global hotkey Ctrl+Space registered via pynput.", flush=True)
            h.join()
    except Exception as e:
        print(f"[nexovian] Note on global hotkey (pynput): {e}", flush=True)



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
            if "--wake" in sys.argv:
                interface.WakeUp()
                print("Nexovian daemon is running. Sent WakeUp signal.")
            elif "--show" in sys.argv:
                interface.ShowBar()
                print("Nexovian daemon is running. Sent ShowBar signal.")
            elif "--hide" in sys.argv:
                interface.HideBar()
                print("Nexovian daemon is running. Sent HideBar signal.")
            else:
                interface.ToggleBar()
                print("Nexovian daemon is running. Sent ToggleBar signal.")
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
    
    # Ensure GNOME shortcuts, IBus trigger fix, and auto-activation are installed
    ensure_system_integration()

    def init_bar():
        text_input_ui.get_bar()
        return False
    GLib.idle_add(init_bar)

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
