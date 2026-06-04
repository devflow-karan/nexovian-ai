#!/bin/bash

echo "Installing system dependencies..."
sudo apt-get update || true
sudo apt-get install -y python3-dbus python3-gi python3-gi-cairo gir1.2-gtk-3.0 espeak portaudio19-dev python3-pip unzip wget wget2 || true
# wget2 might not exist on older systems, fallback to wget

echo "Installing Python packages..."
# Use --break-system-packages for Ubuntu 24.04 compatibility or use a venv. We'll install to user directory.
pip3 install --user dbus-python PyGObject pyttsx3 vosk sounddevice SpeechRecognition pyaudio openwakeword pyautogui ollama requests pynput || pip3 install --break-system-packages --user dbus-python PyGObject pyttsx3 vosk sounddevice SpeechRecognition pyaudio openwakeword pyautogui ollama requests pynput

# Install Ollama if not installed
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "Pulling qwen3:8b model (as requested by user)..."
ollama pull qwen3:8b || echo "Warning: Failed to pull qwen3:8b. Please verify the model name."

echo "Downloading Vosk model..."
MODEL_DIR="$HOME/.local/share/vosk-models"
mkdir -p "$MODEL_DIR"

if [ ! -d "$MODEL_DIR/vosk-model-small-en-us-0.15" ]; then
    echo "Downloading vosk-model-small-en-us-0.15..."
    wget -qO /tmp/vosk-model.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    echo "Extracting model..."
    unzip -q /tmp/vosk-model.zip -d "$MODEL_DIR"
    rm /tmp/vosk-model.zip
else
    echo "Model already downloaded."
fi

echo "Installation complete!"
