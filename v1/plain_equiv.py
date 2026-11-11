"""Check that the plain baseline scores exactly D's questions: for `dev` and `validation`, the question ids enumerated by
v1.plain_baseline (step1.read_questions over the shard files) equal, in order, the question ids of D's own caches
(v1.dtrain.open_data -> premonition.data), and the counts equal PREREG's (42,653 dev, 8,675 validation) when --expect is given.
  python -m v1.plain_equiv --root <v1village> [--expect]       (never reads `test`)"""
import argparse
from pathlib import Path

from v1 import dtrain, plain_baseline as pb

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--expect", action="store_true", help="also require the PREREG counts (full real data only)")
ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"))
a = ap.parse_args()
d = dtrain.open_data(Path(a.root), Path(a.tokenizer), workers=a.workers, log=lambda s: None)
ok = True
for name, cache in (("dev", d.dev), ("validation", d.validation)):
    mine = [q.id for q in pb.split_questions(Path(a.root), name)]
    same = mine == list(cache.question_ids)
    ok &= same and (not a.expect or len(mine) == pb.EXPECTED[name])
    print(f"{name}: plain {len(mine)} questions, D {len(cache.question_ids)}, ids equal in order: {same}"
          + (f", PREREG {pb.EXPECTED[name]}" if a.expect else ""))
raise SystemExit(0 if ok else 1)
