#!/usr/bin/env python3
"""Classify saved numbers4 predictions without loading a model or solving puzzles.

Requires a --details evaluation JSON and its original four-number panel JSONL.
The saved 48 round predictions are used only to measure an oracle upper bound;
the model's own v2 stop remains the scored prediction.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402

CATEGORIES = ("invalid_token", "malformed_postfix_stack", "wrong_input_number_multiset",
              "division_by_zero", "wrong_arithmetic_value", "valid_expression")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(prediction, item):
    """Classify one flattened output using exact rational postfix arithmetic."""
    width = len(item.tokens[0])
    k = len(item.meta["nums"])
    row = prediction[2 * width:2 * width + 2 * k - 1]
    toks, numbers = [], []
    for t in row:
        if type(t) is not int:
            return "invalid_token", None
        if E.VAL <= t < E.VAL + 100:
            v = t - E.VAL
            toks.append(("n", v))
            numbers.append(v)
        elif t in E.OP_OF:
            toks.append(("o", E.OP_OF[t]))
        else:
            return "invalid_token", None
    depth = 0
    for kind, _ in toks:
        depth += 1 if kind == "n" else -1
        if depth < 1:
            return "malformed_postfix_stack", None
    if depth != 1:
        return "malformed_postfix_stack", None
    if sorted(numbers) != sorted(item.meta["nums"]):
        return "wrong_input_number_multiset", None
    st = []
    for kind, value in toks:
        if kind == "n":
            st.append(Fraction(value))
            continue
        y, x = st.pop(), st.pop()
        if value == "+":
            st.append(x + y)
        elif value == "-":
            st.append(x - y)
        elif value == "*":
            st.append(x * y)
        else:
            if y == 0:
                return "division_by_zero", None
            st.append(x / y)
    answer = st[0]
    return ("valid_expression" if answer == item.meta["target"] else
            "wrong_arithmetic_value"), str(answer)


def stop_round(predictions, halts):
    return next((r for r in range(2, len(predictions))
                 if halts[r] > .5 and predictions[r] == predictions[r - 1] == predictions[r - 2]),
                len(predictions) - 1)


def load_item(line):
    d = json.loads(line)
    if d.get("env") != "numbers" or d.get("size") != 4:
        raise ValueError("only a numbers4 panel is permitted")
    return E.Item(d["env"], d["size"], d["tokens"], d["slot"], d["target"], d["meta"])


def diagnose(ev, panel, max_examples):
    if ev.get("panel_sha256") != sha256(panel):
        raise ValueError("evaluation panel SHA-256 does not match original panel")
    items = [load_item(line) for line in Path(panel).read_text(encoding="utf-8").splitlines() if line.strip()]
    records = (ev.get("scores") or {}).get("items")
    if not isinstance(records, list) or len(records) != len(items):
        raise ValueError("evaluation lacks one --details record per panel item")
    categories = collections.Counter()
    own_stop = collections.Counter()
    exact_valid = collections.Counter()
    oracle_valid = oracle_before_stop = own_valid = exact = 0
    examples = {name: [] for name in CATEGORIES}
    for i, (item, record) in enumerate(zip(items, records)):
        trace = record.get("round_predictions")
        halts = record.get("round_halt_probabilities")
        if not isinstance(trace, list) or not isinstance(halts, list) or len(trace) != 48 or len(halts) != 48:
            raise ValueError(f"item {i}: missing 48-round prediction/halt trace")
        width = len(item.tokens[0])
        for r, row in enumerate(trace):
            if not isinstance(row, list) or len(row) != 3 * width:
                raise ValueError(f"item {i}, round {r + 1}: malformed prediction length")
        if any(not isinstance(q, (float, int)) or not math.isfinite(q) or not 0 <= q <= 1 for q in halts):
            raise ValueError(f"item {i}: malformed halt probability")
        chosen = stop_round(trace, halts)
        if record.get("index") != i or record.get("kind") != "numbers" or record.get("size") != 4 or \
                record.get("stop") != chosen + 1 or record.get("prediction") != trace[chosen]:
            raise ValueError(f"item {i}: saved own-stop record differs from v2 trace")
        category, value = classify(trace[chosen], item)
        grid = [trace[chosen][r * width:(r + 1) * width] for r in range(3)]
        checker_valid = bool(E.check(item, grid))
        if checker_valid != (category == "valid_expression") or record.get("valid") is not checker_valid:
            raise ValueError(f"item {i}: exact-arithmetic category and existing checker disagree")
        stored = all(trace[chosen][r * width + c] == item.target[r][c]
                     for r in range(3) for c in range(width) if item.slot[r][c])
        if record.get("exact_stored") is not stored:
            raise ValueError(f"item {i}: exact-stored field mismatch")
        round_valid = []
        for r, pred in enumerate(trace):
            cat, _ = classify(pred, item)
            valid = cat == "valid_expression"
            if valid != bool(E.check(item, [pred[j * width:(j + 1) * width] for j in range(3)])):
                raise ValueError(f"item {i}, round {r + 1}: checker reconciliation failed")
            round_valid.append(valid)
        categories[category] += 1
        own_stop[chosen + 1] += 1
        exact_valid[f"exact={str(stored).lower()},valid={str(checker_valid).lower()}"] += 1
        own_valid += checker_valid
        exact += stored
        oracle_valid += any(round_valid)
        oracle_before_stop += any(round_valid[:chosen + 1])
        if len(examples[category]) < max_examples:
            examples[category].append({"index": i, "numbers": item.meta["nums"],
                                       "target": item.meta["target"], "stop": chosen + 1,
                                       "postfix_tokens": trace[chosen][2 * width:2 * width + 7],
                                       "value": value})
    scores = ev["scores"]
    if scores.get("n") != len(items) or scores.get("valid") != own_valid or scores.get("exact_stored") != exact:
        raise ValueError("stored evaluation summary disagrees with independent recount")
    return {"n": len(items), "panel_sha256": sha256(panel),
            "own_stop_valid": own_valid, "any_valid_round_oracle": oracle_valid,
            "any_valid_through_own_stop": oracle_before_stop,
            "exact_stored": exact, "categories_at_own_stop": {k: categories[k] for k in CATEGORIES},
            "exact_stored_by_validity": dict(sorted(exact_valid.items())),
            "own_stop_round_histogram": dict(sorted(own_stop.items())), "examples": examples,
            "claims": {"SHOWN": "counts on this saved numbers4 panel only",
                       "SUGGESTED": "error categories may point to a training bottleneck",
                       "UNTESTED": "effect of any proposed training change or transfer to five numbers"}}


def selftest():
    item = E.Item("numbers", 4, [[26, 27, 28, 29, 0, 0, 0], [49, 0, 0, 0, 0, 0, 0],
                                  [1] * 7], [[0] * 7, [0] * 7, [1] * 7],
                  [[0] * 7, [0] * 7, [26, 27, 21, 28, 23, 29, 21]],
                  {"nums": [1, 2, 3, 4], "target": 24})
    def pred(row):
        return [0] * 14 + row
    assert classify(pred([21, 26, 27, 28, 29, 21, 21]), item)[0] == "malformed_postfix_stack"
    assert classify(pred([26, 27, 21, 28, 23, 29, 21]), item)[0] == "wrong_arithmetic_value"
    assert classify(pred([26, 27, 21, 28, 23, 0, 21]), item)[0] == "invalid_token"
    assert classify(pred([26, 27, 21, 28, 23, 30, 21]), item)[0] == "wrong_input_number_multiset"
    assert classify(pred([27, 26, 28, 21, 29, 22, 24]), item)[0] == "division_by_zero"
    assert classify(pred([26, 28, 21, 27, 29, 21, 23]), item)[0] == "valid_expression"
    assert E.check(item, [[0] * 7, [0] * 7, [26, 28, 21, 27, 29, 21, 23]])
    assert stop_round([[0], [0], [0]], [0, 0, .9]) == 2
    print("diagnosis selftest passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval", type=Path, help="one --details numbers4 eval JSON")
    ap.add_argument("--panel", type=Path, help="original numbers4 JSONL; defaults to eval.panel")
    ap.add_argument("--out", type=Path, help="output diagnostic JSON")
    ap.add_argument("--max-examples", type=int, default=2)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if args.eval is None or args.out is None:
        ap.error("--eval and --out are required")
    ev = json.loads(args.eval.read_text(encoding="utf-8"))
    panel = args.panel or Path(ev["panel"])
    result = diagnose(ev, panel, args.max_examples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("n", "own_stop_valid", "any_valid_round_oracle", "exact_stored")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
