#!/usr/bin/env python3
"""Independent, registered recount of four saved R1/R2 checkpoints; no training."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import random
import re
import shlex
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True

ART = Path(__file__).resolve().parents[1]
REPO = ART.parents[1]
REL = "artifacts/codex-retention-20260927/verify/PASSMARKS.md"
R1_MARKS = "artifacts/codex-retention-20260927/PASSMARKS.md"
R2_MARKS = "artifacts/codex-retention-20260927/r2/PASSMARKS.md"
R2_COMMIT = "57d6f5cfdb7a6416e1c41beb52ac9c778dcd95a7"
R1_RUNNER = "artifacts/codex-retention-20260927/reasoner/codex_retention_reasoner.py"
R2_RUNNER = "artifacts/codex-retention-20260927/r2/run_mastered.py"
SOURCE_ROOTS = ("scripts/claude_rsn358e_moe.py", "scripts/claude_rsn358a2_run.py", R1_RUNNER)
RUNS = (("R1", 29), ("R1", 30), ("R2", 31), ("R2", 32))
EXPECTED_PARAMS = 1_646_750


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc() -> str:
    return subprocess.check_output(["date", "-u", "+%Y-%m-%d %H:%M:%S UTC"], text=True).strip()


def save_report(out: Path, report: dict) -> None:
    """Keep each completed seed on disk even if a later seed raises."""
    temporary = out / "recount.json.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, out / "recount.json")


def gate(commit: str) -> tuple[dict, Path]:
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", commit):
        raise ValueError("a full --passmarks-sha commit ID is required")
    if git("cat-file", "-t", commit).strip() != b"commit":
        raise ValueError("--passmarks-sha must name a commit")
    if git("show", f"{commit}:{REL}") != (REPO / REL).read_bytes():
        raise ValueError("verifier PASSMARKS differ from the supplied commit")
    inputs = {}
    for label, seed in RUNS:
        root = ART / ("reasoner" if label == "R1" else "r2") / f"seed{seed}"
        result = json.loads((root / "result.json").read_text())
        if (not result.get("end_utc") or not isinstance(result.get("criteria"), dict)
                or set(result.get("phases", {})) != {"grids", "sums"}):
            raise RuntimeError(f"INCOMPLETE: {label} seed {seed} has no completed result")
        for kind in ("grids", "sums"):
            p = root / f"snapshot-{kind}.pt"
            if not p.is_file() or p.stat().st_size == 0:
                raise RuntimeError(f"INCOMPLETE: missing {p}")
        inputs[f"{label}-{seed}"] = (root, result)
    out = ART / "verify" / f"recount-{commit[:12].lower()}"
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    return inputs, out


def note(checks: dict, mismatches: list[str], key: str, actual, expected) -> None:
    ok = type(actual) is type(expected) and actual == expected
    checks[key] = ok
    if not ok:
        def compact(value):
            return f"sha256:{sha(value)}" if isinstance(value, bytes) else repr(value)
        mismatches.append(f"{key}: got {compact(actual)}; expected {compact(expected)}")


def local_source_chain() -> list[str]:
    """Follow import-time local Python imports without executing any project code.

    The runners prepend scripts/ to sys.path. Function bodies and __main__ blocks
    are excluded: their unrelated optional imports are not part of model import.
    """
    try_nodes = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())

    def is_main_guard(test: ast.expr) -> bool:
        return (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
                and test.left.id == "__name__" and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == "__main__")

    def import_time(stmts):
        for node in stmts:
            if isinstance(node, ast.Import):
                yield from (alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                yield node.module
            elif isinstance(node, ast.If):
                if not is_main_guard(node.test):
                    yield from import_time(node.body)
                yield from import_time(node.orelse)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
                yield from import_time(node.body)
                yield from import_time(getattr(node, "orelse", []))
            elif isinstance(node, try_nodes):
                yield from import_time(node.body)
                for handler in node.handlers:
                    yield from import_time(handler.body)
                yield from import_time(node.orelse)
                yield from import_time(node.finalbody)

    pending = [REPO / rel for rel in SOURCE_ROOTS]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for module in import_time(tree.body):
            local = REPO / "scripts" / (module.replace(".", "/") + ".py")
            if local.is_file() and local not in seen:
                pending.append(local)
    return sorted(path.relative_to(REPO).as_posix() for path in seen)


def source_checks(inputs: dict, checks: dict, mismatches: list[str]) -> dict:
    hashes = {}
    chain = local_source_chain()
    required = {"scripts/claude_rsn358m_run.py", "scripts/claude_rsn358t_run.py",
                "scripts/claude_rsn358i2_run.py"}
    note(checks, mismatches, "transitive_chain_includes_MR_T_I2", required <= set(chain), True)
    for rel in chain:
        local = (REPO / rel).read_bytes()
        hashes[rel] = sha(local)
        for label, seed in RUNS:
            head = inputs[f"{label}-{seed}"][1]["software_head"]
            note(checks, mismatches, f"source/{label}-{seed}/{rel}", local, git("show", f"{head}:{rel}"))
    local = (REPO / R2_RUNNER).read_bytes()
    hashes[R2_RUNNER] = sha(local)
    note(checks, mismatches, "r2_registered_runner_bytes", local, git("show", f"{R2_COMMIT}:{R2_RUNNER}"))
    for seed in (31, 32):
        head = inputs[f"R2-{seed}"][1]["software_head"]
        note(checks, mismatches, f"source/R2-{seed}/{R2_RUNNER}", local,
             git("show", f"{head}:{R2_RUNNER}"))
    note(checks, mismatches, "r2_registered_marks_bytes", (REPO / R2_MARKS).read_bytes(),
         git("show", f"{R2_COMMIT}:{R2_MARKS}"))
    for label, seed in RUNS:
        result = inputs[f"{label}-{seed}"][1]
        rel = R1_MARKS if label == "R1" else R2_MARKS
        note(checks, mismatches, f"{label}-{seed}/run_marks_bytes", (REPO / rel).read_bytes(),
             git("show", f"{result['passmarks_commit']}:{rel}"))
        if label == "R2":
            note(checks, mismatches, f"{label}-{seed}/r2_registration_commit",
                 result["passmarks_commit"], R2_COMMIT)
    return hashes


def panels_for(E, seed: int) -> dict:
    rng = random.Random(92000 + seed)
    return {
        "grids5": [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(200)],
        "sums4": [E.make_sum(rng, 4) for _ in range(200)],
    }


def state_hash(state) -> str:
    h = hashlib.sha256()
    for key, value in state.items():
        h.update(key.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def score_from_arrays(d: dict) -> dict:
    return {"right": sum(d["own_stop"]), "fixed16": sum(d["fixed16"]),
            "any48": sum(d["any48"]),
            "mean_rounds": round(sum(x + 1 for x in d["stop_round_zero_based"]) / 200, 2)}


def transition(before: list[bool], after: list[bool]) -> dict:
    return {"previously_correct_items_lost": sum(a and not b for a, b in zip(before, after)),
            "previously_incorrect_items_gained": sum(not a and b for a, b in zip(before, after))}


def execute(inputs: dict, out: Path, report: dict) -> None:
    checks: dict[str, bool] = report["checks"]
    mismatches: list[str] = report["mismatches"]
    hashes = source_checks(inputs, checks, mismatches)
    report["source_sha256"] = hashes
    if mismatches:
        report["verifier_status"] = "FAIL"
        report["reason"] = "source/protocol provenance mismatch before model load"
        save_report(out, report)
        raise AssertionError(f"{len(mismatches)} provenance mismatches; see {out / 'recount.json'}")
    sys.path.insert(0, str(REPO / "scripts"))
    import torch
    import claude_rsn358e_moe as X
    import claude_rsn358a2_run as A2
    R, E = X.R, X.E
    report["torch"] = str(torch.__version__)
    for label, seed in RUNS:
        note(checks, mismatches, f"{label}-{seed}/torch_version", str(torch.__version__),
             inputs[f"{label}-{seed}"][1]["torch"])
    if mismatches:
        report["verifier_status"] = "FAIL"
        report["reason"] = "Torch version differs from saved run before model load"
        save_report(out, report)
        raise AssertionError(f"{len(mismatches)} environment mismatches; see {out / 'recount.json'}")
    if not torch.backends.mps.is_available():
        raise RuntimeError("INCOMPLETE: MPS unavailable; no CPU substitute")
    device = "mps"
    report["device"] = device
    torch.set_num_threads(4)

    def load_checked(root: Path, result: dict, label: str, seed: int, kind: str):
        path = root / f"snapshot-{kind}.pt"
        phase = result["phases"][kind]
        name = f"{label}-{seed}/{kind}"
        recorded = Path(phase["snapshot"])
        expected_suffix = path.relative_to(REPO).parts
        note(checks, mismatches, f"{name}/artifact_path_suffix",
             recorded.parts[-len(expected_suffix):], expected_suffix)
        provenance = report.setdefault("checkpoint_provenance", {})
        file_sha256 = sha(path.read_bytes())
        if name in provenance:
            note(checks, mismatches, f"{name}/file_sha256_stable_across_loads",
                 file_sha256, provenance[name]["loaded_file_sha256"])
        else:
            provenance[name] = {"recorded_path": str(recorded), "loaded_path": str(path),
                                "loaded_file_sha256": file_sha256}
        note(checks, mismatches, f"{name}/bytes", path.stat().st_size, phase["checkpoint_bytes"])
        ck = torch.load(path, map_location="cpu", weights_only=True)
        note(checks, mismatches, f"{name}/checkpoint_fields", set(ck),
             {"arm", "size", "kind", "step", "seed", "state"})
        for key, expected in (("arm", "dense"), ("size", "small"), ("kind", kind),
                              ("step", (6000 if label == "R2" else 2500) if kind == "grids" else 2500),
                              ("seed", seed)):
            note(checks, mismatches, f"{name}/metadata/{key}", ck.get(key), expected)
        net = X.make_net("dense", "small")
        state = ck["state"]
        note(checks, mismatches, f"{name}/state_keys", list(state), list(net.state_dict()))
        note(checks, mismatches, f"{name}/state_shapes",
             {k: tuple(v.shape) for k, v in state.items()},
             {k: tuple(v.shape) for k, v in net.state_dict().items()})
        note(checks, mismatches, f"{name}/state_dtypes",
             {k: str(v.dtype) for k, v in state.items()},
             {k: str(v.dtype) for k, v in net.state_dict().items()})
        note(checks, mismatches, f"{name}/parameters", sum(p.numel() for p in net.parameters()), EXPECTED_PARAMS)
        note(checks, mismatches, f"{name}/state_sha256", state_hash(state), phase["sha256_state"])
        net.load_state_dict(state, strict=True)
        net = net.to(device).eval()
        for p in net.parameters():
            p.requires_grad_(False)
        return net, path.stat().st_size

    @torch.inference_mode()
    def recount(net, items) -> dict:
        out_arrays = {"own_stop": [], "fixed16": [], "any48": [], "stop_round_zero_based": []}
        for i in range(0, len(items), 50):
            chunk = items[i:i + 50]
            t, s, _, env = R.tensors(chunk, device)
            preds, qs = net.loop_rounds(t, s, env, 48)
            for it, p, q in zip(chunk, preds.tolist(), qs.tolist()):
                stop = A2.stop_round(p, q, 48)
                own = bool(E.check(it, R.grid_of(p[stop], it)))
                fixed = bool(E.check(it, R.grid_of(p[15], it)))
                any_round = any(bool(E.check(it, R.grid_of(row, it))) for row in p)
                out_arrays["own_stop"].append(own)
                out_arrays["fixed16"].append(fixed)
                out_arrays["any48"].append(any_round)
                out_arrays["stop_round_zero_based"].append(stop)
        return out_arrays

    @torch.inference_mode()
    def signature(net, items):
        t, s, _, env = R.tensors(items[:16], device)
        p, q = net.loop_rounds(t, s, env, 48)
        return p.cpu().clone(), q.cpu().clone()

    def sig_equal(a, b) -> bool:
        return bool(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1]))

    def route(kind, models):
        if kind not in ("grids", "sums"):
            raise ValueError("unknown task ID")
        return models[kind]

    r1_statuses, r2_statuses = [], []
    for label, seed in RUNS:
        root, result = inputs[f"{label}-{seed}"]
        name = f"{label}-{seed}"
        note(checks, mismatches, f"{name}/seed", result["seed"], seed)
        note(checks, mismatches, f"{name}/held_seed", result["held_seed"], 92000 + seed)
        note(checks, mismatches, f"{name}/device", result["device"], device)
        note(checks, mismatches, f"{name}/parameter_report", result["parameters_per_snapshot"], EXPECTED_PARAMS)
        note(checks, mismatches, f"{name}/total_parameter_report",
             result["total_parameters_across_two_snapshots"], 2 * EXPECTED_PARAMS)
        note(checks, mismatches, f"{name}/steps_report", {k: result["phases"][k]["steps"] for k in ("grids", "sums")},
             {"grids": 6000 if label == "R2" else 2500, "sums": 2500})
        if label == "R2":
            note(checks, mismatches, f"{name}/top_steps_report", result["steps"],
                 {"grids": 6000, "sums": 2500})
        panels = panels_for(E, seed)
        for panel_name, items in panels.items():
            note(checks, mismatches, f"{name}/{panel_name}/item_count", len(items), 200)
            fingerprints = {(it.env, it.size, tuple(tuple(row) for row in it.tokens)) for it in items}
            note(checks, mismatches, f"{name}/{panel_name}/unique_inputs", len(fingerprints), 200)
        models, sizes, arrays = {}, {}, {}
        for kind in ("grids", "sums"):
            models[kind], sizes[kind] = load_checked(root, result, label, seed, kind)
            arrays[kind] = {}
            for panel_name, items in panels.items():
                d = recount(models[kind], items)
                arrays[kind][panel_name] = d
                note(checks, mismatches, f"{name}/{kind}/{panel_name}/score",
                     score_from_arrays(d), result["phases"][kind]["score_current"][panel_name])
        note(checks, mismatches, f"{name}/total_bytes", sum(sizes.values()), result["total_checkpoint_bytes"])
        routed_scores = {"grids": {"grids5": score_from_arrays(arrays["grids"]["grids5"])},
                         "sums": {"grids5": score_from_arrays(arrays["grids"]["grids5"]),
                                  "sums4": score_from_arrays(arrays["sums"]["sums4"])}}
        for kind in ("grids", "sums"):
            note(checks, mismatches, f"{name}/{kind}/routed_score", routed_scores[kind],
                 result["phases"][kind]["score_routed"])
        a_grid = arrays["grids"]["grids5"]["own_stop"]
        b_grid = arrays["sums"]["grids5"]["own_stop"]
        latest_delta = transition(a_grid, b_grid)
        routed_delta = transition(a_grid, arrays["grids"]["grids5"]["own_stop"])
        isolation = result["phases"]["sums"]["grid_isolation"]
        for k, v in routed_delta.items():
            note(checks, mismatches, f"{name}/grid_isolation/{k}", v, isolation[k])
        for k in ("bit_identical_weights", "bit_identical_predictions_and_stop_probabilities",
                  "snapshot_hash_unchanged", "per_item_exactness_identical"):
            note(checks, mismatches, f"{name}/grid_isolation/{k}", isolation[k], True)
        if label == "R2":
            mutable = result["phases"]["sums"]["mutable_control_vs_A"]
            for k, v in latest_delta.items():
                note(checks, mismatches, f"{name}/mutable_control/{k}", v, mutable[k])
            note(checks, mismatches, f"{name}/mutable_control/grids5_after_B",
                 sum(b_grid), mutable["grids5_after_B"])
            note(checks, mismatches, f"{name}/A_itemwise_consistent",
                 sum(a_grid) == routed_scores["grids"]["grids5"]["right"],
                 result["phases"]["grids"]["score_and_itemwise_consistent"])
            note(checks, mismatches, f"{name}/A_checkpoint_trained_match_report",
                 result["phases"]["grids"]["checkpoint_weights_match_trained_A"], True)
        for kind in ("grids", "sums"):
            expected_item = panels["grids5"] if kind == "grids" else panels["sums4"]
            model = models[kind]
            reloaded, _ = load_checked(root, result, label, seed, kind)
            note(checks, mismatches, f"{name}/{kind}/reload_signature",
                 sig_equal(signature(model, expected_item), signature(reloaded, expected_item)), True)
            for panel_name, items in panels.items():
                note(checks, mismatches, f"{name}/{kind}/{panel_name}/reload_itemwise",
                     recount(reloaded, items), arrays[kind][panel_name])
            note(checks, mismatches, f"{name}/{kind}/reported_roundtrip",
                 result["phases"][kind]["snapshot_roundtrip_all_rounds_identical"], True)
        # Alternating known caller IDs, then fresh independent reloads of both routes.
        tasks = (("grids", panels["grids5"]), ("sums", panels["sums4"]),
                 ("grids", panels["grids5"]))
        before = [signature(route(k, models), items) for k, items in tasks]
        fresh = {k: load_checked(root, result, label, seed, k)[0] for k in ("grids", "sums")}
        after = [signature(route(k, fresh), items) for k, items in tasks]
        restart = result["restart_routing"]
        note(checks, mismatches, f"{name}/restart/task_ids", [k for k, _ in tasks], restart["alternating_task_ids"])
        note(checks, mismatches, f"{name}/restart/signatures",
             all(sig_equal(a, b) for a, b in zip(before, after)), restart["exact_outputs_and_stop_probabilities"])
        note(checks, mismatches, f"{name}/restart/grid_repeat", sig_equal(after[0], after[2]),
             restart["first_and_third_grid_requests_identical"])
        note(checks, mismatches, f"{name}/restart/grid_score_unchanged",
             routed_scores["grids"]["grids5"] == routed_scores["sums"]["grids5"],
             restart["grid_score_unchanged"])
        try:
            route("unknown", fresh)
        except ValueError:
            unknown_rejected = True
        else:
            unknown_rejected = False
        note(checks, mismatches, f"{name}/restart/unknown_rejected", unknown_rejected,
             restart["unknown_task_rejected"])
        a = sum(a_grid)
        b = sum(arrays["sums"]["sums4"]["own_stop"])
        route_a = routed_scores["sums"]["grids5"]["right"]
        if label == "R1":
            criteria = {"A_mastery_190": a >= 190, "B_mastery_190": b >= 190,
                        "retained_A_190": route_a >= 190,
                        "isolation": routed_delta["previously_correct_items_lost"] == 0
                        and routed_delta["previously_incorrect_items_gained"] == 0
                        and all(isolation[k] for k in ("bit_identical_weights",
                            "bit_identical_predictions_and_stop_probabilities", "per_item_exactness_identical"))}
            registered_controls = (criteria["isolation"] and isolation["snapshot_hash_unchanged"]
                                   and all(result["phases"][k]["snapshot_roundtrip_all_rounds_identical"]
                                           for k in ("grids", "sums"))
                                   and all(restart[k] for k in restart if k != "alternating_task_ids")
                                   and routed_scores["grids"]["grids5"] == routed_scores["sums"]["grids5"])
            r1_statuses.append({**criteria, "registered_controls": registered_controls})
        else:
            valid = a >= 190 and b >= 190
            isolated = (routed_delta["previously_correct_items_lost"] == 0
                        and routed_delta["previously_incorrect_items_gained"] == 0
                        and all(isolation[k] for k in ("bit_identical_weights",
                            "bit_identical_predictions_and_stop_probabilities", "snapshot_hash_unchanged",
                            "per_item_exactness_identical"))
                        and all(result["phases"]["grids"][k] for k in
                                ("checkpoint_weights_match_trained_A", "snapshot_roundtrip_all_rounds_identical",
                                 "score_and_itemwise_consistent"))
                        and result["phases"]["sums"]["snapshot_roundtrip_all_rounds_identical"]
                        and all(restart[k] for k in restart if k != "alternating_task_ids"))
            criteria = {"A_mastery_190": a >= 190, "B_mastery_190": b >= 190,
                        "isolation": isolated,
                        "baseline_forgetting_reproduced": latest_delta["previously_correct_items_lost"] > 0,
                        "seed_status": "INCONCLUSIVE_MASTERY" if not valid else
                        ("PASS_CONTROLS" if isolated else "FAIL_ISOLATION")}
            r2_statuses.append(criteria)
        note(checks, mismatches, f"{name}/criteria", criteria, result["criteria"])
        report["runs"][name] = {"score_recount": {k: {p: score_from_arrays(d) for p, d in v.items()}
                                                  for k, v in arrays.items()},
                                "per_item": arrays, "routed_scores": routed_scores,
                                "grid_A_to_latest_B": latest_delta, "grid_A_to_routed_A": routed_delta,
                                "criteria_recount": criteria, "checkpoint_bytes": sizes}
        report["completed_seeds"].append(name)
        save_report(out, report)
    report["aggregate"] = {
        "R1": "PASS" if all(all(c.values()) for c in r1_statuses) else
              ("INCONCLUSIVE" if any(not c["A_mastery_190"] or not c["B_mastery_190"]
                                    for c in r1_statuses) else "FAIL"),
        "R2": "INCONCLUSIVE" if any(not c["A_mastery_190"] or not c["B_mastery_190"]
                                    for c in r2_statuses) else
              ("PASS" if all(c["isolation"] for c in r2_statuses) else "FAIL"),
    }
    note(checks, mismatches, "R1_seed29_inconclusive", r1_statuses[0]["A_mastery_190"], False)
    note(checks, mismatches, "R1_aggregate", report["aggregate"]["R1"], "INCONCLUSIVE")
    report["verifier_status"] = "PASS" if not mismatches else "FAIL"
    if mismatches:
        raise AssertionError(f"{len(mismatches)} saved-result mismatches; see {out / 'recount.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passmarks-sha", required=True)
    args = parser.parse_args()
    inputs, out = gate(args.passmarks_sha)  # No output or Torch import before the committed-byte gate.
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    start_utc = utc()
    machine = platform.node()
    pid = os.getpid()
    head = git("rev-parse", "HEAD").decode().strip()
    command = shlex.join([sys.executable, *sys.argv])
    (out / "RUN-NOTE.md").write_text(
        f"# Independent saved-checkpoint recount\n\nUTC start (`date -u`): {start_utc}\n"
        f"Machine: {machine}\nPID: {pid}\nSoftware HEAD: `{head}`\n"
        f"PASSMARKS commit: `{args.passmarks_sha}`\nCommand: `{command}`\n",
        encoding="utf-8")
    report = {"verifier": "saved-checkpoint software recount", "verifier_status": "RUNNING",
              "passmarks_commit": args.passmarks_sha,
              "verifier_source_sha256": sha(Path(__file__).read_bytes()),
              "start_utc": start_utc, "machine": machine, "pid": pid,
              "software_head": head, "command": command,
              "runs": {}, "completed_seeds": [], "checks": {}, "mismatches": []}
    save_report(out, report)
    try:
        execute(inputs, out, report)
    except BaseException as exc:
        (out / "CRASH.txt").write_text(traceback.format_exc(), encoding="utf-8")
        if report["verifier_status"] == "RUNNING":
            report["verifier_status"] = ("INCOMPLETE" if str(exc).startswith("INCOMPLETE:")
                                         else "FAIL")
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["end_utc"] = utc()
        report["wall_seconds"] = round(time.monotonic() - started, 1)
        save_report(out, report)
        raise
    report["end_utc"] = utc()
    report["wall_seconds"] = round(time.monotonic() - started, 1)
    save_report(out, report)
    print(json.dumps({"verifier_status": report["verifier_status"], "aggregate": report["aggregate"],
                      "output": str(out), "mismatches": len(report["mismatches"])}), flush=True)


if __name__ == "__main__":
    main()
