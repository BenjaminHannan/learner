#!/usr/bin/env python3
"""Exp 255 agent: 138m + ONE outermost text-only layer (fixed-reply text).

loop255 = loop138m (scripts/claude_loop138m_agent.py, read-only) with
scripts/claude_fix255_text.py installed as the OUTERMOST turn wrapper.

Why an instance wrapper: on 138m the outermost turn is already an
instance attribute (224c's turn224c over 224's turn224, installed after
the build), so a class mixin would sit INSIDE 224c and never see 224c's
decline sentences. The 255 wrapper is installed on the built loop after
138m's own checks pass, around turn224c, so it sees every final reply
line. It rewrites only whole reply strings that are exactly a fixed
template (claude_fix255_text.rewrite255); it never reads or writes the
notebook and never changes routing.

228 guard: installed at import and first thing in the daemon __init__.
SrcGuardMixin228 cannot be listed first in this daemon's bases because
138m's daemon already carries it inside Loop138kDaemon (Python's MRO
would reject the order); it stays the first guard in the MRO chain below
Text255DaemonMixin, exactly as in 138m, and Text255DaemonMixin calls
install_srcguard228() before anything else.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)

G228.install_srcguard228()

import claude_fix255_text as T255  # noqa: E402 (THE ONE CHANGE)
import claude_loop138m_agent as L138M  # noqa: E402 (base, read-only)

NOTE255 = ("loop255: 138m + claude_fix255_text outermost fixed-reply text "
           "rewrite (whole templates only; no routing, reading or writing)")


def install_text255(loop):
    """Wrap the loop's current (outermost) turn with the 255 text pass."""
    if getattr(loop, "text255_installed", False):
        return loop
    inner = loop.turn  # 138m: the turn224c instance wrapper
    loop.text255_log = []
    loop.text255_ms = []

    def turn255(text):
        lines = inner(text)
        t0 = time.perf_counter()
        if not lines:
            loop.text255_ms.append((time.perf_counter() - t0) * 1000.0)
            return lines
        out = []
        changed = False
        for line in lines:
            new, tid = T255.rewrite255(line)
            if tid is not None:
                changed = True
                entry = {"turn": text, "in": line, "out": new,
                         "template": tid}
                loop.text255_log.append(entry)
                logp = os.environ.get("TEXT255_LOG")
                if logp:
                    with open(logp, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.append(new)
        loop.text255_ms.append((time.perf_counter() - t0) * 1000.0)
        return out if changed else lines

    loop.turn = turn255
    loop.text255_installed = True
    loop.notes.append(NOTE255)
    return loop


def _check255(loop):
    t = vars(loop).get("turn")
    if t is None or getattr(t, "__name__", "") != "turn255":
        raise RuntimeError("255: text wrapper not outermost")
    if not G228.is_installed():
        raise RuntimeError("255: 228 guard not installed")


DEFAULT_CONFIG255: dict = copy.deepcopy(L138M.DEFAULT_CONFIG138M)
DEFAULT_CONFIG255["daemon"]["module"] = (
    "Loop255Daemon (scripts/claude_loop255_agent.py) over Loop138mDaemon")
DEFAULT_CONFIG255["self"]["rule255"] = (
    "255 fixed-reply text pass (scripts/claude_fix255_text.py): whole "
    "fixed templates rewritten to grammatical English; reply text only")


def build_agent255(cfg: dict | None = None):
    G228.install_srcguard228()
    loop = L138M.build_agent138m(cfg)
    install_text255(loop)
    _check255(loop)
    return loop


class Text255DaemonMixin:
    """228 guard first, then the whole 138m daemon build, then the 255
    wrapper on the built loop (before any turn is served)."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        super().__init__(*args, **kwargs)
        install_text255(self.loop)
        _check255(self.loop)


class Loop255Daemon(Text255DaemonMixin, L138M.Loop138mDaemon):
    """Loop138mDaemon + the 255 text pass as the outermost turn."""


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    parser = argparse.ArgumentParser(description="Exp 255 (138m + text)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG255)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG255)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return Loop255Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent255(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
