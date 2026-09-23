#!/usr/bin/env python3
"""Exp 281b blind-panel scorer (mechanical counts only, per-category).

Joins the writer's per-turn panel rows
{dialog_id, turn_index, user_text|user, category, gold} with both arms'
run rows {dialog_id, turn_index, reply, ev, triples} from
scripts/claude_called281b_panelrun.py. Counts only; ids of misses listed,
item text and gold values never printed.

  panelscore <panel.jsonl> <run281.json> <run281b.json> <out.json>

Schema gate: missing file/field/category, a non-triple teach gold, or a
panel row with no arm row prints SCHEMA-MISMATCH and exits 3 (VOID).

Categories (the panel's own labels):
  teach_setup      gold = "Subject|relation|Object" triple; teach-fail on
                   an arm = the triple is NOT in triples-after. Reported
                   per arm (the 281-arm count is the teach-fail count the
                   note requires). VOID bar: at most 2 teach turns fail on
                   the 260 arm (read via the 281 arm: 281 is sealed to keep
                   teaches byte-identical to 260, and 281b provably takes
                   the no-op path on plain teaches; teach stores 281 vs
                   281b are also asserted identical turn by turn).
  stored_called    gold = exact expected value; RIGHT = an answer
                   containing gold; WRONG = an answer without gold;
                   ABSTAIN = clarify/dontknow. M1 denominator: only rows
                   whose dialog's teach triple is stored on the 281 arm
                   (the note's "teach turn the 260 arm stores", via the
                   equivalence above). Bar: >= 90% RIGHT, 0 WRONG.
  nostore_called   gold = "abstain"; RIGHT = abstain; WRONG = any answer
                   (a guess). Bar: all abstain (100%).
  ambiguous_called gold = "abstain"; reported: abstain counts per arm +
                   same-as-281 reply counts. Bar: 0 moves vs 281.
  control_plain    gold = exact expected value; reported: RIGHT counts per
                   arm + same-as-281 counts. Bar: 0 moves vs 281.
M3: per-turn triples equal 281 vs 281b on all turns (0 diffs);
question-turn ev == 0 on 281b (0 question writes; teaches may write).
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


BROKEN281B = re.compile(r"don'?t know .*\b(called|named)\s*[.?!]?\s*$",
                        re.IGNORECASE)

CATS281B = ("teach_setup", "stored_called", "nostore_called",
            "ambiguous_called", "control_plain")


def main(argv):
    panelp, r281p, r281bp, outp = argv[1:5]
    try:
        panel = [json.loads(x) for x in open(panelp).read().splitlines()
                 if x.strip()]
    except FileNotFoundError:
        print(f"SCHEMA-MISMATCH: panel file not found: {panelp}")
        return 3
    try:
        rows281 = json.load(open(r281p))
        rows281b = json.load(open(r281bp))
    except FileNotFoundError as e:
        print(f"SCHEMA-MISMATCH: run file not found: {e}")
        return 3
    r81 = {(r["dialog_id"], r["turn_index"]): r for r in rows281}
    r8b = {(r["dialog_id"], r["turn_index"]): r for r in rows281b}
    for it in panel:
        for k in ("dialog_id", "turn_index", "category", "gold"):
            if k not in it:
                print(f"SCHEMA-MISMATCH: panel row missing {k!r}")
                return 3
        if ("user_text" not in it) and ("user" not in it):
            print("SCHEMA-MISMATCH: panel row has neither user_text nor user")
            return 3
        if it["category"] not in CATS281B:
            print(f"SCHEMA-MISMATCH: unexpected category {it['category']!r}")
            return 3
    rows = []
    for it in panel:
        key = (it["dialog_id"], it["turn_index"])
        if key not in r81 or key not in r8b:
            print(f"SCHEMA-MISMATCH: no arm row for {key[0]}#{key[1]}")
            return 3
        a, b = r81[key], r8b[key]
        cat, gold = it["category"], it["gold"]
        arep, brep = a["reply"], b["reply"]
        row = {"id": f"{key[0]}#{key[1]}", "cat": cat,
               "same_reply": arep == brep,
               "store_same": a["triples"] == b["triples"],
               "ev81": a["ev"], "ev8b": b["ev"],
               "triples81": a["triples"], "triples8b": b["triples"],
               "abstain81": is_abstain(arep),
               "abstain8b": is_abstain(brep),
               "broken8b": bool(BROKEN281B.search(brep or "")),
               "broken81": bool(BROKEN281B.search(arep or ""))}
        if cat == "teach_setup":
            if not isinstance(gold, str) or gold.count("|") != 2:
                print(f"SCHEMA-MISMATCH: teach gold not S|R|O at {row['id']}")
                return 3
            subj, rel, obj = gold.split("|")
            row["gold_trip"] = [subj, rel, obj]
            row["teach_ok81"] = [subj, rel, obj] in a["triples"]
            row["teach_ok8b"] = [subj, rel, obj] in b["triples"]
        elif cat in ("stored_called", "control_plain"):
            if not isinstance(gold, str) or not gold or gold == "abstain":
                print(f"SCHEMA-MISMATCH: bad gold at {row['id']}")
                return 3
            row["gold_in8b"] = gold in brep
            row["gold_in81"] = gold in arep
            for arm in ("81", "8b"):
                if row[f"abstain{arm}"]:
                    row[f"v{arm}"] = "abstain"
                elif row[f"gold_in{arm}"]:
                    row[f"v{arm}"] = "right"
                else:
                    row[f"v{arm}"] = "wrong"
        else:  # nostore_called, ambiguous_called: gold must be abstain
            if gold != "abstain":
                print(f"SCHEMA-MISMATCH: {row['id']} gold {gold!r} != abstain")
                return 3
            for arm in ("81", "8b"):
                row[f"v{arm}"] = ("right" if row[f"abstain{arm}"]
                                  else "wrong-guess")
        rows.append(row)

    def fam(c):
        return [r for r in rows if r["cat"] == c]

    teach = fam("teach_setup")
    stored = fam("stored_called")
    nstore = fam("nostore_called")
    amb = fam("ambiguous_called")
    ctl = fam("control_plain")

    # M1 denominator: stored rows whose dialog's teach triple (matching
    # the gold value) is stored on the 281 arm at question time.
    teach_by_dialog = {}
    for r in teach:
        teach_by_dialog.setdefault(r["id"].split("#")[0], []).append(r)
    denom, denom_excluded = [], []
    for r in stored:
        did = r["id"].split("#")[0]
        cands = teach_by_dialog.get(did, [])
        g = [x for x in panel if x["dialog_id"] == did
             and x["category"] == "stored_called"
             and f"{did}#{x['turn_index']}" == r["id"]]
        gold = g[0]["gold"] if g else None
        ok = False
        for t in cands:
            if t["gold_trip"][2] == gold and t["gold_trip"] in r["triples81"]:
                ok = True
        if not cands:
            ok = any(t[2] == gold for t in r["triples81"])
        (denom if ok else denom_excluded).append(r["id"])
    denom_set = set(denom)
    dstored = [r for r in stored if r["id"] in denom_set]

    qturns = stored + nstore + amb + ctl
    res = {
        "n": len(rows),
        "teach": {"n": len(teach),
                  "ok81": sum(1 for r in teach if r["teach_ok81"]),
                  "ok8b": sum(1 for r in teach if r["teach_ok8b"]),
                  "fail81": [r["id"] for r in teach if not r["teach_ok81"]],
                  "fail8b": [r["id"] for r in teach if not r["teach_ok8b"]],
                  "store_same": sum(1 for r in teach if r["store_same"]),
                  "store_diffs": [r["id"] for r in teach
                                  if not r["store_same"]]},
        "stored": {"n": len(stored),
                   "denom_n": len(dstored),
                   "denom_excluded": denom_excluded,
                   "right8b": sum(1 for r in dstored if r["v8b"] == "right"),
                   "wrong8b": sum(1 for r in dstored if r["v8b"] == "wrong"),
                   "abstain8b": sum(1 for r in dstored
                                    if r["v8b"] == "abstain"),
                   "right81": sum(1 for r in dstored if r["v81"] == "right"),
                   "wrong_ids8b": [r["id"] for r in dstored
                                   if r["v8b"] == "wrong"],
                   "miss_ids8b": [r["id"] for r in dstored
                                  if r["v8b"] != "right"],
                   "all_right8b": sum(1 for r in stored
                                      if r["v8b"] == "right")},
        "notstored": {"n": len(nstore),
                      "right8b": sum(1 for r in nstore if r["v8b"] == "right"),
                      "right81": sum(1 for r in nstore if r["v81"] == "right"),
                      "guesses8b": [r["id"] for r in nstore
                                    if r["v8b"] != "right"],
                      "guesses81": [r["id"] for r in nstore
                                    if r["v81"] != "right"]},
        "ambiguous": {"n": len(amb),
                      "abstain8b": sum(1 for r in amb if r["v8b"] == "right"),
                      "abstain81": sum(1 for r in amb if r["v81"] == "right"),
                      "same": sum(1 for r in amb if r["same_reply"]),
                      "moved_ids": [r["id"] for r in amb
                                    if not r["same_reply"]]},
        "control": {"n": len(ctl),
                    "right8b": sum(1 for r in ctl if r["v8b"] == "right"),
                    "right81": sum(1 for r in ctl if r["v81"] == "right"),
                    "same": sum(1 for r in ctl if r["same_reply"]),
                    "moved_ids": [r["id"] for r in ctl
                                  if not r["same_reply"]]},
        "qwrite8b": [r["id"] for r in qturns if r["ev8b"]],
        "qwrite81": [r["id"] for r in qturns if r["ev81"]],
        "store_diffs": [r["id"] for r in rows if not r["store_same"]],
        "broken8b": [r["id"] for r in rows if r["broken8b"]],
        "broken81": [r["id"] for r in rows if r["broken81"]],
    }
    json.dump(res, open(outp, "w"), indent=1)
    t = res["teach"]
    print(f"teach ok81={t['ok81']}/{t['n']} ok8b={t['ok8b']} "
          f"store_same={t['store_same']} fail81={t['fail81']} "
          f"fail8b={t['fail8b']} teach_store_diffs={t['store_diffs']}")
    s = res["stored"]
    print(f"stored denom={s['denom_n']}/{s['n']} excluded={s['denom_excluded']}")
    print(f"stored(denom): 8b right {s['right8b']}/{s['denom_n']} "
          f"wrong={s['wrong8b']} abstain={s['abstain8b']} "
          f"(281 right={s['right81']}) miss={s['miss_ids8b']} "
          f"wrong={s['wrong_ids8b']} all_n_right8b={s['all_right8b']}")
    n = res["notstored"]
    print(f"notstored abstain8b {n['right8b']}/{n['n']} (281 {n['right81']}) "
          f"guesses8b={n['guesses8b']} guesses81={n['guesses81']}")
    a = res["ambiguous"]
    print(f"ambiguous abstain8b={a['abstain8b']} abstain81={a['abstain81']} "
          f"same={a['same']}/{a['n']} moved={a['moved_ids']}")
    c = res["control"]
    print(f"control right8b={c['right8b']} right81={c['right81']} "
          f"same={c['same']}/{c['n']} moved={c['moved_ids']}")
    print(f"question writes 8b={res['qwrite8b']} 81={res['qwrite81']}")
    print(f"store diffs 281bvs281: {res['store_diffs']}")
    print(f"broken abstains 8b={res['broken8b']} 81={res['broken81']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
