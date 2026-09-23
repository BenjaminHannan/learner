#!/usr/bin/env python3
"""Exp 260 scorer.

  dev   <devcases.json> <rows260.json> <rows138m.json> [out.json]
  panel <panel_dir> <rows260.jsonl> <rows138m.jsonl> [out.json]
  schema <panel_dir>          (schema check only; SCHEMA OK or exit 3)

panel implements openpanel260-spec.txt exactly. The schema is checked when
the panel loads, before anything is scored: any missing/unexpected file,
field, id, family or count prints SCHEMA-MISMATCH and exits with code 3
(no verdict: the run is VOID).
"""
import json
import re
import sys
from pathlib import Path

JUNK_OPENER_RE = None  # set from the fix module (same closed list)


def _junk_re():
    global JUNK_OPENER_RE
    if JUNK_OPENER_RE is None:
        sys.path.insert(0, "scripts")
        import claude_fix260_openers as F  # noqa: E402 (read-only)
        JUNK_OPENER_RE = F.is_junk_subject260
    return JUNK_OPENER_RE


def norm(s) -> str:
    return str(s).lower().strip().strip(" \t\n.,;:!?'\"()").strip()


def ntrip(t):
    return tuple(norm(x) for x in t)


# ------------------------------------------------------------------ dev
def score_dev(cases, rows, base_rows):
    is_junk = _junk_re()
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
        junk = [t for t in r["stored"] if is_junk(t[0])]
        if junk:
            why.append(f"junk {junk}")
        if c["same_as_base"]:
            if b is None:
                why.append("no base row")
            else:
                bt = [x for x in b["rows"] if not x.get("restart")]
                if [x["reply"] for x in bt] != [x["reply"] for x in turns]:
                    why.append("differs from base")
        ok = not why
        res.append({"id": c["id"], "family": c["family"], "right": ok,
                    "why": why, "junk": len(junk)})
        f = fam.setdefault(c["family"], [0, 0])
        f[0] += ok
        f[1] += 1
    return res, fam


# ------------------------------------------------------------------ panel
PANEL_FILES = ("panel.jsonl", "base138m.jsonl", "make_panel.py",
               "run_base.py", "README.md", "SEAL.sha256.txt")
PANEL_FIELDS = ("id", "family", "setup", "turn", "followup", "stated_facts",
                "expect_store", "gold", "plain_turn", "note")
BASE_FIELDS = ("id", "setup_replies", "stored_after_setup", "turn_reply",
               "stored_after_turn", "followup_reply",
               "stored_after_followup", "plain_reply", "base_right",
               "base_junk")
FAMILIES = {"opener_teach": 20, "opener_question": 12,
            "greeting_question": 8, "bare_greeting": 6, "name_trap": 10,
            "junk_guard": 8, "control": 16}
QUESTION_FAMS = ("opener_question", "greeting_question")
TEACH_FAMS = ("opener_teach", "junk_guard", "name_trap")
BAD_GREETING_WORDS = ("save", "understand", "couldn't", "could not",
                      "don't know", "not sure")


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
        base = [json.loads(x) for x in (pdir / "base138m.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
    except json.JSONDecodeError as e:
        mismatch(f"bad json: {e}")
    if len(items) != 80:
        mismatch(f"panel has {len(items)} items, want 80")
    if len(base) != 80:
        mismatch(f"base138m has {len(base)} rows, want 80")
    want_ids = [f"o260-{i:03d}" for i in range(1, 81)]
    for it in items:
        if not isinstance(it, dict) or set(it) != set(PANEL_FIELDS):
            mismatch(f"panel fields {sorted(it) if isinstance(it, dict) else it}")
    for b in base:
        if not isinstance(b, dict) or set(b) != set(BASE_FIELDS):
            mismatch(f"base fields {sorted(b) if isinstance(b, dict) else b}")
    if [it["id"] for it in items] != want_ids:
        mismatch("panel ids are not o260-001..o260-080 in order")
    if sorted(b["id"] for b in base) != want_ids:
        mismatch("base ids do not match o260-001..o260-080")
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
    return it["family"] in QUESTION_FAMS or it["turn"].rstrip().endswith("?")


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
    if fam in QUESTION_FAMS:
        scored = row["turn_reply"]
    elif fam in TEACH_FAMS:
        scored = row["followup_reply"]
    else:
        scored = row["followup_reply"] if it["followup"] else row["turn_reply"]
    gold = norm(it["gold"])
    reply_ok = gold == "" or gold in norm(scored)
    ident = None
    if fam in TEACH_FAMS:
        right = store_ok and reply_ok and not junk and not qw
    elif fam in QUESTION_FAMS:
        right = reply_ok and not qw and not junk
    elif fam == "bare_greeting":
        low = row["turn_reply"].lower()
        right = (s_turn == s_setup and s_f == s_setup
                 and not any(w in low for w in BAD_GREETING_WORDS))
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
            "store_ok": store_ok, "reply_ok": reply_ok, "identical": ident}


def score_panel(pdir, rows_new, rows_m):
    items, base = load_panel(Path(pdir))
    out = {}
    for arm, rows in (("260", rows_new), ("138m", rows_m)):
        rb = {r["id"]: r for r in rows}
        if sorted(rb) != sorted(base):
            print(f"arm {arm}: rows do not cover the 80 ids", flush=True)
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
    n, m = out["260"], out["138m"]
    fn, fm = tally(n), tally(m)
    jn = sum(1 for r in n if r["junk"])
    jm = sum(1 for r in m if r["junk"])
    qn = sum(1 for r in n if r["question_write"])
    qm = sum(1 for r in m if r["question_write"])
    jg_junk_n = sum(1 for r in n if r["family"] == "junk_guard" and r["junk"])
    jg_junk_m = sum(1 for r in m if r["family"] == "junk_guard" and r["junk"])
    mb = {r["id"]: r for r in m}
    newly_wrong = [r["id"] for r in n if r["family"] == "name_trap"
                   and not r["right"] and mb[r["id"]]["right"]]
    ctrl_ident_n = sum(1 for r in n if r["family"] == "control"
                       and r["identical"])
    ctrl_ident_m = sum(1 for r in m if r["family"] == "control"
                       and r["identical"])
    marks = [
        ("opener_teach >= 16/20", fn["opener_teach"][0] >= 16,
         fn["opener_teach"], fm["opener_teach"]),
        ("opener_question >= 10/12", fn["opener_question"][0] >= 10,
         fn["opener_question"], fm["opener_question"]),
        ("greeting_question >= 7/8", fn["greeting_question"][0] >= 7,
         fn["greeting_question"], fm["greeting_question"]),
        ("bare_greeting >= 5/6", fn["bare_greeting"][0] >= 5,
         fn["bare_greeting"], fm["bare_greeting"]),
        ("junk_guard 8/8 with 0 junk",
         fn["junk_guard"][0] == 8 and jg_junk_n == 0,
         fn["junk_guard"] + [f"junk {jg_junk_n}"],
         fm["junk_guard"] + [f"junk {jg_junk_m}"]),
        ("name_trap no item newly wrong vs 138m", not newly_wrong,
         fn["name_trap"] + [f"newly wrong {newly_wrong}"], fm["name_trap"]),
        ("0 junk writes over 80", jn == 0, jn, jm),
        ("0 question writes", qn == 0, qn, qm),
        ("control 16/16 right and byte-identical",
         fn["control"][0] == 16 and ctrl_ident_n == 16,
         fn["control"] + [f"identical {ctrl_ident_n}"],
         fm["control"] + [f"identical {ctrl_ident_m}"]),
    ]
    return marks


def main(argv):
    mode = argv[1]
    if mode == "dev":
        cases = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        rows = json.loads(Path(argv[3]).read_text(encoding="utf-8"))
        base = json.loads(Path(argv[4]).read_text(encoding="utf-8"))
        res, fam = score_dev(cases, rows, base)
        bres, bfam = score_dev(cases, base, base)
        for k in fam:
            print(f"{k:20s} 260 {fam[k][0]}/{fam[k][1]}   "
                  f"138m {bfam[k][0]}/{bfam[k][1]}")
        tot = sum(v[0] for v in fam.values())
        btot = sum(v[0] for v in bfam.values())
        print(f"TOTAL 260 {tot}/{len(res)}  138m {btot}/{len(res)}")
        for r in res:
            if not r["right"]:
                print("MISS", r["id"], r["family"], r["why"])
        if len(argv) > 5:
            Path(argv[5]).write_text(json.dumps(
                {"260": res, "138m": bres, "fam260": fam, "fam138m": bfam},
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
            print(f"{'PASS' if ok else 'FAIL'}  {name:42s} 260={a}  138m={b}")
        # driver fidelity: our 138m arm vs the writer's base138m rows
        rb = {r["id"]: r for r in rows_m}
        diff = [i for i in base if any(
            rb[i][k] != base[i][k] for k in (
                "setup_replies", "stored_after_setup", "turn_reply",
                "stored_after_turn", "followup_reply",
                "stored_after_followup"))]
        print(f"138m arm vs base138m.jsonl: {80 - len(diff)}/80 identical "
              f"{diff}")
        for arm in ("260", "138m"):
            for r in out[arm]:
                if not r["right"]:
                    print(f"MISS {arm} {r['id']} {r['family']} {r}")
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
