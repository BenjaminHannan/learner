#!/usr/bin/env python3
"""WebRED (CC BY 4.0) -> frame records for ears rung 2 (design doc 47 §5), no TensorFlow.

Each TFRecord holds a tf.train.Example with: sentence (SUBJ{..}/OBJ{..} marked), relation_name,
relation_id, source_name, target_name, num_pos_raters, num_raters, url.  We strip the markers and
keep character spans, so the frame head learns to *point* at raw text.

    uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
        scripts/fable_webred_frames.py --out data/open/webred/frames

writes  frames/train.jsonl   (webred_21, positives + negatives, minus held-out relations)
        frames/dev.jsonl     (webred_5)
        frames/heldout.jsonl (webred_21 rows whose relation is in the 40 held-out relations)
        frames/relations.json (relation -> count, closed-list map, held-out list)
One JSON per line: {text, subj:[a,b], obj:[a,b] (first mention), subj_all, obj_all (every mention),
        relation, relation_id, positive, votes:[pos,n], subj_name, obj_name, split}
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import re
import struct

MARK = re.compile(r"(SUBJ|OBJ)\{([^}]*)\}")

# WebRED relation -> our closed list (design 43 / Exp 44 village relations).  Everything else stays open.
CLOSED_MAP = {
    "mother": "mother", "father": "father", "child": "child", "sibling": "sibling", "spouse": "spouse",
    "employer": "employer", "place of birth": "hometown", "educated at": "school",
}
N_HELDOUT = 40


def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s; s += 7
        if not c & 0x80:
            return r, i


def fields(b):
    i = 0
    while i < len(b):
        key, i = varint(b, i)
        f, w = key >> 3, key & 7
        if w == 0:
            v, i = varint(b, i)
        elif w == 2:
            n, i = varint(b, i); v = b[i:i + n]; i += n
        elif w == 1:
            v = b[i:i + 8]; i += 8
        elif w == 5:
            v = b[i:i + 4]; i += 4
        else:
            raise ValueError(w)
        yield f, w, v


def example(b):
    out = {}
    for f, _, v in fields(b):
        if f != 1:
            continue
        for f2, _, v2 in fields(v):
            name, vals = None, []
            for f3, _, v3 in fields(v2):
                if f3 == 1:
                    name = v3.decode()
                elif f3 == 2:
                    for f4, _, v4 in fields(v3):
                        if f4 == 1:
                            vals += [x.decode("utf-8", "replace") for f5, _, x in fields(v4) if f5 == 1]
                        elif f4 == 3:
                            for f5, w5, x in fields(v4):
                                if f5 != 1:
                                    continue
                                if w5 == 0:
                                    vals.append(x)
                                else:
                                    j = 0
                                    while j < len(x):
                                        y, j = varint(x, j); vals.append(y)
            out[name] = vals
    return out


def records(path):
    with open(path, "rb") as fh:
        while True:
            h = fh.read(8)
            if len(h) < 8:
                return
            n = struct.unpack("<Q", h)[0]; fh.read(4)
            yield fh.read(n); fh.read(4)


def strip_markers(sentence: str):
    """'a SUBJ{b} c OBJ{d}' -> ('a b c d', [(2,3)], [(6,7)]).  A quarter of WebRED rows mark an
    entity more than once (coreference: 'she', 'its'); every mention is kept, first one is canonical.
    None if either entity has no mention."""
    text, spans, last = [], {"SUBJ": [], "OBJ": []}, 0
    for m in MARK.finditer(sentence):
        text.append(sentence[last:m.start()])
        start = sum(len(t) for t in text)
        text.append(m.group(2))
        spans[m.group(1)].append((start, start + len(m.group(2))))
        last = m.end()
    text.append(sentence[last:])
    if not spans["SUBJ"] or not spans["OBJ"]:
        return None
    return "".join(text), spans["SUBJ"], spans["OBJ"]


def rows(path, split):
    for r in records(path):
        e = example(r)
        s = strip_markers(e["sentence"][0])
        if s is None:
            continue
        text, subj, obj = s
        pos, n = e["num_pos_raters"][0], e["num_raters"][0]
        yield {"text": text, "subj": list(subj[0]), "obj": list(obj[0]), "subj_all": [list(x) for x in subj],
               "obj_all": [list(x) for x in obj], "relation": e["relation_name"][0],
               "relation_id": e["relation_id"][0], "positive": pos / n > 0.5, "votes": [pos, n],
               "subj_name": e["source_name"][0], "obj_name": e["target_name"][0], "split": split}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/open/webred")
    ap.add_argument("--out", default="data/open/webred/frames")
    ap.add_argument("--seed", type=int, default=47)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    train = list(rows(os.path.join(a.src, "webred_21.tfrecord"), "train"))
    dev = list(rows(os.path.join(a.src, "webred_5.tfrecord"), "dev"))
    counts = collections.Counter(r["relation"] for r in train)
    # held-out relations: 40 mid-frequency relations (30..500 positive rows), never in the closed map,
    # so the held-out test has enough rows without gutting training
    pos_counts = collections.Counter(r["relation"] for r in train if r["positive"])
    eligible = sorted(rel for rel, c in pos_counts.items() if 30 <= c <= 500 and rel not in CLOSED_MAP)
    heldout = set(random.Random(a.seed).sample(eligible, N_HELDOUT))
    kept = [r for r in train if r["relation"] not in heldout]
    held = [r for r in train if r["relation"] in heldout]
    for name, data in (("train", kept), ("dev", dev), ("heldout", held)):
        with open(os.path.join(a.out, f"{name}.jsonl"), "w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{name}: {len(data):,} rows, {sum(r['positive'] for r in data):,} positive, "
              f"{len({r['relation'] for r in data})} relations")
    with open(os.path.join(a.out, "relations.json"), "w") as fh:
        json.dump({"counts": counts, "closed_map": CLOSED_MAP, "heldout": sorted(heldout),
                   "closed_rows_train": sum(r["relation"] in CLOSED_MAP for r in kept)}, fh, indent=1)
    print("closed-list rows in train:", sum(r["relation"] in CLOSED_MAP for r in kept),
          "| held-out relations:", len(heldout))


if __name__ == "__main__":
    main()
