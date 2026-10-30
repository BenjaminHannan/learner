# Applies PREREG Z2/Z3 (amendments A, B) to stage-0 rows on the 120-question set; prints the Stage-1 retriever.
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
rows = [r for r in rows if r.get("in120")]
acc = {a: 100 * sum(r[a]["allhit"] for r in rows) / len(rows) for a in ("S0", "S1", "S2", "S3", "S4")}
pick = "S3" if acc["S3"] >= acc["S2"] + 3 else "S2"
if acc["S4"] >= max(acc["S2"], acc["S3"]) + 3: pick = "S4"
print(json.dumps({"n": len(rows), "allhit": {k: round(v, 1) for k, v in acc.items()}, "Z1_pass": acc["S2"] >= acc["S0"] + 10, "retriever": pick}), file=sys.stderr)
print(pick)
