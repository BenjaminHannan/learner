#!/usr/bin/env python3
"""uw-2 panel blind audit of the correction labels. Wrong-as-fact thread, 2026-09-26. New file. Prints counts and ids
only (never text), so the builder can run it on the TEST-ONLY bank.

  nogold DIR OUT       OUT/turns_nogold.jsonl: life_id, turn_index, user_text only (no kinds, facts, gold or truth)
  compare DIR ANSWERS  ANSWERS = JSON Lines, one per turn the auditor says changes something the user said earlier:
                       {life_id, turn_index, whose, new_value}. "whose" is a name from the life, or "me" for the user.
                       Agreement per correction: the turn is listed, whose matches the gold owner (the 336 scorer's
                       owner rule, via claude_uw1_cards.owner_ok) and new_value names the gold new value (whole words).
                       Prints counts; writes DIR/../audit/disagree_ids.json (ids only).
  --selftest
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_uw1_cards as U  # noqa: E402
import claude_uw2_panelcheck as PC  # noqa: E402


def ld(p: Path) -> list:
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def nogold(d: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rows = [{"life_id": t["life_id"], "turn_index": t["turn_index"], "user_text": t["user_text"]}
            for t in sorted(ld(d / "turns.jsonl"), key=lambda t: (t["life_id"], t["turn_index"]))]
    (out / "turns_nogold.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                            encoding="utf-8")
    print(json.dumps({"turns": len(rows), "lives": len({r["life_id"] for r in rows})}))


def compare(d: Path, answers: Path) -> dict:
    cards = {c["card"]: c for c in U.cards_bank(d)}
    got = {}
    for a in ld(answers):
        got.setdefault(f"{a['life_id']}:{a['turn_index']}", a)
    c = Counter()
    dis = {"missed": [], "owner_or_value": [], "extra": []}
    for k, card in cards.items():
        g = card["gold"]
        a = got.get(k)
        eo = PC.earlier_owner(card)
        if g["type"] == "CHANGE":
            c["corrections"] += 1
            c["earlier_owner"] += eo
            if a is None:
                c["missed"] += 1
                dis["missed"].append(k)
            elif U.owner_ok(a.get("whose", ""), g["owner"]) and U._vmatch(a.get("new_value", ""), g["value"]):
                c["agree"] += 1
                c["agree_earlier_owner"] += eo
            else:
                c["owner_or_value_differs"] += 1
                dis["owner_or_value"].append(k)
        elif a is not None:
            c["extra"] += 1
            c[f"extra_{card['group']}"] += 1
            dis["extra"].append(k)
    c["answers_not_a_turn"] = sum(k not in cards for k in got)
    out = d.parent / "audit"
    out.mkdir(parents=True, exist_ok=True)
    (out / "disagree_ids.json").write_text(json.dumps(dis, indent=1), encoding="utf-8")
    res = dict(sorted(c.items()))
    print(json.dumps(res))
    return res


def selftest() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d) / "bank"
        d.mkdir()
        turns = [{"life_id": "sf-t-01", "day": 1, "turn_index": i, "user_text": t, "kind": k, "ask_type": None,
                  "facts": [], "gold": None, "creative_seed_facts": []}
                 for i, k, t in [(0, "teach", "my sister Oriel lives in Tamsby"), (1, "smalltalk", "hi"),
                                 (2, "correct", "oops she lives in Varn"), (3, "nosave", "maybe i'll move")]]
        truth = [{"fact_id": "f1", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Tamsby",
                  "taught_turn": 0, "valid_until_turn": 2},
                 {"fact_id": "f2", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Varn",
                  "taught_turn": 2, "valid_until_turn": None}]
        corr = [{"life_id": "sf-t-01", "turn_index": 2, "old_fact": "f1", "new_fact": "f2", "style": 2}]
        for name, rows in (("turns", turns), ("truth", truth), ("corrections", corr), ("decoys", [])):
            (d / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        ans = d.parent / "ans.jsonl"
        ans.write_text(json.dumps({"life_id": "sf-t-01", "turn_index": 2, "whose": "Oriel", "new_value": "Varn"}) + "\n"
                       + json.dumps({"life_id": "sf-t-01", "turn_index": 3, "whose": "me", "new_value": "x"}) + "\n")
        r = compare(d, ans)
        assert r["agree"] == 1 == r["agree_earlier_owner"] == r["extra"] and r["corrections"] == 1, r
        nogold(d, d.parent / "ng")
        rows = ld(d.parent / "ng" / "turns_nogold.jsonl")
        assert len(rows) == 4 and set(rows[0]) == {"life_id", "turn_index", "user_text"}
    print("selftest ok")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    elif sys.argv[1] == "nogold":
        nogold(Path(sys.argv[2]), Path(sys.argv[3]))
    elif sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
