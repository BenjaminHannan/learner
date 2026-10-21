"""On-box data build for Gate S (a deterministic SUBSET of the committed build): train shards 0..N-1, dev shards DEV0..DEV0+M-1, and
the `validation` split. Every file is checked against design/v1/data/village-SHA256SUMS.txt (the full build's hashes), so the subset is
byte-identical to the corresponding part of the full data. The sealed `test` split is never built here.
  python -m v1.box_build OUT_ROOT [--train-shards 48] [--dev-shards 4] [--workers 8]
Layout: OUT_ROOT/{train,dev,validation}/shard-*.txt|jsonl + manifest.json (the layout v1.dtrain.open_data expects)."""
import argparse, hashlib, sys
from pathlib import Path

DEV0 = 380
PER = 250


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--train-shards", type=int, default=48)
    ap.add_argument("--dev-shards", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--sums", default=str(Path(__file__).resolve().parent.parent / "design/v1/data/village-SHA256SUMS.txt"))
    a = ap.parse_args(argv)
    from learnlab.village import shards as S
    out = Path(a.out)
    build = out / "_build"
    want = {}
    for line in open(a.sums):
        d, rel = line.split()
        want[rel] = d
    S.write_shards("train", a.train_shards * PER, build, a.workers, seed=0, visits_per_shard=PER, verbose=True)
    S.write_shards("validation", 1000, build, 1, seed=0, visits_per_shard=PER, verbose=False)
    cfg = {"split": "train", "n_visits": 100_000, "seed": 0, "visits_per_shard": PER, "generator": S.GENERATOR, "families": S.FAMILIES,
           "names": S.NAMES, "patterns": None, "tokenizer": None, "window_chars": S.WINDOW_CHARS, "audit_every": S.AUDIT_EVERY}
    S._setup(cfg)
    for k in range(DEV0, DEV0 + a.dev_shards):
        S._make_shard(("train", k, k * PER, (k + 1) * PER, str(build / "train")))
    bad = []
    for split in ("train", "validation"):
        for p in sorted((build / split).iterdir()):
            if p.name.startswith("shard-"):
                if want.get(f"{split}/{p.name}") != sha(p):
                    bad.append(f"{split}/{p.name}")
    if bad:
        sys.exit(f"HASH MISMATCH against the committed build: {bad[:5]} (+{max(len(bad) - 5, 0)})")
    for name in ("train", "dev", "validation"):
        (out / name).mkdir(parents=True, exist_ok=True)
    import os, re
    for p in sorted((build / "train").iterdir()):
        m = re.match(r"shard-(\d+)\.", p.name)
        if m:
            os.link(p, out / ("dev" if int(m.group(1)) >= DEV0 else "train") / p.name)
    for p in sorted((build / "validation").iterdir()):
        if p.name.startswith("shard-"):
            os.link(p, out / "validation" / p.name)
    for name in ("train", "dev"):
        (out / name / "manifest.json").write_text((build / "train" / "manifest.json").read_text())
    (out / "validation" / "manifest.json").write_text((build / "validation" / "manifest.json").read_text())
    print("BOX_BUILD_OK", {n: len(list((out / n).glob("shard-*.txt"))) for n in ("train", "dev", "validation")})


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
