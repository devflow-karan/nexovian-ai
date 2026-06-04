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

def resolve_project_path(path_str):
    if not path_str:
        return None
        
    from datetime import datetime
    current_year = str(datetime.now().year)
    base_dir = f"/data/projects/{current_year}"
    
    # If path_str is absolute, use it (ensuring it is resolved safely)
    if os.path.isabs(path_str):
        return os.path.normpath(path_str)
        
    # Check if directory exists in the current year's projects folder
    path_in_year = os.path.join(base_dir, path_str)
    if os.path.exists(path_in_year):
        return os.path.normpath(path_in_year)
        
    # Check in /data/projects generally
    path_in_projects = os.path.join("/data/projects", path_str)
    if os.path.exists(path_in_projects):
        return os.path.normpath(path_in_projects)
        
    # Check in home directory
    path_in_home = os.path.expanduser(f"~/{path_str}")
    if os.path.exists(path_in_home):
        return os.path.normpath(path_in_home)
        
    # Otherwise, default to current year's projects folder and create it
    try:
        os.makedirs(path_in_year, exist_ok=True)
        return os.path.normpath(path_in_year)
    except Exception:
        # Fallback to home documents if permission error in /data/projects
        docs_fallback = os.path.expanduser(f"~/Documents/{path_str}")
        os.makedirs(docs_fallback, exist_ok=True)
        return os.path.normpath(docs_fallback)

def open_application(app_name, path=None):
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
    
    if path:
        resolved_path = resolve_project_path(path)
        if cmd == "code":
            cmd = f"code {resolved_path}"
        elif cmd == "gnome-terminal":
            cmd = f"gnome-terminal --working-directory={resolved_path}"
        elif cmd == "nautilus":
            cmd = f"nautilus {resolved_path}"
        else:
            # For other apps, pass path as argument
            cmd = f"{cmd} {resolved_path}"
    
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if path:
            return f"Opening {app_name} at {path}."
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
    """Write text or code to a file inside the /data/projects/<current_year>/ folder."""
    try:
        from datetime import datetime
        current_year = str(datetime.now().year)
        base_dir = f"/data/projects/{current_year}"
        
        # Clean path to prevent escaping outside directories
        # Allow subdirectory files, e.g. "abc/main.py"
        safe_path = os.path.normpath(filename).lstrip("/")
        while safe_path.startswith("../") or safe_path == "..":
            safe_path = safe_path[3:]
            
        file_path = os.path.join(base_dir, safe_path)
        
        # Fallback if base_dir is not writable or doesn't exist
        try:
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return f"Successfully created and wrote to {safe_path} in {base_dir}."
        except Exception:
            # Fallback to Documents folder
            fallback_base = os.path.expanduser("~/Documents")
            file_path = os.path.join(fallback_base, safe_path)
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            return f"Successfully created and wrote to {safe_path} in your Documents folder (fallback)."
    except Exception as e:
        return f"Failed to write file: {str(e)}"
