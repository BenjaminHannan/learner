#!/usr/bin/env python3
"""rsn-358m (sleep research thread, 2026-09-26): which net picks up a NEW kind of puzzle faster, loop or plain?

Stage 1 = rsn-358i exactly (scripts/claude_rsn358i_run.py: 358a v2 + grid legend + half-narrow attention heads),
trained from scratch on fresh seeds 5-8, 60,000 steps on sums, grids and number puzzles only. Its checkpoint is scored
on the 358i tests (report only: an independent replication of 358i).
Stage 2 (the test): the same short practice for both nets on a kind neither has seen, mazes
(scripts/claude_rsn358m_maze.py: perfect mazes, unique path, mark the path cells), small sizes only (5x5, 7x7),
MAZE_STEPS steps, batch 256, constant lr 3e-4 after a 200-step warm-up; then scored on bigger mazes.
The maze kind gets its own kind embedding row (4th row, present but unused in stage 1).

  python -B scripts/claude_rsn358m_run.py make-tests --out artifacts/claude-rsn358m-20260926/tests
  python -B scripts/claude_rsn358m_run.py train --arm loop --seed 5 --out W/loop-s5          (stage 1, as 358i)
  python -B scripts/claude_rsn358m_run.py maze  --ckpt W/loop-s5/final.pt --out W/loop-s5    (stage 2 -> final-maze.pt)
  python -B scripts/claude_rsn358m_run.py eval  --ckpt W/loop-s5/final-maze.pt --tests ... --out ...
  python -B scripts/claude_rsn358m_run.py smoke
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
import claude_rsn358i_run as I  # noqa: E402  (358i design: legend grids, v2 stop, half-narrow heads, sums10/12 tests)
import claude_rsn358m_maze as M  # noqa: E402

R, E = I.R, I.E
MAZE_STEPS = 6000
BASE_KINDS = ["sums", "grids", "numbers"]
E.ENVS.append("mazes")
R.TESTS += [("maze7", "mazes", 7, 35841, "maze practised size"), ("maze9", "mazes", 9, 35842, "maze bigger"),
            ("maze11", "mazes", 11, 35843, "maze report"), ("maze13", "mazes", 13, 35844, "maze report")]

_check_v1 = E.check


def check(item, pred):
    return M.check_maze(item, pred) if item.env == "mazes" else _check_v1(item, pred)


E.check = check

_make_test_v1 = R.make_test


def make_test(name, env, size, seed, n=R.N_TEST):
    if env == "mazes":
        rng = random.Random(seed)
        return [M.make_maze(rng, size) for _ in range(n)]
    return _make_test_v1(name, env, size, seed, n)


R.make_test = make_test


def batch(self, B):                                     # stage 1 practises only the three 358i kinds
    env = self.rng.choice(BASE_KINDS)
    size = self.rng.choice(E.TRAIN_SIZES[env])
    return [self.item(env, size) for _ in range(B)]


R.Source.batch = batch


def maze(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(100 + a.seed_offset)
    net = R.load(a.ckpt, device)
    d = torch.load(a.ckpt, map_location="cpu")
    rng, round_rng = random.Random(4100 + d["seed"]), random.Random(4200 + d["seed"])
    dev_rng = random.Random(4300 + d["seed"])
    dev = {f"maze{s}": [M.make_maze(dev_rng, s) for _ in range(200)] for s in (7, 9)}
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / 200))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    out = Path(a.out)
    log = open(out / "maze_log.jsonl", "w", encoding="utf-8")
    t0 = time.time()
    for step in range(1, a.steps + 1):
        net.train()
        items = [M.make_maze(rng, rng.choice(M.SIZES_PRACTICE)) for _ in range(1)]
        size = items[0].size
        items += [M.make_maze(rng, size) for _ in range(a.batch - 1)]
        t, s, y, env = R.tensors(items, device)
        with amp:
            if net.arm == "plain":
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
        if step % a.log_every == 0 or step == a.steps:
            rec = {"step": step, "loss": round(loss.item(), 4), "exact": round(exact.mean().item(), 3),
                   "min": round((time.time() - t0) / 60, 1),
                   "dev": {k: R.evaluate(net, v, device)["right"] for k, v in dev.items()}}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
    torch.save({"arm": net.arm, "seed": d["seed"], "state": net.state_dict(), "maze_steps": a.steps}, out / "final-maze.pt")


def smoke(_):
    tmp = Path(tempfile.mkdtemp())
    R.make_tests(argparse.Namespace(out=tmp / "tests"))
    for arm in R.ARMS:
        R.train(argparse.Namespace(arm=arm, seed=5, out=tmp / arm, steps=6, batch=16, lr=3e-4, warmup=2,
                                   latin_pool=50, log_every=2))
        maze(argparse.Namespace(ckpt=tmp / arm / "final.pt", out=tmp / arm, steps=4, batch=8, lr=3e-4, log_every=2,
                                seed_offset=0))
        R.run_eval(argparse.Namespace(ckpt=tmp / arm / "final-maze.pt", tests=tmp / "tests", limit=10,
                                      out=tmp / arm / "t.json"))
    print("smoke ok", tmp)


if __name__ == "__main__":
    if sys.argv[1:2] == ["maze"]:
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        ap.add_argument("--steps", type=int, default=MAZE_STEPS); ap.add_argument("--batch", type=int, default=256)
        ap.add_argument("--lr", type=float, default=3e-4); ap.add_argument("--log-every", type=int, default=500)
        ap.add_argument("--seed-offset", type=int, default=0)
        maze(ap.parse_args())
    elif sys.argv[1:] == ["smoke"]:
        smoke(None)
    else:
        R.main()
