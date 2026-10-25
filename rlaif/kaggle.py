#!/usr/bin/env python3
"""RLAIF controller for a free Kaggle notebook (2x T4, fp16), driven by the `kaggle` CLI from this container.

Never prints the Anthropic key. The key travels only as a PRIVATE Kaggle dataset (<user>/learner-anthropic-key).

  secret                  create/version the private key dataset from env LEARNER_ANTHROPIC_API_KEY
  build [--run N] [--smoke]   write rlaif/kaggle_kernel/<run>/{kernel-metadata.json,job.py}
  push | status | pull | log  [--run N]     (pull -> rlaif/runs/kaggle-<run>/)

Order once a token exists:  kaggle auth login (or ~/.kaggle/kaggle.json) ; secret ; build --smoke --run smoke ; push --run smoke ;
status --run smoke ; pull --run smoke ; log --run smoke ; then build / push / pull the real run.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KERNELS = HERE / "kaggle_kernel"
RUNS = HERE / "runs"
KEY_ENV = "LEARNER_ANTHROPIC_API_KEY"
KEY_SLUG = "learner-anthropic-key"
ACCEL = "NvidiaTeslaT4"
CODE_FILES = ["train.py", "rollout.py", "grader.py", "sandbox.py", "checks.py", "tools.json"]

FULL = dict(deadline_s=11 * 3600, min_reserve_s=45 * 60, unknown_reserve_s=int(2.5 * 3600), progress_s=300,
            common="--steps 20 --tasks-per-step 8 --group 4 --seed 0 --save-every 2 --max-usd 14 --dtype fp16 --gen-batch 8",
            eval_flags="--eval-only --eval-grade --dtype fp16")
# RLAIF-2 (rlaif/SPEC.md): reward v3, lr 1e-4, 30 steps; eval the base model and run-1 jolt_step20 first, then steps 10/20/30 of both arms.
RLAIF2 = dict(plan="rlaif2", deadline_s=int(10.75 * 3600), min_reserve_s=45 * 60, unknown_reserve_s=int(2.5 * 3600), progress_s=300,
              common="--reward-v3 --lr 1e-4 --steps 30 --tasks-per-step 8 --group 4 --seed 0 --save-every 10 --gen-batch 8 --max-usd 14 --dtype fp16",
              jolt_extra="--beta-t 0.001 --beta-s 0.1",
              eval_flags="--eval-only --eval-grade --dtype fp16 --gen-batch 4")
SMOKE = dict(deadline_s=40 * 60, min_reserve_s=8 * 60, unknown_reserve_s=15 * 60, progress_s=60,
             common="--steps 2 --tasks-per-step 2 --group 2 --seed 0 --save-every 1 --max-usd 2 --dtype fp16",
             eval_flags="--eval-only --eval-grade --dtype fp16 --n-eval 4")


def kg(*args, check=True):
    """Run the kaggle CLI; returns CompletedProcess (stdout/stderr captured, printed by callers if wanted)."""
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"kaggle {' '.join(args[:2])} failed (rc={r.returncode}):\n{(r.stdout + r.stderr).strip()[-1500:]}")
    return r


def username(a=None):
    if a is not None and getattr(a, "user", None):
        return a.user
    if os.environ.get("KAGGLE_USERNAME"):
        return os.environ["KAGGLE_USERNAME"]
    try:
        return json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())["username"]
    except Exception:
        pass
    m = re.search(r"username\W+(\S+)", kg("config", "view", check=False).stdout)
    if m:
        return m.group(1)
    raise SystemExit("cannot find the Kaggle username (set KAGGLE_USERNAME, pass --user, or log in)")


def kdir(run):
    return KERNELS / run


# ----------------------------------------------------------------------------- secret
def secret(a):
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise SystemExit(f"{KEY_ENV} is not set; nothing done")
    u = username(a)
    ref = f"{u}/{KEY_SLUG}"
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "key").write_text(key)
        os.chmod(Path(d) / "key", 0o600)
        (Path(d) / "dataset-metadata.json").write_text(json.dumps(
            {"title": KEY_SLUG, "id": ref, "licenses": [{"name": "CC0-1.0"}], "isPrivate": True}, indent=1))
        exists = kg("datasets", "status", ref, check=False).returncode == 0
        r = kg("datasets", "version", "-p", d, "-m", "update key") if exists else kg("datasets", "create", "-p", d)
    print(json.dumps({"dataset": ref, "action": "versioned" if exists else "created", "private": True,
                      "output": r.stdout.replace(key, "<REDACTED>").strip()[-300:]}))


# ----------------------------------------------------------------------------- build
def pack_code():
    buf = io.BytesIO()

    def norm(i):
        i.uid = i.gid = 0
        i.uname = i.gname = ""
        i.mtime = 0
        return i
    files = [HERE / f for f in CODE_FILES] + sorted((HERE / "data").glob("*.jsonl"))
    with tarfile.open(fileobj=buf, mode="w:xz", preset=9) as t:
        for p in files:
            t.add(p, arcname=str(p.relative_to(HERE)), filter=norm)
    return buf.getvalue(), len(files)


def build(a):
    u = username(a)
    cfg = dict(SMOKE if a.smoke else RLAIF2 if a.plan == "rlaif2" else FULL)
    if a.deadline_h:
        cfg["deadline_s"] = int(a.deadline_h * 3600)
    cfg.update(run=a.run, smoke=bool(a.smoke), heldout="data/tasks_heldout.jsonl", train="data/tasks_train.jsonl")
    code, n = pack_code()
    b64 = base64.b64encode(code).decode()
    payload = "\n".join(b64[i:i + 100] for i in range(0, len(b64), 100))
    job = JOB.replace("__CFG__", json.dumps(cfg)).replace("__PAYLOAD__", payload)
    d = kdir(a.run)
    d.mkdir(parents=True, exist_ok=True)
    (d / "job.py").write_text(job)
    # Kaggle's website "Save & Run All" (the only path that hands over Secrets) treats the kernel as a notebook,
    # so ship the same code as a one-cell notebook.
    nb = {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
          "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": job}]}
    (d / "job.ipynb").write_text(json.dumps(nb))
    meta = {"id": f"{u}/rlaif-{a.run}", "title": f"rlaif-{a.run}", "code_file": "job.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": "true", "enable_gpu": "true", "enable_internet": "true",
            "dataset_sources": ([] if a.no_key_dataset else [f"{u}/{KEY_SLUG}"]) + [f"{u}/{x}" for x in (a.dataset_source or [])], "competition_sources": [],
            "kernel_sources": [f"{u}/{k}" for k in (a.kernel_source or [])]}
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({"dir": str(d), "id": meta["id"], "code_files": n, "xz_bytes": len(code), "job_bytes": len(job),
                      "deadline_h": round(cfg["deadline_s"] / 3600, 2), "smoke": cfg["smoke"]}))


# ----------------------------------------------------------------------------- push / status / pull / log
def ref_of(a):
    return json.loads((kdir(a.run) / "kernel-metadata.json").read_text())["id"] if (kdir(a.run) / "kernel-metadata.json").is_file() \
        else f"{username(a)}/rlaif-{a.run}"


def push(a):
    if not (kdir(a.run) / "job.py").is_file():
        raise SystemExit(f"run build --run {a.run} first")
    r = kg("kernels", "push", "-p", str(kdir(a.run)), "--accelerator", ACCEL)
    print((r.stdout + r.stderr).strip())


def status(a):
    r = kg("kernels", "status", ref_of(a), check=False)
    print((r.stdout + r.stderr).strip())


def pull(a):
    d = RUNS / f"kaggle-{a.run}"
    d.mkdir(parents=True, exist_ok=True)
    r = kg("kernels", "output", ref_of(a), "-p", str(d))
    print((r.stdout + r.stderr).strip()[-800:])
    print("files:", sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file())[:40])
    s = d / "out" / "summary.json"
    if s.is_file():
        print(s.read_text())


def log(a):
    d = RUNS / f"kaggle-{a.run}"
    logs = sorted(d.glob("*.log"))
    if not logs:
        raise SystemExit(f"no .log in {d}; pull first")
    txt = logs[0].read_text(errors="replace")
    try:    # Kaggle logs are a JSON list of {"data": ...} records
        txt = "".join(x.get("data", "") for x in json.loads(txt))
    except Exception:
        pass
    print("\n".join(txt.splitlines()[-a.lines:]))


# ----------------------------------------------------------------------------- the job that runs inside Kaggle
JOB = r'''# Generated by rlaif/kaggle.py. Runs rlaif GRPO vs JOLT+ on 2x T4. Self-contained: code is embedded below.
# KAGGLE_JOB_DRY=1: use $KAGGLE_JOB_ROOT (default /tmp/kjob), fake grader, stub trainer (set KAGGLE_JOB_REAL=1 for the real one).
import base64, glob, io, json, os, shutil, signal, subprocess, sys, tarfile, threading, time
T0 = time.time()
CFG = json.loads(r"""__CFG__""")
PAYLOAD = """
__PAYLOAD__
"""
DRY = os.environ.get("KAGGLE_JOB_DRY") == "1"
ROOT = os.environ.get("KAGGLE_JOB_ROOT", "/tmp/kjob") if DRY else "/kaggle/working"
JOB, OUT = os.path.join(ROOT, "job"), os.path.join(ROOT, "out")
WORK = os.path.join(JOB, "work")
DEADLINE = T0 + CFG["deadline_s"]
lock = threading.Lock()
STATUS, ACTIVE, TIMES = {}, {}, {}


def say(*a):
    print(f"[{time.strftime('%H:%M:%S')} +{(time.time() - T0) / 60:6.1f}m]", *a, flush=True)


def write_status():
    with lock:
        os.makedirs(OUT, exist_ok=True)
        json.dump(STATUS, open(os.path.join(OUT, "status.json"), "w"), indent=1)


STUB = r"""
import argparse, json, os, sys, time
ap = argparse.ArgumentParser(); ap.add_argument("--eval-only", action="store_true"); ap.add_argument("--adapter"); ap.add_argument("--outdir")
ap.add_argument("--steps", type=int, default=2); ap.add_argument("--save-every", type=int, default=1); ap.add_argument("--algo", default="grpo")
a, _ = ap.parse_known_args(); os.makedirs(a.outdir, exist_ok=True); print("stub", sys.argv[1:], os.environ.get("CUDA_VISIBLE_DEVICES"), flush=True)
if a.eval_only:
    time.sleep(1); tag = os.path.basename((a.adapter or "base").rstrip("/"))
    json.dump(dict(adapter=a.adapter, n=4, success_rate=0.5, mean_check_frac=0.5, sonnet_mean=5.0, usd=0.0), open(os.path.join(a.outdir, f"eval_{tag}.json"), "w"))
    json.dump(dict(usd=0.01), open(os.path.join(a.outdir, "spend.json"), "w"))
else:
    for s in range(1, a.steps + 1):
        time.sleep(1 if a.algo == "grpo" else 2); open(os.path.join(a.outdir, "log.jsonl"), "a").write(json.dumps(dict(step=s)) + "\n")
        if s % a.save_every == 0 or s == a.steps:
            d = os.path.join(a.outdir, f"adapter_step{s}"); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "adapter_config.json"), "w").write("{}"); open(os.path.join(d, "adapter_model.safetensors"), "w").write("x" * 10)
    os.makedirs(os.path.join(a.outdir, "adapter_final"), exist_ok=True)
    open(os.path.join(a.outdir, "adapter_final", "adapter_config.json"), "w").write("{}"); open(os.path.join(a.outdir, "adapter_final", "adapter_model.safetensors"), "w").write("x" * 10)
    json.dump(dict(usd=0.02), open(os.path.join(a.outdir, "spend.json"), "w"))
"""


def unpack():
    shutil.rmtree(JOB, ignore_errors=True)
    os.makedirs(JOB)
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode("".join(PAYLOAD.split()))), mode="r:xz") as t:
        t.extractall(JOB, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    open(os.path.join(JOB, "stub_train.py"), "w").write(STUB)
    say("unpacked:", sorted(os.listdir(JOB)))


def find_key():
    for p in glob.glob("/kaggle/input/**/key", recursive=True):
        if os.path.isfile(p):
            v = open(p).read().strip()
            if v:
                os.environ["LEARNER_ANTHROPIC_API_KEY"] = v
                return True
    if not os.environ.get("LEARNER_ANTHROPIC_API_KEY"):
        try:  # a Kaggle Secret named LEARNER_ANTHROPIC_API_KEY attached to the notebook in the Kaggle UI
            from kaggle_secrets import UserSecretsClient
            v = UserSecretsClient().get_secret("LEARNER_ANTHROPIC_API_KEY")
            if v:
                os.environ["LEARNER_ANTHROPIC_API_KEY"] = v.strip()
        except Exception as e:
            say("no Kaggle secret:", type(e).__name__)
    return bool(os.environ.get("LEARNER_ANTHROPIC_API_KEY"))


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def pip_ensure():
    from importlib import metadata
    try:  # Kaggle ships torchao 0.10; peft 0.20 refuses to build LoRA layers when an old torchao is importable
        if tuple(int(x) for x in metadata.version("torchao").split(".")[:2]) < (0, 16):
            r = sh([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"]); say("removed old torchao rc", r.returncode)
    except Exception:
        pass
    need = []
    for pkg in ("peft", "anthropic"):
        try:
            metadata.version(pkg)
        except Exception:
            need.append(pkg)
    try:
        tv = tuple(int(x) for x in metadata.version("transformers").split(".")[:2])
    except Exception:
        tv = (0, 0)
    if tv < (4, 51):
        need.append("transformers>=4.51")
    if need and not DRY:
        say("pip install", need)
        r = sh([sys.executable, "-m", "pip", "install", "-q", *need])
        print((r.stdout + r.stderr)[-1500:], flush=True)


def preflight():
    key = find_key()
    gpus = sh(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]).stdout.strip().splitlines() if shutil.which("nvidia-smi") else []
    pip_ensure()
    v = sh([sys.executable, "-c", "import torch,transformers,peft,anthropic;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),"
            "'gpus',torch.cuda.device_count(),'bf16',torch.cuda.is_available() and torch.cuda.is_bf16_supported(),'transformers',transformers.__version__,"
            "'peft',peft.__version__,'anthropic',anthropic.__version__)"])
    say("PREFLIGHT gpus:", gpus or "none", "| key present:", "yes" if key else "NO", "|", (v.stdout.strip() or v.stderr.strip()[-300:]))
    return len(gpus), key


def reserve():
    if CFG.get("plan") == "rlaif2":  # phase 2 = three evals per GPU
        d = TIMES.get("eval_jolt1_step20")
        return max(CFG["min_reserve_s"], 3.3 * d) if d else CFG["unknown_reserve_s"]
    d = TIMES.get("eval_base")
    return max(CFG["min_reserve_s"], 1.5 * d) if d else CFG["unknown_reserve_s"]


def run_step(name, args, gpu, stop_at, outdir):
    """Run train.py (cwd JOB) on one GPU; stdout -> file. Killed (process group) when stop_at() passes. Never raises."""
    log = os.path.join(OUT, "logs", f"{name}.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    script = "stub_train.py" if DRY and os.environ.get("KAGGLE_JOB_REAL") != "1" else "train.py"
    cmd = [sys.executable, "-u", script, *args, "--outdir", outdir]
    if CFG["smoke"] and not os.environ.get("LEARNER_ANTHROPIC_API_KEY") and "--fake-grader" not in cmd:
        cmd += ["--fake-grader"]  # smoke without a key still tests GPU/fp16/plumbing
    if DRY and script == "train.py":
        cmd += ["--fake-grader"] + os.environ.get("KAGGLE_JOB_EXTRA", "").split()
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false",
               PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", HF_HUB_DISABLE_PROGRESS_BARS="1")
    if time.time() >= stop_at():
        STATUS[name] = dict(rc=None, note="SKIPPED_DEADLINE"); write_status(); say(name, "skipped (deadline)"); return None
    t = time.time()
    say(f"START {name} gpu={gpu}:", " ".join(args))
    STATUS[name] = dict(rc="running", gpu=gpu, start_s=round(t - T0)); write_status()
    note = ""
    try:
        with open(log, "ab") as f:
            p = subprocess.Popen(cmd, cwd=JOB, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
            ACTIVE[name] = (p, log, t)
            while p.poll() is None:
                if time.time() >= stop_at():
                    note = "TIMEOUT (killed at its stop time)"
                    os.killpg(p.pid, signal.SIGTERM)
                    try:
                        p.wait(30)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL); p.wait()
                    break
                time.sleep(1 if DRY else 10)
        rc = p.returncode
    except Exception as e:
        rc, note = -999, f"controller error {type(e).__name__}: {e}"
    ACTIVE.pop(name, None)
    TIMES[name] = time.time() - t
    STATUS[name] = dict(rc=rc, note=note, gpu=gpu, dur_s=round(TIMES[name]))
    write_status()
    say(f"END {name} rc={rc} {note} dur={TIMES[name] / 60:.1f}m")
    return rc


def monitor(stop):
    while not stop.wait(CFG["progress_s"]):
        for n, (p, log, t) in list(ACTIVE.items()):
            try:
                tail = open(log, "rb").read()[-600:].decode("utf8", "replace").strip().splitlines()[-1][:300]
            except Exception:
                tail = ""
            say(f"PROGRESS {n} running {(time.time() - t) / 60:.1f}m | {tail}")


def adapters(run):
    """{step: path} of saved, complete adapters for a train run."""
    d, out = os.path.join(WORK, run), {}
    for p in glob.glob(os.path.join(d, "adapter_step*")):
        try:
            s = int(os.path.basename(p)[len("adapter_step"):])
        except ValueError:
            continue
        fs = [os.path.join(p, f) for f in ("adapter_config.json", "adapter_model.safetensors")]
        if all(os.path.exists(f) and os.path.getsize(f) > 0 for f in fs):
            out[s] = p
    return out


def summary_of(outdir):
    fs = sorted(glob.glob(os.path.join(outdir, "eval_*.json")))
    return json.load(open(fs[0])) if fs else None


def spend(d):
    try:
        return json.load(open(os.path.join(d, "spend.json")))["usd"]
    except Exception:
        return 0.0


def collect(names, keep_adapters):
    for r in names:
        for pat in ("log.jsonl", "eval_*.json", "eval_*.jsonl", "spend.json", "spot.jsonl"):
            for f in glob.glob(os.path.join(WORK, r, pat)):
                os.makedirs(os.path.join(OUT, "runs", r), exist_ok=True)
                shutil.copy(f, os.path.join(OUT, "runs", r, os.path.basename(f)))
    for name, src in keep_adapters:
        shutil.copytree(src, os.path.join(OUT, "adapters", name), dirs_exist_ok=True)


def main_rlaif2(ngpu):
    ev = CFG["eval_flags"].split()
    heldout, train = CFG["heldout"], CFG["train"]
    common = ["--train", train, *CFG["common"].split()]
    train_stop = lambda: DEADLINE - reserve()
    hard_stop = lambda: DEADLINE - 120
    g1 = 1 if ngpu >= 2 else 0
    W = lambda n: os.path.join(WORK, n)
    old = sorted(glob.glob("/kaggle/input/**/jolt_step20/adapter_config.json", recursive=True))
    if not old:  # a dataset uploaded with -r tar/zip may arrive still packed
        for arc in glob.glob("/kaggle/input/**/jolt_step20.tar", recursive=True) + glob.glob("/kaggle/input/**/jolt_step20.zip", recursive=True):
            shutil.unpack_archive(arc, os.path.join(JOB, "run1"))
        old = sorted(glob.glob(os.path.join(JOB, "run1", "**", "adapter_config.json"), recursive=True))
    old = os.path.dirname(old[0]) if old else None
    say("run-1 jolt_step20:", old or "NOT FOUND (step 0 skipped)")
    stop = threading.Event()
    threading.Thread(target=monitor, args=(stop,), daemon=True).start()

    def lane0():
        if old:
            run_step("eval_jolt1_step20", ev + ["--adapter", old, "--heldout", heldout], 0, hard_stop, W("eval_jolt1_step20"))
        run_step("train_grpo", ["--algo", "grpo", *common], 0, train_stop, W("grpo"))

    def lane1():  # untrained base first: its strict_success is the pass-mark reference
        run_step("eval_base", ev + ["--heldout", heldout], g1, hard_stop, W("eval_base"))
        run_step("train_jolt", ["--algo", "jolt_plus", *common, *CFG["jolt_extra"].split()], g1, train_stop, W("jolt"))
    ls = [lane0, lane1] if g1 else [lambda: (lane0(), lane1())]
    ts = [threading.Thread(target=l) for l in ls]; [t.start() for t in ts]; [t.join() for t in ts]
    say("PHASE 1 done")
    ag, aj = adapters("grpo"), adapters("jolt")
    say("grpo steps", sorted(ag), "jolt steps", sorted(aj))

    def evals(arm, ad, gpu):
        for s in (10, 20, 30):
            if s in ad:
                run_step(f"eval_{arm}_step{s}", ev + ["--adapter", ad[s], "--heldout", heldout], gpu, hard_stop, W(f"eval_{arm}_step{s}"))
    eg, ej = (lambda: evals("grpo", ag, 0)), (lambda: evals("jolt", aj, g1))
    es = [eg, ej] if g1 else [lambda: (eg(), ej())]
    ts = [threading.Thread(target=f) for f in es]; [t.start() for t in ts]; [t.join() for t in ts]
    stop.set()
    runs = [r for r in (os.listdir(WORK) if os.path.isdir(WORK) else [])]
    summ = dict(plan="rlaif2", evals={r: summary_of(W(r)) for r in sorted(runs) if r.startswith("eval_")},
                steps_saved=dict(grpo=sorted(ag), jolt=sorted(aj)), timings_s={n: round(v) for n, v in TIMES.items()},
                total_s=round(time.time() - T0), status=STATUS, grader_usd={r: round(spend(W(r)), 4) for r in sorted(runs)})
    summ["grader_usd_total"] = round(sum(summ["grader_usd"].values()), 4)
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    keep = [(f"{n}_step{max(d)}", d[max(d)]) for n, d in (("grpo", ag), ("jolt", aj)) if d]
    collect(runs, keep)
    shutil.rmtree(JOB, ignore_errors=True)
    say("SUMMARY", json.dumps({r: (v or {}).get("success_rate") for r, v in summ["evals"].items()}), "usd", summ["grader_usd_total"])


def main():
    os.makedirs(OUT, exist_ok=True)
    unpack()
    ngpu, key = preflight()
    if DRY:
        ngpu = 2
    if not key and not CFG["smoke"] and not DRY:
        say("ABORT: no LEARNER_ANTHROPIC_API_KEY (attach the Kaggle Secret to this notebook)"); return
    if CFG.get("plan") == "rlaif2":
        return main_rlaif2(ngpu)
    ev = CFG["eval_flags"].split()
    heldout, train = CFG["heldout"], CFG["train"]
    train_args = lambda algo: ["--algo", algo, "--train", train, *CFG["common"].split()]
    train_stop = lambda: DEADLINE - reserve()
    hard_stop = lambda: DEADLINE - 120
    g1 = 1 if ngpu >= 2 else 0
    stop = threading.Event()
    threading.Thread(target=monitor, args=(stop,), daemon=True).start()
    W = lambda n: os.path.join(WORK, n)

    def lane0():
        run_step("eval_base", ev + ["--heldout", heldout], 0, hard_stop, W("eval_base"))
        run_step("train_grpo", train_args("grpo"), 0, train_stop, W("grpo"))

    def lane1():
        run_step("train_jolt", train_args("jolt_plus"), g1, train_stop, W("jolt"))
    lanes = [lane0, lane1]
    if g1 == 0:
        say("WARNING: only one GPU; lanes run one after the other")
        both = lambda: [l() for l in lanes]
        lanes = [both]
    ts = [threading.Thread(target=l) for l in lanes]
    [t.start() for t in ts]; [t.join() for t in ts]
    say("PHASE 1 done")
    ag, aj = adapters("grpo"), adapters("jolt")
    both_steps = sorted(set(ag) & set(aj))
    k = both_steps[-1] if both_steps else None
    say("grpo steps", sorted(ag), "jolt steps", sorted(aj), "-> k =", k)
    STATUS["k"] = k; write_status()
    if k is not None:
        e0 = lambda: run_step("eval_grpo", ev + ["--adapter", ag[k], "--heldout", heldout], 0, hard_stop, W("eval_grpo"))
        e1 = lambda: run_step("eval_jolt", ev + ["--adapter", aj[k], "--heldout", heldout], g1, hard_stop, W("eval_jolt"))
        es = [e0, e1] if g1 else [lambda: (e0(), e1())]
        ts = [threading.Thread(target=f) for f in es]
        [t.start() for t in ts]; [t.join() for t in ts]
    stop.set()
    summ = dict(k=k, base=summary_of(W("eval_base")), grpo=summary_of(W("eval_grpo")) if k else None,
                jolt=summary_of(W("eval_jolt")) if k else None, steps_saved=dict(grpo=sorted(ag), jolt=sorted(aj)),
                timings_s={n: round(v) for n, v in TIMES.items()}, total_s=round(time.time() - T0), status=STATUS,
                grader_usd={r: round(spend(W(r)), 4) for r in ("eval_base", "grpo", "jolt", "eval_grpo", "eval_jolt")},
                smoke=CFG["smoke"], dry=DRY)
    summ["grader_usd_total"] = round(sum(summ["grader_usd"].values()), 4)
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    # small outputs only: result files, log tails, the two compared adapters
    for r in os.listdir(WORK) if os.path.isdir(WORK) else []:
        for pat in ("log.jsonl", "eval_*.json", "eval_*.jsonl", "spend.json", "spot.jsonl"):
            for f in glob.glob(os.path.join(WORK, r, pat)):
                os.makedirs(os.path.join(OUT, "runs", r), exist_ok=True)
                shutil.copy(f, os.path.join(OUT, "runs", r, os.path.basename(f)))
    if k is not None:
        for name, src in (("grpo", ag[k]), ("jolt", aj[k])):
            shutil.copytree(src, os.path.join(OUT, "adapters", f"{name}_step{k}"), dirs_exist_ok=True)
    shutil.rmtree(JOB, ignore_errors=True)
    say("SUMMARY", json.dumps({x: summ[x] for x in ("k", "base", "grpo", "jolt", "grader_usd_total")}))
    say("out size MB:", round(sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs) / 1e6, 1))


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        say("JOB ERROR", type(e).__name__, e)
        STATUS["job_error"] = f"{type(e).__name__}: {e}"
        write_status()
    sys.exit(0)
'''


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, run=True, **kw):
        s = sub.add_parser(name, **kw)
        s.set_defaults(fn=fn)
        s.add_argument("--user", help="Kaggle username (default: env/config)")
        if run:
            s.add_argument("--run", default="main")
        return s
    add("secret", secret, run=False, help="create/version the private key dataset")
    s = add("build", build, help="write the kernel dir")
    s.add_argument("--no-key-dataset", action="store_true", help="don't mount the key dataset (key via Kaggle Secret, or fake grader in smoke)")
    s.add_argument("--smoke", action="store_true", help="tiny pipeline test (2 steps, n-eval 4, 40 min deadline)")
    s.add_argument("--plan", default="rlaif1", choices=("rlaif1", "rlaif2"), help="rlaif2 = SPEC.md RLAIF-2 (needs --kernel-source rlaif-main for run-1 jolt_step20)")
    s.add_argument("--dataset-source", action="append", help="another private dataset of this user to mount")
    s.add_argument("--kernel-source", action="append", help="another kernel of this user whose output is mounted under /kaggle/input")
    s.add_argument("--deadline-h", type=float, help="override the job deadline in hours (default 11)")
    add("push", push)
    add("status", status)
    add("pull", pull)
    s = add("log", log)
    s.add_argument("--lines", type=int, default=80)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
