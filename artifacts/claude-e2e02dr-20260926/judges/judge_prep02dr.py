"""0.2d-r judge packets for H1 (M2 asks) and H2 (M1 saves): X' and G mixed under neutral ids, seeds 3368 saves /
3369 asks as PASSMARKS-02dr.md fixes. Same packet shape as judge_prep02c.py. Prints counts only.
usage: judge_prep02dr.py BANK SCORE OUTDIR"""
import json, random, sys
from pathlib import Path
BANK, SCORE, OUT = map(Path, sys.argv[1:4])
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
turns = {(t["life_id"], t["turn_index"]): t for t in ld(BANK / "turns.jsonl")}
truth = ld(BANK / "truth.jsonl")
counts = {}
for kind, prefix, seed in (("saves", "S", 3368), ("asks", "Q", 3369)):
    rows = []
    for arm in ("X", "G"):
        for p in ld(SCORE / f"judge_{kind}_{arm}.jsonl"):
            p = dict(p); p["_arm"] = arm; rows.append(p)
    random.Random(seed).shuffle(rows)
    key = {}
    for i, p in enumerate(rows):
        p["id"] = f"{prefix}{i:04d}"; key[p["id"]] = {"arm": p.pop("_arm"), "life_id": p["life_id"], "turn_index": p["turn_index"]}
        t = turns.get((p["life_id"], p["turn_index"]))
        if kind == "asks":
            p["user_text"] = t["user_text"]
            p["truth_valid_now"] = [{k: f[k] for k in ("owner", "relation", "value")} for f in truth
                                    if f["life_id"] == p["life_id"] and f["taught_turn"] <= p["turn_index"]
                                    and (f.get("valid_until_turn") is None or f["valid_until_turn"] > p["turn_index"])]
        else:
            p["user_text"] = t["user_text"] if (t and p.get("row_kind") == "user") else None
    (OUT / "packets").mkdir(parents=True, exist_ok=True); (OUT / "keys").mkdir(parents=True, exist_ok=True)
    (OUT / "packets" / f"{kind}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (OUT / "keys" / f"key_{kind}.json").write_text(json.dumps(key), encoding="utf-8")
    counts[kind] = {a: sum(1 for v in key.values() if v["arm"] == a) for a in ("X", "G")}
print(json.dumps(counts))
