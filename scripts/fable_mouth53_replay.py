#!/usr/bin/env python3
"""Experiment 53 O5: wire51 replay with ONLY the Mouth slot replaced.

wire51 (fable_wire51_run / fable_wire51_adapters) is imported read-only, never
edited: we monkeypatch build_loop in our own process to swap TemplateMouth for
our Mouth, then call the runner's own replay() on a state root inside OUR
artifact folder. Ears/reasoner/sleeper/thinker settings are wire51's defaults.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fable_agent_loop as A
import fable_wire51_adapters as AD
import fable_wire51_run as W
from fable_mouth53_mouth import Mouth


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--replay", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-root", default=None)
    args = ap.parse_args(argv)
    out = Path(args.out)
    state_root = Path(args.state_root) if args.state_root else out.parent / "replay-runs"

    shared = Mouth(args.adapter)
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
    report["mouth"] = {"adapter": str(args.adapter), "says": shared.says,
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
