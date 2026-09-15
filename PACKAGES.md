# Nexovian AI — Complete Packages & Dependencies Audit

This document provides an exhaustive reference of all **system packages (APT)**, **Python libraries (PIP)**, and **external services/binaries** utilized by the **Nexovian AI Agent**.

It details:
- What each package does in the project.
- **Pros** of removing it (resources saved, reduced attack surface).
- **Cons** of removing it (which Nexovian features break).
- **System Impact & OS Risks** (whether removing it will break Ubuntu desktop, GNOME, or system audio).
- Safe alternatives and modular configurations.

---

## 1. System Safety Matrix (Risk Assessment)

Before removing any package from your machine, review this classification:

| Risk Level | Description | Packages in this Category |
| :--- | :--- | :--- |
| 🔴 **CRITICAL RISK**<br>*(DO NOT REMOVE VIA APT)* | Core Ubuntu GNOME desktop dependencies. Removing via `apt remove` will trigger `apt` to uninstall `ubuntu-desktop`, `gnome-shell`, `gnome-control-center`, or break login. | `python3-gi`, `gir1.2-gtk-3.0`, `python3-gi-cairo`, `python3-dbus`, `alsa-utils` |
| 🟡 **MODERATE RISK**<br>*(Affects System Features)* | Shared system utilities. Removing them will not destroy the desktop session, but will break audio playback, screen readers, terminal tools, or PDF handling system-wide. | `espeak`, `espeak-ng`, `portaudio19-dev`, `poppler-utils`, `python3-tk`, `python3-venv`, `python3-pip` |
| 🟢 **SAFE FOR OS**<br>*(Nexovian Impact Only)* | Isolated Python packages or standalone daemons installed in user space or virtual environment. Removing them will **never break Ubuntu**, but will disable specific Nexovian features. | `openwakeword`, `onnxruntime`, `pyautogui`, `SpeechRecognition`, `pyttsx3`, `ollama`, `f5-tts`, `vosk`, `scipy`, `scikit-learn` |

---

## 2. Master Summary Table

| Package Name | Type / Source | Used In | Nexovian Impact if Removed | Ubuntu OS Impact if Removed | OS Safety |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `gir1.2-gtk-3.0` | APT | UI Overlay, Bottom Bar | Nexovian GUI crashes completely | 🔴 Breaks GNOME desktop & GTK apps | 🔴 High Risk |
| `python3-gi` | APT | UI Overlay, Hotkeys, DBus | Nexovian cannot launch | 🔴 Destroys Ubuntu desktop components | 🔴 High Risk |
| `python3-gi-cairo` | APT | Audio waveform visualizer | Glowing wave visualizer crashes | 🔴 Breaks Cairo-rendered desktop UI | 🔴 High Risk |
| `python3-dbus` | APT | Screen lock listener, DBus daemon | Auto-greeting & toggle IPC fails | 🔴 Breaks GNOME screen locking & DBus | 🔴 High Risk |
| `alsa-utils` | APT | Audio capture, volume checks | Mic volume checks fail | 🔴 Breaks system sound & ALSA tools | 🔴 High Risk |
| `pynput` | PIP / APT | Global `Ctrl+Space` listener | Hotkey toggle stops working | 🟢 No OS impact | 🟢 Safe |
| `openwakeword` | PIP | Offline wake-word detection | "Hey Nexovian" detection stops | 🟢 No OS impact | 🟢 Safe |
| `onnxruntime` | PIP | Runs wake-word ML models | Wake-word engine crashes | 🟢 No OS impact | 🟢 Safe |
| `pyaudio` | PIP / APT | Mic streaming for wake words & audio | Voice listening & recording fails | 🟢 No OS impact | 🟢 Safe |
| `portaudio19-dev`| APT | Audio driver header for PyAudio | Cannot compile PyAudio on install | 🟢 No runtime OS impact | 🟡 Moderate |
| `SpeechRecognition`| PIP | Command STT orchestrator | Voice command transcription fails | 🟢 No OS impact | 🟢 Safe |
| `vosk` | PIP / Model | Offline Speech-to-Text | Offline voice commands fail | 🟢 No OS impact | 🟢 Safe |
| `sounddevice` | PIP / APT | Audio input/output helper | Alternative audio capture breaks | 🟢 No OS impact | 🟢 Safe |
| `espeak` / `espeak-ng`| APT | Robotic voice generator | Robotic voice synthesis fails | 🟡 Breaks system speech/Orca | 🟡 Moderate |
| `pyttsx3` | PIP | Fallback Text-to-Speech | Fallback TTS voice unavailable | 🟢 No OS impact | 🟢 Safe |
| `numpy` | PIP / APT | Ring modulator & audio DSP | Robotic voice & wake words crash | 🟢 No OS impact (if pip user) | 🟢 Safe |
| `scipy` | PIP | Wake-word training & resampling | Cannot train/resample wake-words | 🟢 No OS impact | 🟢 Safe |
| `scikit-learn` | PIP | MLP wake-word training | Cannot train custom wake-words | 🟢 No OS impact | 🟢 Safe |
| `onnx` / `skl2onnx` | PIP | Custom ONNX model export | Cannot export trained wake models | 🟢 No OS impact | 🟢 Safe |
| `pyautogui` | PIP | Mouse, keyboard & screenshot | Automation & scrolling fails | 🟢 No OS impact | 🟢 Safe |
| `python3-tk` | APT | GUI backend for PyAutoGUI | PyAutoGUI fallback mode breaks | 🟡 Breaks Tkinter python scripts | 🟡 Moderate |
| `requests` | PIP | REST calls to Ollama, Gemini, wttr.in | Brain & weather API calls break | 🟢 No OS impact | 🟢 Safe |
| `ollama` (daemon) | Binary / System | Local LLM intelligence & vision | Offline AI thinking stops working | 🟢 No OS impact (releases ~8GB RAM) | 🟢 Safe |
| `f5-tts` & `torch`| PIP | Zero-shot Voice Cloning | Voice cloning disabled (falls back) | 🟢 No OS impact (frees ~4GB disk) | 🟢 Safe |
| `poppler-utils` | APT | `pdftotext` document reading | Cannot read user PDF files | 🟡 Breaks PDF thumbnailing/tools | 🟡 Moderate |
| `gnome-screenshot`| APT | Screen capture for vision | Vision analysis falls back to grim | 🟢 No OS impact | 🟢 Safe |
| `grim` | APT | Wayland screenshot utility | Vision falls back to PyAutoGUI | 🟢 No OS impact | 🟢 Safe |
| `xhost` | APT | XWayland input authorization | Hotkey may fail on Wayland | 🟡 Weakens X11 display permissions | 🟡 Moderate |

---

## 3. In-Depth Package Breakdown by Subsystem

---

### Component 1: Graphical Interface & Desktop Integration

#### 1. `gir1.2-gtk-3.0` & `python3-gi`
- **What Nexovian uses it for**:
  - `nexovian.py`: Runs `Gtk.main()` event loop and manages daemon threading.
  - `ui_overlay.py`: Creates the transparent, click-through, frameless floating overlay window on top of all applications.
  - `text_input_ui.py`: Renders the bottom bar chat window with scrollable history, buttons, and custom CSS styling.
- **Pros of Removing**:
  - None. Saves minimal disk space (< 30 MB).
- **Cons (Nexovian Breakdown)**:
  - **Fatal**: Nexovian will immediately crash on launch (`ModuleNotFoundError: No module named 'gi'`).
- **System Issues & OS Breakage**:
  - 🔴 **EXTREME DANGER**: Do NOT run `sudo apt remove python3-gi` or `sudo apt remove gir1.2-gtk-3.0`.
  - In Ubuntu, GNOME Shell, the Settings app (`gnome-control-center`), and system updaters depend on `python3-gi`. Removing this package will prompt APT to uninstall your entire desktop environment.

#### 2. `python3-gi-cairo`
- **What Nexovian uses it for**:
  - `ui_overlay.py`: Renders the real-time vector waveform animations, glow gradients, and alpha-blended transparency.
- **Pros of Removing**:
  - Saves negligible disk space (< 1 MB).
- **Cons (Nexovian Breakdown)**:
  - The animated overlay window fails to draw and throws Cairo context errors.
- **System Issues & OS Breakage**:
  - 🔴 **HIGH DANGER**: Other GTK vector applications rely on this. Removing it via APT can trigger cascading package removal.

#### 3. `python3-dbus` / `dbus`
- **What Nexovian uses it for**:
  - `nexovian.py`: Publishes the `org.nexovian.Agent` service on the session bus.
  - Listens to `org.gnome.ScreenSaver` and systemd `org.freedesktop.login1` signals to detect when you lock and unlock your laptop to greet you.
  - Allows external hotkeys or terminal commands (`gdbus call ... ToggleBar`) to open the UI.
- **Pros of Removing**:
  - None.
- **Cons (Nexovian Breakdown)**:
  - Lock/unlock detection breaks completely. The bottom bar toggle via DBus stops working.
- **System Issues & OS Breakage**:
  - 🔴 **HIGH DANGER**: D-Bus is the central nervous system of Linux desktop IPC. Removing `python3-dbus` can break system scripts and desktop utilities.

#### 4. `pynput`
- **What Nexovian uses it for**:
  - `nexovian.py`: Hooks global keyboard events via `pynput.keyboard.GlobalHotKeys` to capture `Ctrl+Space` from anywhere on X11 / XWayland.
- **Pros of Removing**:
  - Eliminates a low-level keyboard listener thread.
  - Minor memory savings (< 10 MB).
- **Cons (Nexovian Breakdown)**:
  - Pressing `Ctrl+Space` will no longer toggle the bottom bar unless you use the native GNOME media keybinding configured via `gsettings`.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Removing `pynput` has zero effect on the operating system.

---

### Component 2: Wake Word & Speech-to-Text (STT)

#### 5. `openwakeword` & `onnxruntime`
- **What Nexovian uses it for**:
  - `audio_engine.py`: Runs continuous, ultra-low CPU (< 2%) acoustic wake word spotter for "Nexovian", "Hey Nexovian", and "Nexo" using `models/nexovian.onnx`.
- **Pros of Removing**:
  - Saves ~150 MB disk space.
  - Saves ~40 MB RAM by stopping the background ML inference loop.
  - Prevents the microphone from being opened in the background during standby.
- **Cons (Nexovian Breakdown)**:
  - Wake-word voice activation stops working. You will only be able to interact via typed commands (`Ctrl+Space`) or D-Bus WakeUp signals.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Both are self-contained Python libraries. Removing them causes zero system issues.

#### 6. `pyaudio` & `portaudio19-dev`
- **What Nexovian uses it for**:
  - `audio_engine.py`: Reads raw 16 kHz 16-bit PCM microphone streams in chunks of 1280 samples for the wake-word engine.
  - `scripts/record_voice_sample.py`: Records microphone clips for voice cloning.
- **Pros of Removing**:
  - Stops PortAudio audio stream bindings.
- **Cons (Nexovian Breakdown)**:
  - Voice wake-word detection crashes.
  - Microphone recording utility cannot run.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Removing `pyaudio` via `pip` is harmless.
  - 🟡 `portaudio19-dev` is only a build header library; removing it via APT won't break runtime audio, but will prevent compiling audio packages from source.

#### 7. `SpeechRecognition`
- **What Nexovian uses it for**:
  - `audio_engine.py`: Acts as the high-level audio dispatcher. Calibrates ambient noise thresholds, segments spoken phrases, and dispatches the recorded utterance to the active STT provider.
- **Pros of Removing**:
  - Reduces dependency tree.
- **Cons (Nexovian Breakdown)**:
  - Nexovian cannot capture or transcribe your voice commands after wake-word activation.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Pure Python package. Safe to remove.

#### 8. `vosk` & `sounddevice`
- **What Nexovian uses it for**:
  - `providers/stt.py`: Provides 100% offline Speech-to-Text transcription using the local Kaldi model (`vosk-model-small-en-us-0.15`).
  - `unlock_assistant.py`: Used in legacy unlock script.
- **Pros of Removing**:
  - Frees ~100 MB of package size plus ~200 MB for the downloaded acoustic model directory (`~/.local/share/vosk-models/`).
  - Saves memory during voice recognition.
- **Cons (Nexovian Breakdown)**:
  - Offline voice transcription stops working. You must switch to Google Cloud STT fallback (`"stt_provider": "google"` in `config.json`), requiring internet access.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: No OS impact.

---

### Component 3: Text-to-Speech (TTS) & Audio Effects

#### 9. `espeak` & `espeak-ng`
- **What Nexovian uses it for**:
  - `robotic_voice.py`: Generates the raw speech phoneme WAV file before ring modulation.
  - `scripts/train_wakeword.py`: Synthesizes diverse acoustic variations of wake phrases to train custom wake models.
- **Pros of Removing**:
  - Saves ~15 MB disk space.
- **Cons (Nexovian Breakdown)**:
  - The default **Robotic Voice** engine breaks. Nexovian falls back to `pyttsx3` (which itself may depend on espeak) or produces no speech output.
  - `train_wakeword.py` cannot generate synthetic training samples.
- **System Issues & OS Breakage**:
  - 🟡 **MODERATE RISK**: In Ubuntu, `espeak-ng` is often linked to the Orca screen reader and accessibility services. Removing it breaks accessibility speech on Linux.

#### 10. `pyttsx3`
- **What Nexovian uses it for**:
  - `audio_engine.py` & `providers/tts.py`: Acts as the secondary offline TTS fallback engine if robotic or cloned voices encounter an error.
- **Pros of Removing**:
  - Cleans up unused TTS fallback code.
- **Cons (Nexovian Breakdown)**:
  - If the robotic voice or voice clone fails, Nexovian will remain completely silent instead of falling back to system speech.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Pip package with no OS dependency.

#### 11. `numpy`
- **What Nexovian uses it for**:
  - `robotic_voice.py`: Performs digital signal processing (DSP) — 200 Hz carrier wave multiplication (ring modulator), metallic echo delays, and audio normalization.
  - `openwakeword`: Manages multi-dimensional audio tensors and embeddings.
  - `audio_engine.py`: Audio buffer slicing.
- **Pros of Removing**:
  - None. (Almost all modern Python libraries require NumPy).
- **Cons (Nexovian Breakdown)**:
  - **Fatal**: Wake words, robotic speech, and audio processing all crash instantly with `ModuleNotFoundError: No module named 'numpy'`.
- **System Issues & OS Breakage**:
  - 🔴 If removed via `sudo apt remove python3-numpy`, other system tools depending on NumPy will break. If removed only from a virtual environment or pip user site, OS is unharmed.

#### 12. `alsa-utils`, PipeWire (`wpctl`), PulseAudio (`paplay`, `pactl`)
- **What Nexovian uses it for**:
  - `audio_engine.py`: Runs `wpctl get-volume @DEFAULT_AUDIO_SOURCE@` and `pactl get-source-mute` to detect whether your microphone is hardware-muted (pausing the assistant so it doesn't waste CPU or log errors).
  - `robotic_voice.py` & `providers/tts.py`: Uses `paplay` (or `aplay`) to stream generated WAV speech directly to your speakers or Bluetooth headphones.
- **Pros of Removing**:
  - None.
- **Cons (Nexovian Breakdown)**:
  - Nexovian cannot play voice output and cannot detect microphone mute state.
- **System Issues & OS Breakage**:
  - 🔴 **EXTREME DANGER**: Do NOT remove `alsa-utils` or PipeWire packages. These are fundamental sound drivers for Linux. Removing them mutes your entire computer.

#### 13. Voice Cloning: `f5-tts`, `torch`, `torchaudio`, `soundfile`
- **What Nexovian uses it for**:
  - `providers/tts.py` (`ClonedVoiceProvider`): Zero-shot neural voice cloning. Takes a 10-second reference sample of your voice from `~/.config/nexovian/voice_reference.wav` and speaks responses matching your exact vocal tone.
- **Pros of Removing**:
  - **Huge Disk Savings**: PyTorch + Torchaudio + F5-TTS take **3.5 GB to 5.0 GB** of disk space!
  - **Huge RAM/VRAM Savings**: F5-TTS loads deep learning weights requiring 2–4 GB of RAM/VRAM.
  - Removing these packages significantly speeds up dependency installation.
- **Cons (Nexovian Breakdown)**:
  - Nexovian cannot speak in your cloned voice. It automatically and gracefully falls back to the lightweight offline **Robotic Voice** (`robotic_voice.py`), which takes < 15 MB RAM.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Completely isolated Python libraries. Zero risk to the Ubuntu operating system.

---

### Component 4: Local AI Intelligence & Vision

#### 14. `requests`
- **What Nexovian uses it for**:
  - `llm_brain.py` & `providers/llm.py`: Communicates with the local Ollama daemon via REST (`http://localhost:11434/api/generate` and `/api/tags`).
  - Queries Google Gemini API (if configured).
  - Fetches weather from `https://wttr.in`.
- **Pros of Removing**:
  - None.
- **Cons (Nexovian Breakdown)**:
  - **Fatal**: The AI brain becomes disconnected. Nexovian cannot process natural language or talk to any model.
- **System Issues & OS Breakage**:
  - 🟢 Safe if removed from user pip, but keep it for Nexovian to function.

#### 15. `ollama` (Service & CLI)
- **What Nexovian uses it for**:
  - Local LLM execution. Runs models like `qwen3.5:9b`, `qwen3:8b`, `llama3.2`, and `moondream` on your CPU / RTX 5050 Laptop GPU.
- **Pros of Removing / Stopping**:
  - **Massive RAM & VRAM Relief**:
    - Unloading models saves **4 GB to 10 GB** of system memory and GPU VRAM.
    - Stopping the service (`systemctl stop ollama`) prevents background GPU memory allocation.
  - Saves **5 GB to 15 GB** of disk space used by downloaded model weights under `~/.ollama/models`.
- **Cons (Nexovian Breakdown)**:
  - Local AI intelligence completely ceases. Nexovian will be unable to parse commands unless you configure a Google Gemini cloud API key in `config.json`.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Ollama is a third-party daemon. Removing or stopping it has zero impact on Ubuntu desktop operations.

---

### Component 5: Desktop Automation, Document Parsing & Screen Reading

#### 16. `pyautogui` & `python3-tk`
- **What Nexovian uses it for**:
  - `automation_executor.py`: Simulates mouse movement, clicks, mouse scrolling (`scroll down`), keystroke automation, and fallback screenshot capture.
  - Requires Tkinter (`python3-tk`) on Linux for coordinate mapping.
- **Pros of Removing**:
  - Eliminates OS input simulation capabilities (security hardening if you don't want AI manipulating mouse/keyboard).
  - Saves ~50 MB.
- **Cons (Nexovian Breakdown)**:
  - Commands like "scroll down", "scroll up", or automated key clicks will fail.
- **System Issues & OS Breakage**:
  - 🟢 `pyautogui` is a pip package (safe).
  - 🟡 `python3-tk` is an APT package used by Tkinter Python scripts. Safe to keep.

#### 17. `poppler-utils` (`pdftotext`)
- **What Nexovian uses it for**:
  - `automation_executor.py`: When you ask Nexovian to read a file (e.g., "Read my resume KaranKumar.pdf"), it executes `pdftotext <file> -` to extract text up to 4000 characters for the LLM to inspect.
- **Pros of Removing**:
  - Saves ~10 MB.
- **Cons (Nexovian Breakdown)**:
  - Nexovian will fail to read `.pdf` documents. It will only be able to read plain text files (`.txt`, `.py`, `.json`, `.md`) and `.docx` files.
- **System Issues & OS Breakage**:
  - 🟡 **MODERATE RISK**: Removing `poppler-utils` breaks PDF command-line utilities and GNOME file manager PDF preview thumbnailers.

#### 18. `gnome-screenshot` & `grim`
- **What Nexovian uses it for**:
  - `automation_executor.py`: Captures instant screenshots for `read_screen` commands ("What's on my screen?"). Tries `gnome-screenshot` on GNOME/X11, `grim` on Wayland, and falls back to `pyautogui`.
- **Pros of Removing**:
  - Saves ~5 MB disk space.
- **Cons (Nexovian Breakdown)**:
  - Nexovian will fall back to `pyautogui.screenshot()`, which may fail or capture a black image on native Wayland sessions.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: These are standalone screenshot binaries. Removing them won't destabilize Ubuntu.

---

### Component 6: Machine Learning Training Tools (Optional)

#### 19. `scikit-learn` (`sklearn`), `scipy`, `onnx`, `skl2onnx`
- **What Nexovian uses it for**:
  - `scripts/train_wakeword.py`: Synthesizes audio samples, trains an `MLPClassifier` neural network, and builds an ONNX computation graph to export a custom wake-word file (`models/nexovian.onnx`).
  - `scripts/test_wakeword.py`: Resamples synthetic test audio at 16 kHz to verify false-positive and trigger rates.
- **Pros of Removing**:
  - **Saves ~800 MB to 1.2 GB** of disk space!
  - Eliminates heavy data science dependencies that are **only needed when retraining wake-word models**.
- **Cons (Nexovian Breakdown)**:
  - **Zero impact on runtime execution**! The main daemon (`nexovian.py`) uses the pre-compiled `models/nexovian.onnx` file via `onnxruntime` and does NOT require `scikit-learn` or `skl2onnx` to run daily.
  - You will only lose the ability to retrain custom wake-word models from scratch.
- **System Issues & OS Breakage**:
  - 🟢 **SAFE**: Completely safe to remove if you are not retraining wake words.

---

## 4. What Happens If You Remove Specific Packages? (Troubleshooting Scenarios)

### Scenario 1: "I want to save maximum RAM and Disk Space"
- **What to remove/disable**:
  1. Voice Cloning dependencies (`f5-tts`, `torch`, `torchaudio`): **Saves ~4.5 GB disk, ~2 GB RAM**.
     - *Result*: Nexovian automatically switches to the lightweight 15 MB **Robotic Voice**.
  2. Wake Word Training tools (`scikit-learn`, `skl2onnx`, `onnx`): **Saves ~1 GB disk**.
     - *Result*: Nexovian still detects wake words using the existing `nexovian.onnx` model.
  3. Stop Ollama when not in use:
     ```bash
     systemctl --user stop app-nexovian@autostart.service
     sudo systemctl stop ollama
     ```
     - *Result*: **Frees 8 GB+ RAM / VRAM immediately**.

### Scenario 2: "I only want Typed Input (Bottom Bar), NO Voice / Microphone"
- **What to remove/disable**:
  - You can remove `openwakeword`, `pyaudio`, `SpeechRecognition`, `vosk`, and `sounddevice`.
  - In `audio_engine.py`, disable `listen_for_wakeword`.
  - *Result*: Nexovian runs strictly as a Raycast-like floating assistant (`Ctrl+Space`). Microphone access is completely disabled.

### Scenario 3: "I accidentally ran `sudo apt remove python3-gi`"
- **System Disaster**:
  - Your GNOME display manager and Ubuntu desktop UI will fail to start on next boot.
- **Emergency Fix**:
  - Switch to a TTY terminal (`Ctrl+Alt+F3`), log in, and run:
    ```bash
    sudo apt-get update
    sudo apt-get install -y ubuntu-desktop python3-gi gir1.2-gtk-3.0 python3-dbus
    sudo systemctl restart gdm3
    ```

---

## 5. Safe Modular Installation Reference

If you wish to reinstall only the **essential runtime** without the heavy training and cloning extras:

```bash
# 1. Essential System Packages (Required for GUI, Audio & DBus)
sudo apt-get install -y \
  python3-dbus python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
  espeak espeak-ng portaudio19-dev python3-pip python3-numpy \
  python3-pyaudio python3-pynput alsa-utils poppler-utils

# 2. Minimal Runtime Python Packages (Lightweight: < 350 MB)
pip3 install --user --break-system-packages \
  openwakeword onnxruntime SpeechRecognition \
  pyautogui requests pyttsx3 numpy pynput

# 3. Heavy Optional Packages (Omit unless specifically needed):
---

## 6. How to Re-enable and Reuse Optional Modules in the Future

All classes, provider interfaces, and training scripts remain **100% intact in the codebase**. If you ever decide to bring back neural voice cloning or custom wake-word training, you do **not** need to modify any code. Simply install the packages and Nexovian will automatically detect them:

### 1. Re-enabling Neural Voice Cloning (F5-TTS)
```bash
# 1. Install PyTorch & F5-TTS
pip3 install --user --break-system-packages f5-tts torch torchaudio soundfile

# 2. Record or verify your 10-second reference sample (if not already done)
python3 scripts/record_voice_sample.py

# 3. Switch active TTS engine in ~/.config/nexovian/config.json
# Set "tts_engine": "cloned"
```
*Nexovian's `ClonedVoiceProvider` in `providers/tts.py` will dynamically detect the installed libraries on next launch and start speaking in your cloned voice.*

### 2. Re-enabling Custom Wake-Word Model Retraining
```bash
# 1. Install ONNX export tools
pip3 install --user --break-system-packages onnx skl2onnx

# 2. Run the synthetic acoustic trainer
python3 scripts/train_wakeword.py models/nexovian.onnx

# 3. Test detection accuracy
python3 scripts/test_wakeword.py --eval
```

---
*Document generated for Nexovian AI Agent (v1.5.0).*
