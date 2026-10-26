"""Probe-1 analysis (PREREG.md): probe scores from replayed end states, pickers PROBE-S / PROBE-R / HAIKU-PROBE, Pick-1 baselines, AUROC, P1/P2 verdict, diagnostics.
Usage: analyze.py --probes probes_k2.jsonl [--haiku-probes probes_haiku.jsonl] [--k2 SELF k2_scores.jsonl] [--pools pools.jsonl] [--results DIR] [--out DIR]"""
import argparse, json, os, random, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_common import *  # noqa
import replay

P1A = load_pick1("analyze")
group, pick_best, auroc = P1A.group, P1A.pick_best, P1A.auroc
P1_MARGIN, P2_AUROC, WRONG_MARGIN = 5.0, 0.75, 1.0   # points / AUROC, fixed in PREREG
PRE = dict(RAND=19.7, VOTE=22.4, SELF=34.4, SELF_AUROC=0.692)   # Pick-1 numbers quoted in PREREG
EPS = 1e-9


def key(r):
    return f"{r['pool']}|{r['try_idx']}"


def valid(c):
    try:
        return bool(validate_check(c))
    except Exception:  # noqa  (e.g. an unhashable "type")
        return False


def passes(c, w, reply):
    try:
        return bool(run_check(c, w, reply))
    except Exception:  # noqa
        return False


def load_probes(path):
    """{task: [checks-or-None per sample]} from a probe jsonl; None = unparsable reply."""
    out = defaultdict(list)
    for r in read_jsonl(path):
        out[r["task"]].append(r["checks"])
    return dict(out)


def task_valid(samples):
    """samples: list of raw check lists (or None) -> list of lists of valid checks."""
    return [[c for c in (s or []) if valid(c)] for s in samples]


def probe_scores(recs, states, probes):
    """Score per try (PREREG step 3): mean over samples with >= 1 valid probe of passed/valid; no valid probe in the task -> 0.5.
    recs: pool records; states: {key: (world, reply)}; probes: {task: [samples]}. -> {key: score}"""
    vt, out = {t: [s for s in task_valid(v) if s] for t, v in probes.items()}, {}
    for r in recs:
        k, ss = key(r), vt.get(r["task"], [])
        w, reply = states[k]
        out[k] = 0.5 if not ss else sum(sum(passes(c, w, reply) for c in s) / len(s) for s in ss) / len(ss)
    return out


def diagnostics(probes, tasks, ref_states, scores, pools):
    n_samples = sum(len(v) for v in probes.values())
    raw = [len(s or []) for v in probes.values() for s in v]
    vt = {t: task_valid(v) for t, v in probes.items()}
    nvalid = [len(s) for v in vt.values() for s in v]
    ref_pass = ref_tot = 0
    task_ref = {}
    for t, ss in vt.items():
        w, reply = ref_states[t]
        p = [passes(c, w, reply) for s in ss for c in s]
        ref_pass, ref_tot = ref_pass + sum(p), ref_tot + len(p)
        if p:
            task_ref[t] = sum(p) / len(p)
    tied = [len({round(scores[key(r)], 9) for r in m}) == 1 for m in pools.values()]
    return dict(
        n_tasks=len(probes), n_samples=n_samples, unparsable_samples=sum(s is None for v in probes.values() for s in v),
        raw_checks=sum(raw), valid_checks=sum(nvalid), validity_rate=sum(nvalid) / max(1, sum(raw)),
        raw_checks_per_sample=sum(raw) / max(1, n_samples), valid_checks_per_sample=sum(nvalid) / max(1, n_samples),
        samples_over_6_checks=sum(n > 6 for n in raw), samples_with_no_valid=sum(n == 0 for n in nvalid),
        tasks_with_no_valid=len({m[0]["task"] for m in pools.values()} - {t for t in probes if any(vt[t])}),
        reference_agreement=ref_pass / max(1, ref_tot), reference_probes=ref_tot,
        tasks_all_probes_pass_reference=sum(v == 1 for v in task_ref.values()), tasks_with_probes=len(task_ref),
        all_tie_rate=sum(tied) / max(1, len(tied)), all_tie_pools=sum(tied), n_pools=len(tied))


def rates(pools, pickers, solv):
    out = {}
    for name, f in pickers.items():
        def win(m):
            return sum(x["success"] for x in m) / len(m) if f is None else float(f(m)["success"])
        out[name] = dict(all=100 * sum(win(m) for m in pools.values()) / len(pools),
                         solvable=100 * sum(win(m) for p, m in pools.items() if p in solv) / max(1, len(solv)))
    return out


def evaluate(recs, probe=None, haiku_probe=None, k2=None, seed=0):
    """probe / haiku_probe: {key: probe score}. k2: {key: SELF P(yes)} (missing = 0.5). Baselines RAND / VOTE / SELF are Pick-1's code."""
    pools = group(recs)
    solv = {p for p, m in pools.items() if any(x["success"] for x in m)}
    self_ = (lambda r: 0.5 if k2.get(key(r)) is None else k2[key(r)]) if k2 is not None else (lambda r: 0.5)
    pickers = {"RAND": None, "VOTE": P1A.pick_vote}
    if k2 is not None:
        pickers["SELF"] = lambda m: pick_best(m, self_)
    exp_r, flat = {}, [r for m in pools.values() for r in m]

    def mk(name, rname, sc):
        s = lambda r: round(sc[key(r)], 9)   # noqa
        pickers[name] = lambda m: pick_best(m, lambda r: (s(r), self_(r)))   # ties -> SELF -> lowest try
        rng = random.Random(seed)
        picks, exp_r[rname] = {}, {}
        for p in sorted(pools):                                     # ties -> random (one draw, seed 0)
            m, top = pools[p], max(s(r) for r in pools[p])
            c = [r for r in m if s(r) == top]
            picks[p] = rng.choice(c)
            exp_r[rname][p] = sum(r["success"] for r in c) / len(c)
        pickers[rname] = lambda m: picks[m[0]["pool"]]
    for nm, rn, sc in (("PROBE-S", "PROBE-R", probe), ("HAIKU-PROBE", "HAIKU-PROBE-R", haiku_probe)):
        if sc is not None:
            mk(nm, rn, sc)
    rate = rates(pools, pickers, solv)
    for rn, e in exp_r.items():
        rate[f"{rn} (expected over ties)"] = dict(all=100 * sum(e.values()) / len(pools), solvable=100 * sum(v for p, v in e.items() if p in solv) / max(1, len(solv)))
    au, y = {}, [r["success"] for r in flat]
    if k2 is not None:
        au["SELF"] = auroc([self_(r) for r in flat], y)
    for nm, sc in (("PROBE-S", probe), ("HAIKU-PROBE", haiku_probe)):
        if sc is not None:
            au[nm] = auroc([sc[key(r)] for r in flat], y)
    return dict(n_pools=len(pools), n_transcripts=len(flat), n_solvable=len(solv), pick_rate=rate, auroc=au)


def verdict(m):
    pr, au = m["pick_rate"], m["auroc"]
    if "PROBE-S" not in pr:
        return dict(verdict="NO PROBES", checks={})
    S = pr["SELF"]["all"] if "SELF" in pr else PRE["SELF"]
    p = pr["PROBE-S"]["all"]
    chk = dict(P1=p >= S + P1_MARGIN - EPS, P2=au.get("PROBE-S") is not None and au["PROBE-S"] >= P2_AUROC - EPS)
    v = "PASS" if all(chk.values()) else "PROVED WRONG" if p <= S + WRONG_MARGIN + EPS else "INCONCLUSIVE"
    return dict(verdict=v, checks=chk, self_rate=S, p1_needs=S + P1_MARGIN, wrong_at=S + WRONG_MARGIN)


def report_md(m, v, d, hd, gate_rate):
    L = ["# Probe-1 report", "", f"{m['n_pools']} pools, {m['n_transcripts']} tries, {m['n_solvable']} solvable pools. Replay gate: {100 * gate_rate:.2f}% of tries reproduce recorded success.", "",
         "| picker | pick rate, all pools (%) | solvable pools (%) | AUROC |", "|---|---|---|---|"]
    for n, r in m["pick_rate"].items():
        a = m["auroc"].get(n)
        L.append(f"| {n} | {r['all']:.1f} | {r['solvable']:.1f} | {'' if a is None else f'{a:.3f}'} |")
    L += ["", f"Verdict: **{v['verdict']}**"]
    if v["checks"]:
        L.append(f"Pass marks (PREREG): P1 PROBE-S >= SELF + 5 points (>= {v['p1_needs']:.1f}%); P2 AUROC of the probe score >= 0.75. "
                 f"Proved wrong: PROBE-S <= SELF + 1 point (<= {v['wrong_at']:.1f}%). HAIKU-PROBE is reported only. "
                 + ", ".join(f"{k}={'ok' if x else 'FAIL'}" for k, x in v["checks"].items()))
    L.append(f"Pick-1 numbers quoted in PREREG: RAND {PRE['RAND']}, VOTE {PRE['VOTE']}, SELF {PRE['SELF']} (SELF AUROC {PRE['SELF_AUROC']}); the table recomputes them from the same files.")
    for title, x in (("K2 probes", d), ("Haiku probes (reference)", hd)):
        if x:
            L += ["", f"## Diagnostics: {title}", "",
                  f"- samples {x['n_samples']} over {x['n_tasks']} tasks; unparsable replies {x['unparsable_samples']}; samples with no valid probe {x['samples_with_no_valid']}; tasks with no valid probe {x['tasks_with_no_valid']}",
                  f"- validity rate {100 * x['validity_rate']:.1f}% ({x['valid_checks']} of {x['raw_checks']} checks pass the sandbox validator); checks per sample {x['raw_checks_per_sample']:.2f} raw, {x['valid_checks_per_sample']:.2f} valid; samples with more than 6 checks {x['samples_over_6_checks']}",
                  f"- reference agreement {100 * x['reference_agreement']:.1f}% of {x['reference_probes']} valid probes pass the reference plan's end state; {x['tasks_all_probes_pass_reference']} of {x['tasks_with_probes']} tasks have every valid probe passing the reference",
                  f"- uninformative pools (all 12 tries tie on the probe score): {100 * x['all_tie_rate']:.1f}% ({x['all_tie_pools']} of {x['n_pools']})"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probes", default=os.path.join(HERE, "probes_k2.jsonl"))
    ap.add_argument("--haiku-probes", default=os.path.join(HERE, "probes_haiku.jsonl"))
    ap.add_argument("--k2", default=DEFAULT_K2, help="Pick-1 SELF scores (k2_scores.jsonl)")
    ap.add_argument("--pools", default=DEFAULT_POOLS)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    recs, tasks = read_jsonl(a.pools), load_tasks()
    rows = replay.load_rows(a.results, {r["task"] for r in recs})
    rate, bad, _ = replay.gate(rows, tasks)
    if rate < GATE:
        sys.exit(f"replay gate failed ({100 * rate:.2f}% < 99%); no result. Run replay.py --check")
    miss = [key(r) for r in recs if (r["task"], r["pool"].split("|")[1], r["try_idx"]) not in rows]
    if miss:
        sys.exit(f"{len(miss)} pool tries have no transcript in {a.results} (first: {miss[:3]})")
    byid = {t["id"]: t for t in tasks}
    states = {key(r): replay.replay_try(byid[r["task"]], rows[(r["task"], r["pool"].split("|")[1], r["try_idx"])]) for r in recs}
    ref = {t: replay.replay_reference(byid[t]) for t in {r["task"] for r in recs}}
    k2 = {r["key"]: r["p_yes"] for r in read_jsonl(a.k2)} if os.path.exists(a.k2) else None
    pools, out = group(recs), {}
    for nm, path in (("k2", a.probes), ("haiku", a.haiku_probes)):
        if os.path.exists(path) and read_jsonl(path):
            probes = load_probes(path)
            sc = probe_scores(recs, states, probes)
            out[nm] = (sc, diagnostics(probes, tasks, ref, sc, pools))
    m = evaluate(recs, out["k2"][0] if "k2" in out else None, out["haiku"][0] if "haiku" in out else None, k2)
    v = verdict(m)
    d, hd = (out[x][1] if x in out else None for x in ("k2", "haiku"))
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(metrics=m, diagnostics=dict(k2=d, haiku=hd), gate_rate=rate, baselines_in_prereg=PRE, **v), open(os.path.join(a.out, "report.json"), "w"), indent=1)
    with open(os.path.join(a.out, "probe_scores.jsonl"), "w") as f:
        for r in recs:
            f.write(json.dumps(dict(key=key(r), success=r["success"], **{n: out[x][0][key(r)] for n, x in (("probe_k2", "k2"), ("probe_haiku", "haiku")) if x in out})) + "\n")
    md = report_md(m, v, d, hd, rate)
    open(os.path.join(a.out, "report.md"), "w").write(md)
    print(md)


if __name__ == "__main__":
    main()
