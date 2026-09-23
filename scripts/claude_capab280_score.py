#!/usr/bin/env python3
"""Exp 280 dev scorer + blind-panel scorer (mechanical counts only).

  dev <cases.json> <run260.json> <run280.json> <out.json>
    Per family (save ask1 twohop correct forget abstain source): integer
    counts of right / wrong / abstain turns, plus write counts. Ability
    score = right / total. same_as_base: every ability-family reply on 280
    must equal 260's reply (diffs listed). capab turns: checked only on 280
    (general items need >=3 ability keywords and 0 forbidden phrases; cant
    and canyou turns are recorded, never tuned).
    Anything about truth of claims or grammar is NOT graded here (director).
    Never prints panel/dev item text beyond ids and counts.

  panel <panel.jsonl|panel.json> <run260.jsonl> <run280.jsonl> <out.json>
    Flexible loader for the blind capabilpanel280 (schema unknown at seal
    time): accepts items shaped either {id, setup[], turn, followup} or
    {id, turns[]} (or {id, family, dialogs...}); classifies scored turns as
    general / canyou / control from the panel's own family label when
    present, else by turn text. Mechanical counts only:
      M1a: 280 replies claiming an ability the sealed table does not
           support (forbidden-phrase scan): must be 0.
      M1b: every general item's 280 reply lists >= 3 abilities (keyword
           count): all must pass.
      M3: 0 notebook changes on question/self turns (write-delta scan).
    Prints ids of misses, never item text.
"""

import json
import re
import sys

DONTKNOW = ("don't know", "do not know", "never told me",
            "never taught me", "no record")
CLARIFY = ("could you say it another way", "didn't understand",
           "don't understand", "i only know current facts")
# Claims the sealed ability table does not support: exactly the OLD false
# sheet's signatures (kept in sync with scripts/claude_fix280_capab.py
# OLD_SIG280; duplicated here so the scorer never imports agent code).
# The sealed CAN280 reply contains none of these.
FORBIDDEN280 = (
    "one or two steps",
    "following one or two",
    "correct a fact or forget",
    "forget one when you ask",
    "answer questions from my notes, following",
)
# Supported-ability keywords (kept in sync with ABILITY280 phrases).
ABILITY_KW = (
    "save what you teach",
    "notebook",
    "one-step",
    "one step",
    "instead of guessing",
    "do not know",
    "don't know",
    "where each fact came from",
    "came from",
)


def low(s):
    return " ".join(str(s).lower().split())


def is_dontknow(reply):
    return any(m in low(reply) for m in DONTKNOW)


def is_clarify(reply):
    return any(m in low(reply) for m in CLARIFY)


def forbidden_hits(reply):
    r = low(reply)
    return [p for p in FORBIDDEN280 if p in r]


def ability_kw_count(reply):
    r = low(reply)
    return sum(1 for k in ABILITY_KW if k in r)


def check_pass(reply, checks):
    for idx, how, text in checks:
        has = text in reply
        if how == "has" and not has:
            return False
        if how == "not" and has:
            return False
    return True


def score_dev(cases, run260, run280):
    r60 = {c["id"]: c for c in run260}
    r80 = {c["id"]: c for c in run280}
    fams = {}
    diffs = []
    qwrite_viol = []
    for c in cases:
        fam = c["family"]
        f = fams.setdefault(fam, {"n": 0, "r60": [0, 0, 0], "r80": [0, 0, 0],
                                  "w60": 0, "w80": 0})
        a = r60[c["id"]]
        b = r80.get(c["id"])
        rows_a = a["rows"]
        if fam != "capab" and b is not None:
            for ra, rb in zip(rows_a, b["rows"]):
                if ra["reply"] != rb["reply"]:
                    diffs.append((c["id"], ra.get("turn")))
        for arm, rows, k in (("60", rows_a, "r60"), ("80", b["rows"] if b else [], "r80")):
            if fam == "capab":
                continue
            for i, row in enumerate(rows):
                turn = row.get("turn", "")
                rep = row.get("reply", "")
                ev = row.get("ev", 0)
                if ev:
                    f["w" + arm] += 1
                    if turn.strip().endswith("?"):
                        qwrite_viol.append((c["id"], arm, i))
                f["n"] += 0  # counted once below
        f["n"] += 1
        # ability verdict per arm on the scored turn(s)
        for arm, rows, k in (("60", rows_a, "r60"), ("80", b["rows"] if b else [], "r80")):
            if fam == "capab" or not rows:
                continue
            v = verdict(c, rows)
            f[k][v] += 1
    return {"families": fams, "same_as_base_diffs": diffs,
            "question_write_violations": qwrite_viol}


# verdict index: 0 right, 1 wrong, 2 abstain
def verdict(c, rows):
    fam = c["family"]
    if fam in ("save", "ask1"):
        ok = True
        for idx, how, text in c["checks"]:
            rep = rows[idx]["reply"] if idx < len(rows) else ""
            has = text in rep
            if how == "has" and not has:
                ok = False
            if how == "not" and has:
                ok = False
        if c["expect_store"] is not None:
            if sorted(map(list, rows[-1]["triples"])) != sorted(c["expect_store"]):
                ok = False
        return 0 if ok else 1
    if fam == "twohop":
        rep = rows[-1]["reply"]
        ev = rows[-1]["ev"]
        if c["target"] in rep:
            return 0
        if (is_clarify(rep) or is_dontknow(rep)) and ev == 0:
            return 2
        return 1
    if fam == "correct":
        triples = [list(t) for t in rows[-1]["triples"]]
        if list(c["target"]) in triples:
            return 0
        if (is_clarify(rows[-1]["reply"]) or is_dontknow(rows[-1]["reply"])) \
                and triples == [list(c["orig"])]:
            return 2
        return 1
    if fam == "forget":
        triples = [list(t) for t in rows[-1]["triples"]]
        subj = c["target"][0]
        if not any(t[0] == subj for t in triples):
            return 0
        rep = rows[-1]["reply"]
        if (is_clarify(rep) or is_dontknow(rep)) and triples == [list(t) for t in rows[0]["triples"]]:
            return 2
        return 1
    if fam == "abstain":
        rep = rows[-1]["reply"]
        ev = rows[-1]["ev"]
        if is_dontknow(rep) and ev == 0:
            return 0
        if is_clarify(rep) and ev == 0:
            return 2
        return 1
    if fam == "source":
        rep = rows[-1]["reply"]
        ev = rows[-1]["ev"]
        r = low(rep)
        if ev == 0 and "you" in r and any(
                w in r for w in ("taught", "told", "said", "learned",
                                 "learnt", "heard", "know")) and not is_dontknow(rep):
            return 0
        if (is_clarify(rep) or is_dontknow(rep)) and ev == 0:
            return 2
        return 1
    return 1


def score_capab(cases, run280):
    r80 = {c["id"]: c for c in run280}
    out = []
    for c in cases:
        if c["family"] != "capab":
            continue
        rows = r80[c["id"]]["rows"]
        for row in rows:
            turn, rep = row.get("turn", ""), row.get("reply", "")
            kind = classify_turn(c, turn)
            fh = forbidden_hits(rep)
            out.append({"id": c["id"], "kind": kind,
                        "kw": ability_kw_count(rep),
                        "forbidden": fh, "ev": row.get("ev", 0)})
    return out


def classify_turn(case, turn):
    t = low(turn)
    if "not do" in t or "n't do" in t or "cannot" in t or "can't" in t:
        return "cant"
    if t.startswith("can you"):
        return "canyou"
    return "general"


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.load(open(argv[2]))
        run260 = json.load(open(argv[3]))
        run280 = json.load(open(argv[4]))
        outp = argv[5]
        res = score_dev(cases, run260, run280)
        res["capab280"] = score_capab(cases, run280)
        json.dump(res, open(outp, "w"), indent=1)
        for fam, f in res["families"].items():
            n = f["n"]
            print(f"{fam:8s} n={n} 260 R/W/A={f['r60']} W={f['w60']} | "
                  f"280 R/W/A={f['r80']} W={f['w80']}")
        print("same_as_base diffs:", len(res["same_as_base_diffs"]))
        for d in res["same_as_base_diffs"][:20]:
            print("  DIFF", d[0], repr((d[1] or "")[:80]))
        print("question-write violations:", res["question_write_violations"])
        gen = [r for r in res["capab280"] if r["kind"] == "general"]
        print(f"capab general on 280: {len(gen)} turns, "
              f"kw>=3: {sum(1 for r in gen if r['kw'] >= 3)}/{len(gen)}, "
              f"forbidden hits: {sum(1 for r in gen if r['forbidden'])}")
        for r in res["capab280"]:
            if r["forbidden"] or (r["kind"] == "general" and r["kw"] < 3):
                print("  CAPAB-MISS", r)
        return 0
    if mode == "panel":
        return panel_main(argv[2:])
    print("unknown mode", mode)
    return 2


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


def panel_group(items):
    """Group flat turn rows ({dialog_id, turn_index, user_text, category})
    into dialogs. Returns list of (setup[], turn, followup, family, id)
    with the scored turn = last row of each dialog. Items already shaped
    {id, setup[], turn, followup} or {id, turns[]} pass through panel_turns.
    The writer's 'gold' column, if present, is never read here."""
    if items and isinstance(items[0], dict) and "dialog_id" in items[0]:
        by = {}
        for r in items:
            by.setdefault(r["dialog_id"], []).append(r)
        out = []
        for did in sorted(by):
            rows = sorted(by[did], key=lambda r: r.get("turn_index", 0))
            setup = [r["user_text"] for r in rows[:-1]]
            last = rows[-1]
            out.append((setup, last["user_text"], None,
                        last.get("category", ""), did))
        return out
    return [panel_turns(it) for it in items]


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


def panel_main(args):
    panelp, r260p, r280p, outp = args[:4]
    grouped = panel_group(load_panel_items(panelp))

    def load_rows(p):
        txt = open(p).read().strip()
        if p.endswith(".jsonl"):
            return [json.loads(x) for x in txt.split("\n") if x.strip()]
        doc = json.load(open(p))
        return doc if isinstance(doc, list) else doc.get("rows", doc)
    r60 = {r["id"]: r for r in load_rows(r260p)}
    r80 = {r["id"]: r for r in load_rows(r280p)}
    rows = []
    for setup, turn, foll, fam, iid in grouped:
        a = r60[iid]
        b = r80[iid]
        fl = str(fam or "").lower()
        compact = fl.replace(" ", "").replace("-", "").replace("_", "")
        if "general" in fl or "abil" in fl or "cando" in compact:
            kind = "general"
        elif "canyou" in compact:
            kind = "canyou"
        elif "control" in fl:
            kind = "control"
        else:
            t = turn if isinstance(turn, str) else ""
            kind = classify_turn({}, t)
            if kind not in ("general", "canyou", "cant"):
                kind = "control"
        brep = b.get("turn_reply", b.get("reply", ""))
        arep = a.get("turn_reply", a.get("reply", ""))
        fh = forbidden_hits(brep)
        wt60, wt80 = a.get("writes_turn", 0), b.get("writes_turn", 0)
        wf60, wf80 = a.get("writes_followup", 0), b.get("writes_followup", 0)
        t = turn if isinstance(turn, str) else ""
        qturn = t.strip().endswith("?") or kind in ("general", "canyou", "cant")
        rows.append({"id": iid, "kind": kind, "kw": ability_kw_count(brep),
                     "forbidden": fh, "writes_turn60": wt60,
                     "writes_turn80": wt80, "writes_fol60": wf60,
                     "writes_fol80": wf80, "qturn": qturn,
                     "f60": forbidden_hits(arep)})
    m1a_miss = [r["id"] for r in rows if r["forbidden"]]
    gen = [r for r in rows if r["kind"] == "general"]
    m1b_miss = [r["id"] for r in gen if r["kw"] < 3]
    m3_wdiff = [r["id"] for r in rows
                if r["writes_turn80"] != r["writes_turn60"]
                or r["writes_fol80"] != r["writes_fol60"]]
    m3_qwrite = [r["id"] for r in rows
                 if r["qturn"] and (r["writes_turn80"] or r["writes_fol80"])]
    res = {"n": len(rows), "n_general": len(gen),
           "M1a_forbidden_280": len(m1a_miss), "M1a_ids": m1a_miss,
           "M1a_forbidden_260": sum(1 for r in rows if r["f60"]),
           "M1b_general_kwlt3": len(m1b_miss), "M1b_ids": m1b_miss,
           "M3_write_diffs": len(m3_wdiff), "M3_wdiff_ids": m3_wdiff,
           "M3_qwrites_280": len(m3_qwrite), "M3_qwrite_ids": m3_qwrite,
           "rows": rows}
    json.dump(res, open(outp, "w"), indent=1)
    print(f"panel n={len(rows)} general={len(gen)}")
    print(f"M1a forbidden-on-280: {len(m1a_miss)} {m1a_miss} "
          f"(260 arm: {res['M1a_forbidden_260']})")
    print(f"M1b general kw<3: {len(m1b_miss)} {m1b_miss}")
    print(f"M3 write diffs 280vs260: {len(m3_wdiff)} {m3_wdiff}")
    print(f"M3 question/self writes on 280: {len(m3_qwrite)} {m3_qwrite}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
