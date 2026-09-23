#!/usr/bin/env python3
"""Exp 221 -- field-map adapter for the sealed blind panel (written AFTER
the panel was opened; every change here is a listed deviation).

Runs scripts/fable_fix221_panel.py main() unchanged except:
  D-map-1  load_items: panel fields setup/question/family/gold read
           directly; gold "A; B" split on "; " (README: all must be given).
  D-map-2  multi-answer gold scored as ALL parts present (panel rule), not
           "any" as the sealed runner does for a gold list.
  D-map-3  "other taught values" for the wrong-value test come from the
           panel's stored_after_setup triples, not the runner's regex over
           setup sentences (strictly more accurate; same meaning).
  D-map-4  P2 also counts the scored turn of items whose question has no
           "?" (p221-085 "Tell me ...'s.") -- via rows' wrote221.
Run: python -B scripts/fable_fix221_panelmap.py --items PANEL --out DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_fix221_panel as P  # noqa: E402

_ORIG_SCORE = P.score


def load_items(path: Path) -> list[dict]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        turns = [str(s) for s in it["setup"]] + [str(it["question"])]
        gold = [g.strip() for g in str(it["gold"]).split("; ") if g.strip()]
        items.append({"id": it["id"], "turns": turns,
                      "scored": [(len(turns) - 1, it["family"], gold)],
                      "raw_family": it["family"],
                      "stored_values": [t[2] for t in
                                        it.get("stored_after_setup", [])],
                      "expected_reply": it.get("expected_reply")})
    return items


def score(item, j, fam, gold, r221, r138):
    row = _ORIG_SCORE(item, j, fam, gold, r221, r138)
    low = P._n(r221["reply"])
    fl = fam.lower()
    if fl in ("untaught", "no_relation", "self"):
        gold_eff = []  # "abstain"/"clarify"/"current path" are labels
    else:
        gold_eff = gold
    has_all = bool(gold_eff) and all(P._n(g) in low for g in gold_eff)
    has_any = any(P._n(g) in low for g in gold_eff)
    other = [v for v in item.get("stored_values", [])
             if not any(P._n(v) == P._n(g) for g in gold_eff)
             and P._n(v) in low]
    abst = row["abstain221"]
    nu = P.NOT_UNDERSTOOD in low
    if fl == "self":
        ok = r221["reply"] == r138["reply"]
    elif fl == "untaught":
        ok = abst and not other
    elif fl == "no_relation":
        ok = not other and not r221["wrote"]
    else:
        inv = "inverse" in fl
        ok = has_all and (not inv or P.T221.LABEL221 in r221["reply"])
    row["correct221"] = ok
    row["wrong_value221"] = (not ok) and (not abst) and (not nu) \
        and bool(other) and not has_any
    row["other_values_in_reply"] = other
    row["self_matches_expected_reply"] = (
        r221["reply"] == item.get("expected_reply")
        if item.get("expected_reply") else None)
    return row


P.load_items = load_items
P.score = score

if __name__ == "__main__":
    sys.exit(P.main())
