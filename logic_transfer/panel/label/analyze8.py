"""Agreement and label balance by template id (inferred from text).  python3 analyze8.py -> agg8.json"""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
NAMES = ["logic_gate","logic_dev","logic_test_sampler","logic_test_deeper","placebo_dev","placebo_test_wording","logic_train","placebo_train"]
out = {}
for n in NAMES:
    cnt = C.Counter(); agr = C.Counter(); lab = C.defaultdict(C.Counter)
    for l in open(f"{D}/{n}.jsonl"):
        r = json.loads(l)
        if not r["sample"]: continue
        ok = r["mine"] == r["gold"]
        for t in set(r["ids"]):
            cnt[t] += 1; agr[t] += ok
        lab[r["ids"][-1]][r["gold"]] += 1           # question template vs label
    worst = min(agr[t] / cnt[t] for t in cnt)
    ntpl = len(cnt)
    # max deviation of label share per question template from 1/3
    dev = {}
    for q, c in lab.items():
        tot = sum(c.values())
        dev[q] = max(abs(c[k] / tot - 1/3) for k in ("true", "false", "unknown"))
    out[n] = dict(n_templates_seen=ntpl, min_agreement_over_templates=worst, min_rows_per_template=min(cnt.values()), max_rows_per_template=max(cnt.values()),
                  q_template_label_max_dev_from_third=round(max(dev.values()), 3))
    print(n, out[n])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agg8.json"), "w"), indent=1)
