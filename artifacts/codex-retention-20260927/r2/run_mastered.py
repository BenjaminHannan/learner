#!/usr/bin/env python3
"""R2: fixed-budget mastered snapshot comparison; refuses uncommitted PASSMARKS."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[3]
R1_PATH = ARTIFACT / "reasoner" / "codex_retention_reasoner.py"
PASSMARKS = "artifacts/codex-retention-20260927/r2/PASSMARKS.md"
STEPS = {"grids": 6000, "sums": 2500}
BATCH = 64
SEEDS = (31, 32)

spec = importlib.util.spec_from_file_location("retention_r1_helpers", R1_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot import R1 helpers: {R1_PATH}")
R1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R1)
torch, X, E = R1.torch, R1.X, R1.E


def utc() -> str:
    return subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()


def gate(seed: int, out: Path, sha: str) -> tuple[Path, str]:
    """No output, benchmark or training occurs before this committed-byte gate."""
    if seed not in SEEDS or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
        raise ValueError("R2 requires seed 31/32 and a full commit SHA")
    expected = (ARTIFACT / "r2" / f"seed{seed}").resolve()
    if out.resolve() != expected:
        raise ValueError(f"R2 output must be exactly {expected}")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite R2 seed output: {out}")
    kind = subprocess.check_output(["git", "-C", str(REPO), "cat-file", "-t", sha], text=True).strip()
    if kind != "commit":
        raise ValueError("--passmarks-sha must name a commit")
    committed = subprocess.check_output(["git", "-C", str(REPO), "show", f"{sha}:{PASSMARKS}"])
    if committed != (REPO / PASSMARKS).read_bytes():
        raise ValueError("R2 PASSMARKS bytes differ from the supplied committed revision")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    return expected, head


def train_phase(net, kind: str, rng, rr, pool, held_inputs, device: str, out: Path) -> dict:
    """R1's unchanged update/data rule, with R2's explicit per-phase step count."""
    steps = STEPS[kind]
    opt = torch.optim.AdamW(net.parameters(), lr=X.LR, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / X.WARM) *
        0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    rejected = 0
    start = time.monotonic()
    with (out / "train.jsonl").open("a", encoding="utf-8") as log:
        for step in range(1, steps + 1):
            items = X.phase_batch(rng, kind, BATCH, pool)
            for i, item in enumerate(items):
                while R1.fingerprint(item) in held_inputs:
                    rejected += 1
                    item = R1.replacement_at_same_size(rng, item, pool)
                items[i] = item
            loss = R1.train_step(net, opt, sched, items, rr, device)
            if step % 250 == 0 or step == steps:
                R1.synchronize(device)
                rec = {"phase": kind, "step": step, "loss": round(loss, 5),
                       "elapsed_seconds": round(time.monotonic() - start, 1),
                       "heldout_rejections": rejected}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(json.dumps(rec), flush=True)
    return {"steps": steps, "batch": BATCH,
            "elapsed_seconds": round(time.monotonic() - start, 1),
            "heldout_rejections": rejected}


def run(args) -> None:
    out, head = gate(args.seed, args.out, args.passmarks_sha)
    out.mkdir(parents=True, exist_ok=False)
    start_utc, wall_start = utc(), time.monotonic()
    (out / "RUN-NOTE.md").write_text(
        f"# R2 seed {args.seed}\n\nUTC start: {start_utc}\nMachine: {platform.node()}\n"
        f"PID: {os.getpid()}\nSoftware HEAD: `{head}`\n"
        f"PASSMARKS commit: `{args.passmarks_sha}`\n"
        f"Runner SHA256: `{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}`\n",
        encoding="utf-8")

    bench = R1.benchmark()  # after registration gate; resets seed before the real trajectory
    (out / "benchmark.json").write_text(json.dumps(bench, indent=2) + "\n", encoding="utf-8")
    feasible = {d: v["seconds_per_step"] for d, v in bench.items() if "seconds_per_step" in v}
    if not feasible:
        raise RuntimeError("no feasible local device")
    device = min(feasible, key=feasible.get)
    torch.manual_seed(args.seed)
    rng, rr = random.Random(5800 + args.seed), random.Random(5900 + args.seed)
    held_seed = 92000 + args.seed
    panels = R1.heldout(held_seed)
    held_inputs = {R1.fingerprint(it) for items in panels.values() for it in items}
    pool = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = R1.new_net(device)
    params = sum(p.numel() for p in net.parameters())
    result = {"protocol": PASSMARKS, "passmarks_commit": args.passmarks_sha,
              "software_head": head, "seed": args.seed, "held_seed": held_seed,
              "start_utc": start_utc, "machine": platform.node(), "pid": os.getpid(),
              "device": device, "benchmark": bench, "torch": torch.__version__,
              "steps": dict(STEPS), "batch": BATCH, "parameters_per_snapshot": params,
              "routing": "caller Item.env -> immutable complete snapshot", "phases": {}}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    # Phase A: publish a complete frozen snapshot, then clone that exact state for B.
    a = train_phase(net, "grids", rng, rr, pool, held_inputs, device, out)
    a_path = out / "snapshot-grids.pt"
    R1.save_checkpoint(a_path, net, "grids", STEPS["grids"], args.seed)
    old = R1.load_checkpoint(a_path, device)
    a["checkpoint_weights_match_trained_A"] = all(
        torch.equal(v, old.state_dict()[k]) for k, v in net.state_dict().items())
    for p in old.parameters():
        p.requires_grad_(False)
    a["snapshot"] = str(a_path)
    a["checkpoint_bytes"] = a_path.stat().st_size
    a["sha256_state"] = R1.state_hash(old)
    a["score_current"] = {name: R1.score(old, items, device) for name, items in panels.items()}
    a["score_routed"] = {"grids5": R1.SnapshotRouter(out, device).score(panels["grids5"])}
    a["snapshot_roundtrip_all_rounds_identical"] = R1.equal_signature(
        R1.prediction_signature(net, panels["grids5"][:16], device),
        R1.prediction_signature(old, panels["grids5"][:16], device))
    old_sig = R1.prediction_signature(old, panels["grids5"][:16], device)
    old_outcomes = R1.exact_outcomes(old, panels["grids5"], device)
    a["score_and_itemwise_consistent"] = sum(old_outcomes) == a["score_current"]["grids5"]["right"]
    result["phases"]["grids"] = a
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    candidate = copy.deepcopy(old)
    for p in candidate.parameters():
        p.requires_grad_(True)
    assert all(p.requires_grad for p in candidate.parameters())
    assert R1.state_hash(candidate) == a["sha256_state"]
    b = train_phase(candidate, "sums", rng, rr, pool, held_inputs, device, out)
    b_path = out / "snapshot-sums.pt"
    R1.save_checkpoint(b_path, candidate, "sums", STEPS["sums"], args.seed)
    latest = R1.load_checkpoint(b_path, device)
    b["snapshot"] = str(b_path)
    b["checkpoint_bytes"] = b_path.stat().st_size
    b["sha256_state"] = R1.state_hash(latest)
    b["snapshot_roundtrip_all_rounds_identical"] = R1.equal_signature(
        R1.prediction_signature(candidate, panels["sums4"][:16], device),
        R1.prediction_signature(latest, panels["sums4"][:16], device))
    b["score_current"] = {name: R1.score(latest, items, device) for name, items in panels.items()}
    router = R1.SnapshotRouter(out, device)
    b["score_routed"] = {"grids5": router.score(panels["grids5"]),
                         "sums4": router.score(panels["sums4"])}
    reloaded_old = R1.load_checkpoint(a_path, device)
    routed_outcomes = R1.exact_outcomes(reloaded_old, panels["grids5"], device)
    latest_outcomes = R1.exact_outcomes(latest, panels["grids5"], device)
    b["grid_isolation"] = {
        "bit_identical_weights": all(torch.equal(v, reloaded_old.state_dict()[k])
                                     for k, v in old.state_dict().items()),
        "snapshot_hash_unchanged": R1.state_hash(reloaded_old) == a["sha256_state"],
        "bit_identical_predictions_and_stop_probabilities": R1.equal_signature(
            old_sig, R1.prediction_signature(reloaded_old, panels["grids5"][:16], device)),
        "per_item_exactness_identical": old_outcomes == routed_outcomes,
        "previously_correct_items_lost": sum(x and not y for x, y in zip(old_outcomes, routed_outcomes)),
        "previously_incorrect_items_gained": sum(not x and y for x, y in zip(old_outcomes, routed_outcomes)),
    }
    b["mutable_control_vs_A"] = {
        "grids5_after_B": b["score_current"]["grids5"]["right"],
        "previously_correct_items_lost": sum(x and not y for x, y in zip(old_outcomes, latest_outcomes)),
        "previously_incorrect_items_gained": sum(not x and y for x, y in zip(old_outcomes, latest_outcomes)),
    }
    result["phases"]["sums"] = b
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    requests = [panels["grids5"][:16], panels["sums4"][:16], panels["grids5"][:16]]
    before = [router.predict(items) for items in requests]
    restarted = R1.SnapshotRouter(out, device)
    after = [restarted.predict(items) for items in requests]
    try:
        restarted.model_for("unknown")
    except ValueError:
        unknown_rejected = True
    else:
        unknown_rejected = False
    result["restart_routing"] = {
        "alternating_task_ids": [items[0].env for items in requests],
        "exact_outputs_and_stop_probabilities": all(R1.equal_signature(x, y)
                                                         for x, y in zip(before, after)),
        "first_and_third_grid_requests_identical": R1.equal_signature(after[0], after[2]),
        "grid_score_unchanged": a["score_routed"]["grids5"] == b["score_routed"]["grids5"],
        "unknown_task_rejected": unknown_rejected,
    }
    valid = (a["score_current"]["grids5"]["right"] >= 190 and
             b["score_current"]["sums4"]["right"] >= 190)
    isolation = (a["checkpoint_weights_match_trained_A"] and
                 a["snapshot_roundtrip_all_rounds_identical"] and
                 a["score_and_itemwise_consistent"] and
                 b["snapshot_roundtrip_all_rounds_identical"] and
                 all(v for k, v in b["grid_isolation"].items() if isinstance(v, bool)) and
                 b["grid_isolation"]["previously_correct_items_lost"] == 0 and
                 b["score_routed"]["grids5"] == a["score_routed"]["grids5"] and
                 all(v for k, v in result["restart_routing"].items() if k != "alternating_task_ids"))
    result["criteria"] = {"A_mastery_190": a["score_current"]["grids5"]["right"] >= 190,
                          "B_mastery_190": b["score_current"]["sums4"]["right"] >= 190,
                          "isolation": isolation,
                          "baseline_forgetting_reproduced": b["mutable_control_vs_A"]["previously_correct_items_lost"] > 0,
                          "seed_status": "INCONCLUSIVE_MASTERY" if not valid else
                          ("PASS_CONTROLS" if isolation else "FAIL_ISOLATION")}
    R1.synchronize(device)
    result["total_checkpoint_bytes"] = a["checkpoint_bytes"] + b["checkpoint_bytes"]
    result["total_parameters_across_two_snapshots"] = 2 * params
    result["wall_seconds"] = round(time.monotonic() - wall_start, 1)
    result["end_utc"] = utc()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"seed": args.seed, "criteria": result["criteria"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--passmarks-sha", required=True)
    run(parser.parse_args())
