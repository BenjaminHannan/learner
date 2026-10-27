#!/usr/bin/env python3
"""Exp 261 -- sealed checker-query builder (supersedes the checks.py/pchecks.py
drafts, which are not sealed). Two modes:

  panel: --mode panel --turns TURNS.json --a-preds A.json --prompt B --out DIR
    kept frames two ways (canon "<id>#t<k>"; no-canon "nc:<id>#t<k>"),
    prompts via the sealed question (--prompt A|B).
  dev:   --mode dev --dev DEV.jsonl --preds PREDS.json --src SRC --prompt B
    --out DIR (checks + manifest; same ids as the draft builder).

Writes checks.json [{id, prompt}] and manifest.json {id: {row, turn, frame,
claim, canon}}.
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

try:
    import claude_earcheck261_promptB as PB  # noqa: E402
except ImportError:
    PB = None


def ask(prompt, turn, claim, which):
    if which == "B":
        return PB.build_prompt_b(turn, claim)
    return C.build_prompt(turn, claim)


def emit(turn, frame, claim, cid, canon, checks, manif):
    checks.append(dict(id=cid, prompt=ask(None, turn, claim, EMIT_WHICH)))
    manif[cid] = dict(turn=turn, frame=frame, claim=claim, canon=canon)


EMIT_WHICH = "B"


def panel(turns, preds, which, out):
    global EMIT_WHICH
    EMIT_WHICH = which
    checks, manif = [], {}
    for tid, turn in turns.items():
        p = preds[tid]
        arms = A.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], turn)):
            pr = ask(None, turn, q["claim"], which)
            cid = f"{tid}#t{k}"
            checks.append(dict(id=cid, prompt=pr))
            manif[cid] = dict(row=tid, canon=True, turn=turn,
                              frame=q["frame"], claim=q["claim"])
        kept_nc = E.brake(E.parse_frames(p["raw"]), turn)[0]
        n = 0
        for f in kept_nc:
            if f.get("act") != "TEACH":
                continue
            h = C.render_claim(f["subject"], f["relation"], f["value"])
            cid = f"nc:{tid}#t{n}"
            checks.append(dict(id=cid, prompt=ask(None, turn, h, which)))
            manif[cid] = dict(row=tid, canon=False, turn=turn, frame=f, claim=h)
            n += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(turns)} turns -> {len(checks)} checks (prompt {which})")


def dev(dev_path, preds_path, src, which, out):
    rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
    checks, manif = [], {}
    for row in rows:
        p = preds[row["id"]]
        arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], row["turn"])):
            cid = f"{src}:{row['id']}#t{k}"
            checks.append(dict(id=cid, prompt=ask(None, row["turn"], q["claim"], which)))
            manif[cid] = dict(row=row["id"], tag=row.get("tag"), turn=row["turn"],
                              frame=q["frame"], claim=q["claim"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(rows)} rows -> {len(checks)} checks (prompt {which})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["panel", "dev"], required=True)
    ap.add_argument("--prompt", choices=["A", "B"], default="B")
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
        panel(turns, preds, a.prompt, Path(a.out))
    else:
        dev(a.dev, a.preds, a.src, a.prompt, Path(a.out))


if __name__ == "__main__":
    main()
