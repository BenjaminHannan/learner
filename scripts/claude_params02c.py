#!/usr/bin/env python3
"""Report-only: total parameters of every model the 0.2c agent keeps resident (evaluator reply, Ben 02:11 UTC
2026-09-26, section 10: "report total parameters, resident weights ... instead of describing the whole system solely
as 1B"). Reads safetensors headers only (no weights loaded, no GPU); a .pt adapter is counted with torch if present.
Month-end line. New file only.

  python -B scripts/claude_params02c.py --model generator=$BASE --model reader=$READER319 --adapter OUT/sleep/adapter02c.pt
prints one JSON line: {"generator": {"params": ..., "bytes": ...}, "reader": {...}, "adapter": {...}, "total_params": ...}
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

DTYPE_BYTES = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1,
               "F8_E4M3": 1, "F8_E5M2": 1}


def safetensors_count(path: Path) -> tuple[int, int]:
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        head = json.loads(f.read(n))
    params = nbytes = 0
    for name, t in head.items():
        if name == "__metadata__":
            continue
        k = 1
        for d in t["shape"]:
            k *= d
        params += k
        nbytes += k * DTYPE_BYTES.get(t["dtype"], 0)
    return params, nbytes


def model_count(d: Path) -> dict:
    files = sorted(d.glob("*.safetensors")) if d.is_dir() else [d]
    if not files:
        raise SystemExit(f"params02c: no .safetensors under {d}")
    p = b = 0
    for f in files:
        fp, fb = safetensors_count(f)
        p, b = p + fp, b + fb
    return {"params": p, "bytes": b, "files": len(files)}


def adapter_count(path: Path) -> dict:
    import torch
    sd = torch.load(path, map_location="cpu")
    if isinstance(sd, dict) and "state_dict" in sd:
        sd = sd["state_dict"]
    ts = [v for v in (sd.values() if isinstance(sd, dict) else []) if hasattr(v, "numel")]
    return {"params": int(sum(t.numel() for t in ts)), "bytes": int(sum(t.numel() * t.element_size() for t in ts))}


def selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        head = {"a": {"dtype": "BF16", "shape": [3, 4], "data_offsets": [0, 24]},
                "b": {"dtype": "F32", "shape": [5], "data_offsets": [24, 44]}, "__metadata__": {"x": "y"}}
        h = json.dumps(head).encode()
        p = Path(td) / "m.safetensors"
        p.write_bytes(struct.pack("<Q", len(h)) + h + b"\0" * 44)
        r = model_count(Path(td))
        assert r == {"params": 17, "bytes": 44, "files": 1}, r
    print("params02c selftest OK 1/1")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", default=[], help="name=path (a model dir or one .safetensors)")
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    out: dict = {}
    for m in a.model:
        name, _, path = m.partition("=")
        out[name] = model_count(Path(path))
    if a.adapter:
        out["adapter"] = adapter_count(Path(a.adapter))
    out["total_params"] = sum(v["params"] for v in out.values() if isinstance(v, dict))
    print(json.dumps(out), flush=True)


if __name__ == "__main__":
    sys.exit(main())
