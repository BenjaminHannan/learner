#!/usr/bin/env python3
"""Enumerate and cache exact, valid postfix labels for the small number puzzles.

This is training-data generation and diagnosis only; never use it at inference.
The subset DP keeps both operand orders, including for + and *, because their
postfix strings differ even when their rational values agree.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from fractions import Fraction
from pathlib import Path

import claude_rsn358a_envs as E


def _checker_item(nums: list[int], target: int) -> E.Item:
    return E.Item("numbers", len(nums), [], [], [], {"nums": nums, "target": target})


def solutions_for(nums: list[int], target: int) -> list[tuple[int, ...]]:
    """All distinct full binary postfix expressions that hit target exactly."""
    n = len(nums)
    if not 1 <= n <= 4:
        raise ValueError("the training-label enumerator supports 1-4 leaves")
    dp: dict[int, dict[Fraction, set[tuple[int, ...]]]] = {}
    for i, x in enumerate(nums):
        dp[1 << i] = {Fraction(x): {(E.VAL + x,)}}

    for width in range(2, n + 1):
        for mask in range(1, 1 << n):
            if mask.bit_count() != width:
                continue
            out: dict[Fraction, set[tuple[int, ...]]] = {}

            def add(value: Fraction, seq: tuple[int, ...]) -> None:
                out.setdefault(value, set()).add(seq)

            left = (mask - 1) & mask
            while left:
                right = mask ^ left
                if right and left < right:  # one unordered partition; both orientations below
                    for a, aseqs in dp[left].items():
                        for b, bseqs in dp[right].items():
                            for x in aseqs:
                                for y in bseqs:
                                    add(a + b, x + y + (E.OPS["+"],))
                                    add(a + b, y + x + (E.OPS["+"],))
                                    add(a * b, x + y + (E.OPS["*"],))
                                    add(a * b, y + x + (E.OPS["*"],))
                                    add(a - b, x + y + (E.OPS["-"],))
                                    add(b - a, y + x + (E.OPS["-"],))
                                    if b:
                                        add(a / b, x + y + (E.OPS["/"],))
                                    if a:
                                        add(b / a, y + x + (E.OPS["/"],))
                left = (left - 1) & mask
            dp[mask] = out

    solutions = sorted(dp[(1 << n) - 1].get(Fraction(target), set()))
    item = _checker_item(list(nums), target)
    for seq in solutions:
        assert E.check_numbers(item, seq), (nums, target, seq)
    return solutions


def cached_solutions(nums: list[int], target: int, cache_dir: Path) -> list[tuple[int, ...]]:
    """Persist code-checked labels under a caller-provided experiment cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / ("n" + "-".join(map(str, nums)) + f"-t{target}.json")
    if path.exists():
        seqs = [tuple(x) for x in json.loads(path.read_text(encoding="utf-8"))]
        item = _checker_item(list(nums), target)
        assert all(E.check_numbers(item, x) for x in seqs)
        return seqs
    seqs = solutions_for(nums, target)
    path.write_text(json.dumps(seqs, separators=(",", ":")) + "\n", encoding="utf-8")
    return seqs


def load_hand_pool(path: Path) -> tuple[list, list]:
    """Share the runner's raw hand cache without depending on torch."""
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["four"], data["three"]
    four, three = E.number_hands()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"four": four, "three": three}), encoding="utf-8")
    os.replace(tmp, path)
    return four, three


def audit_sample(out: Path) -> dict:
    four, three = load_hand_pool(out.parent.parent / "cache" / "number-hands-v1.json")
    train4, _ = E.split_four(four)
    rng = random.Random(20260927)
    picked = rng.sample(three, 6) + rng.sample(train4, 6)
    cache_dir = out.parent / "label-cache"
    rows = []
    start = time.perf_counter()
    for nums, target, stored in picked:
        t0 = time.perf_counter()
        seqs = cached_solutions(nums, target, cache_dir)
        old = tuple(E.VAL + v if kind == "n" else E.OPS[v] for kind, v in E.to_postfix(stored))
        assert old in seqs
        item = E.number_item(random.Random(0), nums, target, stored)
        alternative = next((x for x in seqs if x != old), None)
        invalid_mix = None
        if alternative:
            for i, v in enumerate(alternative):
                if v != old[i]:
                    mixed = old[:i] + (v,) + old[i + 1:]
                    if not E.check_numbers(item, mixed):
                        invalid_mix = {"slot": i, "tokens": mixed}
                        break
        rows.append({"nums": nums, "target": target, "stored_postfix": old,
                     "valid_postfix_count": len(seqs), "alternative_postfix": alternative,
                     "one_token_mix_invalid": invalid_mix,
                     "seconds": round(time.perf_counter() - t0, 3)})
    result = {"selection_seed": 20260927, "sample": "6 three-number practice pairs + 6 four-number practice hands",
              "total_practice_pairs": len(three) + len(train4), "three_count": len(three),
              "train_four_count": len(train4), "heldout_four_count": len(four) - len(train4),
              "all_have_alternative": all(r["valid_postfix_count"] > 1 for r in rows),
              "invalid_single_token_mix_count": sum(r["one_token_mix_invalid"] is not None for r in rows),
              "elapsed_seconds": round(time.perf_counter() - start, 3), "rows": rows}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def precompute_practice(root: Path) -> dict:
    four, three = load_hand_pool(root / "cache" / "number-hands-v1.json")
    train4, _ = E.split_four(four)
    cache_dir = root / "label-cache"
    start = time.perf_counter()
    counts = []
    for nums, target, stored in three + train4:
        seqs = cached_solutions(nums, target, cache_dir)
        old = tuple(E.VAL + v if kind == "n" else E.OPS[v] for kind, v in E.to_postfix(stored))
        assert old in seqs
        counts.append(len(seqs))
    counts.sort()
    result = {"practice_pairs": len(counts), "three_pairs": len(three), "four_hands": len(train4),
              "valid_postfix_min": counts[0], "valid_postfix_median": counts[len(counts) // 2],
              "valid_postfix_max": counts[-1], "pairs_with_multiple_answers": sum(x > 1 for x in counts),
              "seconds": round(time.perf_counter() - start, 3)}
    path = root / "diagnostics" / "label-cache-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--audit-out", type=Path)
    p.add_argument("--precompute-practice", type=Path)
    a = p.parse_args()
    if bool(a.audit_out) == bool(a.precompute_practice):
        p.error("choose exactly one of --audit-out or --precompute-practice")
    if a.audit_out:
        r = audit_sample(a.audit_out)
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=2))
    else:
        print(json.dumps(precompute_practice(a.precompute_practice), indent=2))
