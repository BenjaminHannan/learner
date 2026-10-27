#!/usr/bin/env python3
"""Exp 261 -- panel checker-query builder.

Reads panel turns + GPU ear preds, recomputes kept frames two ways
(with canonicaliser -> "<id>#t<k>"; without -> "nc:<id>#t<k>"), renders
claims/prompts, writes checks.json for the Qwen client and manifest.json.

python claude_earcheck261_pchecks.py --turns TURNS.json --a-preds A.json --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_earcheck261_arms as A  # noqa: E402
import claude_earcheck261_canon as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    turns = {t["id"]: t["turn"] for t in
             json.loads(Path(a.turns).read_text(encoding="utf-8"))}
    preds = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))["preds"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    checks, manif = [], {}
    for tid, turn in turns.items():
        p = preds[tid]
        arms = A.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], turn)):
            cid = f"{tid}#t{k}"
            checks.append(dict(id=cid, prompt=q["prompt"]))
            manif[cid] = dict(row=tid, canon=True, turn=turn,
                              frame=q["frame"], claim=q["claim"])
        kept_nc = E.brake(E.parse_frames(p["raw"]), turn)[0]
        n = 0
        for f in kept_nc:
            if f.get("act") != "TEACH":
                continue
            h = C.render_claim(f["subject"], f["relation"], f["value"])
            cid = f"nc:{tid}#t{n}"
            checks.append(dict(id=cid, prompt=C.build_prompt(turn, h)))
            manif[cid] = dict(row=tid, canon=False, turn=turn,
                              frame=f, claim=h)
            n += 1
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(turns)} turns -> {len(checks)} checks")


if __name__ == "__main__":
    main()
