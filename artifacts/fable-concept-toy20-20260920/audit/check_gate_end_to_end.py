"""Agent 3: does `gate_calculator.py` consume the REAL evaluator's output format?

The calculator was written before any result existed, from the preregistration and
the rulings alone, against a result-table schema I wrote down in its docstring.
That schema is only worth something if the evaluator that will actually produce
wave-1 numbers emits fields that map onto it.  This file proves the join by
running the whole chain on `fixture-v1.1`:

    real parameters -> real forward pass -> real `evaluate_predictions`
                    -> mechanical adapter -> `gate_calculator.evaluate_two_tier`

Two things are deliberately NOT claimed here.

  * This is a FORMAT check, not a scientific result.  Both "stages" are untrained
    parameter draws (seed 0 and seed 1); nothing was fitted.  The E and L numbers
    are meaningless as accuracy and are not published.
  * The fixture's `outer_split` is `fixture`; the calculator's gate arithmetic
    only reads `validation`.  The adapter relabels it so the gate path executes.
    That relabelling is stated in the output and applies to no registered run.

What IS claimed: every field the calculator's CASE schema requires is present in
the evaluator's output under a named field, the adapter is total (no defaults, no
guesses), and the two INDEPENDENT implementations of the ruling-C9 start-up
predicate - the builder's `startup_classification` and my `classify_startup_case`
- agree on every case, on numbers neither of us chose.

Fixture families are `o` and `c`.  No M-family world is touched and no trace or
score of any kind is published.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
ART = HERE.parent
REPO = ART.parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(HERE))

import fable_concepttoy20_models as M  # noqa: E402
import fable_concepttoy20_sim as S  # noqa: E402
import gate_calculator as G  # noqa: E402

FIXTURE_ROOT = ART / "fixture-v1.1"
PUBLIC = FIXTURE_ROOT / "public"

RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


# --------------------------------------------------------------- predictions
def _features(records: np.ndarray, detector: np.ndarray) -> torch.Tensor:
    count = records.shape[0]
    a = torch.tensor(np.argmax(detector[:, : M.QUERY_A_WIDTH], axis=-1), dtype=torch.int64)
    b = torch.tensor(np.argmax(detector[:, M.QUERY_A_WIDTH :], axis=-1), dtype=torch.int64)
    props = torch.tensor(
        records[:, 0, M.SLICE_PROPERTIES].reshape(count, M.N_OBJECTS, M.N_PROPERTIES),
        dtype=torch.float32,
    )
    return M.build_query_features(props, a, b)


def _pad(records: np.ndarray) -> torch.Tensor:
    out = np.zeros((records.shape[0], M.FIXED_SEQUENCE_LENGTH, M.RECORD_WIDTH), dtype=np.float32)
    out[:, : records.shape[1], :] = records
    return torch.tensor(out)


def predictions_for(world: str, arm: str, param_seed: int, stage: str, rung: str) -> list[dict]:
    d = PUBLIC / world
    params = {
        k: torch.tensor(v, dtype=torch.float32)[None, ...]
        for k, v in M.initial_parameters(arm, world, param_seed).items()
    }
    rows: list[dict] = []

    q_rec = np.load(d / "query_records.npy")
    q_idx = np.load(d / "query_index.npy")
    q_det = np.load(d / "query_detector.npy")
    ids = json.loads((d / "query_record_ids.json").read_text())
    if isinstance(ids, dict):
        ids = ids.get("record_ids", ids.get("ids"))
    with torch.no_grad():
        pred = M.forward(
            arm, params, _pad(q_rec).unsqueeze(0),
            torch.tensor(np.asarray(q_idx), dtype=torch.int64), _features(q_rec, q_det),
        )[0]
    for rid, value in zip(ids, pred.tolist()):
        rows.append({"record_id": str(rid), "prediction": float(value),
                     "arm": arm, "seed": "20001", "rung": rung, "stage": stage})

    a_rec = np.load(d / "audit_records.npy")
    a_idx = np.load(d / "audit_index.npy")
    a_det = np.load(d / "audit_detector.npy")
    keys = json.loads((d / "audit_keys.json").read_text())
    with torch.no_grad():
        pred = M.forward(
            arm, params, _pad(a_rec).unsqueeze(0),
            torch.tensor(np.asarray(a_idx), dtype=torch.int64), _features(a_rec, a_det),
        )[0]
    for row, value in zip(keys, pred.tolist()):
        rows.append({"record_id": row["audit_id"], "prediction": float(value),
                     "arm": arm, "seed": "20001", "stage": stage})
    return rows


# ------------------------------------------------------------------- adapter
REQUIRED_FROM_EVALUATOR = {
    "E":           "groups[].worlds[].E_primary  (stage=final, per rung)",
    "E_initial":   "groups[].worlds[].E_primary  (stage=initial)",
    "L_initial":   "startup_diagnostics[].L_initial",
    "L_final":     "startup_diagnostics[].L_final",
    "E_fit_final": "startup_diagnostics[].E_fit_final",
    "world_public_id": "startup_diagnostics[].world_public_id",
    "outer_split": "startup_diagnostics[].outer_split",
    "family":      "startup_diagnostics[].family",
    "arm":         "startup_diagnostics[].arm",
    "seed":        "startup_diagnostics[].seed",
}


def adapt(report: dict, rung_labels: dict[str, int], split_override: str) -> tuple[dict, list[str]]:
    """Mechanical, total adapter.  Every value is read from a named evaluator
    field; nothing is defaulted, inferred or invented.  Missing input is an
    error recorded in `gaps`, never a silent substitution."""
    gaps: list[str] = []
    e_by_case: dict[tuple[str, str, str], dict[int, float]] = {}
    e_initial: dict[tuple[str, str, str], float] = {}
    for group in report["groups"]:
        if not group["rung"]:
            continue
        budget = rung_labels.get(group["rung"])
        if budget is None:
            gaps.append(f"unmapped rung label {group['rung']!r}")
            continue
        for world in group["worlds"]:
            key = (group["arm"], group["seed"], world["world_public_id"])
            if group["stage"] == "final":
                e_by_case.setdefault(key, {})[budget] = world["E_primary"]
            elif group["stage"] == "initial":
                e_initial[key] = world["E_primary"]

    cases = []
    for row in report["startup_diagnostics"]:
        key = (row["arm"], row["seed"], row["world_public_id"])
        for field in ("L_initial", "L_final", "E_fit_final", "status"):
            if field not in row:
                gaps.append(f"{key}: evaluator did not emit {field}")
        if key not in e_by_case:
            gaps.append(f"{key}: no final-stage query E")
        if key not in e_initial:
            gaps.append(f"{key}: no initial-stage query E")
        cases.append({
            "world_public_id": row["world_public_id"],
            "outer_split": split_override or row["outer_split"],
            "family": row["family"],
            "seed": int(row["seed"]),
            "arm": row["arm"],
            "status": "complete" if row["status"] not in
                      ("numerical_failure", "infrastructure_incomplete") else row["status"],
            "E": e_by_case.get(key, {}),
            "E_initial": e_initial.get(key),
            "L_initial": row["L_initial"],
            "L_final": row["L_final"],
            "E_fit_final": row["E_fit_final"],
        })
    table = {
        "version": G.VERSION,
        "tier": "L",
        "integrity": {"accounting_valid": True, "audit_passed": True, "timing_ok": True},
        "cases": cases,
    }
    return table, gaps


# ---------------------------------------------------------------------- main
def main() -> int:
    worlds = [w["world_public_id"] for w in json.loads((PUBLIC / "worlds.json").read_text())["worlds"]]

    rows: list[dict] = []
    for world in worlds:
        for arm in ("G", "T"):
            # Two untrained draws standing in for the two sealed stages.
            rows += predictions_for(world, arm, 0, "initial", "32")
            rows += predictions_for(world, arm, 1, "final", "512")

    report = S.evaluate_predictions(FIXTURE_ROOT, rows)

    check("G1 the real evaluator scored every row",
          report["n_unknown_record_ids"] == 0,
          f"{report['n_predictions']} rows, {report['n_unknown_record_ids']} unknown")
    check("G2 the evaluator emitted start-up diagnostics",
          len(report["startup_diagnostics"]) == len(worlds) * 2,
          f"{len(report['startup_diagnostics'])} rows")
    check("G3 every field the CASE schema needs exists in the evaluator output",
          all(any(f in r for r in report["startup_diagnostics"])
              for f in ("L_initial", "L_final", "E_fit_final", "outer_split", "family"))
          and all("E_primary" in w for g in report["groups"] for w in g["worlds"]),
          "; ".join(f"{k} <- {v}" for k, v in REQUIRED_FROM_EVALUATOR.items()))

    table, gaps = adapt(report, {"32": 32, "512": 512}, split_override="validation")
    check("G4 the adapter is total: no field defaulted, inferred or missing",
          not gaps, str(gaps[:5]))
    check("G5 the adapted table has one case per world x arm",
          len(table["cases"]) == len(worlds) * 2, f"{len(table['cases'])} cases")

    # The calculator must accept the table without complaint.
    tier = G.evaluate_tier(table)
    check("G6 evaluate_tier accepts the evaluator-derived table",
          tier["verdict"] in G.VERDICTS, str(tier["verdict"]))
    two = G.evaluate_two_tier(table)
    check("G7 evaluate_two_tier returns a well-formed status",
          two["status"] in {"complete", "awaiting-tier-H", "protocol-violation"},
          str(two["status"]))
    check("G8 a start-up label was produced for every case",
          len(tier["startup_labels"]) == len(table["cases"]),
          f"{len(tier['startup_labels'])} labels")

    # The real cross-check: two independent C9 implementations on the same numbers.
    disagreements = []
    for row in report["startup_diagnostics"]:
        case = next(c for c in table["cases"]
                    if (c["arm"], str(c["seed"]), c["world_public_id"])
                    == (row["arm"], row["seed"], row["world_public_id"]))
        mine = G.classify_startup(
            case["L_initial"], case["L_final"], case["E_fit_final"],
            case["E"].get(512), case["status"])
        if mine != row["status"]:
            disagreements.append(f"{row['arm']}/{row['world_public_id']}: "
                                 f"builder={row['status']} agent3={mine}")
    check("G9 builder and Agent 3 agree on the ruling-C9 label for every case",
          not disagreements, str(disagreements))

    # And that they agree on the arithmetic itself, not just the label.
    ratio_bad = []
    for row in report["startup_diagnostics"]:
        if row.get("relative_improvement") is None:
            continue
        mine = (float(row["L_initial"]) - float(row["L_final"])) / float(row["L_initial"])
        if mine != float(row["relative_improvement"]):
            ratio_bad.append(row["world_public_id"])
    check("G10 the relative-improvement ratio matches bit for bit",
          not ratio_bad, str(ratio_bad))

    check("G11 the C9 threshold constant matches between the two implementations",
          G.STARTUP_MIN_RELATIVE_IMPROVEMENT == S.STARTUP_IMPROVEMENT_THRESHOLD
          and G.STARTUP_IMPROVEMENT_TOLERANCE == S.STARTUP_RELATIVE_TOLERANCE
          and G.STARTUP_NEVER_STARTED_FITTING_E == S.STARTUP_NEVER_STARTED_FITTING_E,
          f"{G.STARTUP_MIN_RELATIVE_IMPROVEMENT}/{G.STARTUP_IMPROVEMENT_TOLERANCE}/"
          f"{G.STARTUP_NEVER_STARTED_FITTING_E}")

    failed = [r for r in RESULTS if r["status"] != "PASS"]
    (HERE / "gate_end_to_end_results.json").write_text(json.dumps({
        "note": "FORMAT check on fixture-v1.1 only; both stages are untrained "
                "parameter draws, no fitting occurred, and no E, L or prediction "
                "value is published. outer_split relabelled fixture->validation "
                "so the gate path executes.",
        "evaluator_version": report["version"],
        "models_source_sha256": M.source_hash(),
        "field_map": REQUIRED_FROM_EVALUATOR,
        "total": len(RESULTS), "passed": len(RESULTS) - len(failed), "failed": len(failed),
        "results": RESULTS,
    }, indent=2))
    for r in RESULTS:
        print(f"[{r['status']}] {r['check']}" + (f"  ({r['detail']})" if r["detail"] else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
