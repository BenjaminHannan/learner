import json, statistics as st
S = range(6); T = 2.571
A = [json.load(open(f"results8/two-copy-ctx-tabv-long-mix-seed{s}.json")) for s in S]       # LONG control (re-run)
B = [json.load(open(f"results8/two-copy-ctx-tabv-long-dist-mix-seed{s}.json")) for s in S]  # DIST
g = lambda r, ev, k, m="chain_ok": 100 * r[ev][k][m][0]
print("train fit chain LONG", [r["train_fit_192"]["chain_ok"] for r in A], "DIST", [r["train_fit_192"]["chain_ok"] for r in B])
def paired(label, ev, k, m="chain_ok"):
    a = [g(r, ev, k, m) for r in A]; b = [g(r, ev, k, m) for r in B]; d = [y - x for x, y in zip(a, b)]
    mu = st.mean(d); se = st.stdev(d) / 6 ** .5
    print(f"{label:30s} LONG {st.mean(a):5.1f} ({st.stdev(a):4.1f})  DIST {st.mean(b):5.1f} ({st.stdev(b):4.1f})  gain {mu:+5.1f} [{mu-T*se:+5.1f},{mu+T*se:+5.1f}] up {sum(x>0 for x in d)}/6")
paired("DISTR chain all (headline)", "eval_distr", "all"); paired("DISTR call1", "eval_distr", "all", "call1_ok"); paired("DISTR call2|call1", "eval_distr", "all", "call2_given_call1")
for k in ("tok_55_80", "tok_81_110", "tok_111_150"):
    a = [100 * r["eval_distr"][k]["chain_ok"][0] for r in A]; b = [100 * r["eval_distr"][k]["chain_ok"][0] for r in B]
    print(f"  DISTR {k:12s} LONG {st.mean(a):5.1f}  DIST {st.mean(b):5.1f}  (n/run {A[0]['eval_distr'][k]['chain_ok'][1]})")
paired("DISTR unseen", "eval_distr", "unseen"); paired("DISTR seen", "eval_distr", "seen")
print("DISTR by layout kind:", {k: (round(st.mean(g(r, 'eval_distr', k) for r in A), 1), round(st.mean(g(r, 'eval_distr', k) for r in B), 1)) for k in A[0]["eval_distr"] if k in ("table","report","other","question_first","first_person","ledger","receipt","spreadsheet","chat","instruction")})
for ev, nm in (("eval_long", "round-7 LONG set"), ("eval", "OLD"), ("eval_blind", "BLIND1"), ("eval_blind2", "BLIND2")): paired(f"{nm} chain all", ev, "all")
# distractor-specific error analysis on DISTR rows
import collections
for nm, rs, pre in (("LONG", A, "two-copy-ctx-tabv-long-mix"), ("DIST", B, "two-copy-ctx-tabv-long-dist-mix")):
    tot = bad = 0; kd = collections.defaultdict(lambda: [0, 0])
    for s in S:
        rows = json.load(open(f"results8/{pre}-seed{s}-distrrows.json")); 
        for x in rows:
            tot += 1; kd[x["id"]][1] += 1; kd[x["id"]][0] += x["chain_ok"]
    print(nm, "rows", tot)
