"""Build the corpus: python -m skills_curriculum.build --out DIR --train 200000 --dev-per-cell 40 --seed 1

Deterministic: same arguments give byte-identical files (sha256 in manifest.json).
train.jsonl        ordered easy to hard in 8 stages; stage s mixes 50% newest level, 50% review of earlier levels
                   (stage 8 is a uniform mix). Every row is hold-out clean (no held-out answer, frame, vocab, variant, family).
dev/<kind>.jsonl   isolated shifts, one kind of hold-out each, per family: answer | frame | vocab | variant | family
dev/in_dist.jsonl  fresh rows built the same way as train (new prompts), for fit checks
No prompt appears twice in train, and no dev prompt appears in train.
"""
import argparse
import collections
import hashlib
import json
import os
import random

from . import skills  # noqa: F401  (registers families)
from .core import FAMILIES, make_item, MAX_TOKENS_EST, SPLIT_SEED, ANSWER_FRAC, FRAME_FRAC, VOCAB_FRAC
from . import verify

DIFF_WEIGHTS = (0.4, 0.4, 0.2)
LEVELS = sorted({f["level"] for f in FAMILIES.values()})


def train_families(level=None):
    return [f for f, v in sorted(FAMILIES.items()) if not v["heldout_family"] and (level is None or v["level"] == level)]


def _clean(it, kind):
    f = it["flags"]
    if it["est_tokens"] > MAX_TOKENS_EST:
        return False
    if kind == "train":
        return not any(f.values())
    if kind == "in_dist":
        return not any(f.values())
    if kind == "family":
        return f["family"] and not (f["answer"] or f["frame"] or f["vocab"] or f["variant"]) or f["family"]
    return f[kind] and not any(v for k, v in f.items() if k not in (kind, "family")) and not f["family"]


class Maker:
    """Draws items for one family under one namespace until it finds ones that pass; counts rejects."""

    def __init__(self, fid, ns, seed):
        self.fid, self.ns, self.seed, self.i = fid, ns, seed, 0
        self.rejected = 0
        self.rng = random.Random(f"{ns}|{seed}|{fid}")

    def next(self, kind, seen, give_up=20000):
        for _ in range(give_up):
            self.i += 1
            diff = self.rng.choices((0, 1, 2), DIFF_WEIGHTS)[0]
            it = make_item(self.fid, f"{self.ns}{self.seed}", self.i, diff)
            if not _clean(it, kind):
                self.rejected += 1
                continue
            if it["prompt"] in seen:
                self.rejected += 1
                continue
            return it
        return None


def build(out, n_train, dev_per_cell, seed, write=True):
    os.makedirs(os.path.join(out, "dev"), exist_ok=True)
    seen_train, seen_all = set(), set()
    stages = LEVELS + ["mix"]  # stages 1-8 each take 1/12 of the rows, stage 9 (uniform over everything) takes the other 4/12
    per_stage = n_train // 12
    makers = {f: Maker(f, "T", seed) for f in train_families()}
    rng = random.Random(f"order|{seed}")
    train_rows = []
    for si, L in enumerate(stages):
        last = si == len(stages) - 1
        newest = [] if last else train_families(L)
        review = [f for lv in LEVELS[:si] for f in train_families(lv)]
        for j in range(per_stage if not last else n_train - 8 * per_stage):
            if last or not review:
                pool = [f for lv in LEVELS[:si + 1] for f in train_families(lv)]
            else:
                pool = newest if rng.random() < 0.5 else review
            fid = rng.choice(pool)
            it = makers[fid].next("train", seen_train)
            if it is None:
                continue
            seen_train.add(it["prompt"])
            it["stage"] = si + 1
            train_rows.append(it)
    dev = {}
    dkinds = ["answer", "frame", "vocab", "variant"]
    for kind in dkinds:
        rows = []
        for fid in train_families():
            if kind == "answer" and not FAMILIES[fid]["answer_open"]:
                continue
            if kind == "variant" and len(FAMILIES[fid]["variants"]) < 3 and not FAMILIES[fid]["layout"]:
                continue
            m = Maker(fid, "D" + kind[0], seed)
            for _ in range(dev_per_cell):
                it = m.next(kind, seen_train)
                if it is None:
                    break
                seen_train.add(it["prompt"]) if False else None
                rows.append(it)
        dev[kind] = rows
    rows = []
    for fid in train_families():
        m = Maker(fid, "DI", seed)
        for _ in range(dev_per_cell):
            it = m.next("in_dist", seen_train)
            rows.append(it)
    dev["in_dist"] = rows
    rows = []
    for fid in sorted(f for f, v in FAMILIES.items() if v["heldout_family"]):
        m = Maker(fid, "DF", seed)
        for _ in range(dev_per_cell):
            it = m.next("family", seen_train)
            if it is None:
                break
            rows.append(it)
    dev["family"] = rows
    # no dev prompt may equal a train prompt, nor repeat inside dev
    train_prompts = {r["prompt"] for r in train_rows}
    for k in dev:
        dev[k] = [r for r in dev[k] if r["prompt"] not in train_prompts]
    man = _write(out, train_rows, dev) if write else None
    return train_rows, dev, man


def _dump(path, rows):
    h = hashlib.sha256()
    with open(path, "w") as f:
        for r in rows:
            line = json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n"
            f.write(line)
            h.update(line.encode())
    return h.hexdigest()


def _write(out, train_rows, dev):
    files = {"train.jsonl": _dump(os.path.join(out, "train.jsonl"), train_rows)}
    for k, rows in dev.items():
        files[f"dev/{k}.jsonl"] = _dump(os.path.join(out, "dev", f"{k}.jsonl"), rows)
    bad_total, bad_ex = 0, []
    for rows in [train_rows] + list(dev.values()):
        for r in rows:
            b = verify.check_item(r)
            if b:
                bad_total += 1
                bad_ex.append((r["id"], b[:2]))
    stats = collections.defaultdict(lambda: collections.Counter())
    for r in train_rows:
        stats[r["family"]]["train_rows"] += 1
    distinct_answers = collections.defaultdict(set)
    for r in train_rows:
        distinct_answers[r["family"]].add(r["answer"])
    man = {
        "split_seed": SPLIT_SEED, "answer_frac": ANSWER_FRAC, "frame_frac": FRAME_FRAC, "vocab_frac": VOCAB_FRAC,
        "max_tokens_est": MAX_TOKENS_EST, "files_sha256": files,
        "counts": {"train": len(train_rows), **{f"dev_{k}": len(v) for k, v in dev.items()}},
        "families": {f: {"level": v["level"], "doc": v["doc"], "variants": v["variants"], "heldout_family": v["heldout_family"],
                         "layout_varied": v["layout"], "parse_checked": f in verify.PARSERS,
                         "train_rows": stats[f]["train_rows"], "distinct_train_answers": len(distinct_answers[f])}
                     for f, v in sorted(FAMILIES.items())},
        "train_unique_prompts": len({r["prompt"] for r in train_rows}),
        "train_max_est_tokens": max(r["est_tokens"] for r in train_rows),
        "verify": {"rows_checked": len(train_rows) + sum(len(v) for v in dev.values()), "rows_failing": bad_total, "examples": bad_ex[:10]},
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    return man


def iter_train(seed, levels=None, weights=None):
    """Endless never-repeating training stream for on-the-fly use (no file needed). Hold-out clean."""
    fams = [f for f in train_families() if levels is None or FAMILIES[f]["level"] in levels]
    mk = {f: Maker(f, "S", seed) for f in fams}
    rng = random.Random(f"stream|{seed}")
    seen = set()
    while True:
        fid = rng.choices(fams, [weights.get(f, 1) for f in fams] if weights else None)[0]
        it = mk[fid].next("train", seen)
        if it:
            seen.add(it["prompt"])
            yield it


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", type=int, default=200000)
    ap.add_argument("--dev-per-cell", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--tokenizer", help="optional tokenizer.json (LFM2.5): add a real token-length report to the manifest")
    a = ap.parse_args()
    _, _, m = build(a.out, a.train, a.dev_per_cell, a.seed)
    if a.tokenizer:
        from tokenizers import Tokenizer
        tk = Tokenizer.from_file(a.tokenizer)
        mx = 0
        over = 0
        for fn in ["train.jsonl"] + [f"dev/{k}.jsonl" for k in ("answer", "frame", "vocab", "variant", "family", "in_dist")]:
            for line in open(os.path.join(a.out, fn)):
                n = len(tk.encode(json.loads(line)["prompt"], add_special_tokens=False).ids) + 1
                mx, over = max(mx, n), over + (n > 64)
        m["real_tokens"] = {"max_input_with_EOS": mx, "over_64": over}
        json.dump(m, open(os.path.join(a.out, "manifest.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps({"counts": m["counts"], "verify": m["verify"], "real_tokens": m.get("real_tokens")}))
