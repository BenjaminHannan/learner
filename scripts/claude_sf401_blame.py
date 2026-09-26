#!/usr/bin/env python3
"""sf-401 after the verdict: at each edit ask, did the notebook hold the new value, the old one, both or neither?
Written 2026-09-26 after sf-401's verdict (report only, $0, answers the Thread manager's round-4 question 2). New file.
Prints counts only, never words.

  python3 scripts/claude_sf401_blame.py [RUN_DIR]     (default artifacts/claude-sf401-20260926)

The notebook state is the stored_triples snapshot of the last run row before the ask (the runner logs the whole
stored notebook after every row; values parked as pending by lis-314 are not in it). A value "is held" when a stored
triple's owner matches the fact's owner (the 336 scorer's owner_match) and its value equals the fact's value
(case-insensitive), as the 336 scorer counts facts_saved. Relation is not checked, as in the scorer.
Classes per edit ask (new = the corrected fact the ask's gold uses; old = the fact that correction closed):
  NEW_ONLY  notebook right, the answer step still missed          -> answer step
  BOTH      old and new both held, the answer step had to choose   -> answer step (the reconsolidation case)
  OLD_ONLY  the correction never replaced the old value            -> reader / save
  NEITHER   no value for this fact held at all                     -> reader / save
  NO_LINK   the ask's gold names no corrected fact                 (reported, never guessed)
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_e2e336_score as SC  # noqa: E402

ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]  # noqa: E731


def held(stored, fact) -> bool:
    return any(SC.owner_match(a, fact["owner"]) and str(v).lower() == str(fact["value"]).lower()
               for (a, _r, v) in stored)


def main() -> int:
    R = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/claude-sf401-20260926")
    turns = ld(R / "panel/turns.jsonl")
    tk = {(t["life_id"], t["turn_index"]): t for t in turns}
    truth = {f["fact_id"]: f for f in ld(R / "panel/truth.jsonl")}
    old_of = {c["new_fact"]: c["old_fact"] for c in ld(R / "panel/corrections.jsonl")}
    report = {}
    for arm in ("A", "B"):
        rows = ld(R / f"run/arm_{arm}.jsonl")
        conf = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
        by_life = defaultdict(list)
        for r in rows:
            by_life[r["life_id"]].append(r)
        table = defaultdict(Counter)
        for (life, ti), t in sorted(tk.items()):
            if t["kind"] != "ask" or t["ask_type"] != "edit":
                continue
            row = next((r for r in by_life[life] if r["turn_index"] == ti and r["kind"] == "user"), None)
            if row is None:
                table["NO_ROW"]["asks"] += 1
                continue
            mech = SC.score_ask(t, row, conf.get((life, ti)))
            right = mech in ("RIGHT", "RIGHT_CONFIRM")
            news = [f for f in t["gold"]["uses_facts"] if f in old_of]
            if len(news) != 1:
                cls = "NO_LINK"
            else:
                before = [r for r in by_life[life] if r["turn_index"] < ti and r.get("stored_triples") is not None]
                stored = {tuple(x) for x in before[-1]["stored_triples"]} if before else set()
                n, o = held(stored, truth[news[0]]), held(stored, truth[old_of[news[0]]])
                cls = {(True, False): "NEW_ONLY", (True, True): "BOTH",
                       (False, True): "OLD_ONLY", (False, False): "NEITHER"}[(n, o)]
            table[cls]["asks"] += 1
            table[cls]["right" if right else f"not_right_{mech}"] += 1
        report[arm] = {k: dict(sorted(v.items())) for k, v in sorted(table.items())}
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
