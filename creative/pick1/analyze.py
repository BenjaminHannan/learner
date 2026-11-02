"""Pick-1 analysis: pickers, metrics, verdict (PREREG.md). Usage: analyze.py --pools pools.jsonl [--k2 k2_scores.jsonl] [--haiku haiku_scores.jsonl] [--out DIR]"""
import argparse, json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa

P1_MARGIN, P2_MARGIN, P3_AUROC, WRONG_MARGIN, VOTE_W = 15.0, 5.0, 0.70, 5.0, 0.5   # points / AUROC, fixed in PREREG


def group(recs):
    pools = defaultdict(list)
    for r in recs:
        pools[r["pool"]].append(r)
    return {p: sorted(v, key=lambda r: r["try_idx"]) for p, v in pools.items()}


def pick_best(members, score):
    """Highest score; ties -> lowest try_idx. members sorted by try_idx."""
    best = members[0]
    for m in members[1:]:
        if score(m) > score(best):
            best = m
    return best


def pick_vote(members):
    c = Counter(m["signature"] for m in members)
    top = max(c.values())
    return next(m for m in members if c[m["signature"]] == top)   # first (lowest try) member of a modal signature


def auroc(scores, labels):
    """P(score of a success > score of a failure), ties count 1/2. None if one class is empty."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks, i = [0.0] * len(scores), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    rp = sum(r for r, l in zip(ranks, labels) if l)
    return (rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def load_scores(path, field):
    if not path or not os.path.exists(path):
        return None
    return {r["key"]: r[field] for r in read_jsonl(path)}


def evaluate(recs, k2=None, haiku=None, extra=None):
    """extra: {NAME: (scores_by_key, default_for_missing)} adds a best-of-pool picker and an AUROC per extra judge."""
    pools = group(recs)
    solv = {p for p, m in pools.items() if any(x["success"] for x in m)}
    k = lambda r: f"{r['pool']}|{r['try_idx']}"
    s_self = (lambda r: 0.5 if k2.get(k(r)) is None else k2[k(r)]) if k2 is not None else None
    s_hk = (lambda r: 5.0 if haiku.get(k(r)) is None else haiku[k(r)]) if haiku is not None else None
    pickers = {"RAND": None, "VOTE": lambda m: pick_vote(m)}
    if s_self:
        pickers["SELF"] = lambda m: pick_best(m, s_self)
        pickers["SELF-VOTE"] = lambda m: pick_best(m, lambda r: s_self(r) + VOTE_W * sum(x["signature"] == r["signature"] for x in m) / len(m))
    if s_hk:
        pickers["HAIKU"] = lambda m: pick_best(m, s_hk)
    extra_s = {}
    for nm, (sc, dflt) in (extra or {}).items():
        extra_s[nm] = (lambda sc, dflt: lambda r: dflt if sc.get(k(r)) is None else sc[k(r)])(sc, dflt)
        pickers[nm] = (lambda s_: lambda m: pick_best(m, s_))(extra_s[nm])
    rate = {}
    for name, f in pickers.items():
        def win(m):
            return sum(x["success"] for x in m) / len(m) if f is None else float(f(m)["success"])
        rate[name] = dict(all=100 * sum(win(m) for m in pools.values()) / len(pools),
                          solvable=100 * sum(win(m) for p, m in pools.items() if p in solv) / max(1, len(solv)))
    flat = [r for m in pools.values() for r in m]
    au = {}
    if s_self:
        au["SELF"] = auroc([s_self(r) for r in flat], [r["success"] for r in flat])
    if s_hk:
        au["HAIKU"] = auroc([s_hk(r) for r in flat], [r["success"] for r in flat])
    for nm, s_ in extra_s.items():
        au[nm] = auroc([s_(r) for r in flat], [r["success"] for r in flat])
    return dict(n_pools=len(pools), n_transcripts=len(flat), n_solvable=len(solv), pick_rate=rate, auroc=au,
                k2_null=sum(1 for r in flat if k2 is not None and k2.get(k(r)) is None))


def verdict(m):
    pr, au = m["pick_rate"], m["auroc"]
    if "SELF" not in pr:
        return dict(verdict="NO JUDGE SCORES", checks={})
    R, V, S = pr["RAND"]["all"], pr["VOTE"]["all"], pr["SELF"]["all"]
    sv = max(S, pr["SELF-VOTE"]["all"])
    eps = 1e-9
    chk = dict(P1=S >= R + P1_MARGIN - eps, P2=sv >= V + P2_MARGIN - eps, P3=au.get("SELF") is not None and au["SELF"] >= P3_AUROC - eps)
    v = "PASS" if all(chk.values()) else "PROVED WRONG" if S <= R + WRONG_MARGIN + eps else "INCONCLUSIVE"
    return dict(verdict=v, checks=chk)


P2_RAND, P2_AUROC, P2_OVER_SELF, P2_WRONG = 15.0, 0.70, 3.0, 1.0   # Pick-2 marks, fixed in PREREG-pick2.md


def verdict_pick2(m, variants=("FULL", "THINK")):
    """PREREG-pick2: per variant Q1 rate >= RAND+15, Q2 AUROC >= .70, Q3 rate >= SELF+3. PASS if any variant meets all three;
    PROVED WRONG if every variant <= SELF+1; else INCONCLUSIVE. 'best' = the higher-rate variant (the Q1 max)."""
    pr, au, eps = m["pick_rate"], m["auroc"], 1e-9
    vs = [x for x in variants if x in pr]
    if "SELF" not in pr or not vs:
        return dict(verdict="NO JUDGE SCORES", variants={}, best=None, passing=[])
    R, S = pr["RAND"]["all"], pr["SELF"]["all"]
    out = {}
    for x in vs:
        r, a = pr[x]["all"], au.get(x)
        out[x] = dict(rate=r, auroc=a, Q1=r >= R + P2_RAND - eps, Q2=a is not None and a >= P2_AUROC - eps, Q3=r >= S + P2_OVER_SELF - eps)
    passing = [x for x in vs if out[x]["Q1"] and out[x]["Q2"] and out[x]["Q3"]]
    wrong = all(pr[x]["all"] <= S + P2_WRONG + eps for x in vs)
    v = "PASS" if passing else "PROVED WRONG" if wrong else "INCONCLUSIVE"
    return dict(verdict=v, variants=out, best=max(vs, key=lambda x: pr[x]["all"]), passing=passing)


def report_pick2_md(v):
    L = ["# Pick-2 verdict", ""]
    if not v["variants"]:
        return "\n".join(L + [f"Verdict: **{v['verdict']}**"]) + "\n"
    L += ["| variant | pick rate (%) | AUROC | Q1 >= RAND+15 | Q2 AUROC >= 0.70 | Q3 >= SELF+3 |", "|---|---|---|---|---|---|"]
    for x, c in v["variants"].items():
        au = "" if c["auroc"] is None else format(c["auroc"], ".3f")
        L.append(f"| {x} | {c['rate']:.1f} | {au} | " + " | ".join("ok" if c[q] else "FAIL" for q in ("Q1", "Q2", "Q3")) + " |")
    L += ["", f"Verdict: **{v['verdict']}**" + (f" (passing: {', '.join(v['passing'])})" if v["passing"] else ""),
          f"Higher-rate variant (Q1 max): {v['best']}. PROVED WRONG = both variants <= SELF+1 point (PREREG-pick2)."]
    return "\n".join(L) + "\n"


def report_md(m, v):
    L = ["# Pick-1 report", "", f"{m['n_pools']} pools, {m['n_transcripts']} transcripts, {m['n_solvable']} solvable pools.", "",
         "| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |", "|---|---|---|---|"]
    for n, r in m["pick_rate"].items():
        a = m["auroc"].get(n)
        L.append(f"| {n} | {r['all']:.1f} | {r['solvable']:.1f} | {'' if a is None else f'{a:.3f}'} |")
    L += ["", f"Verdict: **{v['verdict']}**"]
    if v["checks"]:
        L.append("Pass marks (PREREG): P1 SELF >= RAND+15 pts; P2 max(SELF,SELF-VOTE) >= VOTE+5 pts; P3 SELF AUROC >= 0.70. "
                 "Proved wrong: SELF <= RAND+5. HAIKU is reported only. " + ", ".join(f"{k}={'ok' if x else 'FAIL'}" for k, x in v["checks"].items()))
    if m["k2_null"]:
        L.append(f"{m['k2_null']} transcripts had no yes/no token and were scored 0.5.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", default=os.path.join(HERE, "pools.jsonl"))
    ap.add_argument("--k2", default=os.path.join(HERE, "k2_scores.jsonl"))
    ap.add_argument("--haiku", default=os.path.join(HERE, "haiku_scores.jsonl"))
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--judge", action="append", default=[], metavar="NAME=PATH:FIELD", help="extra judge (repeatable); missing score = 0.5 for p_yes, else 0")
    ap.add_argument("--pick2", action="store_true", help="print the Pick-2 verdict for judges named FULL and THINK (PREREG-pick2.md)")
    a = ap.parse_args()
    extra = {}
    for spec in a.judge:
        name, rest = spec.split("=", 1)
        path, field = rest.rsplit(":", 1)
        sc = load_scores(path, field)
        if sc is None:
            print(f"warning: no scores at {path}; judge {name} skipped")
            continue
        extra[name] = (sc, 0.5 if field == "p_yes" else 0.0)
    m = evaluate(read_jsonl(a.pools), load_scores(a.k2, "p_yes"), load_scores(a.haiku, "score"), extra)
    v = verdict(m)
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(metrics=m, **v), open(os.path.join(a.out, "report.json"), "w"), indent=1)
    md = report_md(m, v)
    open(os.path.join(a.out, "report.md"), "w").write(md)
    print(md)
    if a.pick2:
        v2 = verdict_pick2(m)
        json.dump(v2, open(os.path.join(a.out, "report_pick2.json"), "w"), indent=1)
        md2 = report_pick2_md(v2)
        open(os.path.join(a.out, "report_pick2.md"), "w").write(md2)
        print(md2)


if __name__ == "__main__":
    main()
