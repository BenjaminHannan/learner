"""How novel is the held-out wording, really? Static analysis of templates.py: words and word-bigrams of held-out templates that occur in NO train template."""
from common import *
tw, tb = set(), set()
hw = defaultdict(set); hb = defaultdict(set)
def toks(t): return [w.lower() for w in words(re.sub(r"\{[a-z]\}", " X ", t))]
for kind, lst in TP.TEMPLATES.items():
    for i, t in enumerate(lst):
        w = toks(t); b = set(zip(w, w[1:]))
        if i % 3 == 2:
            hw[kind] |= set(w); hb[kind] |= b
        else:
            tw |= set(w); tb |= b
out = {}
for kind in TP.TEMPLATES:
    out[kind] = dict(heldout_templates=len([i for i in range(len(TP.TEMPLATES[kind])) if i % 3 == 2]), train_templates=len([i for i in range(len(TP.TEMPLATES[kind])) if i % 3 != 2]),
                     heldout_words_not_in_any_train_template=sorted(hw[kind] - tw), heldout_bigrams_not_in_any_train_template=sorted(" ".join(b) for b in hb[kind] - tb)[:20],
                     n_novel_bigrams=len(hb[kind] - tb), n_heldout_bigrams=len(hb[kind]))
# per-template: share of its word bigrams that are novel
per = {}
for kind, lst in TP.TEMPLATES.items():
    for i, t in enumerate(lst):
        if i % 3 == 2:
            w = toks(t); b = set(zip(w, w[1:])); per[f"{kind}:{i}"] = dict(text=t, novel_bigram_share=round(len(b - tb) / max(1, len(b)), 2), novel_words=sorted(set(w) - tw))
out["_per_heldout_template"] = per
json.dump(out, open(OUT + "/wording_novelty.json", "w"), indent=1)
allnovel_words = sorted(set().union(*[set(hw[k]) for k in hw]) - tw)
print("held-out words absent from every train template:", allnovel_words)
for k, v in per.items(): print(k, v["text"], v["novel_bigram_share"], v["novel_words"])
