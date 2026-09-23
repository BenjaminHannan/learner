#!/usr/bin/env python3
"""Exp 267 -- C3 PICK-THE-READING checker (new, sealed with PREDICTIONS before
dev.jsonl is opened; never tuned after).

For each kept TEACH frame (S, R, V), one Qwen3.8-27B call (temperature 0,
thinking off, same chat-template transport as 261/264) shows the turn and 4
numbered readings:
  1. the ear's frame (S, R, V);
  2. relation swapped for its nearest table neighbour R' (same value_kind,
     table order, wrapping; aliases/narrower/ancestors of R skipped);
  3. subject swapped for the other name in the turn (first capitalized span
     outside the subject and value spans; fallback below);
  4. value swapped for "not stated".
Save iff the model picks reading 1. Anything else (2/3/4/0/other) holds back
as UNSURE. ASK frames are never checked.

Blind rules fixed here before dev contact (no tuning after the seal):
- neighbour: deterministic from relation table v2 only (see neighbour()).
- other name: regex capitalized spans; value-span and subject-span tokens
  excluded; fallback "the speaker" when S != me, else "the other person".
- abstain: the prompt allows answering 0 when none is stated as a real,
  current fact; 0 is not a reading, and save still requires exactly 1.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402

PROMPT_VERSION = "c3-v1-pick4 (sealed 2026-09-23, before dev contact)"

_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b")

# Capitalized non-names the extractor must skip (blind, fixed pre-seal):
# pronouns, determiners, connectives, question words and discourse markers.
_SKIP = frozenset({
    "i", "my", "me", "mine", "myself", "we", "our", "ours", "us", "ourselves",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
    "they", "them", "their", "theirs", "it", "its",
    "the", "a", "an", "this", "that", "these", "those",
    "and", "but", "or", "nor", "for", "yet", "so", "as", "at", "by",
    "in", "on", "of", "to", "from", "with",
    "is", "are", "was", "were", "be", "been", "do", "does", "did",
    "not", "no", "yes", "oh", "ah", "well", "now", "today", "here", "there",
    "if", "then", "when", "where", "what", "which", "who", "whom", "whose",
    "how", "why",
    "let", "imagine", "suppose", "say", "says", "training", "want", "wants",
})


def _rkey(s: str) -> str:
    return E._rkey(s)


def _narrower_map() -> dict:
    m: dict = {}
    for r in E._TABLE["relations"]:
        nar = [str(x) for x in r.get("narrower", [])]
        if nar:
            m[r["name"]] = {_rkey(x) for x in nar}
    return m


def neighbour(subject_relation: str) -> str:
    """Nearest table neighbour of R: next relation in table order with the same
    value_kind (wrapping), skipping R itself and anything that maps to R
    through names/aliases/narrower/ancestors. Falls back to the next relation
    in table order regardless of kind (same skips)."""
    rels = E._TABLE["relations"]
    try:
        rc = E.canon_rel(subject_relation)
    except Exception:
        rc = None
    if rc is None:
        return rels[0]["name"] if rels else str(subject_relation)
    rk = _rkey(subject_relation)
    nm = _narrower_map()
    ancestors = {p for p, nar in nm.items() if rk in nar}
    skip = {rk}
    try:
        skip.add(_rkey(rc))
    except Exception:
        pass
    for p, nar in nm.items():
        if rk in nar:
            skip.add(_rkey(p))
    skip |= {_rkey(x) for x in nm.get(rc, set())}
    skip |= {_rkey(x) for x in ancestors}
    idx = next(i for i, r in enumerate(rels) if r["name"] == rc)
    kind = rels[idx].get("value_kind")
    n = len(rels)
    for j in range(1, n):
        cand = rels[(idx + j) % n]
        if cand.get("value_kind") == kind and _rkey(cand["name"]) not in skip:
            return cand["name"]
    for j in range(1, n):
        cand = rels[(idx + j) % n]
        if _rkey(cand["name"]) not in skip:
            return cand["name"]
    return rels[(idx + 1) % n]["name"]


def other_name(turn: str, subject: str, value: str) -> str:
    """First capitalized span in the turn outside the subject and value spans.
    Fallback: 'the speaker' when S != me, else 'the other person'."""
    t = str(turn)
    spans = []
    for needle in (str(subject), str(value)):
        needle = needle.strip()
        if needle and needle.lower() != "me":
            start = 0
            while True:
                i = t.find(needle, start)
                if i < 0:
                    break
                spans.append((i, i + len(needle)))
                start = i + 1
    subj_l = str(subject).strip().lower()

    def inside(s, e):
        return any(s < b and e > a for a, b in spans)

    for m in _NAME_RE.finditer(t):
        if inside(m.start(), m.end()):
            continue
        if m.group(0).lower() in _SKIP:
            continue
        return m.group(0)
    if subj_l == "me":
        return "the other person"
    return "the speaker"


def _disp_subject(subject: str) -> str:
    return "the speaker" if str(subject).strip().lower() == "me" else str(subject).strip()


def render_reading(subject: str, relation: str, value: str) -> str:
    s = _disp_subject(subject)
    rw = str(relation).strip().replace("_", " ")
    return f"{s}'s {rw} is {str(value).strip()}."


def build_c3(turn: str, frame: dict) -> tuple:
    """Return (prompt, readings[4]). Reading 1 is always the ear's frame."""
    s, r, v = frame["subject"], frame["relation"], frame["value"]
    r2 = neighbour(r)
    s3 = other_name(turn, s, v)
    readings = [
        render_reading(s, r, v),
        render_reading(s, r2, v),
        render_reading(s3, r, v),
        f"{_disp_subject(s)}'s {str(r).strip().replace('_', ' ')} is not stated in the message.",
    ]
    numbered = "\n".join(f"{i + 1}. {rd}" for i, rd in enumerate(readings))
    prompt = (
        "/no_think\n"
        f"Message from the speaker: \u00ab{str(turn).strip()}\u00bb\n"
        "Four readings of this message:\n"
        f"{numbered}\n"
        "Which reading is what the message states as a real, current fact "
        "the speaker believes (not asked, checked, pretended, supposed, "
        "planned, wished, denied, replaced, or about a different person)? "
        "Answer with one digit: 1, 2, 3 or 4. "
        "If none of them is stated as a real, current fact, answer 0.\n"
        "Answer:"
    )
    return prompt, readings


def parse_c3(text: str):
    """First character 0-4 in the stripped answer, else None (holds back)."""
    t = str(text).strip()
    if t and t[0] in "01234":
        return int(t[0])
    return None


def c3_decide(answer_text: str) -> tuple:
    """Return (save: bool, pick). Save iff the model picks reading 1."""
    pick = parse_c3(answer_text)
    return (pick == 1, pick)
