"""
providers/vision.py
Concrete implementations of VisionProvider for local Ollama models and optional Gemini.
"""

import requests
import json
from typing import Optional

from providers.base import VisionProvider
import config_manager

PROMPT_TEMPLATE = (
    "You are a helpful desktop assistant. The user wants you to analyze their screen.\n"
    "User query: {instruction}\n\n"
    "Please provide your analysis in two sections exactly:\n"
    "Summary: A concise 1-2 sentence overview suitable for text-to-speech. Do not include asterisks or formatting symbols in the summary.\n"
    "Details: A thorough, detailed breakdown of everything on the screen, including text, open applications, and user interface elements."
)

def _format_vision_result(text_content: str) -> str:
    """Ensure output follows [SPOKEN]: summary [DISPLAY]: details format."""
    summary = ""
    details = ""

    if "Summary:" in text_content and "Details:" in text_content:
        try:
            summary = text_content.split("Summary:")[1].split("Details:")[0].strip()
            details = text_content.split("Details:")[1].strip()
        except Exception:
            pass

    if not summary or not details:
        summary = text_content[:150] + "..." if len(text_content) > 150 else text_content
        details = text_content

    summary = summary.replace("*", "").replace("#", "").strip()
    return f"[SPOKEN]: {summary} [DISPLAY]: {details}"


class OllamaVisionProvider(VisionProvider):
    """Local visual analysis using Ollama multimodal models (e.g., moondream, llava-phi3)."""

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "ollama_vision"

    def get_model(self) -> str:
        if self._model_name:
            return self._model_name
        config = config_manager.load_config()
        return config.get("vision_model", "moondream")

    def analyze_screen(self, img_base64: str, instruction: str = "Explain what is on the screen") -> str:
        model = self.get_model()
        host = config_manager.get_ollama_host().rstrip("/")
        url = f"{host}/api/generate"

        payload = {
            "model": model,
            "prompt": PROMPT_TEMPLATE.format(instruction=instruction),
            "images": [img_base64],
            "stream": False,
            "options": {
                "num_predict": 250
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=90)
            if resp.status_code == 200:
                data = resp.json()
                text_content = data.get("response", "").strip()
                if not text_content:
                    return "Local vision model returned an empty explanation."
                return _format_vision_result(text_content)
            elif resp.status_code == 404:
                return f"Local vision model '{model}' is not installed. Please run: ollama pull {model}"
            else:
                return f"Ollama vision request returned status code {resp.status_code}: {resp.text}"
        except requests.exceptions.ConnectionError:
            return "Cannot reach Ollama for screen analysis. Ensure Ollama is running."
        except Exception as e:
            return f"Error communicating with local vision model: {str(e)}"


class GeminiVisionProvider(VisionProvider):
    """Optional cloud visual analysis using Google Gemini API."""

    @property
    def name(self) -> str:
        return "gemini_vision"

    def analyze_screen(self, img_base64: str, instruction: str = "Explain what is on the screen") -> str:
        api_key = config_manager.get_gemini_api_key()
        if not api_key:
            return "Failed to read screen: Gemini API key not configured."

        headers = {"Content-Type": "application/json"}
        prompt_text = PROMPT_TEMPLATE.format(instruction=instruction)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": img_base64
                            }
                        }
                    ]
                }
            ]
        }

        gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        last_error_msg = ""

        for model in gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        return "Gemini API returned no analysis candidates."

                    text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if not text_content:
                        return "Gemini API returned empty explanation."

                    return _format_vision_result(text_content)
                else:
                    last_error_msg = f"Gemini API returned error code {resp.status_code}: {resp.text}"
            except requests.exceptions.Timeout:
                last_error_msg = "Gemini API request timed out."
            except Exception as e:
                last_error_msg = f"Error communicating with Gemini API: {str(e)}"

        return last_error_msg
