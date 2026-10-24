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
HEAD = {"a": "main", "b": "main", "aplus": "main", "bplus": "main", "t": "L8", "t1": "L1", "tw": "L1"}
ALIAS = {"rep18": ("repeatdelta18", "repeat8", "rep8"), "gatesoff8": ("gatesoff",), "swap8": ("swap",), "mean8": ("meanboard8",)}
ND = "not-enough-data"


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

def analyse(res, rows=None, dev_rows=None, cluster="row", notes=()):
    R = Runs(res)
    st = Stats(R, rows, cluster)
    out = {"notes": list(notes), "arms": [], "aborted": []}
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
    out["curve"] = {"t": {str(L): {"per_seed": T[L], "mean": S[L], "n": (R.entry("t", 0, "validation", f"L{L}") or {}).get("n")}
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
    rv = lambda arm, tag: R.rowvec(arm, tag)
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

    # lesions (arm t, L=8, validation)
    sub = lambda x, y: None if x is None or y is None else x - y
    gm, gs = 0, 0
    for s in SEEDS:
        ga, gb = R.vec("t", s, "validation", "gatesoff8"), R.vec("a", s, "validation", "main")
        al = align(ga, gb) if ga and gb else None
        if al is not None:
            gm, gs = gm + int((al[1][0] != al[1][1]).sum()), gs + 1
    gm = gm if gs else None
    out["lesions"] = {"swap": mean(swap), "mean_board": mean(meanb), "repeat_delta1": mean(rep), "gates_off": mean(goff),
                      "swap_drop": sub(S[8], mean(swap)), "mean_drop": sub(S[8], mean(meanb)),
                      "rep_drop": sub(S[8], mean(rep)), "gates_off_rows_differing_from_a": gm, "gates_off_seeds_checked": gs,
                      "b_pass1": mean(val("b", "pass1")), "b_main": mean(b)}

    # marks
    tc = have(T[8])
    marks = []

    def mark(id_, text, status, **kw):
        marks.append({"id": id_, "text": text, "status": status, **kw})
        return marks[-1]

    G = mark("G", "gain", decide(ge(S[8], ref + GAIN) if S[8] is not None and have(T[8]) and have(a) and have(ap) and have(b) else None),
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
    out["futility"] = {"triggered": fut_hit, "only_first": fut_hit == ["F1"]}
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
    if out["aborted"]:
        why.append("mechanics gate aborted: " + ", ".join(f"{x['arm']} s{x['seed']}" for x in out["aborted"]))
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
        why.append("seed-0 futility rule(s): " + ", ".join(fut_hit) + "; do not run seeds 1-2")
        if out["futility"]["only_first"]:
            why.append("only F1 fails: laps real but small; Think-1b gets its own prereg")
    else:
        verdict = "INCOMPLETE"
        miss = [f"{n} {sorted(set(SEEDS) - set(d))}" for n, d in (("t", T[8]), ("t1", t1[1]), ("a", a), ("aplus", ap), ("b", b))
                if not have(d)]
        why.append("missing seeds: " + ("; ".join(miss) if miss else "none") + ("; a seed-0 main_repeat" if tol is None else ""))
        if any(m["status"] == "clear" for m in F_) and not fut_hit and 0 in T[8]:
            why.append("seed-0 futility rules did not fire: go on to seeds 1-2")
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
    P("THINK-1 SUMMARY  (accuracy in percent, validation unless said)")
    if data_note:
        P(data_note)
    for n in o["notes"]:
        P("note: " + n)
    for x in o["aborted"]:
        P(f"ABORTED  {x['arm']} seed {x['seed']}: {x['reason']}")
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
    P(f"swap board     {f2(ls['swap']):>6}   costs {sg(ls['swap_drop'])}{ci_txt(o['intervals']['S8_minus_swap'])}")
    P(f"mean board     {f2(ls['mean_board']):>6}   costs {sg(ls['mean_drop'])}")
    P(f"repeat delta1  {f2(ls['repeat_delta1']):>6}   costs {sg(ls['rep_drop'])}{ci_txt(o['intervals']['S8_minus_rep'])}")
    P(f"gates off      {f2(ls['gates_off']):>6}   rows unlike arm a: {ls['gates_off_rows_differing_from_a']} (must be 0)")
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
        P(f"{'':21}S(8) - best floor {sg(g['ci']['value'])}{ci_txt(g['ci'])}")
    for gid, title in (("R1", "R1 slope"), ("R2", "R2 monotone"), ("R3", "R3 no collapse"), ("R4", "R4 laps, not parameters")):
        P(f"{title}: {o['R_groups'][gid]}")
        for m in o["marks"]:
            if m["id"].startswith(gid):
                body = {"R1a": lambda m: f"S(8)-S(1) {sg(m['value'])} needs >= {m['need']}{ci_txt(m['ci'])}",
                        "R1b": lambda m: f"per seed {', '.join(sg(v) for v in m['per_seed'].values()) or '--'} each >= {m['need']}",
                        "R2a": lambda m: f"S(2) {f2(m['a'])} vs S(1) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R2b": lambda m: f"S(4) {f2(m['a'])} vs S(2) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R2c": lambda m: f"S(8) {f2(m['a'])} vs S(4) {f2(m['b'])} - tol {f2(m['tol'])}",
                        "R3a": lambda m: f"S(12)-S(8) {sg(m['value'])} needs >= {m['need']}",
                        "R3b": lambda m: f"per seed {', '.join(sg(v) for v in m['per_seed'].values()) or '--'} each >= {m['need']}",
                        "R4a": lambda m: f"S(8)-T1 {sg(m['value'])} needs >= {m['need']}{ci_txt(m['ci'])}",
                        "R4b": lambda m: f"S(8)-repeat {sg(m['value'])} needs >= {m['need']}{ci_txt(m['ci'])}"}[m["id"]](m)
                line(m, body)
    P(f"PASS needs G and R:  G {o['groups']['G']}, R {o['R']}")
    P("")
    P("== 5. Wrong-if rules (triggered = the idea is refuted) ==")
    for m in o["marks"]:
        if m["id"].startswith("W"):
            line(m, f"{m['text']}   now {sg(m['value']) if m['id'] != 'W4' else f2(m['value'])}")
    P("")
    P("== 6. Futility stop (seed 0 only; triggered = skip seeds 1-2) ==")
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
          f" needs >= {m['need']:.1f}{ci_txt(m)}")
    sl = o["secondary"]["slices"]
    if sl:
        P("")
        P("S(8)-T1 by slice (95% paired bootstrap):")
        P(f"{'slice':<26}{'n':>5} {'arm a':>6} {'T1':>6} {'S(8)':>6}  diff")
        for name, r in sl.items():
            d = r["S8_minus_T1"]
            P(f"{name[:25]:<26}{r['n']:>5} {f2(r['a']):>6} {f2(r['T1']):>6} {f2(r['S8']):>6}  "
              f"{sg(d and d['value'])}{ci_txt(d).replace('  95% ', ' ')}")
    P("")
    P(f"VERDICT: {o['verdict']}")
    for w in o["why"]:
        P("  " + w)
    return "\n".join(L)


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
