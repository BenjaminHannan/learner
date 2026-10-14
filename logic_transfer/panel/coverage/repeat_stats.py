"""Hidden-shortcut probe: does the unknown label leave a trace in how often content words repeat? (distinct predicates, singleton predicates)
Uses the first 40k rows of each train file. Writes repeat_stats.json"""
from common import *
import statistics as st
out = {}
for name in ["logic_train", "placebo_train"]:
    by = defaultdict(lambda: defaultdict(list))
    for i, r in enumerate(stream_jsonl(TRAIN[name])):
        if i >= 40000: break
        m = r["meta"]
        facts, rules, query = ck.parse_program(m["program"])
        cnt = Counter()
        for f in facts: cnt[f[1]] += 1
        for ru in rules:
            for _, p in ru.lhs + (ru.rhs,): cnt[p] += 1
        cnt[query[1]] += 1
        ents = Counter([f[2] for f in facts] + [ru.ent for ru in rules if ru.ent] + [query[2]])
        key = (r["level"], m["label"])
        by[key]["distinct_preds"].append(len(cnt)); by[key]["singleton_preds"].append(sum(v == 1 for v in cnt.values()))
        by[key]["distinct_ents"].append(len(ents)); by[key]["query_pred_mentions"].append(cnt[query[1]])
        by[key]["query_ent_mentions"].append(ents[query[2]])
        by[key]["n_sent"].append(len(m["template_ids"]))
    out[name] = {f"d{k[0]}|{k[1]}": {kk: round(st.mean(v), 3) for kk, v in d.items()} | {"n": len(d["n_sent"])} for k, d in sorted(by.items())}
json.dump(out, open(OUT + "/repeat_stats.json", "w"), indent=1)
for name in out:
    print("==", name)
    for k, v in out[name].items(): print(" ", k, v)
