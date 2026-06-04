# Changelog

All notable changes to the **Nexovian AI Agent** will be documented in this file.

## [1.5.0] - 2026-06-02
### Added
- **Typed Input / Bottom Bar** (`text_input_ui.py`): A Raycast-style floating bottom bar anchored to the bottom of the screen. Shows a scrollable chat history of typed prompts and Nexovian responses with distinct coloured bubbles.
- **Global Hotkey (Ctrl+Space)**: Press Ctrl+Space from any application to show or hide the bottom bar. Registered system-wide via `pynput.GlobalHotKeys`.
- **Simultaneous Voice + Text Input**: While the bar is open, the existing wake-word / voice pipeline continues to operate. Spoken commands and responses are mirrored into the chat log for a unified conversation view.
- **Persistent Bar**: The bar stays open until the user manually closes it with Ctrl+Space or Escape, maintaining full multi-turn context between queries.
- **pynput** added to `install_dependencies.sh` for global hotkey support.

## [1.4.0] - 2026-06-02
### Added
- **Robotic Voice Engine** (`robotic_voice.py`): Converts TTS output to an AI-sounding robotic voice using espeak + ring modulation + metallic echo FX. Fully offline, no SoX required. Falls back to pyttsx3 if unavailable.
- **`write_file` Action**: New LLM action that writes text or code to a file in `~/Documents` with path-traversal protection.
- **Dynamic Wake Words**: Wake-word detection now automatically includes the current day name (e.g. "Monday") as an extra trigger phrase.
- **Identity Prompt**: Nexovian now explicitly states it was made by Karan when asked about its origin.

### Changed
- Switched LLM model from `llama3.2` to `qwen3:8b`.
- Increased Ollama request timeout from 120 s to 300 s.
- System prompt now injects full weekday + month date for more accurate time-aware reasoning.

### Fixed
- Added 15-second debounce guard in `handle_unlock()` to prevent duplicate greeting triggers on rapid re-locks.
- Reminder alerts now suppress correctly while the system screen is locked (`is_system_locked` flag).

## [1.3.0] - 2026-05-30
### Added
- Persistent Reminders: Time-aware background reminders with 5-minute early warnings, safely surviving system reboots (`reminders.json`).
- LLM Time Injection: Inject live system time into the system prompt to allow for relative time scheduling ("remind me at 11am").
- LLM Output Robustness: Added regex-based parsing and one-shot examples for reliable JSON tool extraction from smaller 3B parameter models.

### Fixed
- Fixed UI locking bug where background threads permanently disabled the microphone by failing to hide the "speaking" overlay.
- Fixed collision bug where background alerts would interrupt active user conversations. Background reminders now patiently wait for standby mode.

## [1.3.0] - 2026-05-30
### Added
- Extended AI Context: Upgraded LLM prompts so Nexovian can act as a fully conversational assistant to answer general knowledge questions.
- Weather Tool API: Added live integration with `wttr.in` to allow Nexovian to check and verbally report real-time weather.
- Intelligent Name Parsing: During onboarding, the LLM now intelligently extracts just the user's first name from full conversational sentences.

### Fixed
- Reverted identity branding from Orion back to Nexovian.
- Increased the STT `pause_threshold` to 2.5 seconds to prevent the assistant from interrupting the user mid-sentence while they think.

## [1.2.0] - 2026-05-30
### Added
- Name configuration onboarding flow (`config.json`).
- Switched to Vosk for reliable custom wake words ("Nexovian" / "Nexovian").
- Implemented phonetic fallbacks for dictionary-based wake word matching.
- Added quick exits for conversational enders ("thank you", "goodbye") to bypass LLM processing time.

### Fixed
- Addressed infinite feedback loop caused by STT silence timeouts.
- Resolved ALSA microphone stream collision between background wake word and active STT.
- Fixed GTK UI overlay state attribute error.

## [1.1.0] - 2026-05-30
### Added
- Animated GTK3 UI overlay for visualizing listening and speaking states.
- Background CSS animations for pulsing UI indicators.
- Automatic startup on system boot via `nexovian.desktop` in `~/.config/autostart/`.
- Detailed project documentation (`project_details.md` and `CHANGELOG.md`).

### Changed
- Converted core daemon from GLib DBus loop to Gtk.main() for native UI integration.
- Switched background audio threading model to trigger Gtk UI updates via `GLib.idle_add`.

## [1.0.0] - 2026-05-30
### Added
- Complete rewrite from `ubuntu-unlock-assistant` to **Nexovian AI Agent**.
- Local LLM integration using Ollama (`qwen3:8b`).
- Local STT and TTS using `SpeechRecognition`, `openWakeWord`, and `pyttsx3`.
- File-based task manager (`~/Documents/tasks.json`).
- `automation_executor.py` capable of opening system applications, controlling mouse/keyboard via `pyautogui`, and executing safe shell commands.
- Strict security blocks against root/sudo operations.
