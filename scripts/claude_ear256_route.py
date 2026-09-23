#!/usr/bin/env python3
"""Exp 256 -- pure helpers for the ear-in-the-loop mixin (no agent state).

* canonical renderings of ear frames (the plain forms the 138l base reads);
* the round-trip table loader and row checks;
* the fixed-act test over the base's OWN dry-run ears reading;
* the 251 direction veto (scripts/claude_fix251_direction.py, read-only).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

REPO = SCRIPTS.parent

FIRST = {"i", "me", "my", "myself", "mine", "user"}
SECOND = {"you", "your", "yours", "yourself", "u", "ur"}

# Canonical templates (tried in this order by the round-trip builder; the
# first one that round-trips is recorded per row and used at run time).
TEACH_NAMED = ["{S}'s {r} is {V}."]
TEACH_FIRST = ["My {r} is {V}."]
ASK_NAMED = ["What is {S}'s {r}?", "Who is {S}'s {r}?"]
ASK_FIRST = ["What is my {r}?", "Who is my {r}?"]
# chains: {P} is the possessive path, e.g. "Tam's sister's" / "my sister's"
ASK_CHAIN = ["What is {P} {r}?", "Who is {P} {r}?"]

KINDS = ("named", "first", "named_chain", "my_chain", "named_hop1", "my_hop1")


def rel_words(rel: str) -> str:
    return str(rel).replace("_", " ").strip()


def is_first(subject: str) -> bool:
    return str(subject).strip().lower() in FIRST


def is_second(subject: str) -> bool:
    toks = re.findall(r"[a-z]+", str(subject).lower())
    return any(t in SECOND for t in toks)


def load_roundtrip(path) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = REPO / p
    return json.loads(p.read_text(encoding="utf-8"))


def row(rt: dict, rel: str, kind: str):
    r = rt.get("rows", {}).get(rel, {}).get(kind)
    return r if (r and r.get("ok")) else None


def render_teach(rt: dict, f: dict):
    """-> canonical sentence or None (row missing / failed)."""
    rel = f["relation"]
    if is_first(f["subject"]):
        r = row(rt, rel, "first")
        if r is None:
            return None
        return r["teach"].format(r=rel_words(rel), V=f["value"])
    r = row(rt, rel, "named")
    if r is None:
        return None
    return r["teach"].format(S=f["subject"], r=rel_words(rel), V=f["value"])


def render_ask(rt: dict, f: dict):
    rels = list(f["relation"])
    first = is_first(f["subject"])
    if len(rels) == 1:
        r = row(rt, rels[0], "first" if first else "named")
        if r is None:
            return None
        if first:
            return r["ask"].format(r=rel_words(rels[0]))
        return r["ask"].format(S=f["subject"], r=rel_words(rels[0]))
    # chain: every inner hop must be a verified hop-1 row, the last a chain row
    hop1_kind = "my_hop1" if first else "named_hop1"
    last_kind = "my_chain" if first else "named_chain"
    for h in rels[:-1]:
        if row(rt, h, hop1_kind) is None:
            return None
    r = row(rt, rels[-1], last_kind)
    if r is None:
        return None
    path = "my" if first else f"{f['subject']}'s"
    for h in rels[:-1]:
        path = f"{path} {rel_words(h)}'s"
    return r["ask"].format(P=path, r=rel_words(rels[-1]))


# ------------------------------------------------------- fixed-act test
import fable_fix156b_smalltalk as ST  # noqa: E402 (read-only)
import fable_earsguard91 as EG  # noqa: E402 (read-only)

# clarify texts that mean "the base could not read this turn" (ordinary
# failures, not fixed acts). Anything else a clarify says is a fixed act.
ORDINARY_CLARIFY = {
    ST.FALLTHROUGH_MSG,
    EG.SPLIT_MSG,
}
PLAIN_ACTS = {"teach", "ask", "clarify"}


def fixed_reason(acts) -> str | None:
    """The base's own dry-run reading -> why this turn is a fixed act (None = not)."""
    for a in acts or []:
        if not isinstance(a, dict):
            return "nondict"
        act = a.get("act")
        if act not in PLAIN_ACTS:
            return f"act:{act}"
        if any(k.startswith("name173") and a.get(k) for k in a):
            return "name173"
        if act == "clarify" and a.get("text", "") not in ORDINARY_CLARIFY:
            return "clarify:" + str(a.get("text", ""))[:40]
    return None


def plain_frames_of(acts):
    """The base's dry-run teach/ask actions as comparable keys (None if any
    action is not a plain teach/ask)."""
    out = []
    for a in acts or []:
        if a.get("act") == "teach":
            out.append(("TEACH", str(a.get("name", "")).lower(), str(a.get("relation", "")),
                        str(a.get("value", "")).lower()))
        elif a.get("act") == "ask":
            out.append(("ASK", str(a.get("name", "")).lower(), tuple(a.get("relations", []))))
        else:
            return None
    return sorted(out)


def ear_keys(frames):
    out = []
    for f in frames:
        s = "user" if is_first(f["subject"]) else f["subject"].lower()
        if f["act"] == "TEACH":
            out.append(("TEACH", s, f["relation"], f["value"].lower()))
        else:
            out.append(("ASK", s, tuple(f["relation"])))
    return sorted(out)


# ------------------------------------------------------- 251 veto
import claude_fix251_direction as D251  # noqa: E402 (read-only; veto only)


def backwards251(turn: str) -> bool:
    try:
        return bool(D251.parse251(turn)) or bool(D251.parse_extra251(turn))
    except Exception:  # noqa: BLE001
        return False
