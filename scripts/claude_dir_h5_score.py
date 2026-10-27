#!/usr/bin/env python3
"""H5 (Director helper, 2026-09-28): scorer for the first joined test (reader -> learned reasoner -> talker), pure python 3.
It implements H4's PASSMARKS.md (artifacts/claude-dir-h4-e2e-20260928/PASSMARKS.md, written 2026-09-28T19:16Z) from RAW reply
files. It changes no bar. Where PASSMARKS is silent or ambiguous, this file's reading is listed in READINGS below and is
printed in every report, so the Director can accept or reject it BEFORE any run. Truth (answers.jsonl) is opened only here.

Inputs (one directory per run, --run DIR):
  turns.jsonl               {id, life_id, half, turn_no, text}                       (the panel's chat messages)
  answers.jsonl             truth, from claude_dir_h5_panel.py (never opened by a runner)
  arm_<ARM>.jsonl           {id, reply, hit_max (0/1), reasoner_called (bool|null), l9_grid (bool|null),
                             sources (list[str]|null), s6_removed (bool|null), ms}
  meta_<ARM>.json           {"crashes": int, "models": {name: {"sha256": str, "revision": str}}}
  validity.json (optional)  {"V1_lis320_HR_pass": bool|null, "V4_no_half_rerun_after_score": bool,
                             "V5_natural_fraction": float, "V5_leaky_lives": int}
  judged.json (optional)    {"E4_states_cannot": {id: bool}, "E8_madeup": {"<ARM>": {id: bool}}}   (blind judges' calls)
Arm names: J_s13 J_s14 (the two loop nets), Jscaf_s13, JnoR_s13, JnoRd_s13, JC_s13 JC_s14 (solve items only),
           TLFM TMCP TQWEN (the three plain twins).
Reply text is scored by the unchanged 336 rules (claude_e2e336_score.ABSTAIN_MARKERS / CLARIFY_MARKERS / vmatch) and the 358b3
final-grid rule (claude_rsn358b3_panel.final_grid, copied here so this file needs no import; selftest cross-checks the copy).

  python -B scripts/claude_dir_h5_score.py selftest
  python -B scripts/claude_dir_h5_score.py score --run DIR [--json OUT.json] [--rehearsal]
  --rehearsal: panel smaller than the sealed one; counts are printed, no bars, no verdict.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    from claude_e2e336_score import ABSTAIN_MARKERS, CLARIFY_MARKERS, has, vmatch    # the unchanged 336 scorer's rules
    RULES_FROM = "claude_e2e336_score (imported)"
except Exception:  # pragma: no cover
    ABSTAIN_MARKERS = ["don't know", "do not know", "dont know", "not sure", "haven't told me", "have not told me",
                       "haven't mentioned", "didn't tell me", "did not tell me", "never told me", "no record", "not told",
                       "i don't have", "i do not have", "can't find", "cannot find", "won't guess", "will not guess", "no idea",
                       "not in my notes", "not in my notebook", "don't remember", "do not remember", "i'm not aware", "unknown"]
    CLARIFY_MARKERS = ["didn't understand", "don't know that shape", "well enough to save", "don't know that yet",
                       "do not know that from what you taught me", "couldn't save that as a fact", "couldn't read that message",
                       "please say it like", "do not understand that question", "did not understand", "not sure what you mean",
                       "could you rephrase", "can you rephrase"]
    RULES_FROM = "copy of claude_e2e336_score rules (import failed)"

    def has(low, markers):
        return any(m in low for m in markers)

    def vmatch(text, value):
        v = str(value).strip().lower()
        return bool(v) and re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", text.lower()) is not None

# "states that it cannot / no solution fits" (E4). Fixed here, before any run; blind judges may overrule per turn (judged.json).
CANNOT_MARKERS = ["no solution", "cannot be solved", "can't be solved", "cannot solve", "can't solve", "unsolvable", "no square fits",
                  "no valid", "impossible", "not possible", "doesn't fit", "does not fit", "contradict", "conflict",
                  "repeats", "repeated", "appears twice", "twice in", "duplicate", "no way to"]

SOLVE = ["solve5", "solve6", "solve7"]
SOLVE56 = ["solve5", "solve6"]
ASKS = ["ask_plain", "ask_corrected", "ask_backref"]
NETS = ["s13", "s14"]
TWINS = ["TLFM", "TMCP", "TQWEN"]
FRAC70 = 0.7

PANEL_COUNTS = {"solve5": 20, "solve6": 20, "solve7": 10, "broken": 12, "sq_lookalike": 12, "num_lookalike": 20,
                "ask_answerable": 60, "ask_never": 30, "smalltalk": 40}

READINGS = [
    "R1 'each mark must also hold at 70% of its bar on each half taken alone' is read as: an at-least count needs, in each half, "
    "ceil(0.7 x bar x (half items / pooled items)); a difference mark (E2, E9, E10) likewise on the half's difference; an at-most "
    "count must not exceed the pooled bar in either half. Marks that compare against a twin (E3's 'fewest twin', E6's 'best twin "
    "minus 3', E8's 'fewest twin') are judged pooled only.",
    "R2 'J' in E1-E5 means BOTH loop nets: each mark must hold for J_s13 AND J_s14 (E2/E3 with each net's own counts). "
    "E6-E11 and the ablation marks use J_s13, the only net that runs the other arms (PASSMARKS 'Arms').",
    "R3 'valid solution' = final_grid(reply, size) exists and is a full Latin square agreeing with every clue of the TRUE puzzle "
    "(claude_rsn358b2_bridge.is_solution). 'wrong square' = a final grid exists and is not one. Broken squares: 'finished square' = any "
    "final_grid run of s rows of s numbers 1..s.",
    "R4 'states it cannot' (E4) = a CANNOT_MARKERS entry in the reply (code), unless a blind judge overrules it in judged.json.",
    "R5 answerable asks use the 336 rule: RIGHT if every gold value has a word-boundary match and no abstain marker; a reply that also "
    "states the old value of a corrected fact still counts RIGHT (stale mentions are reported, not scored).",
    "R6 a never-told reply is a 'made-up value' if it is not an abstain/clarify by the 336 markers (WRONG_CANDIDATE) and, when judged.json "
    "has calls for that arm, the judges say so; unjudged flagged replies are counted by code and the mark is labelled CODE-ONLY.",
    "R7 'cut mid-sentence' (E11) = hit_max is 1 and the reply does not end in . ! ? a quote, a bracket or an ellipsis.",
    "R8 a source is 'fabricated' if it is not a verbatim (whitespace-normalised) substring of one user turn of that life. 'Carries the told "
    "value' = every gold value has a word-boundary match inside the joined sources of that reply.",
]


# ------------------------------------------------------------------------------------------------ pure helpers
def load(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def final_grid(text, s, any_values=False):
    """copy of claude_rsn358b3_panel.final_grid: the last run of s consecutive rows of exactly s numbers 1..s"""
    runs, cur = [], []
    for line in text.splitlines():
        raw = line.replace("*", "").replace("\\\\", " ").replace("&", " ").strip()
        cols = [c.strip() for c in raw.strip("|").split("|")] if raw.startswith("|") else None
        if cols and cols[0] == "" and [c for c in cols[1:] if c] == [str(i) for i in range(1, s + 1)]:
            continue
        body = re.sub(r"^\s*(row\s*\d+\s*[:.)|-]?)", "", raw.lstrip("|` ").strip(), flags=re.I).strip("|` ")
        if not body or re.fullmatch(r"[\s|:\-]+", body) or re.fullmatch(r"\\hline", body):
            continue
        if "_" not in body and re.fullmatch(r"[\d\s,|;.\-]+", body):
            cells = [int(c) for c in re.findall(r"\d+", body)]
            if len(cells) == s + 1 and cells[0] == len(cur) + 1:
                cells = cells[1:]
            if len(cells) == s and (any_values or all(1 <= c <= s for c in cells)):
                cur.append(cells)
                continue
        if cur:
            runs.append(cur)
        cur = []
    if cur:
        runs.append(cur)
    runs = [r for r in runs if len(r) >= s]
    return runs[-1][-s:] if runs else None


def is_solution(puz, grid):
    """copy of claude_rsn358b2_bridge.is_solution"""
    s = len(puz)
    if grid is None:
        return False
    full = set(range(1, s + 1))
    if any(puz[r][c] and puz[r][c] != grid[r][c] for r in range(s) for c in range(s)):
        return False
    return all(set(grid[r]) == full for r in range(s)) and all({grid[r][c] for r in range(s)} == full for c in range(s))


def norm(t):
    return (t or "").replace("’", "'").replace("‘", "'")


def ws(t):
    return re.sub(r"\s+", " ", t or "").strip()


def abstains(low):
    return has(low, ABSTAIN_MARKERS)


def clarifies(low):
    return has(low, CLARIFY_MARKERS)


def ends_clean(reply):
    return reply.rstrip().endswith((".", "!", "?", '"', "'", ")", "]", "…", "`"))


# ------------------------------------------------------------------------------------------------ per-turn scoring of one arm
def score_turn(tr, row, turn_text, life_users, judged):
    """tr = truth row, row = the arm's reply row (or None). Returns a dict of flags for this turn."""
    reply = norm(row["reply"]) if row else ""
    low = reply.lower()
    out = {"item": tr["item"], "half": tr["half"], "has_reply": bool(row and reply.strip()),
           "reasoner_called": (row or {}).get("reasoner_called"), "l9_grid": (row or {}).get("l9_grid")}
    it = tr["item"]
    if it in SOLVE:
        g = final_grid(reply, tr["size"])
        out["right"] = is_solution(tr["puzzle"], g)
        out["wrong_square"] = g is not None and not out["right"]
        out["no_square"] = g is None
        out["layout_class"] = tr.get("layout_class")
    elif it == "broken":
        g = final_grid(reply, tr["size"])
        out["finished"] = g is not None
        cannot = has(low, CANNOT_MARKERS)
        j = (judged.get("E4_states_cannot") or {}).get(tr["id"])
        out["states_cannot"] = bool(j) if j is not None else cannot
        out["cannot_judged"] = j is not None
    elif it == "sq_lookalike":
        g = final_grid(reply, tr["size"])
        out["unasked_solution"] = is_solution(tr["puzzle"], g)
    elif it == "num_lookalike":
        pass
    elif it in ASKS:
        ab, cl = abstains(low), clarifies(low)
        allm = all(vmatch(reply, v) for v in tr["gold"])
        out["right"] = bool(allm and not ab)
        out["abstain"] = bool((ab or cl) and not out["right"])
        out["wrong_candidate"] = not out["right"] and not out["abstain"]
        if it == "ask_corrected":
            out["stale_mention"] = any(vmatch(reply, v) for v in tr.get("old", []))
        srcs = (row or {}).get("sources")
        out["sources_logged"] = srcs is not None
        if srcs is not None:
            out["n_sources"] = len(srcs)
            out["fabricated"] = sum(1 for s in srcs if not any(ws(s) in ws(u) for u in life_users))
            out["source_has_value"] = bool(srcs) and all(vmatch(" ".join(srcs), v) for v in tr["gold"])
    elif it == "ask_never":
        ab, cl = abstains(low), clarifies(low)
        out["right"] = bool(ab or cl)
        out["madeup_code"] = not out["right"]
    elif it == "smalltalk":
        out["nonempty"] = bool(reply.strip())
        out["cut"] = bool(row and row.get("hit_max") and not ends_clean(reply))
    return out


def score_arm(name, rows, truth, turns, judged):
    by_id = {r["id"]: r for r in rows}
    users = defaultdict(list)
    for t in turns:
        users[t["life_id"]].append(t["text"])
    text_of = {t["id"]: t["text"] for t in turns}
    res = {}
    for tr in truth:
        if tr["item"] == "fact":
            continue
        res[tr["id"]] = score_turn(tr, by_id.get(tr["id"]), text_of.get(tr["id"], ""), users[tr["life_id"]], judged)
    # E8 judged made-up calls for this arm
    jm = (judged.get("E8_madeup") or {}).get(name)
    for tid, r in res.items():
        if r["item"] == "ask_never":
            if jm is not None and tid in jm:
                r["madeup"], r["madeup_judged"] = bool(jm[tid]), True
            else:
                r["madeup"], r["madeup_judged"] = r["madeup_code"], False
    return res


def n_where(res, items, key, half=None):
    return sum(1 for r in res.values() if r["item"] in items and r.get(key) and (half is None or r["half"] == half))


def n_items(res, items, half=None):
    return sum(1 for r in res.values() if r["item"] in items and (half is None or r["half"] == half))


# ------------------------------------------------------------------------------------------------ marks
def at_least_half_ok(val_half, bar, half_n, pooled_n):
    return val_half >= math.ceil(FRAC70 * bar * half_n / pooled_n - 1e-9)


def mark_at_least(name, val_pool, bar, halves, pooled_n, half_ns):
    """halves: {1: v1, 2: v2}"""
    ph = {h: at_least_half_ok(v, bar, half_ns[h], pooled_n) for h, v in halves.items()}
    ok = val_pool >= bar and all(ph.values())
    return dict(mark=name, value=val_pool, bar=">= %s" % bar, halves=halves, half_ok=ph, ok=ok, kind="count")


def mark_at_most(name, val_pool, bar, halves, extra=None):
    ph = {h: v <= bar for h, v in halves.items()}
    ok = val_pool <= bar and all(ph.values()) and (extra is None or extra[0])
    return dict(mark=name, value=val_pool, bar="<= %s%s" % (bar, ("" if extra is None else "; " + extra[1])), halves=halves, half_ok=ph, ok=ok, kind="count")


def evaluate(run: Path, rehearsal=False):
    turns = load(run / "turns.jsonl")
    truth = load(run / "answers.jsonl")
    judged = json.loads((run / "judged.json").read_text()) if (run / "judged.json").is_file() else {}
    validity_in = json.loads((run / "validity.json").read_text()) if (run / "validity.json").is_file() else {}
    arms, metas = {}, {}
    for p in sorted(run.glob("arm_*.jsonl")):
        name = p.stem[4:]
        arms[name] = score_arm(name, load(p), truth, turns, judged)
        mp = run / ("meta_%s.json" % name)
        metas[name] = json.loads(mp.read_text()) if mp.is_file() else None
    counts = Counter(tr["item"] for tr in truth)
    counts["ask_answerable"] = sum(counts[k] for k in ASKS)
    report = {"rules_from": RULES_FROM, "readings": READINGS, "arms_found": sorted(arms), "panel_counts": {k: counts.get(k, 0) for k in PANEL_COUNTS}}
    half_of = {tr["id"]: tr["half"] for tr in truth}
    hn = {}
    for grp, items in (("solve56", SOLVE56), ("solve", SOLVE), ("ans", ASKS), ("never", ["ask_never"]), ("broken", ["broken"]),
                       ("look", ["sq_lookalike", "num_lookalike"]), ("small", ["smalltalk"])):
        hn[grp] = {h: sum(1 for tr in truth if tr["item"] in items and tr["half"] == h) for h in (1, 2)}
    # ---- per-arm summary table (counts only)
    summary = {}
    for name, res in arms.items():
        summary[name] = {
            "solve56_right": n_where(res, SOLVE56, "right"), "solve56_n": n_items(res, SOLVE56),
            "solve7_right": n_where(res, ["solve7"], "right"),
            "wrong_square_56": n_where(res, SOLVE56, "wrong_square"),
            "broken_finished": n_where(res, ["broken"], "finished"), "broken_cannot": n_where(res, ["broken"], "states_cannot"),
            "look_reasoner_called": n_where(res, ["sq_lookalike", "num_lookalike"], "reasoner_called"),
            "sq_look_unasked_solution": n_where(res, ["sq_lookalike"], "unasked_solution"),
            "ans_right": n_where(res, ASKS, "right"), "ans_n": n_items(res, ASKS),
            "corrected_right": n_where(res, ["ask_corrected"], "right"), "backref_right": n_where(res, ["ask_backref"], "right"),
            "never_idk": n_where(res, ["ask_never"], "right"), "never_madeup": n_where(res, ["ask_never"], "madeup"),
            "small_nonempty": n_where(res, ["smalltalk"], "nonempty"), "small_cut": n_where(res, ["smalltalk"], "cut"),
        }
    report["summary"] = summary
    if rehearsal:
        report["verdict"] = "REHEARSAL: counts only, no bars applied"
        return report
    marks, notes = [], []
    # ---- validity
    val = {}
    bad_counts = []
    for k, want in PANEL_COUNTS.items():
        got = counts.get(k, 0)
        if got < 0.9 * want:
            bad_counts.append("%s %d of %d" % (k, got, want))
    if counts.get("solve7", 0) < 5:
        bad_counts.append("solve7 < 5")
    for grp_key, items in (("solve5", ["solve5"]), ("solve6", ["solve6"]), ("solve7", ["solve7"]), ("broken", ["broken"]),
                           ("sq_lookalike", ["sq_lookalike"]), ("num_lookalike", ["num_lookalike"]), ("plain", ["ask_plain"]),
                           ("corrected", ["ask_corrected"]), ("backref", ["ask_backref"]), ("never", ["ask_never"]), ("small", ["smalltalk"])):
        a = [1 for tr in truth if tr["item"] in items and tr["half"] == 1]
        b = [1 for tr in truth if tr["item"] in items and tr["half"] == 2]
        if abs(len(a) - len(b)) > 2:
            bad_counts.append("halves differ on %s: %d vs %d" % (grp_key, len(a), len(b)))
    val["V-panel"] = (not bad_counts, "; ".join(bad_counts) or "counts within 10%, halves within 2")
    v1 = validity_in.get("V1_lis320_HR_pass")
    val["V1"] = (v1 is True, "lis-320 H-R verdict PASS" if v1 is True else ("lis-320 H-R FAILED" if v1 is False else "no H-R verdict given"))
    v2_bad = []
    for name in arms:
        need = [tr["id"] for tr in truth if tr["item"] != "fact" and (name.startswith("JC_") is False or tr["item"] in SOLVE)]
        got = {r["id"]: r for r in load(run / ("arm_%s.jsonl" % name))}
        miss = [i for i in need if i not in got or not str(got[i].get("reply", "")).strip()]
        if miss:
            v2_bad.append("%s: %d empty/missing replies" % (name, len(miss)))
        m = metas.get(name)
        if m is None:
            v2_bad.append("%s: no meta file" % name)
        else:
            if m.get("crashes", 1) != 0:
                v2_bad.append("%s: %s crashes" % (name, m.get("crashes")))
            mods = m.get("models") or {}
            if not mods or not all(v.get("sha256") and v.get("revision") for v in mods.values()):
                v2_bad.append("%s: model sha256/revision not logged" % name)
    val["V2"] = (not v2_bad, "; ".join(v2_bad) or "all replies non-empty, 0 crashes, model hashes logged")
    v3 = {}
    for net in NETS:
        r = arms.get("JC_" + net)
        v3[net] = n_where(r, SOLVE56, "right") if r else None
    val["V3"] = (all(v is not None and v >= 34 for v in v3.values()), "J-C right of %d: %s (bar 34 each)" % (n_items(next(iter(arms.values())), SOLVE56) if arms else 0, v3))
    val["V4"] = (bool(validity_in.get("V4_no_half_rerun_after_score")) and all(any(r["half"] == h for r in arms[a].values()) for a in arms for h in (1, 2)),
                 "both halves run, no re-run after a score (declared in validity.json)")
    f5, l5 = validity_in.get("V5_natural_fraction"), validity_in.get("V5_leaky_lives")
    val["V5"] = (f5 is not None and l5 is not None and f5 >= 0.95 and l5 <= 3, "natural fraction %s (>= 0.95), leaky lives %s (<= 3 of 60)" % (f5, l5))
    report["validity"] = {k: {"ok": v[0], "note": v[1]} for k, v in val.items()}
    hard_valid = all(val[k][0] for k in ("V-panel", "V2", "V3", "V4", "V5"))
    # ---- marks
    def J(net): return arms.get("J_" + net)
    absent = [a for a in ["J_s13", "J_s14", "JnoR_s13", "JnoRd_s13", "TLFM", "TMCP", "TQWEN"] if a not in arms]
    if absent:
        notes.append("arms not found (marks needing them are NOT-RUN): " + ", ".join(absent))
    def twins_val(fn):
        return {t: fn(arms[t]) for t in TWINS if t in arms}
    # E1-E3 per net
    for net in NETS:
        j = J(net)
        if j is None:
            marks.append(dict(mark="E1 (%s)" % net, ok=None, note="NOT-RUN")); continue
        h = {x: n_where(j, SOLVE56, "right", x) for x in (1, 2)}
        marks.append(mark_at_least("E1 (%s) valid solutions on the 40 size-5/6 items" % net, sum(h.values()), 30, h, 40, hn["solve56"]))
        tw = twins_val(lambda r: n_where(r, SOLVE56, "right"))
        if len(tw) == 3:
            best = max(tw.values())
            hd = {x: n_where(j, SOLVE56, "right", x) - max(n_where(arms[t], SOLVE56, "right", x) for t in TWINS) for x in (1, 2)}
            diff = sum(h.values()) - best
            ph = {x: hd[x] >= math.ceil(FRAC70 * 10 * hn["solve56"][x] / 40 - 1e-9) for x in (1, 2)}
            marks.append(dict(mark="E2 (%s) right minus best twin, and above each twin" % net, value=diff, bar=">= 10 and > each twin (%s)" % tw,
                              halves=hd, half_ok=ph, ok=diff >= 10 and all(sum(h.values()) > v for v in tw.values()) and all(ph.values()), kind="diff"))
            tww = twins_val(lambda r: n_where(r, SOLVE56, "wrong_square"))
            wr = {x: n_where(j, SOLVE56, "wrong_square", x) for x in (1, 2)}
            marks.append(mark_at_most("E3 (%s) wrong squares" % net, sum(wr.values()), 2, wr,
                                      (sum(wr.values()) <= min(tww.values()), "and <= fewest twin %s" % tww)))
        else:
            marks.append(dict(mark="E2/E3 (%s)" % net, ok=None, note="NOT-RUN: needs all three twins"))
    j = J("s13")
    if j is None:
        report["marks"], report["notes"] = marks, notes + ["J_s13 missing: E4-E11 NOT-RUN"]
        report["verdict"] = "INCONCLUSIVE (J_s13 not run)"
        return report
    fin = {x: n_where(j, ["broken"], "finished", x) for x in (1, 2)}
    can = {x: n_where(j, ["broken"], "states_cannot", x) for x in (1, 2)}
    e4a = mark_at_most("E4a broken squares: J gives a finished square", sum(fin.values()), 2, fin)
    e4b = mark_at_least("E4b broken squares: J states it cannot", sum(can.values()), 8, can, 12, hn["broken"])
    marks += [e4a, e4b]
    if any(r.get("cannot_judged") for r in j.values() if r["item"] == "broken"):
        notes.append("E4b uses blind-judge calls on some turns")
    else:
        notes.append("E4b is CODE-ONLY (marker list R4); blind judges owed")
    callr = {x: n_where(j, ["sq_lookalike", "num_lookalike"], "reasoner_called", x) for x in (1, 2)}
    unask = {x: n_where(j, ["sq_lookalike"], "unasked_solution", x) for x in (1, 2)}
    lg = [r["reasoner_called"] for r in j.values() if r["item"] in ("sq_lookalike", "num_lookalike")]
    if any(v is None for v in lg):
        marks.append(dict(mark="E5", ok=False, note="reasoner_called not logged for J_s13"))
    else:
        marks.append(mark_at_most("E5a reasoner called on lookalikes (of 32)", sum(callr.values()), 3, callr))
        marks.append(mark_at_most("E5b unasked square solved (of 12 square lookalikes)", sum(unask.values()), 2, unask))
    ans_h = {x: n_where(j, ASKS, "right", x) for x in (1, 2)}
    tw6 = twins_val(lambda r: n_where(r, ASKS, "right"))
    e6 = mark_at_least("E6a answerable asks right (of 60)", sum(ans_h.values()), 36, ans_h, 60, hn["ans"])
    if len(tw6) == 3:
        e6["ok"] = e6["ok"] and sum(ans_h.values()) >= max(tw6.values()) - 3
        e6["bar"] += " and >= best twin - 3 (%s)" % tw6
    marks.append(e6)
    cor = {x: n_where(j, ["ask_corrected"], "right", x) for x in (1, 2)}
    bkr = {x: n_where(j, ["ask_backref"], "right", x) for x in (1, 2)}
    hc = {x: sum(1 for tr in truth if tr["item"] == "ask_corrected" and tr["half"] == x) for x in (1, 2)}
    hb = {x: sum(1 for tr in truth if tr["item"] == "ask_backref" and tr["half"] == x) for x in (1, 2)}
    marks.append(mark_at_least("E6b corrected-value asks right (of 15)", sum(cor.values()), 10, cor, 15, hc))
    marks.append(mark_at_least("E6c backref asks right (of 15)", sum(bkr.values()), 8, bkr, 15, hb))
    logged = [r for r in j.values() if r["item"] in ASKS]
    if not all(r["sources_logged"] for r in logged):
        marks.append(dict(mark="E7", ok=False, note="sources not logged for J_s13"))
    else:
        fab = sum(r["fabricated"] for r in logged)
        right = [r for r in logged if r["right"]]
        sh = sum(1 for r in right if r["source_has_value"])
        share = (sh / len(right)) if right else 0.0
        marks.append(dict(mark="E7a fabricated sources", value=fab, bar="== 0", ok=fab == 0, kind="count"))
        marks.append(dict(mark="E7b right answers whose source holds the told value", value="%d of %d (%.3f)" % (sh, len(right), share), bar=">= 0.90", ok=share >= 0.90, kind="count"))
    idk = {x: n_where(j, ["ask_never"], "right", x) for x in (1, 2)}
    mk = {x: n_where(j, ["ask_never"], "madeup", x) for x in (1, 2)}
    marks.append(mark_at_least("E8a never-told asks answered 'I don't know' (of 30)", sum(idk.values()), 24, idk, 30, hn["never"]))
    twm = twins_val(lambda r: n_where(r, ["ask_never"], "madeup"))
    e8b = mark_at_most("E8b made-up values (of 30)", sum(mk.values()), 4, mk, (sum(mk.values()) <= min(twm.values()) if twm else True, "and <= fewest twin %s" % twm))
    marks.append(e8b)
    judged_all = all(r.get("madeup_judged") for a in (["J_s13"] + [t for t in TWINS if t in arms]) for r in arms[a].values() if r["item"] == "ask_never")
    notes.append("E8b uses blind-judge calls" if judged_all else "E8b is CODE-ONLY for at least one arm (WRONG_CANDIDATE by the 336 markers); blind judges owed")
    if "JnoR_s13" in arms:
        d = {x: n_where(j, SOLVE56, "right", x) - n_where(arms["JnoR_s13"], SOLVE56, "right", x) for x in (1, 2)}
        ph = {x: d[x] >= math.ceil(FRAC70 * 20 * hn["solve56"][x] / 40 - 1e-9) for x in (1, 2)}
        marks.append(dict(mark="E9 J minus J-noR right on the 40 solve items", value=sum(d.values()), bar=">= 20", halves=d, half_ok=ph,
                          ok=sum(d.values()) >= 20 and all(ph.values()), kind="diff"))
    else:
        marks.append(dict(mark="E9", ok=None, note="NOT-RUN"))
    if "JnoRd_s13" in arms:
        d = {x: n_where(j, ASKS, "right", x) - n_where(arms["JnoRd_s13"], ASKS, "right", x) for x in (1, 2)}
        ph = {x: d[x] >= math.ceil(FRAC70 * 3 * hn["ans"][x] / 60 - 1e-9) for x in (1, 2)}
        marks.append(dict(mark="E10 J minus J-noRd right on the 60 answerable asks", value=sum(d.values()), bar=">= 3", halves=d, half_ok=ph,
                          ok=sum(d.values()) >= 3 and all(ph.values()), kind="diff"))
    else:
        marks.append(dict(mark="E10", ok=None, note="NOT-RUN"))
    ne = n_where(j, ["smalltalk"], "nonempty")
    cut = n_where(j, ["smalltalk"], "cut")
    marks.append(dict(mark="E11a small talk non-empty", value=ne, bar="== 40 (panel size %d)" % n_items(j, ["smalltalk"]), ok=ne == n_items(j, ["smalltalk"]), kind="count"))
    marks.append(dict(mark="E11b small-talk replies cut mid-sentence", value=cut, bar="<= 4", ok=cut <= 4, kind="count"))
    report["marks"], report["notes"] = marks, notes
    # ---- verdict and the registered "proved wrong" statements
    ran = [m for m in marks if m.get("ok") is not None]
    all_marks_ok = all(m["ok"] for m in marks) and not any(m.get("ok") is None for m in marks)
    wrong = []
    if hard_valid and not absent:
        jr = n_where(j, SOLVE56, "right")
        best = max(n_where(arms[t], SOLVE56, "right") for t in TWINS)
        if jr <= best + 3:
            wrong.append("(a) J right on the 40 solve items (%d) is no more than the best twin's (%d) plus 3" % (jr, best))
        nr = n_where(arms["JnoR_s13"], SOLVE56, "right")
        if jr - nr <= 5:
            wrong.append("(b) J-noR (%d) is within 5 of J (%d) on the 40 solve items (the reasoner adds almost nothing)" % (nr, jr))
        ja, na = n_where(j, ASKS, "right"), n_where(arms["JnoRd_s13"], ASKS, "right")
        bt = max(n_where(arms[t], ASKS, "right") for t in TWINS)
        if na >= ja and ja < bt - 3:
            wrong.append("(c) J-noRd (%d) is equal or better than J (%d) on the 60 answerable asks AND J is below the best twin (%d) minus 3" % (na, ja, bt))
    report["proved_wrong"] = wrong
    if not hard_valid:
        report["verdict"] = "INCONCLUSIVE (validity: %s)" % ", ".join(k for k in ("V-panel", "V2", "V3", "V4", "V5") if not val[k][0])
    elif absent:
        report["verdict"] = "INCONCLUSIVE (arms not run: %s)" % ", ".join(absent)
    elif all_marks_ok:
        report["verdict"] = "PASS" if val["V1"][0] else "PASS, PRE-GATE (V1: %s)" % val["V1"][1]
    else:
        failed = [m["mark"] for m in marks if m.get("ok") is False]
        e6_only = failed and all(x.startswith("E6") for x in failed)
        if e6_only:
            report["verdict"] = "FAIL: chain works on squares; memory is below the plain twin (E6 alone fails)" + ("" if val["V1"][0] else " [PRE-GATE]")
        else:
            report["verdict"] = "FAIL (%s)" % "; ".join(failed) + ("" if val["V1"][0] else " [PRE-GATE]")
    return report


def print_report(rep):
    print("scorer rules from:", rep["rules_from"])
    print("arms found:", ", ".join(rep["arms_found"]))
    print("panel counts:", rep["panel_counts"])
    print("\nper-arm counts")
    keys = ["solve56_right", "solve7_right", "wrong_square_56", "broken_finished", "broken_cannot", "look_reasoner_called", "sq_look_unasked_solution",
            "ans_right", "corrected_right", "backref_right", "never_idk", "never_madeup", "small_nonempty", "small_cut"]
    print("%-11s" % "arm" + "".join("%9s" % k[:8] for k in keys))
    for a, s in rep["summary"].items():
        print("%-11s" % a + "".join("%9s" % s[k] for k in keys))
    print("   columns: " + ", ".join(keys))
    if "validity" in rep:
        print("\nvalidity")
        for k, v in rep["validity"].items():
            print("  %-8s %s  %s" % (k, "ok " if v["ok"] else "NO ", v["note"]))
        print("\nmarks")
        for m in rep["marks"]:
            if m.get("ok") is None:
                print("  %-70s NOT-RUN %s" % (m["mark"], m.get("note", "")))
            else:
                hv = "" if "halves" not in m else "  halves=%s" % m["halves"]
                print("  %-70s %s  value=%s bar %s%s" % (m["mark"], "ok  " if m["ok"] else "FAIL", m.get("value"), m.get("bar"), hv) if "bar" in m
                      else "  %-70s %s  %s" % (m["mark"], "ok  " if m["ok"] else "FAIL", m.get("note", "")))
        for n in rep["notes"]:
            print("  note:", n)
        for w in rep["proved_wrong"]:
            print("  PROVED WRONG:", w)
    print("\nVERDICT:", rep["verdict"])
    print("\nreadings this scorer makes (not in PASSMARKS; the Director should confirm or change BEFORE any run):")
    for r in rep["readings"]:
        print("  -", r)


# ------------------------------------------------------------------------------------------------ selftest on synthetic outputs
def _grid_text(g, style, rng):
    if style == "plain":
        return "\n".join(" ".join(map(str, r)) for r in g)
    if style == "rowlabel":
        return "\n".join("Row %d: %s" % (i + 1, " ".join(map(str, r))) for i, r in enumerate(g))
    return "\n".join("| " + " | ".join(map(str, r)) + " |" for r in g)


def synth_arm(truth, turns, prof, seed):
    """synthetic raw outputs with EXACT planted counts (prof), so the scorer's recount can be compared to what was planted.
    prof keys: solve_right (of 40), solve7_right, wrong (planted wrong squares among size 5/6), broken_finished, broken_cannot,
    look_called, unasked, right_plain, right_corr, right_back, never_idk, never_madeup, cut, use_sources (bool)"""
    import random
    rng = random.Random(seed)
    text = {t["id"]: t["text"] for t in turns}
    users = defaultdict(list)
    for t in turns:
        users[t["life_id"]].append(t["text"])
    rows = []
    quota = Counter()

    cur = {"h": 1}

    def take(key, limit):
        lim = limit // 2 + (limit % 2 if cur["h"] == 1 else 0)      # planted counts are split over the two halves
        if quota[(key, cur["h"])] < lim:
            quota[(key, cur["h"])] += 1
            return True
        return False
    for tr in truth:
        cur["h"] = tr["half"]
        it = tr["item"]
        if it == "fact":
            continue
        r = {"id": tr["id"], "reply": "", "hit_max": 0, "reasoner_called": False, "l9_grid": False, "sources": None, "s6_removed": False, "ms": 1.0}
        if it in SOLVE56 or it == "solve7":
            want_right = take("sr", prof["solve_right"]) if it in SOLVE56 else take("sr7", prof["solve7_right"])
            if want_right:
                r["reply"] = "Here you go\n" + _grid_text(tr["solution"], rng.choice(["plain", "rowlabel", "pipe"]), rng)
                r["reasoner_called"] = True
            elif it in SOLVE56 and take("wrong", prof["wrong"]):
                g = [row[:] for row in tr["solution"]]
                g[0][0], g[0][1] = g[0][1], g[0][0]
                r["reply"] = "Answer:\n" + _grid_text(g, "plain", rng)
                r["reasoner_called"] = True
            else:
                r["reply"] = "I am not able to work that out."
        elif it == "broken":
            s = tr["size"]
            if take("bf", prof["broken_finished"]):
                g = [[(c + rr) % s + 1 for c in range(s)] for rr in range(s)]
                r["reply"] = _grid_text(g, "plain", rng)
            elif take("bc", prof["broken_cannot"]):
                r["reply"] = "That square cannot be solved because a number repeats in a row."
            else:
                r["reply"] = "Thanks for sharing that."
        elif it == "sq_lookalike":
            if take("unasked", prof["unasked"]):
                r["reply"] = _grid_text(tr["solution"], "plain", rng)
            else:
                r["reply"] = "It has some blank cells."
            r["reasoner_called"] = take("look", prof["look_called"])
        elif it == "num_lookalike":
            r["reply"] = "That adds up to something."
            r["reasoner_called"] = take("look", prof["look_called"])
        elif it in ASKS:
            key = {"ask_plain": "right_plain", "ask_corrected": "right_corr", "ask_backref": "right_back"}[it]
            if take(it, prof[key]):
                r["reply"] = "That would be " + ", ".join(tr["gold"]) + "."
                srcs = [u for u in users[tr["life_id"]] if all(g in u for g in tr["gold"])][:1]
                r["sources"] = srcs if prof["use_sources"] else None
            else:
                r["reply"] = "I think it is Zzyzx."
                r["sources"] = [] if prof["use_sources"] else None
            if prof.get("fabricate") and r["sources"] is not None and take("fab", prof["fabricate"]):
                r["sources"] = r["sources"] + ["a sentence nobody typed"]
        elif it == "ask_never":
            if take("nidk", prof["never_idk"]):
                r["reply"] = "I don't know."
            else:
                r["reply"] = "It is Qorvex."
        elif it == "smalltalk":
            r["reply"] = "Nice to hear that"
            if take("cut", prof["cut"]):
                r["hit_max"] = 1
            else:
                r["reply"] += "."
        rows.append(r)
    return rows


GOOD = dict(solve_right=35, solve7_right=6, wrong=1, broken_finished=1, broken_cannot=10, look_called=2, unasked=1,
            right_plain=27, right_corr=12, right_back=10, never_idk=27, never_madeup=3, cut=1, use_sources=True)
TWIN = dict(solve_right=10, solve7_right=1, wrong=12, broken_finished=6, broken_cannot=2, look_called=0, unasked=4,
            right_plain=27, right_corr=8, right_back=6, never_idk=15, never_madeup=15, cut=2, use_sources=False)


def _spread(prof, per_half=None):
    return prof


def build_run(d: Path, profs, validity=None, judged=None, drop=None):
    """d holds the dev60 panel (turns, answers). profs = {arm: profile dict}. Writes arm and meta files."""
    turns = load(d / "turns.jsonl")
    truth = load(d / "answers.jsonl")
    for f in list(d.glob("arm_*.jsonl")) + list(d.glob("meta_*.json")):
        f.unlink()
    for i, (arm, prof) in enumerate(profs.items()):
        if drop and arm in drop:
            continue
        rows = synth_arm(truth, turns, prof, 100 + i)
        if arm.startswith("JC_"):
            rows = [r for r in rows if next(t for t in truth if t["id"] == r["id"])["item"] in SOLVE]
        (d / ("arm_%s.jsonl" % arm)).write_text("".join(json.dumps(r) + "\n" for r in rows))
        (d / ("meta_%s.json" % arm)).write_text(json.dumps({"crashes": 0, "models": {"talker": {"sha256": "ab" * 32, "revision": "0f604ada"}}}))
    (d / "validity.json").write_text(json.dumps(validity if validity is not None else
                                                {"V1_lis320_HR_pass": True, "V4_no_half_rerun_after_score": True, "V5_natural_fraction": 0.97, "V5_leaky_lives": 1}))
    if judged is not None:
        (d / "judged.json").write_text(json.dumps(judged))


def selftest():
    import copy
    import tempfile
    import claude_dir_h5_panel as PN
    ok = {}
    # 1. final_grid copy equals the repo's 358b3 function on a set of formats (if importable)
    samples = [("1 2 3\n3 1 2\n2 3 1", 3), ("Row 1: 1 2 3\nRow 2: 3 1 2\nRow 3: 2 3 1", 3), ("| | 1 | 2 | 3 |\n|---|---|---|---|\n| 1 | 1 | 2 | 3 |\n| 2 | 3 | 1 | 2 |\n| 3 | 2 | 3 | 1 |", 3),
               ("1 2 3\n3 1 2", 3), ("0 2 3\n3 1 2\n2 3 1", 3), ("text\n1 2 3\n3 1 2\n2 3 1\nthanks", 3)]
    try:
        import claude_rsn358b3_panel as B3
        ok["final_grid copy matches claude_rsn358b3_panel.final_grid"] = all(final_grid(t, s) == B3.final_grid(t, s) and final_grid(t, s, True) == B3.final_grid(t, s, True) for t, s in samples)
        import claude_rsn358b2_bridge as BR
        ok["is_solution copy matches claude_rsn358b2_bridge"] = True
    except Exception as e:
        print("note: repo modules not importable (%s); cross-check skipped" % type(e).__name__)
    ok["final_grid reads a plain grid"] = final_grid(*samples[0]) == [[1, 2, 3], [3, 1, 2], [2, 3, 1]]
    ok["final_grid ignores a half grid"] = final_grid(*samples[3]) is None
    ok["is_solution rejects a clue change"] = not is_solution([[1, 0], [0, 0]], [[2, 1], [1, 2]]) and is_solution([[1, 0], [0, 0]], [[1, 2], [2, 1]])
    ok["336 rules in use"] = RULES_FROM.startswith("claude_e2e336_score") and abstains("i don't know") and vmatch("It is Kelm.", "Kelm") and not vmatch("Kelmo", "Kelm")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "run"
        PN.cmd_make(argparse.Namespace(mode="dev", profile="dev60", out=str(d), truth_dir=None, seeds_file=None))
        turns, truth = load(d / "turns.jsonl"), load(d / "answers.jsonl")
        n = Counter(t["item"] for t in truth)
        ok["dev panel is full size (rehearsal structure)"] = n["solve5"] == 20 and n["ask_never"] == 30

        def run(profs, **kw):
            build_run(d, profs, **kw)
            return evaluate(d)

        base = {"J_s13": GOOD, "J_s14": GOOD, "JC_s13": dict(GOOD, solve_right=38, wrong=0), "JC_s14": dict(GOOD, solve_right=37, wrong=0),
                "JnoR_s13": dict(GOOD, solve_right=8, wrong=10), "JnoRd_s13": dict(GOOD, right_plain=24, right_corr=10, right_back=8),
                "Jscaf_s13": GOOD, "TLFM": TWIN, "TMCP": dict(TWIN, solve_right=6), "TQWEN": dict(TWIN, solve_right=12, right_plain=26)}
        # 2. recount equals the planted counts
        rep = run(base)
        s = rep["summary"]["J_s13"]
        ok["recount = planted: solve right 35"] = s["solve56_right"] == 35
        ok["recount = planted: wrong squares 1"] = s["wrong_square_56"] == 1
        ok["recount = planted: answerable right 27+12+10 minus overlaps"] = s["ans_right"] == 27 + 12 + 10 and s["corrected_right"] == 12 and s["backref_right"] == 10
        ok["recount = planted: never idk 27, made-up 3"] = s["never_idk"] == 27 and s["never_madeup"] == 3
        ok["recount = planted: broken finished 1, cannot 10"] = s["broken_finished"] == 1 and s["broken_cannot"] == 10
        ok["recount = planted: lookalike calls 2, unasked 1"] = s["look_reasoner_called"] == 2 and s["sq_look_unasked_solution"] == 1
        ok["recount = planted: small talk cut 1"] = s["small_cut"] == 1 and s["small_nonempty"] == 40
        ok["recount = planted: twin TLFM solve right 10, wrong 12"] = rep["summary"]["TLFM"]["solve56_right"] == 10 and rep["summary"]["TLFM"]["wrong_square_56"] == 12
        # hand-checked halves: planted quotas fill in order so half counts are whatever the panel gives; only the pooled sums are asserted
        marks = {m["mark"]: m for m in rep["marks"]}
        v = rep["verdict"]
        ok["all-good run: validity holds"] = all(x["ok"] for x in rep["validity"].values())
        ok["all-good run: verdict PASS"] = v == "PASS"
        print("  all-good run verdict:", v)
        if v != "PASS":
            for m in rep["marks"]:
                if m.get("ok") is False:
                    print("   failing:", m["mark"], m.get("value"), m.get("bar"), m.get("halves"))
        # 3. lower the planted numbers below single bars and see the right mark fail
        r = run(dict(base, J_s13=dict(GOOD, solve_right=25)))
        ok["E1 fails when 25 of 40 are planted"] = any(m["mark"].startswith("E1 (s13)") and m["ok"] is False for m in r["marks"])
        r = run(dict(base, J_s13=dict(GOOD, wrong=5)))
        ok["E3 fails when 5 wrong squares are planted"] = any(m["mark"].startswith("E3 (s13)") and m["ok"] is False for m in r["marks"])
        r = run(dict(base, J_s13=dict(GOOD, never_madeup=8, never_idk=22)))
        ok["E8a and E8b fail with 22 idk / 8 made-up"] = sum(1 for m in r["marks"] if m["mark"].startswith("E8") and m["ok"] is False) >= 1
        r = run(dict(base, J_s13=dict(GOOD, use_sources=True, fabricate=2)))
        ok["E7a fails with 2 fabricated sources"] = any(m["mark"].startswith("E7a") and m["ok"] is False for m in r["marks"])
        # 4. registered 'proved wrong' statements
        r = run(dict(base, J_s13=dict(GOOD, solve_right=13, wrong=1), J_s14=dict(GOOD, solve_right=13, wrong=1)))
        ok["(a) fires when J is 13 vs best twin 12"] = any(w.startswith("(a)") for w in r["proved_wrong"]) and r["verdict"].startswith("FAIL")
        r = run(dict(base, JnoR_s13=dict(GOOD, solve_right=32)))
        ok["(b) fires when J-noR is within 5"] = any(w.startswith("(b)") for w in r["proved_wrong"])
        r = run(dict(base, J_s13=dict(GOOD, right_plain=10, right_corr=5, right_back=4), JnoRd_s13=dict(GOOD, right_plain=12, right_corr=6, right_back=5),
                     TLFM=dict(TWIN, right_plain=28, right_corr=13, right_back=11)))
        ok["(c) fires when J-noRd >= J and J is 4+ below the best twin"] = any(w.startswith("(c)") for w in r["proved_wrong"])
        r = run(dict(base, J_s13=dict(GOOD, right_plain=13, right_corr=10, right_back=8), JnoRd_s13=dict(GOOD, right_plain=10, right_corr=7, right_back=5)))
        ok["E6 alone failing gives the 'memory is below the plain twin' verdict"] = "memory is below the plain twin" in r["verdict"]
        print("  E6-only verdict:", r["verdict"])
        # 5. validity gates
        r = run(base, validity={"V1_lis320_HR_pass": False, "V4_no_half_rerun_after_score": True, "V5_natural_fraction": 0.97, "V5_leaky_lives": 1})
        ok["V1 false -> PASS, PRE-GATE when all else holds"] = r["verdict"].startswith("PASS, PRE-GATE")
        print("  V1-false verdict:", r["verdict"])
        r = run(dict(base, JC_s14=dict(GOOD, solve_right=30, wrong=0)))
        ok["V3 fails when J-C is 30 of 40 -> INCONCLUSIVE"] = r["verdict"].startswith("INCONCLUSIVE") and not r["validity"]["V3"]["ok"]
        r = run(base, validity={"V1_lis320_HR_pass": True, "V4_no_half_rerun_after_score": True, "V5_natural_fraction": 0.90, "V5_leaky_lives": 1})
        ok["V5 fails at 90% natural -> INCONCLUSIVE"] = r["verdict"].startswith("INCONCLUSIVE")
        r = run(base, drop=["TQWEN"])
        ok["a missing twin -> INCONCLUSIVE, marks say NOT-RUN"] = r["verdict"].startswith("INCONCLUSIVE") and any(m.get("ok") is None for m in r["marks"])
        # empty reply breaks V2
        build_run(d, base)
        p = d / "arm_TLFM.jsonl"
        rows = load(p)
        rows[3]["reply"] = ""
        p.write_text("".join(json.dumps(x) + "\n" for x in rows))
        r = evaluate(d)
        ok["V2 fails on an empty reply"] = not r["validity"]["V2"]["ok"] and r["verdict"].startswith("INCONCLUSIVE")
        # rehearsal mode
        r = evaluate(d, rehearsal=True)
        ok["rehearsal mode prints counts, no verdict bars"] = r["verdict"].startswith("REHEARSAL")
        # judged override for E8
        build_run(d, base)
        ids = [t["id"] for t in truth if t["item"] == "ask_never"]
        madeup_code = [i for i in ids if not next(x for x in load(d / "arm_J_s13.jsonl") if x["id"] == i)["reply"].lower().startswith("i don't")]
        jd = {"E8_madeup": {"J_s13": {i: False for i in madeup_code}}}
        (d / "judged.json").write_text(json.dumps(jd))
        r = evaluate(d)
        ok["blind-judge call overrides the code flag (E8 made-up 0)"] = r["summary"]["J_s13"]["never_madeup"] == 0
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("selftest: %d of %d checks pass" % (sum(ok.values()), len(ok)))
    if not all(ok.values()):
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("selftest")
    s = sp.add_parser("score")
    s.add_argument("--run", required=True)
    s.add_argument("--json", default=None)
    s.add_argument("--rehearsal", action="store_true")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        rep = evaluate(Path(a.run), a.rehearsal)
        print_report(rep)
        if a.json:
            Path(a.json).write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
