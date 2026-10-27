#!/usr/bin/env python3
"""Score the sealed Experiment 44 marks from the run JSONs.  Reporting only; written after
the seal, it reads run output and never trains anything.  Usage:
    python -B scripts/fable_reasoner44_score.py artifacts/fable-reasoner44-20260921/runs
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SEEDS = (4102, 4103, 4104)
WORDS = ("maternal_grandmother", "boss_of_spouse", "doctor_of_mothers_friend")
DEPTHS = (4, 6, 8, 10)


def mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def main() -> None:
    runs = Path(sys.argv[1])
    rows = []
    for seed in SEEDS:
        base = json.loads((runs / f"base-seed{seed}.json").read_text())
        s20 = json.loads((runs / f"sleep-seed{seed}-ep20.json").read_text())
        s50 = json.loads((runs / f"sleep-seed{seed}-ep50.json").read_text())
        f, b = base["fresh60"], base["big200"]
        h = base["honesty_fresh60"]
        r1 = f["hop1to3"] >= 0.99
        r2 = all(f[f"depth{d}"] >= 0.95 for d in DEPTHS)
        r3 = b["hop1to3"] >= 0.99 and all(b[f"depth{d}"] >= 0.95 for d in DEPTHS)
        r4 = h["unknown_rate"] >= 0.99 and h["confident_wrong"] == 0
        r5 = all(rep["words"][w]["true"]["installed"] and rep["words"][w]["true"]["fresh_accuracy"] >= 0.95
                 for rep in (s20, s50) for w in WORDS)
        r6 = s20["reuse_fresh60"] >= 0.95
        r7 = all(rep["words"][w][m]["base_unchanged"] for rep in (s20, s50) for w in WORDS for m in ("true",)) \
            and all(rep["words"][w]["true"]["reload_identical"] for rep in (s20, s50) for w in WORDS) \
            and s20["base_probe_unchanged_after_all"] and s50["base_probe_unchanged_after_all"] \
            and s20["combined_reload_identical"] and s50["combined_reload_identical"] \
            and not any(s20["words"][w]["random"]["installed"] for w in WORDS)
        rows.append({
            "seed": seed,
            "R1_hop1to3_fresh": f["hop1to3"], "R1": mark(r1),
            "R2_depths_fresh": [f[f"depth{d}"] for d in DEPTHS], "R2": mark(r2),
            "R3_big_hop1to3": b["hop1to3"], "R3_big_depths": [b[f"depth{d}"] for d in DEPTHS], "R3": mark(r3),
            "R4_unknown_rate": h["unknown_rate"], "R4_confident_wrong": h["confident_wrong"], "R4": mark(r4),
            "R5_ep20": {w: (s20["words"][w]["true"]["installed"], s20["words"][w]["true"]["fresh_accuracy"]) for w in WORDS},
            "R5_ep50": {w: (s50["words"][w]["true"]["installed"], s50["words"][w]["true"]["fresh_accuracy"]) for w in WORDS},
            "R5": mark(r5),
            "R6_reuse_fresh": s20["reuse_fresh60"], "R6_reuse_big": s20["reuse_big200"], "R6": mark(r6),
            "R7": mark(r7),
            "rec_noisy_installed": {w: s20["words"][w]["noisy"]["installed"] for w in WORDS},
            "rec_noisy_cv_best": {w: max(v["match"] for v in s20["words"][w]["noisy"]["cv_table"].values()) for w in WORDS},
            "rec_random_cv_best": {w: max(v["match"] for v in s20["words"][w]["random"]["cv_table"].values()) for w in WORDS},
            "rec_routed_chain": {w: s20["words"][w]["true"]["routed_chain"] for w in WORDS},
            "rec_chosen_updates_ep20": {w: s20["words"][w]["true"]["chosen_updates"] for w in WORDS},
            "rec_distinct_people_ep50": {w: s50["words"][w]["true"]["distinct_people"] for w in WORDS},
            "rec_word_big200_ep20": {w: s20["words"][w]["true"].get("big200_accuracy") for w in WORDS},
            "rec_seconds": {"base": base["train_seconds"], "sleep20": s20["sleep_seconds"], "sleep50": s50["sleep_seconds"]},
            "rec_params": {"base": base["trainable_parameters_base"], "per_word": base["trainable_parameters_per_word"]},
            "rec_routing_weight_min": min(base["routing_weight"].values()),
            "rec_routing_is_identity": base["routing_is_identity"],
            "rec_honesty_big200": base["honesty_big200"],
        })
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
