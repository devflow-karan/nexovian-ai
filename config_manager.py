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
    # Provide an exhaustive list of known phonetic misinterpretations from the Vosk lightweight model
    default_words = [
        "nexovian", "nexo", "neck so", "next oh", "next so", "neck so the end", "next oh the end",
        "come on agent", "come on a agent", "come on a don't", 
        "come on a and", "come on a dent", "come on his hand", 
        "gone in and", "come on i didn't", "come on isn't", "hello isn't"
    ]
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

def use_gemini_brain():
    config = load_config()
    has_key = bool(config.get("gemini_api_key"))
    return config.get("use_gemini_brain", has_key)
