# Nexovian AI Agent (v1.5.0)

Nexovian (or Nexo) is a personal AI desktop assistant running locally on Ubuntu (22.04 and 24.04). It acts as an interactive desktop automation daemon that operates in the background, listening for wake words and responding intelligently to natural language commands.

## Features

- **Conversational & Weather API:** Ask general knowledge questions or get live weather updates, fully parsed and delivered through natural conversation.
- **Custom User Profiles:** Nexovian asks for your preferred name using conversational AI parsing and remembers it persistently (`~/.config/nexovian`).
- **Animated UI Overlay:** A transparent, pulsing visual interface appears dynamically when Nexovian is listening or speaking, providing clear visual feedback.
- **Auto-Start:** Automatically launches in the background when you log into your Ubuntu session.
- **openWakeWord Custom Wake Words:** Continuously listens for custom wake words like "Nexo" or "Nexovian" with zero cloud dependency using openWakeWord (ONNX Runtime, <2% CPU).
- **System Unlock Greetings:** Integrates with the GNOME ScreenSaver via DBus to automatically greet you when you unlock your machine.
- **Local LLM Intelligence:** Connects to a local instance of Ollama (using the `qwen3.5:9b` model by default) to process natural language intents with full privacy.
- **Desktop Automation:** Capable of controlling the mouse, keyboard, and launching system applications (e.g., VS Code, terminal).
- **Task Management:** Automatically parses intent to create, read, and manage your local TODO tasks in a simple JSON file.
- **Persistent Reminders:** Schedule time-aware background alarms that persist across reboots, with 5-minute early warnings.
- **Robotic Voice:** Uses `espeak` + ring modulation to produce an AI-sounding robotic voice. Falls back to `pyttsx3` if unavailable.
- **Typed Input (Bottom Bar):** Press **Ctrl+Space** from any application to open a Raycast-style floating bottom bar. Type commands directly and see a scrollable chat history of your conversation. Voice and typed inputs are unified in the same log.
- **Strict Security:** Enforces strict permission boundaries, refusing to execute dangerous system operations like `sudo`, `rm -rf /`, or password changes.

## Prerequisites

Before installing, ensure your system meets the following requirements:
- **Operating System:** Ubuntu 22.04, 24.04, or 26.04 LTS
- **Python:** Python 3.10+ (tested with Python 3.14 on Ubuntu 26.04)
- **Hardware:** Sufficient RAM and CPU to run local LLMs (8GB RAM minimum, 16GB+ recommended).
- **Global Hotkey support:** `pynput` with XWayland or native D-Bus shortcut. See [Wayland note](#wayland-note) below.

## Installation

1. **Install System Dependencies and Python Packages**
   Run the included bash script to install all required libraries:
   ```bash
   bash install_dependencies.sh
   ```

2. **Install Ollama**
   Nexovian relies on [Ollama](https://ollama.com/) to process AI commands. If the installation script failed to install Ollama due to `sudo` permissions, you can install it manually:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

3. **Pull the AI Model**
   Once Ollama is installed and running in the background, download the model.
   ```bash
   ollama pull qwen3.5:9b
   ```

## Wake Word System (openWakeWord)

Nexovian uses **openWakeWord** (ONNX-powered acoustic keyword spotter) for offline wake word detection:
- **Model File**: Located at `models/nexovian.onnx` (and auto-copied to `~/.local/share/nexovian/models/nexovian.onnx`).
- **Wake Words**: "Nexovian", "Hey Nexovian", "Hello Nexovian", "Nexo", "Hello Nexo".
- **Testing**: Run the diagnostic CLI tool to test detection via live microphone or synthetic evaluation:
  ```bash
  # Evaluate on test suite
  python3 scripts/test_wakeword.py --eval

  # Test live microphone stream with real-time confidence scores
  python3 scripts/test_wakeword.py
  ```
- **Retraining / Customizing**: Run the automated training script to re-synthesize audio and export a new model:
  ```bash
  python3 scripts/train_wakeword.py
  ```

## How to Run

1. **Start the Agent**
   To start Nexovian, execute the main python script from your terminal:
   ```bash
   GDK_BACKEND=x11 python3 nexovian.py
   ```
   The agent will run continuously as a background daemon attached to your DBus session.

2. **Interact with Nexovian**
   - **On system unlock:** When you enter your password and unlock Ubuntu, Nexovian will automatically greet you and read your pending tasks.
   - **Voice commands:** You can say "Hey Nexovian" followed by a command (e.g., "Open VS Code", "Create a task to write documentation").
   - **Typed commands (Bottom Bar):** Press **Ctrl+Space** from anywhere to open the floating bottom bar. Type your command and press **Enter** or click **Send**. Press **Ctrl+Space** or **Escape** to dismiss.

## Project Structure

- `nexovian.py`: The main daemon entry point managing the DBus session, background threads, and global hotkey listener.
- `audio_engine.py`: Handles microphone input, openWakeWord wake word listening, Google STT for commands, and Text-to-Speech (TTS).
- `models/nexovian.onnx`: Pre-trained acoustic wake-word classifier model for "Nexovian" and "Nexo".
- `scripts/train_wakeword.py`: Synthetic training and ONNX export tool for the custom wake-word model.
- `scripts/test_wakeword.py`: CLI testing and diagnostic tool for microphone and synthetic wake-word verification.
- `text_input_ui.py`: The Raycast-style typed-input bottom bar. GTK3 window with scrollable chat history, activated by Ctrl+Space.
- `ui_overlay.py`: Transparent pulsing overlay for visual listening/speaking feedback.
- `llm_brain.py`: Manages the system prompts, HTTP requests to the Ollama API, and JSON command parsing.
- `automation_executor.py`: Defines the safe boundaries and executes system commands, key presses, and mouse movements.
- `task_manager.py`: Lightweight manager for CRUD operations on your `~/Documents/tasks.json` file.
- `reminder_manager.py`: Background thread for managing and triggering time-based user reminders.
- `robotic_voice.py`: espeak-based TTS post-processor that applies ring modulation + echo for a robotic AI voice.
- `install_dependencies.sh`: Shell script for bootstrapping a fresh Ubuntu environment.

## Wayland Note
 
On Ubuntu (including Ubuntu 26.04), Wayland is enabled by default. Nexovian uses XWayland for transparent Cairo waveforms and window docking. In addition, you can register a native global shortcut in GNOME Settings to toggle the bottom bar instantly from any application (even native Wayland windows):
```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
  "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/']"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/ name 'Nexovian Toggle'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/ command 'gdbus call --session --dest org.nexovian.Agent --object-path /org/nexovian/Agent --method org.nexovian.Agent.ToggleBar'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/ binding '<Control>space'
```

## Security Note
Nexovian is built with a restricted environment paradigm. Even if a user asks the agent to delete critical system files or use root access, the `automation_executor.py` explicitly blocks those commands to prevent accidental or malicious destruction of the host system.
