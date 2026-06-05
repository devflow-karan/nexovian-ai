import requests
import json
from datetime import datetime
import time
import re

import task_manager
import automation_executor
import reminder_manager

OLLAMA_URL  = "http://localhost:11434/api/generate"
OLLAMA_TAGS = "http://localhost:11434/api/tags"
PREFERRED_MODEL = "qwen3:8b"

# Fallback preference order — first match that is installed wins
_MODEL_FALLBACK_CHAIN = [
    "qwen3:8b",
    "qwen2.5:8b",
    "llama3.2:latest",
    "llama3.2",
    "llama3:latest",
    "llama3",
    "mistral:latest",
    "mistral",
    "gemma:latest",
    "gemma",
]

def _resolve_model() -> str:
    """Return the best available Ollama model, falling back gracefully."""
    try:
        resp = requests.get(OLLAMA_TAGS, timeout=5)
        if resp.status_code == 200:
            installed = [m["name"] for m in resp.json().get("models", [])]
            if not installed:
                print("[llm_brain] WARNING: No models found in Ollama. Run: ollama pull llama3.2", flush=True)
                return PREFERRED_MODEL  # will 404 but gives clear error

            # Try preferred chain first
            for candidate in _MODEL_FALLBACK_CHAIN:
                if candidate in installed:
                    if candidate != PREFERRED_MODEL:
                        print(f"[llm_brain] '{PREFERRED_MODEL}' not found. Using '{candidate}' instead.", flush=True)
                        print(f"[llm_brain] To use the preferred model: ollama pull {PREFERRED_MODEL}", flush=True)
                    else:
                        print(f"[llm_brain] Model resolved: {candidate}", flush=True)
                    return candidate

            # Nothing in chain found — just use whatever is first
            first = installed[0]
            print(f"[llm_brain] No preferred model found. Falling back to first available: '{first}'", flush=True)
            return first
    except Exception as e:
        print(f"[llm_brain] Could not query Ollama for models: {e}", flush=True)

    return PREFERRED_MODEL

MODEL_NAME = _resolve_model()

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
You may output multiple commands in sequence using separate <COMMAND>...</COMMAND> blocks.
Format:
TEXT RESPONSE
<COMMAND>{"action": "open_app", "app": "vscode", "path": "optional_folder_name"}</COMMAND>

Supported actions:
- {"action": "open_app", "app": "name", "path": "optional_folder_or_file_path"} (Open applications like vscode, terminal, files (file manager), or browser. An optional relative path/folder name opens the application within that folder under /data/projects/<current_year>/)
- {"action": "add_task", "title": "task description"}
- {"action": "list_tasks"}
- {"action": "execute_cmd", "cmd": "bash command"}
- {"action": "get_weather", "location": "city name or empty for current location"}
- {"action": "set_reminder", "time": "YYYY-MM-DD HH:MM:SS", "message": "reminder description"}
- {"action": "write_file", "filename": "relative_path/name.py", "content": "text or code to write"} (Writes content to a file inside /data/projects/<current_year>/. Automatically creates parent directories if needed.)
- {"action": "scroll", "direction": "up" | "down", "amount": 300} (Scrolls the screen by the specified clicks/units)
- {"action": "read_screen", "instruction": "instructions"} (Captures a screenshot of the user's screen and explains it or answers questions based on it)

Only output commands if an action is requested. Otherwise just output text answering the user's questions naturally.

Example Interaction 1:
User: Open VS Code and write python code to fetch the weather for Tokyo in a folder called weather_app.
Nexovian: I will create the python script in the weather_app folder under the current year's projects directory and open it in VS Code.
<COMMAND>{"action": "write_file", "filename": "weather_app/weather.py", "content": "import requests\nresp = requests.get('https://wttr.in/Tokyo')\nprint(resp.text)"}</COMMAND>
<COMMAND>{"action": "open_app", "app": "vscode", "path": "weather_app"}</COMMAND>

Example Interaction 2:
User: Go to the project_alpha folder and open it in VS Code.
Nexovian: Opening the project_alpha folder in VS Code now.
<COMMAND>{"action": "open_app", "app": "vscode", "path": "project_alpha"}</COMMAND>

Example Interaction 3:
User: What's on my screen?
Nexovian: I will take a screenshot and explain it for you.
<COMMAND>{"action": "read_screen", "instruction": "Explain what is on the screen"}</COMMAND>

Example Interaction 4:
User: Scroll down and explain my screen.
Nexovian: Scrolling down and analyzing the screen content.
<COMMAND>{"action": "scroll", "direction": "down", "amount": 500}</COMMAND>
<COMMAND>{"action": "read_screen", "instruction": "Explain what is on the screen"}</COMMAND>
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
        elif response.status_code == 404:
            return (
                f"Model '{MODEL_NAME}' is not available in Ollama. "
                f"Run: ollama pull {MODEL_NAME}",
                context
            )
        else:
            return f"Error: Ollama returned status {response.status_code}", context
    except requests.exceptions.ConnectionError:
        return "Cannot reach Ollama. Make sure it is running: ollama serve", context
    except Exception as e:
        return f"Error communicating with AI: {str(e)}", context

def process_intent(prompt, context=None):
    text_response, new_context = generate_response(prompt, context)
    
    # Parse for all commands
    action_results = []
    matches = list(re.finditer(r"<COMMAND>(.*?)</\s*COMMAND>", text_response, re.DOTALL | re.IGNORECASE))
    
    for match in matches:
        cmd_str = match.group(1).strip()
        
        try:
            cmd = json.loads(cmd_str)
            action = cmd.get("action")
            res = ""
            
            if action == "open_app":
                res = automation_executor.open_application(cmd.get("app"), cmd.get("path"))
            elif action == "add_task":
                task_manager.add_task(cmd.get("title"))
                res = f"Task added: {cmd.get('title')}"
            elif action == "list_tasks":
                tasks = task_manager.get_pending_tasks()
                if tasks:
                    res = "Pending tasks: " + ", ".join([t['title'] for t in tasks])
                else:
                    res = "You have no pending tasks."
            elif action == "execute_cmd":
                res = automation_executor.execute_command(cmd.get("cmd"))
            elif action == "get_weather":
                loc = cmd.get("location", "")
                url = f"https://wttr.in/{loc}?format=3" if loc else "https://wttr.in/?format=3"
                try:
                    w_res = requests.get(url, timeout=5)
                    if w_res.status_code == 200:
                        weather_txt = w_res.text.strip()
                        condition = weather_txt.split(':')[-1].strip() if ':' in weather_txt else weather_txt
                        if loc:
                            res = f"The weather in {loc} is currently {condition}."
                        else:
                            res = f"The current weather is {condition}."
                    else:
                        res = "Currently I am not getting any information regarding the weather."
                except Exception:
                    res = "Currently I am not getting any information regarding the weather."
            elif action == "set_reminder":
                time_str = cmd.get("time")
                msg = cmd.get("message")
                try:
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    ts = dt.timestamp()
                    now_ts = time.time()
                    if ts <= now_ts:
                        now_formatted = datetime.now().strftime("%I:%M %p")
                        res = f"I cannot set a reminder in the past. It is currently {now_formatted}."
                    else:
                        reminder_manager.add_reminder(ts, msg)
                        res = f"I have successfully scheduled your reminder for {time_str}."
                except Exception as e:
                    res = f"Failed to set reminder. Ensure the time format is correct. Error: {e}"
            elif action == "write_file":
                filename = cmd.get("filename")
                content = cmd.get("content")
                if filename and content is not None:
                    res = automation_executor.write_file(filename, content)
                else:
                    res = "Failed to write file. Filename or content missing."
            elif action == "scroll":
                res = automation_executor.scroll(cmd.get("direction", "down"), cmd.get("amount", 300))
            elif action == "read_screen":
                res = automation_executor.read_screen(cmd.get("instruction", "Explain what is on the screen"))
                
            if res:
                action_results.append(res)
            
        except json.JSONDecodeError:
            action_results.append("Failed to parse command from AI.")
            
    # Clean up the text response to remove all command blocks for speech
    for match in matches:
        text_response = text_response.replace(match.group(0), "")
    text_response = text_response.strip()
            
    action_result = " ".join(action_results)
    return text_response, action_result, new_context

def parse_action_result(action_result):
    """Parse action result into (display_text, spoken_text)."""
    if not action_result:
        return "", ""
    if "[SPOKEN]:" in action_result and "[DISPLAY]:" in action_result:
        try:
            spoken_part = action_result.split("[SPOKEN]:")[1].split("[DISPLAY]:")[0].strip()
            display_part = action_result.split("[DISPLAY]:")[1].strip()
            return display_part, spoken_part
        except Exception:
            pass
    return action_result, action_result

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
