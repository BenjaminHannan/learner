#!/usr/bin/env python3
"""Reader-weights check (month-end line, 2026-09-26). New file only; no agent or runner code changes.

Why: in 0.2c the lis-319 reader code was run with the lis-301 weights on bank D (VERIFY-02c.md, D1). The wrong
weights load without any error (Reading facts, 12:49 UTC 09-26), so a sha check is the only guard.

What: before the next script starts, finds the `--model <dir>` argument of the wrapped command, hashes
<dir>/model.safetensors and compares it with $READER_SHA (required). A mismatch, a missing file or an unset
READER_SHA stops the run with READER-SHA-MISMATCH before anything is loaded. Later builds can import
check_reader_sha() directly.

  READER_SHA=e688e1b2... python -B scripts/claude_readersha_wrap.py \
      scripts/claude_sleepcheck_wrap.py scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --model DIR [args]

  python -B scripts/claude_readersha_wrap.py --selftest
"""
from __future__ import annotations

import hashlib
import os
import runpy
import sys
import tempfile
from pathlib import Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def model_arg(argv: list[str]) -> str:
    for i, a in enumerate(argv):
        if a == "--model" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--model="):
            return a.split("=", 1)[1]
    return ""


def check_reader_sha(model_dir: str, expected: str) -> str:
    """Return the sha256 of model_dir/model.safetensors, or raise SystemExit on any mismatch."""
    if not expected:
        raise SystemExit("READER-SHA-MISMATCH: READER_SHA is not set; refusing to run")
    if not model_dir:
        raise SystemExit("READER-SHA-MISMATCH: the wrapped command has no --model argument")
    f = Path(model_dir) / "model.safetensors"
    if not f.is_file():
        raise SystemExit(f"READER-SHA-MISMATCH: {f} is missing")
    got = file_sha256(f)
    if got != expected.strip().lower():
        raise SystemExit(f"READER-SHA-MISMATCH: {f} has sha256 {got}, expected {expected}")
    return got


def selftest() -> None:
    ok = 0
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "model.safetensors").write_bytes(b"reader weights stand-in")
        good = file_sha256(Path(d) / "model.safetensors")
        assert check_reader_sha(d, good) == good; ok += 1
        assert check_reader_sha(d, good.upper()) == good; ok += 1
        for model_dir, exp in ((d, "0" * 64), (d, ""), ("", good), (str(Path(d) / "nope"), good)):
            try:
                check_reader_sha(model_dir, exp)
            except SystemExit as e:
                assert "READER-SHA-MISMATCH" in str(e); ok += 1
        assert model_arg(["x.py", "--model", d, "--name", "X"]) == d; ok += 1
        assert model_arg(["x.py", f"--model={d}"]) == d; ok += 1
        assert model_arg(["x.py", "--name", "X"]) == ""; ok += 1
    print(f"readersha selftest {ok}/9")


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        selftest()
        return
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_readersha_wrap.py <script.py> [args]")
    got = check_reader_sha(model_arg(sys.argv[2:]), os.environ.get("READER_SHA", ""))
    print(f"readersha: reader weights sha256 {got} match READER_SHA", flush=True)
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
