#!/usr/bin/env python3
"""Run any keyless repo job on a free Kaggle 2x T4 notebook (one command per GPU), from the cloud container.

  build  --name N --account {1,2,3} --include PATH [PATH ...] --lane0 CMD [--lane1 CMD] [--setup CMD] [--data DIR] [--deadline-h 11]
  push   --name N          start it (keyless jobs need no click; Kaggle Secrets are NOT available to API-started runs)
  status --name N
  pull   --name N          -> runs/kaggle/<name>/ (job log + /kaggle/working/out)

Tokens: account 1 = ~/.kaggle/access_token, account k = ~/.kaggle/token<k> (KGAT_ tokens).
On the box: repo files are unpacked to /tmp/repo (cwd of every command, not saved), $OUT=/kaggle/working/out is saved,
$DATA is the mounted --data dir (a private Kaggle dataset). Each lane runs on its own T4 (CUDA_VISIBLE_DEVICES) and is
killed at the deadline (Kaggle discards ALL output at 12h). T4 has no bf16: commands should use fp16/fp32.
"""
import argparse, base64, io, json, os, subprocess, sys, tarfile, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "runs" / "kaggle"
ACCEL = "NvidiaTeslaT4"

BOX = r'''
import base64, glob, io, json, os, signal, subprocess, sys, tarfile, threading, time
T0 = time.time(); CFG = json.loads(CFG_JSON)
OUT = "/kaggle/working/out"; REPO = "/tmp/repo"; os.makedirs(OUT + "/logs", exist_ok=True)
def say(*a): print(time.strftime("[%H:%M:%S"), f"+{(time.time()-T0)/60:6.1f}m]", *a, flush=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)), mode="r:xz") as t:
    t.extractall(REPO, filter="data")
data = sorted(glob.glob(f"/kaggle/input/*{CFG['name']}-data*")) or sorted(glob.glob(f"/kaggle/input/**/{CFG['name']}-data*", recursive=True))
env = dict(os.environ, OUT=OUT, DATA=data[0] if data else "", PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false",
           PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True", HF_HUB_DISABLE_PROGRESS_BARS="1", PYTHONPATH=REPO)
try:  # Kaggle ships torchao 0.10, which makes peft refuse to build LoRA layers
    from importlib import metadata
    if tuple(int(x) for x in metadata.version("torchao").split(".")[:2]) < (0, 16):
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"])
except Exception:
    pass
say("GPUs:", subprocess.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", shell=True, capture_output=True, text=True).stdout.strip().splitlines(), "| DATA:", env["DATA"] or "none")
if CFG.get("setup"):
    r = subprocess.run(CFG["setup"], shell=True, cwd=REPO, env=env, capture_output=True, text=True)
    say("setup rc", r.returncode, (r.stdout + r.stderr)[-1500:])
DEADLINE = T0 + CFG["deadline_s"]; STATUS = {}
def lane(i, cmd):
    log = open(f"{OUT}/logs/lane{i}.log", "w"); t = time.time()
    say(f"START lane{i}:", cmd)
    p = subprocess.Popen(cmd, shell=True, cwd=REPO, env=dict(env, CUDA_VISIBLE_DEVICES=str(i)), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    note = ""
    while p.poll() is None:
        if time.time() > DEADLINE:
            note = "KILLED_DEADLINE"; os.killpg(p.pid, signal.SIGTERM); time.sleep(60)
            if p.poll() is None: os.killpg(p.pid, signal.SIGKILL)
            break
        time.sleep(10)
    p.wait(); STATUS[f"lane{i}"] = dict(cmd=cmd, rc=p.returncode, note=note, min=round((time.time() - t) / 60, 1))
    say(f"END lane{i} rc={p.returncode} {note}")
ths = [threading.Thread(target=lane, args=(i, c)) for i, c in enumerate(CFG["lanes"]) if c]
[t.start() for t in ths]
while any(t.is_alive() for t in ths):
    time.sleep(600)
    for i in range(len(CFG["lanes"])):
        try: say(f"lane{i} tail:", open(f"{OUT}/logs/lane{i}.log").read()[-300:].replace("\n", " | "))
        except Exception: pass
[t.join() for t in ths]
json.dump(dict(STATUS, total_min=round((time.time() - T0) / 60, 1)), open(f"{OUT}/status.json", "w"), indent=1)
say("DONE", json.dumps(STATUS)); say("out MB", round(sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs) / 1e6, 1))
'''


def token(acct):
    p = Path.home() / ".kaggle" / ("access_token" if acct == 1 else f"token{acct}")
    return p.read_text().strip()


def kg(acct, *args, check=True):
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True, env=dict(os.environ, KAGGLE_API_TOKEN=token(acct)))
    if check and r.returncode:
        sys.exit((r.stdout + r.stderr)[-2000:])
    return r


def user(acct):
    out = kg(acct, "config", "view").stdout
    return next(l.split(":", 1)[1].strip() for l in out.splitlines() if "username" in l)


def kdir(name):
    return STATE / name / "kernel"


def build(a):
    acct, u = a.account, user(a.account)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for p in a.include:
            t.add(Path(a.root or ROOT) / p, arcname=p, filter=lambda ti: None if "__pycache__" in ti.name or ti.name.endswith((".pt", ".safetensors")) else ti)
    cfg = dict(name=a.name, lanes=[a.lane0, a.lane1], setup=a.setup, deadline_s=int(a.deadline_h * 3600))
    src = f"CFG_JSON = {json.dumps(json.dumps(cfg))}\nPAYLOAD = {base64.b64encode(buf.getvalue()).decode()!r}\n" + BOX
    d = kdir(a.name); d.mkdir(parents=True, exist_ok=True)
    nb = {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
          "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}]}
    (d / "job.ipynb").write_text(json.dumps(nb))
    sources = []
    if a.data:
        slug = f"{a.name}-data"
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["cp", "-r", f"{a.data.rstrip('/')}/.", td], check=True)
            json.dump({"title": slug, "id": f"{u}/{slug}", "licenses": [{"name": "CC0-1.0"}]}, open(f"{td}/dataset-metadata.json", "w"))
            r = kg(acct, "datasets", "create", "-p", td, "-r", "zip", check=False)
            if r.returncode or "already" in (r.stdout + r.stderr).lower():
                kg(acct, "datasets", "version", "-p", td, "-m", "update", "-r", "zip")
        sources = [f"{u}/{slug}"]
    meta = {"id": f"{u}/{a.name}", "title": a.name, "code_file": "job.ipynb", "language": "python", "kernel_type": "notebook",
            "is_private": "true", "enable_gpu": "true", "enable_internet": "true", "dataset_sources": sources,
            "competition_sources": [], "kernel_sources": []}
    json.dump(meta, open(d / "kernel-metadata.json", "w"), indent=1)
    json.dump({"account": acct, "id": meta["id"]}, open(STATE / a.name / "job.json", "w"))
    print(json.dumps({"id": meta["id"], "account": acct, "payload_kb": len(buf.getvalue()) // 1024, "data": sources}))


def job(name):
    return json.load(open(STATE / name / "job.json"))


def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build"); b.add_argument("--name", required=True); b.add_argument("--account", type=int, default=2)
    b.add_argument("--include", nargs="+", required=True); b.add_argument("--lane0", required=True); b.add_argument("--lane1", default="")
    b.add_argument("--setup", default=""); b.add_argument("--root", help="dir the --include paths are relative to (default: repo root)"); b.add_argument("--data"); b.add_argument("--deadline-h", type=float, default=11.0)
    for c in ("push", "status", "pull"):
        sp.add_parser(c).add_argument("--name", required=True)
    a = ap.parse_args()
    if a.cmd == "build":
        return build(a)
    j = job(a.name)
    if a.cmd == "push":
        print(kg(j["account"], "kernels", "push", "-p", str(kdir(a.name)), "--accelerator", ACCEL).stdout.strip())
    elif a.cmd == "status":
        print(kg(j["account"], "kernels", "status", j["id"], check=False).stdout.strip())
    elif a.cmd == "pull":
        d = STATE / a.name / "output"; d.mkdir(parents=True, exist_ok=True)
        print(kg(j["account"], "kernels", "output", j["id"], "-p", str(d), check=False).stdout[-500:])


if __name__ == "__main__":
    main()
