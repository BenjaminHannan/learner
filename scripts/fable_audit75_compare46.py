"""Audit 75 part 3: compare Exp46 seed-4102 re-run against the registered JSON."""
import json
import sys

W = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"
orig = json.load(open(W + "/artifacts/fable-hardgate46-20260921/runs/hard-seed4102.json"))
new = json.load(open(W + "/artifacts/fable-audit75-20260921/rerun4102/hard-seed4102.json"))
SKIP = {"path", "seconds", "script_sha256"}
bad = 0
out = []
if len(orig["rows"]) != len(new["rows"]):
    out.append("ROW COUNT DIFFERS: %d vs %d" % (len(orig["rows"]), len(new["rows"])))
for o, n in zip(orig["rows"], new["rows"]):
    keys = (set(o) | set(n)) - SKIP
    for k in sorted(keys):
        if o.get(k) != n.get(k):
            bad += 1
            out.append("DIFF %s %s: orig=%s rerun=%s" % (o["word"], k, o.get(k), n.get(k)))
out.append("rows=%d differing fields (excl path/seconds/sha)=%d" % (len(orig["rows"]), bad))
out.append("Paudit75.1: " + ("TRUE - exact reproduction" if bad == 0 else "FALSE"))
sys.stdout.write("\n".join(out) + "\n")
