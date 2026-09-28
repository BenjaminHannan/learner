#!/usr/bin/env python3
"""vread2 scorer (vector-reader thread, 2026-09-28): arm A vs arm B on the fresh Luna rows (chunks 11-13), per seed.

Saves, right and wrong saves, wrong turns and the backref family counts come from scripts/claude_vread_score.py
unchanged (score, choose_bar). This file adds the owner-name copy bins and the marks in PASSMARKS.md.

Owner copies of a gold card: claude_vread2_data.owner_copies (every whole-word exact copy of the owner name in the
turn, previous reply and earlier-turn lines). Bins: 1, 2, 3+ copies.
Matched card: in a backref row, each emitted card (any confidence) takes the first unused gold card with the same
relation and state, preferring one equal in all four fields (claude_vread_score.score's pointer check does the same).
Right-owner card: a matched card whose owner equals the gold owner (lower-cased). Low: its conf < 0.97.

  python -B scripts/claude_vread2_score.py bar --cal-rows CAL --reads-dir DIR --out bar.json
  python -B scripts/claude_vread2_score.py score --rows FRESH --reads READS --tokenizer DIR --bar T --out OUT.json
  python -B scripts/claude_vread2_score.py verdict --scores DIR --out verdict.json
  python -B scripts/claude_vread2_score.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_vread_score as VS  # noqa: E402  (read only)
import claude_vread2_data as D2  # noqa: E402

LOW = 0.97
CKPTS = ("A-s327", "B-s327", "A-s331", "B-s331")
SEEDS = (327, 331)
PROB_NAMES = ["exist", "state", "rel", "os", "oe", "vs", "ve"]
PERSON_RELS = {"apprentice", "aunt", "babysitter", "best_friend", "boss", "brother", "brother_in_law", "child",
               "classmate", "coach", "colleague", "cousin", "daughter", "daughter_in_law", "dentist", "doctor",
               "ex_husband", "ex_wife", "father", "father_in_law", "fiance", "friend", "goddaughter", "godfather",
               "godmother", "grandchild", "granddaughter", "grandfather", "grandmother", "grandson", "great_aunt",
               "great_grandfather", "great_grandmother", "great_uncle", "half_brother", "half_sister", "head_coach",
               "husband", "landlord", "mentor", "mother", "mother_in_law", "neighbour", "nephew", "niece", "parent",
               "partner", "rival", "roommate", "sibling", "sister", "sister_in_law", "son", "son_in_law", "spouse",
               "stepbrother", "stepdaughter", "stepfather", "stepmother", "stepsister", "stepson", "teacher",
               "teammate", "therapist", "tutor", "uncle", "vet"}


def pct(n, d):
    return None if not d else 100.0 * n / d


def attach_gold_copies(rows, tok):
    for r in rows:
        offs = tok(r["prompt"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        r["_copies"] = D2.owner_copies(r, offs)
        r["_offs"] = offs
    return rows


def dialog_names(rows):
    """per dialog: person names in its gold cards (non-me owners, and values of person relations)"""
    out = {}
    for r in rows:
        s = out.setdefault(r["id"].rsplit("-t", 1)[0], set())
        for c in r["cards"]:
            if c["owner"] != "me":
                s.add(c["owner"])
            if c["rel"] in PERSON_RELS:
                s.add(c["value"])
    return out


def match_cards(cards, gold):
    """[(card, gold index or None)] as the pointer check of claude_vread_score.score"""
    used, out = set(), []
    for c in cards:
        cand = [k for k, g in enumerate(gold) if k not in used and g["rel"] == c["rel"] and g["state"] == c["state"]]
        if not cand:
            out.append((c, None))
            continue
        k = next((k for k in cand if VS.same(c, gold[k])), cand[0])
        used.add(k)
        out.append((c, k))
    return out


def owner_bins(rows, reads, names):
    rd = {x["id"]: x for x in reads}
    b = Counter()
    low_min = Counter()
    for r in rows:
        if r["family"] != "backref":
            continue
        regions = D2.row_regions(r)
        dn = names.get(r["id"].rsplit("-t", 1)[0], set())
        gold = r["cards"]
        for c, k in match_cards((rd.get(r["id"]) or {}).get("cards") or [], gold):
            if k is None or r["_copies"][k] is None:
                continue
            g, cp = gold[k], r["_copies"][k]
            bn = D2.copy_bin(len(cp))
            b[f"matched:{bn}"] += 1
            right_owner = VS.norm(c["owner"]) == VS.norm(g["owner"])
            rivals = {n for n in dn if VS.norm(n) != VS.norm(g["owner"]) and n != "me"
                      and D2.copies(n, r["prompt"], regions, r["_offs"])}
            if rivals:
                b["rival_named:matched"] += 1
            if right_owner:
                b[f"right_owner:{bn}"] += 1
                if c["conf"] < LOW:
                    b[f"right_owner_low:{bn}"] += 1
                    low_min[PROB_NAMES[min(range(7), key=lambda i: c["p7"][i])]] += 1
            elif c["owner"] == "me":
                b["owner_me_instead"] += 1
            else:
                b["wrong_person"] += 1
                if rivals:
                    b["rival_named:wrong_person"] += 1
                if c.get("owner_tokens") and c["owner_tokens"][0] > max(s for s, _ in cp):
                    b["wrong_person_newer_than_gold"] += 1
    sh = {bn: pct(b[f"right_owner_low:{bn}"], b[f"right_owner:{bn}"]) for bn in ("1", "2", "3+")}
    return dict(sorted(b.items())), sh, dict(sorted(low_min.items()))


def lowest_prob(reads):
    c = Counter()
    for x in reads:
        for card in x["cards"]:
            if card["conf"] < LOW:
                c[PROB_NAMES[min(range(7), key=lambda i: card["p7"][i])]] += 1
    return dict(sorted(c.items()))


def score_one(rows, reads, bar, tok=None):
    if tok is not None:
        attach_gold_copies(rows, tok)
    back = [r for r in rows if r["family"] == "backref"]
    main = VS.score(rows, reads, "vector", bar, "main")
    hist097 = VS.score(back, reads, "vector", LOW, "hist")
    hist_own = VS.score(back, reads, "vector", bar, "hist")
    bins, shares, low_min = owner_bins(rows, reads, dialog_names(rows))
    gold = Counter()
    for r in back:
        for cp in r["_copies"]:
            gold["backref_cards"] += 1
            gold[f"backref_cards_copies_{'me' if cp is None else D2.copy_bin(len(cp))}"] += 1
    return {"bar": bar, "rows": len(rows), "gold": dict(sorted(gold.items())),
            "M_wrong_turns_main_own_bar": main["wrong_turns"], "right_saves_main_own_bar": main["right_saves"],
            "wrong_saves_main_own_bar": main["wrong_saves"],
            "backref_right_saves_hist_097": hist097["family"]["backref:right"],
            "backref_wrong_saves_hist_097": hist097["wrong_saves"],
            "backref_right_saves_hist_own_bar": hist_own["family"]["backref:right"],
            "backref_wrong_saves_hist_own_bar": hist_own["wrong_saves"],
            "owner_bins": bins, "right_owner_low_share_pct": shares,
            "right_owner_low_lowest_prob": low_min, "all_low_cards_lowest_prob": lowest_prob(reads),
            "main": main, "backref_hist_097": hist097}


def verdict(S):
    """S: {ckpt: score}; the marks in PASSMARKS.md"""
    g = S["A-s327"]["gold"]
    n_back, n3 = g.get("backref_cards", 0), g.get("backref_cards_copies_3+", 0)
    m = {"validity": {"backref_cards": n_back, "backref_cards_3plus": n3, "by_seed": {}}}
    per = {}
    for s in SEEDS:
        A, B = S[f"A-s{s}"], S[f"B-s{s}"]
        a1, a3 = A["right_owner_low_share_pct"]["1"], A["right_owner_low_share_pct"]["3+"]
        b1, b3 = B["right_owner_low_share_pct"]["1"], B["right_owner_low_share_pct"]["3+"]
        rep = None not in (a1, a3) and a3 - a1 >= 25
        m["validity"]["by_seed"][s] = {"A_low_pct_1": a1, "A_low_pct_3plus": a3, "A_repeats_pattern": rep}
        M1 = None not in (b1, b3) and b3 - b1 <= 10
        M2 = B["backref_right_saves_hist_097"] >= A["backref_right_saves_hist_097"] + 0.05 * n_back
        M3 = (B["M_wrong_turns_main_own_bar"] <= A["M_wrong_turns_main_own_bar"] + 2
              and B["backref_wrong_saves_hist_097"] <= A["backref_wrong_saves_hist_097"] + 2)
        pw = None not in (a3, b3) and abs(b3 - a3) <= 10
        per[s] = {"M1": {"B_low_pct_1": b1, "B_low_pct_3plus": b3, "gap": None if None in (b1, b3) else b3 - b1,
                         "met": M1},
                  "M2": {"A": A["backref_right_saves_hist_097"], "B": B["backref_right_saves_hist_097"],
                         "need": A["backref_right_saves_hist_097"] + 0.05 * n_back, "met": M2},
                  "M3": {"A_wrong_turns": A["M_wrong_turns_main_own_bar"], "B_wrong_turns": B["M_wrong_turns_main_own_bar"],
                         "A_backref_wrong_saves_097": A["backref_wrong_saves_hist_097"],
                         "B_backref_wrong_saves_097": B["backref_wrong_saves_hist_097"], "met": M3},
                  "proved_wrong_seed": {"A_low_pct_3plus": a3, "B_low_pct_3plus": b3, "within_10": pw}}
    m["by_seed"] = per
    valid = n_back >= 200 and n3 >= 60 and all(v["A_repeats_pattern"] for v in m["validity"]["by_seed"].values())
    m["validity"]["met"] = valid
    passed = all(per[s][k]["met"] for s in SEEDS for k in ("M1", "M2", "M3"))
    wrong = valid and all(per[s]["proved_wrong_seed"]["within_10"] for s in SEEDS)
    m["passed_all_marks"] = passed
    m["proved_wrong"] = wrong
    m["verdict"] = "INCONCLUSIVE" if not valid else "PASS" if passed else "FAIL (proved wrong)" if wrong else "FAIL"
    return m


def selftest():
    C = lambda o, r, v, s: {"owner": o, "rel": r, "value": v, "state": s}  # noqa: E731
    def row(i, fam, prompt, cards, cps):
        return {"id": i, "family": fam, "turn": "she moved to Velbrook", "prev_reply": "", "history": [],
                "prompt": prompt, "cards": cards, "_copies": cps, "_offs": None}
    rows = [row("d1-t2", "backref", "p", [C("Mira", "city", "Velbrook", "current")], [[(1, 1), (5, 5), (9, 9)]]),
            row("d2-t2", "backref", "p", [C("Kel", "city", "Dunmere", "current")], [[(3, 3)]]),
            row("d3-t2", "backref", "p", [C("Ana", "city", "Orla", "current")], [[(4, 4)]])]
    D2.row_regions = lambda r: []                     # no prompt text here: rivals never found
    P = lambda conf, i=3: [1.0 if j != i else conf for j in range(7)]  # noqa: E731
    reads = [{"id": "d1-t2", "cards": [dict(C("Mira", "city", "Velbrook", "current"), conf=0.5, p7=P(0.5),
                                            owner_tokens=[9, 9])]},
             {"id": "d2-t2", "cards": [dict(C("Kel", "city", "Dunmere", "current"), conf=0.99, p7=P(0.99))]},
             {"id": "d3-t2", "cards": [dict(C("Tovan", "city", "Orla", "current"), conf=0.99, p7=P(0.99),
                                            owner_tokens=[8, 8])]}]
    bins, sh, low = owner_bins(rows, reads, {})
    assert sh == {"1": 0.0, "2": None, "3+": 100.0} and bins["wrong_person"] == 1, (bins, sh)
    assert bins["wrong_person_newer_than_gold"] == 1 and low == {"os": 1}, (bins, low)
    mk = lambda l1, l3, br, wt, bw: {"gold": {"backref_cards": 200, "backref_cards_copies_3+": 60},  # noqa: E731
                                     "right_owner_low_share_pct": {"1": l1, "2": None, "3+": l3},
                                     "backref_right_saves_hist_097": br, "M_wrong_turns_main_own_bar": wt,
                                     "backref_wrong_saves_hist_097": bw}
    S = {"A-s327": mk(5, 60, 100, 3, 1), "B-s327": mk(5, 12, 110, 5, 3),
         "A-s331": mk(0, 40, 100, 3, 1), "B-s331": mk(2, 10, 110, 4, 2)}
    assert verdict(S)["verdict"] == "PASS", verdict(S)
    S["B-s331"] = mk(2, 10, 109, 4, 2)                # M2 short by 1 (need 110)
    assert verdict(S)["verdict"] == "FAIL"
    S["B-s327"], S["B-s331"] = mk(5, 55, 110, 3, 1), mk(2, 45, 110, 3, 1)
    assert verdict(S)["verdict"] == "FAIL (proved wrong)"
    S["A-s331"] = mk(20, 40, 100, 3, 1)               # A's gap 20 < 25: pattern not repeated
    assert verdict(S)["verdict"] == "INCONCLUSIVE"
    print("vread2 score selftest ok: copy bins, low shares, wrong person, lowest probability, verdict branches")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bar", "score", "verdict", "selftest"])
    ap.add_argument("--rows")
    ap.add_argument("--cal-rows")
    ap.add_argument("--reads")
    ap.add_argument("--reads-dir")
    ap.add_argument("--scores")
    ap.add_argument("--tokenizer")
    ap.add_argument("--bar", type=float)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "bar":
        cal = VS.load(a.cal_rows)
        res = {"rule": f"claude_vread_score.choose_bar unchanged: lowest of {VS.BAR_GRID} with wrong saves <= "
                       f"{VS.BAR_MAX_WRONG_SHARE:.1%} of saves on the calibration slice (main rule); 0.999 if none"}
        for ck in CKPTS:
            bar, table = VS.choose_bar(cal, VS.load(Path(a.reads_dir) / f"cal_{ck}.jsonl"))
            res[ck] = {"bar": bar, "table": table}
    elif a.cmd == "score":
        from transformers import AutoTokenizer
        res = score_one(VS.load(a.rows), VS.load(a.reads), a.bar, AutoTokenizer.from_pretrained(a.tokenizer))
    else:
        res = verdict({ck: json.loads((Path(a.scores) / f"{ck}.json").read_text()) for ck in CKPTS})
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n", encoding="utf-8")
    print(txt if a.cmd != "score" else json.dumps({k: res[k] for k in res if k not in ("main", "backref_hist_097")},
                                                    indent=1))


if __name__ == "__main__":
    sys.exit(main())
