"""Calibrate the binding toy: baseline vs known writers vs the oracle address.

The baseline runs exactly like a candidate (untrusted, with the writer checks).
The references come from references.py and run as trusted (the oracle needs roles)."""
import json, sys
from pathlib import Path
import toy

HERE = Path(__file__).resolve().parent
REF = str(HERE / "references.py")
writers = {"baseline_singlepool": (str(HERE / "initial.py"), "CardWriter", False),
           "mean_pool": (REF, "MeanPool", True), "two_pool": (REF, "TwoPool", True),
           "multihead_pool": (REF, "MultiHeadPool", True), "oracle_address": (REF, "OracleAddress", True)}

if __name__ == "__main__":
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(writers)
    seeds = [int(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else [100, 101, 102]
    for n in names:
        r = toy.run(writers[n], seeds)
        m = r["mean"]
        print(n, json.dumps({k: round(v, 3) for k, v in m.items()}), "per-seed score:",
              [round(p["score"], 3) for p in r["per_seed"]], flush=True)
