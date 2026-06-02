import os
import json
import time
import threading
from datetime import datetime

import audio_engine
import ui_overlay

REMINDERS_FILE = os.path.expanduser("~/.config/nexovian/reminders.json")

def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_reminders(reminders):
    os.makedirs(os.path.dirname(REMINDERS_FILE), exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=4)

def add_reminder(timestamp, message):
    reminders = load_reminders()
    reminders.append({
        "timestamp": timestamp,
        "message": message,
        "state": "pending" # pending -> notified_5m -> completed
    })
    save_reminders(reminders)

def check_reminders_loop():
    while True:
        try:
            reminders = load_reminders()
            now = time.time()
            changed = False
            
            for r in reminders:
                if r["state"] == "completed":
                    continue
                    
                time_diff = r["timestamp"] - now
                
                # Check 5 minute warning
                if r["state"] == "pending" and time_diff <= 300 and time_diff > 0:
                    while audio_engine.active_conversation or getattr(audio_engine, 'is_system_locked', False):
                        time.sleep(2)
                    audio_engine.speak(f"Reminder in 5 minutes: {r['message']}")
                    ui_overlay.hide()
                    r["state"] = "notified_5m"
                    changed = True
                    
                # Check exact time or overdue
                elif r["state"] in ["pending", "notified_5m"] and time_diff <= 0:
                    while audio_engine.active_conversation or getattr(audio_engine, 'is_system_locked', False):
                        time.sleep(2)
                    audio_engine.speak(f"Reminder: {r['message']}")
                    ui_overlay.hide()
                    r["state"] = "completed"
                    changed = True
            
            if changed:
                save_reminders(reminders)
                
        except Exception as e:
            print(f"Reminder check error: {e}")
            
        time.sleep(30) # Check every 30 seconds

def start_background_checker():
    threading.Thread(target=check_reminders_loop, daemon=True).start()
