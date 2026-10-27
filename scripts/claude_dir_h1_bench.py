#!/usr/bin/env python3
"""Equal-practice few-example ruler on new held-out kinds (Director helper H1, 2026-09-28).

NEEDS TORCH. NOT RUN when written (the authoring box has no torch); only `py_compile` and the pure-python
parts (claude_dir_h1_kinds.py, claude_dir_h1_marks.py) were run there.

Reuses the sealed ruler code unchanged: claude_fewex_bench (model loading, exact scorer, Learner, old-kind
panels), claude_fewex_eq_bench (source identity check, old-kind scoring), claude_fewex_net (plug-in nets).
The ONLY changes from the maze ruler: the puzzle kind (claude_dir_h1_kinds), the checker (patched into the
scorer for the new kinds), the panel sizes (graph 12/14/16, rank 7/9/10), and no sleep branches.
Same eight rungs k = 1 .. 16,384, same 512 batches x 32 x 4 updates = 2,048 updates per rung, same lrs,
same fixed depth per qualified source, fp32 CPU, no autocast.

  python -B scripts/claude_dir_h1_bench.py selftest
  python -B scripts/claude_dir_h1_bench.py check-source --source-root <folder with qual-*>
  python -B scripts/claude_dir_h1_bench.py timing  --kind graph --arm loop
  python -B scripts/claude_dir_h1_bench.py adapt   --kind graph --arm loop --seed 0 --init pre
  python -B scripts/claude_dir_h1_marks.py gate    --kind graph
  python -B scripts/claude_dir_h1_bench.py holdout --kind graph --arm loop --seed 0 --init pre
  python -B scripts/claude_dir_h1_marks.py score   --kind graph
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
import claude_dir_h1_kinds as K
import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_eq_bench as Q

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-dir-h1-heldout-20260928"
RUNS = ART / "runs"
N_UPDATES = Q.N_UPDATES
assert Q.RUNGS == K.RUNGS and Q.N_BATCHES == K.N_BATCHES and B.MAZE_BATCH == K.MAZE_BATCH

_old_exact = B.exact


def _exact(item, pred):
    """The sealed scorer calls B.exact; route the new kinds to their own checkers, leave the rest alone."""
    return K.check(item, pred) if item.env in K.KINDS else _old_exact(item, pred)


B.exact = _exact


def kind_scores(net, split_panels, depth, kind):
    return {str(n): B.score(net, split_panels[n], depth) for n in K.KINDS[kind]["sizes"]}


def adapt_gradient_check(net, kind, seed):
    """V2k: one fp32 CPU step of the ADAPTATION loss on a batch of the new kind. Every two-dimensional weight
    matrix must get a nonzero gradient, except the loop's stop head (the maze/graph adaptation loss has no
    stop term, exactly as in the ruler)."""
    net = copy.deepcopy(net)
    net.train()
    rng = random.Random(9432700 + seed)
    items = [K.make_item(kind, rng, K.KINDS[kind]["graded"]) for _ in range(32)]
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


def run_dir(kind, arm, seed, init):
    return RUNS / kind / f"{arm}-s{seed}-{init}"


def adapt_job(kind, arm, seed, init, source_dir, out):
    if (out / "adapt.json").exists():
        raise FileExistsError("dev run already complete")
    start = time.monotonic()
    src = Q.identity_source(source_dir, arm, seed)
    depth = src["fixed_depth"]
    lr = src["plain_lr_sweep"]["chosen"] if arm == "plain" else 1e-3
    pan, banned = K.panels(kind)
    pool, keys, digest = K.make_pool(kind, seed, banned)
    if init == "pre":
        base = B.load_model(source_dir / "source.pt", arm)
    else:
        torch.manual_seed(900000 + seed)          # same fresh-init seed rule as the maze ruler
        base = B.N.Net(arm)
    out.mkdir(parents=True, exist_ok=True)
    old = D.old_panels()
    res = {"kind": kind, "arm": arm, "seed": seed, "init": init, "source": str(source_dir),
           "fixed_depth": depth, "lr": lr, "weights": base.weight_count(),
           "persistent_coefficients": base.weight_count(),
           "support_unique_keys": len(keys), "support_panel_overlap": len(keys & banned),
           "support_sha256": digest, "rung_batches": K.N_BATCHES, "batch_size": B.MAZE_BATCH,
           "updates_per_batch": B.UPDATES, "optimizer_updates_per_rung": N_UPDATES,
           "visits_per_item": {str(k): K.N_BATCHES * B.MAZE_BATCH // k for k in K.RUNGS},
           "panel_items": {sp: {str(n): len(v) for n, v in pan[sp].items()} for sp in pan},
           "graded_size": K.KINDS[kind]["graded"],
           "gradient_check_adapt": adapt_gradient_check(base, kind, seed),
           "rungs": {}, "old": {}, "rung_seconds": {}}
    res["rungs"]["0"] = kind_scores(base, pan["dev"], depth, kind)
    res["old"]["before"] = Q.old_scores(base, old, depth)
    B.save_stage(base, out, "k0")
    for k in K.RUNGS:
        t0 = time.monotonic()
        learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(base), lr)
        for batch in K.batches(kind, pool, k, seed):
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
        print(json.dumps({"phase": "rung", "kind": kind, "arm": arm, "seed": seed, "init": init, "k": k,
                          "right_graded": res["rungs"][str(k)][str(K.KINDS[kind]["graded"])]["right"],
                          "seconds": round(time.monotonic() - start)}), flush=True)
    res["training_seconds"] = time.monotonic() - start
    B.dump(out / "adapt.json", res)
    print(json.dumps({"phase": "adapt_done", "kind": kind, "arm": arm, "seed": seed, "init": init,
                      "seconds": round(res["training_seconds"])}), flush=True)


def holdout_job(kind, arm, seed, init, out):
    gate = json.loads((ART / f"DEV-GATE-{kind}.json").read_text())
    if gate["verdict"] != "PASS":
        raise ValueError("dev gate did not pass; holdout must stay sealed")
    if (out / "holdout.json").exists():
        raise FileExistsError("holdout already evaluated")
    with (out / "holdout.started").open("x"):
        pass                                      # never silently re-open this arm's holdout after a partial run
    dev = json.loads((out / "adapt.json").read_text())
    if (dev["kind"], dev["arm"], dev["seed"], dev["init"]) != (kind, arm, seed, init):
        raise ValueError("dev run identity mismatch")
    pan, _ = K.panels(kind)
    scores = {}
    for name in ("0",) + tuple(map(str, K.RUNGS)):
        net = B.load_model(out / f"k{name}.pt", arm)
        scores[name] = kind_scores(net, pan["holdout"], dev["fixed_depth"], kind)
    B.dump(out / "holdout.json", {"kind": kind, "arm": arm, "seed": seed, "init": init, "scores": scores,
                                  "support_sha256": dev["support_sha256"]})


def check_source(root):
    """V1 and V2 on the four qualified source nets (their checkpoints must be on this machine)."""
    res, v1, v2 = {}, True, True
    old = D.old_panels(D.SOURCE_SEED + 300)       # the untouched guard seed of ADDENDUM-3
    for arm in ("loop", "plain"):
        for seed in (0, 1):
            d = root / f"qual-{arm}-s{seed}"
            src = json.loads((d / "source.json").read_text())
            pt = d / "source.pt"
            sha = hashlib.sha256(pt.read_bytes()).hexdigest()
            net = B.load_model(pt, arm)
            now = {k: B.score(net, v, src["fixed_depth"])["right"] for k, v in old.items()}
            was = {"sums4": src["old"]["sums4"]["right"], "grids5": src["old"]["grids5"]["right"]}
            ok1 = all(now[k] >= 190 and abs(now[k] - was[k]) <= 2 for k in was)
            ok2 = bool(src["gradient_check"]["nonzero_all"])
            v1 &= ok1
            v2 &= ok2
            res[f"{arm}-s{seed}"] = {"sha256": sha, "recomputed_right_of_200": now,
                                     "recorded_right_of_200": was, "V1_ok": ok1, "V2_ok": ok2,
                                     "weights": net.weight_count()}
    out = {"V1": v1, "V2": v2, "sources": res}
    path = ART / "SOURCE-CHECK.json"
    if path.exists():
        raise FileExistsError("source check already written")
    B.dump(path, out)
    print(json.dumps({"V1": v1, "V2": v2}))


def timing(kind, arm):
    """Timing only, nothing kept: 16 batches (64 updates) at k=64 from a fresh net."""
    pan, banned = K.panels(kind)
    rng, seen = random.Random(5), set()
    pool = [K.unique_item(kind, rng, K.KINDS[kind]["graded"], banned, seen) for _ in range(64)]
    torch.manual_seed(1)
    learner = getattr(B.N, "Learner", B.Learner)(B.N.Net(arm), 1e-3)
    t0 = time.monotonic()
    for i, batch in enumerate(K.batches(kind, pool, 64, 0)):
        learner.maze_batch(batch)
        if i == 15:
            break
    per = (time.monotonic() - t0) / 16
    print(json.dumps({"kind": kind, "arm": arm, "seconds_per_batch": round(per, 3),
                      "projected_minutes_per_job_training_only": round(per * K.N_BATCHES * len(K.RUNGS) / 60, 1)}))


def selftest():
    for kind in K.KINDS:
        pan, banned = K.panels(kind)
        for arm in ("loop", "plain"):
            torch.manual_seed(0)
            net = B.N.Net(arm)
            gc = adapt_gradient_check(net, kind, 0)
            assert gc["nonzero_all_except_halt"], gc
            n = K.KINDS[kind]["graded"]
            learner = getattr(B.N, "Learner", B.Learner)(copy.deepcopy(net), 1e-3)
            learner.maze_batch(pan["dev"][n][:B.MAZE_BATCH])
            assert learner.steps == B.UPDATES
            sc = kind_scores(learner.net, {s: v[:8] for s, v in pan["dev"].items()}, 16, kind)
            assert all(sc[str(s)]["n"] == 8 for s in K.KINDS[kind]["sizes"])
            print(json.dumps({"selftest": "ok", "kind": kind, "arm": arm, "matrices": gc["matrix_count"],
                              "loss": round(gc["loss"], 3)}), flush=True)
    for arm in ("loop", "plain"):
        print(json.dumps({"weights": {arm: B.N.Net(arm).weight_count()}}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "check-source", "timing", "adapt", "holdout"))
    p.add_argument("--kind", choices=tuple(K.KINDS))
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--seed", type=int, choices=(0, 1))
    p.add_argument("--init", choices=("pre", "fresh"))
    p.add_argument("--source-root", type=Path, default=B.ART / "runs",
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
        if None in (a.kind, a.arm, a.seed, a.init):
            p.error("--kind --arm --seed --init required")
        out = run_dir(a.kind, a.arm, a.seed, a.init)
        if a.cmd == "adapt":
            source = a.source_root / f"qual-{a.arm}-s{a.seed}"
            adapt_job(a.kind, a.arm, a.seed, a.init, source, out)
        else:
            holdout_job(a.kind, a.arm, a.seed, a.init, out)


if __name__ == "__main__":
    main()
