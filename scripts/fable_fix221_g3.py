#!/usr/bin/env python3
"""Exp 221 -- 138i G3 director pairs on loop221 (harness only).

Runs scripts/fable_fix138i_suites.py's run_g3 UNCHANGED, with its agent
module reference (the module attribute S.L138I) pointed at a small shim
whose build_agent138i / DEFAULT_CONFIG138I are loop221's. Runtime
attribute swap in this process only; no file is edited. Each pair's
loop221 replies + stored triples are compared with the SEALED 138i G3 rows
(artifacts/fable-agent138i-20260922/g3g4/suites138i-summary.json).

G4 (index on/off) is NOT run: its off arm is a subprocess hard-wired to
import fable_loop138i_agent, which this wrapper cannot redirect without
editing that file (recorded as a deviation).

Run: python -B scripts/fable_fix221_g3.py --out DIR
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_fix138i_suites as S  # noqa: E402 (driver, read-only)
import fable_loop221_agent as L221  # noqa: E402

SEALED = (ROOT / "artifacts" / "fable-agent138i-20260922" / "g3g4"
          / "suites138i-summary.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    shim = types.SimpleNamespace(
        DEFAULT_CONFIG138I=L221.DEFAULT_CONFIG221,
        build_agent138i=L221.build_agent221)
    S.L138I = shim  # type: ignore[assignment]
    got = S.run_g3()
    sealed = {r["id"]: r for r in
              json.loads(SEALED.read_text(encoding="utf-8"))["g3"]["rows"]}
    rows = []
    for r in got["rows"]:
        b = sealed[r["id"]]
        same = (r["replies138i"] == b["replies138i"]
                and r["stored138i"] == b["stored138i"])
        rows.append({"id": r["id"], "turns": r["turns"],
                     "replies221": r["replies138i"],
                     "stored221": r["stored138i"],
                     "sealed138i_replies": b["replies138i"],
                     "sealed138i_stored": b["stored138i"],
                     "identical_to_sealed138i": same})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summ = {"n": len(rows),
            "identical": sum(r["identical_to_sealed138i"] for r in rows),
            "rows": rows}
    (out / "g3-221.json").write_text(json.dumps(summ, indent=1,
                                                ensure_ascii=False),
                                     encoding="utf-8")
    print(f"G3 identical to sealed 138i: {summ['identical']}/{summ['n']}")
    return 0 if summ["identical"] == summ["n"] else 1


if __name__ == "__main__":
    sys.exit(main())
