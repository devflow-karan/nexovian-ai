import subprocess
import os
import sys
import types
import time
import config_manager

# Headless / missing tkinter fallback for pyautogui on minimal Ubuntu installations
if "tkinter" not in sys.modules:
    try:
        import tkinter
    except ImportError:
        dummy_tk = types.ModuleType("tkinter")
        dummy_tk.ttk = types.ModuleType("ttk")
        dummy_tk.Event = object
        dummy_tk.TkVersion = 8.6
        dummy_tk.TclVersion = 8.6
        sys.modules["tkinter"] = dummy_tk
        sys.modules["tkinter.ttk"] = dummy_tk.ttk

import pyautogui

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
        
    import config_manager
    base_dir = config_manager.get_projects_dir()
    
    # If path_str is absolute, use it (ensuring it is resolved safely)
    if os.path.isabs(path_str):
        return os.path.normpath(path_str)
        
    # Check if directory or file exists in the active projects folder
    path_in_base = os.path.join(base_dir, path_str)
    if os.path.exists(path_in_base):
        return os.path.normpath(path_in_base)
        
    # Check in home directory (e.g. "Downloads/KaranKumar.pdf" -> "~/Downloads/KaranKumar.pdf")
    path_in_home = os.path.expanduser(f"~/{path_str}")
    if os.path.exists(path_in_home):
        return os.path.normpath(path_in_home)
        
    # Otherwise, default to projects folder and create parent directory
    try:
        dir_to_make = os.path.dirname(path_in_base)
        if dir_to_make:
            os.makedirs(dir_to_make, exist_ok=True)
        return os.path.normpath(path_in_base)
    except Exception:
        # Fallback to home documents
        docs_fallback = os.path.expanduser(f"~/Documents/{path_str}")
        dir_fallback = os.path.dirname(docs_fallback)
        if dir_fallback:
            os.makedirs(dir_fallback, exist_ok=True)
        return os.path.normpath(docs_fallback)

def open_application(app_name, path=None):
    import shlex
    import shutil
    import urllib.parse
    
    app_name_lower = app_name.lower().replace(" ", "")
    
    # Detect installed terminal emulator (Ptyxis on Ubuntu 26, gnome-terminal, etc.)
    terminal_bin = None
    for candidate in ["ptyxis", "gnome-terminal", "x-terminal-emulator", "kgx"]:
        if shutil.which(candidate):
            terminal_bin = candidate
            break
    if not terminal_bin:
        terminal_bin = "x-terminal-emulator"

    # Common mappings
    mappings = {
        "vscode": "code",
        "browser": "xdg-open",
        "terminal": terminal_bin,
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
            elif cmd == "ptyxis":
                cmd = f"ptyxis --working-directory={quoted_path}"
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
    """Write text or code to a file inside the active projects folder."""
    try:
        import config_manager
        base_dir = config_manager.get_projects_dir()
        
        # Clean path to prevent escaping outside directories
        # Allow subdirectory files, e.g. "abc/main.py"
        safe_path = os.path.normpath(filename).lstrip("/")
        while safe_path.startswith("../") or safe_path == "..":
            safe_path = safe_path[3:]
            
        file_path = os.path.join(base_dir, safe_path)
        
        # Write to active project directory
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
    import shutil
    import config_manager
    import ui_overlay
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
    
    screenshot_captured = False
    
    # Attempt Wayland / GNOME native tools first
    if shutil.which("gnome-screenshot"):
        try:
            res = subprocess.run(["gnome-screenshot", "-f", temp_img_path], capture_output=True, timeout=5)
            if res.returncode == 0 and os.path.exists(temp_img_path) and os.path.getsize(temp_img_path) > 0:
                screenshot_captured = True
        except Exception:
            pass

    if not screenshot_captured and shutil.which("grim"):
        try:
            res = subprocess.run(["grim", temp_img_path], capture_output=True, timeout=5)
            if res.returncode == 0 and os.path.exists(temp_img_path) and os.path.getsize(temp_img_path) > 0:
                screenshot_captured = True
        except Exception:
            pass

    # Fallback to pyautogui (X11 / Xwayland)
    if not screenshot_captured:
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(temp_img_path)
            screenshot_captured = True
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
            
    # Delegate visual analysis to configured VisionProvider
    from providers import get_vision_provider
    provider = get_vision_provider()
    return provider.analyze_screen(img_base64, instruction)


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
        
        # Enforce safety boundaries: Only allow reading files inside home directory or configured projects
        home_dir = os.path.expanduser("~")
        projects_dir = config_manager.get_projects_dir()
        if not resolved_path.startswith(home_dir) and not resolved_path.startswith(projects_dir):
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
            import sys
            os.makedirs(autostart_dir, exist_ok=True)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            nexovian_py = os.path.join(script_dir, "nexovian.py")
            py_bin = sys.executable or "/usr/bin/python3"
            
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Exec={py_bin} {nexovian_py}\n"
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
                f.write(content)
                    
            return "Autostart enabled successfully. Nexovian will automatically launch when you start your system."
        except Exception as e:
            return f"Failed to enable autostart: {str(e)}"


