#!/usr/bin/env python3
"""Experiment 117 -- patch the genuine bugs from red team 110, on top of loop102.

Loop117 = loop102 + three SMALL additive fixes, subclass/wrap only. No
existing file is edited; everything new lives in this file.

  (1) F5 PLEASE-FORGET SPACE: loop102's please-strip did
      ``"forget" + t[m.end(1):]`` which drops the space (``"forgetMira city"``
      never matches the forget verb), so the "Please forget ..." shape was
      unreachable end-to-end and the stale value kept being answered.
      Loop117Ears._parse_forget is loop102's byte-identical except the strip
      keeps one space: ``"forget " + t[m.end(1):]``.
  (2) M5 SHOUTED POSSESSIVE: FakeEars ``_APOS`` (``['']s\\b``) matches a
      lowercase 's only, so shouted possessives (``"MIRA'S CITY IS OSLO"``,
      ``"WHO IS MIRA'S CITY?"``) never split and the turn clarifies. This
      file applies a runtime-only override of the module global
      ``fable_agent_loop._APOS`` to ``[''][sS]\\b`` (no file edited; the
      override lives and dies with this process). Stored relation keys are
      unchanged (FakeEars._relation still lowercases to the same key).
  (3) UNDERSCORE LEAK: internal relation keys leaked into English replies
      (``"Saved: Roberto Merhi's country_of_citizenship is Spain."``,
      ``"I don't know T01's maternal_grandmother."``). Loop117Mouth wraps the
      loop102 mouth and renders ``_`` as `` `` in the final English sentence
      only; stored relation keys are byte-identical.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop117_agent.py --daemon --dir DIR \\
    --config artifacts/fable-loop117-20260922/loop117-config.json
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

import fable_agent_loop as A  # noqa: E402 (Protocols + base loop, read-only)
import fable_fix77_core as F77  # noqa: E402 (gate + reasoner + seal, read-only)
import fable_loop102_agent as L102  # noqa: E402 (whole loop102 build, read-only)
import fable_loop90_agent as L90  # noqa: E402 (whole loop90 build, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Fix (2): shouted possessives must split exactly like lowercase ones. The
# base FakeEars._chain does re.split(_APOS, ...) against this module global
# at call time, so overriding the global here (this process only, no file
# edited) fixes every FakeEars instance in the wrapped chain.
A._APOS = r"['\u2019][sS]\b\s*"


class Loop117Ears(L102.Loop102Ears):
    """Loop102Ears with the F5 please-strip space restored.

    _parse_forget is loop102's implementation byte-identical except one
    line: ``"forget " + t[m.end(1):]`` keeps the space the please-prefix
    consumed, so "Please forget Mira city" reaches the forget verb.
    """

    def _parse_forget(self, text: str):
        """-> (name, relation) | 'AMBIG' | None. None = not a forget turn."""
        t = text
        m = L102._PLEASE_FORGET_RE.match(t)
        if m:
            t = "forget " + t[m.end(1):]
        if not L102._FORGET_VERB_RE.match(t):
            return None
        if t.rstrip().endswith("?"):
            return None
        m = L102._FORGET_THAT_RE.match(t)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        m = L102._FORGET_POSS_RE.match(t)
        if m:
            return (m.group(1).strip(), m.group(2).strip())
        # Raw M1 shape "forget <Name...> <rel>": never a teach ("is" inside
        # means the sentence teaches; e.g. "Forget's city is Lisbon." never
        # reaches here anyway for lack of the verb+space shape).
        if L102._IS_VERB_RE.search(t):
            return None
        rest = L102._FORGET_VERB_RE.sub("", t, count=1).strip().rstrip(
            ".").strip()
        toks = rest.split()
        if len(toks) < 2:
            return None
        return (" ".join(toks[:-1]).strip(), toks[-1].strip())


class Loop117Mouth:
    """Fix (3): render relation keys with spaces in replies, store unchanged.

    Wraps the loop102 mouth; the final English sentence gets ``_`` -> `` ``.
    Actions, relation keys, and notebook rows are never touched.
    """

    name = "loop117-mouth"

    def __init__(self, inner) -> None:
        self.inner = inner

    def say(self, record: dict) -> str:
        return str(self.inner.say(record)).replace("_", " ")


class Loop117AgentLoop(L102.Loop102AgentLoop):
    """Loop102AgentLoop unchanged (the forget2 action path is already right)."""


DEFAULT_CONFIG117: dict = copy.deepcopy(L102.DEFAULT_CONFIG102)
DEFAULT_CONFIG117["ears"]["stand_in"] = (
    "Loop117Ears (loop102 pre-filter + F5 please-space fix) over Loop96Ears = "
    "GuardedEars91 over ChainEars(bench73 template + FakeEars templates, "
    "M5 shouted-possessive split via runtime _APOS override)")
DEFAULT_CONFIG117["mouth"]["stand_in"] = (
    "Loop117Mouth over FakeMouth (template sentences; relation keys rendered "
    "with spaces in replies only, stored keys unchanged)")
DEFAULT_CONFIG117["daemon"]["module"] = "Loop117Daemon (this file)"


def build_agent117(cfg: dict | None = None) -> Loop117AgentLoop:
    """Build the loop102 agent shape with the three loop117 fixes swapped in."""
    cfg = dict(DEFAULT_CONFIG117, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop117Mouth(A.FakeMouth())
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4117)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop117AgentLoop(
        state_dir, ears=Loop117Ears(Loop96Ears(chain)), mouth=mouth,
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
    return loop


class Loop117Daemon(L102.Loop102Daemon):
    """Loop102Daemon shape with the loop117 agent (F5 byte-safe kept)."""

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
        self.loop = build_agent117(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon117(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop117Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 117 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop102)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG117 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG117)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG117)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon117(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent117(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
