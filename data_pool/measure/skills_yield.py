# Needs: git worktree of origin/claude/project-thread-y0sxwe at $SKILLS_REPO (skills_curriculum/). Run: python3 skills_yield.py 400000 out.json
"""Per-family unique-prompt yield of skills_curriculum (train-clean items only). Usage: skills_yield.py N OUT.json"""
import os, sys, json, random, re, collections, time
sys.path.insert(0, os.environ.get('SKILLS_REPO','/tmp/sk'))
from skills_curriculum import skills  # noqa
from skills_curriculum.core import FAMILIES, make_item, MAX_TOKENS_EST
from skills_curriculum.build import train_families, DIFF_WEIGHTS
from multiprocessing import Pool
N = int(sys.argv[1])
def one(fid):
    rng = random.Random(f"yield|{fid}")
    seen = set(); shape = set(); kept = 0; chars = 0; rej = 0; coll = 0
    t = time.time(); curve = {}
    checkpoints = {1000, 5000, 20000, 50000, 100000, 200000, 400000}
    for i in range(1, N + 1):
        diff = rng.choices((0, 1, 2), DIFF_WEIGHTS)[0]
        it = make_item(fid, "Y1", i, diff)
        if it["est_tokens"] > MAX_TOKENS_EST or any(it["flags"].values()):
            rej += 1; continue
        p = it["prompt"]; kept += 1
        if p in seen: coll += 1
        else: seen.add(p); shape.add(re.sub(r"\d+", "#", p)); chars += len(p) + len(it["answer"])
        if kept in checkpoints: curve[kept] = [len(seen), len(shape)]
    return fid, dict(level=FAMILIES[fid]["level"], drawn=N, kept=kept, rejected=rej, unique=len(seen), shape_unique=len(shape), dup=coll,
                     chars_unique=chars, curve=curve, sec=round(time.time() - t, 1))
if __name__ == "__main__":
    with Pool(4) as p:
        res = dict(p.map(one, train_families(), chunksize=1))
    json.dump(res, open(sys.argv[2], "w"), indent=1)
    print("done", len(res))
