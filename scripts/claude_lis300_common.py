#!/usr/bin/env python3
"""lis-300 shared bits: the reader's prompt and the canonical frame text.

The prompt is plain text (no chat template, no thinking tags) so that training and
inference see exactly the same bytes. The target is compact JSON with keys in a fixed order.
"""
from __future__ import annotations

import json

SYSTEM = ("Read the user's chat turn into a frame. Copy names and values exactly as typed. "
          "Output one JSON object.")
END = "\n<END>"


def build_prompt(turn: str, prev_reply: str = "") -> str:
    return (f"{SYSTEM}\nAssistant said: {prev_reply.strip() or '(nothing)'}\n"
            f"User said: {turn.strip()}\nFrame: ")


FACT_KEYS = ["owner", "rel", "value", "mode", "old"]
ASK_KEYS = ["owner", "rel", "via", "value", "inverse"]


def canon_frame(fr: dict) -> dict:
    facts = []
    for f in fr.get("facts") or []:
        facts.append({k: f[k] for k in FACT_KEYS if k in f and f[k] is not None})
    ask = fr.get("ask")
    if isinstance(ask, dict):
        ask = {k: ask[k] for k in ASK_KEYS if k in ask and ask[k] is not None}
    else:
        ask = None
    return {"act": fr.get("act"), "facts": facts, "ask": ask}


def frame_text(fr: dict) -> str:
    return json.dumps(canon_frame(fr), ensure_ascii=False, separators=(", ", ": ")) + END


def parse_frame(text: str):
    """Parse the model's output; None if it is not a valid frame."""
    t = text.split("<END>")[0].strip()
    try:
        fr = json.loads(t)
    except Exception:
        return None
    if not isinstance(fr, dict) or "act" not in fr or not isinstance(fr.get("facts", []), list):
        return None
    return fr
