#!/usr/bin/env python3
"""Experiment 158c -- wh-city question rewriter on loop158b (Muse).

THE ONE CHANGE: a question rewriter stage in the ears, before the
fallback, mapping exactly five closed city/town question shapes onto the
"Where does <X> live?" question the base (loop158b) already answers, then
running the base unchanged.

Shapes (case-insensitive; trailing "?" or "." optional):
  (e1) "What city does <X> live in?"   -> "Where does <X> live?"
  (e2) "Which city does <X> live in?"  -> "Where does <X> live?"
  (e3) "What city is <X> in?"          -> "Where does <X> live?"
  (e4) "Which city is <X> in?"         -> "Where does <X> live?"
  (e5) "What town does <X> live in?"   -> "Where does <X> live?"

X may be a plain name ("Sue") or a possessive chain ("Kim's mother").
Gates (pass through unchanged unless ALL hold):
  - X resolves to a known entity or possessive chain of known entities,
    using the same rule as loop158b (first segment matches a taught
    subject/object case-insensitively; every further hop matches a taught
    (subject, relation) pair, last-wins, post-edit values;
    scripts/fable_loop158b_agent.py: _ctx/_resolve_x/chain_split).
  - The base (super().hear, i.e. the full loop158b stack incl. the 158b
    whrel rewriter) returned only clarify actions; the rewrite is then run
    through the base unchanged, and only an ask-bearing result is kept
    (any teach/correct/forget2/person/alias/forget/quote/answer in the
    second pass is discarded, so questions never write).

Look-alikes that stay byte-identical to loop158b (verified: none of the
five regexes match them): "What city is the capital of France?"
(no trailing "in"), "What city are you in?" (verb "are", not "is"),
"What city is best?" (no trailing "in"), "What city do you like?"
(different verb frame).

No existing file is edited; everything new lives in this file (+
artifacts/fable-whcity158c-20260922/loop158c-config.json + drivers).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop158c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-whcity158c-20260922/loop158c-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols, read-only)
import fable_daemon108_run as D108  # noqa: E402 (receipts+reconcile, read-only)
import fable_daemon141_settle as D141  # noqa: E402 (settle gate, read-only)
import fable_daemon74_run as D74  # noqa: E402 (log helpers, read-only)
import fable_loop138b_agent as B138  # noqa: E402 (wrapped base, read-only)
import fable_loop158b_agent as B158  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_notebook_contract as C  # noqa: E402 (statuses, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# ------------------------------------------------------- the five closed shapes
_RE_E1 = re.compile(
    r"^\s*what\s+city\s+does\s+(.+?)\s+live\s+in\s*[?.]?\s*$", re.I | re.S)
_RE_E2 = re.compile(
    r"^\s*which\s+city\s+does\s+(.+?)\s+live\s+in\s*[?.]?\s*$", re.I | re.S)
_RE_E3 = re.compile(
    r"^\s*what\s+city\s+is\s+(.+?)\s+in\s*[?.]?\s*$", re.I | re.S)
_RE_E4 = re.compile(
    r"^\s*which\s+city\s+is\s+(.+?)\s+in\s*[?.]?\s*$", re.I | re.S)
_RE_E5 = re.compile(
    r"^\s*what\s+town\s+does\s+(.+?)\s+live\s+in\s*[?.]?\s*$", re.I | re.S)
_SHAPE_RES = (_RE_E1, _RE_E2, _RE_E3, _RE_E4, _RE_E5)


def rewrite_whcity(question: str,
                   triples: list[tuple[str, str, str]]) -> str | None:
    """Map one closed city/town question onto "Where does <X> live?".

    Returns the rewritten question string, or None (pass through
    unchanged). Never writes; pure function of (question, triples).
    """
    rels, ents, fact = B158._ctx(triples)
    _ = rels
    text = " ".join(str(question).split())
    if not text:
        return None
    for rx in _SHAPE_RES:
        m = rx.match(text)
        if not m:
            continue
        x = str(m.group(1)).strip().rstrip("?.").strip()
        if not x:
            return None
        if B158._resolve_x(x, ents, fact) is None:
            return None
        return "Where does %s live?" % x
    return None


# ------------------------------------------------------------ ears: the one change
class Loop158cEars(B158.Loop158bEars):
    """Loop158bEars + the 158c wh-city rewriter before the fallback."""

    name = "loop158c-whcity"

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
            newq = rewrite_whcity(turn, triples)
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
            self.last_stage, self.last_score = ("loop158c-whcity", 1.0)
            return second
        self.last_stage, self.last_score = save_stage, save_score
        return actions


class Loop158cAgentLoop(B158.Loop158bAgentLoop):
    """Loop158bAgentLoop unchanged (turn() inherited verbatim)."""


DEFAULT_CONFIG158C: dict = copy.deepcopy(B158.DEFAULT_CONFIG158B)
DEFAULT_CONFIG158C["ears"]["stand_in"] = (
    "Loop158cEars (loop158b + 158c wh-city question rewriter "
    "(e1)-(e5) before the fallback; base run unchanged)")
DEFAULT_CONFIG158C["daemon"]["module"] = "Loop158cDaemon (this file)"


def build_agent158c(cfg: dict | None = None) -> Loop158cAgentLoop:
    """Build the loop158b shape with the 158c ears swapped in."""
    cfg = dict(DEFAULT_CONFIG158C, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = B138.Loop138bMouth()
    import fable_loop148b_agent as L148b  # noqa: E402 (read-only)
    reasoner = L148b.ScreenStatusReasoner148b()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop158cAgentLoop(
        state_dir, ears=Loop158cEars(Loop96Ears(chain)), mouth=mouth,
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
    loop.notes.append("sleep158c: Sleep145Reasoner + Sleep145Sleeper "
                      "(exp-145 retrofit as in 138b)")
    return loop


# ------------------------------------------------------------ L4: settle + exactly-once daemon
class Loop158cDaemon(B158.Loop158bDaemon):
    """Loop158bDaemon shape with the 158c agent inside + 141 settle gate.

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
        self.loop = build_agent158c(agent_cfg)
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
            files = self.settled_files()  # [158c] same settle rule as 158b
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


def run_daemon158c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop158cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 158c whcity loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop158b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG158C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG158C)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG158C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon158c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent158c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
