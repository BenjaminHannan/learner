"""Task 4: learnability ladder WITHOUT training. Non-neural solvers of increasing sophistication on placebo depth-0 rows
(and, for contrast, logic rows by depth). Also: single-feature accuracy ranking for the audit's structure features.
Writes ladder.json. Pure python/stdlib; no model, no GPU."""
from common import *
import sys, hashlib
sys.path.insert(0, REPO)
import logicgen.audit as AU      # read-only import (bytecode writing is off)

LABELS = ["true", "false", "unknown"]
TEMPLATE_VOCAB = set()
for kind, lst in TP.TEMPLATES.items():
    for t in lst:
        TEMPLATE_VOCAB |= {w.lower() for w in words(re.sub(r"\{[a-z]\}", " ", t))}
TEMPLATE_VOCAB |= {"true", "false", "unknown", "is", "not", "it", "n", "t", "isn", "non"}
res_overlap = sorted(TEMPLATE_VOCAB & (set(LEX.ENTITIES) | set(LEX.COMMON_WORDS)))
NEG_RE = re.compile(r"\bnot\b|n't|\bnever\b|non-", re.I)

def content_tokens(sent):
    toks = words(sent)
    return [w for w in toks if w.lower() not in TEMPLATE_VOCAB]

def coin(rid):
    return int(hashlib.sha256(rid.encode()).hexdigest(), 16) & 1

def solvers(r):
    """returns dict solver_name -> predicted label (text-only unless stated)."""
    P = parse_row(r)
    body, spans, kinds = P["body"], P["spans"], P["kinds"]
    qa, qb, qt = spans[-1]
    qtoks = content_tokens(qt)
    out = {}
    if len(qtoks) != 2:
        return None
    qent = [t for t in qtoks if t[0].isupper()]
    if len(qent) != 1: return None
    qent = qent[0].lower(); qpred = [t for t in qtoks if t.lower() != qent][0].lower()
    qneg = bool(NEG_RE.search(qt))
    ctx_sents = spans[:-1]
    def match(role_aware):
        hits = []
        for i, (a, b, t) in enumerate(ctx_sents):
            if role_aware and kinds[i] not in ("FP", "FN"): continue
            ct = [w.lower() for w in content_tokens(t)]
            if qent in ct and qpred in ct: hits.append(i)
        return hits
    for name, ra in (("S3_text_match_any_sentence", False), ("S5_text_match_fact_sentences_only", True)):
        hits = match(ra)
        if not hits:
            out[name + "_presence"] = "unknown"; out[name + "_polarity"] = "unknown"
            continue
        i = hits[0]
        sneg = bool(NEG_RE.search(ctx_sents[i][2]))
        out[name + "_presence"] = LABELS[coin(r["id"])]            # stated: polarity not looked at -> fair coin between true/false
        out[name + "_presence"] = "true" if coin(r["id"]) else "false"
        out[name + "_polarity"] = "true" if sneg == qneg else "false"
    return out

def run(path, limit=None):
    rows = [r for i, r in enumerate(stream_jsonl(path)) if not limit or i < limit]
    n = len(rows)
    res = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    skipped = 0
    for r in rows:
        s = solvers(r)
        if s is None:
            skipped += 1; continue
        g = f"d{r['level']}" if r["meta"]["sampler"] == "label-first" else "all"
        for key in (g, "ALL"):
            for k, pred in s.items():
                res[key][k][1] += 1; res[key][k][0] += (pred == r["answer"])
            res[key]["majority_const_true"][1] += 1; res[key]["majority_const_true"][0] += (r["answer"] == "true")
    out = {g: {k: dict(correct=c, n=t, acc=round(100 * c / t, 2)) for k, (c, t) in d.items()} for g, d in res.items()}
    return out, skipped, n

def single_feature(path, basic_drop=(), limit=6000, k=5):
    rows = read_jsonl(path, limit)
    X = []
    y = []
    for r in rows:
        m = r["meta"]
        body, _ = split_prompt(r["prompt"])
        row = dict(m); row["question"] = body
        X.append(AU.features(row, basic=False)); y.append(r["answer"])
    cols = AU.FEATURES
    maj = Counter(y).most_common(1)[0][1] / len(y)
    out = {}
    for j, name in enumerate(cols):
        vals = sorted({x[j] for x in X})
        if len(vals) > 12:
            qs = [sorted(x[j] for x in X)[int(p * len(X))] for p in [i / 10 for i in range(1, 10)]]
            def b(v): return sum(v > t for t in qs)
        else:
            def b(v): return v
        ok = 0
        for fold in range(k):
            tab = defaultdict(Counter)
            for i, x in enumerate(X):
                if i % k != fold: tab[b(x[j])][y[i]] += 1
            for i, x in enumerate(X):
                if i % k == fold:
                    c = tab.get(b(x[j]))
                    ok += (c.most_common(1)[0][0] if c else "true") == y[i]
        out[name] = round(100 * (ok / len(X) - maj), 2)
    return dict(majority=round(100 * maj, 2), gain_pts_over_majority_single_feature=out, n=len(rows))

res = {"template_vocab_overlap_with_entity_or_pred_words": res_overlap}
for name in ["placebo_dev", "placebo_test_wording", "logic_gate", "logic_dev", "logic_test_sampler"]:
    out, skipped, n = run(EVAL[name]); res[name] = out; res[name]["_skipped"] = skipped; res[name]["_n"] = n
    print(name, "skipped", skipped, "/", n, file=sys.stderr)
for name in ["placebo_train", "logic_train"]:
    out, skipped, n = run(TRAIN[name], 10000); res[name + "_first10k"] = out; res[name + "_first10k"]["_skipped"] = skipped
# single-feature table from the converted train rows (first 6000)
res["single_feature_table"] = {n: single_feature(TRAIN[n], limit=6000) for n in ["placebo_train", "logic_train"]}
json.dump(res, open(OUT + "/ladder.json", "w"), indent=1)
for k in ["placebo_dev", "placebo_test_wording", "logic_gate"]:
    print("==", k)
    for g, d in res[k].items():
        if g.startswith("_"): continue
        print(" ", g, {kk: v["acc"] for kk, v in d.items()})
print(json.dumps(res["single_feature_table"], indent=1))
print("overlap", res_overlap)
