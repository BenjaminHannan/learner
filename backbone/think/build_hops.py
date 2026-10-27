"""The "hops" bed (PREREG-think2 Addendum G): a clean serial-depth task for testing loops, kept separate from village.
python3 backbone/think/build_hops.py OUT_DIR

Each row is a shuffled list of LINES fact lines and one question, "Where is the {object}?". The object sits inside a container, which sits
inside another, and so on, until the last container sits at a place. depth = the number of lines on that chain. At depth 1: "The key is at the
mill." The answer is the place's name, e.g. "mill". Every row holds CHAINS chains: the query chain and CHAINS - 1 distractor chains built the
same way, whose lengths (1 to MAX_DEPTH each) are drawn until the row has LINES lines in all. So the line count, the number of chains, the
number of places and the answer form do not depend on depth, and the prompt length barely does. What does depend on depth: the number of
lines the model must follow, and (weakly) the distractor chains' mean length, which is (LINES - depth) / (CHAINS - 1). Every name is one
Qwen3.5 token after a space (checked by the tests). The answer and each step on the way are therefore one token each.

Each name is the located item (the thing said to be inside or at something) of at most one line per row, so the chain from the object is
unique. Each line uses one of two phrasings for its relation, chosen at random independently of depth. The CHAINS places of a row are all
different, so each is named once: counting place names gives nothing away, and naming a random place of the row is right 1 / CHAINS of the time
at every depth (the floor).
hops_path = the names reached after hop 1, 2, ..., depth (the containers, then the place). Arm hloops is trained to name hop k after loop k.

Splits use independent seeds; row i of a split is built with Random(f"{split}:{seed}:{i}"):
  train       TRAIN_N rows, depths TRAIN_DEPTHS, equal shares (enough that no arm, at up to 8,000 steps of 16 rows, sees a row twice)
  dev         DEV_N rows, depths TRAIN_DEPTHS (the training-time check set)
  validation  VAL_PER_DEPTH rows at each depth 1..MAX_DEPTH (all decisions read this split)
  fresh       VAL_PER_DEPTH rows at each depth 1..MAX_DEPTH, seed + 1: scored only for final claims on an arm that already passed on validation
Rows: {id, split, depth, bank, template, context, question, answer, steps, steps_src, hops_path}. steps = the chain lines in order.
Writes OUT/{train,dev,validation,fresh}.jsonl and OUT/HOPS_REPORT.json (counts and the sha256 of every file).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

LINES = 32
CHAINS = 7
MAX_DEPTH = 10
TRAIN_DEPTHS = (1, 2, 3, 4)
TRAIN_N, DEV_N, VAL_PER_DEPTH = 128000, 1000, 400
SEED = 0

OBJECTS = ("key", "coin", "ring", "spoon", "whistle", "bell", "comb", "button", "marble", "pen", "pencil", "fork", "knife", "needle", "pin",
           "watch", "phone", "card", "ticket", "stone", "feather", "leaf", "candle", "match", "nail", "screw", "bolt", "badge", "medal", "token",
           "gem", "pearl", "ruby", "bead", "dice", "chip", "clip")
BOXES = ("box", "jar", "bag", "sack", "crate", "chest", "basket", "tin", "pot", "cup", "bowl", "case", "pouch", "purse", "vase", "bucket",
         "barrel", "drawer", "trunk", "cabinet", "closet", "shelf", "locker", "safe", "bin", "tub", "kettle", "pan", "jug", "bottle", "flask",
         "carton", "packet", "envelope", "folder", "wallet", "backpack", "suitcase", "cage", "urn", "tray", "dish", "mug", "pitcher", "kit",
         "tote", "sock", "boot", "shoe", "hat", "glove", "pocket", "coat", "basin", "sink", "oven", "stove", "crib", "cart", "wagon", "boat",
         "sled", "canoe", "nest", "hive", "tube", "vault", "tank", "pipe", "keg", "bundle", "parcel", "package", "capsule", "pod", "drum",
         "skillet", "wok")
PLACES = ("mill", "bakery", "harbour", "cave", "hut", "pond", "school", "market", "chapel", "forge", "barn", "bridge", "tower", "garden",
          "dairy", "square", "library", "stable", "inn", "beach", "quarry", "farm", "field", "river", "lake", "hill", "castle", "church", "shop",
          "hall", "park", "port", "dock", "gate", "road", "yard", "store", "camp", "office", "station", "temple", "palace", "village", "town",
          "city", "island", "forest", "desert", "valley")
IN_FORMS = ("The {a} is inside the {b}.", "The {b} holds the {a}.")
AT_FORMS = ("The {a} is at the {p}.", "The {a} sits by the {p}.")


def chain_lines(rng, obj, boxes, place):
    """The lines of one chain, in order from the object to the place: obj in boxes[0], boxes[0] in boxes[1], ..., boxes[-1] at place."""
    path = [obj, *boxes]
    lines = [rng.choice(IN_FORMS).format(a=a, b=b) for a, b in zip(path, path[1:])]
    return lines + [rng.choice(AT_FORMS).format(a=path[-1], p=place)]


def chain_lens(rng, depth, lines=LINES, max_depth=MAX_DEPTH):
    """[depth, then CHAINS - 1 distractor lengths]: the distractors are drawn from U{1..max_depth} until the row has `lines` lines in all."""
    while True:
        lens = [rng.randint(1, max_depth) for _ in range(CHAINS - 1)]
        if sum(lens) == lines - depth:
            return [depth, *lens]


def make_row(split, seed, i, depth, lines=LINES, max_depth=MAX_DEPTH):
    """One row: a depth-`depth` query chain plus CHAINS - 1 distractor chains, `lines` lines in all, shuffled; every chain ends at its own place.
    lines and max_depth default to the Addendum G bed; mac_laps.py (Addendum H) builds a deeper one."""
    assert 1 <= depth <= max_depth and CHAINS - 1 <= lines - depth <= (CHAINS - 1) * max_depth and lines - CHAINS <= len(BOXES)
    rng = random.Random(f"{split}:{seed}:{i}")
    objs, boxes = list(OBJECTS), list(BOXES)
    rng.shuffle(objs)
    rng.shuffle(boxes)
    chains = []
    for k, place in zip(chain_lens(rng, depth, lines, max_depth), rng.sample(PLACES, CHAINS)):
        obj, bx = objs.pop(), [boxes.pop() for _ in range(k - 1)]
        chains.append((obj, bx, place, chain_lines(rng, obj, bx, place)))
    lines = [ln for *_, c in chains for ln in c]
    rng.shuffle(lines)
    obj, bx, place, steps = chains[0]
    return dict(id=f"hops-{split}-{i}", split=split, depth=depth, bank="hops", template="hops-1",
                context="\n".join(f"[world] {ln}" for ln in lines), question=f"[question] Where is the {obj}?", answer=place,
                steps=[f"[world] {ln}" for ln in steps], steps_src="chain", hops_path=[*bx, place])


def build(split, seed=SEED):
    if split == "train":
        ds = [TRAIN_DEPTHS[i % len(TRAIN_DEPTHS)] for i in range(TRAIN_N)]
    elif split == "dev":
        ds = [TRAIN_DEPTHS[i % len(TRAIN_DEPTHS)] for i in range(DEV_N)]
    else:
        ds = [d for d in range(1, MAX_DEPTH + 1) for _ in range(VAL_PER_DEPTH)]
    rows = [make_row(split, seed, i, d) for i, d in enumerate(ds)]
    random.Random(f"order:{split}:{seed}").shuffle(rows)
    return rows


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report = dict(lines=LINES, chains=CHAINS, max_depth=MAX_DEPTH, train_depths=list(TRAIN_DEPTHS), seed=SEED, files={})
    for split in ("train", "dev", "validation", "fresh"):
        rows = build(split, SEED + (1 if split == "fresh" else 0))
        p = out / f"{split}.jsonl"
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        by = {}
        for r in rows:
            by[str(r["depth"])] = by.get(str(r["depth"]), 0) + 1
        report["files"][split] = dict(n=len(rows), by_depth=dict(sorted(by.items())), sha256=sha(p))
    (out / "HOPS_REPORT.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
