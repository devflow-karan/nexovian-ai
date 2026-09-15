import os
import json

CONFIG_FILE = os.path.expanduser("~/.config/nexovian/config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_user_name():
    config = load_config()
    return config.get("name")

def set_user_name(name):
    config = load_config()
    config["name"] = name
    save_config(config)

def get_wake_words():
    config = load_config()
    default_words = ["nexovian", "nexo"]
    return config.get("wake_words", default_words)

def set_wake_words(words_list):
    config = load_config()
    config["wake_words"] = [w.lower() for w in words_list]
    save_config(config)

def get_gemini_api_key():
    config = load_config()
    return config.get("gemini_api_key")

def set_gemini_api_key(key):
    config = load_config()
    config["gemini_api_key"] = key
    save_config(config)

def get_llm_provider():
    config = load_config()
    return config.get("llm_provider", "ollama")

def set_llm_provider(provider):
    config = load_config()
    config["llm_provider"] = provider.lower()
    save_config(config)

def use_gemini_brain():
    config = load_config()
    # Explicit opt-in only: must have both llm_provider == 'gemini' and an api key
    return config.get("llm_provider") == "gemini" and bool(config.get("gemini_api_key"))

def use_robotic_voice():
    config = load_config()
    return config.get("use_robotic_voice", True)

def get_projects_dir():
    config = load_config()
    configured = config.get("projects_dir")
    if configured:
        expanded = os.path.normpath(os.path.expanduser(configured))
        os.makedirs(expanded, exist_ok=True)
        return expanded

    from datetime import datetime
    year = str(datetime.now().year)

    # If ~/data exists (user's workspace pattern), prefer ~/data/projects/<year>
    user_data_dir = os.path.expanduser("~/data")
    if os.path.exists(user_data_dir):
        p = os.path.join(user_data_dir, "projects", year)
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            pass

    candidates = [
        os.path.expanduser(f"~/Projects/{year}"),
        os.path.expanduser(f"~/Documents/Projects/{year}"),
    ]
    for c in candidates:
        if os.path.exists(os.path.dirname(c)) or os.path.exists(c):
            try:
                os.makedirs(c, exist_ok=True)
                return c
            except Exception:
                pass

    # Default fallback
    fallback = os.path.expanduser(f"~/Documents/Projects/{year}")
    try:
        os.makedirs(fallback, exist_ok=True)
    except Exception:
        fallback = os.path.expanduser("~/Documents")
    return fallback

def set_projects_dir(path):
    config = load_config()
    config["projects_dir"] = path
    save_config(config)

def get_vosk_model_path():
    config = load_config()
    configured = config.get("vosk_model_path")
    if configured and os.path.exists(os.path.expanduser(configured)):
        return os.path.expanduser(configured)

    env_path = os.environ.get("VOSK_MODEL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    base_dir = os.path.expanduser("~/.local/share/vosk-models")
    preferred = os.path.join(base_dir, "vosk-model-small-en-us-0.15")
    if os.path.exists(preferred):
        return preferred

    # Dynamically find any model inside vosk-models
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            full_p = os.path.join(base_dir, entry)
            if os.path.isdir(full_p) and (os.path.exists(os.path.join(full_p, "am")) or os.path.exists(os.path.join(full_p, "conf"))):
                return full_p

    return preferred

def get_tasks_file():
    config = load_config()
    configured = config.get("tasks_file")
    if configured:
        return os.path.expanduser(configured)
    return os.path.expanduser("~/Documents/tasks.json")

def get_ollama_host():
    config = load_config()
    return config.get("ollama_host") or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

def get_enable_thinking():
    config = load_config()
    return config.get("enable_thinking", False)

def set_enable_thinking(enabled: bool):
    config = load_config()
    config["enable_thinking"] = bool(enabled)
    save_config(config)

def get_wakeword_model_path():
    config = load_config()
    configured = config.get("wakeword_model_path")
    if configured and os.path.exists(os.path.expanduser(configured)):
        return os.path.expanduser(configured)

    env_path = os.environ.get("WAKEWORD_MODEL_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # Check project models/ directory
    local_model = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "nexovian.onnx")
    if os.path.exists(local_model):
        return local_model

    # Check user data directory
    user_model = os.path.expanduser("~/.local/share/nexovian/models/nexovian.onnx")
    if os.path.exists(user_model):
        return user_model

    return None

def set_wakeword_model_path(path):
    config = load_config()
    config["wakeword_model_path"] = path
    save_config(config)

def get_wakeword_threshold():
    config = load_config()
    return float(config.get("wakeword_threshold", 0.5))

def set_wakeword_threshold(val):
    config = load_config()
    config["wakeword_threshold"] = float(val)
    save_config(config)

def get_vision_provider():
    config = load_config()
    return config.get("vision_provider", "ollama")

def set_vision_provider(provider):
    config = load_config()
    config["vision_provider"] = provider.lower()
    save_config(config)

def get_vision_model():
    config = load_config()
    return config.get("vision_model", "moondream")

def set_vision_model(model):
    config = load_config()
    config["vision_model"] = model
    save_config(config)

def get_stt_provider():
    config = load_config()
    return config.get("stt_provider", "vosk")

def set_stt_provider(provider):
    config = load_config()
    config["stt_provider"] = provider.lower()
    save_config(config)

def get_tts_engine():
    config = load_config()
    return config.get("tts_engine", "cloned")

def set_tts_engine(engine):
    config = load_config()
    config["tts_engine"] = engine.lower()
    save_config(config)

def get_voice_reference_path():
    config = load_config()
    configured = config.get("voice_reference_path")
    if configured and os.path.exists(os.path.expanduser(configured)):
        return os.path.expanduser(configured)
    return os.path.expanduser("~/.config/nexovian/voice_reference.wav")

def set_voice_reference_path(path):
    config = load_config()
    config["voice_reference_path"] = path
    save_config(config)

