#!/usr/bin/env python3
"""Exp 263 scorer.

  dev   <devcases.json> <rows263.json> <rows260.json> [out.json]
  panel <panel_dir> <rows263.jsonl> <rows260.jsonl> [out.json]
  schema <panel_dir>          (schema check only; SCHEMA OK or exit 3)

panel implements commapanel263-spec.txt: the same 10 panel fields and 10
base-row fields as openpanel260, ids c263-001..c263-060, families
unlisted_opener_teach 20 / appositive_subject 10 / comma_value_ok 8 /
question 8 / control 14. Judgement rules follow openpanel260-spec.txt
(normalise = lowercase + strip edge punctuation/spaces; junk = any triple
stored after the turn or followup that is in neither stored_after_setup
nor expect_store; store_ok = expect_store subset stored_after_turn and
nothing else added; question_write = a question turn or the followup
changes the store; reply_ok = gold "" or gold subset scored reply).
The schema is checked when the panel loads, before anything is scored:
any missing/unexpected file, field, id, family or count prints
SCHEMA-MISMATCH and exits with code 3 (no verdict: the run is VOID).
"""
import json
import sys
from pathlib import Path


def norm(s) -> str:
    return str(s).lower().strip().strip(" \t\n.,;:!?'\"()").strip()


def ntrip(t):
    return tuple(norm(x) for x in t)


def comma_subjects(triples):
    return [t for t in triples if "," in str(t[0])]


# ------------------------------------------------------------------ dev
def score_dev(cases, rows, base_rows):
    byid = {r["id"]: r for r in rows}
    bb = {r["id"]: r for r in base_rows}
    res, fam = [], {}
    for c in cases:
        r, b = byid[c["id"]], bb.get(c["id"])
        turns = [x for x in r["rows"] if not x.get("restart")]
        why = []
        if c["expect_store"] is not None:
            want = sorted(ntrip(t) for t in c["expect_store"])
            got = sorted(ntrip(t) for t in r["stored"])
            if want != got:
                why.append(f"store {got} != {want}")
        for idx, kind, text in c["checks"]:
            rep = turns[idx]["reply"] if idx < len(turns) else ""
            has = text.lower() in rep.lower()
            if (kind == "has") != has:
                why.append(f"t{idx} {kind} {text!r}: {rep!r}")
        for x in turns:
            if x["turn"].rstrip().endswith("?") and x["ev"] != 0:
                why.append(f"question wrote: {x['turn']!r}")
        cs = comma_subjects(r["stored"])
        if cs:
            why.append(f"comma_subject {cs}")
        if c["same_as_base"]:
            if b is None:
                why.append("no base row")
            else:
                bt = [x for x in b["rows"] if not x.get("restart")]
                if [x["reply"] for x in bt] != [x["reply"] for x in turns]:
                    why.append("differs from base")
        ok = not why
        res.append({"id": c["id"], "family": c["family"], "right": ok,
                    "why": why, "comma_subjects": len(cs)})
        f = fam.setdefault(c["family"], [0, 0])
        f[0] += ok
        f[1] += 1
    return res, fam


# ------------------------------------------------------------------ panel
PANEL_FILES = ("panel.jsonl", "base260.jsonl", "make_panel.py",
               "run_base.py", "README.md", "SEAL.sha256.txt")
PANEL_FIELDS = ("id", "family", "setup", "turn", "followup", "stated_facts",
                "expect_store", "gold", "plain_turn", "note")
BASE_FIELDS = ("id", "setup_replies", "stored_after_setup", "turn_reply",
               "stored_after_turn", "followup_reply",
               "stored_after_followup", "plain_reply", "base_right",
               "base_junk")
FAMILIES = {"unlisted_opener_teach": 20, "appositive_subject": 10,
            "comma_value_ok": 8, "question": 8, "control": 14}
TEACH_FAMS = ("unlisted_opener_teach", "comma_value_ok", "appositive_subject")


def mismatch(msg):
    print(f"SCHEMA-MISMATCH: {msg}", flush=True)
    sys.exit(3)


def _triples_ok(v):
    return isinstance(v, list) and all(
        isinstance(t, list) and len(t) == 3 and
        all(isinstance(x, str) for x in t) for t in v)


def load_panel(pdir: Path):
    for f in PANEL_FILES:
        if not (pdir / f).is_file():
            mismatch(f"missing file {f}")
    try:
        items = [json.loads(x) for x in (pdir / "panel.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
        base = [json.loads(x) for x in (pdir / "base260.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
    except json.JSONDecodeError as e:
        mismatch(f"bad json: {e}")
    if len(items) != 60:
        mismatch(f"panel has {len(items)} items, want 60")
    if len(base) != 60:
        mismatch(f"base260 has {len(base)} rows, want 60")
    want_ids = [f"c263-{i:03d}" for i in range(1, 61)]
    for it in items:
        if not isinstance(it, dict) or set(it) != set(PANEL_FIELDS):
            mismatch(f"panel fields {sorted(it) if isinstance(it, dict) else it}")
    for b in base:
        if not isinstance(b, dict) or set(b) != set(BASE_FIELDS):
            mismatch(f"base fields {sorted(b) if isinstance(b, dict) else b}")
    if [it["id"] for it in items] != want_ids:
        mismatch("panel ids are not c263-001..c263-060 in order")
    if sorted(b["id"] for b in base) != want_ids:
        mismatch("base ids do not match c263-001..c263-060")
    fams = {}
    for it in items:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    if fams != FAMILIES:
        mismatch(f"family counts {fams} != {FAMILIES}")
    for it in items:
        if not (isinstance(it["setup"], list)
                and all(isinstance(x, str) for x in it["setup"])):
            mismatch(f"{it['id']} setup")
        for k in ("turn", "followup", "gold", "plain_turn", "note"):
            if not isinstance(it[k], str):
                mismatch(f"{it['id']} {k} not a string")
        if not it["turn"]:
            mismatch(f"{it['id']} empty turn")
        for k in ("stated_facts", "expect_store"):
            if not _triples_ok(it[k]):
                mismatch(f"{it['id']} {k} not a list of 3-string lists")
    return items, {b["id"]: b for b in base}


def question_turn(it) -> bool:
    return it["family"] == "question" or it["turn"].rstrip().endswith("?")


def score_item(it, row, base_row):
    s_setup = {ntrip(t) for t in row["stored_after_setup"]}
    s_turn = {ntrip(t) for t in row["stored_after_turn"]}
    s_f = {ntrip(t) for t in row["stored_after_followup"]}
    expect = {ntrip(t) for t in it["expect_store"]}
    junk_set = {t for t in (s_turn | s_f) if t not in s_setup
                and t not in expect}
    junk = bool(junk_set)
    added = s_turn - s_setup
    store_ok = expect <= s_turn and added <= expect
    qw = False
    if question_turn(it) and s_turn != s_setup:
        qw = True
    if it["followup"] and s_f != s_turn:
        qw = True
    fam = it["family"]
    if fam == "question":
        scored = row["turn_reply"]
    elif fam in TEACH_FAMS:
        scored = row["followup_reply"]
    else:
        scored = row["followup_reply"] if it["followup"] else row["turn_reply"]
    gold = norm(it["gold"])
    reply_ok = gold == "" or gold in norm(scored)
    comma_n = sum(1 for t in (s_turn | s_f)
                  if "," in str(list(t)[0]) and t not in s_setup)
    ident = None
    if fam in TEACH_FAMS or fam == "appositive_subject":
        right = store_ok and reply_ok and not junk and not qw
    elif fam == "question":
        right = reply_ok and not qw and not junk
    else:  # control
        if question_turn(it):
            shape = reply_ok and not qw and not junk
        else:
            shape = store_ok and reply_ok and not junk and not qw
        ident = (row["setup_replies"] == base_row["setup_replies"]
                 and row["turn_reply"] == base_row["turn_reply"]
                 and row["followup_reply"] == base_row["followup_reply"])
        right = shape and ident
    return {"id": it["id"], "family": fam, "right": bool(right),
            "junk": sorted(junk_set), "question_write": qw,
            "store_ok": store_ok, "reply_ok": reply_ok,
            "comma_subjects": comma_n, "identical": ident}


def score_panel(pdir, rows_new, rows_m):
    items, base = load_panel(Path(pdir))
    out = {}
    for arm, rows in (("263", rows_new), ("260", rows_m)):
        rb = {r["id"]: r for r in rows}
        if sorted(rb) != sorted(base):
            print(f"arm {arm}: rows do not cover the 60 ids", flush=True)
            sys.exit(2)
        out[arm] = [score_item(it, rb[it["id"]], base[it["id"]])
                    for it in items]
    return items, base, out


def tally(res):
    fam = {}
    for r in res:
        f = fam.setdefault(r["family"], [0, 0])
        f[0] += r["right"]
        f[1] += 1
    return fam


def panel_marks(items, out):
    n, m = out["263"], out["260"]
    fn, fm = tally(n), tally(m)
    cn = sum(r["comma_subjects"] for r in n)
    cm = sum(r["comma_subjects"] for r in m)
    qn = sum(1 for r in n if r["question_write"])
    qm = sum(1 for r in m if r["question_write"])
    cvn = [r["id"] for r in n if r["family"] == "comma_value_ok"
           and not r["right"]]
    mb = {r["id"]: r for r in m}
    cv_lost = [i for i in cvn if mb[i]["right"]]
    ctrl_ident_n = sum(1 for r in n if r["family"] == "control"
                       and r["identical"])
    marks = [
        ("0 comma subjects over 60", cn == 0, cn, cm),
        ("unlisted_opener_teach >= 16/20 exact",
         fn["unlisted_opener_teach"][0] >= 16,
         fn["unlisted_opener_teach"], fm["unlisted_opener_teach"]),
        ("comma_value_ok 0 lost vs 260", not cv_lost,
         fn["comma_value_ok"] + [f"lost {cv_lost}"],
         fm["comma_value_ok"]),
        ("question 0 writes", qn == 0, qn, qm),
        ("control 14/14 byte-identical",
         fn["control"][0] == 14 and ctrl_ident_n == 14,
         fn["control"] + [f"identical {ctrl_ident_n}"],
         fm["control"]),
    ]
    return marks


ROW_FIELDS = ("setup_replies", "stored_after_setup", "turn_reply",
              "stored_after_turn", "followup_reply", "stored_after_followup")


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        rows = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        base = json.loads(Path(argv[4]).read_text(encoding="utf-8"))
        res, fam = score_dev(cases, rows, base)
        bres, bfam = score_dev(cases, base, base)
        for k in fam:
            print(f"{k:16s} 263 {fam[k][0]}/{fam[k][1]}   "
                  f"260 {bfam[k][0]}/{bfam[k][1]}")
        tot = sum(v[0] for v in fam.values())
        btot = sum(v[0] for v in bfam.values())
        print(f"TOTAL 263 {tot}/{len(res)}  260 {btot}/{len(res)}")
        for r in res:
            if not r["right"]:
                print("MISS", r["id"], r["family"], r["why"])
        if len(argv) > 5:
            Path(argv[5]).write_text(json.dumps(
                {"263": res, "260": bres, "fam263": fam, "fam260": bfam},
                indent=1), encoding="utf-8")
        return 0
    if mode == "panel":
        rows_n = [json.loads(x) for x in Path(argv[3]).read_text(
            encoding="utf-8").splitlines() if x.strip()]
        rows_m = [json.loads(x) for x in Path(argv[4]).read_text(
            encoding="utf-8").splitlines() if x.strip()]
        items, base, out = score_panel(argv[2], rows_n, rows_m)
        print("SCHEMA OK")
        marks = panel_marks(items, out)
        allpass = True
        for name, ok, a, b in marks:
            allpass &= bool(ok)
            print(f"{'PASS' if ok else 'FAIL'}  {name:42s} 263={a}  260={b}")
        rb = {r["id"]: r for r in rows_m}
        diff = [i for i in base if any(
            rb[i][k] != base[i][k] for k in ROW_FIELDS)]
        print(f"260 arm vs base260.jsonl: {60 - len(diff)}/60 identical "
              f"{diff}")
        for arm in ("263", "260"):
            for r in out[arm]:
                if not r["right"]:
                    print(f"MISS {arm} {r['id']} {r['family']} "
                          f"store_ok={r['store_ok']} reply_ok={r['reply_ok']} "
                          f"junk={len(r['junk'])} qw={r['question_write']} "
                          f"comma={r['comma_subjects']} ident={r['identical']}")
        print("M1:", "PASS" if allpass else "FAIL")
        if len(argv) > 5:
            Path(argv[5]).write_text(json.dumps(
                {"marks": [[a, bool(b), c, d] for a, b, c, d in marks],
                 "pass": allpass, "rows": out, "fidelity_diff": diff},
                indent=1, default=str), encoding="utf-8")
        return 0
    if mode == "schema":
        load_panel(Path(argv[2]))
        print("SCHEMA OK")
        return 0
    raise SystemExit("mode must be dev, panel or schema")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
