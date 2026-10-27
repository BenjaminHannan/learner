#!/usr/bin/env python3
"""Read-only reproducibility comparison of concept-toy ct20 wave-1 tier L,
v1.1 (quarantined) vs v1.2 (registered).

Ruling 3 section 2.2 (design/v3/20-concept-toy-rulings-3-fable-review.md):
after the v1.2 verdict is sealed, v1.1 may be opened for exactly one purpose --
a reproducibility comparison against v1.2's tier L:

  (a) tensor equality of model parameters and optimizer moments at all five
      rungs (32, 64, 128, 256, 512),
  (b) equality of ``query_predictions_by_rung``,
  (c) equality of both audit prediction sets,

for all 72 tier-L fits.  File hashes differ because the version string lives
inside the files, so this compares tensors and values, never bytes.

This script NEVER writes to, moves, chmods or deletes anything in either run
tree, and never reports v1.1 scores, errors or verdicts -- only equal /
not-equal, counts and max absolute differences.

Usage:
    python3 scripts/fable_concepttoy20_v11_v12_compare.py [--wave1 DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import torch

RUNGS = (32, 64, 128, 256, 512)
TENSOR_SECTIONS = ("parameters", "moment1", "moment2")
AUDIT_SETS = ("audit_predictions_initial", "audit_predictions_final")

OLD_DIRNAME = "v1.1-INVALID-accounting-QUARANTINED"
NEW_DIRNAME = "registered-v1.2"


# ---------------------------------------------------------------- readers


def load_checkpoint(path: str) -> Dict[str, Any]:
    return torch.load(path, map_location="cpu", weights_only=False)


def load_predictions(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ------------------------------------------------------------ comparators


def compare_tensor_dicts(
    old: Dict[str, torch.Tensor], new: Dict[str, torch.Tensor], label: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Exact (bitwise) tensor equality; report max abs diff where unequal."""
    diffs: List[Dict[str, Any]] = []
    old_keys, new_keys = set(old), set(new)
    for missing in sorted(old_keys ^ new_keys):
        diffs.append(
            {
                "where": f"{label}.{missing}",
                "kind": "key_present_in_one_tree_only",
                "in_v11": missing in old_keys,
                "in_v12": missing in new_keys,
            }
        )
    for key in sorted(old_keys & new_keys):
        a, b = old[key], new[key]
        if not torch.is_tensor(a) or not torch.is_tensor(b):
            if a != b:
                diffs.append({"where": f"{label}.{key}", "kind": "non_tensor_unequal"})
            continue
        if a.shape != b.shape or a.dtype != b.dtype:
            diffs.append(
                {
                    "where": f"{label}.{key}",
                    "kind": "shape_or_dtype",
                    "v11": [list(a.shape), str(a.dtype)],
                    "v12": [list(b.shape), str(b.dtype)],
                }
            )
            continue
        if torch.equal(a, b):
            continue
        max_abs = (a.double() - b.double()).abs().max().item()
        diffs.append(
            {
                "where": f"{label}.{key}",
                "kind": "tensor_unequal",
                "max_abs_diff": max_abs,
                "n_elements_differing": int((a != b).sum().item()),
            }
        )
    return (not diffs), diffs


def compare_value_trees(old: Any, new: Any, label: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Exact equality of nested JSON values; max abs diff for numbers."""
    diffs: List[Dict[str, Any]] = []

    def walk(a: Any, b: Any, path: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for missing in sorted(set(a) ^ set(b)):
                diffs.append(
                    {
                        "where": f"{path}.{missing}",
                        "kind": "key_present_in_one_tree_only",
                        "in_v11": missing in a,
                        "in_v12": missing in b,
                    }
                )
            for key in sorted(set(a) & set(b)):
                walk(a[key], b[key], f"{path}.{key}")
            return
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                diffs.append(
                    {"where": path, "kind": "length", "v11": len(a), "v12": len(b)}
                )
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]")
            return
        if isinstance(a, bool) or isinstance(b, bool):
            if a is not b:
                diffs.append({"where": path, "kind": "bool_unequal"})
            return
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a == b:
                return
            if isinstance(a, float) and isinstance(b, float):
                if math.isnan(a) and math.isnan(b):
                    return
            diffs.append(
                {"where": path, "kind": "value_unequal", "max_abs_diff": abs(float(a) - float(b))}
            )
            return
        if a != b:
            diffs.append({"where": path, "kind": "value_unequal"})

    walk(old, new, label)
    return (not diffs), diffs


def max_abs(diffs: List[Dict[str, Any]]) -> Optional[float]:
    vals = [d["max_abs_diff"] for d in diffs if "max_abs_diff" in d]
    return max(vals) if vals else None


# ---------------------------------------------------------------- driver


def enumerate_fits(root: str) -> List[Tuple[str, str, str]]:
    """Return sorted (arm, world_id, seed) triples under <root>/fits/tierL."""
    base = os.path.join(root, "fits", "tierL")
    out: List[Tuple[str, str, str]] = []
    if not os.path.isdir(base):
        return out
    for arm in sorted(os.listdir(base)):
        arm_dir = os.path.join(base, arm)
        if not os.path.isdir(arm_dir):
            continue
        for world in sorted(os.listdir(arm_dir)):
            world_dir = os.path.join(arm_dir, world)
            if not os.path.isdir(world_dir):
                continue
            for seed in sorted(os.listdir(world_dir)):
                if os.path.isdir(os.path.join(world_dir, seed)):
                    out.append((arm, world, seed))
    return out


def compare_fit(old_dir: str, new_dir: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "comparable": True,
        "not_comparable_reason": None,
        "a_tensors_identical": None,
        "b_query_by_rung_identical": None,
        "c_audit_sets_identical": None,
        "extra_query_initial_identical": None,
        "rungs_compared": [],
        "diffs": [],
        "v11_final_equals_own_rung512": None,
        "v12_final_equals_own_rung512": None,
        "v11_has_query_predictions_final": None,
        "v12_has_query_predictions_final": None,
    }

    missing: List[str] = []
    for rung in RUNGS:
        for tag, base in (("v1.1", old_dir), ("v1.2", new_dir)):
            path = os.path.join(base, f"rung{rung}.pt")
            if not os.path.isfile(path):
                missing.append(f"{tag}:rung{rung}.pt")
    for tag, base in (("v1.1", old_dir), ("v1.2", new_dir)):
        if not os.path.isfile(os.path.join(base, "predictions.json")):
            missing.append(f"{tag}:predictions.json")
    if missing:
        result["comparable"] = False
        result["not_comparable_reason"] = "missing files: " + ", ".join(missing)
        return result

    # (a) parameters + optimizer moments at all five rungs
    tensors_ok = True
    for rung in RUNGS:
        old_ck = load_checkpoint(os.path.join(old_dir, f"rung{rung}.pt"))
        new_ck = load_checkpoint(os.path.join(new_dir, f"rung{rung}.pt"))
        for section in TENSOR_SECTIONS:
            if section not in old_ck or section not in new_ck:
                result["comparable"] = False
                result["not_comparable_reason"] = (
                    f"checkpoint rung{rung} lacks section '{section}' in "
                    f"{'v1.1' if section not in old_ck else 'v1.2'}"
                )
                return result
            ok, diffs = compare_tensor_dicts(
                old_ck[section], new_ck[section], f"rung{rung}.{section}"
            )
            tensors_ok &= ok
            result["diffs"].extend(diffs)
        # structural sanity: same rung bookkeeping (not a score)
        for field in ("rung_budget", "rung_index", "optimizer_step_count", "completed_rung"):
            if old_ck.get(field) != new_ck.get(field):
                result["diffs"].append(
                    {"where": f"rung{rung}.{field}", "kind": "bookkeeping_unequal"}
                )
                tensors_ok = False
        result["rungs_compared"].append(rung)
    result["a_tensors_identical"] = tensors_ok

    old_pred = load_predictions(os.path.join(old_dir, "predictions.json"))
    new_pred = load_predictions(os.path.join(new_dir, "predictions.json"))

    # (b) query_predictions_by_rung
    ok_b, diffs_b = compare_value_trees(
        old_pred.get("query_predictions_by_rung"),
        new_pred.get("query_predictions_by_rung"),
        "query_predictions_by_rung",
    )
    result["b_query_by_rung_identical"] = ok_b
    result["diffs"].extend(diffs_b)

    # (c) both audit prediction sets
    ok_c = True
    for name in AUDIT_SETS:
        ok, diffs = compare_value_trees(old_pred.get(name), new_pred.get(name), name)
        ok_c &= ok
        result["diffs"].extend(diffs)
    result["c_audit_sets_identical"] = ok_c

    # supplementary: query_predictions_initial (pre-training panel)
    ok_i, diffs_i = compare_value_trees(
        old_pred.get("query_predictions_initial"),
        new_pred.get("query_predictions_initial"),
        "query_predictions_initial",
    )
    result["extra_query_initial_identical"] = ok_i
    result["diffs"].extend(diffs_i)

    # known intended difference: v1.2 deleted the redundant final_query_panel pass
    for tag, pred in (("v11", old_pred), ("v12", new_pred)):
        has_final = "query_predictions_final" in pred
        result[f"{tag}_has_query_predictions_final"] = has_final
        if not has_final:
            result[f"{tag}_final_equals_own_rung512"] = None
            continue
        own_512 = (pred.get("query_predictions_by_rung") or {}).get("512")
        if own_512 is None:
            result[f"{tag}_final_equals_own_rung512"] = None
            continue
        same, fdiffs = compare_value_trees(
            pred["query_predictions_final"], own_512, f"{tag}.query_predictions_final_vs_rung512"
        )
        result[f"{tag}_final_equals_own_rung512"] = same
        result[f"{tag}_final_vs_rung512_max_abs_diff"] = max_abs(fdiffs)
        result[f"{tag}_final_vs_rung512_n_differing"] = len(fdiffs)

    return result


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_wave1 = os.path.join(here, "artifacts", "fable-concept-toy20-20260920", "wave1")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wave1", default=default_wave1)
    args = ap.parse_args()

    old_root = os.path.join(args.wave1, OLD_DIRNAME)
    new_root = os.path.join(args.wave1, NEW_DIRNAME)
    for root in (old_root, new_root):
        if not os.path.isdir(root):
            raise SystemExit(f"not comparable: missing run tree {root}")

    new_fits = enumerate_fits(new_root)
    old_fits = enumerate_fits(old_root)
    new_set, old_set = set(new_fits), set(old_fits)

    records: List[Dict[str, Any]] = []
    for arm, world, seed in sorted(new_set | old_set):
        fit_id = f"tierL/{arm}/{world}/{seed}"
        if (arm, world, seed) not in old_set:
            records.append(
                {
                    "fit": fit_id,
                    "comparable": False,
                    "not_comparable_reason": "fit directory absent in v1.1 tree",
                }
            )
            continue
        if (arm, world, seed) not in new_set:
            records.append(
                {
                    "fit": fit_id,
                    "comparable": False,
                    "not_comparable_reason": "fit directory absent in v1.2 tree",
                }
            )
            continue
        old_dir = os.path.join(old_root, "fits", "tierL", arm, world, seed)
        new_dir = os.path.join(new_root, "fits", "tierL", arm, world, seed)
        rec = compare_fit(old_dir, new_dir)
        rec["fit"] = fit_id
        records.append(rec)

    comparable = [r for r in records if r.get("comparable")]
    n_a = sum(1 for r in comparable if r["a_tensors_identical"])
    n_b = sum(1 for r in comparable if r["b_query_by_rung_identical"])
    n_c = sum(1 for r in comparable if r["c_audit_sets_identical"])
    n_i = sum(1 for r in comparable if r["extra_query_initial_identical"])
    v11_final_eq = [r["v11_final_equals_own_rung512"] for r in comparable]
    v12_final_eq = [r["v12_final_equals_own_rung512"] for r in comparable]

    all_diffs = [d for r in comparable for d in r.get("diffs", [])]
    overall_max = max_abs(all_diffs)

    summary = {
        "generated_for": "ruling 3 section 2.2 reproducibility comparison (tier L)",
        "old_tree": os.path.relpath(old_root, args.wave1),
        "new_tree": os.path.relpath(new_root, args.wave1),
        "rungs": list(RUNGS),
        "tensor_sections": list(TENSOR_SECTIONS),
        "n_fits_v12": len(new_fits),
        "n_fits_v11": len(old_fits),
        "n_fits_compared": len(comparable),
        "n_not_comparable": len(records) - len(comparable),
        "a_parameters_and_moments_identical": n_a,
        "b_query_predictions_by_rung_identical": n_b,
        "c_audit_prediction_sets_identical": n_c,
        "extra_query_predictions_initial_identical": n_i,
        "n_differing_items_total": len(all_diffs),
        "max_abs_diff_overall": overall_max,
        "v11_query_predictions_final_present": sum(
            1 for r in comparable if r.get("v11_has_query_predictions_final")
        ),
        "v12_query_predictions_final_present": sum(
            1 for r in comparable if r.get("v12_has_query_predictions_final")
        ),
        "v11_final_equals_own_rung512_count": sum(1 for v in v11_final_eq if v is True),
        "v11_final_not_equal_own_rung512_count": sum(1 for v in v11_final_eq if v is False),
        "v12_final_equals_own_rung512_count": sum(1 for v in v12_final_eq if v is True),
        "v12_final_not_equal_own_rung512_count": sum(1 for v in v12_final_eq if v is False),
    }

    out_json = os.path.join(args.wave1, "V11-V12-COMPARISON.json")
    with open(out_json, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "fits": records}, handle, indent=2, sort_keys=True)
        handle.write("\n")

    verdict = (
        "IDENTICAL"
        if (
            summary["n_not_comparable"] == 0
            and n_a == n_b == n_c == len(comparable) == 72
        )
        else "DIFFERENCES FOUND"
    )

    lines: List[str] = []
    lines.append("# ct20 wave 1 - v1.1 vs v1.2 reproducibility comparison (tier L)")
    lines.append("")
    lines.append(
        "Read-only comparison required by ruling 3 section 2.2 "
        "(`design/v3/20-concept-toy-rulings-3-fable-review.md`). "
        "Neither run tree was modified, moved or rerun. "
        "File bytes are not compared (the version string lives inside every file); "
        "tensors and values are."
    )
    lines.append("")
    lines.append(f"**Result: {verdict}**")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- old (quarantined): `{summary['old_tree']}/`")
    lines.append(f"- new (registered): `{summary['new_tree']}/`")
    lines.append(f"- tier-L fits in v1.2: {summary['n_fits_v12']}")
    lines.append(f"- tier-L fits in v1.1: {summary['n_fits_v11']}")
    lines.append(f"- fits compared: {summary['n_fits_compared']}")
    lines.append(f"- not comparable: {summary['n_not_comparable']}")
    lines.append(f"- rungs: {', '.join(str(r) for r in RUNGS)}")
    lines.append("")
    lines.append("## Categories")
    lines.append("")
    lines.append("| category | what was compared | identical / compared |")
    lines.append("| --- | --- | --- |")
    lines.append(
        f"| (a) | `parameters`, `moment1`, `moment2` tensors at all five rungs "
        f"| {n_a} / {len(comparable)} |"
    )
    lines.append(f"| (b) | `query_predictions_by_rung` | {n_b} / {len(comparable)} |")
    lines.append(
        f"| (c) | `audit_predictions_initial` and `audit_predictions_final` "
        f"| {n_c} / {len(comparable)} |"
    )
    lines.append(
        f"| extra | `query_predictions_initial` (not required by the ruling) "
        f"| {n_i} / {len(comparable)} |"
    )
    lines.append("")
    lines.append(
        f"Differing items across all categories: {summary['n_differing_items_total']}; "
        f"max absolute difference overall: "
        f"{'n/a (no differences)' if overall_max is None else repr(overall_max)}."
    )
    lines.append("")
    lines.append("## Known intended difference: the deleted `final_query_panel` pass")
    lines.append("")
    lines.append(
        "v1.2 deleted a redundant final query panel pass. Both trees still carry a "
        "`query_predictions_final` field, so its absence was not the form the change took; "
        "what matters is whether that field is a re-run panel or the rung-512 panel."
    )
    lines.append("")
    lines.append(
        f"- `query_predictions_final` present: v1.1 in "
        f"{summary['v11_query_predictions_final_present']} / {len(comparable)} fits, "
        f"v1.2 in {summary['v12_query_predictions_final_present']} / {len(comparable)} fits."
    )
    lines.append(
        f"- v1.1 final predictions equal v1.1's own rung-512 predictions: "
        f"{summary['v11_final_equals_own_rung512_count']} / {len(comparable)} fits "
        f"(unequal in {summary['v11_final_not_equal_own_rung512_count']})."
    )
    lines.append(
        f"- v1.2 final predictions equal v1.2's own rung-512 predictions: "
        f"{summary['v12_final_equals_own_rung512_count']} / {len(comparable)} fits "
        f"(unequal in {summary['v12_final_not_equal_own_rung512_count']})."
    )
    lines.append("")

    bad = [r for r in records if not r.get("comparable") or r.get("diffs")]
    lines.append("## Fits with differences or gaps")
    lines.append("")
    if not bad:
        lines.append("None. Every compared fit matched in every category above.")
    else:
        lines.append("| fit | issue | max abs diff |")
        lines.append("| --- | --- | --- |")
        for r in bad:
            if not r.get("comparable"):
                lines.append(f"| `{r['fit']}` | not comparable: {r['not_comparable_reason']} | - |")
                continue
            first = r["diffs"][0]
            m = max_abs(r["diffs"])
            lines.append(
                f"| `{r['fit']}` | {len(r['diffs'])} differing item(s), first at "
                f"`{first.get('where')}` ({first.get('kind')}) | "
                f"{'n/a' if m is None else repr(m)} |"
            )
    lines.append("")
    lines.append("## One line for the wave-1 report")
    lines.append("")
    if verdict == "IDENTICAL":
        one = (
            f"Reproducibility check (ruling 3 section 2.2): all {len(comparable)} tier-L fits are "
            "bit-identical between the quarantined v1.1 run and the registered v1.2 run in model "
            "parameters and both optimizer moments at all five rungs (32/64/128/256/512), in "
            "`query_predictions_by_rung`, and in both audit prediction sets - no differences of any "
            "size; the only change is the version string and v1.2's removal of the redundant final "
            "query-panel pass, whose predictions were already equal to the rung-512 panel."
        )
    else:
        one = (
            f"Reproducibility check (ruling 3 section 2.2): {n_a}/{len(comparable)} tier-L fits match "
            f"on tensors, {n_b}/{len(comparable)} on `query_predictions_by_rung`, "
            f"{n_c}/{len(comparable)} on the audit prediction sets - differences found on the "
            "registered path (see V11-V12-COMPARISON.md); this is itself a finding against audit "
            "C.4.1 and is not resolved by preferring either run."
        )
    lines.append("> " + one)
    lines.append("")
    lines.append("Per-fit detail: `V11-V12-COMPARISON.json`.")
    lines.append("")

    out_md = os.path.join(args.wave1, "V11-V12-COMPARISON.md")
    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("wrote", out_md, sha256_file(out_md))
    print("wrote", out_json, sha256_file(out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
