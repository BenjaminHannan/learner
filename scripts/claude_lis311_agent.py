#!/usr/bin/env python3
"""Exp 311 -- move the lis-310 listener plug-in onto the 292 base.

311 = 292 (scripts/claude_loop292_agent.py: build_agent292 +
    DEFAULT_CONFIG292 + Loop292Daemon, read-only) + the listener turn
    wrapper from lis-310 (scripts/claude_lis310_agent.py:
    install_turn310, read-only) with the real lis-300 Reader.

install_turn310 works on any built loop: it only uses loop.turn,
loop.turn310_inner, loop._act, loop.nb, loop.mouth, loop.dir and
loop.notes. 292's outermost instance wrapper is still turn291 (the 292
build keeps turn291 outside turn260), so turn310 sits outside turn291
exactly as on 310, and the 292 chain is untouched.

Threshold: the sealed lis-300 threshold T = 0.995
(artifacts/claude-lis300-20260923/THRESHOLD.txt). Default model dir:
~/premonition-models/lis300-merged/ (merged-reader sha256
112880d610173aef9b39715e0f6db51a16af8dece42dbd7132b83c0be8285324
as recorded in lis-300's RESULTS.md; the try-out driver verifies it).

CPU/MPS build for the Mac. Unit stub tests use a StubReader (no
weights); pass cfg['lis311']['reader']. Production passes
cfg['lis311']['model_dir'] (or relies on the default above).

New file only; no existing file is edited. Subclass/wrap like 310.
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

import claude_lis310_agent as L310  # noqa: E402 (turn310, read-only)
import claude_loop292_agent as B292  # noqa: E402 (base, read-only)

# ---------------------------------------------------------------- constants

DEFAULT_THRESHOLD311 = 0.995  # sealed lis-300 threshold (THRESHOLD.txt)
DEFAULT_MODEL311 = str(Path.home() / "premonition-models" / "lis300-merged")
LOG_NAME311 = "lis311_log.jsonl"


def _reader_from_cfg311(cfg: dict):
    liscfg = (cfg or {}).get("lis311", {}) or {}
    if liscfg.get("reader") is not None:
        return liscfg["reader"], float(liscfg.get("threshold",
                                                  DEFAULT_THRESHOLD311))
    model_dir = liscfg.get("model_dir") or DEFAULT_MODEL311
    import claude_lis300_read as READ  # noqa: E402 (needs weights)

    return READ.Reader(model_dir), float(liscfg.get(
        "threshold", DEFAULT_THRESHOLD311))


def build_agent311(cfg: dict | None = None):
    """292 base + the listener turn wrapper. cfg['lis311'] keys: reader (a
    StubReader in tests, a lis-300 Reader in production), model_dir
    (default ~/premonition-models/lis300-merged), threshold (default
    0.995)."""
    cfg = dict(DEFAULT_CONFIG311, **(cfg or {}))
    loop = B292.build_agent292(cfg)
    liscfg = cfg.get("lis311", {}) or {}
    reader, threshold = _reader_from_cfg311({"lis311": liscfg})
    try:
        state_dir = Path(loop.dir)
    except Exception:  # noqa: BLE001
        state_dir = Path(".")
    L310.install_turn310(loop, reader, threshold=threshold,
                         log_path=state_dir / LOG_NAME311)
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn310":
        raise RuntimeError("311: turn310 not installed")
    if getattr(loop.turn310_inner, "__name__", "") != "turn291":
        raise RuntimeError("311: turn291 not under turn310")
    notes = getattr(loop, "notes", None)
    if isinstance(notes, list) and not any("lis311" in n for n in notes):
        notes.append("lis311: 292 + listener turn310 (real lis-300 reader; "
                     "threshold 0.995; base rule chain never writes; writes "
                     "only via the teach/correct doorway; me stored as USER)")
    return loop


class Classes311Mixin:
    """Daemon mixin: 292 daemon init, then the 311 listener wrapper."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cfg = kwargs.get("cfg", None)
        if cfg is None and len(args) >= 2:
            cfg = args[1]
        cfg = dict(cfg or {})
        liscfg = dict(cfg.get("lis311", {}) or {})
        reader, threshold = _reader_from_cfg311({"lis311": liscfg})
        try:
            state_dir = Path(self.loop.dir)
        except Exception:  # noqa: BLE001
            state_dir = Path(".")
        L310.install_turn310(self.loop, reader, threshold=threshold,
                             log_path=state_dir / LOG_NAME311)


class Loop311Daemon(Classes311Mixin, B292.Loop292Daemon):
    """Loop292Daemon with the lis-300 listener turn wrapper installed."""


assert Classes311Mixin.__mro__[0].__name__ == "Classes311Mixin"

DEFAULT_CONFIG311: dict = copy.deepcopy(B292.DEFAULT_CONFIG292)
DEFAULT_CONFIG311["daemon"]["module"] = (
    "Loop311Daemon (scripts/claude_lis311_agent.py) over Loop292Daemon "
    "with the lis-300 listener turn wrapper (real reader + write compiler)")
DEFAULT_CONFIG311["lis311"] = {
    "base": "loop292 (scripts/claude_loop292_agent.py)",
    "reader": None,
    "model_dir": DEFAULT_MODEL311,
    "threshold": DEFAULT_THRESHOLD311,
    "threshold_note": ("sealed lis-300 threshold T = 0.995 "
                       "(artifacts/claude-lis300-20260923/THRESHOLD.txt)"),
    "weights_note": ("merged reader sha256 112880d6...e8285324 per "
                     "lis-300 RESULTS.md, at ~/premonition-models/"
                     "lis300-merged/"),
    "me_subject": ("owner 'me' is stored as subject USER, exactly how the "
                   "base stores 'my' facts"),
    "hook": "turn310 outside turn291 (outermost instance wrapper)",
    "log": LOG_NAME311,
}
DEFAULT_CONFIG311["merge311"] = {
    "base": "loop292 (scripts/claude_loop292_agent.py)",
    "added": ["lis-300 reader (real weights, lis300_read.py) + write "
              "compiler (lis300_compiler.py), outermost turn310 wrapper "
              "(install_turn310 from scripts/claude_lis310_agent.py)"],
    "instance": ["turn310(turn291(turn260(turn224c(turn224(class turn))))"],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lis-311 agent (292+listener)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD311)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG311)
        out.pop("lis311", None)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                            encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG311)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.model:
        cfg["lis311"] = dict(cfg.get("lis311", {}), model_dir=args.model,
                             threshold=args.threshold)
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop311Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent311(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
