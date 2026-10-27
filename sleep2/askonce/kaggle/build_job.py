"""Build the Kaggle kernel directory for job 1 or job 2 (one-cell NOTEBOOK kernel; payload = code + frozen data, base64 xz inside the cell).
  python -m sleep2.askonce.kaggle.build_job --job 1 --out /tmp/kern1
  python -m sleep2.askonce.kaggle.build_job --job 2 --out /tmp/kern2 --nightdata /path/nightdata [--pilot] [--scale 1.0]
Nothing is pushed. To launch: `kaggle kernels push -p DIR --accelerator NvidiaTeslaT4` (job 2 wants T4 x2; set it in the Kaggle UI/CLI)."""
import argparse
import base64
import io
import json
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASKONCE = HERE.parent
REPO_SLEEP2 = ASKONCE.parent
OWNER = "thegreatergood"
FROZEN = ["persona.json", "persona.sha256", "requests.jsonl", "requests.sha256", "phrasings.json", "phrasings.sha256", "arc_easy_500.json"]
LIMIT_KB = 800

BOX = r'''
import base64, io, json, os, signal, subprocess, sys, tarfile, threading, time
T0 = time.time(); CFG = json.loads(CFG_JSON)
OUT = "/kaggle/working/out"; REPO = "/tmp/repo"; os.makedirs(OUT + "/logs", exist_ok=True)
def say(*a): print(time.strftime("[%H:%M:%S"), f"+{(time.time()-T0)/60:6.1f}m]", *a, flush=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)), mode="r:xz") as t:
    try:
        t.extractall(REPO, filter="data")
    except TypeError:       # Python without extraction filters
        t.extractall(REPO)
env = dict(os.environ, OUT=OUT, PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false", PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True",
           HF_HUB_DISABLE_PROGRESS_BARS="1", PYTHONPATH=REPO, OMP_NUM_THREADS="2", MKL_NUM_THREADS="2", **CFG["env"])
for k in ("LEARNER_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"):   # no secrets in GPU jobs
    env.pop(k, None)
def sh(cmd, tail=1500):
    r = subprocess.run(cmd, shell=True, cwd=REPO, env=env, capture_output=True, text=True)
    say("RUN", cmd[:120], "rc", r.returncode, (r.stdout + r.stderr)[-tail:].replace("\n", " | ")); return r
sh("pip uninstall -y -q torchao")            # Kaggle's torchao breaks peft LoRA layers
r = sh("pip install -q 'transformers==5.20.2' 'peft==0.21.2' accelerate")   # K2's remote code needs transformers 5.x; versions pinned (checked locally)
if r.returncode != 0:
    raise SystemExit("pip install of the pinned transformers/peft failed; stopping before any GPU time is spent")
sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
DEADLINE = T0 + CFG["deadline_s"]; STATUS = {}
def lane(i, cmd):
    log = open(f"{OUT}/logs/lane{i}.log", "w"); t = time.time(); say(f"START lane{i}:", cmd)
    p = subprocess.Popen(cmd, shell=True, cwd=REPO, env=dict(env, CUDA_VISIBLE_DEVICES=str(i)), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    note = ""
    while p.poll() is None:
        if time.time() > DEADLINE:
            note = "KILLED_DEADLINE"; os.killpg(p.pid, signal.SIGTERM); time.sleep(60)
            if p.poll() is None: os.killpg(p.pid, signal.SIGKILL)
            break
        time.sleep(10)
    p.wait(); STATUS[f"lane{i}"] = dict(cmd=cmd, rc=p.returncode, note=note, min=round((time.time() - t) / 60, 1)); say(f"END lane{i} rc={p.returncode} {note}")
ths = [threading.Thread(target=lane, args=(i, c)) for i, c in enumerate(CFG["lanes"]) if c]
[t.start() for t in ths]
last = 0
while any(t.is_alive() for t in ths):
    time.sleep(10)
    if time.time() - last > 300:
        last = time.time()
        for i in range(len(CFG["lanes"])):
            try: say(f"lane{i} tail:", open(f"{OUT}/logs/lane{i}.log").read()[-300:].replace("\n", " | "))
            except Exception: pass
[t.join() for t in ths]
STATUS["expected_files"] = {f: os.path.exists(os.path.join(OUT, f)) for f in CFG["expect"]}   # judge by output files, not return codes
json.dump(dict(STATUS, total_min=round((time.time() - T0) / 60, 1)), open(f"{OUT}/status.json", "w"), indent=1)
say("DONE", json.dumps(STATUS))
'''


def add(tar, src, arc):
    tar.add(src, arcname=arc, filter=lambda ti: None if "__pycache__" in ti.name else ti)


def payload(job, nightdata=None, pilot=False):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz", preset=9) as t:
        add(t, REPO_SLEEP2 / "__init__.py", "sleep2/__init__.py")
        add(t, REPO_SLEEP2 / "common" / "__init__.py", "sleep2/common/__init__.py")
        add(t, REPO_SLEEP2 / "common" / "paired.py", "sleep2/common/paired.py")
        add(t, ASKONCE / "__init__.py", "sleep2/askonce/__init__.py")
        skip = set()
        for p in sorted(ASKONCE.glob("*.py")):
            if p.name not in skip:
                add(t, p, f"sleep2/askonce/{p.name}")
        for f in FROZEN:
            add(t, ASKONCE / "data" / f, f"sleep2/askonce/data/{f}")
        if job == 2:
            nd = Path(nightdata)
            for p in sorted(nd.rglob("*")):
                if p.is_file() and p.name not in ("stats.json",):
                    add(t, p, f"sleep2/askonce/data/nightdata/{p.relative_to(nd)}")
            # eval sets live next to the night files; phrasings/arc are read from there too
            for f in ("phrasings.json", "arc_easy_500.json"):
                add(t, ASKONCE / "data" / f, f"sleep2/askonce/data/nightdata/{f}")
    return buf.getvalue()


DEADLINE_H = {1: 1.2, 2: 2.5}   # hard cap per lane (6.0 GPU-h in total is the budget; the expected use is about 3 GPU-h)


def build(job, out, nightdata=None, pilot=False, scale=1.0, deadline_h=None, owner=None, slug=None):
    deadline_h = deadline_h or DEADLINE_H[job]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    data = base64.b64encode(payload(job, nightdata, pilot)).decode()
    # night scale and optimizer steps are NOT set here: they are fixed when build_night_data runs in the container (plan.json carries n_opt_steps)
    env = {"ASKONCE_SCALE": str(scale)}
    nd = "/tmp/repo/sleep2/askonce/data/nightdata"
    if job == 1:
        lanes = ["python -m sleep2.askonce.job1 --out $OUT/job1", ""]
        expect = ["job1/diary/day5.jsonl", "job1/oracle/day5.jsonl", "job1/results/P_1.json", "job1/timing.json"]
    else:
        extra = " --pilot" if pilot else ""
        lanes = [f"python -m sleep2.askonce.job2 --seed {s} --nightdata {nd} --out $OUT/job2{extra} --deadline-s {int(deadline_h * 3600 * 0.95)}" for s in (1, 2)]
        if pilot:
            lanes[1] = ""
            expect = ["job2/pilot_seed1.json"]
        else:
            expect = [f"job2/results/{a}_{s}.json" for s in (1, 2) for a in ("A+", "B", "B-sft")]
    cfg = {"lanes": lanes, "env": env, "deadline_s": int(deadline_h * 3600), "expect": expect}
    src = f"CFG_JSON = {json.dumps(json.dumps(cfg))}\nPAYLOAD = {data!r}\n" + BOX
    slug = slug or f"askonce-job{job}"
    nb_name = f"{slug}.ipynb"
    nb = {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
          "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}]}
    (out / nb_name).write_text(json.dumps(nb))
    meta = {"id": f"{owner or OWNER}/{slug}", "title": slug, "code_file": nb_name, "language": "python", "kernel_type": "notebook",
            "is_private": "true", "enable_gpu": "true", "enable_internet": "true", "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    kb = len(data) * 3 // 4 // 1024
    if kb > LIMIT_KB:
        print(f"WARNING: payload {kb} KB exceeds the ~{LIMIT_KB} KB target", file=sys.stderr)
    return {"dir": str(out), "id": meta["id"], "payload_kb": kb, "notebook_kb": (out / nb_name).stat().st_size // 1024, "lanes": lanes, "expect": expect}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", type=int, choices=[1, 2], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nightdata")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--owner", help="Kaggle account for kernel-metadata id (default thegreatergood)")
    ap.add_argument("--slug", help="kernel slug, e.g. askonce-v2-job2 (default askonce-job<N>)")
    a = ap.parse_args()
    if a.job == 2 and not a.nightdata:
        ap.error("--nightdata is required for job 2")
    print(json.dumps(build(a.job, a.out, a.nightdata, a.pilot, a.scale, owner=a.owner, slug=a.slug), indent=1))
