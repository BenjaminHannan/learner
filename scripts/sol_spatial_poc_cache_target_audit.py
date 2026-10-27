"""Human-authorized read of ONE exact shared HF blob, no loader permission.

No model import, CUDA, optimization, copy, download or cache mutation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

EXACT_TARGET = "C:/Users/benja/.cache/huggingface/hub/blobs/02/0223e4373a31a728f6e306f68fc58ad4b41e86054badb87928b7a491437a8b99"
EXPECTED_SHA = "1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a"
FAILED_PROVENANCE = "C:/Users/benja/sol-translator-human-v4/artifacts/sol-translator-20260929/ground-v3-s0/LFM-provenance.json"
PROVENANCE_SHA = "ec5d42dc87c2f2d8a25168de33b5c8324c8f777f75e7c1b69b8c6205fe97bee8"
LOGICAL_FILE = "C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b/model.safetensors"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_exact_target():
    if not os.environ.get("JOB") or not os.environ.get("TREE"):
        raise RuntimeError("queued read-only diagnostic JOB/TREE required")
    provenance = Path(FAILED_PROVENANCE)
    if sha(provenance) != PROVENANCE_SHA:
        raise ValueError("failed V4 provenance changed")
    meta = json.loads(provenance.read_text())
    if meta["files"].get("model.safetensors") != EXPECTED_SHA:
        raise ValueError("expected exact weight digest changed")
    target = Path(EXACT_TARGET)
    if target.resolve() != target or Path(LOGICAL_FILE).resolve() != target:
        raise ValueError("logical weight or target redirects away from the exact authorized blob")
    start = time.monotonic()
    actual = sha(target)
    return {"scope":"ONE-EXACT-SHARED-BLOB-HASH-DIAGNOSTIC",
            "target":str(target),"logical_file":LOGICAL_FILE,"bytes":target.stat().st_size,
            "expected_sha256":EXPECTED_SHA,"actual_sha256":actual,
            "hash_matches":actual == EXPECTED_SHA,"hash_elapsed_seconds_measured":time.monotonic()-start,
            "failed_provenance_sha256":PROVENANCE_SHA,"diagnostic_source_sha256":sha(__file__),
            "optimizer_updates":0,"CUDA_forwards":0,"model_imports":0,
            "file_or_cache_mutations":0,"copy_or_download":False,
            "loader_authorization":False,
            "next_gate":"Separate explicit human approval for this exact blob+digest before any new loader/TRAIN."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args = parser.parse_args()
    result = audit_exact_target()
    out = Path(args.out)
    if out.exists():
        raise SystemExit("existing diagnostic must be preserved; select a fresh output")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result),flush=True)
    raise SystemExit(0 if result["hash_matches"] else 2)
