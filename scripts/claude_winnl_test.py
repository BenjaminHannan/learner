#!/usr/bin/env python3
"""Test for claude_winnl_wrap.py on Linux, with Windows' text-mode line endings simulated (benchmarks thread,
2026-09-25). New file only.

Windows is simulated by wrapping open so that text-mode writes without an explicit newline write "\n" as "\r\n",
which is what Windows does (newline=None -> os.linesep). The fix is then installed on top, the same way
claude_winnl_wrap.py installs it on Windows.

  python -B scripts/claude_winnl_test.py unit
      The sealed turn log and notebook, three ways: simulated Windows without the fix (must fail with the same
      read-back error as BensPC), simulated Windows with the fix (must pass), plain Linux (must pass). The file
      bytes with the fix must equal the plain Linux bytes.
  python -B scripts/claude_winnl_test.py run [--fix] <script.py> [args]
      Runs any script (e.g. the bm-390 smoke) under simulated Windows, with or without the fix.
"""
from __future__ import annotations

import builtins
import io
import json
import os
import runpy
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_winnl_wrap as W  # noqa: E402

_REAL_BUILTIN, _REAL_IO = builtins.open, io.open
_WRITES = set("wax+")


def simulate_windows() -> None:
    real = builtins.open

    def _open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
              opener=None):
        if newline is None and "b" not in mode and _WRITES & set(mode):
            newline = "\r\n"
        return real(file, mode, buffering, encoding, errors, newline, closefd, opener)
    builtins.open = _open
    io.open = _open


def restore() -> None:
    builtins.open, io.open = _REAL_BUILTIN, _REAL_IO


def one_case(sim: bool, fix: bool) -> dict:
    import claude_nb323_turnlog as TL
    import fable_notebook_contract as NC
    out = {"sim_windows": sim, "fix": fix}
    with tempfile.TemporaryDirectory() as d:
        if sim:
            simulate_windows()
        if fix:
            W.apply()
        try:
            try:
                log = TL.TurnLog323(Path(d) / "turns.jsonl")
                log._append({"kind": "BEGIN", "turn_id": 1, "t": "2026-01-01T00:00:00+00:00",
                             "text": "Wren said, \"I moved to Oakvale.\""})
                log._append({"kind": "END", "turn_id": 1, "t": "2026-01-01T00:00:01+00:00", "reply": "Okay."})
                again = TL.TurnLog323(Path(d) / "turns.jsonl")          # re-verify the hash chain from disk
                out["turnlog"] = f"ok lines={again.n_lines} torn={again.torn_tail}"
            except TL.TurnLog323Corrupt as exc:
                out["turnlog"] = f"TurnLog323Corrupt: {exc}"
            try:
                nb = NC.Notebook(Path(d) / "nb")
                nb.declare_relation("e1", "home_town", True)
                nb.declare_relation("e2", "pet", False)
                again = NC.Notebook(Path(d) / "nb")
                out["notebook"] = f"ok events={len(again.events)} torn={again.torn_tail}"
            except NC.LogCorrupt as exc:
                out["notebook"] = f"LogCorrupt: {exc}"
        finally:
            restore()
        files = sorted(p for p in Path(d).rglob("*") if p.is_file())
        out["bytes"] = {str(p.relative_to(d)): p.read_bytes() for p in files}
    return out


def _linux_noop() -> bool:
    """Run the real wrapper on this (non-Windows) machine around a probe script: open must be untouched."""
    import subprocess
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / "probe.py"
        probe.write_text("import builtins, io\n"
                         "print('UNTOUCHED' if not hasattr(builtins.open, 'winnl_inner') and io.open is builtins.open"
                         " else 'PATCHED')\n", encoding="utf-8")
        res = subprocess.run([sys.executable, "-B", str(HERE / "claude_winnl_wrap.py"), str(probe)],
                             capture_output=True, text=True)
    print(res.stdout.strip().replace("\n", " | "))
    return res.returncode == 0 and res.stdout.strip().endswith("UNTOUCHED") and os.name != "nt"


def unit() -> int:
    cases = [one_case(True, False), one_case(True, True), one_case(False, False)]
    for c in cases:
        crlf = sum(b.count(b"\r\n") for b in c["bytes"].values())
        print(json.dumps({"sim_windows": c["sim_windows"], "fix": c["fix"], "turnlog": c["turnlog"],
                          "notebook": c["notebook"], "files": len(c["bytes"]), "crlf_in_files": crlf}))
    sim_nofix, sim_fix, linux = cases
    checks = {
        "without the fix, simulated Windows fails like BensPC":
            sim_nofix["turnlog"].startswith("TurnLog323Corrupt: turnlog323: read-back mismatch")
            and sim_nofix["notebook"].startswith("LogCorrupt: read-back mismatch"),
        "with the fix, simulated Windows passes":
            sim_fix["turnlog"] == "ok lines=2 torn=False" and sim_fix["notebook"] == "ok events=2 torn=False",
        "plain Linux passes": linux["turnlog"] == "ok lines=2 torn=False" and linux["notebook"] == "ok events=2 torn=False",
        "file bytes with the fix equal plain Linux bytes": sim_fix["bytes"] == linux["bytes"],
        "the wrapper changes nothing off Windows": _linux_noop(),
    }
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    ok = all(checks.values())
    print("WINNL-UNIT " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def run(argv: list[str]) -> None:
    fix = bool(argv) and argv[0] == "--fix"
    if fix:
        argv = argv[1:]
    if not argv:
        raise SystemExit("usage: claude_winnl_test.py run [--fix] <script.py> [args]")
    simulate_windows()
    if fix:
        W.apply()
    print(f"winnl-test: simulated Windows line endings; fix={'on' if fix else 'off'}", flush=True)
    sys.argv = [argv[0]] + argv[1:]
    runpy.run_path(argv[0], run_name="__main__")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "unit":
        sys.exit(unit())
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        run(sys.argv[2:])
        sys.exit(0)
    raise SystemExit("usage: claude_winnl_test.py unit | run [--fix] <script.py> [args]")
