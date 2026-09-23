#!/usr/bin/env python3
"""Exp 282 dev scorer + blind-panel scorer + smalltalk234 scorer.

Mechanical counts only (right, wrong, abstain, writes). Truth of claims
and grammar are not graded here; every changed reply is the head's own
canonical small-talk reply, via the rewrite in
scripts/claude_fix282_small.py. Prints ids of misses, never item text.

  dev <cases.json> <run260.json> <run282.json> <probes260.json>
      <probes282.json> <out.json>
    greet/thanks_close: the 282 arm's scored-turn reply must equal its own
      arm's reply to the case's probe ("Hello." / "Thanks!" / "Bye."), with
      0 writes on that turn. 260's reply shown beside (dev info only).
    mixed/control: every 282 reply must equal 260's, with equal stores.
    expect_store checked exactly when given. Small-talk turns with writes
    fail. Never prints item text beyond ids and counts.
  panel <panel.jsonl|json> <run260.json> <run282.json> <probes260.json>
      <probes282.json> <out.json>
    Every turn of every dialog is classified by the sealed matcher
    (scripts/claude_fix282_small.classify_small282); the panel's own
    family/category label is recorded, never trusted for scoring:
      smalltalk : matcher fires. RIGHT = the reply is in the arm's own
                  fitting set (its replies to "Hello.", "Thanks!", "Bye.",
                  "how are you", with/without "Hi! " prefix) with 0 writes;
                  ABSTAIN = clarify/dontknow; else WRONG.
      other     : matcher silent. RIGHT = 282 reply == 260 reply with equal
                  write deltas and equal stores (route preserved). The mixed
                  subset (small-talk words present but silent matcher) is
                  reported separately by id.
    Prints ids of misses, never item text.
  st234 <panel.jsonl> <run260.json> <run282.json> <probes260.json>
      <probes282.json> <out.json>
    smalltalkpanel234 rerun: wellbeing (expect small_talk) fitting hits per
    arm; every other item 282 == 260; 0 writes and identical stores on 282.
"""

import json
import re
import sys

sys.path.insert(0, "scripts")
import claude_fix282_small as F282  # noqa: E402 (matcher only, sealed)


def low(s):
    return " ".join(str(s).lower().split())


DONTKNOW = ("don't know", "do not know", "never told me",
            "never taught me", "no record", "not someone i can look up")
CLARIFY = ("could you say it another way", "didn't understand",
           "don't understand", "couldn't save that", "was that a question",
           "listening mode", "waiting for your next turn",
           "i only know current facts")


def is_dontknow(reply):
    return any(m in low(reply) for m in DONTKNOW)


def is_clarify(reply):
    return any(m in low(reply) for m in CLARIFY)


def is_abstain(reply):
    return is_dontknow(reply) or is_clarify(reply)


def is_question(turn):
    return str(turn).rstrip().endswith("?")


def fitting_set(probes):
    out = set()
    for p in ("Hello.", "Thanks!", "Bye.", "how are you"):
        r = (probes.get(p) or {}).get("reply", "")
        out.add(r)
        out.add("Hi! " + r)
    return out


MIXED_WORDS = re.compile(
    r"\b(hey|hi|hello|hiya|howdy|thanks|thank|thx|cheers|bye|see you|"
    r"see ya|sup|whats up|wassup|good morning|good night|take care|"
    r"talk later|gotta go)\b", re.IGNORECASE)


# ------------------------------------------------------------- dev scoring

def score_dev(cases, run260, run282, probes260, probes282):
    r60 = {c["id"]: c for c in run260}
    r82 = {c["id"]: c for c in run282}
    fams = {}
    moves = []     # (id, turn_idx) where 282 reply != 260 reply
    problems = []

    def famd(fam):
        return fams.setdefault(fam, {"n": 0, "right": 0, "miss": []})

    for c in cases:
        fam = c["family"]
        f = famd(fam)
        f["n"] += 1
        a = r60[c["id"]]["rows"]
        b = r82[c["id"]]["rows"]
        ok = True
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra["reply"] != rb["reply"]:
                moves.append((c["id"], i))
            for row, arm in ((ra, "260"), (rb, "282")):
                if is_question(row.get("turn", "")) and row.get("ev", 0):
                    problems.append(f"{c['id']} turn{i} {arm} question write")
                    ok = False
        if c["expect_store"] is not None:
            got = [list(t) for t in r82[c["id"]]["stored"]]
            if sorted(got) != sorted(c["expect_store"]):
                problems.append(f"{c['id']} store {got} != {c['expect_store']}")
                ok = False
        if fam in ("greet", "thanks_close"):
            want = {"greet": "Hello.", "thanks": "Thanks!",
                    "close": "Bye."}[c["probe"]]
            exp = (probes282.get(want) or {}).get("reply", "")
            got = b[-1]["reply"] if b else ""
            if got != exp:
                problems.append(f"{c['id']} reply != probe {want!r}")
                ok = False
            if b and b[-1].get("ev", 0):
                problems.append(f"{c['id']} scored turn wrote")
                ok = False
        elif fam in ("mixed", "control"):
            for i, (ra, rb) in enumerate(zip(a, b)):
                if ra["reply"] != rb["reply"]:
                    problems.append(
                        f"{c['id']} turn{i} moved "
                        f"{ra['reply'][:40]!r} -> {rb['reply'][:40]!r}")
                    ok = False
                if ra.get("triples") != rb.get("triples"):
                    problems.append(f"{c['id']} turn{i} store differs")
                    ok = False
        if ok:
            f["right"] += 1
        else:
            f["miss"].append(c["id"])
    return {"families": fams, "moves_260_to_282": moves,
            "problems": problems}


# ----------------------------------------------------------- panel scoring

def panel_main(args):
    panelp, r260p, r282p, p260p, p282p, outp = args[:6]
    sys.path.insert(0, "scripts")
    import claude_small282_run as R282
    dialogs = R282.load_panel_dialogs(panelp)
    r60 = {r["id"]: r for r in json.load(open(r260p))}
    r82 = {r["id"]: r for r in json.load(open(r282p))}
    probes260 = json.load(open(p260p))
    probes282 = json.load(open(p282p))
    fit60, fit82 = fitting_set(probes260), fitting_set(probes282)
    rows = []
    for dg in dialogs:
        a = r60[dg["id"]]
        b = r82[dg["id"]]
        for i, (ra, rb) in enumerate(zip(a["rows"], b["rows"])):
            turn = ra.get("turn", "")
            cls = F282.classify_small282(turn)
            small = cls is not None
            in82 = rb["reply"] in fit82
            in60 = ra["reply"] in fit60
            rows.append({
                "id": dg["id"], "turn_idx": i, "class": cls or "other",
                "fam": dg.get("family"), "gold": dg.get("gold"),
                "mixed_hint": bool(not small and MIXED_WORDS.search(turn)),
                "arep_fit": in60, "brep_fit": in82,
                "arep_abstain": is_abstain(ra["reply"]),
                "brep_abstain": is_abstain(rb["reply"]),
                "same_reply": ra["reply"] == rb["reply"],
                "same_ev": ra.get("ev") == rb.get("ev"),
                "same_store": ra.get("triples") == rb.get("triples"),
                "writes_turn82": rb.get("ev", 0),
                "writes_turn60": ra.get("ev", 0),
                "is_question": is_question(turn),
            })
    st = [r for r in rows if r["class"] != "other"]
    ot = [r for r in rows if r["class"] == "other"]
    mx = [r for r in ot if r["mixed_hint"]]

    def verdict_st(r, fit):
        if r["brep_fit"] if fit else r["arep_fit"]:
            return "right"
        if r["brep_abstain"] if fit else r["arep_abstain"]:
            return "abstain"
        return "wrong"
    for r in st:
        r["verdict82"] = ("right" if (r["brep_fit"] and not r["writes_turn82"])
                          else ("abstain" if r["brep_abstain"] else "wrong"))
        r["verdict60"] = ("right" if r["arep_fit"]
                          else ("abstain" if r["arep_abstain"] else "wrong"))
    for r in ot:
        r["verdict82"] = ("same" if (r["same_reply"] and r["same_ev"]
                                     and r["same_store"]) else "moved")
    small_classes = {}
    for r in st:
        d = small_classes.setdefault(r["class"], {"n": 0, "right82": 0,
                                                  "right60": 0})
        d["n"] += 1
        d["right82"] += r["verdict82"] == "right"
        d["right60"] += r["verdict60"] == "right"
    res = {
        "n_dialogs": len(dialogs), "n_turns": len(rows),
        "smalltalk": {
            "n": len(st),
            "right82": sum(1 for r in st if r["verdict82"] == "right"),
            "wrong82": sum(1 for r in st if r["verdict82"] == "wrong"),
            "abstain82": sum(1 for r in st if r["verdict82"] == "abstain"),
            "right60": sum(1 for r in st if r["verdict60"] == "right"),
            "by_class": small_classes,
            "miss_ids82": [f"{r['id']}#{r['turn_idx']}" for r in st
                           if r["verdict82"] != "right"],
            "wrong_ids82": [f"{r['id']}#{r['turn_idx']}" for r in st
                            if r["verdict82"] == "wrong"],
        },
        "other": {
            "n": len(ot),
            "same": sum(1 for r in ot if r["verdict82"] == "same"),
            "moved_ids": [f"{r['id']}#{r['turn_idx']}" for r in ot
                          if r["verdict82"] != "same"],
            "mixed_n": len(mx),
            "mixed_same": sum(1 for r in mx if r["verdict82"] == "same"),
            "mixed_moved_ids": [f"{r['id']}#{r['turn_idx']}" for r in mx
                                if r["verdict82"] != "same"],
        },
        "smalltalk_writes82": [f"{r['id']}#{r['turn_idx']}" for r in st
                               if r["writes_turn82"]],
        "qwrite82": [f"{r['id']}#{r['turn_idx']}" for r in rows
                     if r["is_question"] and r["writes_turn82"]],
        "qwrite60": [f"{r['id']}#{r['turn_idx']}" for r in rows
                     if r["is_question"] and r["writes_turn60"]],
        "store_diffs": [f"{r['id']}#{r['turn_idx']}" for r in rows
                        if not r["same_store"]],
    }
    json.dump(res, open(outp, "w"), indent=1)
    s = res["smalltalk"]
    print(f"dialogs={len(dialogs)} turns={len(rows)} smalltalk={len(st)} "
          f"other={len(ot)} (mixed-hint {len(mx)})")
    print(f"smalltalk: 282 right {s['right82']}/{s['n']} wrong {s['wrong82']} "
          f"abstain {s['abstain82']} (260 right {s['right60']}); "
          f"by-class {s['by_class']}")
    print(f"smalltalk miss {s['miss_ids82']}; wrong {s['wrong_ids82']}")
    print(f"other same {res['other']['same']}/{len(ot)} "
          f"moved {res['other']['moved_ids']}")
    print(f"mixed same {res['other']['mixed_same']}/{len(mx)} "
          f"moved {res['other']['mixed_moved_ids']}")
    print(f"282 smalltalk writes {res['smalltalk_writes82']}; "
          f"question writes 282 {res['qwrite82']} 260 {res['qwrite60']}; "
          f"store diffs {res['store_diffs']}")
    return 0


# ------------------------------------------------------------ st234 scoring

def st234_main(args):
    panelp, r260p, r282p, p260p, p282p, outp = args[:6]
    items = [json.loads(x) for x in open(panelp).read().strip().split("\n")
             if x.strip()]
    r60 = {r["id"]: r for r in json.load(open(r260p))}
    r82 = {r["id"]: r for r in json.load(open(r282p))}
    probes260 = json.load(open(p260p))
    probes282 = json.load(open(p282p))
    fit60, fit82 = fitting_set(probes260), fitting_set(probes282)
    rows = []
    for it in items:
        a = r60[it["id"]]
        b = r82[it["id"]]
        pos = (it.get("expect") == "small_talk")
        rows.append({
            "id": it["id"], "family": it.get("family"),
            "expect": it.get("expect"), "positive": pos,
            "hit60": a["turn_reply"] in fit60,
            "hit82": b["turn_reply"] in fit82,
            "same_reply": a["turn_reply"] == b["turn_reply"],
            "setup_same": a["setup_replies"] == b["setup_replies"],
            "nb_same": (a["stored_after_setup"] == b["stored_after_setup"]
                        and a["stored_after_turn"] == b["stored_after_turn"]),
            "writes82": b["writes_turn"],
            "writes60": a["writes_turn"],
        })
    fams = {}
    for r in rows:
        f = fams.setdefault(r["family"], {"n": 0, "hit60": 0, "hit82": 0,
                                          "same": 0})
        f["n"] += 1
        f["hit60"] += r["hit60"]
        f["hit82"] += r["hit82"]
        f["same"] += r["same_reply"]
    wb = [r for r in rows if r["positive"]]
    other = [r for r in rows if not r["positive"]]
    res = {
        "n": len(rows),
        "families": fams,
        "wellbeing": {"n": len(wb),
                      "hit60": sum(1 for r in wb if r["hit60"]),
                      "hit82": sum(1 for r in wb if r["hit82"]),
                      "miss82": [r["id"] for r in wb if not r["hit82"]]},
        "other": {"n": len(other),
                  "same": sum(1 for r in other if r["same_reply"]),
                  "moved_ids": [r["id"] for r in other
                                if not r["same_reply"]]},
        "writes82": [r["id"] for r in rows if r["writes82"]],
        "store_diffs": [r["id"] for r in rows if not r["nb_same"]],
        "setup_diffs": [r["id"] for r in rows if not r["setup_same"]],
    }
    json.dump(res, open(outp, "w"), indent=1)
    print(f"n={len(rows)} wellbeing 260 {res['wellbeing']['hit60']}/"
          f"{len(wb)} 282 {res['wellbeing']['hit82']}/{len(wb)} "
          f"miss82 {res['wellbeing']['miss82']}")
    print(f"other same {res['other']['same']}/{len(other)} "
          f"moved {res['other']['moved_ids']}")
    print(f"families {json.dumps(fams)}")
    print(f"282 writes {res['writes82']}; store diffs {res['store_diffs']}; "
          f"setup diffs {res['setup_diffs']}")
    return 0


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.load(open(argv[2]))
        run260 = json.load(open(argv[3]))
        run282 = json.load(open(argv[4]))
        probes260 = json.load(open(argv[5]))
        probes282 = json.load(open(argv[6]))
        res = score_dev(cases, run260, run282, probes260, probes282)
        json.dump(res, open(argv[7], "w"), indent=1)
        for fam, f in res["families"].items():
            print(f"{fam:14s} {f['right']}/{f['n']} miss={f['miss']}")
        print("moves 260->282:", len(res["moves_260_to_282"]))
        for m in res["moves_260_to_282"]:
            print("  MOVE", m[0], m[1])
        print("problems:", res["problems"] if res["problems"] else "none")
        return 0
    if mode == "panel":
        return panel_main(argv[2:])
    if mode == "st234":
        return st234_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
