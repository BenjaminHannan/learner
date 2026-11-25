from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

import scorer

HERE = Path(__file__).resolve().parent
TRAIN_PATH = HERE.parent / "wm5" / "data" / "train_dn.npz"
TRAIN_SHA256 = "4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6"
TRAIN_WORLDS = tuple(range(3000, 3072))
EVAL_WORLDS = tuple(range(3072, 3080))
PYTHON = Path.home() / "learner-ops" / "m3-torch" / ".venv" / "bin" / "python"
STEPS = 3000
MAX_MINUTES = 6.5
RUN_SPECS = (
    (7, "uniform"),
    (7, "relper"),
    (8, "relper"),
    (8, "uniform"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subset_by_worlds(split: dict, worlds: tuple[int, ...]) -> dict:
    world_set = set(worlds)
    starts, ends, action_offsets = scorer.episode_index(split)
    frame_mask = np.isin(split["world_id"], np.asarray(worlds, dtype=np.int64))
    action_mask = np.zeros(len(split["actions"]), dtype=bool)
    for start, end, action_offset in zip(starts, ends, action_offsets):
        if int(split["world_id"][start]) in world_set:
            action_mask[action_offset:action_offset + (end - start - 1)] = True
    out = {}
    for key, value in split.items():
        if len(value) == len(split["frames"]):
            out[key] = value[frame_mask]
        elif len(value) == len(split["actions"]):
            out[key] = value[action_mask]
        else:
            raise ValueError(f"Cannot split array {key!r} with shape {value.shape}")
    return out


def validate_split(split: dict, expected_worlds: tuple[int, ...]) -> dict:
    worlds = np.unique(split["world_id"]).astype(int).tolist()
    if worlds != list(expected_worlds):
        raise ValueError(f"world_ids {worlds} != expected {list(expected_worlds)}")
    for k in (1, 3, 5):
        xi, _, window_worlds, _, _ = scorer.windows(split, k)
        if len(xi) == 0 or not np.isin(window_worlds, np.asarray(expected_worlds)).all():
            raise ValueError(f"invalid k={k} windows for worlds {expected_worlds}")
    return {
        "worlds": worlds,
        "frames": int(len(split["frames"])),
        "actions": int(len(split["actions"])),
        "k1_windows": int(len(scorer.windows(split, 1)[0])),
    }


def prepare_data(data_dir: Path) -> tuple[Path, Path, dict]:
    source = TRAIN_PATH.resolve(strict=True)
    source_sha = sha256_file(source)
    if source_sha != TRAIN_SHA256:
        raise ValueError(f"pinned train source SHA {source_sha} != {TRAIN_SHA256}")
    with np.load(source, allow_pickle=False) as loaded:
        full = {key: loaded[key] for key in loaded.files}
    if np.unique(full["world_id"]).astype(int).tolist() != list(TRAIN_WORLDS + EVAL_WORLDS):
        raise ValueError("pinned train source world set changed")
    train = subset_by_worlds(full, TRAIN_WORLDS)
    evaluation = subset_by_worlds(full, EVAL_WORLDS)
    if set(np.unique(train["world_id"])) & set(np.unique(evaluation["world_id"])):
        raise ValueError("pilot train/eval world overlap")
    data_dir.mkdir(parents=True, exist_ok=True)
    train_path = data_dir / "train_worlds_3000_3071.npz"
    eval_path = data_dir / "eval_worlds_3072_3079.npz"
    manifest_path = data_dir / "manifest.json"
    for path, split, worlds in (
        (train_path, train, TRAIN_WORLDS),
        (eval_path, evaluation, EVAL_WORLDS),
    ):
        if path.exists():
            with np.load(path, allow_pickle=False) as existing:
                existing_split = {key: existing[key] for key in existing.files}
            validate_split(existing_split, worlds)
        else:
            np.savez(path, **split)
    manifest = {
        "source_path": str(source),
        "source_sha256": source_sha,
        "train": validate_split(train, TRAIN_WORLDS),
        "eval": validate_split(evaluation, EVAL_WORLDS),
        "train_file_sha256": sha256_file(train_path),
        "eval_file_sha256": sha256_file(eval_path),
        "steps": STEPS,
        "max_minutes": MAX_MINUTES,
        "expected_total_minutes": [24.0, 27.0],
    }
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old.get("source_sha256") != source_sha or old.get("train_file_sha256") != manifest["train_file_sha256"]:
            raise ValueError("existing pilot data manifest does not match pinned source")
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return train_path, eval_path, manifest


def build_run_command(seed: int, sampler: str, train_path: Path, eval_path: Path, out_dir: Path, log_path: Path) -> list[str]:
    return [
        str(HERE / "withlock.sh"),
        str(log_path),
        str(PYTHON),
        "-B",
        "-u",
        str(HERE / "train_v7.py"),
        "--size", "R7conv",
        "--n-history", "2",
        "--rollout", "reencode",
        "--sampler", sampler,
        "--device", "mps",
        "--steps", str(STEPS),
        "--batch", "64",
        "--lr", "3e-4",
        "--wd", "1e-4",
        "--w-lat", "0.05",
        "--seed", str(seed),
        "--max-minutes", str(MAX_MINUTES),
        "--save-forecasts",
        "--train-data", str(train_path),
        "--eval-data", str(eval_path),
        "--out", str(out_dir),
    ]


def load_run_score(out_dir: Path) -> dict:
    score_path = out_dir / "score_dev_reencode.json"
    model_path = out_dir / "model.pt"
    sampler_log_path = out_dir / "sampler_log.jsonl"
    if not score_path.exists() or not model_path.exists() or not sampler_log_path.exists():
        raise ValueError(f"incomplete pilot outputs in {out_dir}")
    return json.loads(score_path.read_text())


def paired_metrics(uniform: dict, relper: dict) -> dict:
    uniform_gap = uniform["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"]
    relper_gap = relper["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"]
    p2 = (
        uniform_gap is not None
        and relper_gap is not None
        and relper_gap >= 3.0 * uniform_gap
    )
    return {
        "uniform_action5_std_ratio": uniform["k1"]["std_ratio_by_action"]["5"]["ratio"],
        "relper_action5_std_ratio": relper["k1"]["std_ratio_by_action"]["5"]["ratio"],
        "P1": bool(relper["k1"]["std_ratio_by_action"]["5"]["ratio"] >= 0.30),
        "uniform_wake_gap": uniform_gap,
        "relper_wake_gap": relper_gap,
        "P2": bool(p2),
        "uniform_k1_E_over_B": uniform["k1"]["E_over_B"],
        "relper_k1_E_over_B": relper["k1"]["E_over_B"],
        "P3_k1": bool(relper["k1"]["E_over_B"] <= uniform["k1"]["E_over_B"] + 0.005),
        "uniform_k3_E_over_B": uniform["k3"]["E_over_B"],
        "relper_k3_E_over_B": relper["k3"]["E_over_B"],
        "P3_k3": bool(relper["k3"]["E_over_B"] <= uniform["k3"]["E_over_B"] + 0.008),
        "uniform_wall_mean_err": uniform["k1"]["block_open"]["model"]["mean_err"],
        "relper_wall_mean_err": relper["k1"]["block_open"]["model"]["mean_err"],
        "P3_wall": bool(
            relper["k1"]["block_open"]["model"]["mean_err"]
            <= uniform["k1"]["block_open"]["model"]["mean_err"] + 0.005
        ),
        "uniform_diag_aslR2": uniform["diag_non_wake_interactions"]["asleep_all"]["R2"],
        "relper_diag_aslR2": relper["diag_non_wake_interactions"]["asleep_all"]["R2"],
    }


def summarize(run_root: Path) -> dict:
    per_seed = {}
    for seed in (7, 8):
        uniform = load_run_score(run_root / f"s{seed}_uniform")
        relper = load_run_score(run_root / f"s{seed}_relper")
        per_seed[str(seed)] = paired_metrics(uniform, relper)
    p1 = all(values["P1"] for values in per_seed.values())
    p2 = all(values["P2"] for values in per_seed.values())
    p3 = all(
        values["P3_k1"] and values["P3_k3"] and values["P3_wall"]
        for values in per_seed.values()
    )
    passed = bool(p1 and p2 and p3)
    summary = {
        "status": "UNSCORED_PILOT",
        "seeds": [7, 8],
        "train_worlds": list(TRAIN_WORLDS),
        "eval_worlds": list(EVAL_WORLDS),
        "steps": STEPS,
        "max_minutes": MAX_MINUTES,
        "per_seed": per_seed,
        "P1_both_seeds": bool(p1),
        "P2_both_seeds": bool(p2),
        "P3_both_seeds": bool(p3),
        "all_three_hold": passed,
        "decision": "GO_SCORED_RANK8" if passed else "NO_SCORED_RANK8",
        "conv_line_record": "2/3; pilot unscored",
        "diag_aslR2_role": "diagnostic_only_not_a_gate",
    }
    path = run_root / "pilot_summary.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    train_path, eval_path, manifest = prepare_data(HERE / "pilot_data")
    print("[PILOT_DATA] " + json.dumps(manifest, sort_keys=True), flush=True)
    if args.prepare_only:
        print("[PILOT] PREPARE_ONLY_NO_TRAINING", flush=True)
        return
    run_root = HERE / "runs"
    run_root.mkdir(parents=True, exist_ok=True)
    for seed, sampler in RUN_SPECS:
        name = f"s{seed}_{sampler}"
        out_dir = run_root / name
        log_path = run_root / f"{name}.log"
        if (out_dir / "model.pt").exists():
            raise ValueError(f"refusing to overwrite existing pilot run {out_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)
        command = build_run_command(seed, sampler, train_path, eval_path, out_dir, log_path)
        print(f"[PILOT_RUN] {name}", flush=True)
        completed = subprocess.run(command, cwd=HERE, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"pilot run {name} failed with exit code {completed.returncode}")
        load_run_score(out_dir)
    summary = summarize(run_root)
    if not summary["all_three_hold"]:
        raise RuntimeError("PILOT_MISS_NO_SCORED_RANK8")


if __name__ == "__main__":
    main()
