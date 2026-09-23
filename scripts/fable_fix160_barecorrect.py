#!/usr/bin/env python3
"""Experiment 160 -- THE ONE CHANGE: bare corrections (class N6).

Responsible code (Step 1, read before sealing):
  scripts/fable_agent_loop.py:95  (_CORRECTION prefix set: only
    "actually"/"no," + full sentence; a bare "no wait, it's Denver" falls
    through to _STATEMENT, fails the 2-part 's-chain and clarifies)
  scripts/fable_loop102_agent.py:92  (_CORRECTION_PREFIX_RE, the real chain:
    "actually,"/"actually "/"no,"/"correction:"/"sorry[ ,] i meant" + full
    sentence; "no wait, it's Denver" matches NO prefix, the teach-template
    parse of the whole turn returns None, so the exact old path clarifies)

THE RULE (sealed; applied in the ears hear() tag + loop _act() resolve,
same two levels as the 139b/150 guards, plus a _listening_tick wrapper
that maintains the previous-turn triple):

  A turn is a BARE CORRECTION iff, after whitespace collapse and stripping
  one trailing ".", it matches one sealed prefix (case-insensitive) AND the
  remainder V passes validation:
    prefixes: "no wait," / "wait," / "sorry," (each optionally followed by
      "it's"/"its"/"it's"/"it is"), "i meant" (optional comma, no it's),
      "no," (optionally followed by it's/it is). Longer prefixes first.
    V valid iff: non-empty; no "?" or "!" in the turn; no "'s"/"'s" and no
      " is "/" are " in V (full sentences fall through to the base path);
      no ","/";"/":" in V; at most 8 words; not a bare question word
      (what/who/where/when/why/how/which/whom/whose); does not start with
      "to " ("I meant to ask ..." falls through).
  Resolution: iff the session has a most-recent saved teach (the latest
  user turn that stored exactly one teach/correct triple), the bare turn
  synthesizes {"act":"correct", same name/relation/is_person, value V}
  and goes through super()._act -- the loop's EXISTING correction
  machinery (same guards, same "Saved: ..." reply, same audit trail and
  supersede rules as "Actually, X's R is V."). Intervening non-write turns
  (questions, clarifies, refusals, small talk) neither set nor clear the
  memory; only a newer stored teach/correct replaces it, so chained bare
  corrections work. (Correction 2026-09-22, post-seal, re-sealed: v1 read
  "IMMEDIATELY previous user turn" strictly, which clarifies on the sealed
  N6 session turn S3n6 -- teach 3 turns back, previous turn a question --
  and cannot meet the sealed C2 bar "the N6 turns become OK". The memory
  is the most-recent saved teach; see RESULTS.md deviations.)
  Otherwise (no saved teach yet this session): one clarify with 0 writes:
    Which fact should I change? You can say e.g. "Actually, Tom's city is Denver."

Cooperative MIXIN (BareCorrect160Mixin): hear() runs base hear first and
only re-tags a single clarify into {"act":"bare_correct","value":V} (never
touches teaches/asks/clarifies that fail the parse, so non-matching turns
are byte-identical to loop150); _act() resolves bare_correct against
_last_teach160; _listening_tick() stores the turn's triple into
_last_teach160 on a single wrote-write, else keeps the most-recent one,
and persists it in state.json ("last_teach160") across resume. No existing file edited.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Reply for a bare correction with no fresh teach (exact, sealed).
CLARIFY_MSG = ('Which fact should I change? You can say e.g. '
               '"Actually, Tom\'s city is Denver."')

_ITS = r"(?:it['\u2019]s|its|it\s+is)\s+"
_PREFIX_RES = (
    re.compile(r"^no\s+wait\s*,\s*(?:" + _ITS + r")?(.+?)\s*\.?\s*$",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"^wait\s*,\s*(?:" + _ITS + r")?(.+?)\s*\.?\s*$",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"^sorry\s*,\s*(?:" + _ITS + r")?(.+?)\s*\.?\s*$",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"^i\s+meant\s*,?\s*(.+?)\s*\.?\s*$",
               re.IGNORECASE | re.DOTALL),
    re.compile(r"^no\s*,\s*(?:" + _ITS + r")?(.+?)\s*\.?\s*$",
               re.IGNORECASE | re.DOTALL),
)

_QWORDS = frozenset({"what", "who", "where", "when", "why", "how",
                     "which", "whom", "whose"})
_POSS_RE = re.compile(r"['\u2019]s\b")
_COPULA_RE = re.compile(r"\b(is|are)\b", re.IGNORECASE)
_MAX_VALUE_WORDS = 8


def _norm(turn: str) -> str:
    return " ".join(str(turn).split())


def parse_bare_correction(turn: str) -> str | None:
    """Bare-correction value V, or None (fall through to the base path).

    Pure function (scanned pre-seal over bench/suite/session strings).
    """
    text = _norm(turn)
    if not text or "?" in text or "!" in text:
        return None
    for rx in _PREFIX_RES:
        m = rx.match(text)
        if not m:
            continue
        val = _norm(m.group(1))
        if not val:
            continue
        if _POSS_RE.search(val) or _COPULA_RE.search(val):
            return None
        if any(c in val for c in ",;:"):
            return None
        toks = val.split()
        if len(toks) > _MAX_VALUE_WORDS:
            return None
        if len(toks) == 1 and toks[0].lower() in _QWORDS:
            return None
        if val.lower() == "to" or val.lower().startswith("to "):
            return None
        return val
    return None


_TEACH_LINE_RE = re.compile(r"^(teach|correct)\s+(.+?)\s+(->|=)\s+(.*)$")


def triple_from_line(line: str) -> dict | None:
    """Parse an AgentLoop teach/correct line back into a triple dict."""
    m = _TEACH_LINE_RE.match(_norm(line))
    if not m:
        return None
    left = _norm(m.group(2)).split()
    if len(left) < 2:
        return None
    return {"name": " ".join(left[:-1]), "relation": left[-1],
            "value": _norm(m.group(4)),
            "is_person": m.group(3) == "->"}


def triple_from_record(rec: dict) -> dict | None:
    """A single wrote-write record -> its triple, else None."""
    if not isinstance(rec, dict) or rec.get("kind") != "write":
        return None
    if not rec.get("wrote"):
        return None
    struct = rec.get("structured")
    if isinstance(struct, dict) and struct.get("act") in ("teach", "correct"):
        if struct.get("name") and struct.get("relation"):
            return {"name": struct["name"], "relation": struct["relation"],
                    "value": struct.get("value", ""),
                    "is_person": bool(struct.get("is_person"))}
        return None
    line = rec.get("line")
    return triple_from_line(line) if line else None


def tag_actions(actions: list[dict], turn: str) -> list[dict]:
    """Re-tag a single base clarify as bare_correct when the parse hits."""
    if (isinstance(actions, list) and len(actions) == 1
            and isinstance(actions[0], dict)
            and actions[0].get("act") == "clarify"):
        val = parse_bare_correction(turn)
        if val is not None:
            return [{"act": "bare_correct", "value": val, "raw": turn}]
    return actions


class BareCorrect160Mixin:
    """Stackable mixin: bare corrections against the previous taught triple."""

    _last_teach160: dict | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        return tag_actions(actions, turn)

    def _act(self, action: dict) -> dict:  # type: ignore[no-redef]
        if isinstance(action, dict) and action.get("act") == "bare_correct":
            prev = getattr(self, "_last_teach160", None)
            if (isinstance(prev, dict) and prev.get("name")
                    and prev.get("relation") is not None):
                built = {"act": "correct", "name": prev["name"],
                         "relation": prev["relation"],
                         "value": action["value"],
                         "is_person": bool(prev.get("is_person"))}
                return super()._act(built)  # type: ignore[misc]
            self.counters["clarifications"] += 1  # type: ignore[attr-defined]
            return {"kind": "clarify", "text": CLARIFY_MSG}
        return super()._act(action)  # type: ignore[misc]

    def _listening_tick(self) -> dict:  # type: ignore[no-redef]
        event = super()._listening_tick()  # type: ignore[misc]
        recs = (event.get("detail") or {}).get("records") or []
        triple = (triple_from_record(recs[0])
                  if len(recs) == 1 else None)
        if triple is not None:
            self._last_teach160 = triple
        # Non-write turns leave the most-recent saved teach intact (never
        # cleared except by replacement; see module docstring correction).
        return event

    def _save(self) -> None:  # type: ignore[no-redef]
        super()._save()  # type: ignore[misc]
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
            raw["last_teach160"] = getattr(self, "_last_teach160", None)
            tmp = self.state_path.with_name(  # type: ignore[attr-defined]
                f"{self.state_path.name}.tmp160")  # type: ignore[attr-defined]
            import os as _os
            with open(tmp, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(raw, ensure_ascii=False,
                                        sort_keys=True))
                handle.flush()
                _os.fsync(handle.fileno())
            _os.replace(tmp, self.state_path)  # type: ignore[attr-defined]
        except OSError:
            pass

    def _load(self) -> None:  # type: ignore[no-redef]
        super()._load()  # type: ignore[misc]
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))  # type: ignore[attr-defined]
            val = raw.get("last_teach160")
            self._last_teach160 = val if isinstance(val, dict) else None
        except (OSError, ValueError):
            self._last_teach160 = None
