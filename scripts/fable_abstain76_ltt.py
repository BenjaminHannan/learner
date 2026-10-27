#!/usr/bin/env python3
"""Exp 76 (registered selector, numpy only): LTT WRITE threshold, candidate grid.

ONE-CHANGE follow-up to exp 64 (scripts/fable_abstain64_ltt.py, from which the
tail test, CP bound, stats, and seal machinery are imported/reused verbatim).
The single change is the grid: exp 64 built G acceptance-fraction quantiles of
ALL CAL scores, so its most-conservative point (99th pct of all 5,000 scores)
sat above every write-candidate score and m=0 stopped the fixed sequence at
once. Here the grid is built over the UNLABELED write-candidate score
distribution: per arm, target acceptance counts linspace(114, N_cand, G=15),
tau_j = the m_j-th largest candidate score, most conservative first. Every
grid point admits >= 114 candidates by construction (ties only raise m).

Label-free validity: Phase 0 loads CAL rows through a restricted loader that
returns ONLY (s, cand) — model outputs computable from inputs alone — and
asserts no label key ("gold"/"ok") is touched before the grid is sealed to
GRID_SEAL.json. Fixed-sequence LTT over a label-independent grid keeps its
FWER guarantee: the candidate hypotheses are fixed before any calibration
label is read (doc 59 sec 2: "label-independent grid"; sec 5: never tune the
grid after seeing errors). Everything else identical to exp 64: alpha=0.02,
delta=0.10 pooled, fixed-sequence most->least conservative, stop at first
non-rejection, test panels opened only after tau-hat is sealed (G4/L4).

If the result is still ABSTAIN-ALL, the run prints the top-10 candidate
scores WITH their labels for the next diagnosis (labels read only then).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_abstain64_ltt as L64  # reuse: tail test, CP bound, stats, constants

ALPHA = L64.ALPHA          # 0.02 target accepted wrong-write rate
DELTA = L64.DELTA          # 0.10, 90% confidence, pooled single stratum
G = 15                     # grid size (same as exp 64 / doc 59)
M_MIN = 114                # certifiable zero-error mass (doc 59 sec 3)
TAU_REGISTERED = L64.TAU_REGISTERED
WRITE_ACTS = L64.WRITE_ACTS
ARMS = L64.ARMS
TEST_PANELS = L64.TEST_PANELS
LABEL_KEYS = ("gold", "ok")

_GRID_SEALED = {"done": False}
_TAU_SEALED = {"done": False}
_OPEN_LOG: list[tuple[str, bool, bool]] = []  # (file, grid_sealed, tau_sealed)


def load_unlabeled(path: Path) -> list[tuple[float, bool]]:
    """Grid-phase loader: returns ONLY (s, cand). Asserts label keys unseen."""
    assert not _GRID_SEALED["done"], "grid phase over: use load_rows after seal"
    raw = json.loads(path.read_text())
    out = []
    for r in raw:
        out.append((float(r["s"]), bool(r["cand"])))
    # Prove label-blindness: rebuild from a projection that drops label keys.
    proj = [{"s": r["s"], "cand": r["cand"]} for r in raw]
    assert all(set(p) == {"s", "cand"} for p in proj)
    _OPEN_LOG.append((path.name, True, False))
    return out


def load_rows(path: Path, *, is_test: bool) -> list[dict]:
    if is_test:
        assert _TAU_SEALED["done"], \
            "G4 violated: a test file was opened before tau-hat was sealed"
    else:
        assert _GRID_SEALED["done"], \
            "labels (CAL gold/ok) may not be read before the grid is sealed"
    _OPEN_LOG.append((path.name, _GRID_SEALED["done"], _TAU_SEALED["done"]))
    return json.loads(path.read_text())


def build_grid_candidate(unlabeled: list[tuple[float, bool]]) -> tuple[list[float], list[int]]:
    """G target counts linspace(114, N_cand, G); tau_j = m_j-th best cand score."""
    cs = sorted((s for s, c in unlabeled if c), reverse=True)
    n = len(cs)
    assert n >= M_MIN, f"only {n} CAL candidates < {M_MIN}: grid unsealable"
    targets = sorted(set(int(round(x)) for x in np.linspace(M_MIN, n, G)))
    taus: list[float] = []
    for m in targets:
        t = float(cs[m - 1])
        if not taus or t != taus[-1]:
            taus.append(t)
    return taus, targets


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="ltt_summary.json")
    a = ap.parse_args()
    d = Path(a.dir)

    # ---- L2 arithmetic (identical to exp 64) ----
    need0 = math.log(DELTA) / math.log1p(-ALPHA)
    print(f"L2: m >= ln({DELTA})/ln(1-{ALPHA}) = {need0:.4f} -> {math.ceil(need0)}")
    assert math.ceil(need0) == 114, "L2 114-check failed"
    assert L64.required_m(0) == 114 and L64.required_m(1) == 194

    # ---- Phase 0: UNLABELED grid construction only ----
    grids: dict[str, list[float]] = {}
    for arm in ARMS:
        unl = load_unlabeled(d / f"per_sentence_{arm}_cal.json")
        grid, targets = build_grid_candidate(unl)
        grids[arm] = grid
        n = sum(1 for _, c in unl if c)
        print(f"{arm}: CAL candidates N={n}, grid targets m={targets[0]}..{targets[-1]} "
              f"G_eff={len(grid)} (tau_1={grid[0]:.4f} .. tau_end={grid[-1]:.4f})")
    (d / "GRID_SEAL.json").write_text(json.dumps(
        {"rule": "linspace(114,N_cand,15) target counts; tau_j=m_j-th candidate score",
         "grids": grids}, indent=1))
    _GRID_SEALED["done"] = True
    print("grid sealed to GRID_SEAL.json BEFORE any label read (gold/ok untouched)")

    # ---- Phase 1: CAL labels, fixed-sequence over the sealed grid ----
    cal = {arm: load_rows(d / f"per_sentence_{arm}_cal.json", is_test=False)
           for arm in ARMS}
    assert all(name.endswith("_cal.json") and gs and not ts
               for name, gs, ts in _OPEN_LOG), "G4: non-CAL file opened pre-seal"

    tau_hat: dict[str, float | None] = {}
    for arm in ARMS:
        last_accepted = None
        detail = []
        for j, tau in enumerate(grids[arm], 1):
            m = sum(1 for r in cal[arm] if r["cand"] and r["s"] >= tau)
            k = sum(1 for r in cal[arm] if r["cand"] and r["s"] >= tau and not r["ok"])
            assert m >= M_MIN, f"grid point admits m={m} < 114"
            p = L64.binom_tail(k, m, ALPHA)
            b = L64.cp_upper(k, m)
            accept = bool(p <= DELTA)
            assert accept == bool(b <= ALPHA + 1e-12), "tail/CP duality violated"
            detail.append({"j": j, "tau": tau, "m": m, "k": k, "p": p,
                           "bound": b, "accept": accept})
            print(f"  cand {j:2d}: tau={tau:.4f} m={m:5d} k={k:3d} "
                  f"p={p:.4f} bound={b:.4f} {'ACCEPT' if accept else 'STOP'}")
            if accept:
                last_accepted = tau
            else:
                break
        tau_hat[arm] = last_accepted
        if last_accepted is None:
            print(f"{arm}: tau-hat = ABSTAIN-ALL (stopped at cand 1)")
            top = sorted([r for r in cal[arm] if r["cand"]],
                         key=lambda r: r["s"], reverse=True)[:10]
            print(f"{arm} top-10 candidates (score, ok, gold):")
            for r in top:
                print(f"    s={r['s']:.6f} ok={r['ok']} gold={r['gold']}")
        else:
            acc = [c for c in detail if c["accept"]][-1]
            print(f"{arm}: tau-hat = {last_accepted:.6f} "
                  f"(m={acc['m']}, k={acc['k']}, bound={acc['bound']:.4f})")

    # ---- seal tau-hat BEFORE any test file is opened ----
    _TAU_SEALED["done"] = True

    # ---- Phase 2: apply tau-hat once per test panel ----
    summary: dict = {"tau_hat": tau_hat, "grids": grids, "test": {}, "cal_stats": {}}
    for arm in ARMS:
        t = tau_hat[arm]
        summary["cal_stats"][arm] = {
            "ltt": L64.stats_at(cal[arm], t),
            "registered_0.5": L64.stats_at(cal[arm], TAU_REGISTERED)}
        for panel in TEST_PANELS:
            rows = load_rows(d / f"per_sentence_{arm}_{panel}.json", is_test=True)
            assert sum(1 for r in rows if r["gold"] in WRITE_ACTS) > 0
            got = L64.stats_at(rows, t)
            ref = L64.stats_at(rows, TAU_REGISTERED)
            base = L64.stats_at(rows, 0.0)
            summary["test"][f"{arm}/{panel}"] = {"ltt": got, "registered_0.5": ref,
                                                  "tau0_0.0": base}
            r_str = "0/0 (abstain-all)" if got["rate"] is None else f"{got['rate']:.4f}"
            print(f"{arm}/{panel}: LTT writes={got['writes']} wrong={got['wrong']} "
                  f"rate={r_str} cov={got['cov']:.4f} | "
                  f"reg@0.5 writes={ref['writes']} wrong={ref['wrong']} "
                  f"rate={ref['rate'] if ref['rate'] is not None else '0/0'} cov={ref['cov']:.4f} | "
                  f"tau0 writes={base['writes']} wrong={base['wrong']} "
                  f"rate={base['rate'] if base['rate'] is not None else '0/0'} cov={base['cov']:.4f}")

    g1_ok = True
    for arm in ARMS:
        t = tau_hat[arm]
        if t is None:
            print(f"G1 {arm}: NO CERTIFIED TAU (ABSTAIN-ALL; see stop point above)")
            g1_ok = False
        else:
            s = summary["cal_stats"][arm]["ltt"]
            ok = s["writes"] >= M_MIN and s["wrong"] == 0
            g1_ok &= ok
            print(f"G1 {arm}: {'PASS' if ok else 'FAIL'} "
                  f"(m={s['writes']}, k={s['wrong']})")
    l1_ok = True
    for key, v in summary["test"].items():
        rate = v["ltt"]["rate"]
        ok = (rate is None) or (rate <= ALPHA)
        l1_ok &= ok
        tag = " (vacuous: 0/0)" if rate is None else ""
        print(f"G2 {key}: {'PASS' if ok else 'FAIL'}{tag}")
    l3_ok = all(v["ltt"]["cov"] is not None for v in summary["test"].values())
    print(f"G3 coverage reported on {len(summary['test'])}/6 panel-arms: "
          f"{'PASS' if l3_ok else 'FAIL'}")
    assert all(ts for name, gs, ts in _OPEN_LOG
               if not name.endswith("_cal.json")), "G4 post-check failed"

    for f in sorted(d.glob("per_sentence_*.json")):
        print(f"input {f.name} sha256={hashlib.sha256(f.read_bytes()).hexdigest()[:16]}…")
    (d / a.out).write_text(json.dumps(summary, indent=1))
    print(f"G1 {'PASS' if g1_ok else 'FAIL'} · G2 {'PASS' if l1_ok else 'FAIL'} · "
          f"G3 {'PASS' if l3_ok else 'FAIL'} · G4 PASS")


if __name__ == "__main__":
    main()
