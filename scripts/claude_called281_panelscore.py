#!/usr/bin/env python3
"""Exp 281 post-seal blind-panel scorer (NEW file; sealed files unchanged).

Joins the writer's per-turn panel rows
{dialog_id, turn_index, user_text, category, gold} with both arms' run rows
{dialog_id, turn_index, reply, ev, triples} from
scripts/claude_called281_panelrun.py. Mechanical counts only, per the
brief's marks; ids of misses listed, item text and gold values never
printed.

  panelscore <panel.jsonl> <run260.json> <run281.json> <out.json>

Categories (the panel's own labels):
  teach_setup      gold = "Subject|relation|Object" triple; RIGHT = the
                   triple is in triples-after. M3: triples + ev identical
                   281 vs 260 on every teach turn.
  stored_called    gold = exact expected value; RIGHT = an answer
                   containing gold; WRONG = an answer without gold;
                   ABSTAIN = clarify/dontknow. Bar: >= 90% RIGHT, 0 WRONG.
  nostore_called   gold = "abstain"; RIGHT = abstain; WRONG = any answer
                   (a guess). Bar: all abstain.
  ambiguous_called gold = "abstain"; reported: abstain counts per arm +
                   same-as-260 reply counts. Bar: 0 moves vs 260.
  control_plain    gold = exact expected value; reported: RIGHT counts per
                   arm + same-as-260 counts. Bar: 0 moves vs 260.
M3: per-turn triples equal 281 vs 260 on all 60 turns (0 diffs);
question-turn ev == 0 on 281 (0 question writes).
Report-only: replies matching "I don't know X's R called/named." per arm.
"""

import json
import re
import sys

DONTKNOW = ("don't know", "do not know", "never told me",
            "never taught me", "no record", "not someone i can look up")
CLARIFY = ("could you say it another way", "didn't understand",
           "don't understand", "was that a question",
           "i only know current facts")


def low(s):
    return " ".join(str(s).lower().split())


def is_abstain(reply):
    r = low(reply)
    return any(m in r for m in DONTKNOW) or any(m in r for m in CLARIFY)


BROKEN281 = re.compile(r"don'?t know .*\b(called|named)\s*[.?!]?\s*$",
                       re.IGNORECASE)


def main(argv):
    panelp, r260p, r281p, outp = argv[1:5]
    panel = [json.loads(x) for x in open(panelp).read().splitlines()
             if x.strip()]
    r60 = {(r["dialog_id"], r["turn_index"]): r
           for r in json.load(open(r260p))}
    r81 = {(r["dialog_id"], r["turn_index"]): r
           for r in json.load(open(r281p))}
    if len(panel) != 60:
        print(f"WARNING: panel turns {len(panel)} != 60")
    rows = []
    for it in panel:
        key = (it["dialog_id"], it["turn_index"])
        a, b = r60[key], r81[key]
        cat, gold = it["category"], it["gold"]
        arep, brep = a["reply"], b["reply"]
        row = {"id": f"{key[0]}#{key[1]}", "cat": cat,
               "same_reply": arep == brep,
               "store_same": a["triples"] == b["triples"],
               "ev60": a["ev"], "ev81": b["ev"],
               "abstain60": is_abstain(arep),
               "abstain81": is_abstain(brep),
               "broken81": bool(BROKEN281.search(brep or "")),
               "broken60": bool(BROKEN281.search(arep or ""))}
        if cat == "teach_setup":
            subj, rel, obj = gold.split("|")
            row["teach_ok81"] = [subj, rel, obj] in b["triples"]
            row["teach_ok60"] = [subj, rel, obj] in a["triples"]
            row["ev_same"] = a["ev"] == b["ev"]
        elif cat in ("stored_called", "control_plain"):
            row["gold_in81"] = (gold in brep) if gold else False
            row["gold_in60"] = (gold in arep) if gold else False
            for arm in ("60", "81"):
                if row[f"abstain{arm}"]:
                    row[f"v{arm}"] = "abstain"
                elif row[f"gold_in{arm}"]:
                    row[f"v{arm}"] = "right"
                else:
                    row[f"v{arm}"] = "wrong"
        else:  # nostore_called, ambiguous_called: gold must be abstain
            assert gold == "abstain", f"{key} gold {gold!r} != abstain"
            for arm in ("60", "81"):
                row[f"v{arm}"] = ("right" if row[f"abstain{arm}"]
                                  else "wrong-guess")
        rows.append(row)

    def fam(c):
        return [r for r in rows if r["cat"] == c]

    stored = fam("stored_called")
    nstore = fam("nostore_called")
    amb = fam("ambiguous_called")
    ctl = fam("control_plain")
    teach = fam("teach_setup")
    qturns = stored + nstore + amb + ctl
    res = {
        "n": len(rows),
        "stored": {"n": len(stored),
                   "right81": sum(1 for r in stored if r["v81"] == "right"),
                   "wrong81": sum(1 for r in stored if r["v81"] == "wrong"),
                   "abstain81": sum(1 for r in stored if r["v81"] == "abstain"),
                   "right60": sum(1 for r in stored if r["v60"] == "right"),
                   "wrong60": sum(1 for r in stored if r["v60"] == "wrong"),
                   "wrong_ids81": [r["id"] for r in stored if r["v81"] == "wrong"],
                   "miss_ids81": [r["id"] for r in stored if r["v81"] != "right"]},
        "notstored": {"n": len(nstore),
                      "right81": sum(1 for r in nstore if r["v81"] == "right"),
                      "right60": sum(1 for r in nstore if r["v60"] == "right"),
                      "guesses81": [r["id"] for r in nstore if r["v81"] != "right"],
                      "guesses60": [r["id"] for r in nstore if r["v60"] != "right"]},
        "ambiguous": {"n": len(amb),
                      "abstain81": sum(1 for r in amb if r["v81"] == "right"),
                      "abstain60": sum(1 for r in amb if r["v60"] == "right"),
                      "same": sum(1 for r in amb if r["same_reply"]),
                      "moved_ids": [r["id"] for r in amb if not r["same_reply"]]},
        "control": {"n": len(ctl),
                    "right81": sum(1 for r in ctl if r["v81"] == "right"),
                    "right60": sum(1 for r in ctl if r["v60"] == "right"),
                    "same": sum(1 for r in ctl if r["same_reply"]),
                    "moved_ids": [r["id"] for r in ctl if not r["same_reply"]]},
        "teach": {"n": len(teach),
                  "ok81": sum(1 for r in teach if r["teach_ok81"]),
                  "ok60": sum(1 for r in teach if r["teach_ok60"]),
                  "store_same": sum(1 for r in teach if r["store_same"]),
                  "ev_same": sum(1 for r in teach if r["ev_same"]),
                  "miss_ids81": [r["id"] for r in teach if not r["teach_ok81"]]},
        "qwrite81": [r["id"] for r in qturns if r["ev81"]],
        "qwrite60": [r["id"] for r in qturns if r["ev60"]],
        "store_diffs": [r["id"] for r in rows if not r["store_same"]],
        "broken81": [r["id"] for r in rows if r["broken81"]],
        "broken60": [r["id"] for r in rows if r["broken60"]],
    }
    json.dump(res, open(outp, "w"), indent=1)
    s = res["stored"]
    print(f"stored {s['right81']}/{s['n']} right81 wrong81={s['wrong81']} "
          f"abstain81={s['abstain81']} (260 right={s['right60']} "
          f"wrong={s['wrong60']}) miss={s['miss_ids81']} wrong={s['wrong_ids81']}")
    n = res["notstored"]
    print(f"notstored abstain81 {n['right81']}/{n['n']} (260 {n['right60']}) "
          f"guesses81={n['guesses81']} guesses60={n['guesses60']}")
    a = res["ambiguous"]
    print(f"ambiguous abstain81={a['abstain81']} abstain60={a['abstain60']} "
          f"same={a['same']}/{a['n']} moved={a['moved_ids']}")
    c = res["control"]
    print(f"control right81={c['right81']} right60={c['right60']} "
          f"same={c['same']}/{c['n']} moved={c['moved_ids']}")
    t = res["teach"]
    print(f"teach ok81={t['ok81']}/{t['n']} ok60={t['ok60']} "
          f"store_same={t['store_same']} ev_same={t['ev_same']} miss={t['miss_ids81']}")
    print(f"question writes 81={res['qwrite81']} 60={res['qwrite60']}")
    print(f"store diffs 281vs260: {res['store_diffs']}")
    print(f"broken abstains 81={res['broken81']} 60={res['broken60']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
