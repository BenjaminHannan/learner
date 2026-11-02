"""Seal dev episodes: python -m bensweek.seal wk09 wk10 (moves them into episodes/sealed.bin)."""
import json
import sys

from . import episodes as E


def seal(ids, dev_dir=None, sealed_path=None):
    dev_dir = dev_dir or E.DEV_DIR
    sealed_path = sealed_path or E.SEALED_PATH
    existing = {e["id"]: e for e in E.read_sealed(sealed_path)}
    files = []
    for i in ids:
        p = dev_dir / f"{i}.json"
        if not p.exists():
            raise SystemExit(f"no such dev episode: {p}")
        ep = json.loads(p.read_text())
        ep["split"] = "sealed"
        existing[ep["id"]] = ep
        files.append(p)
    sealed_path.write_text(E.encode_sealed([existing[k] for k in sorted(existing)]))
    for p in files:
        p.unlink()
    return sorted(existing)


def main(argv=None):
    ids = (argv if argv is not None else sys.argv[1:])
    if not ids:
        raise SystemExit("usage: python -m bensweek.seal wkNN [wkMM ...]")
    print("sealed episodes now:", ", ".join(seal(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
