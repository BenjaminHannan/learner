"""Threshold sweep for rt-02g reader variants (dev + practice data only). tune = dev + odd practice; check = even practice.
  python scripts/claude_rt02g_sweep.py artifacts/claude-rt02g-20260926/dev V0 V1 V2"""
import json, sys
SP = sys.argv[1]
dev1 = [json.loads(l) for l in open(f"{SP}/reads_registered_prompt.jsonl")]


def split(k):
    if k < 55:
        return "tune"
    if k < 175:
        return "tune" if ((k - 55) // 3) % 2 else "check"
    return "tune" if (k - 175) % 2 else "check"


def counts(rows, thr):
    c = {s: {"pz": 0, "exact": 0, "wrong": 0, "neg": 0, "fire": 0} for s in ("tune", "check")}
    for r in rows:
        s = c[split(r["k"])]
        on = r["margin"] >= thr and r["got"] is not None
        if r["kind"] == "puzzle":
            s["pz"] += 1
            s["exact"] += int(on and r["got"] == r["want"])
            s["wrong"] += int(on and r["got"] != r["want"])
        else:
            s["neg"] += 1
            s["fire"] += int(on)
    return c


def rules():
    c = {s: {"pz": 0, "exact": 0, "neg": 0, "fire": 0} for s in ("tune", "check")}
    for k, r in enumerate(dev1):
        s = c[split(k)]
        if r["kind"] == "puzzle":
            s["pz"] += 1
            s["exact"] += int(r["rule"] == r["want"])
        else:
            s["neg"] += 1
            s["fire"] += int(r["rule"] is not None)
    return c


print("rules", rules())
for v in sys.argv[2:]:
    rows = [json.loads(l) for l in open(f"{SP}/margins_{v}.jsonl")]
    if v == "V2":                       # decision by V2's yes/no margin, reading from V1's forced extraction
        v1 = {r["k"]: r for r in (json.loads(l) for l in open(f"{SP}/margins_V1.jsonl"))}
        for r in rows:
            r["got"] = v1[r["k"]]["got"]
    print(v, len(rows))
    for thr in [x / 2 for x in range(-12, 17)]:
        c = counts(rows, thr)
        t, h = c["tune"], c["check"]
        print(f"  thr {thr:5.1f}  tune exact {t['exact']:3d}/{t['pz']} wrong {t['wrong']} fire {t['fire']:2d}/{t['neg']}"
              f"   check exact {h['exact']:3d}/{h['pz']} wrong {h['wrong']} fire {h['fire']:2d}/{h['neg']}")
