#!/usr/bin/env python3
"""Exp 269 -- checker-query builder (prompt B, sealed wording).

Queries are byte-identical to 265's: for every kept TEACH frame under
261-canon order (arm A consumes the non-diverted subsequence; A265 and A261b
consume their own). One pYES file serves all ear arms.

  panel: --mode panel --turns TURNS.json --a-preds A.json --out DIR
  dev:   --mode dev --dev DEV.jsonl --preds PREDS.json --src SRC --out DIR

Writes checks.json [{id, prompt}] and manifest.json {id: {...}} with the
269-divert flag per check for audit.
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
import claude_earcheck261_canon as C261  # noqa: E402
import claude_earcheck261_promptB as PB  # noqa: E402
import claude_ear265_arms as A265  # noqa: E402
import claude_ear265_canon as C265  # noqa: E402


def panel(turns, preds, out):
    checks, manif = [], {}
    for tid, turn in turns.items():
        p = preds[tid]
        arms = A.base_arms(p["raw"], turn, p["greedy_lp"], p["beams"])
        kept265 = A265.kept_265(p["raw"], turn)
        t265 = [f for f in kept265 if f.get("act") == "TEACH"]
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], turn)):
            cid = f"{tid}#t{k}"
            checks.append(dict(id=cid, prompt=PB.build_prompt_b(turn, q["claim"])))
            manif[cid] = dict(row=tid, canon=True, turn=turn,
                              frame=q["frame"], claim=q["claim"],
                              divert_265=bool(C265.is_group_subject(t265[k]["subject"])))
        kept_nc = E.brake(E.parse_frames(p["raw"]), turn)[0]
        n = 0
        for f in kept_nc:
            if f.get("act") != "TEACH":
                continue
            h = C261.render_claim(f["subject"], f["relation"], f["value"])
            cid = f"nc:{tid}#t{n}"
            checks.append(dict(id=cid, prompt=PB.build_prompt_b(turn, h)))
            manif[cid] = dict(row=tid, canon=False, turn=turn, frame=f, claim=h)
            n += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(turns)} turns -> {len(checks)} checks (prompt B)")


def dev(dev_path, preds_path, src, out):
    rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
    checks, manif = [], {}
    for row in rows:
        p = preds[row["id"]]
        arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
        kept265 = A265.kept_265(p["raw"], row["turn"])
        t265 = [f for f in kept265 if f.get("act") == "TEACH"]
        for k, q in enumerate(A.teach_with_p(arms["kept_canon"], row["turn"])):
            cid = f"{src}:{row['id']}#t{k}"
            checks.append(dict(id=cid, prompt=PB.build_prompt_b(row["turn"], q["claim"])))
            manif[cid] = dict(row=row["id"], tag=row.get("family"), turn=row["turn"],
                              frame=q["frame"], claim=q["claim"],
                              divert_265=bool(C265.is_group_subject(t265[k]["subject"])))
        kept_nc = E.brake(E.parse_frames(p["raw"]), row["turn"])[0]
        n = 0
        for f in kept_nc:
            if f.get("act") != "TEACH":
                continue
            h = C261.render_claim(f["subject"], f["relation"], f["value"])
            cid = f"{src}:nc:{row['id']}#t{n}"
            checks.append(dict(id=cid, prompt=PB.build_prompt_b(row["turn"], h)))
            manif[cid] = dict(row=row["id"], tag=row.get("family"), turn=row["turn"],
                              frame=f, claim=h, canon=False)
            n += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(checks, indent=1))
    (out / "manifest.json").write_text(json.dumps(manif, indent=1))
    print(f"{len(rows)} rows -> {len(checks)} checks (prompt B)")


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
