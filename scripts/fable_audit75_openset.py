"""Audit 75 part 2: check open-set descriptive numbers in Exp29 readouts."""
import json
import sys

W = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"
claims = {"F": [0.59, 0.57, 0.60], "F6": [0.54, 0.58, 0.56], "L": [0.66, 0.59, 0.67]}
out = []
for arm, vals in claims.items():
    for i, seed in enumerate(["2106", "2107", "2108"]):
        d = json.load(open("%s/artifacts/fable-newnames29-20260921/readouts/%s-%s.json" % (W, arm, seed)))
        b = d.get("openset_B")
        out.append("%s-%s openset_B=%s (RESULTS claims %s) keys=%s" % (
            arm, seed, b, vals[i], sorted(d.keys())))
sys.stdout.write("\n".join(out) + "\n")
