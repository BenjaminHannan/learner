import json, statistics as st
S = range(6); T = 2.571
def L(arm, s): return json.load(open(f"results6/two-copy-ctx-{arm}-mix-seed{s}.json"))
A = [L("tabv", s) for s in S]; B = [L("rlv", s) for s in S]
def g(r, ev, k, m="chain_ok"): return 100 * r[ev][k][m][0]
def paired(label, ev, k, m="chain_ok"):
    a = [g(r, ev, k, m) for r in A]; b = [g(r, ev, k, m) for r in B]; d = [y - x for x, y in zip(a, b)]
    mu = st.mean(d); se = st.stdev(d) / 6 ** .5
    print(f"{label:34s} TABV {st.mean(a):5.1f} ({st.stdev(a):4.1f})  RLV {st.mean(b):5.1f} ({st.stdev(b):4.1f})  gain {mu:+5.1f} [{mu-T*se:+5.1f},{mu+T*se:+5.1f}] up {sum(x>0 for x in d)}/6")
print("train fit chain TABV", [r["train_fit_192"]["chain_ok"] for r in A], "RLV", [r["train_fit_192"]["chain_ok"] for r in B])
for ev, nm, kinds in (("eval_blind2", "BLIND2", ["report", "table", "other", "question_first", "first_person", "chat", "instruction"]), ("eval_blind", "BLIND1", None), ("eval", "OLD", None)):
    paired(f"{nm} chain all", ev, "all"); paired(f"{nm} call1", ev, "all", "call1_ok"); paired(f"{nm} call2|call1", ev, "all", "call2_given_call1")
    if ev == "eval_blind2":
        print("   blind2 structures present:", [k for k in A[0][ev] if k not in ("all","unseen","seen") and not k.startswith(("first_","second_"))])
        for k in [k for k in A[0][ev] if k not in ("all","unseen","seen") and not k.startswith(("first_","second_"))]: paired(f"{nm} {k}", ev, k)
    paired(f"{nm} unseen", ev, "unseen"); paired(f"{nm} seen", ev, "seen")
fam = {}
for arm, rs in (("TABV", A), ("RLV", B)):
    for r in rs:
        for x in json.load(open(f"results6/{r['name']}-blind2rows.json")):
            fam.setdefault(x["cell"].split("/")[1], {}).setdefault(arm, []).append(x["chain_ok"])
print("per blind-2 family (chain, pooled 6 seeds x 16 q):")
for f, d in fam.items(): print(f"  {f:22s} TABV {100*st.mean(d['TABV']):5.1f}  RLV {100*st.mean(d['RLV']):5.1f}")
