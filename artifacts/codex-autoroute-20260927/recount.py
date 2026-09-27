#!/usr/bin/env python3
"""Independent, read-only recount of AR1's saved mixed prediction streams.

Contract with the runner: panels/seedN.json contains seed, panel_seed,
diagnostic_seed, final (600 rows), and diagnostic (300 rows). A row contains
id, env, size, tokens, slot, target, meta. The ID is SHA256 of compact JSON
of the visible [tokens, slot] array.
Each run directory contains result.json, A.jsonl, B.jsonl, C.jsonl, and
final.pt. A prediction row has id, predictions [48][H*W],
stop_probabilities [48], context_probabilities [4]. manifest.json has a
source_hashes map from repository-relative source paths to SHA256 hex digests.

No runner score or stop decision is trusted. The final checkpoint is replayed
one mixed request at a time on MPS unless --no-model is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ARMS = ("baseline", "late_replay")
SEEDS = tuple(range(41, 47))
PHASES = ("A", "B", "C")
PANELS = {"grids": (5, "grids5"), "sums": (4, "sums4"), "mazes": (7, "maze7")}
PANEL_SEED_BASE = 927204781031
DIAG_SEED_BASE = 927204782031
EXPECTED_PARAMETERS = 1_646_750
REGISTRATION = "cafb67a80d97a8ddc93fe211bfb2e913b9f63119"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def strict_json(text: str):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key {key!r}")
            out[key] = value
        return out

    return json.loads(text, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def read_json(path: Path):
    return strict_json(path.read_text(encoding="utf-8"))


def canonical_id(tokens, slot):
    payload = json.dumps([tokens, slot], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_int(value, low=0, high=None):
    return type(value) is int and value >= low and (high is None or value <= high)


def rectangular(rows):
    return (isinstance(rows, list) and bool(rows) and isinstance(rows[0], list)
            and bool(rows[0]) and all(isinstance(row, list) and len(row) == len(rows[0])
                                    and all(is_int(cell) for cell in row) for row in rows))


def validate_panel_row(row, label):
    if not isinstance(row, dict):
        raise ValueError(f"{label}: row must be an object")
    env = row.get("env")
    if env not in PANELS or row.get("size") != PANELS[env][0] or type(row.get("size")) is not int:
        raise ValueError(f"{label}: unexpected env/size")
    tokens, slot, target = (row.get(key) for key in ("tokens", "slot", "target"))
    if not all(rectangular(value) for value in (tokens, slot, target)):
        raise ValueError(f"{label}: tokens, slot, target must be rectangular integer arrays")
    shape = (len(tokens), len(tokens[0]))
    if any((len(value), len(value[0])) != shape for value in (slot, target)):
        raise ValueError(f"{label}: visible and target shapes differ")
    if any(cell not in (0, 1) for line in slot for cell in line):
        raise ValueError(f"{label}: slot must be binary")
    if row.get("id") != canonical_id(tokens, slot):
        raise ValueError(f"{label}: visible-input SHA256 fingerprint mismatch")
    if not isinstance(row.get("meta"), dict):
        raise ValueError(f"{label}: missing checker metadata")
    return env


def load_panel(path: Path, seed: int):
    data = read_json(path)
    if not isinstance(data, dict) or any(data.get(key) != value or type(data.get(key)) is not int
                                         for key, value in (("seed", seed),
                                                            ("panel_seed", PANEL_SEED_BASE + seed - 41),
                                                            ("diagnostic_seed", DIAG_SEED_BASE + seed - 41))):
        raise ValueError(f"{path}: panel seed fields mismatch")
    for part, n_each in (("final", 200), ("diagnostic", 100)):
        rows = data.get(part)
        if not isinstance(rows, list) or len(rows) != 3 * n_each:
            raise ValueError(f"{path}: {part} must contain {3 * n_each} rows")
        counts = Counter(validate_panel_row(row, f"{path}:{part}:{i}") for i, row in enumerate(rows))
        if counts != {kind: n_each for kind in PANELS}:
            raise ValueError(f"{path}: {part} kind counts {counts}")
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{path}: duplicate visible inputs in {part}")
    if {row["id"] for row in data["final"]} & {row["id"] for row in data["diagnostic"]}:
        raise ValueError(f"{path}: final and diagnostic inputs overlap")
    return data


def own_stop(predictions, stops):
    """One-based 1..48 answer round; fallback is round 48."""
    for index in range(2, 48):
        if stops[index] > 0.5 and predictions[index] == predictions[index - 1] == predictions[index - 2]:
            return index + 1
    return 48


def validate_prediction(row, panel_row, label):
    if not isinstance(row, dict) or row.get("id") != panel_row["id"]:
        raise ValueError(f"{label}: missing or out-of-order fingerprint")
    width = len(panel_row["tokens"]) * len(panel_row["tokens"][0])
    predictions = row.get("predictions")
    stops = row.get("stop_probabilities")
    contexts = row.get("context_probabilities")
    if (not isinstance(predictions, list) or len(predictions) != 48
            or any(not isinstance(p, list) or len(p) != width
                   or any(not is_int(token, 0, 124) for token in p) for p in predictions)):
        raise ValueError(f"{label}: predictions must be 48 flat vocabulary rows of width {width}")
    if (not isinstance(stops, list) or len(stops) != 48
            or any(type(q) not in (int, float) or not math.isfinite(q) or not 0 <= q <= 1 for q in stops)):
        raise ValueError(f"{label}: stop probabilities must be 48 finite values in [0,1]")
    if (not isinstance(contexts, list) or len(contexts) != 4
            or any(type(q) not in (int, float) or not math.isfinite(q) or not 0 <= q <= 1 for q in contexts)
            or abs(sum(contexts) - 1) > 1e-5):
        raise ValueError(f"{label}: context probabilities must be a four-way distribution")
    return predictions, stops, contexts


def source_manifest(manifest, label):
    hashes = manifest.get("source_hashes")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError(f"{label}: missing source_hashes manifest")
    if not {"artifacts/codex-autoroute-20260927/auto_model.py",
            "artifacts/codex-autoroute-20260927/run_experiment.py"} <= set(hashes):
        raise ValueError(f"{label}: source_hashes must cover auto_model.py and run_experiment.py")
    for name, digest in hashes.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not HEX256.fullmatch(digest):
            raise ValueError(f"{label}: malformed source hash entry")
        path = (REPO / name).resolve()
        if not path.is_relative_to(REPO) or not path.is_file():
            raise ValueError(f"{label}: source path absent or outside repository: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != actual:
            raise ValueError(f"{label}: source hash mismatch: {name}")
    return hashes


def raw_path(run_dir, result, phase):
    """Accept a declared relative file, otherwise the agreed A/B/C.jsonl layout."""
    declared = result.get("phases", {}).get(phase, {}).get("raw_predictions")
    if declared is None:
        return run_dir / f"{phase}.jsonl"
    if not isinstance(declared, str) or Path(declared).is_absolute():
        raise ValueError(f"{phase}: raw_predictions must be a relative path")
    path = (run_dir / declared).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ValueError(f"{phase}: raw_predictions escapes run directory")
    return path


def read_stream(path, panel):
    yield from read_stream_n(path, panel)


def recount_stream(path, panel):
    # Import the sealed chain only after all rows have been written by the runner.
    from auto_model import E, R  # noqa: PLC0415

    scores = {name: {"right": 0, "n": 0, "fixed16": 0, "any48": 0,
                     "stopping_rounds_sum": 0} for _, name in PANELS.values()}
    rounds = []
    for panel_row, raw in zip(panel, read_stream(path, panel), strict=True):
        predictions, stops, _ = validate_prediction(raw, panel_row, str(path))
        answer_round = own_stop(predictions, stops)
        rounds.append(answer_round)
        item = E.Item(panel_row["env"], panel_row["size"], panel_row["tokens"],
                      panel_row["slot"], panel_row["target"], panel_row["meta"])
        checks = [bool(E.check(item, R.grid_of(prediction, item))) for prediction in predictions]
        count = scores[PANELS[panel_row["env"]][1]]
        count["n"] += 1
        count["right"] += int(checks[answer_round - 1])
        count["fixed16"] += int(checks[15])
        count["any48"] += int(any(checks))
        count["stopping_rounds_sum"] += answer_round
    return scores, {"mean_rounds": sum(rounds) / len(rounds),
                    "histogram": dict(sorted(Counter(rounds).items()))}


def compare_scores(actual, recorded, label):
    if not isinstance(recorded, dict):
        raise ValueError(f"{label}: missing recorded score")
    for panel, expected in actual.items():
        got = recorded.get(panel)
        if not isinstance(got, dict) or any(got.get(key) != value or type(got.get(key)) is not int
                                            for key, value in expected.items()):
            raise ValueError(f"{label}: {panel} recorded {got} vs raw {expected}")


def recount_context(diag_file, diagnostic, final_file, final, recorded):
    # The map is descriptive only. No context index is used to select a model.
    kinds = tuple(PANELS)
    counts = {i: {kind: 0 for kind in kinds} for i in range(4)}
    for row, prediction in zip(diagnostic, read_stream_n(diag_file, diagnostic), strict=True):
        index = max(range(4), key=lambda i: prediction["context_probabilities"][i])
        counts[index][row["env"]] += 1
    mapping = {i: max(kinds, key=lambda kind: counts[i][kind]) for i in range(4)}
    agreement = sum(mapping[max(range(4), key=lambda i: prediction["context_probabilities"][i])] == row["env"]
                    for row, prediction in zip(final, read_stream(final_file, final), strict=True))
    expected = {"mapping": {str(i): kind for i, kind in mapping.items()},
                "calibration_counts": {str(i): count for i, count in counts.items()},
                "agreement": agreement, "n": 600}
    if recorded != expected:
        raise ValueError(f"report-only context agreement differs from diagnostic/raw C streams: {recorded} vs {expected}")
    return expected


def read_stream_n(path, panel):
    with path.open("r", encoding="utf-8") as fh:
        for i, expected in enumerate(panel):
            line = fh.readline()
            if not line:
                raise ValueError(f"{path}: only {i}/{len(panel)} prediction rows")
            row = strict_json(line)
            validate_prediction(row, expected, f"{path}:{i + 1}")
            yield row
        if fh.readline():
            raise ValueError(f"{path}: more than {len(panel)} prediction rows")


def replay_checkpoint(checkpoint, raw_file, panel):
    import torch  # noqa: PLC0415
    from auto_model import AutoNet  # noqa: PLC0415

    if not torch.backends.mps.is_available():
        raise RuntimeError("MPS unavailable; full recount requires the registered device")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not state or any(not isinstance(v, torch.Tensor) for v in state.values()):
        raise ValueError(f"{checkpoint}: expected a bare model state_dict")
    net = AutoNet()
    nparams = sum(p.numel() for p in net.parameters())
    if nparams != EXPECTED_PARAMETERS or not all(p.requires_grad for p in net.parameters()):
        raise ValueError(f"{checkpoint}: model parameter contract failed ({nparams})")
    net.load_state_dict(state, strict=True)
    net.to("mps").eval()
    mismatches = {"predictions": 0, "stop_probabilities": 0, "context_probabilities": 0}
    examples = []
    for i, (item, raw) in enumerate(zip(panel, read_stream(raw_file, panel), strict=True)):
        tokens = torch.tensor([item["tokens"]], dtype=torch.long, device="mps")
        slots = torch.tensor([item["slot"]], dtype=torch.long, device="mps")
        preds, stops, contexts = net.infer(tokens, slots, rounds=48)
        actual = {"predictions": preds[0].tolist(),
                  "stop_probabilities": stops[0].tolist(),
                  "context_probabilities": contexts[0].tolist()}
        for key in mismatches:
            if actual[key] != raw[key]:
                mismatches[key] += 1
                if len(examples) < 12:
                    examples.append({"row": i, "id": item["id"], "field": key})
    return {"parameters": nparams, "device": "mps", "requests": len(panel),
            "mismatches": mismatches, "examples": examples}


def recount(root: Path, no_model: bool):
    report = {"status": "OK", "mode": "raw-only" if no_model else "full",
              "runs": {}, "errors": [], "missing": [], "panel_files": {}}
    try:
        registered = subprocess.check_output(
            ["git", "show", f"{REGISTRATION}:artifacts/codex-autoroute-20260927/PASSMARKS.md"],
            cwd=REPO)
        if registered != (HERE / "PASSMARKS.md").read_bytes():
            report["errors"].append("PASSMARKS.md differs from the pushed registration commit")
    except (OSError, subprocess.CalledProcessError) as exc:
        report["errors"].append(f"cannot verify registered PASSMARKS.md: {exc}")
    manifests = {}
    for seed in SEEDS:
        panel_path = root.parent / "panels" / f"seed{seed}.json"
        if not panel_path.is_file():
            report["missing"].append(str(panel_path))
            continue
        try:
            panel = load_panel(panel_path, seed)
            report["panel_files"][str(seed)] = {"path": str(panel_path),
                                                 "sha256": hashlib.sha256(panel_path.read_bytes()).hexdigest()}
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            report["errors"].append(str(exc))
            continue
        for arm in ARMS:
            label = f"{arm}-s{seed}"
            run_dir = root / label
            result_path = run_dir / "result.json"
            if not result_path.is_file():
                report["missing"].append(str(result_path))
                continue
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.is_file():
                report["missing"].append(str(manifest_path))
                continue
            try:
                result = read_json(result_path)
                if not isinstance(result, dict) or result.get("complete") is not True:
                    report["missing"].append(f"{result_path}: incomplete")
                    continue
                if result.get("arm") != arm or result.get("seed") != seed:
                    raise ValueError(f"{label}: result identity mismatch")
                if result.get("parameters") != EXPECTED_PARAMETERS or type(result.get("parameters")) is not int:
                    raise ValueError(f"{label}: declared parameter count mismatch")
                if result.get("device") != "mps":
                    raise ValueError(f"{label}: declared device is not mps")
                if result.get("precision") != "float32" or result.get("batch_size") != 64:
                    raise ValueError(f"{label}: declared precision/batch size mismatch")
                manifest = read_json(manifest_path)
                if not isinstance(manifest, dict) or manifest.get("device") != "mps":
                    raise ValueError(f"{label}: invalid MPS manifest")
                if manifest.get("registration_commit") != REGISTRATION:
                    raise ValueError(f"{label}: manifest registration commit mismatch")
                if manifest.get("software_commit") != result.get("software_commit"):
                    raise ValueError(f"{label}: manifest/result software commit mismatch")
                if manifest.get("panel_sha256") != report["panel_files"][str(seed)]["sha256"]:
                    raise ValueError(f"{label}: panel hash mismatch")
                hashes = source_manifest(manifest, label)
                manifests[label] = hashes
                out = {"scores": {}, "stopping": {}, "raw_files": {}}
                for phase in PHASES:
                    path = raw_path(run_dir, result, phase)
                    if not path.is_file():
                        report["missing"].append(str(path))
                        continue
                    if result["phases"][phase].get("predictions_sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
                        raise ValueError(f"{label}:{phase}: raw stream hash mismatch")
                    scores, stopping = recount_stream(path, panel["final"])
                    compare_scores(scores, result.get("phases", {}).get(phase, {}).get("score"), f"{label}:{phase}")
                    out["scores"][phase], out["stopping"][phase] = scores, stopping
                    out["raw_files"][phase] = str(path)
                diagnostic_file = run_dir / "diagnostic.jsonl"
                if not diagnostic_file.is_file():
                    report["missing"].append(str(diagnostic_file))
                elif "C" in out["raw_files"]:
                    out["context_agreement"] = recount_context(
                        diagnostic_file, panel["diagnostic"], Path(out["raw_files"]["C"]),
                        panel["final"], result.get("routing_report_only"))
                if not no_model:
                    checkpoint = run_dir / "final.pt"
                    if not checkpoint.is_file():
                        report["missing"].append(str(checkpoint))
                    elif "C" in out["raw_files"]:
                        if result.get("final_sha256") != hashlib.sha256(checkpoint.read_bytes()).hexdigest():
                            raise ValueError(f"{label}: final checkpoint hash mismatch")
                        out["checkpoint_replay"] = replay_checkpoint(
                            checkpoint, Path(out["raw_files"]["C"]), panel["final"])
                        if any(out["checkpoint_replay"]["mismatches"].values()):
                            raise ValueError(f"{label}: final checkpoint differs from raw C predictions")
                report["runs"][label] = out
            except (OSError, UnicodeError, ValueError, TypeError, RuntimeError, KeyError) as exc:
                report["errors"].append(f"{label}: {exc}")
    if manifests and any(value != next(iter(manifests.values())) for value in manifests.values()):
        report["errors"].append("source hash manifests differ across runs")
    if report["missing"]:
        report["status"] = "INCOMPLETE"
    elif report["errors"]:
        report["status"] = "INVALID"
    elif len(report["runs"]) != 12 or any(len(run["scores"]) != 3 for run in report["runs"].values()):
        report["status"] = "INCOMPLETE"
    elif no_model:
        report["status"] = "RAW ONLY"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=HERE / "run")
    parser.add_argument("--out", required=True, type=Path, help="new .json report path in this artifact directory")
    parser.add_argument("--no-model", action="store_true", help="interim raw recount without checkpoint replay")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.suffix != ".json" or not out.is_relative_to(HERE) or not out.parent.is_dir():
        parser.error("--out must be a .json path in an existing directory under this artifact folder")
    if out.exists():
        parser.error(f"refusing to overwrite {out}")
    report = recount(args.root.resolve(), args.no_model)
    with out.open("x", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(f"{report['status']}: {out}")


if __name__ == "__main__":
    main()
