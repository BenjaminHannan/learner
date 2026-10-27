#!/usr/bin/env python3
"""T3 (newer-weighted rehearsal across three nights) on H6's three-night design.

Marks: artifacts/claude-dir-t3-recency-20260928/PASSMARKS.md (sealed before any run). Helper: Director helper
"sleep tests sealer" (Claude, 2026-09-28).
WRITTEN ON A BOX WITH NO TORCH: only `python3 -m py_compile` and the pure-python marks selftest were run here. The first
real run is the queue job's `smoke`; if it fails, stop and report the traceback (do not patch).

It imports slp-358n3's sealed night code (claude_slp358n3_nights: tests, day puzzles, exclusions, the 50% rehearsal stream,
the loop training step, the scorer) exactly as dir-h6 does, and edits nothing. The night is S's: 300 steps, lr 3e-5, batch 256,
half the batches from the rehearsal stream, half from day puzzles, one optimizer per arm kept across the 3 nights.

THE ONE CHANGE (weights over nights). slp-358n3's night draws its day half only from the current night's 300 puzzles per kind.
Here the day half of night n draws from the puzzles of nights 1..n (all code-made, tests and panels excluded as in slp-358n3),
and the ONLY thing that differs between the arms is the weight of each night in that draw:
  S  0 : 0 : 1     only the current night (slp-358n3's S recipe, run through this code path)
  U  1 : 1 : 1     uniform over nights so far
  W  1 : 2 : 4     newest weighted (weight 2^(night-1); on night n the newest night has the largest weight)
On night 1 all three draw from one night, so night 1 is identical across S, U and W (checked by batch hashes).
All arms share every random number: the kind draw, and per item one u in [0,1) and one integer j; the weights only change
which night u lands in, so U and W are paired item by item. N (no night) is scored once per seed.
Three draws per arm: draw d changes the round draws (rr seed 59100 + seed + 1000 d), the batch-plan draws (59200 + 10 seed
+ day + 1000 d) and the rehearsal stream (100 + seed + 1000 d). Draw 0 of S uses the same seeds as slp-358n3's S.

  python -B scripts/claude_dir_t3_recency.py run --ckpt ck/s13/final.pt --seed 13 --sizes W/sizes.json --out W/s13
  python -B scripts/claude_dir_t3_recency.py smoke
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
import tempfile
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_slp358n3_nights as N3  # noqa: E402  (sealed; imported, never edited)

R = N3.R
ARMS = ("S", "U", "W")
DRAWS = (0, 1, 2)


def weights(arm, night):
    """weight of nights 1..night in the day-half draw"""
    if arm == "S":
        return [0] * (night - 1) + [1]
    if arm == "U":
        return [1] * night
    return [2 ** i for i in range(night)]


def night_of(u, w):
    x, total, cum = u * sum(w), sum(w), 0
    for i, wi in enumerate(w):
        cum += wi
        if x < cum:
            return i
    return len(w) - 1


class Arm(N3.Arm):
    def __init__(self, name, draw, net, src, seed, cfg):
        super().__init__("S", net, src, seed, cfg)         # S's 300 steps and lr; name reset below
        self.name, self.draw = name, draw
        self.rr = random.Random(59100 + seed + 1000 * draw)
        self.plan = {}                                      # day -> hash of every (kind, u, j) drawn (U and W must agree)


def night_mem(arm, day, per_night, seed, cfg, device):
    """per_night[i][env] = the puzzles of night i+1 (only nights <= day are used)."""
    w = weights(arm.name, day)
    nrng = random.Random(59200 + 10 * seed + day + 1000 * arm.draw)
    h = hashlib.sha256()
    for step in range(arm.steps):
        if nrng.random() < 0.5:
            b = arm.src.batch(cfg["batch"])
            h.update(b"r")
        else:
            env = nrng.choice(sorted(per_night[0]))
            b, us = [], []
            for _ in range(cfg["batch"]):
                u, j = nrng.random(), nrng.randrange(1 << 30)
                pool = per_night[night_of(u, w)][env]
                b.append(pool[j % len(pool)])
                us.append((round(u, 12), j))
            h.update(repr((env, us)).encode())
        arm.trace.append((day, step, N3.batch_hash(b)))
        N3.train_step(arm.net, arm.opt, b, arm.rr, device)
    arm.plan[str(day)] = h.hexdigest()[:16]


def run(a, cfg=N3.CFG):
    t0 = time.time()
    torch.manual_seed(a.seed)
    device = a.device or N3.dev_of()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sizes = json.loads(Path(a.sizes).read_text())["sizes"]
    tests = N3.make_tests(sizes, cfg)
    test_keys = {N3.key(it) for v in tests.values() for it in v}
    block = test_keys | {N3.key(it) for v in N3.dev_items(cfg["n_dev"]).values() for it in v} | N3.panel_keys()
    base = N3.load(a.ckpt, device)
    srcs = {d: R.Source(100 + a.seed + 1000 * d, latin_pool=cfg["latin_pool"]) for d in DRAWS}
    arms = {f"{n}{d}": Arm(n, d, copy.deepcopy(base), copy.deepcopy(srcs[d]), a.seed, cfg) for n in ARMS for d in DRAWS}
    log = {"seed": a.seed, "ckpt": str(a.ckpt), "ckpt_sha256": hashlib.sha256(Path(a.ckpt).read_bytes()).hexdigest(),
           "sizes": sizes, "cfg": cfg, "draws": list(DRAWS), "torch": torch.__version__, "device": device,
           "gpu": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
           "weights_night3": {n: weights(n, 3) for n in ARMS}, "arm_steps": {k: v.steps for k, v in arms.items()},
           "morning": {}, "day": {}, "lost": {}, "excluded_day_items": 0, "own_after_last_night": {}}

    def morning(net):
        rights, res = {}, {}
        for k, v in tests.items():
            rights[k], res[k] = N3.judge(net, v, device, cfg["eval_bs"])
        return rights, res

    r0, base_res = morning(base)
    log["morning"]["base"] = base_res
    prev = {k: r0 for k in arms}
    print("base", json.dumps({k: v["right"] for k, v in base_res.items()}), flush=True)
    per_night, kept = [], []
    for day in range(1, cfg["days"] + 1):
        raw = N3.day_items(a.seed, day, sizes, cfg["n_day"])
        items = [it for it in raw if N3.key(it) not in block]
        log["excluded_day_items"] += len(raw) - len(items)
        kept.append(items)
        per_night.append({e: [it for it in items if it.env == e] for e in ("sums", "grids")})
        d = str(day)
        log["day"][d], log["morning"][d], log["lost"][d] = {}, {"N": base_res}, {}
        for name, arm in arms.items():
            log["day"][d][name] = {k: N3.judge(arm.net, per_night[-1][k], device, cfg["eval_bs"])[1] for k in ("sums", "grids")}
            t1 = time.time()
            night_mem(arm, day, per_night, a.seed, cfg, device)
            log.setdefault("night_minutes", {}).setdefault(d, {})[name] = round((time.time() - t1) / 60, 2)
            rights, log["morning"][d][name] = morning(arm.net)
            log["lost"][d][name] = {k: sum(p and not q for p, q in zip(prev[name][k], rights[k])) for k in N3.HARM}
            prev[name] = rights
        print("morning", day, json.dumps({n: {k: v["right"] for k, v in m.items()} for n, m in log["morning"][d].items() if n != "N"}),
              f"{(time.time() - t0) / 60:.1f} min", flush=True)
    # report only: each arm's score on its own night-1 / night-2 / night-3 puzzles (first 100 per kind) after the last night
    for name, arm in arms.items():
        log["own_after_last_night"][name] = {
            str(i + 1): {k: N3.judge(arm.net, [x for x in kept[i] if x.env == k][:100], device, cfg["eval_bs"])[1]["right"]
                         for k in ("sums", "grids")} for i in range(len(kept))}
    # integrity: night 1 is one night for every arm, so S, U and W must draw the same batches; U and W draw the same plan
    log["night1_batches_identical_SUW"] = {str(d): all(
        [t for t in arms[f"{n}{d}"].trace if t[0] == 1] == [t for t in arms[f"S{d}"].trace if t[0] == 1] for n in ("U", "W")) for d in DRAWS}
    log["plan_identical_U_W"] = {str(d): arms[f"U{d}"].plan == arms[f"W{d}"].plan for d in DRAWS}
    log["plan_differs_S_U_night2"] = {str(d): arms[f"S{d}"].plan.get("2") != arms[f"U{d}"].plan.get("2") for d in DRAWS} if cfg["days"] >= 2 else {}
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"dirt3-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    # no weights are saved: this test decides nothing about a product checkpoint


def smoke(_):
    """an untrained full-size loop net on CPU with slp-358n3's tiny settings and 2 nights: every path runs; nothing here is a result"""
    tmp = Path(tempfile.mkdtemp())
    torch.manual_seed(0)
    torch.save({"arm": "loop", "seed": 0, "state": R.Net("loop").state_dict()}, tmp / "c.pt")
    (tmp / "sizes.json").write_text(json.dumps({"sizes": {"sums": 6, "grids": 6}}), encoding="utf-8")
    cfg = dict(N3.TINY, days=2, night_steps=6)
    run(argparse.Namespace(ckpt=tmp / "c.pt", seed=13, sizes=tmp / "sizes.json", out=tmp / "s13", device="cpu"), cfg)
    d = json.loads((tmp / "s13/dirt3-seed13.json").read_text())
    assert set(d["morning"]["2"]) == {"N"} | {f"{n}{x}" for n in ARMS for x in DRAWS}, d["morning"]["2"].keys()
    assert d["weights_night3"] == {"S": [0, 0, 1], "U": [1, 1, 1], "W": [1, 2, 4]}, d["weights_night3"]
    assert all(d["night1_batches_identical_SUW"].values()), d["night1_batches_identical_SUW"]
    assert all(d["plan_identical_U_W"].values()), d["plan_identical_U_W"]
    assert all(d["plan_differs_S_U_night2"].values()), d["plan_differs_S_U_night2"]
    print("smoke ok", tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--ckpt", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--sizes", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--device", default="")
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"run": run, "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
