"""logic_test_sampler composition: label by level, constant-answer accuracy, polarity-only rule.  -> agg9.json"""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
rows = [json.loads(l) for l in open(f"{D}/logic_test_sampler.jsonl")]
bylev = C.defaultdict(C.Counter)
for r in rows: bylev[r["lvl"]][r["gold"]] += 1
pool = [r for r in rows if r["lvl"] in (2, 3)]
const = {k: sum(r["gold"] == k for r in pool) / len(pool) for k in ("true", "false", "unknown")}
# polarity-only rule fitted on the file itself (upper bound for a polarity shortcut)
tab = C.defaultdict(C.Counter)
for r in rows: tab[r["qneg"]][r["gold"]] += 1
best = {k: v.most_common(1)[0][0] for k, v in tab.items()}
pol_acc = sum(r["gold"] == best[r["qneg"]] for r in rows) / len(rows)
pool_tab = C.defaultdict(C.Counter)
for r in pool: pool_tab[r["qneg"]][r["gold"]] += 1
pool_best = {k: v.most_common(1)[0][0] for k, v in pool_tab.items()}
pool_pol = sum(r["gold"] == pool_best[r["qneg"]] for r in pool) / len(pool)
out = dict(label_by_level={str(k): dict(v) for k, v in sorted(bylev.items())}, pooled_depth2_3_n=len(pool), pooled_depth2_3_constant_answer_acc=const,
           polarity_only_rule=dict(rule={str(k): v for k, v in best.items()}, acc_all=pol_acc, acc_pooled_depth2_3=pool_pol, pooled_table={str(k): dict(v) for k, v in pool_tab.items()}))
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg9.json"), "w"), indent=1)

# polarity-only rule fitted per file (query negated or not -> most common label), 20k-sample for train files
res = {}
for n in ["logic_gate", "logic_dev", "logic_test_sampler", "logic_test_deeper", "placebo_dev", "placebo_test_wording", "logic_train", "placebo_train"]:
    rs = [r for r in (json.loads(l) for l in open(f"{D}/{n}.jsonl")) if r["sample"]]
    tab = C.defaultdict(C.Counter)
    for r in rs: tab[r["qneg"]][r["gold"]] += 1
    best = {k: v.most_common(1)[0][0] for k, v in tab.items()}
    res[n] = round(sum(r["gold"] == best[r["qneg"]] for r in rs) / len(rs), 4)
print("polarity-only accuracy by file:", res)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg10_polarity_only.json"), "w"), indent=1)
