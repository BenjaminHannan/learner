#!/usr/bin/env python3
"""Exp F1 agent: 292t plus 241b's sealed reply rewriter as the outermost layer.

F1 (talking line, design/v3/30-modes/talk-fluency-plan.md section "F1") is
one change on 292t (scripts/claude_loop292t_agent.py, read-only):

  292t, then 241b's rewriter outermost.

The rewriter is 241b's sealed code path: per reply line,
scripts/claude_loop241b_agent.render_line (imported read-only), which
parses the line back into a frame (claude_mouth241b_parse), renders stage-A
candidates (claude_mouth241b_say), and keeps the first candidate passing
brake v2 (claude_mouth241b_brake rules 1-9); otherwise the 292t line is kept
byte-identical (sev-1 logged). Unframed lines pass through byte-identical.
Stats keys (mouth241b_stats) and log schema (mouth241b_log, MOUTH241B_LOG
env) are identical to 241b's. The mouth has no notebook handle beyond a
read-only entity-name list for brake rule 3; it cannot write.

Installation note (one documented difference from 241b, forced by 292t's
architecture): 241b installs Mouth241bMixin at the front of the loop class
and its base dispatches turn() through the class. 292t installs its whole
talking stack as instance attributes (loop.turn = turn282b
closure chaining via loop.turn281_inner etc.), which shadow any class-level
turn -- verified: installing 241b's mixin class alone on a 292t loop never
runs (0 mouth stats over 4 probe turns). So F1 installs the mouth the way
292t's own layers install (outermost, instance): loop.turnf1_inner captures
292t's turn282b chain, and the outermost instance turn runs 241b's exact
per-line render_line over its output. The mixin class is still placed at
the front of the loop class (isinstance checks hold) and the instance turn
is its bound method.

New files here: this agent only (+ its config
artifacts/claude-f1-20260923/loopf1-config.json). No existing file is
edited. Piece files (scripts/claude_mouth241b_*.py,
scripts/claude_loop241b_agent.py) are imported unchanged.
"""

from __future__ import annotations

import copy
import sys
import types
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_loop241b_agent as L241B  # noqa: E402 (rewriter, read-only)
import claude_loop292t_agent as T292T  # noqa: E402 (base, read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)

NOTEF1 = ("loopf1: 292t + 241b rewriter outermost (render_line exactly as "
          "241b; re-renders reply lines only; writes untouched)")


class MouthF1Mixin:
    """Outermost turn(): 292t's instance stack, then 241b's exact rewrite.

    Body mirrors Mouth241bMixin.turn line for line; the only difference is
    the inner dispatch (self.turnf1_inner, i.e. 292t's turn282b chain)
    because super().turn() on a 292t loop would bypass the talking layers.
    """

    def turn(self, text):
        lines = self.turnf1_inner(text)
        if not hasattr(self, "mouth241b_stats"):
            self.mouth241b_stats = Counter()
            self.mouth241b_log = []
        try:
            names = [str(n) for n in getattr(self.nb, "entities", {}).values()]
        except Exception:  # noqa: BLE001
            names = []
        records = list(getattr(self, "last_records", []) or [])
        out = []
        for line in (lines or []):
            if not isinstance(line, str):
                out.append(line)
                continue
            r = L241B.render_line(line, records, names)
            self.mouth241b_stats[r["route"]] += 1
            if r["route"] == "legacy":
                self.mouth241b_stats["sev1"] += 1
            if r.get("why") == L241B.AMBIGUOUS_IDENTICAL:
                self.mouth241b_stats["ambiguous_identical"] += 1
            entry = {"turn": text, "in": line, "out": r["text"],
                     "route": r["route"], "act": r["act"],
                     "why": r.get("why"), "ms": round(r["ms"], 4),
                     "sev1_fails": r["fails"] if r["route"] == "legacy"
                     else [],
                     "frame": r.get("frame")}
            self.mouth241b_log.append(entry)
            import json as _json
            import os as _os
            logp = _os.environ.get("MOUTH241B_LOG")
            if logp:
                with open(logp, "a", encoding="utf-8") as fh:
                    fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")
            out.append(r["text"])
        return out


def _upgradef1(loop):
    """Install F1 mouth outermost on a built 292t loop (instance, in order)."""
    if isinstance(loop, MouthF1Mixin) and "turnf1_inner" in vars(loop):
        return loop
    inner_turn = loop.turn  # 292t's turn282b chain (instance attribute)
    if getattr(inner_turn, "__name__", "") != "turn282b":
        raise RuntimeError(
            "f1: expected 292t turn282b outermost, got "
            f"{getattr(inner_turn, '__name__', '')!r}")
    loop.turnf1_inner = inner_turn
    cls = type(loop)
    loop.__class__ = type("LoopF1AgentLoop", (MouthF1Mixin, cls), {
        "__module__": __name__,
        "__doc__": f"{cls.__name__} with MouthF1Mixin at the front."})
    loop.turn = types.MethodType(MouthF1Mixin.turn, loop)
    loop.notes.append(NOTEF1)
    return loop


def _check_f1(loop, tag: str) -> None:
    if not isinstance(loop, MouthF1Mixin):
        raise RuntimeError(f"{tag}: F1 mouth mixin not outermost")
    if getattr(loop.turnf1_inner, "__name__", "") != "turn282b":
        raise RuntimeError(f"{tag}: turn282b not under the F1 mouth")
    if getattr(loop.turn282b_inner, "__name__", "") != "turn282":
        raise RuntimeError(f"{tag}: 282 not under turn282b")
    if not isinstance(loop, T292T.L292.Loop292AgentLoop):
        raise RuntimeError(f"{tag}: loop is not Loop292AgentLoop")


DEFAULT_CONFIGF1: dict = copy.deepcopy(T292T.DEFAULT_CONFIG292T)
DEFAULT_CONFIGF1["daemon"]["module"] = (
    "LoopF1Daemon (scripts/claude_loopf1_agent.py) over "
    "Loop292tDaemon with 241b rewriter (render_line) outermost")
DEFAULT_CONFIGF1["self"] = dict(DEFAULT_CONFIGF1.get("self", {}))
DEFAULT_CONFIGF1["self"]["rulef1"] = (
    "F1 (scripts/claude_loopf1_agent.py): 241b render_line imported "
    "unchanged from scripts/claude_loop241b_agent.py, run outermost over "
    "292t's turn282b chain (instance install, as 292t's own layers); "
    "re-renders reply lines only through stage A + brake v2; "
    "fallback keeps the 292t line; never writes")
DEFAULT_CONFIGF1["expf1"] = {
    "base": "loop292t (scripts/claude_loop292t_agent.py)",
    "added": ["241b render_line outermost (unchanged import; instance "
              "install because 292t's stack is instance attributes)"],
    "instance": ["mouthf1(turn282b(turn282(turn280b(turn280(turn281("
                 "turn291(turn260(turn224c(turn224(class turn)))))))))"],
}


def build_agentf1(cfg: dict | None = None):
    cfg = dict(DEFAULT_CONFIGF1, **(cfg or {}))
    loop = T292T.build_agent292t(cfg)
    loop = _upgradef1(loop)
    _check_f1(loop, "f1")
    return loop


class LoopF1Daemon(T292T.Loop292tDaemon):
    """292t's daemon with the F1 mouth installed outermost after boot."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _upgradef1(self.loop)
        _check_f1(self.loop, "f1d")


assert issubclass(LoopF1Daemon, SrcGuardMixin228)


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Exp F1 (241b mouth on 292t)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIGF1)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIGF1)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return LoopF1Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agentf1(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
