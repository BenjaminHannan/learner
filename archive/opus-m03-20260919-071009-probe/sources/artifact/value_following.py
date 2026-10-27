"""Binding probe, analysis of the SAVED records only (no model is loaded or run). Exploratory synthetic-vocabulary evidence.

Relevant swaps exchange the values of the gold card and its partner card (subject_swap: same_relation card;
relation_swap: same_person card) and leave every other card and the card order unchanged. So on x -> v:
  card-following  keeps attending to / answering from the same card TYPE
  value-following moves with the value (gold <-> partner)
Counts use the full-memory condition. Also: how well a fixed per-checkpoint preference over value words predicts the
answer in x (in-sample, descriptive only).
Run: $PY -B artifacts/opus-m03-20260919-071009/probe/value_following.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_binding_probe as P  # noqa: E402

started = time.perf_counter()
P.bootstrap()
TYPES = P.CARD_TYPES
PARTNER = {"subject_swap": "same_relation", "relation_swap": "same_person"}
out = {"label": "exploratory synthetic-vocabulary evidence; saved records only", "checkpoints": {}}
for name in P.CKPTS:
    recs = json.loads((HERE / "records" / f"{name}.json").read_text())["records"]
    att = {"card_follow": 0, "value_follow": 0, "neither": 0, "x_top_not_gold_or_partner": 0}
    closer = {"value_mapping_closer": 0, "card_mapping_closer": 0, "tie": 0}
    ans = {"card_follow": 0, "value_follow": 0, "neither": 0, "x_answer_not_gold_or_partner": 0}
    for r in recs:
        partner = PARTNER[r["kind_v"]]
        swap = {t: t for t in TYPES} | {"gold": partner, partner: "gold"}
        ax = {t: r["x"]["attention"][f"card_{t}"] for t in TYPES}
        av = {t: r["v"]["attention"][f"card_{t}"] for t in TYPES}
        top_x, top_v = max(ax, key=ax.get), max(av, key=av.get)
        if top_x not in ("gold", partner):
            att["x_top_not_gold_or_partner"] += 1
        else:
            att["card_follow" if top_v == top_x else "value_follow" if top_v == swap[top_x] else "neither"] += 1
        err_card = sum(abs(av[t] - ax[t]) for t in TYPES)
        err_value = sum(abs(av[swap[t]] - ax[t]) for t in TYPES)
        closer["tie" if abs(err_card - err_value) < 1e-9 else
               "value_mapping_closer" if err_value < err_card else "card_mapping_closer"] += 1
        src = r["x"]["source"]["full"]
        if src not in ("gold", partner):
            ans["x_answer_not_gold_or_partner"] += 1
        else:
            v_first = r["v"]["answers"]["full"][:1]
            same_card_value = r["v"]["card_values"][TYPES.index(src)]
            ans["card_follow" if v_first == [same_card_value] else
                "value_follow" if v_first == r["x"]["answers"]["full"][:1] else "neither"] += 1
    # fixed value preference: choice rate of each value word when present on the four x cards
    present, chosen = {}, {}
    for r in recs:
        values, first = r["x"]["card_values"], r["x"]["answers"]["full"][:1]
        for v in set(values):
            present[v] = present.get(v, 0) + 1
            chosen[v] = chosen.get(v, 0) + (first == [v])
    rate = {v: chosen[v] / present[v] for v in present}
    predicted = sum(r["x"]["answers"]["full"][:1] == [max(set(r["x"]["card_values"]), key=lambda v: rate[v])]
                    for r in recs)
    out["checkpoints"][name] = {"triplets": len(recs), "attention_top_card_x_to_v": att,
                                "attention_vector_x_to_v": closer, "answer_x_to_v": ans,
                                "value_preference": {"choice_rate_min": round(min(rate.values()), 3),
                                                     "choice_rate_max": round(max(rate.values()), 3),
                                                     "in_sample_top_present_value_predicts_x_answer": predicted,
                                                     "note": "in-sample (rates fitted on the same x questions)"}}
seconds = time.perf_counter() - started
(HERE / "value_following.json").write_text(json.dumps(out, indent=1))
P.charge("analysis", "value- vs card-following from saved records (no model)", seconds,
         script=str(Path(__file__).relative_to(ROOT)))
print(json.dumps(out, indent=1))
print(f"({seconds:.2f} s)")
