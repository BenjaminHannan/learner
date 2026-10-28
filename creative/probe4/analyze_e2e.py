"""Probe-4 analysis (PREREG.md): end-to-end success of the pickers on each task's 12 tries -- FIRST (try 1), RAND (expected), VOTE, SELF, TEST-B, TEST-T -- plus the oracle (any try passes);
traps vs non-traps; generated tokens per picker; E1-E3 verdict. Test scoring and tie-breaks are Probe-1's code (score = mean passed/valid over the writer's samples, 0.5 if no valid check; ties -> SELF -> lowest try).
Usage: analyze_e2e.py --tries DIR/tries/results.jsonl --self DIR/self_scores.jsonl --test-b DIR/tests_b/probes_k2base_mlx.jsonl --test-t DIR/tests_t/probes_k2.jsonl --out DIR [--tasks tasks_new.jsonl]"""
import argparse, json, os, random, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4common as P
import replay
import analyze as an

E1_PTS, E2_PTS, E3_PTS, WRONG_PTS, EPS = 10.0, 5.0, 5.0, 3.0, 1e-9      # fixed in PREREG
PICKERS = ("FIRST", "RAND", "VOTE", "SELF", "TEST-B", "TEST-T", "ORACLE")


def load_inputs(tasks_path, tries_path, require=P.N_TRIES):
    tasks = P.load_tasks(tasks_path)
    rows = {}
    for r in P.read_jsonl(tries_path):
        if r["arm"] == P.ARM and r["try_idx"] < P.N_TRIES:
            rows.setdefault((r["task_id"], r["try_idx"]), r)
    full = [t for t in tasks if all((t["id"], i) in rows for i in range(require))]
    return tasks, full, rows


def gate(tasks, rows):
    """Replay every try's tool calls in a fresh World; real checks must reproduce the recorded success (Probe-1's gate)."""
    byid = {t["id"]: t for t in tasks}
    states, bad = {}, 0
    for (tid, i), r in rows.items():
        w, rep = replay.replay_try(byid[tid], r)
        states[f"{tid}|{P.ARM}|{i}"] = (w, rep)
        bad += replay.success_of(byid[tid], w, rep) != bool(r["success"])
    return 1 - bad / max(1, len(rows)), states


def self_scores(path):
    return {r["key"]: r["p_yes"] for r in P.read_jsonl(path)} if path and os.path.exists(path) else {}


def genlog(path):
    """{task: (prompt tokens, new tokens)} summed over the test samples of a probe file (its .genlog.jsonl side file)."""
    p = os.path.splitext(path)[0] + ".genlog.jsonl"
    out = defaultdict(lambda: [0, 0])
    for r in P.read_jsonl(p) if os.path.exists(p) else []:
        t = r["key"].split("|")[0]
        out[t][0] += r["prompt_tokens"]
        out[t][1] += r["new_tokens"]
    return out


def pick_all(tasks, rows, states, self_, probes):
    """-> {task: {picker: (success 0/1 or expected, picked try_idx or None)}}, test-score info. probes: {"TEST-B": {task: samples}, "TEST-T": ...}."""
    recs = P.build_pools([rows[(t["id"], i)] for t in tasks for i in range(P.N_TRIES)])
    pools = an.group(recs)
    sf = lambda r: 0.5 if self_.get(an.key(r)) is None else self_[an.key(r)]   # noqa
    sc = {n: an.probe_scores(recs, states, p) for n, p in probes.items()}
    res = {}
    for t in tasks:
        m = pools[f"{t['id']}|{P.ARM}"]
        d = {"FIRST": (float(m[0]["success"]), 0), "RAND": (sum(x["success"] for x in m) / len(m), None), "ORACLE": (float(any(x["success"] for x in m)), None)}
        v = an.P1A.pick_vote(m)
        d["VOTE"] = (float(v["success"]), v["try_idx"])
        if self_:
            s = an.pick_best(m, sf)
            d["SELF"] = (float(s["success"]), s["try_idx"])
        for n in sc:
            b = an.pick_best(m, lambda r: (round(sc[n][an.key(r)], 9), sf(r)))
            d[n] = (float(b["success"]), b["try_idx"])
        res[t["id"]] = d
    return res, sc, recs


def table(tasks, res):
    """{picker: {all, traps, plain}} success rates in %."""
    groups = {"all": tasks, "traps": [t for t in tasks if t.get("trap")], "plain": [t for t in tasks if not t.get("trap")]}
    names = [p for p in PICKERS if all(p in res[t["id"]] for t in tasks)]
    return {p: {g: (100 * sum(res[t["id"]][p][0] for t in ts) / len(ts) if ts else None) for g, ts in groups.items()} for p in names}


def tokens_per_task(tasks, rows, self_rows, gl):
    """Mean generated (completion) and prompt tokens per task for each picker's whole procedure."""
    def tri(t, idx):
        return [rows[(t["id"], i)]["tokens"] for i in idx]
    out = {}
    for p in PICKERS:
        c = pt = 0
        for t in tasks:
            tk = tri(t, [0] if p == "FIRST" else range(P.N_TRIES))
            c += sum(x["completion"] for x in tk)
            pt += sum(x["prompt"] for x in tk)
            if p == "SELF":
                c += P.N_TRIES    # one answer token per judgment
                pt += sum(self_rows.get(f"{t['id']}|{P.ARM}|{i}", 0) for i in range(P.N_TRIES))
            if p in ("TEST-B", "TEST-T") and p in gl:
                pt += gl[p][t["id"]][0]
                c += gl[p][t["id"]][1] + P.N_TRIES    # tests; plus the SELF judgments used for tie-breaks
                pt += sum(self_rows.get(f"{t['id']}|{P.ARM}|{i}", 0) for i in range(P.N_TRIES))
        out[p] = dict(generated=c / len(tasks), prompt=pt / len(tasks))
    return out


def verdict(rt):
    """rt: table()["all"] rates (%). E1: TEST-T >= FIRST + 10; E2: >= SELF + 5; E3: >= TEST-B + 5. PASS = all; PROVED WRONG: TEST-T <= FIRST + 3; else INCONCLUSIVE."""
    if not all(k in rt for k in ("FIRST", "SELF", "TEST-B", "TEST-T")):
        return dict(verdict="INCOMPLETE", checks={})
    T = rt["TEST-T"]
    chk = dict(E1=T >= rt["FIRST"] + E1_PTS - EPS, E2=T >= rt["SELF"] + E2_PTS - EPS, E3=T >= rt["TEST-B"] + E3_PTS - EPS)
    v = "PASS" if all(chk.values()) else "PROVED WRONG" if T <= rt["FIRST"] + WRONG_PTS + EPS else "INCONCLUSIVE"
    return dict(verdict=v, checks=chk, needs=dict(E1=rt["FIRST"] + E1_PTS, E2=rt["SELF"] + E2_PTS, E3=rt["TEST-B"] + E3_PTS), wrong_at=rt["FIRST"] + WRONG_PTS)


def paired_ci(tasks, res, a, b, n=2000, seed=0):
    """95% bootstrap interval (points) of picker a minus picker b over tasks (paired)."""
    d = [100 * (res[t["id"]][a][0] - res[t["id"]][b][0]) for t in tasks]
    rng = random.Random(seed)
    m = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [m[int(0.025 * n)], m[int(0.975 * n)]]


def report_md(info, tab, tok, v, cis, diag):
    L = ["# Probe-4 report", "",
         f"{info['n_tasks']} tasks with all {P.N_TRIES} tries ({info['n_traps']} traps, {info['n_plain']} non-traps); of {info['n_tasks_file']} in the task file. Replay gate: {100 * info['gate']:.2f}% of tries reproduce recorded success.", "",
         "| picker | all tasks (%) | traps (%) | non-traps (%) | generated tokens / task | prompt tokens / task |", "|---|---|---|---|---|---|"]
    f = lambda x: "" if x is None else f"{x:.1f}"   # noqa
    for p, r in tab.items():
        L.append(f"| {p} | {f(r['all'])} | {f(r['traps'])} | {f(r['plain'])} | {tok[p]['generated']:.0f} | {tok[p]['prompt']:.0f} |")
    L += ["", f"Verdict: **{v['verdict']}**"]
    if v["checks"]:
        n = v["needs"]
        L.append(f"Pass marks (PREREG): E1 TEST-T >= FIRST + 10 points (>= {n['E1']:.1f}%); E2 >= SELF + 5 (>= {n['E2']:.1f}%); E3 >= TEST-B + 5 (>= {n['E3']:.1f}%). Proved wrong: TEST-T <= FIRST + 3 (<= {v['wrong_at']:.1f}%). "
                 + ", ".join(f"{k}={'ok' if x else 'FAIL'}" for k, x in v["checks"].items()))
    if cis:
        L += ["", "Paired bootstrap 95% intervals (points, over tasks; reported only, the verdict uses the point values):"] + [f"- {k}: [{lo:.1f}, {hi:.1f}]" for k, (lo, hi) in cis.items()]
    L += ["", "RAND is the expected success of a random try (mean over the 12). Ties for TEST-B / TEST-T break by SELF, then the lowest try. Tokens: FIRST = one try; RAND / VOTE / ORACLE = the 12 tries; SELF = 12 tries + 12 judge passes; "
          "TEST-x = 12 tries + 4 test samples + the 12 judge passes used for tie-breaks."]
    for n, d in diag.items():
        L.append(f"- {n} tests: unparsable replies {d['unparsable_samples']}/{d['n_samples']}, validity {100 * d['validity_rate']:.1f}%, samples with no valid check {d['samples_with_no_valid']}, "
                 f"agree with the reference plan {100 * d['reference_agreement']:.1f}%, tasks where all 12 tries tie on the score {100 * d['all_tie_rate']:.1f}%")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=P.TASKS_NEW)
    ap.add_argument("--tries", required=True)
    ap.add_argument("--self", dest="self_", default=None)
    ap.add_argument("--test-b", default=None)
    ap.add_argument("--test-t", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    alltasks, tasks, rows = load_inputs(a.tasks, a.tries)
    if not tasks:
        sys.exit("no task has all 12 tries")
    rate, states = gate(alltasks, rows)
    if rate < 0.99:
        sys.exit(f"replay gate failed ({100 * rate:.2f}% < 99%)")
    self_ = self_scores(a.self_)
    probes, gl, paths = {}, {}, {"TEST-B": a.test_b, "TEST-T": a.test_t}
    for n, p in paths.items():
        if p and os.path.exists(p) and P.read_jsonl(p):
            probes[n] = an.load_probes(p)
            gl[n] = genlog(p)
    res, sc, recs = pick_all(tasks, rows, states, self_, probes)
    tab = table(tasks, res)
    selfp = {r["key"]: r.get("n_prompt", 0) for r in P.read_jsonl(a.self_)} if a.self_ and os.path.exists(a.self_) else {}
    tok = tokens_per_task(tasks, rows, selfp, gl)
    v = verdict({p: r["all"] for p, r in tab.items()})
    cis = {f"TEST-T - {b}": paired_ci(tasks, res, "TEST-T", b) for b in ("FIRST", "SELF", "TEST-B") if "TEST-T" in tab and b in tab}
    ref = {t["id"]: replay.replay_reference(t) for t in tasks}
    pools = an.group(recs)
    diag = {n: an.diagnostics(probes[n], tasks, ref, sc[n], pools) for n in probes}
    info = dict(n_tasks=len(tasks), n_tasks_file=len(alltasks), n_traps=sum(bool(t.get("trap")) for t in tasks), n_plain=sum(not t.get("trap") for t in tasks), gate=rate, tasks_sha256=P.sha256(a.tasks))
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(info=info, rates=tab, tokens=tok, ci=cis, diagnostics=diag, picks={t: {p: x[1] for p, x in d.items()} for t, d in res.items()}, **v), open(os.path.join(a.out, "report.json"), "w"), indent=1)
    md = report_md(info, tab, tok, v, cis, diag)
    open(os.path.join(a.out, "report.md"), "w").write(md)
    print(md)


if __name__ == "__main__":
    main()
