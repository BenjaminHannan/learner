"""audit.py FULL-feature depth-3 tree (fit on 6000 v2 logic train rows) per depth on gate/dev: shows the full-feature number is a depth-0 lookup effect."""
from common import *
import sys
sys.path.insert(0, REPO)
import logicgen.audit as AU
mk = lambda r: dict(r["meta"], question=split_prompt(r["prompt"])[0])
rows = read_jsonl(TRAIN["logic_train"], 6000)
out = {}
for basic in (False, True):
    X = [AU.features(mk(r), basic) for r in rows]; y = [r["answer"] for r in rows]
    f = AU.fit_tree(X, y)
    for en in ["logic_gate", "logic_dev"]:
        er = read_jsonl(EVAL[en]); by = defaultdict(lambda: [0, 0])
        for r in er:
            p = f(AU.features(mk(r), basic)); by[r["level"]][0] += p == r["answer"]; by[r["level"]][1] += 1
        out[f"{'basic' if basic else 'full'}|{en}"] = {str(k): round(100 * v[0] / v[1], 1) for k, v in sorted(by.items())}
        print("basic" if basic else "full", en, out[f"{'basic' if basic else 'full'}|{en}"], flush=True)
json.dump(out, open(OUT + "/audit_by_depth.json", "w"), indent=1)
