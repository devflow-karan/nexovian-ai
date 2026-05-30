# Changelog

All notable changes to the **Nexovian AI Agent** will be documented in this file.

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
