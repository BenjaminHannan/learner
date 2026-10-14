"""Task 3 (part 1): independence tests of cheap surface variables vs the label. Streams the full train files. Writes shortcuts_chi.json"""
from common import *
import math, sys

# --- chi-square survival function without scipy (regularised upper incomplete gamma, Numerical Recipes)
def gammq(a, x):
    if x <= 0: return 1.0
    if x < a + 1:
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1; d *= x / ap; s += d
            if abs(d) < abs(s) * 1e-14: break
        return 1 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    b = x + 1 - a; c = 1e300; d = 1 / b; h = d
    for i in range(1, 500):
        an = -i * (i - a); b += 2; d = an * d + b; d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d; de = d * c; h *= de
        if abs(de - 1) < 1e-14: break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h

def chi2(table):
    """table: dict row_value -> Counter(label). Returns chi2, df, p, cramersV (cells with expected<5 pooled away by dropping rare rows)."""
    labs = sorted({l for c in table.values() for l in c})
    rows = [v for v in table if sum(table[v].values()) >= 20]
    n = sum(sum(table[v].values()) for v in rows)
    if len(rows) < 2: return None
    col = {l: sum(table[v][l] for v in rows) for l in labs}
    x2 = 0.0
    for v in rows:
        rt = sum(table[v].values())
        for l in labs:
            e = rt * col[l] / n
            if e > 0: x2 += (table[v][l] - e) ** 2 / e
    df = (len(rows) - 1) * (len(labs) - 1)
    V = math.sqrt(x2 / (n * min(len(rows) - 1, len(labs) - 1)))
    return dict(chi2=round(x2, 2), df=df, p=float("%.3g" % gammq(df / 2, x2 / 2)), cramers_V=round(V, 4), n=n, rows_kept=len(rows))

NEG = re.compile(r"\bnot\b|n't|\bnever\b|non-", re.I)
VARS = ["suffix_perm", "answer_slot", "q_template", "q_has_unknown_word", "neg_cue_count", "n_sentences", "chars_decile", "n_FN_sentences", "n_distractors", "depth"]

def scan(path):
    tabs = {v: defaultdict(Counter) for v in VARS}
    chars = []
    rows = []
    for r in stream_jsonl(path):
        m = r["meta"]; lab = r["answer"]
        body, opts = split_prompt(r["prompt"])
        t = tabs
        t["suffix_perm"][opts][lab] += 1
        t["answer_slot"][opts.index(lab)][lab] += 1
        qt = m["template_ids"][-1]
        t["q_template"][qt][lab] += 1
        t["q_has_unknown_word"][qt in ("Q:2", "Q:10")][lab] += 1   # question sentence itself spells out 'true, false or unknown'
        t["neg_cue_count"][min(len(NEG.findall(body)), 7)][lab] += 1
        t["n_sentences"][len(m["template_ids"])][lab] += 1
        t["n_FN_sentences"][min(sum(x.startswith("FN") for x in m["template_ids"]), 4)][lab] += 1
        t["n_distractors"][m["n_distractors"]][lab] += 1
        t["depth"][r["level"]][lab] += 1
        chars.append((len(r["prompt"]), lab))
    cs = sorted(c for c, _ in chars); qs = [cs[int(i * len(cs) / 10)] for i in range(1, 10)]
    for c, lab in chars: tabs["chars_decile"][sum(c > q for q in qs)][lab] += 1
    return {v: chi2(tabs[v]) for v in VARS}, tabs

res = {}
for name, p in list(TRAIN.items()) + list(EVAL.items()):
    r, tabs = scan(p); res[name] = r
    if name in ("logic_train", "placebo_train"):
        res[name + "_tables"] = {"suffix_perm": {" / ".join(k): dict(v) for k, v in tabs["suffix_perm"].items()},
                                 "neg_cue_count": {str(k): dict(v) for k, v in sorted(tabs["neg_cue_count"].items())},
                                 "q_template": {k: dict(v) for k, v in sorted(tabs["q_template"].items(), key=lambda kv: int(kv[0].split(':')[1]))}}
    print("done", name, file=sys.stderr)
json.dump(res, open(OUT + "/shortcuts_chi.json", "w"), indent=1)
print("%-22s" % "file", *["%-18s" % v[:18] for v in VARS])
for name in list(TRAIN) + list(EVAL):
    print("%-22s" % name, *["%-18s" % ("p=%.2g V=%.3f" % (res[name][v]["p"], res[name][v]["cramers_V"]) if res[name][v] else "-") for v in VARS])
