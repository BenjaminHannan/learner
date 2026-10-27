"""382b/383 M2 judge packets (month-end, 2026-09-26, after the run; adapted from judge_prep02c.py). Prints counts only.
Arms E (382b), R (383), G (control) and ER (report only) mixed under neutral ids; keys applied by script later.
usage: judge_prep382.py BANK SCORE OUTDIR"""
import json, random, sys
from pathlib import Path
BANK, SCORE, OUT = map(Path, sys.argv[1:4])
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
turns = {(t["life_id"], t["turn_index"]): t for t in ld(BANK / "turns.jsonl")}
truth = ld(BANK / "truth.jsonl")
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for arm in ("E", "G", "R", "ER"):
    for p in ld(SCORE / f"judge_asks_{arm}.jsonl"):
        p = dict(p); p["_arm"] = arm; rows.append(p)
random.Random(3824).shuffle(rows)
key = {}
for i, p in enumerate(rows):
    p["id"] = f"Q{i:04d}"; key[p["id"]] = p.pop("_arm")
    t = turns.get((p["life_id"], p["turn_index"]))
    p["user_text"] = t["user_text"]
    p["truth_valid_now"] = [{k: f[k] for k in ("owner", "relation", "value")} for f in truth
                            if f["life_id"] == p["life_id"] and f["taught_turn"] <= p["turn_index"]
                            and (f.get("valid_until_turn") is None or f["valid_until_turn"] > p["turn_index"])]
(OUT / "m2").mkdir(parents=True, exist_ok=True)
(OUT / "m2/asks.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
(OUT / "keys").mkdir(parents=True, exist_ok=True)
(OUT / "keys/key_asks.json").write_text(json.dumps(key), encoding="utf-8")
from collections import Counter
print(json.dumps({"asks": len(rows), "per_arm": Counter(key.values())}))
