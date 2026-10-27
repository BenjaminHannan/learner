#!/usr/bin/env python3
"""rsn-358x (sleep research thread, 2026-09-26): does practice on some puzzle kinds carry over to a NEW kind, and does
it carry over more for the loop than for the plain net of the same size?

Ben 15:41 UTC: "take the brains ability to naturally improve over time and be generally intelligent. Apply skills
learned to other places."

Source nets: rsn-358i's sealed checkpoints (seeds 1-4, loop and plain), which practised only sums, grids and number
puzzles for 60,000 steps (~/premonition-models/rsn358i/<arm>-s<seed>/final.pt; sha256 in
artifacts/claude-rsn358i-20260926/SEAL-run.sha256.txt). Held-out kind: perfect mazes (scripts/claude_rsn358m_maze.py;
neither net has seen one; the tokens exist in the vocabulary, the kind gets a new embedding row = the mean of the
three practised kinds' rows).
For each seed and arm, two nets practise mazes identically (sizes 5 and 7, batch 256, lr 3e-4 after a 200-step
warm-up, CARRY_STEPS = 4,000 steps, the arm's own 358i training schedule, the same maze stream):
  pre    starts from the 358i checkpoint
  fresh  starts from random weights (same architecture)
After 0, 125, 250, 500, 750, 1000, 1500, 2000, 3000 and 4000 steps (batch 256, so 32,000 to 1,024,000 mazes) both are
scored on 400 fresh dev mazes (200 at 7x7, 200 at 9x9; seeded, never the test files). Primary number (Ben 15:42,
"a person learns to drive in about 40 hours"): steps to the bar = the first check with >= 150/200 right on 7x7 dev
(5000 if never). The check at 0 steps is solving mazes cold (report only).
At the end each net is scored once on the sealed maze tests (artifacts/claude-rsn358m-20260926/tests: maze7/9/11/13).

  python -B scripts/claude_rsn358x_run.py carry --arm loop|plain --init pre|fresh --seed S [--ckpt SRC.pt] --out DIR
  python -B scripts/claude_rsn358x_run.py eval --ckpt DIR/final-carry.pt --tests artifacts/claude-rsn358m-20260926/tests --out F
  python -B scripts/claude_rsn358x_run.py smoke | selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358m_run as MR  # noqa: E402  (358i design + the maze kind, maze check, maze test makers)

R, E, M = MR.R, MR.E, MR.M
CARRY_STEPS, WARMUP = 4000, 200
CHECKS = [0, 125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000]     # dev checks after these many steps (0 = cold)
BAR7, NEVER = 150, 5000                                               # steps-to-bar; NEVER if not reached by 4000
MAZE_TESTS = [t for t in R.TESTS if t[1] == "mazes"]
R.TESTS[:] = MAZE_TESTS                                   # eval here scores the maze tests only


def load_expanded(ckpt, arm, device):
    """a 358i checkpoint (3 kind rows) into a 4-kind net; the maze row = mean of the practised rows"""
    d = torch.load(ckpt, map_location="cpu")
    assert d["arm"] == arm, (d["arm"], arm)
    state = dict(d["state"])
    w = state["env.weight"]
    if w.shape[0] == len(E.ENVS) - 1:
        state["env.weight"] = torch.cat([w, w.mean(0, keepdim=True)], 0)
    net = R.Net(arm)
    net.load_state_dict(state)
    return net.to(device), d.get("seed")


def carry(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(500 + a.seed)
    if a.init == "pre":
        net, src_seed = load_expanded(a.ckpt, a.arm, device)
        assert src_seed == a.seed, (src_seed, a.seed)
    else:
        net = R.Net(a.arm).to(device)
    rng, round_rng = random.Random(4100 + a.seed), random.Random(4200 + a.seed)   # same stream for pre and fresh
    dev_rng = random.Random(4300 + a.seed)
    dev = {f"maze{s}": [M.make_maze(dev_rng, s) for _ in range(200)] for s in (7, 9)}
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / WARMUP))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "carry_log.jsonl", "w", encoding="utf-8")
    t0, curve = time.time(), {}

    def check(step, loss=None, exact=None):
        res = {k: R.evaluate(net, v, device)["right"] for k, v in dev.items()}
        curve[step] = res
        rec = {"step": step, "min": round((time.time() - t0) / 60, 1), "dev": res}
        if loss is not None:
            rec.update(loss=round(loss.item(), 4), exact=round(exact.mean().item(), 3))
        log.write(json.dumps(rec) + "\n"); log.flush()
        print(json.dumps(rec), flush=True)

    checks = [c for c in a.checks if c <= a.steps]
    if 0 in checks:
        check(0)
    for step in range(1, a.steps + 1):
        net.train()
        size = rng.choice(M.SIZES_PRACTICE)
        items = [M.make_maze(rng, size) for _ in range(a.batch)]
        t, s, y, env = R.tensors(items, device)
        with amp:
            if a.arm == "plain":
                loss, exact = R.ce_and_exact(net.plain_forward(t, s, env), s, y)
            else:
                total = round_rng.randint(1, R.TRAIN_ROUNDS)
                k = round_rng.randint(1, min(total, R.GRAD_ROUNDS))
                ces, hls = [], []
                for lg, q in net.loop_train(t, s, env, total - k, k):
                    c_, ex = R.ce_and_exact(lg, s, y)
                    ces.append(c_); hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
                loss = torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean()
                exact = ex
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step(); sched.step()
        if step in checks:
            check(step, loss, exact)
    torch.save({"arm": a.arm, "seed": a.seed, "state": net.state_dict(), "init": a.init}, out / "final-carry.pt")
    json.dump({"arm": a.arm, "init": a.init, "seed": a.seed, "src": str(a.ckpt) if a.init == "pre" else None,
               "steps": a.steps, "batch": a.batch, "lr": a.lr, "curve": {str(k): v for k, v in curve.items()},
               "steps_to_bar7": next((c for c in checks if curve[c]["maze7"] >= BAR7), NEVER), "minutes": round((time.time() - t0) / 60, 1),
               "device": device}, open(out / "carry_summary.json", "w"), indent=1)


def selftest():
    import claude_rsn358a_envs as E0  # noqa: F401
    tmp = Path(tempfile.mkdtemp())
    for arm in ("loop", "plain"):
        n3 = R.Net(arm)
        st = n3.state_dict()
        st["env.weight"] = st["env.weight"][:3].clone()
        torch.save({"arm": arm, "seed": 1, "state": st}, tmp / f"{arm}.pt")
        net, sd = load_expanded(tmp / f"{arm}.pt", arm, "cpu")
        w = net.env.weight.detach()
        assert sd == 1 and w.shape[0] == 4 and torch.allclose(w[3], w[:3].mean(0)), arm
    assert [t[0] for t in R.TESTS] == ["maze7", "maze9", "maze11", "maze13"]
    print("selftest ok: 3-kind checkpoints load with a mean maze row; eval scores maze tests only")


def smoke(_):
    tmp = Path(tempfile.mkdtemp())
    R.make_tests(argparse.Namespace(out=tmp / "tests"))
    for arm in ("loop", "plain"):
        st = R.Net(arm).state_dict()
        st["env.weight"] = st["env.weight"][:3].clone()
        torch.save({"arm": arm, "seed": 1, "state": st}, tmp / f"{arm}-src.pt")
        for init in ("pre", "fresh"):
            o = tmp / f"{arm}-{init}"
            carry(argparse.Namespace(arm=arm, init=init, seed=1, ckpt=tmp / f"{arm}-src.pt", out=o, steps=4, batch=8,
                                     lr=3e-4, checks=[0, 2, 4]))
            R.run_eval(argparse.Namespace(ckpt=o / "final-carry.pt", tests=tmp / "tests", limit=10, out=o / "t.json"))
    print("smoke ok", tmp)


if __name__ == "__main__":
    if sys.argv[1:2] == ["carry"]:
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--arm", choices=["loop", "plain"], required=True)
        ap.add_argument("--init", choices=["pre", "fresh"], required=True); ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--ckpt"); ap.add_argument("--out", required=True)
        ap.add_argument("--steps", type=int, default=CARRY_STEPS); ap.add_argument("--batch", type=int, default=256)
        ap.add_argument("--lr", type=float, default=3e-4); ap.add_argument("--checks", default=",".join(map(str, CHECKS)))
        args = ap.parse_args()
        args.checks = [int(x) for x in args.checks.split(",")]
        assert args.init == "fresh" or args.ckpt, "--init pre needs --ckpt"
        carry(args)
    elif sys.argv[1:] == ["smoke"]:
        smoke(None)
    elif sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        R.main()
