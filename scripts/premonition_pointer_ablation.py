"""A vs E on the VILLAGE task: what does the pointerizer buy? (additive; nothing existing is edited)

Two otherwise-identical plain `learnlab.core.Core` 4M transformers are trained on the same village visits,
in the same order, for the same number of optimizer steps, and scored by the same `premonition.exp1`
machinery on the validation split in the label-free regime:

  A  ordinary subword text (names are syllable pieces of the v2 tokenizer)
  E  the same text pointerized (`premonition.pointer`): every name is ONE entity id, renumbered by a fresh
     random order for every visit; the decoded answer is detokenised through the visit's name table.

Both arms use ALIGNED one-visit-per-row training rows, the fix `design/06-step1-pilot-results.md` describes:
each row is "<eos> visit <eos>", cut or padded (and loss-masked) to exactly `--seq-len` tokens, so every
trainer row starts at a visit start like an evaluation prompt. `premonition.contenders.train_contender`
does NOT do this (its plain stream is unaligned and `PointerStream` is packed), which is why this script
builds its own streams instead of calling it.

Both arms read the SAME `premonition.data.VisitCache` visits in the SAME seeded order; A's cache is built
with `detector=None` (the names-as-ordinary-tokens control, whose per-line encoding equals
`learnlab.step1.encode_visit` without the trailing <eos>) and E's with the data directory's fitted
`NameDetector`. Only the token mapping differs.

Checkpoints carry exactly the config fields `train_contender` writes, so `contenders.evaluate_contender`
accepts them. The scoring purpose is negotiated down (`primary` -> `diagnostic` -> `legacy`) and the one
that was used is recorded: with `--seq-len 2048` the core's context differs from `premonition.slices.SEQ_LEN`
(768), which `exp1.core_checks` reports as a "shape" problem, and only `legacy` tolerates that.

    PY -B scripts/premonition_pointer_ablation.py smoke                       # CPU end-to-end, seconds
    PY -B scripts/premonition_pointer_ablation.py run --device cuda --visits medium \
        --steps 10000 --batch 16 --seq-len 2048 --arms A:0,E:0,A:1,E:1

Writes only under artifacts/claude-pointer-ablation-20260919/ (one .ckpt directory and one .json per arm,
plus a combined summary JSON and a short text table). Runs under Python 3.10 (Windows) and 3.12 (macOS).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True

# ------------------------------------------------------------------ runtime bootstrap (mirrors run.py)
#
# run.py registers the no-install dependency roots and redirects every cache into .runtime/ BEFORE torch is
# imported. A standalone script must do the same or torch will not import on the Mac at all. The runtime
# file is named by --runtime (or PREMONITION_RUNTIME); the default is the project's runtime.local.json.


def _runtime_path() -> Path:
    for index, argument in enumerate(sys.argv[1:]):
        if argument == "--runtime" and index + 2 < len(sys.argv):
            return Path(sys.argv[index + 2])
        if argument.startswith("--runtime="):
            return Path(argument.split("=", 1)[1])
    return Path(os.environ.get("PREMONITION_RUNTIME") or (ROOT / "runtime.local.json"))


RUNTIME_PATH = _runtime_path()
RUNTIME = json.loads(RUNTIME_PATH.read_text(encoding="utf-8")) if RUNTIME_PATH.is_file() else {}

# Unlike run.py this does not fail on a root that is not there: the same project tree is read on the Mac
# (whose runtime.local.json lists uv archive roots) and on Windows (whose Python has torch installed), and
# `python -m unittest` on the Windows box must be able to import this module with the Mac runtime file
# present. Nothing is ever downloaded or installed either way.
sys.path[0:0] = [d for d in RUNTIME.get("import_roots", []) if Path(d).is_dir()]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for _variable, _suffix in {
    "XDG_CACHE_HOME": "cache",
    "TORCH_HOME": "cache/torch",
    "TORCHINDUCTOR_CACHE_DIR": "cache/inductor",
    "TRITON_CACHE_DIR": "cache/triton",
    "CUDA_CACHE_PATH": "cache/cuda",
    "HF_HOME": "cache/huggingface",
    "PIP_CACHE_DIR": "cache/pip",
    "UV_CACHE_DIR": "cache/uv",
    "TMPDIR": "tmp",
    "TMP": "tmp",
    "TEMP": "tmp",
}.items():
    os.environ[_variable] = str(ROOT / ".runtime" / _suffix)
os.environ.update(
    PYTHONDONTWRITEBYTECODE="1",
    TORCH_COMPILE_DISABLE="1",
    TORCHDYNAMO_DISABLE="1",
    HF_HUB_OFFLINE="1",
    TOKENIZERS_PARALLELISM="false",
    CUDA_CACHE_DISABLE="1",
)

from dataclasses import asdict  # noqa: E402
import random  # noqa: E402
import time  # noqa: E402
from typing import Any, Callable, Iterator, Optional, Sequence  # noqa: E402

import torch  # noqa: E402

from learnlab import step1  # noqa: E402
from learnlab.core import Core  # noqa: E402
from learnlab.train import MemoryGuardError, TrainConfig, Trainer  # noqa: E402

from premonition import contenders, exp1, flops, identity, preprocess, slices  # noqa: E402
from premonition import data as pdata  # noqa: E402
from premonition.batch import N_ENT  # noqa: E402
from premonition.pointer import random_order  # noqa: E402

RUN = "claude-pointer-ablation-20260919"
ARMS = ("A", "E")
Log = Callable[[str], None]


def make_budget():
    """The project's storage budget, configured exactly as run.py configures it."""
    from memorylab.storage import Budget

    budget = Budget(
        ROOT,
        RUNTIME.get("shared_roots", []) + RUNTIME.get("import_roots", []),
        hard=RUNTIME.get("hard_bytes", Budget.HARD),
        steady=RUNTIME.get("steady_bytes", Budget.STEADY),
    )
    budget.ensure_runtime_directories()
    return budget


# ------------------------------------------------------------------ the aligned one-visit-per-row stream


class AlignedVisitStream:
    """Endless stream of aligned rows over one `premonition.data.VisitCache`.

    Each row is "<eos> visit <eos>", cut (counted) or padded to exactly `length`, with a boolean loss mask
    that is True only over the visit's own tokens: the shape `learnlab.step1.TokenStream._aligned` yields,
    so `learnlab.train.Trainer` packs exactly one visit per trainer row.

    Every epoch shuffles the visit indices with `Random(f"{seed}:visits:{epoch}")` and, when `pointer` is
    set, renumbers each visit's entities with `random_order(Random(f"{seed}:entities:{epoch}"))` -- the same
    two streams `contenders.PointerStream` draws, so an A stream and an E stream built with the same seed
    walk the same visits in the same order.
    """

    def __init__(self, cache: Any, *, eos: int, length: int, seed: int = 0, pointer: bool = False) -> None:
        if len(cache) == 0:
            raise ValueError("an empty visit cache")
        if length <= 2:
            raise ValueError("length must leave room for both <eos> tokens")
        self.cache, self.eos, self.length, self.seed, self.pointer = cache, int(eos), int(length), seed, pointer
        self.visits = 0                 # rows yielded
        self.truncated_visits = 0
        self.yielded = 0                # unmasked (real) tokens yielded
        self.padded = 0                 # padding tokens yielded
        self.epoch = 0
        self.order_log: list[int] = []  # visit indices yielded, in order (diagnostics and tests)
        self._items = self._generate()

    def _row(self, tokens: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        ends = torch.tensor([self.eos], dtype=torch.long)
        visit = torch.cat((ends, tokens.long(), ends))
        self.visits += 1
        if visit.numel() > self.length:
            self.truncated_visits += 1
            visit = visit[:self.length]
        mask = torch.zeros(self.length, dtype=torch.bool)
        mask[:visit.numel()] = True
        padded = torch.full((self.length,), self.eos, dtype=torch.long)
        padded[:visit.numel()] = visit
        self.yielded += int(visit.numel())
        self.padded += self.length - int(visit.numel())
        return padded, mask

    def _generate(self) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        base = self.cache.vocab_size
        lookup = torch.arange(base + N_ENT)
        epoch = 0
        while True:
            order = list(range(len(self.cache)))
            random.Random(f"{self.seed}:visits:{epoch}").shuffle(order)
            entities = random.Random(f"{self.seed}:entities:{epoch}")
            for index in order:
                tokens = self.cache.visit_tokens(index)
                if self.pointer:
                    lookup[base:] = base + torch.tensor(random_order(entities))
                    tokens = lookup[tokens]
                self.order_log.append(index)
                yield self._row(tokens)
            epoch += 1
            self.epoch = epoch

    def __iter__(self) -> "AlignedVisitStream":
        return self

    def __next__(self) -> tuple[torch.Tensor, torch.Tensor]:
        return next(self._items)

    def summary(self) -> dict[str, Any]:
        return {
            "kind": "pointer-aligned" if self.pointer else "plain-aligned",
            "row_length": self.length, "rows_yielded": self.visits,
            "truncated_rows": self.truncated_visits,
            "truncated_fraction": self.truncated_visits / max(1, self.visits),
            "real_tokens_yielded": self.yielded, "padding_tokens_yielded": self.padded,
            "padding_fraction": self.padded / max(1, self.padded + self.yielded),
            "epochs": self.visits / len(self.cache), "cache_visits": len(self.cache),
            "cache_tokens": int(self.cache.tokens.numel()),
        }


def open_caches(budget: Any, data: Any, arms: Sequence[str], *, workers: int,
                log: Log = print) -> tuple[dict[str, Any], Any]:
    """The visit caches the requested arms need: A's plain one, E's pointerized one (both legacy v1).

    Legacy v1 (regime=None) is what `contenders._stream` builds for E: whole lines, answers included, since
    a Core training stream keeps answers as LM targets.
    """
    caches: dict[str, Any] = {}
    detector = None
    if "E" in arms:
        detector = pdata.name_detector(budget, data.rel, workers=max(1, workers), log=log)
        caches["E"] = pdata.load_or_build(budget, data.rel, "train", data.tokenizer, detector, split="train",
                                          workers=max(1, workers), log=log)
    if "A" in arms:
        caches["A"] = pdata.load_or_build(budget, data.rel, "train", data.tokenizer, None, split="train",
                                          workers=max(1, workers), log=log)
    if len(caches) == 2 and caches["A"].visit_ids != caches["E"].visit_ids:
        raise SystemExit("the plain and pointerized caches hold different visits; the arms would not be paired")
    return caches, detector


# ------------------------------------------------------------------ training


def train_arm(budget: Any, data: Any, arm: str, cache: Any, detector: Any, *, steps: int, batch: int,
              seq_len: int, device: str, seed: int, lr: Optional[float] = None, warmup: Optional[int] = None,
              log_every: int = 100, save: bool = True, environment: Optional[dict[str, Any]] = None,
              log: Log = print, on_log: Optional[Callable[[dict[str, Any]], None]] = None) -> dict[str, Any]:
    """Train one arm for exactly `steps` optimizer steps of `batch` x `seq_len` aligned tokens."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; choose from {ARMS}")
    spec = contenders.contender(arm)
    tokenizer = data.tokenizer
    config = contenders.core_config(arm, tokenizer.vocab_size, context=seq_len)
    per_step = contenders.step_flops(config, batch, seq_len)
    lr = spec.lr if lr is None else lr
    warmup = (100 if device == "cuda" else 10) if warmup is None else warmup
    train_config = TrainConfig(batch=batch, seq_len=seq_len, lr=lr, warmup_steps=warmup, log_every=log_every)
    torch.manual_seed(seed)
    model = Core(config)
    trainer = Trainer(model, train_config, device)
    stream = AlignedVisitStream(cache, eos=tokenizer.token_to_id("<eos>"), length=seq_len, seed=seed,
                                pointer=spec.inputs == "pointer")
    log(f"{RUN} train {arm} seed {seed}: {model.num_parameters():,} params, {steps:,} steps of "
        f"{batch}x{seq_len} = {steps * batch * seq_len:,} tokens ({steps * per_step:.4g} counted FLOPs), "
        f"lr {lr}, warmup {warmup}, context {seq_len}")
    started = time.perf_counter()

    def logged(record: dict[str, Any]) -> None:
        record["flops"] = record["step"] * per_step
        record["budget_fraction"] = record["step"] / steps
        record["elapsed"] = time.perf_counter() - started
        if on_log is not None:
            on_log(record)

    status, error = "completed", None
    try:
        result = trainer.train(stream, max_tokens=steps * batch * seq_len, on_log=logged)
    except MemoryGuardError as guard:
        status, error = "aborted", str(guard)
        result = {"steps": trainer.step, "tokens": trainer.tokens, "peak_gpu_reserved_bytes": guard.peak,
                  "stop": "memory guard", "seconds": time.perf_counter() - started}
    if status == "completed" and trainer.step != steps:
        status, error = "short", f"{trainer.step} of {steps} steps"
    seconds = float(result.get("seconds") or time.perf_counter() - started)
    achieved = trainer.step * per_step
    extra: dict[str, Any] = {}
    if spec.inputs == "pointer":
        extra = {"pointer": {"detector": f"{data.rel}/{pdata.DETECTOR_FILE}", "sha256": detector.digest,
                             "entities": N_ENT,
                             "cache": pdata.cache_relative(data.rel, "train", tokenizer, detector),
                             "cache_stats": cache.info.get("stats", {})}}
    ckpt_config = {
        "model": contenders.MODEL_NAME, "experiment": 1, "contender": arm, "inputs": spec.inputs,
        "preprocess": preprocess.identity(preprocess.WITH_LABELS),   # Core streams keep answers (design/06 §9.1)
        "core": asdict(config), "train": asdict(train_config), "tokenizer": data.tokenizer_info,
        "data": {"dir": data.rel, "tag": data.tag}, "seed": seed, "max_new": slices.MAX_NEW,
        "flops": {"per_step": per_step, "per_token": per_step / (batch * seq_len),
                  "budget_kind": "steps", "target": steps, "achieved": achieved},
        **extra,
    }
    summary = stream.summary()
    report: dict[str, Any] = {
        "command": "premonition pointer-ablation train", "run": RUN, "experiment": 1, "contender": arm,
        "status": status, "error": error, "parameters": model.num_parameters(), "device": device,
        "seed": seed, "planned_steps": steps, "config": ckpt_config,
        "flops": {"convention": "premonition.flops (FlopCounterMode, dense attention, backward recompute)",
                  "per_step": per_step, "per_token": per_step / (batch * seq_len),
                  "hand_per_token": flops.core_flops_per_token(config, seq_len),
                  "budget_kind": "steps", "target": steps, "achieved": achieved},
        "train": {**result, "flops": achieved, "flops_per_second": achieved / max(seconds, 1e-9),
                  "seconds": seconds},
        "stream": summary, "history": trainer.history, "environment": environment,
    }
    if save:
        stem = f"artifacts/{RUN}/train-{arm}-s{seed}-{time.time_ns()}-{os.getpid()}"
        if status != "aborted":
            from learnlab.ckpt import save_checkpoint

            save_checkpoint(budget, stem + ".ckpt", model=trainer.model, config=ckpt_config,
                            optimizer=trainer.optimizer, trainer_state=trainer.state_dict())
            report["checkpoint"] = stem + ".ckpt"
        report["artifact"] = stem + ".json"
        budget.save_json(report["artifact"], exp1.jsonable(report), 60_000_000)
    log(f"{RUN} train {arm} seed {seed}: {status}; {trainer.step:,} steps, {trainer.tokens:,} target tokens "
        f"({summary['real_tokens_yielded']:,} real, {summary['truncated_rows']:,} truncated rows, "
        f"{summary['padding_fraction']:.1%} padding) in {seconds:.1f}s; peak GPU reserved "
        f"{result.get('peak_gpu_reserved_bytes')}")
    return report


# ------------------------------------------------------------------ evaluation


PURPOSES = ("primary", "diagnostic", "legacy")


def evaluate_arm(project: Path, checkpoint: str, *, device: str, heldin: int, workers: int, batch_size: int,
                 log: Log = print) -> dict[str, Any]:
    """`contenders.evaluate_contender` on the validation split, with the strictest purpose it accepts."""
    failure: Optional[Exception] = None
    for purpose in PURPOSES:
        try:
            report = contenders.evaluate_contender(
                project, checkpoint, split="validation", device=device, heldin=heldin, workers=workers,
                batch_size=batch_size, purpose=purpose, log=log)
        except identity.CheckpointIncompatible as error:
            failure = error
            log(f"{RUN} eval: purpose {purpose!r} refused: {error}")
            continue
        report["purpose_used"] = purpose
        report["purposes_refused"] = list(PURPOSES[:PURPOSES.index(purpose)])
        return report
    raise SystemExit(f"no scoring purpose accepts {checkpoint}: {failure}")


SLICE_KEYS = ("overall", "near", "far", "far_deep", "multi_hop", "reworded")
REPORT_SLICES = SLICE_KEYS + ("fresh_names", "seen_names")


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    """The cells this ablation reports, as k/n plus accuracy and the Wilson interval."""
    summary = report["directories"]["validation"]["summary"]
    cells = dict(summary["cells"])
    cells.update(summary["decision_cells"])
    out: dict[str, Any] = {name: cells.get(name) for name in SLICE_KEYS}
    out["fresh_names"] = report["name_gap"].get("fresh_names")
    out["seen_names"] = report["name_gap"].get("seen_names")
    out["name_gap"] = report["name_gap"].get("gap")
    out["purpose_used"] = report.get("purpose_used")
    out["primary"] = (report.get("identity") or {}).get("primary")
    out["identity_problems"] = (report.get("identity") or {}).get("problems")
    out["decision_items"] = summary["decision_items"]
    out["input_audit"] = report["directories"]["validation"]["input_audit"]
    out["inputs"] = {k: v for k, v in report["inputs"]["per_directory"]["validation"].items()
                     if k in ("max_tokens", "mean_tokens", "inputs", "predictions_with_entity",
                              "predictions_with_unbound_entity", "answers_with_unbound_name",
                              "equal_to_canonical")}
    return out


def item_table(report: dict[str, Any]) -> dict[str, int]:
    """question id -> 1/0 correct, for the validation directory (the paired comparison's raw material)."""
    return {row["id"]: int(bool(row["correct"])) for row in report["items"]["validation"]}


def slice_ids(report: dict[str, Any], name: str) -> list[str]:
    return [row["id"] for row in report["items"]["validation"] if name in row["slices"]]


# ------------------------------------------------------------------ the driver


def run_arms(budget: Any, *, arms: Sequence[tuple[str, int]], visits: Any, steps: int, batch: int,
             seq_len: int, device: str, workers: int, heldin: int, eval_batch: int, log_every: int = 100,
             log: Log = print, save: bool = True) -> dict[str, Any]:
    from memorylab.experiment import environment_report

    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit(f"{RUN} --device cuda: CUDA is not available here. Nothing was run.")
    started = time.perf_counter()
    data = step1.build_data(budget, visits=visits, seed=0, workers=max(1, workers), log=log)
    log(f"{RUN} data: {data.rel} ({data.tag}), tokenizer {data.tokenizer.digest[:12]} "
        f"({data.tokenizer.vocab_size} ids, status {identity.tokenizer_status(data.tokenizer)})")
    caches, detector = open_caches(budget, data, sorted({arm for arm, _ in arms}), workers=workers, log=log)
    environment = environment_report(torch.device(device))
    results: list[dict[str, Any]] = []
    for arm, seed in arms:
        arm_started = time.perf_counter()
        train = train_arm(budget, data, arm, caches[arm], detector, steps=steps, batch=batch, seq_len=seq_len,
                          device=device, seed=seed, save=save, environment=environment, log_every=log_every,
                          log=log, on_log=lambda record: print("LOG " + json.dumps(record), flush=True))
        entry: dict[str, Any] = {"contender": arm, "seed": seed, "train": {
            "status": train["status"], "error": train["error"], "steps": train["train"].get("steps"),
            "target_tokens": train["train"].get("tokens"), "seconds": train["train"]["seconds"],
            "final_loss": train["train"].get("final_loss"),
            "peak_gpu_reserved_bytes": train["train"].get("peak_gpu_reserved_bytes"),
            "flops": train["flops"]["achieved"], "stream": train["stream"],
            "artifact": train.get("artifact"), "checkpoint": train.get("checkpoint")}}
        if train.get("checkpoint") and train["status"] != "aborted":
            evaluation = evaluate_arm(ROOT, train["checkpoint"], device=device, heldin=heldin,
                                      workers=max(1, workers), batch_size=eval_batch, log=log)
            entry["eval"] = summarize(evaluation)
            entry["items"] = item_table(evaluation)
            entry["slice_ids"] = {name: slice_ids(evaluation, name) for name in REPORT_SLICES}
            if save:
                relative = f"artifacts/{RUN}/eval-{arm}-s{seed}-{time.time_ns()}-{os.getpid()}.json"
                budget.save_json(relative, exp1.jsonable(evaluation), 200_000_000)
                entry["eval_artifact"] = relative
            log(exp1.format_report(evaluation))
        entry["seconds"] = time.perf_counter() - arm_started
        results.append(entry)
        log(f"{RUN} arm {arm} seed {seed} done in {entry['seconds']:.1f}s")
    combined = {
        "command": "premonition pointer-ablation", "run": RUN, "experiment": 1,
        "question": "what does replacing names with re-permuted entity ids buy a plain 4M Core?",
        "data": {"dir": data.rel, "tag": data.tag, "visits": str(visits),
                 "tokenizer": {"path": data.tokenizer_info.get("path"), "sha256": data.tokenizer.digest,
                               "vocab_size": data.tokenizer.vocab_size,
                               "status": identity.tokenizer_status(data.tokenizer)}},
        "training": {"steps": steps, "batch": batch, "seq_len": seq_len, "device": device,
                     "rows": "aligned one visit per row, <eos> visit <eos>, padded and loss-masked",
                     "tokens_per_arm": steps * batch * seq_len},
        "evaluation": {"split": "validation", "regime": preprocess.LABEL_FREE, "heldin": heldin,
                       "max_new": slices.MAX_NEW, "max_len": slices.CUT_MAX_LEN},
        "environment": environment, "arms": results, "seconds": time.perf_counter() - started,
    }
    if save:
        relative = f"artifacts/{RUN}/ablation-{time.time_ns()}-{os.getpid()}.json"
        budget.save_json(relative, exp1.jsonable(combined), 200_000_000)
        combined["artifact"] = relative
        log(f"{RUN} report -> {relative}")
    return combined


def format_table(combined: dict[str, Any]) -> str:
    """A compact A-vs-E table: correct/n and accuracy per slice, per arm and seed."""
    rows = [f"{RUN}: A (subword names) vs E (pointerized names) on {combined['data']['tag']}",
            f"  {combined['training']['steps']:,} steps of {combined['training']['batch']}x"
            f"{combined['training']['seq_len']} on {combined['training']['device']}; "
            f"{combined['training']['tokens_per_arm']:,} target tokens per arm", ""]
    rows.append(f"{'arm':>4} {'seed':>4} {'purpose':>10}  "
                + "  ".join(f"{name:>17}" for name in REPORT_SLICES))
    for entry in combined["arms"]:
        evaluation = entry.get("eval")
        if not evaluation:
            rows.append(f"{entry['contender']:>4} {entry['seed']:>4}  (no evaluation: "
                        f"{entry['train']['status']})")
            continue
        cells = []
        for name in REPORT_SLICES:
            cell = evaluation.get(name)
            cells.append(f"{'n/a':>17}" if not cell or not cell.get("n")
                         else f"{cell['hits']:>5}/{cell['n']:<6}{cell['accuracy'] * 100:>5.1f}")
        rows.append(f"{entry['contender']:>4} {entry['seed']:>4} {str(evaluation['purpose_used']):>10}  "
                    + "  ".join(cells))
    return "\n".join(rows)


def parse_arms(text: str) -> list[tuple[str, int]]:
    out = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        arm, _, seed = token.partition(":")
        if arm not in ARMS:
            raise SystemExit(f"unknown arm {arm!r}; choose from {ARMS}")
        out.append((arm, int(seed or 0)))
    if not out:
        raise SystemExit("--arms is empty")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--runtime", default=str(RUNTIME_PATH))     # consumed by the bootstrap above
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "smoke"):
        one = sub.add_parser(name)
        one.add_argument("--arms", default="A:0,E:0,A:1,E:1" if name == "run" else "A:0,E:0")
        one.add_argument("--visits", default="medium" if name == "run" else "tiny")
        one.add_argument("--steps", type=int, default=10_000 if name == "run" else 20)
        one.add_argument("--batch", type=int, default=16 if name == "run" else 2)
        # The smoke's rows are `slices.SEQ_LEN` long, so the evaluation's 736-token inputs fit and the
        # checkpoint also passes the "diagnostic" shape check; the real run uses 2048 (see the module doc).
        one.add_argument("--seq-len", type=int, default=2048 if name == "run" else slices.SEQ_LEN)
        one.add_argument("--device", choices=("cpu", "cuda"), default="cuda" if name == "run" else "cpu")
        one.add_argument("--workers", type=int, default=0, help="encoder/replay processes; 0 = auto")
        one.add_argument("--heldin", type=int, default=3000 if name == "run" else 20,
                         help="trained-on questions scored for the seen-names side of the name gap")
        one.add_argument("--eval-batch", type=int, default=64 if name == "run" else 8)
        one.add_argument("--log-every", type=int, default=100 if name == "run" else 10)
    args = parser.parse_args(argv)
    workers = args.workers or max(1, min(12, (os.cpu_count() or 2) - 1))
    budget = make_budget()
    combined = run_arms(budget, arms=parse_arms(args.arms), visits=args.visits, steps=args.steps,
                        batch=args.batch, seq_len=args.seq_len, device=args.device, workers=workers,
                        heldin=args.heldin, eval_batch=args.eval_batch, log_every=args.log_every,
                        log=lambda message: print(message, flush=True))
    text = format_table(combined)
    print(text, flush=True)
    relative = f"artifacts/{RUN}/table-{time.time_ns()}-{os.getpid()}.txt"
    payload = text.encode("utf-8")
    budget.atomic_write(relative, len(payload), lambda handle: handle.write(payload))
    print(f"{RUN} table -> {relative}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
