"""Show the grader separating a reference-solution transcript from an empty one (real API calls)."""
import json, sys
from grader import Grader
from sandbox import World

rows = [json.loads(l) for l in open("data/tasks_heldout.jsonl")][:int(sys.argv[1]) if len(sys.argv) > 1 else 3]
g = Grader("runs/grader_demo", max_usd=2.0, spot=float(sys.argv[2]) if len(sys.argv) > 2 else 0)
for t in rows:
    w, tr = World.from_json(t["state"]), [{"role": "user", "content": t["user"]}]
    for c in t["reference"]:
        tr += [{"role": "assistant", "content": "<tool_call>\n" + json.dumps(c) + "\n</tool_call>"}, {"role": "tool", "content": w.call(c["name"], c["arguments"])}]
    tr.append({"role": "assistant", "content": t["reference_reply"]})
    ref, emp = g.grade_one(t, tr), g.grade_one(t, [{"role": "user", "content": t["user"]}, {"role": "assistant", "content": ""}])
    print(t["id"], t["scenario"], "| reference:", ref[0], "| empty:", emp[0], "|", emp[1][:110])
print("spend", g.ledger.usd)
