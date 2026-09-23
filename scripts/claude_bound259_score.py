#!/usr/bin/env python3
"""Exp 259 scorer (read-only).

panel <panel_dir> <mine rows> <252b rows>
    corrtail258 schema check FIRST (any mismatch: print SCHEMA-MISMATCH,
    exit 3, no verdict), then the corrtail258 scoring rules on both arms,
    keep/control identity against the writer's base252b.jsonl, and the M1
    bars on "mine".
schema <panel_dir>
    schema check only.
dev <cases> <mine rows> <252b rows>
    the same per-item rules on the dev259 set (+ restart/extra checks, the
    "keep" family must be byte-identical to 252b's rows, pred check).
diff <rows A> <rows B> [cases]
    ids whose rows differ in any field except ms_per_turn; per id the
    changed fields (turn reply / stores) side by side.
falseclaims <cases> <rows>
    target-based false-claim count (corrtail258 rule) on a row file.
latency <rows A> <rows B>
    median ms per turn over all turns of each file and the difference.
suites <sd dir A> <sd dir B>
    fable_suitediff218 outputs: per suite, moves and class counts equal;
    every rows file equal except the timing key "seconds".
smoke <smoke A.json> <smoke B.json>
    every field equal except agent, config, label, paths, seconds / timing.
m2 <dev252b cases> <mine rows> <252b rows>
    moved ids == PRED_M2 exactly; every moved row removes exactly its
    target and says "OK, I removed <V> as <S>'s <R>."; 0 false claims
    (corrtail258 rule) on mine. (Junk / wrong removals / question writes /
    controls: scripts/claude_corr252b_score.py dev, read-only.)
m3 <corrpanel252 panel.jsonl> <mine rows> <252b registered rows>
    sealed move rule (PASSMARKS): a row may move only if 252b's turn reply
    is an "I don't have V as S's R[, so I didn't change anything]." reply
    whose V or R holds a clause boundary; such a row may only become
    (a) "OK, I removed X as S's ..." removing exactly one triple (S, *, X)
    with X == the part of V before its first boundary (case-insensitive),
    (b) "I don't have head(V) as S's R, so I didn't change anything." with
    stores unchanged, or (c) 252's "Which fact is wrong?" ask with stores
    unchanged. Every other row identical except ms_per_turn. Plus 0 new
    wrong values and 0 new junk writes vs 252b (corrpanel rules).
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

PANEL_FILES = ["panel.jsonl", "base252b.jsonl", "make_panel.py",
               "run_base.py", "README.md", "SEAL.sha256.txt"]
PANEL_FIELDS = ["id", "family", "setup", "turn", "followup", "stated_facts",
                "target", "expect_gone", "expect_store", "gold_followup",
                "note"]
BASE_FIELDS = ["id", "setup_replies", "stored_after_setup", "turn_reply",
               "stored_after_turn", "followup_reply", "stored_after_followup",
               "base_right", "base_wrong_value", "base_false_claim"]
FAMILIES = {"that_denial": 12, "that_correction": 12, "pure_denial_that": 10,
            "other_tail_denial": 10, "keep": 8, "question_tail": 6,
            "unstored_tail": 6, "control": 16}
IDENT_FAMS = ("keep", "control")


def load(p):
    return [json.loads(line) for line in
            Path(p).read_text(encoding="utf-8").splitlines() if line.strip()]


def by_id(p):
    return {r["id"]: r for r in load(p)}


def T(xs):
    return {tuple(str(v).lower() for v in x) for x in (xs or [])}


def ww(needle, hay):
    if not needle:
        return False
    return re.search(r"(?<![\w])" + re.escape(str(needle)) + r"(?![\w])",
                     hay or "", re.IGNORECASE) is not None


def mismatch(msg) -> int:
    print(f"SCHEMA-MISMATCH: {msg}")
    return 3


def schema(d: Path):
    """-> (items, base_rows) or an int exit code 3 after printing."""
    for f in PANEL_FILES:
        if not (d / f).is_file():
            return mismatch(f"missing file {f}")
    try:
        items = load(d / "panel.jsonl")
        base = load(d / "base252b.jsonl")
    except Exception as e:  # noqa: BLE001
        return mismatch(f"unreadable jsonl: {e}")
    if len(items) != 80 or len(base) != 80:
        return mismatch(f"line counts {len(items)} / {len(base)} (need 80)")
    for it in items:
        if list(it.keys()) != PANEL_FIELDS and set(it) != set(PANEL_FIELDS):
            return mismatch(f"panel fields {sorted(it)}")
        if set(it) != set(PANEL_FIELDS):
            return mismatch(f"panel fields {sorted(it)}")
    for r in base:
        if set(r) != set(BASE_FIELDS):
            return mismatch(f"base fields {sorted(r)}")
    ids = [it["id"] for it in items]
    want = [f"t258-{k:03d}" for k in range(1, 81)]
    if ids != want:
        return mismatch("panel ids are not t258-001..t258-080 in order")
    if [r["id"] for r in base] != ids:
        return mismatch("base252b ids differ from panel ids / order")
    counts = {}
    for it in items:
        counts[it["family"]] = counts.get(it["family"], 0) + 1
    if counts != FAMILIES:
        return mismatch(f"family counts {counts}")
    # family-block order
    order = [it["family"] for it in items]
    blocks = []
    for f in order:
        if not blocks or blocks[-1] != f:
            blocks.append(f)
    if len(blocks) != len(FAMILIES):
        return mismatch(f"families not in contiguous blocks: {blocks}")
    for it in items:
        if not (isinstance(it["setup"], list) and it["setup"]
                and all(isinstance(s, str) for s in it["setup"])):
            return mismatch(f"{it['id']} setup")
        for k in ("turn", "followup", "note"):
            if not isinstance(it[k], str):
                return mismatch(f"{it['id']} {k} not a string")
        for k in ("stated_facts", "expect_gone", "expect_store"):
            v = it[k]
            if not (isinstance(v, list) and all(
                    isinstance(t, list) and len(t) == 3 for t in v)):
                return mismatch(f"{it['id']} {k} not a list of triples")
        tg = it["target"]
        if tg is not None and not (isinstance(tg, list) and len(tg) == 3):
            return mismatch(f"{it['id']} target")
        g = it["gold_followup"]
        if g is not None and not isinstance(g, str):
            return mismatch(f"{it['id']} gold_followup")
    for r in base:
        for k in ("setup_replies",):
            if not isinstance(r[k], list):
                return mismatch(f"{r['id']} {k}")
        for k in ("stored_after_setup", "stored_after_turn",
                  "stored_after_followup"):
            if not isinstance(r[k], list):
                return mismatch(f"{r['id']} {k}")
        for k in ("turn_reply", "followup_reply"):
            if not isinstance(r[k], str):
                return mismatch(f"{r['id']} {k}")
        for k in ("base_right", "base_wrong_value", "base_false_claim"):
            if not isinstance(r[k], bool):
                return mismatch(f"{r['id']} {k}")
    return items, base


def score_item(it, row, ident_row=None):
    s_setup, s_turn = T(row["stored_after_setup"]), T(row["stored_after_turn"])
    s_follow = T(row["stored_after_followup"])
    es, eg = T(it["expect_store"]), T(it["expect_gone"])
    allowed = s_setup | es
    store_ok = es <= s_turn and not (eg & s_turn) and s_turn <= allowed
    junk = sorted((s_turn - allowed) | (s_follow - allowed))
    fr = row["followup_reply"]
    gone_vals = [t[2] for t in it["expect_gone"]]
    if it["gold_followup"]:
        parts = [p.strip() for p in it["gold_followup"].split(";") if p.strip()]
        followup_ok = (all(p.lower() in fr.lower() for p in parts)
                       and not re.match(r"\s*i (?:don't|do not) know", fr,
                                        re.IGNORECASE))
    else:
        followup_ok = not any(ww(v, fr) for v in gone_vals)
    wrong_value = any(ww(v, fr) for v in gone_vals)
    follow_write = s_follow != s_turn
    tg = it.get("target")
    false_claim = bool(
        tg and tuple(str(x).lower() for x in tg) in s_setup
        and tuple(str(x).lower() for x in tg) in s_turn
        and re.search(r"(?:don't|do not) have", row["turn_reply"], re.I)
        and ww(tg[2], row["turn_reply"]))
    right = store_ok and followup_ok and not follow_write and not false_claim
    if it["family"] == "unstored_tail" and re.search(
            r"removed|updated", row["turn_reply"], re.IGNORECASE):
        right = False
    ident = None
    if ident_row is not None:
        ident = all(row[k] == ident_row[k] for k in (
            "turn_reply", "followup_reply", "stored_after_setup",
            "stored_after_turn", "stored_after_followup"))
        right = right and ident
    return {"id": it["id"], "family": it["family"], "right": bool(right),
            "store_ok": store_ok, "followup_ok": followup_ok,
            "wrong_value": wrong_value, "followup_write": follow_write,
            "false_claim": false_claim, "junk": [list(j) for j in junk],
            "identical": ident}


def fam_table(res):
    out = {}
    for r in res:
        f = out.setdefault(r["family"], {"n": 0, "right": 0, "false_claim": 0,
                                         "junk": 0, "wrong_value": 0})
        f["n"] += 1
        f["right"] += r["right"]
        f["false_claim"] += r["false_claim"]
        f["junk"] += bool(r["junk"])
        f["wrong_value"] += r["wrong_value"]
    return out


def panel(d, mine, ref) -> int:
    got = schema(Path(d))
    if isinstance(got, int):
        return got
    items, base = got
    B = {r["id"]: r for r in base}
    M, R = by_id(mine), by_id(ref)
    if set(M) != {it["id"] for it in items} or set(R) != set(M):
        return mismatch("row files do not cover the panel ids")
    rm, rr = [], []
    for it in items:
        idr = B[it["id"]] if it["family"] in IDENT_FAMS else None
        rm.append(score_item(it, M[it["id"]], idr))
        rr.append(score_item(it, R[it["id"]], idr))
    fm, fr = fam_table(rm), fam_table(rr)
    RR = {r["id"]: r for r in rr}
    newly_wrong = [r["id"] for r in rm if not r["right"]
                   and RR[r["id"]]["right"]]
    junk_items = [r["id"] for r in rm if r["junk"]]
    allowed_junk = [i for i in junk_items
                    if next(x for x in items if x["id"] == i)["family"]
                    in ("that_correction", "pure_denial_that")
                    and RR[i]["junk"] == next(r for r in rm
                                              if r["id"] == i)["junk"]]
    bad_junk = [i for i in junk_items if i not in allowed_junk]
    fc = [r["id"] for r in rm if r["false_claim"]]
    wv = [r["id"] for r in rm if r["wrong_value"] and r["family"] in
          ("that_denial", "other_tail_denial")]
    other_newly = [i for i in newly_wrong
                   if next(x for x in items if x["id"] == i)["family"]
                   not in ("that_denial", "other_tail_denial")]
    # writer's base fields vs my 252b arm (sanity, no bar)
    base_agree = [it["id"] for it in items
                  if B[it["id"]]["base_right"] != RR[it["id"]]["right"]
                  and it["family"] not in IDENT_FAMS]
    ref_ident = [it["id"] for it in items
                 if any(R[it["id"]][k] != B[it["id"]][k] for k in (
                     "turn_reply", "followup_reply", "stored_after_setup",
                     "stored_after_turn", "stored_after_followup"))]
    bars = {
        "that_denial>=10/12": fm["that_denial"]["right"] >= 10,
        "other_tail_denial>=8/10": fm["other_tail_denial"]["right"] >= 8,
        "false_claims==0": not fc,
        "junk_writes==0(except same-as-252b in that_correction/"
        "pure_denial_that)": not bad_junk,
        "wrong_values==0(that_denial,other_tail_denial)": not wv,
        "no_other_family_newly_wrong": not other_newly,
        "question_tail==6/6": fm["question_tail"]["right"] == 6,
        "unstored_tail==6/6": fm["unstored_tail"]["right"] == 6,
        "keep==8/8": fm["keep"]["right"] == 8,
        "control==16/16": fm["control"]["right"] == 16,
    }
    out = {"schema": "OK", "mine": fm, "ref252b": fr,
           "mine_false_claims": fc,
           "ref252b_false_claims": [r["id"] for r in rr if r["false_claim"]],
           "mine_junk_items": junk_items, "junk_allowed_258s_job":
           allowed_junk, "junk_not_allowed": bad_junk,
           "ref252b_junk_items": [r["id"] for r in rr if r["junk"]],
           "mine_wrong_value_denials": wv,
           "ref252b_wrong_value_denials": [
               r["id"] for r in rr if r["wrong_value"] and r["family"] in
               ("that_denial", "other_tail_denial")],
           "newly_wrong_vs_252b": newly_wrong,
           "newly_right_vs_252b": [r["id"] for r in rm if r["right"]
                                   and not RR[r["id"]]["right"]],
           "ref252b_run_vs_writer_base_rows_differ": ref_ident,
           "writer_base_right_vs_my_252b_score_differ": base_agree,
           "bars": bars, "M1_pass": all(bars.values()),
           "items": {r["id"]: {"mine": r, "ref252b": RR[r["id"]]}
                     for r in rm}}
    print(json.dumps({k: v for k, v in out.items() if k != "items"},
                     indent=1))
    Path(mine).with_suffix(".score.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    return 0


def dev(cases, mine, ref) -> int:
    items = load(cases)
    M, R = by_id(mine), by_id(ref)
    res = {}
    for arm, rows in (("mine", M), ("ref252b", R)):
        out = []
        for it in items:
            row = rows[it["id"]]
            idr = R[it["id"]] if (it["family"] == "keep" and arm == "mine") \
                else None
            s = score_item(it, row, idr)
            # stricter dev false claim: "don't have V as S's R" for a stored
            # (S, R, V) after the turn
            for t in row["stored_after_turn"]:
                pat = (r"(?:don't|do not) have " + re.escape(t[2]) + r" as "
                       + re.escape(t[0]) + r"'s " + re.escape(
                           t[1].replace("_", " ")))
                if re.search(pat, row["turn_reply"], re.IGNORECASE):
                    s["false_claim"] = True
                    s["right"] = False
            ok = True
            for q, rep in zip(it.get("extra", []), row.get("extra_replies",
                                                           [])):
                _q, must_not, must = (list(q) + [[], []])[:3]
                if any(ww(v, rep) for v in must_not or []) or any(
                        not ww(v, rep) for v in must or []):
                    ok = False
            if it.get("extra") and T(row.get("stored_end")) != T(
                    row["stored_after_followup"]):
                ok = False
            s["extra_ok"] = ok
            if it["family"] == "keep":
                s["right"] = (s["identical"] if arm == "mine" else None)
            s["right"] = bool(s["right"]) and ok
            s["pred"] = it.get("pred")
            out.append(s)
        res[arm] = out
    fm = fam_table(res["mine"])
    fr = fam_table(res["ref252b"])
    pred_off = [s["id"] for s in res["mine"]
                if (s["pred"] == "right") != s["right"]]
    summary = {"mine": fm, "ref252b": fr,
               "mine_not_right": [(s["id"], s["family"], s["pred"])
                                  for s in res["mine"] if not s["right"]],
               "mine_false_claims": [s["id"] for s in res["mine"]
                                     if s["false_claim"]],
               "ref252b_false_claims": [s["id"] for s in res["ref252b"]
                                        if s["false_claim"]],
               "mine_junk": [(s["id"], s["junk"]) for s in res["mine"]
                             if s["junk"]],
               "ref252b_junk": [(s["id"], s["junk"]) for s in res["ref252b"]
                                if s["junk"]],
               "not_as_predicted": pred_off}
    print(json.dumps(summary, indent=1))
    return 0


def strip(r):
    r = dict(r)
    r.pop("ms_per_turn", None)
    return r


def diff(a, b, cases=None) -> int:
    A, B = by_id(a), by_id(b)
    fam = {}
    if cases:
        fam = {it["id"]: it.get("family") for it in load(cases)}
    moved = []
    for k in A:
        if strip(A[k]) != strip(B.get(k, {})):
            fields = [f for f in strip(A[k]) if A[k].get(f) != B.get(k,
                                                                    {}).get(f)]
            moved.append(k)
            print(f"== {k} {fam.get(k, '')} fields={fields}")
            for f in ("turn_reply", "stored_after_turn", "followup_reply",
                      "stored_after_followup", "extra_replies"):
                if f in fields:
                    print(f"   {f}\n     A: {A[k][f]}\n     B: {B[k][f]}")
    print(json.dumps({"n_a": len(A), "n_b": len(B), "moved": moved},
                     indent=1))
    return 0


def falseclaims(cases, rows) -> int:
    items, R = load(cases), by_id(rows)
    hits = [it["id"] for it in items if it.get("target")
            and score_item(dict(it, family="x"), R[it["id"]])["false_claim"]]
    print(json.dumps({"false_claims": hits}, indent=1))
    return 0


def latency(a, b) -> int:
    def med(p):
        xs = [x for r in load(p) for x in r.get("ms_per_turn", [])]
        return statistics.median(xs), len(xs)
    ma, na = med(a)
    mb, nb = med(b)
    print(json.dumps({"median_ms_a": ma, "turns_a": na, "median_ms_b": mb,
                      "turns_b": nb, "added_ms_a_minus_b": ma - mb},
                     indent=1))
    return 0


def _drop(o, keys):
    if isinstance(o, dict):
        return {k: _drop(v, keys) for k, v in o.items() if k not in keys}
    if isinstance(o, list):
        return [_drop(v, keys) for v in o]
    return o


def _rows_any(p: Path):
    txt = p.read_text(encoding="utf-8")
    try:
        return [json.loads(txt)]
    except json.JSONDecodeError:
        return [json.loads(line) for line in txt.splitlines() if line.strip()]


def suites(a, b) -> int:
    A, B = Path(a), Path(b)
    out, ok = {}, True
    for s in ("rt136", "rt143", "sessions152", "bench"):
        da = json.loads((A / f"{s}-diff.json").read_text(encoding="utf-8"))
        db = json.loads((B / f"{s}-diff.json").read_text(encoding="utf-8"))
        same = (da["moves"] == db["moves"]
                and da["class_counts"] == db["class_counts"])
        out[s] = {"n_moves_a": da["n_moves"], "n_moves_b": db["n_moves"],
                  "moves_equal": same,
                  "new_wrong_a": len(da.get("new_wrong") or []),
                  "new_wrong_write_a": len(da.get("new_wrong_write") or []),
                  "new_junk_a": len(da.get("new_junk") or [])}
        ok = ok and same
    rows = {}
    for f in sorted(A.glob("*-rows.json*")):
        g = B / f.name
        eq = g.is_file() and _drop(_rows_any(f), {"seconds"}) == _drop(
            _rows_any(g), {"seconds"})
        rows[f.name] = eq
        ok = ok and eq
    out["rows_equal_except_seconds"] = rows
    out["all_equal"] = ok
    print(json.dumps(out, indent=1))
    return 0


PRED_M2 = ["b252-001", "b252-003", "b252-010", "b252-013", "b252-014",
           "b252-015"]
BOUNDS = (", ", " - ", " \u2014 ", "; ", " (")
IDONT = re.compile(r"^I don't have (?P<v>.+?) as (?P<s>[A-Z][\w-]*)'s "
                   r"(?P<r>.+?)(?:, so I didn't change anything)?\.$")


def _head(v):
    hits = [i for i in (v.find(b) for b in BOUNDS) if i >= 0]
    return v[:min(hits)].strip() if hits else v


def _hasb(v):
    return any(b in v for b in BOUNDS)


def m2(cases, mine, ref) -> int:
    items = {it["id"]: it for it in load(cases)}
    M, R = by_id(mine), by_id(ref)
    moved = [k for k in R if strip(M[k]) != strip(R[k])]
    bad = []
    for k in moved:
        it, r = items[k], M[k]
        tg = it.get("target")
        want = T(r["stored_after_setup"]) - T([tg] if tg else [])
        if not (tg and T(r["stored_after_turn"]) == want and re.match(
                rf"^OK, I removed {re.escape(tg[2])} as ", r["turn_reply"])):
            bad.append(k)
    fc = [k for k, it in items.items() if it.get("target") and score_item(
        dict(it, family="x"), M[k])["false_claim"]]
    fc_ref = [k for k, it in items.items() if it.get("target") and
              score_item(dict(it, family="x"), R[k])["false_claim"]]
    out = {"moved": moved, "predicted": PRED_M2,
           "moves_as_predicted": sorted(moved) == sorted(PRED_M2),
           "moved_rows_not_a_clean_target_removal": bad,
           "false_claims_mine": fc, "false_claims_252b": fc_ref}
    out["pass_part"] = (out["moves_as_predicted"] and not bad and not fc)
    print(json.dumps(out, indent=1))
    return 0


def m3(panel_items, mine, ref) -> int:
    items = {it["id"]: it for it in load(panel_items)}
    M, R = by_id(mine), by_id(ref)
    allowed, moved, bad = [], [], []
    new_wv, new_junk = [], []
    for k, a in R.items():
        b = M[k]
        m = IDONT.match(a["turn_reply"])
        may = bool(m and (_hasb(m.group("v")) or _hasb(m.group("r"))))
        if may:
            allowed.append(k)
        if strip(a) == strip(b):
            pass
        else:
            moved.append(k)
            ok = False
            if may:
                sa, sb = T(a["stored_after_turn"]), T(b["stored_after_turn"])
                subj, hv = m.group("s"), _head(m.group("v"))
                if b["turn_reply"].startswith("OK, I removed "):
                    gone = sa - sb
                    ok = (len(gone) == 1 and not (sb - sa)
                          and next(iter(gone))[0] == subj.lower()
                          and next(iter(gone))[2] == hv.lower())
                elif b["turn_reply"] == (f"I don't have {hv} as {subj}'s "
                                         f"{m.group('r')}, so I didn't "
                                         "change anything.") or \
                        b["turn_reply"].startswith("I don't have " + hv
                                                   + " as " + subj + "'s ") \
                        and not _hasb(b["turn_reply"][len("I don't have "
                                                          + hv):].split(
                            ", so I didn't")[0]):
                    ok = sa == sb
                elif b["turn_reply"].startswith("Which fact is wrong?"):
                    ok = sa == sb
            if not ok:
                bad.append(k)
        it = items[k]
        for arm_row, tag in ((a, "a"), (b, "b")):
            pass
        sa_ = score_item(dict(it, target=None), a)
        sb_ = score_item(dict(it, target=None), b)
        if sb_["wrong_value"] and not sa_["wrong_value"]:
            new_wv.append(k)
        if sb_["junk"] and sb_["junk"] != sa_["junk"]:
            new_junk.append(k)
    out = {"rows": len(R), "allowed_to_move_by_rule": allowed,
           "moved": moved, "moves_outside_rule": bad,
           "new_wrong_values": new_wv, "new_junk_writes": new_junk}
    out["M3_pass"] = not bad and not new_wv and not new_junk
    print(json.dumps(out, indent=1))
    return 0


SMOKE_SKIP = {"agent", "config", "label", "seconds", "root", "report",
              "path", "paths", "elapsed", "wall_seconds", "time", "ms"}


def smoke(a, b) -> int:
    A = json.loads(Path(a).read_text(encoding="utf-8"))
    B = json.loads(Path(b).read_text(encoding="utf-8"))
    diffs = []

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if k in SMOKE_SKIP or "second" in k or k.endswith("_s") \
                        or k.endswith("_ms"):
                    continue
                walk(x.get(k), y.get(k), path + [k])
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, path + [str(i)])
        elif x != y:
            if isinstance(x, str) and isinstance(y, str) and (
                    "/" in x or "/" in y):
                return  # a path
            diffs.append([".".join(path), x, y])
    walk(A, B, [])
    print(json.dumps({"differences": diffs, "identical": not diffs},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "schema":
        g = schema(Path(args[0]))
        if isinstance(g, int):
            sys.exit(g)
        print("SCHEMA OK")
        sys.exit(0)
    sys.exit({"panel": panel, "dev": dev, "diff": diff,
              "falseclaims": falseclaims, "latency": latency,
              "suites": suites, "smoke": smoke, "m2": m2, "m3": m3}[mode](*args))
