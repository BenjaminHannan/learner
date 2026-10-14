"""Re-derive the singleton leak from the PROMPT TEXT ONLY (no program, no checker): predicate-like words = words not in any template and not capitalised;
count of those occurring exactly once in the prompt. Lookup classifier (singleton count, n sentences) cross-fitted on 40k train rows, applied to eval files."""
from common import *
tw = set()
for kind, lst in TP.TEMPLATES.items():
    for t in lst: tw |= {w.lower() for w in words(re.sub(r"\{[a-z]\}", " ", t))}
tw |= {"t", "isn", "true", "false", "unknown", "non"}
def feat(r):
    body, _ = split_prompt(r["prompt"])
    toks = [w for w in words(body) if w[0].islower() and w.lower() not in tw]
    c = Counter(toks)
    return (sum(v == 1 for v in c.values()), len(sentences(body)))
res = {}
for tr in ["logic_train", "placebo_train"]:
    rows = read_jsonl(TRAIN[tr], 40000)
    F = [feat(r) for r in rows]
    ok = 0
    for fold in range(5):
        t = defaultdict(Counter)
        for i, (f, r) in enumerate(zip(F, rows)):
            if i % 5 != fold: t[f][r["answer"]] += 1
        for i, (f, r) in enumerate(zip(F, rows)):
            if i % 5 == fold:
                c = t.get(f); ok += (c.most_common(1)[0][0] if c else "true") == r["answer"]
    t = defaultdict(Counter)
    for f, r in zip(F, rows): t[f][r["answer"]] += 1
    ev = {}
    for en in [k for k in EVAL if k.startswith(tr.split("_")[0])]:
        er = read_jsonl(EVAL[en]); h = 0
        for r in er:
            c = t.get(feat(r)); h += (c.most_common(1)[0][0] if c else "true") == r["answer"]
        ev[en] = round(100 * h / len(er), 2)
    # mean singleton by label
    by = defaultdict(list)
    for f, r in zip(F, rows): by[r["answer"]].append(f[0])
    res[tr] = dict(oof_acc=round(100 * ok / len(rows), 2), eval=ev, mean_singletons_by_label={k: round(sum(v) / len(v), 3) for k, v in by.items()})
    print(tr, res[tr])
json.dump(res, open(OUT + "/leak_text_only.json", "w"), indent=1)
