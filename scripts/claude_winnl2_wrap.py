#!/usr/bin/env python3
"""Linux line endings on Windows, second version (benchmarks thread, 2026-09-25). New file only; replaces
claude_winnl_wrap.py for bm-390 (that file stays as it was; it failed on BensPC).

Why: the sealed turn log (claude_nb323_turnlog.py, _append) and the notebook (fable_notebook_contract.py, _append)
write each line in text mode, then read the last bytes back in binary mode and expect exactly line + "\n".
Windows text mode writes "\n" as "\r\n", so both checks fail there (RESULTS-benspc.md).

What went wrong with version 1 (RESULTS-benspc2.md): it installed a plain Python function as open. Python 3.10's
pathlib stores open as a class attribute (_NormalAccessor.open = io.open) when pathlib is first imported; a stored
builtin stays unbound, but a stored Python function binds as a method, so every Path.open call passed the Path as
the mode and raised TypeError. The Linux test ran Python 3.11 (no _NormalAccessor) and imported pathlib early, so
it never took that path.

What: on Windows only, before the next script starts, open (builtins.open and io.open) becomes an instance of
LinuxNewlineOpen. An instance with __call__ is not a descriptor, so it is never bound as a method, wherever it is
stored. Every text-mode open FOR WRITING that does not choose a newline gets newline="", so "\n" is written as
"\n", byte for byte what Linux writes. Text reads, binary opens and opens that pass their own newline are
untouched. Off Windows it changes nothing: it prints one line and runs the next script.

  python -B scripts/claude_winnl2_wrap.py scripts/claude_sleepcheck_wrap.py scripts/claude_bm390.py locomo ...

Test (Python 3.10 and 3.11, Windows line endings simulated): scripts/claude_winnl2_test.py.
"""
from __future__ import annotations

import builtins
import io
import os
import runpy
import sys

_WRITES = frozenset("wax+")


class LinuxNewlineOpen:
    """Callable stand-in for open() that is never bound as a method (it has no __get__)."""

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                 opener=None):
        if newline is None and isinstance(mode, str) and "b" not in mode and _WRITES & set(mode):
            newline = ""
        return self.inner(file, mode, buffering, encoding, errors, newline, closefd, opener)


def apply() -> None:
    """Install the stand-in as builtins.open and io.open."""
    new = LinuxNewlineOpen(builtins.open)
    builtins.open = new
    io.open = new


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_winnl2_wrap.py <script.py> [args]")
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    if os.name == "nt":
        apply()
        print("winnl2: Windows text-mode writes use Linux line endings (newline='')", flush=True)
    else:
        print("winnl2: not Windows, nothing changed", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
