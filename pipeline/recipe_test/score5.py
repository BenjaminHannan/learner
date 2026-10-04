import json, statistics as st, sys
S = range(6); T = 2.571
def L(arm, s): return json.load(open(f"results5/two-copy-ctx-{arm}-mix-seed{s}.json"))
A = [L("comp", s) for s in S]; B = [L("tabv", s) for s in S]
def g(r, ev, k, m="chain_ok"): return 100 * r[ev][k][m][0]
def level(rs, ev, k, m="chain_ok"):
    a = [g(r, ev, k, m) for r in rs]; return st.mean(a), st.stdev(a)
def paired(label, ev, k, m="chain_ok"):
    a = [g(r, ev, k, m) for r in A]; b = [g(r, ev, k, m) for r in B]; d = [y - x for x, y in zip(a, b)]
    mu = st.mean(d); se = st.stdev(d) / 6 ** .5
    print(f"{label:34s} COMP {st.mean(a):5.1f} ({st.stdev(a):4.1f})  TABV {st.mean(b):5.1f} ({st.stdev(b):4.1f})  gain {mu:+5.1f} [{mu-T*se:+5.1f},{mu+T*se:+5.1f}] up {sum(x>0 for x in d)}/6")
print("train fit chain COMP", [r["train_fit_192"]["chain_ok"] for r in A], "TABV", [r["train_fit_192"]["chain_ok"] for r in B])
for ev, nm in (("eval", "OLD"), ("eval_blind", "BLIND")):
    paired(f"{nm} chain all", ev, "all"); paired(f"{nm} call1", ev, "all", "call1_ok"); paired(f"{nm} call2|call1", ev, "all", "call2_given_call1")
    for k in (["narrative", "question_first", "table", "distance"] if ev == "eval" else ["table", "question_first", "first_person", "chat", "instruction", "report", "other"]): paired(f"{nm} {k}", ev, k)
    paired(f"{nm} unseen", ev, "unseen"); paired(f"{nm} seen", ev, "seen")
# per blind family
fam = {}
for arm, rs in (("COMP", A), ("TABV", B)):
    for s, r in zip(S, rs):
        rows = json.load(open(f"results5/{r['name']}-blindrows.json"))
        for x in rows:
            f = x["cell"].split("/")[1]; fam.setdefault(f, {}).setdefault(arm, []).append(x["chain_ok"])
print("per blind family (chain, pooled over 6 seeds x 16 q):")
for f, d in fam.items(): print(f"  {f:18s} COMP {100*st.mean(d['COMP']):5.1f}  TABV {100*st.mean(d['TABV']):5.1f}")
