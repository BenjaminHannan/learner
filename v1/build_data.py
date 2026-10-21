"""V1 village data build (deterministic). Usage: python3 v1/build_data.py OUT_DIR [workers]

Splits (learnlab.village.shards.write_shards, seed 0, 250 visits/shard):
  train       100,000 visits = 400 shards. Shards 0-379 are TRAIN (95,000 visits); shards 380-399 are DEV (5,000 visits, ~5%).
  validation  1,000 visits  : held out by whole families/names/templates (learnlab.splits); non-sealed, an early check.
  test        1,000 visits  : SEALED. Read once, only under the open-seal rule.
Writes OUT_DIR/SHA256SUMS.txt (every file) and OUT_DIR/SPLITS.json (per-split digest = sha256 of its sorted 'sha  relpath' lines).
"""
import hashlib, json, sys
from pathlib import Path

PER_SHARD, SEED = 250, 0
PLAN = {"train": 100_000, "validation": 1_000, "test": 1_000}
DEV_FIRST_SHARD = 380


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out = Path(sys.argv[1]).resolve()
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    from learnlab.village.shards import write_shards
    for split, n in PLAN.items():
        write_shards(split, n, out, workers, seed=SEED, visits_per_shard=PER_SHARD)
    lines, digest = [], {}
    for split in PLAN:
        part = []
        for p in sorted((out / split).iterdir()):
            part.append(f"{sha(p)}  {split}/{p.name}")
        lines += part
        digest[split] = hashlib.sha256("\n".join(part).encode()).hexdigest()
    shards = sorted((out / "train").glob("shard-*.txt"))
    digest["train_part"] = hashlib.sha256("\n".join(l for l in lines if l.split("  ")[1].startswith("train/") and int(l.split("shard-")[1][:5]) < DEV_FIRST_SHARD if "shard-" in l).encode()).hexdigest()
    digest["dev_part"] = hashlib.sha256("\n".join(l for l in lines if l.split("  ")[1].startswith("train/") and "shard-" in l and int(l.split("shard-")[1][:5]) >= DEV_FIRST_SHARD).encode()).hexdigest()
    (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    (out / "SPLITS.json").write_text(json.dumps({"seed": SEED, "visits_per_shard": PER_SHARD, "plan": PLAN, "train_shards": [0, DEV_FIRST_SHARD - 1],
                                                   "dev_shards": [DEV_FIRST_SHARD, len(shards) - 1], "sealed": "test", "digests": digest}, indent=1) + "\n")
    print(json.dumps(digest, indent=1))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
