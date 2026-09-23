#!/usr/bin/env python3
"""Exp 64 (registered selector, numpy only): LTT WRITE threshold on rung-1 ears.

Phase 1 opens ONLY the CAL dumps, runs the pre-registered fixed-sequence LTT
(doc 59 sec 2; LTT paper fixed-sequence with exact binomial tail), seals tau-hat.
Phase 2 opens the test dumps once and reports writes / wrong writes /
empirical wrong-write rate / coverage per arm, plus the same at the rung-1
registered tau_exec = 0.5 and the uncertified tau0 = 0.0 for comparison.
ABSTAIN-ALL tau-hat means zero writes on every panel (coverage 0).

L4 is enforced in code: the test loader asserts _TAU_SEALED["done"], and the
opened-path log is asserted to be CAL-only before the seal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ALPHA = 0.02          # target accepted wrong-write rate
DELTA = 0.10          # 90% confidence (pooled, single stratum)
G = 15                # grid size (doc 59)
TAU_REGISTERED = 0.5  # rung-1 ensemble tau_exec, both arms (score-*.json)
WRITE_ACTS = {"person", "alias", "teach", "correct", "forget"}
ARMS = ("tape", "bigru")
TEST_PANELS = ("t_seen", "t_new", "t_hard")

_OPEN_LOG: list[tuple[str, bool]] = []  # (filename, tau_already_sealed)
_TAU_SEALED = {"done": False}


def load_rows(path: Path, *, is_test: bool) -> list[dict]:
    if is_test:
        assert _TAU_SEALED["done"], \
            "L4 violated: a test file was opened before tau-hat was sealed"
    _OPEN_LOG.append((path.name, _TAU_SEALED["done"]))
    return json.loads(path.read_text())


def binom_tail(k: int, m: int, p: float) -> float:
    """P(X <= k | m, p), log-space sum. m = 0 -> 1.0 (vacuous, never rejects)."""
    if m <= 0 or k >= m:
        return 1.0
    if k < 0:
        return 0.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(m + 1) - math.lgamma(i + 1) - math.lgamma(m - i + 1)
             + i * lp + (m - i) * lq for i in range(k + 1)]
    mx = max(terms)
    return sum(math.exp(t - mx) for t in terms) * math.exp(mx)


def cp_upper(k: int, m: int, delta: float = DELTA) -> float:
    """Clopper-Pearson upper bound: p* with tail(k; m, p*) = delta (bisection)."""
    if m <= 0:
        return 1.0
    if k >= m:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if binom_tail(k, m, mid) > delta:
            lo = mid
        else:
            hi = mid
    return hi


def required_m(k: int, alpha: float = ALPHA, delta: float = DELTA) -> int:
    """Smallest m with tail(k; m, alpha) <= delta (exact search)."""
    m = k
    while binom_tail(k, m, alpha) > delta:
        m += 1
        assert m < 10_000_000, "required_m did not converge"
    return m


def build_grid(scores: np.ndarray) -> list[float]:
    """G acceptance-fraction quantiles of ALL CAL scores, most-conservative first."""
    fracs = np.linspace(0.01, 1.00, G)
    taus = [float(np.quantile(scores, 1.0 - f)) for f in fracs]
    grid: list[float] = []
    for t in taus:
        if not grid or t != grid[-1]:
            grid.append(t)
    return grid


def stats_at(rows: list[dict], tau) -> dict:
    # tau = None is the LTT ABSTAIN-ALL outcome: the gate accepts nothing,
    # so no write happens (writes = 0, rate = 0/0, coverage = 0).
    if tau is None:
        g = sum(1 for r in rows if r["gold"] in WRITE_ACTS)
        return {"writes": 0, "wrong": 0, "rate": None, "state_golds": g,
                "state_written": 0, "cov": (0.0 if g else None)}
    writes = wrong = state_golds = state_written = 0
    for r in rows:
        if r["gold"] in WRITE_ACTS:
            state_golds += 1
        if r["cand"] and r["s"] >= tau:
            writes += 1
            if not r["ok"]:
                wrong += 1
            if r["gold"] in WRITE_ACTS:
                state_written += 1
    rate = (wrong / writes) if writes else None  # None = 0/0 (no writes)
    cov = (state_written / state_golds) if state_golds else None
    return {"writes": writes, "wrong": wrong, "rate": rate,
            "state_golds": state_golds, "state_written": state_written, "cov": cov}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="ltt_summary.json")
    a = ap.parse_args()
    d = Path(a.dir)

    # ---- L2 arithmetic (doc 59 sec 3, pooled delta = 0.10) ----
    need0 = math.log(DELTA) / math.log1p(-ALPHA)
    print(f"L2: m >= ln({DELTA})/ln(1-{ALPHA}) = {need0:.4f} -> {math.ceil(need0)} "
          f"(doc 59 sec 3: 114 accepted with 0 errors)")
    assert math.ceil(need0) == 114, "L2 114-check failed"
    assert required_m(0) == 114, "L2 exact-tail 0-error check failed"
    print(f"L2: exact-tail needs: k=0 -> m={required_m(0)}, k=1 -> m={required_m(1)} "
          f"(doc 59 sec 3: ~195)")

    # ---- Phase 1: CAL only ----
    cal = {arm: load_rows(d / f"per_sentence_{arm}_cal.json", is_test=False)
           for arm in ARMS}
    assert all(name.endswith("_cal.json") and not sealed
               for name, sealed in _OPEN_LOG), "L4: non-CAL file opened pre-seal"

    tau_hat: dict[str, float | None] = {}
    cal_detail: dict = {}
    for arm in ARMS:
        scores = np.array([r["s"] for r in cal[arm]])
        grid = build_grid(scores)
        print(f"{arm}: CAL n={len(scores)}, grid G_eff={len(grid)} "
              f"(tau_1={grid[0]:.4f} .. tau_end={grid[-1]:.4f})")
        last_accepted = None
        detail = []
        for j, tau in enumerate(grid, 1):
            m = sum(1 for r in cal[arm] if r["cand"] and r["s"] >= tau)
            k = sum(1 for r in cal[arm] if r["cand"] and r["s"] >= tau and not r["ok"])
            p = binom_tail(k, m, ALPHA)
            b = cp_upper(k, m)
            accept = bool(p <= DELTA)
            # duality between the tail test and the CP bound (must agree)
            assert accept == bool(b <= ALPHA + 1e-12), \
                f"duality violated at {arm} cand {j}: p={p}, bound={b}"
            detail.append({"j": j, "tau": tau, "m": m, "k": k, "p": p,
                           "bound": b, "accept": accept})
            print(f"  cand {j:2d}: tau={tau:.4f} m={m:5d} k={k:3d} "
                  f"p={p:.4f} bound={b:.4f} {'ACCEPT' if accept else 'STOP'}")
            if accept:
                last_accepted = tau
            else:
                break
        tau_hat[arm] = last_accepted
        cal_detail[arm] = detail
        if last_accepted is None:
            print(f"{arm}: tau-hat = ABSTAIN-ALL (stopped at cand 1)")
        else:
            acc = [c for c in detail if c["accept"]][-1]
            print(f"{arm}: tau-hat = {last_accepted:.6f} "
                  f"(m={acc['m']}, k={acc['k']}, bound={acc['bound']:.4f})")

    # ---- seal tau-hat BEFORE any test file is opened ----
    _TAU_SEALED["done"] = True

    # ---- Phase 2: apply tau-hat once per test panel ----
    summary: dict = {"tau_hat": tau_hat, "test": {}, "cal_stats": {}}
    for arm in ARMS:
        t = tau_hat[arm]
        summary["cal_stats"][arm] = {
            "ltt": stats_at(cal[arm], t),
            "registered_0.5": stats_at(cal[arm], TAU_REGISTERED)}
        for panel in TEST_PANELS:
            rows = load_rows(d / f"per_sentence_{arm}_{panel}.json", is_test=True)
            assert sum(1 for r in rows if r["gold"] in WRITE_ACTS) > 0
            got = stats_at(rows, t)
            ref = stats_at(rows, TAU_REGISTERED)
            base = stats_at(rows, 0.0)  # PASSMARKS-registered tau0 = 0.0, UNCERTIFIED
            summary["test"][f"{arm}/{panel}"] = {"ltt": got, "registered_0.5": ref,
                                                 "tau0_0.0": base}
            r_str = "0/0 (abstain-all)" if got["rate"] is None else f"{got['rate']:.4f}"
            cov_str = "n/a" if got["cov"] is None else f"{got['cov']:.4f}"
            ref_str = "0/0" if ref["rate"] is None else f"{ref['rate']:.4f}"
            base_str = "0/0" if base["rate"] is None else f"{base['rate']:.4f}"
            print(f"{arm}/{panel}: LTT writes={got['writes']} wrong={got['wrong']} "
                  f"rate={r_str} cov={cov_str} | "
                  f"reg@0.5 writes={ref['writes']} wrong={ref['wrong']} "
                  f"rate={ref_str} cov={ref['cov']:.4f} | "
                  f"tau0 writes={base['writes']} wrong={base['wrong']} "
                  f"rate={base_str} cov={base['cov']:.4f}")

    # ---- L1 / L3 verdicts ----
    l1_ok = True
    for key, v in summary["test"].items():
        rate = v["ltt"]["rate"]
        ok = (rate is None) or (rate <= ALPHA)
        l1_ok &= ok
        tag = " (vacuous: 0/0, abstain-all)" if rate is None else ""
        print(f"L1 {key}: {'PASS' if ok else 'FAIL'}{tag}")
    l3_ok = all(v["ltt"]["cov"] is not None for v in summary["test"].values())
    print(f"L3 coverage reported on {len(summary['test'])}/6 panel-arms: "
          f"{'PASS' if l3_ok else 'FAIL'}")
    assert all(sealed for name, sealed in _OPEN_LOG
               if not name.endswith("_cal.json")), "L4 post-check failed"

    for f in sorted(d.glob("per_sentence_*.json")):
        print(f"input {f.name} sha256={hashlib.sha256(f.read_bytes()).hexdigest()[:16]}…")
    (d / a.out).write_text(json.dumps(summary, indent=1))
    print(f"L1 {'PASS' if l1_ok else 'FAIL'} · L2 PASS · "
          f"L3 {'PASS' if l3_ok else 'FAIL'} · L4 PASS")


if __name__ == "__main__":
    main()
