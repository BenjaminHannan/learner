#!/usr/bin/env python3
"""Experiment 158b -- relation-word question rewriter on loop138b (Muse).

THE ONE CHANGE: a question rewriter stage in the ears, before the
fallback, mapping relation-word question shapes onto the possessive
question the base already answers, then running the base unchanged.

Shapes (case-insensitive; "?" optional except (c) which requires it):
  (a) "What <R> is <X>?"      -> "What is <X>'s <R>?"
  (b) "What is the <R> of <X>?" -> "What is <X>'s <R>?"
  (c) "<X>'s <R>?" (bare)      -> "What is <X>'s <R>?"
  (d) fixed wh-to-relation table (module constants below, fixed before
      any panel read):
        "When is <X>'s birthday|anniversary?" -> that relation
        "How old is <X>?"      -> age
        "Where is <X> from?"   -> hometown, else birthplace (if in tables)
        "Where does <X> live?" -> city, else home (if in tables)

Gates (pass through unchanged unless ALL hold):
  - R normalises (same rule as FakeEars._relation: lower + underscores,
    scripts/fable_agent_loop.py) to a relation key present in the loop's
    own relation tables, i.e. the notebook triple relation set
    (scripts/fable_loop90_agent.py: notebook_triples).
  - X resolves to a known entity or a possessive chain of known entities:
    first segment matches a taught subject/object (case-insensitive) and
    every further hop matches a taught (subject, relation) pair
    (last-wins, post-edit values).
  - The base (super().hear, i.e. the full loop138b stack incl. the 132
    rewriter) returned only clarify actions; the rewrite is then run
    through the base unchanged, and only an ask-bearing result is kept
    (any teach/correct/forget2 in the second pass is discarded, so
    questions never write).

Fallback (untouched, cited): the base fallback is FakeEars' clarify
"[...] Could you say it another way?" (scripts/fable_agent_loop.py:148)
surfaced through AgentLoop._act (scripts/fable_agent_loop.py:350) and the
frozen loop138 decline rule (scripts/fable_loop138_agent.py:81-93); this
stage runs before that fallback and never alters it.

No existing file is edited; everything new lives in this file (+
artifacts/fable-whrel158b-20260922/loop158b-config.json + drivers).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop158b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-whrel158b-20260922/loop158b-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + _APOS, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_loop148b_agent as L148b  # noqa: E402 (screen reasoner, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop138b_agent as B138  # noqa: E402 (wrapped base, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# ---------------------------------------------------------------- fixed (d) table
# Written before any panel read; never derived from probe data.
WHEN_RELATIONS = ("birthday", "anniversary")
HOW_OLD_RELATION = "age"
WHERE_FROM_CANDIDATES = ("hometown", "birthplace")
WHERE_LIVE_CANDIDATES = ("city", "home")

_APOS_SPLIT = re.compile(r"['\u2019]s\b\s*", re.I)
_WH_LEAD = {"what", "who", "where", "when", "why", "how", "which", "whose",
            "is", "are", "do", "does", "did", "can", "could"}

_RE_A = re.compile(r"^\s*what\s+(.+?)\s+is\s+(.+?)\s*[?.]?\s*$", re.I | re.S)
_RE_B = re.compile(r"^\s*what\s+is\s+the\s+(.+?)\s+of\s+(.+?)\s*[?.]?\s*$",
                   re.I | re.S)
_RE_D_WHEN = re.compile(
    r"^\s*when\s+is\s+(.+?)['\u2019]s\s+(birthday|anniversary)\s*[?.]?\s*$",
    re.I | re.S)
_RE_D_OLD = re.compile(r"^\s*how\s+old\s+is\s+(.+?)\s*[?.]?\s*$", re.I | re.S)
_RE_D_FROM = re.compile(r"^\s*where\s+is\s+(.+?)\s+from\s*[?.]?\s*$",
                        re.I | re.S)
_RE_D_LIVE = re.compile(r"^\s*where\s+does\s+(.+?)\s+live\s*[?.]?\s*$",
                        re.I | re.S)


def norm_relation(surface: str) -> str:
    """Same rule as FakeEars._relation (fable_agent_loop.py)."""
    return "_".join(str(surface).strip().lower().split())


def chain_split(text: str) -> list[str]:
    return [p.strip() for p in _APOS_SPLIT.split(str(text).strip())
            if p.strip()]


def _ctx(triples: list[tuple[str, str, str]]):
    rels = {str(r) for _, r, _ in triples}
    ents: dict[str, str] = {}
    for s, _, o in triples:
        for e in (s, o):
            if str(e).strip() and str(e).strip().casefold() not in ents:
                ents[str(e).strip().casefold()] = str(e).strip()
    fact: dict[tuple[str, str], str] = {}
    for s, r, o in triples:
        fact[(str(s).strip().casefold(), str(r))] = str(o)
    return rels, ents, fact


def _resolve_x(x_text: str, ents: dict, fact: dict) -> str | None:
    parts = chain_split(x_text)
    if not parts:
        return None
    cur = parts[0]
    if cur.casefold() not in ents:
        return None
    for rel_part in parts[1:]:
        key = (cur.casefold(), norm_relation(rel_part))
        if key not in fact:
            return None
        cur = fact[key]
    return cur


def rewrite_whrel(question: str,
                  triples: list[tuple[str, str, str]]) -> str | None:
    """Map one relation-word question onto the canonical possessive form.

    Returns the rewritten question string, or None (pass through unchanged).
    Never writes; pure function of (question, triples).
    """
    rels, ents, fact = _ctx(triples)
    text = " ".join(str(question).split())
    if not text:
        return None

    def ok_pair(r_text: str, x_text: str) -> str | None:
        r = norm_relation(r_text)
        if not r or r in ("is", "are"):
            return None
        if r not in rels:
            return None
        x = str(x_text).strip().rstrip("?.").strip()
        if not x:
            return None
        if _resolve_x(x, ents, fact) is None:
            return None
        return "What is %s's %s?" % (x, r_text.strip())

    m = _RE_D_WHEN.match(text)
    if m:
        return ok_pair(m.group(2), m.group(1))
    m = _RE_D_OLD.match(text)
    if m:
        return ok_pair(HOW_OLD_RELATION, m.group(1))
    m = _RE_D_FROM.match(text)
    if m:
        x = str(m.group(1)).strip().rstrip("?.").strip()
        term = _resolve_x(x, ents, fact)
        if term is not None:
            for cand in WHERE_FROM_CANDIDATES:
                if (term.casefold(), cand) in fact:
                    return "What is %s's %s?" % (x, cand)
        for cand in WHERE_FROM_CANDIDATES:
            if cand in rels:
                return ok_pair(cand, m.group(1))
        return None
    m = _RE_D_LIVE.match(text)
    if m:
        x = str(m.group(1)).strip().rstrip("?.").strip()
        term = _resolve_x(x, ents, fact)
        if term is not None:
            for cand in WHERE_LIVE_CANDIDATES:
                if (term.casefold(), cand) in fact:
                    return "What is %s's %s?" % (x, cand)
        for cand in WHERE_LIVE_CANDIDATES:
            if cand in rels:
                return ok_pair(cand, m.group(1))
        return None
    m = _RE_B.match(text)
    if m:
        return ok_pair(m.group(1), m.group(2))
    m = _RE_A.match(text)
    if m:
        r_text = m.group(1).strip()
        if r_text.strip().lower() in ("is", "are", "the"):
            return None
        return ok_pair(r_text, m.group(2))
    # (c) bare possessive + "?": strictly requires the question mark.
    if text.rstrip().endswith("?"):
        core = text.rstrip()[:-1].strip()
        toks = core.split()
        if toks and toks[0].strip("?.").lower() not in _WH_LEAD:
            parts = chain_split(core)
            if len(parts) >= 2:
                r_text = parts[-1]
                x_text = "'s ".join(parts[:-1])
                return ok_pair(r_text, x_text)
    return None


# ------------------------------------------------------------ ears: the one change
class Loop158bEars(B138.Loop138bEars):
    """Loop138bEars + the 158b relation-word rewriter before the fallback."""

    name = "loop158b-whrel"

    def hear(self, turn: str) -> list[dict]:
        actions = super().hear(turn)
        if not actions or any((not isinstance(a, dict))
                              or a.get("act") != "clarify"
                              for a in actions):
            return actions  # base understood the turn: never touch it
        if getattr(self, "nb", None) is None:
            return actions
        try:
            triples = L90.notebook_triples(self.nb)
            newq = rewrite_whrel(turn, triples)
        except Exception:
            return actions
        if not newq:
            return actions
        save_stage, save_score = self.last_stage, self.last_score
        try:
            second = super().hear(newq)
        except Exception:
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        if not second or not all(isinstance(a, dict) for a in second):
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        if any(a.get("act") in ("teach", "correct", "forget2", "person",
                                "alias", "forget", "quote", "answer")
               for a in second):
            # Questions must never write: discard anything but ask/clarify.
            self.last_stage, self.last_score = save_stage, save_score
            return actions
        if any(a.get("act") == "ask" for a in second):
            self.last_stage, self.last_score = ("loop158b-whrel", 1.0)
            return second
        self.last_stage, self.last_score = save_stage, save_score
        return actions


class Loop158bAgentLoop(B138.Loop138bAgentLoop):
    """Loop138bAgentLoop unchanged (turn() inherited verbatim)."""


DEFAULT_CONFIG158B: dict = copy.deepcopy(B138.DEFAULT_CONFIG138B)
DEFAULT_CONFIG158B["ears"]["stand_in"] = (
    "Loop158bEars (loop138b + 158b relation-word question rewriter "
    "(a)-(d) before the fallback; base run unchanged)")
DEFAULT_CONFIG158B["mouth"]["stand_in"] = B138.DEFAULT_CONFIG138B["mouth"][
    "stand_in"]
DEFAULT_CONFIG158B["daemon"]["module"] = "Loop158bDaemon (this file)"


def build_agent158b(cfg: dict | None = None) -> Loop158bAgentLoop:
    """Build the loop138b shape with the 158b ears swapped in."""
    cfg = dict(DEFAULT_CONFIG158B, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = B138.Loop138bMouth()
    reasoner = L148b.ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop158bAgentLoop(
        state_dir, ears=Loop158bEars(Loop96Ears(chain)), mouth=mouth,
        reasoner=reasoner, sleeper=sleeper, sleep_threshold=int(cfg.get(
            "sleep_threshold", A.SLEEP_THRESHOLD)))
    loop.ears.bind(loop.nb)
    thinker, thinker_module = L90.build_thinker(loop.nb)
    loop.thinker = thinker
    loop.parts90 = {"ears": loop.ears, "mouth": mouth, "reasoner": reasoner,
                    "sleeper": sleeper, "thinker": thinker,
                    "thinker_module": thinker_module,
                    "tau_hat": dict(chain.tau), "tau_family": chain.family,
                    "tau_hat_used": chain.tau_hat,
                    "ears_chain_stages": list(chain.stage_names),
                    "config": cfg}
    loop._screen148b_tag = None
    loop.self_turn_log = []
    loop.self_mode_log = []
    loop.self_origin = {}
    loop.self_web_filings = []
    loop.self_sleep_history = []
    loop.self_forget_log = {}
    loop.self_routed = []
    loop.last_routed = None
    seed = int(cfg.get("sleep145_seed", cfg.get("sleep138_seed", cfg.get(
        "sleep104_seed", cfg.get("sleep131_seed", 1)))))
    import fable_sleep145_agent as S145  # noqa: E402 (read-only retrofit)
    S145.retrofit_sleep145(loop, state_dir, seed=seed)
    loop.notes.append("sleep158b: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit as in 138b)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop158bDaemon(B138.Loop138bDaemon):
    """Loop138bDaemon shape with the 158b agent inside + 141 settle gate.

    Name ends in Daemon / starts with Loop so the marks123 loader picks
    this class.
    """

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
        self.loop = build_agent158b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)

    def settled_files(self) -> list[Path]:
        files = sorted(p for p in self.inbox.glob("*.txt")
                       if not p.name.startswith(".")
                       and ".tmp" not in p.name)
        self.settle.prune({p.name for p in files})
        now = time.monotonic()
        return [p for p in files if self.settle.is_settled(p, now)]

    def run(self) -> int:
        for stale in self.outbox.glob("*.tmp*"):
            try:
                stale.unlink()
            except OSError:
                pass
        status = self.boot_status()
        D74._atomic_write(self.status_path,
                          json.dumps(status, indent=1, sort_keys=True))
        D74._append_log(self.log_path,
                        {"t": D74._now_iso(), "event": "boot", **status})
        self.write_heartbeat()
        last_heartbeat = time.time()
        last_activity = time.time()
        last_idle_tick = 0.0
        while True:
            if self.stop_file.exists():
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(),
                                 "event": "stop-file-seen"})
                self.write_heartbeat()
                D74._append_log(self.log_path,
                                {"t": D74._now_iso(), "event": "stopped"})
                return 0
            files = self.settled_files()  # [158b] same settle rule as 138b
            if files:
                for path in files:
                    if self.stop_file.exists():
                        break
                    try:
                        self.process_file(path)
                    except C.LogCorrupt as exc:
                        D74._append_log(
                            self.log_path,
                            {"t": D74._now_iso(), "event": "log-corrupt",
                             "file": path.name, "error": str(exc)})
                last_activity = time.time()
            else:
                now = time.time()
                if (now - last_activity >= self.idle_seconds
                        and now - last_idle_tick >= self.idle_seconds):
                    event = self.loop.step()
                    last_idle_tick = now
                    D74._append_log(
                        self.log_path,
                        {"t": D74._now_iso(), "event": "idle-tick",
                         "mode": event["mode"],
                         "detail": str(event["detail"])[:300],
                         "counters": dict(self.loop.counters)})
            if time.time() - last_heartbeat >= D74.HEARTBEAT_EVERY_S:
                self.write_heartbeat()
                last_heartbeat = time.time()
            time.sleep(D74.POLL_S)


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic-write client rule: write tmp in the same dir, then rename."""
    import os as _os
    tmp = Path(str(path) + ".tmp%d" % _os.getpid())
    tmp.write_text(text, encoding="utf-8")
    _os.replace(tmp, path)


def run_daemon158b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop158bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 158b whrel loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG158B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG158B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG158B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon158b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent158b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
