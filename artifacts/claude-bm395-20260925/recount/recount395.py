"""bm-395 recount with the independent recount4 scorer (written blind for bm-390 from the LoCoMo repo's own code;
it never used scripts/claude_bm390_score.py). Recomputes E, E20, Rb2, Rb on categories 1-4 and E - Rb2 with a
paired bootstrap (numpy default_rng(390), 10,000). Counts and scores only.
  python recount395.py RUNDIR DATADIR
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "r4", os.path.join(HERE, "..", "..", "claude-bm390-20260925", "recount4", "recount.py"))
r4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r4)
runs, data = sys.argv[1], sys.argv[2]
conv = json.load(open(os.path.join(data, "locomo10.json")))
gold, order = {}, []
for d in conv:
    for i, qa in enumerate(d["qa"]):
        q = "%s#%d" % (d["sample_id"], i); gold[q] = (qa["category"], qa.get("answer")); order.append(q)
o14 = [q for q in order if gold[q][0] in (1, 2, 3, 4)]
per, out = {}, {}
for arm in ("E", "E20", "Rb2", "Rb"):
    rows = {json.loads(x)["qid"]: json.loads(x) for x in open(os.path.join(runs, "locomo_%s.jsonl" % arm))}
    assert set(rows) == set(order) and len(rows) == 1986, arm
    per[arm] = {q: r4.score_item(gold[q][0], r4.hf_clean(rows[q]["reply"]), gold[q][1]) for q in o14}
    out[arm] = {"n": len(o14), "f1x100": round(100 * float(np.mean([per[arm][q] for q in o14])), 2),
                "by_cat": {c: round(100 * float(np.mean([per[arm][q] for q in o14 if gold[q][0] == c])), 2)
                           for c in (1, 2, 3, 4)}}
def boot(a, b):
    d = np.array([per[a][q] - per[b][q] for q in o14])
    m = d[np.random.default_rng(390).integers(0, len(d), size=(10000, len(d)))].mean(1)
    return {"diff": round(100 * float(d.mean()), 2),
            "ci95": [round(100 * float(np.percentile(m, 2.5)), 2), round(100 * float(np.percentile(m, 97.5)), 2)]}
out["E-Rb2"] = boot("E", "Rb2"); out["E20-Rb2"] = boot("E20", "Rb2")
json.dump(out, open(os.path.join(HERE, "recount395.json"), "w"), indent=1)
print(json.dumps(out))
