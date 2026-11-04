"""Runtime configuration. Everything can be overridden with env vars or a .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv is optional at runtime
    pass

# All providers speak the OpenAI-compatible chat completions API.
PROVIDERS = {
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1",
               "model": "meta/llama-3.3-70b-instruct", "key_env": "NVIDIA_API_KEY"},
    "groq": {"base_url": "https://api.groq.com/openai/v1",
             "model": "llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY"},
    # any other OpenAI-compatible endpoint (Meta Llama API, OpenRouter, Together, local vLLM...)
    "custom": {"base_url": "", "model": "", "key_env": "LLM_API_KEY"},
}
DEFAULT_PROVIDER = "nvidia"


@dataclass
class Settings:
    provider: str
    api_key: str | None
    base_url: str
    target_model: str
    attacker_model: str
    judge_model: str
    mock: bool

    @property
    def key_env(self) -> str:
        return PROVIDERS[self.provider]["key_env"]

    @classmethod
    def load(cls, mock: bool | None = None, model: str | None = None,
             base_url: str | None = None, provider: str | None = None) -> "Settings":
        provider = (provider or os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER)).lower()
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}")
        p = PROVIDERS[provider]
        api_key = os.environ.get(p["key_env"]) or os.environ.get("LLM_API_KEY")
        default_model = model or os.environ.get("GUARDRAIL_MODEL") or p["model"]
        env_mock = os.environ.get("GUARDRAIL_MOCK", "").lower() in {"1", "true", "yes"}
        if mock is None:
            # No key -> fall back to offline mock mode instead of crashing.
            mock = env_mock or not api_key
        return cls(
            provider=provider,
            api_key=api_key,
            base_url=(base_url or os.environ.get("LLM_BASE_URL") or p["base_url"]).rstrip("/"),
            target_model=os.environ.get("GUARDRAIL_TARGET_MODEL") or default_model,
            attacker_model=os.environ.get("GUARDRAIL_ATTACKER_MODEL") or default_model,
            judge_model=os.environ.get("GUARDRAIL_JUDGE_MODEL") or default_model,
            mock=mock,
        )
