#!/usr/bin/env python3
"""Exp 261 -- build checker queries from ear predictions + dev rows.

For each dev row: greedy raw -> brake -> canonicalise -> kept TEACH frames ->
render claim + prompt. Writes checks.json [{id, prompt}] for the Qwen client
and manifest.json {id: {row, turn, frame, claim}} for the theta sweep.

Check ids: "<src>:<rowid>#t<k>" (k = index among kept TEACH frames).

python claude_earcheck261_checks.py --dev DEV.jsonl --preds PREDS.json --src dc --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235b_tau as T  # noqa: E402 (gold_frames only)
import claude_earcheck261_arms as A  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.dev).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(a.preds).read_text(encoding="utf-8"))["preds"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    checks, manif = [], {}
    for row in rows:
        p = preds[row["id"]]
        arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], row["turn"])):
            cid = f"{a.src}:{row['id']}#t{k}"
            checks.append(dict(id=cid, prompt=q["prompt"]))
            manif[cid] = dict(row=row["id"], tag=row.get("tag"), turn=row["turn"],
                              frame=q["frame"], claim=q["claim"])
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(rows)} rows -> {len(checks)} checks")


if __name__ == "__main__":
    main()
