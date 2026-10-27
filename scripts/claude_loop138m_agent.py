#!/usr/bin/env python3
"""Merge 138m -- 138l + the conversation line: 219, 230, 230c (with 230b),
227, 227b, 227c, 224c (with 224), 233, 234. New file only; every piece
module is imported read-only and its OWN functions/classes are reused.

loop138m = loop138l (scripts/claude_loop138l_agent.py: 138k + 209, 212,
           216, 222, 223, 226; its ears class Loop138lEars is reused as is)
  loop  + 233 Loop233AgentLoop.turn   polite-negative rewrite at entry
                                       (scripts/claude_loop233_agent.py)
        + 226 Source226Mixin           (as in 138l)
        + 234 Loop234Mixin             how-are-you fixed reply
                                       (scripts/claude_loop234_agent.py)
        + NameLine230cMixin (this file) 219 D8 notebook check
                                       (fable_fix219_selfname.ground219_reply)
                                       then the sealed 230 -> 230b -> 230c
                                       turn bodies, run verbatim
        + Identity227cMixin (this file) 227/227b/227c identity gate
                                       (claude_loop227c_agent.gate227c),
                                       ahead of 138j's 187 self gate
        + 212, 216, 209 loop layers    (as in 138l)
        > Loop138jAgentLoop ...
  instance (after the build, as on 224/224c's own stacks):
        + 224 install_decline224       glue -> one sentence per turn type
        + 224c install_q1honest224c    Q1 only when the notebook confirms

ORDER (outermost first) and why:
  224c/224 instance wrappers  -- they are instance-level on their own stack
      (wrap the whole built turn) and swap ONLY the exact glued decline with
      intent DECLINE, so every other layer's reply passes through untouched.
      138j's 188 swap runs earlier (inside the 138j turn), so a
      statement-shaped glue turn already carries 188's sentence and 224's S1
      never sees it: 188 wins on statement-shaped turns.
  233  -- rewrites the raw text first, as on its own stack (it was the only
      loop layer over 223). Every layer below sees the plain question,
      exactly as if the user had typed it.
  226  -- as in 138l: sees the final reply of everything below it (identity,
      small talk, name line), so its classification matches what was said.
  234  -- post-swap on a whole-turn how-are-you match with 0 writes; it sits
      above the identity and name layers, so on a turn both claim, 234 wins.
  NameLine230c -- 230c's "Yes."/"No." rules are post-processing of the 219
      reply; the 219 check is a swap of G168.grounded_self_answer for the
      turn (138j's turn reads it by module attribute, as 219's turn did).
  Identity227c -- swaps L187.classify_self187 / L187.self187_answer for the
      turn so the 227c gate (227 exact templates with 227b's "My name is
      Premonition.", then 227c's widened matcher) runs FIRST in 138j's
      notebook-miss branch; 187's own patterns still run when 227c misses.
      So on a turn both claim, the 227 line wins over 187 (Ben's name).
  212/216/209 -- unchanged from 138l.

How the classes get in: as in 138l, build_agent138j (read-only) constructs
L138J.Loop138jEars / L138J.Loop138jAgentLoop by module-global name; this
file swaps them (and L138J.build_agent138j, to add the 224/224c instance
wrappers before the daemon's boot reconcile) only while the agent is built
(process-local, restored in finally).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)

G228.install_srcguard228()  # 228 first, at import

import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138l_agent as L138L  # noqa: E402 (base, read-only)
import claude_loop224c_agent as L224C  # noqa: E402 (piece, read-only)
import claude_loop227c_agent as L227C  # noqa: E402 (piece, read-only)
import claude_loop230_agent as L230  # noqa: E402 (piece, read-only)
import claude_loop230c_agent as L230C  # noqa: E402 (piece, read-only)
import claude_loop233_agent as L233  # noqa: E402 (piece, read-only)
import claude_loop234_agent as L234  # noqa: E402 (piece, read-only)
import fable_fix168_ground as G168  # noqa: E402 (swap site, read-only)
import fable_fix219_selfname as F219  # noqa: E402 (piece, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)
import fable_loop187_agent as L187  # noqa: E402 (swap site, read-only)
import fable_loop209_agent as L209  # noqa: E402 (read-only)
import fable_loop212_agent as L212  # noqa: E402 (read-only)
import fable_loop216_agent as L216  # noqa: E402 (read-only)
import fable_loop224_agent as L224  # noqa: E402 (piece, read-only)
import fable_loop226_agent as L226  # noqa: E402 (read-only)

_ORIG_EARS = L138J.Loop138jEars      # 138j originals (138l swaps them only
_ORIG_LOOP = L138J.Loop138jAgentLoop  # during its own builds)
_ORIG_BUILD = L138J.build_agent138j
_ORIG_G168 = G168.grounded_self_answer
_ORIG_C187 = L187.classify_self187
_ORIG_A187 = L187.self187_answer


class _Swap:
    """Set module attributes for the duration of a with-block."""

    def __init__(self, pairs):
        self.pairs = pairs
        self.saved = []

    def __enter__(self):
        for mod, name, val in self.pairs:
            self.saved.append((mod, name, getattr(mod, name)))
            setattr(mod, name, val)
        return self

    def __exit__(self, *exc):
        for mod, name, val in reversed(self.saved):
            setattr(mod, name, val)
        return False


# ------------------------------------------------ identity line (227/b/c)
class _Hit227c(str):
    """A 187 'kind' string that carries the 227c gate's (intent, answer)."""

    hit: tuple = ()


def _classify227c_first(text: str):
    hit = L227C.gate227c(text)  # 227 exact (227b NAME text) -> 227c widened
    if hit is not None:
        k = _Hit227c("identity227c")
        k.hit = hit
        return k
    return _ORIG_C187(text)


def _answer227c_first(loop, kind, text):
    if isinstance(kind, _Hit227c):
        return kind.hit  # (intent tag, sheet answer), as 227c logs them
    return _ORIG_A187(loop, kind, text)


class Identity227cMixin:
    """227c's identity gate at the top of 138j's notebook-miss branch."""

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        with _Swap([(L187, "classify_self187", _classify227c_first),
                    (L187, "self187_answer", _answer227c_first)]):
            return super().turn(text)  # type: ignore[misc]


# ------------------------------------------------ name line (219/230/b/c)
def _grounded219(loop, text: str, intent: str) -> str:
    """fix168's grounded self answer + 219's D8 notebook check."""
    base = _ORIG_G168(loop, text, intent)
    try:
        nb = loop.nb
    except AttributeError:
        return base
    return F219.ground219_reply(nb, intent, base)


class NameLine230cMixin:
    """219's check inside the turn; 230 -> 230b -> 230c bodies verbatim.

    Loop230cAgentLoop.turn calls Loop230bAgentLoop.turn, which calls
    Loop230AgentLoop.turn, which calls L219.Loop219AgentLoop.turn by module
    attribute. For the turn only, claude_loop230_agent.L219 is a namespace
    whose Loop219AgentLoop.turn is the 138m turn below this layer run with
    the 219 grounding swapped in.
    """

    def turn(self, text: str) -> list[str]:  # type: ignore[no-untyped-def]
        below = super().turn  # type: ignore[misc]

        def turn219(_self, t):
            with _Swap([(G168, "grounded_self_answer", _grounded219)]):
                return below(t)

        shim = types.SimpleNamespace(
            Loop219AgentLoop=types.SimpleNamespace(turn=turn219))
        with _Swap([(L230, "L219", shim)]):
            return L230C.Loop230cAgentLoop.turn(self, text)


# ------------------------------------------------------------ classes
Loop138mEars = L138L.Loop138lEars  # ears unchanged from 138l


class Loop138mAgentLoop(L233.Loop233AgentLoop, L226.Source226Mixin,
                        L234.Loop234Mixin, NameLine230cMixin,
                        Identity227cMixin, L212.Loop212AgentLoop,
                        L216.Loop216AgentLoop, L209.WriteScreen209LoopMixin,
                        _ORIG_LOOP):
    """138l loop + 233 rewrite + 234 small talk + name line + identity."""


def _mro_names(cls) -> list[str]:
    return [c.__name__ for c in cls.__mro__]


_L = _mro_names(Loop138mAgentLoop)
assert _L[:11] == ["Loop138mAgentLoop", "Loop233AgentLoop",
                   "Loop223AgentLoop", "Source226Mixin", "Loop234Mixin",
                   "NameLine230cMixin", "Identity227cMixin",
                   "Loop212AgentLoop", "Loop216AgentLoop",
                   "WriteScreen209LoopMixin", "Loop138jAgentLoop"], _L
assert _L.index("Loop138jAgentLoop") < _L.index("Loop138iAgentLoop"), _L
assert "turn" not in vars(L233.L223.Loop223AgentLoop)  # empty class


def _build138j_plus224c(cfg=None):
    """build_agent138j (read-only) + 224 + 224c instance wrappers."""
    loop = _ORIG_BUILD(cfg)
    L224.install_decline224(loop)
    L224C.install_q1honest224c(loop)
    return loop


def _with_138m(fn, *args, **kwargs):
    with _Swap([(L138J, "Loop138jEars", Loop138mEars),
                (L138J, "Loop138jAgentLoop", Loop138mAgentLoop),
                (L138J, "build_agent138j", _build138j_plus224c)]):
        return fn(*args, **kwargs)


NOTE138M = ("loop138m: loop138l + 233 polite rewrite + 234 small talk + "
            "219/230/230b/230c user-name line + 227/227b/227c identity "
            "(Premonition) + 224/224c one-sentence declines")

DEFAULT_CONFIG138M: dict = copy.deepcopy(L138L.DEFAULT_CONFIG138L)
DEFAULT_CONFIG138M["daemon"]["module"] = (
    "Loop138mDaemon (scripts/claude_loop138m_agent.py) over Loop138kDaemon")
DEFAULT_CONFIG138M["self"] = dict(DEFAULT_CONFIG138M.get("self", {}))
for _src in (L230C.DEFAULT_CONFIG230C, L227C.DEFAULT_CONFIG227C):
    for _k, _v in _src.get("self", {}).items():
        if _k.startswith("rule2"):
            DEFAULT_CONFIG138M["self"][_k] = _v
DEFAULT_CONFIG138M["self"]["rule224"] = (
    "224 + 224c instance wrappers (scripts/fable_loop224_agent.py, "
    "scripts/claude_loop224c_agent.py): the exact glued decline with intent "
    "DECLINE becomes one sentence per turn type; Q1 only when confirmed")
DEFAULT_CONFIG138M["self"]["rule233"] = (
    "233 polite negative questions rewritten to the plain question "
    "(scripts/claude_loop233_agent.py polite_rewrite)")
DEFAULT_CONFIG138M["self"]["rule234"] = (
    "234 how-are-you turns with 0 writes get the fixed small-talk reply "
    "(scripts/claude_loop234_agent.py)")
DEFAULT_CONFIG138M["merge138m"] = {
    "base": "loop138l (scripts/claude_loop138l_agent.py)",
    "added": ["219 D8 user-name notebook check",
              "230 'Yes.' only on yes/no questions",
              "230b/230c name check compares or fails closed",
              "227/227b/227c identity sheet (My name is Premonition.)",
              "224/224c one decline sentence per turn type, honest Q1",
              "233 polite negative questions rewritten",
              "234 how-are-you fixed reply"],
    "loop_mro": _L[:12],
    "instance": ["turn224c(turn224(class turn))"],
}


def _check(loop):
    if not isinstance(loop, Loop138mAgentLoop):
        raise RuntimeError("138m: loop is not Loop138mAgentLoop")
    inner = getattr(loop, "_inner138j_ears", None)
    if not isinstance(inner, Loop138mEars):
        raise RuntimeError("138m: inner ears are not Loop138lEars")
    import fable_fix220_restartindex as F220
    if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
        raise RuntimeError("138m: notebook is not FixedIndexedLoopNotebook")
    if not G228.is_installed():
        raise RuntimeError("138m: 228 guard not installed")
    t = vars(loop).get("turn")
    if t is None or getattr(t, "__name__", "") != "turn224c":
        raise RuntimeError("138m: 224c turn wrapper not installed")
    if not hasattr(loop, "decline224_log"):
        raise RuntimeError("138m: 224 not installed")
    loop.notes.append(NOTE138M)


def build_agent138m(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG138M, **(cfg or {}))
    loop = _with_138m(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes138mMixin:
    """Daemon mixin: 228 guard first, then 138k's daemon __init__ with the
    138m classes and the 224c-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_138m(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop138mDaemon(Classes138mMixin, L138K.Loop138kDaemon):
    """Loop138kDaemon + the 138l pieces + the 138m conversation line."""


def run_daemon138m(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    return Loop138mDaemon(root, cfg=cfg, idle_seconds=idle_seconds).run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Merge 138m (138l + 9)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138M)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG138M)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138m(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138m(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
