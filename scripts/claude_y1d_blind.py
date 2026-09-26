#!/usr/bin/env python3
"""y1d blind answer check (Answering-from-memory thread, 2026-09-26). New file. DEV data only.

Packs y1d's guarded replies (ep-382's step, "reply382") to the DEV bank's answerable asks for blind judges who use
Benchmarks' bm-398d rubric verbatim (artifacts/claude-bm398d-20260926/INSTRUCTIONS.md: A right, B right + an
incompatible alternative, C partly right, D wrong, E doesn't know). Items get neutral ids and are shuffled across
conditions (seed 4022), so a judge cannot tell which rows the model was shown. The key stays with the builder.

  python -B scripts/claude_y1d_blind.py prep --rows y1d_rows.jsonl --out JUDGEDIR
      writes JUDGEDIR/batch.jsonl (items), JUDGEDIR/INSTRUCTIONS.md (the rubric, verbatim) and KEY next to it
      (JUDGEDIR/../y1d_blind_key.json; never give it to a judge)
  python -B scripts/claude_y1d_blind.py score --key y1d_blind_key.json --labels L1.jsonl L2.jsonl [--third L3.jsonl]
      final label = the two judges' label when they agree, else the third judge's; prints counts per condition
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
BANK = ROOT / "artifacts/claude-e2e331-dev-20260924"
RUBRIC = ROOT / "artifacts/claude-bm398d-20260926/INSTRUCTIONS.md"
SEED = 4022


def load(p) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def gold_answer(t: dict) -> str:
    g = t["gold"]
    if g["type"] in ("yes", "no"):
        return g["type"]
    return " and ".join(str(v) for v in g["values"])


def prep(rows_path: str, out: str) -> None:
    turns = {(t["life_id"], t["turn_index"]): t for t in load(BANK / "turns.jsonl")}
    facts = {f["fact_id"]: f for f in load(BANK / "truth.jsonl")}
    items, key = [], {}
    for r in load(rows_path):
        t = turns[(r["life_id"], r["turn_index"])]
        if t["gold"]["type"] not in ("value", "yes", "no"):
            continue
        ev_turns = sorted({facts[f]["taught_turn"] for f in t["gold"]["uses_facts"]})
        evidence = [f"(day {turns[(r['life_id'], i)]['day']}) {turns[(r['life_id'], i)]['user_text']}"
                    for i in ev_turns]
        items.append({"question": t["user_text"], "gold_answer": gold_answer(t), "evidence": evidence,
                      "reply": r["reply382"],
                      "_key": {"life_id": r["life_id"], "turn_index": r["turn_index"], "cond": r["cond"],
                               "ask_type": r["ask_type"], "label_p382": r["label_p382"]}})
    random.Random(SEED).shuffle(items)
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    with (o / "batch.jsonl").open("w", encoding="utf-8") as fh:
        for i, it in enumerate(items):
            iid = f"y{i:04d}"
            key[iid] = it.pop("_key")
            fh.write(json.dumps(dict(item=iid, **it), ensure_ascii=False) + "\n")
    shutil.copyfile(RUBRIC, o / "INSTRUCTIONS.md")
    (o.parent / "y1d_blind_key.json").write_text(json.dumps(key, indent=0), encoding="utf-8")
    print(json.dumps({"items": len(items), "by_cond": Counter(k["cond"] for k in key.values())}))


def score(key_path: str, l1: str, l2: str, l3: str | None) -> dict:
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    labs = [{x["item"]: x["label"] for x in load(p)} for p in (l1, l2)]
    third = {x["item"]: x["label"] for x in load(l3)} if l3 else {}
    for lab in labs:
        missing = set(key) - set(lab)
        if missing:
            raise SystemExit(f"labels miss {len(missing)} items")
    agree = sum(labs[0][i] == labs[1][i] for i in key)
    splits = [i for i in key if labs[0][i] != labs[1][i]]
    if splits and not all(i in third for i in splits):
        print(json.dumps({"agree": agree, "splits_needing_third": splits}))
        raise SystemExit("third judge needed on the splits")
    final = {i: (labs[0][i] if labs[0][i] == labs[1][i] else third[i]) for i in key}
    tab = defaultdict(Counter)
    for i, k in key.items():
        tab[k["cond"]][final[i]] += 1
        tab[k["cond"] + "|" + k["ask_type"]][final[i]] += 1
    res = {"items": len(key), "agree": agree, "splits": len(splits),
           "A_right": {c: v.get("A", 0) for c, v in tab.items() if "|" not in c},
           "counts": {c: dict(sorted(v.items())) for c, v in sorted(tab.items())},
           "mech_right_vs_A": dict(Counter((key[i]["label_p382"] in ("RIGHT", "RIGHT_CONFIRM"), final[i] == "A")
                                           .__repr__() for i in key))}
    print(json.dumps(res, indent=1))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--rows", required=True)
    p.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--key", required=True)
    s.add_argument("--labels", nargs=2, required=True)
    s.add_argument("--third")
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a.rows, a.out)
    else:
        score(a.key, a.labels[0], a.labels[1], a.third)


if __name__ == "__main__":
    main()
