#!/usr/bin/env python3
"""uw-2 marks U1-U6 (artifacts/claude-uw2-20260926/PASSMARKS-uw2.md, "Marks"). Wrong-as-fact thread, 2026-09-27,
written and sealed before any uw-2 panel or DEV row exists. New file. Prints counts only (never card text), so it may
read the TEST-ONLY panel.

  panel PANEL ROWS_A ROWS_B   cards from claude_uw1_cards.cards_bank(PANEL). Each rows file must hold exactly one
                              row per card with arm B (the note prompt). Every row is re-parsed from its raw output
                              (parse_note) and re-graded (grade); a stored parse or grade that differs stops the run.
                              E, C, O as PASSMARKS; earlier-owner = claude_uw2_panelcheck.earlier_owner.
                              Prints one JSON line: counts per arm, the six rows with bars, verdict, proved_wrong,
                              corrections right by style.
  dev ROWS_DEV                DEV stop rule: stop if FALSE_CHANGE > 26 or RIGHT < 10 (grades as stored by run).
  --selftest
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_uw1_cards as U  # noqa: E402
import claude_uw2_panelcheck as PC  # noqa: E402

DEV_MAX_FALSE, DEV_MIN_RIGHT = 26, 10
MIN_E = 30


def arm_counts(cards: list[dict], rows_path: Path) -> dict:
    rows = U.ld(rows_path)
    by = {r["card"]: r for r in rows}
    assert len(rows) == len(by) == len(cards) and set(by) == {c["card"] for c in cards}, \
        ("rows do not match the cards one to one", rows_path.name, len(rows), len(by), len(cards))
    n = Counter()
    for c in cards:
        r = by[c["card"]]
        assert r["arm"] == "B", ("rows must use the note prompt (arm B)", rows_path.name)
        p = U.parse_note(r["raw"], c["notes"])
        g = U.grade(c, p)
        assert p == r["parsed"] and g == r["grade"], ("stored parse or grade differs", rows_path.name)
        corr = c["gold"]["type"] == "CHANGE"
        n["UNPARSED"] += g == "UNPARSED"
        if corr:
            n["C_right"] += g == "RIGHT"
            n["C_wrong_change"] += g == "WRONG_CHANGE"
            n[f"style_{c['gold']['style']}_right"] += g == "RIGHT"
            if PC.earlier_owner(c):
                n["E_right"] += g == "RIGHT"
        else:
            n["O_false_change"] += g == "FALSE_CHANGE"
            if c["group"] in ("decoy", "nosave"):
                n["DN_false_change"] += g == "FALSE_CHANGE"
    return dict(sorted(n.items()))


def marks(cards: list[dict], a: dict, b: dict, min_e: int = MIN_E) -> dict:
    corr = [c for c in cards if c["gold"]["type"] == "CHANGE"]
    e = sum(PC.earlier_owner(c) for c in corr)
    cc, o = len(corr), len(cards) - len(corr)
    g = lambda d, k: d.get(k, 0)  # noqa: E731
    rows = {
        "U1": {"A": g(a, "E_right"), "B": g(b, "E_right"), "bar": f">= A + {max(10, math.ceil(e / 3))}",
               "pass": g(b, "E_right") >= g(a, "E_right") + max(10, math.ceil(e / 3))},
        "U2": {"A": g(a, "C_right"), "B": g(b, "C_right"), "bar": f">= A + {max(15, math.ceil(cc / 4))}",
               "pass": g(b, "C_right") >= g(a, "C_right") + max(15, math.ceil(cc / 4))},
        "U3": {"A": g(a, "O_false_change"), "B": g(b, "O_false_change"), "bar": f"<= {math.ceil(o / 100)}",
               "pass": g(b, "O_false_change") <= math.ceil(o / 100)},
        "U4": {"A": g(a, "DN_false_change"), "B": g(b, "DN_false_change"), "bar": "<= 2",
               "pass": g(b, "DN_false_change") <= 2},
        "U5": {"A": g(a, "C_wrong_change"), "B": g(b, "C_wrong_change"), "bar": f"<= {math.ceil(cc / 10)}",
               "pass": g(b, "C_wrong_change") <= math.ceil(cc / 10)},
        "U6": {"A": g(a, "UNPARSED"), "B": g(b, "UNPARSED"), "bar": f"<= {math.ceil((cc + o) / 50)}",
               "pass": g(b, "UNPARSED") <= math.ceil((cc + o) / 50)},
    }
    if e < min_e:
        verdict, proved_wrong = "INCONCLUSIVE", None
    else:
        verdict = "PASS" if all(r["pass"] for r in rows.values()) else "FAIL"
        proved_wrong = g(b, "E_right") <= g(a, "E_right") + 2
    styles = sorted({str(c["gold"]["style"]) for c in corr})
    return {"E": e, "C": cc, "O": o, "decoy_nosave": sum(c["group"] in ("decoy", "nosave") for c in cards),
            "marks": rows, "verdict": verdict, "proved_wrong": proved_wrong,
            "right_by_style": {s: {"of": sum(str(c["gold"]["style"]) == s for c in corr),
                                   "A": g(a, f"style_{s}_right"), "B": g(b, f"style_{s}_right")} for s in styles}}


def dev(rows_path: Path) -> dict:
    n = Counter(r["grade"] for r in U.ld(rows_path))
    return {"rows": sum(n.values()), "RIGHT": n["RIGHT"], "FALSE_CHANGE": n["FALSE_CHANGE"],
            "DEV_STOP": n["FALSE_CHANGE"] > DEV_MAX_FALSE or n["RIGHT"] < DEV_MIN_RIGHT}


def selftest() -> None:
    life = [(0, "teach", "my sister Oriel lives in Tamsby"), (1, "smalltalk", "long day"),
            (2, "correct", "oops, she lives in Varn actually"), (3, "correct", "Oriel is 31 btw, not 30"),
            (4, "nosave", "maybe i'll move"), (5, "smalltalk", "she said hi")]
    turns = [{"life_id": "sf-t-01", "day": 1, "turn_index": i, "user_text": t, "kind": k, "ask_type": None,
              "facts": [], "gold": None, "creative_seed_facts": []} for i, k, t in life]
    truth = [{"fact_id": "f1", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Tamsby",
              "taught_turn": 0, "valid_until_turn": 2},
             {"fact_id": "f2", "life_id": "sf-t-01", "owner": "Oriel", "relation": "lives_in", "value": "Varn",
              "taught_turn": 2, "valid_until_turn": None},
             {"fact_id": "f3", "life_id": "sf-t-01", "owner": "Oriel", "relation": "age", "value": "30",
              "taught_turn": 0, "valid_until_turn": 3},
             {"fact_id": "f4", "life_id": "sf-t-01", "owner": "Oriel", "relation": "age", "value": "31",
              "taught_turn": 3, "valid_until_turn": None}]
    corr = [{"life_id": "sf-t-01", "turn_index": 2, "old_fact": "f1", "new_fact": "f2", "style": 2},
            {"life_id": "sf-t-01", "turn_index": 3, "old_fact": "f3", "new_fact": "f4", "style": 5}]
    decoys = [{"life_id": "sf-t-01", "turn_index": 5}]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for name, rows in (("turns", turns), ("truth", truth), ("corrections", corr), ("decoys", decoys)):
            (d / f"{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        cards = U.cards_bank(d)
        assert [c["group"] for c in cards] == ["teach", "smalltalk", "correct", "correct", "nosave", "decoy"]
        # A: says NONE everywhere except a false change on the decoy. B: both corrections right (card 2 via note 1,
        # card 3 via note 1), a false change on the nosave card, one unparsed smalltalk card.
        raws = {"A": ["NONE", "NONE", "NONE", "NONE", "NONE", "UPDATE 1 | Varn"],
                "B": ["NONE", "hmm", "UPDATE 1 | Varn", "UPDATE 1 | 31", "UPDATE 1 | Varn", "NONE"]}
        paths = {}
        for arm, outs in raws.items():
            paths[arm] = d / f"rows_{arm}.jsonl"
            with open(paths[arm], "w", encoding="utf-8") as fh:
                for c, raw in zip(cards, outs):
                    p = U.parse_note(raw, c["notes"])
                    fh.write(json.dumps({"card": c["card"], "arm": "B", "group": c["group"], "raw": raw, "parsed": p,
                                         "grade": U.grade(c, p), "extra": U.report_extra(c, p)}) + "\n")
        a, b = arm_counts(cards, paths["A"]), arm_counts(cards, paths["B"])
        assert (a.get("C_right", 0), b["C_right"], b["E_right"], b["UNPARSED"]) == (0, 2, 1, 1), (a, b)
        assert (a["DN_false_change"], b["DN_false_change"], b["O_false_change"]) == (1, 1, 1), (a, b)
        m = marks(cards, a, b)
        assert (m["E"], m["C"], m["O"], m["decoy_nosave"]) == (1, 2, 4, 2), m
        assert m["verdict"] == "INCONCLUSIVE" and m["proved_wrong"] is None, m
        assert m["right_by_style"] == {"2": {"of": 1, "A": 0, "B": 1}, "5": {"of": 1, "A": 0, "B": 1}}, m
        assert not m["marks"]["U1"]["pass"] and m["marks"]["U4"]["pass"] and m["marks"]["U6"]["pass"], m
        m1 = marks(cards, a, b, min_e=1)
        assert m1["verdict"] == "FAIL" and m1["proved_wrong"] is True, m1
        bad = [json.loads(x) for x in open(paths["B"], encoding="utf-8")]
        bad[2]["grade"] = "MISSED"
        paths["bad"] = d / "rows_bad.jsonl"
        paths["bad"].write_text("".join(json.dumps(r) + "\n" for r in bad), encoding="utf-8")
        try:
            arm_counts(cards, paths["bad"])
            raise SystemExit("a changed stored grade must stop the run")
        except AssertionError:
            pass
        paths["short"] = d / "rows_short.jsonl"
        paths["short"].write_text("".join(json.dumps(r) + "\n" for r in bad[:5]), encoding="utf-8")
        try:
            arm_counts(cards, paths["short"])
            raise SystemExit("a missing card must stop the run")
        except AssertionError:
            pass
        dv = dev(paths["B"])
        assert dv == {"rows": 6, "RIGHT": 2, "FALSE_CHANGE": 1, "DEV_STOP": True}, dv
    print("selftest ok")


def main() -> int:
    a = sys.argv[1:]
    if a == ["--selftest"]:
        selftest()
    elif len(a) == 4 and a[0] == "panel":
        cards = U.cards_bank(Path(a[1]))
        ca, cb = arm_counts(cards, Path(a[2])), arm_counts(cards, Path(a[3]))
        print(json.dumps({"cards": len(cards), **marks(cards, ca, cb)}, sort_keys=True))
    elif len(a) == 2 and a[0] == "dev":
        print(json.dumps(dev(Path(a[1]))))
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
