#!/usr/bin/env python3
"""Bounded training-step throughput probe on code-made practice puzzles only.

No checkpoint or test panel is read. Run after the active GPU job finishes and
the M3 Pro is clear: --device mps --out artifacts/.../diagnostics/cardbench-mps.json
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import time
from pathlib import Path

import torch
import torch.nn.functional as F

import codex_numbers_20260927_run as N

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts/codex-numbers-20260927"
SMOKE_DATA_SEED = 9276991  # deliberately outside registered training seeds
SMOKE_MODEL_SEED = 9276992
WIDTH, BATCH, FREE, GRADED = 256, 128, 5, 3


def sample_batches(device):
    source = N.Source(SMOKE_DATA_SEED, latin_pool=128, cache_dir=ART / "cache")
    groups = [("sums4", "sums", 4), ("grids5", "grids", 5), ("numbers4", "numbers", 4)]
    out = []
    for name, kind, size in groups:
        items = [source.item(kind, size) for _ in range(BATCH)]
        t, slot, target, env = N.tensors(items, device)
        assert torch.equal(env, torch.zeros_like(env))
        assert all(item.env == kind and item.size == size for item in items)
        out.append((name, t, slot, target, env))
    return out


def memory_snapshot(device):
    if device != "mps":
        return {}
    readings = {}
    for name, field in (("current_allocated_memory", "mps_current_allocated_bytes"),
                        ("driver_allocated_memory", "mps_driver_allocated_bytes")):
        method = getattr(torch.mps, name, None)
        if method is not None:
            readings[field] = int(method())
    return readings


def run_step(net, opt, audit, batch):
    _, t, slot, target, env = batch
    net.train()
    outputs = N.run_train(net, t, slot, env, n_free=FREE, n_grad=GRADED)
    losses = []
    for logits, halt in outputs:
        ce, exact = N.R.ce_and_exact(logits, slot, target)
        losses.append(ce + 0.5 * F.binary_cross_entropy_with_logits(halt.float(), exact))
    loss = torch.stack(losses).mean()
    opt.zero_grad(set_to_none=True)
    loss.backward()
    audit.check(n_grad=GRADED)
    core = [(name, p.grad) for name, p in net.named_parameters()
            if name.startswith("blocks.") and p.ndim == 2]
    cards = [(name, p.grad) for name, p in net.named_parameters() if name.startswith("cards.")]
    core_finite = core and all(g is not None and bool(torch.isfinite(g).all()) for _, g in core)
    card_finite = all(g is not None and bool(torch.isfinite(g).all()) for _, g in cards)
    card_nonzero = all(g is not None and bool(g.detach().abs().sum()) for _, g in cards)
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
    opt.step()
    return {"loss": float(loss.detach()), "core_gradients_finite": bool(core_finite),
            "card_gradients_finite": bool(card_finite),
            "card_gradients_nonzero": bool(card_nonzero) if cards else None}


def benchmark_variant(variant, batches, device, warmup, measured):
    torch.manual_seed(SMOKE_MODEL_SEED)
    if device == "mps":
        torch.mps.manual_seed(SMOKE_MODEL_SEED)
    net = N.make_net(WIDTH, 2, 8, device, variant=variant)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4, weight_decay=0.1, betas=(0.9, 0.95))
    audit = N.GradientAudit(net, device)
    seconds, checks = [], []
    observed_current, observed_driver = [], []
    for step in range(warmup + measured):
        batch = batches[step % len(batches)]
        started = time.monotonic()
        check = run_step(net, opt, audit, batch)
        if device == "mps":
            torch.mps.synchronize()
        elapsed = time.monotonic() - started
        if step >= warmup:
            seconds.append(elapsed)
            checks.append({"kind": batch[0], **check})
            mem = memory_snapshot(device)
            if "mps_current_allocated_bytes" in mem:
                observed_current.append(mem["mps_current_allocated_bytes"])
            if "mps_driver_allocated_bytes" in mem:
                observed_driver.append(mem["mps_driver_allocated_bytes"])
    assert all(x["core_gradients_finite"] and x["card_gradients_finite"] and math.isfinite(x["loss"])
               for x in checks)
    if variant == "candidate":
        assert all(x["card_gradients_nonzero"] for x in checks)
    result = {"variant": variant, "weights": sum(p.numel() for p in net.parameters()),
              "warmup_steps": warmup, "measured_steps": measured,
              "seconds_per_step_mean": sum(seconds) / len(seconds),
              "seconds_per_step_min": min(seconds), "seconds_per_step_max": max(seconds),
              "measured_kind_sequence": [x["kind"] for x in checks],
              "all_core_gradients_finite": True,
              "all_card_gradients_finite": True if variant == "candidate" else None,
              "all_card_gradients_nonzero":
                  all(x["card_gradients_nonzero"] for x in checks) if variant == "candidate" else None,
              "trainer_gradient_audit": audit.report(),
              "losses": [x["loss"] for x in checks],
              "input_tensors_preloaded_on_device": True,
              "data_generation_and_transfer_timed": False,
              "extra_per_step_finite_gradient_validation_included": True}
    if observed_current:
        result["mps_current_allocated_bytes_post_step_max_observed"] = max(observed_current)
    if observed_driver:
        result["mps_driver_allocated_bytes_post_step_max_observed"] = max(observed_driver)
    del net, opt
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--measured", type=int, default=15)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 2 <= args.warmup <= 4 or not 12 <= args.measured <= 18:
        parser.error("bounded probe requires 2-4 warmups and 12-18 measured steps")
    if args.device == "mps" and not torch.backends.mps.is_available():
        parser.error("MPS is unavailable")
    if args.device == "cpu":
        torch.set_num_threads(1)
    out = args.out or ART / "diagnostics" / f"cardbench-{args.device}.json"
    batches = sample_batches(args.device)
    results = [benchmark_variant(variant, batches, args.device, args.warmup, args.measured)
               for variant in ("baseline", "candidate")]
    report = {"device": args.device, "dtype": "float32", "torch": torch.__version__,
              "smoke_data_seed": SMOKE_DATA_SEED, "smoke_model_seed": SMOKE_MODEL_SEED,
              "width": WIDTH, "batch": BATCH, "free_rounds": FREE, "graded_rounds": GRADED,
              "practice_kinds": ["sums4", "grids5", "numbers4"], "results": results,
              "candidate_over_baseline_step_time_ratio":
                  results[1]["seconds_per_step_mean"] / results[0]["seconds_per_step_mean"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), "step_time_ratio":
                      report["candidate_over_baseline_step_time_ratio"]}, sort_keys=True))


if __name__ == "__main__":
    main()
