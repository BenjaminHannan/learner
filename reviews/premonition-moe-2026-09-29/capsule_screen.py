"""Fixed-recipe, train-memory-only PROGRAM-capsule retention screen.

CPU, two threads, 200 full-memory router CE updates; no reasoning updates,
sleep, query tuning, or official holdout construction. All writes stay here.
Results include the router weights/buffers as JSON for exact reconstruction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import random
import time
from unittest.mock import patch

import torch
from torch import nn
from torch.nn import functional as F

import real_screen as S
from capsule_moe import CapsuleMoE

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROUTER_SEED = 74019000
FRESH_PANEL_SEED = 74029000
ROUTER_UPDATES = 200
ROUTER_LR = .003


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def state_sha(module):
    # In-memory serialization avoids any parent-owned checkpoint writes.
    stream = io.BytesIO()
    torch.save(module.state_dict(), stream)
    return hashlib.sha256(stream.getvalue()).hexdigest()


def input_tensors(items):
    # Deliberately never access Item.target/env/size/meta during router fitting.
    return (torch.tensor([x.tokens for x in items]), torch.tensor([x.slot for x in items]))


def input_digest(items):
    return hashlib.sha256(json.dumps([[x.tokens, x.slot] for x in items],
                                     separators=(",", ":")).encode()).hexdigest()


def train_router(net, groups):
    start = time.monotonic()
    features, memberships = [], []
    for items, expert in groups:
        t, s = input_tensors(items)
        features.append(net.routing_features(t, s))
        memberships.append(torch.full((len(items),), expert, dtype=torch.long))
    x, y = torch.cat(features), torch.cat(memberships)
    net.router.standardize_from_train(x)
    net.train()
    opt = torch.optim.AdamW(net.router.parameters(), lr=ROUTER_LR, weight_decay=.0001)
    # Chronological membership labels: expert 0 owns old replay, expert 1 owns
    # new supports. Each expert contributes equally despite the 256:64 counts.
    weights = len(y) / (2 * torch.bincount(y).float())
    initial_loss = float(F.cross_entropy(net.router(x), y, weight=weights).detach())
    losses = []
    optimize_start = time.monotonic()
    for _ in range(ROUTER_UPDATES):
        logits = net.router(x)
        loss = F.cross_entropy(logits, y, weight=weights)
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite router CE")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if any(p.grad is not None for capsule in net.capsules for p in capsule.parameters()):
            raise RuntimeError("router optimization touched an immutable capsule")
        opt.step()
        losses.append(float(loss.detach()))
    optimization_seconds = time.monotonic() - optimize_start
    net.eval()
    with torch.no_grad():
        pred = net.router(x).argmax(-1)
        final_loss = float(F.cross_entropy(net.router(x), y, weight=weights))
    return {"updates": ROUTER_UPDATES, "optimizer": "AdamW", "lr": ROUTER_LR,
            "weight_decay": .0001, "full_batch_size": len(y), "expert_loss_weights": weights.tolist(),
            "initial_ce": initial_loss, "final_ce": final_loss, "last_update_ce": losses[-1],
            "feature_and_fit_seconds": time.monotonic() - start,
            "router_optimization_seconds": optimization_seconds,
            "history_membership_accuracy": float((pred == y).float().mean()),
            "history_membership_counts": [{"assigned_expert": i, "n": int((y == i).sum()),
                                            "correct": int(((pred == y) & (y == i)).sum())}
                                          for i in range(2)],
            "train_route_counts": torch.bincount(pred, minlength=2).tolist(),
            "reasoning_updates": 0, "query_labels_or_query_selection_used": False}


def fresh_panel(supports, historic_panel, n=64):
    rng = random.Random(FRESH_PANEL_SEED)
    panel = {"sums4": [S.E.make_sum(rng, 4) for _ in range(n)],
             "grids5": [S.D.latin_legend(rng, 5) for _ in range(n)]}
    banned = {S.D.layout_key(it) for it in supports}
    banned.update(S.D.layout_key(it) for key, items in historic_panel.items()
                  if key.startswith("mazes") for it in items)
    seen = set()
    for size in (9, 11):
        panel[f"mazes{size}"] = [S.D.unique_maze(rng, size, banned, seen) for _ in range(n)]
    assert not seen & banned
    return panel


def pick(ps, qs):
    stable = (ps[:, 2:] == ps[:, 1:-1]).all(-1) & (ps[:, 1:-1] == ps[:, :-2]).all(-1)
    fire = stable & (qs[:, 2:] > .5)
    rounds = torch.where(fire.any(1), fire.long().argmax(1) + 3,
                         torch.full((len(ps),), ps.shape[1], device=ps.device))
    return ps[torch.arange(len(ps), device=ps.device), rounds - 1], rounds


class TraceView(nn.Module):
    """Delegate to real_screen.evaluate, recording label-free model outputs."""

    def __init__(self, net):
        super().__init__()
        self.net, self.traces = net, []

    @torch.no_grad()
    def loop_rounds(self, t, s, cap):
        ps, qs = self.net.loop_rounds(t, s, cap)
        selected, rounds = pick(ps, qs)
        trace = {"predictions": ps.cpu(), "halt_probabilities": qs.cpu(),
                 "picked": selected.cpu(), "rounds": rounds.cpu()}
        if isinstance(self.net, CapsuleMoE):
            trace.update(routes=self.net.last_routes.cpu(),
                         route_logits=self.net.last_route_logits.cpu())
        self.traces.append(trace)
        return ps, qs


def evaluate_trace(net, panel, phase):
    scores, traces = {}, {}
    for name, items in panel.items():
        view = TraceView(net)
        scores.update(S.evaluate(view, {name: items}, "cpu", batch=16, cap=48))
        traces[name] = {key: torch.cat([row[key] for row in view.traces])
                        for key in view.traces[0]}
        print(json.dumps({"phase": phase, "panel": name, "learned": scores[name]["learned"],
                          "n": len(items)}), flush=True)
    return scores, traces


def correctness(name, items, predictions):
    if name == "sums4":
        return torch.tensor([bool(S.E.check(it, p.reshape(len(it.tokens), -1).tolist()))
                             for it, p in zip(items, predictions)])
    t, s, y = S.N.tensors(items)
    return ((predictions == y.reshape(len(t), -1)) | ~s.reshape(len(t), -1).bool()).all(1)


def routing_report(panel, source, acquired, routed):
    report = {}
    all_predictions_match = True
    for name, items in panel.items():
        src, body, route = source[name], acquired[name], routed[name]
        ids = route["routes"]
        hits = [correctness(name, items, tr["picked"]) for tr in (src, body, route)]
        expected_p = torch.where(ids[:, None, None] == 0, src["predictions"], body["predictions"])
        expected_q = torch.where(ids[:, None] == 0, src["halt_probabilities"], body["halt_probabilities"])
        parity = bool(torch.equal(route["predictions"], expected_p))
        q_error = float((route["halt_probabilities"] - expected_q).abs().max())
        all_predictions_match &= parity
        expected_expert = 0 if name in ("sums4", "grids5") else 1
        source_probability = route["route_logits"].softmax(-1)[:, 0]
        conditioned = []
        for i in range(2):
            selected = ids == i
            conditioned.append({"route": i, "n": int(selected.sum()),
                                "routed_picked_exact": int((hits[2] & selected).sum()),
                                "source_picked_exact": int((hits[0] & selected).sum()),
                                "acquired_picked_exact": int((hits[1] & selected).sum())})
        report[name] = {"n": len(items), "route_counts_source_acquired": torch.bincount(ids, minlength=2).tolist(),
                        "expected_history_expert_for_report_only": expected_expert,
                        "history_route_correct": int((ids == expected_expert).sum()),
                        "mean_source_probability": float(source_probability.mean()),
                        "min_source_probability": float(source_probability.min()),
                        "max_source_probability": float(source_probability.max()),
                        "conditioned_exact_comparison": conditioned,
                        "routed_minus_source_picked_exact": int(hits[2].sum() - hits[0].sum()),
                        "routed_minus_acquired_picked_exact": int(hits[2].sum() - hits[1].sum()),
                        "source_correct_lost_by_routing": int((hits[0] & ~hits[2]).sum()),
                        "source_correct_recovered_vs_body": int((hits[0] & ~hits[1] & hits[2]).sum()),
                        "acquired_correct_lost_by_routing": int((hits[1] & ~hits[2]).sum()),
                        "selected_branch_all_round_prediction_parity": parity,
                        "selected_branch_halt_probability_max_abs_error": q_error}
        if not parity or q_error > 1e-5:
            raise RuntimeError(f"routed branch semantics differ on {name}")
    return report, all_predictions_match


def selftest(net, supports):
    """Exercise mixed routes, separate embeddings, inherited loops and freezing."""
    t, s = input_tensors(supports[:4])
    routes = torch.tensor([0, 1, 0, 1])
    forced_logits = F.one_hot(routes, 2).float() * 10
    calls = [[], []]
    hooks = [capsule.blocks[0].register_forward_pre_hook(
        lambda module, inputs, index=i: calls[index].append(len(inputs[0])))
             for i, capsule in enumerate(net.capsules)]
    try:
        with patch.object(net, "route_logits", return_value=forced_logits), torch.no_grad():
            e, (dr, dc) = net.embed(t, s)
            h = torch.zeros_like(e)
            for _ in range(4):
                h = net.step(h, e, dr, dc)
            logits, halt = net.read(h)
        assert calls == [[2] * 4, [2] * 4], calls
    finally:
        for hook in hooks:
            hook.remove()
    errors = []
    with torch.no_grad():
        for i, capsule in enumerate(net.capsules):
            ids = (routes == i).nonzero(as_tuple=True)[0]
            ce, (cr, cc) = capsule.embed(t[ids], s[ids])
            torch.testing.assert_close(e[ids, :, :256], ce, rtol=0, atol=0)
            ch = torch.zeros_like(ce)
            for _ in range(4):
                ch = capsule.step(ch, ce, cr, cc)
            lg, q = capsule.read(ch)
            torch.testing.assert_close(logits[ids], lg, rtol=1e-5, atol=1e-5)
            torch.testing.assert_close(halt[ids], q, rtol=1e-5, atol=1e-5)
            errors.append(float((logits[ids] - lg).abs().max()))
        # Match Peirce's active executor: remove/permutate batch rows in h/e
        # without calling embed again or updating any cached router outputs.
        retained = torch.tensor([3, 0, 1])
        compact_h, compact_e = h[retained], e[retained]
        for _ in range(2):
            compact_h = net.step(compact_h, compact_e, dr, dc)
        compact_lg, compact_q = net.read(compact_h)
        compact_error = 0.
        for i, capsule in enumerate(net.capsules):
            local = (routes[retained] == i).nonzero(as_tuple=True)[0]
            original_rows = retained[local]
            ce, (cr, cc) = capsule.embed(t[original_rows], s[original_rows])
            ch = torch.zeros_like(ce)
            for _ in range(6):
                ch = capsule.step(ch, ce, cr, cc)
            lg, q = capsule.read(ch)
            torch.testing.assert_close(compact_lg[local], lg, rtol=1e-5, atol=1e-5)
            torch.testing.assert_close(compact_q[local], q, rtol=1e-5, atol=1e-5)
            compact_error = max(compact_error, float((compact_lg[local] - lg).abs().max()))
        assert torch.equal(compact_h[:, 0, -1].long(), routes[retained])
        one_lg, one_q = net.read(compact_h[[0]])
        torch.testing.assert_close(one_lg, compact_lg[[0]], rtol=1e-5, atol=1e-5)
        torch.testing.assert_close(one_q, compact_q[[0]], rtol=1e-5, atol=1e-5)
        a, _ = net.capsules[0].embed(t, s)
        b, _ = net.capsules[1].embed(t, s)
        embedding_gap = float((a - b).abs().max())
        assert embedding_gap > 0, "fixture must exercise different learned embeddings"
        for empty_slots in (torch.zeros_like(s), torch.ones_like(s)):
            assert torch.isfinite(net.routing_features(t, empty_slots)).all()
        with patch.object(net, "route_logits", return_value=forced_logits):
            outs = net.loop_train(t, s, 2, 2)
            torch.testing.assert_close(outs[-1][0], logits, rtol=1e-5, atol=1e-5)
            ps, qs = net.loop_rounds(t, s, 4)
            assert torch.equal(ps[:, -1], logits.argmax(-1))
            assert tuple(qs.shape) == (4, 4)
            ips, iqs = net.infer_rounds(t, s, 4)
            assert torch.equal(ips, ps) and torch.equal(iqs, qs)
            cells, stops = net(t, s)
            assert len(cells) == len(stops) == 48 and cells[-1].shape[-1] == 125
    net.train()
    assert all(not c.training for c in net.capsules)
    assert all(not p.requires_grad for c in net.capsules for p in c.parameters())
    net.eval()
    return {"passed": True, "mixed_macro_routes": routes.tolist(),
            "macro_block_dispatch_rows_per_round": calls,
            "per_expert_logit_max_abs_errors": errors,
            "source_vs_acquired_embedding_max_abs_gap": embedding_gap,
            "embedding_and_state_width": 257, "explicit_route_control_channel": True,
            "row_compaction_and_permutation": "pass",
            "compacted_branch_logit_max_abs_error": compact_error,
            "read_after_independent_row_compaction": "pass",
            "loop_train_loop_rounds_infer_rounds_forward": "pass",
            "empty_and_full_fill_masks_finite": True,
            "frozen_capsules_remain_eval_in_train_mode": True}


def confined_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError("output must stay under reviews/premonition-moe-2026-09-29")
    return path


def verify_active_executor(net, panel, replay):
    """Small actual-executor check; no training, tuning or timing claim."""
    import active_eval as A
    start = time.monotonic()
    before = [state_sha(c) for c in net.capsules]
    learned = A.compare_development(net, {name: items[:8] for name, items in panel.items()},
                                    batch=8, cap=48)
    t, s = input_tensors(replay["sums4"][:8])
    routes = torch.tensor([0, 1, 0, 1, 0, 1, 0, 1])
    with patch.object(net, "route_logits", return_value=F.one_hot(routes, 2).float() * 10):
        pred, rr, stopped = A.offline_execute(net, t, s, 48)
        active = A.active_execute(net, t, s, 48)
    assert torch.equal(active.predictions, pred)
    assert torch.equal(active.rounds, rr)
    assert torch.equal(active.stopped, stopped)
    assert any(size < len(routes) for size in active.active_sizes)
    assert active.row_rounds == int(rr.sum())
    after = [state_sha(c) for c in net.capsules]
    assert before == after
    return {"actual_active_eval_integration": "pass", "active_eval_path": str(HERE / "active_eval.py"),
            "active_eval_sha256": sha(HERE / "active_eval.py"), "device": "cpu", "threads": 2,
            "fit_updates": 0, "fresh_first8_per_panel": learned,
            "forced_mixed_train_replay_routes": routes.tolist(),
            "forced_mixed_predictions_rounds_stops_exact": True,
            "forced_mixed_active_sizes": list(active.active_sizes),
            "forced_mixed_selected_rounds": rr.tolist(), "frozen_state_sha256_before": before,
            "frozen_state_sha256_after": after, "verification_seconds": time.monotonic() - start,
            "wall_clock_speed_claim": False}


def run(args):
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(ROUTER_SEED + args.seed)
    record_path = Path(args.record or HERE / f"real_screen/moe_local_manual_plastic_anchor_replay-s{args.seed}.json").resolve()
    out = confined_path(args.out or HERE / ("capsule_screen.json" if args.seed == 0 else f"capsule_screen-s{args.seed}.json"))
    notes = confined_path(args.notes or HERE / ("capsule_notes.md" if args.seed == 0 else f"capsule_notes-s{args.seed}.md"))
    if out.exists() or notes.exists():
        raise FileExistsError("capsule output already exists; choose a new --out/--notes")
    record = json.loads(record_path.read_text())
    if record["seed"] != args.seed or record["arm"] != "moe_local_manual_plastic_anchor_replay":
        raise ValueError("record must identify the matching DAY arm and seed")
    body_record_path = Path(args.body_record).resolve() if args.body_record else record_path
    body_record = json.loads(body_record_path.read_text())
    for key in ("seed", "source_sha256", "support_sha256"):
        if body_record[key] != record[key]:
            raise ValueError(f"body record has incompatible source/training provenance: {key}")
    if body_record.get("new_family", "maze") != "maze":
        raise ValueError("this fixed capsule proof uses the original maze TRAIN memories")
    body_arm = body_record["arm"]
    checkpoint = Path(args.body_checkpoint).resolve() if args.body_checkpoint else body_record_path.with_suffix(".k64.pt")
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    external_body_record = checkpoint.with_suffix(".json") if args.body_checkpoint else None
    if external_body_record is not None and not external_body_record.exists():
        external_body_record = None
    source_path = ROOT / f"artifacts/claude-fewex-20260927/runs/qual-loop-s{args.seed}/source.pt"
    if sha(source_path) != record["source_sha256"]:
        raise ValueError("original source provenance differs from DAY record")
    original = S.N.Net("loop")
    original.load_state_dict(torch.load(source_path, map_location="cpu", weights_only=True), strict=True)
    # Preserve the original E8 constructor's RNG sequence for macro-router
    # initialization. Auto-arm loading runs in a fork and does not perturb it.
    # This temporary untrained allocation is discarded, never stepped/stored.
    body = S.SleepMoE(original, local="manual", freeze_shared=False)
    if args.body_record:
        with torch.random.fork_rng(devices=[]):
            body, loaded_source_path = S.load(body_arm, args.seed, "cpu")
        if Path(loaded_source_path).resolve() != source_path.resolve():
            raise ValueError("auto-arm body loader selected a different original source")
    body.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    if body.weight_count() != body_record["stored"]:
        raise ValueError("loaded body parameter count differs from its record")
    net = CapsuleMoE(original, body)
    historic, supports, replay, digest = S.make_development(args.seed, 64, "maze")
    if digest != record["support_sha256"]:
        raise ValueError("permitted TRAIN supports no longer match the DAY checkpoint")
    before_hashes = [state_sha(c) for c in net.capsules]
    tests = selftest(net, supports)
    source_train, _ = evaluate_trace(original, replay, "source_train_qualification")
    qualified = all(v["learned"] >= .95 * v["n"] for v in source_train.values())
    if not qualified:
        raise RuntimeError("original source misses the 95% TRAIN replay bar")
    fit = train_router(net, [(replay["sums4"], 0), (replay["grids5"], 0), (supports, 1)])
    router_state = {name: value.detach().cpu().tolist() for name, value in net.router.state_dict().items()}
    after_fit_hashes = [state_sha(c) for c in net.capsules]
    assert before_hashes == after_fit_hashes, "body/source weights changed during router fit"
    # The fresh query panel is created only AFTER the fixed 200-update fit.
    panel = fresh_panel(supports, historic)
    panel_inputs = {name: input_digest(items) for name, items in panel.items()}
    eval_start = time.monotonic()
    source_scores, source_trace = evaluate_trace(original, panel, "fresh_original_source")
    body_scores, body_trace = evaluate_trace(body, panel, "fresh_acquired_body")
    net.reset_activity()
    routed_scores, routed_trace = evaluate_trace(net, panel, "fresh_routed_capsules")
    activity = dict(net.activity)
    activity["mean_active_core_parameters_per_problem_round"] = activity["active_core_parameter_sum"] / activity["problem_rounds"]
    conditioning, parity = routing_report(panel, source_trace, body_trace, routed_trace)
    fresh_seconds = time.monotonic() - eval_start
    historic_scores = None
    historical_stage = None
    if checkpoint == body_record_path.with_suffix(".k64.pt"):
        historical_stage = "after_adapt"
    elif checkpoint == body_record_path.with_suffix(".k64.sleep.pt"):
        historical_stage = "after_sleep"
    if historical_stage is not None:
        historic_scores, _ = evaluate_trace(body, historic, f"historical_body_{historical_stage}_reproduction")
        for name, score in historic_scores.items():
            expected = body_record["rungs"]["64"][historical_stage][name]
            if any(score[key] != expected[key] for key in ("learned", "fixed16", "fixed32", "fixed48")):
                raise RuntimeError(f"body reconstruction fails {historical_stage} score parity on {name}")
    active_verification = verify_active_executor(net, panel, replay)
    final_hashes = [state_sha(c) for c in net.capsules]
    assert final_hashes == before_hashes
    assert all(p.grad is None for c in net.capsules for p in c.parameters())
    # Round-trip the saved JSON router to check that its serialized recipe is usable.
    with torch.no_grad():
        example_t, example_s = input_tensors(supports[:8])
        features = net.routing_features(example_t, example_s)
        expected_logits = net.router(features).clone()
        decoded = json.loads(json.dumps(router_state))
        net.router.load_state_dict({name: torch.tensor(value, dtype=net.router.state_dict()[name].dtype)
                                    for name, value in decoded.items()}, strict=True)
        assert torch.equal(net.router(features), expected_logits)
    result = {"candidate": "hierarchical_sparse_PROGRAM_capsules", "seed": args.seed,
              "created_utc": datetime.now(timezone.utc).isoformat(), "development_only": True,
              "official_holdout_opened_or_constructed": False, "device": "cpu", "threads": 2,
              "torch_version": torch.__version__, "original_source_checkpoint": str(source_path),
              "original_source_sha256": sha(source_path), "body_checkpoint": str(checkpoint),
              "body_checkpoint_sha256": sha(checkpoint), "body_arm": body_arm,
              "body_record": str(body_record_path), "body_record_sha256": sha(body_record_path),
              "body_record_stored_parameters": body_record["stored"],
              "body_stage": historical_stage or "external_frozen_body",
              "external_body_record": str(external_body_record) if external_body_record else None,
              "external_body_record_sha256": sha(external_body_record) if external_body_record else None,
              "DAY_record": str(record_path), "DAY_record_sha256": sha(record_path),
              "code_sha256": {str(path.relative_to(ROOT)): sha(path) for path in
                               [HERE / "capsule_moe.py", Path(__file__).resolve(), HERE / "real_screen.py",
                                HERE / "sleep_moe.py", HERE / "fast_depthwise.py", HERE / "active_eval.py",
                                ROOT / "scripts/claude_fewex_net.py", ROOT / "scripts/claude_fewex_data.py",
                                ROOT / "scripts/claude_rsn358a_envs.py", ROOT / "scripts/claude_rsn358m_maze.py"]},
              "provenance_limit": "Strict checkpoint loading and default DAY historical score reproduction establish current semantics. Present-day dependency hashes cannot prove the definitions originally imported by the parent run.",
              "train_memory": {"sums_replay": 128, "grid_replay": 128, "new_supports": 64,
                               "support_layout_sha256": digest,
                               "input_sha256": {"sums4": input_digest(replay["sums4"]),
                                                "grids5": input_digest(replay["grids5"]),
                                                "new_supports": input_digest(supports)},
                               "label_provenance": "expert 0 for old experience, expert 1 for acquired experience, assigned solely by chronology/history; no puzzle targets read by router training",
                               "retained_replay_input_and_membership_json_bytes": len(json.dumps(
                                   [{"tokens": it.tokens, "slots": it.slot, "expert": expert}
                                    for items, expert in [(replay["sums4"], 0), (replay["grids5"], 0), (supports, 1)]
                                    for it in items], separators=(",", ":")).encode())},
              "source_train_qualification": {"bar": .95, "passed": qualified, "scores": source_train,
                                              "replay_is_permitted_training_evidence": True},
              "routing_features": "SOURCE frozen embeddings: fill-slot mean, non-fill-slot mean, whole-input mean, H/16, W/16, fill fraction; train-only standardization with scale floor .05",
              "router_seed": ROUTER_SEED + args.seed, "router_fit": fit,
              "router_initialization": "legacy E8 initialization stream preserved; body-record auto-arm loading isolated with torch.random.fork_rng",
              "router_state_dict": router_state, "router_json_roundtrip_exact": True,
              "counts": net.counts(), "frozen_state_sha256_before": before_hashes,
              "frozen_state_sha256_after_router_fit": after_fit_hashes,
              "frozen_state_sha256_after_all_evaluations": final_hashes,
              "selftest": tests, "fresh_development": {"seed": FRESH_PANEL_SEED, "n_per_panel": 64,
                  "input_sha256": panel_inputs, "same_input_seed_across_model_seeds": True,
                  "maze_layouts_disjoint_from_supports_and_historical_panel": True,
                  "created_after_router_fit": True,
                  "stop_rule": "argmax all 125 classes; full prediction stable for 3 rounds, learned halt probability > .5, minimum 3 rounds, cap 48",
                  "scorer": "real_screen.evaluate: original sum checker; masked canonical exact for unique legend grids and mazes",
                  "per_expert_stage": {"original_source": source_scores, "frozen_acquired_body": body_scores},
                  "routed_picked_accuracy": routed_scores, "routing_conditioned_comparison": conditioning,
                  "selected_branch_prediction_parity": parity, "actual_activity": activity,
                  "full_cap_eval_seconds": fresh_seconds},
              "historical_DAY_reproduction": historic_scores if historical_stage == "after_adapt" and body_record_path == record_path else None,
              "historical_body_reproduction": {"stage": historical_stage, "scores": historic_scores} if historical_stage else None,
              "active_executor_verification": active_verification,
              "sleep_updates": 0, "extra_reasoning_updates": 0,
              "query_hyperparameter_searches": 0, "total_seconds": time.monotonic() - started,
              "implementation_amendment": "Initial cached-batch prototype was interrupted for the user-requested row-compaction interface amendment after some seed-0 development inference. Router features, seed, optimizer, updates and training memories were unchanged; no parameter selection was based on those query outcomes.",
              "scope": "partial retention proof on generated development panels; two complete stored cores, no broad/time or million-tiny-experts claim"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    write_notes(notes, result, out)
    print(json.dumps({"phase": "done", "output": str(out), "fit_seconds": fit["feature_and_fit_seconds"],
                      "scores": {name: {"source": source_scores[name]["learned"],
                                        "body": body_scores[name]["learned"],
                                        "routed": routed_scores[name]["learned"],
                                        "routes": conditioning[name]["route_counts_source_acquired"]}
                                 for name in panel}, "total_seconds": result["total_seconds"]}), flush=True)


def write_notes(path, result, out):
    fresh, counts, fit = result["fresh_development"], result["counts"], result["router_fit"]
    microbanks = ", ".join(f"block {i}: E={cfg['E']}, k={cfg['k']}"
                           for i, cfg in enumerate(counts["microbank_config"]))
    rows = []
    for name, routed in fresh["routed_picked_accuracy"].items():
        source = fresh["per_expert_stage"]["original_source"][name]
        body = fresh["per_expert_stage"]["frozen_acquired_body"][name]
        routes = fresh["routing_conditioned_comparison"][name]["route_counts_source_acquired"]
        rows.append(f"| {name} | {source['learned']}/{source['n']} | {body['learned']}/{body['n']} | {routed['learned']}/{routed['n']} | {routes[0]}/{routes[1]} |")
    text = f"""# PROGRAM-capsule development proof, seed {result['seed']}

The router was fitted once for exactly 200 full-memory CPU updates with two
threads, using 128 sum and 128 grid replay inputs assigned source expert 0 and
64 maze support inputs assigned acquired expert 1 by chronology. Expert
membership is ordinary replay supervision. No answer targets, task-kind IDs,
token-ID thresholds, expert predictions, checkers, development selection, or
official holdout construction entered routing. The fixed 32-unit router uses
three means of frozen original-source embeddings plus observed H, W and mask
fraction. Both complete cores remain frozen; state hashes match before/after
training and evaluation. Original-source TRAIN replay passes the 95% bar.

Fresh panel seed {fresh['seed']}, 64 each, created after router fitting. Maze
layouts exclude both DAY supports and the historical screen. `real_screen.evaluate`
uses all 125 classes and the original full-prediction stability/halt rule with
a 48-round cap. Scores are picked puzzle exact accuracy, not cell accuracy.

| Panel | Original source | Frozen body | Routed picked | Source/acquired routes |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

The JSON includes exact comparisons conditioned on the chosen route against
both experts, source-correct answers lost/recovered, acquired answers lost,
full-trajectory branch prediction parity and halt-logit probability errors.
Forced mixed-route tests validate separate expert embeddings, one macroexpert
per row per loop, all inherited Net loop APIs, and frozen/eval expert bodies.
Embedding and state are `[B,N,257]`: 256 learned channels plus one explicit
route-control channel. `step` reads the route from `e`, and `read` from `h`.
Compacting/permuting rows without re-embedding passes direct-branch parity;
there is no execution dependency on per-batch route/embedding caches. Both
capsules share each problem's geometry. The extra control channel adds one
FP32 value per token per state/embedding tensor (0.390625% channel overhead).
Recognized DAY/NIGHT checkpoint paths also reproduce their corresponding
historical scores without training on them. Actual `active_eval` compaction
passes prediction, selected-round and stop-flag parity on eight fresh inputs
per panel and a mixed-route TRAIN replay batch.

Router feature extraction and fitting took {fit['feature_and_fit_seconds']:.6f}s;
the actual 200 CE optimizer updates took {fit['router_optimization_seconds']:.6f}s.
Train chronology accuracy: {fit['history_membership_accuracy']:.6f}.
Total screen time: {result['total_seconds']:.6f}s. Full-cap timing executes all
48 rounds; picked mean rounds are not actual early-exit compute savings.

Storage: source {counts['source_core']:,}, body {counts['acquired_core']:,},
router {counts['router']:,} parameters; total {counts['stored_parameters']:,}
({counts['stored_parameter_bytes_fp32']:,} raw FP32 weight bytes),
{counts['stored_ratio_vs_acquired_body']:.6f} times body-only storage. Additional
router normalization buffers: {counts['router_standardization_buffer_floats']:,}
FP32 values. Serialized replay inputs/membership would occupy
{result['train_memory']['retained_replay_input_and_membership_json_bytes']:,} compact
JSON bytes; the existing training memory is regenerated deterministically here.
The result also stores router weights as JSON, whose file size includes text
serialization overhead and is not the raw parameter byte count.

Source active core: {counts['active_source_core']:,}; acquired always-active
core/interfaces/micro routers: {counts['active_acquired_always']:,}; acquired
microbank configuration is {microbanks}. Selected-weight count per loop ranges
{counts['active_acquired_core_per_loop_min']:,}–{counts['active_acquired_core_per_loop_max']:,}.
Charge an additional {counts['router']:,} macro-router parameters once per
problem; acquired routes also access {counts['source_embedding_parameters_once_per_problem']:,}
original-source embedding parameters for routing. Each selected trajectory
uses its own input embedding and readout. Microexpert selections can change
over rounds; the JSON records actual activity and microexpert dispatch counts. These counts are
weight sets accessed, not FLOPs, and do not support a speedup claim.

This is a two-complete-core partial retention prototype, not a million-tiny-
experts design, a broad generalization result or a two-times quality/time result.
No extra reasoning training or sleep was performed. Geometry distinguishes
these panels and is a permissible routing feature; this does not establish
routing between experiences with matching input distributions or geometry.

Source SHA256: `{result['original_source_sha256']}`.
Body SHA256: `{result['body_checkpoint_sha256']}`.
Body: `{result['body_checkpoint']}`.
Body arm: `{result['body_arm']}`; record: `{result['body_record']}`.
Present-day dependency hashes cannot certify the parent's originally imported
definitions; strict loading and DAY historical parity establish current
reconstruction semantics. Full provenance and learned router state: `{out.name}`.

Reproduce using `PYTHONDONTWRITEBYTECODE=1 uv run --offline --with torch python
reviews/premonition-moe-2026-09-29/capsule_screen.py --seed {result['seed']}`
with fresh `--out` and `--notes` paths under the review directory.
Optional `--body-checkpoint /absolute/external.ck` freezes a later compatible
body with the same router recipe and source/training memories. It requires an
existing checkpoint and uses the original DAY record for memory provenance;
unrecognized checkpoint paths have no historical score reproduction. No maturation
or sleep job is started by this script.
Use `--body-record` with a different arm's original acquisition record for
automatic `real_screen.load` architecture selection. Record source, seed and
TRAIN-support hashes must match the original DAY memories. Actual per-bank
E/k is validated and used for dispatch histograms and min/max active counts.
The macro-router initialization stream remains exactly the legacy E8 recipe,
independent of the body-arm constructor; no additional router search occurs.
"""
    path.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=(0, 1), default=0)
    parser.add_argument("--record", help="original DAY JSON, not a sleep report")
    parser.add_argument("--body-record", help="acquisition JSON defining body arm; source/seed/supports must match --record")
    parser.add_argument("--body-checkpoint", help="optional already-existing compatible frozen body")
    parser.add_argument("--out", help="new JSON under this review directory")
    parser.add_argument("--notes", help="new notes under this review directory")
    run(parser.parse_args())
