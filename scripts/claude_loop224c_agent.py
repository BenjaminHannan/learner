#!/usr/bin/env python3
"""Exp 224c -- loop224c: loop224 with an HONEST Q1 decline.

THE ONE CHANGE. loop224 (scripts/fable_loop224_agent.py, unchanged, reused
read-only) serves Q1 "I don't know that yet -- you haven't told me." on any
glue turn where the ears emitted an ask. In 224b's registered run a flake
(bench132-4hop-031) served Q1 for facts that HAD been taught. loop224c
keeps Q1 only when a read-only notebook check confirms the notebook holds
no live fact for what was asked; otherwise the Q1 reply becomes Q2
("I didn't understand that question -- could you say it another way?").

The check (q1_confirmed) sees only read-only views (types.MappingProxyType /
frozenset / tuples) built from the inner notebook's dicts. It is given no
notebook object and calls no notebook method, so it cannot write, append,
touch the fix170 triple cache, or change any index. Q1 is kept only if, for
EVERY ask the ears emitted on the turn:
  * the asked name is not a pronoun (me/my/his/...), and
  * known name: walking the asked relation chain from the named entity
    reaches a hop with NO live fact (any source; not retracted, not
    superseded). If every hop resolves -> the answer is stored -> Q2. If a
    hop's value cannot be followed (literal with no entity) -> unsure -> Q2.
    Extra misread guards at the empty hop: (a) if the entity there has a
    live fact whose relation word appears in the turn text but is not in
    the asked chain, the ears may have misread the relation -> Q2; (b) if
    the asked relation word is used by NO live fact in the notebook, it
    may be a synonym of a stored relation ("manager" for a taught "boss")
    or an inverse ("employee") that a word-level check cannot rule out
    -> Q2.
  * unknown name: no live fact has that name as its value, no known
    entity name (or any word of one, 3+ letters) appears in the turn
    text, and the asked name shares no such word with a known name
    ("Mira" for a taught "Mira Vell"; a misparsed subject like "the home
    of Mira Vell") -> else Q2.
  Known limit (disclosed): if BOTH a stored relation and its synonym are
  in use in the notebook, a word-level check cannot tell them apart.
Any exception or malformed ask -> Q2 (the safe direction).

Also installed (required by the 2026-09-22 rules for every new 138i-family
experiment): the exp-228 fix170 _src_of identity guard
(scripts/claude_fix228_srcguard.py), at import, in build_agent224c and as
the first daemon base -- copied from scripts/claude_loop228_agent.py.

Nothing else changes: S1, Q2, and every reply that is not exactly the Q1
sentence of a loop224 Q1 swap pass through byte for byte. The self logs are
updated to what was actually said (as loop224 does). No new sentence.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_decline224 as DEC  # noqa: E402 (sealed sentences)
import fable_loop224_agent as L224  # noqa: E402 (wrapped, read-only)
from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

Q1 = DEC.NEW_SENTENCES224["Q1"]
Q2 = DEC.NEW_SENTENCES224["Q2"]

PRONOUNS = frozenset(
    "i me my mine myself you your yours yourself he him his himself she her "
    "hers herself it its itself we us our ours they them their theirs "
    "this that who what someone somebody".split())
REL_STOP = frozenset("of in on at the a an is to for by and has had was "
                     "with from as".split())


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def _relnorm(s: str) -> str:
    return " ".join(str(s).replace("_", " ").strip().lower().split())


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).lower())


def notebook_view(nb) -> dict:
    """Read-only snapshot views of the inner notebook's dicts (no methods)."""
    inner = getattr(nb, "nb", nb)
    return {
        "facts": types.MappingProxyType(dict(inner.facts)),
        "entities": types.MappingProxyType(dict(inner.entities)),
        "aliases": types.MappingProxyType(
            {k: tuple(v) for k, v in inner.aliases.items()}),
        "retracted": frozenset(inner.retracted),
        "superseded": frozenset(inner.superseded),
    }


def _live(view, fact_id: str, fact) -> bool:
    return (fact_id not in view["retracted"]
            and fact_id not in view["superseded"])


def _ids_for(view, name: str) -> set[str]:
    key = _norm(name)
    ids = set(view["aliases"].get(key, ()))
    ids |= {eid for eid, disp in view["entities"].items()
            if _norm(disp) == key}
    return ids


def _show(view, value) -> str:
    if isinstance(value, dict) and "entity" in value:
        return view["entities"].get(value["entity"], value["entity"])
    if isinstance(value, dict):
        return str(value.get("literal", ""))
    return str(value)


def _rel_in_text(rel: str, words: list[str]) -> bool:
    for tok in _relnorm(rel).split():
        if len(tok) < 3 or tok in REL_STOP:
            continue
        stem = tok[:4]
        for w in words:
            if len(w) >= 3 and (w.startswith(stem) or tok.startswith(w[:4])
                                and len(w) >= 4):
                return True
    return False


def _one_ask_empty(view, ask: dict, text: str) -> tuple[bool, str]:
    name = ask.get("name")
    rels = ask.get("relations")
    if rels is None and ask.get("relation"):
        rels = [ask.get("relation")]
    if not isinstance(name, str) or not name.strip() or not rels \
            or not all(isinstance(r, str) and r.strip() for r in rels):
        return False, "malformed-ask"
    if _norm(name) in PRONOUNS:
        return False, "pronoun-subject"
    words = _words(text)
    live = [(fid, f) for fid, f in view["facts"].items()
            if _live(view, fid, f)]
    ids = _ids_for(view, name)
    if not ids:
        key = _norm(name)
        if any(_norm(_show(view, f.get("value"))) == key for _, f in live):
            return False, "unknown-subject-appears-as-value"
        low = " " + " ".join(words) + " "
        wset = set(words)
        nwords = set(_words(name))
        for disp in view["entities"].values():
            dws = _words(disp)
            dw = " ".join(dws)
            if dw and len(dw) >= 2 and f" {dw} " in low:
                return False, f"known-name-in-text:{disp}"
            part = {w for w in dws if len(w) >= 3}
            if part & nwords:
                return False, f"partial-known-name:{disp}"
            if part & wset:
                return False, f"known-name-word-in-text:{disp}"
        return True, "unknown-subject-no-facts"
    cur = set(ids)
    asked = {_relnorm(r) for r in rels}
    for hop, rel in enumerate(rels):
        rn = _relnorm(rel)
        hits = [f for _, f in live
                if f.get("subject") in cur and _relnorm(f.get("relation", ""))
                == rn]
        if not hits:
            for _, f in live:
                if f.get("subject") in cur:
                    frel = _relnorm(f.get("relation", ""))
                    if frel not in asked and _rel_in_text(frel, words):
                        return False, f"possible-misread-relation:{frel}"
            if not any(_relnorm(f.get("relation", "")) == rn
                       for _, f in live):
                return False, f"relation-new-to-notebook:{rn}"
            return True, f"empty-at-hop-{hop}:{rn}"
        nxt: set[str] = set()
        for f in hits:
            v = f.get("value")
            if isinstance(v, dict) and "entity" in v:
                nxt.add(v["entity"])
            else:
                nxt |= _ids_for(view, _show(view, v))
        if hop < len(rels) - 1 and not nxt:
            return False, f"unfollowable-at-hop-{hop}"
        cur = nxt
    return False, "answer-stored"


def q1_confirmed(view, asks: list, text: str) -> tuple[bool, list]:
    """True only if every ask is confirmed to have no stored answer."""
    asks = [a for a in asks if isinstance(a, dict) and a.get("act") == "ask"]
    if not asks:
        return False, ["no-ask"]
    reasons = []
    for a in asks:
        ok, why = _one_ask_empty(view, a, text)
        reasons.append(why)
        if not ok:
            return False, reasons
    return True, reasons


def _loop224_state(turn224) -> dict:
    """loop224's own per-turn tap state (its closure cell 'state'), read-only.

    Reusing it means loop224c adds no ears tap and no per-turn allocation
    on ordinary turns (the known 228 flake is allocation-order sensitive).
    """
    cells = dict(zip(turn224.__code__.co_freevars,
                     (c.cell_contents for c in turn224.__closure__)))
    state = cells["state"]
    if not isinstance(state, dict) or "acts" not in state:
        raise RuntimeError("loop224 tap state not found")
    return state


def install_q1honest224c(loop) -> None:
    loop.q1honest224c_log = []
    turn224 = loop.turn
    state224 = _loop224_state(turn224)
    dlog = loop.decline224_log

    def turn224c(text: str) -> list[str]:
        n_log = len(dlog)
        said = turn224(text)
        if not (len(said) == 1 and said[0] == Q1 and len(dlog) == n_log + 1
                and dlog[-1].get("kind") == "Q1"):
            return said
        asks = [a for a in state224["acts"]
                if isinstance(a, dict) and a.get("act") == "ask"]
        inner = getattr(loop.nb, "nb", loop.nb)
        n_ev = len(inner.events)
        try:
            ok, reasons = q1_confirmed(notebook_view(loop.nb), asks, text)
        except Exception as exc:  # noqa: BLE001 -- unsure -> Q2
            ok, reasons = False, [f"check-error:{type(exc).__name__}"]
        assert len(inner.events) == n_ev, "224c check wrote to the notebook"
        loop.q1honest224c_log.append({
            "text": text, "kept_q1": ok, "reasons": reasons,
            "asks": [{"name": a.get("name"),
                      "relations": a.get("relations")}
                     for a in asks]})
        if ok:
            return said
        routed = getattr(loop, "last_routed", None)
        if isinstance(routed, dict):
            routed["answer"] = Q2
            routed["decline224"] = "Q2"
            routed["decline224c"] = "Q1->Q2"
        try:
            loop.self_turn_log[-1]["reply"] = Q2
        except (AttributeError, IndexError):
            pass
        dlog[-1]["kind"] = "Q2"
        dlog[-1]["q1honest224c"] = reasons
        return [Q2]

    loop.turn = turn224c
    loop.notes.append("loop224c: Q1 only when a read-only notebook check "
                      "confirms nothing is stored for the ask; else Q2")


DEFAULT_CONFIG224C: dict = copy.deepcopy(L224.DEFAULT_CONFIG224)
DEFAULT_CONFIG224C["self"] = dict(DEFAULT_CONFIG224C.get("self", {}))
DEFAULT_CONFIG224C["self"]["q1honest224c"] = (
    "Q1 kept only when a read-only notebook check confirms no stored answer")
DEFAULT_CONFIG224C["daemon"] = {"module": "Loop224cDaemon (this file)"}


def build_agent224c(cfg: dict | None = None):
    install_srcguard228()
    loop = L224.build_agent224(cfg)
    install_q1honest224c(loop)
    return loop


class _Body224c(L224.Loop224Daemon):
    """Loop224Daemon.__init__ body with build_agent224c."""

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
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent224c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


class Loop224cDaemon(SrcGuardMixin228, _Body224c):
    """_Body224c with the 228 guard guaranteed installed (mixin first)."""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 224c loop224c")
    ap.add_argument("--config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None, help="daemon directory")
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--once", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG224C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop224cDaemon(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds).run()
    if args.once:
        if not args.state_dir:
            ap.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent224c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
