#!/usr/bin/env python3
"""Exp 280b dev scorer + blind-panel scorer (mechanical counts only).

  dev <cases.json> <run280.json> <run280b.json> <out.json>
    general turns: 280b reply must equal the sealed CAN280 text exactly
      (duplicated below; the scorer never imports agent code).
    canyou / nearmiss / control / ability turns: 280b reply must equal
      280's reply byte-identically (diffs listed). Question-turn writes
      flagged. Never prints item text beyond ids and counts.

  panel <panel.jsonl|json> <run280.json> <run280b.json> <out.json>
    Schema gate first: every row must carry dialog_id, turn_index and
    user_text; (dialog_id, turn_index) unique; scored turn = last row
    of each dialog. On any violation: print SCHEMA-MISMATCH, exit 3,
    no verdict (that run is VOID, not FAIL). The writer's gold column,
    if present, is never read. Mechanical counts only:
      M1gen: every general item's 280b reply == CAN280 exactly.
      M1a: 0 unsupported-claim replies on 280b (old-sheet scan).
      M1xy: canyou/nearmiss/control items byte-identical 280b vs 280.
      M3: 0 notebook write diffs; 0 question/self-turn writes on 280b.
    Prints ids of misses, never item text.
"""

import json
import sys

# Sealed CAN280 text, duplicated from scripts/claude_fix280_capab.py so
# the scorer never imports agent code.
CAN280B_SEALED = (
    "I can: save what you teach me in my notebook; "
    "answer one-step questions from my notes, like 'Where does Tavish live?'; "
    "correct a fact if you say it like 'No, Mira's city is York'; "
    "forget a fact if you say it like 'Forget Quinn's cat'; "
    "follow two steps if you ask like 'Who is Nils's boss's boss?'; "
    "and say I do not know instead of guessing. "
    "I can't yet answer mixed two-fact questions like "
    "'Where does Quill's boss live?', forget things you phrase any other "
    "way, or tell you where a fact came from."
)

FORBIDDEN280B = (
    "one or two steps",
    "following one or two",
    "correct a fact or forget",
    "forget one when you ask",
    "answer questions from my notes, following",
)


def low(s):
    return " ".join(str(s).lower().split())


def forbidden_hits(reply):
    r = low(reply)
    return [p for p in FORBIDDEN280B if p in r]


# ---------------- panel schema ----------------

def load_panel_items(path):
    txt = open(path).read().strip()
    if path.endswith(".jsonl"):
        return [json.loads(x) for x in txt.split("\n") if x.strip()]
    doc = json.load(open(path))
    if isinstance(doc, list):
        return doc
    for k in ("items", "dialogs", "cases", "panel", "rows"):
        if k in doc and isinstance(doc[k], list):
            return doc[k]
    print("SCHEMA-MISMATCH: no item list found")
    raise SystemExit(3)


def check_schema(items, src="<panel>"):
    if not items:
        print("SCHEMA-MISMATCH: empty panel")
        raise SystemExit(3)
    seen = set()
    for n, r in enumerate(items):
        if not isinstance(r, dict):
            print(f"SCHEMA-MISMATCH: row {n} not an object")
            raise SystemExit(3)
        for f in ("dialog_id", "turn_index", "user_text"):
            if f not in r:
                print(f"SCHEMA-MISMATCH: row {n} missing field {f}")
                raise SystemExit(3)
        try:
            ti = int(r["turn_index"])
        except (TypeError, ValueError):
            print(f"SCHEMA-MISMATCH: row {n} bad turn_index")
            raise SystemExit(3)
        key = (str(r["dialog_id"]), ti)
        if key in seen:
            print(f"SCHEMA-MISMATCH: duplicate {key}")
            raise SystemExit(3)
        seen.add(key)
        if not isinstance(r["user_text"], str):
            print(f"SCHEMA-MISMATCH: row {n} user_text not a string")
            raise SystemExit(3)
    return True


def panel_group(items):
    """Group flat turn rows into dialogs. Returns list of
    (setup[], turn, followup_or_None, family, id); scored turn = last
    row of each dialog ordered by turn_index. Gold never read."""
    by = {}
    for r in items:
        by.setdefault(str(r["dialog_id"]), []).append(r)
    out = []
    for did in sorted(by):
        rows = sorted(by[did], key=lambda r: int(r["turn_index"]))
        setup = [r["user_text"] for r in rows[:-1]]
        last = rows[-1]
        out.append((setup, last["user_text"], None,
                    last.get("category", last.get("family", "")), did))
    return out


def classify(fam, turn):
    fl = str(fam or "").lower().replace("_", "").replace("-", "")
    if "general" in fl or "abil" in fl:
        return "general"
    if "canyou" in fl or ("can" in fl and "you" in fl):
        return "canyou"
    if "near" in fl or "miss" in fl:
        return "nearmiss"
    if "control" in fl:
        return "control"
    t = low(turn)
    if t.startswith("can you") or t.startswith("can u"):
        return "canyou"
    return "control"


# ---------------- dev ----------------

def score_dev(cases, run280, run280b):
    r80 = {c["id"]: c for c in run280}
    r8b = {c["id"]: c for c in run280b}
    fams = {}
    diffs = []
    gen_miss = []
    qwrite_viol = []
    for c in cases:
        fam = c["family"]
        f = fams.setdefault(fam, {"n": 0, "same": 0, "moved": 0,
                                  "w80": 0, "w8b": 0})
        f["n"] += 1
        a = r80[c["id"]]
        b = r8b.get(c["id"])
        for i, (ra, rb) in enumerate(zip(a["rows"], b["rows"])):
            if ra.get("ev", 0):
                f["w80"] += 1
            if rb.get("ev", 0):
                f["w8b"] += 1
                if str(ra.get("turn", "")).strip().endswith("?"):
                    qwrite_viol.append((c["id"], i))
            if ra.get("reply") == rb.get("reply"):
                f["same"] += 1
            else:
                f["moved"] += 1
                diffs.append((c["id"], i, fam))
        if fam == "general":
            last = b["rows"][-1]["reply"] if b["rows"] else ""
            if last != CAN280B_SEALED:
                gen_miss.append(c["id"])
    return {"families": fams, "general_miss": gen_miss,
            "non_general_diffs": [d for d in diffs if d[2] != "general"],
            "general_noncanon": [d for d in diffs if d[2] == "general"
                                 and d[0] not in gen_miss
                                 and r80[d[0]]["rows"][d[1]]["reply"]
                                 != CAN280B_SEALED],
            "question_write_violations": qwrite_viol}


# ---------------- panel ----------------

def panel_main(args):
    panelp, r280p, r28bp, outp = args[:4]
    items = load_panel_items(panelp)
    check_schema(items, panelp)
    grouped = panel_group(items)

    def load_rows(p):
        txt = open(p).read().strip()
        if p.endswith(".jsonl"):
            return [json.loads(x) for x in txt.split("\n") if x.strip()]
        doc = json.load(open(p))
        return doc if isinstance(doc, list) else doc.get("rows", doc)
    r0 = {r["id"]: r for r in load_rows(r280p)}
    r1 = {r["id"]: r for r in load_rows(r28bp)}
    rows = []
    for setup, turn, foll, fam, iid in grouped:
        if iid not in r0 or iid not in r1:
            print(f"SCHEMA-MISMATCH: dialog {iid} missing from a run file")
            raise SystemExit(3)
        a, b = r0[iid], r1[iid]
        kind = classify(fam, turn if isinstance(turn, str) else "")
        brep = b.get("turn_reply", b.get("reply", ""))
        arep = a.get("turn_reply", a.get("reply", ""))
        wt0, wt1 = a.get("writes_turn", 0), b.get("writes_turn", 0)
        wf0, wf1 = a.get("writes_followup", 0), b.get("writes_followup", 0)
        t = turn if isinstance(turn, str) else ""
        qturn = t.strip().endswith("?") or kind in ("general", "canyou")
        rows.append({"id": iid, "kind": kind,
                     "canon": brep == CAN280B_SEALED,
                     "same": brep == arep,
                     "forbidden": forbidden_hits(brep),
                     "f280": forbidden_hits(arep),
                     "writes_turn280": wt0, "writes_turn280b": wt1,
                     "writes_fol280": wf0, "writes_fol280b": wf1,
                     "qturn": bool(qturn)})
    gen = [r for r in rows if r["kind"] == "general"]
    cy = [r for r in rows if r["kind"] == "canyou"]
    nm = [r for r in rows if r["kind"] == "nearmiss"]
    ct = [r for r in rows if r["kind"] == "control"]
    m_gen_miss = [r["id"] for r in gen if not r["canon"]]
    m_forbid = [r["id"] for r in rows if r["forbidden"]]
    m_cy_move = [r["id"] for r in cy if not r["same"]]
    m_nm_move = [r["id"] for r in nm if not r["same"]]
    m_ct_move = [r["id"] for r in ct if not r["same"]]
    m_wdiff = [r["id"] for r in rows
               if r["writes_turn280b"] != r["writes_turn280"]
               or r["writes_fol280b"] != r["writes_fol280"]]
    m_qwrite = [r["id"] for r in rows
                if r["qturn"] and (r["writes_turn280b"]
                                   or r["writes_fol280b"])]
    res = {"n": len(rows), "n_general": len(gen), "n_canyou": len(cy),
           "n_nearmiss": len(nm), "n_control": len(ct),
           "M1gen_noncanon": len(m_gen_miss), "M1gen_ids": m_gen_miss,
           "M1a_forbidden_280b": len(m_forbid), "M1a_ids": m_forbid,
           "M1a_forbidden_280": sum(1 for r in rows if r["f280"]),
           "M1_canyou_moves": len(m_cy_move), "M1_canyou_ids": m_cy_move,
           "M1_nearmiss_moves": len(m_nm_move),
           "M1_nearmiss_ids": m_nm_move,
           "M1_control_moves": len(m_ct_move), "M1_control_ids": m_ct_move,
           "M3_write_diffs": len(m_wdiff), "M3_wdiff_ids": m_wdiff,
           "M3_qwrites_280b": len(m_qwrite), "M3_qwrite_ids": m_qwrite,
           "rows": rows}
    json.dump(res, open(outp, "w"), indent=1)
    print(f"panel n={len(rows)} general={len(gen)} canyou={len(cy)} "
          f"nearmiss={len(nm)} control={len(ct)}")
    print(f"M1gen non-canon: {len(m_gen_miss)} {m_gen_miss}")
    print(f"M1a forbidden-on-280b: {len(m_forbid)} {m_forbid} "
          f"(280 arm: {res['M1a_forbidden_280']})")
    print(f"M1 canyou moves: {len(m_cy_move)} {m_cy_move}")
    print(f"M1 nearmiss moves: {len(m_nm_move)} {m_nm_move}")
    print(f"M1 control moves: {len(m_ct_move)} {m_ct_move}")
    print(f"M3 write diffs: {len(m_wdiff)} {m_wdiff}")
    print(f"M3 question/self writes on 280b: {len(m_qwrite)} {m_qwrite}")
    return 0


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.load(open(argv[2]))
        run280 = json.load(open(argv[3]))
        run280b = json.load(open(argv[4]))
        outp = argv[5]
        res = score_dev(cases, run280, run280b)
        json.dump(res, open(outp, "w"), indent=1)
        for fam, f in res["families"].items():
            print(f"{fam:9s} n={f['n']} same={f['same']} "
                  f"moved={f['moved']} W280={f['w80']} W280b={f['w8b']}")
        print("general non-canon:", res["general_miss"])
        print("non-general diffs:", res["non_general_diffs"])
        print("question-write violations:",
              res["question_write_violations"])
        return 0
    if mode == "panel":
        return panel_main(argv[2:])
    print("unknown mode", mode)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
