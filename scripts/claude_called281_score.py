#!/usr/bin/env python3
"""Exp 281 dev scorer + blind-panel scorer (mechanical counts only).

  dev <cases.json> <run260.json> <run281.json> <out.json>
    stored_*  : 281 must answer with the target value, 0 writes on the
                question turn. 260's reply shown beside (dev info only).
    notstored : both arms must abstain (dontknow/clarify), 0 writes.
    ambiguous : every 281 reply must equal 260's (route preserved).
    control   : every 281 reply must equal 260's.
    expect_store checked exactly when given. Question-turn writes fail.
    Never prints item text beyond ids and counts.

  panel <panel.jsonl|panel.json> <run260.json> <run281.json> <out.json>
    Flexible loader (the blind panel's exact schema is set by its writer):
    items shaped {id, setup[], turn, followup} or {id, turns[]} (or
    {id, family, ...}). Mechanical classes from the turn text + the store
    after setup (the panel's own family label is recorded, never trusted
    for scoring):
      stored    : a called/named/name-of/do-you-call rewrite matched AND a
                  [X, R, V] triple is in stored_after_setup. RIGHT = an
                  answer containing V; WRONG = an answer without V;
                  ABSTAIN = clarify/dontknow.
      notstored : a rewrite matched but no [X, R] triple is stored. RIGHT =
                  abstain; WRONG (a guess) = any answer.
      ambiguous : called/named wording with no rewrite match ("called Bo"
                  belongs to the value). RIGHT = 281 reply == 260 reply.
      control   : no called/named wording. Reported: 281 == 260 counts.
    M3: stored_after_setup/turn/followup equal 281 vs 260 on every item;
    0 question-turn writes on 281. Truth of claims and grammar are
    director-graded, ungraded here; changed replies come only from
    scripts/claude_fix281_called.py (rewrite + head's own answer).
    Prints ids of misses, never item text.
"""

import json
import re
import sys

sys.path.insert(0, "scripts")
import claude_fix281_called as F281  # noqa: E402 (matcher only, sealed)

DONTKNOW = ("don't know", "do not know", "never told me",
            "never taught me", "no record", "not someone i can look up")
CLARIFY = ("could you say it another way", "didn't understand",
           "don't understand", "was that a question",
           "i only know current facts")


def low(s):
    return " ".join(str(s).lower().split())


def is_dontknow(reply):
    return any(m in low(reply) for m in DONTKNOW)


def is_clarify(reply):
    return any(m in low(reply) for m in CLARIFY)


def is_abstain(reply):
    return is_dontknow(reply) or is_clarify(reply)


def is_question(turn):
    return str(turn).rstrip().endswith("?")


CALLED_WORDS = ("called", "named", "name of", "do you call")


def has_called_wording(turn):
    return any(w in low(turn) for w in CALLED_WORDS)


def norm_name(s):
    return " ".join(str(s).replace("\u2019", "'").replace("\u2018", "'")
                    .lower().split())


def parse_rel(rel):
    """'Ana's cat' -> (Ana, cat); else None."""
    parts = norm_name(rel).split("'s")
    if len(parts) != 2:
        return None
    subj = parts[0].strip().strip(" ?!.,\"'")
    relation = parts[1].strip().strip(" ?!.,\"'")
    if not subj or not relation or " " in relation.strip():
        # relation must be a single word ("cat"); multi-word -> unparsed
        if " " in relation.strip():
            return None
    if not subj or not relation:
        return None
    return subj, relation


def lookup(stored, subj, relation):
    for t in stored or []:
        if len(t) == 3 and norm_name(t[0]) == subj \
                and norm_name(t[1]) == relation:
            return t[2]
    return None


BROKEN281 = re.compile(r"don'?t know .*\b(called|named)\s*[.?!]?\s*$",
                       re.IGNORECASE)


# ------------------------------------------------------------- dev scoring

def score_dev(cases, run260, run281):
    r60 = {c["id"]: c for c in run260}
    r81 = {c["id"]: c for c in run281}
    fams = {}
    moves = []     # (id, turn_idx) where 281 reply != 260 reply
    problems = []

    def famd(fam):
        return fams.setdefault(fam, {"n": 0, "right": 0, "miss": []})

    for c in cases:
        fam = c["family"]
        f = famd(fam)
        f["n"] += 1
        a = r60[c["id"]]["rows"]
        b = r81[c["id"]]["rows"]
        ok = True
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra["reply"] != rb["reply"]:
                moves.append((c["id"], i))
            for row, arm in ((ra, "260"), (rb, "281")):
                if is_question(row.get("turn", "")) and row.get("ev", 0):
                    problems.append(f"{c['id']} turn{i} {arm} question write")
                    ok = False
        if c["expect_store"] is not None:
            got = [list(t) for t in r81[c["id"]]["stored"]]
            if sorted(got) != sorted(c["expect_store"]):
                problems.append(f"{c['id']} store {got} != {c['expect_store']}")
                ok = False
        if fam.startswith("stored") or fam == "opener_called":
            for idx, how, text in c["checks"]:
                rep = b[idx]["reply"] if idx < len(b) else ""
                has = text in rep
                if (how == "has" and not has) or \
                        (how == "not" and has):
                    problems.append(f"{c['id']} check {idx} {how} {text!r}")
                    ok = False
            if b[-1].get("ev", 0):
                problems.append(f"{c['id']} scored turn wrote")
                ok = False
        elif fam == "notstored":
            for row in b:
                if is_question(row.get("turn", "")):
                    if not is_abstain(row["reply"]) or row.get("ev", 0):
                        problems.append(f"{c['id']} notstored not-abstain")
                        ok = False
                        break
        elif fam in ("ambiguous", "control"):
            for i, (ra, rb) in enumerate(zip(a, b)):
                if ra["reply"] != rb["reply"]:
                    problems.append(f"{c['id']} turn{i} moved "
                                    f"{ra['reply'][:40]!r} -> {rb['reply'][:40]!r}")
                    ok = False
        if ok:
            f["right"] += 1
        else:
            f["miss"].append(c["id"])
    return {"families": fams, "moves_260_to_281": moves,
            "problems": problems}


# ----------------------------------------------------------- panel scoring

def load_panel_items(path):
    txt = open(path).read().strip()
    if path.endswith(".jsonl"):
        return [json.loads(x) for x in txt.split("\n") if x.strip()]
    doc = json.load(open(path))
    if isinstance(doc, list):
        return doc
    for k in ("items", "dialogs", "cases", "panel"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    raise SystemExit("panel loader: no item list found")


def panel_turns(it):
    """Return (setup[], turn, followup_or_None, family, id) flexibly."""
    iid = it.get("id", "?")
    fam = it.get("family", it.get("cat", it.get("kind", it.get("group", ""))))
    if "turns" in it and isinstance(it["turns"], list):
        ts = it["turns"]
        setup = ts[:-1] if len(ts) > 1 else []
        return setup, ts[-1], None, fam, iid
    setup = it.get("setup", it.get("teach", it.get("teaches", [])))
    if isinstance(setup, str):
        setup = [setup]
    turn = it.get("turn", it.get("question", it.get("text", "")))
    foll = it.get("followup", it.get("follow_up"))
    return list(setup or []), turn, foll, fam, iid


def classify_panel(turn, stored_after_setup):
    """(class, gold_or_None)."""
    if not is_question(turn):
        return ("control", None)
    if not has_called_wording(turn):
        return ("control", None)
    rw = F281.rewrite_called281(turn)
    if rw is None:
        return ("ambiguous", None)
    m, _kind = F281._match_core(_apos_strip(turn))
    if m is None:
        # opener-prefixed: match on the opener-stripped core
        import claude_fix260_openers as F260
        sp = F260.split_openers260(_apos_strip(turn))
        if sp is None:
            return ("unparsed", None)
        m, _kind = F281._match_core(sp[0].strip())
        if m is None:
            return ("unparsed", None)
    pr = parse_rel(m.group("rel"))
    if pr is None:
        return ("unparsed", None)
    subj, relation = pr
    v = lookup(stored_after_setup, subj, relation)
    if v is None:
        return ("notstored", None)
    return ("stored", v)


def _apos_strip(turn):
    return F281._apos(str(turn)).strip()


def load_rows(p):
    txt = open(p).read().strip()
    if p.endswith(".jsonl"):
        return [json.loads(x) for x in txt.split("\n") if x.strip()]
    doc = json.load(open(p))
    return doc if isinstance(doc, list) else doc.get("rows", doc)


def panel_main(args):
    panelp, r260p, r281p, outp = args[:4]
    items = load_panel_items(panelp)
    r60 = {r["id"]: r for r in load_rows(r260p)}
    r81 = {r["id"]: r for r in load_rows(r281p)}
    rows = []
    for it in items:
        _setup, turn, _foll, fam, iid = panel_turns(it)
        a = r60[iid]
        b = r81[iid]
        cls, gold = classify_panel(turn if isinstance(turn, str) else "",
                                   a.get("stored_after_setup"))
        arep = a.get("turn_reply", a.get("reply", ""))
        brep = b.get("turn_reply", b.get("reply", ""))
        wt60, wt81 = a.get("writes_turn", 0), b.get("writes_turn", 0)
        wf60, wf81 = a.get("writes_followup", 0), b.get("writes_followup", 0)
        s_same = (a.get("stored_after_setup") == b.get("stored_after_setup")
                  and a.get("stored_after_turn") == b.get("stored_after_turn")
                  and a.get("stored_after_followup") == b.get("stored_after_followup"))
        rows.append({"id": iid, "class": cls, "gold": gold,
                     "fam": fam, "arep_abstain": is_abstain(arep),
                     "brep_abstain": is_abstain(brep),
                     "gold_in_b": (gold in brep) if gold else None,
                     "gold_in_a": (gold in arep) if gold else None,
                     "same_reply": arep == brep,
                     "writes_turn81": wt81, "writes_fol81": wf81,
                     "writes_turn60": wt60, "writes_fol60": wf60,
                     "store_same": s_same,
                     "broken_abstain81": bool(BROKEN281.search(brep or "")),
                     "broken_abstain60": bool(BROKEN281.search(arep or ""))})
    stored = [r for r in rows if r["class"] == "stored"]
    nstored = [r for r in rows if r["class"] == "notstored"]
    amb = [r for r in rows if r["class"] == "ambiguous"]
    ctl = [r for r in rows if r["class"] == "control"]
    unp = [r for r in rows if r["class"] == "unparsed"]

    def verdict_stored(r):
        if r["gold_in_b"] and not r["brep_abstain"]:
            return "right"
        if r["brep_abstain"]:
            return "abstain"
        return "wrong"
    for r in stored:
        r["verdict81"] = verdict_stored(r)
        r["verdict60"] = ("right" if (r["gold_in_a"] and not r["arep_abstain"])
                          else ("abstain" if r["arep_abstain"] else "wrong"))
    for r in nstored:
        r["verdict81"] = "right" if r["brep_abstain"] else "wrong-guess"
        r["verdict60"] = "right" if r["arep_abstain"] else "wrong-guess"
    for r in amb + ctl:
        r["verdict81"] = "same" if r["same_reply"] else "moved"
    res = {
        "n": len(rows),
        "stored": {"n": len(stored),
                   "right81": sum(1 for r in stored if r["verdict81"] == "right"),
                   "wrong81": sum(1 for r in stored if r["verdict81"] == "wrong"),
                   "abstain81": sum(1 for r in stored if r["verdict81"] == "abstain"),
                   "right60": sum(1 for r in stored if r["verdict60"] == "right"),
                   "wrong_ids81": [r["id"] for r in stored if r["verdict81"] == "wrong"],
                   "miss_ids81": [r["id"] for r in stored if r["verdict81"] != "right"]},
        "notstored": {"n": len(nstored),
                      "right81": sum(1 for r in nstored if r["verdict81"] == "right"),
                      "guesses81": [r["id"] for r in nstored if r["verdict81"] != "right"],
                      "right60": sum(1 for r in nstored if r["verdict60"] == "right")},
        "ambiguous": {"n": len(amb),
                      "same": sum(1 for r in amb if r["same_reply"]),
                      "moved_ids": [r["id"] for r in amb if not r["same_reply"]]},
        "control": {"n": len(ctl),
                    "same": sum(1 for r in ctl if r["same_reply"]),
                    "moved_ids": [r["id"] for r in ctl if not r["same_reply"]]},
        "unparsed": [r["id"] for r in unp],
        "qwrite81": [r["id"] for r in rows if r["writes_turn81"] or r["writes_fol81"]],
        "store_diffs": [r["id"] for r in rows if not r["store_same"]],
        "broken_abstain81": [r["id"] for r in rows if r["broken_abstain81"]],
        "broken_abstain60": [r["id"] for r in rows if r["broken_abstain60"]],
        "rows": [{k: r[k] for k in ("id", "class", "verdict81", "same_reply",
                                    "store_same")} for r in rows],
    }
    json.dump(res, open(outp, "w"), indent=1)
    print(f"panel n={len(rows)} stored={len(stored)} notstored={len(nstored)} "
          f"ambiguous={len(amb)} control={len(ctl)} unparsed={len(unp)}")
    s = res["stored"]
    print(f"stored: 281 right {s['right81']}/{s['n']} wrong {s['wrong81']} "
          f"(260 right {s['right60']}); miss {s['miss_ids81']}; "
          f"wrong {s['wrong_ids81']}")
    n = res["notstored"]
    print(f"notstored: 281 abstain {n['right81']}/{n['n']} (260 {n['right60']}); "
          f"guesses {n['guesses81']}")
    print(f"ambiguous same {res['ambiguous']['same']}/{len(amb)} "
          f"moved {res['ambiguous']['moved_ids']}")
    print(f"control same {res['control']['same']}/{len(ctl)} "
          f"moved {res['control']['moved_ids']}")
    print(f"unparsed {res['unparsed']}")
    print(f"281 question writes {res['qwrite81']}; store diffs {res['store_diffs']}")
    print(f"broken abstains 281 {res['broken_abstain81']} "
          f"(260: {res['broken_abstain60']})")
    return 0


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.load(open(argv[2]))
        run260 = json.load(open(argv[3]))
        run281 = json.load(open(argv[4]))
        res = score_dev(cases, run260, run281)
        json.dump(res, open(argv[5], "w"), indent=1)
        for fam, f in res["families"].items():
            print(f"{fam:14s} {f['right']}/{f['n']} miss={f['miss']}")
        print("moves 260->281:", len(res["moves_260_to_281"]))
        for m in res["moves_260_to_281"][:40]:
            print("  MOVE", m[0], m[1])
        print("problems:", res["problems"] if res["problems"]
              else "none")
        return 0
    if mode == "panel":
        return panel_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
