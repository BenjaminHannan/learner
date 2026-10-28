"""Check the night's dreams against the diary before training on them, with sleepmode's dream checker (sleepmode/dreamcheck.py).

The checker is a small tool-using agent (diary_search / diary_read; no web at night) that ends with VERDICT SUPPORTED | CONTRADICTED | UNKNOWN,
and SUPPORTED needs a quote that really is in a diary result. Here it runs on the trainer's own model in this process (the plain base, adapter
off), so no second server and no extra memory is needed.

Policy for a 1.7B checker (cards were already verified once from the chat text by the base model, so UNKNOWN is not a reason to drop):
    CONTRADICTED -> the card is dropped (its FIX is not trusted: a small model's correction is a new, unchecked claim)
    SUPPORTED / UNKNOWN / not reached in the time cap -> kept
The checker is found as the `sleepmode` package on sys.path, or in SLEEPMLX_DREAMCHECK_PATH (the folder that holds `sleepmode/`).
When it is not installed the night goes on without it and says so in its stats ("available": false).
"""
from __future__ import annotations

import hashlib
import importlib
import os
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence

MAX_TOKENS = 200      # per model turn of the checker
MAX_STEPS = 4         # tool turns per item


def load_checker(env=os.environ):
    """-> (dreamcheck module, ToolBox class) or (None, reason)."""
    extra = env.get("SLEEPMLX_DREAMCHECK_PATH")
    if extra:
        extra = os.path.expanduser(extra)
        if extra not in sys.path:
            sys.path.insert(0, extra)
    try:
        dc = importlib.import_module("sleepmode.dreamcheck")
        tools = importlib.import_module("sleepmode.tools")
        return dc, tools.ToolBox
    except Exception as e:   # not installed, or broken: never fail the night over it
        return None, "%s: %s" % (type(e).__name__, e)


class LocalChat:
    """The ChatModel interface dreamcheck's agent needs (chat(messages, max_tokens, temperature) -> str), on the trainer's backend.
    No chat_tools: the agent then uses its `TOOL: name {json}` text protocol."""

    def __init__(self, backend, tok, prof, adapter: bool = False, max_tokens: int = MAX_TOKENS):
        self.be, self.tok, self.prof, self.adapter, self.cap = backend, tok, prof, adapter, max_tokens

    def render(self, messages) -> str:
        msgs = [{"role": m["role"] if m["role"] in ("system", "user", "assistant") else "user", "content": m.get("content") or ""} for m in messages]
        if self.tok is not None and hasattr(self.tok, "apply_chat_template") and self.prof.template_mode == "tokenizer":
            t = self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        else:
            tp = self.prof.template
            t = ""
            for m in msgs:
                key = m["role"] if m["role"] in ("system", "user") else None
                if key:
                    t += tp.get(key, key + ": {content}\n").format(content=m["content"])
                else:
                    t += tp.get("assistant_open", "assistant: ") + m["content"] + (self.prof.stop_token or "") + "\n"
            t += tp.get("assistant_open", "assistant: ")
        suf = self.prof.nothink_suffix
        if suf and not t.endswith(suf):
            t += suf
        return t

    def chat(self, messages, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        return self.be.generate([self.render(messages)], min(int(max_tokens), self.cap), 0.0, adapter=self.adapter)[0]


def item_id(q: str, a: str) -> str:
    return hashlib.sha1(("%s\x00%s" % (q, a)).encode()).hexdigest()[:16]


def check(rows: Sequence[dict], model, diary_dir: str, budget_s: float, now: Callable[[], float] = time.time,
          checker=None, env=os.environ, cache: Optional[Dict[str, str]] = None, log: Callable[[str], None] = lambda m: None) -> Dict:
    """rows: [{"q", "a", "source"?}]. -> {"verdicts": {id: verdict}, "stats": {...}}. cache: id -> verdict from an earlier chunk."""
    cache = {} if cache is None else cache
    st = {"available": True, "n": len(rows), "supported": 0, "contradicted": 0, "unknown": 0, "unchecked": 0, "cached": 0, "errors": 0, "elapsed_s": 0.0}
    out: Dict[str, str] = {}
    if checker is None:
        dc, tb = load_checker(env)
        if dc is None:
            st.update(available=False, reason=tb, unchecked=len(rows))
            return {"verdicts": {item_id(r["q"], r["a"]): "UNCHECKED" for r in rows}, "stats": st}
        toolbox = tb(diary_dir, web=False)
        checker = lambda item: dc.check_item(model, toolbox, item, max_steps=MAX_STEPS, budget_s=120.0)[0]   # noqa: E731
    t0 = now()
    for r in rows:
        i = item_id(r["q"], r["a"])
        if i in cache:
            out[i] = cache[i]
            st["cached"] += 1
        elif now() - t0 >= budget_s:
            out[i] = "UNCHECKED"
        else:
            try:
                v = checker({"id": i, "question": r["q"], "answer": r["a"], "source": r.get("source", "")})
            except Exception as e:
                v = "UNKNOWN"
                st["errors"] += 1
                log("[dreamcheck] error: %s" % e)
            out[i] = cache[i] = v if v in ("SUPPORTED", "CONTRADICTED", "UNKNOWN") else "UNKNOWN"
        key = out[i].lower()
        st[key if key in st else "unknown"] += 1
    st["elapsed_s"] = round(now() - t0, 1)
    return {"verdicts": out, "stats": st}
