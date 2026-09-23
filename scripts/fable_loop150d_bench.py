#!/usr/bin/env python3
"""Exp 150d G1 driver -- bench121 new + old fresh + Fable-Edit + bench132.

REUSES artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py BY
IMPORT (run_item/classify/summarize path, splits, row format); only the
agent module reference is repointed to loop150d and the output dir to this
exp's artifact folder. Compares per-item verdicts against loop138b's OWN
frozen rows (read-only). Bar: 0 new wrong vs loop138b on all 4 splits;
exactly one predicted move (bench132-4hop-152 wrong->correct).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop150d_bench.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop150d_agent as L150d  # noqa: E402 (agent under test)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hedgecase150d-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def load_bench138b():
    path = ART138B / "fable_loop138b_bench121.py"
    spec = importlib.util.spec_from_file_location(
        "fable_loop138b_bench121_reuse", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    B138 = load_bench138b()
    B138.ART = ART
    B138.L138b = L150d  # run loop150d through the 138b bench path
    rc = B138.main(["--agent", "loop138b", "--only", "all"])
    _ = rc
    # Own compare vs loop138b frozen rows (G1 bar; the driver's built-in
    # compare uses loop138 rows and is ignored for the verdict).
    tag = "loop138b"
    frozen = {
        "new_121_4hop": "fable_bench121_loop138b_new_121_4hop_rows.jsonl",
        "old_s2fresh_4hop": "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
        "edit200": "fable_bench121_loop138b_edit200_rows.jsonl",
        "bench132_4hop": "fable_bench121_loop138b_bench132_4hop_rows.jsonl",
    }
    new_rows = {
        "new_121_4hop": "fable_bench121_loop138b_new_121_4hop_rows.jsonl",
        "old_s2fresh_4hop": "fable_bench121_loop138b_old_s2fresh_4hop_rows.jsonl",
        "edit200": "fable_bench121_loop138b_edit200_rows.jsonl",
        "bench132_4hop": "fable_bench121_loop138b_bench132_4hop_rows.jsonl",
    }

    def load(p: Path) -> list[dict]:
        return [json.loads(l) for l in p.read_text(
            encoding="utf-8").splitlines() if l.strip()]

    fails, moves = 0, []
    for stag, fname in frozen.items():
        base = {r["id"]: r for r in load(ART138B / fname)}
        got = {r["id"]: r for r in load(ART / new_rows[stag])}
        assert set(base) == set(got), f"{stag} id mismatch"
        for rid, r in got.items():
            b = base[rid]
            if r["verdict"] != b["verdict"]:
                moves.append((stag, rid, b["verdict"], r["verdict"]))
                if b["verdict"] != "wrong" and r["verdict"] == "wrong":
                    fails += 1
                    print(f"  NEW-WRONG {stag} {rid}", flush=True)
    print(f"G1 moves vs loop138b rows: {len(moves)}", flush=True)
    for m in moves:
        print(f"  MOVE {m[0]} {m[1]}: {m[2]} -> {m[3]}", flush=True)
    predicted = [m for m in moves if m[1] == "bench132-4hop-152"
                 and m[2] == "wrong" and m[3] == "correct"]
    ok = (fails == 0 and len(moves) == 1 and len(predicted) == 1)
    print(f"G1 {'PASS' if ok else 'FAIL'}: new_wrong={fails} "
          f"moves={len(moves)} (predicted: bench132-4hop-152 wrong->correct)",
          flush=True)
    (ART / "bench150d-compare.json").write_text(
        json.dumps({"new_wrong": fails, "moves": moves, "pass": bool(ok)},
                   indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
