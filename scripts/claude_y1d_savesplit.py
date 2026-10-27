#!/usr/bin/env python3
"""y1d free split (Answering-from-memory thread, 2026-09-26). New file. DEV bank only.

For each answerable dev ask (gold type value/yes/no), was every fact it cites saved in the notebook at the ask's
row (the 336 scorer's rule: a stored triple with the same owner and the same value, case-insensitive; relation not
checked), and what did the arm reply (score_ask label)? Separates "the fact was never saved" from "saved, but the
question side lost it". Prints counts only.

  python -B scripts/claude_y1d_savesplit.py <arm_*.jsonl run on artifacts/claude-e2e331-dev-20260924> ...
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_e2e336_score as S  # noqa: E402

BANK = SCRIPTS.parent / "artifacts/claude-e2e331-dev-20260924"


def saved_at(stored, f) -> bool:
    for tr in stored or []:
        if len(tr) >= 3 and S.owner_match(tr[0], f["owner"]) and \
                str(tr[2]).strip().lower() == str(f["value"]).strip().lower():
            return True
    return False


def split(path):
    turns = S.load(BANK / "turns.jsonl")
    fid = {f["fact_id"]: f for f in S.load(BANK / "truth.jsonl")}
    rows = S.load(path)
    user = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "user"}
    conf = {(r["life_id"], r["turn_index"]): r for r in rows if r["kind"] == "confirm_answer"}
    tab, bytype = defaultdict(Counter), defaultdict(Counter)
    for t in turns:
        if t["kind"] != "ask" or t["gold"]["type"] not in ("value", "yes", "no"):
            continue
        r = user.get((t["life_id"], t["turn_index"]))
        if r is None:
            continue
        c = S.score_ask(t, r, conf.get((t["life_id"], t["turn_index"])))
        fs = [fid[x] for x in t["gold"]["uses_facts"]]
        k = sum(saved_at(r.get("stored_triples"), f) for f in fs)
        k = "all_saved" if k == len(fs) else ("some_saved" if k else "none_saved")
        tab[k][c] += 1
        tab["ALL"][c] += 1
        bytype[t["ask_type"]][k] += 1
    return tab, bytype


if __name__ == "__main__":
    for p in sys.argv[1:]:
        tab, bytype = split(p)
        print("==", Path(p).name)
        for k in ("all_saved", "some_saved", "none_saved", "ALL"):
            print(f"  {k:11s} n={sum(tab[k].values()):3d}", dict(sorted(tab[k].items())))
        print("  saved status by ask_type:", {k: dict(v) for k, v in sorted(bytype.items())})
