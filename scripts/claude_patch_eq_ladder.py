#!/usr/bin/env python3
"""Resumable driver for the equal-practice ladder (same computation as
claude_fewex_eq_bench.adapt_job; that harness is not edited and is still what `holdout` uses).

Why: the container running this test restarts without warning and kills every process; the
harness has no resume, and one patch ladder takes many hours. This driver runs the harness's
own pieces unchanged (make_pool, batches, the plug-in's Learner, B.maze_scores, B.save_stage,
B.SLEEP_STEPS, the same assertions, the same output files: k*.pt, sleep*.pt, partial.json,
adapt.json) and adds only checkpoints:
  * ck.pt every CK_EVERY batches inside a rung (net incl. patch buffers, optimizer, scheduler,
    step and write counters); on restart the rung continues from the saved batch, skipping the
    same first n batches of the harness's deterministic generator;
  * a finished rung (scored, checkpointed, slept where required) is recorded in partial.json
    and never redone.
Nothing in the computation uses torch's or Python's global RNG, so a resumed run is
bit-identical to an uninterrupted one (--selftest checks this). Wall-clock fields sum the
segments and are labelled; `interruptions` counts restarts.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B  # noqa: E402
import claude_fewex_data as D  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402

CK_EVERY = 32


def learner_cls():
    return getattr(B.N, "Learner", B.Learner)


def save_ck(path, k, done, learner, seconds):
    tmp = path.with_suffix(".tmp")
    torch.save({"k": k, "done": done, "net": learner.net.state_dict(), "opt": learner.opt.state_dict(),
                "sched": learner.sched.state_dict(), "steps": learner.steps,
                "writes": getattr(learner, "writes", 0), "write_rounds": getattr(learner, "write_rounds", 0),
                "write_seconds": getattr(learner, "write_seconds", 0.0), "seconds": seconds}, tmp)
    tmp.replace(path)


def train_rung(base, lr, pool, k, seed, out, n_batches=EQ.N_BATCHES, stop_after=None):
    """The harness's rung loop, resumable. Returns the trained learner and seconds spent."""
    learner = learner_cls()(copy.deepcopy(base), lr)
    ck, done, prior = out / "ck.pt", 0, 0.0
    if ck.exists():
        st = torch.load(ck, map_location="cpu", weights_only=False)
        if st["k"] == k:
            learner.net.load_state_dict(st["net"])
            learner.opt.load_state_dict(st["opt"])
            learner.sched.load_state_dict(st["sched"])
            learner.steps, done, prior = st["steps"], st["done"], st["seconds"]
            for name in ("writes", "write_rounds", "write_seconds"):
                if hasattr(learner, name):
                    setattr(learner, name, st[name])
    t0 = time.monotonic()
    for i, batch in enumerate(EQ.batches(pool, k, seed)):
        if i >= n_batches:
            break
        if i < done:
            continue
        learner.maze_batch(batch)
        done = i + 1
        if done % CK_EVERY == 0 or done == n_batches:
            save_ck(ck, k, done, learner, prior + time.monotonic() - t0)
        if stop_after is not None and done == stop_after:
            return learner, prior + time.monotonic() - t0
    return learner, prior + time.monotonic() - t0


def job(arm, seed, init, source_dir, out):
    if (out / "adapt.json").exists():
        raise FileExistsError("equal-practice dev run already complete")
    src = EQ.identity_source(source_dir, arm, seed)
    depth = src["fixed_depth"]
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    panels, banned = D.panels()
    pool, keys, digest = EQ.make_pool(seed, banned)
    base = B.load_model(source_dir / "source.pt", arm) if init == "pre" else None
    if init != "pre":
        torch.manual_seed(900000 + seed)
        base = B.N.Net(arm)
    old = D.old_panels()
    replay = D.replay_old()
    out.mkdir(parents=True, exist_ok=True)
    partial = out / "partial.json"
    if partial.exists():
        res = json.loads(partial.read_text())
        res["interruptions"] = res.get("interruptions", 0) + 1
    else:
        res = {
            "arm": arm, "seed": seed, "init": init, "source": str(source_dir),
            "fixed_depth": depth, "lr": lr, "weights": base.weight_count(),
            "persistent_coefficients": base.weight_count(),
            "support_unique_layouts": len(keys), "support_panel_overlap": len(keys & banned),
            "support_sha256": digest, "rung_batches": EQ.N_BATCHES,
            "batch_size": B.MAZE_BATCH, "updates_per_batch": B.UPDATES,
            "optimizer_updates_per_rung": EQ.N_UPDATES,
            "visits_per_layout": {str(k): EQ.N_BATCHES * B.MAZE_BATCH // k for k in EQ.RUNGS},
            "panel_layouts": {split: {str(s): len({D.layout_key(x) for x in items})
                                      for s, items in panel.items()}
                              for split, panel in panels.items()},
            "rungs": {}, "old": {}, "sleep": {}, "rung_seconds": {}, "interruptions": 0,
            "driver": "claude_patch_eq_ladder.py (resumable; same computation as the harness's adapt_job)"}
        res["rungs"]["0"] = B.maze_scores(base, panels["dev"], depth)
        res["old"]["before"] = EQ.old_scores(base, old, depth)
        B.save_stage(base, out, "k0")
        B.dump(partial, res)
    for k in EQ.RUNGS:
        need_sleep = k in (64, 16384)
        if str(k) in res["rung_seconds"]:
            continue
        learner, train_seconds = train_rung(base, lr, pool, k, seed, out)
        if learner.steps != EQ.N_UPDATES:
            raise ValueError(f"k={k}: expected {EQ.N_UPDATES} updates, got {learner.steps}")
        net = learner.net
        res["rungs"][str(k)] = B.maze_scores(net, panels["dev"], depth)
        B.save_stage(net, out, f"k{k}")
        if need_sleep:
            res["old"][f"after_{k}"] = EQ.old_scores(net, old, depth)
            sleeper = learner_cls()(copy.deepcopy(net), lr)
            sleep_seconds = sleeper.sleep(pool[:k], seed + k, replay)
            if sleeper.steps != B.SLEEP_STEPS:
                raise ValueError(f"sleep k={k}: expected {B.SLEEP_STEPS} updates")
            res["sleep"][str(k)] = {"seconds": sleep_seconds, "updates": sleeper.steps,
                                    "old": EQ.old_scores(sleeper.net, old, depth),
                                    "maze_dev": B.maze_scores(sleeper.net, panels["dev"], depth)}
            B.save_stage(sleeper.net, out, f"sleep{k}")
        extra = {n: getattr(learner, n) for n in ("writes", "write_rounds", "write_seconds")
                 if hasattr(learner, n)}
        res.setdefault("rung_extra", {})[str(k)] = extra
        res["rung_seconds"][str(k)] = train_seconds  # training only, summed across restarts
        B.dump(partial, res)
        (out / "ck.pt").unlink(missing_ok=True)
        print(json.dumps({"phase": "rung", "arm": arm, "seed": seed, "init": init, "k": k,
                          "right9": res["rungs"][str(k)]["9"]["right"],
                          "train_seconds": round(train_seconds),
                          "interruptions": res["interruptions"]}), flush=True)
    res["training_seconds"] = sum(res["rung_seconds"].values())
    res["training_seconds_note"] = "sum of per-rung training segments (checkpointed across restarts); excludes scoring and sleep"
    B.dump(out / "adapt.json", res)
    print(json.dumps({"phase": "adapt_done", "arm": arm, "seed": seed, "init": init,
                      "seconds": round(res["training_seconds"])}), flush=True)


def selftest(a):
    """A rung interrupted after 3 batches and resumed equals an uninterrupted one, bit for bit,
    and both equal the harness's own loop over its own batches()."""
    import tempfile
    src = json.loads((a.source / "source.json").read_text())
    _, banned = D.panels()
    pool, _, _ = EQ.make_pool(a.seed, banned)
    base = B.load_model(a.source / "source.pt", a.arm) if a.init == "pre" else None
    if base is None:
        torch.manual_seed(900000 + a.seed)
        base = B.N.Net(a.arm)
    lr, n = 1e-3, 6
    full, _ = train_rung(base, lr, pool, 1, a.seed, Path(tempfile.mkdtemp()), n_batches=n)
    d = Path(tempfile.mkdtemp())
    part, _ = train_rung(base, lr, pool, 1, a.seed, d, n_batches=n, stop_after=3)
    save_ck(d / "ck.pt", 1, 3, part, 0.0)
    resumed, _ = train_rung(base, lr, pool, 1, a.seed, d, n_batches=n)
    ref = learner_cls()(copy.deepcopy(base), lr)
    for i, batch in enumerate(EQ.batches(pool, 1, a.seed)):
        if i == n:
            break
        ref.maze_batch(batch)
    same = lambda x, y: all(torch.equal(x.net.state_dict()[k], y.net.state_dict()[k]) for k in x.net.state_dict())
    ok = {"resumed_equals_uninterrupted": same(full, resumed), "driver_equals_harness_loop": same(full, ref),
          "steps": [full.steps, resumed.steps, ref.steps], "batches": n}
    print(json.dumps(ok))
    assert ok["resumed_equals_uninterrupted"] and ok["driver_equals_harness_loop"]
    if a.out:
        B.dump(a.out, ok)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("adapt", "selftest"))
    ap.add_argument("--plugin", default="claude_fewex_net")
    ap.add_argument("--arm", choices=("loop", "plain"), default="loop")
    ap.add_argument("--seed", type=int, choices=(0, 1), required=True)
    ap.add_argument("--init", choices=("pre", "fresh"), required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    B.N = EQ.B.N = importlib.import_module(a.plugin)
    torch.set_num_threads(a.threads)
    if a.cmd == "adapt":
        job(a.arm, a.seed, a.init, a.source, a.out)
    else:
        selftest(a)
