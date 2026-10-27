#!/usr/bin/env python3
"""Think-1 summary: reads result_*.json and applies the PREREG.md marks (G, R1-R4, wrong-if, futility, M1, M2, verdict).

  python backbone/think/summarize.py out/think [--data out/data] [--json] [--cluster {row,visit}]

Accuracies are percent. Differences between arms are paired on the same validation rows (hits are stored per row in file
order); depth / bank / qtype slices come from the data files. Paired bootstrap: 2,000 resamples, fixed seed, 95% interval.
Marks that need seeds 0-2 say "not-enough-data" until all three are in.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from pathlib import Path

import numpy as np

SEEDS = (0, 1, 2)
FLOOR_A, FLOOR_B = 66.72, 67.12
GAIN, SLOPE, SLOPE_SEED, TOL_MIN = 3.0, 1.5, 0.5, 0.3
COLLAPSE, COLLAPSE_SEED, LAP_NEED, REPEAT_NEED = 1.0, 2.0, 2.0, 1.0
W_T1, W_LAP2, W_SWAP, W_FLOOR = 1.0, 0.5, 1.0, 1.0
FUT_ACC = 68.0
M1_NEED, M2_NEED = 3.0, 2.0
CHAIN = ("q.where_before", "q.plan_get")
LAPS = (0, 1, 2, 4, 8, 12, 16, 24)
BOOT_N, BOOT_SEED, EPS = 2000, 20261024, 1e-9
ARMS = ("a", "b", "aplus", "bplus", "t", "t1", "tw")
HEAD = {"a": "main", "b": "main", "aplus": "main", "bplus": "main", "t": "L8", "t1": "L1", "tw": "L1", "tj": "L4", "tf": "L4", "tc": "L0",
        "ws": "T", "wsham": "T", "tsd": "L4", "tsd1": "L1", "br": "main", "aplong": "main"}
ALIAS = {"rep18": ("repeatdelta18", "repeat8", "rep8"), "gatesoff8": ("gatesoff",), "swap8": ("swap",), "mean8": ("meanboard8",)}
ND = "not-enough-data"
T2_P1, T2_P2, T2_P3, T2_W1, T2_W2 = 2.0, 1.0, 0.5, 1.0, 0.5  # PREREG-think2.md lines 30-32 (P1-P3) and 40-42 (wrong-if); seed 0 only
# codi-plan P1 (written steps, arms ws / wsham) and P2b (step-supervised notes, arms tsd / tsd1); all in points, fixed before any run
P1_OPEN, P1_SHAM, P1_WRONG, P1_REF74 = 2.0, 1.0, 0.5, 74.6
P2_A, P2_A_WRONG, P2_C, P2_C_WRONG, P2_D, P2_D_WRONG = 2.0, 0.5, 1.0, 0.3, 10.0, 2.0
# Addendum F (arm br: the block's own layers looped, random loop counts in training; aplong: LoRA given br's extra layer passes as steps)
F1_GAIN, F1_WRONG, F2_RISE, F2_WRONG, F2_KEEP = 2.0, 0.5, 2.0, 0.5, 1.0
H1_KEEP, H1_FRAC, H2_RISE, H_WRONG_RHO = 0.5, 0.6, 1.0, 0.1
USED, UNUSED, SEED_BAND = 1.0, 0.3, 1.0  # a lesion is "used" at a cost >= 1.0 with a 95% interval excluding 0, "unused" below 0.3; a margin inside +-1 point needs seeds 2-3


# ---------------------------------------------------------------- loading

def norm_tag(t):
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


def decode_hits(s):
    a = np.frombuffer(s.encode("ascii"), dtype=np.uint8)
    if len(a) and not np.isin(a, (48, 49)).all():
        raise ValueError("hits must be a string of 0/1")
    return (a - 48).astype(np.float64)


def load_results(root):
    """{(arm, seed): result} from every result_*.json under root, plus notes on files that were skipped."""
    res, notes, stamp = {}, [], {}
    for p in sorted(Path(root).rglob("result_*.json")):
        try:
            r = json.loads(p.read_text())
        except Exception as e:
            notes.append(f"skipped {p}: {e}")
            continue
        if not isinstance(r, dict) or "arm" not in r or "seed" not in r or ("eval" not in r and not r.get("aborted")):
            notes.append(f"skipped {p}: not a Think-1 result file")
            continue
        key = (r["arm"], int(r["seed"]))
        if key in res:
            old_lab, new_lab = res[key].get("source") == "label", r.get("source") == "label"
            if old_lab != new_lab:  # from_label.py output (0.1-point rounding, no hits) never replaces a real result file
                notes.append(f"{key[0]} seed {key[1]}: using the real result file; ignoring the label-rebuilt one ({p if new_lab else stamp[key]})")
                if new_lab:
                    continue
                res[key], stamp[key] = r, str(p)
                continue
            notes.append(f"two files for {key[0]} seed {key[1]}: using the newer of {stamp[key]} and {p}")
            if p.stat().st_mtime < Path(stamp[key]).stat().st_mtime:
                continue
        res[key], stamp[key] = r, str(p)
    return res, notes


def load_rows(path):
    if not Path(path).is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class Runs:
    def __init__(self, res):
        self.res = res

    def entry(self, arm, seed, split, tag):
        r = self.res.get((arm, seed))
        if not r or r.get("aborted"):
            return None
        d = (r.get("eval") or {}).get(split) or {}
        want = norm_tag(tag)
        names = {want, *ALIAS.get(want, ()), want.replace("l", "", 1) if re.fullmatch(r"l\d+", want) else want}
        for k, v in d.items():
            if norm_tag(k) in names:
                return v
        return None

    def vec(self, arm, seed, split, tag):
        e = self.entry(arm, seed, split, tag)
        if e is None or not e.get("hits"):
            return None
        return int(e.get("row_offset", 0)), decode_hits(e["hits"])

    def acc(self, arm, seed, split, tag):
        e = self.entry(arm, seed, split, tag)
        if e is None:
            return None
        v = self.vec(arm, seed, split, tag)
        return 100 * float(v[1].mean()) if v is not None and len(v[1]) else 100 * float(e["acc"])

    def by_seed(self, arm, tag, split="validation"):
        return {s: a for s in SEEDS if (a := self.acc(arm, s, split, tag)) is not None}

    def rowvec(self, arm, tag, split="validation", seeds=SEEDS):
        vs = [v for s in seeds if (v := self.vec(arm, s, split, tag)) is not None]
        if not vs:
            return None
        al = align(*vs)
        return None if al is None else (al[0], np.mean(al[1], 0))


def align(*vs):
    lo, hi = max(o for o, _ in vs), min(o + len(a) for o, a in vs)
    return None if hi <= lo else (lo, [a[lo - o:hi - o] for o, a in vs])


def mean(d):
    return float(np.mean(list(d.values()))) if d else None


def have(d):
    return all(s in d for s in SEEDS)


# ---------------------------------------------------------------- statistics

def boot(vecs, fn, units=None, n=BOOT_N, seed=BOOT_SEED):
    """Paired bootstrap 95% interval of fn(percent means). Every vector is resampled with the same rows (or story units)."""
    keys = list(vecs)
    N = len(vecs[keys[0]])
    if N < 2:
        return None
    inv = np.arange(N) if units is None else np.unique(units, return_inverse=True)[1].reshape(-1)
    U = int(inv.max()) + 1
    cnt = np.bincount(inv, minlength=U).astype(float)
    sums = {k: np.bincount(inv, weights=np.asarray(v, float), minlength=U) for k, v in vecs.items()}
    rng = np.random.default_rng(seed)
    out = []
    for c in range(0, n, 200):
        idx = rng.integers(0, U, size=(min(200, n - c), U))
        den = cnt[idx].sum(1)
        out.append(fn({k: 100 * s[idx].sum(1) / den for k, s in sums.items()}))
    v = np.concatenate(out)
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


class Stats:
    def __init__(self, runs, rows, cluster="row"):
        self.runs, self.rows, self.cluster = runs, rows, cluster
        self.units = np.array([r.get("visit_id", i) for i, r in enumerate(rows)]) if rows and cluster == "visit" else None

    def stat(self, parts, fn, sel=None, ci=True):
        """parts: name -> (offset, row vector) or None. Returns {value, lo, hi, n} for fn(percent means), or None."""
        if not parts or any(v is None for v in parts.values()):
            return None
        al = align(*parts.values())
        if al is None:
            return None
        lo, arrs = al
        n = len(arrs[0])
        keep = np.ones(n, bool)
        if sel is not None:
            if len(sel) < lo + n:
                return None
            keep = np.asarray(sel[lo:lo + n], bool)
        if keep.sum() < 1:
            return None
        vecs = {k: a[keep] for k, a in zip(parts, arrs)}
        out = {"value": float(fn({k: 100 * v.mean() for k, v in vecs.items()})), "lo": None, "hi": None, "n": int(keep.sum())}
        if ci:
            u = None if self.units is None or len(self.units) < lo + n else self.units[lo:lo + n][keep]
            b = boot(vecs, fn, u)
            if b:
                out["lo"], out["hi"] = b
        return out

    def diff(self, x, y, sel=None, ci=True):
        return self.stat({"x": x, "y": y}, lambda m: m["x"] - m["y"], sel, ci)


def ge(x, y):
    return x >= y - EPS


def decide(ok):
    return ND if ok is None else ("PASS" if ok else "FAIL")


def trig(c):
    return ND if c is None else ("triggered" if c else "clear")


def group(parts):
    st = [p["status"] for p in parts]
    return "FAIL" if "FAIL" in st else (ND if ND in st else "PASS")


# ---------------------------------------------------------------- analysis

PARENT = {"br": "a", "aplong": "a", "aplus": "a", "t": "a", "t1": "a", "tw": "a", "tj": "a", "tf": "a", "tc": "a", "bplus": "b", "ws": "a", "wsham": "a", "tsd": "a", "tsd1": "a"}  # the stage-1 arm whose adapter each arm starts from
BPLUS_EXTEND = 1.0  # PREREG: bplus on all seeds only if bplus - b (seed 0) >= 1.0


def drop_unmatched(res):
    """(kept results, excluded list). A dependent whose recorded stage-1 adapter hash differs from the hash its stage-1 arm's result
    carries was trained on another copy of that adapter (the stage-1 arm was retrained afterwards): excluded from every mark.
    Results without hashes are kept."""
    keep, out = {}, []
    for (arm, seed), r in res.items():
        par = res.get((PARENT.get(arm), seed))
        h, ph = r.get("stage1_adapter_sha"), (par or {}).get("adapter_sha")
        if h and ph and h != ph:
            out.append({"arm": arm, "seed": seed, "sha": h[:12], "parent": PARENT[arm], "parent_sha": ph[:12]})
        else:
            keep[(arm, seed)] = r
    return keep, out


def think2(R, st, lab):
    """PREREG-think2 marks for arms tj and tf (seed 0, L_max 4). P1 is judged against max(aplus, tc): the harder (smaller) diff."""
    out = {}

    def cmp(a, tag, v4, s4):
        o = R.acc(a, 0, "validation", tag)
        if o is None:
            return None
        ov = None if lab else R.rowvec(a, tag, seeds=(0,))
        d = st.diff(v4, ov) if v4 and ov else None
        return d or {"value": s4 - o, "lo": None, "hi": None, "n": None}

    for arm in ("tj", "tf"):
        s4 = R.acc(arm, 0, "validation", "L4")
        if s4 is None:
            continue
        v4 = None if lab else R.rowvec(arm, "L4", seeds=(0,))
        c = lambda a, tag: cmp(a, tag, v4, s4)
        tag_c = next((t for t in ("L0", "main") if R.entry("tc", 0, "validation", t)), None)
        d_ap, d_tc = c("aplus", "main"), tag_c and c("tc", tag_c)
        d_sw, d_l1 = c(arm, "swap4"), c(arm, "L1")
        p1src = [(n, d) for n, d in (("aplus", d_ap), ("tc", d_tc)) if d]
        hard = min(p1src, key=lambda x: x[1]["value"]) if p1src else None
        d1 = hard and hard[1]
        p1 = ND if not d1 else ("FAIL" if d1["value"] < T2_P1 - EPS else ND if d1["lo"] is None else "PASS" if d1["lo"] > 0 else "FAIL")
        p2 = decide(None if not d_sw else ge(d_sw["value"], T2_P2))
        p3 = decide(None if not d_l1 else ge(d_l1["value"], T2_P3))
        w = [None if not d1 else d1["value"] < T2_W1 - EPS, None if not d_sw else d_sw["value"] < T2_W2 - EPS]
        wi = trig(True if True in w else (False if w == [False, False] else None))
        dec = "stop" if "FAIL" in (p1, p2) else "run seeds 1 and 2 for this arm" if p1 == p2 == "PASS" else ND
        out[arm] = {"S4": s4, "S1": R.acc(arm, 0, "validation", "L1"), "swap4": R.acc(arm, 0, "validation", "swap4"),
                    "gatesoff4": R.acc(arm, 0, "validation", "gatesoff4"), "aplus": R.acc("aplus", 0, "validation", "main"),
                    "tc": tag_c and R.acc("tc", 0, "validation", tag_c), "tc_present": tag_c is not None,
                    "S4_minus_aplus": d_ap, "S4_minus_tc": d_tc, "P1_vs": hard and hard[0], "P1_diff": d1, "S4_minus_swap4": d_sw,
                    "S4_minus_L1": d_l1, "S4_minus_blind4": c(arm, "blind4") if arm == "tf" else None,
                    "P1": {"status": p1, "need": T2_P1, "ci_excludes_0": True}, "P2": {"status": p2, "need": T2_P2},
                    "P3": {"status": p3, "need": T2_P3, "available": d_l1 is not None}, "wrong_if": wi, "decision": dec}
    return out


def seed_rule(items, n):
    """codi-plan 6.0. items = (margin, wrong_margin) for each ACCURACY pass condition: margin = value - pass bar, wrong_margin = value - proved-wrong bar (None if
    the condition has none). A condition is settled if it is met by >= 1 point or missed by >= 1 point, or already sits on the proved-wrong side. All settled ->
    decide on the seeds in (seed 1); otherwise seeds 2-3 are owed, and with all three in the 3-seed means decide. Lesion costs and the decoder gap do not count."""
    if any(m is None for m, _ in items):
        return ND
    if n >= 3:
        return "3-seed means"
    if any(w is not None and w < 0 for _, w in items):  # one condition already proved wrong closes the proposition: more seeds cannot change the outcome
        return f"decided on {n} seed(s)"
    settled = all(abs(m) >= SEED_BAND - EPS for m, w in items)
    return f"decided on {n} seed(s)" if settled else "needs seeds 2-3"


def common(R, arms_tags, split="validation"):
    """Seeds at which every (arm, tag) has a result, and the mean accuracy of each over them: ({key: mean}, seeds)."""
    seeds = [sd for sd in SEEDS if all(R.acc(a, sd, split, t) is not None for a, t in arms_tags.values())]
    return {k: float(np.mean([R.acc(a, sd, split, t) for sd in seeds])) for k, (a, t) in arms_tags.items()} if seeds else {}, seeds


def tc_tag(R):
    return next((t for t in ("L0", "main") if any(R.entry("tc", sd, "validation", t) for sd in SEEDS)), "L0")


def by_depth(st, rows, vecs, lab):
    """{slice: {name: percent}} for named row vectors over depth 0, 1..6, 1-3 and 4-6 (no pass mark)."""
    if lab or not rows or any(v is None for v in vecs.values()):
        return None
    depth = np.array([r.get("depth") if r.get("depth") is not None else -1 for r in rows])
    out = {}
    for name, sel in (("depth 0", depth == 0), *((f"depth {d}", depth == d) for d in range(1, 7)), ("depth 1-3", (depth >= 1) & (depth <= 3)), ("depth 4-6", depth >= 4)):
        if not sel.any():
            continue
        vals = {k: st.stat({"x": v}, lambda m: m["x"], sel, ci=False) for k, v in vecs.items()}
        out[name] = {"n": int(sel.sum()), **{k: v and v["value"] for k, v in vals.items()}}
    return out


def lesion(st, vs, vl, cost):
    """'used' / 'unused' / 'not shown' for one lesion (cost = score - lesioned score, paired 95% interval of the same difference)."""
    if cost is None:
        return {"status": ND, "cost": None, "lo": None, "hi": None}
    d = st.diff(vs, vl) if vs is not None and vl is not None else None
    lo, hi = (d["lo"], d["hi"]) if d else (None, None)
    status = "used" if cost >= USED - EPS and lo is not None and lo > 0 else "unused" if cost < UNUSED - EPS else "not shown"
    return {"status": status, "cost": cost, "lo": lo, "hi": hi}


def p1(R, st, rows, lab):
    """codi-plan P1. T = ws writes its steps then the answer; C1 = the same weights answering directly; sham = wsham written (filler); C0' = tc."""
    tg = tc_tag(R)
    m, seeds = common(R, {"T": ("ws", "T"), "C1": ("ws", "C1"), "sham": ("wsham", "T"), "tc": ("tc", tg)})
    if not seeds:
        return {"status": ND, "why": "needs ws, wsham and tc at one seed"} if {"ws", "wsham"} & {a for a, _ in R.res} else None
    ref = max(m["tc"], m["C1"])
    vec = (lambda a, t: None) if lab else (lambda a, t: R.rowvec(a, t, seeds=tuple(seeds)))
    vT, vC1, vsh, vtc = vec("ws", "T"), vec("ws", "C1"), vec("wsham", "T"), vec("tc", tg)
    d_ref = st.stat({"T": vT, "C1": vC1, "tc": vtc}, lambda x: x["T"] - np.maximum(x["C1"], x["tc"])) if None not in (vT, vC1, vtc) else None
    d_sh = st.diff(vT, vsh) if vT is not None and vsh is not None else None
    a, b = m["T"] - ref, m["T"] - m["sham"]
    opens = a >= P1_OPEN - EPS and b >= P1_SHAM - EPS
    wrong = a < P1_WRONG - EPS
    if opens:
        outcome = "PASS: P4 opens"
    elif wrong:
        outcome = "PROVED WRONG: written steps teach this model nothing (P4 closes; the loop line does not)"
    elif a >= P1_OPEN - EPS:
        outcome = "extra positions help; content not shown (P4 stays closed)"
    else:
        outcome = "not shown (P4 stays closed)"
    gen = {arm: [(R.entry(arm, sd, "validation", "T") or {}).get("mean_gen_tokens") for sd in seeds] for arm in ("ws", "wsham")}
    fmt = {arm: [(R.entry(arm, sd, "validation", "fmt") or {}).get("acc") for sd in seeds] for arm in ("ws", "wsham")}
    marker = [(R.entry("ws", sd, "validation", "T") or {}).get("marker_rate") for sd in seeds]
    return {"status": "computed", "seeds": seeds, "T": m["T"], "C1": m["C1"], "sham": m["sham"], "C0": m["tc"], "ref": ref, "ref_name": "tc" if m["tc"] >= m["C1"] else "C1",
            "T_minus_ref": a, "T_minus_sham": b, "T_vs_74_6": m["T"] - P1_REF74, "ci_ref": d_ref, "ci_sham": d_sh, "opens_P4": opens, "wrong": wrong, "outcome": outcome,
            "seed_rule": seed_rule([(a - P1_OPEN, a - P1_WRONG), (b - P1_SHAM, None)], len(seeds)),
            "mean_gen_tokens": {k: [None if x is None else float(x) for x in v] for k, v in gen.items()},
            "marker_rate": [None if x is None else float(x) for x in marker],
            "format_check": {k: [None if x is None else 100 * float(x) for x in v] for k, v in fmt.items()},
            "by_depth": by_depth(st, rows, {"T": vT, "C1": vC1, "sham": vsh, "tc": vtc}, lab)}


def p2b(R, st, rows, lab):
    """codi-plan P2b. S = tsd at lap 4, against max(tc, C1) and the one-lap arm tsd1; lesions on S; decoder step-token gap from the result files."""
    tg = tc_tag(R)
    m, seeds = common(R, {"S": ("tsd", "L4"), "tc": ("tc", tg), "C1": ("ws", "C1"), "S1": ("tsd1", "L1"), "swap": ("tsd", "swap4"), "random": ("tsd", "random4")})
    if not seeds:
        return {"status": ND, "why": "needs tsd (with swap4 and random4), tsd1, tc and ws (for C1) at one seed"} if {"tsd", "tsd1"} & {a for a, _ in R.res} else None
    ref = max(m["tc"], m["C1"])
    zero = [R.acc("tsd", sd, "validation", "zero4") for sd in seeds]
    gaps = [((R.res.get(("tsd", sd)) or {}).get("decoder") or {}).get("gap") for sd in seeds]
    dec = [(R.res.get(("tsd", sd)) or {}).get("decoder") or {} for sd in seeds]
    gap = None if any(g is None for g in gaps) else float(np.mean(gaps))
    vec = (lambda a, t: None) if lab else (lambda a, t: R.rowvec(a, t, seeds=tuple(seeds)))
    vS, vC1, vtc, vS1 = vec("tsd", "L4"), vec("ws", "C1"), vec("tc", tg), vec("tsd1", "L1")
    les = {k: lesion(st, vS, vec("tsd", f"{k}4"), m["S"] - m[k]) for k in ("swap", "random")}
    les["zero"] = lesion(st, vS, vec("tsd", "zero4"), None if None in zero else m["S"] - float(np.mean(zero)))
    a, c = m["S"] - ref, m["S"] - m["S1"]
    d_ref = st.stat({"S": vS, "C1": vC1, "tc": vtc}, lambda x: x["S"] - np.maximum(x["C1"], x["tc"])) if None not in (vS, vC1, vtc) else None
    d_one = st.diff(vS, vS1) if vS is not None and vS1 is not None else None
    pa, pb, pc = a >= P2_A - EPS, les["swap"]["status"] == "used" and les["random"]["status"] == "used", c >= P2_C - EPS
    pd = None if gap is None else gap >= P2_D - EPS
    wrong = [n for n, hit in (("a: arm < max(tc, C1) + 0.5", a < P2_A_WRONG - EPS), ("swap unused", les["swap"]["status"] == "unused"),
                              ("decoder gap < 2", gap is not None and gap < P2_D_WRONG - EPS), ("arm < one-lap arm + 0.3", c < P2_C_WRONG - EPS)) if hit]
    one_shot = bool(pa and pb and pd and not pc)
    note = "one-shot side module with step targets helps, looping not shown (counts as a fail for the give-up rule)"
    if pa and pb and pc and pd:
        outcome = "PASS"
    elif wrong:
        outcome = "PROVED WRONG: " + "; ".join(wrong) + ("; separate finding: " + note if one_shot else "")
    elif one_shot:
        outcome = note
    else:
        outcome = "not shown"
    margins = [(a - P2_A, a - P2_A_WRONG), (c - P2_C, c - P2_C_WRONG)]  # the accuracy pass conditions (a) and (c) only
    return {"status": "computed", "seeds": seeds, "S": m["S"], "tc": m["tc"], "C1": m["C1"], "ref": ref, "tsd1": m["S1"], "swap": m["swap"], "random": m["random"],
            "zero": None if None in zero else float(np.mean(zero)), "S_minus_ref": a, "S_minus_tsd1": c, "ci_ref": d_ref, "ci_one": d_one, "lesions": les,
            "decoder": {"gap": gap, "true": [d.get("true") for d in dec], "swap": [d.get("swap") for d in dec], "tokens": [d.get("tokens") for d in dec]},
            "conditions": {"a": pa, "b": pb, "c": pc, "d": pd}, "one_shot": one_shot, "wrong_by": wrong, "outcome": outcome,
            "swapped_score_vs_C0": m["swap"] - m["tc"], "P3_entry": bool(pd) and les["swap"]["status"] != "used",
            "seed_rule": seed_rule(margins, len(seeds)), "by_depth": by_depth(st, rows, {"S": vS, "tsd1": vS1, "C1": vC1, "tc": vtc}, lab)}


def pbr(R, st, rows, lab):
    """Addendum F. F1: br at 4 loops - max(aplus, tc, aplong) >= +2.0 (interval above 0); proved wrong below +0.5. F2 (depth 4-6, beyond train depth):
    S(r4) - S(r1) >= +2.0 (interval above 0) and S(r8) >= S(r4) - 1.0; proved wrong if S(r4) - S(r1) < +0.5. Halting (Addendum E, judged only if F1 and F2
    pass): H1 answer-stable halting keeps accuracy within 0.5 of S(r4) at mean loops <= 0.6 x 8; H2 depth 4-6 uses >= 1.0 more loops than depth 1-2;
    wrong if Spearman(depth, loops) <= 0.1."""
    if not any(a == "br" for a, _ in R.res):
        return None
    tg = tc_tag(R)
    m, seeds = common(R, {"S": ("br", "r4"), "S1": ("br", "r1"), "S8": ("br", "r8"), "aplus": ("aplus", "main"), "tc": ("tc", tg), "aplong": ("aplong", "main")})
    if not seeds:
        return {"status": ND, "why": "needs br, aplus, tc and aplong at one seed"}
    vec = (lambda a, t: None) if lab else (lambda a, t: R.rowvec(a, t, seeds=tuple(seeds)))
    v = {k: vec(*at) for k, at in {"S": ("br", "r4"), "S1": ("br", "r1"), "S8": ("br", "r8"), "aplus": ("aplus", "main"), "tc": ("tc", tg), "aplong": ("aplong", "main")}.items()}
    refs = {k: m[k] for k in ("aplus", "tc", "aplong")}
    ref_name = max(refs, key=refs.get)
    a = m["S"] - refs[ref_name]
    d_ref = st.stat({"S": v["S"], "aplus": v["aplus"], "tc": v["tc"], "aplong": v["aplong"]},
                    lambda x: x["S"] - np.maximum(np.maximum(x["aplus"], x["tc"]), x["aplong"])) if all(x is not None for x in v.values()) else None
    deep = None if not rows else np.array([(r.get("depth") or 0) >= 4 for r in rows])
    d_rise = st.diff(v["S"], v["S1"], deep) if deep is not None and v["S"] is not None else None
    d_keep = st.diff(v["S8"], v["S"], deep, ci=False) if deep is not None and v["S"] is not None else None
    f1 = None if d_ref is None or d_ref["lo"] is None else (a >= F1_GAIN - EPS and d_ref["lo"] > 0)
    f2 = None if d_rise is None or d_rise["lo"] is None or d_keep is None else (d_rise["value"] >= F2_RISE - EPS and d_rise["lo"] > 0 and d_keep["value"] >= -F2_KEEP - EPS)
    wrong = [w for w, c in (("F1: gain below +0.5", a < F1_WRONG - EPS), ("F2: loops add < +0.5 on depth 4-6", d_rise is not None and d_rise["value"] < F2_WRONG - EPS)) if c]
    outcome = "PASS: looping the block's own layers helps; halting marks apply" if f1 and f2 else ("PROVED WRONG (" + "; ".join(wrong) + ")") if wrong else "not shown"
    halts = [(R.res.get(("br", sd)) or {}).get("halting") for sd in seeds]
    h = halts[0] if halts and halts[0] else None
    hal = None
    if h:
        bd = h["by_depth"]
        mean_of = lambda ds: (lambda xs: sum(n * l for n, l in xs) / sum(n for n, _ in xs) if xs else None)([(bd[str(d)]["n"], bd[str(d)]["mean_loops"]) for d in ds if str(d) in bd])
        lo_l, hi_l = mean_of((1, 2)), mean_of((4, 5, 6))
        rise = None if lo_l is None or hi_l is None else hi_l - lo_l
        rho = h.get("spearman_depth_loops")
        h1 = 100 * h["acc"] >= (R.acc("br", seeds[0], "validation", "r4") or 0) - H1_KEEP - EPS and h["mean_loops"] <= H1_FRAC * 8 + EPS
        h2 = rise is not None and rise >= H2_RISE - EPS
        hal = {"acc": 100 * h["acc"], "mean_loops": h["mean_loops"], "loops_depth_1_2": lo_l, "loops_depth_4_6": hi_l, "rise": rise, "spearman": rho,
               "H1": h1, "H2": h2, "wrong": rho is not None and rho <= H_WRONG_RHO + EPS, "judged": bool(f1 and f2), "rule": h.get("rule")}
    loops_curve = {f"r{r}": float(np.mean([R.acc("br", sd, "validation", f"r{r}") or 0 for sd in seeds])) for r in (1, 2, 3, 4, 6, 8)}
    sched = (R.res.get(("br", seeds[0])) or {}).get("loop_schedule") or {}
    return {"status": "computed", "seeds": seeds, **m, "ref_name": ref_name, "S_minus_ref": a, "ci_ref": d_ref, "deep_rise": d_rise, "deep_r8_minus_r4": d_keep,
            "F1": f1, "F2": f2, "wrong_by": wrong, "outcome": outcome, "halting": hal, "loops_curve": loops_curve, "schedule": sched,
            "seed_rule": seed_rule([(a - F1_GAIN, a - F1_WRONG)] + ([(d_rise["value"] - F2_RISE, d_rise["value"] - F2_WRONG)] if d_rise else [(None, None)]), len(seeds)),
            "by_depth": by_depth(st, rows, {f"r{r}": vec("br", f"r{r}") for r in (1, 2, 4, 8)} | {"aplus": v["aplus"], "tc": v["tc"], "aplong": v["aplong"]}, lab)}


def analyse(res, rows=None, dev_rows=None, cluster="row", notes=()):
    res, excluded = drop_unmatched(res)
    R = Runs(res)
    st = Stats(R, rows, cluster)
    out = {"notes": list(notes), "arms": [], "aborted": [], "excluded": excluded}
    for (arm, seed), r in sorted(res.items(), key=lambda kv: (ARMS.index(kv[0][0]) if kv[0][0] in ARMS else 99, kv[0][1])):
        if r.get("aborted"):
            out["aborted"].append({"arm": arm, "seed": seed, "reason": str(r["aborted"])})
        row = {"arm": arm, "seed": seed, "aborted": r.get("aborted"), "params": r.get("params_trainable"),
               "steps": [r.get("steps_stage1"), r.get("steps_stage2")], "seconds": (r.get("train") or {}).get("seconds")}
        for split in ("dev", "validation"):
            row[split] = R.acc(arm, seed, split, HEAD[arm])
            row[split + "_n"] = (R.entry(arm, seed, split, HEAD[arm]) or {}).get("n")
        out["arms"].append(row)
    val = R.by_seed
    a, b, ap, bp = val("a", "main"), val("b", "main"), val("aplus", "main"), val("bplus", "main")
    T = {L: val("t", f"L{L}") for L in LAPS}
    swap, meanb, rep, goff = val("t", "swap8"), val("t", "mean8"), val("t", "rep1_8"), val("t", "gatesoff8")
    t1 = {L: val("t1", f"L{L}") for L in (0, 1, 8)}
    tw1 = val("tw", "L1")
    S = {L: mean(d) for L, d in T.items()}
    T1 = mean(t1[1])
    a_ref = max([FLOOR_A] + [x for x in (mean(a), mean(ap)) if x is not None])
    b_ref = max([FLOOR_B] + [x for x in (mean(b), mean(bp)) if x is not None])
    ref = max(a_ref, b_ref)
    out["seeds"] = {arm: sorted(s for (a_, s) in res if a_ == arm and not res[(a_, s)].get("aborted")) for arm in ARMS}
    out["floors"] = {"A_ref": a_ref, "B_ref": b_ref, "a": mean(a), "aplus": mean(ap), "b": mean(b), "bplus": mean(bp),
                     "seeds": {"a": sorted(a), "aplus": sorted(ap), "b": sorted(b), "bplus": sorted(bp)}}
    out["curve"] = {"t": {str(L): {"per_seed": T[L], "mean": S[L], "n": next((e["n"] for sd in SEEDS if (e := R.entry("t", sd, "validation", f"L{L}")) and e.get("n")), None)}
                          for L in LAPS},
                    "t1": {str(L): {"per_seed": d, "mean": mean(d)} for L, d in t1.items()}, "tw": {"L1": tw1},
                    "dev": {f"L{L}": R_dev(R, L) for L in (0, 1, 8)}}
    noise = None
    r0, r1 = R.acc("a", 0, "validation", "main"), R.acc("a", 0, "validation", "main_repeat")
    if r0 is not None and r1 is not None:
        noise = abs(r0 - r1)
    tol = None if noise is None else max(TOL_MIN, 2 * noise)
    out["noise"] = {"a_s0_main": r0, "a_s0_repeat": r1, "diff": noise, "tol": tol}

    # row vectors for the paired intervals (mean over the seeds present)
    labelled = sorted((ARMS.index(a_) if a_ in ARMS else 99, a_, s_) for (a_, s_), r in res.items() if r.get("source") == "label")
    if labelled:  # rebuilt from instance labels (from_label.py): no per-row hits, so no intervals at all (a partial set of seeds would not match the point estimates)
        out["label_sourced"] = [f"{a_} s{s_}" for _, a_, s_ in labelled]
    rv = (lambda arm, tag: None) if labelled else (lambda arm, tag: R.rowvec(arm, tag))
    v8, v1, v2, vt1 = rv("t", "L8"), rv("t", "L1"), rv("t", "L2"), rv("t1", "L1")
    vrefs = {"a": rv("a", "main"), "ap": rv("aplus", "main"), "b": rv("b", "main"), "bp": rv("bplus", "main")}
    vrefs = {k: v for k, v in vrefs.items() if v is not None}
    best = lambda floor, ks, m: functools.reduce(np.maximum, [floor] + [m[k] for k in ks if k in m])
    refs = lambda m: np.maximum(best(FLOOR_A, ("a", "ap"), m), best(FLOOR_B, ("b", "bp"), m))
    ci_ref = st.stat({"S8": v8, **vrefs}, lambda m: m["S8"] - refs(m)) if v8 is not None else None
    ci_81, ci_8t1 = st.diff(v8, v1) if v8 and v1 else None, st.diff(v8, vt1) if v8 and vt1 else None
    ci_82 = st.diff(v8, v2) if v8 and v2 else None
    ci_swap = st.diff(v8, rv("t", "swap8")) if v8 and rv("t", "swap8") else None
    ci_rep = st.diff(v8, rv("t", "rep1_8")) if v8 and rv("t", "rep1_8") else None
    cis = {"S8_minus_best_ref": ci_ref, "S8_minus_S1": ci_81, "S8_minus_T1": ci_8t1, "S8_minus_S2": ci_82,
           "S8_minus_swap": ci_swap, "S8_minus_rep": ci_rep}
    out["intervals"] = cis
    out["think2"] = think2(R, st, bool(labelled))
    out["p1"], out["p2b"] = p1(R, st, rows, bool(labelled)), p2b(R, st, rows, bool(labelled))
    out["br"] = pbr(R, st, rows, bool(labelled))

    # lesions (arm t, L=8, validation)
    sub = lambda x, y: None if x is None or y is None else x - y
    gm, gs, rm, rs = 0, 0, 0, 0  # gates-off rows unlike arm a (other decode path: bf16 noise) / unlike the board-free decode of the same batches (must be 0)
    gap = []
    for s in SEEDS:
        ga, gb, gr = (R.vec("t", s, "validation", "gatesoff8"), R.vec("a", s, "validation", "main"), R.vec("t", s, "validation", "ref0"))
        al = align(ga, gb) if ga and gb else None
        if al is not None:
            gm, gs = gm + int((al[1][0] != al[1][1]).sum()), gs + 1
            gap.append(100 * float(al[1][0].mean() - al[1][1].mean()))
        al = align(ga, gr) if ga and gr else None
        if al is not None:
            rm, rs = rm + int((al[1][0] != al[1][1]).sum()), rs + 1
    gm, rm = gm if gs else None, rm if rs else None
    ref0 = val("t", "ref0")
    out["lesions"] = {"swap": mean(swap), "mean_board": mean(meanb), "repeat_delta1": mean(rep), "gates_off": mean(goff), "ref0": mean(ref0),
                      "swap_drop": sub(S[8], mean(swap)), "mean_drop": sub(S[8], mean(meanb)),
                      "rep_drop": sub(S[8], mean(rep)), "gates_off_rows_differing_from_a": gm, "gates_off_seeds_checked": gs,
                      "gates_off_minus_a_points": mean(dict(enumerate(gap))) if gap else None,
                      "gates_off_rows_differing_from_ref0": rm, "gates_off_ref0_seeds_checked": rs,
                      "same_path_gain": sub(S[8], mean(goff)),
                      "b_pass1": mean(val("b", "pass1")), "b_main": mean(b)}
    d0 = sub(bp.get(0), b.get(0))
    out["bplus_extend"] = {"bplus_minus_b_s0": d0, "need": BPLUS_EXTEND, "run_seeds_1_2": None if d0 is None else d0 >= BPLUS_EXTEND - EPS}

    # marks
    tc = have(T[8])
    marks = []

    def mark(id_, text, status, **kw):
        marks.append({"id": id_, "text": text, "status": status, **kw})
        return marks[-1]

    G = mark("G", "gain", decide(ge(S[8], ref + GAIN) if S[8] is not None and have(T[8]) and have(a) and have(ap) and have(b)
                      and (not out["bplus_extend"]["run_seeds_1_2"] or have(bp)) else None),  # bplus on all seeds is owed once the extension rule fired: B_ref uses its mean
             value=S[8], need=ref + GAIN, ref=ref, A_ref=a_ref, B_ref=b_ref, ci=ci_ref)
    d81 = {s: T[8][s] - T[1][s] for s in SEEDS if s in T[8] and s in T[1]}
    d128 = {s: T[12][s] - T[8][s] for s in SEEDS if s in T[12] and s in T[8]}
    S81 = sub(S[8], S[1])
    R1 = [mark("R1a", "slope S(8)-S(1)", decide(ge(S81, SLOPE) if tc and have(T[1]) else None), value=S81, need=SLOPE, ci=ci_81),
          mark("R1b", "slope in every seed", decide(all(ge(v, SLOPE_SEED) for v in d81.values()) if have(d81) else None),
               per_seed=d81, need=SLOPE_SEED)]
    tol_ok = lambda hi, lo_: None if tol is None or not (have(T[hi]) and have(T[lo_])) else ge(S[hi], S[lo_] - tol)
    R2 = [mark("R2a", "S(2) >= S(1) - tol", decide(tol_ok(2, 1)), a=S[2], b=S[1], tol=tol),
          mark("R2b", "S(4) >= S(2) - tol", decide(tol_ok(4, 2)), a=S[4], b=S[2], tol=tol),
          mark("R2c", "S(8) >= S(4) - tol", decide(tol_ok(8, 4)), a=S[8], b=S[4], tol=tol)]
    R3 = [mark("R3a", "S(12) >= S(8) - 1.0", decide(ge(S[12] - S[8], -COLLAPSE) if tc and have(T[12]) else None),
               value=sub(S[12], S[8]), need=-COLLAPSE),
          mark("R3b", "S_s(12) >= S_s(8) - 2.0", decide(all(ge(v, -COLLAPSE_SEED) for v in d128.values()) if have(d128) else None),
               per_seed=d128, need=-COLLAPSE_SEED)]
    tcomplete1 = have(t1[1])
    R4 = [mark("R4a", "S(8) - T1", decide(ge(S[8] - T1, LAP_NEED) if tc and tcomplete1 else None),
               value=sub(S[8], T1), need=LAP_NEED, ci=ci_8t1),
          mark("R4b", "S(8) - repeat-delta1(8)", decide(ge(S[8] - mean(rep), REPEAT_NEED) if tc and have(rep) else None),
               value=sub(S[8], mean(rep)), need=REPEAT_NEED, ci=ci_rep)]
    Rg = {"R1": group(R1), "R2": group(R2), "R3": group(R3), "R4": group(R4)}
    Rall = group([{"status": v} for v in Rg.values()])
    out["R_groups"] = Rg
    out["R"] = Rall

    W = [mark("W1", "S(8) - T1 < 1.0 (laps add nothing)", trig(S[8] - T1 < W_T1 - EPS if tc and tcomplete1 else None),
              value=sub(S[8], T1), need=W_T1),
         mark("W2", "S(8) - S(2) < 0.5 (done by lap 2)", trig(S[8] - S[2] < W_LAP2 - EPS if tc and have(T[2]) else None),
              value=sub(S[8], S[2]), need=W_LAP2, ci=ci_82),
         mark("W3", "swap lesion < 1.0 (board unused)", trig(S[8] - mean(swap) < W_SWAP - EPS if tc and have(swap) else None),
              value=out["lesions"]["swap_drop"], need=W_SWAP, ci=ci_swap),
         mark("W4", "S(8) < A_ref + 1.0", trig(S[8] < a_ref + W_FLOOR - EPS if tc and have(a) and have(ap) else None),
              value=S[8], need=a_ref + W_FLOOR)]

    # futility (seed 0)
    s8, s2, s1_0 = T[8].get(0), T[2].get(0), t1[1].get(0)
    sw0 = None if 0 not in swap or s8 is None else s8 - swap[0]
    F_ = [mark("F1", "S_0(8) < 68.0", trig(s8 < FUT_ACC - EPS if s8 is not None else None), value=s8, need=FUT_ACC),
          mark("F2", "S_0(8) - T1_0 < 1.0", trig(s8 - s1_0 < 1.0 - EPS if s8 is not None and s1_0 is not None else None),
               value=sub(s8, s1_0), need=1.0),
          mark("F3", "S_0(8) - S_0(2) < 0.5", trig(s8 - s2 < 0.5 - EPS if s8 is not None and s2 is not None else None),
               value=sub(s8, s2), need=0.5),
          mark("F4", "swap lesion_0 < 1.0", trig(sw0 < 1.0 - EPS if sw0 is not None else None), value=sw0, need=1.0)]
    fut_hit = [m["id"] for m in F_ if m["status"] == "triggered"]

    # secondary: M1, M2 and slices
    sec = {"slices": {}, "M1": None, "M2": None}
    depth = bank = qtype = None
    if rows:
        depth = np.array([r.get("depth") if r.get("depth") is not None else -1 for r in rows])
        bank = np.array([str(r.get("bank")) for r in rows])
        qtype = np.array([str(r.get("qtype")) for r in rows])
    sel_m1 = None if bank is None else np.isin(bank, CHAIN)
    sel_m2 = None if depth is None else depth >= 4
    va = rv("a", "main")

    def slice_row(sel):
        d = st.diff(v8, vt1, sel) if v8 and vt1 else None
        d1 = st.diff(v8, v1, sel) if v8 and v1 else None
        sa = st.stat({"x": va}, lambda m: m["x"], sel, ci=False) if va else None
        s8_ = st.stat({"x": v8}, lambda m: m["x"], sel, ci=False) if v8 else None
        t1_ = st.stat({"x": vt1}, lambda m: m["x"], sel, ci=False) if vt1 else None
        return {"n": int(sel.sum()), "a": sa and sa["value"], "S8": s8_ and s8_["value"], "T1": t1_ and t1_["value"],
                "S8_minus_T1": d, "S8_minus_S1": d1}

    if rows and v8 is not None:
        for name, sel in (("depth 0-3", depth <= 3), ("depth 4-6", depth >= 4)):
            sec["slices"][name] = slice_row(sel)
        for dv in sorted(set(depth.tolist())):
            if dv >= 0:
                sec["slices"][f"depth {dv}"] = slice_row(depth == dv)
        for nm, col in (("bank", bank), ("qtype", qtype)):
            for k in sorted(set(col.tolist())):
                sec["slices"][f"{nm} {k}"] = slice_row(col == k)
    for key, sel, need, nm in (("M1", sel_m1, M1_NEED, "chain banks"), ("M2", sel_m2, M2_NEED, "depth >= 4")):
        d = st.diff(v8, vt1, sel) if sel is not None and v8 and vt1 else None
        full = d is not None and tc and tcomplete1
        sec[key] = {"text": nm, "need": need, "n": None if d is None else d["n"], "value": d and d["value"],
                    "lo": d and d["lo"], "hi": d and d["hi"], "status": decide(ge(d["value"], need) if full else None),
                    "seeds_t": sorted(T[8]), "seeds_t1": sorted(t1[1])}
    out["secondary"] = sec

    out["marks"] = marks
    out["groups"] = {"G": G["status"], **Rg, "R": Rall}
    out["wrong_if"] = [m["id"] for m in W if m["status"] == "triggered"]
    out["futility"] = {"triggered": fut_hit, "only_first": fut_hit == ["F1"] and all(m["status"] == "clear" for m in F_[1:])}  # "laps are real" needs F2-F4 computed and clear
    out["lap_curve_first2000"] = None
    if v8 is not None:
        first = {}
        for L in (8, 16, 24):
            v = rv("t", f"L{L}")
            first[L] = v
        if first[16] is not None or first[24] is not None:
            parts = {f"L{L}": v for L, v in first.items() if v is not None}
            al = align(*parts.values())
            if al:
                out["lap_curve_first2000"] = {"n": len(al[1][0]), **{k: 100 * float(a.mean()) for k, a in zip(parts, al[1])}}
    out["tw"] = {"tw_L1_s0": tw1.get(0), "t1_L1_s0": s1_0, "t_L8_s0": s8}

    # verdict
    decided = all(m["status"] != ND for m in [G, *R1, *R2, *R3, *R4, *W])
    why = []

    def _missing():
        arms = [("t", T[8]), ("t1", t1[1]), ("a", a), ("aplus", ap), ("b", b)] + ([("bplus", bp)] if out["bplus_extend"]["run_seeds_1_2"] else [])
        return "; ".join(f"{n} {sorted(set(SEEDS) - set(d))}" for n, d in arms if not have(d))

    if out["aborted"]:
        why.append("mechanics gate aborted: " + ", ".join(f"{x['arm']} s{x['seed']}" for x in out["aborted"]))
    if excluded:
        why.append("excluded (stage-1 adapter differs from the one the dependent was trained on): " + ", ".join(f"{x['arm']} s{x['seed']}" for x in excluded))
    if decided:
        if out["wrong_if"]:
            verdict = "WRONG"
            why.append("wrong-if rule(s) triggered: " + ", ".join(out["wrong_if"]))
            if G["status"] == "PASS" and Rall == "PASS":
                why.append("G and R both pass, but a wrong-if rule overrides (PREREG lists wrong-if as refuting)")
        elif G["status"] == "PASS" and Rall == "PASS":
            verdict = "PASS"
            why.append("G and R both pass; no wrong-if rule triggered")
        else:
            verdict = "PARTIAL"
            why.append("not PASS and no wrong-if rule: reported, no scale-up")
    elif fut_hit:
        verdict = "FUTILE-STOP"
        unstarted = sorted(set(SEEDS) - {s_ for (_, s_) in res})  # no result file of any arm = not started (PREREG amendment 2026-10-24: a stop is for seeds not yet started; completed seeds count)
        why.append("seed-0 futility rule(s): " + ", ".join(fut_hit) + "; "
                   + (f"do not start seed(s) {', '.join(map(str, unstarted))}" if unstarted else "no unstarted seeds left to stop")
                   + "; seeds that completed count (marks are provisional until all seeds are in)")
        why.append("missing seeds: " + (_missing() or "none") + ("; a seed-0 main_repeat" if tol is None else ""))
        if out["futility"]["only_first"]:
            why.append("only F1 fails: laps real but small; Think-1b gets its own prereg")
    else:
        verdict = "INCOMPLETE"
        why.append("missing seeds: " + (_missing() or "none") + ("; a seed-0 main_repeat" if tol is None else ""))
        if all(m["status"] == "clear" for m in F_):
            why.append("seed-0 futility rules did not fire: go on to seeds 1-2")
        elif not fut_hit and any(m["status"] == "clear" for m in F_):
            why.append("seed-0 futility undecided (" + ", ".join(m["id"] for m in F_ if m["status"] != "clear")
                       + " not computable yet): do not start new seeds on this basis")
    out["verdict"], out["why"] = verdict, why
    return out


def R_dev(R, L):
    return {s: a for s in SEEDS if (a := R.acc("t", s, "dev", f"L{L}")) is not None}


# ---------------------------------------------------------------- text report

f2 = lambda x: "--" if x is None else f"{x:.2f}"
sg = lambda x: "--" if x is None else f"{x:+.2f}"


def ci_txt(c):
    return "" if not c or c.get("lo") is None else f"  95% [{c['lo']:+.2f}, {c['hi']:+.2f}]"


def seeds_txt(d):
    return " ".join(f"{d[s]:.2f}" if s in d else "  -- " for s in SEEDS)


def report(o, data_note=""):
    L = []
    P = L.append
    lab = o.get("label_sourced")
    ci_txt_ = (lambda c: ci_txt(c) or "  95% n/a") if lab else ci_txt  # label-only results carry no per-row hits: intervals print as n/a
    P("THINK-1 SUMMARY  (accuracy in percent, validation unless said)")
    if lab:
        P(f"FROM LABELS: {', '.join(lab)} rebuilt from Vast instance labels (0.1-point rounding, no per-row hits): point estimates only, "
          f"every 95% interval is n/a; slices, M1/M2 and the row-level lesion checks need the result files.")
    if data_note:
        P(data_note)
    for n in o["notes"]:
        P("note: " + n)
    for x in o["aborted"]:
        P(f"ABORTED  {x['arm']} seed {x['seed']}: {x['reason']}")
    for x in o.get("excluded", []):
        P(f"EXCLUDED {x['arm']} seed {x['seed']}: trained on stage-1 adapter {x['sha']}, but arm {x['parent']} seed {x['seed']} now has adapter "
          f"{x['parent_sha']} (stage-1 arm retrained after it); not used in any mark")
    P("")
    P("== 1. What each run scored ==")
    P("arm    seed   dev    val   notes")
    for r in o["arms"]:
        extra = "ABORTED" if r["aborted"] else ""
        if r["params"] and not r["aborted"]:
            extra = f"{r['params']:,} trainable"
        if r["seconds"] and not r["aborted"]:
            extra += f", {r['seconds'] / 3600:.2f} h"
        P(f"{r['arm']:<6} {r['seed']:<4} {f2(r['dev']):>6} {f2(r['validation']):>6}   {extra}")
    fl = o["floors"]
    P("")
    P("Means over seeds, and the floors the marks use:")
    P(f"  a {f2(fl['a'])}  aplus {f2(fl['aplus'])}  b {f2(fl['b'])}  bplus {f2(fl['bplus'])}")
    P(f"  A_ref = {fl['A_ref']:.2f}  = max(66.72, a, aplus)")
    P(f"  B_ref = {fl['B_ref']:.2f}  = max(67.12, b, bplus)")
    be = o["bplus_extend"]
    if be["bplus_minus_b_s0"] is None:
        P("  bplus - b (seed 0): not available; bplus seeds 1-2 are run only if it is >= 1.0")
    else:
        P(f"  bplus - b (seed 0) = {sg(be['bplus_minus_b_s0'])}; run bplus seeds 1-2 (bplus:1,bplus:2): {'yes' if be['run_seeds_1_2'] else 'no'} (needs >= 1.0)")
    nz = o["noise"]
    P(f"  a seed 0 scored twice: {f2(nz['a_s0_main'])} vs {f2(nz['a_s0_repeat'])}"
      f"  (noise {f2(nz['diff'])}, R2 tol {f2(nz['tol'])})")
    P("")
    P("== 2. Arm t: score by laps (L=0 is pause slots) ==")
    P("lap     n      s0     s1     s2    mean   vs prev")
    prev = None
    for k in LAPS:
        c = o["curve"]["t"][str(k)]
        ch = "" if prev is None or c["mean"] is None or k > 12 else sg(c["mean"] - prev)
        P(f"L{k:<3} {c['n'] if c['n'] else '--':>6}  {seeds_txt(c['per_seed'])}  {f2(c['mean']):>6}  {ch:>7}")
        if k <= 12 and c["mean"] is not None:
            prev = c["mean"]
        elif k > 12:
            prev = None
    f2k = o["lap_curve_first2000"]
    if f2k:
        P(f"same first {f2k['n']} rows: " + "  ".join(f"{k} {v:.2f}" for k, v in f2k.items() if k != "n"))
    c1 = o["curve"]["t1"]
    P(f"t1 (one refinement): L0 {f2(c1['0']['mean'])}  L1 {f2(c1['1']['mean'])}  L8 {f2(c1['8']['mean'])}")
    P(f"tw (144 slots, L1, seed 0): {f2(o['tw']['tw_L1_s0'])}  vs t1 seed 0: {f2(o['tw']['t1_L1_s0'])}"
      f"  vs t L8 seed 0: {f2(o['tw']['t_L8_s0'])}")
    dv = o["curve"]["dev"]
    P("dev, arm t: " + "  ".join(f"{k} {f2(mean(v))}" for k, v in dv.items()))
    P("")
    P("== 3. Lesions (arm t, L=8) ==")
    ls = o["lesions"]
    P(f"swap board     {f2(ls['swap']):>6}   costs {sg(ls['swap_drop'])}{ci_txt_(o['intervals']['S8_minus_swap'])}")
    P(f"mean board     {f2(ls['mean_board']):>6}   costs {sg(ls['mean_drop'])}")
    P(f"repeat delta1  {f2(ls['repeat_delta1']):>6}   costs {sg(ls['rep_drop'])}{ci_txt_(o['intervals']['S8_minus_rep'])}")
    ro = ls["gates_off_rows_differing_from_ref0"]
    P(f"gates off      {f2(ls['gates_off']):>6}   rows unlike the same batches without a board: {'--' if ro is None else ro} (must be 0)")
    if ls["gates_off_rows_differing_from_a"] is not None:
        gp = ls["gates_off_minus_a_points"]
        P(f"               rows unlike arm a's main: {ls['gates_off_rows_differing_from_a']} ({sg(gp)} points); another code path, so bf16 noise")
        if ls["gates_off_rows_differing_from_a"] > 0:
            P(f"               NOTE: S(8) vs A_ref is path-confounded (~{abs(gp):.2f} points); S(8) - gates off = {sg(ls['same_path_gain'])}")
    P(f"arm b: 3 loops {f2(ls['b_main'])}, 1 pass {f2(ls['b_pass1'])}")
    P("")
    P("== 4. PASS marks ==")
    P("seeds in: " + "  ".join(f"{a} {''.join(map(str, v)) or '-'}" for a, v in o["seeds"].items()) + "   (marks need 012)")
    mk = {m["id"]: m for m in o["marks"]}

    def line(m, body):
        P(f"{m['status']:<16} {m['id']:<4} {body}")

    g = mk["G"]
    P(f"G gain: {g['status']}")
    line(g, f"S(8) {f2(g['value'])} needs >= {f2(g['need'])}  (best floor {g['ref']:.2f} + 3.0)")
    if g["ci"]:
        P(f"{'':21}S(8) - best floor {sg(g['ci']['value'])}{ci_txt_(g['ci'])}")
    elif lab:
        P(f"{'':21}S(8) - best floor {sg(None if g['value'] is None else g['value'] - g['ref'])}  95% n/a")
    for gid, title in (("R1", "R1 slope"), ("R2", "R2 monotone"), ("R3", "R3 no collapse"), ("R4", "R4 laps, not parameters")):
        P(f"{title}: {o['R_groups'][gid]}")
        for m in o["marks"]:
            if m["id"].startswith(gid):
                body = {"R1a": lambda m: f"S(8)-S(1) {sg(m['value'])} needs >= {m['need']}{ci_txt_(m['ci'])}",
                        "R1b": lambda m: f"per seed {', '.join(sg(v) for v in m['per_seed'].values()) or '--'} each >= {m['need']}",
                        "R2a": lambda m: f"S(2) {f2(m['a'])} vs S(1) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R2b": lambda m: f"S(4) {f2(m['a'])} vs S(2) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R2c": lambda m: f"S(8) {f2(m['a'])} vs S(4) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R3a": lambda m: f"S(12)-S(8) {sg(m['value'])} needs >= {m['need']}",
                        "R3b": lambda m: f"per seed {', '.join(sg(v) for v in m['per_seed'].values()) or '--'} each >= {m['need']}",
                        "R4a": lambda m: f"S(8)-T1 {sg(m['value'])} needs >= {m['need']}{ci_txt_(m['ci'])}",
                        "R4b": lambda m: f"S(8)-repeat {sg(m['value'])} needs >= {m['need']}{ci_txt_(m['ci'])}"}[m["id"]](m)
                line(m, body)
    P(f"PASS needs G and R:  G {o['groups']['G']}, R {o['R']}")
    P("")
    P("== 5. Wrong-if rules (triggered = the idea is refuted) ==")
    for m in o["marks"]:
        if m["id"].startswith("W"):
            line(m, f"{m['text']}   now {sg(m['value']) if m['id'] != 'W4' else f2(m['value'])}")
    P("")
    P("== 6. Futility check (seed 0 only; triggered = stop seeds not yet started; done seeds count) ==")
    for m in o["marks"]:
        if m["id"].startswith("F"):
            line(m, f"{m['text']}   now {f2(m['value'])}")
    if o["futility"]["only_first"]:
        P("Only F1 fires: laps are real but small. PASS track stops; Think-1b.")
    P("")
    P("== 7. Secondary (no weight in PASS) ==")
    for k in ("M1", "M2"):
        m = o["secondary"][k]
        P(f"{m['status']:<16} {k}   {m['text']} (n={m['n'] or '--'}): S(8)-T1 {sg(m['value'])}"
          f" needs >= {m['need']:.1f}{ci_txt_(m)}")
    sl = o["secondary"]["slices"]
    if sl:
        P("")
        P("S(8)-T1 by slice (95% paired bootstrap):")
        P(f"{'slice':<26}{'n':>5} {'arm a':>6} {'T1':>6} {'S(8)':>6}  diff")
        for name, r in sl.items():
            d = r["S8_minus_T1"]
            P(f"{name[:25]:<26}{r['n']:>5} {f2(r['a']):>6} {f2(r['T1']):>6} {f2(r['S8']):>6}  "
              f"{sg(d and d['value'])}{ci_txt_(d).replace('  95% ', ' ')}")
    t2 = o.get("think2")
    if t2:
        P("")
        P("== 8. Think-2 (PREREG-think2.md; seed 0, L_max 4; tj and tf judged separately) ==")
        for arm, t in t2.items():
            d = t["P1_diff"]
            P(f"arm {arm}: S(4) {f2(t['S4'])}  aplus {f2(t['aplus'])}  tc {f2(t['tc']) if t['tc_present'] else 'absent'}  S(1) {f2(t['S1'])}"
              f"  swap4 {f2(t['swap4'])}  gatesoff4 {f2(t['gatesoff4'])}")
            vs = "max(aplus, tc)" if t["tc_present"] else "aplus"
            P(f"{t['P1']['status']:<16} {arm} P1 S(4) - {vs} = {sg(d and d['value'])}{ci_txt_(d)}   needs >= +2.0 and 95% interval excluding 0 (l.30)"
              + ("" if t["tc_present"] else "   [tc absent: judged against aplus only, may get harder]")
              + (f"   [harder control: {t['P1_vs']}]" if t["tc_present"] and t["P1_vs"] else ""))
            for k in ("S4_minus_aplus", "S4_minus_tc"):
                if t[k]:
                    P(f"{'':17}S(4) - {k[9:]} {sg(t[k]['value'])}{ci_txt_(t[k])}")
            d = t["S4_minus_swap4"]
            P(f"{t['P2']['status']:<16} {arm} P2 S(4) - swap4 = {sg(d and d['value'])}{ci_txt_(d)}   needs >= +1.0 (l.31)")
            d = t["S4_minus_L1"]
            P(f"{t['P3']['status']:<16} {arm} P3 " + (f"S(4) - S(1) = {sg(d['value'])}{ci_txt_(d)}   needs >= +0.5 (l.32, reported only)" if d
                                                      else "unavailable: no L1 row for this arm   needs >= +0.5 (l.32, reported only)"))
            if t["S4_minus_blind4"]:
                P(f"{'':17}S(4) - blind4 = {sg(t['S4_minus_blind4']['value'])}{ci_txt_(t['S4_minus_blind4'])} (first 2,000 rows; no mark)")
            P(f"{t['wrong_if']:<16} {arm} wrong-if: S(4) - A+ < +1.0 or swap lesion < 0.5 (l.40-42)")
            P(f"{'':17}decision (l.36-38): {t['decision']}")
    if o.get("p1"):
        report_p1(o["p1"], P, ci_txt_)
    if o.get("p2b"):
        report_p2b(o["p2b"], P, ci_txt_)
    if o.get("br"):
        report_br(o["br"], P, ci_txt_)
    P("")
    P(f"VERDICT: {o['verdict']}")
    for w in o["why"]:
        P("  " + w)
    return "\n".join(L)


def depth_table(P, bd, names):
    P(f"{'slice':<12}{'n':>6} " + " ".join(f"{n:>7}" for n in names))
    for k, v in bd.items():
        P(f"{k:<12}{v['n']:>6} " + " ".join(f"{f2(v.get(n)):>7}" for n in names))


def report_p1(x, P, ci):
    P("")
    P("== 9. P1 written steps (codi-plan; arms ws, wsham; judged against tc = C0' and C1 = ws answering directly) ==")
    if x["status"] != "computed":
        P(f"{ND:<16} {x['why']}")
        return
    sd = ",".join(map(str, x["seeds"]))
    f1 = lambda v: "--" if not v or v[0] is None else "/".join(f"{y:.1f}" for y in v)
    P(f"seeds {sd}  T {f2(x['T'])}  C1 {f2(x['C1'])}  tc {f2(x['C0'])}  sham T {f2(x['sham'])}  (reference = max(tc, C1) = {f2(x['ref'])}, {x['ref_name']})")
    P(f"T - max(tc, C1) = {sg(x['T_minus_ref'])}{ci(x['ci_ref'])}   P4 needs >= +{P1_OPEN:.1f}; proved wrong below +{P1_WRONG:.1f}")
    P(f"T - sham        = {sg(x['T_minus_sham'])}{ci(x['ci_sham'])}   P4 needs >= +{P1_SHAM:.1f}")
    P(f"T vs 74.6 (for the record) = {sg(x['T_vs_74_6'])}")
    P(f"mean generated tokens per row: ws {f1(x['mean_gen_tokens']['ws'])}, wsham {f1(x['mean_gen_tokens']['wsham'])}; ws wrote 'The answer is:' in {f1([None if v is None else 100 * v for v in x['marker_rate']])}% of rows")
    P(f"format check (gold steps in, answer read; first 500 rows with steps; no pass mark): ws {f1(x['format_check']['ws'])}, wsham (filler in) {f1(x['format_check']['wsham'])}")
    P(f"OUTCOME: {x['outcome']}")
    P(f"seed rule: {x['seed_rule']}")
    if x.get("by_depth"):
        P("accuracy by depth (no pass mark):")
        depth_table(P, x["by_depth"], ("T", "C1", "sham", "tc"))


def report_p2b(x, P, ci):
    P("")
    P("== 10. P2b step-supervised notes (codi-plan; arms tsd, tsd1; judged against max(tc, C1) and the one-lap arm tsd1) ==")
    if x["status"] != "computed":
        P(f"{ND:<16} {x['why']}")
        return
    f1 = lambda v: "--" if not v or v[0] is None else "/".join(f"{y:.1f}" for y in v)
    P(f"seeds {','.join(map(str, x['seeds']))}  tsd S(4) {f2(x['S'])}  tsd1 {f2(x['tsd1'])}  tc {f2(x['tc'])}  C1 {f2(x['C1'])}  (reference = {f2(x['ref'])})")
    c = x["conditions"]
    mk = lambda v: ND if v is None else "PASS" if v else "FAIL"
    P(f"{mk(c['a']):<16} (a) S - max(tc, C1) = {sg(x['S_minus_ref'])}{ci(x['ci_ref'])}   needs >= +{P2_A:.1f}")
    for k in ("swap", "random", "zero"):
        l = x["lesions"][k]
        P(f"{l['status']:<16} (b) {k} lesion {f2(x[k])}: costs {sg(l['cost'])}{ci_txt({'lo': l['lo'], 'hi': l['hi']}) if l['lo'] is not None else '  95% n/a'}"
          + ("   (reported, not in the pass marks)" if k == "zero" else f"   used needs >= {USED:.1f} with the interval above 0; unused below {UNUSED:.1f}"))
    P(f"{mk(c['c']):<16} (c) S - tsd1 = {sg(x['S_minus_tsd1'])}{ci(x['ci_one'])}   needs >= +{P2_C:.1f}; proved wrong below +{P2_C_WRONG:.1f}")
    d = x["decoder"]
    P(f"{mk(c['d']):<16} (d) decoder step-token accuracy, true notes {f1(d['true'])}% vs swapped {f1(d['swap'])}%: gap {sg(d['gap'])} points   needs >= {P2_D:.0f}; proved wrong below {P2_D_WRONG:.0f}")
    P(f"swapped-notes score minus tc = {sg(x['swapped_score_vs_C0'])} (rough split: a gain that survives the swap sits in the backbone, not the notes)")
    P(f"OUTCOME: {x['outcome']}")
    P(f"P3 entry (gap >= 10 and swap not 'used'): {'yes' if x['P3_entry'] else 'no'};  seed rule: {x['seed_rule']}")
    if x.get("by_depth"):
        P("accuracy by depth (no pass mark):")
        depth_table(P, x["by_depth"], ("S", "tsd1", "C1", "tc"))


def report_br(x, P, ci):
    P("")
    P("== 11. Addendum F: loop the model's own layers (arm br, random loop counts; judged against max(aplus, tc, aplong)) ==")
    if x["status"] != "computed":
        P(f"{ND:<16} {x['why']}")
        return
    mk = lambda v: ND if v is None else "PASS" if v else "FAIL"
    sc = x["schedule"]
    P(f"seeds {','.join(map(str, x['seeds']))}  br r4 {f2(x['S'])}  aplus {f2(x['aplus'])}  tc {f2(x['tc'])}  aplong {f2(x['aplong'])}  "
      f"(train loops mean {f2(sc.get('mean'))}, compute ratio {f2(sc.get('compute_ratio'))}, block {sc.get('block')})")
    P("validation by loop count: " + "  ".join(f"{k} {f2(v)}" for k, v in x["loops_curve"].items()))
    P(f"{mk(x['F1']):<16} F1 S(r4) - max(aplus, tc, aplong) = {sg(x['S_minus_ref'])}{ci(x['ci_ref'])}   needs >= +{F1_GAIN:.1f}; proved wrong below +{F1_WRONG:.1f} (max is {x['ref_name']})")
    dr, dk = x["deep_rise"], x["deep_r8_minus_r4"]
    P(f"{mk(x['F2']):<16} F2 depth 4-6: S(r4) - S(r1) = {sg(dr and dr['value'])}{ci(dr) if dr else ''}   needs >= +{F2_RISE:.1f}; S(r8) - S(r4) = {sg(dk and dk['value'])}   needs >= -{F2_KEEP:.1f}")
    P(f"OUTCOME: {x['outcome']};  seed rule: {x['seed_rule']}")
    h = x.get("halting")
    if h:
        tag = "judged" if h["judged"] else "reported only (F1 and F2 must pass first)"
        P(f"halting (answer-stable rule, {tag}): {f2(h['acc'])}% at mean {f2(h['mean_loops'])} loops; depth 1-2 {f2(h['loops_depth_1_2'])} vs depth 4-6 "
          f"{f2(h['loops_depth_4_6'])} loops (rise {sg(h['rise'])}); Spearman(depth, loops) {f2(h['spearman'])}; H1 {mk(h['H1'])} H2 {mk(h['H2'])}"
          + ("; WRONG: loops do not follow depth" if h["wrong"] else ""))
    if x.get("by_depth"):
        P("accuracy by depth (no pass mark):")
        depth_table(P, x["by_depth"], ("r1", "r2", "r4", "r8", "aplus", "tc", "aplong"))


def summarize(root, data="out/data", cluster="row"):
    res, notes = load_results(root)
    rows = load_rows(Path(data) / "validation.jsonl")
    dev = load_rows(Path(data) / "dev.jsonl")
    n_hits = max([len(e.get("hits", "")) + int(e.get("row_offset", 0)) for r in res.values()
                  for e in ((r.get("eval") or {}).get("validation") or {}).values()] or [0])
    if rows is None:
        notes.append(f"no validation.jsonl in {data}: depth/bank/qtype slices and M1/M2 are not available")
    elif len(rows) < n_hits:
        notes.append(f"{data}/validation.jsonl has {len(rows)} rows but hits cover {n_hits}: slices skipped")
        rows = None
    o = analyse(res, rows, dev, cluster, notes)
    o["data"] = str(data)
    o["validation_rows"] = None if rows is None else len(rows)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="directory holding result_*.json (searched recursively)")
    ap.add_argument("--data", default="out/data")
    ap.add_argument("--json", action="store_true", help="print the numbers as JSON instead of the text report")
    ap.add_argument("--cluster", choices=["row", "visit"], default="row", help="what the bootstrap resamples (default: rows)")
    args = ap.parse_args(argv)
    o = summarize(args.out, args.data, args.cluster)
    if args.json:
        print(json.dumps(o, indent=1, default=lambda x: float(x) if isinstance(x, np.floating) else int(x) if isinstance(x, np.integer) else str(x)))
    else:
        vr = o["validation_rows"]
        print(report(o, f"data: {args.data}" + (f" ({vr} validation rows)" if vr else " (no validation rows)")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
