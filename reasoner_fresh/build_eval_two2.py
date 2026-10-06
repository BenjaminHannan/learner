"""EVAL-TWO-v2: 96 two-step questions with the earlier eval wording + 96 held-out variants of table / question-first / distance structures. Fast lane."""
import json, random
from pathlib import Path
import gen, gen_two, gen_two2
H = Path(__file__).resolve().parent
T, Ho = gen.answer_split()
old = json.loads((H / "EVAL-TWO-v1.json").read_text())
rows = [dict(r, structure="old_frames", id="A-" + r["id"]) for r in old]
rng = random.Random(20261008)
ev = gen.load("templates_eval.json"); weak = gen_two2.weak_eval()
used = {(r["x"], r["y"], r["z"]) for r in old}
combos = [("ADD", "ADD"), ("ADD", "SUB"), ("SUB", "ADD"), ("SUB", "SUB")]
n = 0
for sname, frames in weak.items():
    for (o1, o2) in combos:
        fr = [f for f in frames if (f[0], f[1]) == (o1, o2)]
        for ans_cell, finals in (("unseen", set(Ho)), ("seen", set(T))):
            for k in range(4):
                while True:
                    x, y, z = (rng.randint(10, 99) for _ in range(3))
                    v = gen_two.ok_values(x, y, z, o1, o2)
                    if v and v[1] in finals and (x, y, z) not in used: break
                used.add((x, y, z))
                text = rng.choice(fr)[2].format(name=rng.choice(ev["names"]), noun=rng.choice(ev["nouns"]), x=x, y=y, z=z)
                rows.append({"id": f"B-{sname}-{o1}{o2}-{ans_cell}-{k}", "cell": f"{ans_cell}/two_step", "structure": sname, "steps": 2, "op1": o1, "op2": o2,
                             "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
(H / "EVAL-TWO-v2.json").write_text(json.dumps(rows, indent=1))
import collections
print(len(rows), collections.Counter(r["structure"] for r in rows), collections.Counter(r["cell"] for r in rows))
