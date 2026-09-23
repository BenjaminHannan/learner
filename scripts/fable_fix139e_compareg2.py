#!/usr/bin/env python3
"""Experiment 139e G2 -- per-case compare of marks123 outputs vs marks139c.

Compares artifacts/fable-tail139e-20260922/marks139e against the frozen
artifacts/fable-tailwords139c-20260922/marks139c. Semantic level: per-case
verdict + reply/observed text. Byte level: normalized JSON (volatile keys
dropped: timings, tmp paths, pids, replied_before_kill counts,
statuses-metadata, sleep SKIP reason that names the agent file).
Bar: semantic moves only on PASSMARKS-predicted cases (predicted: none).

Usage: python -B scripts/fable_fix139e_compareg2.py [--out FILE]
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix139d_compareg2 as C139d  # noqa: E402 (compare logic, read-only)

ROOT = SCRIPTS.parent
C139d.NEW = ROOT / "artifacts" / "fable-tail139e-20260922" / "marks139e"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 139e G2 compare")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.out:
        return C139d.main(["--out", args.out])
    default = (ROOT / "artifacts" / "fable-tail139e-20260922"
               / "g2-compare.json")
    return C139d.main(["--out", str(default)])


if __name__ == "__main__":
    sys.exit(main())
