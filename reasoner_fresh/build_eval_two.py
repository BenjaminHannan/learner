"""Held-out two-step eval (fast lane: simple held-out split, no authored/sealed form). Eval wording = gen_two EV_* frames."""
import json, random
from pathlib import Path
import gen, gen_two
H = Path(__file__).resolve().parent
T, Ho = gen.answer_split()
rng = random.Random(20261007)
combos = [("ADD", "ADD"), ("ADD", "SUB"), ("SUB", "ADD"), ("SUB", "SUB")]
fr = {c: [f for f in gen_two.frames("eval") if (f[0], f[1]) == c] for c in combos}
rows, used = [], set()
for cell, finals in (("unseen", set(Ho)), ("seen", set(T))):
    for k in range(48):
        o1, o2 = combos[k % 4]
        while True:
            x, y, z = (rng.randint(10, 99) for _ in range(3))
            v = gen_two.ok_values(x, y, z, o1, o2)
            if v and v[1] in finals and (x, y, z) not in used:
                break
        used.add((x, y, z))
        text = rng.choice(fr[(o1, o2)])[2].format(noun=rng.choice(gen.load("templates_eval.json")["nouns"]), place=rng.choice(gen_two.EV_PLACES), name="", x=x, y=y, z=z)
        rows.append({"id": f"two-{cell}-{k:02d}", "cell": f"{cell}/two_step", "steps": 2, "op1": o1, "op2": o2, "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
(H / "EVAL-TWO-v1.json").write_text(json.dumps(rows, indent=1))
print(len(rows), rows[0]["text"], rows[0]["answer"])
