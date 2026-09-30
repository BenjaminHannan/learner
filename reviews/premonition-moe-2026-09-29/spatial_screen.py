"""Fixed-budget cheap spatial-loop acquisition; DEVELOPMENT only.

All four arms receive identical original64 maze memories/eight D4 views,
512updates*8 examples, full24 differentiated loops and final23/24 CE. Dense
source is the genuine qualified loop, not a reduced unqualified toy. Frozen
queries are opened only after every arm's final checkpoint is saved. Learned
stopping, sleep, few-example and isolated time-to-quality are separate tests.
"""
import argparse
import copy
import json
import random
import time
from pathlib import Path

import torch

import allactive_dispatch as F
import capsule_screen as C
import real_screen as S
import spatial_relation as M
import stop_controller as H


ARMS = ("spatial_sum_all2", "spatial_mean_all2", "spatial_sum_top1", "source_dense_full24")


def transform(item, reflection, turns):
    result = copy.deepcopy(item)
    for name in ("tokens", "slot", "target"):
        grid = copy.deepcopy(getattr(item, name))
        if reflection:
            grid = [row[::-1] for row in grid]
        for _ in range(turns):
            grid = [list(row) for row in zip(*grid[::-1])]
        setattr(result, name, grid)
    return result


def build(seed):
    historical, supports, _, digest = S.make_development(seed, 64)
    panel = C.fresh_panel(supports, historical, 64)
    views = [[transform(item, reflect, turns) for reflect in (False, True)
              for turns in range(4)] for item in supports]
    train_layouts = {S.D.layout_key(x) for row in views for x in row}
    query_layouts = {S.D.layout_key(x) for kind, rows in panel.items()
                     if kind.startswith("mazes") for x in rows}
    if train_layouts & query_layouts:
        raise ValueError("D4 TRAIN view overlaps frozen fresh query layout; do not change query seed")
    # Independent checks of copied view targets belong to data mechanics only.
    for row in views:
        for item in row:
            assert C.correctness("mazes9", [item], torch.tensor(item.target).flatten()[None]).item()
    return supports, views, panel, {
        "original_support_layout_sha256": digest,
        "original_support_input_sha256": C.input_digest(supports),
        "TRAIN_view_input_sha256": C.input_digest([x for row in views for x in row]),
        "original_memories": len(supports), "views_per_memory": 8,
        "distinct_view_layouts": len(train_layouts),
        "TRAIN_D4_views_and_queries_disjoint": True,
        "input_sha256": {k: C.input_digest(v) for k, v in panel.items()},
        "augmentation_prior": "generic square-grid D4 geometry; targets transformed, not recomputed"}


def forward(model, items, rounds=24, output_rounds=(23, 24)):
    tokens, slots, _ = S.tensor_batch(items, "cpu")
    if isinstance(model, M.SpatialRelation):
        return model(tokens, slots, rounds=rounds, grad_rounds=None,
                     output_rounds=output_rounds)
    e, offsets = model.embed(tokens, slots)
    h = torch.zeros_like(e)
    outputs = []
    for r in range(1, rounds + 1):
        h = model.step(h, e, *offsets)
        if r in output_rounds:
            outputs.append(model.read(h)[0].reshape(*tokens.shape, 125))
    return torch.stack(outputs, 1)


def loss(logits, items):
    _, slots, target = S.tensor_batch(items, "cpu")
    return torch.stack([S.N.ce_and_exact(x.flatten(1, 2), slots, target)[0]
                        for x in logits.unbind(1)]).mean()


@torch.no_grad()
def evaluate(model, items):
    result = {str(r): {"exact": 0, "predictions": [], "per_puzzle_correctness": []}
              for r in (24, 48)}
    for begin in range(0, len(items), 8):
        chunk = items[begin:begin + 8]
        logits = forward(model, chunk, 48, (24, 48))
        for r, lg in zip((24, 48), logits.unbind(1)):
            predictions = lg.argmax(-1).flatten(1)
            correct = C.correctness("mazes9", chunk, predictions).tolist()
            result[str(r)]["exact"] += sum(correct)
            result[str(r)]["predictions"].extend(predictions.tolist())
            result[str(r)]["per_puzzle_correctness"].extend(correct)
    for row in result.values():
        row["n"] = len(items)
    return result


def run(args):
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    F.BUSY_SCRIPTS += ("numeric_active_proof.py", "graph_state_stop_screen.py",
                      "stop_controller_stream.py", "program_library_screen.py", "spatial_relation.py")
    F.require_idle()
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    spec_file = S.HERE / "spatial-screen-spec.json"
    spec = json.loads(spec_file.read_text())
    hashes = {name: C.sha(S.HERE / name) for name in spec["code_sha256"]}
    assert hashes == spec["code_sha256"]
    mechanics = json.loads((S.HERE / "spatial-relation-selftest.json").read_text())
    assert mechanics["passed"] and mechanics["task_items_generated_or_evaluated"] == 0
    supports, views, panel, split = build(args.seed)
    source, src = S.load("loop_legacy", args.seed, "cpu")
    source_before = H.state_hash(source)
    torch.manual_seed(74120929 + 100000 * args.seed)
    base = M.SpatialRelation(source.tok, expert_count=2, top_k=2, raw_sum=True)
    models = {arm: copy.deepcopy(base) for arm in ARMS[:-1]}
    models["spatial_mean_all2"].raw_sum = False
    models["spatial_sum_top1"].top_k = 1
    models[ARMS[-1]] = copy.deepcopy(source)
    rng = random.Random(74121029 + 100000 * args.seed)
    visits = [0] * 64
    batches = []
    for _ in range(64):
        order = list(range(64)); rng.shuffle(order)
        for begin in range(0, 64, 8):
            batch = []
            for i in order[begin:begin + 8]:
                batch.append(views[i][visits[i] % 8]); visits[i] += 1
            batches.append(batch)
    assert len(batches) == 512
    record = {**split, "source_seed": args.seed, "source_sha256": C.sha(src),
              "development_only": True, "official_holdout_opened": False,
              "updates": 512, "batch": 8, "new_presentation_slots_per_arm": 4096,
              "fully_differentiated_rounds": 24, "supervised_rounds": [23, 24],
              "primary_fixed_depth": 48, "diagnostic_fixed_depth": 24,
              "old_replay_slots": 0, "old_retention_not_proved": True,
              "learned_stopping_not_calibrated": True, "isolated_latency_claim": False,
              "query_selected_checkpoint_or_threshold": False,
              "code_sha256": hashes, "spec_sha256": C.sha(spec_file), "models": {}}
    started = time.monotonic()
    for arm, model in models.items():
        train_tick = time.monotonic()
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                    lr=.001, betas=(.9, .95), weight_decay=.1)
        losses = []
        for i, items in enumerate(batches):
            logits = forward(model, items)
            objective = loss(logits, items)
            assert bool(torch.isfinite(objective))
            optimizer.zero_grad(set_to_none=True)
            objective.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            for group in optimizer.param_groups:
                group["lr"] = .001 * min(1., (i + 1) / 32)
            optimizer.step()
            losses.append(float(objective.detach()))
        checkpoint = out.with_suffix(f".{arm}.pt")
        torch.save(model.state_dict(), checkpoint)
        model.eval().requires_grad_(False)
        record["models"][arm] = {
            "checkpoint": str(checkpoint), "checkpoint_sha256": C.sha(checkpoint),
            "training_seconds_not_time_to_quality": time.monotonic() - train_tick,
            "first16_train_ce": sum(losses[:16]) / 16,
            "last16_train_ce": sum(losses[-16:]) / 16,
            "frozen_core_state_sha256": H.state_hash(model),
            "stored_parameters": sum(p.numel() for p in model.parameters())}
        if isinstance(model, M.SpatialRelation):
            record["models"][arm]["architecture_counts"] = model.counts(cells=81)
        out.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"phase": "spatial_TRAIN_complete", "arm": arm,
                          **record["models"][arm]}), flush=True)
    # No query scoring before all four checkpoint states are final and frozen.
    for arm, model in models.items():
        record["models"][arm]["scores"] = {
            "TRAIN_original": evaluate(model, supports),
            **{kind: evaluate(model, rows) for kind, rows in panel.items()
               if kind.startswith("mazes")}}
        assert H.state_hash(model) == record["models"][arm]["frozen_core_state_sha256"]
        print(json.dumps({"phase": "spatial_frozen_scores", "arm": arm,
              "exact": {k: {d: z["exact"] for d, z in value.items()}
                        for k, value in record["models"][arm]["scores"].items()}}), flush=True)
    assert H.state_hash(source) == source_before
    record.update(complete=True, elapsed_seconds=time.monotonic() - started,
                  global_2x_proven=False)
    out.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=(0, 1), required=True)
    parser.add_argument("--out", required=True)
    run(parser.parse_args())
