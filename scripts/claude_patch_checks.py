#!/usr/bin/env python3
"""Pre-race structural and numerical checks for the feedback-written patch.

Run with ``uv run --offline --no-project --python python3.12 --with torch
python -B scripts/claude_patch_checks.py --out artifacts/claude-patch-20260927/checks.json``.
No optimizer step is applied to the patch arm; the MAML smoke uses functional
parameters and one differentiable inner step only.
"""
from __future__ import annotations

import argparse
import hashlib
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.func import functional_call

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_patch_data as D  # noqa: E402
import claude_patch_net as P  # noqa: E402


def record(results: dict, name: str, passed: bool, **details: object) -> None:
    results["checks"][name] = {"passed": bool(passed), **details}


def tensors(item: object, device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return tuple(torch.tensor([part], device=device, dtype=torch.long)
                 for part in (item.tokens, item.slot, item.target))  # type: ignore[return-value]


def task_loss(logits: torch.Tensor, stop: torch.Tensor, slot: torch.Tensor,
              target: torch.Tensor) -> torch.Tensor:
    mask = slot.flatten(1).bool()
    answer = target.flatten(1)
    ce = F.cross_entropy(logits.float()[mask], answer[mask])
    exact = ((logits.argmax(-1) == answer) | ~mask).all(dim=1).float()
    return ce + 0.5 * F.binary_cross_entropy_with_logits(stop.float(), exact)


def group(name: str) -> str:
    if name.startswith("blocks."):
        parts = name.split(".")
        return f"blocks.{parts[1]}.{parts[2]}" if len(parts) > 2 else name
    return name.split(".")[0]


def count_table(net: P.Net) -> dict:
    parts: dict[str, int] = defaultdict(int)
    entries = []
    for name, parameter in net.named_parameters():
        count = parameter.numel()
        parts[group(name)] += count
        entries.append({"name": name, "shape": list(parameter.shape), "coefficients": count})
    learned = sum(parts.values())
    persistent = 2 * P.RANK * P.WIDTH if net.arm == "patch" else 0
    return {"parts": dict(sorted(parts.items())), "parameters": entries,
            "learned": learned, "persistent_A_B": persistent,
            "total": learned + persistent}


def build_cases(device: torch.device):
    # Distinct support and query inputs. Their shape stays small enough for the
    # full second-order graph while still exercising answer and stop heads.
    import random
    items = D.batch("sorting", random.Random(901277), 3, size=4)
    return [tensors(item, device) for item in items]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", choices=("mps", "cpu", "cuda"), default="mps")
    parser.add_argument("--checkpoint", type=Path, help="This experiment's own trained patch checkpoint")
    args = parser.parse_args()
    if args.device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but unavailable; pass --device cpu explicitly")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device(args.device)
    torch.manual_seed(20260927)
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(1)
    net = P.Net("patch").to(device=device, dtype=torch.float32)
    if args.checkpoint:
        saved = torch.load(args.checkpoint, map_location=device, weights_only=False)
        if saved.get("arm") != "patch":
            raise ValueError("expected this experiment's patch checkpoint")
        net.load_state_dict(saved["state"])
    loop = P.Net("loop").to(device=device, dtype=torch.float32)
    plain = P.Net("plain").to(device=device, dtype=torch.float32)
    autocast_active = torch.is_autocast_enabled(device.type)
    all_fp32 = all(p.dtype == torch.float32 for model in (net, loop, plain)
                   for p in model.parameters())
    result: dict = {"passed": False, "torch": torch.__version__, "device": str(device),
                    "dtype": "float32", "autocast": autocast_active,
                    "net_sha256": hashlib.sha256(Path(P.__file__).read_bytes()).hexdigest(),
                    "utc": subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"],
                                                   text=True).strip(), "checks": {}}
    record(result, "fp32_no_autocast", all_fp32 and not autocast_active,
           all_parameters_fp32=all_fp32, autocast_active=autocast_active)

    patch_table = count_table(net)
    loop_table = count_table(loop)
    plain_table = count_table(plain)
    ref = P.REFERENCE_COEFFICIENTS
    ratio = abs(patch_table["total"] - ref) / ref
    own_loop_ratio = abs(patch_table["total"] - loop_table["total"]) / loop_table["total"]
    plain_loop_ratio = abs(plain_table["total"] - loop_table["total"]) / loop_table["total"]
    result["weight_table"] = {"patch": patch_table, "loop": loop_table, "plain": plain_table,
                              "reference": ref, "difference": patch_table["total"] - ref,
                              "relative_difference": ratio,
                              "own_loop_difference": patch_table["total"] - loop_table["total"],
                              "own_loop_relative_difference": own_loop_ratio,
                              "plain_loop_relative_difference": plain_loop_ratio}
    record(result, "weight_budget", patch_table["total"] == P.coefficient_count(net)
           and loop_table["total"] == P.coefficient_count(loop)
           and plain_table["total"] == P.coefficient_count(plain)
           and patch_table["persistent_A_B"] == 4096 and ratio <= 0.02
           and own_loop_ratio <= 0.02 and plain_loop_ratio <= 0.02,
           total=patch_table["total"], persistent=patch_table["persistent_A_B"],
           relative_difference=ratio, own_loop_relative_difference=own_loop_ratio,
           plain_loop_relative_difference=plain_loop_ratio)

    cases = build_cases(device)
    support1, support2, query = cases
    initial = net.zero_patch(device=device)
    before = {name: p.detach().clone() for name, p in net.named_parameters()}
    p1 = net.write_support(*support1, initial, n_free=0, n_grad=2)
    p2 = net.write_support(*support2, p1, n_free=0, n_grad=2)
    weight_unchanged = all(torch.equal(before[name], p.detach()) for name, p in net.named_parameters())
    bounded = all(bool((x.abs() <= P.SLOT_LIMIT + 1e-7).all().item()) for x in (p1.A, p1.B, p2.A, p2.B))
    changed = bool((p2.A.abs().sum() + p2.B.abs().sum()).item() > 0)
    record(result, "frozen_support_write", weight_unchanged and bounded and changed,
           ordinary_weights_unchanged=weight_unchanged, patch_bounded=bounded,
           patch_nonzero=changed)

    # Loss is exclusively on a different query after both support writes.
    # The stop target comes from query correctness, never from a parameter sum.
    outs = net.loop_train(query[0], query[1], 0, 2, p2)
    loss = sum(task_loss(lg, stop, query[1], query[2]) for lg, stop in outs) / len(outs)
    net.zero_grad(set_to_none=True)
    loss.backward()
    matrices = {}
    for name, parameter in net.named_parameters():
        if parameter.ndim >= 2:
            grad = parameter.grad
            norm = float(grad.float().norm().item()) if grad is not None else 0.0
            matrices[name] = {"gradient_norm": norm,
                              "nonzero_finite": bool(norm > 0 and math.isfinite(norm))}
    gradients_pass = bool(matrices) and all(row["nonzero_finite"] for row in matrices.values())
    result["matrix_gradients"] = matrices
    record(result, "query_and_stop_matrix_gradients", gradients_pass,
           loss=float(loss.item()), nonzero=sum(row["nonzero_finite"] for row in matrices.values()),
           total=len(matrices))
    net.zero_grad(set_to_none=True)

    with torch.no_grad():
        tok, slot, _ = query
        none_outputs = net.loop_train(tok, slot, 0, 3, None)
        zero_outputs = net.loop_train(tok, slot, 0, 3, initial)
        max_delta = max(float((a - b).abs().max().item())
                        for pair_a, pair_b in zip(none_outputs, zero_outputs)
                        for a, b in zip(pair_a, pair_b))
    record(result, "zero_patch_matches_disabled", max_delta == 0.0, max_abs_difference=max_delta)

    # Query inference has no target argument and must leave the persistent state
    # untouched. Reusing p2 across two independent calls tests lifetime and
    # working-state reset without relying on output accuracy at random init.
    saved = (p2.A.detach().clone(), p2.B.detach().clone())
    with torch.no_grad():
        q_first = net.loop_rounds(query[0], query[1], 3, p2)
        net.loop_rounds(support1[0], support1[1], 2, p2)
        q_again = net.loop_rounds(query[0], query[1], 3, p2)
    persists = torch.equal(saved[0], p2.A) and torch.equal(saved[1], p2.B)
    isolated = all(torch.equal(a, b) for a, b in zip(q_first, q_again))
    record(result, "query_isolation_and_persistence", persists and isolated,
           state_unchanged=persists, repeat_query_identical=isolated)

    # Entrywise extreme patches bound each factor's Frobenius norm by one.
    # Alternating/random signs avoid cancellation against centered hidden states.
    # Check every hidden state over all 48 rounds on a larger 11x11 input.
    with torch.no_grad():
        tok = torch.randint(0, P.E.VOCAB, (1, 11, 11), device=device)
        slot = torch.randint(0, 2, (1, 11, 11), device=device)
        emb, (dr, dc) = net.embed(tok, slot)
        base_h = net.step(torch.zeros_like(emb), emb, dr, dc, None)
        ar = torch.arange(initial.A.numel(), device=device).reshape_as(initial.A)
        br = torch.arange(initial.B.numel(), device=device).reshape_as(initial.B)
        alternating = P.PatchState(torch.where(ar % 2 == 0, P.SLOT_LIMIT, -P.SLOT_LIMIT),
                                    torch.where(br % 3 == 0, P.SLOT_LIMIT, -P.SLOT_LIMIT))
        generator = torch.Generator(device="cpu").manual_seed(727)
        random_a = torch.randint(0, 2, initial.A.shape, generator=generator).to(device)
        random_b = torch.randint(0, 2, initial.B.shape, generator=generator).to(device)
        random_patch = P.PatchState((2 * random_a - 1) * P.SLOT_LIMIT,
                                     (2 * random_b - 1) * P.SLOT_LIMIT)
        patterns = {"all_positive": P.PatchState(torch.full_like(initial.A, P.SLOT_LIMIT),
                                                  torch.full_like(initial.B, P.SLOT_LIMIT)),
                    "alternating": alternating, "random_signs": random_patch}
        stress = {}
        for label, full in patterns.items():
            h = torch.zeros_like(emb)
            max_abs = 0.0
            finite = True
            for _ in range(P.MAX_ROUNDS):
                h = net.step(h, emb, dr, dc, full)
                logits, halt = net.read(h)
                finite = finite and all(bool(torch.isfinite(x).all().item()) for x in (h, logits, halt))
                max_abs = max(max_abs, float(h.abs().max().item()))
            effect = (net.step(base_h, emb, dr, dc, full)
                      - net.step(base_h, emb, dr, dc, None)).norm().item()
            norm_a, norm_b = float(full.A.norm().item()), float(full.B.norm().item())
            stress[label] = {"all_finite": finite, "max_abs_hidden": max_abs,
                             "nonzero_effect_norm": float(effect),
                             "frobenius_A": norm_a, "frobenius_B": norm_b,
                             "operator_bound": P.PATCH_EFFECT * norm_a * norm_b}
    stress_pass = all(v["all_finite"] and v["max_abs_hidden"] < 1e4
                      and v["frobenius_A"] <= 1 + 1e-5
                      and v["frobenius_B"] <= 1 + 1e-5
                      and v["operator_bound"] <= P.PATCH_EFFECT + 1e-5
                      for v in stress.values()) and any(v["nonzero_effect_norm"] > 0 for v in stress.values())
    record(result, "max_patch_48_round_stability", stress_pass,
           rounds=P.MAX_ROUNDS, input_shape=[11, 11], patterns=stress)

    # Functional one-step ordinary adaptation on the control. Differentiating
    # the post-update query loss checks that the inner update retains second
    # derivatives, as needed by the loop's episodic MAML control.
    loop.zero_grad(set_to_none=True)
    parameters = dict(loop.named_parameters())
    inner_out = functional_call(loop, parameters,
                                (support1[0], support1[1], 1, 2, None))[-1]
    inner_loss = task_loss(*inner_out, support1[1], support1[2])
    first = torch.autograd.grad(inner_loss, tuple(parameters.values()), create_graph=True)
    updated = {name: value - 1e-3 * grad for (name, value), grad in zip(parameters.items(), first)}
    outer_out = functional_call(loop, updated, (query[0], query[1], 1, 2, None))[-1]
    outer_loss = task_loss(*outer_out, query[1], query[2])
    second = torch.autograd.grad(outer_loss, tuple(parameters.values()), allow_unused=True)
    valid = sum(g is not None and bool(torch.isfinite(g).all().item()) and bool((g != 0).any().item())
                for g in second)
    record(result, "functional_second_order_adaptation", valid == len(parameters),
           finite_nonzero_gradients=valid, parameter_tensors=len(parameters),
           support_loss=float(inner_loss.item()), query_loss=float(outer_loss.item()))

    if args.checkpoint:
        result["checkpoint_sha256"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    result["passed"] = all(row["passed"] for row in result["checks"].values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "out": str(args.out),
                      "checks": {key: value["passed"] for key, value in result["checks"].items()}},
                     sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
