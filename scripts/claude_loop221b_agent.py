#!/usr/bin/env python3
"""Experiment 221b -- STORED-RELATION FALLBACK for questions, on loop221.

loop221b = loop221 (scripts/fable_loop221_agent.py, read-only) + ONE change:
StoredRel221bMixin sits OUTERMOST on the ears, outside TableAsk221Mixin.
It only looks at turns ending in "?" and only ever emits an ordinary
single-hop ask action, so no write path is reachable from it.

When it fires (and only then):
  (A) the whole 221 stack understood nothing (base_missed221: no actions,
      or only the not-understood clarify), OR
  (B) the 221 stack produced exactly one single-hop ask on a named subject
      that resolves, and NONE of that ask's keys has a current answering
      row (i.e. the reply would be the "I don't know X's R." abstain).
In both cases the question is read against the relation words the subject
ALREADY HOLDS as active TAUGHT facts (source == "taught" and nb.active:
never inferred, sleep-derived, web, proposed, retracted or superseded).
A value is served only when exactly one stored relation matches; else the
221 actions are returned unchanged (byte-identical reply).

Sealed matching rule (match221b):
  * The question must start with who/whom/what/which/when/where (or
    who's/what's/when's/where's), optionally after "do you know" /
    "can you tell me" / "could you tell me" / "tell me". No other
    you-word may appear. No "whose" anywhere. Yes/no questions never fire.
  * Subject: exactly one of {one known notebook entity named in the
    question (whole words, longest name wins), USER via my/me/i/mine}.
    USER is never scanned by name. Two different subjects -> no fire.
  * Inverse guards (no new backward readings): no fire if the subject is
    right after "by"; no fire if the question has " of " and the subject
    is not right after "of" (or "of my" for USER); no fire for
    "who/whom/what [does|do|did] SUBJECT ..." (subject acts, value is the
    object); "what/which NOUN does|do|did SUBJECT VERB" is read as in Q
    below, e.g. "What sport does Kim play?" -> {sport}.
  * Content words Q = question word tokens minus STOP221B and minus the
    subject's name tokens. Q must be non-empty. In the "what/which NOUN
    does SUBJECT VERB" shape, Q = the NOUN words, and the VERB words are
    optional: they may cover relation words but need not match.
  * Relation words W = the key split on "_" and spaces, minus STOP221B.
  * stem221b: lower-case; strip ONE suffix from
    ("ings","ing","ers","er","ions","ion","ies","es","ed","s") when at
    least 3 letters stay ("s" never stripped after "s"; "es" only after
    s/x/z/ch/sh, else "s"); then a final "e" is dropped when 4+ letters
    stay. founded~founding, graduate~graduation, coaches~coach,
    owns~owner, opening~open.
  * Match iff every stem of Q is a stem of W, and every stem of W not in
    Q is a GENERIC head (date, year, day, time, name, place, city, town,
    country, location), and the wh-type fits: when -> W has a TIME word;
    where -> W has a PLACE word; who/whom -> W has neither; what/which ->
    any.
  * Exactly ONE stored relation key of the subject matches -> ask on it.
    0 or 2+ -> no fire.
The ask reply is the loop's normal one-hop answer, which names the
stored relation ("Tova Renn's landlord is Ada Wren.").

No synonym lists (doctor/physician stays out of scope). The relation table
file and every earlier piece are read-only.

Daemon launch (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop221b_agent.py --daemon --dir DIR \\
    --config artifacts/claude-storedrel221b-20260922/loop221b-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop221_agent as L221  # noqa: E402 (wrapped base, read-only)
import fable_fix221_tableask as T221  # noqa: E402 (helpers, read-only)
import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)

STAGE221B = "loop221b-storedrel"
USER_KEY = T221.USER_KEY221

WH221B = ("who", "whom", "what", "which", "when", "where")
PREFIXES221B = ("do you know ", "can you tell me ", "could you tell me ",
                "tell me ")
SELF221B = frozenset({"you", "your", "yours", "yourself", "u", "ur"})
USERWORDS221B = frozenset({"my", "me", "i", "mine"})
STOP221B = frozenset("""
who whom what which when where whose how why s is are was were be been am
do does did has have had the a an of to for in on at by with from my me i
mine again please tell know name named called exactly currently now
""".split())
GENERIC221B = frozenset("""date year day time name place city town country
location""".split())
TIME221B = frozenset("date year day time anniversary birthday".split())
PLACE221B = frozenset("place city town country location".split())
_SUFFIXES = ("ings", "ing", "ers", "er", "ions", "ion", "ies", "es", "ed",
             "s")
_AUX = ("does", "do", "did")


def stem221b(w: str) -> str:
    w = w.lower()
    for suf in _SUFFIXES:
        if not w.endswith(suf) or len(w) - len(suf) < 3:
            continue
        if suf == "s" and w.endswith("ss"):
            break
        if suf == "es" and not re.search(r"(s|x|z|ch|sh)es$", w):
            continue  # fall through to plain "s"
        w = w[:-len(suf)]
        break
    if w.endswith("e") and len(w) >= 5:
        w = w[:-1]
    return w


def _toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower().replace("’", "'"))


def rel_words221b(key: str) -> list[str]:
    return [w for w in re.split(r"[_\s]+", str(key).lower())
            if w and w not in STOP221B]


def _taught_keys(nb, eid: str) -> dict[str, int]:
    """Active TAUGHT relation keys of entity eid -> count of rows."""
    out: dict[str, int] = {}
    for fact in nb.facts.values():
        if fact.get("subject") != eid or fact.get("source") != "taught":
            continue
        try:
            if not nb.active(fact["fact_id"]):
                continue
        except Exception:  # noqa: BLE001
            continue
        out[fact["relation"]] = out.get(fact["relation"], 0) + 1
    return out


def _user_eid(nb):
    for eid, name in nb.entities.items():
        if name == USER_KEY:
            return eid
    return None


def _find_subject(nb, qtoks: list[str]):
    """-> (eid, name, (start, end) token span or None for USER) | None."""
    hits = []
    for eid, name in nb.entities.items():
        if name == USER_KEY or not str(name).strip():
            continue
        nt = _toks(str(name))
        if not nt:
            continue
        n = len(nt)
        for i in range(len(qtoks) - n + 1):
            if qtoks[i:i + n] == nt:
                hits.append((i, i + n, eid, name))
    # keep maximal spans only (longest name wins over a contained one)
    keep = []
    for h in hits:
        if any(o is not h and o[0] <= h[0] and h[1] <= o[1]
               and (o[1] - o[0]) > (h[1] - h[0]) for o in hits):
            continue
        keep.append(h)
    ents = {h[2] for h in keep}
    user = bool(set(qtoks) & USERWORDS221B)
    if len(ents) + (1 if user else 0) != 1:
        return None
    if user:
        eid = _user_eid(nb)
        return (eid, USER_KEY, None) if eid else None
    spans = [h for h in keep]
    s = min(spans)
    return (s[2], s[3], (s[0], s[1]))


def match221b(nb, question: str):
    """Pure read of (question, notebook). -> dict or None (no fire)."""
    t = " ".join(str(question).split())
    if not t.endswith("?"):
        return None
    low = t.lower().replace("’", "'")
    for p in PREFIXES221B:
        if low.startswith(p):
            low = low[len(p):]
            break
    qt = _toks(low)
    if not qt or qt[0] not in WH221B:
        return None
    wh = qt[0]
    if set(qt) & SELF221B or "whose" in qt:
        return None
    subj = _find_subject(nb, qt)
    if subj is None:
        return None
    eid, name, span = subj
    if span is None:  # USER
        idxs = [i for i, w in enumerate(qt) if w in USERWORDS221B]
        s0, s1 = idxs[0], idxs[0] + 1
    else:
        s0, s1 = span
    # inverse guards
    if s0 > 0 and qt[s0 - 1] == "by":
        return None
    if "of" in qt and not (s0 > 0 and qt[s0 - 1] == "of"):
        return None
    if s0 >= 2 and qt[s0 - 1] in _AUX and wh in ("who", "whom", "what",
                                                 "which"):
        if wh in ("who", "whom") or s0 == 2:
            return None
        # "what/which NOUN does SUBJECT VERB": the NOUN words must all
        # match; the VERB words after the subject are optional (they may
        # cover relation words, but need not)
        q_words = [w for w in qt[1:s0 - 1] if w not in STOP221B]
        opt_words = [w for w in qt[s1:] if w not in STOP221B]
    else:
        q_words = [w for k, w in enumerate(qt)
                   if w not in STOP221B and not (s0 <= k < s1)]
        opt_words = []
    if not q_words:
        return None
    qs = {stem221b(w) for w in q_words}
    os_ = {stem221b(w) for w in opt_words}
    matches = []
    for key in _taught_keys(nb, eid):
        ws = rel_words221b(key)
        if not ws:
            continue
        wset = set(ws)
        rs = {stem221b(w) for w in ws}
        if not qs <= rs:
            continue
        rest = {w for w in ws if stem221b(w) not in qs | os_}
        if not rest <= GENERIC221B:
            continue
        is_time = bool(wset & TIME221B)
        is_place = bool(wset & PLACE221B)
        if wh == "when" and not is_time:
            continue
        if wh == "where" and not is_place:
            continue
        if wh in ("who", "whom") and (is_time or is_place):
            continue
        matches.append(key)
    return {"eid": eid, "name": name, "wh": wh, "q_words": q_words,
            "matches": matches}


def _would_abstain(nb, act: dict) -> str | None:
    """(B): single-hop named ask whose keys all have no current row ->
    the resolved entity id, else None."""
    rels = act.get("relations") or []
    if act.get("act") != "ask" or len(rels) != 1 or act.get("entity_id"):
        return None
    name = act.get("name")
    if not name:
        return None
    try:
        found = nb.resolve(str(name))
    except Exception:  # noqa: BLE001
        return None
    if getattr(found, "status", None) != "OK":
        return None
    eid = found.detail.get("entity_id")
    try:
        if nb.current(eid, str(rels[0])):
            return None
    except Exception:  # noqa: BLE001
        return None
    return eid


class StoredRel221bMixin:
    """Outermost ears mixin: stored-relation fallback (never writes)."""

    storedrel221b_log: list | None = None

    def hear(self, turn: str) -> list[dict]:  # type: ignore[no-redef]
        actions = super().hear(turn)  # type: ignore[misc]
        t = " ".join(str(turn).split())
        if not t.endswith("?") or not isinstance(actions, list):
            return actions
        nb = getattr(self, "nb", None)
        if nb is None:
            return actions
        want_eid = None
        if T221.base_missed221(actions):
            pass
        elif len(actions) == 1 and isinstance(actions[0], dict):
            want_eid = _would_abstain(nb, actions[0])
            if want_eid is None:
                return actions
        else:
            return actions
        m = match221b(nb, t)
        if m is None or len(m["matches"]) != 1:
            return actions
        if want_eid is not None and m["eid"] != want_eid:
            return actions
        key = m["matches"][0]
        act = {"act": "ask", "name": m["name"], "relations": [key],
               "stage": STAGE221B, "storedrel221b": key}
        if m["name"] == USER_KEY:
            act["me166"] = True
        try:
            self.last_stage, self.last_score = STAGE221B, 1.0
        except AttributeError:
            pass
        return [act]


class Loop221bEars(StoredRel221bMixin, L221.Loop221Ears):
    name = "loop221b-storedrel"


DEFAULT_CONFIG221B: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG221B["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"]
    + "; 221b stored-relation fallback outermost (taught keys only)")
DEFAULT_CONFIG221B["daemon"]["module"] = "Loop221bDaemon (this file)"


def build_agent221b(cfg: dict | None = None):
    """build_agent221 unchanged, then the ears object's class is swapped to
    Loop221bEars (a subclass of Loop221Ears; no state is touched)."""
    cfg = dict(DEFAULT_CONFIG221B, **(cfg or {}))
    loop = L221.build_agent221(cfg)
    ears, seen = loop.ears, 0
    while type(ears) is not L221.Loop221Ears and seen < 10:
        ears, seen = getattr(ears, "inner", None), seen + 1
    if type(ears) is not L221.Loop221Ears:
        raise RuntimeError("Loop221Ears not found under loop.ears")
    ears.__class__ = Loop221bEars
    loop.notes.append("loop221b: loop221 + StoredRel221bMixin outermost "
                      "(stored taught relation fallback; writes untouched)")
    return loop


class Loop221bDaemon(L221.Loop221Daemon):
    """Loop221Daemon shape with the 221b agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        self.pid = _os.getpid()
        self.boot_time = time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent221b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 221b stored-relation "
                                     "fallback on loop221")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG221B)
        out["thinker"]["module"] = L221.L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG221B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        d = Loop221bDaemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
        return d.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent221b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
