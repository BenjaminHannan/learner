"""Build the probe rows: village validation shard 0 (no train or test data), depth 2-4, short 'the X' answers,
plus the story lines each answer rests on (the generator's evidence_text_lines). Usage: python3 make_rows.py OUT_DIR"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "backbone")]
import build_data as B  # noqa: E402

out = Path(sys.argv[1])
B._init()
B.make_shard(("validation", 0, str(out / "vshard")))
rows = B.shard_rows("validation", 0, str(out / "vshard"))
json.dump(rows[:400], open(out / "vrows.json", "w"))
lines = open(out / "vshard/shard-00000.txt").read().split("\n")
ev = {q["id"]: q for q in map(json.loads, open(out / "vshard/shard-00000.jsonl")) if "evidence" in q}
sel = [r for r in rows[:400] if 2 <= r["depth"] <= 4 and r["answer"].startswith("the ") and len(r["answer"].split()) <= 3][:24]
json.dump([{**r, "evidence_lines": [lines[i] for i in sorted(ev[r["id"]]["evidence_text_lines"])]} for r in sel],
          open(out / "ev_rows.json", "w"))
