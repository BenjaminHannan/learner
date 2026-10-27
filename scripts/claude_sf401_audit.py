#!/usr/bin/env python3
"""sf-401 panel assembly and blind audit helpers. New file only. Prints counts and ids only (never text).

  merge  PARTS OUT        concatenate PARTS/p1..p4/{turns,truth,decoys,corrections}.jsonl into OUT/ (life order)
  nogold DIR OUT          OUT/turns_nogold.jsonl: life_id, day, turn_index, user_text, is_ask (no kinds, facts, gold)
                          for an auditor who answers every ask from the user's words alone
  compare DIR ANSWERS     ANSWERS = JSON Lines {life_id, turn_index, answer}; answer "IDK" for "not told", "YES"/"NO"
                          for yes/no asks, else the value(s). Agreement rules: value gold -> every gold value appears in
                          the answer (whole words, any case); yes/no gold -> same word; idk gold -> IDK.
                          Prints agreement per ask_type; writes DIR/audit/disagree_ids.json (ids only)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

FILES = ("turns", "truth", "decoys", "corrections")


def ld(p: Path) -> list:
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def wr(p: Path, rows: list) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def merge(parts: Path, out: Path) -> None:
    counts = {}
    for name in FILES:
        rows = []
        for n in (1, 2, 3, 4):
            rows += ld(parts / f"p{n}" / f"{name}.jsonl")
        key = (lambda r: (r["life_id"], r["turn_index"])) if name != "truth" else (lambda r: (r["life_id"], r["fact_id"]))
        rows.sort(key=key)
        wr(out / f"{name}.jsonl", rows)
        counts[name] = len(rows)
    print(json.dumps(counts))


def nogold(d: Path, out: Path) -> None:
    rows = [{"life_id": t["life_id"], "day": t["day"], "turn_index": t["turn_index"], "user_text": t["user_text"],
             "is_ask": t["kind"] == "ask"} for t in ld(d / "turns.jsonl")]
    wr(out / "turns_nogold.jsonl", rows)
    print(json.dumps({"rows": len(rows), "asks": sum(r["is_ask"] for r in rows)}))


def _has(text: str, v: str) -> bool:
    v = str(v).strip().lower()
    return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", str(text).lower()) is not None


def compare(d: Path, answers: Path) -> None:
    turns = {(t["life_id"], t["turn_index"]): t for t in ld(d / "turns.jsonl")}
    ans = {(a["life_id"], a["turn_index"]): str(a.get("answer", "")) for a in ld(answers)}
    c, bad = Counter(), []
    for k, t in sorted(turns.items()):
        if t["kind"] != "ask":
            continue
        g, a = t["gold"], ans.get(k)
        if a is None:
            ok = False
        elif g["type"] == "idk":
            ok = a.strip().upper() == "IDK"
        elif g["type"] in ("yes", "no"):
            ok = a.strip().upper().startswith(g["type"].upper())
        else:
            ok = all(_has(a, v) for v in g["values"]) and a.strip().upper() != "IDK"
        c[(t["ask_type"], ok)] += 1
        if not ok:
            bad.append(f"{k[0]}:{k[1]}")
    (d / "audit").mkdir(exist_ok=True)
    (d / "audit" / "disagree_ids.json").write_text(json.dumps(bad), encoding="utf-8")
    per = {}
    for (typ, ok), n in c.items():
        per.setdefault(typ, {"agree": 0, "disagree": 0})["agree" if ok else "disagree"] += n
    print(json.dumps({"asks": sum(c.values()), "agree": sum(n for (_t, ok), n in c.items() if ok),
                      "disagree": len(bad), "answers_missing": sum(1 for k, t in turns.items()
                                                                   if t["kind"] == "ask" and k not in ans),
                      "per_type": per}, sort_keys=True))


def main() -> int:
    cmd, a = sys.argv[1], [Path(x) for x in sys.argv[2:]]
    {"merge": merge, "nogold": nogold, "compare": compare}[cmd](*a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
