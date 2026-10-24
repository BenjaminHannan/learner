"""Count-handoff items: a village visit that ends in a Q5 count question (true answer c) + a creative few-shot rule prompt whose query number is hidden.

Item = (village visit, one Q5 count question of it, c).  The creative prompt is "Examples: 4 -> 20; 5 -> 24; 16 -> 68. Now @ -> ?" and the target is
f(c), f = the prompt's rule.  The creative model cannot know c from its prompt; only D (which read the story) can.

Two independent halves:
  * VillageItems     - which (visit, question) pairs exist in a split and their true c (from the shard jsonl: bank q.count_at / q.count_held, knowable).
  * make_prompt      - the creative side: a rule drawn from creative.rules_real (same generator, same rule families, same domain), a hidden query.
Splits: train = village train shards 0-379, dev = shards 380-399, validation = held-out families.  The sealed `test` split and creative/data/c2/test.jsonl
are never opened here (open_village refuses the name).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional, Sequence

import torch

from creative import fewshot, rules_real as R
from creative.programs import register_targets, train_form
from custom_io.models import progparse as pp

PLACEHOLDER = "@"
CMAX = 20                       # classes 0..CMAX (the village oracle writes numbers "zero".."twenty")
COUNT_BANKS = ("q.count_at", "q.count_held")
NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
SEALED = ("test",)
TAUGHT = ("add", "mult")        # the creative model's practised kinds (creative/rules_real.PRACTISED)


def word_to_int(text: str) -> int:
    """'four' -> 4; anything else ('not told', '<ent3>', '') -> -1."""
    return NUMBER_WORDS.get(text.strip().lower(), -1)


# --------------------------------------------------------------------------- village side
@dataclass
class VillageItems:
    split: str
    cache: Any                       # premonition.data.VisitCache
    q: torch.Tensor                  # [N] long: global question index in the cache
    visit: torch.Tensor              # [N] long: visit index in the cache
    c: torch.Tensor                  # [N] long: true count
    qid: list                        # [N] question ids ("train-12:q4")
    bank: list                       # [N] q.count_at / q.count_held

    def __len__(self) -> int:
        return int(self.c.numel())

    def take(self, idx: Sequence[int]) -> "VillageItems":
        t = torch.as_tensor(list(idx), dtype=torch.long)
        return replace(self, q=self.q[t], visit=self.visit[t], c=self.c[t], qid=[self.qid[i] for i in t.tolist()], bank=[self.bank[i] for i in t.tolist()])


def _shard_questions(split_dir: Path, shard_names: Sequence[str]) -> dict:
    out = {}
    for name in shard_names:
        meta = (split_dir / name).with_suffix(".jsonl")
        with open(meta, encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if row.get("kind") == "question" and row.get("bank") in COUNT_BANKS:
                    out[row["id"]] = (row["bank"], row["answer"], bool(row.get("knowable", True)))
    return out


def village_items(cache, split_dir: Path, split: str) -> VillageItems:
    """Q5 count questions of `cache` whose answer is a number word and that are knowable (a 'not told' count is not an item)."""
    if split in SEALED:
        raise ValueError("the sealed split is never read here")
    info = _shard_questions(Path(split_dir), cache.info["shards"])
    qs, vs, cs, ids, banks = [], [], [], [], []
    for v in range(len(cache)):
        for q in cache.questions_of(v):
            hit = info.get(cache.question_ids[q])
            if hit is None or not hit[2] or word_to_int(hit[1]) < 0:
                continue
            qs.append(q); vs.append(v); cs.append(word_to_int(hit[1])); ids.append(cache.question_ids[q]); banks.append(hit[0])
    t = lambda x: torch.tensor(x, dtype=torch.long)
    return VillageItems(split, cache, t(qs), t(vs), t(cs), ids, banks)


def open_village(root, tokenizer_path, splits=("train", "dev", "validation"), workers: int = 1, log=lambda s: None):
    """-> (tokenizer, {split: VillageItems}).  Uses v1.dtrain.open_data for the caches (train / dev / validation only; the sealed split is never listed)."""
    from v1 import dtrain
    for s in splits:
        if s in SEALED:
            raise ValueError("the sealed split is never read here")
    root = Path(root)
    data = dtrain.open_data(root, Path(tokenizer_path), workers=workers, log=log)
    caches = {"train": data.train, "dev": data.dev, "validation": data.validation}
    return data.tokenizer, {s: village_items(caches[s], root / s, s) for s in splits}


def make_smoke_root(out: Path, train_visits: int = 120, dev_visits: int = 40, val_visits: int = 40, per_shard: int = 20, seed: int = 0) -> Path:
    """A tiny village data root with the v1 layout (train / dev / validation), generated by the real village generator.  CPU smoke only."""
    from learnlab.village.shards import write_shards
    out = Path(out)
    if (out / "validation").is_dir() and any((out / "validation").glob("shard-*.txt")):
        return out
    build = out.parent / (out.name + "-build")
    n_tr = train_visits + dev_visits
    write_shards("train", n_tr, build, 1, seed=seed, visits_per_shard=per_shard, verbose=False)
    write_shards("validation", val_visits, build, 1, seed=seed, visits_per_shard=per_shard, verbose=False)
    n_dev = max(1, dev_visits // per_shard)
    shards = sorted((build / "train").glob("shard-*.txt"))
    first_dev = len(shards) - n_dev
    for name in ("train", "dev", "validation"):
        (out / name).mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(shards):
        dest = out / ("dev" if i >= first_dev else "train")
        for suf in (".txt", ".jsonl"):
            shutil.copy(p.with_suffix(suf), dest / (p.stem + suf))
    for suf in ("txt", "jsonl"):
        for p in (build / "validation").glob(f"shard-*.{suf}"):
            shutil.copy(p, out / "validation" / p.name)
    for name in ("train", "dev"):
        shutil.copy(build / "train" / "manifest.json", out / name / "manifest.json")
    shutil.copy(build / "validation" / "manifest.json", out / "validation" / "manifest.json")
    return out


def c_stats(c: torch.Tensor, ref: Optional[torch.Tensor] = None) -> dict:
    """Distribution of the true count: range, entropy (bits), mode and the majority/prior baseline accuracy (guess the train-mode every time).
    `ref` = the counts the mode is taken from (train); default: c itself."""
    ref = c if ref is None else ref
    cnt = Counter(ref.tolist())
    mode = max(cnt, key=lambda k: (cnt[k], -k))
    own = Counter(c.tolist())
    n = max(len(c), 1)
    ent = -sum(v / n * math.log2(v / n) for v in own.values())
    return dict(n=len(c), min=int(c.min()) if len(c) else None, max=int(c.max()) if len(c) else None, mode=int(mode),
                hist={str(k): own[k] for k in sorted(own)}, entropy_bits=ent, max_entropy_bits=math.log2(max(len(own), 1)),
                prior_acc=own.get(mode, 0) / n)


# --------------------------------------------------------------------------- creative side
def _rule_table():
    return R.ALL_RULES


def warm_references(kinds: Sequence[str] = TAUGHT + ("last_digit", "square"), path: Optional[Path] = None) -> None:
    """Fill creative.rules_real's reference-program cache for every parameter of `kinds` (the breadth-first search is the slow part: ~0.1-3 s each);
    pickled beside the checkpoints so later runs and the GPU box skip it."""
    import pickle
    path = Path(path) if path else Path(__file__).resolve().parent / "ckpt" / "refs.pkl"
    if path.exists():
        R._REF.update(pickle.load(open(path, "rb")))
    todo = [(k, p) for k in kinds for p in R.PARAMS[k] if (k, p) not in R._REF]
    for k, p in todo:
        R.reference(k, p)
    if todo:
        path.parent.mkdir(exist_ok=True)
        pickle.dump(dict(R._REF), open(path, "wb"))


def make_prompt(c: int, rng: random.Random, kinds: Sequence[str] = TAUGHT, k_ex: int = 3, uid: str = "x") -> dict:
    """One creative item for hidden count c.  -> dict(row [Ledger row with prompt 'Examples: ... Now @ -> ?' and the answer f(c)], typed (same row, c typed in),
    kind, params, nums [x1 y1 .. c], steps (forced program), ans_slot).  Rules and example domain are creative/rules_real's; the examples must pin the rule at c
    (every rule of every kind that fits the examples predicts the same f(c)), so a right answer is the rule, not luck."""
    for _ in range(10000):
        kind = kinds[rng.randrange(len(kinds))]
        ps = R.PARAMS[kind]
        params = ps[rng.randrange(len(ps))]
        if R.reference(kind, params) is None:
            continue
        f = R.fn(kind, params)
        xs = rng.sample(R.DOMAIN, k_ex)
        ys = [f(x) for x in xs]
        if min(ys) < 0 or any(y in (1, 2, 10, 100) for y in ys):
            continue
        preds = {R.fn(k, p)(c) for k, p in _rule_table() if all(R.fn(k, p)(x) == y for x, y in zip(xs, ys))}
        if preds != {f(c)}:
            continue
        ex = "; ".join(f"{x} -> {y}" for x, y in zip(xs, ys))
        hidden = f"Examples: {ex}. Now {PLACEHOLDER} -> ?"
        typed = hidden.replace(PLACEHOLDER, str(c))
        nums = [v for xy in zip(xs, ys) for v in xy] + [c]
        t, _, qs = R.reference(kind, params)
        t = R.remap(t, qs, 2 * k_ex)
        steps, ans = train_form(t)
        base = dict(answer=str(f(c)), accepted=[str(f(c))], family="fewshot_number_rule", level=7, stage=9, variant="", steps=[], kind=kind, params=list(params))
        return dict(row=dict(base, id=f"hj:{uid}", prompt=hidden), typed=dict(base, id=f"hj:{uid}:t", prompt=typed), kind=kind, params=params,
                    nums=nums, program=(steps, ans), c=c)
    raise RuntimeError("no creative prompt found")


def register(item: dict) -> None:
    """Seed custom_io's per-row target cache so Ledger.loss forces exactly the reference program on this row (hidden and typed forms)."""
    steps, ans = item["program"]
    for key in ("row", "typed"):
        register_targets(item[key]["id"], item["nums"], steps, ans)


def release(item: dict) -> None:
    for key in ("row", "typed"):
        pp._CACHE.pop(item[key]["id"], None)


def item_rng(seed: int, split: str, qid: str) -> random.Random:
    """Deterministic per-item generator for evaluation (the same prompt for the same question in every arm and every run)."""
    h = hashlib.sha256(f"{seed}|{split}|{qid}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def eval_prompts(items: VillageItems, kinds: Sequence[str], seed: int, c_override: Optional[Sequence[int]] = None, k_ex: int = 3) -> list:
    """Fixed creative items for every village item of a split (c from the village unless overridden: oracle / D-text arms re-make nothing, they retype)."""
    out = []
    for i in range(len(items)):
        c = int(items.c[i]) if c_override is None else int(c_override[i])
        out.append(make_prompt(c, item_rng(seed, items.split, items.qid[i]), kinds, k_ex, uid=f"{items.split}:{items.qid[i]}"))
    return out
