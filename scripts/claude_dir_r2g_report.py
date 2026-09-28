#!/usr/bin/env python3
"""R2g race table and verdict: the H3 addendum's arithmetic (scripts/claude_dir_h3_report_add1.py, imported unedited) on this design's runs.

Differences from calling add1 directly, and nothing else: (1) run folders are read from this design's own folder, where the runs are
named h3-pre-s{seed} and h3-fresh-s{seed} because add1 hard-codes those names ("h3" there means "the design under test": here R2g);
(2) the mechanism sentence of add1 (settle gate, dead gate, constant-g control) is not used; this design's own sentence comes from the
swap check (scripts/claude_dir_r2g_swapcheck.py read). It never changes the verdict word. Pure standard library.

  python3 scripts/claude_dir_r2g_report.py selftest
  python3 scripts/claude_dir_r2g_report.py --split dev|holdout --runs <eq-runs dir> --loop '<...>/loop-s{seed}-pre' --plain '<...>/plain-s{seed}-pre' \
      [--sleep-draws DIR] [--swap-design 'DIR/swap-design-s{seed}.json' --swap-loop 'DIR/swap-loop-s{seed}.json'] --out table.json
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h3_report_add1 as A  # noqa: E402
import claude_dir_r2g_swapcheck as S  # noqa: E402


def symmetry_sentence(word, swap_design, swap_loop):
    if not word.startswith("PASS"):
        return "no mechanism claim (not a PASS)"
    lines = []
    for seed in (0, 1):
        d = swap_design.format(seed=seed) if swap_design else None
        if not d or not Path(d).exists():
            return "PASS without the swap check: no symmetry claim"
        lines.append(S.read(d, swap_loop.format(seed=seed) if swap_loop else None))
    return " | ".join(f"seed {i}: {x}" for i, x in enumerate(lines))


def main(split, runs, loop, plain, out, sleep_dir=None, swap_design=None, swap_loop=None):
    res = A.build(split, runs, loop, plain, sleep_dir, None, None)
    if split == "holdout":
        res["verdict"], res["failing_gates"] = A.verdict(res["seeds"])
        res["symmetry_sentence"] = symmetry_sentence(res["verdict"], swap_design, swap_loop)
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for seed, row in res["seeds"].items():
        print(f"seed {seed}: F_eq design {row['h3']['F_eq']:.2f}, fresh {row['h3_fresh']['F_eq']:.2f}, loop {row['loop']['F_eq']:.2f}, "
              f"plain {row['plain']['F_eq']:.2f}; design-loop {row['F_eq_minus_loop']:+.2f}; F_few design {row['h3']['F_few']:.2f} "
              f"loop {row['loop']['F_few']:.2f} ({row['F_few_minus_loop']:+.2f})")
    if split == "holdout":
        print("verdict:", res["verdict"], res["failing_gates"])
        print("symmetry:", res["symmetry_sentence"])


def selftest():
    """End to end on the baseline's own raw files: the practised loop stands in for the design (so the verdict must be REJECTED, a tie),
    a copy of the plain net stands in for the fresh arm. Proves the wrapper reads the ruler's real JSON shape."""
    import shutil
    ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-fewex-20260927" / "eq-runs"
    if not (ART / "loop-s0-pre" / "holdout.json").exists():
        print("baseline raw files missing: selftest skipped")
        return
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for s in (0, 1):
            for name, src in (("h3-pre", "loop-s%d-pre"), ("h3-fresh", "loop-s%d-fresh")):
                shutil.copytree(ART / (src % s), d / f"{name}-s{s}")
        f = d / "table.json"
        main("holdout", d, str(ART / "loop-s{seed}-pre"), str(ART / "plain-s{seed}-pre"), f)
        r = json.loads(f.read_text())
        assert r["verdict"] == "REJECTED" and abs(r["seeds"]["0"]["F_eq_minus_loop"]) < 1e-9 and abs(r["seeds"]["0"]["h3"]["F_eq"] - 51.0) < 0.01
        assert abs(r["seeds"]["1"]["h3"]["F_eq"] - 51.29) < 0.01, r["seeds"]["1"]["h3"]["F_eq"]
        assert r["symmetry_sentence"] == "no mechanism claim (not a PASS)"
        main("dev", d, str(ART / "loop-s{seed}-pre"), str(ART / "plain-s{seed}-pre"), d / "dev.json")
    assert "no symmetry claim" in symmetry_sentence("PASS", None, None)
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        sys.exit(0)
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), required=True)
    p.add_argument("--runs", required=True)
    p.add_argument("--loop", required=True)
    p.add_argument("--plain", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--sleep-draws", default=None)
    p.add_argument("--swap-design", default=None)
    p.add_argument("--swap-loop", default=None)
    a = p.parse_args()
    main(a.split, a.runs, a.loop, a.plain, a.out, a.sleep_draws, a.swap_design, a.swap_loop)
