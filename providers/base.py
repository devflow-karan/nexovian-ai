"""
providers/base.py
Abstract base classes defining the core service provider interfaces for Nexovian.
"""

from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

class LLMProvider(ABC):
    """Abstract interface for Large Language Model generation."""

    @abstractmethod
    def generate_response(self, prompt: str, context: Any = None) -> Tuple[str, Any]:
        """
        Generate a conversational response from the model.
        Returns (response_text, new_context).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass


class VisionProvider(ABC):
    """Abstract interface for desktop screenshot visual analysis."""

    @abstractmethod
    def analyze_screen(self, img_base64: str, instruction: str = "Explain what is on the screen") -> str:
        """
        Analyze a base64-encoded PNG screenshot.
        Returns a formatted string containing:
        '[SPOKEN]: {summary} [DISPLAY]: {details}'
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text transcription."""

    @abstractmethod
    def transcribe(self, recognizer: Any, audio_data: Any) -> str:
        """
        Transcribe an AudioData object into plain text.
        Returns recognized string (or empty string if nothing recognized).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech audio synthesis and playback."""

    @abstractmethod
    def speak(self, text: str) -> bool:
        """
        Synthesize text and play audio via PipeWire/paplay.
        Returns True on success, False otherwise.
        """
        pass

    @abstractmethod
    def cancel(self) -> None:
        """Immediately abort active playback."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass
