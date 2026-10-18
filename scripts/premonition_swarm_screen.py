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
import time  # noqa: E402
from typing import Any, Callable, Mapping, Optional, Sequence  # noqa: E402

import torch  # noqa: E402

# ------------------------------------------------------------------ the registered arms and numbers
ARMS: dict[str, dict[str, Any]] = {
    "D1": {},
    "S0": dict(thinkers=4, swarm_board=False, swarm_rounds=4, board_cards=16),
    "S1": dict(thinkers=4, swarm_board=True, swarm_rounds=4, board_cards=16),
}
C0_ARMS: dict[str, dict[str, Any]] = {
    "D1": {}, "S0m2": dict(thinkers=2), "S0m4": ARMS["S0"], "S0m8": dict(thinkers=8), "S1m4": ARMS["S1"],
}
MODES = ("gold", "teacher", "own")
P_OWN = 0.75                                         # the curriculum's flat p_own in the own phase
CURRICULUM_WEIGHTS = {"gold": 0.05, "teacher": 0.25, "own": 0.70}
F_TARGET = 2.6e16                                    # RUNCARD-S0 section 1: D1's FLOPs that define T
T_STEP, T_CAP = 300, 3600
STOP_RATIO = 2.5                                     # FUNDING-BID C0 rule
MONEY_CAP_USD = 3.50                                 # the S0 hard cap
BOX_OVERHEAD = 1.15
S0_RUNS = 6                                          # D1 and S0 x seeds 0-2: trains and validation evals
VOCAB_V2 = 7068
CKPT_DIR = "checkpoints/swarm-screen"
MANIFEST_FILES = [f"premonition/{name}.py" for name in
                  ("config", "model", "swarm", "train", "store", "batch", "data", "exp1", "slices",
                   "identity", "preprocess", "flops")] + [
    "learnlab/step1.py", "learnlab/metrics.py", "learnlab/policy.py",     # data build, p-values, alpha / margin
    "scripts/premonition_swarm_screen.py", "scripts/premonition_swarm_marks.py", "scripts/premonition_swarm_box.sh"]
MANIFEST_PATH = "scripts/premonition_swarm_manifest.txt"

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


def projected_box_hours(T: float, eval_seconds: float, *, runs: int = S0_RUNS, overhead: float = BOX_OVERHEAD
                        ) -> float:
    """(runs x T + runs x measured eval estimate) / 3600 x overhead: the S0 box-hours (BOX-SPEC C0)."""
    return (runs * T + runs * eval_seconds) / 3600.0 * overhead


def stop_flags(s0m4_weighted: float, d1_weighted: float, T: float, eval_seconds: float, dph: float
               ) -> dict[str, Any]:
    """The two C0 stop flags and their inputs."""
    ratio = s0m4_weighted / d1_weighted
    hours = projected_box_hours(T, eval_seconds)
    cost = hours * dph
    return {"ratio": ratio, "stop_ratio": STOP_RATIO, "stop_and_ask": bool(ratio > STOP_RATIO),
            "T": T, "eval_seconds_estimate": eval_seconds, "projected_s0_box_hours": hours, "dph": dph,
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
        raise SystemExit("--device cuda: CUDA is not available here. Nothing was run.")


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
        raise SystemExit(f"tokenizer has {data.tokenizer.vocab_size} ids, the registered v2 tokenizer has {VOCAB_V2}")
    if data.tokenizer_info["path"] != path:
        raise SystemExit(f"build_data used {data.tokenizer_info['path']}, not the registered {path}")
    if status != "v2":
        raise SystemExit(f"tokenizer status is {status!r}, not the v2 contender tokenizer")
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


def fresh_trainer(arm_config: Mapping[str, Any], size: str, vocab: int, device: str):
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    from premonition.train import MiniTrainer, mini_train_config
    torch.manual_seed(0)
    model = PremonitionMini(MiniConfig.preset("D", size, vocab_size=vocab, **arm_config))
    return MiniTrainer(model, mini_train_config(), device, flop_budget=1e30, seed=0)


def _sync(device: str) -> None:
    if device == "cuda":
        torch.cuda.synchronize()


def time_run(arm_config: Mapping[str, Any], mode: str, batches: Sequence[Any], *, size: str, vocab: int,
             device: str, warmup: int, timed: int, chunk: int) -> dict[str, Any]:
    """One fresh model, `warmup` untimed updates, then `timed` timed ones in chunks: s/update per chunk."""
    from premonition.train import Plan, planned_loops
    trainer = fresh_trainer(arm_config, size, vocab, device)
    config = trainer.model.config
    plan = Plan(mode, mode, P_OWN if mode == "own" else 0.0)
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for batch in batches[:warmup]:
        trainer._train_step(batch, plan, planned_loops(batch, mode, config), False)
    rows = list(batches[warmup:warmup + timed])
    chunks = []
    for start in range(0, len(rows), chunk):
        part = rows[start:start + chunk]
        _sync(device)
        began = time.perf_counter()
        for batch in part:
            trainer._train_step(batch, plan, planned_loops(batch, mode, config), False)
        _sync(device)
        chunks.append((time.perf_counter() - began) / len(part))
    peak = torch.cuda.max_memory_allocated() if device == "cuda" else None
    del trainer
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return {"chunks": chunks, "round_value": median_of(chunks), "peak_allocated_bytes": peak}


def gpu_busy_fraction(arm_config: Mapping[str, Any], batches: Sequence[Any], *, size: str, vocab: int,
                      device: str, updates: int = 10, warmup: int = 3) -> Optional[float]:
    """Sum of CUDA kernel self time / wall time over `updates` own-mode updates (None off CUDA)."""
    if device != "cuda":
        return None
    from torch.profiler import ProfilerActivity, profile
    from premonition.train import Plan, planned_loops
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
                         workers: int, ckpt_dir: str = CKPT_DIR) -> dict[str, Any]:
    """Seconds of one validation eval of a fresh (untrained) S0 checkpoint, the second pass (caches warm).

    S0 does not halt, so an untrained S0 does the same work as a trained one; D1's six-run share is charged at
    S0's rate, which is the larger. The first pass is reported too (it builds the validation cache)."""
    from premonition import preprocess
    from premonition.train import checkpoint_config, evaluate_d_checkpoint, save_mini_checkpoint
    from learnlab.tokenizer import Tokenizer
    from premonition import data as pdata
    trainer = fresh_trainer(ARMS["S0"], size, vocab, device)
    tokenizer = Tokenizer.load(Path(budget.root) / tokenizer_path)
    detector = pdata.name_detector(budget, data_rel, workers=workers, log=log)
    config = checkpoint_config(trainer, contender="D", tokenizer={"path": tokenizer_path, "sha256": tokenizer.digest},
                               detector=detector.digest, data={"dir": data_rel, "tag": Path(data_rel).name},
                               preprocess_identity=preprocess.identity(preprocess.LABEL_FREE))
    relative = f"{ckpt_dir}/c0-evalprobe-{time.time_ns()}"
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


def cmd_c0(args: argparse.Namespace) -> int:
    from premonition.train import mini_train_config  # noqa: F401  (import check before the long bench)
    from premonition import data as pdata
    require_device(args.device)
    root = Path(args.root)
    budget = make_budget(root)
    started = time.perf_counter()
    tokenizer, detector, train_cache = open_caches(budget, args.data_rel, args.tokenizer, max(1, args.workers))
    vocab = tokenizer.vocab_size
    if args.size == "full" and vocab != VOCAB_V2:
        raise SystemExit(f"tokenizer has {vocab} ids, the registered v2 tokenizer has {VOCAB_V2}")
    need = args.warmup + args.timed
    stream = pdata.batches(train_cache, args.max_tokens, seed=0, epochs=None, max_visits=48)
    fixed = list(itertools.islice(stream, need))                      # drawn once, label-free, shared by all runs
    if len(fixed) < need:
        raise SystemExit(f"only {len(fixed)} batches could be drawn, need {need}")
    log(f"c0: {need} fixed batches ({sum(b.tokens.numel() for b in fixed):,} padded tokens), "
        f"{args.rounds} rounds x {len(C0_ARMS)} arms x {len(MODES)} modes, warmup {args.warmup} "
        f"timed {args.timed} chunk {args.chunk}, size {args.size} on {args.device}")
    runs: dict[str, dict[str, list[dict[str, Any]]]] = {arm: {mode: [] for mode in MODES} for arm in C0_ARMS}
    failed: dict[str, str] = {}
    for round_index in range(1, args.rounds + 1):
        for arm, config in C0_ARMS.items():
            if arm in failed:
                continue
            for mode in MODES:
                try:
                    result = time_run(config, mode, fixed, size=args.size, vocab=vocab, device=args.device,
                                      warmup=args.warmup, timed=args.timed, chunk=args.chunk)
                except torch.cuda.OutOfMemoryError as error:         # the arm is reported as not runnable
                    failed[arm] = f"CUDA out of memory in {mode}: {str(error)[:200]}"
                    log(f"c0: {arm} {failed[arm]}")
                    gc.collect()
                    torch.cuda.empty_cache()
                    break
                runs[arm][mode].append(result)
                log(f"c0 round {round_index} {arm:>5} {mode:>7}: {result['round_value']:.4f} s/update "
                    f"(chunks {', '.join(f'{c:.3f}' for c in result['chunks'])})")
    for required in ("D1", "S0m4"):
        if required in failed:
            raise SystemExit(f"c0: {required} could not run ({failed[required]}); the bench cannot set T")
    per_arm: dict[str, Any] = {}
    for arm in C0_ARMS:
        if arm in failed:
            per_arm[arm] = {"error": failed[arm]}
            continue
        by_mode = {mode: median_of([r["round_value"] for r in runs[arm][mode]]) for mode in MODES}
        peaks = [r["peak_allocated_bytes"] for mode in MODES for r in runs[arm][mode]
                 if r["peak_allocated_bytes"] is not None]
        per_arm[arm] = {"s_per_update": by_mode, "weighted_s_per_update": weighted(by_mode),
                        "peak_allocated_bytes": max(peaks) if peaks else None,
                        "round_values": {mode: [r["round_value"] for r in runs[arm][mode]] for mode in MODES}}
    # D1's FLOP fit and FLOP/s
    d1 = fresh_trainer(ARMS["D1"], args.size, vocab, args.device)
    fit = d1.calibrate(fixed[:4])
    flops = curriculum_flops(fit, fixed, d1.model.config)
    d1_flops_per_s = flops["weighted"] / per_arm["D1"]["weighted_s_per_update"]
    t_raw, t_formula = compute_T(d1_flops_per_s)
    T = int(args.t_override) if args.t_override is not None else t_formula
    log(f"c0: D1 {per_arm['D1']['weighted_s_per_update']:.4f} s/update weighted, {flops['weighted']:.4e} FLOPs/update "
        f"-> {d1_flops_per_s:.4e} FLOP/s; T_raw {t_raw:.1f} s, T {t_formula}"
        f"{'' if args.t_override is None else f' (overridden to {T})'}")
    del d1
    gc.collect()
    busy = {"D1": gpu_busy_fraction(C0_ARMS["D1"], fixed, size=args.size, vocab=vocab, device=args.device),
            "S0m4": gpu_busy_fraction(C0_ARMS["S0m4"], fixed, size=args.size, vocab=vocab, device=args.device)}
    probe = measure_eval_seconds(budget, args.data_rel, args.tokenizer, size=args.size, vocab=vocab,
                                 device=args.device, workers=max(1, args.workers), ckpt_dir=args.ckpt_dir)
    flags = stop_flags(per_arm["S0m4"]["weighted_s_per_update"], per_arm["D1"]["weighted_s_per_update"], T,
                       probe["estimate_seconds"], args.dph)
    log(f"c0: S0m4/D1 weighted ratio {flags['ratio']:.3f} (stop above {STOP_RATIO}): stop_and_ask "
        f"{flags['stop_and_ask']}; projected S0 {flags['projected_s0_box_hours']:.3f} box-hours x ${args.dph}/h = "
        f"${flags['projected_s0_cost_usd']:.3f} (cap ${MONEY_CAP_USD}): money_stop {flags['money_stop']}")
    write_json(args.out, {
        "command": "c0", "size": args.size, "device": args.device, "data_rel": args.data_rel,
        "tag": Path(args.data_rel).name, "tokenizer_path": args.tokenizer, "tokenizer_sha256": tokenizer.digest,
        "vocab_size": vocab, "settings": {"rounds": args.rounds, "warmup": args.warmup, "timed": args.timed,
                                          "chunk": args.chunk, "max_tokens": args.max_tokens,
                                          "p_own": P_OWN, "weights": CURRICULUM_WEIGHTS},
        "arms": per_arm, "weighted_flops_per_update": flops, "flop_fit": {"a": fit.a, "b": fit.b, "worst": fit.worst},
        "d1_flops_per_s": d1_flops_per_s, "f_target": F_TARGET, "T_raw": t_raw, "T_formula": t_formula,
        "t_override": args.t_override, "T": T, "gpu_busy": busy, "eval_probe": probe,
        "ratio_s0m4_over_d1": flags["ratio"], "stop_and_ask": flags["stop_and_ask"],
        "money_stop": flags["money_stop"], "flags": flags,
        "ratios_over_d1": {arm: v["weighted_s_per_update"] / per_arm["D1"]["weighted_s_per_update"]
                           for arm, v in per_arm.items() if "weighted_s_per_update" in v},
        "seconds": time.perf_counter() - started, "environment": environment(args.device)})
    return 0


# ------------------------------------------------------------------ train, eval
def cmd_train(args: argparse.Namespace) -> int:
    from premonition.train import train_d
    require_device(args.device)
    budget = make_budget(Path(args.root))
    began = time.perf_counter()
    report = train_d(budget, data_rel=args.data_rel, tokenizer_path=args.tokenizer, flop_budget=1e30,
                     seconds_budget=args.seconds, swarm=ARMS[args.arm] or None, seed=args.seed, device=args.device,
                     size=args.size, eval_every=0, max_tokens=args.max_tokens, workers=max(1, args.workers),
                     checkpoint=f"{args.ckpt_dir}/{args.arm}-s{args.seed}", log=log)
    report = trim_history(report)
    report.update(arm=args.arm, seed=args.seed, seconds_requested=args.seconds,
                  wall_seconds=time.perf_counter() - began, size=args.size, environment=environment(args.device))
    write_json(args.out, report)
    return 0 if report.get("status") == "completed" else 2


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
    one = sub.add_parser("c0")
    common(one)
    one.add_argument("--data-rel", required=True)
    one.add_argument("--tokenizer", required=True)
    one.add_argument("--rounds", type=int, default=3)
    one.add_argument("--warmup", type=int, default=10)
    one.add_argument("--timed", type=int, default=40)
    one.add_argument("--chunk", type=int, default=5)
    one.add_argument("--max-tokens", type=int, default=55_000)
    one.add_argument("--dph", type=float, default=0.0, help="billed $/h (0 = the money check cannot fire)")
    one.add_argument("--t-override", type=float, default=None, help="dry run only: T instead of the formula")
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
    return {"data": cmd_data, "c0": cmd_c0, "train": cmd_train, "eval": cmd_eval,
            "manifest": cmd_manifest}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
