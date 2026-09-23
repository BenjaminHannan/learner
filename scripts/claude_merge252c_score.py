#!/usr/bin/env python3
"""Exp 252c scorer (read-only on every input). Run with uv Python 3.12 or
/usr/bin/python3 (never bare python3 on this Mac).

Shared definitions
  false reply  = (the bar; see false_reply) a turn reply "... don't have
                 X as S's R ..." where (S, R, headc(X)) is stored after
                 the turn; headc = X up to its first clause boundary with
                 252's clause-end words dropped ("Tobin anymore" -> Tobin,
                 "Brimwell, that's outdated" -> Brimwell; "Garrow Hall" stays
                 a different value from "Garrow"). A "don't have" reply in
                 another form uses the loose rule: V, S and R's surface
                 words all appear (whole word) for some stored (S, R, V).
                 The loose rule on every reply is reported as information.
  junk (m3)    = the corrtail258 junk rule; dev259 "keep" items carry no
                 expect_store in 259's dev schema, so they are checked by
                 identity to the own arm instead.
  panel scoring = the corrtail258 spec rules, imported read-only from
                 scripts/claude_bound259_score.py (score_item, schema).

Modes
m1 <corrtail258 dir> <252c rows> <252b rows> <258 rows> <259 rows>
    schema check first (SCHEMA-MISMATCH -> exit 3, no verdict). Bars:
    every item right on 258 or 259 is right on 252c; 0 false claims /80;
    0 junk writes /80; no item has a wrong value on 252c where 258 or 259
    had none; keep 8/8 and control 16/16 right and byte-identical to
    base252b.jsonl; question_tail 6/6; unstored_tail 6/6.
    Information: 252c vs the sealed prediction (258's row where 258 moved
    vs 252b, else 259's row where 259 moved, else 252b's row).
m2 <dev252b cases> <252c rows> <252b rows same session> <258 reg rows>
   <259 reg rows>
    0 junk, 0 wrong removals, 0 question writes, controls identical to
    the same-session 252b rows except ms_per_turn (252b scorer's
    definitions), 0 false replies; moved ids == PRED_M2 exactly and each
    moved row == its predicted record (258's registered row for 258's 29,
    259's registered row for b252-003 / b252-015), except ms_per_turn.
m3 <cases> <252c rows> <own-arm rows> <pred file> <other-arm rows>
    every item == the own arm's row except the ids in the sealed pred
    file, which must equal their predicted record in that file (and are
    reported against the other arm's same-session row); 0 false replies;
    0 junk writes (corrtail258 junk rule).
m4 <corrpanel252 dir> <252c rows> <252b reg rows> <258 reg rows>
   <259 reg rows>
    sealed mechanical move rule (PASSMARKS) + 0 new wrong values, 0 new
    junk vs 252b, 0 false replies. Prints ids and rule classes only (the
    panel is TEST-ONLY: no item text is printed).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_bound259_score as S259  # noqa: E402 (read-only)

ORDER = ["that_denial", "that_correction", "pure_denial_that",
         "other_tail_denial", "keep", "question_tail", "unstored_tail",
         "control"]

PRED_M2_258 = ["b252-001", "b252-002", "b252-004", "b252-005", "b252-006",
               "b252-007", "b252-008", "b252-010", "b252-011", "b252-013",
               "b252-014", "b252-016", "b252-017", "b252-018", "b252-019",
               "b252-020", "b252-021", "b252-023", "b252-024", "b252-026",
               "b252-027", "b252-029", "b252-030", "b252-031", "b252-032",
               "b252-033", "b252-035", "b252-036", "b252-037"]
PRED_M2_259 = ["b252-003", "b252-015"]
PRED_M2 = sorted(PRED_M2_258 + PRED_M2_259)

TAIL_RX = re.compile(
    r"(?:\s*,?\s*(?:now|instead|these days|nowadays|actually|then|"
    r"anymore|any more|any longer|at all|though|please))+\s*$",
    re.IGNORECASE)  # copy of 252's _TAIL_RX (claude_fix252_correct.py)
BOUNDS = (", ", " - ", " — ", "; ", " (")
IDONT = re.compile(r"^I don't have (?P<v>.+?) as (?P<s>.+?)'s (?P<r>.+?)"
                   r"(?:, so I didn't change anything)?\.$")


def rows(p):
    return {json.loads(line)["id"]: json.loads(line) for line in
            Path(p).read_text(encoding="utf-8").splitlines() if line.strip()}


def items_of(p):
    return [json.loads(line) for line in
            Path(p).read_text(encoding="utf-8").splitlines() if line.strip()]


def strip(r):
    r = dict(r)
    r.pop("ms_per_turn", None)
    return r


T = S259.T
ww = S259.ww


IDONT_ANY = re.compile(r"(?:don't|do not) have (?P<v>.+?) as (?P<s>.+?)'s "
                       r"(?P<r>.+?)(?:, so I didn't change anything)?\.?$",
                       re.IGNORECASE)


def false_reply_loose(row) -> bool:
    """Information only: any stored (S, R, V) whose V, S and R surface all
    appear (whole word) in a turn reply containing don't/do not have."""
    rep = row.get("turn_reply") or ""
    if not re.search(r"(?:don't|do not) have", rep, re.IGNORECASE):
        return False
    for s, r, v in row.get("stored_after_turn") or []:
        if ww(v, rep) and ww(s, rep) and ww(str(r).replace("_", " "), rep):
            return True
    return False


def false_reply(row) -> bool:
    """The bar. A reply of the form "... don't have X as S's R ..." is
    false when (S, R, headc(X)) is stored after the turn (headc: X up to
    its first clause boundary, 252's clause-end words dropped, so "Tobin
    anymore" and "Brimwell, that's outdated" count as Tobin / Brimwell,
    while "Garrow Hall" is a different value from "Garrow"). A reply with
    "don't have" in another form falls back to the loose rule."""
    rep = row.get("turn_reply") or ""
    if not re.search(r"(?:don't|do not) have", rep, re.IGNORECASE):
        return False
    m = IDONT_ANY.search(rep)
    if not m:
        return false_reply_loose(row)
    x = headc(m.group("v")).lower()
    s_ = m.group("s").strip().lower()
    r_ = m.group("r").strip().lower()
    for s, r, v in row.get("stored_after_turn") or []:
        if (str(s).lower() == s_ and str(v).lower() == x
                and r_.startswith(str(r).replace("_", " ").lower())):
            return True
    return False


def junk_spec(it, row) -> bool:
    allowed = T(row["stored_after_setup"]) | T(it.get("expect_store") or [])
    return not (T(row["stored_after_turn"]) <= allowed
                and T(row["stored_after_followup"]) <= allowed)


def headc(v: str) -> str:
    """Part of V before its first clause boundary, 252's clause-end words
    ("anymore", "now", ...) dropped (259's head259; fixes 259's scorer)."""
    hits = [i for i in (v.find(b) for b in BOUNDS) if i >= 0]
    h = v[:min(hits)] if hits else v
    return TAIL_RX.sub("", h.strip().rstrip(".!").strip()).strip()


# ---------------------------------------------------------------- m1
def m1(d, mine, base, r258, r259) -> int:
    got = S259.schema(Path(d))
    if isinstance(got, int):
        return got
    items, wbase = got
    WB = {r["id"]: r for r in wbase}
    M, B, E, N = rows(mine), rows(base), rows(r258), rows(r259)
    ids = [it["id"] for it in items]
    for X in (M, B, E, N):
        if set(X) != set(ids):
            return S259.mismatch("row files do not cover the panel ids")
    res = {}
    for arm, X in (("252c", M), ("252b", B), ("258", E), ("259", N)):
        res[arm] = {}
        for it in items:
            idr = WB[it["id"]] if it["family"] in S259.IDENT_FAMS else None
            res[arm][it["id"]] = S259.score_item(it, X[it["id"]], idr)
    fam = {}
    for arm in res:
        fam[arm] = {f: 0 for f in ORDER}
        for it in items:
            fam[arm][it["family"]] += res[arm][it["id"]]["right"]
    tot = {arm: {"right": sum(r["right"] for r in res[arm].values()),
                 "false_claim": sum(r["false_claim"]
                                    for r in res[arm].values()),
                 "junk": sum(bool(r["junk"]) for r in res[arm].values()),
                 "wrong_value": sum(r["wrong_value"]
                                    for r in res[arm].values())}
           for arm in res}
    lost = [i for i in ids if (res["258"][i]["right"] or res["259"][i]["right"])
            and not res["252c"][i]["right"]]
    fc = [i for i in ids if res["252c"][i]["false_claim"]]
    junk = [i for i in ids if res["252c"][i]["junk"]]
    wv_new = [i for i in ids if res["252c"][i]["wrong_value"]
              and not (res["258"][i]["wrong_value"]
                       and res["259"][i]["wrong_value"])]
    fam_of = {it["id"]: it["family"] for it in items}
    keep_ok = fam["252c"]["keep"] == 8
    ctrl_ok = fam["252c"]["control"] == 16
    bars = {
        "every item right on 258 or 259 is right on 252c": not lost,
        "false claims == 0 /80": not fc,
        "junk writes == 0 /80": not junk,
        "no wrong value where 258 or 259 had none": not wv_new,
        "keep 8/8 byte-identical": keep_ok,
        "control 16/16 byte-identical": ctrl_ok,
        "question_tail 6/6": fam["252c"]["question_tail"] == 6,
        "unstored_tail 6/6": fam["252c"]["unstored_tail"] == 6,
    }
    # information: sealed prediction
    pred_off = []
    for i in ids:
        if strip(E[i]) != strip(B[i]):
            p = E[i]
        elif strip(N[i]) != strip(B[i]):
            p = N[i]
        else:
            p = B[i]
        if strip(M[i]) != strip(p):
            pred_off.append(i)
    moved = [i for i in ids if strip(M[i]) != strip(B[i])]
    out = {"schema": "OK", "family_right": fam, "totals": tot,
           "lost_vs_258_or_259": lost, "false_claims_252c": fc,
           "junk_252c": junk, "wrong_value_new_252c": wv_new,
           "false_replies_252c(info)": [i for i in ids
                                        if false_reply(M[i])],
           "moved_vs_252b": moved,
           "newly_right_vs_252b": [i for i in ids if res["252c"][i]["right"]
                                   and not res["252b"][i]["right"]],
           "newly_wrong_vs_252b": [i for i in ids
                                   if res["252b"][i]["right"]
                                   and not res["252c"][i]["right"]],
           "not_as_predicted(info)": pred_off,
           "per_item_right": {i: [fam_of[i], res["252b"][i]["right"],
                                  res["258"][i]["right"],
                                  res["259"][i]["right"],
                                  res["252c"][i]["right"]] for i in ids},
           "bars": bars, "M1_pass": all(bars.values())}
    print(json.dumps(out, indent=1))
    return 0


# ---------------------------------------------------------------- m2
def m2(cases, mine, base, r258, r259) -> int:
    items = items_of(cases)
    M, B, E, N = rows(mine), rows(base), rows(r258), rows(r259)
    out = {"junk_writes": [], "wrong_removals": [], "question_writes": [],
           "control_diffs": [], "false_replies": []}
    for it in items:
        r = M[it["id"]]
        a = T(r["stored_after_setup"])
        new = T([it["new"]]) if it.get("new") else set()
        tgt = T([it["target"]]) if it.get("target") else set()
        for key in ("stored_after_turn", "stored_after_followup"):
            b = T(r[key])
            if b - a - new:
                out["junk_writes"].append(it["id"])
            if a - b - tgt:
                out["wrong_removals"].append(it["id"])
        if it["family"] == "question_tail" and (
                T(r["stored_after_turn"]) != a
                or T(r["stored_after_followup"]) != a):
            out["question_writes"].append(it["id"])
        if it["family"] == "control" and strip(r) != strip(B[it["id"]]):
            out["control_diffs"].append(it["id"])
        if false_reply(r):
            out["false_replies"].append(it["id"])
    moved = sorted(k for k in B if strip(M[k]) != strip(B[k]))
    rec_off = []
    for k in PRED_M2:
        src = E if k in PRED_M2_258 else N
        if strip(M[k]) != strip(src[k]):
            rec_off.append(k)
    out["moved"] = moved
    out["n_moved"] = len(moved)
    out["unpredicted"] = sorted(set(moved) - set(PRED_M2))
    out["missing"] = sorted(set(PRED_M2) - set(moved))
    out["record_not_as_predicted"] = rec_off
    out["false_replies_252b"] = [k for k in B if false_reply(B[k])]
    out["false_replies_loose(info)"] = [it["id"] for it in items
                                        if false_reply_loose(M[it["id"]])]
    out["M2_pass"] = not (out["junk_writes"] or out["wrong_removals"]
                          or out["question_writes"] or out["control_diffs"]
                          or out["false_replies"] or out["unpredicted"]
                          or out["missing"] or rec_off)
    print(json.dumps(out, indent=1))
    return 0


# ---------------------------------------------------------------- m3
def m3(cases, mine, own, pred, other) -> int:
    items = items_of(cases)
    M, O, X = rows(mine), rows(own), rows(other)
    P = rows(pred)
    diff_own = [k for k in M if strip(M[k]) != strip(O[k])]
    unpred = [k for k in diff_own if k not in P]
    pred_off = [k for k in P if strip(M[k]) != strip(P[k])]
    eq_other = {k: strip(M[k]) == strip(X[k]) for k in P}
    fr = [it["id"] for it in items if false_reply(M[it["id"]])]
    jk = [it["id"] for it in items if junk_spec(it, M[it["id"]])
          and not (it["family"] == "keep" and not it.get("expect_store"))]
    out = {"n": len(items), "differs_from_own_arm": diff_own,
           "predicted_exceptions": sorted(P),
           "unpredicted_diffs": unpred,
           "exceptions_not_equal_to_predicted_record": pred_off,
           "exception_equals_other_arm(info)": eq_other,
           "false_replies": fr, "junk_writes": jk,
           "false_replies_own_arm(info)": [it["id"] for it in items
                                           if false_reply(O[it["id"]])],
           "false_replies_loose(info)": [it["id"] for it in items
                                         if false_reply_loose(M[it["id"]])],
           "keep_identical_to_own_arm": all(
               strip(M[it["id"]]) == strip(O[it["id"]]) for it in items
               if it["family"] == "keep" and it["id"] not in P),
           "junk_own_arm(info)": [it["id"] for it in items
                                  if junk_spec(it, O[it["id"]]) and not (
                                      it["family"] == "keep"
                                      and not it.get("expect_store"))]}
    out["M3_pass"] = not (unpred or pred_off or fr or jk)
    print(json.dumps(out, indent=1))
    return 0


# ---------------------------------------------------------------- m4
def _clean_removal(a, m, subj, val) -> bool:
    sa, sm = T(a["stored_after_turn"]), T(m["stored_after_turn"])
    gone = sa - sm
    if len(gone) != 1 or (sm - sa):
        return False
    g = next(iter(gone))
    return (g[0] == subj.lower() and g[2] == val.lower()
            and m["turn_reply"].startswith("OK, I removed ")
            and T(m["stored_after_followup"]) == sm)


def m4(d, mine, base, r258, r259) -> int:
    d = Path(d)
    items = {it["id"]: it for it in items_of(d / "panel.jsonl")}
    M, B, E, N = rows(mine), rows(base), rows(r258), rows(r259)
    if set(M) != set(B) or set(E) != set(B) or set(N) != set(B):
        print("ROW-ID-MISMATCH")
        return 3
    cls, bad, moved = {}, [], []
    for k, a in B.items():
        m, e, n = M[k], E[k], N[k]
        mv8, mv9 = strip(e) != strip(a), strip(n) != strip(a)
        if strip(m) != strip(a):
            moved.append(k)
        if not mv8 and not mv9:
            c, ok = "neither", strip(m) == strip(a)
        elif mv9 and not mv8:
            c, ok = "259-only", strip(m) == strip(n)
        elif mv8 and not mv9:
            c = "258-only"
            ok = strip(m) == strip(e)
            if not ok:
                g = IDONT.match(e["turn_reply"])
                if g:
                    hv = headc(g.group("v"))
                    sub = g.group("s")
                    if m["turn_reply"].startswith("OK, I removed "):
                        ok = hv.lower() != g.group("v").lower() and \
                            _clean_removal(a, m, sub, hv)
                        c = "258-only+glue-removal"
                    elif m["turn_reply"].startswith(f"I have {sub}'s "):
                        ok = (T(m["stored_after_turn"])
                              == T(a["stored_after_turn"])
                              and T(m["stored_after_followup"])
                              == T(a["stored_after_turn"]))
                        c = "258-only+glue-nearmiss"
        else:
            c = "both"
            g = IDONT.match(a["turn_reply"])
            if g:
                ok = _clean_removal(a, m, g.group("s"), headc(g.group("v")))
            else:
                gone = T(a["stored_after_turn"]) - T(m["stored_after_turn"])
                ok = len(gone) == 1 and _clean_removal(
                    a, m, next(iter(gone))[0], next(iter(gone))[2]) and \
                    ww(next(iter(gone))[0], a["turn_reply"]) and \
                    ww(next(iter(gone))[2], a["turn_reply"])
            if k == "c252-022":
                ok = ok and m["turn_reply"].startswith(
                    "OK, I removed Tobin as ") and any(
                    t[2] == "tobin" for t in
                    T(a["stored_after_turn"]) - T(m["stored_after_turn"]))
        cls[k] = c
        if not ok:
            bad.append(k)
    new_wv, new_junk = [], []
    for k, a in B.items():
        it, m = items[k], M[k]
        gone = [x[2] for x in it.get("expect_gone") or []]
        if any(ww(v, m["followup_reply"]) for v in gone) and not any(
                ww(v, a["followup_reply"]) for v in gone):
            new_wv.append(k)
        if junk_spec(it, m) and not junk_spec(it, a):
            new_junk.append(k)
    fr = [k for k in M if false_reply(M[k])]
    fr_loose = [k for k in M if false_reply_loose(M[k])]
    counts = {}
    for c in cls.values():
        counts[c] = counts.get(c, 0) + 1
    out = {"rows": len(B), "class_counts": counts,
           "moved_vs_252b": moved,
           "moved_class": {k: cls[k] for k in moved},
           "rows_outside_rule": bad, "new_wrong_values": new_wv,
           "new_junk_writes": new_junk, "false_replies_252c": fr,
           "false_replies_252b(info)": [k for k in B if false_reply(B[k])],
           "false_replies_loose_252c(info)": fr_loose,
           "c252_022_class": cls.get("c252-022")}
    out["M4_pass"] = not (bad or new_wv or new_junk or fr)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    sys.exit({"m1": m1, "m2": m2, "m3": m3, "m4": m4}[mode](*args))
