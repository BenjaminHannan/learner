from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIME_BUDGET_SECONDS = 570
STAGE_ORDER = ("score", "model", "train")
RESULT_SENTINEL = "AUDIT_RESULT "
TRAIN_STEPS = 20
TRAIN_SEED = 7
MODEL_RUNS = ("s7_uniform", "s8_uniform")
TRAIN_QUANTITIES = (
    "sampled_indices_sha256",
    "x_prev_sha256",
    "x_t_sha256",
    "x_next_sha256",
    "act_sha256",
    "batch_tensors_sha256",
    "loss_value_sha256",
    "gradient_vector_sha256",
    "gradient_vector_clipped_sha256",
    "updated_weights_sha256",
    "buffers_sha256",
    "model_state_sha256",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def preflight_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    absolute = candidate.absolute()
    real = os.path.realpath(absolute)
    if "sealed" in str(absolute).lower() or "sealed" in real.lower():
        raise RuntimeError(f"REFUSED: sealed path is forbidden: {absolute} (resolved: {real})")
    return Path(real)


def load_pilot_modules(root: Path) -> dict[str, Any]:
    root = preflight_path(root)
    if not root.is_dir():
        raise RuntimeError(f"--root is not a directory: {root}")
    code_paths = [root / name for name in ("train_v7.py", "model_v7.py", "scorer.py", "pilot_driver.py")]
    for path in code_paths:
        preflight_path(path)
        if path.is_symlink():
            raise RuntimeError(f"REFUSED: pilot code symlink is not allowed: {path}")
        if not path.is_file():
            raise RuntimeError(f"Missing pilot code file: {path}")
    sys.dont_write_bytecode = True
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import train_v7
    import model_v7
    import scorer
    import pilot_driver

    for path in code_paths:
        train_v7.guard_sealed_path(str(path), eval_only=False, allow_sealed=False)
    scorer_sha = model_v7.verify_pinned_scorer(root / "scorer.py")
    return {
        "root": root,
        "train_v7": train_v7,
        "model_v7": model_v7,
        "scorer": scorer,
        "pilot_driver": pilot_driver,
        "code_paths": code_paths,
        "code_sha256": {path.name: sha256_file(path) for path in code_paths},
        "scorer_sha256": scorer_sha,
    }


def guarded_file(modules: dict[str, Any], path: str | Path) -> Path:
    candidate = preflight_path(path)
    if not candidate.is_file():
        raise RuntimeError(f"Missing required file: {candidate}")
    modules["train_v7"].guard_sealed_path(str(candidate), eval_only=False, allow_sealed=False)
    return candidate


def guarded_sha256(modules: dict[str, Any], path: str | Path) -> tuple[Path, str]:
    candidate = guarded_file(modules, path)
    return candidate, sha256_file(candidate)


def read_json(modules: dict[str, Any], path: str | Path) -> tuple[Path, dict[str, Any]]:
    candidate = guarded_file(modules, path)
    with candidate.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {candidate}")
    return candidate, value


def configure_device(modules: dict[str, Any], device_name: str) -> Any:
    import torch

    device = torch.device(device_name)
    if device.type not in ("mps", "cpu"):
        raise RuntimeError(f"--device must be mps or cpu, got {device_name!r}")
    if device.type == "mps":
        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested but torch.backends.mps.is_available() is false")
        modules["train_v7"].check_mps_power()
    return device


def load_eval_split(modules: dict[str, Any]) -> tuple[Path, str, dict[str, Any], dict[str, Any]]:
    driver = modules["pilot_driver"]
    path = modules["root"] / "pilot_data" / driver.EVAL_FILE
    path, digest = guarded_sha256(modules, path)
    if digest != driver.EVAL_SHA256:
        raise RuntimeError(f"Pilot eval SHA-256 mismatch: {path} ({digest})")
    split = modules["scorer"].load_split(str(path))
    manifest = driver.validate_split(split, driver.EVAL_WORLDS)
    return path, digest, split, manifest


def load_train_split(modules: dict[str, Any]) -> tuple[Path, str, dict[str, Any], dict[str, Any]]:
    driver = modules["pilot_driver"]
    path = modules["root"] / "pilot_data" / driver.TRAIN_FILE
    path, digest = guarded_sha256(modules, path)
    if digest != driver.TRAIN_SHA256:
        raise RuntimeError(f"Pilot train SHA-256 mismatch: {path} ({digest})")
    split = modules["scorer"].load_split(str(path))
    manifest = driver.validate_split(split, driver.TRAIN_WORLDS)
    return path, digest, split, manifest


def load_forecasts(modules: dict[str, Any], run_name: str) -> tuple[Path, str, Any, dict[str, Any]]:
    import numpy as np

    path = modules["root"] / "runs" / run_name / "forecasts_dev_reencode.npz"
    path, digest = guarded_sha256(modules, path)
    with np.load(path, allow_pickle=False) as loaded:
        keys = sorted(loaded.files)
        if "pred_k1" not in loaded.files:
            raise RuntimeError(f"{path} does not contain pred_k1")
        predictions = loaded["pred_k1"].copy()
    info = {
        "keys": keys,
        "shape": list(predictions.shape),
        "dtype": str(predictions.dtype),
        "sha256": sha256_bytes(predictions.tobytes(order="C")),
    }
    return path, digest, predictions, info


def load_score(modules: dict[str, Any], run_name: str) -> tuple[Path, str, dict[str, Any]]:
    path = modules["root"] / "runs" / run_name / "score_dev_reencode.json"
    candidate, value = read_json(modules, path)
    return candidate, sha256_bytes(candidate.read_bytes()), value


def tensor_sha256(tensor: Any) -> str:
    return sha256_bytes(tensor.detach().cpu().contiguous().numpy().tobytes(order="C"))


def array_sha256(array: Any) -> str:
    import numpy as np

    return sha256_bytes(np.ascontiguousarray(array).tobytes(order="C"))


def parameter_vector_sha256(model: Any, *, gradients: bool) -> str:
    import torch

    parts = []
    for parameter in model.parameters():
        value = parameter.grad if gradients else parameter
        if value is None:
            raise RuntimeError(f"Missing {'gradient' if gradients else 'weight'} during hash")
        flat = value.detach().cpu().contiguous().view(-1)
        parts.append(flat)
    if not parts:
        return sha256_bytes(b"")
    return sha256_bytes(torch.cat(parts).numpy().tobytes(order="C"))


def buffer_vector_sha256(model: Any) -> str:
    import torch

    parts = []
    names = []
    for name, buffer in model.named_buffers():
        flat = buffer.detach().cpu().contiguous().view(-1)
        parts.append(flat)
        names.append(name)
    data = torch.cat(parts).numpy().tobytes(order="C") if parts else b""
    return sha256_bytes(data), names


def state_dict_sha256(state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name]
        if not hasattr(value, "detach"):
            raise RuntimeError(f"Non-tensor state entry: {name}")
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(tuple(tensor.shape)).encode("ascii"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def encode_calls(values: bytes) -> dict[str, Any]:
    return {
        "encoding": "zlib+base64",
        "value_map": {"0": "invalid", "1": "blocked", "2": "open"},
        "length": len(values),
        "sha256": sha256_bytes(values),
        "data": base64.b64encode(zlib.compress(values, level=9)).decode("ascii"),
    }


def decode_calls(payload: dict[str, Any]) -> bytes:
    if payload.get("encoding") != "zlib+base64":
        raise RuntimeError("Unsupported per-window call encoding")
    values = zlib.decompress(base64.b64decode(payload["data"]))
    if len(values) != int(payload["length"]):
        raise RuntimeError("Per-window call length mismatch")
    if sha256_bytes(values) != payload["sha256"]:
        raise RuntimeError("Per-window call hash mismatch")
    return values


def first_bytes_difference(left: bytes, right: bytes) -> int | None:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return index
    if len(left) != len(right):
        return limit
    return None


def first_mapping_difference(left: dict[str, Any], right: dict[str, Any], keys: list[str] | tuple[str, ...]) -> dict[str, Any] | None:
    for key in keys:
        if left.get(key) != right.get(key):
            return {"quantity": key, "left": left.get(key), "right": right.get(key)}
    return None


def wall_replay(
    modules: dict[str, Any],
    eval_split: dict[str, Any],
    predictions: Any,
    *,
    prediction_source: str,
    eval_path: str,
    eval_sha256: str,
) -> dict[str, Any]:
    import numpy as np

    scorer = modules["scorer"]
    hfr = eval_split["frames"].astype(np.float64)
    xi, ai, world_ids, _, _ = scorer.windows(eval_split, 1)
    actions = scorer.action_values(eval_split["actions"], ai, 1)[:, 0]
    x0 = hfr[xi]
    true_k1 = hfr[xi + 1]
    pred_k1 = np.asarray(predictions, dtype=np.float64)
    if pred_k1.shape != true_k1.shape:
        raise RuntimeError(f"k1 prediction shape {pred_k1.shape} != target shape {true_k1.shape}")
    if not np.isfinite(pred_k1).all():
        raise RuntimeError("k1 predictions contain non-finite values")

    wall = scorer.score_block_open(x0, pred_k1, true_k1, actions, world_ids)
    valid, true_open, _ = scorer.classify_move_displacement(x0, true_k1, actions)
    _, pred_open, _ = scorer.classify_move_displacement(x0, pred_k1, actions)
    true_calls = np.zeros(len(valid), dtype=np.uint8)
    pred_calls = np.zeros(len(valid), dtype=np.uint8)
    true_calls[valid] = np.where(true_open[valid], 2, 1)
    pred_calls[valid] = np.where(pred_open[valid], 2, 1)
    true_bytes = true_calls.tobytes(order="C")
    pred_bytes = pred_calls.tobytes(order="C")

    open_to_open = int((valid & true_open & pred_open).sum())
    open_to_blocked = int((valid & true_open & ~pred_open).sum())
    blocked_to_open = int((valid & ~true_open & pred_open).sum())
    blocked_to_blocked = int((valid & ~true_open & ~pred_open).sum())
    counts = {
        "valid_moves": int(valid.sum()),
        "true_open": int(true_open.sum()),
        "true_blocked": int((valid & ~true_open).sum()),
        "open_to_open": open_to_open,
        "open_to_blocked": open_to_blocked,
        "blocked_to_open": blocked_to_open,
        "blocked_to_blocked": blocked_to_blocked,
    }
    return {
        "prediction_source": prediction_source,
        "prediction_original_dtype": str(np.asarray(predictions).dtype),
        "prediction_original_sha256": array_sha256(predictions),
        "prediction_scoring_dtype": "float64",
        "prediction_scoring_sha256": array_sha256(pred_k1),
        "prediction_shape": list(pred_k1.shape),
        "eval_path": str(eval_path),
        "eval_sha256": eval_sha256,
        "window_indices_sha256": array_sha256(xi),
        "window_count": int(len(xi)),
        "x0_sha256": array_sha256(x0),
        "true_k1_sha256": array_sha256(true_k1),
        "actions_sha256": array_sha256(actions),
        "world_ids_sha256": array_sha256(world_ids),
        "wall": wall,
        "integer_confusion": counts,
        "per_window": {
            "true_calls": encode_calls(true_bytes),
            "pred_calls": encode_calls(pred_bytes),
        },
    }


def infer_saved_counts(wall: dict[str, Any]) -> dict[str, int]:
    n_open = int(wall["true_open"])
    n_blocked = int(wall["true_blocked"])
    return {
        "valid_moves": int(wall["valid_moves"]),
        "true_open": n_open,
        "true_blocked": n_blocked,
        "open_to_blocked": int(round(float(wall["false_block_rate"]) * n_open)),
        "blocked_to_open": int(round(float(wall["false_open_rate"]) * n_blocked)),
        "open_to_open": n_open - int(round(float(wall["false_block_rate"]) * n_open)),
        "blocked_to_blocked": n_blocked - int(round(float(wall["false_open_rate"]) * n_blocked)),
    }


def compare_wall_to_saved(replay: dict[str, Any], saved_wall: dict[str, Any]) -> dict[str, Any]:
    saved_counts = infer_saved_counts(saved_wall)
    differences = []
    for key in ("valid_moves", "true_open", "true_blocked"):
        if replay["wall"][key] != saved_wall[key]:
            differences.append({"quantity": key, "replay": replay["wall"][key], "saved": saved_wall[key]})
    for key in ("false_block_rate", "false_open_rate", "mean_err"):
        replay_value = float(replay["wall"][key])
        saved_value = float(saved_wall[key])
        if not math.isclose(replay_value, saved_value, rel_tol=0.0, abs_tol=1e-15):
            differences.append({"quantity": key, "replay": replay_value, "saved": saved_value})
    if replay["wall"]["mean_err_ci95_worlds"] != saved_wall["mean_err_ci95_worlds"]:
        differences.append(
            {
                "quantity": "mean_err_ci95_worlds",
                "replay": replay["wall"]["mean_err_ci95_worlds"],
                "saved": saved_wall["mean_err_ci95_worlds"],
            }
        )
    for key, saved_value in saved_counts.items():
        replay_value = replay["integer_confusion"][key]
        if replay_value != saved_value:
            differences.append({"quantity": f"integer_confusion.{key}", "replay": replay_value, "saved": saved_value})
    for count_key, rate_key, denominator_key in (
        ("open_to_blocked", "false_block_rate", "true_open"),
        ("blocked_to_open", "false_open_rate", "true_blocked"),
    ):
        expected = saved_counts[count_key] / max(saved_counts[denominator_key], 1)
        if not math.isclose(expected, float(saved_wall[rate_key]), rel_tol=0.0, abs_tol=1e-15):
            differences.append(
                {
                    "quantity": f"saved_rate_count_consistency.{rate_key}",
                    "replay": expected,
                    "saved": saved_wall[rate_key],
                }
            )
    return {
        "status": "PASS" if not differences else "DIFF",
        "saved_integer_confusion": saved_counts,
        "differences": differences,
        "first_difference": differences[0] if differences else None,
    }


def compare_replay_runs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "prediction_original_dtype",
        "prediction_original_sha256",
        "prediction_scoring_sha256",
        "prediction_shape",
        "eval_sha256",
        "window_indices_sha256",
        "window_count",
        "x0_sha256",
        "true_k1_sha256",
        "actions_sha256",
        "world_ids_sha256",
        "wall",
        "integer_confusion",
    ]
    difference = first_mapping_difference(left, right, keys)
    true_left = decode_calls(left["per_window"]["true_calls"])
    true_right = decode_calls(right["per_window"]["true_calls"])
    pred_left = decode_calls(left["per_window"]["pred_calls"])
    pred_right = decode_calls(right["per_window"]["pred_calls"])
    call_differences = {}
    for name, left_bytes, right_bytes in (
        ("true_calls", true_left, true_right),
        ("pred_calls", pred_left, pred_right),
    ):
        index = first_bytes_difference(left_bytes, right_bytes)
        if index is not None:
            call_differences[name] = {
                "first_window_index": index,
                "left": left_bytes[index] if index < len(left_bytes) else None,
                "right": right_bytes[index] if index < len(right_bytes) else None,
            }
    if difference is None and call_differences:
        difference = {"quantity": "per_window_calls", **call_differences}
    return {
        "status": "PASS" if difference is None else "DIFF",
        "first_difference": difference,
        "per_window_call_differences": call_differences,
    }


def compare_per_window(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    differences = {}
    for name in ("true_calls", "pred_calls"):
        left_bytes = decode_calls(left[name])
        right_bytes = decode_calls(right[name])
        index = first_bytes_difference(left_bytes, right_bytes)
        if index is not None:
            differences[name] = {
                "first_window_index": index,
                "left": left_bytes[index] if index < len(left_bytes) else None,
                "right": right_bytes[index] if index < len(right_bytes) else None,
            }
    return {
        "status": "PASS" if not differences else "DIFF",
        "first_difference": next(iter(differences.items())) if differences else None,
        "differences": differences,
    }


def metadata_differences(actual: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    differences = []
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            differences.append({"quantity": key, "actual": actual.get(key), "expected": expected_value})
    return differences


def expected_score_metadata(modules: dict[str, Any], seed: int) -> dict[str, Any]:
    driver = modules["pilot_driver"]
    return {
        "arch": modules["train_v7"].ARCH_TAG_BY_HIST[2],
        "size": "R7conv",
        "n_history": 2,
        "rollout_mode": "reencode",
        "sampler": "uniform",
        "seed": seed,
        "batch": 64,
        "lr": 3e-4,
        "wd": 1e-4,
        "w_lat": 0.05,
        "trained_steps": driver.STEPS,
        "train_data_sha256": driver.TRAIN_SHA256,
        "eval_data_sha256": driver.EVAL_SHA256,
    }


def worker_score(modules: dict[str, Any], device: Any) -> dict[str, Any]:
    eval_path, eval_sha, eval_split, eval_manifest = load_eval_split(modules)
    forecast_path, forecast_sha, predictions, forecast_info = load_forecasts(modules, "s7_uniform")
    score_path, score_sha, score = load_score(modules, "s7_uniform")
    canonical_path, canonical = read_json(modules, modules["root"] / "runs" / "s7_uniform" / "score_dev.json")
    canonical_sha = sha256_bytes(canonical_path.read_bytes())
    replay = wall_replay(
        modules,
        eval_split,
        predictions,
        prediction_source="runs/s7_uniform/forecasts_dev_reencode.npz:pred_k1",
        eval_path=str(eval_path),
        eval_sha256=eval_sha,
    )
    saved_wall = score["k1"]["block_open"]["model"]
    return {
        "worker": "score",
        "device": str(device),
        "eval_manifest": eval_manifest,
        "forecast_path": str(forecast_path),
        "forecast_file_sha256": forecast_sha,
        "forecast_info": forecast_info,
        "score_path": str(score_path),
        "score_file_sha256": score_sha,
        "canonical_score_path": str(canonical_path),
        "canonical_score_file_sha256": canonical_sha,
        "canonical_wall_equal": canonical["k1"]["block_open"]["model"] == saved_wall,
        "metadata_differences": metadata_differences(score, expected_score_metadata(modules, 7)),
        "saved_wall": saved_wall,
        "saved_comparison": compare_wall_to_saved(replay, saved_wall),
        "replay": replay,
        "source_fact": {
            "pilot_scored_from": "preds_by_k[1] in memory as float64 inside evaluate_model",
            "pilot_saved_after_scoring": "pred_k1 cast to float16 by np.savez",
            "exact_original_float64_predictions_saved": False,
        },
    }


def model_metadata_differences(modules: dict[str, Any], checkpoint: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    meta = checkpoint.get("meta", {})
    expected = expected_score_metadata(modules, seed)
    differences = metadata_differences(meta, expected)
    if int(checkpoint.get("steps", -1)) != modules["pilot_driver"].STEPS:
        differences.append({"quantity": "checkpoint.steps", "actual": checkpoint.get("steps"), "expected": modules["pilot_driver"].STEPS})
    return differences


def worker_model(modules: dict[str, Any], device: Any, run_name: str) -> dict[str, Any]:
    import numpy as np
    import torch

    from model_v7 import SpatialWorldModelV7

    seed = int(run_name.split("_", 1)[0][1:])
    eval_path, eval_sha, eval_split, eval_manifest = load_eval_split(modules)
    forecast_path, forecast_sha, saved_predictions, forecast_info = load_forecasts(modules, run_name)
    score_path, score_sha, score = load_score(modules, run_name)
    checkpoint_path = guarded_file(modules, modules["root"] / "runs" / run_name / "model.pt")
    checkpoint_sha = sha256_file(checkpoint_path)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if not isinstance(checkpoint, dict) or "model" not in checkpoint:
        raise RuntimeError(f"Invalid checkpoint structure: {checkpoint_path}")
    differences = model_metadata_differences(modules, checkpoint, seed)

    torch.manual_seed(seed)
    model = SpatialWorldModelV7(size="R7conv", n_history=2).to(device)
    model.load_state_dict(checkpoint["model"], strict=True)
    model.eval()
    loaded_state_hash = state_dict_sha256(model.state_dict())
    loaded_buffer_hash, buffer_names = buffer_vector_sha256(model)

    preds_by_k, _, _, _, _ = modules["train_v7"].rollout_eval_predictions(
        model,
        eval_split,
        device,
        rollout="reencode",
        batch_size=128,
        horizons=(1,),
        compute_ceiling=False,
    )
    generated_predictions = np.asarray(preds_by_k[1], dtype=np.float64)
    generated_replay = wall_replay(
        modules,
        eval_split,
        generated_predictions,
        prediction_source=f"regenerated {run_name} k1 float64",
        eval_path=str(eval_path),
        eval_sha256=eval_sha,
    )
    saved_replay = wall_replay(
        modules,
        eval_split,
        saved_predictions,
        prediction_source=f"runs/{run_name}/forecasts_dev_reencode.npz:pred_k1",
        eval_path=str(eval_path),
        eval_sha256=eval_sha,
    )
    generated_float16 = generated_predictions.astype(np.float16)
    saved_wall = score["k1"]["block_open"]["model"]
    mismatch_count = int(np.count_nonzero(generated_float16 != saved_predictions))
    return {
        "worker": "model",
        "run_name": run_name,
        "device": str(device),
        "torch_version": torch.__version__,
        "eval_manifest": eval_manifest,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_file_sha256": checkpoint_sha,
        "checkpoint_steps": checkpoint.get("steps"),
        "checkpoint_metadata": {
            key: checkpoint.get("meta", {}).get(key)
            for key in ("arch", "size", "n_history", "rollout_mode", "sampler", "seed", "device", "batch", "lr", "wd", "w_lat")
        },
        "metadata_differences": differences,
        "loaded_state_sha256": loaded_state_hash,
        "loaded_buffers_sha256": loaded_buffer_hash,
        "loaded_buffer_names": buffer_names,
        "forecast_path": str(forecast_path),
        "forecast_file_sha256": forecast_sha,
        "forecast_info": forecast_info,
        "score_path": str(score_path),
        "score_file_sha256": score_sha,
        "score_metadata_differences": metadata_differences(score, expected_score_metadata(modules, seed)),
        "generated_prediction": {
            "shape": list(generated_predictions.shape),
            "dtype": "float64",
            "sha256": array_sha256(generated_predictions),
            "float16_sha256": array_sha256(generated_float16),
            "finite": bool(np.isfinite(generated_predictions).all()),
        },
        "saved_prediction": forecast_info,
        "saved_comparison": {
            "status": "PASS" if mismatch_count == 0 else "DIFF",
            "float16_exact_equal": bool(mismatch_count == 0),
            "mismatched_elements": mismatch_count,
            "total_elements": int(generated_float16.size),
            "max_abs_float64_vs_saved": float(np.max(np.abs(generated_predictions - saved_predictions.astype(np.float64)))),
            "full_precision_equality_available": False,
        },
        "generated_wall_vs_saved_score": compare_wall_to_saved(generated_replay, score["k1"]["block_open"]["model"]),
        "saved_artifact_wall_vs_saved_score": compare_wall_to_saved(saved_replay, score["k1"]["block_open"]["model"]),
        "generated_calls_vs_saved_artifact": compare_per_window(generated_replay["per_window"], saved_replay["per_window"]),
        "generated_replay": generated_replay,
        "saved_artifact_replay": saved_replay,
    }


def batch_tensor_hashes(batch: dict[str, Any]) -> dict[str, str]:
    digest = hashlib.sha256()
    hashes = {}
    for name in ("x_prev", "x_t", "x_next", "act"):
        value = batch[name].detach().cpu().contiguous()
        data = value.numpy().tobytes(order="C")
        hashes[f"{name}_sha256"] = sha256_bytes(data)
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(tuple(value.shape)).encode("ascii"))
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    hashes["batch_tensors_sha256"] = digest.hexdigest()
    return hashes


def worker_train(modules: dict[str, Any], device: Any) -> dict[str, Any]:
    import numpy as np
    import torch

    from model_v7 import SpatialWorldModelV7

    train_path, train_sha, train_split, train_manifest = load_train_split(modules)
    scorer = modules["scorer"]
    trainer = modules["train_v7"]
    xi1, ai1, _, _, ti1 = scorer.windows(train_split, 1)
    h1 = trainer.prev_frame_indices(train_split, xi1, ti1)

    torch.manual_seed(TRAIN_SEED)
    model = SpatialWorldModelV7(size="R7conv", n_history=2).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: trainer.lr_factor(step, modules["pilot_driver"].STEPS))
    rng = np.random.default_rng(TRAIN_SEED)
    model.train()
    initial = {
        "weights_sha256": parameter_vector_sha256(model, gradients=False),
        "buffers_sha256": buffer_vector_sha256(model)[0],
        "model_state_sha256": state_dict_sha256(model.state_dict()),
        "optimizer_state_entries": len(optimizer.state),
        "parameter_count": sum(int(parameter.numel()) for parameter in model.parameters()),
    }
    trace = []
    for step in range(TRAIN_STEPS):
        indices = trainer.draw_minibatch_indices(rng, len(xi1), 64, None)
        frame_indices = xi1[indices]
        history_indices = h1[indices]
        batch = {
            "x_prev": torch.from_numpy(train_split["frames"][history_indices].astype(np.float32)).to(device),
            "x_t": torch.from_numpy(train_split["frames"][frame_indices].astype(np.float32)).to(device),
            "x_next": torch.from_numpy(train_split["frames"][frame_indices + 1].astype(np.float32)).to(device),
            "act": torch.from_numpy(train_split["actions"][ai1[indices]].astype(np.int64)).to(device),
        }
        loss, metrics, _ = trainer.compute_train_step_loss(
            model,
            batch["x_prev"],
            batch["x_t"],
            batch["act"],
            batch["x_next"],
            w_lat=0.05,
        )
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss at step {step}: {metrics}")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        gradient_hash = parameter_vector_sha256(model, gradients=True)
        grad_norm = trainer.clip_and_check_grad_norm(model.parameters(), 1.0)
        clipped_gradient_hash = parameter_vector_sha256(model, gradients=True)
        optimizer.step()
        scheduler.step()
        if device.type == "mps":
            torch.mps.synchronize()
        record = {
            "step_index": step,
            "step_number": step + 1,
            "sampled_indices_sha256": array_sha256(indices),
            **batch_tensor_hashes(batch),
            "loss_value": float(loss.detach()),
            "loss_value_sha256": tensor_sha256(loss.detach()),
            "gradient_vector_sha256": gradient_hash,
            "gradient_vector_clipped_sha256": clipped_gradient_hash,
            "grad_norm": float(grad_norm),
            "updated_weights_sha256": parameter_vector_sha256(model, gradients=False),
            "buffers_sha256": buffer_vector_sha256(model)[0],
            "model_state_sha256": state_dict_sha256(model.state_dict()),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "metrics": metrics,
        }
        trace.append(record)
    return {
        "worker": "train",
        "device": str(device),
        "torch_version": torch.__version__,
        "train_path": str(train_path),
        "train_sha256": train_sha,
        "train_manifest": train_manifest,
        "seed": TRAIN_SEED,
        "steps": TRAIN_STEPS,
        "batch": 64,
        "sampler": "uniform",
        "size": "R7conv",
        "n_history": 2,
        "lr": 3e-4,
        "wd": 1e-4,
        "w_lat": 0.05,
        "scheduler_total_steps": modules["pilot_driver"].STEPS,
        "initial": initial,
        "trace": trace,
    }


def training_first_difference(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    initial_difference = first_mapping_difference(left["initial"], right["initial"], tuple(left["initial"].keys()))
    if initial_difference is not None:
        return {"step_index": None, "step_number": None, "stage": "initial", **initial_difference}
    left_trace = left["trace"]
    right_trace = right["trace"]
    if len(left_trace) != len(right_trace):
        return {
            "step_index": min(len(left_trace), len(right_trace)),
            "step_number": min(len(left_trace), len(right_trace)) + 1,
            "stage": "trace_length",
            "quantity": "trace_length",
            "left": len(left_trace),
            "right": len(right_trace),
        }
    for index, (left_record, right_record) in enumerate(zip(left_trace, right_trace)):
        difference = first_mapping_difference(left_record, right_record, TRAIN_QUANTITIES)
        if difference is not None:
            return {"step_index": index, "step_number": index + 1, "stage": "step", **difference}
    return None


def model_repeat_comparison(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "device",
        "checkpoint_file_sha256",
        "loaded_state_sha256",
        "loaded_buffers_sha256",
        "generated_prediction",
        "saved_prediction",
        "generated_replay",
        "saved_artifact_replay",
    ]
    difference = first_mapping_difference(left, right, keys)
    return {"status": "PASS" if difference is None else "DIFF", "first_difference": difference}


def model_result_status(result: dict[str, Any]) -> tuple[bool, str]:
    checks = {
        "metadata": not result["metadata_differences"],
        "score_metadata": not result["score_metadata_differences"],
        "loaded_buffers": len(result["loaded_buffer_names"]) == 2,
        "generated_finite": result["generated_prediction"]["finite"],
        "saved_float16_predictions": result["saved_comparison"]["status"] == "PASS",
        "generated_wall_matches_saved_score": result["generated_wall_vs_saved_score"]["status"] == "PASS",
        "saved_artifact_wall_matches_saved_score": result["saved_artifact_wall_vs_saved_score"]["status"] == "PASS",
        "generated_calls_match_saved_artifact": result["generated_calls_vs_saved_artifact"]["status"] == "PASS",
    }
    failed = [name for name, passed in checks.items() if not passed]
    return not failed, ",".join(failed)


def run_worker(script: Path, modules: dict[str, Any], worker: str, device: str, deadline: float, run_name: str | None = None) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 1:
        return {"ok": False, "error": "global time budget exhausted before worker launch"}
    command = [
        sys.executable,
        "-B",
        "-u",
        str(script),
        "--worker",
        worker,
        "--root",
        str(modules["root"]),
        "--device",
        device,
    ]
    if run_name is not None:
        command.extend(["--run-name", run_name])
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=str(script.parent),
            env=environment,
            capture_output=True,
            text=True,
            timeout=min(300.0, remaining),
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {"ok": False, "error": f"worker timeout after {error.timeout:.1f}s", "stdout": error.stdout, "stderr": error.stderr}
    result_lines = [line for line in completed.stdout.splitlines() if line.startswith(RESULT_SENTINEL)]
    if completed.returncode != 0:
        return {
            "ok": False,
            "error": f"worker exited {completed.returncode}",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    if len(result_lines) != 1:
        return {
            "ok": False,
            "error": f"expected one {RESULT_SENTINEL!r} line, got {len(result_lines)}",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    try:
        payload = json.loads(result_lines[0][len(RESULT_SENTINEL) :])
    except json.JSONDecodeError as error:
        return {"ok": False, "error": f"invalid worker JSON: {error}", "stdout": completed.stdout, "stderr": completed.stderr}
    payload["_worker_stderr"] = completed.stderr
    return {"ok": True, "result": payload}


def worker_failure(run: dict[str, Any]) -> dict[str, Any]:
    def normalize(value: Any) -> Any:
        return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value

    return {
        "ok": run["ok"],
        "error": run.get("error"),
        "stdout": normalize(run.get("stdout")),
        "stderr": normalize(run.get("stderr")),
    }


def stage_score(script: Path, modules: dict[str, Any], device: str, deadline: float) -> dict[str, Any]:
    runs = []
    failures = []
    for _ in range(2):
        run = run_worker(script, modules, "score", device, deadline)
        if run["ok"]:
            runs.append(run["result"])
        else:
            failures.append(worker_failure(run))
    if failures or len(runs) != 2:
        return {"status": "DIFF", "runs": runs, "worker_failures": failures, "line": "score replay worker failed"}
    repeat = compare_replay_runs(runs[0]["replay"], runs[1]["replay"])
    passed = (
        repeat["status"] == "PASS"
        and all(run["saved_comparison"]["status"] == "PASS" for run in runs)
        and all(not run["metadata_differences"] for run in runs)
        and all(run["canonical_wall_equal"] for run in runs)
    )
    return {
        "status": "PASS" if passed else "DIFF",
        "repeat_comparison": repeat,
        "runs": runs,
        "line": "two fresh score replays and saved float16 artifact wall numbers agree"
        if passed
        else "score replay or saved-wall comparison differs",
    }


def stage_model(script: Path, modules: dict[str, Any], device: str, deadline: float, score_stage: dict[str, Any] | None) -> dict[str, Any]:
    per_run = {}
    failures = []
    for run_name in MODEL_RUNS:
        runs = []
        for _ in range(2):
            run = run_worker(script, modules, "model", device, deadline, run_name=run_name)
            if run["ok"]:
                runs.append(run["result"])
            else:
                failures.append({"run_name": run_name, **worker_failure(run)})
        if len(runs) != 2:
            per_run[run_name] = {"status": "DIFF", "runs": runs, "line": "model replay worker failed"}
            continue
        repeat = model_repeat_comparison(runs[0], runs[1])
        result_ok, failed_checks = model_result_status(runs[0])
        cross_stage = None
        if score_stage is not None and score_stage.get("runs") and run_name == "s7_uniform":
            cross_stage = compare_replay_runs(score_stage["runs"][0]["replay"], runs[0]["saved_artifact_replay"])
        passed = repeat["status"] == "PASS" and result_ok and (cross_stage is None or cross_stage["status"] == "PASS")
        per_run[run_name] = {
            "status": "PASS" if passed else "DIFF",
            "repeat_comparison": repeat,
            "failed_checks": failed_checks.split(",") if failed_checks else [],
            "stage1_saved_artifact_comparison": cross_stage,
            "runs": runs,
            "line": "two fresh model replays, saved predictions, and saved wall agree"
            if passed
            else f"model replay differs: {failed_checks or 'repeat mismatch'}",
        }
    overall = all(value["status"] == "PASS" for value in per_run.values()) and not failures
    return {
        "status": "PASS" if overall else "DIFF",
        "per_run": per_run,
        "worker_failures": failures,
        "line": "s7_uniform and s8_uniform model replays agree" if overall else "one or more model replays differ",
    }


def stage_train(script: Path, modules: dict[str, Any], device: str, deadline: float) -> dict[str, Any]:
    runs = []
    failures = []
    for _ in range(2):
        run = run_worker(script, modules, "train", device, deadline)
        if run["ok"]:
            runs.append(run["result"])
        else:
            failures.append(worker_failure(run))
    if failures or len(runs) != 2:
        return {"status": "DIFF", "runs": runs, "worker_failures": failures, "line": "training replay worker failed"}
    difference = training_first_difference(runs[0], runs[1])
    valid = all(run["steps"] == TRAIN_STEPS and len(run["trace"]) == TRAIN_STEPS for run in runs)
    passed = difference is None and valid
    if passed:
        line = "two fresh seed-7 20-step uniform training replays are bit-identical"
    elif difference is not None:
        location = "initial state" if difference["stage"] == "initial" else f"step {difference['step_number']}"
        line = f"first training difference at {location}, quantity {difference['quantity']}"
    else:
        line = "training replay trace is incomplete"
    return {
        "status": "PASS" if passed else "DIFF",
        "first_difference": difference,
        "runs": runs,
        "line": line,
    }


def parse_stages(value: str) -> tuple[str, ...]:
    requested = [item.strip() for item in value.split(",") if item.strip()]
    if not requested:
        raise ValueError("--stages must contain at least one of score,model,train")
    unknown = sorted(set(requested) - set(STAGE_ORDER))
    if unknown:
        raise ValueError(f"unknown stages: {', '.join(unknown)}")
    return tuple(stage for stage in STAGE_ORDER if stage in set(requested))


def write_audit(output_dir: Path, audit: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "audit.json"
    temporary = output_dir / ".audit.json.tmp"
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def run_selftest() -> int:
    calls = bytes([0, 1, 2, 2, 1, 0])
    encoded = encode_calls(calls)
    assert decode_calls(encoded) == calls
    assert first_bytes_difference(bytes([0, 1, 2]), bytes([0, 1, 0])) == 2
    saved_wall = {
        "valid_moves": 4,
        "true_open": 2,
        "true_blocked": 2,
        "false_block_rate": 0.5,
        "false_open_rate": 0.5,
        "mean_err": 0.5,
        "mean_err_ci95_worlds": [0.5, 0.5],
    }
    replay = {
        "wall": saved_wall,
        "integer_confusion": {
            "valid_moves": 4,
            "true_open": 2,
            "true_blocked": 2,
            "open_to_open": 1,
            "open_to_blocked": 1,
            "blocked_to_open": 1,
            "blocked_to_blocked": 1,
        },
    }
    assert compare_wall_to_saved(replay, saved_wall)["status"] == "PASS"
    left = {"initial": {"weights_sha256": "a"}, "trace": [{"loss_value_sha256": "x"}]}
    right = {"initial": {"weights_sha256": "a"}, "trace": [{"loss_value_sha256": "y"}]}
    difference = training_first_difference(left, right)
    assert difference is not None and difference["step_number"] == 1 and difference["quantity"] == "loss_value_sha256"
    print("SELFTEST PASS: stdlib audit helper plumbing")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Determinism audit for the Problem 7 pilot-2 conv world model")
    parser.add_argument("--root", help="Path to the forecast8-pilot2 folder")
    parser.add_argument("--device", default="mps", help="Replay device: mps (default) or cpu")
    parser.add_argument("--stages", default="score,model,train", help="Comma-separated subset: score,model,train")
    parser.add_argument("--self-test", action="store_true", help="Run the stdlib-only synthetic helper self-test")
    parser.add_argument("--worker", choices=("score", "model", "train"), help=argparse.SUPPRESS)
    parser.add_argument("--run-name", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_selftest()
    if args.worker is not None:
        if args.root is None:
            parser.error("--root is required for workers")
        modules = load_pilot_modules(Path(args.root))
        device = configure_device(modules, args.device) if args.worker != "score" else "not-used"
        if args.worker == "score":
            result = worker_score(modules, device)
        elif args.worker == "model":
            if args.run_name not in MODEL_RUNS:
                parser.error("--run-name must be s7_uniform or s8_uniform")
            result = worker_model(modules, device, args.run_name)
        else:
            result = worker_train(modules, device)
        print(RESULT_SENTINEL + json_text(result), flush=True)
        return 0
    if args.root is None:
        parser.error("--root is required")
    try:
        stages = parse_stages(args.stages)
    except ValueError as error:
        parser.error(str(error))
    if args.device not in ("mps", "cpu"):
        parser.error("--device must be mps or cpu")

    started_monotonic = time.monotonic()
    deadline = started_monotonic + TIME_BUDGET_SECONDS
    output_dir = Path(__file__).resolve().parent
    script_path = Path(__file__).resolve()
    audit: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": str(script_path),
        "script_sha256": sha256_file(script_path),
        "root": str(Path(args.root).expanduser().absolute()),
        "device_requested": args.device,
        "stages_requested": list(stages),
        "time_budget_seconds": TIME_BUDGET_SECONDS,
        "python": sys.version,
        "platform": platform.platform(),
        "stages": {},
    }
    try:
        modules = load_pilot_modules(Path(args.root))
        if set(stages) & {"model", "train"}:
            configure_device(modules, args.device)
        audit["code_sha256"] = modules["code_sha256"]
        audit["scorer_sha256"] = modules["scorer_sha256"]
        audit["python_executable"] = sys.executable
        audit["pilot_driver_python"] = str(modules["pilot_driver"].PYTHON)
        audit["interpreter_matches_pilot_driver"] = Path(sys.executable).resolve() == Path(modules["pilot_driver"].PYTHON).resolve()
        audit["source_facts"] = {
            "wall_scoring_call": "scorer.score_block_open(x0, P, yk, a0, wi)",
            "wall_prediction_source": "evaluate_model receives float64 preds_by_k[1] and scores before saving",
            "saved_prediction_artifact": "forecasts_dev_reencode.npz pred_k1 is float16",
            "saved_score_artifact": "score_dev_reencode.json and canonical score_dev.json",
            "saved_raw_confusion_counts_available": False,
            "saved_confusion_count_recovery": "round(false_block_rate * true_open), round(false_open_rate * true_blocked)",
        }
        if "score" in stages:
            audit["stages"]["score"] = stage_score(script_path, modules, args.device, deadline)
            print(f"[SCORE] {audit['stages']['score']['status']}: {audit['stages']['score']['line']}", flush=True)
        if "model" in stages:
            audit["stages"]["model"] = stage_model(
                script_path,
                modules,
                args.device,
                deadline,
                audit["stages"].get("score"),
            )
            for run_name, result in audit["stages"]["model"]["per_run"].items():
                print(f"[MODEL {run_name}] {result['status']}: {result['line']}", flush=True)
            print(f"[MODEL] {audit['stages']['model']['status']}: {audit['stages']['model']['line']}", flush=True)
        if "train" in stages:
            audit["stages"]["train"] = stage_train(script_path, modules, args.device, deadline)
            print(f"[TRAIN] {audit['stages']['train']['status']}: {audit['stages']['train']['line']}", flush=True)
    except Exception as error:
        audit["fatal_error"] = f"{type(error).__name__}: {error}"
        print(f"[AUDIT] DIFF: {type(error).__name__}: {error}", flush=True)
    audit["wall_seconds"] = round(time.monotonic() - started_monotonic, 3)
    audit["within_time_budget"] = audit["wall_seconds"] < 600
    stage_statuses = [stage.get("status", "DIFF") for stage in audit["stages"].values()]
    audit["status"] = (
        "PASS"
        if "fatal_error" not in audit
        and audit["within_time_budget"]
        and stage_statuses
        and all(status == "PASS" for status in stage_statuses)
        else "DIFF"
    )
    output_path = write_audit(output_dir, audit)
    print(f"[AUDIT] {audit['status']}: wrote {output_path}", flush=True)
    return 0 if audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
