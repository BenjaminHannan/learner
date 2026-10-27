#!/usr/bin/env python3
"""Exp 142 S2 (REGISTERED): 5,000-turn reply byte-identity loop142 vs loop134.

128's C2 pattern on the loop134 lineage: first 5,000 seed-93 turns through
both agents in lockstep, replies compared byte-for-byte.

Run: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \\
  --python 3.12 --with torch --with numpy python -B \\
  scripts/fable_perf142_c2.py --out artifacts/fable-perf142-20260922/c2.json
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop134_agent as L134
import fable_loop142_agent as L142
import fable_soak108_run as S108

N = 5000

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/fable-perf142-20260922/c2.json")
    ap.add_argument("--n", type=int, default=N)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    turns, _ = S108.build_plan(20000, 93)
    import tempfile
    base = L134.build_agent134({"sleep_threshold": 10**9,
                                "state_dir": tempfile.mkdtemp(prefix="fable_perf142_c2a_")})
    fast = L142.build_agent142({"sleep_threshold": 10**9,
                                "state_dir": tempfile.mkdtemp(prefix="fable_perf142_c2b_")})
    mism = []
    for i, t in enumerate(turns[:a.n]):
        r1 = " ".join(base.turn(t["text"]))
        r2 = " ".join(fast.turn(t["text"]))
        if r1 != r2:
            mism.append({"seq": i, "kind": t["kind"], "text": t["text"][:120],
                         "base": r1[:200], "fast": r2[:200]})
            if len(mism) >= 10:
                break
        if (i+1) % 1000 == 0:
            print(f"C2 {i+1}/{a.n} mism={len(mism)}", flush=True)
    res = {"n": a.n, "mismatches": mism, "n_mismatch": len(mism),
           "pass": len(mism) == 0, "seconds": round(time.time()-t0, 1)}
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("C2", "PASS" if res["pass"] else "FAIL",
          f"{a.n-len(mism)}/{a.n} identical ({res['seconds']}s)", flush=True)
    return 0 if res["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
