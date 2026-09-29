#!/usr/bin/env python3
"""Judge for the history-read test (artifacts/claude-dir-hist-20260929/PASSMARKS.md; the page wins if they disagree).

  python -B scripts/claude_dir_hist_marks.py selftest     # reproduces the baseline numbers and checks the word logic on made-up numbers
  python -B scripts/claude_dir_hist_marks.py judge --hist DIR --ctrl DIR   # DIR has {name}-s{0,1}/adapt.json
F_eq / F_few reads come from claude_dir_h12_marks.f_all (dev panel, 9x9, learned and fixed-16 reads), unedited.
Not executed where written unless python3 alone suffices (it needs no torch)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h12_marks as H  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "artifacts/claude-fewex-20260927/eq-runs"
BAR = {"F_eq": 10.0, "F_few": 10.5}      # PASSMARKS: "gain over the higher comparator"
PLAIN_BAR = 10.0
OLD_MIN = 190


def load(p):
    return json.loads(Path(p).read_text())


def best(run, key):
    r = H.f_all(run)[key]
    return max(r["learned"], r["fixed"])


def judge_seed(hist, ctrl, loop, plain):
    out = {}
    for key in ("F_eq", "F_few"):
        comp = max(best(loop, key), best(ctrl, key))
        out[key] = {"hist": round(best(hist, key), 2), "loop": round(best(loop, key), 2), "ctrl_w1": round(best(ctrl, key), 2),
                    "gain_over_higher": round(best(hist, key) - comp, 2), "pass": best(hist, key) - comp >= BAR[key]}
    out["plain_row"] = {"gain_over_plain": round(best(hist, "F_eq") - best(plain, "F_eq"), 2),
                        "pass": best(hist, "F_eq") - best(plain, "F_eq") >= PLAIN_BAR}
    return out


def word(rows):
    """rows: {seed: judge_seed output}. Every-seed reading."""
    ok = [all(r[k]["pass"] for k in ("F_eq", "F_few", "plain_row")) for r in rows.values()]
    gain = [rows[s]["F_eq"]["gain_over_higher"] for s in rows]
    ctrl_better = [rows[s]["F_eq"]["hist"] < rows[s]["F_eq"]["ctrl_w1"] - 3.33 for s in rows]
    if all(ok):
        return "HISTORY HELPS"
    if all(g <= -BAR["F_eq"] / 2 for g in gain) or all(ctrl_better):
        return "HISTORY DOES NOT HELP (clearly below in both seeds)"
    return "NOT SHOWN"


def main_judge(hist_dir, ctrl_dir):
    rows = {}
    for s in (0, 1):
        rows[s] = judge_seed(load(Path(hist_dir) / f"hist-pre-s{s}/adapt.json"), load(Path(ctrl_dir) / f"histw1-pre-s{s}/adapt.json"),
                             load(BASE / f"loop-s{s}-pre/adapt.json"), load(BASE / f"plain-s{s}-pre/adapt.json"))
    print(json.dumps({"rows": {str(k): v for k, v in rows.items()}, "word": word(rows)}, indent=1))


def selftest():
    loop = {s: load(BASE / f"loop-s{s}-pre/adapt.json") for s in (0, 1)}
    plain = {s: load(BASE / f"plain-s{s}-pre/adapt.json") for s in (0, 1)}
    print("baseline F_eq (higher read):", [round(best(loop[s], "F_eq"), 2) for s in (0, 1)], "plain:", [round(best(plain[s], "F_eq"), 2) for s in (0, 1)])
    assert abs(best(loop[0], "F_eq") - 51.21) < 0.02 and abs(best(loop[1], "F_eq") - 51.67) < 0.02
    # word logic: control = the loop itself (a run cannot gain over itself) -> NOT SHOWN; a run 12 points up in both seeds -> HELPS
    same = {s: judge_seed(loop[s], loop[s], loop[s], plain[s]) for s in (0, 1)}
    assert word(same) == "NOT SHOWN", word(same)
    up = {s: {"F_eq": {"hist": 63, "loop": 51, "ctrl_w1": 50, "gain_over_higher": 12, "pass": True},
              "F_few": {"hist": 26, "loop": 14, "ctrl_w1": 13, "gain_over_higher": 12, "pass": True},
              "plain_row": {"gain_over_plain": 29, "pass": True}} for s in (0, 1)}
    assert word(up) == "HISTORY HELPS"
    one = {0: up[0], 1: {**up[1], "F_few": {**up[1]["F_few"], "pass": False}}}
    assert word(one) == "NOT SHOWN"
    print("SELFTEST-marks ok")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "judge"))
    p.add_argument("--hist"); p.add_argument("--ctrl")
    a = p.parse_args()
    selftest() if a.cmd == "selftest" else main_judge(a.hist, a.ctrl)
