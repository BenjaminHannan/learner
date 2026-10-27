#!/usr/bin/env python3
"""The mouth layer for the joined build (330b): the 1B mouth's reply, or the base's own text if any check fails.

    layer = MouthLayer(mouth, readback=None)
    text, info = layer.say(record, user_turn, tag, fallback_text)
Checks, in order; any failure -> fallback_text (292t's fixed wording), and info["used"] says which:
  1. slot gate: the sealed own-M1 slot_check (no slot the record lacks, required slots present, no capitalised
     word or digit outside slots);
  2. leak gate: no record name or value typed literally, in any case, outside a slot (slot_check only catches
     capitalised words; a mouth could type "melon" instead of <V1>);
  3. read-back (own-M2a, optional): a callable readback(filled_text, record) -> [] or problems.
The printer fills <R1> with the relation's plain noun phrase from the 241b say-forms table ("favorite food",
not "favorite_food"), joined with "'s " for chains.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_own_m1_common import SLOT_RE, slot_check, slot_values  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
_SAY = _REPO / "artifacts" / "claude-mouth241b-20260922" / "say_forms.json"
try:
    NOUNS = {k: v["noun"] for k, v in json.loads(_SAY.read_text())["rows"].items()}
except Exception:  # table missing: fall back to plain underscores -> spaces
    NOUNS = {}


def relation_phrase(rels):
    return "'s ".join(NOUNS.get(r, r.replace("_", " ")) for r in rels)


def natural_values(record):
    v = slot_values(record)
    f = record.get("fields", {}) or {}
    rels = record.get("relations") or ([f["relation"]] if f.get("relation") else [])
    if rels:
        v["<R1>"] = relation_phrase(rels)
    return v


def fill_natural(raw, record):
    out = raw
    for tok, s in natural_values(record).items():
        out = out.replace(tok, s)
    return out


def leak_check(raw, record):
    """Record strings typed outside slots, in any case (names, values, stated values)."""
    bare = SLOT_RE.sub(" ", raw).lower()
    f = record.get("fields", {}) or {}
    strings = [record.get("name"), f.get("subject"), f.get("answer"), f.get("value"), f.get("stated_value")]
    probs = []
    for s in strings:
        if s and isinstance(s, str) and s.lower() not in ("our", "we", "my", "me") and \
                re.search(r"(?<![\w])" + re.escape(s.lower()) + r"(?![\w])", bare):
            probs.append(f"literal record string outside slot: {s}")
    return probs


class MouthLayer:
    def __init__(self, mouth, readback=None):
        self.mouth, self.readback = mouth, readback

    def say(self, record, user_turn, tag, fallback_text):
        text, info = self.mouth.say(record, user_turn, tag)
        if text is None:
            return fallback_text, {**info, "used": "fallback: slot gate"}
        raw = info["raw"][info["tries"] - 1]
        if slot_check(raw, record):  # belt and braces: re-check the winning raw
            return fallback_text, {**info, "used": "fallback: slot gate"}
        leak = leak_check(raw, record)
        if leak:
            return fallback_text, {**info, "used": "fallback: leak gate", "leak": leak}
        filled = fill_natural(raw, record)
        if self.readback is not None:
            rb = self.readback(filled, record)
            if rb:
                return fallback_text, {**info, "used": "fallback: read-back", "readback": rb}
        return filled, {**info, "used": "mouth"}
