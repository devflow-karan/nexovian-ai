import subprocess
import pyautogui
import os
import time

def is_safe_command(cmd_str):
    """Check if the command is safe to run. Prevent sudo/root operations."""
    dangerous_keywords = ["sudo", "su", "rm -rf /", "chown", "chmod 777", "passwd"]
    for keyword in dangerous_keywords:
        if keyword in cmd_str:
            return False
    return True

def execute_command(cmd_str):
    if not is_safe_command(cmd_str):
        return "That action is above my permissions. Administrator privileges are required."
    
    try:
        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"Command executed successfully. Output: {result.stdout.strip()}"
        else:
            return f"Command failed with error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def open_application(app_name):
    # Try to use xdg-open or gtk-launch
    # Simplest approach for ubuntu is to run the app name if it's in path, or gtk-launch
    app_name_lower = app_name.lower().replace(" ", "")
    
    # Common mappings
    mappings = {
        "vscode": "code",
        "browser": "xdg-open http://google.com",
        "terminal": "gnome-terminal",
        "files": "nautilus"
    }
    
    cmd = mappings.get(app_name_lower, app_name_lower)
    
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opening {app_name}."
    except Exception as e:
        return f"Failed to open {app_name}: {str(e)}"

def type_text(text):
    pyautogui.write(text, interval=0.05)
    return f"Typed: {text}"

def press_key(key):
    pyautogui.press(key)
    return f"Pressed key: {key}"

def write_file(filename, content):
    """Write text or code to a file in the Documents folder."""
    try:
        documents_path = os.path.expanduser("~/Documents")
        os.makedirs(documents_path, exist_ok=True)
        # Prevent path traversal
        clean_filename = os.path.basename(filename)
        file_path = os.path.join(documents_path, clean_filename)
        
        with open(file_path, "w") as f:
            f.write(content)
        return f"Successfully created and wrote to {clean_filename} in your Documents folder."
    except Exception as e:
        return f"Failed to write file: {str(e)}"
