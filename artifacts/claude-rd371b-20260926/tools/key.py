"""key from two blind judge outputs: both ok -> ok, both unsupported -> unsupported, else excluded. Counts only."""
import json, sys
from collections import Counter
jin, a, b, out = sys.argv[1:5]
K = {r["dialog"]: r["kind"] for r in map(json.loads, open(jin, encoding="utf-8"))}
A = {(r["dialog"], int(r["t"])): r["verdicts"] for r in map(json.loads, open(a, encoding="utf-8"))}
B = {(r["dialog"], int(r["t"])): r["verdicts"] for r in map(json.loads, open(b, encoding="utf-8"))}
c = Counter(); rows = []
for d in map(json.loads, open(jin, encoding="utf-8")):
    for t in d["turns"]:
        ns = t.get("notes") or []
        if not ns:
            continue
        va, vb = A[(d["dialog"], t["t"])], B[(d["dialog"], t["t"])]
        assert len(va) == len(vb) == len(ns)
        for k, (x, y) in enumerate(zip(va, vb)):
            lab = x if x == y and x in ("ok", "unsupported") else "excluded"
            c[f"{d['kind']}:{lab}"] += 1; c["agree" if x == y else "disagree"] += 1
            rows.append({"dialog": d["dialog"], "t": t["t"], "k": k, "kind": d["kind"], "label": lab})
open(out, "w", encoding="utf-8").write("".join(json.dumps(r) + "\n" for r in rows))
print(json.dumps(dict(c)))
