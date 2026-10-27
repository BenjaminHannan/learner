"""Verdict for PREREG-habit1-mini.md from the two arms' result.json (habit_mini.py). Points are percentage points; marks are the prereg's:
M1 m3 fact gain >= 25 AND m3 ARC after >= before - 5; M2 (needs m4) m3 fact gain >= m4 fact gain - 10; MH m3 routine after >= 60 AND gain >= 25;
wrong if m3 fact gain < 10 while m4's >= 25.
  python habit_mini_score.py runs/m3/result.json runs/m4/result.json     (the m4 file may be missing: M2 and the wrong-if are then untested)"""
import json
import sys
from pathlib import Path

EPS = 1e-6  # 1 question = 2.5 / 5 / 1.67 points; ARC "-5" is 3 questions = 5.0 points, so compare with a float margin


def load(p):
    return json.loads(Path(p).read_text()) if p and Path(p).exists() else None


def gain(r, k):
    return r[f"{k}_after"] - r[f"{k}_before"]


def verdict(m3, m4):
    g3, g4 = gain(m3, "fact"), (gain(m4, "fact") if m4 else None)
    out = {"M1": g3 >= 25 - EPS and m3["arc_after"] >= m3["arc_before"] - 5 - EPS,
           "M2": None if m4 is None else g3 >= g4 - 10 - EPS,
           "MH": m3["routine_after"] >= 60 - EPS and gain(m3, "routine") >= 25 - EPS,
           "wrong_if": None if m4 is None else g3 < 10 - EPS and g4 >= 25 - EPS}
    return g3, g4, out


def main():
    m3, m4 = load(sys.argv[1]), load(sys.argv[2] if len(sys.argv) > 2 else None)
    if m3 is None:
        sys.exit("m3 result.json missing")
    for name, r in (("m3", m3), ("m4", m4)):
        if r is None:
            print(f"{name}: no result")
            continue
        print(f"{name}: fact {r['fact_before']:.1f} -> {r['fact_after']:.1f} ({gain(r, 'fact'):+.1f})  routine {r['routine_before']:.1f} -> {r['routine_after']:.1f} "
              f"({gain(r, 'routine'):+.1f})  ARC {r['arc_before']:.1f} -> {r['arc_after']:.1f} ({gain(r, 'arc'):+.1f})  spotter yes {r['spotter_yes']}/{r['spotter_asked']}  "
              f"iters {r['iters_done']}  samples {r['samples']['train']}  s/iter {r['s_per_iter']}  peak GB {r['peak_mem_gb']}/{r['peak_mem_gb_lora']}  wall {r['wall_seconds']:.0f} s")
    g3, g4, v = verdict(m3, m4)
    show = lambda x: "untested (no m4)" if x is None else ("PASS" if x else "FAIL")  # noqa: E731
    print(f"M1 (3-bit can sleep): fact gain {g3:+.1f} >= +25 and ARC {m3['arc_after'] - m3['arc_before']:+.1f} >= -5: {show(v['M1'])}")
    print(f"M2 (3-bit ~ 4-bit): m3 gain {g3:+.1f} >= m4 gain {'n/a' if g4 is None else format(g4, '+.1f')} - 10: {show(v['M2'])}")
    print(f"MH (spotter through sleep, 3-bit): routine after {m3['routine_after']:.1f} >= 60 and gain {gain(m3, 'routine'):+.1f} >= +25: {show(v['MH'])}")
    print(f"WRONG IF (m3 gain < 10 while m4 gain >= 25): {'untested (no m4)' if v['wrong_if'] is None else ('YES: 3 bits blocks learning; sleep the assistant on a 4-bit copy' if v['wrong_if'] else 'no')}")


if __name__ == "__main__":
    main()
