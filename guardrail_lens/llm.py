"""Minimal OpenAI-compatible chat client (Groq, Meta Llama API, OpenRouter, ...)."""
from __future__ import annotations

import time

import requests


class LLMError(RuntimeError):
    pass


class ChatClient:
    def __init__(self, api_key: str, base_url: str, timeout: int = 60, max_retries: int = 5):
        if not api_key:
            raise LLMError("No API key. Set NVIDIA_API_KEY (or GROQ_API_KEY with LLM_PROVIDER=groq) in .env or run with --mock.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def chat(self, model: str, messages: list[dict], temperature: float = 0.7,
             max_tokens: int = 512, json_mode: bool = False) -> str:
        payload = {"model": model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                                  headers=headers, timeout=self.timeout)
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise LLMError(str(e)) from e
                time.sleep(delay)
                delay *= 2
                continue
            if r.status_code == 429 or r.status_code >= 500:
                wait = float(r.headers.get("retry-after", delay) or delay)
                time.sleep(min(wait, 30))
                delay *= 2
                continue
            if r.status_code == 400 and "response_format" in payload:
                payload.pop("response_format")  # some providers reject JSON mode; prompt asks for JSON anyway
                continue
            if r.status_code >= 400:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            return r.json()["choices"][0]["message"]["content"] or ""
        raise LLMError("Exceeded retries (rate limited?)")
