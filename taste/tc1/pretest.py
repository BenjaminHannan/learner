"""Pick-only pre-test on the day-0 maker: python3 -m tc1.pretest --seed S --out DIR [--small]"""
import argparse, json, os, time
import numpy as np
import torch

from .config import make_config
from . import night, critic as critic_mod, copyguard, oracle
from .maker import Maker
from .run import prepare


def run_pretest(seed, cfg, ckpt_dir, n_req=None, log=print):
    t0 = time.time()
    ctx = prepare(seed, cfg, ckpt_dir, log)
    n_req = n_req or cfg.requests
    maker = Maker(); maker.load_state_dict(ctx.state); maker.eval()
    guard = copyguard.CopyGuard(ctx.data.critic, ctx.k)
    tb = night.make_tries(maker, seed, 1, n_req, 16, 1.0, guard)       # day-1 streams, 16 tries
    sh = (n_req, 16)
    flat_pass = tb.passing.reshape(-1)
    hs = np.full(flat_pass.shape, 0.0)
    hs[flat_pass] = oracle.scores(tb.grids[flat_pass])
    # critic trained once as on day 1 (buffer = passing tries among the first 8 per request)
    first8 = tb.passing.copy(); first8[:, 8:] = False
    cr = critic_mod.Critic(seed, cfg.critic_lr)
    stats = critic_mod.daily_train(cr, ctx.data.critic, tb.grids[first8.reshape(-1)], cfg.critic_steps,
                                   cfg.critic_batch, cfg.r1_weight, np.random.default_rng([seed, 7001]))
    exam = critic_mod.critic_exam(cr, ctx.data, tb.grids[first8.reshape(-1)])
    blank = critic_mod.Critic(seed + 77, cfg.critic_lr)
    lc, lb = cr.logits(tb.grids), blank.logits(tb.grids)

    def mean_pick(arm, n_use, logits=None):
        idx = night.pick(arm, tb, n_use, logits, hs)
        got = idx >= 0
        vals = np.zeros(n_req)
        vals[got] = hs.reshape(sh)[np.arange(n_req)[got], idx[got]]
        return {"mean": float(vals.mean()), "mean_given_pass": float(vals[got].mean()) if got.any() else None,
                "requests_with_pass": int(got.sum())}

    out = {"seed": seed, "k": ctx.k, "config": cfg.to_dict(), "n_requests": n_req, "critic_train": stats,
           "critic_exam": exam,
           "picks_8": {"C": mean_pick("C", 8, lc), "R": mean_pick("R", 8), "B": mean_pick("B", 8, lb),
                       "H": mean_pick("H", 8), "O": mean_pick("O", 8)},
           "C_by_tries": {str(n): mean_pick("C", n, lc) for n in (2, 4, 8, 16)},
           "mean_hidden_all_passing_tries": float(hs[flat_pass].mean()) if flat_pass.any() else None,
           "pass_rate": float(flat_pass.mean()), "copy_rate": float(tb.copy.mean())}
    out["headroom_O_minus_R"] = out["picks_8"]["O"]["mean"] - out["picks_8"]["R"]["mean"]
    out["wall_time"] = time.time() - t0
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--ckpt-dir")
    ap.add_argument("--pretrain-programs", type=int)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    cfg = make_config(a.small, None, pretrain_programs=a.pretrain_programs)
    os.makedirs(a.out, exist_ok=True)
    res = run_pretest(a.seed, cfg, a.ckpt_dir or os.path.join(a.out, "ckpt"))
    p = os.path.join(a.out, f"pretest-s{a.seed}.json")
    json.dump(res, open(p, "w"), indent=1)
    print("wrote", p)
    print(json.dumps({k: res[k] for k in ("picks_8", "C_by_tries", "headroom_O_minus_R")}, indent=1))


if __name__ == "__main__":
    main()
