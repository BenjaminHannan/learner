#!/usr/bin/env python3
"""Equal-practice few-example ruler; see ADDENDUM-4.md.

Reuses the sealed model, learner and scorers without changing the old harness.
All baseline training and inference are fp32 CPU with no autocast.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_bench as B
import claude_fewex_data as D

ART = B.ART
EQ_RUNS = ART / "eq-runs"
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
N_BATCHES = 512
N_UPDATES = N_BATCHES * B.UPDATES
POOL_SEED = 9292700


def make_pool(seed, banned):
    """One ordered, nested, panel-disjoint support pool per paired seed."""
    rng = random.Random(POOL_SEED + seed)
    seen = set()
    pool = [D.unique_maze(rng, 9, banned, seen) for _ in range(RUNGS[-1])]
    assert len(seen) == RUNGS[-1] and not seen & banned
    keys = [D.layout_key(item) for item in pool]
    digest = hashlib.sha256("\n".join(keys).encode()).hexdigest()
    return pool, seen, digest


def batches(pool, k, seed):
    """Exactly 16,384 slots, in shuffled cycles shared across arms."""
    rng = random.Random(9272700 + seed + k)
    order = list(range(k))
    pos = k
    for _ in range(N_BATCHES):
        batch = []
        while len(batch) < B.MAZE_BATCH:
            if pos == k:
                rng.shuffle(order)
                pos = 0
            take = min(B.MAZE_BATCH - len(batch), k - pos)
            batch.extend(pool[i] for i in order[pos:pos + take])
            pos += take
        yield batch


def identity_source(source_dir, arm, seed):
    source = json.loads((source_dir / "source.json").read_text())
    if (source["arm"], source["seed"]) != (arm, seed):
        raise ValueError("source checkpoint identity mismatch")
    if not (source["old"]["sums4"]["right"] >= 190 and
            source["old"]["grids5"]["right"] >= 190 and
            source["gradient_check"]["nonzero_all"]):
        raise ValueError("qualified source failed V1 or V2")
    return source


def old_scores(net, panel, depth):
    return {name: B.score(net, items, depth) for name, items in panel.items()}


def adapt_job(arm, seed, init, source_dir, out):
    if (out / "adapt.json").exists():
        raise FileExistsError("equal-practice dev run already complete")
    start = time.monotonic()
    src = identity_source(source_dir, arm, seed)
    depth = src["fixed_depth"]
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    panels, banned = D.panels()
    pool, keys, digest = make_pool(seed, banned)
    if init == "pre":
        base = B.load_model(source_dir / "source.pt", arm)
    else:
        torch.manual_seed(900000 + seed)
        base = B.N.Net(arm)
    old = D.old_panels()
    replay = D.replay_old()
    out.mkdir(parents=True, exist_ok=True)
    res = {
        "arm": arm, "seed": seed, "init": init, "source": str(source_dir),
        "fixed_depth": depth, "lr": lr, "weights": base.weight_count(),
        "persistent_coefficients": base.weight_count(),
        "support_unique_layouts": len(keys), "support_panel_overlap": len(keys & banned),
        "support_sha256": digest, "rung_batches": N_BATCHES,
        "batch_size": B.MAZE_BATCH, "updates_per_batch": B.UPDATES,
        "optimizer_updates_per_rung": N_UPDATES,
        "visits_per_layout": {str(k): N_BATCHES * B.MAZE_BATCH // k for k in RUNGS},
        "panel_layouts": {split: {str(s): len({D.layout_key(x) for x in items})
                                  for s, items in panel.items()}
                          for split, panel in panels.items()},
        "rungs": {}, "old": {}, "sleep": {}, "rung_seconds": {},
    }
    res["rungs"]["0"] = B.maze_scores(base, panels["dev"], depth)
    res["old"]["before"] = old_scores(base, old, depth)
    B.save_stage(base, out, "k0")
    for k in RUNGS:
        t0 = time.monotonic()
        learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(base), lr)
        for batch in batches(pool, k, seed):
            learner.maze_batch(batch)
        if learner.steps != N_UPDATES:
            raise ValueError(f"k={k}: expected {N_UPDATES} updates, got {learner.steps}")
        net = learner.net
        res["rungs"][str(k)] = B.maze_scores(net, panels["dev"], depth)
        B.save_stage(net, out, f"k{k}")
        if k in (64, 16384):
            res["old"][f"after_{k}"] = old_scores(net, old, depth)
            sleeper = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), lr)
            sleep_seconds = sleeper.sleep(pool[:k], seed + k, replay)
            if sleeper.steps != B.SLEEP_STEPS:
                raise ValueError(f"sleep k={k}: expected {B.SLEEP_STEPS} updates")
            res["sleep"][str(k)] = {
                "seconds": sleep_seconds, "updates": sleeper.steps,
                "old": old_scores(sleeper.net, old, depth),
                "maze_dev": B.maze_scores(sleeper.net, panels["dev"], depth),
            }
            B.save_stage(sleeper.net, out, f"sleep{k}")
        res["rung_seconds"][str(k)] = time.monotonic() - t0
        B.dump(out / "partial.json", res)
        print(json.dumps({"phase": "rung", "arm": arm, "seed": seed, "init": init,
                          "k": k, "right9": res["rungs"][str(k)]["9"]["right"],
                          "seconds": round(time.monotonic() - start)}), flush=True)
    res["training_seconds"] = time.monotonic() - start
    B.dump(out / "adapt.json", res)
    print(json.dumps({"phase": "adapt_done", "arm": arm, "seed": seed, "init": init,
                      "seconds": round(res["training_seconds"])}), flush=True)


def all_paths():
    for arm in ("loop", "plain"):
        for seed in (0, 1):
            for init in ("pre", "fresh"):
                yield arm, seed, init, EQ_RUNS / f"{arm}-s{seed}-{init}"


def gate_job():
    gate_path = ART / "EQ-DEV-GATE.json"
    if gate_path.exists():
        raise FileExistsError("equal-practice dev gate already written")
    arms = {}
    v1 = v2 = True
    for arm, seed, init, path in all_paths():
        src = json.loads((ART / "runs" / f"qual-{arm}-s{seed}" / "source.json").read_text())
        v1 &= all(src["old"][kind]["right"] >= 190 for kind in ("sums4", "grids5"))
        v2 &= bool(src["gradient_check"]["nonzero_all"])
        r = json.loads((path / "adapt.json").read_text())
        if (r["arm"], r["seed"], r["init"]) != (arm, seed, init):
            raise ValueError("dev run identity mismatch")
        counts = {str(k): r["rungs"][str(k)]["9"]["right"] for k in RUNGS}
        middle = [k for k in RUNGS if 30 < counts[str(k)] < 270]
        arms[f"{arm}-s{seed}-{init}"] = {"right9": counts, "middle_rungs": middle,
                                       "middle_count": len(middle)}
    v3 = any(x["middle_count"] >= 3 for x in arms.values())
    result = {"V1": bool(v1), "V2": bool(v2), "V3": v3,
              "verdict": "PASS" if v1 and v2 and v3 else "INCONCLUSIVE",
              "arms": arms}
    B.dump(gate_path, result)
    print(json.dumps({k: result[k] for k in ("V1", "V2", "V3", "verdict")}))


def holdout_job(arm, seed, init, out):
    gate = json.loads((ART / "EQ-DEV-GATE.json").read_text())
    if gate["verdict"] != "PASS":
        raise ValueError("dev V3 did not pass; holdout must stay sealed")
    if (out / "holdout.json").exists():
        raise FileExistsError("holdout already evaluated")
    marker = out / "holdout.started"
    with marker.open("x"):
        pass  # Never silently re-open this arm's holdout after a partial run.
    dev = json.loads((out / "adapt.json").read_text())
    if (dev["arm"], dev["seed"], dev["init"]) != (arm, seed, init):
        raise ValueError("dev run identity mismatch")
    panels, _ = D.panels()
    scores = {}
    for name in ("0",) + tuple(map(str, RUNGS)) + ("sleep64", "sleep16384"):
        stage = f"k{name}" if name[0].isdigit() else name
        net = B.load_model(out / f"{stage}.pt", arm)
        scores[name] = B.maze_scores(net, panels["holdout"], dev["fixed_depth"])
    B.dump(out / "holdout.json", {"arm": arm, "seed": seed, "init": init,
                                   "scores": scores, "support_sha256": dev["support_sha256"]})


def selftest():
    panels, banned = D.panels()
    for seed in (0, 1):
        pool, seen, digest = make_pool(seed, banned)
        assert len(seen) == RUNGS[-1] and not seen & banned
        for k in RUNGS:
            visit = {D.layout_key(x): 0 for x in pool[:k]}
            for batch in batches(pool, k, seed):
                assert len(batch) == B.MAZE_BATCH
                for x in batch:
                    visit[D.layout_key(x)] += 1
            assert set(visit.values()) == {N_BATCHES * B.MAZE_BATCH // k}
        print(json.dumps({"seed": seed, "support_unique_layouts": len(seen),
                          "support_panel_overlap": len(seen & banned),
                          "support_sha256": digest,
                          "panel_layouts": {sp: {str(s): len(panels[sp][s]) for s in (7, 9, 11)}
                                            for sp in panels}}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "source", "adapt", "gate", "holdout"))
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--init", choices=("pre", "fresh"))
    p.add_argument("--out", type=Path)
    p.add_argument("--source", type=Path)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--plugin", default="claude_fewex_net",
                   help="importable module implementing PROTOCOL.md plug-in interface")
    a = p.parse_args()
    B.N = importlib.import_module(a.plugin)
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "gate":
        gate_job()
    else:
        if a.arm is None or a.seed is None:
            p.error("--arm and --seed required")
        source = a.source or ART / "runs" / f"qual-{a.arm}-s{a.seed}"
        out = a.out or EQ_RUNS / f"{a.arm}-s{a.seed}-{a.init}"
        if a.cmd == "source":
            B.source_job(a.arm, a.seed, out)
        else:
            if a.init is None:
                p.error("--init required for adapt and holdout")
            if a.cmd == "adapt":
                adapt_job(a.arm, a.seed, a.init, source, out)
            else:
                holdout_job(a.arm, a.seed, a.init, out)


if __name__ == "__main__":
    main()
