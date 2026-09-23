"""Agent 3: verify the rulings-2 query-isolation requirement INDEPENDENTLY.

Rulings 2, public-interface ratification: "Each query branch must be predicted
independently.  No prediction may inspect another query branch, including its
paired counterpart; no cross-query state, batch statistics, pair detection, joint
fitting or prediction copying is allowed. ... Vectorized inference is allowed
only with independent lanes and the same results as separate inference."

The first-version text adds the auditor's instruction verbatim: "the auditor must
verify on fixtures that changing companions, ordering or batch partition leaves a
fixed query's prediction unchanged under the frozen numerical convention."

This file does that with the real forward pass and does NOT call the builder's
own `isolation_guard`, so it is an independent witness rather than a re-run of
their check.  Fixture families are o and c; no M world, no published score.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
ART = HERE.parent
sys.path.insert(0, str(ART.parents[1] / "scripts"))

import fable_concepttoy20_models as M  # noqa: E402

FIXTURE = ART / "fixture-v1.1"
PUBLIC = FIXTURE / "public"
RESULTS: list[dict] = []
DELTAS: dict[str, float] = {}


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})


def load(world: str):
    d = PUBLIC / world
    recs = np.load(d / "query_records.npy")
    idx = np.load(d / "query_index.npy")
    det = np.load(d / "query_detector.npy")
    ids = json.loads((d / "query_record_ids.json").read_text())
    if isinstance(ids, dict):
        ids = ids.get("record_ids", ids.get("ids"))
    n = recs.shape[0]
    padded = np.zeros((n, M.FIXED_SEQUENCE_LENGTH, M.RECORD_WIDTH), dtype=np.float32)
    padded[:, : recs.shape[1], :] = recs
    a = torch.tensor(np.argmax(det[:, : M.QUERY_A_WIDTH], axis=-1), dtype=torch.int64)
    b = torch.tensor(np.argmax(det[:, M.QUERY_A_WIDTH:], axis=-1), dtype=torch.int64)
    props = torch.tensor(recs[:, 0, M.SLICE_PROPERTIES].reshape(n, M.N_OBJECTS, M.N_PROPERTIES),
                         dtype=torch.float32)
    return (torch.tensor(padded), torch.tensor(np.asarray(idx), dtype=torch.int64),
            M.build_query_features(props, a, b), [str(x) for x in ids])


def predict(arm, params, records, endpoint, features, rows):
    """Predict exactly the given row subset, as one batch."""
    sel = torch.tensor(rows, dtype=torch.int64)
    with torch.no_grad():
        return M.forward(arm, params, records[sel].unsqueeze(0),
                         endpoint[sel], features[sel])[0]


def main() -> int:
    worlds = [w["world_public_id"]
              for w in json.loads((PUBLIC / "worlds.json").read_text())["worlds"]]
    world = worlds[0]
    records, endpoint, features, ids = load(world)
    n = records.shape[0]

    truth = json.loads((FIXTURE / "private" / world / "query_truth.json").read_text())
    by_id = {e["record_id"]: e for e in truth}
    # A real panel-3 pair: two branches of one statistical unit.
    pairs: dict = {}
    for e in truth:
        if e["panel"] == 3 and e["pair_key"]:
            pairs.setdefault(e["pair_key"], {})[e["branch"]] = ids.index(e["record_id"])
    pair = next(p for p in pairs.values() if "treated" in p and "control" in p)
    target, partner = pair["treated"], pair["control"]
    check("I0 a real panel-3 pair was located in the fixture",
          target != partner, f"treated=row{target} control=row{partner}")

    for arm in ("G", "T"):
        params = {k: torch.tensor(v, dtype=torch.float32)[None, ...]
                  for k, v in M.initial_parameters(arm, world, 0).items()}

        others = [i for i in range(n) if i not in (target, partner)]
        # --- 1. companion replacement, same batch size --------------------------
        batch_a = [target] + others[:15]
        batch_b = [target] + others[15:30]
        pa = predict(arm, params, records, endpoint, features, batch_a)[0]
        pb = predict(arm, params, records, endpoint, features, batch_b)[0]
        d = float((pa - pb).abs())
        DELTAS[f"{arm}/companion_replacement"] = d
        check(f"I1 arm {arm}: replacing all 15 companions leaves the target bit-identical",
              d == 0.0, f"delta={d!r}")

        # --- 2. reordering ------------------------------------------------------
        shuffled = list(reversed(batch_a))
        ps = predict(arm, params, records, endpoint, features, shuffled)
        d = float((pa - ps[shuffled.index(target)]).abs())
        DELTAS[f"{arm}/reordering"] = d
        check(f"I2 arm {arm}: reversing the batch order leaves the target bit-identical",
              d == 0.0, f"delta={d!r}")

        # --- 3. paired-branch replacement --------------------------------------
        with_partner = [target, partner] + others[:14]
        without = [target, others[20]] + others[:14]
        pw = predict(arm, params, records, endpoint, features, with_partner)[0]
        pn = predict(arm, params, records, endpoint, features, without)[0]
        d = float((pw - pn).abs())
        DELTAS[f"{arm}/paired_branch_replacement"] = d
        check(f"I3 arm {arm}: removing the paired counterpart leaves the target "
              f"bit-identical", d == 0.0, f"delta={d!r}")

        # --- 4. different partition, SAME batch size ---------------------------
        part_a = [target] + others[:31]
        part_b = [target] + others[31:62]
        d = float((predict(arm, params, records, endpoint, features, part_a)[0]
                   - predict(arm, params, records, endpoint, features, part_b)[0]).abs())
        DELTAS[f"{arm}/repartition_same_size"] = d
        check(f"I4 arm {arm}: a different partition at equal batch size is bit-identical",
              d == 0.0, f"delta={d!r}")

        # --- 5. CHANGED batch size ---------------------------------------------
        alone = predict(arm, params, records, endpoint, features, [target])[0]
        full = predict(arm, params, records, endpoint, features, list(range(n)))[target]
        d = float((alone - full).abs())
        DELTAS[f"{arm}/batch_size_1_vs_{n}"] = d
        check(f"I5 arm {arm}: changing the batch SHAPE moves the prediction only at "
              f"float32 rounding scale", d <= 1e-6, f"delta={d!r}")

        # Every row, not just one, under a batch-shape change.
        worst = 0.0
        full_all = predict(arm, params, records, endpoint, features, list(range(n)))
        for r in range(0, n, 8):
            solo = predict(arm, params, records, endpoint, features, [r])[0]
            worst = max(worst, float((solo - full_all[r]).abs()))
        DELTAS[f"{arm}/batch_shape_worst_over_rows"] = worst
        check(f"I6 arm {arm}: worst batch-shape delta across sampled rows is tiny",
              worst <= 1e-6, f"worst={worst!r}")

        # --- 6. the decisive negative control ----------------------------------
        # If the model really ignores companions, then poisoning a companion's
        # CONTENT (not just its identity) must also change nothing.
        poisoned = records.clone()
        poisoned[others[0]] = poisoned[others[0]] + 5.0
        with torch.no_grad():
            sel = torch.tensor(batch_a, dtype=torch.int64)
            pp = M.forward(arm, params, poisoned[sel].unsqueeze(0),
                           endpoint[sel], features[sel])[0][0]
        d = float((pa - pp).abs())
        DELTAS[f"{arm}/companion_content_poisoning"] = d
        check(f"I7 arm {arm}: corrupting a companion's CONTENT leaves the target "
              f"bit-identical", d == 0.0, f"delta={d!r}")

    failed = [r for r in RESULTS if r["status"] != "PASS"]
    (HERE / "isolation_results.json").write_text(json.dumps({
        "note": "Independent isolation witness on fixture-v1.1 with untrained "
                "parameters. No fitting, no published score.",
        "models_source_sha256": M.source_hash(),
        "deltas": DELTAS,
        "total": len(RESULTS), "passed": len(RESULTS) - len(failed), "failed": len(failed),
        "results": RESULTS}, indent=2))
    for r in RESULTS:
        print(f"[{r['status']}] {r['check']}" + (f"  ({r['detail']})" if r["detail"] else ""))
    print("\ndeltas:")
    for k, v in DELTAS.items():
        print(f"  {k}: {v!r}")
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
