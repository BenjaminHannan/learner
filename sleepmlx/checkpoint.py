"""Crash-consistent night checkpoints and adapter publication.

A generation is immutable. Only the manifest rename publishes it; incomplete
staging directories are never resumed. Old generations remain usable until the
night completes. Optimizer state is deliberately not part of a checkpoint.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from .paths import write_json


class CheckpointError(RuntimeError):
    pass


def _read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise CheckpointError("cannot read checkpoint %s: %s" % (path, e)) from e


def required_adapter(night):
    return night.get("done_steps", 0) > 0 or night.get("phase") in ("downscale", "gate", "finalize")


def validate_adapter(path):
    path = Path(path)
    weights = ("adapters.safetensors", "adapter_model.safetensors", "adapter_model.bin")
    if not (path / "adapter_config.json").is_file() or not any((path / f).is_file() for f in weights):
        raise CheckpointError("required adapter checkpoint is missing or incomplete: %s" % path)


def sync_dir(path):
    # Windows does not support opening a directory for fsync. File writes and
    # atomic replacements still protect process-kill recovery there.
    if os.name != "nt":
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def sync_tree(path):
    for p in Path(path).rglob("*"):
        if p.is_file():
            with p.open("rb") as f:
                os.fsync(f.fileno())
    for p in sorted((p for p in Path(path).rglob("*") if p.is_dir()), reverse=True):
        sync_dir(p)
    sync_dir(path)


def _link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def copy_adapter(src, dst):
    validate_adapter(src)
    # Published adapters are immutable, so links avoid recopying weights for
    # metadata-only generations. copy2 is the cross-filesystem fallback.
    shutil.copytree(src, dst, copy_function=_link_or_copy)


def save_adapter_directory(path, writer):
    """Backends write new immutable destinations; an old save is never removed."""
    path = Path(path)
    if path.exists():
        raise FileExistsError("adapter destination already exists; save a new generation: %s" % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name("." + path.name + "-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        writer(staging)
        validate_adapter(staging)
        sync_tree(staging)
        staging.rename(path)
        sync_dir(path.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def checkpoint_path(work, night):
    descriptor = night.get("checkpoint")
    if not descriptor:
        return Path(work) / "adapter"  # older night format, checked on load
    if not isinstance(descriptor, dict):
        raise CheckpointError("invalid checkpoint generation descriptor")
    generation = descriptor.get("generation", "")
    if (descriptor.get("version") != 1 or not isinstance(generation, str) or len(generation) != 32
            or any(c not in "0123456789abcdef" for c in generation)):
        raise CheckpointError("invalid checkpoint generation descriptor")
    return Path(work) / "checkpoints" / generation / "adapter"


class Checkpoints:
    def __init__(self, paths, hook=None):
        self.paths = paths
        self.hook = hook or (lambda stage: None)

    def load(self):
        if not self.paths.night_json.exists():
            return None, None
        night = _read(self.paths.night_json)
        if (not isinstance(night, dict) or night.get("phase") not in ("tag", "dream", "train", "downscale", "gate", "finalize", "done")
                or type(night.get("done_steps", 0)) is not int or night.get("done_steps", 0) < 0):
            raise CheckpointError("invalid night checkpoint manifest")
        adapter = checkpoint_path(self.paths.work, night)
        items = None
        if night.get("checkpoint"):
            generation = adapter.parent
            if _read(generation / "night.json") != night:
                raise CheckpointError("night manifest does not match its checkpoint generation")
            items = _read(generation / "items.json")
            if not isinstance(items, dict):
                raise CheckpointError("invalid checkpoint items snapshot")
        if required_adapter(night):
            validate_adapter(adapter)
        return night, items

    def publish(self, night, items, save_adapter=None):
        previous, _ = self.load()
        generation = uuid.uuid4().hex
        root = self.paths.work / "checkpoints"
        root.mkdir(parents=True, exist_ok=True)
        staging = root / (".pending-" + generation)
        staging.mkdir()
        adapter = staging / "adapter"
        if save_adapter:
            save_adapter(adapter)
            validate_adapter(adapter)
            self.hook("adapter_saved")
        elif previous:
            old = checkpoint_path(self.paths.work, previous)
            if old.exists():
                copy_adapter(old, adapter)
        published = dict(night, checkpoint={"version": 1, "generation": generation})
        if required_adapter(published):
            validate_adapter(adapter)
        write_json(staging / "items.json", items)
        write_json(staging / "night.json", published)
        sync_tree(staging)
        staging.rename(root / generation)
        sync_dir(root)
        self.hook("generation_ready")
        write_json(self.paths.night_json, published)
        night["checkpoint"] = published["checkpoint"]
        self.hook("manifest_published")

    def promote(self, night):
        """Publish current and previous together, retaining the night candidate."""
        manifest = self.paths.home / "adapters.json"
        old = _read(manifest) if manifest.exists() else {}
        if not isinstance(old, dict):
            raise CheckpointError("invalid committed adapter manifest")
        if old.get("night_id") == night["id"]:
            if old.get("current") != (Path("adapters") / night["id"]).as_posix():
                raise CheckpointError("committed adapter does not match its night id")
            validate_adapter(self.paths.adapter)
            return
        incumbent = self.paths.adapter
        if incumbent.exists():
            validate_adapter(incumbent)
        dst = self.paths.home / "adapters" / night["id"]
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            staging = dst.with_name(".pending-" + uuid.uuid4().hex)
            copy_adapter(self.paths.work_adapter, staging)
            sync_tree(staging)
            staging.rename(dst)
            sync_dir(dst.parent)
        validate_adapter(dst)
        self.hook("promotion_ready")
        write_json(manifest, {"version": 1, "night_id": night["id"], "current": dst.relative_to(self.paths.home).as_posix(),
                              "previous": incumbent.relative_to(self.paths.home).as_posix() if incumbent.exists() else None})
        self.hook("promotion_published")
