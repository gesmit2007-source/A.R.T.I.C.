"""Engine-agnostic LLM layer. Memory lives in the vault, so engines are swappable."""
from __future__ import annotations
import json
import os
import urllib.request


class Engine:
    name = "base"

    def complete(self, system: str, messages: list[dict]) -> str:
        raise NotImplementedError


def _post(url: str, headers: dict, payload: dict) -> dict:
    timeout = float(os.environ.get("ARTIC_TIMEOUT", "600"))
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class AnthropicEngine(Engine):
    name = "anthropic"

    def __init__(self):
        self.key = os.environ["ARTIC_API_KEY"]
        self.model = os.environ.get("ARTIC_MODEL", "claude-sonnet-5-5")

    def complete(self, system, messages):
        d = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                  {"model": self.model, "max_tokens": 2000, "system": system, "messages": messages})
        return "".join(b.get("text", "") for b in d["content"])


class OpenAICompatEngine(Engine):
    """OpenAI, Ollama, LM Studio, vLLM, llama.cpp server... anything with /v1/chat/completions."""
    name = "openai"

    def __init__(self):
        self.base = os.environ.get("ARTIC_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.key = os.environ.get("ARTIC_API_KEY", "none")
        self.model = os.environ.get("ARTIC_MODEL", "qwen3.5:4b")

    def complete(self, system, messages):
        payload = {"model": self.model, "max_tokens": int(os.environ.get("ARTIC_MAX_TOKENS", "800")),
                   "messages": [{"role": "system", "content": system}, *messages]}
        effort = os.environ.get("ARTIC_REASONING_EFFORT", "none")
        if effort:
            payload["reasoning_effort"] = effort
        d = _post(f"{self.base}/chat/completions", {"Authorization": f"Bearer {self.key}"}, payload)
        return d["choices"][0]["message"]["content"]


class EchoEngine(Engine):
    """Offline engine for tests and demos."""
    name = "echo"

    def complete(self, system, messages):
        last = messages[-1]["content"]
        if "Return ONLY JSON" in system and "dreaming" in system:
            return json.dumps({"title": "Synthesis", "insight": "Notes appear related.", "tags": ["dream"], "links": []})
        if "Return ONLY JSON" in system:
            words = [w for w in last.split() if w.isalpha() and len(w) > 4][:3] or ["thought"]
            return json.dumps({"title": " ".join(words).title(), "summary": f"Discussed: {last[:200]}",
                               "tags": [words[0].lower()], "links": []})
        return f"(echo engine) I heard: {last[:200]}"


def make_engine(name: str | None = None) -> Engine:
    name = (name or os.environ.get("ARTIC_ENGINE", "openai")).lower()
    return {"anthropic": AnthropicEngine, "openai": OpenAICompatEngine, "echo": EchoEngine}[name]()
