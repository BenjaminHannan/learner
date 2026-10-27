"""Agent 3: verify ruling R1 on the evaluator by INDEPENDENT hand computation.

R1 fixes the gate's error definition:

    E_primary = (E_panel1_ordinary + E_panel2_composition) / 2

with panel 1 "the equal average of its three horizon-specific means (h=1,2,4)"
and explicitly NOT "a flat mean of its 6/5/5 targets"; panel 2 the equal average
of its 16 units; panels 3 and 4 separately scored guards that never enter primary
E; and V the evaluator-only normalizer from panels 1/2 with equal panel
weighting, population variance and a 0.05 floor.

This file recomputes all of that from the frozen private truth with plain
arithmetic and compares against `evaluate_predictions`.  No model is involved:
the "predictions" are a fixed deterministic sequence, so nothing here is an
accuracy measurement of any learner.  Fixture families are o and c; no M-family
world is touched and no score of any real arm is published.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ART = HERE.parent
sys.path.insert(0, str(ART.parents[1] / "scripts"))

import fable_concepttoy20_sim as S  # noqa: E402

FIXTURE = ART / "fixture-v1.1"
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def synthetic(record_id: str) -> float:
    """A deterministic pseudo-prediction.  Not a model output."""
    h = int.from_bytes(record_id.encode()[-8:], "big")
    return ((h % 20000) / 10000.0) - 1.0


def main() -> int:
    worlds = [w["world_public_id"]
              for w in json.loads((FIXTURE / "public" / "worlds.json").read_text())["worlds"]]
    truth = {w: json.loads((FIXTURE / "private" / w / "query_truth.json").read_text())
             for w in worlds}
    norm = json.loads((FIXTURE / "private" / "normalization.json").read_text())
    config = json.loads((FIXTURE / "private" / "world_config.json").read_text())

    rows = []
    for w in worlds:
        for e in truth[w]:
            rows.append({"record_id": e["record_id"], "prediction": synthetic(e["record_id"]),
                         "arm": "G", "seed": "20001", "rung": "512", "stage": "final"})
    report = S.evaluate_predictions(FIXTURE, rows)
    pred = {r["record_id"]: r["prediction"] for r in rows}
    scored = {w["world_public_id"]: w for w in report["groups"][0]["worlds"]}

    for w in worlds:
        entries = truth[w]
        cfg = config[w]
        v = float(norm[f"{cfg['outer_split']}/A/{cfg['family']}"]["V"])

        # ---- V, recomputed by hand: panels 1+2, population variance, 0.05 floor
        p12 = [e["noise_free_response"] for e in entries if e["panel"] in (1, 2)]
        v_hand = max(float(np.var(np.asarray(p12, dtype=np.float64))), 0.05)
        check(f"R1 V is the population variance of panels 1+2 with a 0.05 floor [{w}]",
              v_hand == v, f"hand={v_hand!r} evaluator={v!r} n={len(p12)}")

        def sq(es):
            return [(pred[e["record_id"]] - e["noise_free_response"]) ** 2 for e in es]

        # ---- panel 1: equal average of the three horizon means, NOT a flat mean
        p1 = [e for e in entries if e["panel"] == 1]
        by_h = {h: [e for e in p1 if e["horizon"] == h] for h in (1, 2, 4)}
        e_p1_hand = sum(float(np.mean(sq(by_h[h]))) for h in (1, 2, 4)) / 3.0 / v
        e_p1_flat = float(np.mean(sq(p1))) / v
        check(f"R1 E_panel1 is the equal average of the h=1/2/4 means [{w}]",
              math.isclose(e_p1_hand, scored[w]["E_panel1_ordinary"], rel_tol=0, abs_tol=1e-12),
              f"hand={e_p1_hand!r} evaluator={scored[w]['E_panel1_ordinary']!r}")
        check(f"R1 that is genuinely different from a flat 6/5/5 mean [{w}]",
              e_p1_hand != e_p1_flat,
              f"horizon-weighted={e_p1_hand!r} flat={e_p1_flat!r} "
              f"counts={[len(by_h[h]) for h in (1, 2, 4)]}")

        # ---- panel 2: equal average of its 16 units
        p2 = [e for e in entries if e["panel"] == 2]
        e_p2_hand = float(np.mean(sq(p2))) / v
        check(f"R1 E_panel2 is the equal average of its 16 units [{w}]",
              len(p2) == 16 and math.isclose(e_p2_hand, scored[w]["E_panel2_composition"],
                                             rel_tol=0, abs_tol=1e-12),
              f"hand={e_p2_hand!r} evaluator={scored[w]['E_panel2_composition']!r}")

        # ---- E_primary
        e_primary_hand = (e_p1_hand + e_p2_hand) / 2.0
        check(f"R1 E_primary = (E_panel1 + E_panel2)/2 [{w}]",
              math.isclose(e_primary_hand, scored[w]["E_primary"], rel_tol=0, abs_tol=1e-12),
              f"hand={e_primary_hand!r} evaluator={scored[w]['E_primary']!r}")

        # ---- panels 3 and 4 must not enter primary E
        check(f"R1 E_primary differs from E_all_targets, so panels 3/4 are excluded [{w}]",
              scored[w]["E_primary"] != scored[w]["E_all_targets"],
              f"E_primary={scored[w]['E_primary']!r} E_all={scored[w]['E_all_targets']!r}")

    # ---- operational: perturbing panels 3 and 4 must not move E_primary --------
    poisoned = []
    for r in rows:
        e = next(x for w in worlds for x in truth[w] if x["record_id"] == r["record_id"])
        poisoned.append({**r, "prediction": (r["prediction"] + 50.0
                                             if e["panel"] in (3, 4) else r["prediction"])})
    rep2 = S.evaluate_predictions(FIXTURE, poisoned)
    same = all(rep2["groups"][0]["worlds"][i]["E_primary"]
               == report["groups"][0]["worlds"][i]["E_primary"] for i in range(len(worlds)))
    check("R1 perturbing every panel-3/4 prediction leaves E_primary bit-identical", same)
    moved = any(rep2["groups"][0]["worlds"][i]["panel3_relevant_pairs"]
                != report["groups"][0]["worlds"][i]["panel3_relevant_pairs"]
                for i in range(len(worlds)))
    check("R1 the same perturbation DOES move the panel-3 guard, so it was real", moved)

    # ---- null E_primary on truncated predictions ------------------------------
    keep = [r for r in rows if not r["record_id"].endswith(("0", "1"))]
    rep3 = S.evaluate_predictions(FIXTURE, keep)
    w0 = rep3["groups"][0]["worlds"][0]
    check("R1 a truncated prediction set is reported incomplete",
          w0["complete"] is False,
          f"scored {w0['n_targets_scored']}/{w0['n_targets_expected']}")
    check("R1 an incomplete world yields E_primary = null, not a partial number",
          w0["E_primary"] is None, repr(w0["E_primary"]))
    check("R1 the partial count is still reported so the gap is visible",
          w0["n_targets_scored"] < w0["n_targets_expected"])

    # ---- and my calculator must treat that null as MISSING, never as 0.0 ------
    sys.path.insert(0, str(HERE))
    import gate_calculator as G  # noqa: E402
    case = {"world_public_id": "w", "outer_split": "validation", "family": "c",
            "seed": 20001, "arm": "G", "status": "complete",
            "E": {32: 0.3, 64: 0.3, 128: 0.3, 256: 0.3, 512: None},
            "E_initial": 10.0, "L_initial": 1.0, "L_final": 0.1, "E_fit_final": 0.1}
    check("R1 the gate calculator treats a null E_512 as missing, never as 0.0",
          G.is_learned_case(case)[0] is False
          and "missing" in G.is_learned_case(case)[1])

    failed = [r for r in RESULTS if r["status"] != "PASS"]
    (HERE / "r1_evaluator_results.json").write_text(json.dumps({
        "note": "Hand computation against the frozen fixture truth using deterministic "
                "synthetic predictions. No learner was fitted, scored or evaluated.",
        "evaluator_version": report["version"],
        "total": len(RESULTS), "passed": len(RESULTS) - len(failed), "failed": len(failed),
        "results": RESULTS}, indent=2))
    for r in RESULTS:
        print(f"[{r['status']}] {r['check']}" + (f"  ({r['detail']})" if r["detail"] else ""))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
