"""Choose a verified daytime GGUF adapter, otherwise use the plain base model.

Missing/legacy sidecars are deliberately ineligible. This launcher path only
serves exports with a completed positive served check and bound artifact bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .export import prev_path, sidecar_path
from .profile import load_profile


def _resolved(value):
    if not isinstance(value, str) or not value:
        raise ValueError("missing model path")
    return Path(value).expanduser().resolve()


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def adapter_reason(path, profile, base_dir, base_gguf=None):
    """None means eligible; a concise reason explains a rejected candidate."""
    path = Path(path)
    if not path.is_file():
        return "adapter is missing"
    try:
        record = json.loads(sidecar_path(path).read_text())
    except (OSError, ValueError):
        return "missing or invalid export metadata; legacy adapters are not auto-loaded"
    if not isinstance(record, dict):
        return "invalid export metadata"
    if record.get("profile") != profile.name or record.get("base_hf_id") != profile.hf_id:
        return "export belongs to another model or profile"
    try:
        if _resolved(record.get("base_dir")) != _resolved(str(base_dir)):
            return "export belongs to another HF base directory"
        if base_gguf is not None and _resolved(record.get("base_gguf")) != _resolved(str(base_gguf)):
            return "export was checked against another GGUF base"
    except (OSError, ValueError):
        return "export is missing its model paths"
    if "served_pending" in record:
        return "served check is still pending"
    served = record.get("served")
    if not isinstance(served, dict) or served.get("ok") is not True or served.get("pending", False) is not False:
        return "served check did not complete successfully"
    if not isinstance(record.get("night_id"), str) or not record["night_id"]:
        return "export has no completed night identity"
    artifact = record.get("artifact")
    if (not isinstance(artifact, dict) or type(artifact.get("version")) is not int or artifact["version"] != 1
            or type(artifact.get("bytes")) is not int or artifact["bytes"] <= 0
            or not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"])):
        return "export lacks bound artifact metadata; legacy adapters are not auto-loaded"
    try:
        if path.stat().st_size != artifact["bytes"]:
            return "adapter size differs from the completed export"
        if _hash(path) != artifact["sha256"]:
            return "adapter hash differs from the completed export"
    except OSError:
        return "adapter could not be read"
    return None


def select_adapter(home, profile=None, *, base_dir=None, base_gguf=None):
    """Return JSON-friendly selection/reasons; current then accepted fallback."""
    profile = profile or load_profile("lfm3_mps", {})
    base_dir = base_dir or profile.expanded_model_dir
    current = Path(home).expanduser().resolve() / "adapter.gguf"
    reasons = []
    for candidate in (current, prev_path(current)):
        reason = adapter_reason(candidate, profile, base_dir, base_gguf)
        if reason is None:
            return {"adapter": str(candidate), "fallback": candidate != current, "rejected": reasons}
        reasons.append({"path": str(candidate), "reason": reason})
    return {"adapter": None, "fallback": False, "rejected": reasons}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True)
    parser.add_argument("--profile", default="lfm3_mps")
    parser.add_argument("--base-dir")
    parser.add_argument("--base-gguf")
    parser.add_argument("--json", action="store_true", help="include rejection reasons; default prints only an eligible path")
    args = parser.parse_args(argv)
    result = select_adapter(args.home, load_profile(args.profile, {}), base_dir=args.base_dir, base_gguf=args.base_gguf)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    elif result["adapter"]:
        print(result["adapter"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
