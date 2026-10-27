#!/usr/bin/env python3
"""Experiment 144 -- loop129b + the exp-144 multi-"of"-name mixin (ONE CHANGE).

loop144 = loop129b + fable_fix144_ofname, subclass only. No existing file is
edited; everything new lives in this file (+ scripts/fable_fix144_ofname.py).

  Loop144Ears(Loop129bEars): hear() delegates to the exact loop129b path
    first. Only when loop129b returns a single one-fact-at-a-time clarify
    ("could you split that?") is the turn re-examined: if it parses as ONE
    teach triple (bench73 template first, else the exp-92 extra patterns,
    same preprocessing as Loop121Ears) whose value passes the exp-144
    screen -- i.e. the ONLY refusal reason was length and the value is a
    single capitalised "of"-name with no embedded teach frame -- the
    structured teach/correct action the chain would have built is returned
    instead. Every other turn (including every genuine two-fact message,
    which always trips another screen or the frame backstop) is
    byte-identical to loop129b, stage tags included.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop144_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix144-20260922/loop144-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench73_english_arm as B73  # noqa: E402 (teach patterns, read-only)
import fable_fix144_ofname as F144  # noqa: E402 (this experiment's mixin)
import fable_loop121_agent as L121  # noqa: E402 (parse helpers, read-only)
import fable_loop102_agent as L102  # noqa: E402 (pre-filter logic, read-only)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


def _parse_single_teach(turn: str) -> tuple[tuple[str, str, str], bool] | None:
    """Mirror Loop121Ears teach preprocessing; return (triple, correction).

    bench73 template first, else the exp-92 extra patterns -- the same
    order and the same qualifier/correction/forget handling as
    fable_loop121_agent.py:171-227. None when the turn is not one teach.
    """
    text = " ".join(str(turn).split())
    if not text or text.rstrip().endswith("?"):
        return None
    if L102.is_hearsay(text):
        return None
    stripped = L102.strip_correction_prefix(text)
    if stripped is not None:
        cand = L102._cap1(L102.strip_trailing_qualifier(stripped))
        if not cand:
            return None
        triple = B73.hear_teach_template(cand)
        if triple is None:
            triple = L121.hear_teach_extra(cand)
        if triple is None:
            return None
        return triple, True
    t = text
    m = L102._PLEASE_FORGET_RE.match(t)
    if m:
        t = "forget" + t[m.end(1):]
    if L102._FORGET_VERB_RE.match(t):
        return None
    cand = L102.strip_trailing_qualifier(text)
    if not cand:
        return None
    triple = B73.hear_teach_template(cand)
    if triple is None:
        triple = L121.hear_teach_extra(cand)
    if triple is None:
        return None
    return triple, False


class Loop144Ears(L129b.Loop129bEars):
    """Loop129bEars + the exp-144 single-of-name upgrade on SPLIT clarifies."""

    name = "loop144-ofname"

    def hear(self, turn: str) -> list[dict]:
        actions = super().hear(turn)
        if (len(actions) == 1 and actions[0].get("act") == "clarify"
                and "split that" in str(actions[0].get("text", "")).lower()
                and getattr(self, "nb", None) is not None):
            parsed = _parse_single_teach(turn)
            if parsed is not None:
                triple, correction = parsed
                if (not L102.subject_is_hearsay_shaped(triple[0])
                        and F144.screen_value_144(triple[2]) is None):
                    if correction:
                        action = self._structured_correct(triple)
                    else:
                        action = self._bench73_action(triple)
                    action["stage"] = "loop144"
                    self.last_stage, self.last_score = "loop144-ofname", 1.0
                    return [action]
        return actions


DEFAULT_CONFIG144: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG144["ears"]["stand_in"] = (
    "Loop144Ears (loop129b + exp-144 single-of-name upgrade: a SPLIT clarify "
    "becomes the structured teach/correct only when the turn parses as one "
    "teach whose value is a single capitalised of-name with no embedded "
    "teach frame) over loop129b chain")
DEFAULT_CONFIG144["daemon"]["module"] = "Loop144Daemon (this file)"


def build_agent144(cfg: dict | None = None) -> L129b.Loop129bAgentLoop:
    """Build the loop129b agent shape with Loop144Ears swapped in."""
    cfg = dict(DEFAULT_CONFIG144, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop144Ears
    loop.ears.name = Loop144Ears.name
    return loop


class Loop144Daemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop144 agent inside (mailbox same)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent144(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon144(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop144Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 144 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG144 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG144)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG144)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon144(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent144(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
