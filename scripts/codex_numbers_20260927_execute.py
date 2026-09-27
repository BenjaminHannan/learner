#!/usr/bin/env python3
"""Sequential supervisor for the registered small-number experiment.

This module does no work on import. ``validate`` checks registration and config;
``run`` is the only command that trains or evaluates. Registration files live in
artifacts/codex-numbers-20260927/: EXPERIMENT.json and SEAL-code.json. The seal
schema is {"files": {"repo/relative/path": "sha256 hex", ...}} and must include
EXPERIMENT.json, this script, the runner, labels, and panel maker.

EXPERIMENT.json schema: python, device, seeds (four or more),
sealed_seed, train (steps, batch, width, layers, heads, latin_pool, lr, warmup,
log_every), eval_batch, registered_panel_sha256 (the four immutable 358i test
files), and diagnostic_gate (a preregistered baseline memorization receipt).
Pass the pushed registration commit on the command
line; embedding its hash in its own committed config would be circular. A
training failure or interrupted evaluation requires explicit audited recovery;
this supervisor never silently repeats a sealed evaluation.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import gzip
import hashlib
import inspect
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts/codex-numbers-20260927"
CONFIG = ART / "EXPERIMENT.json"
SEAL = ART / "SEAL-code.json"
PASSMARKS = ART / "PASSMARKS.md"
RUNNER = ROOT / "scripts/codex_numbers_20260927_run.py"
PANELS = ROOT / "scripts/codex_numbers_20260927_panels.py"
RUNS = ART / "registered"
FROZEN = ART / "CHECKPOINTS-FROZEN.json"
PANEL_NAMES = ("numbers4", "numbers5", "sums4", "grids5", "numbers5_old")
LEGACY_TESTS = ROOT / "artifacts/claude-rsn358i-20260926/tests"
LEGACY_PANELS = {"numbers4": LEGACY_TESTS / "numbers4.jsonl",
                 "sums4": LEGACY_TESTS / "sums4.jsonl",
                 "grids5": LEGACY_TESTS / "grids5.jsonl",
                 "numbers5_old": LEGACY_TESTS / "numbers5.jsonl"}
REQUIRED_SEAL = (
    "artifacts/codex-numbers-20260927/EXPERIMENT.json",
    "scripts/codex_numbers_20260927_execute.py",
    "scripts/codex_numbers_20260927_recount.py",
    "scripts/codex_numbers_20260927_report.py",
    "scripts/codex_numbers_20260927_cards.py",
    "scripts/codex_numbers_20260927_cardcheck.py",
    "scripts/codex_numbers_20260927_run.py",
    "scripts/codex_numbers_20260927_labels.py",
    "scripts/codex_numbers_20260927_panels.py",
    "scripts/claude_rsn358i_run.py",
    "scripts/claude_rsn358g_run.py",
    "scripts/claude_rsn358a2_run.py",
    "scripts/claude_rsn358a_run.py",
    "scripts/claude_rsn358a_envs.py",
    "scripts/claude_blurt1.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            digest.update(part)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def create_json(path: Path, obj: dict) -> None:
    """Exclusive file creation; a stale marker needs explicit audited recovery."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(*args: str, capture: bool = False) -> bytes | None:
    p = subprocess.run(["git", *args], cwd=ROOT, check=True,
                       stdout=subprocess.PIPE if capture else None)
    return p.stdout if capture else None


def verify_local_seal(expected_seal_sha256: str | None = None) -> None:
    if expected_seal_sha256 is not None and sha256(SEAL) != expected_seal_sha256:
        raise RuntimeError("SEAL-code.json changed during the experiment")
    files = read_json(SEAL)["files"]
    if not isinstance(files, dict) or not set(REQUIRED_SEAL) <= files.keys():
        raise ValueError(f"seal must include {REQUIRED_SEAL}")
    for relative, expected in files.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"invalid sealed path: {relative}")
        if sha256(path) != expected:
            raise RuntimeError(f"source changed after registration: {relative}")


def verify_registration(commit: str) -> dict:
    cfg, seal = read_json(CONFIG), read_json(SEAL)
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("registration_commit must be a full lowercase SHA-1")
    git("fetch", "origin", "main")
    git("merge-base", "--is-ancestor", commit, "origin/main")
    for path in (PASSMARKS, SEAL):
        relative = path.relative_to(ROOT).as_posix()
        pushed = git("show", f"{commit}:{relative}", capture=True)
        if pushed != path.read_bytes():
            raise RuntimeError(f"local {relative} differs from pushed registration")
    if "files" not in seal:
        raise ValueError("SEAL-code.json needs a files map")
    verify_local_seal()
    seeds = cfg["seeds"]
    if len(seeds) < 4 or len(set(seeds)) != len(seeds) or not all(isinstance(x, int) for x in seeds):
        raise ValueError("at least four distinct integer training seeds are required")
    if cfg["sealed_seed"] != 9276501:
        raise ValueError("sealed_seed must be the registered 9276501")
    if cfg["device"] != "mps":
        raise ValueError("registered training and eval require MPS")
    if not (ROOT / cfg["python"]).is_file():
        raise ValueError("configured Python is missing")
    expected_train = {"steps", "batch", "width", "layers", "heads", "latin_pool", "lr", "warmup", "log_every"}
    if set(cfg["train"]) != expected_train:
        raise ValueError(f"train settings must be exactly {sorted(expected_train)}")
    if cfg["train"]["width"] % cfg["train"]["heads"]:
        raise ValueError("width must divide heads")
    if cfg["eval_batch"] <= 0:
        raise ValueError("eval_batch must be positive")
    registered = cfg["registered_panel_sha256"]
    if set(registered) != set(LEGACY_PANELS):
        raise ValueError("registered_panel_sha256 must cover four immutable 358i test files")
    for name, expected in registered.items():
        path = LEGACY_PANELS[name]
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"registered source panel changed or missing: {name}: {path}")
    gate_ref = cfg["diagnostic_gate"]
    if set(gate_ref) != {"summary_path", "summary_sha256", "manifest_path", "manifest_sha256"}:
        raise ValueError("diagnostic_gate must pin the summary and dev-split manifest")
    summary_path = (ROOT / gate_ref["summary_path"]).resolve()
    manifest_path = (ROOT / gate_ref["manifest_path"]).resolve()
    if any(not path.is_relative_to(ART) or not path.is_file() or sha256(path) != gate_ref[key]
           for path, key in ((summary_path, "summary_sha256"),
                             (manifest_path, "manifest_sha256"))):
        raise RuntimeError("preregistered diagnostic evidence missing or changed")
    evidence, split = read_json(summary_path), read_json(manifest_path)
    checkpoint = summary_path.parent / "final.pt"
    practice = manifest_path.parent / "diagnostic-panels/train_numbers4.jsonl"
    if not checkpoint.is_file() or sha256(checkpoint) != evidence["checkpoint_sha256"] or \
            not practice.is_file() or sha256(practice) != split["panel_sha256"]["train_numbers4"]:
        raise RuntimeError("diagnostic checkpoint or practice panel changed")
    if split["train_four_count"] != 962 or split["dev_four_count"] != 100 or \
            len({tuple(x) for x in split["train_four_hands"]} &
                {tuple(x) for x in split["dev_four_hands"]}) != 0:
        raise RuntimeError("diagnostic practice/dev split is not 962/100 disjoint hands")
    scores = evidence["final_probe"]["scores"]["train_numbers4"]
    if scores["n"] != 962 or scores["exact_stored"] / scores["n"] < .95 or \
            evidence.get("diagnostic_gate_met") is not True:
        raise RuntimeError("diagnostic baseline did not reach 0.95 practice exact")
    if evidence.get("dev_holdout") != 100 or evidence.get("device") != cfg["device"] or \
            evidence.get("dtype") != "float32" or evidence.get("fixed_env") != 0 or \
            evidence.get("arm") != "loop":
        raise RuntimeError("diagnostic split, device, dtype, or env differs from registration")
    for key in ("width", "layers", "heads", "batch", "steps", "lr", "warmup", "latin_pool"):
        if evidence.get(key) != cfg["train"][key]:
            raise RuntimeError(f"diagnostic and registered training differ at {key}")
    return cfg


def _ps_rows() -> list[dict]:
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,%cpu=,comm=,args="],
                                text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("process scan unavailable; no GPU phase may start") from exc
    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) != 5:
            continue
        pid, ppid, cpu, comm, args = parts
        try:
            rows.append({"pid": int(pid), "ppid": int(ppid), "cpu": float(cpu),
                         "name": Path(comm).name, "args": args})
        except ValueError:
            continue
    return rows


def gpu_safety_snapshot(phase: str) -> dict:
    """Fail closed on another visible GPU-capable training or serving process."""
    rows = _ps_rows()
    parents = {r["pid"]: r["ppid"] for r in rows}
    excluded = set()
    pid = os.getpid()
    while pid > 0 and pid not in excluded:
        excluded.add(pid)
        pid = parents.get(pid, 0)
    suspicious = re.compile(r"(?i)(torchrun|accelerate|fine.?tun|(^|[ /_-])train([ /_.-]|$)|"
                            r"mlx|llama|ollama|deepspeed|vllm|codex_numbers_20260927_(run|bench))")
    candidates = []
    for row in rows:
        if row["pid"] in excluded:
            continue
        name = row["name"].lower()
        if suspicious.search(name + " " + row["args"]):
            candidates.append({"pid": row["pid"], "name": row["name"], "cpu": row["cpu"]})
    snapshot = {"phase": phase, "time_unix": time.time(), "self_pid": os.getpid(),
                "excluded_own_ancestor_pids": sorted(excluded), "candidates": candidates,
                "safe": not candidates}
    path = ART / "registered" / "gpu-checks" / f"{int(time.time() * 1000)}-{phase}.json"
    create_json(path, snapshot)
    if candidates:
        raise RuntimeError(f"GPU phase {phase} blocked by visible competing processes: {candidates}")
    return snapshot


def run_order(cfg: dict) -> list[tuple[str, int]]:
    order = []
    for i, seed in enumerate(cfg["seeds"]):
        order.extend((variant, seed) for variant in
                     (("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")))
    return order


def train_one(cfg: dict, variant: str, seed: int, seal_digest: str) -> None:
    out = RUNS / f"{variant}-s{seed}"
    summary_path, ckpt = out / "train_summary.json", out / "final.pt"
    if summary_path.exists() and ckpt.exists():
        summary = read_json(summary_path)
        if summary.get("checkpoint_sha256") != sha256(ckpt):
            raise RuntimeError(f"completed checkpoint hash mismatch: {out}")
        if summary.get("seed") != seed or summary.get("variant") != variant:
            raise RuntimeError(f"completed run identity mismatch: {out}")
        return
    if out.exists():
        raise RuntimeError(f"partial run requires explicit audited recovery: {out}")
    verify_local_seal(seal_digest)
    gpu_safety_snapshot(f"train-{variant}-s{seed}")
    out.mkdir(parents=True)
    python = str(ROOT / cfg["python"])
    command = [python, "-B", str(RUNNER), "train", "--variant", variant,
               "--seed", str(seed), "--device", cfg["device"], "--out", str(out)]
    for name in ("steps", "batch", "width", "layers", "heads", "latin_pool", "lr", "warmup", "log_every"):
        command += ["--" + name.replace("_", "-"), str(cfg["train"][name])]
    started = time.monotonic()
    print(f"starting {variant} seed {seed}: {cfg['train']['steps']} steps on MPS", flush=True)
    with (out / "supervisor.log").open("x", encoding="utf-8") as log:
        completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f"training failed (exit {completed.returncode}); review {out / 'supervisor.log'}")
    if not summary_path.exists() or not ckpt.exists():
        raise RuntimeError(f"training did not save final checkpoint and summary: {out}")
    summary = read_json(summary_path)
    if summary.get("checkpoint_sha256") != sha256(ckpt):
        raise RuntimeError(f"new checkpoint hash mismatch: {out}")
    if summary.get("seed") != seed or summary.get("variant") != variant:
        raise RuntimeError(f"new run identity mismatch: {out}")
    atomic_json(out / "supervisor-summary.json", {"variant": variant, "seed": seed,
                "wall_minutes": (time.monotonic() - started) / 60,
                "checkpoint_sha256": sha256(ckpt)})
    print(f"finished {variant} seed {seed}: {summary['minutes']:.2f} minutes", flush=True)


def freeze_checkpoints(cfg: dict, commit: str) -> dict:
    runs = []
    for variant, seed in run_order(cfg):
        out = RUNS / f"{variant}-s{seed}"
        summary = read_json(out / "train_summary.json")
        digest = sha256(out / "final.pt")
        if summary["checkpoint_sha256"] != digest:
            raise RuntimeError(f"checkpoint changed: {out}")
        if summary["seed"] != seed or summary.get("variant") != variant:
            raise RuntimeError(f"run identity mismatch: {out}")
        if summary["device"] != cfg["device"] or summary["dtype"] != "float32":
            raise RuntimeError(f"device/dtype mismatch: {out}")
        if summary.get("fixed_env") != 0 or summary.get("unused_env_rows") != 2:
            raise RuntimeError(f"fixed-env audit failed: {out}")
        if any(summary[name] != cfg["train"][name] for name in cfg["train"]):
            raise RuntimeError(f"run settings mismatch: {out}")
        grads = summary["gradient_check"]
        if grads["steps_seen"] != cfg["train"]["steps"] or any(
                grads[key] for key in ("steps_block_nograd", "steps_block_missing", "steps_block_allzero")):
            raise RuntimeError(f"gradient audit failed: {out}")
        card_grad = grads.get("card_gradient_check") or {}
        if variant == "candidate":
            samples = card_grad.get("per_parameter_norms")
            counts = card_grad.get("per_parameter_counts")
            if not isinstance(samples, list) or not samples or \
                    card_grad.get("parameters", 0) <= 0 or card_grad.get("multi_grad_steps", 0) <= 0 or \
                    card_grad.get("multi_grad_steps", 0) + \
                    card_grad.get("single_grad_steps_exempt", 0) != cfg["train"]["steps"] or \
                    not isinstance(counts, dict) or len(counts) != card_grad["parameters"] or \
                    any(not isinstance(c, dict) or c.get("nonfinite_steps") != 0 or
                        c.get("nonfinite_any_step") != 0 or
                        c.get("missing_steps", -1) + c.get("finite_steps", -1) != card_grad["multi_grad_steps"] or
                        c.get("nonzero_steps", -1) + c.get("zero_steps", -1) != c.get("finite_steps")
                        for c in counts.values()) or \
                    any(not isinstance(value, (int, float)) or not math.isfinite(value)
                        for sample in samples for key, value in sample.items() if key != "step"):
                raise RuntimeError(f"card gradient audit missing or nonfinite: {out}")
        elif card_grad.get("parameters") != 0:
            raise RuntimeError(f"baseline unexpectedly has card gradients: {out}")
        runs.append({"variant": variant, "seed": seed, "checkpoint": str(out / "final.pt"),
                     "checkpoint_sha256": digest, "summary_sha256": sha256(out / "train_summary.json"),
                     "minutes": summary["minutes"], "weights": summary["weights"],
                     "stream_sha256": summary["stream_sha256"],
                     "base_init_state_sha256": summary["base_init_state_sha256"],
                     "source_hashes": summary["source_hashes"],
                     "runner_script_sha256": summary["script_sha256"],
                     "cache_hashes": summary["cache_hashes"]})
    for seed in cfg["seeds"]:
        baseline = next(x for x in runs if x["seed"] == seed and x["variant"] == "baseline")
        candidate = next(x for x in runs if x["seed"] == seed and x["variant"] == "candidate")
        if baseline["stream_sha256"] != candidate["stream_sha256"]:
            raise RuntimeError(f"unpaired training stream at seed {seed}")
        if baseline["base_init_state_sha256"] != candidate["base_init_state_sha256"]:
            raise RuntimeError(f"unpaired core model initialization at seed {seed}")
        for field in ("source_hashes", "runner_script_sha256", "cache_hashes"):
            if baseline[field] != candidate[field]:
                raise RuntimeError(f"unpaired {field} at seed {seed}")
        if baseline["source_hashes"].get("scratch_cards") != \
                sha256(ROOT / "scripts/codex_numbers_20260927_cards.py"):
            raise RuntimeError(f"unsealed card source at seed {seed}")
        if abs(baseline["weights"] - candidate["weights"]) > 0.01 * baseline["weights"]:
            raise RuntimeError(f"weight-count gap exceeds 1% at seed {seed}")
    manifest = {"registration_commit": commit,
                "experiment_sha256": sha256(CONFIG), "seal_sha256": sha256(SEAL),
                "diagnostic_summary_sha256": cfg["diagnostic_gate"]["summary_sha256"],
                "runs": runs}
    if FROZEN.exists():
        if read_json(FROZEN) != manifest:
            raise RuntimeError("frozen checkpoint manifest differs; explicit audited recovery required")
    else:
        create_json(FROZEN, manifest)
    return manifest


def ensure_sealed(cfg: dict, commit: str) -> Path:
    path = ART / "panels" / "numbers5.jsonl"
    record = ART / "SEALED-PANEL.json"
    if path.exists() or record.exists():
        if not path.exists() or not record.exists():
            raise RuntimeError("partial sealed-panel generation requires explicit audited recovery")
        info = read_json(record)
        if info["registration_commit"] != commit or info["seed"] != cfg["sealed_seed"]:
            raise RuntimeError("sealed-panel registration mismatch")
        if info["sha256"] != sha256(path):
            raise RuntimeError("sealed panel changed")
        return path
    subprocess.run([str(ROOT / cfg["python"]), "-B", str(PANELS), "sealed",
                    "--registration", commit,
                    "--seed", str(cfg["sealed_seed"])], cwd=ROOT, check=True)
    if not path.exists() or not record.exists():
        raise RuntimeError("sealed-panel maker did not save panel and record")
    if read_json(record)["sha256"] != sha256(path):
        raise RuntimeError("new sealed-panel hash mismatch")
    return path


def evaluate_frozen(cfg: dict, manifest: dict, commit: str, seal_digest: str) -> None:
    # Import only after all checkpoints are frozen and the sealed panel exists.
    import codex_numbers_20260927_run as runner
    import torch

    panels = {**LEGACY_PANELS, "numbers5": ART / "panels/numbers5.jsonl"}
    if not all(path.is_file() for path in panels.values()):
        raise RuntimeError("one or more frozen test panels are missing")
    for name, expected in cfg["registered_panel_sha256"].items():
        if sha256(panels[name]) != expected:
            raise RuntimeError(f"registered source panel changed before evaluation: {name}")
    # All five panels are parsed once for the whole frozen checkpoint sweep.
    # Inference sees the same in-memory items for every seed and both arms.
    panel_items = {name: runner.read_panel(panels[name]) for name in PANEL_NAMES}
    for run in manifest["runs"]:
        variant, seed = run["variant"], run["seed"]
        ckpt = Path(run["checkpoint"])
        folder = RUNS / f"{variant}-s{seed}"
        target = folder / "tests.json.gz"
        wiped_target = folder / "tests-wiped.json.gz" if variant == "candidate" else None
        claim = folder / "tests.claim.json"
        done = folder / "tests.done.json"
        if sha256(ckpt) != run["checkpoint_sha256"]:
            raise RuntimeError(f"checkpoint changed before eval: {ckpt}")
        verify_local_seal(seal_digest)
        if done.exists():
            receipt = read_json(done)
            if not claim.exists() or not target.exists() or receipt["result_sha256"] != sha256(target):
                raise RuntimeError(f"completed evaluation evidence changed: {folder}")
            if variant == "candidate" and (not wiped_target.exists() or
                    receipt.get("wiped_result_sha256") != sha256(wiped_target)):
                raise RuntimeError(f"completed wiped-card evidence changed: {folder}")
            continue
        if claim.exists() or target.exists() or (wiped_target is not None and wiped_target.exists()):
            raise RuntimeError(f"interrupted sealed evaluation requires explicit audited recovery: {folder}")
        gpu_safety_snapshot(f"eval-{variant}-s{seed}")
        create_json(claim, {"checkpoint_sha256": run["checkpoint_sha256"],
                            "panel_sha256": {name: sha256(path) for name, path in panels.items()},
                            "registration_commit": commit, "time_unix": time.time(),
                            "candidate_wiped_cards": variant == "candidate",
                            "ablation": "wipe_cards_before_every_read_from_round0"
                            if variant == "candidate" else None})
        started_run = time.monotonic()
        net, loaded_cfg = runner.load_checkpoint(ckpt, cfg["device"])
        tests, wiped_tests = {}, {}
        for name in PANEL_NAMES:
            panel = panels[name]
            started = time.monotonic()
            items = panel_items[name]
            scores = runner.predict_at_stop(net, items, cfg["device"], cfg["eval_batch"], details=True)
            poison = runner.poison_test(net, items[0], cfg["device"])
            if cfg["device"] == "mps":
                torch.mps.synchronize()
            tests[name] = {"panel": str(panel), "panel_sha256": sha256(panel),
                           "checkpoint": str(ckpt), "checkpoint_sha256": run["checkpoint_sha256"],
                           "variant": variant, "seed": seed, "config": loaded_cfg,
                           "scores": scores, "poison": poison,
                           "eval_minutes": (time.monotonic() - started) / 60}
            if variant == "candidate":
                wiped_started = time.monotonic()
                wiped_scores = runner.predict_at_stop(net, items, cfg["device"],
                                                       cfg["eval_batch"], details=True,
                                                       wipe_cards=True)
                wiped_poison = runner.poison_test(net, items[0], cfg["device"], wipe_cards=True)
                if cfg["device"] == "mps":
                    torch.mps.synchronize()
                wiped_tests[name] = {"panel": str(panel), "panel_sha256": sha256(panel),
                                     "checkpoint": str(ckpt),
                                     "checkpoint_sha256": run["checkpoint_sha256"],
                                     "variant": variant, "seed": seed,
                                     "ablation": "wipe_cards_before_every_read_from_round0",
                                     "config": loaded_cfg, "scores": wiped_scores,
                                     "poison": wiped_poison,
                                     "eval_minutes": (time.monotonic() - wiped_started) / 60}
        with target.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
                gz.write(json.dumps(tests, sort_keys=True, separators=(",", ":")).encode())
        if wiped_target is not None:
            with wiped_target.open("xb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
                    gz.write(json.dumps(wiped_tests, sort_keys=True, separators=(",", ":")).encode())
        create_json(done, {"result_sha256": sha256(target), "time_unix": time.time(),
                           "wiped_result_sha256": sha256(wiped_target) if wiped_target else None,
                           "eval_minutes": (time.monotonic() - started_run) / 60})
        print(f"saved five-panel evaluation evidence for {variant} seed {seed}", flush=True)


@contextlib.contextmanager
def single_supervisor():
    lock = ART / "registered" / "execute.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another experiment supervisor is running") from exc
        yield


def run(commit: str) -> None:
    with single_supervisor():
        cfg = verify_registration(commit)
        import codex_numbers_20260927_run as runner
        for name in ("predict_at_stop", "poison_test"):
            if "wipe_cards" not in inspect.signature(getattr(runner, name)).parameters:
                raise RuntimeError(f"runner {name} lacks preregistered wipe_cards ablation")
        if Path(sys.executable).resolve() != (ROOT / cfg["python"]).resolve():
            raise RuntimeError("run the supervisor with EXPERIMENT.json's Python runtime")
        seal_digest = sha256(SEAL)
        for variant, seed in run_order(cfg):
            train_one(cfg, variant, seed, seal_digest)
        manifest = freeze_checkpoints(cfg, commit)
        verify_local_seal(seal_digest)
        ensure_sealed(cfg, commit)
        evaluate_frozen(cfg, manifest, commit, seal_digest)
        atomic_json(ART / "registered" / "EVALUATION-COMPLETE.json",
                    {"registration_commit": commit,
                     "checkpoint_manifest_sha256": sha256(FROZEN),
                     "completed_unix": time.time(),
                     "evaluations": len(manifest["runs"]) * len(PANEL_NAMES),
                     "wiped_evaluations": len(cfg["seeds"]) * len(PANEL_NAMES)})
        verify_local_seal(seal_digest)
        python = str(ROOT / cfg["python"])
        subprocess.run([python, "-B", str(ROOT / "scripts/codex_numbers_20260927_recount.py"),
                        str(ART)], cwd=ROOT, check=True)
        subprocess.run([python, "-B", str(ROOT / "scripts/codex_numbers_20260927_report.py"),
                        "--root", str(ART)], cwd=ROOT, check=True)
        result = read_json(ART / "RECOUNT.json")
        atomic_json(ART / "registered" / "EXPERIMENT-COMPLETE.json",
                    {"registration_commit": commit, "verdict": result["verdict"],
                     "results_sha256": sha256(ART / "RESULTS.md"),
                     "recount_sha256": sha256(ART / "RECOUNT.json"),
                     "completed_unix": time.time()})
        print(f"experiment complete: {result['verdict']}; see {ART / 'RESULTS.md'}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "run"))
    parser.add_argument("--registration", required=True, help="full SHA of the pushed registration commit")
    args = parser.parse_args()
    if args.command == "validate":
        cfg = verify_registration(args.registration)
        print(json.dumps({"valid_registration": True, "run_order": run_order(cfg),
                          "device": cfg["device"], "train": cfg["train"]}, indent=2))
    else:
        run(args.registration)


if __name__ == "__main__":
    main()
