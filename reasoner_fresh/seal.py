"""Build and seal the eval form, arm A pool and arm B generator spec before any training."""
import hashlib, json
from pathlib import Path
import gen
H = Path(__file__).resolve().parent
T, Ho = gen.answer_split()
form = gen.eval_form()
ex = gen.eval_pair_set(form)
pool = gen.pool_a(ex)
(H / "EVAL-FORM-v1.json").write_text(json.dumps(form, indent=1))
(H / "ARM-A-POOL-v1.json").write_text(json.dumps(pool, indent=1))
b0 = gen.stream_b(ex, 0, 2000)  # preview only; the full stream is regenerated from seed at train time
assert not (ex & {(r["x"], r["y"]) for r in pool}), "pool overlaps eval pairs"
assert all(r["answer"] in set(T) for r in pool)
assert len({r["text"] for r in form}) == len(form)
def fsha(p): return hashlib.sha256((H / p).read_bytes()).hexdigest()
seal = {"answers_train_T": T, "answers_heldout_H": Ho,
  "files": {p: fsha(p) for p in ["EVAL-FORM-v1.json", "ARM-A-POOL-v1.json", "templates_train.json", "templates_eval.json", "gen.py", "PASS-MARKS.md"]},
  "eval_cells": {c: sum(r["cell"] == c for r in form) for c in sorted({r["cell"] for r in form})}}
(H / "SEAL.json").write_text(json.dumps(seal, indent=1))
print(json.dumps(seal["eval_cells"]), "pool families", {f: sum(r['family']==f for r in pool) for f in {r['family'] for r in pool}})
print("T unused-in-pool answers:", len(set(T) - {r['answer'] for r in pool}))
