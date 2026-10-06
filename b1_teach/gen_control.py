"""B1 GEN (control arm): 200,000 question rows from round 6's generator, six practised kinds, --block-r6.

Round 6 ran: gen_english.make(n, 1000 + seed, "train", kinds=6, block_files=BLOCK_R6). One example carries 2 questions,
so 100,000 examples give 200,000 question rows. Output schema is the same flat schema TEACH uses (one question per row).
Usage: python3 gen_control.py --out DIR [--rows 200000] [--seed 5001]
"""
import argparse, json, hashlib
from pathlib import Path
import gen_english as GE

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--rows", type=int, default=200000)
ap.add_argument("--seed", type=int, default=5001)
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
ex = GE.make(a.rows // 2, a.seed, "train", kinds=6, block_files=GE.BLOCK_R6)
n = 0
with open(out / "gen_200k.jsonl", "w") as f:
    for e in ex:
        for qi, q in enumerate(e["questions"]):
            f.write(json.dumps({"id": f"{e['id']}-q{qi}", "kind": e["family"], "source_text": e["source_text"], "paraphrase": e["paraphrase"],
                                "question": q["question"], "type": q["type"], "canonical_answer": q["canonical_answer"],
                                "accepted_answers": q["accepted_answers"]}) + "\n"); n += 1
h = hashlib.sha256((out / "gen_200k.jsonl").read_bytes()).hexdigest()
(out / "gen_200k.meta.json").write_text(json.dumps({"rows": n, "examples": len(ex), "seed": a.seed, "kinds": 6, "block": list(GE.BLOCK_R6), "sha256": h}, indent=1))
print(n, "rows", h)
