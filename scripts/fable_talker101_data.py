"""Exp 101 talker prep: carve a sealed 1% held-out val split from SimpleStories train.

Reads the 7 downloaded train parquets, selects 1% of global story indices with
numpy default_rng(101), writes the sorted index array + a JSON manifest with the
exact source URL / revision / licence / file hashes. No training happens here.
"""
import argparse, hashlib, json, os
import numpy as np

SRC_REV = "e63b8adc3b1a1bdc7cac5b500d150b71346b0628"
SRC_BASE = "https://huggingface.co/datasets/SimpleStories/SimpleStories"
SRC_LICENCE = "MIT (dataset card `license: mit`, tags include `license:mit`; verified 2026-09-22)"
FILES = [f"train-{i:05d}-of-00007.parquet" for i in range(7)]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/open/simplestories")
    ap.add_argument("--out-dir", default="artifacts/fable-talker101-20260921")
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--val-frac", type=float, default=0.01)
    args = ap.parse_args()

    try:
        import pyarrow.parquet as pq
    except ImportError as e:
        raise SystemExit("need pyarrow: uv run --offline --with pyarrow ...") from e

    counts, total = [], 0
    for f in FILES:
        n = pq.ParquetFile(os.path.join(args.data_dir, f)).metadata.num_rows
        counts.append(n)
        total += n
    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(total)
    n_val = int(total * args.val_frac)
    val_idx = np.sort(perm[:n_val].astype(np.int64))

    os.makedirs(args.out_dir, exist_ok=True)
    val_path = os.path.join(args.out_dir, "fable_talker101_val_idx.npy")
    np.save(val_path, val_idx)
    manifest = {
        "source_url": SRC_BASE,
        "revision_sha": SRC_REV,
        "licence": SRC_LICENCE,
        "files": [
            {"name": f, "sha256": sha256_file(os.path.join(args.data_dir, f)), "rows": n}
            for f, n in zip(FILES, counts)
        ],
        "total_train_rows": total,
        "val_frac": args.val_frac,
        "seed": args.seed,
        "n_val": int(n_val),
        "val_idx_sha256": sha256_file(val_path),
    }
    with open(os.path.join(args.out_dir, "fable_talker101_split_info.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({k: manifest[k] for k in
                      ("total_train_rows", "n_val", "seed", "val_idx_sha256", "revision_sha")}, indent=2))


if __name__ == "__main__":
    main()
