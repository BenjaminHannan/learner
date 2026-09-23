#!/usr/bin/env python3
"""Exp 138b B4a driver -- question red team 143 through loop138b + loop138.

Reuses scripts/fable_redteam143_run.py BY IMPORT (sealed cases, judge,
markers); only the daemon factory is swapped per arm (the module builds
its daemon from module globals Loop132Daemon/DEFAULT_CONFIG132, so they
are repointed -- the same swap pattern as the exp-138 bench driver).
Compares per-case verdicts 138b vs 138. Bar: 0 new WRONG-ANSWER vs
loop138; every other move listed. Outputs into
artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_redteam143.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138_agent as L138  # noqa: E402 (frozen base, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138b-20260922"


def run_arm(tag: str, daemon_cls, base_cfg: dict) -> list[dict]:
    R143.Loop132Daemon = daemon_cls  # type: ignore[method-assign]
    R143.DEFAULT_CONFIG132 = copy.deepcopy(base_cfg)  # type: ignore[method-assign]
    suite = json.loads(R143.CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / f"scratch143-{tag}"
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = R143.run_case(case, scratch / case["id"], markers)
        rows.append(rec)
    (ART / f"redteam143-{tag}.json").write_text(
        json.dumps({"seconds": 0, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    return rows


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cfg138 = copy.deepcopy(L138.DEFAULT_CONFIG138)
    cfg138["sleep_threshold"] = 100000
    rows138 = run_arm("loop138", L138.Loop138Daemon, cfg138)
    cfg138b = copy.deepcopy(L138b.DEFAULT_CONFIG138B)
    cfg138b["sleep_threshold"] = 100000
    rows138b = run_arm("loop138b", L138b.Loop138bDaemon, cfg138b)
    b_by_id = {r["id"]: r for r in rows138}
    moves, new_wrong = [], 0
    for r in rows138b:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "family": r.get("family"),
                          "loop138": b["verdict"], "loop138b": r["verdict"],
                          "reply138": str(b.get("reply", ""))[:120],
                          "reply138b": str(r.get("reply", ""))[:120],
                          "reasons": r.get("reasons", [])})
            if r["verdict"] == "WRONG-ANSWER" and b["verdict"] != "WRONG-ANSWER":
                new_wrong += 1
    out = {"seconds": round(time.time() - t0, 1),
           "loop138": dict(Counter(r["verdict"] for r in rows138)),
           "loop138b": dict(Counter(r["verdict"] for r in rows138b)),
           "new_wrong_vs_loop138": new_wrong, "moves": moves}
    (ART / "redteam143-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"B4a 143: loop138 {out['loop138']} loop138b {out['loop138b']} "
          f"new_wrong={new_wrong} moves={len(moves)} in {out['seconds']}s",
          flush=True)
    for m in moves:
        print(f"  MOVE {m['id']} [{m['family']}]: "
              f"{m['loop138']} -> {m['loop138b']}", flush=True)
    return 1 if new_wrong else 0


if __name__ == "__main__":
    sys.exit(main())
