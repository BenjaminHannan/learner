"""Fast CPU contracts for the A3-teacher-delay-v2 operations tooling (design/v3/13-launch-rulings.md).

Covers, with synthetic fixtures in a temporary directory: the 13.1 placement formula for all 48 pairs
and the 13.3 wave rungs, the arm-free opaque ids, the generated launch scripts, the 13.4 pinned
preflight comparison, the 13.7 freeze / freeze-check byte attestation, the 13.6 monitoring allowlist
(a leak test with sentinel values), the copy-back inventory, the 13.2 hash-chained incident log and
recovery refusals, the 13.6 roster lock, and the 13.3 cost/time worksheet arithmetic.

No GPU, no network, no training, no spending.  Torch is only touched by one optional smoke check at
the end, which is skipped if torch is not importable.

    PY -B tests/test_premonition_teacher_delay_ops.py
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_teacher_delay_ops as OPS  # noqa: E402

CHECKS = 0


def check(name, cond):
    global CHECKS
    assert bool(cond), name
    CHECKS += 1
    print("PASS " + name, flush=True)


def refuses(name, call):
    try:
        call()
    except SystemExit:
        check(name, True)
        return
    check(name, False)


def run(argv):
    """ops.main with stdout captured, returning (exit code, printed text)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = OPS.main(argv)
    return code, buffer.getvalue()


# ------------------------------------------------------------------------------------- fixtures
def make_plan(pairs=OPS.PAIRS) -> dict:
    rows = []
    for i in range(pairs):
        rows.append({"pair_id": i, "init_seed": 100000 + i, "data_seed": 200000 + i,
                     "eval_seed": 300000 + i,
                     "jobs": {"control": {"job_id": f"p{i:03d}-control", "teacher_until": 0.3666,
                                          "ramp_until": 0.5334},
                              "delayed": {"job_id": f"p{i:03d}-delayed", "teacher_until": 0.6,
                                          "ramp_until": 0.7668}}})
    return {"experiment_id": OPS.EXPERIMENT_ID, "B": OPS.B, "max_updates": OPS.MAX_UPDATES,
            "max_seconds": OPS.MAX_SECONDS, "pairs": rows}


PANEL_CELLS = ("c1", "c2", "c3", "c4", "c5", "c6", "reads")


def write_panels(root: Path, pairs=OPS.PAIRS) -> None:
    for pair_id in range(pairs):
        folder = root / "panels" / f"p{pair_id:03d}"
        folder.mkdir(parents=True)
        panels = {}
        for cell in PANEL_CELLS:
            path = folder / f"{cell}.pt"
            path.write_bytes(f"panel {cell} pair {pair_id}".encode())
            panels[cell] = {"cell": cell, "file": path.name, "n": 8,
                            "sha256": OPS.sha256_file(path), "bytes": path.stat().st_size}
        (folder / "manifest.json").write_text(json.dumps(
            {"experiment_id": OPS.EXPERIMENT_ID, "pair_id": pair_id, "eval_seed": 300000 + pair_id,
             "full_size": True, "panels": panels}, indent=1))


def preflight_record(box: str, **overrides) -> dict:
    pinned = {"python_version": "3.12.14", "python_implementation": "CPython",
              "torch_version": "2.8.0+cu128", "torch_cuda_version": "12.8", "cudnn_version": 91002,
              "cuda_matmul_allow_tf32": False, "cudnn_allow_tf32": True,
              "float32_matmul_precision": "highest", "cudnn_benchmark": False,
              "cudnn_deterministic": False, "deterministic_algorithms_enabled": False,
              "torch_num_threads": 1, "torch_num_interop_threads": 1,
              "pip_freeze_sha256": "a" * 64, "nvidia_driver_version": "580.65.06",
              "gpu_names": ["NVIDIA GeForce RTX 5060 Ti"] * 4,
              "platform_system": "Linux", "platform_machine": "x86_64",
              "image_digest": "sha256:" + "d" * 64,
              "env": {name: None for name in OPS.PREFLIGHT_ENV_VARS}}
    pinned["env"]["CUDA_MPS_PIPE_DIRECTORY"] = "/tmp/nvidia-mps"
    pinned["env"]["OMP_NUM_THREADS"] = "1"
    pinned.update(overrides)
    return {"format": OPS.FORMAT + "-preflight", "experiment_id": OPS.EXPERIMENT_ID, "box": box,
            "created_utc": OPS.utc_now(), "pinned": pinned,
            "telemetry": {"gpu_uuids": [f"GPU-{box}-{i}" for i in range(4)],
                          "cpu_model": "AMD EPYC 9354", "cpu_logical_cores": 96,
                          "hostname": f"box-{box}", "platform": "Linux-6.8.0-x86_64",
                          "platform_release": "6.8.0", "captured_utc": OPS.utc_now(),
                          "instance_env": {}},
            "pip_freeze": "torch==2.8.0\n", "notes": []}


def good_result(pair_id: int, arm: str, **overrides) -> dict:
    job = f"p{pair_id:03d}-{arm}"
    record = {"format": "premonition-teacher-delay-v2", "experiment_id": OPS.EXPERIMENT_ID,
              "job_id": job, "pair_id": pair_id, "arm": arm, "status": "complete",
              "report": {"stop": "flop budget", "budget_ok": True, "flops": OPS.B * 1.01,
                         "steps": 4200, "seconds": 900.0},
              "curve": [{"step": 50, "loss": 1.5}], "parameters": OPS.PARAMETERS,
              "init_state_sha256": f"init-{pair_id}", "first_batches_sha256": f"batches-{pair_id}",
              "seconds_train": 900.0, "updates_done": 4200, "flop_budget": OPS.B,
              "checkpoint_sha256": f"ckpt-{job}", "device": "cuda"}
    record.update(overrides)
    return record


def good_eval(pair_id: int, arm: str, **overrides) -> dict:
    job = f"p{pair_id:03d}-{arm}"
    record = {"experiment_id": OPS.EXPERIMENT_ID, "job_id": job, "pair_id": pair_id, "arm": arm,
              "status": "complete", "counts": {"c1": 2000}, "accuracy": {"c1": 0.97},
              "L_train": True, "G_pair": True, "c1_stuck": False,
              "integrity": {"weights_unchanged": True, "label_perturbation_identical": True,
                            "world_isolation_pass": True, "own_fixed_parity": {"pass": True},
                            "reads_parity_gold_read_K2": {"pass": True}, "all_pass": True},
              "reuse_key": {"checkpoint_sha256": f"ckpt-{job}"}}
    record.update(overrides)
    return record


def write_jobs(root: Path, plan: dict, mutate=None) -> None:
    for pair in plan["pairs"]:
        pair_id = int(pair["pair_id"])
        for arm in OPS.ARMS:
            job = pair["jobs"][arm]["job_id"]
            result, evaljson = good_result(pair_id, arm), good_eval(pair_id, arm)
            if mutate is not None:
                keep = mutate(pair_id, arm, result, evaljson)
                if keep is False:
                    continue
            folder = root / "jobs" / job
            folder.mkdir(parents=True)
            (folder / "result.json").write_text(json.dumps(result, indent=1))
            (folder / "eval.json").write_text(json.dumps(evaljson, indent=1))
            (folder / "model.pt").write_bytes(b"checkpoint bytes " + job.encode())


# ------------------------------------------------------------------------------------- the checks
def main() -> int:
    started = time.perf_counter()
    tmp = tempfile.TemporaryDirectory(prefix="teacher-delay-ops-test-")
    work = Path(tmp.name)
    plan = make_plan()

    # ------------------------------------------------------------------ 1. 13.1 placement formula
    boxes = {box: [p for p in range(OPS.PAIRS) if OPS.box_of(p) == box] for box in OPS.BOXES}
    check("13.1: even pair ids go to box A, odd to box B, 24 pairs each",
          boxes["A"] == list(range(0, OPS.PAIRS, 2)) and boxes["B"] == list(range(1, OPS.PAIRS, 2)))
    check("13.1: the GPU index is floor(pair_id/2) mod 4 for all 48 pairs",
          all(OPS.gpu_of(p) == (p // 2) % 4 for p in range(OPS.PAIRS)))
    check("13.1: every GPU of every box holds exactly 6 pairs",
          all(len(OPS.gpu_pairs(box, gpu)) == OPS.PAIRS_PER_GPU
              for box in OPS.BOXES for gpu in range(OPS.GPUS_PER_BOX))
          and sum(len(OPS.gpu_pairs(b, g)) for b in OPS.BOXES for g in range(4)) == OPS.PAIRS)
    check("13.1: the first arm is control when floor(pair_id/8) is even",
          all(OPS.first_arm_of(p) == ("control" if (p // 8) % 2 == 0 else "delayed")
              for p in range(OPS.PAIRS)))
    balance = {(box, gpu): sum(1 for p in OPS.gpu_pairs(box, gpu) if OPS.first_arm_of(p) == "control")
               for box in OPS.BOXES for gpu in range(OPS.GPUS_PER_BOX)}
    check("13.1: first-arm starts are balanced 3:3 on every GPU of every box",
          set(balance.values()) == {3} and len(balance) == 8)

    # ------------------------------------------------------------------ 2. 13.3 wave rungs
    for procs, expected in ((12, 1), (6, 2), (4, 3), (2, 6)):
        record = OPS.build_waves(plan, procs)
        pairs_per_wave = procs // 2
        check(f"13.3: {procs} processes/GPU gives {expected} wave(s)",
              record["waves"] == expected and len(record["boxes"]["A"]["waves"]) == expected
              and record["pairs_per_gpu_per_wave"] == pairs_per_wave)
        check(f"13.3: {procs} processes/GPU places all {OPS.JOBS} jobs exactly once",
              len(record["table"]) == OPS.JOBS
              and sum(len(g["jobs"]) for box in OPS.BOXES for w in record["boxes"][box]["waves"]
                      for g in w["gpus"]) == OPS.JOBS)
        whole, consecutive, formula, per_gpu_ok = True, True, True, True
        for box in OPS.BOXES:
            seen_per_gpu = {gpu: [] for gpu in range(OPS.GPUS_PER_BOX)}
            for wave in record["boxes"][box]["waves"]:
                for gpu in wave["gpus"]:
                    ids = [job["pair_id"] for job in gpu["jobs"]]
                    if len(gpu["pairs"]) != pairs_per_wave:
                        whole = False
                    if sorted(set(ids)) != sorted(gpu["pairs"]):
                        whole = False
                    for index in range(0, len(ids), 2):
                        if ids[index] != ids[index + 1]:
                            consecutive = False
                        arms = [gpu["jobs"][index]["job_id"].split("-")[1],
                                gpu["jobs"][index + 1]["job_id"].split("-")[1]]
                        if arms[0] != OPS.first_arm_of(ids[index]) or arms[0] == arms[1]:
                            consecutive = False
                    for job in gpu["jobs"]:
                        placed = record["table"][job["job_id"]]
                        if (placed["box"] != box or placed["gpu"] != gpu["gpu"]
                                or placed["wave"] != wave["wave"]
                                or OPS.box_of(job["pair_id"]) != box
                                or OPS.gpu_of(job["pair_id"]) != gpu["gpu"]):
                            formula = False
                    seen_per_gpu[gpu["gpu"]].extend(gpu["pairs"])
            for gpu, ids in seen_per_gpu.items():
                if ids != sorted(ids) or ids != OPS.gpu_pairs(box, gpu):
                    per_gpu_ok = False
        check(f"13.3: {procs} processes/GPU fills waves with whole pairs only", whole)
        check(f"13.3: {procs} processes/GPU starts a pair's two arms consecutively, first arm first",
              consecutive)
        check(f"13.3: {procs} processes/GPU keeps 13.1's box/GPU placement", formula)
        check(f"13.3: {procs} processes/GPU assigns successive pairs in ascending order per GPU",
              per_gpu_ok)

    waves_record = OPS.build_waves(plan, 6)
    tags = [row["opaque_id"] for row in waves_record["table"].values()]
    check("13.6: the 96 opaque job ids are unique and hide the arm names",
          len(set(tags)) == OPS.JOBS
          and all(t.startswith("j-") and len(t) == 12 for t in tags)
          and not any("control" in t or "delayed" in t or t[2:].isdigit() for t in tags))
    check("the opaque id is the documented sha256 prefix",
          OPS.opaque_id("p000-control")
          == "j-" + hashlib.sha256(b"A3-teacher-delay-v2|p000-control").hexdigest()[:10])

    # ------------------------------------------------------------------ 3. waves command + scripts
    box_root = work / "root"
    box_root.mkdir()
    (box_root / "plan.json").write_text(json.dumps(plan, indent=1))
    plan_path = box_root / "plan.json"
    waves_path = box_root / "waves.json"
    code, _ = run(["waves", "--plan", str(plan_path), "--procs-per-gpu", "6",
                   "--out", str(waves_path), "--python", "/usr/bin/python3.12",
                   "--repo", "/workspace/beautiful-model", "--root", "/workspace/a3"])
    check("waves writes the map and both launch scripts", code == 0 and waves_path.is_file()
          and (box_root / "launch_A.sh").is_file() and (box_root / "launch_B.sh").is_file())
    refuses("waves refuses to overwrite an existing map",
            lambda: run(["waves", "--plan", str(plan_path), "--procs-per-gpu", "6",
                         "--out", str(waves_path)]))

    script = (box_root / "launch_A.sh").read_text()
    check("the launch script pins the MPS directories and starts the control daemon if absent",
          'CUDA_MPS_PIPE_DIRECTORY="/tmp/nvidia-mps"' in script
          and 'CUDA_MPS_LOG_DIRECTORY="/tmp/nvidia-mps-log"' in script
          and "nvidia-cuda-mps-control -d" in script
          and 'if [ ! -e "$CUDA_MPS_PIPE_DIRECTORY/control" ]; then' in script)
    check("the launch script starts every job detached on a pinned GPU",
          "setsid nohup" in script and 'CUDA_VISIBLE_DEVICES="$gpu"' in script
          and "< /dev/null &" in script and "run-job" in script
          and "--device cuda" in script)
    check("the launch script writes a pid file and waits for each wave",
          'echo $! > "$ROOT/pids/$tag.pid"' in script and script.count("\nwait_for ") == 2)
    check("no launch script uses pkill anywhere",
          "pkill" not in script and "pkill" not in (box_root / "launch_B.sh").read_text())
    path_tokens = [token for text in (script, (box_root / "launch_B.sh").read_text())
                   for token in text.split() if ".log" in token or ".pid" in token]
    check("no arm name reaches a log or pid path",
          path_tokens and not any("control" in t or "delayed" in t for t in path_tokens))
    started_jobs = [line.split()[3] for line in script.splitlines() if line.startswith("start_job ")]
    check("box A's script starts its 48 jobs by opaque id only",
          len(started_jobs) == 48 and all(t.startswith("j-") for t in started_jobs)
          and len(set(started_jobs)) == 48)
    waves_json = json.loads(waves_path.read_text())
    check("the waves file carries the flat placement table",
          set(waves_json["table"]["p000-control"]) >= {"box", "gpu", "wave", "start_order"}
          and waves_json["table"]["p001-delayed"]["box"] == "B")

    # ------------------------------------------------------------------ 4. 13.4 preflight
    a1, a2 = preflight_record("A"), preflight_record("A")
    check("13.4: identical pinned sections compare equal", OPS.compare_pinned(a1, a2) == [])
    differing = preflight_record("A", torch_version="2.8.1+cu128")
    check("13.4: a pinned software difference is reported",
          any("torch_version" in line for line in OPS.compare_pinned(a1, differing)))
    tf32 = preflight_record("A", cuda_matmul_allow_tf32=True)
    check("13.4: a TF32 flag difference is reported",
          any("cuda_matmul_allow_tf32" in line for line in OPS.compare_pinned(a1, tf32)))
    env_changed = preflight_record("A")
    env_changed["pinned"]["env"]["OMP_NUM_THREADS"] = "8"
    check("13.4: an environment override difference is reported",
          any("env.OMP_NUM_THREADS" in line for line in OPS.compare_pinned(a1, env_changed)))
    nulled = preflight_record("A", cudnn_version=None)
    problems = OPS.compare_pinned(nulled, a1)
    check("13.4: a null pinned value fails even before the comparison",
          any("cudnn_version" in line and "null" in line for line in problems))
    unknown = preflight_record("A", float32_matmul_precision="default")
    check('13.4: "default" is not an acceptable pinned value',
          any("not an acceptable pinned value" in line for line in OPS.compare_pinned(unknown, a1)))
    check("13.4: an unset environment override is a real pinned value, not an unknown",
          OPS.compare_pinned(preflight_record("A"), preflight_record("A")) == [])
    no_digest = preflight_record("A", image_digest=None)
    check("13.4: an unrecorded container image digest fails --require",
          any("image_digest" in line and "null" in line
              for line in OPS.compare_pinned(no_digest, a1)))

    pre_a, pre_b = box_root / "preflight_A.json", box_root / "preflight_B.json"
    pre_a.write_text(json.dumps(a1, indent=1))
    pre_b.write_text(json.dumps(preflight_record("B"), indent=1))
    other = work / "preflight_A_drifted.json"
    other.write_text(json.dumps(differing, indent=1))
    code, _ = run(["preflight", "--use-record", str(pre_a), "--require", str(pre_a)])
    check("preflight --require exits 0 on an identical pinned section", code == 0)
    code, _ = run(["preflight", "--use-record", str(pre_a), "--require", str(other)])
    check("preflight --require exits non-zero on a pinned difference", code == 2)

    # ------------------------------------------------------------------ 5. 13.3 worksheet
    sheet_path = box_root / "worksheet.json"
    code, _ = run(["worksheet", "--concurrency", "12", "--rate", "4e11", "--eval-seconds", "20",
                   "--setup-seconds", "100", "--price-per-hour", "0.30", "--machines", "2",
                   "--accrued-dollars", "0.50", "--out", str(sheet_path)])
    sheet = json.loads(sheet_path.read_text())
    expect_t = 100.0 + 8 * (OPS.B / 4e11 + 20.0)
    check("13.3: T = s + ceil(96/C)*(B/f + e) is computed exactly",
          code == 0 and sheet["derived"]["batches_ceil_96_over_C"] == 8
          and abs(sheet["derived"]["T_seconds"] - expect_t) < 1e-9
          and abs(sheet["derived"]["per_job_training_seconds"] - OPS.B / 4e11) < 1e-9)
    check("13.3: the projected cost is accrued + machines*price*T/3600",
          abs(sheet["derived"]["projected_cost_dollars"] - (0.5 + 2 * 0.30 * expect_t / 3600)) < 1e-9)
    check("13.3: the admission flags cover the floor rate, the 1200 s job cap, 1500/1800 s and $2.50",
          sheet["flags"] == {"rate_above_nominal_floor": True,
                             "per_job_training_within_1200_seconds": True,
                             "T_within_target_1500_seconds": True,
                             "T_within_ceiling_1800_seconds": True,
                             "projected_cost_within_2_50": True} and sheet["admitted"] is True)
    check("13.3: the $2 exception comparison is present and left for the operator",
          sheet["two_dollar_exception"]["operator_must_fill"] is True
          and sheet["two_dollar_exception"]["exception_available"] is None
          and sheet["two_dollar_exception"][
              "lowest_cost_credible_plan_meeting_1800_seconds"]["price_per_hour_dollars"] is None)
    check("13.3: ceil(96/C) rounds up",
          [OPS.ceil_div(96, c) for c in (1, 7, 12, 13, 48, 95, 96, 97)]
          == [math.ceil(96 / c) for c in (1, 7, 12, 13, 48, 95, 96, 97)])
    slow_path = work / "worksheet_slow.json"
    code, _ = run(["worksheet", "--concurrency", "4", "--rate", "2e10", "--eval-seconds", "30",
                   "--setup-seconds", "120", "--price-per-hour", "0.60", "--machines", "2",
                   "--accrued-dollars", "1.90", "--out", str(slow_path)])
    slow = json.loads(slow_path.read_text())
    check("13.3: a rate below the nominal floor is flagged and the sheet is not admitted",
          code == 2 and slow["flags"]["rate_above_nominal_floor"] is False
          and slow["flags"]["per_job_training_within_1200_seconds"] is False
          and slow["flags"]["T_within_ceiling_1800_seconds"] is False
          and slow["admitted"] is False)
    refuses("worksheet refuses to overwrite an existing sheet",
            lambda: run(["worksheet", "--concurrency", "12", "--rate", "4e11", "--eval-seconds", "20",
                         "--setup-seconds", "100", "--price-per-hour", "0.30", "--machines", "2",
                         "--accrued-dollars", "0.50", "--out", str(sheet_path)]))

    # ------------------------------------------------------------------ 6. 13.7 freeze
    write_panels(box_root)
    reh_a, reh_b = box_root / "rehearsal_A.json", box_root / "rehearsal_B.json"
    reh_a.write_text(json.dumps({"box": "A", "concurrency_note": "6 per GPU"}, indent=1))
    reh_b.write_text(json.dumps({"box": "B", "concurrency_note": "6 per GPU"}, indent=1))
    (box_root / "validation").mkdir()
    transcript = box_root / "validation" / "transcript.txt"
    transcript.write_text("AAAAAAAAAA\n")

    freeze_args = ["freeze", "--root", str(box_root), "--plan", str(plan_path),
                   "--waves", str(waves_path), "--preflight", str(pre_a), "--preflight", str(pre_b),
                   "--rehearsal", str(reh_a), "--rehearsal", str(reh_b),
                   "--worksheet", str(sheet_path)]

    hidden = box_root / "panels" / "p017" / "c4.pt"
    stash = work / "c4.pt.stash"
    shutil.move(str(hidden), str(stash))
    refuses("13.7: freeze refuses when one pair's panel bytes are missing",
            lambda: run(freeze_args + ["--out", str(work / "freeze_missing_panel")]))
    shutil.move(str(stash), str(hidden))

    dropped = box_root / "panels" / "p041"
    shutil.move(str(dropped), str(work / "p041"))
    refuses("13.7: freeze refuses when a pair has no panel manifest at all",
            lambda: run(freeze_args + ["--out", str(work / "freeze_missing_pair")]))
    shutil.move(str(work / "p041"), str(dropped))

    refuses("13.7: freeze refuses when only one box has a preflight record",
            lambda: run(["freeze", "--root", str(box_root), "--plan", str(plan_path),
                         "--waves", str(waves_path), "--preflight", str(pre_a),
                         "--rehearsal", str(reh_a), "--worksheet", str(sheet_path),
                         "--out", str(work / "freeze_one_box")]))

    freeze_dir = box_root / "freeze"
    code, text = run(freeze_args + ["--out", str(freeze_dir)])
    manifest = json.loads((freeze_dir / "freeze_manifest.json").read_text())
    record = json.loads((freeze_dir / "freeze_record.json").read_text())
    check("13.7: freeze writes the manifest and a separate timestamped freeze record",
          code == 0 and record["manifest_sha256"] == OPS.sha256_file(freeze_dir / "freeze_manifest.json")
          and record["manifest_sha256"] in text and record["experiment_id"] == OPS.EXPERIMENT_ID)
    frozen = {(row["group"], row["path"]) for row in manifest["files"]}
    check("13.7.1: 08, 09, 12 and 13 are frozen",
          all(("authority", rel) in frozen for rel in OPS.DESIGN_FILES))
    check("13.7.2: the launcher, evaluator and ops tooling plus their tests are frozen",
          ("tooling", "scripts/premonition_teacher_delay.py") in frozen
          and ("tooling", "scripts/premonition_teacher_delay_eval.py") in frozen
          and ("tooling", "scripts/premonition_teacher_delay_ops.py") in frozen
          and ("tooling", "tests/test_premonition_teacher_delay_ops.py") in frozen)
    closure = {row["path"] for row in manifest["files"] if row["group"] == "source_closure"}
    check("13.7.2: the transitive premonition_* source closure is frozen",
          all(f"scripts/{m}.py" in closure for m in OPS.CLOSURE_SEEDS)
          and len(closure) >= len(OPS.CLOSURE_SEEDS))
    snapshot = [row for row in manifest["files"] if row["group"] == "frozen_snapshot"]
    check("13.7.2: every file FROZEN.SHA256SUMS lists is frozen, with the sums file itself",
          len(snapshot) >= 2 and any(row["path"].endswith("FROZEN.SHA256SUMS") for row in snapshot)
          and all(row.get("listed_sha256") in (None, row["sha256"]) for row in snapshot))
    panel_rows = [row for row in manifest["files"] if row["group"] == "panels"]
    check("13.7.5: all 48 pairs' panel manifests and panel bytes are frozen",
          len({row["pair_id"] for row in panel_rows}) == OPS.PAIRS
          and len(panel_rows) == OPS.PAIRS * (len(PANEL_CELLS) + 1))
    check("13.7.6/7: the plan, waves, both launch scripts, preflights, rehearsals, worksheet and "
          "validation transcripts are frozen",
          {row.get("role") for row in manifest["files"] if row["group"] == "plan_and_waves"}
          >= {"plan", "waves", "launch_A", "launch_B"}
          and sum(1 for row in manifest["files"] if row["group"] == "preflight") == 2
          and sum(1 for row in manifest["files"] if row["group"] == "rehearsal") == 2
          and any(row.get("role") == "cost_time_worksheet" for row in manifest["files"])
          and any(row["group"] == "validation" for row in manifest["files"]))
    refuses("13.7: freeze refuses to reuse an existing freeze directory",
            lambda: run(freeze_args + ["--out", str(freeze_dir)]))

    # ------------------------------------------------------------------ 7. 13.7 freeze-check
    record_path = freeze_dir / "freeze_record.json"
    code, _ = run(["freeze-check", "--record", str(record_path), "--root", str(box_root)])
    check("13.7: freeze-check passes on the untouched tree", code == 0)

    transcript.write_text("BAAAAAAAAA\n")          # one byte changed, same size
    problems = OPS.check_freeze(record_path, box_root, OPS.REPO)
    code, _ = run(["freeze-check", "--record", str(record_path), "--root", str(box_root)])
    check("13.7: freeze-check detects a one-byte, same-size change",
          code == 2 and len(problems) == 1 and problems[0].startswith("HASH"))
    transcript.write_text("AAAAAAAAAA\n")

    panel = box_root / "panels" / "p003" / "c2.pt"
    panel.write_bytes(panel.read_bytes() + b"x")
    check("13.7: freeze-check detects an appended byte in a panel file",
          any("p003/c2.pt" in line for line in OPS.check_freeze(record_path, box_root, OPS.REPO)))
    panel.write_bytes(panel.read_bytes()[:-1])

    moved = work / "waves.json.stash"
    shutil.move(str(waves_path), str(moved))
    check("13.7: freeze-check reports a missing frozen file",
          any(line.startswith("MISSING") and "waves.json" in line
              for line in OPS.check_freeze(record_path, box_root, OPS.REPO)))
    shutil.move(str(moved), str(waves_path))
    check("13.7: freeze-check restricted to the executed groups still covers plan and waves",
          OPS.check_freeze(record_path, box_root, OPS.REPO, OPS.EXECUTED_GROUPS) == []
          and any(row["group"] in OPS.EXECUTED_GROUPS and row.get("role") == "waves"
                  for row in manifest["files"]))
    tampered = freeze_dir / "freeze_manifest.json"
    tampered.write_text(tampered.read_text() + " ")
    refuses("13.7: freeze-check refuses a manifest whose own hash no longer matches the record",
            lambda: OPS.check_freeze(record_path, box_root, OPS.REPO))
    tampered.write_text(tampered.read_text()[:-1])

    # ------------------------------------------------------ 7b. run-job refuses on a changed byte
    plan_path.write_text(plan_path.read_text() + " ")          # a "late source/config fix"
    refuses("13.7: run-job refuses to start when a frozen byte changed since the freeze",
            lambda: run(["run-job", "--freeze", str(record_path), "--plan", str(plan_path),
                         "--job", "p000-control", "--out-root", str(box_root), "--device", "cpu"]))
    tag_first = OPS.opaque_id("p000-control")
    beat = json.loads((box_root / "heartbeats" / f"{tag_first}.json").read_text())
    check("13.6: the refusal is visible as a heartbeat with an exit code and a sanitized error type",
          beat["opaque_id"] == tag_first and beat["exit_code"] == 3
          and beat["error_type"] == "FrozenBytesChanged" and beat["stage"] == "refused"
          and (box_root / "pids" / f"{tag_first}.pid").read_text().strip().isdigit())
    check("13.6: no heartbeat or pid file carries an arm name",
          not any("control" in p.name or "delayed" in p.name
                  for p in (box_root / "heartbeats").iterdir())
          and not any("control" in p.name or "delayed" in p.name
                      for p in (box_root / "pids").iterdir()))
    plan_path.write_text(plan_path.read_text()[:-1])
    check("13.7: freeze-check passes again once the deployed bytes are restored",
          OPS.check_freeze(record_path, box_root, OPS.REPO) == [])

    # ------------------------------------------------------------------ 8. 13.6 health allowlist
    sentinel_loss, sentinel_count = 0.123456789, 1969424242
    leaky_result = good_result(0, "control")
    leaky_result.update({
        "curve": [{"step": 50, "loss": sentinel_loss, "lm": sentinel_loss, "ans": sentinel_loss,
                   "ask": sentinel_loss, "halt": sentinel_loss}],
        "phases": {"own": {"loss": sentinel_loss}}, "diagnostics": {"stuck": True},
        "accuracy": sentinel_loss, "error": "RuntimeError: CUDA error on device 3 while at loss "
                                            f"{sentinel_loss}"})
    leaky_result["report"].update({"loss": sentinel_loss, "answer_acc": sentinel_loss,
                                   "gold_recall_at_4": sentinel_loss})
    leaky_eval = good_eval(0, "control")
    leaky_eval.update({"counts": {"c1": sentinel_count, "c2": sentinel_count},
                       "per_unit": {"c1": [1, 0, 1]}, "accuracy": {"c1": sentinel_loss},
                       "L_train": True, "G_pair": False, "c1_stuck": True,
                       "diagnostics": {"c1": {"gold_recall_at_4": sentinel_loss}},
                       "cells": {"c1": {"count": sentinel_count}},
                       "status": "failed", "reason": f"an integrity check failed at {sentinel_loss}"})
    projection = OPS.project(leaky_result, leaky_eval)
    blob = json.dumps(projection)
    forbidden_keys = ("curve", "loss", "lm", "ans", "ask", "halt", "gold_recall_at_4", "answer_acc",
                      "counts", "per_unit", "L_train", "G_pair", "c1_stuck", "diagnostics",
                      "accuracy", "cells", "reason", "phases")
    check("13.6: the projection leaks no forbidden key",
          not any(f'"{key}"' in blob for key in forbidden_keys))
    check("13.6: the projection leaks no sentinel value",
          str(sentinel_loss) not in blob and str(sentinel_count) not in blob)
    check("13.6: the projection carries no arm name",
          "control" not in blob and "delayed" not in blob and "p000" not in blob)
    check("13.6: the projection keeps exactly the allowlisted fields",
          set(projection) == {"training_status", "stop_reason", "budget_ok", "updates_done",
                              "counted_flops", "counted_flop_share", "seconds_train",
                              "infrastructure_error_type", "evaluation_status",
                              "evaluation_failure_class", "integrity"}
          and set(projection["integrity"]) == {"weights_unchanged", "label_perturbation",
                                               "world_isolation", "parity"})
    check("13.6: the sanitized infrastructure error is the exception TYPE only",
          projection["infrastructure_error_type"] == "RuntimeError")
    check("13.6: allowlisted status fields still come through",
          projection["training_status"] == "complete" and projection["stop_reason"] == "flop-budget"
          and projection["budget_ok"] is True and projection["updates_done"] == 4200
          and abs(projection["counted_flop_share"] - 1.01) < 1e-6
          and projection["evaluation_status"] == "failed"
          and projection["evaluation_failure_class"] == "integrity-check-failed"
          and projection["integrity"]["weights_unchanged"] is True)
    check("13.6: a time-stopped job projects a time-cap stop reason, not a number",
          OPS.project({"status": "incomplete", "report": {"stop": "max_seconds", "budget_ok": False}},
                      None)["stop_reason"] == "time-cap")

    health_root = work / "health-root"
    small_plan = make_plan(2)
    (health_root / "jobs" / "p000-control").mkdir(parents=True)
    (health_root / "jobs" / "p000-control" / "result.json").write_text(json.dumps(leaky_result))
    (health_root / "jobs" / "p000-control" / "eval.json").write_text(json.dumps(leaky_eval))
    (health_root / "jobs" / "p000-control" / "model.pt").write_bytes(b"ck")
    (health_root / "jobs" / "p001-delayed").mkdir(parents=True)
    (health_root / "jobs" / "p001-delayed" / "manifest.json").write_text(json.dumps(
        {"format": "premonition-teacher-delay-v2", "job_id": "p001-delayed", "pair_id": 1,
         "arm": "delayed", "status": "started", "init_seed": 1, "flop_budget": OPS.B}))
    (health_root / "heartbeats").mkdir(parents=True)
    tag0 = OPS.opaque_id("p000-control")
    (health_root / "heartbeats" / f"{tag0}.json").write_text(json.dumps(
        {"opaque_id": tag0, "started_utc": OPS.utc_now(), "pid": 999999999,
         "host": "some-rental-box", "exit_code": None}))
    (health_root / "pids").mkdir(parents=True)
    (health_root / "pids" / f"{tag0}.pid").write_text("999999999\n")
    view = OPS.health(health_root, small_plan, waves_record)
    blob = json.dumps(view)
    check("13.6: the whole health view leaks no outcome key or sentinel",
          not any(f'"{key}"' in blob for key in forbidden_keys)
          and str(sentinel_loss) not in blob and str(sentinel_count) not in blob)
    check("13.6: the health view names jobs only by opaque id",
          "control" not in blob and "delayed" not in blob
          and all(row["opaque_id"].startswith("j-") for row in view["jobs"])
          and len(view["jobs"]) == 4)
    check("13.6: the health view reports placement, pid, checkpoint and aggregate counts",
          view["jobs"][0]["placement"]["box"] == "A"
          and view["jobs"][0]["placement"]["gpu"] == 0
          and view["jobs"][0]["pid"] == 999999999
          and view["jobs"][0]["checkpoint"]["exists"] is True
          and view["jobs"][0]["checkpoint"]["sha256"] == OPS.sha256_file(
              health_root / "jobs" / "p000-control" / "model.pt")
          and view["aggregate"]["jobs"] == 4 and view["aggregate"]["started"] == 2
          and view["aggregate"]["train_complete"] == 1 and view["aggregate"]["eval_complete"] == 0)
    check("13.6: a job that has only started is visible before any result.json exists",
          view["jobs"][3]["training_status"] == "started"
          and view["jobs"][3]["updates_done"] is None
          and view["jobs"][3]["checkpoint"]["exists"] is False)
    check("13.6: a remote job's liveness comes from the heartbeat, not from a local pid probe",
          view["jobs"][0]["alive"] is None)

    # ------------------------------------------------------------------ 9. 13.7 inventory/copy
    inv_root = work / "remote"
    (inv_root / "jobs" / "p000-control").mkdir(parents=True)
    (inv_root / "jobs" / "p000-control" / "model.pt").write_bytes(b"weights-0123456789")
    (inv_root / "jobs" / "p000-control" / "result.json").write_text('{"status": "complete"}')
    (inv_root / "incidents.jsonl").write_text("")
    inv_path = work / "inventory.json"
    code, _ = run(["inventory", "--root", str(inv_root), "--out", str(inv_path)])
    inventory = json.loads(inv_path.read_text())
    check("13.7: the inventory records path, bytes and sha256 for every file, skipping nothing",
          code == 0 and inventory["files"] == 3
          and {row["path"] for row in inventory["entries"]}
          == {"incidents.jsonl", "jobs/p000-control/model.pt", "jobs/p000-control/result.json"})
    refuses("inventory refuses to write inside the tree it describes",
            lambda: run(["inventory", "--root", str(inv_root), "--out", str(inv_root / "inv.json")]))

    local = work / "local"
    shutil.copytree(inv_root, local)
    code, _ = run(["verify-copy", "--inventory", str(inv_path), "--local-root", str(local)])
    check("13.7: verify-copy passes on a faithful copy", code == 0)
    (local / "jobs" / "p000-control" / "result.json").unlink()
    report = OPS.verify_copy(inventory, local)
    check("13.7: verify-copy reports a missing file",
          report["missing"] == ["jobs/p000-control/result.json"] and report["verified"] == 2)
    (local / "jobs" / "p000-control" / "result.json").write_text('{"status": "complete"} ')
    report = OPS.verify_copy(inventory, local)
    check("13.7: verify-copy reports a size change", len(report["size_mismatch"]) == 1)
    (local / "jobs" / "p000-control" / "model.pt").write_bytes(b"weights-9876543210")
    report = OPS.verify_copy(inventory, local)
    check("13.7: verify-copy reports a same-size content change",
          report["hash_mismatch"] == ["jobs/p000-control/model.pt"])
    code, _ = run(["verify-copy", "--inventory", str(inv_path), "--local-root", str(local)])
    check("13.7: verify-copy exits non-zero when custody is not proven", code == 2)

    # ------------------------------------------------------------------ 10. 13.2 incidents
    inc_root = work / "incidents"
    inc_root.mkdir()
    for seq, pair_id in enumerate((5, 5, 12), start=1):
        code, _ = run(["incident", "--root", str(inc_root), "--append",
                       "--cause", "provider host death",
                       "--evidence", "provider console event log entry",
                       "--jobs", f"p{pair_id:03d}-control,p{pair_id:03d}-delayed",
                       "--attestation", "no registered learning outcome was exposed"])
        check(f"13.2: incident record {seq} appends to the hash chain", code == 0)
    code, _ = run(["incident", "--root", str(inc_root), "--verify"])
    check("13.2: the untampered incident chain verifies", code == 0
          and OPS.verify_incidents(inc_root) == [])
    lines = OPS.incidents_path(inc_root).read_text().splitlines()
    check("13.2: every record carries the previous line's hash",
          json.loads(lines[0])["prev_sha256"] == OPS.GENESIS
          and json.loads(lines[1])["prev_sha256"] == OPS.sha256_text(lines[0])
          and json.loads(lines[2])["prev_sha256"] == OPS.sha256_text(lines[1]))
    edited = json.loads(lines[1])
    edited["cause"] = "a quietly rewritten cause"
    OPS.incidents_path(inc_root).write_text("\n".join(
        [lines[0], json.dumps(edited, sort_keys=True), lines[2]]) + "\n")
    problems = OPS.verify_incidents(inc_root)
    code, _ = run(["incident", "--root", str(inc_root), "--verify"])
    check("13.2: rewriting an earlier incident breaks the chain", code == 2 and problems
          and "line 3" in problems[0])
    refuses("13.2: appending onto a broken chain is refused",
            lambda: run(["incident", "--root", str(inc_root), "--append", "--cause", "x",
                         "--evidence", "y", "--jobs", "p001-control", "--attestation", "z"]))
    OPS.incidents_path(inc_root).write_text("\n".join(lines) + "\n")
    refuses("13.2: an incident without evidence or attestation is refused",
            lambda: run(["incident", "--root", str(inc_root), "--append", "--cause", "x",
                         "--jobs", "p001-control"]))

    # ------------------------------------------------------------------ 11. 13.2 recovery
    refuses("13.2: recovery-plan refuses a pair no incident record names",
            lambda: run(["recovery-plan", "--root", str(inc_root), "--plan", str(plan_path),
                         "--pair", "7"]))
    code, text = run(["recovery-plan", "--root", str(inc_root), "--plan", str(plan_path),
                      "--pair", "5"])
    out = json.loads(text)
    check("13.2: recovery-plan names both arms' new attempt1 directories",
          code == 0 and out["new_directories"] == [str(inc_root / "attempt1" / "jobs" / "p005-control"),
                                                   str(inc_root / "attempt1" / "jobs" / "p005-delayed")])
    check("13.2: recovery keeps the ORIGINAL seeds, box, GPU and first arm, and never resumes",
          out["seeds"] == {"init": 100005, "data": 200005, "eval": 300005}
          and out["box"] == OPS.box_of(5) and out["gpu"] == OPS.gpu_of(5)
          and out["first_arm"] == OPS.first_arm_of(5) and out["resume"] is False)
    refuses("13.2: a second recovery for the same pair is refused",
            lambda: run(["recovery-plan", "--root", str(inc_root), "--plan", str(plan_path),
                         "--pair", "5"]))
    code, _ = run(["recovery-plan", "--root", str(inc_root), "--plan", str(plan_path), "--pair", "12"])
    check("13.2: a different evidenced pair may still elect its one recovery", code == 0)
    fresh = work / "fresh-incidents"
    fresh.mkdir()
    run(["incident", "--root", str(fresh), "--append", "--cause", "storage failure",
         "--evidence", "provider storage incident ticket", "--jobs", "p020-control,p020-delayed",
         "--attestation", "no registered learning outcome was exposed"])
    (fresh / "attempt1" / "jobs" / "p020-control").mkdir(parents=True)
    refuses("13.2: an existing attempt1 directory is never reused",
            lambda: run(["recovery-plan", "--root", str(fresh), "--plan", str(plan_path),
                         "--pair", "20"]))

    # ------------------------------------------------------------------ 12. 13.6 lock
    lock_ok = work / "lock-ok"
    write_jobs(lock_ok, plan)
    lock_path = work / "lock-ok.json"
    code, _ = run(["lock", "--root", str(lock_ok), "--plan", str(plan_path), "--out", str(lock_path)])
    lock = json.loads(lock_path.read_text())
    check("13.6: a complete roster locks as locked-complete",
          code == 0 and lock["verdict"] == "locked-complete" and lock["failures"] == {}
          and lock["jobs_listed"] == OPS.JOBS)
    check("13.6: the lock carries job dirs and result/eval hashes, and no outcome",
          all(row["result_sha256"] and row["eval_sha256"] for row in lock["roster"])
          and not any(f'"{key}"' in json.dumps(lock)
                      for key in ("counts", "per_unit", "L_train", "G_pair", "c1_stuck",
                                  "accuracy", "curve", "diagnostics")))
    refuses("lock refuses to overwrite an existing lock record",
            lambda: run(["lock", "--root", str(lock_ok), "--plan", str(plan_path),
                         "--out", str(lock_path)]))

    def break_things(pair_id, arm, result, evaljson):
        if (pair_id, arm) == (1, "control"):                    # a time stop, not a FLOP stop
            result["report"]["stop"] = "max_seconds"
            result["status"] = "incomplete"
            result["seconds_train"] = 1200.5
        if (pair_id, arm) == (2, "delayed"):                    # budget_ok false
            result["report"]["budget_ok"] = False
        if (pair_id, arm) == (3, "control"):                    # within-pair init digest mismatch
            result["init_state_sha256"] = "init-somewhere-else"
        if (pair_id, arm) == (4, "delayed"):                    # evaluation of another checkpoint
            evaljson["reuse_key"]["checkpoint_sha256"] = "ckpt-someone-else"
        if (pair_id, arm) == (6, "control"):                    # integrity did not all pass
            evaljson["integrity"]["world_isolation_pass"] = False
            evaljson["integrity"]["all_pass"] = False
        if (pair_id, arm) == (9, "control"):                    # the update ceiling was reached
            result["updates_done"] = 20001
        if (pair_id, arm) == (5, "delayed"):                    # never started / lost
            return False
        return True

    lock_bad = work / "lock-bad"
    write_jobs(lock_bad, plan, break_things)
    bad_path = work / "lock-bad.json"
    code, _ = run(["lock", "--root", str(lock_bad), "--plan", str(plan_path), "--out", str(bad_path)])
    bad = json.loads(bad_path.read_text())
    failures = bad["failures"]

    def classes(job):
        return failures.get(OPS.opaque_id(job), [])

    check("13.6: a broken roster locks as locked-with-terminal-failures", code == 2
          and bad["verdict"] == "locked-with-terminal-failures")
    check("13.6: a time-stopped job is a terminal failure",
          "not-a-flop-budget-stop" in classes("p001-control")
          and "training-not-complete" in classes("p001-control")
          and "time-cap-exceeded" in classes("p001-control"))
    check("13.6: budget_ok false is a terminal failure",
          classes("p002-delayed") == ["budget-not-ok"])
    check("13.6: a within-pair initialization digest mismatch fails BOTH arms",
          "pair-init-digest-mismatch" in classes("p003-control")
          and "pair-init-digest-mismatch" in classes("p003-delayed"))
    check("13.6: an evaluation whose reuse key names another checkpoint fails",
          classes("p004-delayed") == ["evaluation-checkpoint-mismatch"])
    check("13.6: a missing job directory fails, and drags its pair's digest check with it",
          "missing-job-directory" in classes("p005-delayed")
          and "pair-init-digest-mismatch" in classes("p005-control"))
    check("13.6: an integrity check that did not pass fails",
          classes("p006-control") == ["integrity-not-all-true"])
    check("13.6: exceeding the 20,000-update ceiling fails",
          classes("p009-control") == ["update-cap-exceeded"])
    check("13.6: every reported failure uses an opaque id and a declared failure CLASS only",
          all(tag.startswith("j-") for tag in failures)
          and all(name in OPS.FAILURE_CLASSES for names in failures.values() for name in names))
    check("13.6: untouched pairs are not flagged", OPS.opaque_id("p047-control") not in failures)

    # ------------------------------------------------------------------ 13. optional torch smoke
    try:
        import torch                                            # noqa: F401
    except BaseException:                                       # noqa: BLE001 - torch is optional here
        print("SKIP torch preflight smoke (torch is not importable here)", flush=True)
    else:
        smoke = work / "preflight_live.json"
        code, _ = run(["preflight", "--out", str(smoke)])
        live = json.loads(smoke.read_text())
        check("13.4: a live preflight capture records the pinned numerics and separates telemetry",
              code == 0 and live["pinned"]["torch_version"]
              and live["pinned"]["float32_matmul_precision"] in ("highest", "high", "medium")
              and isinstance(live["pinned"]["cuda_matmul_allow_tf32"], bool)
              and isinstance(live["pinned"]["cudnn_benchmark"], bool)
              and set(live["pinned"]["env"]) == set(OPS.PREFLIGHT_ENV_VARS)
              and "cpu_logical_cores" in live["telemetry"]
              and "gpu_uuids" in live["telemetry"])
        check("13.4: a live capture compares equal to itself and is not silently 'unknown'",
              OPS.compare_pinned(live, live) == []
              or all("null" in line for line in OPS.compare_pinned(live, live)))

    tmp.cleanup()
    print(f"ALL {CHECKS} CHECKS PASSED in {time.perf_counter() - started:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
