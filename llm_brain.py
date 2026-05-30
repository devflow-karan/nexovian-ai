import requests
import json
import task_manager
import automation_executor

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b" # User requested

SYSTEM_PROMPT = """You are Nexovian (Nexo), a personal AI desktop assistant running locally on Ubuntu 22.04 and Ubuntu 24.04.

Your personality is professional, proactive, intelligent, concise, and helpful.

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

Only output commands if an action is requested. Otherwise just output text.
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
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
                
            # Clean up the text response to remove the command block for speech
            text_response = text_response[:text_response.find("<COMMAND>")].strip()
            
        except json.JSONDecodeError:
            action_result = "Failed to parse command from AI."
            
    return text_response, action_result, new_context
