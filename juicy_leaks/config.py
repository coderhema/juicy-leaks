"""Runtime configuration. Everything can be overridden with env vars or a .env file."""
from __future__ import annotations

import os

# Back-compat: the project used to be called GuardRail Lens; honour old GUARDRAIL_* env vars.
for _k, _v in list(os.environ.items()):
    if _k.startswith("GUARDRAIL_"):
        os.environ.setdefault("JUICY_" + _k[len("GUARDRAIL_"):], _v)
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv is optional at runtime
    pass

# All providers speak the OpenAI-compatible chat completions API.
PROVIDERS = {
    # meta/llama-3.3-70b-instruct reached end of life on NIM (2026-08-26); Meta's Muse Glimmer
    # is the Meta chat model NIM serves now. It reasons before answering, so we ask for low effort.
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1",
               "model": "meta/muse-glimmer-30b", "key_env": "NVIDIA_API_KEY",
               "extra_body": {"reasoning_effort": "low"}},
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
    extra_body: dict | None = None

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
        default_model = model or os.environ.get("JUICY_MODEL") or p["model"]
        env_mock = os.environ.get("JUICY_MOCK", "").lower() in {"1", "true", "yes"}
        if mock is None:
            # No key -> fall back to offline mock mode instead of crashing.
            mock = env_mock or not api_key
        return cls(
            provider=provider,
            api_key=api_key,
            base_url=(base_url or os.environ.get("LLM_BASE_URL") or p["base_url"]).rstrip("/"),
            target_model=os.environ.get("JUICY_TARGET_MODEL") or default_model,
            attacker_model=os.environ.get("JUICY_ATTACKER_MODEL") or default_model,
            judge_model=os.environ.get("JUICY_JUDGE_MODEL") or default_model,
            mock=mock,
            extra_body=None if os.environ.get("JUICY_REASONING_EFFORT") == "off" else (
                {"reasoning_effort": os.environ["JUICY_REASONING_EFFORT"]}
                if os.environ.get("JUICY_REASONING_EFFORT") else p.get("extra_body")),
        )
