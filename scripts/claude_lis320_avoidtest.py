#!/usr/bin/env python3
"""lis-320: hashed avoid list of every capitalised word in the TEST-ONLY panels (reading thread, 2026-09-26).

The lis-320 seeder must never reuse a name from a sealed test panel, but no one may read those panels. This script reads
them itself and writes only sha256 hashes of the lowercased words (one per line, sorted). It prints counts only.
claude_lis320_seed.py --avoid-hashes FILE then skips any generated name whose words hash into the list.

python3 claude_lis320_avoidtest.py --dirs DIR [DIR ...] --out avoid_test.sha256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CAP = re.compile(r"\b[A-Z][a-z]{2,}\b")


def h(w):
    return hashlib.sha256(w.lower().encode("utf-8")).hexdigest()


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    words, files, bad = set(), 0, 0
    for d in a.dirs:
        for p in sorted(Path(d).rglob("*.jsonl")):
            files += 1
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    obj = json.loads(line)
                except ValueError:
                    bad += 1
                    continue
                for s in strings(obj):
                    words.update(w.lower() for w in CAP.findall(s))
    Path(a.out).write_text("".join(x + "\n" for x in sorted(map(h, words))), encoding="utf-8")
    print(json.dumps({"dirs": len(a.dirs), "files": files, "unparsed_lines": bad, "hashes": len(words)}))


if __name__ == "__main__":
    main()
