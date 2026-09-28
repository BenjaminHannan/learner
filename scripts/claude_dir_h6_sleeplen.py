#!/usr/bin/env python3
"""dir-h6 (helper H6, Claude, 2026-09-28): does a gentler long night keep the grid gain that slp-358n3's long night lost?

Marks and design: artifacts/claude-dir-h6-sleeplen-20260928/PASSMARKS.md and DESIGN.md (drafted a few minutes AFTER this
file by mistake of order; both were fixed before any run and before any score of the new arm B exists).
WRITTEN ON A BOX WITH NO TORCH: this file was only checked with `python3 -m py_compile`. Nothing in it has run. The first
run is the queue job's `smoke` step; if smoke fails, stop and report the traceback (do not patch).

It changes NO existing file. It imports the sealed slp-358n3 night code (scripts/claude_slp358n3_nights.py) and reuses its
tests, day puzzles, exclusion list, night mix, loop training step and scorer unchanged. The ONE change it adds is a new arm B:

  arm N  no night                                   (control)
  arm S  300 steps, lr 3e-5 constant                (slp-358n3's S, control)
  arm L  6,000 steps, lr 3e-5 constant              (slp-358n3's report-only L, control; now on all 4 seeds)
  arm B  6,000 steps, lr 3e-5 * 300 / 6000 = 1.5e-6 (L with ONLY the learning rate changed: same total learning budget as S)

B and L get the same round draws (rr seed), the same batch plan (nrng seed) and the same rehearsal stream, so they differ in
the learning rate only. Optimizer: AdamW wd 0.1, betas (0.9, 0.95), one per arm kept across the 3 nights, as in slp-358n3.
Output JSON uses slp-358n3's layout (morning / day / lost / night_minutes), so its blind-recount scorer style applies.

  python -B scripts/claude_dir_h6_sleeplen.py run --ckpt ck/s13/final.pt --seed 13 --sizes W/sizes.json --out W/s13
  python -B scripts/claude_dir_h6_sleeplen.py smoke
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
ARMS = "NSLB"
STEP_RATIO = 300 / 6000                      # B's lr = night_lr * night_steps / long_steps (same lr x steps as S)


class Arm(N3.Arm):
    """slp-358n3's Arm; B is L's twin with a smaller learning rate. Name 'L' is passed up so steps come from long_steps and
    night() treats it exactly like S/L (real answers, the same half-day half-rehearsal draw)."""

    def __init__(self, name, net, src, seed, cfg):
        super().__init__("L" if name == "B" else name, net, src, seed, cfg)
        self.name = name
        self.lr = cfg["night_lr"]
        if name == "B":
            self.lr = cfg["night_lr"] * cfg["night_steps"] / cfg["long_steps"]
            for g in self.opt.param_groups:
                g["lr"] = self.lr


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
    src0 = R.Source(100 + a.seed, latin_pool=cfg["latin_pool"])       # the same rehearsal stream seed as slp-358n3
    arms = {n: Arm(n, copy.deepcopy(base), copy.deepcopy(src0), a.seed, cfg) for n in ARMS}
    log = {"seed": a.seed, "ckpt": str(a.ckpt), "ckpt_sha256": hashlib.sha256(Path(a.ckpt).read_bytes()).hexdigest(),
           "sizes": sizes, "cfg": cfg, "arm_lr": {n: arms[n].lr for n in ARMS},
           "arm_steps": {n: arms[n].steps for n in ARMS}, "torch": torch.__version__, "device": device,
           "gpu": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
           "morning": {}, "day": {}, "lost": {}, "excluded_day_items": 0}

    def morning(net):
        rights, res = {}, {}
        for k, v in tests.items():
            rights[k], res[k] = N3.judge(net, v, device, cfg["eval_bs"])
        return rights, res

    r0, log["morning"]["base"] = morning(base)
    prev = {n: r0 for n in ARMS}
    print("base", json.dumps({k: v["right"] for k, v in log["morning"]["base"].items()}), flush=True)
    for day in range(1, cfg["days"] + 1):
        raw = N3.day_items(a.seed, day, sizes, cfg["n_day"])
        items = [it for it in raw if N3.key(it) not in block]
        log["excluded_day_items"] += len(raw) - len(items)
        d = str(day)
        log["day"][d], log["morning"][d], log["lost"][d] = {}, {}, {}
        for n, arm in arms.items():
            log["day"][d][n] = {k: N3.judge(arm.net, [i for i in items if i.env == k], device, cfg["eval_bs"])[1]
                                for k in ("sums", "grids")}
            if n != "N":
                t1 = time.time()
                N3.night(arm, day, items, a.seed, cfg, device)
                log.setdefault("night_minutes", {}).setdefault(d, {})[n] = round((time.time() - t1) / 60, 2)
            rights, log["morning"][d][n] = morning(arm.net)
            log["lost"][d][n] = {k: sum(p and not q for p, q in zip(prev[n][k], rights[k])) for k in N3.HARM}
            prev[n] = rights
        print("morning", day, json.dumps({n: {k: v["right"] for k, v in m.items()} for n, m in log["morning"][d].items()}),
              f"{(time.time() - t0) / 60:.1f} min", flush=True)
    # the batch plans of L and B must be identical (the only difference is the learning rate)
    log["plan_identical_L_B"] = arms["L"].trace == arms["B"].trace
    log["plan_first300_identical_S_L"] = [t for t in arms["S"].trace if t[0] == 1] == [t for t in arms["L"].trace if t[0] == 1 and t[1] < cfg["night_steps"]]
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"dirh6-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    # no weights are saved: this test decides nothing about a product checkpoint


def smoke(_):
    """an untrained full-size loop net on CPU with slp-358n3's tiny settings: every path runs; nothing here is a result"""
    tmp = Path(tempfile.mkdtemp())
    torch.manual_seed(0)
    torch.save({"arm": "loop", "seed": 0, "state": R.Net("loop").state_dict()}, tmp / "c.pt")
    (tmp / "sizes.json").write_text(json.dumps({"sizes": {"sums": 6, "grids": 6}}), encoding="utf-8")
    cfg = N3.TINY
    run(argparse.Namespace(ckpt=tmp / "c.pt", seed=13, sizes=tmp / "sizes.json", out=tmp / "s13", device="cpu"), cfg)
    d = json.loads((tmp / "s13/dirh6-seed13.json").read_text())
    assert set(d["morning"]["1"]) == set(ARMS), d["morning"]["1"].keys()
    assert d["arm_steps"] == {"N": cfg["night_steps"], "S": cfg["night_steps"], "L": cfg["long_steps"], "B": cfg["long_steps"]}, d["arm_steps"]
    want = cfg["night_lr"] * cfg["night_steps"] / cfg["long_steps"]
    assert abs(d["arm_lr"]["B"] - want) < 1e-12 and d["arm_lr"]["L"] == cfg["night_lr"] == d["arm_lr"]["S"], d["arm_lr"]
    assert d["plan_identical_L_B"] is True
    assert all(v == 0 for v in d["lost"]["1"]["N"].values())
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
