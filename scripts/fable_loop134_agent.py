#!/usr/bin/env python3
"""Experiment 134 -- port, not new science: loop121 + the three loop117 fixes.

Loop134 = loop121 (teach-side phrasing coverage over the loop113b N-hop
router + loop102 fallback) with the three loop117 red-team fixes ported as
small mixin classes layered on the Loop121 classes. Same logic as loop117,
re-expressed as mixins; method resolution order is explicit:

    Loop134Ears(PleaseForgetSpaceMixin134,
                ShoutedPossessiveMixin134,
                Loop121Ears)

  MRO for hear(): Loop134Ears -> PleaseForgetSpaceMixin134 (no hear;
  provides _parse_forget) -> ShoutedPossessiveMixin134.hear (installs the
  shouted-possessive split around the turn, then super) -> Loop121Ears.hear
  (teach coverage; "?" side exact loop113b) -> ... -> Loop102Ears.hear,
  whose self._parse_forget resolves back to PleaseForgetSpaceMixin134.

    Loop134Mouth(UnderscoreSpaceMouthMixin134, FakeMouth)

  MRO for say(): Loop134Mouth -> UnderscoreSpaceMouthMixin134.say (renders
  "_" as " " in the final English sentence only) -> FakeMouth.say.

The three ported fixes (loop117 logic, unchanged):

  (1) F5 PLEASE-FORGET SPACE: Loop102Ears._parse_forget did
      ``"forget" + t[m.end(1):]``, dropping the space (``"forgetMira city"``
      never matches the forget verb), so "Please forget ..." was unreachable
      and the stale value kept being answered. PleaseForgetSpaceMixin134
      keeps one space: ``"forget " + t[m.end(1):]``. Byte-identical to
      Loop117Ears._parse_forget otherwise.
  (2) M5 SHOUTED POSSESSIVE: FakeEars ``_APOS`` (``['']s\\b``) matches a
      lowercase 's only, so shouted possessives (``"MIRA'S CITY IS OSLO"``,
      ``"WHO IS MIRA'S CITY?"``) never split and the turn clarifies.
      Loop117 applied a runtime-only override of the module global
      ``fable_agent_loop._APOS`` to ``[''][sS]\\b``. This file applies the
      identical override value at import (this process only, no file edited;
      stored relation keys unchanged -- FakeEars._relation still lowercases
      to the same key), and ShoutedPossessiveMixin134 re-asserts it at bind
      time so every Loop134Ears instance carries the fix.
  (3) UNDERSCORE LEAK: internal relation keys leaked into English replies
      (``"Saved: Roberto Merhi's country_of_citizenship is Spain."``,
      ``"I don't know T01's maternal_grandmother."``).
      UnderscoreSpaceMouthMixin134 renders ``_`` as `` `` in the final
      English sentence only (via super().say, i.e. FakeMouth); actions,
      relation keys, and notebook rows are never touched. Same output as
      Loop117Mouth, re-expressed as a mixin instead of a wrapper.

No existing file is edited; everything new lives in this file. Loop121
teach coverage (exp-92 employer/occupation/child patterns + Title-Case
and-name guard narrowing) and the loop113b question side are untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop134_agent.py --daemon --dir DIR \\
    --config artifacts/fable-loop134-20260922/loop134-config.json
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
import fable_loop102_agent as L102  # noqa: E402 (regexes, read-only)
import fable_loop121_agent as L121  # noqa: E402 (wrapped base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (chain + thinker, read-only)
from fable_wire51_adapters import (  # noqa: E402 (sleeper/thinker, read-only)
    HardGate46Sleeper)

# Fix (2): shouted possessives must split exactly like lowercase ones. The
# base FakeEars chain calls re.split(_APOS, ...) against this module global
# at call time, so overriding the global here (this process only, no file
# edited) fixes every FakeEars instance in the wrapped chain. Value is
# byte-identical to loop117's override; stored relation keys are unchanged.
_APOS_SHOUTED_134 = r"['\u2019][sS]\b\s*"
A._APOS = _APOS_SHOUTED_134


class PleaseForgetSpaceMixin134:
    """Fix (1): F5 please-strip space restored.

    _parse_forget is loop102's implementation byte-identical except one
    line: ``"forget " + t[m.end(1):]`` keeps the space the please-prefix
    consumed, so "Please forget Mira city" reaches the forget verb.
    Identical logic to Loop117Ears._parse_forget, re-expressed as a mixin
    so dynamic dispatch (Loop102Ears.hear calling self._parse_forget)
    picks it up through the whole loop121 fallback chain.
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


class ShoutedPossessiveMixin134:
    """Fix (2): M5 shouted-possessive split, mixin layer.

    The logic is the process-wide ``fable_agent_loop._APOS`` override to
    ``[''][sS]\\b`` (applied at import above, verbatim loop117 value).
    This mixin re-asserts it at bind time so the fix provably travels with
    every Loop134Ears instance; it defines no hear() itself, so
    Loop121Ears.hear runs unchanged underneath.
    """

    def bind(self, nb):
        A._APOS = _APOS_SHOUTED_134
        return super().bind(nb)


class UnderscoreSpaceMouthMixin134:
    """Fix (3): render relation keys with spaces in replies, store unchanged.

    Same output as Loop117Mouth (final English sentence gets ``_`` -> `` ``)
    re-expressed as a mixin over FakeMouth via super().say(). Actions,
    relation keys, and notebook rows are never touched.
    """

    name = "loop134-mouth"

    def say(self, record: dict) -> str:
        return str(super().say(record)).replace("_", " ")


class Loop134Ears(PleaseForgetSpaceMixin134, ShoutedPossessiveMixin134,
                  L121.Loop121Ears):
    """Loop121Ears + the three loop117 fixes (MRO explicit in module docstring).

    Teach coverage and the "?" question side are inherited unchanged from
    loop121; the fixes alter only: _parse_forget (fix 1, first in MRO),
    the _APOS split used by the inner FakeEars chain (fix 2, via bind),
    and reply rendering (fix 3, on the mouth, not here).
    """


class Loop134Mouth(UnderscoreSpaceMouthMixin134, A.FakeMouth):
    """FakeMouth with fix (3) layered by MRO (mixin first, base second)."""


class Loop134AgentLoop(L121.Loop121AgentLoop):
    """Loop121AgentLoop (forget2 action included); ears/mouth differ only."""


DEFAULT_CONFIG134: dict = copy.deepcopy(L121.DEFAULT_CONFIG121)
DEFAULT_CONFIG134["ears"]["stand_in"] = (
    "Loop134Ears (Loop121Ears teach coverage + N-hop router + loop102 "
    "fallback, with loop117 fixes ported as mixins: F5 please-space "
    "_parse_forget, M5 shouted-possessive _APOS split, underscore-space "
    "reply rendering on the mouth) over Loop121Ears over Loop113bEars over "
    "Loop102Ears pre-filter over Loop96Ears = GuardedEars91 over "
    "ChainEars(bench73 template + FakeEars templates); question side "
    "identical to loop121")
DEFAULT_CONFIG134["mouth"]["stand_in"] = (
    "Loop134Mouth (UnderscoreSpaceMouthMixin134 over FakeMouth: template "
    "sentences; relation keys rendered with spaces in replies only, stored "
    "keys unchanged)")
DEFAULT_CONFIG134["daemon"]["module"] = "Loop134Daemon (this file)"


def build_agent134(cfg: dict | None = None) -> Loop134AgentLoop:
    """Build the loop121 agent shape with the three loop117 fixes swapped in."""
    cfg = dict(DEFAULT_CONFIG134, **(cfg or {}))
    state_dir = Path(cfg.get("state_dir", "."))
    chain = L90.ChainEars(cfg)
    mouth = Loop134Mouth()
    reasoner = F77.QualifierAwareReasoner77()
    sleeper = HardGate46Sleeper(state_dir, reasoner=None, seed=4121)
    from fable_loop96_agent import Loop96Ears  # noqa: E402 (read-only wrap)
    loop = Loop134AgentLoop(
        state_dir, ears=Loop134Ears(Loop96Ears(chain)), mouth=mouth,
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


class Loop134Daemon(L121.Loop121Daemon):
    """Loop121Daemon shape with the loop134 agent inside (mailbox identical)."""

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
        self.loop = build_agent134(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon134(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop134Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 134 ported loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop121)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG134 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG134)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG134)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon134(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent134(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
