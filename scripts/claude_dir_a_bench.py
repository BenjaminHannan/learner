#!/usr/bin/env python3
"""Few-example ruler on the three held-out kinds, for the breadth-practised nets (Director helper A, 2026-09-28).

NEEDS TORCH. NOT RUN when written (the authoring box has no torch); only `py_compile` and the pure-python parts
(claude_dir_a_kinds.py, claude_dir_a_marks.py) were run there.

Runs the SAME ruler as the maze run (artifacts/claude-fewex-20260927, ADDENDUM-4) and as H1 (graph, rank) on nets
whose source practice was the ten-kind mixture (claude_dir_a_practice.py). Everything except the source net is
identical to the comparison runs, on purpose: same panels, same 16,384-item pools (per kind and seed), same nested
prefixes and batch order, 512 batches x 32 x 4 updates = 2,048 updates per rung, same learning rates rule, same
fixed-depth rule, fp32 CPU. The sealed ruler code (claude_fewex_bench, claude_fewex_eq_bench, claude_dir_h1_kinds,
claude_dir_h1_bench) is imported, never edited. Only "pre" (practised) starts are run here: the fresh-net arms do
not depend on the practice and are taken from the existing runs.

  python -B scripts/claude_dir_a_bench.py selftest
  python -B scripts/claude_dir_a_bench.py check-source --source-root <folder with qual-*>
  python -B scripts/claude_dir_a_bench.py adapt   --kind maze|graph|rank --arm loop --seed 0 --source-root <root>
  python -B scripts/claude_dir_a_marks.py gate    --kind maze|graph|rank
  python -B scripts/claude_dir_a_bench.py holdout --kind maze|graph|rank --arm loop --seed 0
  python -B scripts/claude_dir_a_marks.py score   --kind maze|graph|rank
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
import claude_dir_a_kinds as A
import claude_dir_h1_bench as HB          # patches B.exact for graph and rank at import
import claude_dir_h1_kinds as K
import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_eq_bench as Q

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-dir-a-breadth-20260928"
RUNS = ART / "runs"
N_UPDATES = Q.N_UPDATES
RUNGS = K.RUNGS
KINDS = ("maze", "graph", "rank")
SIZES = {"maze": (7, 9, 11), "graph": K.KINDS["graph"]["sizes"], "rank": K.KINDS["rank"]["sizes"]}
GRADED = {"maze": 9, "graph": K.KINDS["graph"]["graded"], "rank": K.KINDS["rank"]["graded"]}
assert Q.RUNGS == K.RUNGS and Q.N_BATCHES == K.N_BATCHES and B.MAZE_BATCH == K.MAZE_BATCH

_prev_exact = B.exact


def _exact(item, pred):
    return A.check(item, pred) if item.env in A.NEW_KINDS else _prev_exact(item, pred)


B.exact = _exact


# ---- one small interface over the three held-out kinds; each function reuses the sealed code of that kind ----
def kind_panels(kind):
    if kind == "maze":
        pan, banned = D.panels()
        return pan, banned
    return K.panels(kind)


def kind_pool(kind, seed, banned):
    if kind == "maze":
        return Q.make_pool(seed, banned)
    return K.make_pool(kind, seed, banned)


def kind_batches(kind, pool, k, seed):
    return Q.batches(pool, k, seed) if kind == "maze" else K.batches(kind, pool, k, seed)


def kind_scores(net, split_panels, depth, kind):
    return {str(n): B.score(net, split_panels[n], depth) for n in SIZES[kind]}


def adapt_gradient_check(net, items):
    """V2k: one fp32 CPU step of the ADAPTATION loss on 32 items of the held-out kind; every 2-D weight matrix must
    get a nonzero gradient, except the loop's stop head (no stop term in the adaptation loss, as in the ruler)."""
    net = copy.deepcopy(net)
    net.train()
    t, s, y = B.N.tensors(items)
    net.zero_grad(set_to_none=True)
    if net.arm == "plain":
        loss = B.N.ce_and_exact(net.plain_forward(t, s), s, y)[0]
    else:
        e, (dr, dc) = net.embed(t, s)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(3):
                h = net.step(h, e.detach(), dr, dc)
        h = h.detach()
        ces = []
        for _ in range(2):
            h = net.step(h, e, dr, dc)
            ces.append(B.N.ce_and_exact(net.read(h)[0], s, y)[0])
        loss = torch.stack(ces).mean()
    loss.backward()
    missing = [name for name, p in net.named_parameters()
               if p.ndim == 2 and (p.grad is None or not bool(torch.any(p.grad != 0)))]
    return {"matrix_count": sum(p.ndim == 2 for p in net.parameters()), "missing": missing,
            "nonzero_all_except_halt": not (set(missing) - {"halt.weight"}), "loss": float(loss)}


def run_dir(kind, arm, seed):
    return RUNS / kind / f"{arm}-s{seed}-pre"


def identity_source(source_dir, arm, seed):
    src = json.loads((source_dir / "source.json").read_text())
    if (src["arm"], src["seed"], src.get("recipe")) != (arm, seed, "breadth10"):
        raise ValueError("source identity mismatch (arm, seed or recipe)")
    if not src["gradient_check"]["nonzero_all"]:
        raise ValueError("source failed V2")
    return src


def adapt_job(kind, arm, seed, source_dir, out):
    if (out / "adapt.json").exists():
        raise FileExistsError("dev run already complete")
    start = time.monotonic()
    src = identity_source(source_dir, arm, seed)
    depth = src["fixed_depth"]
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    pan, banned = kind_panels(kind)
    pool, keys, digest = kind_pool(kind, seed, banned)
    base = B.load_model(source_dir / "source.pt", arm)
    out.mkdir(parents=True, exist_ok=True)
    old = D.old_panels()
    res = {"kind": kind, "arm": arm, "seed": seed, "init": "pre", "recipe": "breadth10", "source": str(source_dir),
           "fixed_depth": depth, "lr": lr, "weights": base.weight_count(),
           "persistent_coefficients": base.weight_count(),
           "support_unique_keys": len(keys), "support_panel_overlap": len(keys & banned),
           "support_sha256": digest, "rung_batches": K.N_BATCHES, "batch_size": B.MAZE_BATCH,
           "updates_per_batch": B.UPDATES, "optimizer_updates_per_rung": N_UPDATES,
           "visits_per_item": {str(k): K.N_BATCHES * B.MAZE_BATCH // k for k in RUNGS},
           "panel_items": {sp: {str(n): len(v) for n, v in pan[sp].items()} for sp in pan},
           "graded_size": GRADED[kind],
           "gradient_check_adapt": adapt_gradient_check(base, pool[:32]),
           "rungs": {}, "old": {}, "rung_seconds": {}}
    res["rungs"]["0"] = kind_scores(base, pan["dev"], depth, kind)
    res["old"]["before"] = Q.old_scores(base, old, depth)
    B.save_stage(base, out, "k0")
    for k in RUNGS:
        t0 = time.monotonic()
        learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(base), lr)
        for batch in kind_batches(kind, pool, k, seed):
            learner.maze_batch(batch)
        if learner.steps != N_UPDATES:
            raise ValueError(f"k={k}: expected {N_UPDATES} updates, got {learner.steps}")
        net = learner.net
        res["rungs"][str(k)] = kind_scores(net, pan["dev"], depth, kind)
        B.save_stage(net, out, f"k{k}")
        if k in (64, 16384):
            res["old"][f"after_{k}"] = Q.old_scores(net, old, depth)
        res["rung_seconds"][str(k)] = time.monotonic() - t0
        B.dump(out / "partial.json", res)
        print(json.dumps({"phase": "rung", "kind": kind, "arm": arm, "seed": seed, "k": k,
                          "right_graded": res["rungs"][str(k)][str(GRADED[kind])]["right"],
                          "seconds": round(time.monotonic() - start)}), flush=True)
    res["training_seconds"] = time.monotonic() - start
    B.dump(out / "adapt.json", res)
    print(json.dumps({"phase": "adapt_done", "kind": kind, "arm": arm, "seed": seed,
                      "seconds": round(res["training_seconds"])}), flush=True)


def holdout_job(kind, arm, seed, out):
    gate = json.loads((ART / f"DEV-GATE-{kind}.json").read_text())
    if gate["verdict"] != "PASS":
        raise ValueError("dev gate did not pass; holdout must stay sealed")
    if (out / "holdout.json").exists():
        raise FileExistsError("holdout already evaluated")
    with (out / "holdout.started").open("x"):
        pass                                      # never silently re-open this arm's holdout after a partial run
    dev = json.loads((out / "adapt.json").read_text())
    if (dev["kind"], dev["arm"], dev["seed"]) != (kind, arm, seed):
        raise ValueError("dev run identity mismatch")
    pan, _ = kind_panels(kind)
    scores = {}
    for name in ("0",) + tuple(map(str, RUNGS)):
        net = B.load_model(out / f"k{name}.pt", arm)
        scores[name] = kind_scores(net, pan["holdout"], dev["fixed_depth"], kind)
    B.dump(out / "holdout.json", {"kind": kind, "arm": arm, "seed": seed, "init": "pre", "scores": scores,
                                  "support_sha256": dev["support_sha256"]})


def check_source(root):
    """V1a and V2 on the four breadth sources (checkpoints must be on this machine). Recomputes the mastery guard
    on the fresh guard panel and requires it to match source.json within 2 per kind (same weights, same panel)."""
    res, v1a_all, v2_all, loop_ok, plain_ok = {}, True, True, True, True
    for arm in ("loop", "plain"):
        for seed in (0, 1):
            d = root / f"qual-{arm}-s{seed}"
            src = identity_source(d, arm, seed)
            pt = d / "source.pt"
            net = B.load_model(pt, arm)
            from claude_dir_a_practice import all_kind_scores           # same scorer the source job used
            now = {k: v["right"] for k, v in all_kind_scores(net, A.GUARD_SEED, src["fixed_depth"]).items()}
            was = {k: v["right"] for k, v in src["practice"].items()}
            match = all(abs(now[k] - was[k]) <= 2 for k in A.KINDS)
            mastered = sum(1 for k in A.KINDS if now[k] >= 180)
            ok1 = match and mastered >= 8
            ok2 = bool(src["gradient_check"]["nonzero_all"])
            v1a_all &= ok1
            v2_all &= ok2
            loop_ok &= ok1 if arm == "loop" else True
            plain_ok &= ok1 if arm == "plain" else True
            res[f"{arm}-s{seed}"] = {"sha256": hashlib.sha256(pt.read_bytes()).hexdigest(),
                                     "recomputed_right_of_200": now, "recorded_right_of_200": was,
                                     "recompute_matches": match, "mastered_of_10": mastered,
                                     "V1a_ok": ok1, "V2_ok": ok2, "weights": net.weight_count()}
    out = {"V1a_loop": loop_ok, "V1a_plain": plain_ok, "V2": v2_all, "sources": res}
    path = ART / "SOURCE-CHECK.json"
    if path.exists():
        raise FileExistsError("source check already written")
    B.dump(path, out)
    print(json.dumps({"V1a_loop": loop_ok, "V1a_plain": plain_ok, "V2": v2_all}))


def timing(kind, arm):
    """Timing only, nothing kept: 16 batches (64 updates) at k=64 from a fresh net."""
    pan, banned = kind_panels(kind)
    pool, _, _ = kind_pool(kind, 0, banned)
    torch.manual_seed(1)
    learner = getattr(B.N, "Learner", B.Learner)(B.N.Net(arm), 1e-3)
    t0 = time.monotonic()
    for i, batch in enumerate(kind_batches(kind, pool, 64, 0)):
        learner.maze_batch(batch)
        if i == 15:
            break
    per = (time.monotonic() - t0) / 16
    print(json.dumps({"kind": kind, "arm": arm, "seconds_per_batch": round(per, 3),
                      "projected_minutes_per_job_training_only": round(per * K.N_BATCHES * len(RUNGS) / 60, 1)}))


def selftest():
    for kind in KINDS:
        pan, banned = kind_panels(kind)
        for arm in ("loop", "plain"):
            torch.manual_seed(0)
            net = B.N.Net(arm)
            n = GRADED[kind]
            pool_items = pan["dev"][n][:B.MAZE_BATCH]
            gc = adapt_gradient_check(net, pool_items)
            assert gc["nonzero_all_except_halt"], gc
            learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), 1e-3)
            learner.maze_batch(pool_items)
            assert learner.steps == B.UPDATES
            sc = kind_scores(learner.net, {s: v[:8] for s, v in pan["dev"].items()}, 16, kind)
            assert all(sc[str(s)]["n"] == 8 for s in SIZES[kind])
            print(json.dumps({"selftest": "ok", "kind": kind, "arm": arm, "matrices": gc["matrix_count"],
                              "loss": round(gc["loss"], 3)}), flush=True)
    for arm in ("loop", "plain"):
        print(json.dumps({"weights": {arm: B.N.Net(arm).weight_count()}}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "check-source", "timing", "adapt", "holdout"))
    p.add_argument("--kind", choices=KINDS)
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--source-root", type=Path, default=RUNS / "sources",
                   help="folder holding qual-<arm>-s<seed>/source.pt and source.json (checkpoints are not in git)")
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--plugin", default="claude_fewex_net")
    a = p.parse_args()
    B.N = importlib.import_module(a.plugin)
    Q.B.N = B.N
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "check-source":
        check_source(a.source_root)
    elif a.cmd == "timing":
        timing(a.kind, a.arm)
    else:
        if None in (a.kind, a.arm, a.seed):
            p.error("--kind --arm --seed required")
        out = run_dir(a.kind, a.arm, a.seed)
        if a.cmd == "adapt":
            adapt_job(a.kind, a.arm, a.seed, a.source_root / f"qual-{a.arm}-s{a.seed}", out)
        else:
            holdout_job(a.kind, a.arm, a.seed, out)


if __name__ == "__main__":
    main()
