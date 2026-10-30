"""Practice-2 verdicts (PREREG-2). Reads a run dir written by `practice.job --rg-skills` (CUDA) or `practice.mac_run --rg-skills` (Mac) and prints one JSON report.
  python -m practice.analyze_rg <out> [--night 3]
S1 (per skill): P{n} >= A0 + 10 points, paired sign-flip p < 0.05, Holm over the skills.  S2: P{n} >= C{n} + 5 points, p < 0.05.
S3: test100 P{n} >= test100 A0 - 5 points and tool calls per try >= half of A0's.  Wrong if: P <= A0 + 3 on all skills, or P < C on all skills.
Also: per-day practice solve rate, unique wins per night, per-skill P curve (A0, P1, P3)."""
import json
import sys
from pathlib import Path

from .analyze_mac import cmp, jl, mean, tools
from .mac_run import puzzle_scores


def first(*paths):
    for p in paths:
        if Path(p).exists():
            return jl(p)
    return []


def ev(sd, arm, tag, kind):
    """Eval tries of `tag` (kind test|sibling) in either layout (job: <arm>/eval/<tag>_<kind>.jsonl; Mac: <arm>/eval_<tag>_<kind>.jsonl, sibling = _sib)."""
    k2 = "sib" if kind == "sibling" else kind
    arms = ["P", "A0"] if tag == "A0" else [arm]
    return first(*[x for a in arms for x in (sd / a / "eval" / f"{tag}_{kind}.jsonl", sd / a / f"eval_{tag}_{k2}.jsonl")])


def days(sd, arm, n):
    return first(sd / arm / "day" / f"day{n}.jsonl", sd / arm / f"day{n}.jsonl")


def night_stats(sd, arm, n):
    for f in (sd / arm / "results" / f"night{n}.json", sd / arm / f"night{n}_lessons.json"):
        if f.exists():
            d = json.loads(f.read_text())
            d = d.get("lessons", d)
            return {k: d.get(k) for k in ("tries_in_store", "wins_in_store", "sft_unique", "pairs", "pair_candidates", "steps", "n_items") if k in d}
    return {}


def holm(ps, alpha=0.05):
    """-> {skill: reject?} with Holm's step-down over the skills."""
    out, stop = {}, False
    for i, (k, p) in enumerate(sorted(ps.items(), key=lambda kv: kv[1])):
        stop = stop or p >= alpha / (len(ps) - i)
        out[k] = not stop
    return out


def analyze(root, n=3):
    root = Path(root).expanduser()
    skills = json.loads((root / "stage0.json").read_text())["picked"] if (root / "stage0.json").exists() else []
    skills = [s for s in skills if (root / s).is_dir()] or sorted(d.name for d in root.iterdir() if d.is_dir() and (d / "rgdata").is_dir() and d.name != "stage0")
    rep = {"night": n, "skills": {}}
    if (root / "stage0.json").exists():
        rep["stage0"] = json.loads((root / "stage0.json").read_text())
    a0_t100 = []
    for s in skills:
        if not a0_t100:
            a0_t100 = ev(root / s, "P", "A0", "sibling")
    P, C = f"P{n}", f"C{n}"
    s1p = {}
    for s in skills:
        sd = root / s
        e = {"A0": ev(sd, "P", "A0", "test"), P: ev(sd, "P", P, "test"), C: ev(sd, "C", C, "test"), "P1": ev(sd, "P", "P1", "test")}
        sc = {k: puzzle_scores(v) for k, v in e.items() if v}
        r = {"tries": {k: len(v) for k, v in e.items()}, "score_pct": {k: mean(v) for k, v in sc.items()}, "tools": {k: tools(v) for k, v in e.items() if v}, "v": {}}
        if P in sc and "A0" in sc:
            c = cmp(sc[P], sc["A0"])
            r["v"]["S1"] = dict(c, mark="P >= A0 + 10, p < 0.05 (Holm over skills)", meets_size=c["diff_points"] >= 10)
            r["v"]["wrong_if_P_le_A0_plus_3"] = c["diff_points"] <= 3
            s1p[s] = c["p_signflip"]
        if P in sc and C in sc:
            c = cmp(sc[P], sc[C])
            r["v"]["S2"] = dict(c, mark="P >= C + 5, p < 0.05", passed=c["diff_points"] >= 5 and c["p_signflip"] < 0.05)
            r["v"]["wrong_if_P_below_C"] = c["diff_points"] < 0
        if C in sc and "A0" in sc:
            r["v"]["C_vs_A0"] = cmp(sc[C], sc["A0"])
        t100 = ev(sd, "P", P, "sibling")
        if t100 and a0_t100:
            sa, sp = puzzle_scores(a0_t100), puzzle_scores(t100)
            t0, t1 = tools(a0_t100)["tool_calls_per_try"], tools(t100)["tool_calls_per_try"]
            c = cmp(sp, sa)
            r["v"]["S3"] = dict(c, A0_tools_per_try=t0, P_tools_per_try=t1, mark="test100 P >= A0 - 5 and tools >= half of A0", passed=c["diff_points"] >= -5 and t1 >= 0.5 * t0)
        r["practice_solve_rate_by_day"] = {f"{arm}{d}": round(100 * sum(x["correct"] for x in days(sd, arm, d)) / max(1, len(days(sd, arm, d))), 1)
                                           for arm in ("P", "C") for d in range(1, n + 1) if days(sd, arm, d)}
        r["nights"] = {f"{arm}{d}": night_stats(sd, arm, d) for arm in ("P", "C") for d in range(1, n + 1) if night_stats(sd, arm, d)}
        rep["skills"][s] = r
    rej = holm(s1p) if s1p else {}
    for s, r in rep["skills"].items():
        if "S1" in r["v"]:
            r["v"]["S1"]["p_holm_reject"] = rej[s]
            r["v"]["S1"]["passed"] = r["v"]["S1"]["meets_size"] and rej[s]
    allv = [r["v"] for r in rep["skills"].values()]
    rep["wrong_if"] = {"P_le_A0_plus_3_on_all_skills": bool(allv) and all(v.get("wrong_if_P_le_A0_plus_3") for v in allv if "wrong_if_P_le_A0_plus_3" in v) and any("wrong_if_P_le_A0_plus_3" in v for v in allv),
                       "P_below_C_on_all_skills": bool(allv) and all(v.get("wrong_if_P_below_C") for v in allv if "wrong_if_P_below_C" in v) and any("wrong_if_P_below_C" in v for v in allv)}
    return rep


def main(argv):
    n = int(argv[argv.index("--night") + 1]) if "--night" in argv else 3
    print(json.dumps(analyze(argv[0], n), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
