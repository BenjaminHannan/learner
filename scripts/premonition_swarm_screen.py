"""Swarm screen runner (design/swarm/BOX-SPEC.md): data, C0 bench, train, eval, manifest.

One script, plain argparse, JSON out, logs to stdout. It serves RUNCARD-S0 (D1 vs S0) and RUNCARD-S1.

    python -B scripts/premonition_swarm_screen.py data  --visits large --out data.json
    python -B scripts/premonition_swarm_screen.py c0    --data-rel ... --tokenizer ... --dph 0.40 --out c0.json
    python -B scripts/premonition_swarm_screen.py train --arm S0 --seed 0 --seconds 3600 --data-rel ... \
        --tokenizer ... --out train-S0-s0.json
    python -B scripts/premonition_swarm_screen.py eval  --checkpoint checkpoints/swarm-screen/S0-s0 \
        [--lesion board] --out eval-S0-s0.json
    python -B scripts/premonition_swarm_screen.py manifest [--check]

`--size tiny` and `--device cpu` exist for the CPU dry run only (its numbers mean nothing). The readout is
`scripts/premonition_swarm_marks.py`.

The tokenizer. `learnlab.step1.build_data` picks `premonition-tok-v2.json` (7,289 ids) whenever the village
renders the real pattern bank, and the 7,068-id `premonition-tok-v2-fallback.json` only while it renders the
hand-written fallback patterns. `premonition.identity` (and `config.VOCAB_V2`) accept only the 7,068-id file as
"the v2 contender" tokenizer, and `evaluate_d_checkpoint` refuses anything else for a primary report. So `data`
passes the fallback path to `build_data` explicitly and asserts 7,068 ids for `--size full`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True

# ------------------------------------------------------------------ runtime bootstrap (as the pointer ablation)


def _runtime_path() -> Path:
    for index, argument in enumerate(sys.argv[1:]):
        if argument == "--runtime" and index + 2 < len(sys.argv):
            return Path(sys.argv[index + 2])
        if argument.startswith("--runtime="):
            return Path(argument.split("=", 1)[1])
    return Path(os.environ.get("PREMONITION_RUNTIME") or (ROOT / "runtime.local.json"))


RUNTIME_PATH = _runtime_path()
RUNTIME = json.loads(RUNTIME_PATH.read_text(encoding="utf-8")) if RUNTIME_PATH.is_file() else {}
sys.path[0:0] = [d for d in RUNTIME.get("import_roots", []) if Path(d).is_dir()]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

for _variable, _suffix in {
    "XDG_CACHE_HOME": "cache", "TORCH_HOME": "cache/torch", "TORCHINDUCTOR_CACHE_DIR": "cache/inductor",
    "TRITON_CACHE_DIR": "cache/triton", "CUDA_CACHE_PATH": "cache/cuda", "HF_HOME": "cache/huggingface",
    "PIP_CACHE_DIR": "cache/pip", "UV_CACHE_DIR": "cache/uv", "TMPDIR": "tmp", "TMP": "tmp", "TEMP": "tmp",
}.items():
    os.environ[_variable] = str(ROOT / ".runtime" / _suffix)
os.environ.update(
    PYTHONDONTWRITEBYTECODE="1", TORCH_COMPILE_DISABLE="1", TORCHDYNAMO_DISABLE="1", HF_HUB_OFFLINE="1",
    TOKENIZERS_PARALLELISM="false", CUDA_CACHE_DISABLE="1",
)

import functools  # noqa: E402
import gc  # noqa: E402
import itertools  # noqa: E402
import platform  # noqa: E402
import shutil  # noqa: E402
import statistics  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from typing import Any, Callable, Mapping, Optional, Sequence  # noqa: E402

import torch  # noqa: E402

from premonition.model import MODES  # noqa: E402  (the one definition; after the bootstrap above)

# ------------------------------------------------------------------ the registered arms and numbers
ARMS: dict[str, dict[str, Any]] = {
    "D1": {},
    "S0": dict(thinkers=4, swarm_board=False, swarm_rounds=4, board_cards=16),
    "S1": dict(thinkers=4, swarm_board=True, swarm_rounds=4, board_cards=16),
}
C0_ARMS: dict[str, dict[str, Any]] = {
    "D1": {}, "S0m2": dict(thinkers=2), "S0m4": ARMS["S0"], "S0m8": dict(thinkers=8), "S1m4": ARMS["S1"],
}
P_OWN = 0.75                                         # the curriculum's flat p_own in the own phase
CURRICULUM_WEIGHTS = {"gold": 0.05, "teacher": 0.25, "own": 0.70}
F_TARGET = 2.6e16                                    # RUNCARD-S0 section 1: D1's FLOPs that define T
T_STEP, T_CAP = 300, 3600
STOP_RATIO = 2.5                                     # FUNDING-BID C0 rule
MONEY_CAP_USD = 3.50                                 # the S0 hard cap
BOX_OVERHEAD = 1.15
S0_RUNS = 6                                          # D1 and S0 x seeds 0-2: trains and validation evals
PROCESS_MARGIN_SECONDS = 60.0                        # start-up of each fresh train / eval process (eighth sweep, 5)
# The registered C0 protocol (BOX-SPEC C0). c0.json records the settings it ran with; the box's C0 gate and the
# readout accept only these (round 3, ninth pass, blocking 1).
REGISTERED_C0 = {"rounds": 3, "warmup": 10, "timed": 40, "chunk": 5, "max_tokens": 55_000}
VOCAB_V2 = 7068
CKPT_DIR = "artifacts/claude-swarm-screen-20261018/ckpt-manual"   # git-ignored (round 3, sixth pass, item 12)
REFUSED, C0_STOP = 2, 3                              # the box's exit codes (premonition_swarm_box.sh header)


class Stop(SystemExit):
    """A refusal before any work (exit REFUSED) or a C0 stop: the bench cannot set T (exit C0_STOP). `main` prints
    the message to stderr and exits with the code, so the box tells a refusal or a stop from a crash (round 3, eighth
    pass, item 9)."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(code)
        self.message = message

    def __str__(self) -> str:
        return self.message


def refused(message: str) -> Stop:
    return Stop(REFUSED, message)


def c0_stop(message: str) -> Stop:
    return Stop(C0_STOP, message)
# Every repo module the run imports (review round 3, item 2): the closure of CLOSURE_SEEDS below, kept as an
# explicit list so the manifest reads plainly. `ManifestCoverageTest` recomputes the closure and fails if an
# imported repo module is missing, so a new import cannot go unpinned. Plus the box script.
MANIFEST_FILES = sorted(
    [f"premonition/{name}.py" for name in ("__init__", "batch", "config", "data", "exp1", "flops", "identity",
                                           "model", "pointer", "preprocess", "slices", "store", "swarm", "train")]
    + [f"learnlab/{name}.py" for name in ("__init__", "ckpt", "core", "leaks", "metrics", "patterns", "policy",
                                          "readonly", "splits", "step1", "tokenizer", "toy", "train")]
    + [f"learnlab/village/{name}.py" for name in ("__init__", "names", "oracle", "render", "scheduler", "shards",
                                                  "stream", "vocab", "world")]
    + [f"memorylab/{name}.py" for name in ("__init__", "checkpoint", "experiment", "model", "positive_controls",
                                           "storage", "tasks", "transformer_model")]
    + ["scripts/premonition_swarm_screen.py", "scripts/premonition_swarm_marks.py", "scripts/premonition_swarm_box.sh"])
CLOSURE_SEEDS = ("premonition_swarm_screen", "premonition_swarm_marks", "premonition.train", "premonition.exp1",
                 "premonition.slices", "premonition.data", "premonition.preprocess", "premonition.identity",
                 "premonition.swarm", "premonition.flops", "premonition.pointer", "learnlab.step1", "learnlab.metrics",
                 "learnlab.policy", "learnlab.ckpt", "learnlab.tokenizer", "learnlab.readonly", "learnlab.train",
                 "memorylab.storage", "memorylab.experiment", "learnlab.village")


_CLOSURE_PROGRAM = """
import importlib, json, pkgutil, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(root), str(root / "scripts")]
for name in json.loads(sys.argv[2]):
    importlib.import_module(name)
village = importlib.import_module("learnlab.village")
for info in pkgutil.walk_packages(village.__path__, "learnlab.village."):
    importlib.import_module(info.name)
found = set()
for module in list(sys.modules.values()):
    path = getattr(module, "__file__", None)
    if not path or not Path(path).is_absolute():
        continue
    path = Path(path).resolve()
    if path.is_relative_to(root) and path.is_file() and path.relative_to(root).parts[0] != "tests":
        found.add(path.relative_to(root).as_posix())
print(json.dumps(sorted(found)))
"""


def import_closure(root: Path) -> list[str]:
    """Repo files of every module the run imports: CLOSURE_SEEDS (they cover the lazy, in-function imports of
    train_d / evaluate_d_checkpoint / the data build) plus every learnlab.village submodule. It runs in a FRESH
    interpreter, so modules imported by a caller (a test runner, say) never leak into the answer."""
    import subprocess
    out = subprocess.run([sys.executable, "-B", "-c", _CLOSURE_PROGRAM, str(Path(root).resolve()),
                          json.dumps(list(CLOSURE_SEEDS))], capture_output=True, text=True, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


MANIFEST_PATH = "scripts/premonition_swarm_manifest.txt"
# The one source of the screen's trainer settings: `cmd_train` passes them to train_d, and C0 builds its bench
# trainers from them (`fresh_trainer`), so the bench times exactly the workload the runs train.
RUN_SETTINGS = dict(flop_budget=1e30, lr=1e-3, warmup_steps=100, log_every=50, eval_every=0)
BENCH_SECONDS = float(T_CAP)                         # any set budget turns the diagnostics off

Log = Callable[[str], None]
log: Log = functools.partial(print, flush=True)


# ------------------------------------------------------------------ pure helpers (unit-tested)
def compute_T(d1_flops_per_s: float, *, target: float = F_TARGET, step: int = T_STEP, cap: int = T_CAP
              ) -> tuple[float, int]:
    """(T_raw, T): T_raw = target / D1 FLOP/s; T = min(cap, step * ceil(T_raw / step)) (RUNCARD-S0 section 1)."""
    if not (d1_flops_per_s > 0 and math.isfinite(d1_flops_per_s)):
        raise ValueError("D1 FLOP/s must be positive and finite")
    raw = target / d1_flops_per_s
    return raw, int(min(cap, step * max(1, math.ceil(raw / step))))


def t_raw_from_modes(seconds: Mapping[str, float], flops: Mapping[str, float], *, target: float = F_TARGET,
                     weights: Mapping[str, float] = None) -> float:
    """The seconds D1 needs for `target` FLOPs under the curriculum (RUNCARD-S0 section 1).

    A seconds-budget run splits its phases by TIME (`MiniTrainer.plan` reads train_seconds / seconds_budget):
    shares `weights` (0.05 gold, 0.25 teacher, 0.70 own) of T are spent in each mode at that mode's FLOP/s
    f_m / s_m. So D1 spends `target` FLOPs in T_raw = target / sum_m w_m x f_m / s_m, with s_m D1's seconds per
    update and f_m D1's FLOPs per update in mode m over the same timed batches. (Coordinator ruling Oct 20, round 3
    eighth pass, item 4: the time-share formula replaces the sixth pass's FLOP-share one.)"""
    weights = CURRICULUM_WEIGHTS if weights is None else weights
    for mode in MODES:
        if not (seconds[mode] > 0 and flops[mode] > 0 and math.isfinite(seconds[mode]) and math.isfinite(flops[mode])):
            raise ValueError(f"mode {mode}: seconds and FLOPs per update must be positive and finite")
    return target / sum(weights[mode] * flops[mode] / seconds[mode] for mode in MODES)


def projected_box_hours(T: float, eval_seconds: float, *, train_overhead: float,
                        eval_seconds_d1: Optional[float] = None, train_overhead_d1: Optional[float] = None,
                        runs: int = S0_RUNS, overhead: float = BOX_OVERHEAD,
                        process_margin: float = PROCESS_MARGIN_SECONDS) -> float:
    """The S0 box-hours (BOX-SPEC C0): half the runs are S0, half D1, each a train (T + its overhead outside T) and
    an eval, every one a fresh process (+ `process_margin` each); x `overhead`.

    `train_overhead` is the measured time a train step spends outside its T: caches, FLOP calibration, the final
    validation and the checkpoint save (review round 3, item 4). It is required, so no caller can leave it out.
    D1's eval and overhead are measured separately (ninth pass, item 5); without them D1 is charged at S0's."""
    eval_d1 = eval_seconds if eval_seconds_d1 is None else eval_seconds_d1
    over_d1 = train_overhead if train_overhead_d1 is None else train_overhead_d1
    half = runs / 2
    seconds = (half * (T + train_overhead + eval_seconds) + half * (T + over_d1 + eval_d1)
               + 2 * runs * process_margin)
    return seconds / 3600.0 * overhead


def steps_ratio(d1: Mapping[str, float], s0: Mapping[str, float], weights: Mapping[str, float] = None) -> float:
    """How many times fewer updates S0 gets in T than D1: sum_m w_m / s_m(D1) / sum_m w_m / s_m(S0), with s_m the
    seconds per update in mode m and w_m the curriculum's TIME shares (a seconds-budget run splits phases by time).
    The C0 stop-and-ask ratio (coordinator ruling Oct 20, ninth pass, blocking 2; RUNCARD-S0 §1)."""
    weights = CURRICULUM_WEIGHTS if weights is None else weights
    return (sum(weights[m] / d1[m] for m in MODES)) / (sum(weights[m] / s0[m] for m in MODES))


def stop_flags(ratio: float, T: float, eval_seconds: float, dph: float, *, train_overhead: float,
               eval_seconds_d1: Optional[float] = None, train_overhead_d1: Optional[float] = None
               ) -> dict[str, Any]:
    """The two C0 stop flags and their inputs. `ratio` is `steps_ratio(D1, S0m4)`."""
    hours = projected_box_hours(T, eval_seconds, train_overhead=train_overhead, eval_seconds_d1=eval_seconds_d1,
                                train_overhead_d1=train_overhead_d1)
    cost = hours * dph
    return {"ratio": ratio, "stop_ratio": STOP_RATIO, "stop_and_ask": bool(ratio > STOP_RATIO),
            "T": T, "eval_seconds_estimate": eval_seconds, "train_overhead_seconds": train_overhead,
            "eval_seconds_estimate_d1": eval_seconds_d1, "train_overhead_seconds_d1": train_overhead_d1,
            "process_margin_seconds": PROCESS_MARGIN_SECONDS,
            "projected_s0_box_hours": hours, "dph": dph,
            "projected_s0_cost_usd": cost, "money_cap_usd": MONEY_CAP_USD, "money_stop": bool(cost > MONEY_CAP_USD)}


def weighted(values: Mapping[str, float]) -> float:
    """Curriculum-weighted mean of per-mode values: 0.05 gold + 0.25 teacher + 0.70 own."""
    return sum(CURRICULUM_WEIGHTS[mode] * values[mode] for mode in MODES)


def median_of(values: Sequence[float]) -> float:
    return float(statistics.median(values))


def manifest_lines(root: Path) -> list[str]:
    return [f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}" for name in MANIFEST_FILES]


def check_manifest(root: Path, manifest: Path) -> list[str]:
    """Problems (empty: every listed file matches, and every file this runner pins is listed)."""
    problems: list[str] = []
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.partition("  ")
            listed[name.strip()] = digest.strip()
    for name in MANIFEST_FILES:
        if name not in listed:
            problems.append(f"{name}: not in {manifest}")
    for name, digest in listed.items():
        path = root / name
        if not path.is_file():
            problems.append(f"{name}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"{name}: sha256 differs from the manifest")
    return problems


def trim_history(report: dict[str, Any], keep: int = 5) -> dict[str, Any]:
    """The train report without the bulk of "history" (the last `keep` records stay)."""
    out = dict(report)
    history = out.get("history") or []
    out["history_total"] = len(history)
    out["history"] = history[-keep:]
    return out


# ------------------------------------------------------------------ environment
def make_budget(root: Path = ROOT):
    """The project's storage budget, configured as run.py configures it (copied from the pointer ablation)."""
    from memorylab.storage import Budget
    budget = Budget(
        root,
        RUNTIME.get("shared_roots", []) + RUNTIME.get("import_roots", []),
        hard=RUNTIME.get("hard_bytes", Budget.HARD),
        steady=RUNTIME.get("steady_bytes", Budget.STEADY),
    )
    budget.ensure_runtime_directories()
    return budget


def environment(device: str) -> dict[str, Any]:
    info: dict[str, Any] = {"python": platform.python_version(), "torch": torch.__version__,
                            "cuda": torch.version.cuda, "platform": platform.platform(),
                            "cpu_count": os.cpu_count(), "device": device}
    if device == "cuda" and torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["gpu_memory_bytes"] = torch.cuda.get_device_properties(0).total_memory
    return info


def require_device(device: str) -> None:
    if device == "cuda" and not torch.cuda.is_available():
        raise refused("--device cuda: CUDA is not available here. Nothing was run.")


def write_json(path: str, payload: Mapping[str, Any]) -> None:
    from premonition import exp1
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(exp1.jsonable(payload), indent=1, sort_keys=False) + "\n", encoding="utf-8")
    log(f"wrote {target} ({target.stat().st_size:,} bytes)")


def tokenizer_paths() -> tuple[str, str]:
    from premonition import identity
    path = identity.V2_TOKENIZER["path"]
    return path, path.replace(".json", ".manifest.json")


# ------------------------------------------------------------------ data
def cmd_data(args: argparse.Namespace) -> int:
    from learnlab import step1
    from premonition import identity
    budget = make_budget(Path(args.root))
    path, manifest = tokenizer_paths()
    started = time.perf_counter()
    data = step1.build_data(budget, visits=args.visits, seed=0, workers=max(1, args.workers),
                            tokenizer_path=path, tokenizer_manifest=manifest, log=log)
    status = identity.tokenizer_status(data.tokenizer)
    log(f"swarm-screen data: {data.rel} ({data.tag}); tokenizer {data.tokenizer_info['path']} "
        f"{data.tokenizer.digest[:12]} ({data.tokenizer.vocab_size} ids, status {status})")
    if args.size == "full" and data.tokenizer.vocab_size != VOCAB_V2:
        raise refused(f"tokenizer has {data.tokenizer.vocab_size} ids, the registered v2 tokenizer has {VOCAB_V2}")
    if data.tokenizer_info["path"] != path:
        raise refused(f"build_data used {data.tokenizer_info['path']}, not the registered {path}")
    if status != "v2":
        raise refused(f"tokenizer status is {status!r}, not the v2 contender tokenizer")
    write_json(args.out, {
        "command": "data", "data_rel": data.rel, "tag": data.tag, "tokenizer_path": path,
        "tokenizer_sha256": data.tokenizer.digest, "vocab_size": data.tokenizer.vocab_size,
        "tokenizer_status": status, "visits": str(args.visits), "size": args.size,
        "seconds": time.perf_counter() - started, "environment": environment("cpu")})
    return 0


# ------------------------------------------------------------------ c0
def open_caches(budget: Any, data_rel: str, tokenizer_path: str, workers: int):
    from learnlab.tokenizer import Tokenizer
    from premonition import data as pdata, preprocess
    tokenizer = Tokenizer.load(Path(budget.root) / tokenizer_path)
    detector = pdata.name_detector(budget, data_rel, workers=workers, log=log)
    train = pdata.load_or_build(budget, data_rel, "train", tokenizer, detector, workers=workers,
                                regime=preprocess.LABEL_FREE, log=log)
    return tokenizer, detector, train


LOSS_NAMES = ("loss", "lm", "ask", "ans", "halt")


def nonfinite_logged_steps(history: Sequence[Mapping[str, Any]]) -> list[Any]:
    """Steps of the FULL training history with a non-finite logged loss (or loss term). It is computed before
    `trim_history` keeps only the last 5 records, so M5's no-NaN check sees every window (round 3, fifth pass, 4)."""
    bad = []
    for record in history:
        values = [record.get(name) for name in LOSS_NAMES if record.get(name) is not None]
        if any(not math.isfinite(float(v)) for v in values):
            bad.append(record.get("step"))
    return bad


def run_trainer(model: Any, device: str, seconds: float):
    """The trainer a screen `train` step uses (`train_d` builds it through `d_trainer` with RUN_SETTINGS)."""
    from premonition.train import d_trainer
    return d_trainer(model, device, seed=0, seconds_budget=seconds, **RUN_SETTINGS)


def fresh_trainer(arm_config: Mapping[str, Any], size: str, vocab: int, device: str):
    """C0's bench trainer: EXACTLY the run's trainer (review round 3, fourth pass, item 1). It uses the same
    RUN_SETTINGS and has a seconds budget, so training diagnostics are off just as in the matched-T runs. The
    budget's value (BENCH_SECONDS) only sets the curriculum share and the stop, and the bench uses neither: it calls
    `_train_step` with fixed plans."""
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    torch.manual_seed(0)
    model = PremonitionMini(MiniConfig.preset("D", size, vocab_size=vocab, **arm_config))
    return run_trainer(model, device, BENCH_SECONDS)


def reset_peak(device: str) -> None:
    """Restart CUDA's peak-memory counter, which the run trainer's 14 GiB guard reads. Called before each probe and
    after a failed bench arm, so no earlier arm's peak can trip a later guard (round 3, ninth pass, item 4)."""
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()


def time_run(arm_config: Mapping[str, Any], mode: str, batches: Sequence[Any], *, size: str, vocab: int,
             device: str, warmup: int, timed: int, chunk: int) -> dict[str, Any]:
    """One fresh model, `warmup` untimed updates, then `timed` timed ones in chunks: s/update per chunk."""
    from premonition.train import Plan, _sync, planned_loops
    trainer = fresh_trainer(arm_config, size, vocab, device)
    config = trainer.model.config
    plan = Plan(mode, mode, P_OWN if mode == "own" else 0.0)
    reset_peak(device)
    for batch in batches[:warmup]:
        trainer._train_step(batch, plan, planned_loops(batch, mode, config), False)
    rows = list(batches[warmup:warmup + timed])
    chunks, total = [], 0.0
    for start in range(0, len(rows), chunk):
        part = rows[start:start + chunk]
        _sync(device)
        began = time.perf_counter()
        for batch in part:
            trainer._train_step(batch, plan, planned_loops(batch, mode, config), False)
        _sync(device)
        took = time.perf_counter() - began
        total += took
        chunks.append(took / len(part))
        trainer._check_memory()          # the run trainer's 14 GiB reserved guard (sixth pass, item 1): raises if over
    peak = torch.cuda.max_memory_allocated() if device == "cuda" else None
    del trainer
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return {"chunks": chunks, "round_value": median_of(chunks), "seconds": total, "updates": len(rows),
            "peak_allocated_bytes": peak}


def gpu_busy_fraction(arm_config: Mapping[str, Any], batches: Sequence[Any], *, size: str, vocab: int,
                      device: str, updates: int = 10, warmup: int = 3) -> Optional[float]:
    """Sum of CUDA kernel self time / wall time over `updates` own-mode updates (None off CUDA)."""
    if device != "cuda":
        return None
    from torch.profiler import ProfilerActivity, profile
    from premonition.train import Plan, _sync, planned_loops
    trainer = fresh_trainer(arm_config, size, vocab, device)
    config = trainer.model.config
    plan = Plan("own", "own", P_OWN)
    rows = [batches[i % len(batches)] for i in range(warmup + updates)]
    for batch in rows[:warmup]:
        trainer._train_step(batch, plan, planned_loops(batch, "own", config), False)
    _sync(device)
    with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as prof:
        began = time.perf_counter()
        for batch in rows[warmup:]:
            trainer._train_step(batch, plan, planned_loops(batch, "own", config), False)
        _sync(device)
        wall = time.perf_counter() - began
    kernel_us = 0.0
    for event in prof.key_averages():
        if str(getattr(event, "device_type", "")).endswith("CUDA"):
            kernel_us += float(getattr(event, "self_device_time_total", None)
                               or getattr(event, "self_cuda_time_total", 0.0))
    del trainer
    gc.collect()
    torch.cuda.empty_cache()
    return kernel_us * 1e-6 / wall


def curriculum_flops(fit: Any, batches: Sequence[Any], config: Any) -> dict[str, float]:
    """Mean fitted FLOPs per update in each mode over `batches`, and the curriculum-weighted mean."""
    from premonition.train import planned_loops
    per_mode = {mode: sum(fit(b.tokens.numel(), int(planned_loops(b, mode, config).sum())) for b in batches)
                / len(batches) for mode in MODES}
    return {**per_mode, "weighted": weighted(per_mode)}


def eval_purpose(size: str, purpose: Optional[str] = None) -> Optional[str]:
    """None (= primary) for the full preset. The tiny preset (dry run only) differs from the contender's shape,
    which `identity.admit` refuses for primary and diagnostic reports, so it is scored as "legacy" (shape
    problems allowed and reported; tokenizer, vocabulary and configuration checks still block)."""
    return purpose or ("legacy" if size == "tiny" else None)


def measure_eval_seconds(budget: Any, data_rel: str, tokenizer_path: str, *, size: str, vocab: int, device: str,
                         workers: int, ckpt_dir: str = CKPT_DIR, arm: str = "S0") -> dict[str, Any]:
    """Seconds of one validation eval of a fresh (untrained) `arm` checkpoint, the second pass (caches warm).

    S0 does not halt, so an untrained S0 does the same work as a trained one. D1 halts, so its probe is the worst
    case: HALT never fires and ASK always does, so it runs all max_loops loops (ninth pass, item 5: D1's evals are
    measured, not charged at S0's rate). The first pass is reported too (it builds the validation cache)."""
    from premonition import preprocess
    from premonition.train import _sync, checkpoint_config, evaluate_d_checkpoint, save_mini_checkpoint
    from learnlab.tokenizer import Tokenizer
    from premonition import data as pdata
    reset_peak(device)
    trainer = fresh_trainer(ARMS[arm], size, vocab, device)
    if arm == "D1":
        heads = trainer.model.heads
        with torch.no_grad():
            heads.halt.weight.zero_(), heads.halt.bias.fill_(-20.0)
            if heads.ask is not None:
                heads.ask.weight.zero_(), heads.ask.bias.fill_(20.0)
    tokenizer = Tokenizer.load(Path(budget.root) / tokenizer_path)
    detector = pdata.name_detector(budget, data_rel, workers=workers, log=log)
    config = checkpoint_config(trainer, contender="D", tokenizer={"path": tokenizer_path, "sha256": tokenizer.digest},
                               detector=detector.digest, data={"dir": data_rel, "tag": Path(data_rel).name},
                               preprocess_identity=preprocess.identity(preprocess.LABEL_FREE))
    relative = f"{ckpt_dir}/c0-evalprobe-{arm}-{time.time_ns()}"
    save_mini_checkpoint(budget, relative, trainer, config)
    seconds = []
    try:
        for _ in range(2):
            began = time.perf_counter()
            evaluate_d_checkpoint(budget, relative, split="validation", device=device, workers=workers,
                                  purpose=eval_purpose(size), log=lambda message: None)
            _sync(device)
            seconds.append(time.perf_counter() - began)
    finally:
        shutil.rmtree(Path(budget.root) / relative, ignore_errors=True)
    return {"first_pass_seconds": seconds[0], "second_pass_seconds": seconds[1], "estimate_seconds": seconds[1]}


def train_probe(budget: Any, data_rel: str, tokenizer_path: str, *, size: str, device: str, workers: int,
                ckpt_dir: str, seconds: float, max_tokens: int, arm: str) -> dict[str, Any]:
    """The probe itself (run in its own process by `measure_train_overhead`): one short `train_d` with a `seconds`
    budget and per-phase memory logging; the probe checkpoint is deleted afterwards."""
    from premonition.train import _sync, train_d
    relative = f"{ckpt_dir}/c0-trainprobe-{arm}-{time.time_ns()}"
    began = time.perf_counter()
    try:
        report = train_d(budget, data_rel=data_rel, tokenizer_path=tokenizer_path, seconds_budget=seconds,
                         swarm=ARMS[arm] or None, seed=0, device=device, size=size, max_tokens=max_tokens,
                         workers=workers, checkpoint=relative, memory_phases=True, log=lambda message: None,
                         **RUN_SETTINGS)
        _sync(device)
    finally:
        shutil.rmtree(Path(budget.root) / relative, ignore_errors=True)
    return {"status": report.get("status"), "error": report.get("error"), "train_seconds": report.get("train_seconds"),
            "inner_wall_seconds": time.perf_counter() - began, "memory_phases": report.get("memory_phases")}


def phase_summary(phases: Optional[Sequence[Mapping[str, Any]]]) -> str:
    """"name alloc/reserved GiB" per closed memory phase (CUDA only)."""
    parts = []
    for p in phases or []:
        if p.get("peak_reserved_bytes") is not None:
            parts.append(f"{p['phase']} {p['peak_allocated_bytes'] / 2**30:.2f}/{p['peak_reserved_bytes'] / 2**30:.2f}")
    return ", ".join(parts) or "no CUDA phases"


def measure_train_overhead(budget: Any, data_rel: str, tokenizer_path: str, *, size: str, device: str, workers: int,
                           ckpt_dir: str, seconds: float, max_tokens: int, arm: str = "S0") -> dict[str, Any]:
    """Seconds a train step spends OUTSIDE its T (review round 3, item 4): one short `train_d` of `arm` with a
    `seconds` budget, wall time minus `train_seconds`. That covers start-up, caches, FLOP calibration, the final
    validation and the save. It runs in a FRESH subprocess, as each real train does, after the parent frees what it
    can (coordinator ruling on RUN2-C0-STOP, option ii), and logs peak allocated / reserved memory per phase (start,
    calibration, step1, train, validation, save), so an abort names its phase. An abort stops C0."""
    import subprocess
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "probe.json"
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "train-probe", "--arm", arm,
                   "--seconds", str(seconds), "--data-rel", data_rel, "--tokenizer", tokenizer_path,
                   "--root", str(budget.root), "--device", device, "--size", size, "--workers", str(workers),
                   "--ckpt-dir", ckpt_dir, "--max-tokens", str(max_tokens), "--out", str(out)]
        began = time.perf_counter()
        done = subprocess.run(command, capture_output=True, text=True)
        wall = time.perf_counter() - began
        if done.returncode != 0 or not out.is_file():
            raise c0_stop(f"c0: the {arm} train-overhead probe process failed (rc {done.returncode}): "
                          f"{(done.stderr or done.stdout)[-300:]}")
        probe = json.loads(out.read_text(encoding="utf-8"))
    phases = phase_summary(probe.get("memory_phases"))
    if probe.get("status") != "completed":                  # sixth pass, item 1: an aborted probe stops C0
        raise c0_stop(f"c0: the {arm} train-overhead probe did not complete (status {probe.get('status')!r}: "
                      f"{str(probe.get('error'))[:160]}); memory per phase, allocated/reserved GiB: {phases}; "
                      f"{arm} would abort the same way")
    trained = float(probe["train_seconds"])
    return {"probe_seconds": seconds, "wall_seconds": wall, "train_seconds": trained,
            "overhead_seconds": max(0.0, wall - trained), "fresh_process": True,
            "memory_phases": probe.get("memory_phases"), "memory_summary_gib": phases}


def cmd_train_probe(args: argparse.Namespace) -> int:
    require_device(args.device)
    result = train_probe(make_budget(Path(args.root)), args.data_rel, args.tokenizer, size=args.size,
                         device=args.device, workers=max(1, args.workers), ckpt_dir=args.ckpt_dir,
                         seconds=args.seconds, max_tokens=args.max_tokens, arm=args.arm)
    Path(args.out).write_text(json.dumps(result, default=str), encoding="utf-8")
    return 0


REQUIRED_ARMS = ("D1", "S0m4")                       # without these two the bench cannot set T


def bench(run_one: Callable[[Mapping[str, Any], str], dict[str, Any]], *, rounds: int, device: str,
          log: Callable[[str], None]) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], dict[str, str]]:
    """C0's interleaved rounds over C0_ARMS x MODES: (runs, failed). An arm that trips the run trainer's memory
    guard or runs out of CUDA memory is reported as failed and skipped from then on. A failed REQUIRED arm stops
    C0 at once (round 3, eighth pass, item 7: no more billed benching). The cache is emptied AFTER the except
    block, once the traceback (and the arm's tensors it holds) is released (item 6)."""
    from learnlab.train import MemoryGuardError
    runs: dict[str, dict[str, list[dict[str, Any]]]] = {arm: {mode: [] for mode in MODES} for arm in C0_ARMS}
    failed: dict[str, str] = {}
    for round_index in range(1, rounds + 1):
        for arm, config in C0_ARMS.items():
            if arm in failed:
                continue
            for mode in MODES:
                problem = None
                try:
                    result = run_one(config, mode)
                except MemoryGuardError as error:                    # the run trainer's guard: the arm cannot train
                    problem = f"memory guard in {mode}: {str(error)[:200]}"
                except torch.cuda.OutOfMemoryError as error:         # the arm is reported as not runnable
                    problem = f"CUDA out of memory in {mode}: {str(error)[:200]}"
                if problem is not None:                              # outside the handler: its frames are gone
                    failed[arm] = problem
                    log(f"c0: {arm} {problem}")
                    gc.collect()
                    if device == "cuda":
                        torch.cuda.empty_cache()
                    reset_peak(device)
                    if arm in REQUIRED_ARMS:
                        raise c0_stop(f"c0: {arm} could not run ({problem}); the bench cannot set T")
                    break
                runs[arm][mode].append(result)
                log(f"c0 round {round_index} {arm:>5} {mode:>7}: {result['round_value']:.4f} s/update "
                    f"(chunks {', '.join(f'{c:.3f}' for c in result['chunks'])})")
    return runs, failed


def cmd_c0(args: argparse.Namespace) -> int:
    from premonition.train import mini_train_config  # noqa: F401  (import check before the long bench)
    if args.t_override is not None and args.size != "tiny":
        raise refused("c0: --t-override is for the tiny CPU dry run only; the real T is the registered formula")
    from premonition import data as pdata
    require_device(args.device)
    root = Path(args.root)
    budget = make_budget(root)
    started = time.perf_counter()
    tokenizer, detector, train_cache = open_caches(budget, args.data_rel, args.tokenizer, max(1, args.workers))
    vocab = tokenizer.vocab_size
    if args.size == "full" and vocab != VOCAB_V2:
        raise refused(f"tokenizer has {vocab} ids, the registered v2 tokenizer has {VOCAB_V2}")
    need = args.warmup + args.timed
    stream = pdata.batches(train_cache, args.max_tokens, seed=0, epochs=None, max_visits=48)
    fixed = list(itertools.islice(stream, need))                      # drawn once, label-free, shared by all runs
    if len(fixed) < need:
        raise c0_stop(f"only {len(fixed)} batches could be drawn, need {need}")
    log(f"c0: {need} fixed batches ({sum(b.tokens.numel() for b in fixed):,} padded tokens), "
        f"{args.rounds} rounds x {len(C0_ARMS)} arms x {len(MODES)} modes, warmup {args.warmup} "
        f"timed {args.timed} chunk {args.chunk}, size {args.size} on {args.device}")
    runs, failed = bench(lambda config, mode: time_run(config, mode, fixed, size=args.size, vocab=vocab,
                                                       device=args.device, warmup=args.warmup, timed=args.timed,
                                                       chunk=args.chunk),
                         rounds=args.rounds, device=args.device, log=log)
    per_arm: dict[str, Any] = {}
    for arm in C0_ARMS:
        if arm in failed:
            per_arm[arm] = {"error": failed[arm]}
            continue
        by_mode = {mode: median_of([r["round_value"] for r in runs[arm][mode]]) for mode in MODES}
        peaks = [r["peak_allocated_bytes"] for mode in MODES for r in runs[arm][mode]
                 if r["peak_allocated_bytes"] is not None]
        means = {mode: sum(r["seconds"] for r in runs[arm][mode]) / sum(r["updates"] for r in runs[arm][mode])
                 for mode in MODES}                    # total timed seconds / timed updates (ninth pass, item 7)
        per_arm[arm] = {"s_per_update": by_mode, "weighted_s_per_update": weighted(by_mode),
                        "mean_s_per_update": means,
                        "peak_allocated_bytes": max(peaks) if peaks else None,
                        "round_values": {mode: [r["round_value"] for r in runs[arm][mode]] for mode in MODES}}
    # D1's FLOP fit and FLOP/s
    d1 = fresh_trainer(ARMS["D1"], args.size, vocab, args.device)
    fit = d1.calibrate(fixed[:4])
    timed_rows = fixed[args.warmup:args.warmup + args.timed]                  # the batches the seconds were timed on
    flops = curriculum_flops(fit, timed_rows, d1.model.config)
    t_raw_modes = t_raw_from_modes(per_arm["D1"]["mean_s_per_update"], flops)   # means, like the FLOPs (item 7)
    d1_flops_per_s = F_TARGET / t_raw_modes                    # time-share-weighted curriculum FLOP/s
    t_raw, t_formula = compute_T(d1_flops_per_s)
    T = int(args.t_override) if args.t_override is not None else t_formula
    log(f"c0: D1 {per_arm['D1']['weighted_s_per_update']:.4f} s/update weighted, {flops['weighted']:.4e} FLOPs/update "
        f"-> {d1_flops_per_s:.4e} FLOP/s; T_raw {t_raw:.1f} s, T {t_formula}"
        f"{'' if args.t_override is None else f' (overridden to {T})'}")
    del d1
    gc.collect()
    busy = {"D1": gpu_busy_fraction(C0_ARMS["D1"], fixed, size=args.size, vocab=vocab, device=args.device),
            "S0m4": gpu_busy_fraction(C0_ARMS["S0m4"], fixed, size=args.size, vocab=vocab, device=args.device)}
    probes = {arm: measure_eval_seconds(budget, args.data_rel, args.tokenizer, size=args.size, vocab=vocab,
                                        device=args.device, workers=max(1, args.workers), ckpt_dir=args.ckpt_dir,
                                        arm=arm) for arm in ("S0", "D1")}
    train_probes = {arm: measure_train_overhead(budget, args.data_rel, args.tokenizer, size=args.size,
                                                device=args.device, workers=max(1, args.workers),
                                                ckpt_dir=args.ckpt_dir, seconds=args.overhead_probe_seconds,
                                                max_tokens=args.max_tokens, arm=arm) for arm in ("S0", "D1")}
    probe, train_probe = probes["S0"], train_probes["S0"]
    ratio = steps_ratio(per_arm["D1"]["mean_s_per_update"], per_arm["S0m4"]["mean_s_per_update"])
    flags = stop_flags(ratio, T, probe["estimate_seconds"], args.dph, train_overhead=train_probe["overhead_seconds"],
                       eval_seconds_d1=probes["D1"]["estimate_seconds"],
                       train_overhead_d1=train_probes["D1"]["overhead_seconds"])
    settings = {"rounds": args.rounds, "warmup": args.warmup, "timed": args.timed, "chunk": args.chunk,
                "max_tokens": args.max_tokens}
    log(f"c0: S0m4/D1 steps-in-T ratio {flags['ratio']:.3f} (stop above {STOP_RATIO}): stop_and_ask "
        f"{flags['stop_and_ask']}; projected S0 {flags['projected_s0_box_hours']:.3f} box-hours x ${args.dph}/h = "
        f"${flags['projected_s0_cost_usd']:.3f} (cap ${MONEY_CAP_USD}): money_stop {flags['money_stop']}")
    write_json(args.out, {
        "command": "c0", "size": args.size, "device": args.device, "data_rel": args.data_rel,
        "tag": Path(args.data_rel).name, "tokenizer_path": args.tokenizer, "tokenizer_sha256": tokenizer.digest,
        "vocab_size": vocab, "settings": {**settings, "p_own": P_OWN, "weights": CURRICULUM_WEIGHTS},
        "registered_settings": settings == REGISTERED_C0, "dph": args.dph,
        "arms": per_arm, "weighted_flops_per_update": flops, "flop_fit": {"a": fit.a, "b": fit.b, "worst": fit.worst},
        "d1_flops_per_s": d1_flops_per_s, "f_target": F_TARGET, "T_raw": t_raw, "T_formula": t_formula,
        "t_raw_curriculum": t_raw_modes, "t_override": args.t_override, "T": T, "gpu_busy": busy, "eval_probe": probe, "train_probe": train_probe,
        "eval_probe_d1": probes["D1"], "train_probe_d1": train_probes["D1"],
        "ratio_s0m4_over_d1": flags["ratio"], "stop_and_ask": flags["stop_and_ask"],
        "money_stop": flags["money_stop"], "flags": flags,
        "ratios_over_d1": {arm: steps_ratio(per_arm["D1"]["mean_s_per_update"], v["mean_s_per_update"])
                           for arm, v in per_arm.items() if "mean_s_per_update" in v},   # steps-in-T ratios
        "seconds": time.perf_counter() - started, "environment": environment(args.device)})
    return 0


# ------------------------------------------------------------------ train, eval
def checkpoint_free(root: Path, relative: str) -> None:
    """Refuse BEFORE training if the checkpoint already exists (review round 3, item b): `save_checkpoint` never
    overwrites, so a rerun would spend its whole T and then fail at the save, leaving no train JSON."""
    target = Path(root) / relative
    if target.exists():
        raise refused(f"REFUSED before training: checkpoint {target} already exists (a rerun after a VOID or a "
                         f"partial PART=s0 run). Move it aside or pass a fresh --ckpt-dir; nothing was trained.")


def cmd_train(args: argparse.Namespace) -> int:
    from premonition.train import _sync, train_d
    require_device(args.device)
    checkpoint = f"{args.ckpt_dir}/{args.arm}-s{args.seed}"
    checkpoint_free(Path(args.root), checkpoint)
    budget = make_budget(Path(args.root))
    began = time.perf_counter()
    report = train_d(budget, data_rel=args.data_rel, tokenizer_path=args.tokenizer, seconds_budget=args.seconds,
                     swarm=ARMS[args.arm] or None, seed=args.seed, device=args.device, size=args.size,
                     max_tokens=args.max_tokens, workers=max(1, args.workers), checkpoint=checkpoint, log=log,
                     **RUN_SETTINGS)
    report["nonfinite_logged_steps"] = nonfinite_logged_steps(report.get("history") or [])   # before trimming
    report = trim_history(report)
    report.update(arm=args.arm, seed=args.seed, seconds_requested=args.seconds,
                  wall_seconds=time.perf_counter() - began, size=args.size, environment=environment(args.device))
    write_json(args.out, report)
    return 0 if report.get("status") == "completed" else 5          # 2 means "refused"; 5 = a step failed


def cmd_eval(args: argparse.Namespace) -> int:
    from premonition.train import evaluate_d_checkpoint
    require_device(args.device)
    budget = make_budget(Path(args.root))
    began = time.perf_counter()
    report = evaluate_d_checkpoint(budget, args.checkpoint, split="validation", device=args.device,
                                   lesion=args.lesion, workers=max(1, args.workers),
                                   purpose=eval_purpose(args.size, args.purpose), log=log)
    report["wall_seconds"] = time.perf_counter() - began
    write_json(args.out, report)
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    root = Path(args.root)
    target = root / MANIFEST_PATH
    if args.check:
        problems = check_manifest(root, target)
        problems += [f"{name}: imported by the run but not pinned in MANIFEST_FILES"
                     for name in import_closure(root) if name not in MANIFEST_FILES]
        for problem in problems:
            print(problem, file=sys.stderr)
        print("manifest OK" if not problems else f"manifest FAILED ({len(problems)} problems)")
        return 1 if problems else 0
    target.write_text("\n".join(manifest_lines(root)) + "\n", encoding="utf-8")
    print(f"wrote {target}")
    return 0


# ------------------------------------------------------------------ command line
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--runtime", default=str(RUNTIME_PATH))          # consumed by the bootstrap above
    sub = parser.add_subparsers(dest="command", required=True)

    def common(one: argparse.ArgumentParser, *, out: bool = True) -> None:
        one.add_argument("--root", default=str(ROOT), help="project root (default: the repository)")
        one.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
        one.add_argument("--size", choices=("full", "tiny"), default="full", help="tiny = CPU dry run only")
        one.add_argument("--workers", type=int, default=0, help="data/replay processes; 0 = auto")
        if out:
            one.add_argument("--out", required=True)

    one = sub.add_parser("data")
    common(one)
    one.add_argument("--visits", default="large", help="large, or tiny for the dry run")
    one = sub.add_parser("c0", allow_abbrev=False)   # no "--t-o" for "--t-override" (ninth pass, blocking 1)
    common(one)
    one.add_argument("--data-rel", required=True)
    one.add_argument("--tokenizer", required=True)
    for name in ("rounds", "warmup", "timed", "chunk"):                  # defaults: the registered protocol
        one.add_argument(f"--{name}", type=int, default=REGISTERED_C0[name])
    one.add_argument("--max-tokens", type=int, default=REGISTERED_C0["max_tokens"])
    one.add_argument("--dph", type=float, default=0.0, help="billed $/h (0 = the money check cannot fire)")
    one.add_argument("--t-override", type=float, default=None, help="dry run only: T instead of the formula")
    one.add_argument("--overhead-probe-seconds", type=float, default=20.0,
                     help="seconds budget of the train-overhead probe (one short S0 train_d)")
    one.add_argument("--ckpt-dir", default=CKPT_DIR, help="folder for the eval-time probe checkpoint (removed)")
    one = sub.add_parser("train")
    common(one)
    one.add_argument("--arm", choices=sorted(ARMS), required=True)
    one.add_argument("--seed", type=int, required=True)
    one.add_argument("--seconds", type=float, required=True)
    one.add_argument("--data-rel", required=True)
    one.add_argument("--tokenizer", required=True)
    one.add_argument("--max-tokens", type=int, default=55_000)
    one.add_argument("--ckpt-dir", default=CKPT_DIR, help="checkpoint folder, relative to --root")
    one = sub.add_parser("train-probe", help="C0's train-overhead probe, run in its own process by c0")
    common(one)
    one.add_argument("--arm", choices=sorted(ARMS), required=True)
    one.add_argument("--seconds", type=float, required=True)
    one.add_argument("--data-rel", required=True)
    one.add_argument("--tokenizer", required=True)
    one.add_argument("--max-tokens", type=int, default=REGISTERED_C0["max_tokens"])
    one.add_argument("--ckpt-dir", default=CKPT_DIR)
    one = sub.add_parser("eval")
    common(one)
    one.add_argument("--checkpoint", required=True, help="checkpoint folder, relative to --root")
    one.add_argument("--lesion", choices=("board", "notes", "cards"), default=None)
    one.add_argument("--purpose", default=None, help="identity purpose; default primary (legacy for --size tiny)")
    one = sub.add_parser("manifest")
    one.add_argument("--root", default=str(ROOT))
    one.add_argument("--check", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "workers", 1) == 0:
        args.workers = max(1, min(12, (os.cpu_count() or 2) - 1))
    try:
        return {"data": cmd_data, "c0": cmd_c0, "train": cmd_train, "eval": cmd_eval,
                "manifest": cmd_manifest, "train-probe": cmd_train_probe}[args.command](args)
    except Stop as stop:
        print(("REFUSED: " if stop.code == REFUSED else "C0 STOP: ") + stop.message, file=sys.stderr, flush=True)
        return stop.code


if __name__ == "__main__":
    raise SystemExit(main())
