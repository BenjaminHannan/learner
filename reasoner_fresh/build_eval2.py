"""Fresh eval form v2: new story STRUCTURES (templates_eval2.json). Same answer-split logic as gen.py."""
import json, random
from pathlib import Path
import gen
H = Path(__file__).resolve().parent
SEED2 = 20261006
T, Ho = gen.answer_split(); Ts, Hs = set(T), set(Ho)
ev = json.loads((H / "templates_eval2.json").read_text())
v1pairs = gen.eval_pair_set(gen.eval_form())
rng = random.Random(SEED2)
pairs = [(x, y) for x in range(gen.LO, gen.HI) for y in range(gen.LO, gen.HI) if gen.valid_pair(x, y) and (x, y) not in v1pairs]
unseen = [p for p in pairs if p[0] + p[1] in Hs and p[0] - p[1] in Hs]
seen = [p for p in pairs if p[0] + p[1] in Ts and p[0] - p[1] in Ts]
rng.shuffle(unseen); rng.shuffle(seen)
rows = []
for ans_cell, pool in (("unseen", unseen), ("seen", seen)):
    for k in range(48):
        x, y = pool.pop()
        fam = ev["families"][k % len(ev["families"])]
        st = random.Random(f"{SEED2}-{ans_cell}-{k}")
        name, name2 = st.sample(ev["names"], 2); noun = st.choice(ev["nouns"])
        cell = f"{ans_cell}/new_structure"
        for op in ("add", "sub"):
            rows.append({"id": f"{ans_cell}-new_structure-{k:02d}-{op}", "pair_id": f"{ans_cell}-new_structure-{k:02d}", "cell": cell,
                         "family": fam["id"], "op": op.upper(), "x": x, "y": y, "answer": x + y if op == "add" else x - y,
                         "text": fam[op].format(name=name, name2=name2, noun=noun, x=x, y=y)})
(H / "EVAL-FORM-v2.json").write_text(json.dumps(rows, indent=1))
print(len(rows), {c: sum(r["cell"] == c for r in rows) for c in {r["cell"] for r in rows}})
