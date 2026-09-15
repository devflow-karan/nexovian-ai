"""
providers/__init__.py
Registry and factory accessors for Nexovian service providers.
"""

from typing import Optional

from providers.base import LLMProvider, VisionProvider, STTProvider, TTSProvider
from providers.llm import OllamaProvider, GeminiProvider
from providers.vision import OllamaVisionProvider, GeminiVisionProvider
from providers.stt import VoskSTTProvider, GoogleSTTProvider
from providers.tts import RoboticVoiceProvider, SystemVoiceProvider, ClonedVoiceProvider
import config_manager

_cached_llm: Optional[LLMProvider] = None
_cached_vision: Optional[VisionProvider] = None
_cached_stt: Optional[STTProvider] = None
_cached_tts: Optional[TTSProvider] = None

def get_llm_provider(system_prompt: str) -> LLMProvider:
    """Return configured LLMProvider (defaults to Ollama)."""
    global _cached_llm
    config = config_manager.load_config()
    provider_name = config.get("llm_provider", "ollama").lower()

    # If user explicitly opted into gemini and provided an api key, use Gemini
    if provider_name == "gemini" and config_manager.get_gemini_api_key():
        if _cached_llm is None or _cached_llm.name != "gemini":
            _cached_llm = GeminiProvider(system_prompt)
        return _cached_llm

    # Default to local Ollama
    if _cached_llm is None or _cached_llm.name != "ollama":
        _cached_llm = OllamaProvider(system_prompt)
    return _cached_llm


def get_vision_provider() -> VisionProvider:
    """Return configured VisionProvider (defaults to local Ollama vision)."""
    global _cached_vision
    config = config_manager.load_config()
    provider_name = config.get("vision_provider", "ollama").lower()

    if provider_name == "gemini" and config_manager.get_gemini_api_key():
        if _cached_vision is None or _cached_vision.name != "gemini_vision":
            _cached_vision = GeminiVisionProvider()
        return _cached_vision

    if _cached_vision is None or _cached_vision.name != "ollama_vision":
        _cached_vision = OllamaVisionProvider()
    return _cached_vision


def get_stt_provider() -> STTProvider:
    """Return configured STTProvider (defaults to local Vosk)."""
    global _cached_stt
    config = config_manager.load_config()
    provider_name = config.get("stt_provider", "vosk").lower()

    if provider_name == "google":
        if _cached_stt is None or _cached_stt.name != "google":
            _cached_stt = GoogleSTTProvider()
        return _cached_stt

    # Default to local offline Vosk
    if _cached_stt is None or _cached_stt.name != "vosk":
        _cached_stt = VoskSTTProvider()
    return _cached_stt


def get_tts_provider() -> TTSProvider:
    """Return configured TTSProvider (defaults to Cloned Voice with Robotic Fallback)."""
    global _cached_tts
    config = config_manager.load_config()
    engine_name = config.get("tts_engine", "cloned").lower()

    if engine_name == "robotic":
        if _cached_tts is None or _cached_tts.name != "robotic":
            _cached_tts = RoboticVoiceProvider()
        return _cached_tts
    elif engine_name == "system":
        if _cached_tts is None or _cached_tts.name != "system":
            _cached_tts = SystemVoiceProvider()
        return _cached_tts

    # Default to Cloned with automatic fallback to Robotic
    if _cached_tts is None or _cached_tts.name != "cloned":
        _cached_tts = ClonedVoiceProvider(fallback_provider=RoboticVoiceProvider())
    return _cached_tts
