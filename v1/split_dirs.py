"""Arrange a v1/build_data.py output into the training layout without copying data.
Usage: python3 v1/split_dirs.py BUILD_DIR ROOT_DIR
  ROOT/train = shards 0-379 of the build's train split, ROOT/dev = shards 380-399, ROOT/validation, ROOT/test (sealed) = links.
"""
import json, os, re, sys
from pathlib import Path

DEV_FIRST = 380


def main():
    build, root = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    for name in ("train", "dev", "validation", "test"):
        (root / name).mkdir(parents=True, exist_ok=True)
    for p in sorted((build / "train").iterdir()):
        m = re.match(r"shard-(\d+)\.", p.name)
        if m:
            dest = root / ("dev" if int(m.group(1)) >= DEV_FIRST else "train") / p.name
        else:
            continue
        if not dest.exists():
            os.symlink(p, dest)
    for split in ("validation", "test"):
        for p in sorted((build / split).iterdir()):
            dest = root / split / p.name
            if not dest.exists():
                os.symlink(p, dest)
    for name in ("train", "dev"):                # manifests: keep the build's train manifest for provenance
        src = build / "train" / "manifest.json"
        (root / name / "manifest.json").write_text(src.read_text())
    print("ok", {n: len(list((root / n).glob("shard-*.txt"))) for n in ("train", "dev", "validation", "test")})


if __name__ == "__main__":
    main()
