#!/usr/bin/env python3
"""lis-315 -- per-fact release, one wrapper (turn315) outside turn310 (or turn313).

Why: lis-310 saves all of a turn's facts or none. One blocked fact (unsure, "we", an owner not
in the turn) blocks every other fact in that turn, even ones the reader is sure of. On lis-301's
dev readings per-fact release raised right saves from 462 to 534 of 771 at T 0.995 with the same
2 wrong-save turns (artifacts/claude-lis302-20260924/RESULTS.md).

Per user turn:
  - A plain yes/no answering turn310's pending ask-back: passed through, no read.
  - Otherwise read once (MemoReader, shared with the inner layers) and compile at T.
    If the all-or-nothing compiler already writes, or nothing in the turn is both
    structurally writable and >= T, the turn is passed through unchanged.
  - Else (the confident facts were blocked by another fact): save exactly the confident facts
    through turn310's own doorway (_save_all310: the 209 and 252b screens, teach/correct
    choice, "me" stored as USER). Then, for what is left: a "we" fact gets turn310's
    "Whose ... ?" question; else the first remaining writable-looking fact gets turn310's
    ask-back ("Just to check: ...?"), answered through turn310's pending branch. Facts in
    held modes (REPORTED, SUPPOSE, ...) are never saved, as in turn310.
    If a screen rejects the confident facts, nothing is saved and the turn is passed through.

New file only; no existing file is edited. The wrapper writes only through _save_all310.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_lis300_compiler as CMP  # noqa: E402 (read-only)
import claude_lis310_agent as L310  # noqa: E402 (read-only)

LOG_NAME315 = "lis315_log.jsonl"


def split315(frame, turn, prev, confs, threshold):
    """(confident, whose, rest): confident = check_fact passes and conf >= T; whose = "we"
    facts; rest = writable-looking facts that are not confident (unsure, or a structural
    failure other than a held mode)."""
    confident, whose, rest = [], [], []
    facts = frame.get("facts") or [] if isinstance(frame, dict) else []
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            continue
        why = CMP.check_fact(f, turn, prev)
        c = confs[i] if i < len(confs) else 0.0
        if why is None and c >= threshold:
            confident.append(f)
        elif why == "we":
            whose.append(f)
        elif why is None or not why.startswith("mode:"):
            rest.append(f)
    return confident, whose, rest


def _log315(loop, row):
    try:
        with open(loop.lis315_log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def install_turn315(loop, memo, threshold=L310.DEFAULT_THRESHOLD310, log_path=None):
    """Install turn315 outside the current loop.turn (turn310 or turn313, built on memo)."""
    inner = loop.turn
    if getattr(inner, "__name__", "") not in ("turn310", "turn313"):
        raise RuntimeError("315: needs turn310 or turn313 inside")
    loop.turn315_inner = inner
    loop.lis315_threshold = float(threshold)
    loop.lis315_log_path = str(log_path or (Path(loop.lis310_log_path).parent / LOG_NAME315))
    st = loop.lis315_stats = {"turns": 0, "released": 0, "facts_saved": 0, "then_whose": 0,
                              "then_askback": 0, "screen_pass_through": 0}

    def turn315(text):  # type: ignore[no-untyped-def]
        t = str(text)
        st["turns"] += 1
        prev = loop.lis310_prev or ""
        if loop.lis310_pending is not None and L310._norm_yesno(t) in (L310.YES310 | L310.NO310):
            return inner(t)
        read = memo.read(t, prev)
        frame = read[0] if isinstance(read, (tuple, list)) and read else None
        if not isinstance(frame, dict):
            return inner(t)
        try:
            confs = list(read[1]) if read[1] is not None else []
        except TypeError:
            confs = []
        dec = CMP.compile_frame(frame, t, prev, confs, loop.lis315_threshold)
        confident, whose, rest = split315(frame, t, prev, confs, loop.lis315_threshold)
        if dec.get("write") or not confident:
            return inner(t)
        ev0 = len(loop.nb.events)
        wrote, say, screen = L310._save_all310(loop, confident, t)
        if screen is not None:
            st["screen_pass_through"] += 1
            assert len(loop.nb.events) == ev0, "315: a screened turn wrote"
            return inner(t)
        st["released"] += 1
        st["facts_saved"] += len(wrote)
        loop.lis310_stats["writes"] += len(wrote)
        parts = [say] if say else []
        decision = "released"
        if whose:
            st["then_whose"] += 1
            parts.append(L310.WHOSE_FMT310.format(rel=whose[0].get("rel"),
                                                  value=whose[0].get("value")))
            decision += "+whose"
        elif rest:
            st["then_askback"] += 1
            fact = rest[0]
            loop.lis310_pending = {"fact": fact, "conf": None}
            parts.append(L310.ASKBACK_FMT310.format(
                owner=L310._owner_display310(fact.get("owner", "")),
                rel=fact.get("rel", ""), value=fact.get("value", "")))
            decision += "+askback"
        reply = [" ".join(p for p in parts if p) or L310.NOT_PLAIN310]
        loop.lis310_prev = reply[0]
        loop.lis310_stats["turns"] += 1
        _log315(loop, {"turn": t, "prev": prev, "frame": frame, "confs": confs,
                       "decision": decision, "wrote": wrote, "reply": reply})
        return reply

    turn315.__name__ = "turn315"
    loop.turn = turn315
    return loop
