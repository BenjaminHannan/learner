#!/usr/bin/env python3
"""Experiment 120c O5: wire51 replay with ONLY the Mouth slot replaced.

Byte-for-byte copy of scripts/fable_talker120_replay.py except the mouth
import: Talker120cMouth (120 mouth + contract-template fallback for
non-six statuses) instead of TalkerMouth. wire51 files untouched.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fable_agent_loop as A
import fable_wire51_adapters as AD
import fable_wire51_run as W
from fable_talker120c_mouth import Talker120cMouth


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tok", required=True)
    ap.add_argument("--replay", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-root", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out)
    state_root = Path(args.state_root) if args.state_root else out.parent / "replay-runs"

    shared = Talker120cMouth(args.ckpt, args.tok)
    original = AD.build_loop

    def build(*a, **kw):
        loop, parts = original(*a, **kw)
        parts["mouth"] = shared
        loop.mouth = shared
        return loop, parts

    AD.build_loop = build
    try:
        report = W.replay(state_root, args.replay, ears_mode="auto",
                          sleep_threshold=A.SLEEP_THRESHOLD, base_url=None,
                          checkpoint=None, seed=4102)
    finally:
        AD.build_loop = original
    report["mouth"] = {"ckpt": str(args.ckpt), "says": shared.says,
                       "fallbacks": shared.fallbacks, "reasons": shared.reasons}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    summary = {k: report.get(k) for k in ("turns", "taught_rows", "wrong_writes",
                                          "missing_writes", "correct_answers", "wrong_answers",
                                          "abstentions", "missed_abstentions",
                                          "two_hop_correct", "sleeps", "unexpected_entities")}
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
