"""Aggregate results/*.json into results/SUMMARY.md (mean +- sd over seeds, pass/fail against PREREG.md)."""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from .models import ARMS

RES = Path(__file__).parent / "results"
DIRS = {"A->B": ("B", "ab_v"), "B->A": ("A", None)}      # direction -> (head that must use the message, probe key)
CHANCE = 1 / 8
REAL_MIN, ABL_MAX, PROBE_MIN, LEAK, BROKEN = 0.90, 0.16, 0.80, 0.20, 0.50


def pm(xs: list[float]) -> str:
    return "n/a" if not xs else f"{100 * st.mean(xs):.1f}+-{100 * (st.stdev(xs) if len(xs) > 1 else 0):.1f}"


def vals(runs: list[dict], key: str, mode: str, head: str) -> list[float]:
    return [r[key][mode][head] for r in runs if mode in r[key]]


def probe(runs: list[dict], dirn: str) -> list[float]:
    out = []
    for r in runs:
        p = r["probe"]
        if p:
            out.append(p["ab_v"] if dirn == "A->B" else p["ba_u"])
    return out


def main() -> None:
    runs = [json.loads(p.read_text()) for p in sorted(RES.glob("*_s*.json"))]
    rows, verdicts, wrong = [], {}, []
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        if not rs:
            continue
        for dirn, (head, _) in DIRS.items():
            m = {k: vals(rs, "acc", k, head) for k in ("real", "off", "shuffle", "mean")}
            held, pr = vals(rs, "acc_heldout", "real", head), probe(rs, dirn)
            mean = lambda xs: st.mean(xs) if xs else None
            if arm == "none":
                v = "baseline"
            else:
                ok = (mean(m["real"]) >= REAL_MIN and mean(m["shuffle"]) <= ABL_MAX and mean(m["mean"]) <= ABL_MAX
                      and mean(pr) is not None and mean(pr) >= PROBE_MIN)
                v = "PASS" if ok else "FAIL"
            verdicts[(arm, dirn)] = v
            if arm in ("none", "ema_const") and mean(m["real"]) > LEAK:
                wrong.append(f"{arm} {dirn} real {100 * mean(m['real']):.1f}% > 20% (task leaks)")
            if arm not in ("none", "ema_const") and mean(m["real"]) >= REAL_MIN and mean(m["shuffle"]) >= BROKEN:
                wrong.append(f"{arm} {dirn} real >= 90% but shuffle >= 50%")
            rows.append(f"| {arm} | {dirn} | {len(rs)} | {pm(m['real'])} | {pm(m['off'])} | {pm(m['shuffle'])} | {pm(m['mean'])} | {pm(pr)} | {pm(held)} | {v} |")
    t = [r["train_s"] for r in runs]
    out = ["# bridgelab summary", "",
           f"Accuracy %, mean+-sd over seeds. Chance = {100 * CHANCE:.1f}%. Direction A->B = head B (needs v from A); B->A = head A (needs u from B).",
           "Probe: A->B message -> v; B->A message -> u. ema_const shuffle is a no-op by construction (all items get one vector).", "",
           "| arm | direction | seeds | real | off | shuffle | mean-msg | probe | heldout-names real | verdict |", "|---|---|---|---|---|---|---|---|---|---|", *rows, "",
           "Pass = real >= 90, shuffle <= 16, mean-msg <= 16, probe >= 80 (PREREG.md).", "",
           "Proved-wrong checks: " + ("; ".join(wrong) if wrong else "none triggered."), "",
           f"Total train time (sum over runs): {sum(t) / 60:.1f} min; mean per run {st.mean(t) / 60 if t else 0:.1f} min."]
    (RES / "SUMMARY.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
