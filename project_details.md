# Nexovian AI Agent - Project Details

## Overview (v1.5.0)
Nexovian is a local, privacy-focused desktop automation and conversational assistant designed exclusively for Ubuntu Linux environments. It bridges the gap between powerful local Large Language Models (LLMs) and local desktop scripting, giving users a **voice-controlled and typed** interface to interact with the OS and the internet seamlessly — entirely on your machine.

## Architecture & Core Modules
The system is built on a modular, multi-threaded Python 3 architecture:
1. **`nexovian.py`**: The main entry point. It manages the GTK3 event loop, DBus bindings (listening to `org.gnome.ScreenSaver`), and the global `pynput` Ctrl+Space hotkey listener thread. Orchestrates the full interaction flow from standby → listening → executing.
2. **`ui_overlay.py`**: The visual layer. Uses GTK3 with a Cairo Drawing Area to render a frameless, transparent pulsing animation overlay for listening/speaking state feedback.
3. **`text_input_ui.py`**: The typed input layer. A Raycast-style GTK3 window anchored to the bottom of the screen, featuring a scrollable chat log with coloured user/assistant bubbles. Handles typed command submission on a background thread, mirrors voice commands into the same log, and responds via both text and TTS.
4. **`llm_brain.py`**: The intelligence engine. Interfaces with a local Ollama service (defaulting to the `qwen3:8b` model) via REST calls. Utilises a strict system prompt to parse raw transcripts into actionable JSON commands.
5. **`audio_engine.py`**: The sensory layer. Runs a dedicated background thread for `openWakeWord` to constantly monitor for "Hey Nexovian", while also providing Text-To-Speech (TTS) via `robotic_voice.py` (with `pyttsx3` fallback) and Speech-To-Text (STT) via `SpeechRecognition`.
6. **`robotic_voice.py`**: The voice FX layer. Converts espeak WAV output through a ring modulator and metallic echo pipeline using NumPy, producing an AI-sounding robotic voice without any SoX dependency.
7. **`automation_executor.py`**: The interaction layer. Uses `pyautogui` for simulating mouse and keyboard events, and `subprocess` for launching applications. Enforces strict security policies to prevent destructive OS actions.
8. **`task_manager.py`**: The data layer. A lightweight JSON manager for handling CRUD operations on the user's TODO list.

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
- **Command Palette**: The bottom bar could be extended with quick-action buttons or slash-command autocompletion (e.g., `/remind`, `/weather`) for power-user workflows.
- **Conversation History Persistence**: The chat log in `text_input_ui.py` could be persisted to disk between sessions so users can review past interactions.
