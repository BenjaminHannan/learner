"""Which surface WORDS carry label information? presence-of-word vs label, 50k train rows per file, template/function words only (entity and predicate
words are random per problem). z = (observed count in class - expected)/sqrt(expected*(1-p)). Writes word_info.json"""
from common import *
import math
tw = set()
for kind, lst in TP.TEMPLATES.items():
    for t in lst: tw |= {w.lower() for w in words(re.sub(r"\{[a-z]\}", " ", t))}
tw |= {"t", "isn"}
out = {}
for name in ["logic_train", "placebo_train"]:
    lab = Counter(); df = defaultdict(Counter); n = 0
    for i, r in enumerate(stream_jsonl(TRAIN[name])):
        if i >= 50000: break
        body, _ = split_prompt(r["prompt"])
        toks = {w.lower() for w in words(body)} & tw
        if "n't" in body: toks.add("n't")
        a = r["answer"]; lab[a] += 1; n += 1
        for t in toks: df[t][a] += 1
    res = []
    for t, c in df.items():
        tot = sum(c.values())
        if tot < 500: continue
        for a in lab:
            p = lab[a] / n; e = tot * p; z = (c[a] - e) / math.sqrt(e * (1 - p))
            res.append((abs(z), t, a, round(100 * c[a] / tot, 1), tot, round(z, 1)))
    res.sort(reverse=True)
    out[name] = [dict(word=t, label=a, pct_label_given_word=pc, n_rows_with_word=tot, z=z) for _, t, a, pc, tot, z in res[:14]]
    print(name, [(o["word"], o["label"], o["pct_label_given_word"], o["z"]) for o in out[name][:10]])
json.dump(out, open(OUT + "/word_info.json", "w"), indent=1)
