#!/bin/bash

echo "Installing system dependencies..."
sudo apt-get update || true
sudo apt-get install -y python3-dbus python3-gi python3-gi-cairo gir1.2-gtk-3.0 espeak espeak-ng portaudio19-dev python3-pip python3-numpy python3-pyaudio python3-sounddevice python3-pynput python3-venv python3-tk alsa-utils poppler-utils unzip wget || true

echo "Installing Python packages..."
# Use --break-system-packages for Ubuntu 24.04/26.04 compatibility if not in a venv.
pip3 install --break-system-packages --user pyttsx3 openwakeword onnxruntime scipy scikit-learn onnx skl2onnx sounddevice SpeechRecognition pyaudio pyautogui ollama requests pynput numpy || pip3 install --user pyttsx3 openwakeword onnxruntime scipy scikit-learn onnx skl2onnx sounddevice SpeechRecognition pyaudio pyautogui ollama requests pynput numpy

# Install Ollama if not installed
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "Pulling qwen3.5:9b model..."
ollama pull qwen3.5:9b || echo "Warning: Failed to pull qwen3.5:9b. Please verify the model name."

echo "Setting up Nexovian openWakeWord model..."
MODEL_DIR="$HOME/.local/share/nexovian/models"
mkdir -p "$MODEL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/models/nexovian.onnx" ]; then
    cp "$SCRIPT_DIR/models/nexovian.onnx" "$MODEL_DIR/"
    echo "Copied nexovian.onnx model to $MODEL_DIR/"
else
    echo "Training custom nexovian.onnx model..."
    python3 "$SCRIPT_DIR/scripts/train_wakeword.py" "$MODEL_DIR/nexovian.onnx"
fi

echo "Configuring GNOME global shortcuts and D-Bus services..."
mkdir -p "$HOME/.local/share/dbus-1/services"
cat << EOF > "$HOME/.local/share/dbus-1/services/org.nexovian.Agent.service"
[D-BUS Service]
Name=org.nexovian.Agent
Exec=/usr/bin/python3 $SCRIPT_DIR/nexovian.py
EOF

mkdir -p "$HOME/.config/autostart" "$HOME/.local/share/applications"
if [ -f "$SCRIPT_DIR/nexovian.desktop" ]; then
    cp "$SCRIPT_DIR/nexovian.desktop" "$HOME/.config/autostart/"
    cp "$SCRIPT_DIR/nexovian.desktop" "$HOME/.local/share/applications/"
fi

# GNOME Keybinding and IBus trigger resolution
if command -v gsettings &> /dev/null; then
    # Unbind Control+space from ibus trigger if present
    python3 -c "import ast, subprocess; res = subprocess.run(['gsettings', 'get', 'org.freedesktop.ibus.general.hotkey', 'trigger'], capture_output=True, text=True); t = [x for x in ast.literal_eval(res.stdout.strip()) if x != 'Control+space'] if res.returncode == 0 and 'Control+space' in res.stdout else None; subprocess.run(['gsettings', 'set', 'org.freedesktop.ibus.general.hotkey', 'trigger', str(t)]) if t is not None else None" 2>/dev/null || true

    # Configure GNOME custom keybinding
    KEY_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/nexovian/"
    python3 -c "import ast, subprocess; res = subprocess.run(['gsettings', 'get', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings'], capture_output=True, text=True); val = res.stdout.strip(); b = [] if val.startswith('@as') else ast.literal_eval(val); (b.append('$KEY_PATH'), subprocess.run(['gsettings', 'set', 'org.gnome.settings-daemon.plugins.media-keys', 'custom-keybindings', str(b)])) if '$KEY_PATH' not in b else None" 2>/dev/null || true
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH name 'Nexovian Toggle' 2>/dev/null || true
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH command 'gdbus call --session --dest org.nexovian.Agent --object-path /org/nexovian/Agent --method org.nexovian.Agent.ToggleBar' 2>/dev/null || true
    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$KEY_PATH binding '<Control>space' 2>/dev/null || true
fi

echo "Installation complete!"
