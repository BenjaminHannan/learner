"""Paired exact McNemar per item, pooled over the 2 seeds, plus the per-seed sign check; the pass marks of the pre-registration.

Input: graded files results/recallread/graded/{arm}_{seed}.jsonl (grade.py). Baseline arms (D0, D2, D3, D4) have no LoRA: their {arm}_s0 file serves both seeds,
so in the pooled test their rows appear twice (the per-seed tests are the conservative check, and the sign must hold in each).
"""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

from .arms import BASE_ARMS

SEEDS = ("1", "2")


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def load(resdir) -> dict:
    """{(arm, seed): {row_id: row}} with baseline arms stored under seed 's0'."""
    g = Path(resdir) / "results" / "recallread" / "graded"
    out = {}
    for f in sorted(g.glob("*.jsonl")):
        arm, s = f.stem.rsplit("_", 1)
        out[(arm, "0" if s == "s0" else s)] = {r["row_id"]: r for r in map(json.loads, f.read_text().splitlines()) if r}
    return out


def rows(data, arm, seed, split=None, exclude_dev=False):
    d = data.get((arm, "0")) if arm in BASE_ARMS else data.get((arm, seed))
    if d is None:
        return {}
    return {k: r for k, r in d.items() if (split is None or r["split"] == split) and not (exclude_dev and r.get("dev"))}


def paired(a: dict, b: dict) -> dict:
    ks = sorted(set(a) & set(b))
    ao = sum(a[k]["correct"] and not b[k]["correct"] for k in ks)
    bo = sum(b[k]["correct"] and not a[k]["correct"] for k in ks)
    n = max(len(ks), 1)
    pa, pb = 100 * sum(a[k]["correct"] for k in ks) / n, 100 * sum(b[k]["correct"] for k in ks) / n
    return dict(n=len(ks), a=round(pa, 1), b=round(pb, 1), b_minus_a=round(pb - pa, 1), a_only=ao, b_only=bo, p=round(mcnemar_exact(ao, bo), 5))


def pooled(data, arm_a, arm_b, split, **kw):
    """Stack the two seeds (keys (seed, row_id)); also per-seed results."""
    A, B, per = {}, {}, {}
    for s in SEEDS:
        ra, rb = rows(data, arm_a, s, split, **kw), rows(data, arm_b, s, split, **kw)
        if not ra or not rb:
            continue
        per[s] = paired(ra, rb)
        A.update({(s, k): v for k, v in ra.items()})
        B.update({(s, k): v for k, v in rb.items()})
    return dict(pooled=paired(A, B) if A else None, per_seed=per)


def acc(data, arm, split, **kw):
    v = [r["correct"] for s in SEEDS for r in rows(data, arm, s, split, **kw).values()]
    return round(100 * sum(v) / len(v), 1) if v else None


def best_rival(data, split):
    c = {a: acc(data, a, split) for a in ("D3", "D4")}
    c = {a: v for a, v in c.items() if v is not None}
    return max(c, key=c.get) if c else None


def mark(data, split, margin, name):
    rv = best_rival(data, split)
    if rv is None or not rows(data, "R", "1", split):
        return dict(name=name, status="MISSING DATA")
    t = pooled(data, rv, "R", split)  # a = rival, b = R
    ps = t["pooled"]
    sign = all(v["b_minus_a"] > 0 for v in t["per_seed"].values()) and len(t["per_seed"]) == len(SEEDS)
    ok = ps["b_minus_a"] >= margin and ps["p"] < 0.05 and ps["b_minus_a"] > 0 and sign
    return dict(name=name, split=split, rival=rv, margin=margin, R_minus_rival=ps["b_minus_a"], p=ps["p"], per_seed_diff={s: v["b_minus_a"] for s, v in t["per_seed"].items()},
                sign_holds_each_seed=sign, R=ps["b"], rival_acc=ps["a"], status="PASS" if ok else "FAIL")


def pass_marks(data) -> dict:
    out = {}
    out["1_natural_twohop"] = mark(data, "twohop_nat", 8, "R >= max(D3,D4) + 8, p<0.05")
    out["2_condition_W"] = mark(data, "W_nat", 15, "R >= max(D3,D4) + 15, p<0.05")
    for key, split, slack, nm in (("3_onehop", "onehop", 1, "R >= D0 - 1"), ("4_never_taught", "never", 5, "R >= D0 - 5 ('don't know' rate)")):
        r, d = acc(data, "R", split), acc(data, "D0", split)
        out[key] = dict(name=nm, R=r, D0=d, status="MISSING DATA" if r is None or d is None else ("PASS" if r >= d - slack else "FAIL"))
    out["5_mac"] = dict(name="Mac latency <= 1.5 s, other agents' tok/s drop <= 10%", status="NOT RUN (out of scope for this job; later step, mac_latency.py)")
    m1, m2 = out["1_natural_twohop"], out["2_condition_W"]
    wrong = None
    if m1.get("R_minus_rival") is not None and m2.get("R_minus_rival") is not None:
        wrong = m1["R_minus_rival"] < 3 and m2["R_minus_rival"] < 8
    out["proves_wrong"] = dict(rule="R - max(D3,D4) < 3 on natural AND < 8 on condition W", triggered=wrong)
    out["accuracy_marks_1_to_4"] = "ALL PASS" if all(out[k]["status"] == "PASS" for k in ("1_natural_twohop", "2_condition_W", "3_onehop", "4_never_taught")) else (
        "pass 2 alone: keep only as fallback when diary search misses" if m2["status"] == "PASS" and m1["status"] != "PASS" else "NOT ALL PASS")
    return out


def bridge_diagnostic(data, split="twohop_nat"):
    v = [r.get("bridge_named") for s in SEEDS for r in rows(data, "R", s, split).values() if r.get("bridge_named") is not None]
    br = round(100 * sum(v) / len(v), 1) if v else None
    a = acc(data, "R", split)
    return dict(bridge_named_pct=br, R_twohop_acc=a, reader_bottleneck=(br is not None and a is not None and br > 80 and a < 50))


def rate(data, arm, split, field):
    v = [r.get(field) for s in SEEDS for r in rows(data, arm, s, split).values() if r.get(field) is not None]
    return round(100 * sum(v) / len(v), 1) if v else None


def summary(data) -> dict:
    arms = sorted({a for a, _ in data})
    splits = ("twohop_nat", "twohop_gap", "W_nat", "onehop", "never")
    tab = {a: {sp: acc(data, a, sp) for sp in splits} for a in arms}
    diag = {a: {sp: dict(bridge_named=rate(data, a, sp, "bridge_named"), hit3_hop1=rate(data, a, sp, "hit3_hop1"), hit3_hop2=rate(data, a, sp, "hit3_hop2"))
                for sp in ("twohop_nat", "W_nat")} for a in arms}
    extra = {}
    for nm, (x, y, sp) in {"D1_vs_D0_natural": ("D0", "D1", "twohop_nat"), "R_vs_D2_natural": ("D2", "R", "twohop_nat"), "RD3_vs_D3_natural": ("D3", "RD3", "twohop_nat"),
                           "RD3_vs_D3_W": ("D3", "RD3", "W_nat"), "R_vs_D0_natural": ("D0", "R", "twohop_nat"), "R_vs_D0_W": ("D0", "R", "W_nat"),
                           "R_vs_D1_natural": ("D1", "R", "twohop_nat")}.items():
        if all(rows(data, a, "1", sp) for a in (x, y)):
            extra[nm] = pooled(data, x, y, sp)
    return dict(accuracy_pct=tab, diagnostics=diag, secondary=extra, pass_marks=pass_marks(data), bridge_diagnostic=bridge_diagnostic(data),
                gap_vs_natural_note="twohop_gap is lexically filtered and favours every expansion arm; pass marks use natural phrasing")
