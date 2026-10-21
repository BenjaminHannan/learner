"""Atomic checkpoint + resume. A checkpoint is one file `<dir>/step-<N>.pt` plus `<file>.sha256`, written to a temp name and
renamed, so a half-written file never loads. Holds model + optimizer states, step, RNG (python/torch/cuda) and any extras."""
from __future__ import annotations

import hashlib
import os
import random
import re
from pathlib import Path
from typing import Any, Optional

import torch

_NAME = re.compile(r"^step-(\d+)\.pt$")


def rng_state() -> dict[str, Any]:
    return {"python": random.getstate(), "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def set_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    torch.set_rng_state(state["torch"].cpu())
    if state["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all([s.cpu() for s in state["cuda"]])


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def save(directory: Path, step: int, payload: dict[str, Any], keep: int = 3) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / f"step-{step}.pt"
    tmp = directory / f".tmp-step-{step}.pt"
    torch.save({**payload, "step": step, "rng": rng_state()}, tmp)
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    digest = _sha(tmp)
    os.replace(tmp, final)
    (directory / f"step-{step}.pt.sha256").write_text(digest + "\n")
    for old in sorted(_listing(directory))[:-keep] if keep else []:
        for suffix in ("", ".sha256"):
            (directory / f"step-{old}.pt{suffix}").unlink(missing_ok=True)
    return final


def _listing(directory: Path) -> list[int]:
    return sorted(int(m.group(1)) for p in directory.glob("step-*.pt") if (m := _NAME.match(p.name))
                  and (directory / (p.name + ".sha256")).exists())


def latest_step(directory: Path) -> Optional[int]:
    steps = _listing(Path(directory)) if Path(directory).exists() else []
    return steps[-1] if steps else None


def load(directory: Path, step: Optional[int] = None, map_location: Any = "cpu") -> Optional[dict[str, Any]]:
    """Newest verified checkpoint (or `step`), None if there is none. A hash mismatch raises, never loads."""
    directory = Path(directory)
    step = latest_step(directory) if step is None else step
    if step is None:
        return None
    path = directory / f"step-{step}.pt"
    want = (directory / f"step-{step}.pt.sha256").read_text().strip()
    if _sha(path) != want:
        raise RuntimeError(f"{path} fails its sha256; refusing to load")
    return torch.load(path, map_location=map_location, weights_only=False)
