#!/usr/bin/env python3
"""Exp 282b dev scorer + blind-panel scorer + smalltalk234 scorer.

Mechanical counts only (right, wrong, abstain, writes), per the panel
writer's categories (greeting / closing / mixed / control). Truth of
claims and grammar are not graded here; every changed reply is the
head's own canonical small-talk reply, via the layer in
scripts/claude_fix282b_vocab.py. Prints ids of misses, never item text.

  dev <cases.json> <run282.json> <run282b.json> <probes282.json>
      <probes282b.json> <out.json>
    greet/thanks_close: the 282b arm's scored-turn reply must equal its
      own arm's reply to the case's probe ("Hello." / "Thanks!" /
      "Bye."), with 0 writes on that turn. 282's reply shown beside
      (dev info only).
    mixed/control: every 282b reply must equal 282's, with equal stores.
    expect_store checked exactly when given. Small-talk turns with writes
    fail. Never prints item text beyond ids and counts.
  panel <panel.jsonl|json> <run282.json> <run282b.json> <probes282.json>
      <probes282b.json> <out.json>
    Schema gate first: every row must hold dialog_id, turn_index,
    user_text (or `user`), category, gold, with category in
    {greeting, closing, mixed, control}. A missing file, field, family
    or label prints SCHEMA-MISMATCH and exits 3 (VOID, not FAIL).
    Then per writer category:
      greeting: RIGHT = reply is the arm's own "Hello." reply (plain or
                "Hi! "-prefixed) with 0 writes; ABSTAIN = clarify/dontknow;
                else WRONG.
      closing : RIGHT = reply is the arm's own "Thanks!" or "Bye." reply
                (plain or "Hi! "-prefixed) with 0 writes; else as above.
      mixed/control: RIGHT = 282b reply == 282 reply with equal write
                deltas and equal stores (route preserved).
    Prints ids of misses, never item text.
  st234 <panel.jsonl> <run282.json> <run282b.json> <probes282.json>
      <probes282b.json> <out.json>
    smalltalkpanel234 rerun: wellbeing (expect small_talk) fitting hits per
    arm; every other item 282b == 282; 0 writes and identical stores.
"""

import json
import sys

sys.path.insert(0, "scripts")

PANEL_CATS282B = ("greeting", "closing", "mixed", "control")


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


def fitting_greet(probes):
    r = (probes.get("Hello.") or {}).get("reply", "")
    return {r, "Hi! " + r}


def fitting_close(probes):
    out = set()
    for p in ("Thanks!", "Bye."):
        r = (probes.get(p) or {}).get("reply", "")
        out.add(r)
        out.add("Hi! " + r)
    return out


# ------------------------------------------------------------- dev scoring

def score_dev(cases, run282, run282b, probes282, probes282b):
    r82 = {c["id"]: c for c in run282}
    r8b = {c["id"]: c for c in run282b}
    fams = {}
    moves = []     # (id, turn_idx) where 282b reply != 282 reply
    problems = []

    def famd(fam):
        return fams.setdefault(fam, {"n": 0, "right": 0, "miss": []})

    for c in cases:
        fam = c["family"]
        f = famd(fam)
        f["n"] += 1
        a = r82[c["id"]]["rows"]
        b = r8b[c["id"]]["rows"]
        ok = True
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra["reply"] != rb["reply"]:
                moves.append((c["id"], i))
            for row, arm in ((ra, "282"), (rb, "282b")):
                if is_question(row.get("turn", "")) and row.get("ev", 0):
                    problems.append(f"{c['id']} turn{i} {arm} question write")
                    ok = False
        if c["expect_store"] is not None:
            got = [list(t) for t in r8b[c["id"]]["stored"]]
            if sorted(got) != sorted(c["expect_store"]):
                problems.append(f"{c['id']} store {got} != {c['expect_store']}")
                ok = False
        if fam in ("greet", "thanks_close"):
            want = {"greet": "Hello.", "thanks": "Thanks!",
                    "close": "Bye."}[c["probe"]]
            exp = (probes282b.get(want) or {}).get("reply", "")
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
    return {"families": fams, "moves_282_to_282b": moves,
            "problems": problems}


# ----------------------------------------------------------- panel scoring

def _panel_rows(path):
    import claude_small282b_run as R282B
    items = R282B._panel_items(path)
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
            print(f"EMPTY-TURN: row {n} has empty turn text; refusing to score")
            raise SystemExit(4)
        if it["category"] not in PANEL_CATS282B:
            print(f"SCHEMA-MISMATCH: row {n} unexpected category "
                  f"{it['category']!r}")
            raise SystemExit(3)
    return items


def panel_main(args):
    panelp, r282p, r282bp, p282p, p282bp, outp = args[:6]
    import claude_small282b_run as R282B
    items = _panel_rows(panelp)
    dialogs = R282B.load_panel_dialogs(panelp)
    r82 = {r["id"]: r for r in json.load(open(r282p))}
    r8b = {r["id"]: r for r in json.load(open(r282bp))}
    probes282 = json.load(open(p282p))
    probes282b = json.load(open(p282bp))
    fg82, fg8b = fitting_greet(probes282), fitting_greet(probes282b)
    fc82, fc8b = fitting_close(probes282), fitting_close(probes282b)
    rows = []
    for dg in dialogs:
        try:
            a, b = r82[dg["id"]], r8b[dg["id"]]
        except KeyError as e:
            print(f"SCORE-ERROR: dialog {e} missing from a run file")
            raise SystemExit(2)
        for i, (ra, rb) in enumerate(zip(a["rows"], b["rows"])):
            turn = ra.get("turn", "")
            cat = dg["cats"][i] if i < len(dg.get("cats", [])) else "?"
            if cat == "greeting":
                fit82, fit8b = ra["reply"] in fg82, rb["reply"] in fg8b
            elif cat == "closing":
                fit82, fit8b = ra["reply"] in fc82, rb["reply"] in fc8b
            else:
                fit82 = fit8b = None
            rows.append({
                "id": dg["id"], "turn_idx": i, "cat": cat,
                "fit82": fit82, "fit8b": fit8b,
                "abstain82": is_abstain(ra["reply"]),
                "abstain8b": is_abstain(rb["reply"]),
                "same_reply": ra["reply"] == rb["reply"],
                "same_ev": ra.get("ev") == rb.get("ev"),
                "same_store": ra.get("triples") == rb.get("triples"),
                "writes_turn8b": rb.get("ev", 0),
                "writes_turn82": ra.get("ev", 0),
                "is_question": is_question(turn),
            })
    sc = [r for r in rows if r["cat"] in ("greeting", "closing")]
    mc = [r for r in rows if r["cat"] in ("mixed", "control")]

    def verdict_sc(r, arm8b):
        fit = r["fit8b"] if arm8b else r["fit82"]
        abst = r["abstain8b"] if arm8b else r["abstain82"]
        if fit and not (arm8b and r["writes_turn8b"]):
            return "right"
        if abst:
            return "abstain"
        return "wrong"
    for r in sc:
        r["verdict8b"] = verdict_sc(r, True)
        r["verdict82"] = verdict_sc(r, False)
    for r in mc:
        r["verdict8b"] = ("same" if (r["same_reply"] and r["same_ev"]
                                     and r["same_store"]) else "moved")
    by_cat = {}
    for r in sc:
        d = by_cat.setdefault(r["cat"], {"n": 0, "right8b": 0,
                                         "right82": 0})
        d["n"] += 1
        d["right8b"] += r["verdict8b"] == "right"
        d["right82"] += r["verdict82"] == "right"
    n_sc = len(sc)
    right8b = sum(1 for r in sc if r["verdict8b"] == "right")
    import math
    bar = math.ceil(0.9 * n_sc) if n_sc else 0
    res = {
        "n_dialogs": len(dialogs), "n_turns": len(rows),
        "smalltalk": {
            "n": n_sc, "bar": bar,
            "right8b": right8b,
            "wrong8b": sum(1 for r in sc if r["verdict8b"] == "wrong"),
            "abstain8b": sum(1 for r in sc if r["verdict8b"] == "abstain"),
            "right82": sum(1 for r in sc if r["verdict82"] == "right"),
            "by_cat": by_cat,
            "pass_bar": right8b >= bar,
            "miss_ids8b": [f"{r['id']}#{r['turn_idx']}" for r in sc
                           if r["verdict8b"] != "right"],
            "wrong_ids8b": [f"{r['id']}#{r['turn_idx']}" for r in sc
                            if r["verdict8b"] == "wrong"],
        },
        "mixed_control": {
            "n": len(mc),
            "same": sum(1 for r in mc if r["verdict8b"] == "same"),
            "moved_ids": [f"{r['id']}#{r['turn_idx']}" for r in mc
                          if r["verdict8b"] != "same"],
        },
        "smalltalk_writes8b": [f"{r['id']}#{r['turn_idx']}" for r in sc
                               if r["writes_turn8b"]],
        "qwrite8b": [f"{r['id']}#{r['turn_idx']}" for r in rows
                     if r["is_question"] and r["writes_turn8b"]],
        "qwrite82": [f"{r['id']}#{r['turn_idx']}" for r in rows
                     if r["is_question"] and r["writes_turn82"]],
        "store_diffs": [f"{r['id']}#{r['turn_idx']}" for r in rows
                        if not r["same_store"]],
    }
    ok = (res["smalltalk"]["pass_bar"]
          and not res["smalltalk_writes8b"]
          and not res["qwrite8b"]
          and res["mixed_control"]["same"] == len(mc)
          and not res["store_diffs"])
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    s = res["smalltalk"]
    print(f"dialogs={len(dialogs)} turns={len(rows)} writer-smalltalk={n_sc} "
          f"(bar {bar}) mixed/control={len(mc)}")
    print(f"writer-smalltalk: 282b right {s['right8b']}/{n_sc} "
          f"wrong {s['wrong8b']} abstain {s['abstain8b']} "
          f"(282 right {s['right82']}); by-cat {s['by_cat']}")
    print(f"282b miss {s['miss_ids8b']}; wrong {s['wrong_ids8b']}")
    print(f"mixed/control same {res['mixed_control']['same']}/{len(mc)} "
          f"moved {res['mixed_control']['moved_ids']}")
    print(f"282b smalltalk writes {res['smalltalk_writes8b']}; "
          f"question writes 282b {res['qwrite8b']} 282 {res['qwrite82']}; "
          f"store diffs {res['store_diffs']}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


# ------------------------------------------------------------ st234 scoring

def st234_main(args):
    panelp, r282p, r282bp, p282p, p282bp, outp = args[:6]
    items = [json.loads(x) for x in open(panelp).read().strip().split("\n")
             if x.strip()]
    r82 = {r["id"]: r for r in json.load(open(r282p))}
    r8b = {r["id"]: r for r in json.load(open(r282bp))}
    probes282 = json.load(open(p282p))
    probes282b = json.load(open(p282bp))

    def fitset(probes):
        out = set()
        for p in ("Hello.", "Thanks!", "Bye.", "how are you"):
            r = (probes.get(p) or {}).get("reply", "")
            out.add(r)
            out.add("Hi! " + r)
        return out
    fit82, fit8b = fitset(probes282), fitset(probes282b)
    rows = []
    for it in items:
        a = r82[it["id"]]
        b = r8b[it["id"]]
        pos = (it.get("expect") == "small_talk")
        rows.append({
            "id": it["id"], "family": it.get("family"),
            "expect": it.get("expect"), "positive": pos,
            "hit82": a["turn_reply"] in fit82,
            "hit8b": b["turn_reply"] in fit8b,
            "same_reply": a["turn_reply"] == b["turn_reply"],
            "setup_same": a["setup_replies"] == b["setup_replies"],
            "nb_same": (a["stored_after_setup"] == b["stored_after_setup"]
                        and a["stored_after_turn"] == b["stored_after_turn"]),
            "writes8b": b["writes_turn"],
            "writes82": a["writes_turn"],
        })
    fams = {}
    for r in rows:
        f = fams.setdefault(r["family"], {"n": 0, "hit82": 0, "hit8b": 0,
                                          "same": 0})
        f["n"] += 1
        f["hit82"] += r["hit82"]
        f["hit8b"] += r["hit8b"]
        f["same"] += r["same_reply"]
    wb = [r for r in rows if r["positive"]]
    other = [r for r in rows if not r["positive"]]
    res = {
        "n": len(rows),
        "families": fams,
        "wellbeing": {"n": len(wb),
                      "hit82": sum(1 for r in wb if r["hit82"]),
                      "hit8b": sum(1 for r in wb if r["hit8b"]),
                      "miss8b": [r["id"] for r in wb if not r["hit8b"]]},
        "other": {"n": len(other),
                  "same": sum(1 for r in other if r["same_reply"]),
                  "moved_ids": [r["id"] for r in other
                                if not r["same_reply"]]},
        "writes8b": [r["id"] for r in rows if r["writes8b"]],
        "store_diffs": [r["id"] for r in rows if not r["nb_same"]],
        "setup_diffs": [r["id"] for r in rows if not r["setup_same"]],
    }
    ok = (res["wellbeing"]["hit8b"] >= res["wellbeing"]["hit82"]
          and res["other"]["same"] == len(other)
          and not res["writes8b"] and not res["store_diffs"]
          and not res["setup_diffs"])
    res["verdict"] = "PASS" if ok else "FAIL"
    json.dump(res, open(outp, "w"), indent=1)
    print(f"n={len(rows)} wellbeing 282 {res['wellbeing']['hit82']}/"
          f"{len(wb)} 282b {res['wellbeing']['hit8b']}/{len(wb)} "
          f"miss8b {res['wellbeing']['miss8b']}")
    print(f"other same {res['other']['same']}/{len(other)} "
          f"moved {res['other']['moved_ids']}")
    print(f"families {json.dumps(fams)}")
    print(f"282b writes {res['writes8b']}; store diffs {res['store_diffs']}; "
          f"setup diffs {res['setup_diffs']}")
    print("VERDICT:", res["verdict"])
    return 0 if ok else 1


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.load(open(argv[2]))
        run282 = json.load(open(argv[3]))
        run282b = json.load(open(argv[4]))
        probes282 = json.load(open(argv[5]))
        probes282b = json.load(open(argv[6]))
        res = score_dev(cases, run282, run282b, probes282, probes282b)
        json.dump(res, open(argv[7], "w"), indent=1)
        for fam, f in res["families"].items():
            print(f"{fam:14s} {f['right']}/{f['n']} miss={f['miss']}")
        print("moves 282->282b:", len(res["moves_282_to_282b"]))
        for m in res["moves_282_to_282b"]:
            print("  MOVE", m[0], m[1])
        print("problems:", res["problems"] if res["problems"] else "none")
        return 0 if not res["problems"] else 1
    if mode == "panel":
        return panel_main(argv[2:])
    if mode == "st234":
        return st234_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
