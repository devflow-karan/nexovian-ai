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
        
    # If path starts with tilde (~), expand it directly
    if path_str.startswith("~"):
        return os.path.normpath(os.path.expanduser(path_str))
        
    from datetime import datetime
    current_year = str(datetime.now().year)
    base_dir = f"/data/projects/{current_year}"
    
    # If path_str is absolute, use it (ensuring it is resolved safely)
    if os.path.isabs(path_str):
        return os.path.normpath(path_str)
        
    # Check if directory or file exists in the current year's projects folder
    path_in_year = os.path.join(base_dir, path_str)
    if os.path.exists(path_in_year):
        return os.path.normpath(path_in_year)
        
    # Check in /data/projects generally
    path_in_projects = os.path.join("/data/projects", path_str)
    if os.path.exists(path_in_projects):
        return os.path.normpath(path_in_projects)
        
    # Check in home directory (e.g. "Downloads/KaranKumar.pdf" -> "~/Downloads/KaranKumar.pdf")
    path_in_home = os.path.expanduser(f"~/{path_str}")
    if os.path.exists(path_in_home):
        return os.path.normpath(path_in_home)
        
    # Otherwise, default to current year's projects folder and create parent directory
    try:
        dir_to_make = os.path.dirname(path_in_year)
        if dir_to_make:
            os.makedirs(dir_to_make, exist_ok=True)
        return os.path.normpath(path_in_year)
    except Exception:
        # Fallback to home documents if permission error in /data/projects
        docs_fallback = os.path.expanduser(f"~/Documents/{path_str}")
        dir_fallback = os.path.dirname(docs_fallback)
        if dir_fallback:
            os.makedirs(dir_fallback, exist_ok=True)
        return os.path.normpath(docs_fallback)

def open_application(app_name, path=None):
    import shlex
    import urllib.parse
    
    app_name_lower = app_name.lower().replace(" ", "")
    
    # Common mappings
    mappings = {
        "vscode": "code",
        "browser": "xdg-open",
        "terminal": "gnome-terminal",
        "files": "nautilus"
    }
    
    cmd = mappings.get(app_name_lower, app_name_lower)
    
    if app_name_lower == "browser":
        # Handle browser URL/search routing
        if path:
            # Check if it starts like a URL
            if path.startswith("http://") or path.startswith("https://") or path.startswith("www."):
                url = path
                if url.startswith("www."):
                    url = "http://" + url
            else:
                # Format as Google search query
                url = f"https://google.com/search?q={urllib.parse.quote(path)}"
            
            cmd = f"xdg-open {shlex.quote(url)}"
        else:
            cmd = "xdg-open http://google.com"
    else:
        if path:
            resolved_path = resolve_project_path(path)
            quoted_path = shlex.quote(resolved_path)
            if cmd == "code":
                cmd = f"code {quoted_path}"
            elif cmd == "gnome-terminal":
                cmd = f"gnome-terminal --working-directory={quoted_path}"
            elif cmd == "nautilus":
                cmd = f"nautilus {quoted_path}"
            else:
                cmd = f"{cmd} {quoted_path}"
    
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

def scroll(direction, amount=300):
    """Scroll the screen up or down by amount."""
    try:
        # In Linux, scroll up is positive, scroll down is negative
        clicks = int(amount)
        if direction.lower() == "down":
            clicks = -clicks
        
        pyautogui.scroll(clicks)
        return f"Scrolled {direction} by {amount} units."
    except Exception as e:
        return f"Failed to scroll: {str(e)}"

def read_screen(instruction="Explain what is on the screen"):
    """Capture the screen and get Gemini API explanation."""
    import base64
    import requests
    import config_manager
    import ui_overlay
    import text_input_ui
    
    api_key = config_manager.get_gemini_api_key()
    if not api_key:
        return "Failed to read screen: Gemini API key not configured."
        
    temp_img_path = os.path.expanduser("~/.config/nexovian/temp_screenshot.png")
    os.makedirs(os.path.dirname(temp_img_path), exist_ok=True)
    
    # Check if bottom bar / overlay are open so we can restore them
    bar_was_visible = False
    try:
        bar = text_input_ui.get_bar()
        if bar.get_visible():
            bar_was_visible = True
            text_input_ui.hide_bar()
    except Exception:
        pass
        
    overlay_was_active = False
    try:
        ui = ui_overlay.get_ui()
        if ui.active:
            overlay_was_active = True
            ui_overlay.hide()
    except Exception:
        pass
        
    # Give UI windows time to fade out / hide
    time.sleep(0.5)
    
    try:
        # Capture screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_img_path)
    except Exception as e:
        # Restore UI before returning error
        if bar_was_visible:
            text_input_ui.show_bar()
        if overlay_was_active:
            ui_overlay.show_state("standby")
        return f"Failed to capture screenshot: {str(e)}"
        
    # Restore UI
    if bar_was_visible:
        text_input_ui.show_bar()
    if overlay_was_active:
        ui_overlay.show_state("standby")
        
    try:
        with open(temp_img_path, "rb") as image_file:
            img_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        return f"Failed to read image file: {str(e)}"
    finally:
        try:
            os.remove(temp_img_path)
        except OSError:
            pass
            
    # Send to Gemini API
    headers = {"Content-Type": "application/json"}
    
    prompt_text = (
        f"You are a helpful desktop assistant. The user wants you to analyze their screen.\n"
        f"User query: {instruction}\n\n"
        f"Please provide your analysis in two sections exactly:\n"
        f"Summary: A concise 1-2 sentence overview suitable for text-to-speech. Do not include asterisks or formatting symbols in the summary.\n"
        f"Details: A thorough, detailed breakdown of everything on the screen, including text, open applications, and user interface elements."
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": img_base64
                        }
                    }
                ]
            }
        ]
    }
    
    gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    last_error_msg = ""
    
    for model in gemini_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return "Gemini API returned no analysis candidates."
                    
                text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not text_content:
                    return "Gemini API returned empty explanation."
                    
                # Parse Summary and Details
                summary = ""
                details = ""
                
                if "Summary:" in text_content and "Details:" in text_content:
                    try:
                        summary = text_content.split("Summary:")[1].split("Details:")[0].strip()
                        details = text_content.split("Details:")[1].strip()
                    except Exception:
                        pass
                        
                if not summary or not details:
                    # Fallback if structure wasn't strictly followed
                    summary = text_content[:150] + "..." if len(text_content) > 150 else text_content
                    details = text_content
                    
                # Clean summary of formatting symbols
                summary = summary.replace("*", "").replace("#", "").strip()
                
                return f"[SPOKEN]: {summary} [DISPLAY]: {details}"
            else:
                last_error_msg = f"Gemini API returned error code {resp.status_code}: {resp.text}"
        except requests.exceptions.Timeout:
            last_error_msg = "Gemini API request timed out."
        except Exception as e:
            last_error_msg = f"Error communicating with Gemini API: {str(e)}"
            
    return last_error_msg


def read_file(filename):
    """Read contents of a file inside home directories or projects."""
    try:
        resolved_path = resolve_project_path(filename)
        if not resolved_path or not os.path.exists(resolved_path):
            expanded = os.path.expanduser(filename)
            if os.path.exists(expanded):
                resolved_path = expanded
            else:
                return f"File not found: {filename}"
                
        resolved_path = os.path.normpath(resolved_path)
        
        # Enforce safety boundaries: Only allow reading files inside home directory or /data/projects
        home_dir = os.path.expanduser("~")
        if not resolved_path.startswith(home_dir) and not resolved_path.startswith("/data/projects"):
            return "That action is above my permissions. Accessing system files is restricted."
            
        # PDF parsing support
        if resolved_path.lower().endswith(".pdf"):
            import subprocess
            try:
                result = subprocess.run(["pdftotext", resolved_path, "-"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    content = result.stdout[:4000]
                    if len(result.stdout) >= 4000:
                        content += "\n... [truncated]"
                    return content
                else:
                    return f"Failed to extract PDF text: {result.stderr.strip()}"
            except Exception as pdf_err:
                return f"Failed to run pdftotext: {str(pdf_err)}"
                
        # DOCX parsing support
        elif resolved_path.lower().endswith(".docx"):
            import zipfile
            import xml.etree.ElementTree as ET
            try:
                with zipfile.ZipFile(resolved_path) as docx:
                    xml_content = docx.read('word/document.xml')
                    root = ET.fromstring(xml_content)
                    namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    text_parts = []
                    for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                        p_text = "".join(node.text for node in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text)
                        if p_text:
                            text_parts.append(p_text)
                    full_text = "\n".join(text_parts)
                    content = full_text[:4000]
                    if len(full_text) >= 4000:
                        content += "\n... [truncated]"
                    return content
            except Exception as docx_err:
                return f"Failed to extract DOCX text: {str(docx_err)}"
            
        with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(4000)
            if len(content) >= 4000:
                content += "\n... [truncated]"
            return content
    except Exception as e:
        return f"Failed to read file: {str(e)}"

def set_autostart_enabled(enabled: bool):
    """Enable or disable the autostart desktop entry for Nexovian."""
    autostart_dir = os.path.expanduser("~/.config/autostart")
    dest_path = os.path.join(autostart_dir, "nexovian.desktop")
    
    if not enabled:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
                return "Autostart disabled successfully. Nexovian will no longer launch automatically on login."
            except Exception as e:
                return f"Failed to disable autostart: {str(e)}"
        return "Autostart is already disabled."
    else:
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            src_path = os.path.join(script_dir, "nexovian.desktop")
            
            if os.path.exists(src_path):
                import shutil
                shutil.copy2(src_path, dest_path)
            else:
                default_content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Exec=/usr/bin/python3 {os.path.join(script_dir, 'nexovian.py')}\n"
                    "Icon=audio-input-microphone\n"
                    "Hidden=false\n"
                    "NoDisplay=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                    "Name=Nexovian AI Agent\n"
                    "Comment=Desktop automation AI that listens for unlock and wake words\n"
                    "Terminal=false\n"
                    "Categories=Utility;Accessibility;\n"
                )
                with open(dest_path, "w") as f:
                    f.write(default_content)
            
            # Ensure it is enabled in the file
            if os.path.exists(dest_path):
                with open(dest_path, "r") as f:
                    lines = f.readlines()
                new_lines = []
                has_enabled_key = False
                for line in lines:
                    if line.strip().startswith("X-GNOME-Autostart-enabled"):
                        new_lines.append("X-GNOME-Autostart-enabled=true\n")
                        has_enabled_key = True
                    else:
                        new_lines.append(line)
                if not has_enabled_key:
                    new_lines.append("X-GNOME-Autostart-enabled=true\n")
                with open(dest_path, "w") as f:
                    f.writelines(new_lines)
                    
            return "Autostart enabled successfully. Nexovian will automatically launch when you start your system."
        except Exception as e:
            return f"Failed to enable autostart: {str(e)}"


