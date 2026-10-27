#!/usr/bin/env python3
"""T2 (the model picks its own replay) and T1 (fresh-question replay) sleeps, one sleep per call.

Marks: artifacts/claude-dir-t2-selfpick-20260928/PASSMARKS.md and artifacts/claude-dir-t1-fresh-20260928/PASSMARKS.md
(sealed before any run). Helper: Director helper "sleep tests sealer" (Claude, 2026-09-28).
WRITTEN ON A BOX WITH NO TORCH: only `python3 -m py_compile` and the pure-python marks selftest were run here.
The first real run is the queue job's `selftest`; if it fails, stop and report the traceback (do not patch).

It imports the sealed harness (claude_fewex_bench, claude_fewex_data, claude_fewex_eq_bench, claude_fewex_net) and the
distill test's sleep (claude_fewex_distill_sleep.sleep, teacher_rounds, kl_cells, fresh_panel) and edits none of them.
Start points are the ks prep nets ($KS_NETS/loop-s{seed}-pre/{k0,k64,k16384}.pt, written by queue job ks-1-lead0).
fp32 on CPU, one thread per call. Every arm shares the harness's own draws: same maze picks, same round counts, same 512
updates, same optimizer, same 3 draw seeds (seed + k + 0 / 101 / 202) as the distill and ks tests.

Arms (each: 4 cells = seed 0/1 x k 64/16384, 3 draws = 12 sleeps per arm)
  T2   R16    store = first 16 stored sums + 16 grids (the harness's own R16; "random 16": the pool is code-made i.i.d.)
       R16b   store = items 16..31 of the same pool (a second random 16; measures how much "which 16" alone moves the score)
       PICK   store = 8 highest-loss + 8 lowest-loss items per kind, chosen by the post-maze net's own loss on the 128 pool
       HARD   store = the 16 highest-loss items per kind (control: picks failures vs picks something)
  T1   D16    distill's D16 (store 16, true-answer loss + KL to the pre-maze net), as sealed in the distill test
       K16    store 16, the true-answer loss on sums and grids REPLACED by the KL alone (no true labels)
       FRESH  as K16, but the 4 + 4 old-kind inputs of every update are fresh code-made puzzles (no store used for training)
  The single T1 change is FRESH against K16 (inputs fresh instead of stored). R16 and D16 are the fair comparators.

  python -B scripts/claude_dir_t12_sleep.py selftest
  python -B scripts/claude_dir_t12_sleep.py sleep --seed 0 --k 64 --arm PICK --draw 0
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_distill_sleep as DS  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

N = B.N
ROOT = HERE.parent
T2_DIR = ROOT / "artifacts" / "claude-dir-t2-selfpick-20260928"
T1_DIR = ROOT / "artifacts" / "claude-dir-t1-fresh-20260928"
NETS = Path(os.environ.get("KS_NETS", str(Path.home() / "premonition-ks" / "nets")))
SRC = Path(os.environ.get("KS_SRC", "/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927"))
ARM_DIR = {"R16": T2_DIR, "R16b": T2_DIR, "PICK": T2_DIR, "HARD": T2_DIR, "D16": T1_DIR, "K16": T1_DIR, "FRESH": T1_DIR}
ARMS = tuple(ARM_DIR)
SEEDS, BRANCHES = (0, 1), (64, 16384)
DRAW_OFFSETS = (0, 101, 202)
LR = 1e-3
FRESH_STREAM_SEED = 9300000        # fresh old-kind questions: seed + sleep_seed (never the panel seeds 9233200 / 9233201)


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def net_from(path):
    net = N.Net("loop")
    net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    return net


class Env:
    def __init__(self, seed):
        self.seed = seed
        self.depth = EQ.identity_source(SRC / "runs" / f"qual-loop-s{seed}", "loop", seed)["fixed_depth"]
        self.panels, self.banned = D.panels()
        self.old = D.old_panels()
        self.pool_old = D.replay_old()                    # 128 stored sums4 + 128 stored grids5 (the pool to pick from)
        self.fresh, _ = DS.fresh_panel()
        self.pool = EQ.make_pool(seed, self.banned)[0]    # the day's maze layouts (pool[:k] is the day)


# ------------------------------------------------------------------ the model's own choice (T2)
@torch.no_grad()
def item_losses(net, items, rounds=N.TRAIN_ROUNDS, bs=32):
    """Per-item mean cross-entropy over the item's answer cells at round `rounds` (the net's own loss on the stored puzzle)."""
    net.eval()
    out = []
    for i in range(0, len(items), bs):
        t, s, y = N.tensors(items[i:i + bs])
        lg = DS.teacher_rounds(net, t, s, rounds, 1)[0].float()          # [B, T, V]
        b_ = s.shape[0]
        mask = s.view(b_, -1).bool()
        ce = F.cross_entropy(lg.reshape(-1, lg.shape[-1]), y.view(-1), reduction="none").view(b_, -1)
        out += ((ce * mask).sum(1) / mask.sum(1)).tolist()
    return out


def pick_store(net, pool_old, depth, arm):
    """Per kind, 16 of the 128 pool items. PICK: the 8 highest and the 8 lowest own-loss items. HARD: the 16 highest.
    Ties go to the lower pool index. The list keeps pool order. Also returns what the model 'got right' (report only)."""
    store, info = {}, {}
    for kind, items in pool_old.items():
        ce = item_losses(net, items)
        order = sorted(range(len(items)), key=lambda i: (-ce[i], i))      # highest loss first
        idx = order[:16] if arm == "HARD" else order[:8] + order[-8:]
        idx = sorted(idx)
        right = [B.score(net, [it], depth)["right"] for it in items]
        store[kind] = [items[i] for i in idx]
        info[kind] = {"idx": idx, "loss_of_picked": [round(ce[i], 4) for i in idx],
                      "pool_loss_min_median_max": [round(min(ce), 4), round(sorted(ce)[len(ce) // 2], 4), round(max(ce), 4)],
                      "pool_right_at_learned_stop": int(sum(right)), "picked_right": int(sum(right[i] for i in idx)),
                      "overlap_with_first16": len(set(idx) & set(range(16)))}
    return store, info


def store_for(arm, net, env):
    if arm == "R16" or arm in ("D16", "K16", "FRESH"):
        return {k: v[:16] for k, v in env.pool_old.items()}, None
    if arm == "R16b":
        return {k: v[16:32] for k, v in env.pool_old.items()}, None
    return pick_store(net, env.pool_old, env.depth, arm)


# ------------------------------------------------------------------ fresh questions (T1)
class FreshStream:
    """Fresh code-made sums4 and grids5, never equal to a stored puzzle, a fixed-panel puzzle or a fresh-panel puzzle."""

    def __init__(self, sleep_seed, env):
        self.rng = random.Random(FRESH_STREAM_SEED + sleep_seed)
        self.banned = {DS.item_key(x) for v in list(env.pool_old.values()) + list(env.old.values()) + list(env.fresh.values()) for x in v}
        self.drawn, self.skipped, self.seen = 0, 0, set()

    def take(self, make, n):
        out = []
        while len(out) < n:
            it = make()
            key = DS.item_key(it)
            if key in self.banned or key in self.seen:
                self.skipped += 1
                continue
            self.seen.add(key)
            out.append(it)
        self.drawn += n
        return out

    def sums(self, n):
        return self.take(lambda: E.make_sum(self.rng, 4), n)

    def grids(self, n):
        return self.take(lambda: D.latin_legend(self.rng, 5), n)


def sleep_kl(learner, mazes, seed, store, mode, teacher, fresh=None, steps=B.SLEEP_STEPS):
    """distill's sleep (claude_fewex_distill_sleep.sleep) with the old kinds' loss = KL(teacher || student) ONLY (no
    true-answer term). mode K16: inputs from the stored 16. mode FRESH: inputs from `fresh` (fresh code-made puzzles).
    The `rng` calls, `round_rng` calls, optimizer and maze part are line for line the harness's, so every arm is paired."""
    net = learner.net
    rng = random.Random(9262700 + seed)
    round_rng = random.Random(9282700 + seed)
    t0 = time.monotonic()
    kl_log = {"sums4": [], "grids5": []}
    for _ in range(steps):
        old_a = rng.sample(store["sums4"], 4)          # drawn in FRESH mode too, so the maze draw below is the same
        old_b = rng.sample(store["grids5"], 4)
        new = rng.choices(mazes, k=8)
        if mode == "FRESH":
            old_a, old_b = fresh.sums(4), fresh.grids(4)
        losses = []
        for name, items in (("sums4", old_a), ("grids5", old_b), ("mazes", new)):
            t, s, y = N.tensors(items)
            rr = round_rng.randint(1, N.TRAIN_ROUNDS)
            grad = round_rng.randint(1, min(rr, N.GRAD_ROUNDS))
            outs = net.loop_train(t, s, rr - grad, grad)
            if name == "mazes":
                loss = torch.stack([N.ce_and_exact(lg, s, y)[0] for lg, _ in outs]).mean()
            else:
                tl = DS.teacher_rounds(teacher, t, s, rr, grad)
                loss = torch.stack([DS.kl_cells(a, b, s) for a, (b, _) in zip(tl, outs)]).mean()
                kl_log[name].append(loss.item())
            losses.append(loss)
        learner.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
    return time.monotonic() - t0, kl_log


# ------------------------------------------------------------------ one sleep
def sleep_job(seed, k, arm, draw):
    out_dir = ARM_DIR[arm] / "sleeps"
    rec = out_dir / f"s{seed}-k{k}-{arm}-d{draw}.json"
    if rec.exists():
        raise FileExistsError(rec)
    start, started = time.monotonic(), utc()
    env = Env(seed)
    nd = NETS / f"loop-s{seed}-pre"
    student = net_from(nd / f"k{k}.pt")
    teacher = net_from(nd / "k0.pt")
    for p in teacher.parameters():
        p.requires_grad_(False)
    start_old = DS.old_scores(student, env.old, env.depth)
    store, pick_info = store_for(arm, student, env)
    assert all(len(v) == 16 for v in store.values())
    learner = B.Learner(net_from(nd / f"k{k}.pt"), LR)     # a fresh load, as the ks sleeps do (scoring above puts `student` in eval mode)
    sleep_seed = seed + k + DRAW_OFFSETS[draw]
    fresh = FreshStream(sleep_seed, env) if arm == "FRESH" else None
    if arm in ("R16", "R16b", "PICK", "HARD"):
        seconds, stats = DS.sleep(learner, env.pool[:k], sleep_seed, store, "R")
    elif arm == "D16":
        seconds, stats = DS.sleep(learner, env.pool[:k], sleep_seed, store, "D", teacher)
    else:
        seconds, stats = sleep_kl(learner, env.pool[:k], sleep_seed, store, arm, teacher, fresh)
    assert learner.steps == B.SLEEP_STEPS
    net = learner.net
    res = {"seed": seed, "k": k, "arm": arm, "draw": draw, "sleep_seed": sleep_seed, "store_per_kind": 16,
           "updates": learner.steps, "sleep_seconds": seconds, "fixed_depth": env.depth, "started_utc": started,
           "student_sha256": sha(nd / f"k{k}.pt"), "teacher_sha256": sha(nd / "k0.pt"),
           "start_old": {n: v["right"] for n, v in start_old.items()},
           "old": {n: v["right"] for n, v in DS.old_scores(net, env.old, env.depth).items()},
           "fresh_old": {n: v["right"] for n, v in DS.old_scores(net, env.fresh, env.depth).items()},
           "maze_dev": {p: v["right"] for p, v in B.maze_scores(net, env.panels["dev"], env.depth).items()}}
    res["maze9"] = res["maze_dev"]["9"]
    if pick_info is not None:
        res["pick"] = pick_info
    if fresh is not None:
        res["fresh_stream"] = {"puzzles_used_per_kind": fresh.drawn // 2, "skipped_overlaps": fresh.skipped}
    res["seconds_total"] = time.monotonic() - start
    res["finished_utc"] = utc()
    B.dump(rec, res)
    print(json.dumps({"phase": "sleep_done", "seed": seed, "k": k, "arm": arm, "draw": draw, "old": res["old"],
                      "fresh_old": res["fresh_old"], "maze9": res["maze9"], "seconds": round(res["seconds_total"])}), flush=True)


# ------------------------------------------------------------------ selftest (needs torch; runs in the queue job)
def selftest():
    torch.manual_seed(0)
    env = Env(0)
    net = N.Net("loop")
    out = {"utc": utc()}
    # 1. picks: 16 per kind, from the pool, no repeats; HARD is the top 16 loss; PICK is top 8 + bottom 8; R16b is items 16..31
    for arm in ("PICK", "HARD"):
        store, info = pick_store(net, {k: v[:24] for k, v in env.pool_old.items()}, env.depth, arm)
        for kind in store:
            assert len(store[kind]) == 16 and len({DS.item_key(x) for x in store[kind]}) == 16
            idx = info[kind]["idx"]
            assert idx == sorted(idx) and all(0 <= i < 24 for i in idx)
        out[f"pick_{arm}_ok"] = True
    s16, _ = store_for("R16", net, env)
    s16b, _ = store_for("R16b", net, env)
    assert [DS.item_key(x) for x in s16["sums4"]] == [DS.item_key(x) for x in env.pool_old["sums4"][:16]]
    assert [DS.item_key(x) for x in s16b["grids5"]] == [DS.item_key(x) for x in env.pool_old["grids5"][16:32]]
    out["r16_and_r16b_slices_ok"] = True
    # 2. the fresh stream never repeats or touches a store / panel puzzle, and is deterministic for a sleep seed
    fs = FreshStream(64, env)
    a, g = fs.sums(64), fs.grids(64)
    keys = {DS.item_key(x) for x in a + g}
    assert len(keys) == 128 and not keys & fs.banned
    fs2 = FreshStream(64, env)
    assert [DS.item_key(x) for x in fs2.sums(64)] == [DS.item_key(x) for x in a]
    out["fresh_stream_ok"] = {"distinct": len(keys), "skipped": fs.skipped}
    # 3. K16 / FRESH: the KL is zero at step 1 when teacher == student; FRESH differs from K16 afterwards; both finish 2 steps
    base = copy.deepcopy(net)
    for mode in ("K16", "FRESH"):
        learner = B.Learner(copy.deepcopy(base), LR)
        _, kl = sleep_kl(learner, env.pool[:64], 64, s16, mode, copy.deepcopy(base),
                         FreshStream(64, env) if mode == "FRESH" else None, steps=1)
        assert all(abs(v[0]) < 1e-6 for v in kl.values()), kl
        out[f"first_step_kl_self_{mode}"] = {n: v[0] for n, v in kl.items()}
    la = B.Learner(copy.deepcopy(base), LR)
    lb = B.Learner(copy.deepcopy(base), LR)
    teacher = N.Net("loop")
    sleep_kl(la, env.pool[:64], 64, s16, "K16", teacher, steps=2)
    sleep_kl(lb, env.pool[:64], 64, s16, "FRESH", teacher, FreshStream(64, env), steps=2)
    differ = any(not torch.equal(x, y) for x, y in zip(la.net.state_dict().values(), lb.net.state_dict().values()))
    assert differ
    out["k16_and_fresh_differ"] = True
    # 4. R16 through the distill sleep equals the harness sleep (the distill selftest's claim, repeated for 2 steps, custom store)
    lc = B.Learner(copy.deepcopy(base), LR)
    ld = B.Learner(copy.deepcopy(base), LR)
    steps, old = B.SLEEP_STEPS, B.SLEEP_STEPS
    B.SLEEP_STEPS = 2
    try:
        ld.sleep(env.pool[:64], 64, s16)
    finally:
        B.SLEEP_STEPS = old
    DS.sleep(lc, env.pool[:64], 64, s16, "R", steps=2)
    assert all(torch.equal(x, y) for x, y in zip(lc.net.state_dict().values(), ld.net.state_dict().values()))
    out["distill_R_equals_harness_sleep"] = True
    B.dump(T2_DIR / "selftest.json", out)
    print(json.dumps(out), flush=True)
    print("t12 selftest ok", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "sleep"))
    p.add_argument("--seed", type=int, choices=SEEDS)
    p.add_argument("--k", type=int, choices=BRANCHES)
    p.add_argument("--arm", choices=ARMS)
    p.add_argument("--draw", type=int, choices=(0, 1, 2))
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    selftest() if a.cmd == "selftest" else sleep_job(a.seed, a.k, a.arm, a.draw)


if __name__ == "__main__":
    main()
