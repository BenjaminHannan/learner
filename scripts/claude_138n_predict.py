#!/usr/bin/env python3
"""Merge 138n -- build predicted_moves138n.json from the LAST pilot (before
the seal). Every move is listed by id with its exact expected record and a
category + reason. Run once; the output is sealed.

usage: claude_138n_predict.py <pilot_dir> <raw_pred_m2_m6.json> <out.json>
  <pilot_dir>/l1/<piece>-{own,m,n}.json      (M1 pilot rows)
  <raw_pred_m2_m6.json>  from `claude_138n_score.py --predict`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_138n_l1 as L1  # noqa: E402

CAT = {
    "base138m": "138n gives exactly 138m's record here: a 138m layer "
                "(222 teach / 224c decline / 227c / 230c / 233-234 / 209 / "
                "226) claims this turn before the piece's layer, as in 138m",
    "t237_v11": "questions read table v1.1 (237) not v1: the canonical key / "
                "extra aliases answer where the piece's own table abstained",
    "x232c_save": "232c now saves a multi-word verb-subject statement, and a "
                  "later question is answered from that save",
    "x232c_question": "232c/236 reads the multi-word name; the reply is the "
                      "name-aware abstain instead of the piece's own reply",
    "x232c_correction": "192/232c correction wording ('Updated: ... (it was "
                        "X)') replaces the piece's own correction reply",
    "t229_nosave": "229 table teach sees a base-missed statement it cannot "
                   "store and replies with its nosave clarify (no write)",
    "t229_yes": "229 / 232c confirmation path: 'yes' now confirms a pending "
                "multi-word teach",
    "g1_particle": "glue G1: 236 first-name resolution skips a candidate "
                   "that is really the start of a 232c particle name",
    "g3_cap": "glue G3: reply starting 'your ' is capitalised",
    "base_fixed_reply": "138m's fixed reply for a statement shape it cannot "
                        "save replaces the piece's own fallback (no write)",
    "base_question_fallback": "138m's question fallback wording replaces the "
                              "piece's own combined fallback",
    "table_abstain_wording": "table reader abstains with \"I don't know X's "
                             "R.\" (no write)",
    "answer_change": "an answer changes; listed by id and reviewed by hand",
    "writes_only": "same replies, different notebook (reviewed by hand)",
}
MANUAL = {
    "221c/d221c-057": ("t237_v11", "v1.1 alias makes 'bosses' read as boss; "
                       "the single stored boss is given (221c gold was "
                       "abstain) -- a known cost, true stored fact"),
    "221b/K04": ("x232c_save", "232c saves the multi-word-subject employer "
                 "statement; 221 then answers it backwards"),
    "236/d236-04": ("x232c_save", "232c saves the multi-word subject; 236 "
                    "then resolves the first name to it"),
    "236/d236-21": ("x232c_save", "232c saves the multi-word subject; 236 "
                    "then resolves the first name to it"),
    "221b/G06": ("t237_v11", "v1.1 alias doctor->physician"),
    "221b/G09": ("t237_v11", "v1.1 alias native language"),
    "221b/A01": ("t237_v11", "ambiguous wording: 221b own abstains, v1.1 "
                 "answers the table's canonical key (stored fact)"),
    "221b/A02": ("t237_v11", "ambiguous wording -> v1.1 canonical key"),
    "221b/A03": ("t237_v11", "ambiguous wording -> v1.1 canonical key"),
    "221b/A05": ("t237_v11", "ambiguous wording -> v1.1 canonical key"),
    "221b/A08": ("t237_v11", "ambiguous wording -> v1.1 canonical key"),
    "229/d229-055": ("base138m_cost", "INHERITED 138m DEFECT (known cost): "
                     "138m's 222 teach saves the pronoun subject 'He'; 229 "
                     "own refused. 138n == 138m. Not fixed in this merge."),
    "229/d229-034": ("base138m_rawkey", "138m's 222 teach claims the "
                     "statement first and saves the raw key; 138n == 138m"),
    "229/d229-039": ("base138m_rawkey", "as d229-034"),
    "229/d229-041": ("base138m_rawkey", "as d229-034"),
    "229/d229-043": ("base138m_rawkey", "as d229-034"),
    "229/d229-076": ("base138m_rawkey", "as d229-034"),
    "229/d229-031": ("base138m_teach", "138m's 222 teach saves the right "
                     "direction; 229 own saved a broken key. 138n == 138m"),
    "229/d229-065": ("base138m_teach", "138m's 222 teach saves it; 138n == "
                     "138m"),
}


ABST = ("I don't know", "didn't understand", "I do not know",
        "I did not save", "couldn't save", "can't save",
        "Was that a question", "not sure")


def _abst(s: str) -> bool:
    return any(k in s for k in ABST)


def turn_cat(o: str, x: str) -> str:
    if o and x == o[0].upper() + o[1:]:
        return "g3_cap"
    if "I did not save that" in x:
        return "t229_nosave"
    if "Updated:" in x and "(it was" in x:
        return "x232c_correction"
    if "know anyone called" in x:
        return "x232c_question"
    if "that shape yet" in x:
        return "base_fixed_reply"
    if "didn't understand that question" in x:
        return "base_question_fallback"
    if x.startswith("I don't know ") and x.endswith("."):
        return "table_abstain_wording"
    return "answer_change"


def classify(key: str, mv: dict) -> tuple[list, str, list]:
    turns = [(i, o, x) for i, (o, x) in
             enumerate(zip(mv["own_replies"], mv["n_replies"])) if o != x]
    flips = [i for i, o, x in turns if _abst(x) and not _abst(o)]
    cats = sorted({turn_cat(o, x) for _, o, x in turns})
    if not turns:
        cats = ["writes_only"]
    if key in MANUAL:
        c, why = MANUAL[key]
        return sorted(set(cats) | {c}), why, flips
    why = "; ".join(CAT.get(c, c) for c in cats)
    if mv["n_equals_m"]:
        why = "138n == 138m on this case. " + why
    return cats, why, flips


def main(argv: list[str]) -> int:
    pilot, raw, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    d = pilot / "l1"
    m1: dict = {}
    counts: dict = {}
    for piece in L1.PIECES:
        own = {r["id"]: r for r in L1._load(d / f"{piece}-own.json")}
        n = {r["id"]: r for r in L1._load(d / f"{piece}-n.json")}
        m = {r["id"]: r for r in L1._load(d / f"{piece}-m.json")}
        for cid, orow in own.items():
            nrow = n[cid]
            if L1.rec(orow) == L1.rec(nrow):
                continue
            mv = {"own_replies": orow["replies"], "n_replies": nrow["replies"],
                  "n_equals_m": L1.rec(nrow) == L1.rec(m[cid]),
                  "active_same": orow["active"] == nrow["active"],
                  "all_same": orow["all"] == nrow["all"]}
            cats, why, flips = classify(f"{piece}/{cid}", mv)
            m1.setdefault(piece, {})[cid] = {
                "categories": cats, "reason": why,
                "abstain_flip_turns": flips,
                "n_equals_m": mv["n_equals_m"],
                "writes_differ_from_own": not (mv["active_same"]
                                               and mv["all_same"]),
                "expect_n": L1.rec(nrow)}
            for cat in cats:
                counts.setdefault(piece, {}).setdefault(cat, 0)
                counts[piece][cat] += 1
    r = json.loads(raw.read_text(encoding="utf-8"))
    m2 = r["m2"]
    m2["allowed_bad"] = {
        "rt136": {i: "inherited 222 exception: identical to 138m's saved "
                     "row (138m's own M2 allowed it); labels are vs 138j"
                  for i in sorted({mv["id"] for mv in m2["rt136"]
                                   if mv["class"] in ("new WRONG",
                                                      "new WRONG-WRITE",
                                                      "new junk write",
                                                      "lost OK")})},
        "rt143": {"S5": "true taught fact given back (spouse was taught in "
                        "the case); suite gold is abstain because it is a "
                        "2-cycle loop test. 221's own RESULTS flags the same "
                        "case. Reply only, no write."}}
    m2["reasons"] = {
        "rt136/C115": "t229_nosave (reply only, no write)",
        "rt136/C076": "reply-only vs 138j label; identical to 138m's saved "
                      "row (the direct 138m comparison moves only C115)",
        "rt136/C079": "as C076",
        "sessions152/S1-family10#19": "fixed: table reader answers the "
                                      "stored spouse",
        "rt143_nogate": "18 reply-only moves: K/L/O/Q7 abstain wording from "
                        "the table reader; P1 P2 Q1 Q2 MISSED->OK; S5 see "
                        "allowed_bad",
    }
    m6 = r["m6"]
    m6["reasons"] = {
        "p3-dialogs:d00:t04": "t237 table read of 'where does X live' (city)",
        "p3-dialogs:d01:t03": "abstain wording change (abstain -> abstain); "
                              "the table reader answers the boss hop",
        "p3-dialogs:d05:t03": "table USER template + G3 capital",
        "v138m-probes-dialogs:d59:t00": "abstain -> name-aware abstain "
                                        "(table reader / 236); no write",
        "v138m-probes-dialogs:d61:t01": "question reader (221c wrapper + "
                                        "table) answers a stored boss; "
                                        "fallback -> answer; no write",
    }
    pred = {"m1": m1, "m1_counts": counts, "m2": m2, "m6": m6,
            "category_text": CAT,
            "note": "Built from the last pilot before the seal; every move "
                    "by id with its exact expected record."}
    out.write_text(json.dumps(pred, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(json.dumps(counts, indent=1))
    print("answer_change:", [f"{p}/{c}" for p, v in m1.items()
                             for c, x in v.items()
                             if "answer_change" in x["categories"]])
    print("abstain flips:", [(f"{p}/{c}", x["abstain_flip_turns"])
                             for p, v in m1.items() for c, x in v.items()
                             if x["abstain_flip_turns"]])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
