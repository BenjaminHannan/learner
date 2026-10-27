#!/usr/bin/env python3
"""Exp 78 (registered selector, numpy only): exp-76-exact LTT on a fresh CAL.

Procedure is exp 76 verbatim (scripts/fable_abstain76_ltt.py, whose grid
builder is reused read-only; exp 64/76 files never edited): candidate-quantile
grid (linspace(114, N_cand, 15) target counts, every point m >= 114), sealed
label-free before any label read, alpha = 0.02, delta = 0.10 pooled,
fixed-sequence most -> least conservative. Added reporting only:
H3 applies exp 76's tau-hat UNCHANGED to the test panels (the real
confirmation: does the old gate still give <= 2% wrong writes?).
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
import fable_abstain64_ltt as L64  # reuse: tail test, CP bound, stats
import fable_abstain76_ltt as L76  # reuse: candidate-quantile grid builder

ALPHA = L64.ALPHA
DELTA = L64.DELTA
M_MIN = 114
TAU_REGISTERED = L64.TAU_REGISTERED
ARMS = L64.ARMS
TEST_PANELS = L64.TEST_PANELS
OLD_TAU = {"tape": 0.088756, "bigru": 0.30286}  # exp 76 certified tau-hat

_GRID_SEALED = {"done": False}
_TAU_SEALED = {"done": False}
_OPEN_LOG: list[tuple[str, bool, bool]] = []


def load_unlabeled(path: Path) -> list[tuple[float, bool]]:
    assert not _GRID_SEALED["done"], "grid phase over: use load_rows after seal"
    raw = json.loads(path.read_text())
    out = [(float(r["s"]), bool(r["cand"])) for r in raw]
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="ltt_summary.json")
    a = ap.parse_args()
    d = Path(a.dir)

    need0 = math.log(DELTA) / math.log1p(-ALPHA)
    print(f"L2: m >= ln({DELTA})/ln(1-{ALPHA}) = {need0:.4f} -> {math.ceil(need0)}")
    assert math.ceil(need0) == 114, "L2 114-check failed"
    assert L64.required_m(0) == 114 and L64.required_m(1) == 194

    grids: dict[str, list[float]] = {}
    for arm in ARMS:
        unl = load_unlabeled(d / f"per_sentence_{arm}_cal.json")
        grid, targets = L76.build_grid_candidate(unl)
        grids[arm] = grid
        n = sum(1 for _, c in unl if c)
        print(f"{arm}: CAL candidates N={n}, grid targets m={targets[0]}..{targets[-1]} "
              f"G_eff={len(grid)} (tau_1={grid[0]:.4f} .. tau_end={grid[-1]:.4f})")
    (d / "GRID_SEAL.json").write_text(json.dumps(
        {"rule": "linspace(114,N_cand,15) target counts; tau_j=m_j-th candidate score",
         "grids": grids}, indent=1))
    _GRID_SEALED["done"] = True
    print("grid sealed to GRID_SEAL.json BEFORE any label read (gold/ok untouched)")

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
        else:
            acc = [c for c in detail if c["accept"]][-1]
            print(f"{arm}: tau-hat = {last_accepted:.6f} "
                  f"(m={acc['m']}, k={acc['k']}, bound={acc['bound']:.4f})")

    _TAU_SEALED["done"] = True

    summary: dict = {"tau_hat": tau_hat, "grids": grids, "test": {},
                     "cal_stats": {}, "old_tau": {}}
    for arm in ARMS:
        t = tau_hat[arm]
        summary["cal_stats"][arm] = {
            "ltt": L64.stats_at(cal[arm], t),
            "registered_0.5": L64.stats_at(cal[arm], TAU_REGISTERED)}
        for panel in TEST_PANELS:
            rows = load_rows(d / f"per_sentence_{arm}_{panel}.json", is_test=True)
            assert sum(1 for r in rows if r["gold"] in L64.WRITE_ACTS) > 0
            got = L64.stats_at(rows, t)
            ref = L64.stats_at(rows, TAU_REGISTERED)
            base = L64.stats_at(rows, 0.0)
            old = L64.stats_at(rows, OLD_TAU[arm])
            summary["test"][f"{arm}/{panel}"] = {"ltt": got, "registered_0.5": ref,
                                                 "tau0_0.0": base}
            summary["old_tau"][f"{arm}/{panel}"] = old
            r_str = "0/0 (abstain-all)" if got["rate"] is None else f"{got['rate']:.4f}"
            o_str = "0/0" if old["rate"] is None else f"{old['rate']:.4f}"
            print(f"{arm}/{panel}: LTT writes={got['writes']} wrong={got['wrong']} "
                  f"rate={r_str} cov={got['cov']:.4f} | "
                  f"reg@0.5 writes={ref['writes']} wrong={ref['wrong']} cov={ref['cov']:.4f} | "
                  f"tau0 writes={base['writes']} wrong={base['wrong']} cov={base['cov']:.4f} | "
                  f"OLD76 writes={old['writes']} wrong={old['wrong']} rate={o_str}")

    print("--- H3: fresh tau-hat vs exp-76 tau-hat ---")
    for arm in ARMS:
        t, o = tau_hat[arm], OLD_TAU[arm]
        if t is None:
            print(f"H3 {arm}: fresh=ABSTAIN-ALL vs old={o:.6f} (no finite delta)")
        else:
            print(f"H3 {arm}: fresh={t:.6f} old={o:.6f} |delta|={abs(t - o):.6f}")

    g1_ok = True
    for arm in ARMS:
        t = tau_hat[arm]
        if t is None:
            print(f"H1 {arm}: NO CERTIFIED TAU (ABSTAIN-ALL; see stop point above)")
            g1_ok = False
        else:
            s = summary["cal_stats"][arm]["ltt"]
            ok = s["writes"] >= M_MIN and s["wrong"] == 0
            g1_ok &= ok
            print(f"H1 {arm}: {'PASS' if ok else 'FAIL'} "
                  f"(m={s['writes']}, k={s['wrong']})")
    h2_ok = True
    for key, v in summary["test"].items():
        rate = v["ltt"]["rate"]
        ok = (rate is None) or (rate <= ALPHA)
        h2_ok &= ok
        tag = " (vacuous: 0/0)" if rate is None else ""
        print(f"H2 {key}: {'PASS' if ok else 'FAIL'}{tag}")
    h3b_ok = True
    for key, v in summary["old_tau"].items():
        rate = v["rate"]
        ok = (rate is None) or (rate <= ALPHA)
        h3b_ok &= ok
        print(f"H3b(old-tau) {key}: {'PASS' if ok else 'FAIL'} "
              f"(writes={v['writes']} wrong={v['wrong']})")
    h4_ok = all(v["ltt"]["cov"] is not None for v in summary["test"].values())
    print(f"H4 coverage reported on {len(summary['test'])}/6 panel-arms: "
          f"{'PASS' if h4_ok else 'FAIL'}")
    assert all(ts for name, gs, ts in _OPEN_LOG
               if not name.endswith("_cal.json")), "G4 post-check failed"

    for f in sorted(d.glob("per_sentence_*.json")):
        print(f"input {f.name} sha256={hashlib.sha256(f.read_bytes()).hexdigest()[:16]}…")
    (d / a.out).write_text(json.dumps(summary, indent=1))
    print(f"H1 {'PASS' if g1_ok else 'FAIL'} · H2 {'PASS' if h2_ok else 'FAIL'} · "
          f"H3b {'PASS' if h3b_ok else 'FAIL'} · H4 {'PASS' if h4_ok else 'FAIL'} · G4 PASS")


if __name__ == "__main__":
    main()
