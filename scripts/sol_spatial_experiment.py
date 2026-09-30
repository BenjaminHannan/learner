#!/usr/bin/env python3
"""Isolated, sealed spatial development experiment. Training requires queue release.

No holdout loader is called. --smoke is synthetic mechanics without an optimizer.
--diagnose is a fixed two-seed TRAIN-only read/backward, without weight updates.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "artifacts/sol-spatial-20260929"
REVIEW = ROOT / "reviews/premonition-moe-2026-09-29"
ARMS = ("top1_base", "top1_bias_plus1", "qualified_dense")


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(p, value):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(p)


def verify():
    seal = json.loads((BUNDLE / "SEAL.json").read_text())
    for name, wanted in seal["files"].items():
        if sha(ROOT / name) != wanted:
            raise ValueError("SEAL-MISMATCH: " + name)
    spec = json.loads((BUNDLE / "SPEC.json").read_text())
    return spec, sha(BUNDLE / "SEAL.json")


def imports():
    sys.path.insert(0, str(REVIEW))
    import torch
    import real_screen as S
    import spatial_screen as P
    import spatial_relation as M
    import spatial_init_variant as V
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    return torch, S, P, M, V


def state_hash(model):
    h = hashlib.sha256()
    for name, x in sorted(model.state_dict().items()):
        h.update(name.encode()); h.update(str(x.dtype).encode())
        h.update(str(tuple(x.shape)).encode()); h.update(x.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def train_items(S, P, seed, spec):
    # Recreate the parent's TRAIN pool, using only development-layout exclusions.
    # S.make_development never invokes D.panels (the official holdout builder).
    _, supports, _, _ = S.make_development(seed, 64)
    views = [[P.transform(x, reflect, turns) for reflect in (False, True)
              for turns in range(4)] for x in supports]
    def full(items):
        return digest([[x.tokens, x.slot, x.target] for x in items])
    data = {"supports_full_sha256": full(supports),
            "views_full_sha256": full([x for row in views for x in row]),
            "support_layout_sha256": hashlib.sha256("\n".join(S.D.layout_key(x) for x in supports).encode()).hexdigest()}
    # Parent TRAIN input hashes bind exact original memories without query scoring.
    parent = json.loads((REVIEW / f"spatial-horizon512-s{seed}.json").read_text())
    if P.C.input_digest(supports) != parent["original_support_input_sha256"]:
        raise ValueError("original TRAIN inputs differ")
    if P.C.input_digest([x for row in views for x in row]) != parent["TRAIN_view_input_sha256"]:
        raise ValueError("TRAIN view inputs differ")
    return supports, views, data


def schedule(seed, updates):
    rng = random.Random(74121029 + 100000 * seed)
    visits, batches = [0] * 64, []
    for _ in range(updates // 8):
        order = list(range(64)); rng.shuffle(order)
        for begin in range(0, 64, 8):
            batch = []
            for i in order[begin:begin + 8]:
                batch.append((i, visits[i] % 8)); visits[i] += 1
            batches.append(batch)
    assert len(batches) == updates and sum(visits) == updates * 8
    return batches, visits


def models(torch, S, M, V, seed):
    source, src = S.load("loop_legacy", seed, "cpu")
    constructor_seed = 74120929 + 100000 * seed
    torch.manual_seed(constructor_seed)
    base = M.SpatialRelation(source.tok, top_k=1, raw_sum=True)
    base_rng = torch.get_rng_state().clone()
    torch.manual_seed(constructor_seed)
    variant = V.SpatialInitVariant(source.tok, top_k=1, raw_sum=True)
    assert torch.equal(base_rng, torch.get_rng_state())
    for name, x in base.state_dict().items():
        expected = x.clone()
        if name == "recurrent.bias_ih":
            expected[48:96].add_(1.)
        assert torch.equal(expected, variant.state_dict()[name]), name
    return {ARMS[0]: base, ARMS[1]: variant, ARMS[2]: copy.deepcopy(source)}, src


def smoke():
    spec, seal = verify()
    torch, S, P, M, V = imports()
    before = sha(REVIEW / "spatial_relation.py")
    checks = []
    for seed in spec["seeds"]:
        torch.manual_seed(74120929 + 100000 * seed)
        embedding = torch.randn(125, 256)
        torch.manual_seed(74120929 + 100000 * seed)
        base = M.SpatialRelation(embedding, top_k=1, raw_sum=True)
        rng = torch.get_rng_state().clone()
        torch.manual_seed(74120929 + 100000 * seed)
        variant = V.SpatialInitVariant(embedding, top_k=1, raw_sum=True)
        assert torch.equal(rng, torch.get_rng_state())
        changed = []
        for name, x in base.state_dict().items():
            expected = x.clone()
            if name == "recurrent.bias_ih": expected[48:96].add_(1.)
            assert torch.equal(expected, variant.state_dict()[name])
            if not torch.equal(x, variant.state_dict()[name]): changed.append(name)
        assert changed == ["recurrent.bias_ih"]
        assert int((base.recurrent.bias_ih != variant.recurrent.bias_ih).sum()) == 48
        tokens = torch.randint(125, (2, 2, 3)); slots = torch.randint(2, tokens.shape)
        initial = state_hash(variant)
        logits = variant(tokens, slots, rounds=24, output_rounds=(23, 24))
        assert logits.shape == (2, 2, 2, 3, 125)
        logits.square().mean().backward()
        assert variant.recurrent.bias_ih.grad.abs().sum() > 0
        assert state_hash(variant) == initial
        batches, visits = schedule(seed, spec["updates"])
        assert set(visits) == {spec["updates"] // 8}
        checks.append({"seed": seed, "changed_tensor": changed, "changed_scalars": 48,
                       "constructor_rng_equal": True, "backward_finite": bool(torch.isfinite(variant.recurrent.bias_ih.grad).all()),
                       "batch_order_sha256": digest(batches), "visits_per_memory": spec["updates"] // 8,
                       "counts": variant.counts(cells=81)})
    assert before == sha(REVIEW / "spatial_relation.py")
    return {"passed": True, "seal_sha256": seal, "checks": checks,
            "optimizer_steps": 0, "task_examples_scored": 0,
            "source_checkpoints_loaded": 0, "torch_version": torch.__version__}


def probe(torch, S, P, model, items, spatial):
    """One fixed TRAIN CE backward and label-free gate observations at read24."""
    model.eval(); model.zero_grad(set_to_none=True)
    core = state_hash(model)
    gates, routes, hidden_norms = [], [], []
    hooks = []
    if spatial:
        def gate_hook(module, args, output):
            x, h = args
            gi = torch.nn.functional.linear(x, module.weight_ih, module.bias_ih)
            gh = torch.nn.functional.linear(h, module.weight_hh, module.bias_hh)
            z = (gi.chunk(3, -1)[1] + gh.chunk(3, -1)[1]).sigmoid().detach()
            gates.append({"mean": float(z.mean()), "below_05": float((z < .05).float().mean()),
                          "above_95": float((z > .95).float().mean())})
            hidden_norms.append(float(output.detach().square().mean().sqrt()))
        def router_hook(module, args, output):
            p = output.detach().softmax(-1)
            routes.append({"counts": torch.bincount(p.argmax(-1).flatten(), minlength=2).tolist(),
                           "entropy": float(-(p * p.clamp_min(1e-20).log()).sum(-1).mean())})
        hooks = [model.recurrent.register_forward_hook(gate_hook), model.router.register_forward_hook(router_hook)]
    try:
        logits = P.forward(model, items, 24, (23, 24))
        ce = P.loss(logits, items)
        ce.backward()
    finally:
        for h in hooks: h.remove()
    _, slots, y = S.tensor_batch(items, "cpu")
    mask = slots.bool()
    pred = logits[:, -1].detach().argmax(-1)
    def hist(values): return torch.bincount(values[mask].flatten(), minlength=125).tolist()
    gradients = {n: {"l2": float(p.grad.norm()), "finite": bool(torch.isfinite(p.grad).all())}
                 for n, p in model.named_parameters() if p.grad is not None}
    assert state_hash(model) == core
    return {"TRAIN_items": len(items), "TRAIN_ce": float(ce.detach()),
            "TRAIN_exact_of_2": int(((pred == y) | ~mask).flatten(1).all(1).sum()),
            "TRAIN_cell_correct": int(((pred == y) & mask).sum()), "TRAIN_answer_cells": int(mask.sum()),
            "TRAIN_target_histogram": hist(y), "TRAIN_prediction_histogram": hist(pred),
            "gru_update_gates_by_round": gates, "router_by_round": routes,
            "hidden_rms_by_round": hidden_norms, "parameter_gradients": gradients,
            "weights_unchanged": True, "core_sha256": core}


def diagnose():
    spec, seal = verify()
    torch, S, P, M, V = imports()
    result = {"seal_sha256": seal, "development_only": True, "TRAIN_only": True,
              "optimizer_steps": 0, "query_model_evaluations": 0, "seeds": {}}
    for seed in spec["seeds"]:
        supports, _, data = train_items(S, P, seed, spec)
        nets, _ = models(torch, S, M, V, seed)
        rows = {}
        for arm in ARMS:
            rows[arm + "_fresh"] = probe(torch, S, P, nets[arm], supports[:2], arm != ARMS[2])
        for arm, parent_name in ((ARMS[0], "spatial_sum_top1"), (ARMS[2], "source_dense_full24")):
            ck = REVIEW / f"spatial-horizon512-s{seed}.{parent_name}.pt"
            nets[arm].load_state_dict(torch.load(ck, map_location="cpu", weights_only=True), strict=True)
            rows[arm + "_historical512"] = {"checkpoint_sha256": sha(ck),
                **probe(torch, S, P, nets[arm], supports[:2], arm != ARMS[2])}
        result["seeds"][str(seed)] = {"data": data, "measurements": rows}
    result["limitations"] = "Fixed first two TRAIN memories only. Gradients are local CE sensitivities, not causal evidence. No recipe changes from this probe."
    return result


def run(queue):
    spec, seal = verify()
    queue = Path(queue).resolve()
    expected_dir = ROOT / "handoff/queue"
    if queue.parent != expected_dir or sha(queue) != spec["queue_sha256"]:
        raise ValueError("Training requires coordinator-installed exact queue file under handoff/queue")
    # Atomic once-only claim precedes imports/fit; interruption never silently retrains.
    out = BUNDLE / "run"
    out.mkdir(exist_ok=False)
    record = {"seal_sha256": seal, "spec_sha256": sha(BUNDLE / "SPEC.json"),
              "queue_sha256": sha(queue), "started_utc": utc(), "pid": os.getpid(),
              "development_only": True, "official_holdout_opened": False,
              "complete": False, "models": {}, "scores": {}}
    ledger = {"started_utc": utc(), "pid": os.getpid(), "status": "PREPARING",
              "training_parameters": spec["training"], "jobs": [],
              "planned_total_updates": 6 * spec["updates"], "planned_presentation_slots": 48 * spec["updates"],
              "historical_source_training": "two reused qualified 12000-update sources; not included in new slots",
              "partial_unsaved_work_policy": "ledger before every step bounds one in-flight batch (8 slots); no automatic restart"}
    write(out / "record.json", record); write(out / "ledger.json", ledger)
    try:
        torch, S, P, M, V = imports()
        record.update(torch_version=torch.__version__, cpu_threads=2, interop_threads=1,
                      deterministic_algorithms=True)
        frozen = {}
        for seed in spec["seeds"]:
            supports, views, data = train_items(S, P, seed, spec)
            # Parent split-integrity checks (layout/target only; no model queries).
            parent_supports, _, _, split = P.build(seed)
            assert P.C.input_digest(parent_supports) == P.C.input_digest(supports)
            batches, visits = schedule(seed, spec["updates"])
            order_hash = digest(batches)
            nets, src = models(torch, S, M, V, seed)
            for arm in ARMS:
                model = nets[arm]
                key = f"s{seed}-{arm}"
                params = {"stored": sum(p.numel() for p in model.parameters()),
                          "trainable": sum(p.numel() for p in model.parameters() if p.requires_grad)}
                job = {"key": key, "seed": seed, "arm": arm, "status": "RUNNING",
                       "started_utc": utc(), "pid": os.getpid(), "parameters": params,
                       "optimizer_updates_completed": 0, "inflight_presentation_slots": 0,
                       "initial_core_sha256": state_hash(model), "source_sha256": sha(src),
                       "batch_order_sha256": order_hash, "data": data}
                ledger["jobs"].append(job); ledger["status"] = "TRAINING"
                write(out / "ledger.json", ledger)
                optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=.001, betas=(.9, .95), weight_decay=.1)
                model.train(); losses = []; tick = time.monotonic()
                for i, addresses in enumerate(batches):
                    job["inflight_presentation_slots"] = 8
                    write(out / "ledger.json", ledger)
                    items = [views[a][b] for a, b in addresses]
                    loss = P.loss(P.forward(model, items), items)
                    if not bool(torch.isfinite(loss)): raise ValueError("nonfinite loss")
                    optimizer.zero_grad(set_to_none=True); loss.backward()
                    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
                    for g in optimizer.param_groups: g["lr"] = .001 * min(1., (i + 1) / 32)
                    optimizer.step(); losses.append(float(loss.detach()))
                    job.update(optimizer_updates_completed=i + 1, inflight_presentation_slots=0,
                               completed_presentation_slots=(i + 1) * 8)
                    if (i + 1) % 128 == 0:
                        print(json.dumps({"phase": "TRAIN", "key": key, "update": i + 1,
                                          "last128_ce": sum(losses[-128:]) / 128}), flush=True)
                    write(out / "ledger.json", ledger)
                ck = out / (key + ".pt"); torch.save(model.state_dict(), ck)
                model.eval().requires_grad_(False)
                row = {"seed": seed, "arm": arm, "updates": len(losses), "losses": losses,
                       "parameters": params, "checkpoint": str(ck.relative_to(ROOT)),
                       "checkpoint_sha256": sha(ck), "final_core_sha256": state_hash(model),
                       "initial_core_sha256": job["initial_core_sha256"],
                       "batch_order_sha256": order_hash, "visits_per_memory": visits,
                       "data": data, "split": split, "source_sha256": sha(src),
                       "training_seconds": time.monotonic() - tick,
                       "last_gradient_norm_before_clip": float(grad_norm),
                       "presentation_slots": len(losses) * 8}
                if arm != ARMS[2]: row["architecture_counts"] = model.counts(cells=81)
                record["models"][key] = row
                frozen[key] = model
                job.update(status="FROZEN", finished_utc=utc(), checkpoint_sha256=sha(ck),
                           training_seconds=row["training_seconds"])
                write(out / "record.json", record); write(out / "ledger.json", ledger)
        assert len(frozen) == 6
        # One evaluation phase, after all six final checkpoints are frozen.
        # Marker refuses any second evaluation even if the process is interrupted.
        with (out / "evaluation.started").open("x") as f: f.write(utc() + "\n")
        ledger["status"] = "EVALUATING_DEVELOPMENT_ONCE"; write(out / "ledger.json", ledger)
        for seed in spec["seeds"]:
            supports, _, panel, split = P.build(seed)
            for arm in ARMS:
                key = f"s{seed}-{arm}"; model = frozen[key]
                assert split == record["models"][key]["split"]
                record["scores"][key] = {"TRAIN_original": P.evaluate(model, supports),
                    **{kind: P.evaluate(model, items) for kind, items in panel.items() if kind.startswith("mazes")}}
                assert state_hash(model) == record["models"][key]["final_core_sha256"]
                assert sha(ROOT / record["models"][key]["checkpoint"]) == record["models"][key]["checkpoint_sha256"]
                write(out / "record.json", record)
        verify()
        record.update(complete=True, finished_utc=utc(), global_2x_proven=False,
                      new_training_presentation_slots=48 * spec["updates"])
        ledger.update(status="COMPLETE_DEVELOPMENT", finished_utc=utc())
        write(out / "record.json", record); write(out / "ledger.json", ledger)
    except BaseException as e:
        ledger.update(status="INTERRUPTED_OR_FAILED", exception=repr(e), observed_utc=utc())
        write(out / "ledger.json", ledger)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("check", "smoke", "diagnose", "run"))
    p.add_argument("--queue-file")
    args = p.parse_args()
    if args.mode == "check":
        spec, seal = verify(); print(json.dumps({"ready": True, "seal_sha256": seal,
            "seeds": spec["seeds"], "training_launched": False}))
    elif args.mode == "smoke": print(json.dumps(smoke(), indent=2))
    elif args.mode == "diagnose": print(json.dumps(diagnose(), indent=2))
    else:
        if not args.queue_file: p.error("--queue-file required")
        run(args.queue_file)


if __name__ == "__main__": main()
