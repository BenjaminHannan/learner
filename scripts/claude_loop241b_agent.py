#!/usr/bin/env python3
"""Experiment 241b agent: base 228 (138i + 228 guard) + ONE change, the
mouth stage A v2 (claude_mouth241b_*; 241's layer with the brief's fixes).

241b additions here: an AMBIGUOUS line whose listed full names are not
all different passes through unchanged (route passthrough, why "ambiguous
identical names (owner: ambiguity handler)") and is counted in
mouth241b_stats["ambiguous_identical"]. 241 text follows.

The change: Mouth241bMixin at the front of the outermost loop class. It runs
after the base's whole turn() -- every reply string already exists, and
nothing downstream changes strings again. For each reply line it:
  1. parses the line back into a frame (claude_mouth241b_parse; lossless or
     not framed at all),
  2. renders the frame with stage A (claude_mouth241b_say candidates, in
     preference order),
  3. keeps the first candidate that passes brake v2 (claude_mouth241b_brake,
     rules 1-9); if none passes, the legacy line is kept and a sev-1 bug is
     logged.
Unframed lines pass through byte-identical and are counted. The mouth has
no notebook handle beyond a read-only list of entity names for brake rule
3; it cannot write.

The 228 _src_of guard is installed at import and by the daemon mixin
(SrcGuardMixin228 first in the daemon bases).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import claude_loop228_agent as L228  # noqa: E402 (base, read-only)
import fable_loop138i_agent as L138I  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import claude_mouth241b_brake as BRAKE  # noqa: E402
import claude_mouth241b_parse as PARSE  # noqa: E402
import claude_mouth241b_say as SAY  # noqa: E402

ROW_ACTS = {"ANSWER", "ANSWER_LIST", "YESNO_YES", "YESNO_NO",
            "YESNO_NOTKNOWN", "REVERSE", "ABSTAIN_MISSING", "BROKEN_CHAIN",
            "SAVED", "CONFLICT", "FORGOTTEN", "FORGOTTEN_ONE", "NOT_HAD"}


AMBIGUOUS_IDENTICAL = "ambiguous identical names (owner: ambiguity handler)"


def render_line(line: str, records=None, names=()) -> dict:
    """One base reply line -> {"text", "route", "act", "fails", "ms"}.
    route: A | legacy (sev-1: every A candidate failed the brake) |
           passthrough (unframed / no say row)."""
    t0 = time.perf_counter()
    fr = PARSE.parse(line, records)
    if fr is None:
        return {"text": line, "route": "passthrough", "why": "unframed",
                "act": None, "fails": [],
                "ms": (time.perf_counter() - t0) * 1000}
    act = fr["act"]
    if act == "AMBIGUOUS" and SAY.ambiguous_names(fr.get("choices") or []) \
            is None:
        return {"text": line, "route": "passthrough",
                "why": AMBIGUOUS_IDENTICAL, "act": act, "fails": [],
                "frame": _public(fr),
                "ms": (time.perf_counter() - t0) * 1000}
    if act in ROW_ACTS:
        row = SAY.row_for(fr["path"][-1]) if fr.get("path") else None
        if row is None:
            return {"text": line, "route": "passthrough", "why": "no say row",
                    "act": act, "fails": [],
                    "ms": (time.perf_counter() - t0) * 1000}
        fr["_row"] = row
    body = line
    prefix = PARSE.NOTE_DROPPED * len(fr.get("notes") or [])
    body = line[len(prefix):]
    all_fails = []
    for cand in SAY.candidates(fr):
        ok, fails = BRAKE.check(fr, cand, names, legacy=body)
        if ok:
            return {"text": prefix + cand, "route": "A", "act": act,
                    "fails": all_fails, "frame": _public(fr),
                    "ms": (time.perf_counter() - t0) * 1000}
        all_fails.append({"cand": cand, "fails": fails})
    return {"text": line, "route": "legacy", "why": "sev-1: A failed brake",
            "act": act, "fails": all_fails, "frame": _public(fr),
            "ms": (time.perf_counter() - t0) * 1000}


def _public(fr: dict) -> dict:
    return {k: v for k, v in fr.items() if not k.startswith("_")}


class Mouth241bMixin:
    """Outermost turn(): re-render every reply line through stage A."""

    def turn(self, text):
        lines = super().turn(text)
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
            r = render_line(line, records, names)
            self.mouth241b_stats[r["route"]] += 1
            if r["route"] == "legacy":
                self.mouth241b_stats["sev1"] += 1
            if r.get("why") == AMBIGUOUS_IDENTICAL:
                self.mouth241b_stats["ambiguous_identical"] += 1
            entry = {"turn": text, "in": line, "out": r["text"],
                     "route": r["route"], "act": r["act"],
                     "why": r.get("why"), "ms": round(r["ms"], 4),
                     "sev1_fails": r["fails"] if r["route"] == "legacy"
                     else [],
                     "frame": r.get("frame")}
            self.mouth241b_log.append(entry)
            logp = os.environ.get("MOUTH241B_LOG")
            if logp:
                with open(logp, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.append(r["text"])
        return out


def _upgrade241b(loop):
    if isinstance(loop, Mouth241bMixin):
        return loop
    cls = type(loop)
    loop.__class__ = type("Loop241bAgentLoop", (Mouth241bMixin, cls), {
        "__module__": __name__,
        "__doc__": f"{cls.__name__} with Mouth241bMixin at the front."})
    loop.notes.append("loop241b: 228 + Mouth241bMixin (outermost turn(); "
                      "re-renders reply lines only; writes untouched)")
    return loop


DEFAULT_CONFIG241B = copy.deepcopy(L228.DEFAULT_CONFIG228)
DEFAULT_CONFIG241B["daemon"]["module"] = (
    "Loop241bDaemon (scripts/claude_loop241b_agent.py)")


def build_agent241b(cfg: dict | None = None):
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG241B, **(cfg or {}))
    return _upgrade241b(L228.build_agent228(cfg))


class Loop241bDaemon(SrcGuardMixin228, L138I.Loop138iDaemon):
    """Loop138iDaemon with the 228 guard and the 241b mouth (A v2)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        _upgrade241b(self.loop)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 241b mouth stage A v2")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG241B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG241B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if not args.dir:
        ap.error("--daemon needs --dir")
    d = Loop241bDaemon(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
    return d.run()


if __name__ == "__main__":
    sys.exit(main())
