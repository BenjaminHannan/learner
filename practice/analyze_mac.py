"""Practice-1M verdicts (PREREG addenda 4-7): reads the two side-by-side run dirs and prints one JSON report.
  python -m practice.analyze_mac ~/learner-ops/practice1m/runP ~/learner-ops/practice1m/runC [--night 2]
T1: P{n} >= mean(A0_P, A0_C) + 8 points, p < 0.05.  T2: P{n} >= C{n} + 5 points, p < 0.05.  Noise: A0_P vs A0_C.
Also per kind, tool use (harm check: P tool calls/try >= half of A0's) and how many tries were lessons each night."""
import json
import sys
from pathlib import Path

from .mac_run import puzzle_scores, signflip_p


def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.open() if l.strip()] if p.exists() else []


def mean(d):
    return round(100 * sum(d.values()) / max(1, len(d)), 1)


def by_kind(recs):
    k = {}
    for r in recs:
        k.setdefault(r.get("kind", "?"), []).append(r["correct"])
    return {a: f"{sum(v)}/{len(v)}" for a, v in sorted(k.items())}


def tools(recs):
    n = max(1, len(recs))
    return {"tool_calls_per_try": round(sum(r.get("tool_calls", 0) for r in recs) / n, 2), "answered": round(sum(bool(r.get("answered")) for r in recs) / n, 3),
            "python_share": round(sum("python" in (r.get("tools") or []) for r in recs) / n, 3), "gen_tokens_per_try": round(sum(r.get("gen_tokens", 0) for r in recs) / n)}


def cmp(a, b):
    common = {k: a[k] for k in a if k in b}
    return {"diff_points": round(100 * sum(common[k] - b[k] for k in common) / max(1, len(common)), 1), "p_signflip": round(signflip_p(common, b), 4), "n_puzzles": len(common)}


def main(argv):
    dp, dc = Path(argv[0]).expanduser(), Path(argv[1]).expanduser()
    n = int(argv[argv.index("--night") + 1]) if "--night" in argv else 2
    e = {"A0_P": jl(dp / "A0" / "eval_A0_test.jsonl"), "A0_C": jl(dc / "A0" / "eval_A0_test.jsonl"),
         f"P{n}": jl(dp / "P" / f"eval_P{n}_test.jsonl"), f"C{n}": jl(dc / "C" / f"eval_C{n}_test.jsonl")}
    s = {k: puzzle_scores(v) for k, v in e.items() if v}
    rep = {"tries": {k: len(v) for k, v in e.items()}, "score_pct": {k: mean(v) for k, v in s.items()},
           "by_kind": {k: by_kind(v) for k, v in e.items() if v}, "tools": {k: tools(v) for k, v in e.items() if v}}
    if "A0_P" in s and "A0_C" in s:
        a0 = {k: (s["A0_P"][k] + s["A0_C"][k]) / 2 for k in s["A0_P"] if k in s["A0_C"]}
        s["A0"] = a0
        rep["score_pct"]["A0_mean"] = mean(a0)
        rep["noise_A0P_vs_A0C"] = cmp(s["A0_P"], s["A0_C"])
    P, C = f"P{n}", f"C{n}"
    v = {}
    if P in s and "A0" in s:
        c = cmp(s[P], s["A0"])
        v["T1_practice_sleep_works"] = dict(c, mark="P >= A0 + 8, p < 0.05", passed=c["diff_points"] >= 8 and c["p_signflip"] < 0.05)
    if P in s and C in s:
        c = cmp(s[P], s[C])
        v["T2_checker_matters"] = dict(c, mark="P >= C + 5, p < 0.05", passed=c["diff_points"] >= 5 and c["p_signflip"] < 0.05,
                                       suggested=c["diff_points"] >= 5 and c["p_signflip"] >= 0.05)
    if C in s and "A0" in s:
        v["C_vs_A0"] = cmp(s[C], s["A0"])
    if P in e and e[P] and e["A0_P"]:
        t0, t1 = tools(e["A0_P"])["tool_calls_per_try"], tools(e[P])["tool_calls_per_try"]
        v["T4_no_tool_collapse"] = {"A0": t0, P: t1, "passed": t1 >= 0.5 * t0}
    if P in s and "A0" in s:
        v["wrong_if_P_le_A0_plus_2"] = cmp(s[P], s["A0"])["diff_points"] <= 2
    if P in s and C in s:
        v["wrong_if_P_below_C"] = cmp(s[P], s[C])["diff_points"] < 0
    rep["verdicts"] = v
    nights = {}
    for arm, d in (("P", dp), ("C", dc)):
        for f in sorted((d / arm).glob("night*.json")):
            try:
                nights[f"{arm}/{f.stem}"] = {k: x for k, x in json.loads(f.read_text()).items() if not isinstance(x, (list, dict))}
            except ValueError:
                pass
    rep["nights"] = nights
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
