#!/usr/bin/env python3
"""Sleep that also matches the loop's own pre-maze answers, round by round.

See artifacts/claude-distill-20260928/PASSMARKS.md. Imports the sealed
equal-practice harness (claude_fewex_eq_bench.py, claude_fewex_bench.py) and
never edits it. fp32 on CPU, one thread per job, no autocast.

Commands
  selftest   generalized sleep in mode R equals the harness sleep bit for bit;
             KL is zero when student == teacher; fresh panel has no overlap.
  rebuild    k0.pt, k{k}.pt and the harness's own sleep{k} for one seed and
             one rung, from a rebuilt source net, using harness functions only.
  sleep      one arm x seed x branch x draw; writes one JSON record.
  report     aggregate the 60 records and apply the marks.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

N = B.N
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "claude-distill-20260928"
REBUILD = OUT / "rebuild"
SLEEPS = OUT / "sleeps"
RULER = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"

ARMS = ("R128", "D128", "W128", "R16", "D16")
BRANCHES = (64, 16384)
SEEDS = (0, 1)
DRAW_OFFSETS = (0, 101, 202)       # draw 0 is the harness's own sleep seed, seed + k
KL_WEIGHT = 1.0                    # fixed before any sleep; not tuned
FRESH_SEED = D.SOURCE_SEED + 500   # fresh old-kind panel, report only
LR = 1e-3                          # loop learning rate in the harness


def utc():
    return subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True).strip()


def item_key(item):
    return item.env, tuple(map(tuple, item.tokens))


def fresh_panel():
    """200 sums4 + 200 grids5 from FRESH_SEED, skipping any puzzle in the store or the fixed panel."""
    store, fixed = D.replay_old(), D.old_panels()
    banned = {item_key(x) for v in list(store.values()) + list(fixed.values()) for x in v}
    rng = random.Random(FRESH_SEED)
    out, skipped, seen = {"sums4": [], "grids5": []}, {"sums4": 0, "grids5": 0}, set()
    for name, make in (("sums4", lambda: E.make_sum(rng, 4)), ("grids5", lambda: D.latin_legend(rng, 5))):
        while len(out[name]) < 200:
            it = make()
            key = item_key(it)
            if key in banned or key in seen:
                skipped[name] += 1
                continue
            seen.add(key)
            out[name].append(it)
    return out, skipped


def store_for(arm):
    store = D.replay_old()
    n = 16 if arm.endswith("16") else 128
    return {k: v[:n] for k, v in store.items()}


def teacher_rounds(teacher, t, s, total, grad):
    """Frozen teacher runs the same puzzle for `total` rounds; logits of the last `grad`."""
    with torch.no_grad():
        e, (dr, dc) = teacher.embed(t, s)
        h = torch.zeros_like(e)
        out = []
        for r in range(total):
            h = teacher.step(h, e, dr, dc)
            if r >= total - grad:
                out.append(teacher.read(h)[0])
    return out


def kl_cells(t_logits, s_logits, s):
    """Mean KL(teacher || student) over answer cells, temperature 1."""
    B_ = s.shape[0]
    mask = s.view(B_, -1).bool()
    lt = F.log_softmax(t_logits.float(), -1)[mask]
    ls = F.log_softmax(s_logits.float(), -1)[mask]
    return (lt.exp() * (lt - ls)).sum(-1).mean()


def sleep(learner, mazes, seed, old, mode, teacher=None, steps=B.SLEEP_STEPS):
    """The harness's Learner.sleep (claude_fewex_bench.py) with two optional changes on the
    stored sums and grids only: mode D adds KL_WEIGHT x mean KL to each old kind's loss,
    mode W doubles each old kind's loss. RNG draws are identical in every mode."""
    net = learner.net
    rng = random.Random(9262700 + seed)
    round_rng = random.Random(9282700 + seed)
    t0 = time.monotonic()
    stats = {"total_rounds": {"sums4": [], "grids5": [], "mazes": []},
             "grad_rounds": {"sums4": [], "grids5": [], "mazes": []},
             "kl": {"sums4": [], "grids5": []}}
    for _ in range(steps):
        old_a = rng.sample(old["sums4"], 4)
        old_b = rng.sample(old["grids5"], 4)
        new = rng.choices(mazes, k=8)
        losses = []
        for name, items in (("sums4", old_a), ("grids5", old_b), ("mazes", new)):
            t, s, y = N.tensors(items)
            rr = round_rng.randint(1, N.TRAIN_ROUNDS)
            grad = round_rng.randint(1, min(rr, N.GRAD_ROUNDS))
            stats["total_rounds"][name].append(rr)
            stats["grad_rounds"][name].append(grad)
            outs = net.loop_train(t, s, rr - grad, grad)
            loss = torch.stack([N.ce_and_exact(lg, s, y)[0] for lg, _ in outs]).mean()
            if name != "mazes" and mode == "D":
                tl = teacher_rounds(teacher, t, s, rr, grad)
                kl = torch.stack([kl_cells(a, b, s) for a, (b, _) in zip(tl, outs)]).mean()
                stats["kl"][name].append(kl.item())
                loss = loss + KL_WEIGHT * kl
            elif name != "mazes" and mode == "W":
                loss = 2 * loss
            losses.append(loss)
        learner.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
    return time.monotonic() - t0, stats


@torch.no_grad()
def mean_kl(student, teacher, items, rounds=N.TRAIN_ROUNDS, batch=32):
    """Report only: KL(teacher || student) per round 1..rounds, mean over answer cells."""
    per_round = torch.zeros(rounds)
    cells = 0
    for i in range(0, len(items), batch):
        t, s, _ = N.tensors(items[i:i + batch])
        n = int(s.sum())
        tl = teacher_rounds(teacher, t, s, rounds, rounds)
        sl = teacher_rounds(student, t, s, rounds, rounds)
        for r in range(rounds):
            per_round[r] += kl_cells(tl[r], sl[r], s) * n
        cells += n
    per_round /= cells
    return {"mean_rounds_1_16": per_round.mean().item(), "round_16": per_round[-1].item(),
            "per_round": [round(x, 6) for x in per_round.tolist()]}


def old_scores(net, panel, depth):
    return {name: B.score(net, items, depth) for name, items in panel.items()}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebuild_job(seed, k):
    """Harness steps for k0, rung k and its sleep, in adapt_job's order, from the rebuilt source."""
    out = REBUILD / f"loop-s{seed}-pre"
    rec = out / f"rebuild-k{k}.json"
    if rec.exists():
        raise FileExistsError(rec)
    start = time.monotonic()
    source_dir = REBUILD / f"qual-loop-s{seed}"
    src = EQ.identity_source(source_dir, "loop", seed)
    depth = src["fixed_depth"]
    panels, banned = D.panels()
    pool, keys, digest = EQ.make_pool(seed, banned)
    base = B.load_model(source_dir / "source.pt", "loop")
    old, replay = D.old_panels(), D.replay_old()
    out.mkdir(parents=True, exist_ok=True)
    res = {"seed": seed, "k": k, "started_utc": utc(), "fixed_depth": depth,
           "source_sha256": sha(source_dir / "source.pt"), "support_sha256": digest,
           "rungs": {}, "old": {}, "sleep": {}}
    res["rungs"]["0"] = B.maze_scores(base, panels["dev"], depth)
    res["old"]["before"] = old_scores(base, old, depth)
    if k == BRANCHES[0]:
        B.save_stage(base, out, "k0")
    learner = B.Learner(copy.deepcopy(base), LR)
    for batch in EQ.batches(pool, k, seed):
        learner.maze_batch(batch)
    assert learner.steps == EQ.N_UPDATES
    net = learner.net
    res["rungs"][str(k)] = B.maze_scores(net, panels["dev"], depth)
    B.save_stage(net, out, f"k{k}")
    res["old"][f"after_{k}"] = old_scores(net, old, depth)
    sleeper = B.Learner(copy.deepcopy(net), LR)
    seconds = sleeper.sleep(pool[:k], seed + k, replay)
    assert sleeper.steps == B.SLEEP_STEPS
    res["sleep"][str(k)] = {"seconds": seconds, "updates": sleeper.steps,
                            "old": old_scores(sleeper.net, old, depth),
                            "maze_dev": B.maze_scores(sleeper.net, panels["dev"], depth)}
    B.save_stage(sleeper.net, out, f"sleep{k}")
    res["checkpoint_sha256"] = {n: sha(out / f"{n}.pt") for n in (f"k{k}", f"sleep{k}")}
    res["seconds"] = time.monotonic() - start
    res["finished_utc"] = utc()
    res["compare_original"] = compare_original(res, seed, k)
    B.dump(rec, res)
    print(json.dumps({"phase": "rebuild_done", "seed": seed, "k": k,
                      "exact": res["compare_original"]["all_exact"]}), flush=True)


def compare_original(res, seed, k):
    orig = json.loads((RULER / f"loop-s{seed}-pre" / "adapt.json").read_text())
    pairs = {
        "rung0_maze_dev": (orig["rungs"]["0"], res["rungs"]["0"]),
        "old_before": (orig["old"]["before"], res["old"]["before"]),
        f"rung{k}_maze_dev": (orig["rungs"][str(k)], res["rungs"][str(k)]),
        f"old_after_{k}": (orig["old"][f"after_{k}"], res["old"][f"after_{k}"]),
        f"sleep{k}_old": (orig["sleep"][str(k)]["old"], res["sleep"][str(k)]["old"]),
        f"sleep{k}_maze_dev": (orig["sleep"][str(k)]["maze_dev"], res["sleep"][str(k)]["maze_dev"]),
    }
    out = {"support_sha256_equal": orig["support_sha256"] == res["support_sha256"]}
    for name, (a, b) in pairs.items():
        out[name] = {"exact": a == b,
                     "right_original": {p: v["right"] for p, v in a.items()},
                     "right_rebuild": {p: v["right"] for p, v in b.items()}}
    out["all_exact"] = all(v["exact"] for v in out.values() if isinstance(v, dict))
    return out


def sleep_job(seed, k, arm, draw):
    rec = SLEEPS / f"s{seed}-k{k}-{arm}-d{draw}.json"
    if rec.exists():
        raise FileExistsError(rec)
    start = time.monotonic()
    started = utc()
    src_dir = REBUILD / f"loop-s{seed}-pre"
    depth = EQ.identity_source(REBUILD / f"qual-loop-s{seed}", "loop", seed)["fixed_depth"]
    panels, banned = D.panels()
    pool, _, digest = EQ.make_pool(seed, banned)
    old, (fresh, _) = D.old_panels(), fresh_panel()
    store = store_for(arm)
    full_store = D.replay_old()
    student = B.load_model(src_dir / f"k{k}.pt", "loop")
    teacher = B.load_model(src_dir / "k0.pt", "loop")
    for p in teacher.parameters():
        p.requires_grad_(False)
    kl_before = {n: mean_kl(student, teacher, v) for n, v in full_store.items()}
    learner = B.Learner(copy.deepcopy(student), LR)
    sleep_seed = seed + k + DRAW_OFFSETS[draw]
    seconds, stats = sleep(learner, pool[:k], sleep_seed, store, arm[0],
                           teacher if arm[0] == "D" else None)
    assert learner.steps == B.SLEEP_STEPS
    net = learner.net
    res = {"seed": seed, "branch": k, "arm": arm, "draw": draw, "sleep_seed": sleep_seed,
           "mode": arm[0], "store_per_kind": len(store["sums4"]), "kl_weight": KL_WEIGHT,
           "updates": learner.steps, "sleep_seconds": seconds, "fixed_depth": depth,
           "support_sha256": digest, "started_utc": started,
           "student_sha256": sha(src_dir / f"k{k}.pt"), "teacher_sha256": sha(src_dir / "k0.pt"),
           "teacher_used_in_loss": arm[0] == "D",
           "old": old_scores(net, old, depth),
           "fresh_old": old_scores(net, fresh, depth),
           "maze_dev": B.maze_scores(net, panels["dev"], depth),
           "kl_store128_before": kl_before,
           "kl_store128_after": {n: mean_kl(net, teacher, v) for n, v in full_store.items()},
           "train_rounds": {
               "mean_total": {n: sum(v) / len(v) for n, v in stats["total_rounds"].items()},
               "mean_grad": {n: sum(v) / len(v) for n, v in stats["grad_rounds"].items()}},
           "sleep_kl_term": {n: (sum(v) / len(v) if v else None,
                                 v[0] if v else None, v[-1] if v else None)
                             for n, v in stats["kl"].items()}}
    res["sleep_kl_term_note"] = "per kind: (mean over 512 steps, first step, last step); D arms only"
    res["seconds_total"] = time.monotonic() - start
    res["finished_utc"] = utc()
    B.dump(rec, res)
    print(json.dumps({"phase": "sleep_done", "seed": seed, "k": k, "arm": arm, "draw": draw,
                      "old": {n: v["right"] for n, v in res["old"].items()},
                      "maze9": res["maze_dev"]["9"]["right"],
                      "seconds": round(res["seconds_total"])}), flush=True)


def teacher_job():
    """Report only: the teacher's own scores and its fresh-panel scores, both seeds."""
    rec = OUT / "teacher.json"
    fresh, skipped = fresh_panel()
    res = {"fresh_seed": FRESH_SEED, "fresh_skipped_overlaps": skipped, "started_utc": utc()}
    panels, _ = D.panels()
    for seed in SEEDS:
        net = B.load_model(REBUILD / f"loop-s{seed}-pre" / "k0.pt", "loop")
        res[str(seed)] = {"old": old_scores(net, D.old_panels(), 16),
                          "fresh_old": old_scores(net, fresh, 16)}
    res["finished_utc"] = utc()
    B.dump(rec, res)


def selftest():
    torch.manual_seed(0)
    panels, banned = D.panels()
    pool, _, _ = EQ.make_pool(0, banned)
    store = store_for("R128")
    base = N.Net("loop")
    # 1. mode R equals the harness sleep bit for bit (few steps, fresh net).
    steps = 3
    a = B.Learner(copy.deepcopy(base), LR)
    B_steps, B.SLEEP_STEPS = B.SLEEP_STEPS, steps
    try:
        a.sleep(pool[:64], 64, store)
    finally:
        B.SLEEP_STEPS = B_steps
    b = B.Learner(copy.deepcopy(base), LR)
    sleep(b, pool[:64], 64, store, "R", steps=steps)
    same = all(torch.equal(x, y) for x, y in zip(a.net.state_dict().values(), b.net.state_dict().values()))
    # 2. W differs from R; D with teacher == student has zero KL at the first step.
    teacher = copy.deepcopy(base)
    c = B.Learner(copy.deepcopy(base), LR)
    _, st = sleep(c, pool[:64], 64, store, "D", teacher, steps=1)
    fresh, skipped = fresh_panel()
    fixed_keys = {item_key(x) for v in D.old_panels().values() for x in v}
    store_keys = {item_key(x) for v in D.replay_old().values() for x in v}
    fresh_keys = {item_key(x) for v in fresh.values() for x in v}
    out = {"mode_R_equals_harness_sleep": same,
           "first_step_kl_self": {n: v[0] for n, v in st["kl"].items()},
           "fresh_sizes": {n: len(v) for n, v in fresh.items()},
           "fresh_unique": len(fresh_keys),
           "fresh_overlap_store": len(fresh_keys & store_keys),
           "fresh_overlap_fixed_panel": len(fresh_keys & fixed_keys),
           "fresh_skipped": skipped, "utc": utc()}
    assert same and all(abs(v) < 1e-6 for v in out["first_step_kl_self"].values())
    assert out["fresh_unique"] == 400 and not out["fresh_overlap_store"] and not out["fresh_overlap_fixed_panel"]
    B.dump(OUT / "selftest.json", out)
    print(json.dumps(out), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "rebuild", "sleep", "teacher"))
    p.add_argument("--seed", type=int, choices=SEEDS)
    p.add_argument("--k", type=int, choices=BRANCHES)
    p.add_argument("--arm", choices=ARMS)
    p.add_argument("--draw", type=int, choices=(0, 1, 2))
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "rebuild":
        rebuild_job(a.seed, a.k)
    elif a.cmd == "teacher":
        teacher_job()
    else:
        sleep_job(a.seed, a.k, a.arm, a.draw)


if __name__ == "__main__":
    main()
