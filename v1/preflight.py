"""Pinned-environment preflight (Gate S item 1) on the actual box.
  python -m v1.preflight [--allow-unpinned] [--device cuda|cpu] [--commit-file COMMIT] [--steps5 CMD...]
Prints one JSON report and exits non-zero on any failure. Checks: versions vs v1/PINS.json, no git needed, COMMIT file,
guard limit from the detected card, device matmul, checkpoint save/load round trip, and (optionally) 5 training steps."""
import argparse, json, platform, sys, tempfile
from pathlib import Path

import torch

from v1 import ckpt as vckpt
from v1 import guard as vguard


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pins", default=str(Path(__file__).with_name("PINS.json")))
    ap.add_argument("--allow-unpinned", action="store_true", help="CPU wiring checks only; never for Gate S or the arms")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--commit-file", default=None)
    ap.add_argument("--five-steps", default=None, help="module:function that runs 5 training steps and returns a dict")
    a = ap.parse_args(argv)
    pins = json.loads(Path(a.pins).read_text())
    dev = torch.device(a.device)
    rep, problems = {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
                     "device": a.device, "pins": pins}, []
    if torch.__version__.split("+")[0] != pins["torch"]:
        problems.append(f"torch {torch.__version__} != pinned {pins['torch']}")
    if dev.type == "cuda":
        if torch.version.cuda != pins["cuda"]:
            problems.append(f"cuda {torch.version.cuda} != pinned {pins['cuda']}")
        rep["card"] = torch.cuda.get_device_name(dev)
        rep["capability"] = list(torch.cuda.get_device_capability(dev))
    if a.allow_unpinned:
        rep["WARNING"] = "unpinned allowed: this report does NOT satisfy Gate S item 1"
        problems = [p for p in problems if False]
    total = vguard.detect_memory_bytes(dev)
    rep["memory_total_gib"] = round(total / vguard.GIB, 2)
    rep["guard_limit_gib"] = round(vguard.limit_bytes(dev) / vguard.GIB, 2)
    if abs(vguard.limit_bytes(dev) - 0.9 * total) > 1:
        problems.append("guard is not 0.9 x detected memory")
    x = torch.randn(256, 256, device=dev)
    rep["matmul_ok"] = bool(torch.isfinite(x @ x).all())
    if a.commit_file:
        rep["commit"] = Path(a.commit_file).read_text().strip()
    with tempfile.TemporaryDirectory() as d:
        vckpt.save(Path(d), 7, {"w": torch.arange(4.0)})
        rep["ckpt_roundtrip"] = bool(torch.equal(vckpt.load(Path(d))["w"], torch.arange(4.0)))
    if not (rep["matmul_ok"] and rep["ckpt_roundtrip"]):
        problems.append("matmul or checkpoint round trip failed")
    if a.five_steps:
        import importlib
        mod, fn = a.five_steps.split(":")
        rep["five_steps"] = getattr(importlib.import_module(mod), fn)(dev)
    rep["problems"], rep["pass"] = problems, not problems
    print(json.dumps(rep, indent=1, default=str))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
