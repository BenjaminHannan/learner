"""Checkpoints for the core learner: one directory of three files.

- `state.pt`: model, optimizer and trainer state plus RNG (`torch.save`);
- `config.json`: the JSON configuration needed to rebuild the model;
- `manifest.json`: byte count and SHA-256 of both, written last.

Every file is written no-clobber through `Budget.atomic_write`, so a directory
without a manifest is an unfinished save and does not load. Loading checks
sizes and hashes before deserializing, and deserializes only with
`torch.load(weights_only=True)`, which refuses arbitrary pickled objects.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import random
from typing import Any, Optional, Union

import torch
from torch import nn

FORMAT = "learnlab-core-checkpoint"
VERSION = 1
MEMBERS = ("state.pt", "config.json")
_MANIFEST_LIMIT = 65536
_CONFIG_LIMIT = 1_000_000


class CheckpointError(RuntimeError):
    """Checkpoint is incomplete, tampered with, or does not match the target."""


def rng_state() -> dict[str, Any]:
    """Python, torch CPU and (if already initialized) CUDA generator states."""
    cuda = torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []
    return {"python": random.getstate(), "torch": torch.get_rng_state(), "cuda": cuda}


def set_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"].cpu())
    if state["cuda"]:
        if not torch.cuda.is_available():
            raise CheckpointError("checkpoint has CUDA RNG state but CUDA is unavailable")
        torch.cuda.set_rng_state_all([s.cpu() for s in state["cuda"]])


def _json(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")


def save_checkpoint(budget: Any, relative: Union[str, Path], *, model: nn.Module,
                    config: dict[str, Any], optimizer: Optional[torch.optim.Optimizer] = None,
                    trainer_state: Optional[dict[str, Any]] = None) -> Path:
    """Write a checkpoint directory at `relative` under the budget's root; never overwrites."""
    relative = Path(relative).as_posix()
    target = Path(budget.root) / relative
    if target.exists():
        raise CheckpointError(f"refusing to overwrite existing checkpoint: {target}")
    buffer = io.BytesIO()
    torch.save({
        "model": model.state_dict(),
        "optimizer": None if optimizer is None else optimizer.state_dict(),
        "trainer": trainer_state,
        "rng": rng_state(),
    }, buffer)
    payloads = {"state.pt": buffer.getbuffer(), "config.json": _json(config)}
    manifest = {
        "format": FORMAT, "version": VERSION, "torch": torch.__version__,
        "members": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in payloads.items()},
    }
    payloads["manifest.json"] = _json(manifest)
    for name, data in payloads.items():
        budget.atomic_write(f"{relative}/{name}", len(data),
                            lambda handle, data=data: handle.write(data))
    return target


def _manifest(path: Path) -> dict[str, Any]:
    file = path / "manifest.json"
    if not file.is_file():
        raise CheckpointError(f"no manifest.json in {path}: missing or unfinished checkpoint")
    if file.stat().st_size > _MANIFEST_LIMIT:
        raise CheckpointError("manifest.json is too large")
    try:
        manifest = json.loads(file.read_bytes())
    except ValueError as error:
        raise CheckpointError("manifest.json is not valid JSON") from error
    if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT
            or manifest.get("version") != VERSION
            or not isinstance(manifest.get("members"), dict)
            or set(manifest["members"]) != set(MEMBERS)):
        raise CheckpointError("unsupported or malformed checkpoint manifest")
    return manifest


def _member(path: Path, manifest: dict[str, Any], name: str) -> bytes:
    record, file = manifest["members"][name], path / name
    size = file.stat().st_size if file.is_file() else None
    if not isinstance(record, dict) or size is None or size != record.get("bytes"):
        raise CheckpointError(f"{name} is missing or has the wrong size")
    if name == "config.json" and record["bytes"] > _CONFIG_LIMIT:
        raise CheckpointError("config.json is too large")
    data = file.read_bytes()
    if hashlib.sha256(data).hexdigest() != record.get("sha256"):
        raise CheckpointError(f"SHA-256 mismatch for {name}")
    return data


def read_config(path: Union[str, Path]) -> dict[str, Any]:
    """The verified JSON config, to rebuild the model before `load_checkpoint`."""
    path = Path(path)
    return json.loads(_member(path, _manifest(path), "config.json"))


def load_checkpoint(path: Union[str, Path], model: nn.Module, *,
                    optimizer: Optional[torch.optim.Optimizer] = None,
                    map_location: Union[str, torch.device] = "cpu",
                    restore_rng: bool = True) -> dict[str, Any]:
    """Restore model (and optimizer, RNG) in place; returns config, trainer state and manifest."""
    path = Path(path)
    manifest = _manifest(path)
    config = json.loads(_member(path, manifest, "config.json"))
    data = _member(path, manifest, "state.pt")
    try:
        state = torch.load(io.BytesIO(data), map_location=map_location, weights_only=True)
    except Exception as error:  # the weights-only unpickler raises several types
        raise CheckpointError(f"state.pt could not be loaded safely: {error}") from error
    if optimizer is not None and state["optimizer"] is None:
        raise CheckpointError("checkpoint has no optimizer state")
    model.load_state_dict(state["model"], strict=True)
    if optimizer is not None:
        optimizer.load_state_dict(state["optimizer"])
    if restore_rng:
        set_rng_state(state["rng"])
    return {"config": config, "trainer": state["trainer"], "manifest": manifest}


__all__ = [
    "CheckpointError", "FORMAT", "VERSION", "load_checkpoint", "read_config", "rng_state",
    "save_checkpoint", "set_rng_state",
]
