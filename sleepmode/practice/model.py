"""OpenAI-compatible chat client (stdlib) and a FakeModel for tests."""
from __future__ import annotations

import json
import re
import urllib.request

_THINK = re.compile(r"<think>.*?</think>", re.S)


class ModelError(RuntimeError):
    pass


def strip_think(text: str) -> str:
    text = _THINK.sub("", text or "")
    if "</think>" in text:  # reply started mid-thought
        text = text.split("</think>")[-1]
    if "<think>" in text:  # never closed
        text = text.split("<think>")[0]
    return text.strip()


def _endpoint(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"


class ChatModel:
    def __init__(self, url: str, model: str, api_key: str | None = None, timeout: float = 300.0):
        self.url, self.model, self.api_key, self.timeout = _endpoint(url), model, api_key, timeout

    def chat(self, messages, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        body = json.dumps({"model": self.model, "messages": messages, "max_tokens": max_tokens,
                           "temperature": temperature, "stream": False}).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        last = None
        for _ in range(2):  # one retry
            try:
                req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8", "replace"))
                return strip_think(data["choices"][0]["message"]["content"] or "")
            except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
                last = e
        raise ModelError("chat failed: %r" % (last,))


class FakeModel:
    """fn(messages) -> reply text (or fn(messages, max_tokens=, temperature=))."""

    def __init__(self, fn):
        self.fn, self.calls = fn, []

    def chat(self, messages, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        self.calls.append(messages)
        return strip_think(str(self.fn(messages)))
