#!/usr/bin/env python3
"""Blind recount from the sealed checks and, when available, raw practice rows.

Reads no summaries or markdown results. Run with cached uv Python 3.12, torch,
and numpy. This script never trains, changes a model, or reads a checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-patch-20260927"
sys.path.insert(0, str(ROOT / "scripts"))


def utc() -> str:
    return subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shape_count(shape: list[int]) -> int:
    if not shape or any(type(x) is not int or x < 1 for x in shape):
        raise ValueError(f"invalid parameter shape {shape!r}")
    return math.prod(shape)


def recount_weights(checks: dict) -> dict:
    # Model instantiation is a separate source of the parameter names and shapes.
    # The raw JSON supplies its own inventory. Compare them by name and shape.
    from claude_patch_net import Net

    table = checks["weight_table"]
    arms = {}
    for arm in ("patch", "loop", "plain"):
        net = Net(arm)
        instantiated = {name: list(param.shape) for name, param in net.named_parameters()}
        reported_rows = table[arm]["parameters"]
        duplicates = len(reported_rows) != len({r["name"] for r in reported_rows})
        reported = {r["name"]: r for r in reported_rows}
        count_mismatches = {
            name: {"reported": row["coefficients"], "shape_product": shape_count(row["shape"])}
            for name, row in reported.items() if row["coefficients"] != shape_count(row["shape"])
        }
        shape_mismatches = {
            name: {"reported": reported[name]["shape"], "instantiated": instantiated[name]}
            for name in reported.keys() & instantiated.keys()
            if reported[name]["shape"] != instantiated[name]
        }
        learned_raw = sum(shape_count(row["shape"]) for row in reported_rows)
        learned_instance = sum(shape_count(shape) for shape in instantiated.values())
        patch = net.zero_patch() if arm == "patch" else None
        persistent = sum(math.prod(t.shape) for t in patch) if patch else 0
        total = learned_instance + persistent
        raw_parts = defaultdict(int)
        for row in reported_rows:
            name = row["name"]
            part = ".".join(name.split(".")[:-1]) if name.endswith((".weight", ".bias")) else name
            if ".mlp." in part:
                part = part.split(".mlp.")[0] + ".mlp"
            if part.startswith("writer."):
                part = "writer"
            raw_parts[part] += shape_count(row["shape"])
        part_mismatches = {
            key: {"raw_shapes": raw_parts.get(key), "reported": table[arm]["parts"].get(key)}
            for key in raw_parts.keys() | table[arm]["parts"].keys()
            if raw_parts.get(key) != table[arm]["parts"].get(key)
        }
        valid = not (duplicates or count_mismatches or shape_mismatches or part_mismatches)
        valid &= reported.keys() == instantiated.keys()
        valid &= learned_raw == learned_instance == table[arm]["learned"]
        valid &= persistent == table[arm]["persistent_A_B"] and total == table[arm]["total"]
        arms[arm] = {
            "passed": bool(valid), "raw_learned": learned_raw,
            "instantiated_learned": learned_instance, "persistent_A_B": persistent,
            "total": total, "raw_parameter_rows": len(reported_rows),
            "missing_in_raw": sorted(instantiated.keys() - reported.keys()),
            "extra_in_raw": sorted(reported.keys() - instantiated.keys()),
            "duplicate_names": duplicates, "count_mismatches": count_mismatches,
            "shape_mismatches": shape_mismatches, "part_mismatches": part_mismatches,
        }
    loop_total = arms["loop"]["total"]
    reference = table["reference"]
    patch_total = arms["patch"]["total"]
    differences = {
        "patch_minus_loop": patch_total - loop_total,
        "patch_vs_loop_fraction": abs(patch_total - loop_total) / loop_total,
        "patch_minus_reference": patch_total - reference,
        "patch_vs_reference_fraction": abs(patch_total - reference) / reference,
        "plain_vs_loop_fraction": abs(arms["plain"]["total"] - loop_total) / loop_total,
    }
    comparison = {
        "difference": differences["patch_minus_reference"],
        "relative_difference": differences["patch_vs_reference_fraction"],
        "own_loop_difference": differences["patch_minus_loop"],
        "own_loop_relative_difference": differences["patch_vs_loop_fraction"],
        "plain_loop_relative_difference": differences["plain_vs_loop_fraction"],
    }
    reported_match = all(math.isclose(table[k], v, rel_tol=1e-10, abs_tol=1e-10)
                         for k, v in comparison.items())
    return {"passed": all(a["passed"] for a in arms.values()) and reported_match
            and differences["patch_vs_loop_fraction"] <= .02
            and differences["patch_vs_reference_fraction"] <= .02,
            "arms": arms, "differences": differences,
            "reported_comparisons_match": reported_match, "within_two_percent":
            differences["patch_vs_loop_fraction"] <= .02 and differences["patch_vs_reference_fraction"] <= .02}


def recount_gradients(checks: dict) -> dict:
    from claude_patch_net import Net

    # "Matrix" includes embedding tables and the two 8x9 relative-bias tables.
    expected = {name for name, p in Net("patch").named_parameters() if p.ndim == 2}
    raw = checks["matrix_gradients"]
    bad = {name: value for name, value in raw.items()
           if not isinstance(value.get("gradient_norm"), (int, float))
           or not math.isfinite(value["gradient_norm"]) or value["gradient_norm"] <= 0
           or value.get("nonzero_finite") is not True}
    counted = len(expected & raw.keys()) - len(expected & bad.keys())
    stated = checks["checks"]["query_and_stop_matrix_gradients"]
    return {"passed": expected == raw.keys() and not bad and
            counted == stated["nonzero"] == stated["total"] and stated["passed"] is True,
            "nonzero": counted, "total": len(expected),
            "missing": sorted(expected - raw.keys()), "extra": sorted(raw.keys() - expected),
            "bad": bad, "reported_nonzero": stated["nonzero"], "reported_total": stated["total"]}


def as_item(raw: dict):
    from claude_patch_data import KINDS

    src = raw.get("item", raw.get("input", raw.get("puzzle", raw)))
    if not isinstance(src, dict):
        raise ValueError("raw input/item is not an object")
    kind = src.get("env", src.get("kind", raw.get("kind", raw.get("env"))))
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    tokens = src.get("tokens")
    slot = src.get("slot", src.get("slots"))
    target = src.get("target")
    if tokens is None or slot is None or target is None:
        raise ValueError("raw row lacks tokens, slot, or target")
    if not tokens or any(len(row) != len(tokens[0]) for row in tokens):
        raise ValueError("input tokens are not rectangular")
    if len(slot) != len(tokens) or len(target) != len(tokens):
        raise ValueError("slot/target height mismatch")
    if any(len(row) != len(tokens[0]) for row in slot + target):
        raise ValueError("slot/target width mismatch")
    return SimpleNamespace(env=kind, size=src.get("size", len(tokens[0])),
                           tokens=tokens, slot=slot, target=target,
                           meta=src.get("meta", {}))


def prediction(raw: dict, item) -> list[int]:
    value = next((raw[k] for k in ("pred", "prediction", "predicted", "answer") if k in raw), None)
    if value is None and isinstance(raw.get("output"), dict):
        value = raw["output"].get("pred", raw["output"].get("prediction"))
    if value is None:
        raise ValueError("raw row lacks a prediction")
    if isinstance(value, dict):
        value = value.get("tokens", value.get("pred", value.get("prediction")))
    if not isinstance(value, list):
        raise ValueError("prediction is not a list")
    if value and isinstance(value[0], list):
        value = [x for row in value for x in row]
    if len(value) != len(item.tokens) * len(item.tokens[0]):
        raise ValueError("prediction length differs from input grid")
    if any(type(x) is not int for x in value):
        raise ValueError("prediction contains non-integer tokens")
    return value


def find_reported_count(obj, kind: str):
    """Find an explicit integer count for this kind within one result section."""
    if not isinstance(obj, dict):
        return None
    if kind in obj:
        value = obj[kind]
        if type(value) is int:
            return value
        if isinstance(value, dict):
            for key in ("correct", "right", "passed", "raw_correct", "count", "raw_count"):
                if type(value.get(key)) is int:
                    return value[key]
    for value in obj.values():
        if isinstance(value, dict):
            found = find_reported_count(value, kind)
            if found is not None:
                return found
    return None


def recount_raw(path: Path) -> dict:
    from claude_patch_data import check

    counts = defaultdict(lambda: {"correct": 0, "total": 0})
    errors = []
    with path.open() as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                item = as_item(row)
                pred = prediction(row, item)
                good = bool(check(item, pred))
                counts[item.env]["total"] += 1
                counts[item.env]["correct"] += int(good)
                for flag in ("right", "correct"):
                    if flag in row and bool(row[flag]) != good:
                        errors.append(f"line {line_no}: row {flag} flag differs from independent grade")
            except Exception as exc:
                errors.append(f"line {line_no}: {exc}")
    result_path = path.with_name("result.json")
    if not result_path.exists():
        result_path = path.with_name(path.name.replace("-raw.jsonl", "-result.json"))
    reported = json.loads(result_path.read_text()) if result_path.exists() else None
    section = path.name.split("-raw.jsonl")[0]
    reported_section = reported.get(section) if isinstance(reported, dict) else None
    result_counts = {kind: find_reported_count(reported_section, kind) for kind in counts}
    discrepancies = {kind: {"raw": c["correct"], "result_json": result_counts[kind]}
                     for kind, c in counts.items()
                     if reported is not None and result_counts[kind] != c["correct"]}
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path),
            "counts": dict(counts), "errors": errors,
            "result_json": str(result_path.relative_to(ROOT)) if result_path.exists() else None,
            "result_section": section, "result_counts": result_counts,
            "discrepancies": discrepancies,
            "passed": not errors and not discrepancies and bool(counts)}


def practice_gate(raw: list[dict]) -> dict:
    """Evaluate verify panels by arm and seed; missing arms remain untested."""
    from claude_patch_data import KINDS

    by_seed = defaultdict(lambda: defaultdict(dict))
    duplicate_panels = []
    for panel in raw:
        path = Path(panel["path"])
        if path.name != "verify-raw.jsonl":
            continue
        match = next((re.fullmatch(r"(patch|loop|loop_meta|plain)-(\d+)", part)
                      for part in path.parts if re.fullmatch(r"(patch|loop|loop_meta|plain)-(\d+)", part)), None)
        if match is None:
            continue
        arm, seed = match.groups()
        for kind, count in panel["counts"].items():
            if kind in by_seed[seed][arm]:
                duplicate_panels.append({"seed": seed, "arm": arm, "kind": kind})
            by_seed[seed][arm][kind] = dict(count)
    marks = {"sums": 285, "grids": 285, **{k: 270 for k in KINDS if k not in ("sums", "grids")}}
    # 285/270 are the fixed 95%/90% marks of 300. A panel of other size is
    # reported as untested for this gate, not silently scaled.
    thresholds, comparisons = {}, {}
    for seed, arms in by_seed.items():
        thresholds[seed], comparisons[seed] = {}, {}
        for arm, kinds in arms.items():
            thresholds[seed][arm] = {}
            for kind, count in kinds.items():
                thresholds[seed][arm][kind] = {"mark": marks[kind], "count": count["correct"],
                                               "total": count["total"],
                                               "passed": count["correct"] >= marks[kind] if count["total"] == 300 else None}
        for rival in ("loop", "loop_meta"):
            comparisons[seed][rival] = {}
            for kind in KINDS:
                p, r = arms.get("patch", {}).get(kind), arms.get(rival, {}).get(kind)
                if p is None or r is None or p["total"] != 300 or r["total"] != 300:
                    comparisons[seed][rival][kind] = {"status": "untested"}
                else:
                    gap = r["correct"] - p["correct"]
                    comparisons[seed][rival][kind] = {"status": "pass" if gap <= 9 else "fail",
                                                      "rival_minus_patch": gap, "allowed_gap": 9}
    required_arms = ("patch", "loop", "loop_meta", "plain")
    ready = len(by_seed) >= 2 and not duplicate_panels and all(
        all(all(arms.get(arm, {}).get(kind, {}).get("total") == 300 for kind in KINDS)
            for arm in required_arms) for arms in by_seed.values())
    passed = ready and all(
        thresholds[seed][arm][kind]["passed"] is True
        for seed in by_seed for arm in required_arms for kind in KINDS) and all(
        comparisons[seed][rival][kind]["status"] == "pass"
        for seed in by_seed for rival in ("loop", "loop_meta") for kind in KINDS)
    return {"status": "pass" if passed else "fail" if ready else "untested",
            "marks_of_300": marks,
            "by_seed": {seed: dict(arms) for seed, arms in by_seed.items()},
            "duplicate_panels": duplicate_panels, "thresholds": thresholds,
            "patch_within_9_of_both": comparisons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", type=Path, default=ART / "checks.json")
    parser.add_argument("--raw", action="append", type=Path, help="raw JSONL panel; repeat for several")
    args = parser.parse_args()
    checks = json.loads(args.checks.read_text())
    weights = recount_weights(checks)
    gradients = recount_gradients(checks)
    raw_paths = args.raw if args.raw is not None else sorted(ART.glob("**/*-raw.jsonl"))
    raw = [recount_raw(path) for path in raw_paths]
    gate = practice_gate(raw)
    evidence = {"utc": utc(), "sources": {"checks": str(args.checks.relative_to(ROOT)),
                "checks_sha256": digest(args.checks)}, "weights": weights,
                "matrix_gradients": gradients, "raw_panels": raw, "practice_gate": gate,
                "checks_recount_passed": weights["passed"] and gradients["passed"]}
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "BLIND-RECOUNT.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    lines = ["# Blind recount", "", f"UTC: {evidence['utc']}",
             f"Checks SHA-256: `{evidence['sources']['checks_sha256']}`", "",
             f"**Shown:** Weight inventory and instantiated shapes {'agree' if weights['passed'] else 'DISAGREE'}. "
             f"Patch {weights['arms']['patch']['total']:,}; loop {weights['arms']['loop']['total']:,}; "
             f"plain {weights['arms']['plain']['total']:,}. "
             f"Patch is {100 * weights['differences']['patch_vs_loop_fraction']:.3f}% from own loop.", "",
             f"**Shown:** {gradients['nonzero']} of {gradients['total']} matrix gradients have a finite, "
             f"positive norm in raw checks; inventory {'agrees' if gradients['passed'] else 'DISAGREES'}. "
             "This audits the recorded gradient norms; it does not rerun backpropagation.", ""]
    if raw:
        lines.append("**Shown:** Independently graded raw panels:")
        lines.append("")
        for panel in raw:
            score = ", ".join(f"{k} {v['correct']} of {v['total']}" for k, v in panel["counts"].items())
            lines.append(f"- `{panel['path']}`: {score or 'no graded rows'}; "
                         f"{'PASS' if panel['passed'] else 'DISCREPANCY'}")
        lines.extend(["", f"**{'Shown' if gate['status'] != 'untested' else 'Untested'}:** "
                      f"Practice gate {gate['status']}; patch comparisons use both loop and loop_meta "
                      "with a maximum gap of 9 of 300.", ""])
    else:
        lines.extend(["**Untested:** No practice or race raw panel is present. "
                      "This is absence of data, not a failed gate.", ""])
    lines.append("**Untested:** Race outcome and sleep absorption require later raw records.")
    (ART / "BLIND-RECOUNT.md").write_text("\n".join(lines) + "\n")
    print(f"checks_recount={evidence['checks_recount_passed']} practice_gate={gate['status']} raw_panels={len(raw)}")
    return 0 if evidence["checks_recount_passed"] and all(x["passed"] for x in raw) else 1


if __name__ == "__main__":
    raise SystemExit(main())
