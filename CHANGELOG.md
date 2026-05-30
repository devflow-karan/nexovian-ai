# Changelog

All notable changes to the **Nexovian AI Agent** will be documented in this file.

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
