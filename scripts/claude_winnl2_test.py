#!/usr/bin/env python3
"""Test for claude_winnl2_wrap.py with Windows' text-mode line endings simulated (benchmarks thread, 2026-09-25).
New file only. Run it with Python 3.10 (BensPC's version) and 3.11.

Windows is simulated by an open stand-in that writes "\n" as "\r\n" for text-mode writes without an explicit
newline (what Windows does with newline=None). It is a callable instance, so a class that stores it (Python 3.10
pathlib) calls it unbound, like the real builtin. Nothing here imports pathlib before the fix is installed, so the
import order matches a fresh BensPC process (the order that broke version 1).

  python -B scripts/claude_winnl2_test.py binding
      Fresh processes, pathlib first imported AFTER the fix: Path.write_text / read_text, a class that stores
      io.open the way 3.10 pathlib does, and importlib.metadata. Version 1 must fail on 3.10 the way BensPC did;
      version 2 must pass and write no "\r".
  python -B scripts/claude_winnl2_test.py unit
      The sealed turn log and notebook: simulated Windows without the fix fails like BensPC, with version 2 passes,
      and its file bytes equal plain Linux bytes.
  python -B scripts/claude_winnl2_test.py run [--fix] <script.py> [args]
      Runs any script (e.g. the bm-390 smoke) under simulated Windows, with or without version 2.
"""
from __future__ import annotations

import builtins
import io
import json
import os
import runpy
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import claude_winnl2_wrap as W2  # noqa: E402

_REAL_BUILTIN, _REAL_IO = builtins.open, io.open
_WRITES = frozenset("wax+")


class SimWindowsOpen:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                 opener=None):
        if newline is None and isinstance(mode, str) and "b" not in mode and _WRITES & set(mode):
            newline = "\r\n"
        return self.inner(file, mode, buffering, encoding, errors, newline, closefd, opener)


def simulate_windows() -> None:
    sim = SimWindowsOpen(builtins.open)
    builtins.open = sim
    io.open = sim


def restore() -> None:
    builtins.open, io.open = _REAL_BUILTIN, _REAL_IO


# ------------------------------------------------------------------ binding (fresh processes)
def probe(argv: list[str]) -> None:
    """One fresh process: [--sim] [--fix 1|2]. Prints one JSON line."""
    out = {"python": sys.version.split()[0], "pathlib_loaded_before_fix": "pathlib" in sys.modules}
    if "--sim" in argv:
        simulate_windows()
    fix = argv[argv.index("--fix") + 1] if "--fix" in argv else ""
    if fix == "1":
        import claude_winnl_wrap as W1
        W1.apply()
    elif fix == "2":
        W2.apply()
    out.update(sim="--sim" in argv, fix=fix or "none")
    try:
        import importlib.metadata as md
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.txt"
            p.write_text("a\nb\n", encoding="utf-8")                 # pathlib write
            with open(os.path.join(d, "y.txt"), "a", encoding="utf-8") as fh:   # builtin append (the turn log)
                fh.write("c\n")
            raw = p.read_bytes() + open(os.path.join(d, "y.txt"), "rb").read()
            text = p.read_text(encoding="utf-8")

            class Acc:                                                 # how 3.10 pathlib stores open
                open = io.open
            via_class = Acc().open(p, "r", -1, "utf-8").read()
            dist = next(iter(md.distributions()))
            ver = md.version(dist.metadata["Name"])
        out.update(ok=True, crlf=raw.count(b"\r\n"), text_ok=text == "a\nb\n" and via_class == "a\nb\n",
                   metadata_ok=bool(ver))
    except Exception as exc:  # noqa: BLE001
        out.update(ok=False, error=f"{type(exc).__name__}: {exc}")
    print(json.dumps(out))


def binding() -> int:
    rows = {}
    for key, args in (("sim, no fix", ["--sim"]), ("sim, version 1", ["--sim", "--fix", "1"]),
                      ("sim, version 2", ["--sim", "--fix", "2"]), ("plain", [])):
        res = subprocess.run([sys.executable, "-B", os.path.abspath(__file__), "probe", *args],
                             capture_output=True, text=True)
        line = (res.stdout.strip().splitlines() or ["{}"])[-1]
        rows[key] = json.loads(line)
        print(key, "|", line)
    checks = {
        "pathlib not imported before the fix (BensPC order)": all(not r.get("pathlib_loaded_before_fix", True)
                                                                  for r in rows.values()),
        "the simulation writes \\r\\n": rows["sim, no fix"].get("ok") and rows["sim, no fix"].get("crlf", 0) > 0,
        "version 1 fails like BensPC (TypeError from a stored open)":
            not rows["sim, version 1"].get("ok") and "TypeError" in rows["sim, version 1"].get("error", ""),
        "version 2 passes, 0 \\r\\n": rows["sim, version 2"].get("ok") is True
            and rows["sim, version 2"].get("crlf") == 0 and rows["sim, version 2"].get("text_ok")
            and rows["sim, version 2"].get("metadata_ok"),
        "plain run passes, 0 \\r\\n": rows["plain"].get("ok") is True and rows["plain"].get("crlf") == 0,
    }
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    ok = all(checks.values())
    print(f"WINNL2-BINDING ({sys.version.split()[0]}) " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ------------------------------------------------------------------ unit (the sealed classes)
def one_case(sim: bool, fix: bool) -> dict:
    import tempfile
    from pathlib import Path
    import claude_nb323_turnlog as TL
    import fable_notebook_contract as NC
    out = {"sim_windows": sim, "fix": fix}
    with tempfile.TemporaryDirectory() as d:
        if sim:
            simulate_windows()
        if fix:
            W2.apply()
        try:
            try:
                log = TL.TurnLog323(Path(d) / "turns.jsonl")
                log._append({"kind": "BEGIN", "turn_id": 1, "t": "2026-01-01T00:00:00+00:00",
                             "text": "Wren said, \"I moved to Oakvale.\""})
                log._append({"kind": "END", "turn_id": 1, "t": "2026-01-01T00:00:01+00:00", "reply": "Okay."})
                again = TL.TurnLog323(Path(d) / "turns.jsonl")
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
        "with version 2, simulated Windows passes":
            sim_fix["turnlog"] == "ok lines=2 torn=False" and sim_fix["notebook"] == "ok events=2 torn=False",
        "plain Linux passes": linux["turnlog"] == "ok lines=2 torn=False" and linux["notebook"] == "ok events=2 torn=False",
        "file bytes with version 2 equal plain Linux bytes": sim_fix["bytes"] == linux["bytes"],
    }
    res = subprocess.run([sys.executable, "-B", os.path.join(HERE, "claude_winnl2_wrap.py"), os.devnull],
                         capture_output=True, text=True)
    checks["the wrapper changes nothing off Windows"] = (os.name != "nt"
                                                         and "winnl2: not Windows, nothing changed" in res.stdout)
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    ok = all(checks.values())
    print(f"WINNL2-UNIT ({sys.version.split()[0]}) " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def run(argv: list[str]) -> None:
    fix = bool(argv) and argv[0] == "--fix"
    if fix:
        argv = argv[1:]
    if not argv:
        raise SystemExit("usage: claude_winnl2_test.py run [--fix] <script.py> [args]")
    loaded = "pathlib" in sys.modules
    simulate_windows()
    if fix:
        W2.apply()
    print(f"winnl2-test: simulated Windows line endings; fix={'on' if fix else 'off'}; "
          f"pathlib loaded before: {loaded}", flush=True)
    sys.argv = [argv[0]] + argv[1:]
    runpy.run_path(argv[0], run_name="__main__")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) >= 2 else ""
    if cmd == "probe":
        probe(sys.argv[2:])
    elif cmd == "binding":
        sys.exit(binding())
    elif cmd == "unit":
        sys.exit(unit())
    elif cmd == "run":
        run(sys.argv[2:])
    else:
        raise SystemExit("usage: claude_winnl2_test.py binding | unit | run [--fix] <script.py> [args]")
