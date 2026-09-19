"""Versioned, no-pickle checkpoints for the controlled-English learner.

The archive contains only JSON metadata and raw tensor bytes. Loading never
calls pickle or ``torch.load``, so checkpoint contents cannot execute Python
code. SHA-256 hashes cover every payload member before any state is restored.

Temporary reasoning workspace is deliberately not serializable here. The
scored restart helper restores only theta, phi, and persistent W, and returns a
fresh ``workspace=None`` marker so callers cannot accidentally carry z across
the restart boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import random
from typing import Any
import zipfile

import torch


FORMAT = "memorylab-checkpoint"
VERSION = 1
MEMORY_SHAPE = (128, 128)
MULTIHEAD_MEMORY_SHAPE = (4, 128, 128)
MEMORY_SHAPES = frozenset((MEMORY_SHAPE, MULTIHEAD_MEMORY_SHAPE))
MEMORY_DTYPE = torch.float32
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
_MANIFEST_LIMIT = 256 * 1024
_METADATA_LIMIT = 8 * 1024 * 1024
_MEMBERS = frozenset({"manifest.json", "metadata.json", "tensors.bin"})

_DTYPE_TO_NAME = {
    torch.bool: "bool",
    torch.uint8: "uint8",
    torch.int8: "int8",
    torch.int16: "int16",
    torch.int32: "int32",
    torch.int64: "int64",
    torch.float16: "float16",
    torch.bfloat16: "bfloat16",
    torch.float32: "float32",
    torch.float64: "float64",
    torch.complex64: "complex64",
    torch.complex128: "complex128",
}
_NAME_TO_DTYPE = {name: dtype for dtype, name in _DTYPE_TO_NAME.items()}


class CheckpointError(RuntimeError):
    """Checkpoint is malformed, incompatible, oversized, or unsafe to restore."""


@dataclass(frozen=True)
class LoadedCheckpoint:
    W: torch.Tensor
    config: dict[str, Any]
    manifest: dict[str, Any]
    optimizer_state: dict[str, Any] | None
    workspace: None = None


@dataclass(frozen=True)
class ScoredRestart:
    W: torch.Tensor
    manifest: dict[str, Any]
    workspace: None = None


def _require_max_bytes(max_bytes: int) -> int:
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    return max_bytes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CheckpointError("Checkpoint metadata must be finite JSON data") from error


def _clean_config(config: dict[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, dict) or any(not isinstance(key, str) for key in config):
        raise CheckpointError("config must be a JSON object with string keys")
    # Round-trip to reject arbitrary objects, NaN/Inf, and mutable aliases.
    try:
        return json.loads(_json_bytes(config).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:  # pragma: no cover
        raise CheckpointError("Invalid config JSON") from error


def _config_fingerprint(config: dict[str, Any]) -> str:
    """Return the semantic configuration fingerprint stored in the manifest."""
    return _sha256(_json_bytes(_clean_config(config)))


def _require_expected_config(
    stored: dict[str, Any],
    expected: dict[str, Any] | None,
) -> None:
    """Reject a semantically incompatible checkpoint before mutating modules."""
    if expected is None:
        return
    if _clean_config(stored) != _clean_config(expected):
        raise CheckpointError("Checkpoint config does not match expected config")


def _validate_W(W: torch.Tensor) -> None:
    if not isinstance(W, torch.Tensor):
        raise CheckpointError("W must be a torch.Tensor")
    if tuple(W.shape) not in MEMORY_SHAPES or W.dtype != MEMORY_DTYPE:
        raise CheckpointError(
            "W must have shape (128, 128) or (4, 128, 128) and dtype float32"
        )
    if not torch.isfinite(W).all().item():
        raise CheckpointError("W contains non-finite values")


class _Encoder:
    def __init__(self) -> None:
        self.raw = io.BytesIO()
        self.table: list[dict[str, Any]] = []

    def _tensor(self, value: torch.Tensor) -> dict[str, str]:
        if value.dtype not in _DTYPE_TO_NAME:
            raise CheckpointError(f"Unsupported tensor dtype: {value.dtype}")
        tensor = value.detach().to("cpu").contiguous().clone()
        raw = bytes(tensor.reshape(-1).view(torch.uint8).untyped_storage())
        expected = tensor.numel() * tensor.element_size()
        if len(raw) != expected:
            raise CheckpointError("Unexpected tensor storage extent")
        ident = f"t{len(self.table):08d}"
        offset = self.raw.tell()
        self.raw.write(raw)
        self.table.append({
            "id": ident,
            "dtype": _DTYPE_TO_NAME[tensor.dtype],
            "shape": list(tensor.shape),
            "offset": offset,
            "nbytes": len(raw),
        })
        return {"__tensor__": ident}

    def encode(self, value: Any) -> Any:
        if isinstance(value, torch.Tensor):
            return self._tensor(value)
        if value is None or isinstance(value, (bool, str, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise CheckpointError("Non-finite scalar in checkpoint state")
            return value
        if isinstance(value, list):
            return {"__kind__": "list", "items": [self.encode(item) for item in value]}
        if isinstance(value, tuple):
            return {"__kind__": "tuple", "items": [self.encode(item) for item in value]}
        if isinstance(value, dict):
            return {"__kind__": "dict", "items": [
                [self.encode(key), self.encode(item)] for key, item in value.items()
            ]}
        raise CheckpointError(f"Unsupported checkpoint state type: {type(value).__name__}")


class _Decoder:
    def __init__(self, table: Any, raw: bytes, map_location: str | torch.device,
                 max_bytes: int) -> None:
        if not isinstance(table, list):
            raise CheckpointError("tensor_table must be a list")
        try:
            self.device = torch.device(map_location)
        except (TypeError, RuntimeError) as error:
            raise CheckpointError("Invalid map_location") from error
        self.raw = raw
        self.entries: dict[str, dict[str, Any]] = {}
        self.cache: dict[str, torch.Tensor] = {}
        cursor = 0
        for index, entry in enumerate(table):
            if not isinstance(entry, dict) or set(entry) != {"id", "dtype", "shape", "offset", "nbytes"}:
                raise CheckpointError("Malformed tensor table entry")
            ident = entry["id"]
            dtype_name = entry["dtype"]
            shape = entry["shape"]
            offset = entry["offset"]
            nbytes = entry["nbytes"]
            if ident != f"t{index:08d}" or dtype_name not in _NAME_TO_DTYPE:
                raise CheckpointError("Invalid tensor id or dtype")
            if (not isinstance(shape, list) or len(shape) > 16
                    or any(not isinstance(dim, int) or dim < 0 or dim > 1_000_000_000
                           for dim in shape)):
                raise CheckpointError("Invalid tensor shape")
            if not isinstance(offset, int) or not isinstance(nbytes, int) or offset != cursor or nbytes < 0:
                raise CheckpointError("Invalid tensor byte range")
            elements = math.prod(shape)
            itemsize = torch.empty((), dtype=_NAME_TO_DTYPE[dtype_name]).element_size()
            if elements * itemsize != nbytes or nbytes > max_bytes:
                raise CheckpointError("Tensor shape does not match serialized byte count")
            cursor += nbytes
            if cursor > len(raw):
                raise CheckpointError("Tensor byte range exceeds payload")
            self.entries[ident] = entry
        if cursor != len(raw):
            raise CheckpointError("Unreferenced bytes in tensor payload")

    def _tensor(self, ident: str) -> torch.Tensor:
        if ident in self.cache:
            return self.cache[ident]
        entry = self.entries.get(ident)
        if entry is None:
            raise CheckpointError("Unknown tensor reference")
        start = entry["offset"]
        end = start + entry["nbytes"]
        dtype = _NAME_TO_DTYPE[entry["dtype"]]
        shape = tuple(entry["shape"])
        if entry["nbytes"] == 0:
            tensor = torch.empty(shape, dtype=dtype)
        else:
            # bytearray gives torch.frombuffer writable owned memory; clone then
            # detaches the tensor from that temporary buffer.
            tensor = torch.frombuffer(bytearray(self.raw[start:end]), dtype=dtype).clone()
            tensor = tensor.reshape(shape)
        tensor = tensor.to(self.device)
        self.cache[ident] = tensor
        return tensor

    def decode(self, value: Any) -> Any:
        if value is None or isinstance(value, (bool, str, int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                raise CheckpointError("Non-finite scalar in checkpoint")
            return value
        if not isinstance(value, dict):
            raise CheckpointError("Malformed structured checkpoint value")
        if set(value) == {"__tensor__"} and isinstance(value["__tensor__"], str):
            return self._tensor(value["__tensor__"])
        if set(value) != {"__kind__", "items"} or not isinstance(value["items"], list):
            raise CheckpointError("Malformed structured checkpoint object")
        kind = value["__kind__"]
        items = value["items"]
        if kind == "list":
            return [self.decode(item) for item in items]
        if kind == "tuple":
            return tuple(self.decode(item) for item in items)
        if kind == "dict":
            result = {}
            for pair in items:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise CheckpointError("Malformed dictionary entry")
                key, item = self.decode(pair[0]), self.decode(pair[1])
                try:
                    if key in result:
                        raise CheckpointError("Duplicate dictionary key")
                    result[key] = item
                except TypeError as error:
                    raise CheckpointError("Unhashable dictionary key") from error
            return result
        raise CheckpointError("Unknown structured checkpoint kind")


def capture_rng_state() -> dict[str, Any]:
    """Capture Python and PyTorch RNG state without initializing a GPU backend."""
    cuda_states: list[torch.Tensor] = []
    if torch.cuda.is_available() and torch.cuda.is_initialized():
        cuda_states = torch.cuda.get_rng_state_all()
    return {
        "python": random.getstate(),
        "torch_cpu": torch.random.get_rng_state(),
        "torch_cuda": cuda_states,
    }


def restore_rng_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict) or set(state) != {"python", "torch_cpu", "torch_cuda"}:
        raise CheckpointError("Malformed RNG state")
    cpu = state["torch_cpu"]
    cuda = state["torch_cuda"]
    if not isinstance(cpu, torch.Tensor) or cpu.dtype != torch.uint8 or cpu.ndim != 1:
        raise CheckpointError("Malformed torch CPU RNG state")
    if not isinstance(cuda, list) or any(
            not isinstance(item, torch.Tensor) or item.dtype != torch.uint8 or item.ndim != 1
            for item in cuda):
        raise CheckpointError("Malformed torch CUDA RNG state")
    try:
        probe = random.Random()
        probe.setstate(state["python"])
    except (TypeError, ValueError) as error:
        raise CheckpointError("Malformed Python RNG state") from error
    if cuda:
        if not torch.cuda.is_available():
            raise CheckpointError("Checkpoint has CUDA RNG state but CUDA is unavailable")
        if len(cuda) != torch.cuda.device_count():
            raise CheckpointError("CUDA RNG state count does not match visible devices")
    try:
        random.setstate(state["python"])
        torch.random.set_rng_state(cpu.to("cpu"))
        if cuda:
            torch.cuda.set_rng_state_all([item.to("cpu") for item in cuda])
    except (TypeError, ValueError, RuntimeError) as error:
        if isinstance(error, CheckpointError):
            raise
        raise CheckpointError("Could not restore RNG state") from error


def _state_dict(module: torch.nn.Module, name: str) -> dict[str, torch.Tensor]:
    if not isinstance(module, torch.nn.Module):
        raise CheckpointError(f"{name} must be a torch.nn.Module")
    state = dict(module.state_dict())
    if any(not isinstance(key, str) or not isinstance(value, torch.Tensor)
           for key, value in state.items()):
        raise CheckpointError(f"{name} state_dict must contain only named tensors")
    return state


def _validate_module_state(module: torch.nn.Module, state: Any, name: str) -> None:
    if not isinstance(state, dict) or any(
            not isinstance(key, str) or not isinstance(value, torch.Tensor)
            for key, value in state.items()):
        raise CheckpointError(f"Malformed {name} state_dict")
    expected = module.state_dict()
    if set(state) != set(expected):
        raise CheckpointError(f"{name} state_dict keys do not match current module")
    for key, value in state.items():
        target = expected[key]
        if tuple(value.shape) != tuple(target.shape) or value.dtype != target.dtype:
            raise CheckpointError(f"{name} tensor mismatch for {key}")


def _archive_bytes(metadata: dict[str, Any], tensors: bytes, has_optimizer: bool,
                   max_bytes: int, memory_shape: tuple[int, ...]) -> tuple[bytes, dict[str, Any]]:
    metadata_bytes = _json_bytes(metadata)
    if len(metadata_bytes) > _METADATA_LIMIT:
        raise CheckpointError("Checkpoint metadata is unexpectedly large")
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "sha256",
        "members": {
            "metadata.json": {"bytes": len(metadata_bytes), "sha256": _sha256(metadata_bytes)},
            "tensors.bin": {"bytes": len(tensors), "sha256": _sha256(tensors)},
        },
        "persistent_memory": {"shape": list(memory_shape), "dtype": "float32"},
        "config_sha256": _config_fingerprint(metadata["config"]),
        "has_optimizer": has_optimizer,
        "workspace_persisted": False,
    }
    manifest_bytes = _json_bytes(manifest)
    if len(manifest_bytes) > _MANIFEST_LIMIT:
        raise CheckpointError("Checkpoint manifest is unexpectedly large")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("metadata.json", metadata_bytes)
        archive.writestr("tensors.bin", tensors)
    blob = stream.getvalue()
    if len(blob) > max_bytes:
        raise CheckpointError(f"Checkpoint would exceed {max_bytes} bytes")
    return blob, manifest


def save_checkpoint(budget: Any, relative: str | Path, theta: torch.nn.Module,
                    phi: torch.nn.Module, W: torch.Tensor, *, optimizer: Any = None,
                    config: dict[str, Any] | None = None,
                    max_bytes: int = DEFAULT_MAX_BYTES) -> Path:
    """Write one bounded, no-clobber checkpoint through ``Budget.atomic_write``.

    ``config`` is for static run/model configuration only. Evaluator labels,
    audit logs, answers, and temporary workspace must never be passed here.
    """
    max_bytes = _require_max_bytes(max_bytes)
    if not hasattr(budget, "atomic_write"):
        raise CheckpointError("A memorylab.storage.Budget-compatible object is required")
    _validate_W(W)
    encoder = _Encoder()
    if optimizer is not None and not hasattr(optimizer, "state_dict"):
        raise CheckpointError("optimizer must provide state_dict()")
    optimizer_state = None if optimizer is None else optimizer.state_dict()
    metadata = {
        "schema_version": VERSION,
        "theta": encoder.encode(_state_dict(theta, "theta")),
        "phi": encoder.encode(_state_dict(phi, "phi")),
        "optimizer": encoder.encode(optimizer_state),
        "rng": encoder.encode(capture_rng_state()),
        "config": _clean_config(config),
        "W": encoder.encode(W),
        "tensor_table": encoder.table,
    }
    blob, _ = _archive_bytes(
        metadata,
        encoder.raw.getvalue(),
        optimizer is not None,
        max_bytes,
        tuple(W.shape),
    )

    relative = str(relative)
    return budget.atomic_write(relative, max_bytes, lambda handle: handle.write(blob))


def _read_archive(path: str | Path, map_location: str | torch.device,
                  max_bytes: int) -> tuple[dict[str, Any], _Decoder, dict[str, Any]]:
    max_bytes = _require_max_bytes(max_bytes)
    path = Path(path)
    try:
        size = path.stat().st_size
    except OSError as error:
        raise CheckpointError(f"Cannot stat checkpoint: {path}") from error
    if not path.is_file() or size <= 0 or size > max_bytes:
        raise CheckpointError("Checkpoint is not a bounded regular file")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) != len(_MEMBERS) or {info.filename for info in infos} != _MEMBERS:
                raise CheckpointError("Checkpoint has unexpected archive members")
            for info in infos:
                if info.is_dir() or info.compress_type != zipfile.ZIP_STORED:
                    raise CheckpointError("Checkpoint members must be uncompressed regular data")
                if info.file_size < 0 or info.file_size > max_bytes or info.compress_size != info.file_size:
                    raise CheckpointError("Checkpoint member size is invalid")
            by_name = {info.filename: info for info in infos}
            if by_name["manifest.json"].file_size > _MANIFEST_LIMIT:
                raise CheckpointError("Manifest is too large")
            if by_name["metadata.json"].file_size > _METADATA_LIMIT:
                raise CheckpointError("Metadata is too large")
            manifest_bytes = archive.read("manifest.json")
            metadata_bytes = archive.read("metadata.json")
            tensors = archive.read("tensors.bin")
    except CheckpointError:
        raise
    except (OSError, EOFError, ValueError, NotImplementedError, zipfile.BadZipFile, RuntimeError) as error:
        raise CheckpointError("Invalid checkpoint archive") from error

    try:
        manifest = json.loads(manifest_bytes)
        metadata = json.loads(metadata_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckpointError("Invalid checkpoint JSON") from error
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
        raise CheckpointError("Unsupported checkpoint format/version")
    if manifest.get("hash_algorithm") != "sha256" or manifest.get("workspace_persisted") is not False:
        raise CheckpointError("Invalid checkpoint safety manifest")
    if not isinstance(manifest.get("has_optimizer"), bool):
        raise CheckpointError("Invalid optimizer manifest flag")
    persistent = manifest.get("persistent_memory")
    if (
        not isinstance(persistent, dict)
        or set(persistent) != {"shape", "dtype"}
        or persistent.get("dtype") != "float32"
        or not isinstance(persistent.get("shape"), list)
        or tuple(persistent["shape"]) not in MEMORY_SHAPES
    ):
        raise CheckpointError("Invalid persistent-memory manifest")
    members = manifest.get("members")
    if not isinstance(members, dict) or set(members) != {"metadata.json", "tensors.bin"}:
        raise CheckpointError("Malformed hash manifest")
    for name, data in (("metadata.json", metadata_bytes), ("tensors.bin", tensors)):
        record = members[name]
        if (not isinstance(record, dict) or set(record) != {"bytes", "sha256"}
                or record["bytes"] != len(data) or record["sha256"] != _sha256(data)):
            raise CheckpointError(f"SHA-256 validation failed for {name}")
    if not isinstance(metadata, dict) or set(metadata) != {
            "schema_version", "theta", "phi", "optimizer", "rng", "config", "W", "tensor_table"}:
        raise CheckpointError("Malformed checkpoint metadata")
    if metadata["schema_version"] != VERSION or not isinstance(metadata["config"], dict):
        raise CheckpointError("Unsupported checkpoint metadata version/config")
    if (
        not isinstance(manifest.get("config_sha256"), str)
        or manifest["config_sha256"] != _config_fingerprint(metadata["config"])
    ):
        raise CheckpointError("Checkpoint config fingerprint is invalid")
    if manifest["has_optimizer"] != (metadata["optimizer"] is not None):
        raise CheckpointError("Optimizer manifest does not match checkpoint metadata")
    decoder = _Decoder(metadata["tensor_table"], tensors, map_location, max_bytes)
    return metadata, decoder, manifest


def _decode_persistent(metadata: dict[str, Any], decoder: _Decoder,
                       theta: torch.nn.Module, phi: torch.nn.Module,
                       manifest: dict[str, Any]) -> tuple[
                           dict[str, torch.Tensor], dict[str, torch.Tensor], torch.Tensor]:
    theta_state = decoder.decode(metadata["theta"])
    phi_state = decoder.decode(metadata["phi"])
    W = decoder.decode(metadata["W"])
    _validate_module_state(theta, theta_state, "theta")
    _validate_module_state(phi, phi_state, "phi")
    _validate_W(W)
    if tuple(W.shape) != tuple(manifest["persistent_memory"]["shape"]):
        raise CheckpointError("Persistent-memory tensor does not match its manifest")
    return theta_state, phi_state, W


def load_checkpoint(path: str | Path, theta: torch.nn.Module, phi: torch.nn.Module, *,
                    optimizer: Any = None, map_location: str | torch.device = "cpu",
                    restore_rng: bool = True,
                    max_bytes: int = DEFAULT_MAX_BYTES,
                    expected_config: dict[str, Any] | None = None) -> LoadedCheckpoint:
    """Restore a training checkpoint after validating format, hashes, and tensors."""
    metadata, decoder, manifest = _read_archive(path, map_location, max_bytes)
    _require_expected_config(metadata["config"], expected_config)
    theta_state, phi_state, W = _decode_persistent(metadata, decoder, theta, phi, manifest)
    optimizer_state = decoder.decode(metadata["optimizer"])
    rng_state = decoder.decode(metadata["rng"])
    if optimizer_state is not None and not isinstance(optimizer_state, dict):
        raise CheckpointError("Malformed optimizer state")
    if optimizer is not None and optimizer_state is None:
        raise CheckpointError("Optimizer requested but checkpoint has no optimizer state")
    if optimizer is not None and not hasattr(optimizer, "load_state_dict"):
        raise CheckpointError("optimizer must provide load_state_dict()")

    theta.load_state_dict(theta_state, strict=True)
    phi.load_state_dict(phi_state, strict=True)
    if optimizer is not None:
        optimizer.load_state_dict(optimizer_state)
    if restore_rng:
        restore_rng_state(rng_state)
    return LoadedCheckpoint(W=W, config=_clean_config(metadata["config"]), manifest=manifest,
                            optimizer_state=optimizer_state, workspace=None)


def inspect_checkpoint_config(
    path: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Read authenticated JSON configuration without mutating model state."""
    metadata, _, _ = _read_archive(path, "cpu", max_bytes)
    return _clean_config(metadata["config"])


def load_scored_restart(path: str | Path, theta: torch.nn.Module, phi: torch.nn.Module, *,
                        map_location: str | torch.device = "cpu",
                        max_bytes: int = DEFAULT_MAX_BYTES,
                        expected_config: dict[str, Any] | None = None) -> ScoredRestart:
    """Restore only theta/phi/W for scoring after optional config matching.

    Optimizer, RNG, and temporary workspace are deliberately discarded.  A
    caller that knows the intended model/run configuration should pass it as
    ``expected_config`` so token semantics and behavior-only settings cannot
    silently change while tensor shapes still happen to match.
    """
    metadata, decoder, manifest = _read_archive(path, map_location, max_bytes)
    _require_expected_config(metadata["config"], expected_config)
    theta_state, phi_state, W = _decode_persistent(metadata, decoder, theta, phi, manifest)
    theta.load_state_dict(theta_state, strict=True)
    phi.load_state_dict(phi_state, strict=True)
    # Temporary workspace is not present in the archive by construction. This
    # explicit marker is the only workspace value exposed to scored inference.
    return ScoredRestart(W=W, manifest=manifest, workspace=None)
