import requests
import json
import task_manager
import automation_executor

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b" # User requested

SYSTEM_PROMPT = """You are Nexovian (Nexovian), a personal AI desktop assistant running locally on Ubuntu 22.04 and Ubuntu 24.04.

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

Only output commands if an action is requested. Otherwise just output text answering the user's questions naturally.
"""

def generate_response(prompt, context=None):
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}\nNexovian:",
        "stream": False
    }
    
    if context:
        payload["context"] = context
        
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
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
    if "<COMMAND>" in text_response and "</COMMAND>" in text_response:
        start_idx = text_response.find("<COMMAND>") + len("<COMMAND>")
        end_idx = text_response.find("</COMMAND>")
        cmd_str = text_response[start_idx:end_idx].strip()
        
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
                
            # Clean up the text response to remove the command block for speech
            text_response = text_response[:text_response.find("<COMMAND>")].strip()
            
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
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
