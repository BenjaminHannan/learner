"""R0: regenerate the village DEV (train shards 380-399), `validation`, and a small TRAIN subset (name detector) with the v1 generator (seed 0, 250 visits/shard).
Output layout = v1.split_dirs root (train/ dev/ validation/). Deterministic per (split, index); same bytes as v1/build_data.py would write."""
import json, multiprocessing, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from learnlab.village import shards as S

def main(root, n_train_shards=40, workers=2):
    root = Path(root)
    cfg = {"split": "train", "n_visits": 0, "seed": 0, "visits_per_shard": 250, "generator": S.GENERATOR, "families": S.FAMILIES,
           "names": S.NAMES, "patterns": None, "tokenizer": None, "window_chars": S.WINDOW_CHARS, "audit_every": S.AUDIT_EVERY}
    tasks = []
    for name, split, shard_ids in (("train", "train", range(n_train_shards)), ("dev", "train", range(380, 400)), ("validation", "validation", range(4))):
        d = root / name; d.mkdir(parents=True, exist_ok=True)
        S._setup(cfg | {"split": split})
        man = {"split": split, "patterns": S._STATE["source"].version}
        (d / "manifest.json").write_text(json.dumps(man))
        for k in shard_ids:
            idx = k  # shard number inside this directory keeps the build's number
            if not (d / f"shard-{k:05d}.txt").exists():
                tasks.append((split, k, k * 250, k * 250 + 250, str(d)))
    t = time.time()
    with multiprocessing.get_context("spawn").Pool(workers, initializer=S._worker_init, initargs=(cfg,)) as p:
        for r in p.imap_unordered(S._make_shard, tasks):
            print(r["shard"], round(time.time() - t), flush=True)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 40)
