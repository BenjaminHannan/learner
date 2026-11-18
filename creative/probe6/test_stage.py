"""Probe-6 TEST stage (PREREG.md). WRITTEN, NOT RUN: runs once, after DEV.md (with the chosen arm and t) is committed.
Applies ASK-GATE (chosen judge arm, chosen t) to the frozen Probe-5 LFM3 pools (96 tasks) with Probe-5's TEST-T and SELF scores and its tries; no new tries.
Inputs: Probe-5 results dir (tries/results.jsonl, self_scores.jsonl, tests_t/probes_lfm3.jsonl), tasks_new.jsonl, judge scores {task, p_ask} from the CHOSEN arm and from J-HAIKU on those 96 tasks,
and dev_choice.json (written by dev stage: {"arm":..., "t":...}). Pass marks: A1 all-task pick >= TEST-T + 5 (62.3 on the prereg's 57.3); A2 non-trap pick >= 77.5. PASS = A1 and A2;
PROVED WRONG: all-task pick <= TEST-T + 1 (58.3); else INCONCLUSIVE. Reported: traps / non-traps, judge test AUROC, ORACLE-GATE, J-HAIKU gate, TEST-T.
Usage: test_stage.py --p5 creative/probe5/results/m3 --choice out/dev_choice.json --judge out/test_judge.jsonl --haiku out/test_haiku.jsonl --out out/test_report.json"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p6common as C

A1_PTS, A2_FLOOR, WRONG_PTS, EPS = 5.0, 77.5, 1.0, 1e-9      # fixed in PREREG (A2 = 81.0 - 3.5; A1/WRONG relative to TEST-T measured on the same pools)
PREREG_TEST_T = 57.3


def verdict(test_t_all, gate_all, gate_plain):
    """A1: gate_all >= TEST-T + 5; A2: gate_plain >= 77.5. PASS = both; PROVED WRONG: gate_all <= TEST-T + 1; else INCONCLUSIVE."""
    a1 = gate_all >= test_t_all + A1_PTS - EPS
    a2 = gate_plain >= A2_FLOOR - EPS
    v = "PASS" if a1 and a2 else "PROVED WRONG" if gate_all <= test_t_all + WRONG_PTS + EPS else "INCONCLUSIVE"
    return dict(verdict=v, A1=a1, A2=a2, needs_all=test_t_all + A1_PTS, wrong_at=test_t_all + WRONG_PTS)


def committed_dev():
    """Refuse to run unless DEV.md and dev_choice.json are committed (clean) -- the choice must precede any Probe-5 pool."""
    here = os.path.dirname(os.path.abspath(__file__))
    for f in ("DEV.md", "out/dev_choice.json"):
        if subprocess.run(["git", "-C", here, "ls-files", "--error-unmatch", f], capture_output=True).returncode:
            sys.exit(f"{f} is not committed: finish and commit the dev stage first")
        if subprocess.run(["git", "-C", here, "diff", "--quiet", "HEAD", "--", f]).returncode:
            sys.exit(f"{f} has uncommitted changes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p5", required=True); ap.add_argument("--choice", required=True)
    ap.add_argument("--judge", required=True); ap.add_argument("--haiku", required=True)
    ap.add_argument("--tasks", default=None); ap.add_argument("--tries", default=None, help="decompressed tries/results.jsonl (the repo copy is .gz)"); ap.add_argument("--out", required=True)
    ap.add_argument("--skip-commit-check", action="store_true")
    a = ap.parse_args()
    if not a.skip_commit_check:
        committed_dev()
    sys.path.insert(0, os.path.join(C.CREATIVE, "probe5"))
    import p5common  # noqa: F401  (sets sys.path for probe4 / probe1)
    import analyze_e2e as E
    P, an = E.P, E.an
    choice = json.load(open(a.choice))
    alltasks, tasks, rows = E.load_inputs(a.tasks or P.TASKS_NEW, a.tries or os.path.join(a.p5, "tries", "results.jsonl"))
    rate, states = E.gate(alltasks, rows)
    if rate < 0.99:
        sys.exit(f"replay gate failed ({100 * rate:.2f}% < 99%)")
    self_ = E.self_scores(os.path.join(a.p5, "self_scores.jsonl"))
    probes = {"TEST-T": an.load_probes(os.path.join(a.p5, "tests_t", "probes_lfm3.jsonl"))}
    _, sc, recs = E.pick_all(tasks, rows, states, self_, probes)
    test_t = sc["TEST-T"]
    pools = {}
    for r in recs:
        pools.setdefault(r["pool"], []).append(dict(pool=r["pool"], task=r["task"], try_idx=r["try_idx"], success=bool(r["success"]),
                                                    final_reply=rows[(r["task"], r["try_idx"])].get("final_reply") or "", k=f"{r['pool']}|{r['try_idx']}"))
    pools = {p: sorted(v, key=lambda m: m["try_idx"]) for p, v in pools.items()}
    tb = {t["id"]: t for t in tasks}
    trap = lambda tid: bool(tb[tid].get("trap"))     # noqa: E731  (Probe-4/5 task files carry the trap flag)

    def rates(p_ask, t):
        g = {"all": [], "traps": [], "plain": []}
        for mem in pools.values():
            w = float(C.gate_pick(mem, test_t, self_, p_ask.get(mem[0]["task"]), t)["success"])
            g["all"].append(w); g["traps" if trap(mem[0]["task"]) else "plain"].append(w)
        return {k: (100 * sum(v) / len(v) if v else None) for k, v in g.items()}

    load = lambda p: {r["task"]: r["p_ask"] for r in C.read_jsonl(p)}   # noqa: E731
    judge, haiku = load(a.judge), load(a.haiku)
    oracle = {t: 1.0 if trap(t) else 0.0 for t in tb}
    t = choice["t"]
    ids = [x for x in tb if judge.get(x) is not None]
    out = dict(choice=choice, n_tasks=len(tb), n_traps=sum(map(trap, tb)), replay_gate=rate,
               rates={"TEST-T": rates({}, 2.0), "ASK-GATE": rates(judge, t), "ORACLE-GATE": rates(oracle, 0.5), "J-HAIKU": rates(haiku, t)},
               judge_auroc=C.auroc([judge[x] for x in ids], [trap(x) for x in ids]),
               haiku_auroc=C.auroc([haiku[x] for x in tb if haiku.get(x) is not None], [trap(x) for x in tb if haiku.get(x) is not None]),
               missing_judge=len(tb) - len(ids))
    out["verdict"] = verdict(out["rates"]["TEST-T"]["all"], out["rates"]["ASK-GATE"]["all"], out["rates"]["ASK-GATE"]["plain"])
    out["prereg_test_t_reference"] = PREREG_TEST_T
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
