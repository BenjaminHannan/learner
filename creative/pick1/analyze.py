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


def evaluate(recs, k2=None, haiku=None):
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
    a = ap.parse_args()
    m = evaluate(read_jsonl(a.pools), load_scores(a.k2, "p_yes"), load_scores(a.haiku, "score"))
    v = verdict(m)
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(metrics=m, **v), open(os.path.join(a.out, "report.json"), "w"), indent=1)
    md = report_md(m, v)
    open(os.path.join(a.out, "report.md"), "w").write(md)
    print(md)


if __name__ == "__main__":
    main()
