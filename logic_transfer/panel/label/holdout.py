"""Template hold-out check from template ids INFERRED FROM THE TEXT (perrow/*.jsonl 'ids'), not from the stored meta.
   usage: python3 holdout.py  -> holdout.json"""
import json, os, re, collections as C, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perrow")
NAMES = ["logic_gate","logic_dev","logic_test_sampler","logic_test_deeper","placebo_dev","placebo_test_wording","logic_train","placebo_train"]
res = {}
for n in NAMES:
    use = C.Counter(); held = C.Counter(); tot = 0; rows_all_held = 0; rows_any_held = 0; tsets = C.Counter()
    for l in open(f"{D}/{n}.jsonl"):
        r = json.loads(l)
        ids = r["ids"]
        hs = [int(i.split(":")[1]) % 3 == 2 for i in ids]
        tsets[r["tset"]] += 1
        for i, h in zip(ids, hs):
            use[i.split(":")[0]] += 1; held[i.split(":")[0]] += h
        rows_all_held += all(hs); rows_any_held += any(hs)
        tot += 1
    res[n] = dict(rows=tot, meta_template_set=dict(tsets), rows_with_any_heldout_template=rows_any_held, rows_with_all_templates_heldout=rows_all_held,
                  heldout_sentence_share_by_kind={k: round(held[k] / use[k], 4) for k in use})
    print(n, res[n])
# lexical novelty of held-out templates (words that occur in no train template)
tpl = {"R1": rlib._R1, "R2": rlib._R2, "R3": rlib._R3, "R4": rlib._R4, "R5": rlib._R5, "FP": rlib._FP, "FN": rlib._FN, "Q": rlib._QS}
words = lambda t: re.findall(r"[A-Za-z']+(?:-)?", re.sub(r"\{[A-Z]\}", " ", t).lower())
trainw = {w for k, L in tpl.items() for i, t in enumerate(L) if i % 3 != 2 for w in words(t)}
nov = {}
for k, L in tpl.items():
    for i, t in enumerate(L):
        if i % 3 == 2:
            nw = sorted(set(words(t)) - trainw)
            nov[f"{k}:{i}"] = dict(text=t, novel_words=nw)
res["heldout_templates"] = nov
print({k: v["novel_words"] for k, v in nov.items() if v["novel_words"]})
print("held-out templates:", len(nov), " with >=1 word absent from every train template:", sum(bool(v["novel_words"]) for v in nov.values()))
# any held-out template identical (after slot masking) to a train template of another kind?
mask = lambda t: re.sub(r"\{[A-Z]\}", "_", t)
allm = C.Counter(mask(t) for L in tpl.values() for t in L)
res["template_strings_duplicated_across_kinds"] = [m for m, c in allm.items() if c > 1]
print("duplicate masked template strings:", res["template_strings_duplicated_across_kinds"])
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout.json"), "w"), indent=1)
