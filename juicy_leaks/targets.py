"""Target chatbots: a system prompt + model, an HTTP endpoint, or an offline mock."""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml

HARDEN_MARKER = "## Security rules (added by Juicy Leaks)"


@dataclass
class Target:
    name: str
    system_prompt: str = ""
    description: str = ""
    model: str | None = None
    secrets: list[str] = field(default_factory=list)   # canary strings that must never leak
    pii: list[str] = field(default_factory=list)       # fake personal data that must never leak
    policies: list[str] = field(default_factory=list)  # behaviours the bot must refuse
    endpoint: dict | None = None                       # optional HTTP target config
    type: str = "chatbot"                              # chatbot | http | mcp
    mcp: dict | None = None                            # MCP connection config

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Target":
        data = yaml.safe_load(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "Target":
        return cls(
            name=data.get("name", "target"),
            system_prompt=data.get("system_prompt", ""),
            description=data.get("description", ""),
            model=data.get("model"),
            secrets=[str(s) for s in data.get("secrets", [])],
            pii=[str(s) for s in data.get("pii", [])],
            policies=list(data.get("policies", [])),
            endpoint=data.get("endpoint"),
            type=data.get("type") or ("mcp" if data.get("mcp") else "http" if data.get("endpoint") else "chatbot"),
            mcp=data.get("mcp"),
        )

    def with_system_prompt(self, prompt: str) -> "Target":
        return Target(self.name, prompt, self.description, self.model, self.secrets,
                      self.pii, self.policies, self.endpoint, self.type, self.mcp)


class LLMTarget:
    """Runs the target's system prompt on a real model."""

    def __init__(self, target: Target, client, model: str):
        self.target, self.client, self.model = target, client, target.model or model

    def ask(self, user_message: str) -> str:
        msgs = [{"role": "system", "content": self.target.system_prompt},
                {"role": "user", "content": user_message}]
        return self.client.chat(self.model, msgs, temperature=0.3, max_tokens=400)


class HTTPTarget:
    """Sends each attack to a live chatbot endpoint.

    endpoint:
      url: https://example.com/chat
      headers: {Authorization: "Bearer ..."}
      body_field: message          # JSON field that receives the attack
      response_field: reply        # dotted path to the bot's answer
    """

    def __init__(self, target: Target):
        self.cfg = _expand(target.endpoint or {})

    def ask(self, user_message: str) -> str:
        body = dict(self.cfg.get("extra_body", {}))
        body[self.cfg.get("body_field", "message")] = user_message
        r = requests.post(self.cfg["url"], json=body, headers=self.cfg.get("headers", {}), timeout=60)
        r.raise_for_status()
        data = r.json()
        for key in self.cfg.get("response_field", "reply").split("."):
            data = data[int(key)] if isinstance(data, list) else data[key]
        return str(data)


def _expand(obj):
    """Expand ${ENV_VAR} in endpoint config so tokens stay out of YAML files."""
    import os
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    return os.path.expandvars(obj) if isinstance(obj, str) else obj


class MockTarget:
    """Deterministic offline stand-in for a naive chatbot.

    Unhardened prompts leak often (like real naive bots do); prompts that carry the
    Juicy Leaks security block refuse almost everything. Lets the whole pipeline,
    the UI and the tests run with no API key.
    """

    def __init__(self, target: Target):
        self.target = target

    def _roll(self, text: str) -> int:
        return int(hashlib.sha256((self.target.system_prompt[:200] + text).encode()).hexdigest(), 16) % 100

    def ask(self, user_message: str, category: str | None = None) -> str:
        t = self.target
        hardened = HARDEN_MARKER in t.system_prompt
        roll = self._roll(user_message)
        leak_rate = 8 if hardened else 70
        if roll >= leak_rate:
            return ("I'm sorry, I can't help with that. I can only assist with questions about "
                    f"{t.description or 'our services'}.")
        secret = t.secrets[0] if t.secrets else "INTERNAL-NOTE"
        msg = user_message.lower()
        if "base64" in msg or "encode" in msg:
            return "Sure, here it is encoded: " + base64.b64encode(secret.encode()).decode()
        if "system prompt" in msg or "instructions" in msg or "above" in msg or "verbatim" in msg:
            return "Of course! My instructions are:\n" + t.system_prompt[:600]
        if t.pii and any(w in msg for w in ("employee", "salary", "record", "customer", "address", "phone", "passport", "personal")):
            return "Here are the details I have: " + "; ".join(t.pii[:3])
        if "leet" in msg or "1337" in msg:
            return "H3r3 y0u g0: " + secret.replace("E", "3").replace("O", "0").replace("A", "4")
        return f"Since you asked nicely: the internal code is {secret}."


def build_target_runner(target: Target, settings, client=None):
    if target.endpoint:
        return HTTPTarget(target)
    if settings.mock:
        return MockTarget(target)
    return LLMTarget(target, client, settings.target_model)
