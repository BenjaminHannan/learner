#!/usr/bin/env python3
"""Exp 292t joinpanel scorer: mechanical ownership for EVERY turn.

Mechanical rule (registered for 292t): the owner is the single
single-layer arm (292+280b, 292+281 or 292+282b) whose reply, writes or
store differ from 292's, or 292 if none does. Two or more differing pieces
on one turn = overlap = FAIL.

  panel <panel> <run292> <run280b> <run281> <run282b> <run292t>
        <probes292> <probes280b> <probes281> <probes282b> <probes292t> <out>
    Schema gate first: every row must hold dialog_id, turn_index,
    user_text, category, gold, with category in
    {ability, called, teach, smalltalk, mixed, control}. The text key
    `user` is also accepted as an alias for user_text. A missing file,
    field, family or label prints SCHEMA-MISMATCH and exits 3 (VOID,
    not FAIL). Empty turn text refuses with exit 4.
    Bars: 292t reply, write count and store byte-identical to the
    mechanical owner on every turn (100%); 0 overlaps; 0 writes on
    question and smalltalk turns on 292t. Report only: absolute rates
    per category, 292 beside 292t; old-sheet scan hits over every 292t
    reply (director checks claims; reply files are listed for the
    claim check). Prints ids of misses, never item text.
  st234 <panel> <run292> <run292t> <probes292> <probes292t> <out>
    smalltalkpanel234: wellbeing (expect small_talk) fitting hits 292t >=
    292; every other item 292t == 292; 0 writes and identical stores.
  dev <run292> <run280b> <run281> <run282b> <run292t> <out>
    Builder pilot on own dev cases: same mechanical rule per turn;
    reports agreement of 292t with the owner, overlaps, and per-layer
    fire counts. No bars (pilot only).
"""

import json
import sys

sys.path.insert(0, "scripts")
import claude_fix280_capab as F280  # noqa: E402 (read-only old-sheet scan)

PANEL_CATS292T = ("ability", "called", "teach", "smalltalk", "mixed",
                  "control")
PIECE_ARMS = ("280b", "281", "282b")


def low(s):
    return " ".join(str(s).lower().split())


def is_question(turn):
    return str(turn).rstrip().endswith("?")


# --- schema gate ---

def _panel_rows(path):
    import claude_join292t_run as R292T
    items = R292T._panel_items(path)
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
        if it["category"] not in PANEL_CATS292T:
            print(f"SCHEMA-MISMATCH: row {n} unexpected category "
                  f"{it['category']!r}")
            raise SystemExit(3)
    return items


def _differs(a, b):
    """True if reply, writes or store differ between two run rows."""
    return (a.get("reply") != b.get("reply")
            or a.get("ev") != b.get("ev")
            or a.get("triples") != b.get("triples"))


def mech_owner(r292, r280b, r281, r282b):
    """Return (owner, overlap). Owner in {292,280b,281,282b} or OVERLAP."""
    diffs = []
    if _differs(r280b, r292):
        diffs.append("280b")
    if _differs(r281, r292):
        diffs.append("281")
    if _differs(r282b, r292):
        diffs.append("282b")
    if len(diffs) == 0:
        return "292", False
    if len(diffs) == 1:
        return diffs[0], False
    return "OVERLAP", True


CAN_LINE = "say i do not know instead of guessing"


def panel_main(args):
    (panelp, r292p, r280bp, r281p, r282bp, r292tp, _p292, _p280b, _p281,
     _p282b, _p292t, outp) = args[:12]
    import claude_join292t_run as R292T
    _panel_rows(panelp)
    dialogs = R292T.load_panel_dialogs(panelp)
    runs = {}
    for tag, p in (("292", r292p), ("280b", r280bp), ("281", r281p),
                   ("282b", r282bp), ("292t", r292tp)):
        runs[tag] = {r["id"]: r for r in json.load(open(p))}
    rows = []
    for dg in dialogs:
        try:
            arms = {t: runs[t][dg["id"]] for t in runs}
        except KeyError as e:
            print(f"SCORE-ERROR: dialog {e} missing from a run file")
            raise SystemExit(2)
        n = len(arms["292t"]["rows"])
        for i in range(n):
            r292 = arms["292"]["rows"][i]
            r280b = arms["280b"]["rows"][i]
            r281 = arms["281"]["rows"][i]
            r282b = arms["282b"]["rows"][i]
            r292t = arms["292t"]["rows"][i]
            cat = dg["cats"][i] if i < len(dg.get("cats", [])) else "?"
            owner, overlap = mech_owner(r292, r280b, r281, r282b)
            if overlap:
                agree = False
                same_reply = same_ev = same_store = False
            else:
                ro = arms[owner]["rows"][i]
                same_reply = r292t["reply"] == ro["reply"]
                same_ev = r292t.get("ev") == ro.get("ev")
                same_store = r292t.get("triples") == ro.get("triples")
                agree = same_reply and same_ev and same_store
            rows.append({
                "id": dg["id"], "turn_idx": i, "cat": cat,
                "owner": owner, "overlap": overlap,
                "same_reply": same_reply if not overlap else False,
                "same_ev": same_ev if not overlap else False,
                "same_store": same_store if not overlap else False,
                "agree": agree,
                "can292t": CAN_LINE in low(r292t["reply"]),
                "can292": CAN_LINE in low(r292["reply"]),
                "oldhit": any(s in low(r292t["reply"])
                              for s in F280.OLD_SIG280),
                "writes292t": r292t.get("ev", 0),
                "is_question": is_question(r292.get("turn", "")),
                "store_diff_292": (r292t.get("triples")
                                   != r292.get("triples")),
                "ev_diff_292": r292t.get("ev") != r292.get("ev"),
            })
    by_cat = {}
    for r in rows:
        d = by_cat.setdefault(r["cat"], {"n": 0, "agree": 0, "can292t": 0,
                                         "can292": 0})
        d["n"] += 1
        d["agree"] += r["agree"]
        d["can292t"] += r["can292t"]
        d["can292"] += r["can292"]
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
               if r["is_question"] and r["writes292t"]]
    stwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows
                if r["cat"] == "smalltalk" and r["writes292t"]]
    storediffs = [f"{r['id']}#{r['turn_idx']}" for r in rows
                  if r["store_diff_292"]]
    oldhits = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["oldhit"]]
    ok = (n_agree == n_all and not qwrites and not stwrites
          and not overlaps)
    res = {"n_dialogs": len(dialogs), "n_turns": n_all,
           "by_cat": by_cat,
           "agree": {"n": n_agree, "denom": n_all,
                     "moved_ids": moved},
           "overlaps": overlaps, "qwrite292t": qwrites,
           "smalltalk_writes292t": stwrites,
           "store_diffs_292t_vs_292": storediffs,
           "old_sheet_hits_292t": oldhits,
           "mech_owners": own_counts}
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"dialogs={len(dialogs)} turns={n_all} agree={n_agree}/{n_all}")
    print(f"by_cat={json.dumps(by_cat)} mech_owners={own_counts}")
    print(f"moved={moved}")
    print(f"overlaps={overlaps}")
    print(f"292t question writes={qwrites}; smalltalk writes={stwrites}; "
          f"store diffs vs 292={storediffs}")
    print(f"old-sheet hits on 292t={oldhits} (director claim check)")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


def dev_main(args):
    """Pilot on dev-case run files (run_dev schema: [{id, rows[]}] + cases.

    dev <run292> <run280b> <run281> <run282b> <run292t> <cases> <out>
    """
    r292p, r280bp, r281p, r282bp, r292tp, casesp, outp = args[:7]
    cases = {c["id"]: c for c in json.load(open(casesp))}
    runs = {}
    for tag, p in (("292", r292p), ("280b", r280bp), ("281", r281p),
                   ("282b", r282bp), ("292t", r292tp)):
        runs[tag] = {r["id"]: r for r in json.load(open(p))}
    rows = []
    for cid, case in cases.items():
        try:
            arms = {t: runs[t][cid] for t in runs}
        except KeyError as e:
            print(f"SCORE-ERROR: case {e} missing from a run file")
            raise SystemExit(2)
        fam = case.get("family", "?")
        n = len(arms["292t"]["rows"])
        for i in range(n):
            r292 = arms["292"]["rows"][i]
            r280b = arms["280b"]["rows"][i]
            r281 = arms["281"]["rows"][i]
            r282b = arms["282b"]["rows"][i]
            r292t = arms["292t"]["rows"][i]
            diffs = [t for t, r in (("280b", r280b), ("281", r281),
                                    ("282b", r282b)) if _differs(r, r292)]
            overlap = len(diffs) >= 2
            owner = diffs[0] if len(diffs) == 1 else (
                "OVERLAP" if overlap else "292")
            if overlap:
                agree = False
            else:
                ro = arms[owner]["rows"][i]
                agree = (r292t["reply"] == ro["reply"]
                         and r292t.get("ev") == ro.get("ev")
                         and r292t.get("triples") == ro.get("triples"))
            rows.append({"id": cid, "turn_idx": i, "fam": fam,
                         "fires": diffs, "overlap": overlap,
                         "owner": owner, "agree": agree,
                         "oldhit": any(s in low(r292t["reply"])
                                       for s in F280.OLD_SIG280),
                         "qwrite": (is_question(r292.get("turn", ""))
                                    and r292t.get("ev", 0))})
    n_all = len(rows)
    n_agree = sum(1 for r in rows if r["agree"])
    overlaps = [f"{r['id']}#{r['turn_idx']}({','.join(r['fires'])})"
                for r in rows if r["overlap"]]
    fires = {}
    for r in rows:
        for f in r["fires"]:
            fires[f] = fires.get(f, 0) + 1
    by_fam = {}
    for r in rows:
        d = by_fam.setdefault(r["fam"], {"n": 0, "agree": 0})
        d["n"] += 1
        d["agree"] += r["agree"]
    moved = [f"{r['id']}#{r['turn_idx']}({r['fam']}->{r['owner']})"
             for r in rows if not r["agree"]]
    qwrites = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["qwrite"]]
    oldhits = [f"{r['id']}#{r['turn_idx']}" for r in rows if r["oldhit"]]
    res = {"n_cases": len(cases), "n_turns": n_all,
           "agree": {"n": n_agree, "denom": n_all, "moved_ids": moved},
           "by_fam": by_fam, "fires": fires, "overlaps": overlaps,
           "qwrite292t": qwrites, "old_sheet_hits_292t": oldhits}
    res["verdict"] = ("PASS" if (n_agree == n_all and not overlaps
                                 and not qwrites) else "FAIL")
    json.dump(res, open(outp, "w"), indent=1)
    print(f"cases={len(cases)} turns={n_all} agree={n_agree}/{n_all}")
    print(f"by_fam={json.dumps(by_fam)} fires={fires}")
    print(f"moved={moved}")
    print(f"overlaps={overlaps}")
    print(f"292t question writes={qwrites}")
    print(f"old-sheet hits on 292t={oldhits} (director claim check)")
    print("VERDICT:", res["verdict"])
    return 0 if res["verdict"] == "PASS" else 1


# --- st234 scoring (292 vs 292t), identical rule to 280p scorer ---

def st234_main(args):
    panelp, r292p, r292tp, p292p, p292tp, outp = args[:6]
    items = [json.loads(x) for x in open(panelp).read().strip().split("\n")
             if x.strip()]
    r92 = {r["id"]: r for r in json.load(open(r292p))}
    r92t = {r["id"]: r for r in json.load(open(r292tp))}
    probes292 = json.load(open(p292p))
    probes292t = json.load(open(p292tp))

    def fitset(probes):
        out = set()
        for p in ("Hello.", "Thanks!", "Bye.", "how are you"):
            r = (probes.get(p) or {}).get("reply", "")
            out.add(r)
            out.add("Hi! " + r)
        return out
    fit92, fit92t = fitset(probes292), fitset(probes292t)
    rows = []
    for it in items:
        a = r92[it["id"]]
        b = r92t[it["id"]]
        pos = (it.get("expect") == "small_talk")
        rows.append({
            "id": it["id"], "family": it.get("family"),
            "expect": it.get("expect"), "positive": pos,
            "hit92": a["turn_reply"] in fit92,
            "hit92t": b["turn_reply"] in fit92t,
            "same_reply": a["turn_reply"] == b["turn_reply"],
            "setup_same": a["setup_replies"] == b["setup_replies"],
            "nb_same": (a["stored_after_setup"] == b["stored_after_setup"]
                        and a["stored_after_turn"] == b["stored_after_turn"]),
            "writes92t": b["writes_turn"],
            "writes92": a["writes_turn"],
        })
    fams = {}
    for r in rows:
        f = fams.setdefault(r["family"], {"n": 0, "hit92": 0, "hit92t": 0,
                                          "same": 0})
        f["n"] += 1
        f["hit92"] += r["hit92"]
        f["hit92t"] += r["hit92t"]
        f["same"] += r["same_reply"]
    wb = [r for r in rows if r["positive"]]
    other = [r for r in rows if not r["positive"]]
    res = {
        "n": len(rows),
        "families": fams,
        "wellbeing": {"n": len(wb),
                      "hit92": sum(1 for r in wb if r["hit92"]),
                      "hit92t": sum(1 for r in wb if r["hit92t"]),
                      "miss92t": [r["id"] for r in wb if not r["hit92t"]]},
        "other": {"n": len(other),
                  "same": sum(1 for r in other if r["same_reply"]),
                  "moved_ids": [r["id"] for r in other
                                if not r["same_reply"]]},
        "writes92t": [r["id"] for r in rows if r["writes92t"]],
        "store_diffs": [r["id"] for r in rows if not r["nb_same"]],
        "setup_diffs": [r["id"] for r in rows if not r["setup_same"]],
    }
    ok = (res["wellbeing"]["hit92t"] >= res["wellbeing"]["hit92"]
          and res["other"]["same"] == len(other)
          and not res["writes92t"] and not res["store_diffs"]
          and not res["setup_diffs"])
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"n={len(rows)} wellbeing 292 {res['wellbeing']['hit92']}/"
          f"{len(wb)} 292t {res['wellbeing']['hit92t']}/{len(wb)} "
          f"miss92t {res['wellbeing']['miss92t']}")
    print(f"other same {res['other']['same']}/{len(other)} "
          f"moved {res['other']['moved_ids']}")
    print(f"families {json.dumps(fams)}")
    print(f"292t writes {res['writes92t']}; store diffs {res['store_diffs']}; "
          f"setup diffs {res['setup_diffs']}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


def main(argv):
    mode = argv[1]
    if mode == "panel":
        return panel_main(argv[2:])
    if mode == "dev":
        return dev_main(argv[2:])
    if mode == "st234":
        return st234_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
