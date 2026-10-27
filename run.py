"""No-install entry point. Configure tracked caches before importing PyTorch."""
import argparse
import json
import os
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

# Parse only the runtime location before importing anything that can initialize
# PyTorch or a cache. Full command parsing happens after all cache guards exist.
bootstrap = argparse.ArgumentParser(add_help=False)
bootstrap.add_argument("--runtime", default=str(ROOT / "runtime.local.json"))
bootstrap_options, bootstrap_remaining = bootstrap.parse_known_args()
with open(bootstrap_options.runtime, encoding="utf-8") as handle:
    runtime = json.load(handle)

for directory in runtime.get("import_roots", []):
    if not Path(directory).is_dir():
        raise SystemExit(f"Missing registered dependency: {directory}. Nothing was downloaded.")
sys.path[0:0] = runtime.get("import_roots", [])

for variable, suffix in {
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
    os.environ[variable] = str(ROOT / ".runtime" / suffix)
os.environ.update(
    PYTHONDONTWRITEBYTECODE="1",
    TORCH_COMPILE_DISABLE="1",
    TORCHDYNAMO_DISABLE="1",
    HF_HUB_OFFLINE="1",
    TOKENIZERS_PARALLELISM="false",
    CUDA_CACHE_DISABLE="1",
)

from memorylab.storage import Budget


budget = Budget(
    ROOT,
    runtime.get("shared_roots", []) + runtime.get("import_roots", []),
    hard=runtime.get("hard_bytes", Budget.HARD),
    steady=runtime.get("steady_bytes", Budget.STEADY),
)
# The bootstrap itself consists of bounded source/JSON files, below 2 MiB.
# No pip, compiler, downloads, or unbounded subprocess writers are invoked.
budget.ensure_runtime_directories()

parser = argparse.ArgumentParser(description="Persistent-memory learner harness")
subparsers = parser.add_subparsers(dest="command")
audit_parser = subparsers.add_parser("audit", help="audit tracked storage")
audit_parser.add_argument("--save", action="store_true")
subparsers.add_parser("test", help="run the local unittest suite")
subparsers.add_parser("step0", help="validate the learnlab test bench against planted flaws")
bench_parser = subparsers.add_parser("bench", help="bounded device benchmark of real training steps")
bench_parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
bench_parser.add_argument("--backbones", default="transformer,gru")
bench_parser.add_argument("--steps", type=int, default=30)
bench_parser.add_argument("--warmup", type=int, default=3)
bench_parser.add_argument("--seconds", type=float, default=300.0)
bench_parser.add_argument("--seed", type=int, default=0)
train_lm_parser = subparsers.add_parser(
    "train-lm", help="bounded smoke run of the learnlab core on a synthetic pattern stream")
train_lm_parser.add_argument("--size", choices=("4M", "28M", "90M"), default="4M")
train_lm_parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
train_lm_parser.add_argument("--seconds", type=float, default=60.0)
train_lm_parser.add_argument("--max-tokens", type=int, default=None)
train_lm_parser.add_argument("--seq-len", type=int, default=512)
train_lm_parser.add_argument("--batch", type=int, default=32)
train_lm_parser.add_argument("--lr", type=float, default=1e-3)
train_lm_parser.add_argument("--seed", type=int, default=0)
village_parser = subparsers.add_parser("village-sample", help="print a rendered village stream for inspection")
village_parser.add_argument("--split", choices=("train", "validation", "test"), default="train")
village_parser.add_argument("--seed", type=int, default=0)
village_parser.add_argument("--visits", type=int, default=1)
step1_parser = subparsers.add_parser(
    "step1", help="Step 1 (childhood): village data, tokenizer, core training, read-only QA eval, gate")
step1_parser.add_argument("--size", choices=("4M", "28M", "90M"), default="4M")
step1_parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
step1_parser.add_argument("--seconds", type=float, default=600.0,
                          help="budget after the data is ready: training + evaluation, at most 4 hours")
step1_parser.add_argument("--visits", default="small",
                          help="train visits: a preset (tiny, small, medium, large) or a count")
step1_parser.add_argument("--eval-every", type=int, default=0,
                          help="optimizer steps between evaluations; 0 = six evenly timed points")
step1_parser.add_argument("--seed", type=int, default=0)
step1_parser.add_argument("--seq-len", type=int, default=768)
step1_parser.add_argument("--batch", type=int, default=32)
step1_parser.add_argument("--lr", type=float, default=None)
step1_parser.add_argument("--workers", type=int, default=0, help="simulator/encoder processes; 0 = auto")
step1_parser.add_argument("--eval-limit", type=int, default=None,
                          help="held-out visible questions per split (default 2000 on cuda, 60 on cpu)")
step1_parser.add_argument("--build-only", action="store_true",
                          help="build (or verify) the cached data and tokenizer, then stop")

from memorylab.experiment import configure_subcommands, run_from_args

configure_subcommands(subparsers)
args = parser.parse_args(bootstrap_remaining)

if args.command is None:
    args.command = "audit"

if args.command == "audit":
    report = budget.audit()
    print(json.dumps(report, indent=2))
    if getattr(args, "save", False):
        budget.save_json(f"artifacts/storage-{time.time_ns()}.json", report, 2_000_000)
elif args.command == "step0":
    from learnlab.step0 import run_step0
    from memorylab.experiment import environment_report
    import torch

    report = run_step0()
    report["environment"] = environment_report(torch.device("cpu"))
    relative = f"artifacts/step0-{time.time_ns()}-{os.getpid()}.json"
    report["artifact"] = relative
    budget.save_json(relative, report, 2_000_000)
    for check in report["checks"]:
        print(("PASS " if check["passed"] else "FAIL ") + check["check"])
    print(f"STEP0={report['status']} ({sum(c['passed'] for c in report['checks'])}/{len(report['checks'])}) -> {relative}")
    raise SystemExit(0 if report["status"] == "passed" else 1)
elif args.command == "bench":
    from memorylab.bench import run_benchmark

    report = run_benchmark(
        device=args.device,
        backbones=tuple(name for name in args.backbones.split(",") if name),
        steps=args.steps,
        warmup=args.warmup,
        seconds=args.seconds,
        seed=args.seed,
    )
    relative = f"artifacts/bench-{args.device}-{time.time_ns()}-{os.getpid()}.json"
    report["artifact"] = relative
    budget.save_json(relative, report, 2_000_000)
    print(json.dumps(report, indent=2))
elif args.command == "train-lm":
    if not 0 < args.seconds <= 600:
        parser.error("train-lm --seconds must be in (0, 600]")
    from learnlab.ckpt import save_checkpoint
    from learnlab.train import smoke_run
    from memorylab.experiment import environment_report
    import torch

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("train-lm --device cuda: CUDA is not available here. Nothing was run.")
    report, trainer, config = smoke_run(
        size=args.size, device=args.device, seconds=args.seconds, max_tokens=args.max_tokens,
        seq_len=args.seq_len, batch=args.batch, lr=args.lr, seed=args.seed,
        on_log=lambda record: print("LOG " + json.dumps(record), flush=True),
    )
    report["environment"] = environment_report(trainer.device)
    stem = f"artifacts/train-lm-{args.size}-{args.device}-{time.time_ns()}-{os.getpid()}"
    if report["status"] == "completed":
        save_checkpoint(budget, stem + ".ckpt", model=trainer.model, config=config,
                        optimizer=trainer.optimizer, trainer_state=trainer.state_dict())
        report["checkpoint"] = stem + ".ckpt"
    else:
        print(f"ABORTED: {report['error']}", flush=True)
    report["artifact"] = stem + ".json"
    budget.save_json(report["artifact"], report, 2_000_000)
    print(json.dumps({key: value for key, value in report.items() if key != "history"}, indent=2))
    raise SystemExit(0 if report["status"] == "completed" else 1)
elif args.command == "step1":
    from learnlab.step1 import MAX_SECONDS as STEP1_MAX_SECONDS

    if not 0 < args.seconds <= STEP1_MAX_SECONDS:
        parser.error(f"step1 --seconds must be in (0, {STEP1_MAX_SECONDS}]")
    if args.eval_every < 0:
        parser.error("step1 --eval-every must be >= 0")
    from learnlab import step1
    from memorylab.experiment import environment_report
    import torch

    workers = args.workers or max(1, min(12, (os.cpu_count() or 2) - 1))
    if args.build_only:
        data = step1.build_data(budget, visits=args.visits, seed=args.seed, workers=workers,
                                log=lambda message: print(message, flush=True))
        print(json.dumps(data.summary(), indent=2))
        raise SystemExit(0)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("step1 --device cuda: CUDA is not available here. Nothing was run.")
    report = step1.run_step1(
        budget, size=args.size, device=args.device, seconds=args.seconds, visits=args.visits,
        eval_every=args.eval_every, seed=args.seed, workers=workers, seq_len=args.seq_len,
        batch=args.batch, lr=args.lr, eval_limit=args.eval_limit,
        environment=environment_report(torch.device(args.device)),
        log=lambda message: print(message, flush=True),
        on_log=lambda record: print("LOG " + json.dumps(record), flush=True),
    )
    print(step1.format_summary(report), flush=True)
    if report["status"] != "completed":
        print(f"ABORTED: {report['error']}", flush=True)
    raise SystemExit(0 if report["status"] == "completed" else 1)
elif args.command == "village-sample":
    from learnlab.village.shards import sample_text

    print(sample_text(args.split, args.visits, seed=args.seed), end="")
elif args.command == "test":
    import unittest

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
else:
    run_from_args(args, budget, runtime)
