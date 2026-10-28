"""Data-shape round 1 verdicts (PREREG-datashape-r1.md) from race_mini result.json files.

  python backbone/sleep/brain/datashape/analyze.py --ctl OUT/c75_s1 OUT/c75_s2 --W DS/W_s1 DS/W_s2 --L DS/L_s1 DS/L_s2 [--json verdict.json]
"""
import argparse
import json
import sys
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
from make_tapes import WEEK, carded  # noqa: E402


def mcnemar(a, b):  # exact two-sided McNemar on paired booleans (a = control, b = arm)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n = n01 + n10
    if n == 0:
        return 1.0, n01, n10
    k = min(n01, n10)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n), n01, n10


def rows(res, tag, kind):
    return res["scores"][tag]["rows"][kind]


def c24(res, tag):
    return [r["ok"] for r in rows(res, tag, "forward") if r.get("cls") in ("C2", "C4")]


def load(ps):
    return [json.loads((Path(p) / "result.json").read_text()) for p in ps]


def pct(xs):
    return round(100 * sum(xs) / max(len(xs), 1), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctl", nargs=2, required=True)
    ap.add_argument("--W", nargs=2)
    ap.add_argument("--L", nargs=2)
    ap.add_argument("--json")
    a = ap.parse_args()
    ctl = load(a.ctl)
    pooled_final = pct(sum((c24(r, "final") for r in ctl), []))
    tag = "night4" if pooled_final >= 90 else "final"  # race-mini addendum 1's ceiling rule, decided from the control alone
    out = {"headline": tag, "ctl_pooled_final": pooled_final}
    base = sum((c24(r, tag) for r in ctl), [])
    cflags = [c for _, c in carded(json.loads(WEEK.read_text()))]

    def common(arm):
        x = sum((c24(r, tag) for r in arm), [])
        p, n01, n10 = mcnemar(base, x)
        d = {"recall": pct(x), "ctl": pct(base), "diff": round(pct(x) - pct(base), 1), "p": round(p, 5), "gain": n01, "loss": n10,
             "per_seed": [pct(c24(r, tag)) for r in arm], "ctl_per_seed": [pct(c24(r, tag)) for r in ctl],
             "arc": [r.get("arc") for r in arm], "arc_base": [r.get("arc_base") for r in arm], "kl": [r.get("kl_heldout") for r in arm],
             "reverse": [r["scores"]["final"]["reverse"]["C24"] for r in arm], "changed_new": [r["scores"]["final"]["changed"]["new"] for r in arm],
             "C1": [r["scores"]["final"]["forward"]["C1"] for r in arm]}
        d["harm"] = any(isinstance(r.get("arc"), float) and r["arc"] < r["arc_base"] - 0.05 for r in arm)
        return d

    if a.W:
        W = load(a.W)
        d = common(W)
        d["verdict"] = ("PASS" if d["diff"] >= 4 and d["p"] < 0.05 and d["loss"] < d["gain"] and not d["harm"] else
                        "WRONG" if d["diff"] <= -4 and d["p"] < 0.05 else "FAIL")
        out["W"] = d
    if a.L:
        L = load(a.L)
        d = common(L)
        th = lambda rs, want: sum(([r["ok"] for r, c in zip(rows(x, "final", "twohop"), cflags) if c == want] for x in rs), [])  # noqa: E731
        lc, lu, cc, cu = th(L, True), th(L, False), th(ctl, True), th(ctl, False)
        pu, g, l = mcnemar(cu, lu)
        d.update({"twohop_carded": pct(lc), "twohop_uncarded": pct(lu), "ctl_twohop_carded": pct(cc), "ctl_twohop_uncarded": pct(cu),
                  "uncarded_p": round(pu, 5), "uncarded_gain": g, "uncarded_loss": l})
        d["L1"] = "PASS" if pct(lc) >= 50 and pct(lc) >= pct(lu) + 30 else "FAIL"
        d["L2"] = "PASS" if pct(lu) >= pct(cu) + 10 and pu < 0.05 else "FAIL"
        d["no_harm"] = "PASS" if d["diff"] > -3 and not d["harm"] else "FAIL"
        out["L"] = d
    print(json.dumps(out, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
