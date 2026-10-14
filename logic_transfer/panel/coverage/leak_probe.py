"""Singleton-predicate leak: unknown rows carry one dangling fresh predicate (break_chain / near-miss). Lookup-table classifier on
(distinct predicates, singleton predicates, #sentences) trained on 50k train rows, applied to every eval file. Writes leak_probe.json"""
from common import *
import math

def feats(r):
    m = r["meta"]
    facts, rules, query = ck.parse_program(m["program"])
    cnt = Counter()
    for f in facts: cnt[f[1]] += 1
    for ru in rules:
        for _, p in ru.lhs + (ru.rhs,): cnt[p] += 1
    cnt[query[1]] += 1
    return (len(cnt), sum(v == 1 for v in cnt.values()), len(m["template_ids"]))

def table(rows, keyf):
    t = defaultdict(Counter)
    for r in rows: t[keyf(r)][r["answer"]] += 1
    return t

res = {}
LABS = ["true", "false", "unknown"]
for tr in ["logic_train", "placebo_train"]:
    rows = read_jsonl(TRAIN[tr], 50000)
    F = [feats(r) for r in rows]
    for r, f in zip(rows, F): r["_f"] = f
    keysets = {"singleton_preds+distinct_preds+n_sent": lambda r: r["_f"], "singleton_preds only": lambda r: r["_f"][1], "distinct_preds only": lambda r: r["_f"][0]}
    res[tr] = {}
    for kn, kf in keysets.items():
        # 5-fold cross-fit inside train
        ok = 0; ll = 0.0
        for fold in range(5):
            t = table([r for i, r in enumerate(rows) if i % 5 != fold], kf)
            for i, r in enumerate(rows):
                if i % 5 == fold:
                    c = t.get(kf(r)); 
                    pred = c.most_common(1)[0][0] if c else "true"; ok += pred == r["answer"]
                    n = sum(c.values()) if c else 0
                    p = ((c[r["answer"]] if c else 0) + 1) / (n + 3)   # add-one smoothing
                    ll += -math.log(p)
        d = dict(oof_acc=round(100 * ok / len(rows), 2), oof_logloss=round(ll / len(rows), 4))
        t = table(rows, kf)
        d["eval"] = {}
        if tr == "logic_train":
            evn = [k for k in EVAL if k.startswith("logic")]
        else:
            evn = [k for k in EVAL if k.startswith("placebo")]
        for en in evn:
            er = read_jsonl(EVAL[en])
            hit = 0; byd = defaultdict(lambda: [0, 0])
            for r in er:
                r["_f"] = feats(r); c = t.get(kf(r)); pred = c.most_common(1)[0][0] if c else "true"
                hit += pred == r["answer"]; byd[r["level"]][0] += pred == r["answer"]; byd[r["level"]][1] += 1
            d["eval"][en] = dict(acc=round(100 * hit / len(er), 2), n=len(er), by_level={str(k): round(100 * v[0] / v[1], 1) for k, v in sorted(byd.items())})
        res[tr][kn] = d
    print(tr, json.dumps({k: (v["oof_acc"], v["oof_logloss"], {e: x["acc"] for e, x in v["eval"].items()}) for k, v in res[tr].items()}, indent=1))
res["ln3"] = round(math.log(3), 4)
json.dump(res, open(OUT + "/leak_probe.json", "w"), indent=1)
