#!/usr/bin/env python3
"""Exp 293 blind-panel scorer driver: run the sealed score_panel.py once
per arm, then cross-check controls/writes/stages from the row files.

New file only. CPU only. Never prints item text or replies: ids,
families, stages and counts only.

Usage:
  uv run ... python -B scripts/claude_293_panelscore.py <paneldir> <rows138nb> <rows293> <outdir>

Runs: <paneldir>/score_panel.py <panel.jsonl> <rows> <score.json> per arm
(exit 3 = SCHEMA-MISMATCH -> VOID, reported, no hand scoring).
Then prints: per-arm right/wrong/write counts from the score JSON, the
ids of every wrong item and every question write, and the control-family
identity check (reply+stores identical to base rows).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    paneldir, rows_b, rows_n, outdir = sys.argv[1:5]
    pd = Path(paneldir)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    panel = pd / "panel.jsonl"
    scorer = pd / "score_panel.py"
    for req in (panel, scorer):
        if not req.exists():
            print(f"SCHEMA-MISMATCH: missing {req}")
            return 3
    items = [json.loads(x) for x in panel.read_text(
        encoding="utf-8").splitlines() if x.strip()]
    fams: dict[str, int] = {}
    for it in items:
        fams[it.get("family", "?")] = fams.get(it.get("family", "?"), 0) + 1
    print(f"panel items={len(items)} families={fams}")
    PY = ["uv", "run", "--offline", "--no-project", "--python", "3.12",
          "--with", "torch", "--with", "numpy", "python", "-B"]
    scores = {}
    for arm, rows in (("138nb", rows_b), ("293", rows_n)):
        score_p = out / f"score-{arm}.json"
        cmd = PY + [str(scorer), str(panel), str(rows), str(score_p)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(f"--- scorer {arm} rc={r.returncode}")
        print((r.stdout or "")[-2000:])
        print((r.stderr or "")[-500:])
        if r.returncode == 3:
            print("SCHEMA-MISMATCH -> VOID, no hand scoring")
            return 3
        if r.returncode != 0:
            print(f"SCORER-FAILED {arm}")
            return 2
        try:
            scores[arm] = json.loads(score_p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"score parse failed {arm}: {e}")
            return 2
        print(f"--- score {arm}: {json.dumps(scores[arm])[:1500]}")
    rb = {json.loads(x)["id"]: json.loads(x) for x in
          Path(rows_b).read_text(encoding="utf-8").splitlines() if x.strip()}
    rn = {json.loads(x)["id"]: json.loads(x) for x in
          Path(rows_n).read_text(encoding="utf-8").splitlines() if x.strip()}
    exp = {it["id"]: it for it in items}
    ctrl_ids = [i for i in exp if exp[i].get("expect") == "control"]
    ctrl_ok = [i for i in ctrl_ids
               if rn.get(i, {}).get("question_reply") == rb.get(i, {}).get("question_reply")
               and rn.get(i, {}).get("stored_after_question_actual") == rb.get(i, {}).get("stored_after_question_actual")]
    print(f"control identical: {len(ctrl_ok)}/{len(ctrl_ids)}")
    print("control non-identical ids:",
          [i for i in ctrl_ids if i not in ctrl_ok])
    for arm, rr in (("138nb", rb), ("293", rn)):
        wrote = [i for i in rr if rr[i].get("question_wrote")]
        print(f"{arm} question_wrote: {len(wrote)} ids={wrote}")
    stages: dict[str, int] = {}
    for i in rn:
        stages[rn[i].get("question_stage", "?")] = \
            stages.get(rn[i].get("question_stage", "?"), 0) + 1
    print(f"293 stages: {stages}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
