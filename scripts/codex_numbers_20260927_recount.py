#!/usr/bin/env python3
"""Independent, inference-free recount of registered small-puzzle evaluations.

Input: ROOT/registered/{baseline,candidate}-sSEED/{config.json,
train_summary.json,train_log.jsonl,final.pt,tests.json.gz}.  tests.json.gz maps the
four panel names to the JSON emitted by codex_numbers_20260927_run.py eval
with --details. Each eval names its original JSONL panel, which must still
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402

PANELS = {"numbers4": ("numbers", 4), "numbers5": ("numbers", 5),
          "sums4": ("sums", 4), "grids5": ("grids", 5)}
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


def recount_panel(root, run, name, ev, cfg, ck_hash, problems):
    label = f"{run}/{name}"
    if not isinstance(ev, dict):
        problems.append(f"{label}: missing evaluation")
        return None
    path = panel_path(root, ev.get("panel", ""))
    if not checked(path.is_file(), problems, f"{label}: panel file missing: {path}"):
        return None
    checked(ev.get("panel_sha256") == digest(path), problems,
            f"{label}: panel SHA-256 mismatch")
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


def recount_run(root, arm, seed, problems):
    name = f"{arm}-s{seed}"
    folder = root / "registered" / name
    test_file = "tests.json.gz" if (folder / "tests.json.gz").is_file() else "tests.json"
    required = ["config.json", "train_summary.json", "train_log.jsonl", "final.pt", test_file]
    if not checked(all((folder / p).is_file() for p in required), problems,
                   f"{name}: missing registered file(s): " +
                   ", ".join(p for p in required if not (folder / p).is_file())):
        return None
    try:
        cfg = read_json(folder / "config.json")
        summary = read_json(folder / "train_summary.json")
        tests = read_json(folder / test_file)
        log = [json.loads(line) for line in (folder / "train_log.jsonl").read_text().splitlines()
               if line.strip()]
    except (ValueError, TypeError) as exc:
        problems.append(f"{name}: invalid run JSON: {exc}")
        return None
    if not checked(isinstance(tests, dict), problems, f"{name}: tests.json is not a panel map"):
        return None
    checked(cfg.get("seed") == seed and cfg.get("arm") in (arm, "loop"), problems,
            f"{name}: arm or seed mismatch")
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
    minutes = summary.get("minutes")
    checked(isinstance(minutes, (int, float)) and math.isfinite(minutes) and minutes > 0,
            problems, f"{name}: invalid training minutes")
    checked(bool(log) and log[-1].get("step") == cfg.get("steps"), problems,
            f"{name}: train log does not reach configured steps")
    checked(isinstance(summary.get("stream_sha256"), str) and
            len(summary["stream_sha256"]) == 64, problems,
            f"{name}: missing full training stream digest")
    checked(isinstance(summary.get("init_state_sha256"), str) and
            len(summary["init_state_sha256"]) == 64, problems,
            f"{name}: missing initial state digest")
    checked(isinstance(summary.get("source_hashes"), dict) and
            bool(summary["source_hashes"]), problems,
            f"{name}: missing imported source hashes")
    grad = summary.get("gradient_check") or {}
    checked(grad.get("steps_seen") == cfg.get("steps") and
            grad.get("steps_block_missing") == 0 and grad.get("steps_block_allzero") == 0 and
            grad.get("steps_block_nograd") == 0 and
            isinstance(grad.get("grad_norms"), list) and bool(grad["grad_norms"]) and
            type(grad.get("block_linear_matrices")) is int and grad["block_linear_matrices"] > 0,
            problems,
            f"{name}: missing or failed gradient checks")
    for sample in grad.get("grad_norms", []) if isinstance(grad.get("grad_norms"), list) else []:
        checked(isinstance(sample, dict) and type(sample.get("step")) is int and
                1 <= sample["step"] <= cfg.get("steps", 0) and
                {k for k in sample if k.startswith("block")} ==
                {f"block{i}" for i in range(cfg.get("layers", 0))} and
                all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
                    for k, v in sample.items() if k.startswith("block")), problems,
                f"{name}: invalid sampled gradient norms")
    result = {"config": cfg, "minutes": minutes if isinstance(minutes, (int, float)) else 0,
              "checkpoint_sha256": ck_hash, "panels": {},
              "training": {k: summary.get(k) for k in
                           ("stream_sha256", "init_state_sha256", "source_hashes", "gradient_check")}}
    for panel in PANELS:
        result["panels"][panel] = recount_panel(root, name, panel, tests.get(panel),
                                                cfg, ck_hash, problems)
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
        for key in ("stream_sha256", "init_state_sha256", "source_hashes"):
            checked(same(b["training"][key], c["training"][key]), problems,
                    f"seed {seed}: paired {key} differs")
        bw, cw = bc.get("weights"), cc.get("weights")
        checked(type(bw) is int and type(cw) is int and bw > 0 and
                abs(cw - bw) / bw <= .01, problems,
                f"seed {seed}: candidate parameter count differs by more than 1%")
        entry = {"seed": seed, "baseline_minutes": b["minutes"],
                 "candidate_minutes": c["minutes"], "panels": {}}
        for panel in PANELS:
            bp, cp = b["panels"][panel], c["panels"][panel]
            if bp is None or cp is None:
                continue
            checked(bp["panel_sha256"] == cp["panel_sha256"], problems,
                    f"seed {seed}/{panel}: paired panel differs")
            entry["panels"][panel] = {"baseline": bp["valid"], "candidate": cp["valid"],
                                      "gap": cp["valid"] - bp["valid"]}
        rows.append(entry)
    for panel in PANELS:
        hashes = {r["panels"][panel]["panel_sha256"] for r in runs.values()
                  if r is not None and r["panels"][panel] is not None}
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
    return {"N1": n1, "N2": n2, "N3": n3, "N4": True,
            "proved_wrong": mean(by("numbers4", "gap")) <= 10,
            "means": {p: {f: mean(by(p, f)) for f in ("baseline", "candidate", "gap")}
                      for p in PANELS}}


def verdict_for(problems, rows):
    complete = not problems and len(rows) >= 4 and all(len(r["panels"]) == len(PANELS) for r in rows)
    result_marks = marks(rows) if complete else None
    verdict = ("INCOMPLETE" if not complete else
               "PASS" if all(result_marks[k] for k in ("N1", "N2", "N3", "N4")) else "FAIL")
    return verdict, result_marks


def selftest():
    def row(seed, n4b=40, n4c=100, n5b=0, n5c=30, sumb=300, sumc=295,
            gridb=300, gridc=295):
        vals = {"numbers4": (n4b, n4c), "numbers5": (n5b, n5c),
                "sums4": (sumb, sumc), "grids5": (gridb, gridc)}
        return {"seed": seed, "panels": {k: {"baseline": b, "candidate": c, "gap": c - b}
                                          for k, (b, c) in vals.items()}}
    rows = [row(i) for i in range(4)]
    assert verdict_for([], rows)[0] == "PASS"
    assert verdict_for(["missing trace"], rows)[0] == "INCOMPLETE"
    assert verdict_for([], rows[:3])[0] == "INCOMPLETE"
    assert verdict_for([], rows)[1]["proved_wrong"] is False
    assert verdict_for([], [row(i, n4c=50) for i in range(4)])[1]["proved_wrong"] is True
    assert verdict_for([], [row(i, n5c=29) for i in range(4)])[0] == "FAIL"
    assert verdict_for([], [row(i, sumc=289) if i == 0 else row(i) for i in range(4)])[0] == "FAIL"
    assert verdict_for([], [row(i, n4c=99) for i in range(4)])[0] == "FAIL"
    assert stop_round([[1], [1], [1], [2]], [.9, .9, .9, .9]) == 2
    assert stop_round([[1], [2], [2], [2]], [.9, .9, .5, .9]) == 3
    assert stop_round([[1], [2], [3]], [.9, .9, .9]) == 2
    print("recount selftest passed")


def markdown(report):
    out = ["# Independent recount", "", f"**Verdict: {report['verdict']}**", "",
           "SHOWN: Counts below use each recorded prediction at the model's own stop and the existing checker.",
           "The four-number design panel was already seen during development; the five-number panel is the clean test.",
           "SUGGESTED: A passing pattern would support the selected training change on these panels.",
           "UNTESTED: Transfer beyond these panels, the 1B chat model, and the joined build.", ""]
    for panel in PANELS:
        out += [f"## {panel}", "", "| Seed | Baseline /300 | Candidate /300 | Gap | Baseline min | Candidate min |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |"]
        for row in report["rows"]:
            x = row["panels"].get(panel)
            if x:
                out.append(f"| {row['seed']} | {x['baseline']} | {x['candidate']} | {x['gap']:+d} | "
                           f"{row['baseline_minutes']:.2f} | {row['candidate_minutes']:.2f} |")
        out.append("")
    if report["marks"]:
        out += ["## Registered marks", ""]
        for k in ("N1", "N2", "N3", "N4", "proved_wrong"):
            out.append(f"- {k}: {'met' if report['marks'][k] else 'not met'}")
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
    registered = root / "registered"
    names = [p.name for p in registered.iterdir() if p.is_dir()] if registered.is_dir() else []
    seeds = sorted({int(name.split("-s")[-1]) for name in names
                    if name.startswith(("baseline-s", "candidate-s")) and name.split("-s")[-1].isdigit()})
    checked(len(seeds) >= 4, problems, f"expected at least four paired seeds, found {len(seeds)}")
    runs = {f"{arm}-s{seed}": recount_run(root, arm, seed, problems)
            for seed in seeds for arm in ("baseline", "candidate")}
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
