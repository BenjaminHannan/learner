#!/usr/bin/env python3
"""Exp 264 -- QA query builder (three questions per kept TEACH frame).

Two modes:
  panel: --mode panel --turns TURNS.json --a-preds A.json --out DIR
    kept frames from 261's sealed base_arms (brake -> canon); three checks per
    kept TEACH frame: "<id>#t<k>#qvalue", "<id>#t<k>#qowner", "<id>#t<k>#qrel".
  dev:   --mode dev --dev DEV.jsonl --preds PREDS.json --src SRC --out DIR
    ids "<src>:<rowid>#t<k>#q<which>".

Writes checks.json [{id, prompt, q}] and manifest.json {id: {...}}.
Prompts come from claude_earcheck264_qa (spec verbatim v0 unless PASSMARKS logs
a change).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck264_qa as QA  # noqa: E402


def frame_checks(turn, frame, cid_base, checks, manif, row, tag, canon=True):
    s, r, v = frame["subject"], frame["relation"], frame["value"]
    qs = [("value", QA.build_q_value(turn, s, r)),
          ("owner", QA.build_q_owner(turn, r, v)),
          ("relation", QA.build_q_relation(turn, s, v))]
    for q, prompt in qs:
        cid = f"{cid_base}#q{q}"
        checks.append(dict(id=cid, prompt=prompt, q=q))
        manif[cid] = dict(row=row, tag=tag, turn=turn, frame=frame,
                          canon=canon, q=q)


def panel(turns, preds, out):
    checks, manif = [], {}
    for tid, turn in turns.items():
        p = preds[tid]
        arms = A261.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        k = 0
        for f in arms["kept_canon"]:
            if f.get("act") != "TEACH":
                continue
            frame_checks(turn, f, f"{tid}#t{k}", checks, manif, tid, None)
            k += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(turns)} turns -> {len(checks)} checks (QA x3)")


def dev(dev_path, preds_path, src, out):
    rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
    checks, manif = [], {}
    for row in rows:
        p = preds[row["id"]]
        arms = A261.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
        k = 0
        for f in arms["kept_canon"]:
            if f.get("act") != "TEACH":
                continue
            frame_checks(row["turn"], f, f"{src}:{row['id']}#t{k}",
                         checks, manif, row["id"], row.get("tag"))
            k += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(rows)} rows -> {len(checks)} checks (QA x3)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["panel", "dev"], required=True)
    ap.add_argument("--turns", default=None)
    ap.add_argument("--a-preds", default=None)
    ap.add_argument("--dev", default=None)
    ap.add_argument("--preds", default=None)
    ap.add_argument("--src", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.mode == "panel":
        turns = {t["id"]: t["turn"] for t in
                 json.loads(Path(a.turns).read_text(encoding="utf-8"))}
        preds = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))["preds"]
        panel(turns, preds, Path(a.out))
    else:
        dev(a.dev, a.preds, a.src, Path(a.out))


if __name__ == "__main__":
    main()
