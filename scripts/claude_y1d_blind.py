#!/usr/bin/env python3
"""y1d blind answer check (Answering-from-memory thread, 2026-09-26). New file. DEV data only.

Packs y1d's guarded replies (ep-382's step, "reply382") to the DEV bank's answerable asks for blind judges who use
Benchmarks' bm-398d rubric verbatim (artifacts/claude-bm398d-20260926/INSTRUCTIONS.md: A right, B right + an
incompatible alternative, C partly right, D wrong, E doesn't know). Latin square (Benchmarks, 13:48 UTC): group g
holds, for ask number i, condition CONDS[(i + g) % 3], so no judge sees two conditions of the same ask. Each group
gets two judges (a, b) in private folders; a fresh third judge (c) labels only that group's splits. Items have
neutral ids and are shuffled within a group (seed 4022). The key stays with the builder.

  python -B scripts/claude_y1d_blind.py prep --rows y1d_rows.jsonl --out JUDGEDIR
      JUDGEDIR/judge_g<g>_<a|b>/{batch.jsonl, INSTRUCTIONS.md}; key at JUDGEDIR/../y1d_blind_key.json
  python -B scripts/claude_y1d_blind.py splits --out JUDGEDIR
      JUDGEDIR/judge_g<g>_c/{batch.jsonl, INSTRUCTIONS.md} with only the items judges a and b split on
  python -B scripts/claude_y1d_blind.py score --key y1d_blind_key.json --out JUDGEDIR
      final label = a and b's label when they agree, else c's; prints counts per condition
Judges write labels/batch.jsonl in their own folder: {"item": ..., "label": "A".."E"} per line.
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


CONDS = ("gold", "all", "k20")


def _write_judge(folder: Path, items: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "batch.jsonl").open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    shutil.copyfile(RUBRIC, folder / "INSTRUCTIONS.md")


def prep(rows_path: str, out: str) -> None:
    turns = {(t["life_id"], t["turn_index"]): t for t in load(BANK / "turns.jsonl")}
    facts = {f["fact_id"]: f for f in load(BANK / "truth.jsonl")}
    by_ask = defaultdict(dict)
    for r in load(rows_path):
        t = turns[(r["life_id"], r["turn_index"])]
        if t["gold"]["type"] in ("value", "yes", "no"):
            by_ask[(r["life_id"], r["turn_index"])][r["cond"]] = r
    key, groups = {}, defaultdict(list)
    n = 0
    for i, ak in enumerate(sorted(by_ask)):
        t = turns[ak]
        ev_turns = sorted({facts[f]["taught_turn"] for f in t["gold"]["uses_facts"]})
        evidence = [f"(day {turns[(ak[0], j)]['day']}) {turns[(ak[0], j)]['user_text']}" for j in ev_turns]
        for g in range(3):
            r = by_ask[ak].get(CONDS[(i + g) % 3])
            if r is None:
                continue
            iid = f"y{n:04d}"
            n += 1
            key[iid] = {"life_id": r["life_id"], "turn_index": r["turn_index"], "cond": r["cond"], "group": g,
                        "ask_type": r["ask_type"], "label_p382": r["label_p382"]}
            groups[g].append({"item": iid, "question": t["user_text"], "gold_answer": gold_answer(t),
                              "evidence": evidence, "reply": r["reply382"]})
    o = Path(out)
    for g, items in groups.items():
        random.Random(SEED + g).shuffle(items)
        for j in ("a", "b"):
            _write_judge(o / f"judge_g{g}_{j}", items)
    (o.parent / "y1d_blind_key.json").write_text(json.dumps(key, indent=0), encoding="utf-8")
    print(json.dumps({"items": len(key), "per_group": {g: len(v) for g, v in groups.items()},
                      "by_cond": Counter(k["cond"] for k in key.values())}))


def _labels(folder: Path) -> dict:
    p = folder / "labels" / "batch.jsonl"
    return {x["item"]: x["label"] for x in load(p)} if p.exists() else {}


def splits(out: str) -> None:
    o = Path(out)
    for g in range(3):
        a, b = _labels(o / f"judge_g{g}_a"), _labels(o / f"judge_g{g}_b")
        items = load(o / f"judge_g{g}_a" / "batch.jsonl")
        miss = [it["item"] for it in items if it["item"] not in a or it["item"] not in b]
        if miss:
            raise SystemExit(f"group {g}: {len(miss)} items unlabelled")
        sp = [it for it in items if a[it["item"]] != b[it["item"]]]
        if sp:
            _write_judge(o / f"judge_g{g}_c", sp)
        print(json.dumps({"group": g, "items": len(items), "splits": len(sp)}))


def score(key_path: str, out: str) -> dict:
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    o = Path(out)
    final, agree, nsplit = {}, 0, 0
    for g in range(3):
        a, b, c = (_labels(o / f"judge_g{g}_{j}") for j in ("a", "b", "c"))
        for iid, k in key.items():
            if k["group"] != g:
                continue
            if iid not in a or iid not in b:
                raise SystemExit(f"group {g}: {iid} unlabelled")
            if a[iid] == b[iid]:
                agree += 1
                final[iid] = a[iid]
            else:
                nsplit += 1
                if iid not in c:
                    raise SystemExit(f"group {g}: split {iid} needs the third judge")
                final[iid] = c[iid]
    tab = defaultdict(Counter)
    for i, k in key.items():
        tab[k["cond"]][final[i]] += 1
        tab[k["cond"] + "|" + k["ask_type"]][final[i]] += 1
    mech = Counter(f"mech_right={key[i]['label_p382'] in ('RIGHT', 'RIGHT_CONFIRM')} judged_A={final[i] == 'A'}"
                   for i in key)
    res = {"items": len(key), "agree": agree, "splits": nsplit,
           "A_right": {c: v.get("A", 0) for c, v in tab.items() if "|" not in c},
           "counts": {c: dict(sorted(v.items())) for c, v in sorted(tab.items())}, "mech_vs_judged": dict(mech)}
    print(json.dumps(res, indent=1))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--rows", required=True)
    p.add_argument("--out", required=True)
    sp = sub.add_parser("splits")
    sp.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--key", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "prep":
        prep(a.rows, a.out)
    elif a.cmd == "splits":
        splits(a.out)
    else:
        score(a.key, a.out)


if __name__ == "__main__":
    main()
