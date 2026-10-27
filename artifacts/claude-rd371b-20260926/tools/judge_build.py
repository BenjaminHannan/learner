"""build judge_in (union of distinct notes per turn) from dialogs + drafts; optional shards. Counts only."""
import json, sys
from collections import Counter
dialogs, drafts, out = sys.argv[1], sys.argv[2], sys.argv[3]
shards = int(sys.argv[4]) if len(sys.argv) > 4 else 1
D = [json.loads(l) for l in open(dialogs, encoding="utf-8") if l.strip()]
N = {}
c = Counter()
for l in open(drafts, encoding="utf-8"):
    if not l.strip():
        continue
    r = json.loads(l)
    c["draft:" + r["draft"]] += 1
    lst = N.setdefault((r["dialog"], int(r["t"])), [])
    for n in r.get("notes") or []:
        key = " ".join(n["text"].split()).lower()
        if key not in {" ".join(x["text"].split()).lower() for x in lst}:
            lst.append(n)
        else:
            c["dup"] += 1
for d in D:
    for tr in d["turns"]:
        if (d["dialog"], int(tr["t"])) in N:
            tr["notes"] = N[(d["dialog"], int(tr["t"]))]
            c["notes"] += len(tr["notes"])
            c["turns"] += 1
if shards == 1:
    open(out, "w", encoding="utf-8").write("".join(json.dumps(d) + "\n" for d in D))
else:
    for i in range(shards):
        part = D[i::shards]
        open(f"{out}.{i}", "w", encoding="utf-8").write("".join(json.dumps(d) + "\n" for d in part))
        c[f"shard{i}_notes"] = sum(len(t.get("notes") or []) for d in part for t in d["turns"])
    open(out, "w", encoding="utf-8").write("".join(json.dumps(d) + "\n" for d in D))
print(json.dumps(dict(c)))
