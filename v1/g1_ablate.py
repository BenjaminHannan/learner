"""G1 ablation on the creative module alone (design/v1/g1-ablate/PREREG.md). No D, no bridge, no village data.

  python3 -m v1.g1_ablate --b2 B2.pt --skills SKILLS_DIR --out OUT --device cuda --seeds 0 [--arms g1_empirical g1_example g1_off] [--smoke]

Per seed and arm: the creative chain of `v1.creative_sleep.run_creative` (warm-up -> N' -> two nights) from the raw parent, G1 per arm
(empirical = v1 as is, example = NK30 per-example G, off = no guard). After W1 and W2: skills5 (harm vs the RAW parent's score and vs the arm's own N')
and creative DEV first-try by kind. OUT/results.json = numbers per arm + the PREREG verdict. The sealed test split is never read (dev only).
Resumable: run_creative skips finished stages; a finished arm (arm_result.json) is skipped."""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any, Optional

ARMS = ("g1_empirical", "g1_example", "g1_off")
NORM = {"g1_empirical": "none", "g1_example": "example"}
SMOKE = dict(pool_limit=64, dev_limit=16, n1=4, n2=8, T=1.0, updates_cap=2, diary=64)
FIRST_TRY_TOL = 2.0       # points
BUYS_MIN = 2.0            # points
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def verdict(arms: dict[str, dict]) -> dict[str, Any]:
    """PREREG pass marks on the final night (W2), harm vs the raw parent, in points. Pure function of the per-arm numbers (means over seeds)."""
    need = ARMS
    if any(a not in arms for a in need):
        return dict(status="incomplete", missing=[a for a in need if a not in arms])
    e, x, o = (arms[a] for a in need)
    ex_ok = x["harm_w2"] <= e["harm_w2"] and abs(x["first_try_w2"] - e["first_try_w2"]) <= FIRST_TRY_TOL
    buys = (o["harm_w2"] - e["harm_w2"]) >= BUYS_MIN
    return dict(status="done",
                example_ok=dict(passes=ex_ok, harm_example=x["harm_w2"], harm_empirical=e["harm_w2"],
                                first_try_gap_points=x["first_try_w2"] - e["first_try_w2"]),
                g1_buys_retention=dict(passes=buys, harm_off_minus_empirical=o["harm_w2"] - e["harm_w2"]),
                proved_wrong=dict(example_fix=not ex_ok, g1_benefit=not buys))


def arm_summary(ret: dict) -> dict[str, float]:
    w1, w2 = ret["W1"], ret["W2"]
    return dict(harm_w1=w1["harm_points"], harm_w2=w2["harm_points"], first_try_w1=100 * w1["dev_first_try"], first_try_w2=100 * w2["dev_first_try"])


def run_arm(arm: str, a, seed: int, out: str, smoke: bool) -> dict[str, Any]:
    from creative import fastsleep, sleep
    from v1 import creative_sleep, g1 as g1mod
    os.makedirs(out, exist_ok=True)
    done = os.path.join(out, "arm_result.json")
    if os.path.exists(done):
        return json.load(open(done))
    kw = dict(SMOKE) if smoke else {}
    diary_n = kw.pop("diary", g1mod.DIARY_SIZE)
    raw, _, _ = sleep.load_parent(a.b2, a.device)
    base5_raw = fastsleep.skills5(raw, a.skills, a.device)
    dev_raw = creative_sleep.dev_report(a.b2, a.device, limit=kw.get("dev_limit"))["first_try"]
    del raw
    factory = None
    if arm != "g1_off":
        def factory(raw_, replay):
            parent = g1mod.frozen_copy(raw_)
            diary = g1mod.build_diary(parent, replay, n=diary_n, seed=seed, device=a.device)
            return g1mod.G1(parent, diary, raw_.vocab, device=a.device, seed=seed, norm=NORM[arm])
    ret = creative_sleep.retention_fn(a.skills, a.device, base5=base5_raw, dev_limit=kw.get("dev_limit"))
    t0 = time.time()
    info = creative_sleep.run_creative(out, a.b2, os.path.join(a.skills, "train.jsonl"), a.skills, device=a.device, seed=seed,
                                       g1_factory=factory, retention=ret, **kw)
    if "stop" in info:
        res = dict(arm=arm, seed=seed, stop=info["stop"])
    else:
        nprime, _, _ = sleep.load_parent(os.path.join(out, "Nprime.pt"), a.device)
        n5 = fastsleep.skills5(nprime, a.skills, a.device)
        res = dict(arm=arm, seed=seed, g1_norm=NORM.get(arm), base5_raw=base5_raw, dev_first_try_raw=dev_raw, base5_Nprime=n5,
                   retention=info["retention"], summary=arm_summary(info["retention"]),
                   harm_vs_own_Nprime={k: 100 * (n5 - v["skills5"]) for k, v in info["retention"].items()},
                   kl_share={k: v.get("kl_share_mean_after_25pct") for k, v in info["phases"].items()}, seconds=round(time.time() - t0))
    json.dump(res, open(done, "w"), indent=1, default=float)
    return res


def aggregate(results: list[dict]) -> dict[str, Any]:
    by: dict[str, list[dict]] = {}
    for r in results:
        if "summary" in r:
            by.setdefault(r["arm"], []).append(r["summary"])
    arms = {k: {m: sum(s[m] for s in v) / len(v) for m in v[0]} for k, v in by.items()}
    return dict(arms=arms, verdict=verdict(arms), per_run=results)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--b2", required=True)
    ap.add_argument("--skills", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=ARMS)
    ap.add_argument("--smoke", action="store_true", help="tiny sizes, CPU smoke test only")
    a = ap.parse_args(argv)
    results = []
    for seed in a.seeds:
        for arm in a.arms:
            out = os.path.join(a.out, f"s{seed}", arm)
            log("ARM", arm, "seed", seed)
            results.append(run_arm(arm, a, seed, out, a.smoke))
    agg = aggregate(results)
    os.makedirs(a.out, exist_ok=True)
    json.dump(agg, open(os.path.join(a.out, "results.json"), "w"), indent=1, default=float)
    log("RESULTS", json.dumps(agg["verdict"], default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
