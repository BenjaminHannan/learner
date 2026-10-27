#!/usr/bin/env python3
"""Independent, inference-free recount of registered small-puzzle evaluations.

Input: ROOT/registered/{baseline,candidate}-sSEED/{config.json,
train_summary.json,train_log.jsonl,final.pt,tests.json.gz}.  tests.json.gz maps the
five panel names to the JSON emitted by codex_numbers_20260927_run.py eval
with --details. Candidate runs also require tests-wiped.json.gz for the same
panels, checkpoints, and item order. Each eval names its original JSONL panel, which must still
exist. This script reads predictions and calls the existing checker; it never
loads a model or makes predictions.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402

PANELS = {"numbers4": ("numbers", 4), "numbers5": ("numbers", 5),
          "sums4": ("sums", 4), "grids5": ("grids", 5),
          "numbers5_old": ("numbers", 5)}
REPO = Path(__file__).resolve().parent.parent
LEGACY = REPO / "artifacts/claude-rsn358i-20260926/tests"
EXPECTED_PATHS = {"numbers4": LEGACY / "numbers4.jsonl",
                  "sums4": LEGACY / "sums4.jsonl",
                  "grids5": LEGACY / "grids5.jsonl",
                  "numbers5_old": LEGACY / "numbers5.jsonl"}
COMMON_CONFIG = ("seed", "steps", "batch", "width", "layers", "heads", "latin_pool",
                 "lr", "warmup", "train_rounds", "grad_rounds", "test_rounds",
                 "device", "dtype", "torch", "arm", "fixed_env", "unused_env_rows",
                 "unused_env_weights", "cache_hashes", "script_sha256", "source_hashes")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(path.read_text(encoding="utf-8"))


def checked(condition, problems, message):
    if not condition:
        problems.append(message)
    return bool(condition)


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def check_registered_settings(cfg, registered, arm, seed, problems):
    """Compare one saved run with the pushed experiment's training settings."""
    label = f"{arm}-s{seed}"
    train = registered.get("train") or {}
    for key in ("steps", "batch", "width", "layers", "heads", "latin_pool",
                "lr", "warmup", "log_every"):
        checked(key in train and same(cfg.get(key), train.get(key)), problems,
                f"{label}: setting {key} differs from registered EXPERIMENT")
    for key, expected in (("seed", seed), ("variant", arm), ("device", registered.get("device")),
                          ("dtype", "float32"), ("torch", registered.get("torch_version")),
                          ("fixed_env", 0), ("dev_holdout", 0)):
        checked(same(cfg.get(key), expected), problems,
                f"{label}: setting {key} differs from registered EXPERIMENT")


def check_registered_seeds(discovered, registered, problems):
    expected = registered.get("seeds")
    valid = (isinstance(expected, list) and len(expected) >= 4 and
             all(type(x) is int for x in expected) and len(set(expected)) == len(expected))
    checked(valid, problems, "EXPERIMENT.seeds must contain at least four distinct integers")
    if valid:
        checked(set(discovered) == set(expected) and len(discovered) == len(expected), problems,
                "registered run directories do not exactly match EXPERIMENT.seeds")
    return expected if valid else []


def panel_path(root, stated):
    p = Path(stated)
    if p.is_absolute():
        return p
    candidates = (root / p, Path(__file__).resolve().parent.parent / p)
    return next((x for x in candidates if x.is_file()), candidates[0])


def stop_round(predictions, halts):
    return next((r for r in range(2, len(predictions))
                 if halts[r] > .5 and predictions[r] == predictions[r - 1] == predictions[r - 2]),
                len(predictions) - 1)


def recount_panel(root, run, name, ev, cfg, ck_hash, expected_hashes, problems):
    label = f"{run}/{name}"
    if not isinstance(ev, dict):
        problems.append(f"{label}: missing evaluation")
        return None
    path = panel_path(root, ev.get("panel", ""))
    expected_path = EXPECTED_PATHS.get(name, root / "panels/numbers5.jsonl")
    checked(path.resolve() == expected_path.resolve(), problems,
            f"{label}: source panel path differs from registered path")
    if not checked(path.is_file(), problems, f"{label}: panel file missing: {path}"):
        return None
    checked(ev.get("panel_sha256") == digest(path), problems,
            f"{label}: panel SHA-256 mismatch")
    checked(digest(path) == expected_hashes.get(name), problems,
            f"{label}: panel differs from registered panel hash")
    checked(ev.get("checkpoint_sha256") == ck_hash, problems,
            f"{label}: checkpoint SHA-256 mismatch")
    checked(same(ev.get("config"), cfg), problems, f"{label}: evaluation config mismatch")
    poison = ev.get("poison") or {}
    checked(poison.get("rounds") == cfg.get("test_rounds") and
            set(poison.get("tested_kinds", [])) == set(E.ENVS) and
            all(poison.get(k) is True for k in
                ("logits_equal", "predictions_equal", "raw_halts_equal")),
            problems, f"{label}: hidden-kind poison test absent or failed")
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        items = [json.loads(line) for line in lines if line.strip()]
    except (ValueError, TypeError) as exc:
        problems.append(f"{label}: invalid panel JSON: {exc}")
        return None
    expected_env, expected_size = PANELS[name]
    checked(len(items) == 300, problems, f"{label}: expected 300 panel items, got {len(items)}")
    scores = ev.get("scores") or {}
    records = scores.get("items")
    if not checked(isinstance(records, list) and len(records) == len(items), problems,
                   f"{label}: missing one prediction per panel item"):
        return None
    valid = exact = 0
    for i, (raw, record) in enumerate(zip(items, records)):
        prefix = f"{label} item {i}"
        try:
            item = E.Item(raw["env"], raw["size"], raw["tokens"], raw["slot"],
                          raw["target"], raw["meta"])
            checked(item.env == expected_env and item.size == expected_size, problems,
                    f"{prefix}: wrong kind/size")
            checked(record.get("index") == i and record.get("kind") == item.env and
                    record.get("size") == item.size, problems,
                    f"{prefix}: record identity mismatch")
            stop = record.get("stop")
            rounds = cfg.get("test_rounds")
            checked(type(stop) is int and type(rounds) is int and 3 <= stop <= rounds, problems,
                    f"{prefix}: own stop outside 3..{rounds}")
            pred = record.get("prediction")
            height, width = len(item.tokens), len(item.tokens[0])
            rounds_pred = record.get("round_predictions")
            rounds_halt = record.get("round_halt_probabilities")
            if not isinstance(rounds_pred, list) or not isinstance(rounds_halt, list) or \
                    len(rounds_pred) != rounds or len(rounds_halt) != rounds:
                raise ValueError("missing full per-round prediction/halt trace")
            if any(not isinstance(q, (int, float)) or not math.isfinite(q) or not 0 <= q <= 1
                   for q in rounds_halt):
                raise ValueError("invalid halt probability")
            if any(not isinstance(row, list) or len(row) != height * width or
                   any(type(x) is not int or x < 0 or x >= E.VOCAB for x in row)
                   for row in rounds_pred):
                raise ValueError("invalid round prediction")
            chosen_round = stop_round(rounds_pred, rounds_halt)
            checked(stop == chosen_round + 1 and pred == rounds_pred[chosen_round], problems,
                    f"{prefix}: saved own-stop choice differs from v2 trace")
            if not isinstance(pred, list) or len(pred) != height * width or any(
                    type(x) is not int or x < 0 or x >= E.VOCAB for x in pred):
                raise ValueError("missing or malformed full-grid prediction")
            grid = [pred[r * width:(r + 1) * width] for r in range(height)]
            good = bool(E.check(item, grid))
            same_answer = all(pred[j] == item.target[j // width][j % width]
                              for j, slot in enumerate(x for row in item.slot for x in row) if slot)
            checked(record.get("valid") is good and record.get("exact_stored") is same_answer,
                    problems, f"{prefix}: stored grading differs from checker recount")
            valid += good
            exact += same_answer
        except (KeyError, TypeError, ValueError, IndexError, AssertionError) as exc:
            problems.append(f"{prefix}: {exc}")
    checked(scores.get("n") == len(items) and scores.get("valid") == valid and
            scores.get("exact_stored") == exact, problems,
            f"{label}: stored summary differs from item recount")
    return {"n": len(items), "valid": valid, "exact_stored": exact,
            "panel_sha256": digest(path)}


def recount_run(root, arm, seed, expected_hashes, registered_config, registration_commit, problems):
    name = f"{arm}-s{seed}"
    folder = root / "registered" / name
    test_file = "tests.json.gz" if (folder / "tests.json.gz").is_file() else "tests.json"
    required = ["config.json", "train_summary.json", "train_log.jsonl", "final.pt", test_file]
    if arm == "candidate":
        required.append("tests-wiped.json.gz")
    if not checked(all((folder / p).is_file() for p in required), problems,
                   f"{name}: missing registered file(s): " +
                   ", ".join(p for p in required if not (folder / p).is_file())):
        return None
    try:
        cfg = read_json(folder / "config.json")
        summary = read_json(folder / "train_summary.json")
        tests = read_json(folder / test_file)
        wiped_tests = read_json(folder / "tests-wiped.json.gz") if arm == "candidate" else None
        log = [json.loads(line) for line in (folder / "train_log.jsonl").read_text().splitlines()
               if line.strip()]
    except (ValueError, TypeError) as exc:
        problems.append(f"{name}: invalid run JSON: {exc}")
        return None
    if not checked(isinstance(tests, dict), problems, f"{name}: tests.json is not a panel map"):
        return None
    checked(cfg.get("seed") == seed and cfg.get("arm") in (arm, "loop"), problems,
            f"{name}: arm or seed mismatch")
    checked(cfg.get("variant") == arm, problems, f"{name}: variant mismatch")
    check_registered_settings(cfg, registered_config, arm, seed, problems)
    checked(cfg.get("fixed_env") == 0 or cfg.get("env_mode") == "fixed_zero", problems,
            f"{name}: no explicit fixed-env marker")
    checked(cfg.get("unused_env_rows") == len(E.ENVS) - 1, problems,
            f"{name}: unused env row accounting missing")
    checked(all(same(summary.get(k), value) for k, value in cfg.items()), problems,
            f"{name}: training summary config mismatch")
    # The runner writes config.json before training and adds the stream digest
    # to the checkpoint's config only after the last step.
    cfg = {**cfg, "stream_sha256": summary.get("stream_sha256")}
    ck_hash = digest(folder / "final.pt")
    checked(summary.get("checkpoint_sha256") == ck_hash, problems,
            f"{name}: training summary checkpoint SHA-256 mismatch")
    done = folder / "tests.done.json"
    claim = folder / "tests.claim.json"
    if checked(claim.is_file(), problems, f"{name}: preregistered evaluation claim missing"):
        claim_data = read_json(claim)
        checked(claim_data.get("registration_commit") == registration_commit, problems,
                f"{name}: claim registration commit mismatch")
        checked(claim_data.get("checkpoint_sha256") == ck_hash, problems,
                f"{name}: claim checkpoint hash mismatch")
        checked(claim_data.get("panel_sha256") == expected_hashes, problems,
                f"{name}: claim panel hash map mismatch")
        if arm == "candidate":
            checked(claim_data.get("candidate_wiped_cards") is True and
                    claim_data.get("ablation") == "wipe_cards_before_every_read_from_round0",
                    problems, f"{name}: wiped-card claim missing")
    if checked(done.is_file(), problems, f"{name}: evaluation receipt missing"):
        receipt = read_json(done)
        checked(receipt.get("result_sha256") == digest(folder / test_file), problems,
                f"{name}: evaluation receipt hash mismatch")
        if arm == "candidate":
            checked(receipt.get("wiped_result_sha256") == digest(folder / "tests-wiped.json.gz"),
                    problems, f"{name}: wiped-card evaluation receipt hash mismatch")
    minutes = summary.get("minutes")
    checked(isinstance(minutes, (int, float)) and math.isfinite(minutes) and minutes > 0,
            problems, f"{name}: invalid training minutes")
    checked(bool(log) and log[-1].get("step") == cfg.get("steps"), problems,
            f"{name}: train log does not reach configured steps")
    checked(isinstance(summary.get("stream_sha256"), str) and
            len(summary["stream_sha256"]) == 64, problems,
            f"{name}: missing full training stream digest")
    checked(isinstance(summary.get("base_init_state_sha256"), str) and
            len(summary["base_init_state_sha256"]) == 64, problems,
            f"{name}: missing core initial state digest")
    checked(isinstance(summary.get("source_hashes"), dict) and
            bool(summary["source_hashes"]), problems,
            f"{name}: missing imported source hashes")
    sources = summary.get("source_hashes") or {}
    checked(sources.get("scratch_cards") == digest(REPO / "scripts/codex_numbers_20260927_cards.py"),
            problems, f"{name}: card module source hash mismatch")
    grad = summary.get("gradient_check") or {}
    checked(grad.get("steps_seen") == cfg.get("steps") and
            grad.get("steps_block_missing") == 0 and grad.get("steps_block_allzero") == 0 and
            grad.get("steps_block_nograd") == 0 and
            isinstance(grad.get("grad_norms"), list) and bool(grad["grad_norms"]) and
            type(grad.get("block_linear_matrices")) is int and grad["block_linear_matrices"] > 0,
            problems,
            f"{name}: missing or failed gradient checks")
    card_grad = grad.get("card_gradient_check") or {}
    if arm == "candidate":
        counts = card_grad.get("per_parameter_counts")
        checked(type(card_grad.get("parameters")) is int and card_grad["parameters"] > 0 and
                type(card_grad.get("multi_grad_steps")) is int and card_grad["multi_grad_steps"] > 0 and
                isinstance(card_grad.get("per_parameter_norms"), list) and
                bool(card_grad["per_parameter_norms"]) and
                isinstance(counts, dict) and len(counts) == card_grad["parameters"] and
                card_grad.get("single_grad_steps_exempt", 0) +
                card_grad["multi_grad_steps"] == cfg.get("steps"), problems,
                f"{name}: card gradient audit missing")
        if isinstance(counts, dict):
            for param, c in counts.items():
                checked(isinstance(c, dict) and c.get("nonfinite_steps") == 0 and
                        c.get("nonfinite_any_step") == 0 and
                        c.get("missing_steps", -1) + c.get("finite_steps", -1) ==
                        card_grad.get("multi_grad_steps") and
                        c.get("nonzero_steps", -1) + c.get("zero_steps", -1) ==
                        c.get("finite_steps"), problems,
                        f"{name}: card gradient counts invalid for {param}")
        for sample in card_grad.get("per_parameter_norms", []) if isinstance(card_grad.get("per_parameter_norms"), list) else []:
            checked(isinstance(sample, dict) and all(
                isinstance(value, (int, float)) and math.isfinite(value)
                for key, value in sample.items() if key != "step"), problems,
                f"{name}: nonfinite sampled card gradient")
    else:
        checked(card_grad.get("parameters") == 0, problems,
                f"{name}: baseline unexpectedly has card gradients")
    for sample in grad.get("grad_norms", []) if isinstance(grad.get("grad_norms"), list) else []:
        checked(isinstance(sample, dict) and type(sample.get("step")) is int and
                1 <= sample["step"] <= cfg.get("steps", 0) and
                {k for k in sample if k.startswith("block")} ==
                {f"block{i}" for i in range(cfg.get("layers", 0))} and
                all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
                    for k, v in sample.items() if k.startswith("block")), problems,
                f"{name}: invalid sampled gradient norms")
    result = {"config": cfg, "minutes": minutes if isinstance(minutes, (int, float)) else 0,
              "checkpoint_sha256": ck_hash, "panels": {}, "wiped_panels": {},
              "train_summary_sha256": digest(folder / "train_summary.json"),
              "training": {k: summary.get(k) for k in
                           ("stream_sha256", "base_init_state_sha256", "source_hashes", "gradient_check")}}
    for panel in PANELS:
        ev = tests.get(panel)
        checked(isinstance(ev, dict) and ev.get("variant") == arm and ev.get("seed") == seed,
                problems, f"{name}/{panel}: evaluation arm or seed mismatch")
        result["panels"][panel] = recount_panel(root, name, panel, ev,
                                                cfg, ck_hash, expected_hashes, problems)
        if arm == "candidate":
            wiped = wiped_tests.get(panel) if isinstance(wiped_tests, dict) else None
            checked(isinstance(wiped, dict) and
                    wiped.get("variant") == arm and wiped.get("seed") == seed and
                    wiped.get("ablation") == "wipe_cards_before_every_read_from_round0",
                    problems, f"{name}/{panel}: wiped-card ablation marker missing")
            result["wiped_panels"][panel] = recount_panel(root, name + " wiped", panel, wiped,
                                                          cfg, ck_hash, expected_hashes, problems)
    return result


def compare(runs, seeds, problems):
    rows = []
    for seed in seeds:
        b, c = runs.get(f"baseline-s{seed}"), runs.get(f"candidate-s{seed}")
        if b is None or c is None:
            continue
        bc, cc = b["config"], c["config"]
        for key in COMMON_CONFIG:
            checked(key in bc and key in cc and same(bc.get(key), cc.get(key)), problems,
                    f"seed {seed}: paired config differs at {key}")
        for key in ("stream_sha256", "base_init_state_sha256"):
            checked(same(b["training"][key], c["training"][key]), problems,
                    f"seed {seed}: paired {key} differs")
        bw, cw = bc.get("weights"), cc.get("weights")
        checked(bc.get("card_weights") == 0 and type(cc.get("card_weights")) is int and
                type(cw) is int and type(bw) is int and cc["card_weights"] == cw - bw, problems,
                f"seed {seed}: candidate card parameter accounting differs from weight gap")
        checked(type(bw) is int and type(cw) is int and bw > 0 and
                abs(cw - bw) / bw <= .01, problems,
                f"seed {seed}: candidate parameter count differs by more than 1%")
        entry = {"seed": seed, "baseline_minutes": b["minutes"],
                 "candidate_minutes": c["minutes"], "panels": {}}
        for panel in PANELS:
            bp, cp = b["panels"][panel], c["panels"][panel]
            wp = c["wiped_panels"].get(panel)
            if bp is None or cp is None or wp is None:
                continue
            checked(bp["panel_sha256"] == cp["panel_sha256"], problems,
                    f"seed {seed}/{panel}: paired panel differs")
            checked(cp["panel_sha256"] == wp["panel_sha256"], problems,
                    f"seed {seed}/{panel}: intact and wiped panels differ")
            entry["panels"][panel] = {"baseline": bp["valid"], "candidate": cp["valid"],
                                      "gap": cp["valid"] - bp["valid"],
                                      "wiped": wp["valid"],
                                      "intact_minus_wiped": cp["valid"] - wp["valid"]}
        rows.append(entry)
    for panel in PANELS:
        hashes = {r["panels"][panel]["panel_sha256"] for r in runs.values()
                  if r is not None and r["panels"][panel] is not None}
        hashes.update(r["wiped_panels"][panel]["panel_sha256"] for r in runs.values()
                      if r is not None and r["wiped_panels"].get(panel) is not None)
        checked(len(hashes) <= 1, problems, f"{panel}: panel differs across seeds/arms")
    return rows


def marks(rows):
    n = len(rows)
    by = lambda panel, field: [r["panels"][panel][field] for r in rows]
    mean = lambda vals: sum(vals) / n
    n1 = mean(by("numbers4", "candidate")) >= 100 and all(x >= 60 for x in by("numbers4", "gap"))
    n2 = mean(by("numbers5", "candidate")) >= 30 and sum(x > 0 for x in by("numbers5", "gap")) / n >= .75
    n3 = all(abs(mean(by(p, "gap"))) <= 5 and all(x >= -10 for x in by(p, "gap"))
             for p in ("sums4", "grids5"))
    n5 = all(mean(by(p, "intact_minus_wiped")) >= threshold and
             sum(x > 0 for x in by(p, "intact_minus_wiped")) >= math.ceil(.75 * n)
             for p, threshold in (("numbers4", 10), ("numbers5", 5)))
    return {"N1": n1, "N2": n2, "N3": n3, "N4": True, "N5": n5,
            "proved_wrong": mean(by("numbers4", "gap")) <= 10,
            "proved_wrong_bigger": mean(by("numbers5", "gap")) <= 5,
            "proved_wrong_memory": {p: mean(by(p, "intact_minus_wiped")) <= 0
                                    for p in ("numbers4", "numbers5")},
            "proved_wrong_memory_any": any(mean(by(p, "intact_minus_wiped")) <= 0
                                           for p in ("numbers4", "numbers5")),
            "means": {p: {f: mean(by(p, f)) for f in
                          ("baseline", "candidate", "gap", "wiped", "intact_minus_wiped")}
                      for p in PANELS}}


def verdict_for(problems, rows):
    complete = not problems and len(rows) >= 4 and all(len(r["panels"]) == len(PANELS) for r in rows)
    result_marks = marks(rows) if complete else None
    verdict = ("INCOMPLETE" if not complete else
               "PASS" if all(result_marks[k] for k in ("N1", "N2", "N3", "N4", "N5")) else "FAIL")
    return verdict, result_marks


def selftest():
    registered = {"seeds": [11, 12, 13, 14], "device": "mps", "torch_version": "2.11.0",
                  "train": {"steps": 60, "batch": 8, "width": 32, "layers": 2,
                            "heads": 8, "latin_pool": 10, "lr": .0003,
                            "warmup": 5, "log_every": 10}}
    run_cfg = {**registered["train"], "seed": 11, "variant": "baseline",
               "device": "mps", "dtype": "float32", "torch": "2.11.0",
               "fixed_env": 0, "dev_holdout": 0}
    gate_problems = []
    check_registered_seeds([11, 12, 13, 14], registered, gate_problems)
    check_registered_settings(run_cfg, registered, "baseline", 11, gate_problems)
    assert gate_problems == []
    check_registered_seeds([11, 12, 13, 15], registered, gate_problems)
    check_registered_settings({**run_cfg, "steps": 59}, registered, "baseline", 11,
                              gate_problems)
    assert any("EXPERIMENT.seeds" in x for x in gate_problems)
    assert any("setting steps" in x for x in gate_problems)
    def row(seed, n4b=40, n4c=100, n5b=0, n5c=30, sumb=300, sumc=295,
            gridb=300, gridc=295):
        vals = {"numbers4": (n4b, n4c), "numbers5": (n5b, n5c),
                "numbers5_old": (n5b, n5c),
                "sums4": (sumb, sumc), "grids5": (gridb, gridc)}
        return {"seed": seed, "panels": {k: {"baseline": b, "candidate": c, "gap": c - b}
                                          | {"wiped": 80 if k == "numbers4" else
                                              20 if k == "numbers5" else c,
                                             "intact_minus_wiped": c - (80 if k == "numbers4" else
                                                                           20 if k == "numbers5" else c)}
                                          for k, (b, c) in vals.items()}}
    rows = [row(i) for i in range(4)]
    assert verdict_for([], rows)[0] == "PASS"
    assert verdict_for(["missing trace"], rows)[0] == "INCOMPLETE"
    assert verdict_for([], rows[:3])[0] == "INCOMPLETE"
    assert verdict_for([], rows)[1]["proved_wrong"] is False
    assert verdict_for([], [row(i, n4c=50) for i in range(4)])[1]["proved_wrong"] is True
    assert verdict_for([], [row(i, n5c=5) for i in range(4)])[1]["proved_wrong_bigger"] is True
    assert verdict_for([], [row(i, n5c=6) for i in range(4)])[1]["proved_wrong_bigger"] is False
    assert verdict_for([], [row(i, n5c=29) for i in range(4)])[0] == "FAIL"
    assert verdict_for([], [row(i, sumc=289) if i == 0 else row(i) for i in range(4)])[0] == "FAIL"
    assert verdict_for([], [row(i, n4c=99) for i in range(4)])[0] == "FAIL"
    assert verdict_for([], rows)[1]["N5"] is True
    weak_memory = [row(i) for i in range(4)]
    for item in weak_memory:
        item["panels"]["numbers4"]["wiped"] = 91
        item["panels"]["numbers4"]["intact_minus_wiped"] = 9
    assert verdict_for([], weak_memory)[1]["N5"] is False
    assert stop_round([[1], [1], [1], [2]], [.9, .9, .9, .9]) == 2
    assert stop_round([[1], [2], [2], [2]], [.9, .9, .5, .9]) == 3
    assert stop_round([[1], [2], [3]], [.9, .9, .9]) == 2
    with tempfile.TemporaryDirectory(prefix="codex-recount-") as temporary:
        root = Path(temporary)
        panel = root / "panels/numbers5.jsonl"
        panel.parent.mkdir()
        raw = {"env": "numbers", "size": 5,
               "tokens": [[26] * 5 + [0] * 4, [49] + [0] * 8, [1] * 9],
               "slot": [[0] * 9, [0] * 9, [1] * 9],
               "target": [[0] * 9, [0] * 9, [26] * 9],
               "meta": {"nums": [1] * 5, "target": 24}}
        panel.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        pred = [0] * 27
        rec = {"index": 0, "kind": "numbers", "size": 5, "stop": 48,
               "prediction": pred, "valid": False, "exact_stored": False,
               "round_predictions": [pred] * 48, "round_halt_probabilities": [0.0] * 48}
        evaluation = {"panel": str(panel), "panel_sha256": digest(panel),
                      "checkpoint_sha256": "f" * 64, "config": {"test_rounds": 48},
                      "poison": {"rounds": 48, "tested_kinds": E.ENVS,
                                 "logits_equal": True, "predictions_equal": True,
                                 "raw_halts_equal": True},
                      "scores": {"n": 1, "valid": 0, "exact_stored": 0, "items": [rec]}}
        problems = []
        result = recount_panel(root, "synthetic", "numbers5", evaluation,
                               {"test_rounds": 48}, "f" * 64,
                               {"numbers5": digest(panel)}, problems)
        assert result["valid"] == 0 and problems == ["synthetic/numbers5: expected 300 panel items, got 1"]
        rec["stop"] = 47
        rec["valid"] = True
        problems = []
        recount_panel(root, "synthetic", "numbers5", evaluation,
                      {"test_rounds": 48}, "f" * 64,
                      {"numbers5": digest(panel)}, problems)
        assert any("own-stop choice differs" in p for p in problems)
        assert any("checker recount" in p for p in problems)
    print("recount selftest passed")


def markdown(report):
    out = ["# Independent recount", "", f"**Verdict: {report['verdict']}**", "",
           "SHOWN: Counts below use each recorded prediction at the model's own stop and the existing checker.",
           "N1 uses the immutable 358i numbers4 file, which earlier runs have scored; its totals were known.",
           "N2 uses the new five-number panel drawn after registration and is the cleanest test.",
           "numbers5_old is the previously scored 358i seed-35832 panel and is report-only.",
           "N5 compares the same candidate checkpoint and panel items with cards intact and wiped before every read.",
           "SUGGESTED: A passing pattern would support the selected training change on these panels.",
           "UNTESTED: Transfer beyond these panels, the 1B chat model, and the joined build.", ""]
    for panel in PANELS:
        out += [f"## {panel}", "", "| Seed | Baseline /300 | Candidate /300 | Wiped /300 | Candidate−baseline | Intact−wiped | Baseline min | Candidate min |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in report["rows"]:
            x = row["panels"].get(panel)
            if x:
                out.append(f"| {row['seed']} | {x['baseline']} | {x['candidate']} | {x['wiped']} | "
                           f"{x['gap']:+d} | {x['intact_minus_wiped']:+d} | "
                           f"{row['baseline_minutes']:.2f} | {row['candidate_minutes']:.2f} |")
        out.append("")
    if report["marks"]:
        out += ["## Registered marks", ""]
        for k in ("N1", "N2", "N3", "N4", "N5", "proved_wrong", "proved_wrong_bigger"):
            out.append(f"- {k}: {'met' if report['marks'][k] else 'not met'}")
        for panel, value in report["marks"]["proved_wrong_memory"].items():
            out.append(f"- Proved wrong for memory on {panel} (intact mean ≤ wiped mean): "
                       f"{'met' if value else 'not met'}")
        out.append("- Proved wrong for useful memory on both panels (either panel mean intact ≤ wiped): "
                   f"{'met' if report['marks']['proved_wrong_memory_any'] else 'not met'}")
        out.append("")
    if report["problems"]:
        out += ["## Missing or inconsistent evidence", ""] + [f"- {x}" for x in report["problems"]] + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, nargs="?", help="experiment artifact root")
    ap.add_argument("--out", type=Path, help="output directory (default: root)")
    ap.add_argument("--selftest", action="store_true", help="run synthetic marks and incomplete checks")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return 0
    ap.error("root is required") if args.root is None else None
    root = args.root.resolve()
    out = (args.out or root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    problems = []
    expected_hashes = {}
    experiment = root / "EXPERIMENT.json"
    sealed = root / "SEALED-PANEL.json"
    frozen_path = root / "CHECKPOINTS-FROZEN.json"
    seal_path = root / "SEAL-code.json"
    complete_receipt = root / "registered/EVALUATION-COMPLETE.json"
    if not complete_receipt.is_file():
        report = {"verdict": "INCOMPLETE", "seeds": [], "rows": [], "marks": None,
                  "problems": ["registered evaluation completion receipt missing; sealed panels were not opened"],
                  "runs": {}, "claim_labels": {}}
        (out / "RECOUNT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        (out / "RECOUNT.md").write_text(markdown(report))
        print("INCOMPLETE: evaluation not complete; sealed panels were not opened")
        return 2
    completed = read_json(complete_receipt)
    if frozen_path.is_file():
        frozen = read_json(frozen_path)
        checked(completed.get("checkpoint_manifest_sha256") == digest(frozen_path), problems,
                "completion receipt checkpoint manifest hash mismatch")
    else:
        frozen = {}
        problems.append("frozen checkpoint manifest missing")
    registration_commit = frozen.get("registration_commit")
    checked(isinstance(registration_commit, str) and len(registration_commit) == 40,
            problems, "frozen manifest registration commit missing")
    checked(completed.get("registration_commit") == registration_commit, problems,
            "completion receipt registration commit mismatch")
    if experiment.is_file():
        config = read_json(experiment)
        checked(frozen.get("experiment_sha256") == digest(experiment), problems,
                "frozen manifest EXPERIMENT hash mismatch")
        expected_hashes.update(config.get("registered_panel_sha256", {}))
        gate = config.get("diagnostic_gate", {})
        checked(frozen.get("diagnostic_summary_sha256") == gate.get("summary_sha256"),
                problems, "frozen manifest diagnostic gate hash mismatch")
        if set(gate) == {"summary_path", "summary_sha256", "manifest_path", "manifest_sha256"}:
            summary_path = REPO / gate["summary_path"]
            manifest_path = REPO / gate["manifest_path"]
            if summary_path.is_file() and manifest_path.is_file() and \
                    digest(summary_path) == gate["summary_sha256"] and \
                    digest(manifest_path) == gate["manifest_sha256"]:
                diagnostic = read_json(summary_path)
                split = read_json(manifest_path)
                scores = ((diagnostic.get("final_probe") or {}).get("scores") or {}).get("train_numbers4") or {}
                checked(scores.get("n") == 962 and
                        type(scores.get("exact_stored")) is int and scores["exact_stored"] >= .95 * 962 and
                        split.get("train_four_count") == 962 and split.get("dev_four_count") == 100,
                        problems, "registered diagnostic practice gate did not reach 0.95")
            else:
                problems.append("registered diagnostic evidence files changed or missing")
        else:
            problems.append("registered diagnostic gate reference missing")
    else:
        config = {}
        problems.append("registered EXPERIMENT.json missing")
    if seal_path.is_file():
        checked(frozen.get("seal_sha256") == digest(seal_path), problems,
                "frozen manifest code seal hash mismatch")
    else:
        problems.append("registered code seal missing")
    if sealed.is_file():
        sealed_info = read_json(sealed)
        expected_hashes["numbers5"] = sealed_info.get("sha256")
        checked(sealed_info.get("registration_commit") == registration_commit, problems,
                "sealed panel registration commit mismatch")
        checked(sealed_info.get("seed") == config.get("sealed_seed"), problems,
                "sealed panel seed differs from EXPERIMENT")
        checked(sealed_info.get("frozen_manifest_sha256") == digest(frozen_path)
                if frozen_path.is_file() else False, problems,
                "sealed panel frozen manifest hash mismatch")
        checked(sealed_info.get("n") == 300 and sealed_info.get("training_hand_overlap") == 0 and
                sealed_info.get("training_hand_overlap_basis") ==
                "training uses only three- and four-number hands; this panel contains five-number hands",
                problems, "sealed panel count or training-hand nonoverlap proof missing")
    else:
        problems.append("new five-number sealed-panel receipt missing")
    if set(expected_hashes) != set(PANELS):
        problems.append("registered panel hashes do not cover all five panels")
    registered = root / "registered"
    names = [p.name for p in registered.iterdir() if p.is_dir()] if registered.is_dir() else []
    seeds = sorted({int(name.split("-s")[-1]) for name in names
                    if name.startswith(("baseline-s", "candidate-s")) and name.split("-s")[-1].isdigit()})
    check_registered_seeds(seeds, config, problems)
    runs = {f"{arm}-s{seed}": recount_run(root, arm, seed, expected_hashes,
                                         config, registration_commit, problems)
            for seed in seeds for arm in ("baseline", "candidate")}
    frozen_runs = frozen.get("runs")
    if checked(isinstance(frozen_runs, list), problems, "frozen manifest run inventory missing"):
        identities = [(entry.get("variant"), entry.get("seed")) for entry in frozen_runs
                      if isinstance(entry, dict)]
        expected_identities = {(arm, seed) for seed in config.get("seeds", [])
                               for arm in ("baseline", "candidate")}
        checked(len(identities) == len(frozen_runs) == len(expected_identities) and
                set(identities) == expected_identities,
                problems, "frozen manifest inventory differs from registered runs")
        for entry in frozen_runs:
            if not isinstance(entry, dict):
                continue
            arm, seed = entry.get("variant"), entry.get("seed")
            name = f"{arm}-s{seed}"
            run = runs.get(name)
            if run is None:
                continue
            folder = root / "registered" / name
            checked(Path(entry.get("checkpoint", "")).resolve() == (folder / "final.pt").resolve() and
                    entry.get("checkpoint_sha256") == run["checkpoint_sha256"] and
                    entry.get("summary_sha256") == run["train_summary_sha256"] and
                    entry.get("weights") == run["config"].get("weights") and
                    entry.get("stream_sha256") == run["training"].get("stream_sha256") and
                    entry.get("base_init_state_sha256") == run["training"].get("base_init_state_sha256") and
                    entry.get("source_hashes") == run["training"].get("source_hashes") and
                    entry.get("runner_script_sha256") == run["config"].get("script_sha256") and
                    entry.get("cache_hashes") == run["config"].get("cache_hashes"),
                    problems, f"{name}: frozen manifest checkpoint/summary/config mismatch")
    checked(completed.get("evaluations") == len(seeds) * len(PANELS) * 2,
            problems, "evaluation completion count mismatch")
    checked(completed.get("wiped_evaluations") == len(seeds) * len(PANELS),
            problems, "wiped-card evaluation completion count mismatch")
    rows = compare(runs, seeds, problems)
    verdict, result_marks = verdict_for(problems, rows)
    report = {"verdict": verdict, "seeds": seeds, "rows": rows, "marks": result_marks,
              "problems": problems, "runs": runs,
              "claim_labels": {"SHOWN": "checker-recount panel counts and audited evidence",
                               "SUGGESTED": "interpretation of the registered change",
                               "UNTESTED": "broader transfer and other model families"}}
    (out / "RECOUNT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (out / "RECOUNT.md").write_text(markdown(report))
    print(f"{verdict}: {len(seeds)} seed(s), {len(problems)} evidence problem(s)")
    return 0 if verdict != "INCOMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
