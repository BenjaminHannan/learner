#!/usr/bin/env python3
"""rsn-299 layer for the joined agent: "think, then answer" on everyday reasoning questions.

install_think299(loop, model) wraps loop.turn. A turn goes to the think path only when ALL hold:
  - it is a question ("?" or a question word first);
  - it carries a reasoning signal: 2+ numbers, a clock time, a weekday with a number, or
    "how many" with a list of 3+ items or a quoted word;
  - it names nobody the notebook knows (those questions stay with the reader and reasoner);
  - it is not about the assistant itself ("you"/"your").
Everything else passes straight to the inner loop unchanged. A think turn is read-only: it never
writes the notebook (checked), and when the 1B gives no answer line the turn falls back to the
inner loop. The reply is the answer, then the worked steps with the calculator's exact results.

  model: a directory (loaded once, cached) or any object with .tok, .model, .dev (e.g. 333's Gen333)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn299_run as R  # noqa: E402

QWORD = re.compile(r"^\s*(how|what|when|which|who|where|is|are|can|do|does|will|should|if)\b", re.I)
NUMS = re.compile(r"\d+(?:[.,]\d+)?")
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b")
WEEKDAY = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
SELF = re.compile(r"\b(you|your|yourself)\b", re.I)
_MODELS: dict = {}


def _names(loop) -> set[str]:
    try:
        return {str(n).lower() for n in loop.nb.entities.values() if str(n).lower() not in ("user", "me")}
    except AttributeError:
        return set()


def is_reasoning(text: str, loop=None) -> bool:
    t = text.strip()
    if not t or SELF.search(t):
        return False
    if "?" not in t and not QWORD.search(t.split(".")[-1] if "." in t else t):
        return False
    low = t.lower()
    nums = NUMS.findall(t)
    signal = (len(nums) >= 2 or bool(CLOCK.search(t)) or (bool(WEEKDAY.search(t)) and len(nums) >= 1)
              or ("how many" in low and (t.count(",") >= 2 or bool(re.search(r"['\"]\w+['\"]", t)))))
    if not signal:
        return False
    if loop is not None:
        for n in _names(loop):
            if re.search(r"\b" + re.escape(n) + r"\b", low):
                return False
    return True


def _bundle(model):
    if hasattr(model, "tok") and hasattr(model, "model"):
        return model.tok, model.model, getattr(model, "dev", "cpu")
    if model not in _MODELS:
        _MODELS[model] = R.load(model)
    return _MODELS[model]


def render(steps: str) -> str | None:
    ans = R.answer_line(steps)
    if not ans:
        return None
    body = steps[:steps.rfind("Answer:")].strip()
    body = re.sub(r"<<([^<>]*)>>=(\S+?)([.,;]?)(?=\s|$)", r"\1 = \2\3", body)
    body = " ".join(line.strip() for line in body.splitlines() if line.strip())
    if R.UNSURE.search(ans):
        return f"I'm not sure. {body}".strip() if body else "I'm not sure."
    return f"{ans}. How I worked it out: {body}" if body else ans


def install_think299(loop, model) -> None:
    inner = loop.turn
    tok, mdl, dev = _bundle(model)
    gen = lambda text, mx, stops: R._gen(tok, mdl, dev, text, mx, stops)
    loop.think299_stats = {"think_turns": 0, "fallbacks": 0, "passed_through": 0}

    def turn299(text: str) -> list[str]:
        if not is_reasoning(text, loop):
            loop.think299_stats["passed_through"] += 1
            return inner(text)
        ev0 = len(loop.nb.events)
        steps, calls = R.solve("T", text, gen)
        reply = render(steps)
        if len(loop.nb.events) != ev0:
            raise RuntimeError("299: think turn wrote to the notebook")
        if reply is None:
            loop.think299_stats["fallbacks"] += 1
            return inner(text)
        loop.think299_stats["think_turns"] += 1
        loop.experience.append({"tick": loop.tick, "kind": "work", "phase": "think299",
                                "calls": len(calls)})
        return [reply]

    turn299.__name__ = "turn299"
    loop.turn = turn299
