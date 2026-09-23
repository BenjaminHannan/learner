#!/usr/bin/env python3
"""Exp 280p joinpanel scorer: mechanical ownership for EVERY turn.

Mechanical rule (registered for 280p, director 2026-09-23 13:28 UTC):
  owner = the single piece arm (280b, 281 or 282b) whose reply, writes
  or store differ from 260's, else 260. Two or more differing pieces
  on one turn = overlap = FAIL.

  panel <panel> <run260> <run280b> <run281> <run282b> <run280m>
        <probes260> <probes280b> <probes281> <probes282b> <probes280m> <out>
    Schema gate first: every row must hold dialog_id, turn_index,
    user_text, category, gold, with category in
    {ability, called, teach, smalltalk, mixed, control}. The text key
    `user` is also accepted as an alias for user_text. A missing file,
    field, family or label prints SCHEMA-MISMATCH and exits 3 (VOID,
    not FAIL). Empty turn text refuses with exit 4.
    Bars: 280m reply, write count and store byte-identical to the
    mechanical owner on every turn (100%); 0 overlaps; 0 writes on
    question and smalltalk turns on 280m. Report only: absolute rates
    per category, 260 beside 280m; old-sheet scan hits over every 280m
    reply (director checks claims; reply files are listed for the
    claim check). Prints ids of misses, never item text.
  st234 <panel> <run260> <run280m> <probes260> <probes280m> <out>
    smalltalkpanel234: wellbeing (expect small_talk) fitting hits 280m >=
    260; every other item 280m == 260; 0 writes and identical stores.
"""

import json
import sys

sys.path.insert(0, "scripts")
import claude_fix280_capab as F280  # noqa: E402 (read-only old-sheet scan)

PANEL_CATS280P = ("ability", "called", "teach", "smalltalk", "mixed",
                  "control")
PIECE_ARMS = ("280b", "281", "282b")


def low(s):
    return " ".join(str(s).lower().split())


def is_question(turn):
    return str(turn).rstrip().endswith("?")


# --- schema gate ---

def _panel_rows(path):
    import claude_join280m_run as R280M
    items = R280M._panel_items(path)
    if not items:
        print("SCHEMA-MISMATCH: empty panel")
        raise SystemExit(3)
    for n, it in enumerate(items):
        if not isinstance(it, dict):
            print(f"SCHEMA-MISMATCH: row {n} is not an object")
            raise SystemExit(3)
        for key in ("dialog_id", "turn_index", "category", "gold"):
            if key not in it:
                print(f"SCHEMA-MISMATCH: row {n} missing key {key!r}")
                raise SystemExit(3)
        if "user_text" not in it and "user" not in it:
            print(f"SCHEMA-MISMATCH: row {n} missing text key")
            raise SystemExit(3)
        text = it.get("user_text", it.get("user"))
        if text is None or str(text).strip() == "":
            print(f"EMPTY-TURN: row {n} has empty turn text; "
                  "refusing to score")
            raise SystemExit(4)
        if it["category"] not in PANEL_CATS280P:
            print(f"SCHEMA-MISMATCH: row {n} unexpected category "
                  f"{it['category']!r}")
            raise SystemExit(3)
    return items


def _differs(a, b):
    """True if reply, writes or store differ between two run rows."""
    return (a.get("reply") != b.get("reply")
            or a.get("ev") != b.get("ev")
            or a.get("triples") != b.get("triples"))


def mech_owner(r260, r280b, r281, r282b):
    """Return (owner, overlap). Owner in {260,280b,281,282b} or OVERLAP."""
    diffs = []
    if _differs(r280b, r260):
        diffs.append("280b")
    if _differs(r281, r260):
        diffs.append("281")
    if _differs(r282b, r260):
        diffs.append("282b")
    if len(diffs) == 0:
        return "260", False
    if len(diffs) == 1:
        return diffs[0], False
    return "OVERLAP", True


CAN_LINE = "say i do not know instead of guessing"


def panel_main(args):
    (panelp, r260p, r280bp, r281p, r282bp, r280mp, _p260, _p280b, _p281,
     _p282b, _p280m, outp) = args[:12]
    import claude_join280m_run as R280M
    _panel_rows(panelp)
    dialogs = R280M.load_panel_dialogs(panelp)
    runs = {}
    for tag, p in (("260", r260p), ("280b", r280bp), ("281", r281p),
                   ("282b", r282bp), ("280m", r280mp)):
        runs[tag] = {r["id"]: r for r in json.load(open(p))}
    rows = []
    for dg in dialogs:
        try:
            arms = {t: runs[t][dg["id"]] for t in runs}
        except KeyError as e:
            print(f"SCORE-ERROR: dialog {e} missing from a run file")
            raise SystemExit(2)
        n = len(arms["280m"]["rows"])
        for i in range(n):
            r260 = arms["260"]["rows"][i]
            r280b = arms["280b"]["rows"][i]
            r281 = arms["281"]["rows"][i]
            r282b = arms["282b"]["rows"][i]
            r280m = arms["280m"]["rows"][i]
            cat = dg["cats"][i] if i < len(dg.get("cats", [])) else "?"
            owner, overlap = mech_owner(r260, r280b, r281, r282b)
            if overlap:
                agree = False
                same_reply = same_ev = same_store = False
            else:
                ro = arms[owner]["rows"][i]
                same_reply = r280m["reply"] == ro["reply"]
                same_ev = r280m.get("ev") == ro.get("ev")
                same_store = r280m.get("triples") == ro.get("triples")
                agree = same_reply and same_ev and same_store
            rows.append({
                "id": dg["id"], "turn_idx": i, "cat": cat,
                "owner": owner, "overlap": overlap,
                "same_reply": same_reply if not overlap else False,
                "same_ev": same_ev if not overlap else False,
                "same_store": same_store if not overlap else False,
                "agree": agree,
                "can280": CAN_LINE in low(r280m["reply"]),
                "can260": CAN_LINE in low(r260["reply"]),
                "oldhit": any(s in low(r280m["reply"])
                              for s in F280.OLD_SIG280),
                "writes280m": r280m.get("ev", 0),
                "is_question": is_question(r260.get("turn", "")),
                "store_diff_260": (r280m.get("triples")
                                   != r260.get("triples")),
                "ev_diff_260": r280m.get("ev") != r260.get("ev"),
            })
    by_cat = {}
    for r in rows:
        d = by_cat.setdefault(r["cat"], {"n": 0, "agree": 0, "can280m": 0,
                                         "can260": 0})
        d["n"] += 1
        d["agree"] += r["agree"]
        d["can280m"] += r["can280"]
        d["can260"] += r["can260"]
    own_counts = {}
    for r in rows:
        own_counts.setdefault(r["owner"], 0)
        own_counts[r["owner"]] += 1
    n_all = len(rows)
    n_agree = sum(1 for r in rows if r["agree"])
    overlaps = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["overlap"]]
    moved = [f"{r['id']}#{r['turn_idx']}({r['cat']}->{r['owner']})"
             for r in rows if not r["agree"]]
    qwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows
               if r["is_question"] and r["writes280m"]]
    stwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows
                if r["cat"] == "smalltalk" and r["writes280m"]]
    storediffs = [f"{r['id']}#{r['turn_idx']}" for r in rows
                  if r["store_diff_260"]]
    oldhits = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["oldhit"]]
    ok = (n_agree == n_all and not qwrites and not stwrites
          and not overlaps)
    res = {"n_dialogs": len(dialogs), "n_turns": n_all,
           "by_cat": by_cat,
           "agree": {"n": n_agree, "denom": n_all,
                     "moved_ids": moved},
           "overlaps": overlaps, "qwrite280m": qwrites,
           "smalltalk_writes280m": stwrites,
           "store_diffs_280m_vs_260": storediffs,
           "old_sheet_hits_280m": oldhits,
           "mech_owners": own_counts}
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"dialogs={len(dialogs)} turns={n_all} agree={n_agree}/{n_all}")
    print(f"by_cat={json.dumps(by_cat)} mech_owners={own_counts}")
    print(f"moved={moved}")
    print(f"overlaps={overlaps}")
    print(f"280m question writes={qwrites}; smalltalk writes={stwrites}; "
          f"store diffs vs 260={storediffs}")
    print(f"old-sheet hits on 280m={oldhits} (director claim check)")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


# --- st234 scoring (260 vs 280m), identical rule to 280m scorer ---

def st234_main(args):
    panelp, r260p, r280mp, p260p, p280mp, outp = args[:6]
    items = [json.loads(x) for x in open(panelp).read().strip().split("\n")
             if x.strip()]
    r60 = {r["id"]: r for r in json.load(open(r260p))}
    r80m = {r["id"]: r for r in json.load(open(r280mp))}
    probes260 = json.load(open(p260p))
    probes280m = json.load(open(p280mp))

    def fitset(probes):
        out = set()
        for p in ("Hello.", "Thanks!", "Bye.", "how are you"):
            r = (probes.get(p) or {}).get("reply", "")
            out.add(r)
            out.add("Hi! " + r)
        return out
    fit60, fit80m = fitset(probes260), fitset(probes280m)
    rows = []
    for it in items:
        a = r60[it["id"]]
        b = r80m[it["id"]]
        pos = (it.get("expect") == "small_talk")
        rows.append({
            "id": it["id"], "family": it.get("family"),
            "expect": it.get("expect"), "positive": pos,
            "hit60": a["turn_reply"] in fit60,
            "hit80m": b["turn_reply"] in fit80m,
            "same_reply": a["turn_reply"] == b["turn_reply"],
            "setup_same": a["setup_replies"] == b["setup_replies"],
            "nb_same": (a["stored_after_setup"] == b["stored_after_setup"]
                        and a["stored_after_turn"] == b["stored_after_turn"]),
            "writes80m": b["writes_turn"],
            "writes60": a["writes_turn"],
        })
    fams = {}
    for r in rows:
        f = fams.setdefault(r["family"], {"n": 0, "hit60": 0, "hit80m": 0,
                                          "same": 0})
        f["n"] += 1
        f["hit60"] += r["hit60"]
        f["hit80m"] += r["hit80m"]
        f["same"] += r["same_reply"]
    wb = [r for r in rows if r["positive"]]
    other = [r for r in rows if not r["positive"]]
    res = {
        "n": len(rows),
        "families": fams,
        "wellbeing": {"n": len(wb),
                      "hit60": sum(1 for r in wb if r["hit60"]),
                      "hit80m": sum(1 for r in wb if r["hit80m"]),
                      "miss80m": [r["id"] for r in wb if not r["hit80m"]]},
        "other": {"n": len(other),
                  "same": sum(1 for r in other if r["same_reply"]),
                  "moved_ids": [r["id"] for r in other
                                if not r["same_reply"]]},
        "writes80m": [r["id"] for r in rows if r["writes80m"]],
        "store_diffs": [r["id"] for r in rows if not r["nb_same"]],
        "setup_diffs": [r["id"] for r in rows if not r["setup_same"]],
    }
    ok = (res["wellbeing"]["hit80m"] >= res["wellbeing"]["hit60"]
          and res["other"]["same"] == len(other)
          and not res["writes80m"] and not res["store_diffs"]
          and not res["setup_diffs"])
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"n={len(rows)} wellbeing 260 {res['wellbeing']['hit60']}/"
          f"{len(wb)} 280m {res['wellbeing']['hit80m']}/{len(wb)} "
          f"miss80m {res['wellbeing']['miss80m']}")
    print(f"other same {res['other']['same']}/{len(other)} "
          f"moved {res['other']['moved_ids']}")
    print(f"families {json.dumps(fams)}")
    print(f"280m writes {res['writes80m']}; store diffs {res['store_diffs']}; "
          f"setup diffs {res['setup_diffs']}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


def main(argv):
    mode = argv[1]
    if mode == "panel":
        return panel_main(argv[2:])
    if mode == "st234":
        return st234_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
