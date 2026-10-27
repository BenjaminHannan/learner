#!/usr/bin/env python3
"""Merge 138k -- staged merge: 138j + the 228 src guard + the 220 restart index.

loop138k = loop138j (scripts/fable_loop138j_agent.py, unchanged, read-only)
         + exp 228 SrcGuardMixin228 / install_srcguard228
           (scripts/claude_fix228_srcguard.py): fix170's _src_of only trusts
           the live cached triples list (kills the 1-in-800 run-to-run flip)
         + exp 220 FixedIndexedLoopNotebook
           (scripts/fable_fix220_restartindex.py): after a restart the fast
           index holds every event exactly once (kills the restart ghost).
Nothing else. No existing file is edited.

How 220 is applied (same mechanism exp 220 used on 138i,
scripts/fable_loop220_agent.py:build_agent220): the only notebook
construction site in the whole 138 lineage is
L138d.Loop138dAgentLoop.__init__ (scripts/fable_loop138d_agent.py:221),
which reads the module global L138d.IndexedLoopNotebook. 138f's __init__
delegates to it; 138g/h/i/j and every 138j layer-C mixin define no
__init__. RestartIndex220Mixin swaps that global for
FixedIndexedLoopNotebook only while the agent is being built, and restores
it before returning (process-local; base builds elsewhere untouched).
build_agent138k asserts the built notebook really is the fixed class.

Coverage audit (merge 138k design note, design/v3/30-modes/138k-merge-opus.md):
every 138j path that reads stored facts reads either the source of truth
(nb.facts / nb.events / nb.active: 154f negate, 154g replace, 192 Updated,
154b helpers) or the inner fast index that 220 rebuilds (_triples via the
170-cached L90.notebook_triples for 190/190b reverse lookup; _sr/_sro via
the 142 compose paths). fix170's list caches are keyed by
(inner notebook, len(events)) and are rebuilt from inner._triples. No
138j path keeps its own cache outside the 220 rebuild.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/claude_loop138k_agent.py --daemon --dir DIR \\
    --config artifacts/claude-merge138k-20260922/loop138k-config.json
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

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
import fable_fix220_restartindex as F220  # noqa: E402 (220 notebook, read-only)
import fable_loop138d_agent as L138d  # noqa: E402 (patch site, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (base, read-only)

# 228: installed at import (and again, idempotently, by the daemon mixin).
G228.install_srcguard228()

DEFAULT_CONFIG138K: dict = copy.deepcopy(L138J.DEFAULT_CONFIG138J)
DEFAULT_CONFIG138K["notebook"]["class"] = (
    "FixedIndexedLoopNotebook (scripts/fable_fix220_restartindex.py: "
    "IndexedLoopNotebook with _load indexing each event exactly once)")
DEFAULT_CONFIG138K["daemon"]["module"] = (
    "Loop138kDaemon (this file): SrcGuardMixin228 > RestartIndex220Mixin "
    "> Loop138jDaemon")
DEFAULT_CONFIG138K["merge138k"] = {
    "base": "loop138j (scripts/fable_loop138j_agent.py)",
    "added": ["228 src guard (scripts/claude_fix228_srcguard.py)",
              "220 restart index (scripts/fable_fix220_restartindex.py)"],
}


def _with_fixed_notebook(fn, *args, **kwargs):
    """Run fn with L138d.IndexedLoopNotebook -> FixedIndexedLoopNotebook."""
    orig = L138d.IndexedLoopNotebook
    L138d.IndexedLoopNotebook = F220.FixedIndexedLoopNotebook  # type: ignore[misc]
    try:
        return fn(*args, **kwargs)
    finally:
        L138d.IndexedLoopNotebook = orig  # type: ignore[misc]


def build_agent138k(cfg: dict | None = None):
    """Build the loop138j agent shape with the 220 fixed notebook inside."""
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG138K, **(cfg or {}))
    loop = _with_fixed_notebook(L138J.build_agent138j, cfg)
    if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
        raise RuntimeError("138k: notebook is not FixedIndexedLoopNotebook")
    loop.notes.append("loop138k: loop138j + 228 src guard + 220 "
                      "FixedIndexedLoopNotebook (restart indexes each "
                      "event exactly once)")
    return loop


class RestartIndex220Mixin:
    """Daemon mixin: the agent built by the base daemon's __init__ gets
    the 220 fixed notebook (swap active only during construction)."""

    def __init__(self, *args, **kwargs):
        _with_fixed_notebook(super().__init__, *args, **kwargs)
        loop = getattr(self, "loop", None)
        if loop is not None:
            if not isinstance(loop.nb, F220.FixedIndexedLoopNotebook):
                raise RuntimeError(
                    "138k: notebook is not FixedIndexedLoopNotebook")
            loop.notes.append("loop138k: loop138j + 228 src guard + 220 "
                              "FixedIndexedLoopNotebook")


class Loop138kDaemon(G228.SrcGuardMixin228, RestartIndex220Mixin,
                     L138J.Loop138jDaemon):
    """Loop138jDaemon + 228 guard + 220 restart index. Nothing else."""


def run_daemon138k(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop138kDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    import fable_loop90_agent as L90  # noqa: E402 (thinker module, read-only)
    parser = argparse.ArgumentParser(description="Merge 138k (138j+228+220)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG138K to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None)
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG138K)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG138K)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon138k(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent138k(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
