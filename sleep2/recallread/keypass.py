"""The key pass: a fixed 1-shot prompt asks the model for up to 4 bridge names / short facts in at most 40 greedy tokens.

R uses the slept LoRA (adapter on); D2 uses the base (adapter off); D3 writes keys after reading round-1 hits (see round1_key_prompt).
The parse and the per-key mean log-probability are independent of the model, so they are unit-tested without one.
"""
from __future__ import annotations

import re

KEY_MAX_NEW = 40
MAX_KEYS = 4
KEY_SYS = ("You help Sam search his own diary of past chats. Given a question, write up to 4 short search keys: names of the people or things "
           "the question depends on and short facts about them, separated by semicolons, on one line. No other text.")
EXAMPLE_Q = "What's the name of my sister's dentist?"
EXAMPLE_A = "my sister -> Maya; Maya -> dentist Dr. Lee"


def key_user(q: str) -> str:
    return f"Question: {EXAMPLE_Q}\nKeys: {EXAMPLE_A}\n\nQuestion: {q}\nKeys:"


def key_prompt(render, q: str) -> str:
    return render(KEY_SYS, key_user(q))


def round1_key_prompt(render, ctx: str, q: str) -> str:
    """D3: the base reads the round-1 hits and writes bridge keys in the same format and budget."""
    u = (f"Notes from earlier chats:\n{ctx}\n\nQuestion: {EXAMPLE_Q}\nKeys: {EXAMPLE_A}\n\nQuestion: {q}\n"
         f"Keys (names and short facts needed to answer, which the notes above may not contain):")
    return render(KEY_SYS, u)


def parse_keys(text: str, max_keys: int = MAX_KEYS) -> list[str]:
    t = text.strip().splitlines()[0] if text.strip() else ""
    t = re.sub(r"^\s*keys?\s*:\s*", "", t, flags=re.I)
    out = []
    for k in re.split(r";|\n", t):
        k = k.strip(" \t.-")
        if k and k.lower() not in ("none", "n/a", "unknown") and k not in out:
            out.append(k)
    return out[:max_keys]


def key_logprobs(pieces: list[str], lps: list[float], keys: list[str]) -> list[float | None]:
    """Mean log-probability of the generated tokens that overlap each key's characters. pieces are the decoded tokens in order
    (concatenated they give the reply, up to leading whitespace)."""
    full = "".join(pieces)
    spans, pos = [], 0
    for p, lp in zip(pieces, lps):
        spans.append((pos, pos + len(p), lp))
        pos += len(p)
    res, cur = [], 0
    for k in keys:
        i = full.find(k, cur)
        if i < 0:
            res.append(None)
            continue
        cur = i + len(k)
        sel = [lp for a, b, lp in spans if a < cur and b > i]
        res.append(sum(sel) / len(sel) if sel else None)
    return res


def gate(keys: list[str], lps: list[float | None], tau: float | None) -> list[str]:
    """Ablation only: keep keys whose mean logprob >= tau (tau None / -inf keeps all)."""
    if tau is None:
        return list(keys)
    return [k for k, l in zip(keys, lps) if l is not None and l >= tau]
