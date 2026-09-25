#!/usr/bin/env python3
"""Linux line endings on Windows (benchmarks thread, 2026-09-25). New file only; no agent or runner code changes.

Why: bm-390's smoke on BensPC stopped at the first agent turn with TurnLog323Corrupt "read-back mismatch"
(artifacts/claude-bm390-20260925/RESULTS-benspc.md). The sealed turn log (claude_nb323_turnlog.py, _append) and
the notebook (fable_notebook_contract.py, _append) write each line in text mode, then read the last bytes back in
binary mode and expect exactly line + "\n". On Windows, text mode writes "\n" as "\r\n", so the check fails on
every write. Linux and macOS never translate, which is why the same agent runs there.

What: on Windows only, before the next script starts, every text-mode open FOR WRITING that does not choose a
newline itself gets newline="", so "\n" is written as "\n", byte for byte what Linux writes. Text reads, binary
opens and opens that pass their own newline are untouched. On Linux and macOS this file changes nothing: it
prints one line and runs the next script. What the models compute is not touched on any system; only the bytes
of files written in text mode on Windows change (no "\r").

  python -B scripts/claude_winnl_wrap.py scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo ...

Test (Linux, a simulated Windows): scripts/claude_winnl_test.py.
"""
from __future__ import annotations

import builtins
import io
import os
import runpy
import sys

_WRITES = set("wax+")


def linux_newlines(open_fn):
    """Wrap an open function so text-mode writes without an explicit newline use newline=""."""
    def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
              opener=None):
        if newline is None and "b" not in mode and _WRITES & set(mode):
            newline = ""
        return open_fn(file, mode, buffering, encoding, errors, newline, closefd, opener)
    _open.winnl_inner = open_fn
    return _open


def apply() -> None:
    """Install the wrapper as builtins.open and io.open (pathlib's Path.open and write_text call io.open)."""
    new = linux_newlines(builtins.open)
    builtins.open = new
    io.open = new


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_winnl_wrap.py <script.py> [args]")
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    if os.name == "nt":
        apply()
        print("winnl: Windows text-mode writes use Linux line endings (newline='')", flush=True)
    else:
        print("winnl: not Windows, nothing changed", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
