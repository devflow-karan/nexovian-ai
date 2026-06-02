import requests
import json
from datetime import datetime
import time
import re

import task_manager
import automation_executor
import reminder_manager

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"

SYSTEM_PROMPT = """You are Nexovian (Nexovian), a personal AI desktop assistant running locally on Ubuntu 22.04 and Ubuntu 24.04.

If anyone asks about your identity or who made you, you must explicitly reply that Karan made you and you are Nexovian.

Your personality is professional, proactive, intelligent, concise, and helpful. You act as a conversational companion. Answer general knowledge questions naturally.

You must NEVER perform:
* sudo commands
* root operations
* system-wide package installations requiring sudo
* changing user passwords
* modifying security policies
* deleting critical system files

If asked to perform a restricted action, respond:
"That action is above my permissions. Administrator privileges are required."

Available Tools:
You can output specific JSON commands mixed with your text response to trigger local actions.
Format:
TEXT RESPONSE
<COMMAND>{"action": "open_app", "app": "vscode"}</COMMAND>

Supported actions:
- {"action": "open_app", "app": "name"}
- {"action": "add_task", "title": "task description"}
- {"action": "list_tasks"}
- {"action": "execute_cmd", "cmd": "bash command"}
- {"action": "get_weather", "location": "city name or empty for current location"}
- {"action": "set_reminder", "time": "YYYY-MM-DD HH:MM:SS", "message": "reminder description"}
- {"action": "write_file", "filename": "name.txt", "content": "text or code to write"}

Only output commands if an action is requested. Otherwise just output text answering the user's questions naturally.

Example Interaction 1:
User: Remind me today at 3pm to buy milk.
Nexovian: I will set that reminder for you right now.
<COMMAND>{"action": "set_reminder", "time": "2026-05-30 15:00:00", "message": "buy milk"}</COMMAND>

Example Interaction 2:
User: Open visual studio code.
Nexovian: Opening VS Code now.
<COMMAND>{"action": "open_app", "app": "vscode"}</COMMAND>
"""

def generate_response(prompt, context=None):
    now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    system_prompt_with_time = SYSTEM_PROMPT + f"\n\nCurrent System Time: {now_str}\nUse this exact current time to interpret phrases like 'today', 'tomorrow', 'in 5 minutes', or 'at 11am'."
    
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{system_prompt_with_time}\n\nUser: {prompt}\nNexovian:",
        "stream": False
    }
    
    if context:
        payload["context"] = context
        
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", ""), data.get("context", [])
        else:
            return f"Error: Ollama returned status {response.status_code}", context
    except Exception as e:
        return f"Error communicating with AI: {str(e)}", context

def process_intent(prompt, context=None):
    text_response, new_context = generate_response(prompt, context)
    
    # Parse for commands
    action_result = ""
    match = re.search(r"<COMMAND>(.*?)</\s*COMMAND>", text_response, re.DOTALL | re.IGNORECASE)
    if match:
        cmd_str = match.group(1).strip()
        
        try:
            cmd = json.loads(cmd_str)
            action = cmd.get("action")
            
            if action == "open_app":
                action_result = automation_executor.open_application(cmd.get("app"))
            elif action == "add_task":
                task_manager.add_task(cmd.get("title"))
                action_result = f"Task added: {cmd.get('title')}"
            elif action == "list_tasks":
                tasks = task_manager.get_pending_tasks()
                if tasks:
                    action_result = "Pending tasks: " + ", ".join([t['title'] for t in tasks])
                else:
                    action_result = "You have no pending tasks."
            elif action == "execute_cmd":
                action_result = automation_executor.execute_command(cmd.get("cmd"))
            elif action == "get_weather":
                loc = cmd.get("location", "")
                url = f"https://wttr.in/{loc}?format=3" if loc else "https://wttr.in/?format=3"
                try:
                    w_res = requests.get(url, timeout=5)
                    if w_res.status_code == 200:
                        weather_txt = w_res.text.strip()
                        # Format 3 output looks like "London: ⛅️ +11°C". We parse out the weather part.
                        condition = weather_txt.split(':')[-1].strip() if ':' in weather_txt else weather_txt
                        if loc:
                            action_result = f"The weather in {loc} is currently {condition}."
                        else:
                            action_result = f"The current weather is {condition}."
                    else:
                        action_result = "Currently I am not getting any information regarding the weather."
                except Exception:
                    action_result = "Currently I am not getting any information regarding the weather."
            elif action == "set_reminder":
                time_str = cmd.get("time")
                msg = cmd.get("message")
                try:
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    ts = dt.timestamp()
                    now_ts = time.time()
                    if ts <= now_ts:
                        now_formatted = datetime.now().strftime("%I:%M %p")
                        action_result = f"I cannot set a reminder in the past. It is currently {now_formatted}."
                    else:
                        reminder_manager.add_reminder(ts, msg)
                        action_result = f"I have successfully scheduled your reminder for {time_str}."
                except Exception as e:
                    action_result = f"Failed to set reminder. Ensure the time format is correct. Error: {e}"
            elif action == "write_file":
                filename = cmd.get("filename")
                content = cmd.get("content")
                if filename and content is not None:
                    action_result = automation_executor.write_file(filename, content)
                else:
                    action_result = "Failed to write file. Filename or content missing."
                
            # Clean up the text response to remove the command block for speech
            # We remove the entire matched `<COMMAND>...</COMMAND>` string
            text_response = text_response.replace(match.group(0), "").strip()
            
        except json.JSONDecodeError:
            action_result = "Failed to parse command from AI."
            
    return text_response, action_result, new_context

def extract_name(spoken_text):
    """Uses the LLM to extract just the user's name from a conversational sentence."""
    prompt = f"Extract ONLY the person's first name from this text, nothing else. If there is no name, output 'User'. Text: '{spoken_text}'"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            name = response.json().get("response", "User").strip()
            # Clean up potential LLM conversational garbage
            name = name.split()[0].replace(".", "").replace(",", "")
            if len(name) < 2:
                return "User"
            return name
    except Exception:
        pass
    
    # Fallback to last word if LLM fails
    words = spoken_text.strip().split()
    return words[-1] if words else "User"
