#!/usr/bin/env python3
"""own-M1 mouth: shared bits (prompt, slot filling, slot check).

The mouth sees a checked reply record with names and values replaced by slot tokens,
the user's last turn (same slots), and a dialog tag. It writes a conversational reply
that uses the slot tokens; the printer puts the exact strings back afterwards, so the
model can never misspell or invent a name that reaches the user through a slot.

Slots: <S1> owner name, <V1> value / answer, <R1> relation phrase ("sibling's child").
"""
from __future__ import annotations

import re

SLOTS = ("<S1>", "<V1>", "<R1>")
SLOT_RE = re.compile(r"<[A-Z]+\d+>")

# statuses whose reply must state the value, and statuses that must never state one
NEEDS_VALUE = {"OK", "SAVED"}
NO_VALUE = {"UNKNOWN", "FORGOT", "ABSTAIN", "CLARIFY"}


def slot_values(record: dict) -> dict:
    """Map slot token -> exact string, from a talker120-style record."""
    f = record.get("fields", {}) or {}
    out = {}
    name = record.get("name") or f.get("subject")
    if name and not f.get("owner_phrase"):  # our/we owners are not a name slot (Ben's our-policy: ask whose)
        out["<S1>"] = name
    rels = record.get("relations") or ([f["relation"]] if f.get("relation") else [])
    if rels:
        out["<R1>"] = "'s ".join(rels)
    val = f.get("answer") or f.get("value")
    if val:
        out["<V1>"] = val
    return out


def slotify(text: str, values: dict) -> str:
    """Replace literal names/values in text with their slot tokens (longest first, whole words)."""
    for tok, s in sorted(values.items(), key=lambda kv: -len(kv[1])):
        if tok == "<R1>":
            continue  # relation words are ordinary English in the user's turn
        text = re.sub(r"(?<![\w])" + re.escape(s) + r"(?![\w])", tok, text, flags=re.IGNORECASE)
    return text


def record_text(record: dict, values: dict) -> str:
    f = record.get("fields", {}) or {}
    lines = [f"status: {record.get('status', '')}"]
    for tok in SLOTS:
        if tok in values:
            lines.append({"<S1>": "name", "<V1>": "value", "<R1>": "relation"}[tok] + f": {tok}")
    if f.get("source"):
        lines.append(f"source: {f['source']}")
    if f.get("hop"):
        lines.append(f"hops: {f['hop']}")
    return "\n".join(lines)


def build_prompt(record: dict, user_turn: str, tag: str) -> str:
    values = slot_values(record)
    return ("### Record\n" + record_text(record, values) +
            "\n### User\n" + slotify(user_turn or "", values) +
            "\n### Tag\n" + tag + "\n### Reply\n")


def fill(reply: str, values: dict) -> str:
    for tok, s in values.items():
        reply = reply.replace(tok, s)
    return reply


def slot_check(reply: str, record: dict) -> list[str]:
    """Problems with a slotted reply against its record; [] means it passes.

    Code-only faithfulness gate (independent of the M0 builder's checker):
    - no slot the record lacks, no unknown slot token;
    - OK/SAVED replies state <S1> and <V1>; UNKNOWN/FORGOT/ABSTAIN/CLARIFY never state <V1>;
    - replies about a named fact mention <S1>;
    - no capitalised word outside slots except sentence starts, "I" and contractions of I;
    - no digits (records carry no numbers the mouth may say).
    """
    values = slot_values(record)
    status = record.get("status", "")
    probs = []
    used = set(SLOT_RE.findall(reply))
    for t in used:
        if t not in SLOTS:
            probs.append(f"unknown slot {t}")
        elif t not in values:
            probs.append(f"slot {t} not in record")
    if status in NEEDS_VALUE and "<V1>" in values and "<V1>" not in used:
        probs.append("value missing")
    if status in NO_VALUE and "<V1>" in used:
        probs.append("value stated for a no-value status")
    if "<S1>" in values and status in NEEDS_VALUE | {"UNKNOWN", "FORGOT"} and "<S1>" not in used:
        probs.append("owner missing")
    bare = SLOT_RE.sub(" x ", reply)
    for m in re.finditer(r"[A-Za-z][A-Za-z']*", bare):
        word = m.group(0)
        if not word[0].isupper() or word in ("I", "I'm", "I've", "I'll", "I'd"):
            continue
        before = bare[:m.start()].rstrip(" \t\"'(")
        if before == "" or before[-1] in ".!?\n:":
            continue  # sentence start
        probs.append(f"capitalised word outside slots: {word}")
    if re.search(r"\d", bare):
        probs.append("digit in reply")
    return probs
