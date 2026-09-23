"""A3-teacher-delay-v2 OPERATIONS tooling -- makes design/v3/13-launch-rulings.md enforceable.

Additive: this module never edits, moves or deletes an existing file, never trains anything itself,
never talks to the network and (apart from `nvidia-smi` and `pip freeze` during `preflight`) runs no
external programs.  Everything imported at module load time is the Python standard library, so this
script stays usable on a box where torch is missing or broken; `preflight` and `run-job` import torch
and the launcher lazily, inside the sub-command.

Sub-commands, in the order an operator uses them:

    waves         13.1/13.3  frozen pair/box/GPU/wave/order map + the two POSIX launch scripts
    preflight     13.4       capture the pinned numerics/software record; --require compares them
    freeze        13.7       hash every authority, source, recipe, panel and admission byte
    freeze-check  13.7       recompute those hashes ("check deployed bytes before each start")
    run-job       13.4/13.7  freeze-check + preflight --require + heartbeat, then ONE launcher job
    health        13.6       the ONLY monitoring view: a hard allowlist projection
    inventory     13.7       remote artifact inventory (path, bytes, sha256)
    verify-copy   13.7       local custody check against that inventory
    incident      13.2       append-only hash-chained incident log
    recovery-plan 13.2       one blinded same-seed recovery per pair, never a resume
    lock          13.6       immutable roster/attempt lock, outcomes still sealed
    worksheet     13.3       T = s + ceil(96/C)*(B/f + e), the caps and the $2.50 cutoff

Nothing here ever prints a learning outcome.  `health` and `lock` are the two commands allowed to read
result.json / eval.json at all, and both pass everything they emit through an explicit allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import time

# ----------------------------------------------------------------------------- frozen constants
EXPERIMENT_ID = "A3-teacher-delay-v2"
OPAQUE_SALT = "A3-teacher-delay-v2|"
FORMAT = "premonition-teacher-delay-v2-ops"

B = 34062815112683.242                      # 12's frozen FLOP budget literal; never recomputed
NOMINAL_FLOOR_RATE = 2.838567926e10         # B / 1200, the nominal per-job counted-FLOP/s floor
MAX_UPDATES = 20000
MAX_SECONDS = 1200
PARAMETERS = 79748
PAIRS = 48
ARMS = ("control", "delayed")
JOBS = PAIRS * len(ARMS)                    # 96 canonical jobs
BOXES = ("A", "B")
GPUS_PER_BOX = 4
PAIRS_PER_GPU = PAIRS // (len(BOXES) * GPUS_PER_BOX)      # 6
PROCS_PER_GPU_RUNGS = (12, 6, 4, 2)         # 13.3's fixed rehearsal order

T_TARGET_SECONDS = 1500.0
T_CEILING_SECONDS = 1800.0
SPEND_CAP_DOLLARS = 2.50
EXCEPTION_THRESHOLD_DOLLARS = 2.00

REPO = Path(__file__).resolve().parents[1]
ARCHIVE_RUN = "opus-ovn-20260918-235851"

DESIGN_FILES = ("design/v3/08-pairsuite-adjudication.md",
                "design/v3/09-reconciliation.md",
                "design/v3/12-teacher-delay-contract.md",
                "design/v3/13-launch-rulings.md")
CLOSURE_SEEDS = ("premonition_gpu_port", "premonition_ovn_retrieval", "premonition_ovn_ladder",
                 "premonition_first_card_probe", "premonition_pair_suite", "premonition_handoff_diag")
IMPORT_RE = re.compile(r"^[ \t]*(?:import|from)[ \t]+(premonition_[A-Za-z0-9_]+)", re.M)

# groups of the freeze manifest that `run-job` re-checks before every start (13.7's "check deployed
# source/config bytes before each start") -- the executed bytes plus the plan and the wave map.
EXECUTED_GROUPS = ("tooling", "source_closure", "frozen_snapshot", "plan_and_waves")

PREFLIGHT_ENV_VARS = ("NVIDIA_TF32_OVERRIDE", "TORCH_ALLOW_TF32_CUBLAS_OVERRIDE", "OMP_NUM_THREADS",
                      "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "CUDA_MPS_PIPE_DIRECTORY",
                      "CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "CUBLAS_WORKSPACE_CONFIG",
                      "PYTORCH_CUDA_ALLOC_CONF")

CHUNK = 1 << 20


# ----------------------------------------------------------------------------- small helpers
def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_json(path):
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"no such file: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}") from None


def write_new_json(path, payload) -> Path:
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path} already exists; this tool never overwrites an operations record")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    return path


def opaque_id(job_id: str) -> str:
    """Arm-free, collision-checked monitoring id (13.6: "arm names are unnecessary in monitoring")."""
    return "j-" + hashlib.sha256((OPAQUE_SALT + str(job_id)).encode("utf-8")).hexdigest()[:10]


# ----------------------------------------------------------------------------- plan access
def load_plan(path) -> dict:
    plan = read_json(path)
    if plan.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit(f"plan experiment_id {plan.get('experiment_id')!r} is not {EXPERIMENT_ID!r}")
    pairs = plan.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise SystemExit("plan has no pairs")
    for pair in pairs:
        jobs = pair.get("jobs")
        if not isinstance(jobs, dict) or sorted(jobs) != sorted(ARMS):
            raise SystemExit(f"pair {pair.get('pair_id')} does not register exactly the arms {ARMS}")
    return plan


def plan_pair_ids(plan: dict) -> list:
    return [int(pair["pair_id"]) for pair in plan["pairs"]]


def plan_job_ids(plan: dict) -> list:
    """Canonical job ids in (pair, arm) order."""
    out = []
    for pair in plan["pairs"]:
        for arm in ARMS:
            out.append(str(pair["jobs"][arm]["job_id"]))
    return out


def plan_pair(plan: dict, pair_id: int) -> dict:
    for pair in plan["pairs"]:
        if int(pair["pair_id"]) == int(pair_id):
            return pair
    raise SystemExit(f"plan has no pair {pair_id}")


def require_full_roster(plan: dict) -> None:
    ids = plan_pair_ids(plan)
    if sorted(ids) != list(range(PAIRS)):
        raise SystemExit(f"this command needs the full {PAIRS}-pair roster; the plan has {len(ids)} pairs")


# ----------------------------------------------------------------------------- 13.1/13.3 placement
def box_of(pair_id: int) -> str:
    """13.1: even pair ids on A, odd on B."""
    return "A" if int(pair_id) % 2 == 0 else "B"


def gpu_of(pair_id: int) -> int:
    """13.1: GPU index floor(pair_id/2) mod 4; both arms share that one physical GPU."""
    return (int(pair_id) // 2) % GPUS_PER_BOX


def first_arm_of(pair_id: int) -> str:
    """13.1: control first when floor(pair_id/8) is even, delayed otherwise (3:3 on every GPU)."""
    return "control" if (int(pair_id) // 8) % 2 == 0 else "delayed"


def arm_order(pair_id: int) -> tuple:
    first = first_arm_of(pair_id)
    return (first, "delayed" if first == "control" else "control")


def gpu_pairs(box: str, gpu: int) -> list:
    return [p for p in range(PAIRS) if box_of(p) == box and gpu_of(p) == gpu]


def wave_shape(procs_per_gpu: int) -> tuple:
    if procs_per_gpu not in PROCS_PER_GPU_RUNGS:
        raise SystemExit(f"--procs-per-gpu must be one of {PROCS_PER_GPU_RUNGS} (13.3's fixed rungs)")
    pairs_per_wave = procs_per_gpu // len(ARMS)
    if PAIRS_PER_GPU % pairs_per_wave:
        raise SystemExit(f"{procs_per_gpu} processes/GPU does not divide {PAIRS_PER_GPU} whole pairs")
    return pairs_per_wave, PAIRS_PER_GPU // pairs_per_wave


def build_waves(plan: dict, procs_per_gpu: int) -> dict:
    require_full_roster(plan)
    pairs_per_wave, n_waves = wave_shape(procs_per_gpu)
    by_pair = {int(p["pair_id"]): {arm: str(p["jobs"][arm]["job_id"]) for arm in ARMS}
               for p in plan["pairs"]}

    boxes, table = {}, {}
    for box in BOXES:
        waves = []
        for wave in range(n_waves):
            gpus = []
            for gpu in range(GPUS_PER_BOX):
                mine = gpu_pairs(box, gpu)
                if len(mine) != PAIRS_PER_GPU:
                    raise SystemExit(f"box {box} GPU {gpu} holds {len(mine)} pairs, expected {PAIRS_PER_GPU}")
                chunk = mine[wave * pairs_per_wave:(wave + 1) * pairs_per_wave]
                jobs = []
                for pair_id in chunk:
                    for arm in arm_order(pair_id):
                        job = by_pair[pair_id][arm]
                        row = {"job_id": job, "opaque_id": opaque_id(job), "pair_id": pair_id,
                               "start_order": len(jobs)}
                        jobs.append(row)
                        table[job] = {"box": box, "gpu": gpu, "wave": wave, "pair_id": pair_id,
                                      "start_order": row["start_order"], "opaque_id": row["opaque_id"]}
                gpus.append({"gpu": gpu, "pairs": chunk, "jobs": jobs})
            waves.append({"wave": wave, "gpus": gpus,
                          "jobs_in_wave": sum(len(g["jobs"]) for g in gpus)})
        boxes[box] = {"box": box, "pairs": sorted(p for p in range(PAIRS) if box_of(p) == box),
                      "waves": waves}

    tags = sorted(row["opaque_id"] for row in table.values())
    if len(set(tags)) != len(tags):
        raise SystemExit("opaque job ids collided; widen the digest prefix before launching")
    if len(table) != JOBS:
        raise SystemExit(f"placed {len(table)} jobs, expected {JOBS}")

    return {
        "format": FORMAT + "-waves", "experiment_id": EXPERIMENT_ID, "created_utc": utc_now(),
        "procs_per_gpu": procs_per_gpu, "pairs_per_gpu_per_wave": pairs_per_wave, "waves": n_waves,
        "boxes_used": list(BOXES), "gpus_per_box": GPUS_PER_BOX, "pairs": PAIRS, "jobs": JOBS,
        "placement_rule": {
            "box": "A if pair_id is even else B (13.1)",
            "gpu": "floor(pair_id / 2) mod 4 (13.1); both arms of a pair share that GPU and wave",
            "first_arm": "control when floor(pair_id / 8) is even, delayed otherwise (13.1)",
            "wave_fill": "successive WHOLE pairs in ascending pair_id per GPU (13.3)",
            "start": "the two arms of a pair are started consecutively, first arm first"},
        "opaque_id_rule": 'sha256("' + OPAQUE_SALT + '" + job_id), first 10 hex, prefixed "j-"',
        "boxes": boxes, "table": table,
        "launch_scripts": {box: f"launch_{box}.sh" for box in BOXES},
    }


# ----------------------------------------------------------------------------- launch scripts
LAUNCH_HEADER = """#!/bin/sh
# A3-teacher-delay-v2 -- box {box} launch script, generated by
#   scripts/premonition_teacher_delay_ops.py waves --procs-per-gpu {procs}
# Frozen map: {waves} wave(s) per GPU, {procs} processes per GPU, {gpus} GPUs, whole pairs only.
# Run it NON-INTERACTIVELY (`sh launch_{box}.sh`) so that $! names the job itself.
# Edit only the five variables below; the wave/order map is frozen and must not be reordered.
set -eu

PYTHON="{python}"
REPO_DIR="{repo}"
ROOT="{root}"
PLAN="{plan}"
FREEZE_RECORD="{freeze}"

OPS="scripts/premonition_teacher_delay_ops.py"

# ---- 13.4: CUDA MPS is pinned ON with these directories.
CUDA_MPS_PIPE_DIRECTORY="/tmp/nvidia-mps"
CUDA_MPS_LOG_DIRECTORY="/tmp/nvidia-mps-log"
export CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY
mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"
mkdir -p "$ROOT/sealed_logs" "$ROOT/pids" "$ROOT/heartbeats"

if [ ! -e "$CUDA_MPS_PIPE_DIRECTORY/control" ]; then
    nvidia-cuda-mps-control -d
fi

cd "$REPO_DIR"

# ---- one job.  $3 is the opaque monitoring id: no arm name ever reaches a log or pid path.
start_job() {{
    gpu="$1"
    job="$2"
    tag="$3"
    CUDA_VISIBLE_DEVICES="$gpu" setsid nohup "$PYTHON" -B "$OPS" run-job \\
        --freeze "$FREEZE_RECORD" --plan "$PLAN" --job "$job" \\
        --out-root "$ROOT" --device cuda \\
        > "$ROOT/sealed_logs/$tag.log" 2>&1 < /dev/null &
    echo $! > "$ROOT/pids/$tag.pid"
}}

# ---- wait for every job of a wave before the next wave starts (13.3: no mid-comparison tuning).
wait_for() {{
    for tag in "$@"; do
        waited=0
        while [ ! -f "$ROOT/heartbeats/$tag.json" ] && [ "$waited" -lt 900 ]; do
            sleep 2
            waited=$((waited + 2))
        done
        while :; do
            if [ ! -f "$ROOT/pids/$tag.pid" ]; then break; fi
            pid=`cat "$ROOT/pids/$tag.pid"`
            if [ -z "$pid" ]; then break; fi
            if kill -0 "$pid" 2>/dev/null; then sleep 5; else break; fi
        done
    done
}}
"""


def launch_script(waves_record: dict, box: str, *, python: str, repo: str, root: str,
                  plan: str, freeze: str) -> str:
    entry = waves_record["boxes"][box]
    lines = [LAUNCH_HEADER.format(box=box, procs=waves_record["procs_per_gpu"],
                                  waves=waves_record["waves"], gpus=GPUS_PER_BOX,
                                  python=python, repo=repo, root=root, plan=plan, freeze=freeze)]
    for wave in entry["waves"]:
        tags = []
        lines.append(f"\n# ---------------------------------------------------------------- wave "
                     f"{wave['wave']}")
        for gpu in wave["gpus"]:
            for job in gpu["jobs"]:
                lines.append("start_job {} {} {}".format(gpu["gpu"], shlex.quote(job["job_id"]),
                                                         job["opaque_id"]))
                tags.append(job["opaque_id"])
        lines.append("wait_for " + " ".join(tags))
    lines.append('\necho "box {} finished every wave; outcomes stay sealed"\n'.format(box))
    return "\n".join(lines)


def cmd_waves(args) -> int:
    plan_path = Path(args.plan).resolve()
    plan = load_plan(plan_path)
    record = build_waves(plan, int(args.procs_per_gpu))
    out = Path(args.out)
    scripts = {box: out.parent / f"launch_{box}.sh" for box in BOXES}
    for path in [out] + list(scripts.values()):
        if Path(path).exists():
            raise SystemExit(f"{path} already exists; choose a new waves output path")
    out.parent.mkdir(parents=True, exist_ok=True)
    record["launch_scripts"] = {box: str(path) for box, path in scripts.items()}
    out.write_text(json.dumps(record, indent=2) + "\n")
    for box, path in scripts.items():
        path.write_text(launch_script(record, box, python=args.python, repo=args.repo,
                                      root=args.root, plan=args.plan_path, freeze=args.freeze_record))
        os.chmod(path, 0o755)
    print(json.dumps({"waves": str(out), "procs_per_gpu": record["procs_per_gpu"],
                      "wave_count": record["waves"], "jobs": record["jobs"],
                      "launch_scripts": record["launch_scripts"],
                      "waves_sha256": sha256_file(out)}, indent=2))
    return 0


# ----------------------------------------------------------------------------- 13.4 preflight
def _run(cmd, timeout=120):
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout


def _cpu_model():
    if sys.platform == "darwin":
        out = _run(["sysctl", "-n", "machdep.cpu.brand_string"], timeout=20)
        return out.strip() if out else None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def _nvidia_smi():
    out = _run(["nvidia-smi", "--query-gpu=index,name,uuid,driver_version",
                "--format=csv,noheader"], timeout=60)
    if not out:
        return {"present": False, "driver_version": None, "gpu_names": None, "gpu_uuids": None}
    names, uuids, drivers = [], [], []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        names.append(parts[1])
        uuids.append(parts[2])
        drivers.append(parts[3])
    if not names:
        return {"present": False, "driver_version": None, "gpu_names": None, "gpu_uuids": None}
    return {"present": True, "driver_version": drivers[0] if len(set(drivers)) == 1 else None,
            "gpu_names": names, "gpu_uuids": uuids}


def capture_preflight(box=None, image_digest=None) -> dict:
    """Capture 13.4's pinned numerics/software record plus 13.4's provenance telemetry.

    Anything that could not be read is written as an explicit null: "default"/"unknown" are never
    acceptable pinned values, and a null makes `--require` fail.
    """
    pinned = {key: None for key in (
        "python_version", "python_implementation", "torch_version", "torch_cuda_version",
        "cudnn_version", "cuda_matmul_allow_tf32", "cudnn_allow_tf32", "float32_matmul_precision",
        "cudnn_benchmark", "cudnn_deterministic", "deterministic_algorithms_enabled",
        "torch_num_threads", "torch_num_interop_threads", "pip_freeze_sha256",
        "nvidia_driver_version", "gpu_names", "platform_system", "platform_machine",
        "image_digest")}
    telemetry = {key: None for key in (
        "gpu_uuids", "cpu_model", "cpu_logical_cores", "hostname", "platform", "platform_release",
        "captured_utc", "instance_env")}
    notes = []

    pinned["image_digest"] = image_digest         # 13.4: the resolved immutable image digest
    pinned["python_version"] = platform.python_version()
    pinned["python_implementation"] = platform.python_implementation()
    pinned["platform_system"] = platform.system() or None
    pinned["platform_machine"] = platform.machine() or None

    try:
        import torch
    except BaseException as error:                            # noqa: BLE001 - recorded as a null row
        torch = None
        notes.append(f"torch unavailable: {type(error).__name__}")
    if torch is not None:
        pinned["torch_version"] = str(torch.__version__)
        pinned["torch_cuda_version"] = getattr(torch.version, "cuda", None)
        try:
            pinned["cudnn_version"] = torch.backends.cudnn.version()
        except BaseException:                                 # noqa: BLE001
            pinned["cudnn_version"] = None
        pinned["cuda_matmul_allow_tf32"] = bool(torch.backends.cuda.matmul.allow_tf32)
        pinned["cudnn_allow_tf32"] = bool(torch.backends.cudnn.allow_tf32)
        pinned["float32_matmul_precision"] = str(torch.get_float32_matmul_precision())
        pinned["cudnn_benchmark"] = bool(torch.backends.cudnn.benchmark)
        pinned["cudnn_deterministic"] = bool(torch.backends.cudnn.deterministic)
        pinned["deterministic_algorithms_enabled"] = bool(torch.are_deterministic_algorithms_enabled())
        pinned["torch_num_threads"] = int(torch.get_num_threads())
        pinned["torch_num_interop_threads"] = int(torch.get_num_interop_threads())

    env = {name: os.environ.get(name) for name in PREFLIGHT_ENV_VARS}
    pinned["env"] = env

    freeze_text = _run([sys.executable, "-m", "pip", "freeze"], timeout=180)
    pinned["pip_freeze_sha256"] = sha256_text(freeze_text) if freeze_text is not None else None
    if freeze_text is None:
        notes.append("pip freeze failed; the dependency inventory is a null and --require will fail")

    smi = _nvidia_smi()
    pinned["nvidia_driver_version"] = smi["driver_version"]
    pinned["gpu_names"] = smi["gpu_names"]
    telemetry["gpu_uuids"] = smi["gpu_uuids"]
    if not smi["present"]:
        notes.append("nvidia-smi is not available on this host")

    telemetry["cpu_model"] = _cpu_model()
    telemetry["cpu_logical_cores"] = os.cpu_count()
    telemetry["hostname"] = platform.node() or None
    telemetry["platform"] = platform.platform()
    telemetry["platform_release"] = platform.release() or None
    telemetry["captured_utc"] = utc_now()
    telemetry["instance_env"] = {name: os.environ.get(name) for name in
                                 ("VAST_CONTAINERLABEL", "CONTAINER_ID", "HOSTNAME", "CUDA_VISIBLE_DEVICES")}

    return {
        "format": FORMAT + "-preflight", "experiment_id": EXPERIMENT_ID, "box": box,
        "created_utc": utc_now(),
        "pinned_note": "13.4: these values are PINNED, not merely recorded. 'default', 'fp32' and "
                       "'unknown' are not acceptable values; a null here fails --require.",
        "telemetry_note": "13.4: provenance only. Never an adaptive control and never compared.",
        "threads_policy": "run-job always passes --threads 1 to the launcher (13.4)",
        "pinned": pinned, "telemetry": telemetry,
        "pip_freeze": freeze_text, "notes": notes,
    }


def _flatten_pinned(pinned: dict) -> dict:
    flat = {}
    for key, value in pinned.items():
        if key == "env" and isinstance(value, dict):
            for name, item in value.items():
                flat[f"env.{name}"] = item
        elif isinstance(value, list):
            flat[key] = list(value)
        else:
            flat[key] = value
    return flat


# environment variables whose ABSENCE is the pinned value: an unset override is what 13.4 calls the
# image's unmodified startup policy, so None here is a real value rather than an unknown.
NULLABLE_PINNED = tuple(f"env.{name}" for name in PREFLIGHT_ENV_VARS)


def compare_pinned(current: dict, required: dict) -> list:
    """Every difference between two preflight records' pinned sections, as readable strings."""
    a = _flatten_pinned((current or {}).get("pinned") or {})
    b = _flatten_pinned((required or {}).get("pinned") or {})
    problems = []
    for key in sorted(set(a) | set(b)):
        if key not in a:
            problems.append(f"{key}: missing from the captured record (required {b[key]!r})")
            continue
        if key not in b:
            problems.append(f"{key}: missing from the required record (captured {a[key]!r})")
            continue
        if key not in NULLABLE_PINNED:
            if a[key] is None:
                problems.append(f"{key}: captured value is null; 13.4 forbids an unknown pinned value")
            if b[key] is None:
                problems.append(f"{key}: required value is null; 13.4 forbids an unknown pinned value")
            if isinstance(a[key], str) and a[key].strip().lower() in ("default", "unknown"):
                problems.append(f"{key}: captured value {a[key]!r} is not an acceptable pinned value")
        if a[key] != b[key]:
            problems.append(f"{key}: captured {a[key]!r} != required {b[key]!r}")
    return problems


def cmd_preflight(args) -> int:
    record = (read_json(args.use_record) if args.use_record
              else capture_preflight(args.box, args.image_digest))
    if args.box and record.get("box") not in (None, args.box):
        raise SystemExit(f"--box {args.box} but the record says box {record.get('box')!r}")
    if args.out:
        write_new_json(args.out, record)
    problems = []
    if args.require:
        problems = compare_pinned(record, read_json(args.require))
    summary = {"box": record.get("box"), "out": str(args.out) if args.out else None,
               "required": str(args.require) if args.require else None,
               "pinned_differences": len(problems), "notes": record.get("notes", [])}
    print(json.dumps(summary, indent=2))
    for line in problems:
        print("PINNED MISMATCH " + line, file=sys.stderr)
    return 2 if problems else 0


# ----------------------------------------------------------------------------- 13.7 freeze
def source_closure(repo: Path, seeds) -> list:
    """Transitive `premonition_*` closure under scripts/, by parsing import lines recursively."""
    seen, stack = set(), list(seeds)
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        path = repo / "scripts" / (module + ".py")
        if not path.is_file():
            raise SystemExit(f"source closure: {path} does not exist")
        seen.add(module)
        stack.extend(IMPORT_RE.findall(path.read_text()))
    return sorted(seen)


def _base_of(path: Path, root: Path, repo: Path) -> tuple:
    path = Path(path).resolve()
    if root is not None and path.is_relative_to(root):
        return "root", path.relative_to(root).as_posix()
    if path.is_relative_to(repo):
        return "repo", path.relative_to(repo).as_posix()
    return "abs", path.as_posix()


def _resolve(base: str, rel: str, root: Path, repo: Path) -> Path:
    if base == "root":
        return Path(root) / rel
    if base == "repo":
        return Path(repo) / rel
    return Path(rel)


def _entry(path: Path, group: str, root: Path, repo: Path, **extra) -> dict:
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"freeze: {path} does not exist (13.7 admits no placeholder)")
    base, rel = _base_of(path, root, repo)
    row = {"group": group, "base": base, "path": rel, "bytes": path.stat().st_size,
           "sha256": sha256_file(path)}
    row.update(extra)
    return row


def panels_root(root: Path, plan_path: Path) -> Path:
    for candidate in (Path(root) / "panels", Path(plan_path).resolve().parent / "panels"):
        if candidate.is_dir():
            return candidate
    raise SystemExit(f"freeze: no panels/ directory under {root} or beside {plan_path}")


def build_freeze_manifest(*, root: Path, repo: Path, plan_path: Path, waves_path: Path,
                          preflights, rehearsals, worksheet: Path) -> dict:
    files = []

    for rel in DESIGN_FILES:
        files.append(_entry(repo / rel, "authority", root, repo))

    tooling = sorted(repo.glob("scripts/premonition_teacher_delay*.py"))
    tooling += sorted(repo.glob("tests/test_premonition_teacher_delay*.py"))
    if not tooling:
        raise SystemExit("freeze: no premonition_teacher_delay* sources found")
    for path in tooling:
        files.append(_entry(path, "tooling", root, repo))

    seeds = list(CLOSURE_SEEDS)
    seeds += [p.stem for p in repo.glob("scripts/premonition_teacher_delay*.py")]
    for module in source_closure(repo, seeds):
        path = repo / "scripts" / (module + ".py")
        if any(row["base"] == "repo" and row["path"] == path.relative_to(repo).as_posix()
               for row in files):
            continue
        files.append(_entry(path, "source_closure", root, repo, module=module))

    archive = repo / "archive" / ARCHIVE_RUN
    sums = archive / "FROZEN.SHA256SUMS"
    if not sums.is_file():
        raise SystemExit(f"freeze: {sums} is missing; the frozen snapshot cannot be attested")
    files.append(_entry(sums, "frozen_snapshot", root, repo))
    listed = 0
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        member = archive / "frozen" / name.strip()
        row = _entry(member, "frozen_snapshot", root, repo, listed_sha256=digest)
        if row["sha256"] != digest:
            raise SystemExit(f"freeze: {member} no longer matches FROZEN.SHA256SUMS")
        files.append(row)
        listed += 1
    if not listed:
        raise SystemExit("freeze: FROZEN.SHA256SUMS lists no files")

    plan_row = _entry(plan_path, "plan_and_waves", root, repo, role="plan")
    files.append(plan_row)
    sources = Path(plan_path).resolve().parent / "plan_sources.json"
    if sources.is_file():
        files.append(_entry(sources, "plan_and_waves", root, repo, role="plan_sources"))
    waves_row = _entry(waves_path, "plan_and_waves", root, repo, role="waves")
    files.append(waves_row)
    for box in BOXES:
        script = Path(waves_path).resolve().parent / f"launch_{box}.sh"
        if not script.is_file():
            raise SystemExit(f"freeze: {script} is missing; the launch order is part of the freeze")
        files.append(_entry(script, "plan_and_waves", root, repo, role=f"launch_{box}"))

    preflight_rows = []
    for path in preflights:
        record = read_json(path)
        row = _entry(path, "preflight", root, repo, box=record.get("box"))
        files.append(row)
        preflight_rows.append({"base": row["base"], "path": row["path"], "box": record.get("box")})
    boxes_seen = sorted({row["box"] for row in preflight_rows if row["box"]})
    if boxes_seen != sorted(BOXES):
        raise SystemExit(f"freeze: preflight records cover boxes {boxes_seen}, expected {list(BOXES)} "
                         f"(pass --box A / --box B when capturing them)")

    for path in rehearsals:
        files.append(_entry(path, "rehearsal", root, repo))
    files.append(_entry(worksheet, "admission", root, repo, role="cost_time_worksheet"))

    panels = panels_root(root, plan_path)
    missing = []
    for pair_id in range(PAIRS):
        manifest_path = panels / f"p{pair_id:03d}" / "manifest.json"
        if not manifest_path.is_file():
            missing.append(f"p{pair_id:03d}/manifest.json")
            continue
        files.append(_entry(manifest_path, "panels", root, repo, pair_id=pair_id))
        manifest = read_json(manifest_path)
        cells = manifest.get("panels")
        if not isinstance(cells, dict) or not cells:
            missing.append(f"p{pair_id:03d}: manifest lists no panels")
            continue
        for cell, info in sorted(cells.items()):
            data = manifest_path.parent / str(info.get("file"))
            if not data.is_file():
                missing.append(f"p{pair_id:03d}/{info.get('file')}")
                continue
            row = _entry(data, "panels", root, repo, pair_id=pair_id, cell=cell,
                         listed_sha256=info.get("sha256"))
            if info.get("sha256") and row["sha256"] != info["sha256"]:
                missing.append(f"p{pair_id:03d}/{info.get('file')}: content no longer matches the manifest")
                continue
            files.append(row)
    if missing:
        raise SystemExit("freeze: evaluation panel bytes are incomplete (13.7.5 admits no placeholder): "
                         + ", ".join(missing[:12]) + (" ..." if len(missing) > 12 else ""))

    validation = Path(root) / "validation"
    if validation.is_dir():
        for path in sorted(p for p in validation.rglob("*") if p.is_file()):
            files.append(_entry(path, "validation", root, repo))

    files.sort(key=lambda row: (row["group"], row["base"], row["path"]))
    return {
        "format": FORMAT + "-freeze", "experiment_id": EXPERIMENT_ID, "created_utc": utc_now(),
        "repo": str(repo), "root": str(root),
        "constants": {"B": B, "nominal_per_job_floor_counted_flops_per_second": NOMINAL_FLOOR_RATE,
                      "max_updates": MAX_UPDATES, "max_seconds": MAX_SECONDS,
                      "parameters": PARAMETERS, "pairs": PAIRS, "jobs": JOBS,
                      "spend_cap_dollars": SPEND_CAP_DOLLARS},
        "plan_file": {"base": plan_row["base"], "path": plan_row["path"]},
        "waves_file": {"base": waves_row["base"], "path": waves_row["path"]},
        "preflight_files": preflight_rows,
        "executed_groups": list(EXECUTED_GROUPS),
        "counts": {group: sum(1 for row in files if row["group"] == group)
                   for group in sorted({row["group"] for row in files})},
        "files": files,
    }


def cmd_freeze(args) -> int:
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists; a freeze directory is never reused")
    root = Path(args.root).resolve()
    repo = REPO
    manifest = build_freeze_manifest(root=root, repo=repo, plan_path=Path(args.plan).resolve(),
                                     waves_path=Path(args.waves).resolve(),
                                     preflights=[Path(p).resolve() for p in args.preflight],
                                     rehearsals=[Path(p).resolve() for p in args.rehearsal],
                                     worksheet=Path(args.worksheet).resolve())
    out.mkdir(parents=True)
    manifest_path = out / "freeze_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    digest = sha256_file(manifest_path)
    record = {"format": FORMAT + "-freeze-record", "experiment_id": EXPERIMENT_ID,
              "manifest_sha256": digest, "manifest": "freeze_manifest.json",
              "created_utc": utc_now(), "repo": str(repo), "root": str(root),
              "files": len(manifest["files"]),
              "note": "13.7: generated artifacts and incident addenda reference this hash; the freeze "
                      "itself is never rewritten."}
    (out / "freeze_record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"freeze": str(out), "manifest_sha256": digest,
                      "files": len(manifest["files"]), "counts": manifest["counts"]}, indent=2))
    return 0


def load_freeze(record_path) -> tuple:
    record = read_json(record_path)
    folder = Path(record_path).resolve().parent
    manifest_path = folder / str(record.get("manifest", "freeze_manifest.json"))
    if not manifest_path.is_file():
        raise SystemExit(f"freeze manifest {manifest_path} is missing")
    digest = sha256_file(manifest_path)
    if digest != record.get("manifest_sha256"):
        raise SystemExit(f"freeze manifest hash {digest} != the frozen record's "
                         f"{record.get('manifest_sha256')}")
    return record, read_json(manifest_path), manifest_path


def check_freeze(record_path, root, repo, groups=None) -> list:
    _, manifest, _ = load_freeze(record_path)
    root, repo = Path(root).resolve(), Path(repo).resolve()
    problems = []
    for row in manifest["files"]:
        if groups and row["group"] not in groups:
            continue
        path = _resolve(row["base"], row["path"], root, repo)
        if not path.is_file():
            problems.append(f"MISSING {row['group']} {row['base']}:{row['path']}")
            continue
        size = path.stat().st_size
        if size != row["bytes"]:
            problems.append(f"SIZE {row['group']} {row['base']}:{row['path']} {size} != {row['bytes']}")
            continue
        digest = sha256_file(path)
        if digest != row["sha256"]:
            problems.append(f"HASH {row['group']} {row['base']}:{row['path']} {digest} != {row['sha256']}")
    return problems


def cmd_freeze_check(args) -> int:
    groups = tuple(g.strip() for g in args.groups.split(",")) if args.groups else None
    problems = check_freeze(args.record, args.root, args.repo, groups)
    print(json.dumps({"record": str(args.record), "groups": list(groups) if groups else "all",
                      "problems": len(problems)}, indent=2))
    for line in problems:
        print(line, file=sys.stderr)
    return 2 if problems else 0


# ----------------------------------------------------------------------------- 13.4/13.7 run-job
def cmd_run_job(args) -> int:
    root = Path(args.out_root).resolve()
    record_path = Path(args.freeze).resolve()
    repo = REPO
    tag = opaque_id(args.job)

    # The heartbeat and pid file come FIRST, so that a refusal below is visible to the wave loop and
    # to `health` immediately instead of after a timeout. Neither file ever carries an arm name.
    for name in ("heartbeats", "pids", "sealed_logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    heartbeat_path = root / "heartbeats" / f"{tag}.json"
    heartbeat = {"format": FORMAT + "-heartbeat", "opaque_id": tag, "box": None, "gpu": None,
                 "wave": None, "stage": "preflight", "started_utc": utc_now(),
                 "started_monotonic": time.time(), "pid": os.getpid(), "host": platform.node(),
                 "device": args.device, "freeze_manifest_sha256": None,
                 "exit_code": None, "finished_utc": None, "error_type": None}

    def beat() -> None:
        heartbeat["elapsed_seconds"] = round(time.time() - heartbeat["started_monotonic"], 3)
        heartbeat_path.write_text(json.dumps(heartbeat, indent=2) + "\n")

    def refuse(message: str, error_type: str, lines=()) -> None:
        for line in lines:
            print(line, file=sys.stderr)
        heartbeat.update(exit_code=3, error_type=error_type, finished_utc=utc_now(), stage="refused")
        beat()
        raise SystemExit("run-job refused: " + message)

    beat()
    (root / "pids" / f"{tag}.pid").write_text(f"{os.getpid()}\n")

    try:
        record, manifest, _ = load_freeze(record_path)
    except SystemExit as error:
        refuse(str(error), "FreezeRecordError")
        raise                                                 # unreachable; keeps the flow explicit
    heartbeat["freeze_manifest_sha256"] = record.get("manifest_sha256")

    # (a) the deployed executed bytes, plan and wave map, re-checked before this start.
    problems = check_freeze(record_path, root, repo, EXECUTED_GROUPS)
    if problems:
        refuse(f"{len(problems)} frozen byte(s) changed since the freeze", "FrozenBytesChanged",
               problems)

    waves_ref = manifest.get("waves_file") or {}
    waves = read_json(_resolve(waves_ref.get("base", "root"), waves_ref.get("path", "waves.json"),
                               root, repo))
    placement = (waves.get("table") or {}).get(args.job)
    if not placement:
        refuse(f"{args.job!r} is not in the frozen wave map", "UnplacedJob")
    box = placement["box"]
    if placement.get("opaque_id") not in (None, tag):
        refuse("the frozen wave map disagrees with this tool's opaque id rule", "OpaqueIdMismatch")
    heartbeat.update(box=box, gpu=placement["gpu"], wave=placement["wave"])
    beat()

    # (b) this box's frozen numerics/software record must still hold exactly.
    wanted = [row for row in manifest.get("preflight_files", []) if row.get("box") == box]
    if len(wanted) != 1:
        refuse(f"the freeze holds {len(wanted)} preflight records for box {box}; expected 1",
               "PreflightRecordMissing")
    required = read_json(_resolve(wanted[0]["base"], wanted[0]["path"], root, repo))
    # The image digest is not observable from inside the container, so the operator must attest it
    # again at launch (A3_IMAGE_DIGEST), exactly as `preflight --image-digest` did; a missing or
    # different attestation still refuses. Every other pinned field is measured live.
    differences = compare_pinned(
        capture_preflight(box, os.environ.get("A3_IMAGE_DIGEST") or None), required)
    if differences:
        refuse(f"{len(differences)} pinned preflight difference(s) on box {box}", "PinnedDrift",
               ["PINNED MISMATCH " + line for line in differences])

    # (c) exactly one launcher job, in-process, with --threads 1.
    heartbeat["stage"] = "training"
    beat()

    import contextlib
    import io

    sys.path.insert(0, str(repo / "scripts"))
    code, error_type = 1, None
    sealed = io.StringIO()
    try:
        import premonition_teacher_delay as TD
        with contextlib.redirect_stdout(sealed):
            code = int(TD.main(["run", "--plan", str(Path(args.plan).resolve()), "--job", args.job,
                                "--out-root", str(root), "--device", args.device, "--threads", "1"]))
    except SystemExit as exit_error:                          # noqa: PERF203 - recorded, then reported
        code = int(exit_error.code) if isinstance(exit_error.code, int) else 1
        error_type = "SystemExit"
    except BaseException as error:                            # noqa: BLE001 - type only, never message
        code, error_type = 1, type(error).__name__
    finally:
        # the launcher's own stdout may carry allowlisted fields, but it is sealed either way.
        (root / "sealed_logs" / f"{tag}.launcher.out").write_text(sealed.getvalue())
        heartbeat.update(exit_code=code, error_type=error_type, finished_utc=utc_now(),
                         stage="finished")
        beat()
    # no learning outcome is printed here: the opaque id and the exit code only.
    print(json.dumps({"opaque_id": tag, "box": box, "gpu": placement["gpu"],
                      "wave": placement["wave"], "exit_code": code, "error_type": error_type}))
    return code


# ----------------------------------------------------------------------------- 13.6 health
_STOP_CLASSES = (("flop budget", "flop-budget"), ("max_steps", "update-cap"),
                 ("max_seconds", "time-cap"), ("stream ended", "stream-ended"))
_TRAINING_STATUSES = ("started", "complete", "incomplete", "failed")
_EVAL_FAILURE_PREFIXES = (
    ("parameters changed during evaluation", "weights-changed"),
    ("an integrity check failed", "integrity-check-failed"),
    ("panel scoring failed", "panel-scoring-failed"),
    ("no panels", "panels-missing"),
    ("no checkpoint", "checkpoint-missing"),
    ("checkpoint", "checkpoint-identity-mismatch"),
)


def _stop_class(stop):
    if not isinstance(stop, str):
        return None
    for prefix, name in _STOP_CLASSES:
        if stop.startswith(prefix):
            return name
    return "other"


def _eval_failure_class(reason):
    if not isinstance(reason, str):
        return None
    text = reason.strip().lower()
    for prefix, name in _EVAL_FAILURE_PREFIXES:
        if text.startswith(prefix):
            return name
    return "unclassified"


def _error_type(text):
    """Exception TYPE name only -- 13.6 allows a sanitized infrastructure error, never its message."""
    if not isinstance(text, str) or not text.strip():
        return None
    head = text.split(":", 1)[0].strip()
    return head if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", head) else "UnparsedError"


def _number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def project(result, evaljson) -> dict:
    """13.6's monitoring allowlist, as an explicit whitelist: nothing else can reach a dashboard.

    Deliberately absent, whatever the inputs contain: losses, curves, cell counts, per-unit vectors,
    accuracies, recall, gates, L_train / G_pair, c1-stuck, diagnostics, raw reasons, raw stdout --
    and the arm names, which 13.6 calls unnecessary in monitoring.
    """
    out = {
        "training_status": None, "stop_reason": None, "budget_ok": None,
        "updates_done": None, "counted_flops": None, "counted_flop_share": None,
        "seconds_train": None, "infrastructure_error_type": None,
        "evaluation_status": None, "evaluation_failure_class": None,
        "integrity": {"weights_unchanged": None, "label_perturbation": None,
                      "world_isolation": None, "parity": None},
    }
    if isinstance(result, dict):
        status = result.get("status")
        if isinstance(status, str):
            out["training_status"] = status if status in _TRAINING_STATUSES else "unknown"
        report = result.get("report")
        if isinstance(report, dict):
            out["stop_reason"] = _stop_class(report.get("stop"))
            if "budget_ok" in report:
                out["budget_ok"] = bool(report.get("budget_ok"))
            out["counted_flops"] = _number(report.get("flops"))
        budget = _number(result.get("flop_budget"))
        if out["counted_flops"] is not None and budget:
            out["counted_flop_share"] = round(out["counted_flops"] / budget, 6)
        updates = result.get("updates_done")
        if isinstance(updates, int) and not isinstance(updates, bool):
            out["updates_done"] = updates
        seconds = _number(result.get("seconds_train"))
        out["seconds_train"] = round(seconds, 3) if seconds is not None else None
        out["infrastructure_error_type"] = _error_type(result.get("error"))
    if isinstance(evaljson, dict):
        status = evaljson.get("status")
        if isinstance(status, str):
            out["evaluation_status"] = ("complete" if status == "complete"
                                        else "failed" if status == "failed" else "unknown")
        if out["evaluation_status"] == "failed":
            out["evaluation_failure_class"] = _eval_failure_class(evaljson.get("reason"))
        integrity = evaljson.get("integrity")
        if isinstance(integrity, dict):
            parity = (_truth(integrity.get("own_fixed_parity")),
                      _truth(integrity.get("reads_parity_gold_read_K2")))
            out["integrity"] = {
                "weights_unchanged": _truth(integrity.get("weights_unchanged")),
                "label_perturbation": _truth(integrity.get("label_perturbation_identical")),
                "world_isolation": _truth(integrity.get("world_isolation_pass")),
                "parity": None if None in parity else bool(parity[0] and parity[1]),
            }
    return out


def _truth(value):
    """True/False for a boolean or a {'pass': bool} record; None when the field is absent."""
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and isinstance(value.get("pass"), bool):
        return value["pass"]
    return None


def _alive(pid, heartbeat):
    if heartbeat and heartbeat.get("exit_code") is not None:
        return False
    host = (heartbeat or {}).get("host")
    if pid is None:
        return None
    if host is not None and host != platform.node():
        return None                                           # remote: only the heartbeat can say
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError):
        return None
    return True


def health(root: Path, plan: dict, waves=None) -> dict:
    root = Path(root)
    rows, aggregate = [], {"jobs": 0, "started": 0, "running": 0, "train_complete": 0,
                           "train_incomplete": 0, "failed": 0, "eval_complete": 0}
    table = (waves or {}).get("table") or {}
    for pair in plan["pairs"]:
        pair_id = int(pair["pair_id"])
        for arm in ARMS:
            job = str(pair["jobs"][arm]["job_id"])
            tag = opaque_id(job)
            placed = table.get(job) or {}
            aggregate["jobs"] += 1

            pid_path = root / "pids" / f"{tag}.pid"
            pid = None
            if pid_path.is_file():
                text = pid_path.read_text().strip()
                pid = int(text) if text.isdigit() else None
            heartbeat_path = root / "heartbeats" / f"{tag}.json"
            heartbeat = read_json(heartbeat_path) if heartbeat_path.is_file() else None

            folder = root / "jobs" / job
            # result.json only appears when the launcher finishes; its manifest.json carries the
            # "started"/"failed" status from the first second, and no outcome field at all.
            result = None
            for name in ("result.json", "manifest.json"):
                if (folder / name).is_file():
                    result = read_json(folder / name)
                    break
            evaljson = read_json(folder / "eval.json") if (folder / "eval.json").is_file() else None
            checkpoint = folder / "model.pt"
            ckpt = {"exists": checkpoint.is_file(), "bytes": None, "sha256": None}
            if ckpt["exists"]:
                ckpt["bytes"] = checkpoint.stat().st_size
                ckpt["sha256"] = sha256_file(checkpoint)

            elapsed = None
            if heartbeat:
                if heartbeat.get("elapsed_seconds") is not None:
                    elapsed = _number(heartbeat.get("elapsed_seconds"))
                elif heartbeat.get("started_monotonic") is not None:
                    elapsed = round(time.time() - float(heartbeat["started_monotonic"]), 1)

            alive = _alive(pid, heartbeat)
            row = {"opaque_id": tag,
                   "placement": {"box": placed.get("box", box_of(pair_id)),
                                 "gpu": placed.get("gpu", gpu_of(pair_id)),
                                 "wave": placed.get("wave"),
                                 "start_order": placed.get("start_order")},
                   "pid": pid, "alive": alive, "elapsed_seconds": elapsed,
                   "exit_code": (heartbeat or {}).get("exit_code"),
                   "heartbeat_started_utc": (heartbeat or {}).get("started_utc"),
                   "heartbeat_finished_utc": (heartbeat or {}).get("finished_utc"),
                   "host": (heartbeat or {}).get("host"),
                   "checkpoint": ckpt}
            row.update(project(result, evaljson))
            if row["infrastructure_error_type"] is None and (heartbeat or {}).get("error_type"):
                row["infrastructure_error_type"] = _error_type(heartbeat["error_type"])
            rows.append(row)

            if heartbeat or result:
                aggregate["started"] += 1
            if alive:
                aggregate["running"] += 1
            if row["training_status"] == "complete":
                aggregate["train_complete"] += 1
            elif row["training_status"] == "incomplete":
                aggregate["train_incomplete"] += 1
            elif row["training_status"] == "failed":
                aggregate["failed"] += 1
            if row["evaluation_status"] == "complete":
                aggregate["eval_complete"] += 1

    return {"format": FORMAT + "-health", "experiment_id": EXPERIMENT_ID, "created_utc": utc_now(),
            "root": str(root), "allowlist_note":
                "13.6: placement, pid/alive/heartbeat, elapsed time, updates, counted FLOPs and share, "
                "training status, stop reason, budget_ok, exit code, sanitized error TYPE, checkpoint "
                "existence/size/hash, evaluation computation/integrity status. Nothing else, ever.",
            "aggregate": aggregate, "jobs": rows}


def cmd_health(args) -> int:
    plan = load_plan(args.plan)
    waves = read_json(args.waves) if args.waves else None
    record = health(Path(args.root), plan, waves)
    text = json.dumps(record, indent=2) + "\n"
    if args.out:
        write_new_json(args.out, record)
    print(text, end="")
    return 0


# ----------------------------------------------------------------------------- 13.7 inventory
def build_inventory(root: Path) -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise SystemExit(f"no such directory: {root}")
    rows, total = [], 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        size = path.stat().st_size
        total += size
        rows.append({"path": path.relative_to(root).as_posix(), "bytes": size,
                     "sha256": sha256_file(path)})
    return {"format": FORMAT + "-inventory", "experiment_id": EXPERIMENT_ID,
            "created_utc": utc_now(), "root": str(root), "files": len(rows),
            "total_bytes": total, "entries": rows}


def cmd_inventory(args) -> int:
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    if out.is_relative_to(root):
        raise SystemExit(f"{out} is inside {root}; write the inventory outside the tree it describes")
    record = build_inventory(root)
    write_new_json(out, record)
    print(json.dumps({"inventory": str(out), "files": record["files"],
                      "total_bytes": record["total_bytes"]}, indent=2))
    return 0


def verify_copy(inventory: dict, local_root: Path) -> dict:
    local_root = Path(local_root).resolve()
    missing, size_bad, hash_bad = [], [], []
    for row in inventory["entries"]:
        path = local_root / row["path"]
        if not path.is_file():
            missing.append(row["path"])
            continue
        if path.stat().st_size != row["bytes"]:
            size_bad.append(f"{row['path']}: {path.stat().st_size} bytes, inventory says {row['bytes']}")
            continue
        if sha256_file(path) != row["sha256"]:
            hash_bad.append(row["path"])
    listed = {row["path"] for row in inventory["entries"]}
    extra = sorted(p.relative_to(local_root).as_posix()
                   for p in local_root.rglob("*") if p.is_file()
                   and p.relative_to(local_root).as_posix() not in listed)
    return {"expected": len(inventory["entries"]),
            "verified": len(inventory["entries"]) - len(missing) - len(size_bad) - len(hash_bad),
            "missing": missing, "size_mismatch": size_bad, "hash_mismatch": hash_bad,
            "not_in_inventory": extra}


def cmd_verify_copy(args) -> int:
    report = verify_copy(read_json(args.inventory), Path(args.local_root))
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()},
                     indent=2))
    for label in ("missing", "size_mismatch", "hash_mismatch"):
        for item in report[label]:
            print(f"{label.upper()} {item}", file=sys.stderr)
    bad = len(report["missing"]) + len(report["size_mismatch"]) + len(report["hash_mismatch"])
    return 2 if bad else 0


# ----------------------------------------------------------------------------- 13.2 incidents
def incidents_path(root: Path) -> Path:
    return Path(root) / "incidents.jsonl"


GENESIS = sha256_text(EXPERIMENT_ID + "|incident-chain-genesis")


def read_incidents(root: Path) -> list:
    path = incidents_path(root)
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append({"line": line, "seq": number, "record": json.loads(line)})
        except json.JSONDecodeError:
            rows.append({"line": line, "seq": number, "record": None})
    return rows


def verify_incidents(root: Path) -> list:
    """Every break in the append-only hash chain, as readable strings."""
    problems, previous = [], GENESIS
    for row in read_incidents(root):
        record = row["record"]
        if record is None:
            problems.append(f"line {row['seq']}: not valid JSON")
            return problems
        if record.get("prev_sha256") != previous:
            problems.append(f"line {row['seq']}: prev_sha256 {record.get('prev_sha256')!r} != "
                            f"the previous line's hash {previous!r}")
        if record.get("seq") != row["seq"]:
            problems.append(f"line {row['seq']}: seq field is {record.get('seq')!r}")
        previous = sha256_text(row["line"])
    return problems


def append_incident(root: Path, *, cause: str, evidence: str, jobs, attestation: str) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    problems = verify_incidents(root)
    if problems:
        raise SystemExit("the incident chain is already broken; refusing to append: " + problems[0])
    rows = read_incidents(root)
    previous = sha256_text(rows[-1]["line"]) if rows else GENESIS
    job_ids = [j.strip() for j in jobs if j.strip()]
    pairs = sorted({int(match.group(1)) for j in job_ids
                    for match in [re.match(r"p(\d+)-", j)] if match})
    if not job_ids:
        raise SystemExit("--jobs must name at least one affected job id")
    record = {"format": FORMAT + "-incident", "experiment_id": EXPERIMENT_ID,
              "seq": len(rows) + 1, "utc": utc_now(), "cause": cause, "evidence": evidence,
              "jobs": job_ids, "pairs": pairs, "attestation": attestation,
              "supersession": "13.2: both arms of every affected pair are superseded and restarted "
                              "from the original initialization/seeds/streams at zero FLOPs; "
                              "no partial resume; maximum one training recovery per pair.",
              "prev_sha256": previous}
    line = json.dumps(record, sort_keys=True)
    with open(incidents_path(root), "a") as handle:
        handle.write(line + "\n")
    return record


def cmd_incident(args) -> int:
    root = Path(args.root)
    if args.verify:
        problems = verify_incidents(root)
        print(json.dumps({"incidents": len(read_incidents(root)), "problems": len(problems)}, indent=2))
        for line in problems:
            print("CHAIN " + line, file=sys.stderr)
        return 2 if problems else 0
    if not args.append:
        raise SystemExit("pass --append to add a record or --verify to check the chain")
    for name in ("cause", "evidence", "jobs", "attestation"):
        if not getattr(args, name):
            raise SystemExit(f"--{name} is required when appending an incident (13.2)")
    record = append_incident(root, cause=args.cause, evidence=args.evidence,
                             jobs=args.jobs.split(","), attestation=args.attestation)
    print(json.dumps({"seq": record["seq"], "pairs": record["pairs"], "jobs": record["jobs"],
                      "prev_sha256": record["prev_sha256"]}, indent=2))
    return 0


# ----------------------------------------------------------------------------- 13.2 recovery
def recoveries_path(root: Path) -> Path:
    return Path(root) / "recoveries.jsonl"


def elected_pairs(root: Path) -> set:
    path = recoveries_path(root)
    if not path.is_file():
        return set()
    out = set()
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.add(int(json.loads(line)["pair_id"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return out


def cmd_recovery_plan(args) -> int:
    root, pair_id = Path(args.root), int(args.pair)
    plan = load_plan(args.plan)
    pair = plan_pair(plan, pair_id)

    problems = verify_incidents(root)
    if problems:
        raise SystemExit("the incident chain is broken; no recovery may be elected: " + problems[0])
    naming = [row["record"] for row in read_incidents(root)
              if row["record"] and pair_id in (row["record"].get("pairs") or [])]
    if not naming:
        raise SystemExit(f"no incident record names pair {pair_id}; 13.2 permits a recovery only for "
                         f"an independently evidenced external interruption, appended and hashed first")
    if pair_id in elected_pairs(root):
        raise SystemExit(f"pair {pair_id} already has an elected recovery; 13.2 allows at most one "
                         f"training recovery per pair and never selects between attempts")
    attempt = root / "attempt1" / "jobs"
    existing = [pair["jobs"][arm]["job_id"] for arm in ARMS
                if (attempt / str(pair["jobs"][arm]["job_id"])).exists()]
    if existing:
        raise SystemExit(f"attempt1 directories already exist for {existing}; a recovery is never "
                         f"re-elected and a job directory is never reused")

    dirs = {arm: str(attempt / str(pair["jobs"][arm]["job_id"])) for arm in ARMS}
    record = {"format": FORMAT + "-recovery", "experiment_id": EXPERIMENT_ID, "pair_id": pair_id,
              "utc": utc_now(), "attempt": 1,
              "incident_seqs": [r.get("seq") for r in naming],
              "box": box_of(pair_id), "gpu": gpu_of(pair_id), "first_arm": first_arm_of(pair_id),
              "init_seed": pair.get("init_seed"), "data_seed": pair.get("data_seed"),
              "eval_seed": pair.get("eval_seed"),
              "directories": dirs,
              "opaque_ids": {arm: opaque_id(pair["jobs"][arm]["job_id"]) for arm in ARMS},
              "rule": "13.2: BOTH arms restart from the original initialization/seeds/streams at zero "
                      "FLOPs. No partial resume, no checkpoint reuse, no outcome-based selection; "
                      "attempt 1 is mandatory once elected and the originals are preserved."}
    recoveries_path(root).parent.mkdir(parents=True, exist_ok=True)
    with open(recoveries_path(root), "a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps({"pair_id": pair_id, "box": record["box"], "gpu": record["gpu"],
                      "first_arm": record["first_arm"], "seeds":
                          {"init": record["init_seed"], "data": record["data_seed"],
                           "eval": record["eval_seed"]},
                      "new_directories": [dirs[arm] for arm in ARMS],
                      "resume": False, "rule": record["rule"]}, indent=2))
    return 0


# ----------------------------------------------------------------------------- 13.6 lock
FAILURE_CLASSES = ("missing-job-directory", "missing-result", "unreadable-result",
                   "training-not-complete", "not-a-flop-budget-stop", "budget-not-ok",
                   "update-cap-exceeded", "time-cap-exceeded", "parameter-count-mismatch",
                   "missing-evaluation", "evaluation-not-complete", "integrity-not-all-true",
                   "evaluation-checkpoint-mismatch", "pair-init-digest-mismatch",
                   "pair-first-batches-mismatch")


def _job_failures(folder: Path) -> tuple:
    """(failure classes, {result digests}) for one canonical job. Never returns an outcome."""
    bad, facts = [], {"result_sha256": None, "eval_sha256": None, "checkpoint_sha256": None,
                      "init_state_sha256": None, "first_batches_sha256": None}
    if not folder.is_dir():
        return ["missing-job-directory"], facts
    result_path, eval_path = folder / "result.json", folder / "eval.json"
    if not result_path.is_file():
        bad.append("missing-result")
        return bad, facts
    facts["result_sha256"] = sha256_file(result_path)
    try:
        result = json.loads(result_path.read_text())
    except json.JSONDecodeError:
        return bad + ["unreadable-result"], facts
    facts["checkpoint_sha256"] = result.get("checkpoint_sha256")
    facts["init_state_sha256"] = result.get("init_state_sha256")
    facts["first_batches_sha256"] = result.get("first_batches_sha256")

    report = result.get("report") if isinstance(result.get("report"), dict) else {}
    if result.get("status") != "complete":
        bad.append("training-not-complete")
    if not str(report.get("stop", "")).startswith("flop budget"):
        bad.append("not-a-flop-budget-stop")
    if not bool(report.get("budget_ok")):
        bad.append("budget-not-ok")
    updates = result.get("updates_done")
    if not isinstance(updates, int) or updates > MAX_UPDATES:
        bad.append("update-cap-exceeded")
    seconds = result.get("seconds_train")
    if not isinstance(seconds, (int, float)) or seconds > MAX_SECONDS:
        bad.append("time-cap-exceeded")
    if result.get("parameters") != PARAMETERS:
        bad.append("parameter-count-mismatch")

    if not eval_path.is_file():
        bad.append("missing-evaluation")
        return bad, facts
    facts["eval_sha256"] = sha256_file(eval_path)
    try:
        evaljson = json.loads(eval_path.read_text())
    except json.JSONDecodeError:
        bad.append("evaluation-not-complete")
        return bad, facts
    if evaljson.get("status") != "complete":
        bad.append("evaluation-not-complete")
    integrity = evaljson.get("integrity") if isinstance(evaljson.get("integrity"), dict) else {}
    flags = project(None, evaljson)["integrity"]
    if not (all(flags[k] is True for k in flags) and _truth(integrity.get("all_pass")) is True):
        bad.append("integrity-not-all-true")
    reuse = evaljson.get("reuse_key") if isinstance(evaljson.get("reuse_key"), dict) else {}
    if not facts["checkpoint_sha256"] or reuse.get("checkpoint_sha256") != facts["checkpoint_sha256"]:
        bad.append("evaluation-checkpoint-mismatch")
    return bad, facts


def build_lock(root: Path, plan: dict) -> dict:
    require_full_roster(plan)
    root = Path(root)
    jobs, failures = [], {}
    facts_by_job = {}
    for pair in plan["pairs"]:
        for arm in ARMS:
            job = str(pair["jobs"][arm]["job_id"])
            folder = root / "jobs" / job
            bad, facts = _job_failures(folder)
            facts_by_job[job] = facts
            tag = opaque_id(job)
            jobs.append({"opaque_id": tag, "job_dir": str(folder),
                         "result_sha256": facts["result_sha256"], "eval_sha256": facts["eval_sha256"],
                         "checkpoint_sha256": facts["checkpoint_sha256"]})
            if bad:
                failures.setdefault(tag, []).extend(bad)
    for pair in plan["pairs"]:
        left, right = (facts_by_job[str(pair["jobs"][arm]["job_id"])] for arm in ARMS)
        tags = [opaque_id(str(pair["jobs"][arm]["job_id"])) for arm in ARMS]
        for field, name in (("init_state_sha256", "pair-init-digest-mismatch"),
                            ("first_batches_sha256", "pair-first-batches-mismatch")):
            if left[field] is None or right[field] is None or left[field] != right[field]:
                for tag in tags:
                    failures.setdefault(tag, []).append(name)

    failures = {tag: sorted(set(classes)) for tag, classes in failures.items()}
    verdict = "locked-complete" if not failures else "locked-with-terminal-failures"
    return {"format": FORMAT + "-lock", "experiment_id": EXPERIMENT_ID, "created_utc": utc_now(),
            "root": str(root), "expected_jobs": JOBS, "jobs_listed": len(jobs),
            "checks": {"training_status": "complete", "stop": "flop budget",
                       "budget_ok": True, "max_updates": MAX_UPDATES, "max_seconds": MAX_SECONDS,
                       "parameters": PARAMETERS, "evaluation_status": "complete",
                       "integrity": "weights_unchanged, label_perturbation, world_isolation, parity",
                       "reuse": "eval reuse_key.checkpoint_sha256 == result checkpoint_sha256",
                       "within_pair": "equal init_state_sha256 and first_batches_sha256"},
            "failure_classes": list(FAILURE_CLASSES),
            "verdict": verdict, "failures": failures, "failed_jobs": len(failures),
            "roster": jobs,
            "note": "13.6: this lock carries identity and completion only. No count, gate, loss, "
                    "recall, accuracy or paired summary appears here, and outcomes stay sealed until "
                    "the lock is final and recovery is permanently closed."}


def cmd_lock(args) -> int:
    plan = load_plan(args.plan)
    record = build_lock(Path(args.root), plan)
    write_new_json(args.out, record)
    print(json.dumps({"lock": str(args.out), "verdict": record["verdict"],
                      "jobs_listed": record["jobs_listed"], "failed_jobs": record["failed_jobs"],
                      "failures": record["failures"]}, indent=2))
    return 0 if record["verdict"] == "locked-complete" else 2


# ----------------------------------------------------------------------------- 13.3 worksheet
def ceil_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise SystemExit("--concurrency must be at least 1")
    return -(-int(numerator) // int(denominator))


def build_worksheet(*, concurrency, rate, eval_seconds, setup_seconds, price_per_hour,
                    machines, accrued) -> dict:
    if rate <= 0:
        raise SystemExit("--rate must be a positive counted-FLOP/s measurement")
    batches = ceil_div(JOBS, concurrency)
    per_job_train = B / float(rate)
    per_job = per_job_train + float(eval_seconds)
    total = float(setup_seconds) + batches * per_job
    machine_hours = float(machines) * total / 3600.0
    cost = float(accrued) + float(machines) * float(price_per_hour) * total / 3600.0
    flags = {
        "rate_above_nominal_floor": bool(float(rate) > NOMINAL_FLOOR_RATE),
        "per_job_training_within_1200_seconds": bool(per_job_train <= MAX_SECONDS),
        "T_within_target_1500_seconds": bool(total <= T_TARGET_SECONDS),
        "T_within_ceiling_1800_seconds": bool(total <= T_CEILING_SECONDS),
        "projected_cost_within_2_50": bool(cost <= SPEND_CAP_DOLLARS),
    }
    return {
        "format": FORMAT + "-worksheet", "experiment_id": EXPERIMENT_ID, "created_utc": utc_now(),
        "formula": "T = s + ceil(96/C) * (B/f_rate + e)   (12, retained by 13.3)",
        "inputs": {"concurrency_C": int(concurrency), "rate_counted_flops_per_second": float(rate),
                   "eval_seconds_e": float(eval_seconds), "setup_seconds_s": float(setup_seconds),
                   "price_per_hour_dollars": float(price_per_hour), "machines": int(machines),
                   "accrued_dollars": float(accrued)},
        "constants": {"B": B, "jobs": JOBS,
                      "nominal_per_job_floor_counted_flops_per_second": NOMINAL_FLOOR_RATE,
                      "max_seconds_per_job": MAX_SECONDS, "max_updates": MAX_UPDATES,
                      "target_seconds": T_TARGET_SECONDS, "ceiling_seconds": T_CEILING_SECONDS,
                      "spend_cap_dollars": SPEND_CAP_DOLLARS,
                      "two_dollar_threshold": EXCEPTION_THRESHOLD_DOLLARS},
        "derived": {"batches_ceil_96_over_C": batches,
                    "per_job_training_seconds": per_job_train,
                    "per_job_seconds_including_e": per_job,
                    "T_seconds": total, "machine_hours": machine_hours,
                    "projected_cost_dollars": cost},
        "flags": flags,
        "two_dollar_exception": {
            "rule": "13.3: a slower paid two-box plan is permitted only if the LOWEST-COST credible "
                    "available plan meeting 1,800 seconds costs OVER $2, with its full "
                    "price/performance basis recorded. A credible qualifying option at $2 or less "
                    "rules the slower fallback out; unknown cost/throughput never establishes it.",
            "operator_must_fill": True,
            "lowest_cost_credible_plan_meeting_1800_seconds": {
                "provider": None, "instance": None, "gpus": None,
                "price_per_hour_dollars": None, "projected_T_seconds": None,
                "projected_total_dollars": None, "quote_text": None, "quoted_utc": None,
                "source": None},
            "exception_available": None},
        "admitted": all(flags.values()),
        "admitted_note": "every flag must be true AND the $2 comparison above must be filled in "
                         "before any registered learning update.",
    }


def cmd_worksheet(args) -> int:
    record = build_worksheet(concurrency=args.concurrency, rate=args.rate,
                             eval_seconds=args.eval_seconds, setup_seconds=args.setup_seconds,
                             price_per_hour=args.price_per_hour, machines=args.machines,
                             accrued=args.accrued_dollars)
    write_new_json(args.out, record)
    print(json.dumps({"worksheet": str(args.out), "T_seconds": record["derived"]["T_seconds"],
                      "projected_cost_dollars": record["derived"]["projected_cost_dollars"],
                      "flags": record["flags"], "admitted": record["admitted"]}, indent=2))
    return 0 if record["admitted"] else 2


# ----------------------------------------------------------------------------- cli
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subs = parser.add_subparsers(dest="cmd", required=True)

    w = subs.add_parser("waves", help="the frozen pair/box/GPU/wave/order map and launch scripts")
    w.add_argument("--plan", required=True)
    w.add_argument("--procs-per-gpu", type=int, required=True, choices=PROCS_PER_GPU_RUNGS)
    w.add_argument("--out", required=True)
    w.add_argument("--python", default="python3", help="PYTHON variable of the launch scripts")
    w.add_argument("--repo", default="/workspace/beautiful-model", help="REPO_DIR variable")
    w.add_argument("--root", default="/workspace/a3-teacher-delay-v2", help="ROOT variable")
    w.add_argument("--plan-path", default="$ROOT/plan.json", help="PLAN variable")
    w.add_argument("--freeze-record", default="$ROOT/freeze/freeze_record.json",
                   help="FREEZE_RECORD variable")
    w.set_defaults(func=cmd_waves)

    p = subs.add_parser("preflight", help="capture / compare the pinned numerics and software record")
    p.add_argument("--out")
    p.add_argument("--box", choices=BOXES)
    p.add_argument("--require", help="a frozen preflight record whose pinned section must match exactly")
    p.add_argument("--use-record", help="compare this already-captured record instead of capturing live")
    p.add_argument("--image-digest", help="the resolved immutable container image digest (13.4); "
                                          "omitting it leaves an explicit null that fails --require")
    p.set_defaults(func=cmd_preflight)

    f = subs.add_parser("freeze", help="hash and freeze every authority, source, recipe and panel byte")
    f.add_argument("--root", required=True)
    f.add_argument("--plan", required=True)
    f.add_argument("--waves", required=True)
    f.add_argument("--preflight", action="append", required=True)
    f.add_argument("--rehearsal", action="append", required=True)
    f.add_argument("--worksheet", required=True)
    f.add_argument("--out", required=True)
    f.set_defaults(func=cmd_freeze)

    c = subs.add_parser("freeze-check", help="recompute every frozen hash")
    c.add_argument("--record", required=True)
    c.add_argument("--root", required=True)
    c.add_argument("--repo", default=str(REPO))
    c.add_argument("--groups", help="comma-separated subset, e.g. " + ",".join(EXECUTED_GROUPS))
    c.set_defaults(func=cmd_freeze_check)

    r = subs.add_parser("run-job", help="freeze-check + preflight --require, then ONE launcher job")
    r.add_argument("--freeze", required=True)
    r.add_argument("--plan", required=True)
    r.add_argument("--job", required=True)
    r.add_argument("--out-root", required=True)
    r.add_argument("--device", choices=("cuda", "cpu"), required=True)
    r.set_defaults(func=cmd_run_job)

    h = subs.add_parser("health", help="the ONLY monitoring view (13.6's allowlist)")
    h.add_argument("--root", required=True)
    h.add_argument("--plan", required=True)
    h.add_argument("--waves")
    h.add_argument("--out")
    h.set_defaults(func=cmd_health)

    i = subs.add_parser("inventory", help="path, bytes and sha256 for every file under ROOT")
    i.add_argument("--root", required=True)
    i.add_argument("--out", required=True)
    i.set_defaults(func=cmd_inventory)

    v = subs.add_parser("verify-copy", help="local custody check against a remote inventory")
    v.add_argument("--inventory", required=True)
    v.add_argument("--local-root", required=True)
    v.set_defaults(func=cmd_verify_copy)

    n = subs.add_parser("incident", help="append-only hash-chained incident log")
    n.add_argument("--root", required=True)
    n.add_argument("--append", action="store_true")
    n.add_argument("--verify", action="store_true")
    n.add_argument("--cause")
    n.add_argument("--evidence")
    n.add_argument("--jobs", help="comma-separated affected job ids")
    n.add_argument("--attestation", help="outcome-exposure attestation (13.2)")
    n.set_defaults(func=cmd_incident)

    y = subs.add_parser("recovery-plan", help="one blinded same-seed recovery per pair; never a resume")
    y.add_argument("--root", required=True)
    y.add_argument("--plan", required=True)
    y.add_argument("--pair", type=int, required=True)
    y.set_defaults(func=cmd_recovery_plan)

    k = subs.add_parser("lock", help="immutable roster/attempt lock; outcomes stay sealed")
    k.add_argument("--root", required=True)
    k.add_argument("--plan", required=True)
    k.add_argument("--out", required=True)
    k.set_defaults(func=cmd_lock)

    t = subs.add_parser("worksheet", help="T, the caps and the $2.50 cutoff")
    t.add_argument("--concurrency", type=int, required=True)
    t.add_argument("--rate", type=float, required=True)
    t.add_argument("--eval-seconds", type=float, required=True)
    t.add_argument("--setup-seconds", type=float, required=True)
    t.add_argument("--price-per-hour", type=float, required=True)
    t.add_argument("--machines", type=int, required=True)
    t.add_argument("--accrued-dollars", type=float, required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(func=cmd_worksheet)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
