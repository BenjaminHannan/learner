#!/usr/bin/env python3
"""sf-401 -- stale-fact guard (wrong-as-fact thread, 2026-09-26). New file only; no existing file is edited.

Why (0.2c row H1, "wrong answers stated as fact", X 8 vs G 5). Counts only on bank D (TEST-ONLY, no item read):
10 of the 13 judged-wrong answers are questions asked after a correction, all 13 name a value that was in the
notebook at that moment, and 8 name the old, corrected value. At those questions the notebook held the new value
in 7 of 30 edit asks (X). The mechanism, read on DEV data (artifacts/claude-lis319-20260925/reads_e2edev_B.jsonl):
the lis-319 reader reads 9 of the 10 DEV correction turns with the right person and new value, but below the
0.995 bar (0.25 to 0.98), so the new value is parked in lis-314's pending store or asked back, the old value stays
saved, and lis-314 only uses a pending fact when the notebook has no answer. So the old value is stated as fact.

The one change: a saved fact that a later user turn contradicted is never stated as fact.
  Doubt. On a turn the reader does not read as a question (act != "ASK"), for each fact in the reader's own frame,
  at ANY confidence (read before any inner layer edits it), a saved fact (s, r, v) becomes doubted when the
  frame's person resolves to the saved person (same_person) and
    (a) the frame, in mode ASSERT or CORRECT, gives another value for the same relation, the relation holds one
        value (not in MULTI401), and the new value is in the user's words; or
    (b) the frame, in mode ASSERT or CORRECT, names v as the "old" value of a correction, v in the user's words; or
    (c) the frame says the saved fact itself is no longer true (mode NEGATED, or FORMER from lis-319f; same
        relation and value). QUESTION, SUPPOSE, REPORTED and other modes never raise a doubt;
  and (s, r, v) is still saved after the turn (a confident correction has already replaced it: nothing to do).
  A later frame that repeats (s, r, v) exactly, not negated, clears its doubt.
  Answer. On a question turn (reader act ASK or a "?" in the user's words), when the inner reply is a statement
  (it does not end with "?") that names a doubted fact's value v (whole word, any case), and no other saved,
  undoubted fact with the value v whose person is named in the question or the reply explains it, the reply is
  replaced:
    - if the contradicting turn gave a new value (a, b), lis-314's own confirm question for it, on the saved
      person and relation ("I think you told me X, is that right?"). The next turn is lis-314's: a "yes" saves
      it through turn310's doorway (a correct, which replaces the old value), a "no" drops it; this layer then
      clears the doubt on "no" and never asks the same offer twice;
    - otherwise, or once the offer was answered "yes": HEDGE401 with the old claim.
  Nothing is deleted or written to the notebook by this layer. Doubts are kept in <state_dir>/sf401_doubts.json
  so they survive a restart.

Install: install_sf401(loop, memo) right outside the listener stack (on turn316); build_02c_sf401 is 0.2c's
build_02c with this layer added there and nothing else (a build-time wrapper around claude_lis_stackb.build_stack).
Counters: loop.sf401_stats; with SF401_LOG=<path> each built agent appends its counters (counts only) at exit.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_lis300_compiler as CMP  # noqa: E402 (read-only: relation table, write modes)
import claude_lis310_agent as L310  # noqa: E402 (read-only: yes/no words, USER subject)
import claude_lis314b_agent as L314  # noqa: E402 (read-only: confirm wording and claim renderer)
import fable_fix154e_allowlist as M154E  # noqa: E402 (read-only: the base's multi-valued relations)

STORE_NAME401 = "sf401_doubts.json"
HEDGE401 = "Earlier you told me {claim}, but I think that has changed since, so I'm not sure now."
# Relations where a second value is normal: the base's own list (154e) plus common reader relation names of the
# same kind. Fixed before any run; rule (a) never fires on these (rules b and c still do).
MULTI401 = frozenset(set(M154E.MULTI_VALUED_154E) | {
    "kid", "grandparent", "grandson", "granddaughter", "niece", "nephew", "neighbour", "neighbor", "roommate",
    "classmate", "teammate", "student", "hobby", "allergy", "speaks", "plays", "instrument", "sport", "car"})
# Modes that say a value is no longer true (lis-319f adds FORMER, "I used to be a nurse"; Reading facts 13:11 UTC).
STALE_MODES401 = ("NEGATED", "FORMER")
USER_WORDS401 = re.compile(r"\b(i|i'm|im|me|my|mine|you|your|yours|you're)\b", re.I)


def _low(x) -> str:
    return str(x or "").strip().lower()


def _names(text: str, value: str) -> bool:
    """value occurs in text as whole words, any case (the scorer's own matching rule)."""
    v = _low(value)
    return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", _low(text)) is not None


def same_person(subject: str, owner: str) -> bool:
    """A notebook subject (display name, "USER" for the user) and a reader owner ("me" for the user)."""
    s, o = _low(subject), _low(owner)
    if not s or not o:
        return False
    if s == _low(L310.USER_SUBJECT310):
        return o in ("me", "i", "user")
    if o in ("me", "i", "user"):
        return False
    return s == o or s.split()[0] == o or o.split()[0] == s


def claim401(subject: str, rel: str, value: str) -> str:
    owner = "me" if _low(subject) == _low(L310.USER_SUBJECT310) else str(subject)
    return L314.claim314({"owner": owner, "rel": rel, "value": value})


def _triples(loop) -> set:
    import fable_loop90_agent as L90
    return {tuple(t) for t in L90.notebook_triples(loop.nb)}


def doubts_from_frame(frame: dict, turn: str, before: set) -> tuple[list[dict], list[tuple]]:
    """(new doubts, triples a frame repeats exactly). Pure: reads the frame and the triples saved before the turn."""
    new, repeats = [], []
    if not isinstance(frame, dict) or frame.get("act") == "ASK":
        return new, repeats
    for f in frame.get("facts") or []:
        if not isinstance(f, dict):
            continue
        owner, rel, val = str(f.get("owner", "")), str(f.get("rel", "")), str(f.get("value", ""))
        mode, old = f.get("mode"), str(f.get("old") or "")
        for (s, r, v) in before:
            offer = None
            if val and _low(val) != _low(v) and _names(turn, val) and mode in CMP.WRITE_MODES \
                    and r in CMP.REL_NAMES:
                offer = {"owner": "me" if _low(s) == _low(L310.USER_SUBJECT310) else s, "rel": r,
                         "value": val, "mode": "CORRECT"}
            if not same_person(s, owner):
                continue
            if mode in STALE_MODES401:
                if r == rel and _low(v) == _low(val):
                    new.append({"s": s, "r": r, "v": v, "rule": "c", "new": None})
                continue
            if r == rel and _low(v) == _low(val):
                repeats.append((s, r, v))
                continue
            if old and _low(old) == _low(v) and _names(turn, old) and mode in CMP.WRITE_MODES:
                new.append({"s": s, "r": r, "v": v, "rule": "b", "new": offer})
            elif r == rel and r not in MULTI401 and offer is not None:
                new.append({"s": s, "r": r, "v": v, "rule": "a", "new": offer})
    return new, repeats


def explained_by_other(value: str, doubt_keys: set, triples: set, text: str) -> bool:
    """Another saved, undoubted fact has this value and its person is named in the question or reply."""
    for (s, r, v) in triples:
        if (s, r, v) in doubt_keys or _low(v) != _low(value):
            continue
        if _low(s) == _low(L310.USER_SUBJECT310):
            if USER_WORDS401.search(text):
                return True
        elif _names(text, s) or _names(text, str(s).split()[0]):
            return True
    return False


def _load(path) -> list[dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict) and {"s", "r", "v"} <= set(d)]
    except (OSError, ValueError):
        return []


def install_sf401(loop, memo, store_path=None):
    inner = loop.turn
    if getattr(inner, "__name__", "") not in ("turn316", "turn314"):
        raise RuntimeError("sf401: needs the listener stack with lis-314 inside (turn316 or turn314)")
    if not hasattr(loop, "lis314_store"):
        raise RuntimeError("sf401: needs lis-314 (pending store and confirm)")
    try:
        sdir = Path(loop.dir)
    except Exception:  # noqa: BLE001
        sdir = Path(loop.lis310_log_path).parent
    path = str(store_path or (sdir / STORE_NAME401))
    doubts = _load(path)
    st = loop.sf401_stats = {"turns": 0, "reads_seen": 0, "doubt_a": 0, "doubt_b": 0, "doubt_c": 0,
                             "cleared_repeat": 0, "cleared_no": 0, "question_turns": 0, "fired": 0,
                             "fired_confirm": 0, "fired_hedge": 0, "explained_skip": 0, "offer_yes": 0,
                             "offer_no": 0, "doubts_live": len(doubts)}
    first = {"read": None}
    orig_read = memo.read

    def read401(turn, prev_reply=""):  # the first read of a turn is the reader's own, before any layer edits it
        out = orig_read(turn, prev_reply)
        if first["read"] is None:
            first["read"] = out
        return out

    memo.read = read401
    pending_offer = {"key": None}

    def save():
        try:
            Path(path).write_text(json.dumps(doubts, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        st["doubts_live"] = len(doubts)

    def key(d):
        return (d["s"], d["r"], d["v"])

    def turn401(text):  # type: ignore[no-untyped-def]
        t = str(text)
        st["turns"] += 1
        offered = pending_offer["key"]
        pending_offer["key"] = None
        if offered is not None:
            yn = L310._norm_yesno(t)
            for d in doubts:
                if key(d) == offered:
                    if yn in L310.NO310:
                        doubts.remove(d)
                        st["offer_no"] += 1
                        st["cleared_no"] += 1
                    elif yn in L310.YES310:
                        d["confirmed"] = True
                        st["offer_yes"] += 1
                    save()
                    break
        before = _triples(loop)
        first["read"] = None
        reply = inner(t)
        read = first["read"]
        frame = read[0] if isinstance(read, (tuple, list)) and read and isinstance(read[0], dict) else None
        if frame is None:
            return reply
        st["reads_seen"] += 1
        after = _triples(loop)
        if frame.get("act") != "ASK":
            new, repeats = doubts_from_frame(frame, t, before)
            changed = False
            for k in repeats:
                for d in list(doubts):
                    if key(d) == k:
                        doubts.remove(d)
                        st["cleared_repeat"] += 1
                        changed = True
            have = {key(d) for d in doubts}
            for d in new:
                if key(d) in after and key(d) not in have:
                    doubts.append(dict(d, confirmed=False))
                    have.add(key(d))
                    st["doubt_" + d["rule"]] += 1
                    changed = True
            if changed:
                save()
        if not (frame.get("act") == "ASK" or "?" in t):
            return reply
        st["question_turns"] += 1
        said = " ".join(p for p in (reply or []) if p) if isinstance(reply, list) else str(reply or "")
        if not said.strip() or said.rstrip().endswith("?"):
            return reply
        live = [d for d in doubts if key(d) in after]
        keys = {key(d) for d in live}
        for d in live:
            if not _names(said, d["v"]):
                continue
            if explained_by_other(d["v"], keys, after, t + " " + said):
                st["explained_skip"] += 1
                continue
            offer = d.get("new")
            st["fired"] += 1
            if offer and not d.get("confirmed"):
                loop.lis314_confirming = dict(offer)
                loop.lis310_pending = None
                pending_offer["key"] = key(d)
                out = L314.CONFIRM_FMT314.format(claim=L314.claim314(offer))
                st["fired_confirm"] += 1
            else:
                out = HEDGE401.format(claim=claim401(d["s"], d["r"], d["v"]))
                st["fired_hedge"] += 1
            loop.lis310_prev = out
            return [out]
        return reply

    turn401.__name__ = "turn401"
    loop.turn = turn401
    loop.sf401_path = path
    log = os.environ.get("SF401_LOG")
    if log:
        def _dump():
            try:
                with open(log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(st, sort_keys=True) + "\n")
            except OSError:
                pass
        atexit.register(_dump)
    return loop


def build_02c_sf401(state_dir, args):
    """0.2c's build_02c (scripts/claude_e2e02c.py, sealed) plus install_sf401 right after the listener stack."""
    import claude_e2e02c as E02C
    import claude_lis_stackb as STACK
    orig = STACK.build_stack

    def build_stack401(loop, reader, threshold, layers=("313", "315", "314"), log_dir=None):
        out = orig(loop, reader, threshold, layers=layers, log_dir=log_dir)
        install_sf401(loop, loop.lis_memo)
        return out

    STACK.build_stack = build_stack401
    try:
        loop = E02C.build_02c(state_dir, args)
    finally:
        STACK.build_stack = orig
    if getattr(loop, "sf401_stats", None) is None:
        raise RuntimeError("sf401: build_02c did not go through claude_lis_stackb.build_stack")
    loop.layers330c = ["sf401"] + list(getattr(loop, "layers330c", []))
    return loop
