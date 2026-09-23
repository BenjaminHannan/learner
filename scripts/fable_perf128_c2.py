#!/usr/bin/env python3
"""Exp 128 C2: replies byte-identical to unwrapped loop102, first 5000 seed-93 turns."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop102_agent as L102
import fable_perf128_index as F128
import fable_soak108_run as S108

N = 5000

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/fable-perf128-20260922/c2.json")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    turns, _ = S108.build_plan(20000, 93)
    import tempfile
    base = L102.build_agent102({"sleep_threshold": 10**9,
                                "state_dir": tempfile.mkdtemp(prefix="fable_perf128_c2a_")})
    fast = F128.build_fast_agent102({"sleep_threshold": 10**9,
                                     "state_dir": tempfile.mkdtemp(prefix="fable_perf128_c2b_")})
    mism = []
    for i, t in enumerate(turns[:N]):
        r1 = " ".join(base.turn(t["text"]))
        r2 = " ".join(fast.turn(t["text"]))
        if r1 != r2:
            mism.append({"seq": i, "kind": t["kind"], "text": t["text"][:120],
                         "base": r1[:200], "fast": r2[:200]})
            if len(mism) >= 10:
                break
        if (i+1) % 1000 == 0:
            print(f"C2 {i+1}/{N} mism={len(mism)}", flush=True)
    res = {"n": N, "mismatches": mism, "n_mismatch": len(mism),
           "pass": len(mism) == 0, "seconds": round(time.time()-t0, 1)}
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("C2", "PASS" if res["pass"] else "FAIL", f"{N-len(mism)}/{N} identical ({res['seconds']}s)", flush=True)
    return 0 if res["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
