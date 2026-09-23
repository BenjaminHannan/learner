#!/usr/bin/env python3
"""Exp 138f M4/G3-rt143 driver -- question red team 143 through loop138f.

Same shape as scripts/fable_loop138d_redteam143.py (cases + judge from
scripts/fable_redteam143_run.py, read-only); runs ONLY the 138f arm and
compares per-case verdicts against the SEALED loop138b rows (read-only).
Bar: M3 identical to loop138b; 0 new WRONG-ANSWER vs loop138b; every other
move predicted in PASSMARKS.md. Outputs into
artifacts/fable-agent138f-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix138f_rt143.py
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

import fable_loop138f_agent as L138f  # noqa: E402 (agent under test)
import fable_redteam143_run as R143  # noqa: E402 (cases + judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138f-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


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
    rows = run_arm("loop138f", L138f.Loop138fDaemon,
                   L138f.DEFAULT_CONFIG138F)
    base = json.loads(
        (ART138B / "redteam143-loop138b.json").read_text(encoding="utf-8"))
    b_by_id = {r["id"]: r for r in base["rows"]}
    moves, new_wrong = [], 0
    for r in rows:
        b = b_by_id.get(r["id"])
        if b is None:
            continue
        if r["verdict"] != b["verdict"]:
            moves.append({"id": r["id"], "loop138b": b["verdict"],
                          "loop138f": r["verdict"],
                          "reply138b": str(b.get("reply", ""))[:120],
                          "reply138f": str(r.get("reply", ""))[:120]})
            if r["verdict"] in ("WRONG-ANSWER", "WRONG") and \
                    b["verdict"] not in ("WRONG-ANSWER", "WRONG"):
                new_wrong += 1
    m3 = next((r for r in rows if r["id"] == "M3"), {})
    b3 = b_by_id.get("M3", {})
    m3_identical = (m3.get("verdict") == b3.get("verdict")
                    and str(m3.get("reply", "")).strip()
                    == str(b3.get("reply", "")).strip())
    out = {"seconds": round(time.time() - t0, 1),
           "counter": dict(Counter(r["verdict"] for r in rows)),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves,
           "M3_identical_to_138b": m3_identical,
           "M3_138f": {k: m3.get(k) for k in ("verdict", "reply")}}
    (ART / "redteam143-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"M4 rt143: {out['counter']} new_wrong={new_wrong} "
          f"moves={len(moves)} M3_identical={m3_identical} "
          f"in {out['seconds']}s", flush=True)
    for m in moves:
        print(f"  MOVE {m['id']}: {m['loop138b']} -> {m['loop138f']}",
              flush=True)
    rc = 1 if (new_wrong or not m3_identical) else 0
    print(f"M4 rt143 rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
