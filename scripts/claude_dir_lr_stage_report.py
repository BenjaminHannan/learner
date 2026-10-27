#!/usr/bin/env python3
"""Apply STAGE-PASSMARKS.md to the staged-unfreeze dev (or holdout) records. Reads raw JSON only.

  python3 -B scripts/claude_dir_lr_stage_report.py dev
  python3 -B scripts/claude_dir_lr_stage_report.py holdout
  python3 -B scripts/claude_dir_lr_stage_report.py selftest
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs"
STAGE = ROOT / "artifacts" / "claude-dir-lr-20260928" / "stage-runs"
KS = ("1", "4", "16", "64", "256", "1024", "4096", "16384")
BAR_EQ, BAR_FEW = 8.0, 10.5   # points; STAGE-PASSMARKS.md
STARTS = [(a, i) for a in ("loop", "plain") for i in ("pre", "fresh")]


def curve(root, arm, seed, init, part):
    d = json.loads((root / f"{arm}-s{seed}-{init}" / ("adapt.json" if part == "dev" else "holdout.json")).read_text())
    r = d["rungs"] if part == "dev" else d["scores"]
    return [100 * r[k]["9"]["right"] / r[k]["9"]["n"] for k in KS]


def feq(c): return sum(c) / 8
def ffew(c): return sum(c[:4]) / 4


def words(d_eq, d_few):
    """Per row, both seeds: HELPS if both >= +bar, HURTS if both <= -bar, else NOT SHOWN."""
    def w(ds, bar):
        return "HELPS" if all(x >= bar for x in ds) else "HURTS" if all(x <= -bar for x in ds) else "NOT SHOWN"
    return w(d_eq, BAR_EQ), w(d_few, BAR_FEW)


def report(part, base=BASE, stage=STAGE):
    res, lines = {}, []
    for arm, init in STARTS:
        eq_b, eq_s, fw_b, fw_s = [], [], [], []
        for seed in (0, 1):
            b, s = curve(base, arm, seed, init, part), curve(stage, arm, seed, init, part)
            eq_b.append(feq(b)); eq_s.append(feq(s)); fw_b.append(ffew(b)); fw_s.append(ffew(s))
        d_eq = [s - b for s, b in zip(eq_s, eq_b)]
        d_few = [s - b for s, b in zip(fw_s, fw_b)]
        res[(arm, init)] = dict(eq_base=eq_b, eq_stage=eq_s, few_base=fw_b, few_stage=fw_s, d_eq=d_eq, d_few=d_few,
                                words=words(d_eq, d_few))
        lines.append(f"{arm}-{init}: F_eq base {eq_b[0]:.2f}/{eq_b[1]:.2f} staged {eq_s[0]:.2f}/{eq_s[1]:.2f} "
                     f"delta {d_eq[0]:+.2f}/{d_eq[1]:+.2f} ({res[(arm, init)]['words'][0]}) | F_few base {fw_b[0]:.2f}/{fw_b[1]:.2f} "
                     f"staged {fw_s[0]:.2f}/{fw_s[1]:.2f} delta {d_few[0]:+.2f}/{d_few[1]:+.2f} ({res[(arm, init)]['words'][1]})")
    pl, fl, pp = res[("loop", "pre")], res[("loop", "fresh")], res[("plain", "pre")]
    gap_plain = [a - b for a, b in zip(pl["eq_stage"], pp["eq_stage"])]
    gap_fresh = [a - b for a, b in zip(pl["eq_stage"], fl["eq_stage"])]
    row_plain = all(g >= BAR_EQ for g in gap_plain)
    row_fresh = all(g >= BAR_EQ for g in gap_fresh)
    lines.append(f"plain-net row: staged practised loop minus staged practised plain F_eq {gap_plain[0]:+.2f}/{gap_plain[1]:+.2f} "
                 f"(need >= +{BAR_EQ} both): {'PASS' if row_plain else 'FAIL'}")
    lines.append(f"carry-over row: staged practised loop minus staged fresh loop F_eq {gap_fresh[0]:+.2f}/{gap_fresh[1]:+.2f}: {'PASS' if row_fresh else 'FAIL'}")
    w_eq, w_few = pl["words"]
    promoted = w_eq == "HELPS" and w_few == "HELPS" and row_plain and row_fresh
    verdict = "PROMOTE (both rows both seeds, controls pass)" if promoted else \
        "REJECTED (practised loop HURTS on F_eq in both seeds)" if w_eq == "HURTS" else "NOT SHOWN"
    lines.append(f"VERDICT ({part}): {verdict}")
    return lines, verdict


def selftest():
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp())
    try:
        for arm, init in STARTS:
            for seed in (0, 1):
                d = tmp / f"{arm}-s{seed}-{init}"; d.mkdir(parents=True)
                lift = 10 if (arm, init) == ("loop", "pre") else 0
                rungs = {k: {"9": {"right": min(300, 90 + lift * 3), "n": 300}} for k in KS}
                (d / "adapt.json").write_text(json.dumps({"rungs": rungs}))
        # base = same numbers without lift -> delta = +lift for practised loop only
        base = Path(tempfile.mkdtemp())
        for arm, init in STARTS:
            for seed in (0, 1):
                d = base / f"{arm}-s{seed}-{init}"; d.mkdir(parents=True)
                (d / "adapt.json").write_text(json.dumps({"rungs": {k: {"9": {"right": 90, "n": 300}} for k in KS}}))
        lines, v = report("dev", base, tmp)
        assert v == "NOT SHOWN", lines            # delta +10 F_eq passes bar, but plain/fresh rows tie -> no promote
        assert "loop-pre" in lines[0] and "HELPS" in lines[0]
        assert words([9, 7.9], [11, 11]) == ("NOT SHOWN", "HELPS") and words([-8, -9], [-11, -12]) == ("HURTS", "HURTS")
        shutil.rmtree(base)
    finally:
        shutil.rmtree(tmp)
    print("stage report selftest ok")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        selftest()
    else:
        for l in report(sys.argv[1])[0]:
            print(l)
