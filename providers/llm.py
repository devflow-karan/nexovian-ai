"""
providers/llm.py
Concrete implementations of LLMProvider for Ollama and Gemini.
"""

import requests
import json
import os
from datetime import datetime
from typing import Any, Tuple, Optional

from providers.base import LLMProvider
import config_manager

PREFERRED_MODEL = "qwen3.5:9b"

_MODEL_FALLBACK_CHAIN = [
    "qwen3.5:9b",
    "qwen3.5",
    "qwen3:8b",
    "qwen2.5:8b",
    "qwen2.5:7b",
    "qwen2.5:3b",
    "qwen2.5:1.5b",
    "qwen2.5:0.5b",
    "llama3.2:latest",
    "llama3.2",
    "llama3.2:3b",
    "llama3.2:1b",
    "llama3.1:8b",
    "llama3.1",
    "llama3:latest",
    "llama3",
    "mistral:latest",
    "mistral",
    "gemma:latest",
    "gemma",
]


class OllamaProvider(LLMProvider):
    """Primary local LLM provider connecting to local Ollama daemon."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self._model_name: Optional[str] = None

    @property
    def name(self) -> str:
        return "ollama"

    def get_ollama_url(self) -> str:
        host = config_manager.get_ollama_host().rstrip("/")
        return f"{host}/api/generate"

    def get_ollama_tags_url(self) -> str:
        host = config_manager.get_ollama_host().rstrip("/")
        return f"{host}/api/tags"

    def resolve_model(self) -> str:
        """Query Ollama daemon for installed models and select best match."""
        if self._model_name:
            return self._model_name

        try:
            resp = requests.get(self.get_ollama_tags_url(), timeout=5)
            if resp.status_code == 200:
                installed = [m["name"] for m in resp.json().get("models", [])]
                if not installed:
                    self._model_name = PREFERRED_MODEL
                    return self._model_name

                for candidate in _MODEL_FALLBACK_CHAIN:
                    for inst in installed:
                        if inst == candidate or inst == f"{candidate}:latest" or candidate == f"{inst}:latest":
                            self._model_name = inst
                            return self._model_name

                self._model_name = installed[0]
                return self._model_name
        except Exception:
            pass

        self._model_name = PREFERRED_MODEL
        return self._model_name

    def generate_response(self, prompt: str, context: Any = None) -> Tuple[str, Any]:
        model = self.resolve_model()
        now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        system_prompt_with_time = (
            f"{self.system_prompt}\n\nCurrent System Time: {now_str}\n"
            "Use this exact current time to interpret phrases like 'today', 'tomorrow', 'in 5 minutes', or 'at 11am'."
        )

        payload = {
            "model": model,
            "prompt": f"{system_prompt_with_time}\n\nUser: {prompt}\nNexovian:",
            "stream": False,
            "think": config_manager.get_enable_thinking(),
            "options": {
                "num_predict": 150
            }
        }

        if context and isinstance(context, list) and all(isinstance(x, int) for x in context):
            payload["context"] = context

        try:
            response = requests.post(self.get_ollama_url(), json=payload, timeout=300)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", ""), data.get("context", [])
            elif response.status_code == 404:
                return (
                    f"Model '{model}' is not available in Ollama. Run: ollama pull {model}",
                    context
                )
            else:
                return f"Error: Ollama returned status {response.status_code}", context
        except requests.exceptions.ConnectionError:
            return "Cannot reach Ollama. Make sure it is running: ollama serve", context
        except Exception as e:
            return f"Error communicating with local AI: {str(e)}", context


class GeminiProvider(LLMProvider):
    """Optional legacy cloud LLM provider connecting to Google Gemini API."""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    @property
    def name(self) -> str:
        return "gemini"

    def generate_response(self, prompt: str, context: Any = None) -> Tuple[str, Any]:
        api_key = config_manager.get_gemini_api_key()
        if not api_key:
            return "Gemini API key is not configured.", context

        now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
        system_prompt_with_time = (
            f"{self.system_prompt}\n\nCurrent System Time: {now_str}\n"
            "Use this exact current time to interpret phrases like 'today', 'tomorrow', 'in 5 minutes', or 'at 11am'."
        )

        if not isinstance(context, list):
            context = []

        new_context = list(context)
        new_context.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": new_context,
            "systemInstruction": {
                "parts": [{"text": system_prompt_with_time}]
            }
        }

        gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        last_error = ""

        for model in gemini_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text_content:
                            new_context.append({
                                "role": "model",
                                "parts": [{"text": text_content}]
                            })
                            return text_content, new_context
                    return "Gemini returned an empty response.", context
                else:
                    last_error = f"Gemini API returned error code {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = f"Error communicating with Gemini API: {str(e)}"

        return last_error, context
