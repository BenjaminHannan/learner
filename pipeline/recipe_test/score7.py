import json, statistics as st
S = range(6); T = 2.571
A = [json.load(open(f"results6/two-copy-ctx-tabv-mix-seed{s}.json")) for s in S]       # control (round 6 TABV)
B = [json.load(open(f"results7/two-copy-ctx-tabv-long-mix-seed{s}.json")) for s in S]  # LONG
g = lambda r, ev, k, m="chain_ok": 100 * r[ev][k][m][0]
print("train fit chain LONG", [r["train_fit_192"]["chain_ok"] for r in B])
def paired(label, ev, k, m="chain_ok"):
    a = [g(r, ev, k, m) for r in A]; b = [g(r, ev, k, m) for r in B]; d = [y - x for x, y in zip(a, b)]
    mu = st.mean(d); se = st.stdev(d) / 6 ** .5
    print(f"{label:28s} TABV {st.mean(a):5.1f} ({st.stdev(a):4.1f})  LONG {st.mean(b):5.1f} ({st.stdev(b):4.1f})  gain {mu:+5.1f} [{mu-T*se:+5.1f},{mu+T*se:+5.1f}] up {sum(x>0 for x in d)}/6")
for ev, nm in (("eval", "OLD"), ("eval_blind", "BLIND1"), ("eval_blind2", "BLIND2")):
    paired(f"{nm} chain all", ev, "all"); paired(f"{nm} call1", ev, "all", "call1_ok"); paired(f"{nm} call2|call1", ev, "all", "call2_given_call1")
lc = [g(r, "eval_long", "all") for r in B]
print(f"LONG set chain: mean {st.mean(lc):.1f} (SD {st.stdev(lc):.1f}) per seed {lc}; questions per run {[r['eval_long']['all']['chain_ok'][1] for r in B]}")
print("  call1", round(st.mean(g(r, "eval_long", "all", "call1_ok") for r in B), 1), " call2|call1", round(st.mean(g(r, "eval_long", "all", "call2_given_call1") for r in B), 1))
for k in ("tok_55_80", "tok_81_110", "tok_111_150"):
    v = [100 * r["eval_long"][k]["chain_ok"][0] for r in B]; print(f"  {k:12s} chain {st.mean(v):5.1f} (n/run {B[0]['eval_long'][k]['chain_ok'][1]})")
print("  by structure:", {k: round(st.mean(g(r, "eval_long", k) for r in B), 1) for k in B[0]["eval_long"] if k in ("table","report","other","question_first","first_person","ledger","receipt","spreadsheet","chat","instruction")})
print("  unseen / seen:", round(st.mean(g(r, "eval_long", "unseen") for r in B), 1), round(st.mean(g(r, "eval_long", "seen") for r in B), 1))
print("  length range", B[0]["eval_long"]["ntok_min_max"])
