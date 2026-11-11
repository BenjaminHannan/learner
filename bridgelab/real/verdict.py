"""Read results/*.json and apply PREREG.md's pass marks.  python -m bridgelab.real.verdict [results_dir] [--split dev]

Per seed: the per-item bridges (pooled, xattn) are judged against that seed's `ema_const` and the prior baseline of the split.  Prints a plain table and writes verdict.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(d: Path):
    out = {}
    for p in sorted(d.glob("*.json")):
        if p.name == "verdict.json":
            continue
        j = json.load(open(p))
        if "bridge" in j and "results" in j:
            out.setdefault((j["bridge"], j.get("args", {}).get("tag", ""), j["seed"]), j)
    return out


def judge(run: dict, ema: dict | None, split: str = "dev") -> dict:
    r = run["results"][split]
    prior = 100 * r["c"]["prior_acc"]
    arms = {k: 100 * v["acc"] for k, v in r["arms"].items()}
    d_own = 100 * r["d_own"]["acc"]
    v = dict(split=split, prior=prior, d_own=d_own, arms=arms, smoke=run.get("smoke", False))
    real, shuf, mean = arms.get("real"), arms.get("shuffle"), arms.get("mean")
    ema_acc = None if ema is None else 100 * ema["results"][split]["arms"]["real"]["acc"]
    v["marks"] = dict(a_real_ge_prior_plus_30=real is not None and real >= prior + 30,
                      b_shuffle_le_prior_plus_5=shuf is not None and shuf <= prior + 5,
                      c_mean_le_prior_plus_5=mean is not None and mean <= prior + 5,
                      d_ema_const_le_prior_plus_5=None if ema_acc is None else ema_acc <= prior + 5)
    v["wrong"] = dict(no_flow_real_le_prior_plus_10=real is not None and real <= prior + 10,
                      not_via_message_shuffle_within_10_of_real=real is not None and shuf is not None and real - shuf <= 10)
    v["precondition_d_too_weak"] = d_own < prior + 35
    v["precondition_creative_too_weak"] = arms.get("oracle_inject", 0) < prior + 40
    v["passes"] = all(x is True for x in v["marks"].values())
    v["d_text_vs_real"] = None if "d_text" not in arms or real is None else real - arms["d_text"]
    return v


def main():
    d = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path(__file__).resolve().parent / "results"
    splits = ["dev", "validation"]
    runs = load(d)
    out = []
    for (bridge, tag, seed), run in runs.items():
        if bridge not in ("pooled", "xattn"):
            continue
        ema = runs.get(("ema_const", tag, seed))
        for sp in splits:
            v = judge(run, ema, sp)
            v.update(bridge=bridge, seed=seed, tag=tag)
            out.append(v)
            flag = "SMOKE (not a result) " if v["smoke"] else ""
            print(f"{flag}{bridge} seed {seed} {sp}: prior {v['prior']:.1f}  D-own {v['d_own']:.1f}  " + "  ".join(f"{k} {a:.1f}" for k, a in v["arms"].items()))
            print("   marks", {k: x for k, x in v["marks"].items()}, "PASS" if v["passes"] else "not passed")
            print("   proved-wrong flags", v["wrong"], "| D too weak" if v["precondition_d_too_weak"] else "", "| creative too weak" if v["precondition_creative_too_weak"] else "")
    json.dump(out, open(d / "verdict.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
