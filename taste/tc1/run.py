"""CLI: python3 -m tc1.run --arm {C,R,R07,B,H,O,N} --seed S --out DIR [--days 6] [--small]"""
import argparse, json, os, sys, time
from types import SimpleNamespace
import numpy as np
import torch

from .config import make_config
from . import houses, copyguard, maker as maker_mod, night, eval as eval_mod

ARMS = ["C", "R", "R07", "B", "H", "O", "N"]


def prepare(seed, cfg, ckpt_dir, log=print):
    data = houses.make_data(seed)
    k = copyguard.calibrate_k(data.heldback, data.critic)
    os.makedirs(ckpt_dir, exist_ok=True)
    path = os.path.join(ckpt_dir, f"maker-s{seed}-p{cfg.pretrain_programs}-e{cfg.pretrain_epochs}"
                                  f"-b{cfg.pretrain_batch}-pool{cfg.pool}-ho{cfg.heldout}"
                                  + ("" if cfg.prior == "clutter" else f"-{cfg.prior}") + ".pt")
    if os.path.exists(path):
        ck = torch.load(path, weights_only=True)
        log(f"loaded checkpoint {path}")
    else:
        state, pool, heldout, info = maker_mod.pretrain(cfg, seed, log)
        ck = {"state": state, "pool": pool, "heldout": heldout, "info": json.dumps(info)}
        torch.save(ck, path + ".tmp")
        os.replace(path + ".tmp", path)
        log(f"saved checkpoint {path}")
    return SimpleNamespace(data=data, k=k, state=ck["state"], pool=ck["pool"], heldout=ck["heldout"],
                           pretrain_info=json.loads(ck["info"]), ckpt=path)


def run_one(arm, seed, cfg, ckpt_dir, log=print, ctx=None, evaluator_on=True):
    ctx = ctx or prepare(seed, cfg, ckpt_dir, log)
    guard = copyguard.CopyGuard(ctx.data.critic, ctx.k)
    evaluator = (lambda m, nt: eval_mod.evaluate(m, ctx.data, guard, cfg, seed, nt, ctx.heldout)) \
        if evaluator_on else None
    osc = None
    if arm == "O":
        from . import oracle          # arm O's separate code path
        osc = oracle.scores
    res, kept = night.run_arm(arm, seed, cfg, ctx.data, ctx.k, ctx.state, ctx.pool, evaluator, osc, log)
    res.update({"arm": arm, "seed": seed, "config": cfg.to_dict(), "k": ctx.k,
                "pretrain": ctx.pretrain_info, "maker_params": ctx.pretrain_info.get("n_params")})
    return res, kept


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int)
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--ckpt-dir")
    ap.add_argument("--pretrain-programs", type=int, help="override (timing/smoke only)")
    ap.add_argument("--pretrain-only", action="store_true")
    ap.add_argument("--prior", choices=["clutter", "touching"], default="clutter")
    ap.add_argument("--distinct", action="store_true", help="TC-1c variety guard on each night's picks")
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    cfg = make_config(a.small, a.days, pretrain_programs=a.pretrain_programs, prior=a.prior,
                      distinct=a.distinct or None)
    os.makedirs(a.out, exist_ok=True)
    ckpt_dir = a.ckpt_dir or os.path.join(a.out, "ckpt")
    if a.pretrain_only or a.arm is None:
        prepare(a.seed, cfg, ckpt_dir)
        return
    t0 = time.time()
    res, _ = run_one(a.arm, a.seed, cfg, ckpt_dir)
    res["wall_time_total_incl_load"] = time.time() - t0
    p = os.path.join(a.out, f"{a.arm}-s{a.seed}.json")
    with open(p, "w") as f:
        json.dump(res, f, indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
