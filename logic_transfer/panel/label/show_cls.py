import json, os, sys, random
sys.path.insert(0, '.')
import rlib
ROWS = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/"
D = "perrow/"
want = sys.argv[1]; fn = sys.argv[2]; k = int(sys.argv[3])
rel = {"logic_train": "logic_train.jsonl", "placebo_train": "placebo_train.jsonl"}.get(fn, f"eval/{fn}.jsonl")
per = [json.loads(l) for l in open(D + fn + ".jsonl")]
sel = [p["i"] for p in per if (want == "incons" and p["cls"] == "inconsistent") or (want == "ent" and p["gold"] == "unknown" and p["cls"] in ("true", "false"))]
random.Random(3).shuffle(sel)
sel = set(sel[:k])
for i, line in enumerate(open(ROWS + rel)):
    if i in sel:
        r = json.loads(line)
        print(per[i]["id"], "gold", r["answer"], "classical", per[i]["cls"])
        print("  ", r["prompt"])
        print("  ", r["meta"]["program"])
