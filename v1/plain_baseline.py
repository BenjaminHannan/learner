"""Plain-transformer baseline for V1 (design/v1/plain-baseline/PREREG.md).

A `learnlab.core.Core` (the contender-A family: pre-norm decoder-only, learned positions, tied head) of 2.13M parameters
(+-10%, embeddings counted, vocab 7,289) reads the visit's visible lines in the label-free regime, then the question, and
generates the answer. Everything else is held at D's V1 constants (v1/dtrain.py, v1/run.py): TRAIN shards only (<root>/train),
seed 0, AdamW (0.9, 0.99, eps 1e-8, wd 0.1 on matrices, lr 1e-3, 100 warmup steps, clip 1.0, bf16 autocast on CUDA), about
55,000 real tokens per step, a STEP budget, a checkpoint every 5% of steps with exact resume, memory guard = 0.9 x the card.

Reused, not re-implemented: `learnlab.train.Trainer` (optimizer groups, warmup, clip, bf16 step), `premonition.lookup.LineIds` /
`plain_input` (contender A's label-free 736-token window), `premonition.exp1`'s scoring rule (`step1.greedy_decode`,
`step1.answer_text`, `step1.exact_match`), `v1.ckpt` (atomic checkpoints), `v1.guard`.

Training examples (label-free, one per question): the newest whole visible lines that fit 736 tokens minus the question
(`lookup.plain_input`), then the question cut at "[answer]", then the gold answer tokens and the newline. Earlier question
lines in the window read "[question] ... [answer]" with no answer (label-free), so the newline after an earlier [answer] is not
a training target (otherwise it would contradict the final [answer]'s target); every other window token is an LM target, as in
D's L_lm over visible text. Rows are one example each (right-padded, pads masked), so training sees what scoring sees.

Scoring: exact-match answer accuracy on every question of `dev` and `validation`, enumerated by `step1.read_questions` over the
shard files, the same call `premonition.data` makes when it builds D's caches (see design/v1/plain-baseline/EQUIVALENCE.md).
The sealed `test` split is never opened: `open_split` refuses it.

  python -m v1.plain_baseline --root <v1village> --out <dir> --steps 12000 --workers 8 [--device cuda]
"""
from __future__ import annotations

import argparse
import json
import queue
import random
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence

import torch

from learnlab import step1
from learnlab.core import Core, CoreConfig
from learnlab.step1 import ANSWER_TAG, FEEDBACK_TAG, Question
from learnlab.tokenizer import Tokenizer
from learnlab.train import TrainConfig, Trainer
from premonition import preprocess
from premonition.lookup import LineIds, plain_input
from premonition.slices import CUT_MAX_LEN, MAX_NEW, SEQ_LEN
from v1 import ckpt as vckpt
from v1 import guard as vguard

SEALED = "test"
ALLOWED = ("train", "dev", "validation")
VOCAB = 7289
TARGET_PARAMS = 2_130_516                       # D's count (V1_PARAMS)
BAND = 0.10
SHAPE = (128, 5, 4)                             # d_model, layers, heads -> 2,022,912 params at vocab 7,289, context 768
SEED, LR, WARMUP, BETAS, EPS, WD, CLIP = 0, 1e-3, 100, (0.9, 0.99), 1e-8, 0.1, 1.0
MAX_TOKENS = 55_000
GROUP_SHARDS = 8
EXPECTED = {"dev": 42_653, "validation": 8_675}      # PREREG scored question counts on the real data
REGIME = preprocess.LABEL_FREE


class SealedSplitError(RuntimeError):
    """The sealed `test` split was asked for."""


class BandError(ValueError):
    """The model's parameter count is outside the pre-registered band."""


def log(*a: Any) -> None:
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ----------------------------------------------------------------- model


def build_model(vocab_size: int = VOCAB, shape: Sequence[int] = SHAPE, context: int = SEQ_LEN, *,
                enforce_band: bool = True) -> Core:
    """The plain Core; refuses (BandError) a count outside 2.13M +-10% unless `enforce_band` is off (tests only)."""
    d, layers, heads = shape
    model = Core(CoreConfig(vocab_size, context, d, layers, heads))
    n = model.num_parameters()
    lo, hi = TARGET_PARAMS * (1 - BAND), TARGET_PARAMS * (1 + BAND)
    log(f"plain Core d{d} x {layers} layers x {heads} heads, vocab {vocab_size}, context {context}: {n:,} parameters "
        f"(band {lo:,.0f}-{hi:,.0f}; D has {TARGET_PARAMS:,})")
    if enforce_band and not lo <= n <= hi:
        raise BandError(f"{n:,} parameters is outside the band {lo:,.0f}-{hi:,.0f}")
    return model


# ----------------------------------------------------------------- data


def open_split(root: Path, name: str) -> list[tuple[Path, Path]]:
    """(text, meta) shard pairs of one non-sealed split; the sealed one is refused by construction."""
    if name == SEALED or name.split("-")[0] == SEALED:
        raise SealedSplitError(f"the {name!r} split is sealed; no trainer or evaluator may read it")
    if name not in ALLOWED:
        raise ValueError(f"unknown split {name!r}; choose from {ALLOWED}")
    return step1.shard_files(Path(root) / name)


def read_shard(pair: tuple[Path, Path], name: str) -> list[Question]:
    """One shard's questions. The same call as premonition.data._shard_questions (dev shards are train-split records)."""
    return step1.read_questions(pair[0], pair[1], "train" if name == "dev" else name)


def split_questions(root: Path, name: str, limit: Optional[int] = None) -> list[Question]:
    out: list[Question] = []
    for pair in open_split(root, name):
        out.extend(read_shard(pair, name))
        if limit is not None and len(out) >= limit:
            return out[:limit]
    return out


class Example:
    __slots__ = ("ids", "mask")

    def __init__(self, ids: list[int], mask: list[bool]) -> None:
        self.ids, self.mask = ids, mask


def make_example(q: Question, lines: LineIds, tokenizer: Tokenizer, max_new: int = MAX_NEW) -> Example:
    prompt, _ = plain_input(q, lines, max_len=CUT_MAX_LEN)           # label-free window + question up to [answer]
    answer_id = tokenizer.token_to_id(ANSWER_TAG)
    tail = tokenizer.encode(q.prompt_line)
    answer_text = q.raw_line[len(q.prompt_line):].split(FEEDBACK_TAG)[0].rstrip()
    full = tokenizer.encode(q.prompt_line + answer_text + "\n")
    if full[:len(tail)] != tail:
        raise AssertionError(f"{q.id}: the answer tokens do not extend the prompt tokens")
    after = full[len(tail):][:max_new]
    if not after:
        raise AssertionError(f"{q.id}: empty answer")
    ids = prompt + after
    mask = [True] * len(ids)
    for i in range(1, len(prompt)):                                   # the newline after an earlier (cut) [answer]
        if prompt[i - 1] == answer_id:
            mask[i] = False
    mask[0] = False                                                   # nothing predicts the first token
    return Example(ids, mask)


def collate(examples: Sequence[Example], pad: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    width = max(len(e.ids) for e in examples)
    ids = torch.full((len(examples), width), pad, dtype=torch.long)
    mask = torch.zeros((len(examples), width), dtype=torch.bool)
    for r, e in enumerate(examples):
        ids[r, :len(e.ids)] = torch.tensor(e.ids)
        mask[r, :len(e.ids)] = torch.tensor(e.mask)
    return ids[:, :-1], ids[:, 1:], mask[:, 1:]


class TrainStream:
    """Deterministic endless stream of batches (~`max_tokens` real tokens each). Shards are shuffled per epoch, taken in groups of
    `group_shards`, and the group's questions are shuffled; `state` = (epoch, group, offset) is the position after the last
    yielded batch, so a resumed stream continues exactly (the held-over example is rebuilt, not stored)."""

    def __init__(self, root: Path, tokenizer: Tokenizer, *, seed: int = SEED, max_tokens: int = MAX_TOKENS,
                 group_shards: int = GROUP_SHARDS, workers: int = 1, state: Optional[dict[str, int]] = None) -> None:
        self.pairs = open_split(root, "train")                        # TRAIN only; refuses the sealed split by name
        if not self.pairs:
            raise FileNotFoundError(f"no train shards under {root}/train")
        self.tok, self.seed, self.max_tokens, self.group = tokenizer, seed, max_tokens, group_shards
        self.lines = LineIds(tokenizer, regime=REGIME)
        self.pool = ThreadPoolExecutor(max(1, workers))
        self.state = dict(state or {"epoch": 0, "group": 0, "offset": 0})
        self.pad = tokenizer.token_to_id("<pad>")

    def _group_questions(self, epoch: int, group: int) -> list[Question]:
        order = list(range(len(self.pairs)))
        random.Random(f"{self.seed}:order:{epoch}").shuffle(order)
        members = order[group * self.group:(group + 1) * self.group]
        qs = [q for i in members for q in read_shard(self.pairs[i], "train")]
        random.Random(f"{self.seed}:group:{epoch}:{group}").shuffle(qs)
        return qs

    def _n_groups(self) -> int:
        return -(-len(self.pairs) // self.group)

    def __iter__(self) -> Iterator[tuple[tuple[torch.Tensor, ...], dict[str, int], int]]:
        s = self.state
        while True:
            qs = self._group_questions(s["epoch"], s["group"])
            pending: deque[Example] = deque()
            built = s["offset"]                                       # index of the next question to turn into an example
            while s["offset"] < len(qs):
                taken: list[Example] = []
                total = 0
                while True:
                    if not pending:
                        chunk = qs[built:built + 64]
                        if not chunk:
                            break
                        pending.extend(self.pool.map(lambda q: make_example(q, self.lines, self.tok), chunk))
                        built += len(chunk)
                    nxt = pending[0]
                    if taken and total + len(nxt.ids) - 1 > self.max_tokens:
                        break
                    taken.append(pending.popleft())
                    total += len(taken[-1].ids) - 1
                s["offset"] += len(taken)
                yield collate(taken, self.pad), dict(s), total
            s["group"] += 1
            s["offset"] = 0
            if s["group"] >= self._n_groups():
                s["epoch"] += 1
                s["group"] = 0


class Prefetch:
    """Runs the stream on a background thread (queue of ready batches)."""

    def __init__(self, stream: TrainStream, depth: int = 6) -> None:
        self.q: queue.Queue = queue.Queue(depth)
        self.err: Optional[BaseException] = None
        threading.Thread(target=self._run, args=(iter(stream),), daemon=True).start()

    def _run(self, it) -> None:
        try:
            for item in it:
                self.q.put(item)
        except BaseException as e:               # noqa: BLE001 - re-raised in the consumer
            self.err = e
            self.q.put(None)

    def __iter__(self):
        return self

    def __next__(self):
        item = self.q.get()
        if item is None:
            raise self.err or StopIteration
        return item


# ----------------------------------------------------------------- scoring


@torch.no_grad()
def score_questions(model: Core, tokenizer: Tokenizer, questions: Sequence[Question], *, batch_size: int = 128,
                    max_new: int = MAX_NEW) -> dict[str, Any]:
    """Exact-match accuracy (step1.exact_match on step1.answer_text of the greedy continuation), with per-qtype counts."""
    was = model.training
    model.eval()
    lines = LineIds(tokenizer, regime=REGIME)
    prompts = [plain_input(q, lines, max_len=CUT_MAX_LEN)[0] for q in questions]
    for p in prompts:
        preprocess.audit_ids(p, tokenizer, REGIME)
    stops, newline = step1.stop_ids(tokenizer)
    gen = step1.greedy_decode(model, prompts, max_new=max_new, stop=stops, batch_size=batch_size,
                              pad_id=tokenizer.token_to_id("<pad>"))
    by: dict[str, list[int]] = {}
    hit = 0
    for q, g in zip(questions, gen):
        ok = step1.exact_match(step1.answer_text(tokenizer, g, stops, newline), q.answer)
        hit += ok
        e = by.setdefault(q.qtype, [0, 0])
        e[0] += ok
        e[1] += 1
    model.train(was)
    n = len(questions)
    return {"questions": n, "correct": hit, "accuracy": hit / n if n else None,
            "by_qtype": {k: {"n": v[1], "correct": v[0], "accuracy": v[0] / v[1]} for k, v in sorted(by.items())}}


def final_eval(model: Core, tokenizer: Tokenizer, root: Path, out: Path, steps: int, limit: Optional[int],
               check_counts: bool) -> dict[str, Any]:
    res: dict[str, Any] = {"arm": "plain", "steps": steps, "parameters": model.num_parameters(), "regime": REGIME}
    for name in ("dev", "validation"):
        qs = split_questions(root, name, limit)
        r = score_questions(model, tokenizer, qs)
        if check_counts and limit is None and r["questions"] != EXPECTED[name]:
            raise RuntimeError(f"{name}: scored {r['questions']} questions, PREREG says {EXPECTED[name]}; the comparison is void")
        res[name] = r
        log(f"final {name}: {r['correct']}/{r['questions']} = {r['accuracy']:.4f}")
    (out / "final_dev.json").write_text(json.dumps(res, indent=1, default=float))
    return res


# ----------------------------------------------------------------- main


def payload(model: Core, trainer: Trainer, stream_state: dict[str, int], steps: int) -> dict[str, Any]:
    return {"model": model.state_dict(), "optimizer": trainer.optimizer.state_dict(),
            "trainer": {"step": trainer.step, "tokens": trainer.tokens}, "stream": dict(stream_state),
            "extra": {"total_steps": steps, "shape": list(SHAPE)}}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="village data root (train/dev/validation; the sealed `test` dir is never read)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=12_000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--ckpt-every", type=int, default=None, help="default 5%% of steps")
    ap.add_argument("--eval-every", type=int, default=None, help="default 20%% of steps (first --eval-n dev questions)")
    ap.add_argument("--eval-n", type=int, default=1000)
    ap.add_argument("--group-shards", type=int, default=GROUP_SHARDS)
    ap.add_argument("--stop-after", type=int, default=None, help="testing only: stop after this many steps (kill simulation)")
    ap.add_argument("--final-limit", type=int, default=None, help="testing only: score only this many dev/validation questions")
    ap.add_argument("--shape", default=None, help="testing only: d,layers,heads (needs --allow-off-band)")
    ap.add_argument("--allow-off-band", action="store_true", help="testing only")
    a = ap.parse_args(argv)

    root, out = Path(a.root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device(a.device)
    tok = Tokenizer.load(Path(a.tokenizer))
    if tok.vocab_size != VOCAB and not a.allow_off_band:
        raise SystemExit(f"tokenizer vocab {tok.vocab_size} != {VOCAB}")
    shape = tuple(int(x) for x in a.shape.split(",")) if a.shape else SHAPE
    if a.shape and not a.allow_off_band:
        raise SystemExit("--shape needs --allow-off-band (testing only)")
    torch.manual_seed(SEED)
    model = build_model(tok.vocab_size, shape, enforce_band=not a.allow_off_band)
    tc = TrainConfig(batch=1, seq_len=SEQ_LEN, lr=LR, beta1=BETAS[0], beta2=BETAS[1], eps=EPS, weight_decay=WD, grad_clip=CLIP,
                     warmup_steps=WARMUP, log_every=50, memory_limit_bytes=vguard.limit_bytes(device), memory_check_every=50)
    trainer = Trainer(model, tc, device)
    ck_dir = out / "wake-ckpt"
    stream_state = {"epoch": 0, "group": 0, "offset": 0}
    got = vckpt.load(ck_dir, map_location="cpu")
    if got is not None:
        model.load_state_dict(got["model"])
        trainer.optimizer.load_state_dict(got["optimizer"])
        trainer.step, trainer.tokens = int(got["trainer"]["step"]), int(got["trainer"]["tokens"])
        stream_state = dict(got["stream"])
        vckpt.set_rng_state(got["rng"])
        log(f"RESUMED from step {trainer.step}, stream {stream_state}")
    ck_every = a.ckpt_every or max(1, a.steps // 20)
    eval_every = a.eval_every or max(1, a.steps // 5)
    eval_qs = split_questions(root, "dev", a.eval_n)
    stream = Prefetch(TrainStream(root, tok, max_tokens=a.max_tokens, group_shards=a.group_shards, workers=a.workers,
                                  state=stream_state))
    train_log = (out / "train_log.jsonl").open("a")
    started, real_tokens, window, wl = time.perf_counter(), 0, 0, 0.0
    first = trainer.step
    model.train()
    while trainer.step < a.steps:
        if a.stop_after is not None and trainer.step - first >= a.stop_after:
            break
        (x, y, m), stream_state, real = next(stream)
        loss, gnorm, _ = trainer._step(x, y, m, track=False)
        loss_v = float(loss)
        if loss_v != loss_v or loss_v in (float("inf"), float("-inf")):
            raise FloatingPointError(f"non-finite loss at step {trainer.step}")
        real_tokens += real
        window += 1
        wl += loss_v
        if trainer.step == first + 1 or trainer.step % 50 == 0:
            trainer._check_memory()
        if trainer.step % 50 == 0:
            rec = {"step": trainer.step, "loss": wl / window, "grad_norm": float(gnorm), "stream": dict(stream_state),
                   "tok_per_s": real_tokens / (time.perf_counter() - started)}
            train_log.write(json.dumps(rec) + "\n")
            train_log.flush()
            log(f"step {trainer.step}/{a.steps} loss {rec['loss']:.4f} {rec['tok_per_s']:,.0f} tok/s")
            window, wl = 0, 0.0
        if trainer.step % eval_every == 0 and trainer.step < a.steps:
            r = score_questions(model, tok, eval_qs)
            (out / "dev_evals.jsonl").open("a").write(json.dumps({"step": trainer.step, "n": r["questions"], "accuracy": r["accuracy"]}) + "\n")
            log(f"eval step {trainer.step}: dev[:{r['questions']}] accuracy {r['accuracy']:.4f}")
        if trainer.step % ck_every == 0 or trainer.step == a.steps:
            vckpt.save(ck_dir, trainer.step, payload(model, trainer, stream_state, a.steps))
    if trainer.step < a.steps:
        log(f"stopped at step {trainer.step} (--stop-after)")
        return 0
    torch.save(model.state_dict(), out / "plain-final.pt")
    res = final_eval(model, tok, root, out, trainer.step, a.final_limit, check_counts=not a.allow_off_band)
    log("PLAIN_DONE", json.dumps({k: res[k]["accuracy"] for k in ("dev", "validation")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
