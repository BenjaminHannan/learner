#!/usr/bin/env python3
"""Bounded, task-aware full-snapshot retention experiment on the 358e dense loop."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import claude_rsn358e_moe as X
import claude_rsn358a2_run as A2

R, E = X.R, X.E
KINDS = ("grids", "sums")
STEPS = {"grids": 2500, "sums": 2500}
BATCH = 64


def fingerprint(item):
    return (item.env, item.size, tuple(tuple(row) for row in item.tokens))


def heldout(held_seed):
    rng = random.Random(held_seed)
    panels = {
        "grids5": [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(200)],
        "sums4": [E.make_sum(rng, 4) for _ in range(200)],
    }
    for name, items in panels.items():
        assert len({fingerprint(it) for it in items}) == 200, name
    return panels


def state_hash(net):
    h = hashlib.sha256()
    for key, value in net.state_dict().items():
        h.update(key.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


@torch.no_grad()
def prediction_signature(net, items, device):
    net.eval()
    t, s, _, env = R.tensors(items, device)
    p, q = net.loop_rounds(t, s, env, R.TEST_ROUNDS)
    return p.cpu().clone(), q.cpu().clone()


def equal_signature(a, b):
    return torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])


def score(net, items, device):
    r = R.evaluate(net, items, device, bs=50)
    return {"right": r["right"], "fixed16": r["fixed_rounds"]["16"],
            "any48": r["right_at_any_round"], "mean_rounds": r["mean_rounds"]}


@torch.no_grad()
def exact_outcomes(net, items, device):
    """Per-item exactness under the original own-stop rule, in panel order."""
    net.eval()
    outcomes = []
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        t, s, _, env = R.tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, R.TEST_ROUNDS)
        for item, p, q in zip(chunk, preds.tolist(), qs.tolist()):
            stop = A2.stop_round(p, q, R.TEST_ROUNDS)
            outcomes.append(bool(E.check(item, R.grid_of(p[stop], item))))
    return outcomes


def replacement_at_same_size(rng, item, pool):
    if item.env == "sums":
        return E.make_sum(rng, item.size)
    if item.env == "grids":
        return E.latin_item(rng, *E.augment_latin(rng, *rng.choice(pool[item.size])))
    raise ValueError(f"unexpected practice skill: {item.env}")


def new_net(device):
    return X.make_net("dense", "small").to(device)


def train_step(net, optimizer, scheduler, items, rr, device):
    net.train()
    t, s, y, env = R.tensors(items, device)
    total = rr.randint(1, R.TRAIN_ROUNDS)
    k = rr.randint(1, min(total, R.GRAD_ROUNDS))
    losses = []
    for lg, q in net.loop_train(t, s, env, total - k, k):
        ce, exact = R.ce_and_exact(lg, s, y)
        losses.append(ce + 0.5 * F.binary_cross_entropy_with_logits(q.float(), exact))
    loss = torch.stack(losses).mean()
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
    optimizer.step()
    scheduler.step()
    return float(loss.detach())


def synchronize(device):
    if device == "mps":
        torch.mps.synchronize()


def benchmark():
    torch.set_num_threads(4)
    rng = random.Random(888)
    items = [E.make_sum(rng, 4) for _ in range(BATCH)]
    results = {}
    for device in ("cpu", "mps"):
        if device == "mps" and not torch.backends.mps.is_available():
            continue
        torch.manual_seed(123)
        net = new_net(device)
        optimizer = torch.optim.AdamW(net.parameters(), lr=X.LR, weight_decay=0.1, betas=(0.9, 0.95))
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
        rr = random.Random(777)
        try:
            for _ in range(3):
                train_step(net, optimizer, scheduler, items, rr, device)
            synchronize(device)
            t0 = time.monotonic()
            for _ in range(8):
                train_step(net, optimizer, scheduler, items, rr, device)
            synchronize(device)
            elapsed = time.monotonic() - t0
            results[device] = {"seconds_per_step": round(elapsed / 8, 4),
                               "steps_per_minute": round(8 * 60 / elapsed, 1)}
        except RuntimeError as exc:
            results[device] = {"error": str(exc)[:500]}
    return results


def save_checkpoint(path, net, kind, step, seed):
    torch.save({"arm": "dense", "size": "small", "kind": kind, "step": step,
                "seed": seed, "state": {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}}, path)


def load_checkpoint(path, device):
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    net = new_net(device)
    net.load_state_dict(ckpt["state"], strict=True)
    net.eval()
    return net


class SnapshotRouter:
    """Select a complete immutable model using the caller's known task identity."""

    def __init__(self, root, device):
        self.root, self.device = Path(root), device
        self._cache = {}

    def model_for(self, kind):
        if kind not in KINDS:
            raise ValueError(f"unknown task identity: {kind}")
        if kind not in self._cache:
            self._cache[kind] = load_checkpoint(self.root / f"snapshot-{kind}.pt", self.device)
            for p in self._cache[kind].parameters():
                p.requires_grad_(False)
        return self._cache[kind]

    def score(self, items):
        if not items or len({item.env for item in items}) != 1:
            raise ValueError("routing requires a nonempty panel with one caller task identity")
        return score(self.model_for(items[0].env), items, self.device)

    def predict(self, items):
        if not items or len({item.env for item in items}) != 1:
            raise ValueError("routing requires a nonempty request with one caller task identity")
        return prediction_signature(self.model_for(items[0].env), items, self.device)


def train_phase(net, kind, rng, rr, pool, held_inputs, device, out):
    steps = STEPS[kind]
    optimizer = torch.optim.AdamW(net.parameters(), lr=X.LR, weight_decay=0.1, betas=(0.9, 0.95))
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda i: min(1, (i + 1) / X.WARM) *
        0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    rejected = 0
    start = time.monotonic()
    log_path = out / "train.jsonl"
    with log_path.open("a", encoding="utf-8") as log:
        for step in range(1, steps + 1):
            items = X.phase_batch(rng, kind, BATCH, pool)
            for i, item in enumerate(items):
                while fingerprint(item) in held_inputs:
                    rejected += 1
                    item = replacement_at_same_size(rng, item, pool)
                items[i] = item
            loss = train_step(net, optimizer, scheduler, items, rr, device)
            if step % 250 == 0 or step == steps:
                synchronize(device)
                rec = {"phase": kind, "step": step, "loss": round(loss, 5),
                       "elapsed_seconds": round(time.monotonic() - start, 1), "heldout_rejections": rejected}
                line = json.dumps(rec)
                log.write(line + "\n")
                log.flush()
                print(line, flush=True)
    return {"steps": steps, "batch": BATCH, "elapsed_seconds": round(time.monotonic() - start, 1),
            "heldout_rejections": rejected}


def committed_passmarks(repo, sha):
    path = "artifacts/codex-retention-20260927/PASSMARKS.md"
    saved = subprocess.check_output(["git", "-C", str(repo), "show", f"{sha}:{path}"])
    current = (repo / path).read_bytes()
    if saved != current:
        raise ValueError("PASSMARKS in workspace differs from supplied committed revision")
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def run(args):
    repo = Path(__file__).resolve().parents[3]
    if not args.benchmark_only:
        if args.seed not in (29, 30):
            raise ValueError("R1 permits only preregistered training seeds 29 and 30")
        if not args.passmarks_sha:
            raise ValueError("registered training requires --passmarks-sha")
        head = committed_passmarks(repo, args.passmarks_sha)
    out = Path(args.out)
    if out.exists() and not args.benchmark_only:
        raise FileExistsError(f"refusing to overwrite a registered run: {out}")
    out.mkdir(parents=True, exist_ok=args.benchmark_only)
    started_utc = subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()
    wall_start = time.monotonic()
    if not args.benchmark_only:
        (out / "RUN-NOTE.md").write_text(
            f"# R1 seed {args.seed}\n\nUTC start (`date -u`): {started_utc}\n"
            f"Machine: {platform.node()}\nPID: {os.getpid()}\n"
            f"Software HEAD: `{head}`\nPASSMARKS commit: `{args.passmarks_sha}`\n"
            f"Command: `python -B artifacts/codex-retention-20260927/reasoner/codex_retention_reasoner.py"
            f" --out {out} --seed {args.seed} --passmarks-sha {args.passmarks_sha}`\n",
            encoding="utf-8")
    bench = benchmark()
    (out / "benchmark.json").write_text(json.dumps(bench, indent=2) + "\n")
    if args.benchmark_only:
        print(json.dumps({"benchmark": bench}), flush=True)
        return
    feasible = {d: x["seconds_per_step"] for d, x in bench.items() if "seconds_per_step" in x}
    device = min(feasible, key=feasible.get)
    print(json.dumps({"benchmark": bench, "chosen_device": device}), flush=True)
    torch.manual_seed(args.seed)
    rng, rr = random.Random(5800 + args.seed), random.Random(5900 + args.seed)
    held_seed = 92000 + args.seed
    panels = heldout(held_seed)
    held_inputs = {fingerprint(it) for items in panels.values() for it in items}
    pool = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = new_net(device)
    params = sum(p.numel() for p in net.parameters())
    result = {"protocol": "../PASSMARKS.md",
              "passmarks_commit": args.passmarks_sha, "software_head": head,
              "start_utc": started_utc, "machine": platform.node(), "pid": os.getpid(),
              "seed": args.seed, "held_seed": held_seed,
              "device": device, "benchmark": bench, "parameters_per_snapshot": params,
              "torch": torch.__version__, "phases": {}, "routing": "caller Item.env -> frozen full snapshot"}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    for kind in KINDS:
        if kind != "grids":
            net = copy.deepcopy(net)  # trainable branch from the previous immutable snapshot
            assert all(p.requires_grad for p in net.parameters())
        phase = train_phase(net, kind, rng, rr, pool, held_inputs, device, out)
        path = out / f"snapshot-{kind}.pt"
        save_checkpoint(path, net, kind, STEPS[kind], args.seed)
        frozen = load_checkpoint(path, device)
        assert all(torch.equal(a.cpu(), b.cpu()) for a, b in zip(net.state_dict().values(), frozen.state_dict().values()))
        phase["snapshot"] = str(path)
        phase["checkpoint_bytes"] = path.stat().st_size
        phase["sha256_state"] = state_hash(frozen)
        phase["snapshot_roundtrip_all_rounds_identical"] = equal_signature(
            prediction_signature(net, panels["grids5"][:16], device),
            prediction_signature(frozen, panels["grids5"][:16], device))
        assert phase["snapshot_roundtrip_all_rounds_identical"]
        phase["score_current"] = {name: score(net, items, device) for name, items in panels.items()}
        phase["score_routed"] = {}
        router = SnapshotRouter(out, device)
        for previous in KINDS[:KINDS.index(kind) + 1]:
            name = {"grids": "grids5", "sums": "sums4"}[previous]
            phase["score_routed"][name] = router.score(panels[name])
        if kind == "grids":
            grid_state = {k: v.detach().cpu().clone() for k, v in frozen.state_dict().items()}
            grid_sig = prediction_signature(frozen, panels["grids5"][:16], device)
            grid_outcomes = exact_outcomes(frozen, panels["grids5"], device)
            assert sum(grid_outcomes) == phase["score_current"]["grids5"]["right"]
        else:
            old = load_checkpoint(out / "snapshot-grids.pt", device)
            old_outcomes = exact_outcomes(old, panels["grids5"], device)
            phase["grid_isolation"] = {
                "bit_identical_weights": all(torch.equal(v, old.state_dict()[k].cpu()) for k, v in grid_state.items()),
                "bit_identical_predictions_and_stop_probabilities": equal_signature(
                    grid_sig, prediction_signature(old, panels["grids5"][:16], device)),
                "snapshot_hash_unchanged": state_hash(old) == result["phases"]["grids"]["sha256_state"],
                "previously_correct_items_lost": sum(a and not b for a, b in zip(grid_outcomes, old_outcomes)),
                "previously_incorrect_items_gained": sum(not a and b for a, b in zip(grid_outcomes, old_outcomes)),
                "per_item_exactness_identical": grid_outcomes == old_outcomes,
            }
            assert all(phase["grid_isolation"][k] for k in (
                "bit_identical_weights", "bit_identical_predictions_and_stop_probabilities",
                "snapshot_hash_unchanged", "per_item_exactness_identical"))
        result["phases"][kind] = phase
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"completed": kind, "scores": phase["score_current"],
                          "routed": phase["score_routed"]}), flush=True)
    a = result["phases"]["grids"]["score_current"]["grids5"]["right"]
    b = result["phases"]["sums"]["score_current"]["sums4"]["right"]
    retained = result["phases"]["sums"]["score_routed"]["grids5"]["right"]
    result["criteria"] = {"A_mastery_190": a >= 190, "B_mastery_190": b >= 190,
                          "retained_A_190": retained >= 190,
                          "isolation": result["phases"]["sums"]["grid_isolation"]["per_item_exactness_identical"] and
                          result["phases"]["sums"]["grid_isolation"]["bit_identical_weights"] and
                          result["phases"]["sums"]["grid_isolation"]["bit_identical_predictions_and_stop_probabilities"]}
    requests = [panels["grids5"][:16], panels["sums4"][:16], panels["grids5"][:16]]
    first_router = SnapshotRouter(out, device)
    first_outputs = [first_router.predict(items) for items in requests]
    del first_router
    restarted_router = SnapshotRouter(out, device)
    second_outputs = [restarted_router.predict(items) for items in requests]
    result["restart_routing"] = {
        "alternating_task_ids": [items[0].env for items in requests],
        "exact_outputs_and_stop_probabilities": all(equal_signature(a, b) for a, b in zip(first_outputs, second_outputs)),
        "first_and_third_grid_requests_identical": equal_signature(second_outputs[0], second_outputs[2]),
        "grid_score_unchanged": result["phases"]["grids"]["score_routed"]["grids5"] ==
                                result["phases"]["sums"]["score_routed"]["grids5"],
    }
    try:
        restarted_router.model_for("unknown")
    except ValueError:
        result["restart_routing"]["unknown_task_rejected"] = True
    else:
        result["restart_routing"]["unknown_task_rejected"] = False
    assert all(v for k, v in result["restart_routing"].items() if k != "alternating_task_ids")
    synchronize(device)
    result["total_checkpoint_bytes"] = sum(p["checkpoint_bytes"] for p in result["phases"].values())
    result["total_parameters_across_two_snapshots"] = 2 * params
    result["wall_seconds"] = round(time.monotonic() - wall_start, 1)
    result["end_utc"] = subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"criteria": result["criteria"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--seed", type=int, choices=(29, 30), default=29)
    parser.add_argument("--passmarks-sha")
    run(parser.parse_args())
