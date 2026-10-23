"""W2 no-learning baselines on creative dev (CPU, reads creative/data/c2/dev.jsonl only, never test.jsonl): python -m pytest v1/tests/test_creative_baselines.py"""
import json
from pathlib import Path

from creative import fewshot
from v1.creative_baselines import creative_baselines

DEV = Path(__file__).resolve().parent.parent.parent / "creative/data/c2/dev.jsonl"


def _rows():
    return [json.loads(l) for l in DEV.read_text().splitlines() if l.strip()]


def test_values_on_dev():
    rows = _rows()
    assert len(rows) == 256
    r = creative_baselines(rows)
    assert r["all"]["best_fixed_program"] == 51 / 256
    b = r["all"]["blind_first_fit_right"]
    assert b["1"] == 0.0
    assert b["32"] == 100 / 256                     # 0.390625 (about 0.391)
    assert b["4"] == 51 / 256                       # measured: 0.199, not the 0.0 the audit's pass mark wrote down
    assert r["parameterised"]["n"] == 154
    assert r["parameterised"]["blind_first_fit_right"]["1"] == 0.0
    assert r["proposed_W2_threshold"] == max(51 / 256, 0.0) + 0.10
    assert abs(r["proposed_W2_threshold"] - 0.2992) < 5e-5
    assert creative_baselines(rows) == r            # deterministic


def test_constant_square_prediction_scores_like_old_mark():
    rows = _rows()
    right = sum(str(fewshot.parse(r["prompt"])["q"] ** 2) in r["accepted"] for r in rows)
    assert right == 51 and abs(right / len(rows) - 0.1992) < 5e-5   # an input-blind "answer q*q" sits 0.08 points under the flat 20% mark
