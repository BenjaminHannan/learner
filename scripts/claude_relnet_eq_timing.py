#!/usr/bin/env python3
"""Timing probe: relation net vs the baseline loop, one process, CPU fp32. Training losses only; nothing is scored."""
import argparse, copy, json, random, sys, time
from pathlib import Path
import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B, claude_fewex_data as D, claude_fewex_net as base
import claude_relnet_eq_plugin as P

def run(mod, learner_cls, threads):
    torch.set_num_threads(threads)
    B.N = mod
    rng = random.Random(11)
    mazes = [D.make_maze(rng, 9) for _ in range(32)]
    torch.manual_seed(0)
    net = mod.Net("loop")
    r = {"threads": threads}
    # practice: 10 real-stream steps (random round schedule)
    pr = mod.Practice("loop", 0, 12000)
    src, t0 = random.Random(7000000), time.monotonic()
    for _ in range(10):
        pr.step(D.source_batch(src, 64))
    r["practice_step_s"] = (time.monotonic() - t0) / 10
    lr_ = learner_cls(net, 1e-3)
    lr_.maze_batch(mazes)   # warm-up
    t0 = time.monotonic()
    for _ in range(2):
        lr_.maze_batch(mazes)
    r["maze_batch_9x9_b32_s"] = (time.monotonic() - t0) / 2
    old = D.replay_old()
    B.SLEEP_STEPS = 4
    r["sleep_step_s"] = lr_.sleep(mazes, 5, old) / 4
    for s in (7, 9, 11):
        ms = [D.make_maze(rng, s) for _ in range(32)]
        t, sl, _ = mod.tensors(ms)
        t0 = time.monotonic()
        net.infer_rounds(t, sl, 48)
        r[f"infer48_{s}x{s}_b32_s"] = time.monotonic() - t0
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--threads", type=int, default=1); ap.add_argument("--out")
    a = ap.parse_args()
    res = {"torch": torch.__version__, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "relnet": run(P, P.Learner, a.threads), "loop": run(base, B.Learner, a.threads)}
    print(json.dumps(res, indent=1))
    if a.out: Path(a.out).write_text(json.dumps(res, indent=1))
