"""logicgen/audit.py classifiers (naive Bayes, nearest centroid, depth-3 tree) fitted on 6000 FINAL v2 train rows and applied to every eval file.
basic = without the two exact-match features. Writes audit_eval.json"""
from common import *
import sys
sys.path.insert(0, REPO)
import logicgen.audit as AU
def mk(r):
    row = dict(r["meta"]); row["question"] = split_prompt(r["prompt"])[0]; return row
out = {}
for tr, evs in [("logic_train", [k for k in EVAL if k.startswith("logic")]), ("placebo_train", [k for k in EVAL if k.startswith("placebo")])]:
    rows = read_jsonl(TRAIN[tr], 6000)
    y = [r["answer"] for r in rows]
    out[tr] = {}
    for basic in (True, False):
        X = [AU.features(mk(r), basic) for r in rows]
        fits = {"naive_bayes": AU.fit_nb(X, y), "nearest_centroid": AU.fit_centroid(X, y), "tree_depth3": AU.fit_tree(X, y)}
        key = "basic" if basic else "full"
        out[tr][key] = {}
        for en in evs:
            er = read_jsonl(EVAL[en]); Xe = [AU.features(mk(r), basic) for r in er]; ye = [r["answer"] for r in er]
            maj = Counter(ye).most_common(1)[0][1] / len(ye)
            out[tr][key][en] = {k: round(100 * sum(f(x) == t for x, t in zip(Xe, ye)) / len(ye), 2) for k, f in fits.items()}
            out[tr][key][en]["majority"] = round(100 * maj, 2)
        print(tr, key, json.dumps(out[tr][key]), flush=True)
json.dump(out, open(OUT + "/audit_eval.json", "w"), indent=1)
