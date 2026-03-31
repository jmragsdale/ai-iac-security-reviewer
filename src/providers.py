"""
LLM provider abstraction layer.
Supports local LM Studio, OpenAI, and Anthropic with a unified interface.
"""

import json
import os
import requests
from typing import Optional


class LLMProvider:
    """Base class for LLM providers."""

    def chat(self, system_prompt: str, user_message: str) -> str:
        raise NotImplementedError


class LocalProvider(LLMProvider):
    """LM Studio local server (OpenAI-compatible API). No data leaves the machine."""

    def __init__(self, base_url: str = "http://localhost:1234/v1", model: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.model = model or self._detect_model()

    def _detect_model(self) -> str:
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            resp.raise_for_status()
            models = resp.json().get("data", [])
            if not models:
                raise RuntimeError("No model loaded in LM Studio. Load a model and start the server.")
            model_id = models[0]["id"]
            print(f"[+] LM Studio  |  model: {model_id}  |  zero data exfiltration")
            return model_id
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Cannot connect to LM Studio at http://localhost:1234\n"
                "Start LM Studio, load a model, and enable the Local Server."
            )

    def chat(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 3000,
        }
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


class OpenAIProvider(LLMProvider):
    """OpenAI API (gpt-4o recommended)."""

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set OPENAI_API_KEY environment variable.")
        print(f"[+] OpenAI  |  model: {self.model}")

    def chat(self, system_prompt: str, user_message: str) -> str:
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"].strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set ANTHROPIC_API_KEY environment variable.")
        print(f"[+] Anthropic  |  model: {self.model}")

    def chat(self, system_prompt: str, user_message: str) -> str:
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 3000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["content"][0]["text"].strip()


def get_provider(name: str, **kwargs) -> LLMProvider:
    providers = {
        "local":     LocalProvider,
        "openai":    OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    if name not in providers:
        raise ValueError(f"Unknown provider '{name}'. Choose: {', '.join(providers)}")
    return providers[name](**kwargs)
