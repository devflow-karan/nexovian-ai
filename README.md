# Nexovian AI Agent (v1.3.0)

Nexovian (or Nexo) is a personal AI desktop assistant running locally on Ubuntu (22.04 and 24.04). It acts as an interactive desktop automation daemon that operates in the background, listening for wake words and responding intelligently to natural language commands.

## Features

- **Conversational & Weather API:** Ask general knowledge questions or get live weather updates, fully parsed and delivered through natural conversation.
- **Custom User Profiles:** Nexovian asks for your preferred name using conversational AI parsing and remembers it persistently (`~/.config/nexovian`).
- **Animated UI Overlay:** A transparent, pulsing visual interface appears dynamically when Nexovian is listening or speaking, providing clear visual feedback.
- **Auto-Start:** Automatically launches in the background when you log into your Ubuntu session.
- **Vosk Custom Wake Words:** Continuously listens for custom wake words like "Nexo" or "Nexovian" with zero cloud dependency.
- **System Unlock Greetings:** Integrates with the GNOME ScreenSaver via DBus to automatically greet you when you unlock your machine.
- **Local LLM Intelligence:** Connects to a local instance of Ollama (using the `qwen3:8b` model by default) to process natural language intents with full privacy.
- **Desktop Automation:** Capable of controlling the mouse, keyboard, and launching system applications (e.g., VS Code, terminal).
- **Task Management:** Automatically parses intent to create, read, and manage your local TODO tasks in a simple JSON file.
- **Strict Security:** Enforces strict permission boundaries, refusing to execute dangerous system operations like `sudo`, `rm -rf /`, or password changes.

## Prerequisites

Before installing, ensure your system meets the following requirements:
- **Operating System:** Ubuntu 22.04 or 24.04
- **Python:** Python 3.10+
- **Hardware:** Sufficient RAM and CPU to run local LLMs (8GB RAM minimum, 16GB+ recommended).

## Installation

1. **Install System Dependencies and Python Packages**
   Run the included bash script to install all required libraries (such as `pyautogui`, `openwakeword`, system audio libraries, etc.):
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
   ollama pull qwen3:8b
   ```
   *(Note: If `qwen3:8b` is unavailable, you may edit `llm_brain.py` to use an alternative model like `llama3` or `qwen2.5:8b` and pull that instead).*

## How to Run

1. **Start the Agent**
   To start Nexovian, simply execute the main python script from your terminal:
   ```bash
   python3 nexovian.py
   ```
   The agent will run continuously as a background daemon attached to your DBus session.

2. **Interact with Nexovian**
   - **On system unlock:** When you enter your password and unlock Ubuntu, Nexovian will automatically greet you and read your pending tasks.
   - **Voice commands:** You can say "Hey Nexovian" followed by a command (e.g., "Open VS Code", "Create a task to write documentation").

## Project Structure

- `nexovian.py`: The main daemon entry point managing the DBus session and background threads.
- `audio_engine.py`: Handles microphone input, openWakeWord listening, and Text-to-Speech (TTS).
- `llm_brain.py`: Manages the system prompts, HTTP requests to the Ollama API, and JSON command parsing.
- `automation_executor.py`: Defines the safe boundaries and executes system commands, key presses, and mouse movements.
- `task_manager.py`: Lightweight manager for CRUD operations on your `~/Documents/tasks.json` file.
- `install_dependencies.sh`: Shell script for bootstrapping a fresh Ubuntu environment.

## Security Note
Nexovian is built with a restricted environment paradigm. Even if a user asks the agent to delete critical system files or use root access, the `automation_executor.py` explicitly blocks those commands to prevent accidental or malicious destruction of the host system.
