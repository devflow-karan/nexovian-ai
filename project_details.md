# Nexovian AI Agent - Project Details

## Overview
Nexovian is a local, privacy-focused desktop automation assistant designed exclusively for Ubuntu Linux environments. It bridges the gap between powerful local Large Language Models (LLMs) and local desktop operations, ensuring all data, speech, and task logic remains entirely on your machine.

## Architecture & Core Modules
The system is built on a modular, multi-threaded Python 3 architecture:
1. **`nexovian.py`**: The main entry point. It manages the GTK3 event loop and DBus bindings (listening to `org.gnome.ScreenSaver`). This orchestrates the user interaction flow from standby to listening to executing.
2. **`ui_overlay.py`**: The visual layer. It uses GTK3 with a Cairo Drawing Area to render a frameless, transparent overlay on top of all windows, providing visual feedback (pulsing animations) for Nexovian's state.
3. **`llm_brain.py`**: The intelligence engine. It interfaces with a local Ollama service (defaulting to the `qwen3:8b` model) via REST calls. It utilizes a strict system prompt to parse raw audio transcripts into actionable JSON commands.
4. **`audio_engine.py`**: The sensory layer. It runs a dedicated background thread for `openWakeWord` to constantly monitor for "Hey Nexovian", while also providing Text-To-Speech (TTS) via `pyttsx3` and Speech-To-Text (STT) via `SpeechRecognition`.
5. **`automation_executor.py`**: The interaction layer. It uses `pyautogui` for simulating mouse and keyboard events, and `subprocess` for launching applications. It enforces strict security policies to prevent destructive OS actions.
6. **`task_manager.py`**: The data layer. A lightweight JSON manager for handling CRUD operations on the user's TODO list.

## Security Posture
Nexovian is designed to run in user-space. It uses a blacklist and boundary approach within `automation_executor.py` to outright reject commands containing:
- `sudo`
- `su`
- `rm -rf /`
- `chown` / `chmod 777`
- `passwd`

## Future Development & Extensibility
- **Custom Wake Words**: While `openWakeWord` is integrated, future iterations can allow the user to easily record and train customized wake words.
- **SQLite Migration**: For larger task datasets, the `tasks.json` structure can be migrated to a SQLite local database.
- **Plugin System**: The `llm_brain.py` JSON parser can easily be expanded to support new action tools.
