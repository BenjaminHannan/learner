#!/usr/bin/env python3
"""Seal the uncle's questions: split one-per-line, keep text in a blind folder
OUTSIDE the repo, write only hashes to a manifest.

  python3 scripts/claude_dir_uncle_seal.py uncle_raw.txt [--out DIR] [--manifest PATH]
  python3 scripts/claude_dir_uncle_seal.py --verify BLIND_DIR MANIFEST
"""
import argparse, hashlib, json, os, stat, sys, time


def h(b):
    return hashlib.sha256(b).hexdigest()


def items_of(raw):
    return [l.strip() for l in raw.decode("utf-8").splitlines() if l.strip()]


def seal(a):
    raw = open(a.file, "rb").read()
    items = items_of(raw)
    stamp = time.strftime("%Y%m%d", time.gmtime())
    out = os.path.abspath(a.out or os.path.expanduser(f"~/premonition-blind/uncle-{stamp}"))
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if out == repo or out.startswith(repo + os.sep):
        sys.exit("blind folder must be outside the git repo")
    if os.path.exists(out):
        sys.exit(f"{out} exists; sealed sets are never overwritten (use a new --out)")
    os.makedirs(out, mode=0o700)
    manifest = {"n_items": len(items), "whole_file_sha256": h(raw),
                "sealed_utc": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
                "items": []}
    for i, t in enumerate(items, 1):
        name = f"Q{i:03d}.txt"
        p = os.path.join(out, name)
        with open(p, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(p, stat.S_IRUSR)
        manifest["items"].append({"id": name[:-4], "sha256": h(t.encode("utf-8"))})
    mpath = a.manifest or f"handoff/uncle-questions/manifest-{stamp}.json"
    os.makedirs(os.path.dirname(os.path.abspath(mpath)), exist_ok=True)
    json.dump(manifest, open(mpath, "w"), indent=1)
    print(f"sealed {len(items)} items into {out}\nmanifest (hashes only, safe to commit): {mpath}")


def verify(a):
    m = json.load(open(a.manifest))
    bad = 0
    for it in m["items"]:
        p = os.path.join(a.verify, it["id"] + ".txt")
        ok = os.path.exists(p) and h(open(p, "rb").read()) == it["sha256"]
        bad += not ok
    extra = set(os.listdir(a.verify)) - {it["id"] + ".txt" for it in m["items"]}
    print(f"checked {len(m['items'])} items: {len(m['items'])-bad} match, {bad} bad, {len(extra)} unexpected files")
    sys.exit(1 if bad or extra else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--manifest")
    ap.add_argument("--verify", metavar="BLIND_DIR")
    a = ap.parse_args()
    if a.verify:
        if not a.manifest and a.file:
            a.manifest = a.file
        verify(a)
    elif a.file:
        seal(a)
    else:
        ap.error("give a file to seal, or --verify BLIND_DIR MANIFEST")
