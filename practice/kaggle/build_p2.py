"""Build the Kaggle kernel directory for a Practice-2 skill (PREREG-2 + addenda 1-4) on T4 x2: lane 0 = arm P (with A0 and the P evals), lane 1 = arm C (waits for
P's night counts), both through the OpenCode harness (vLLM fp16 eager in its own venv + practice/k2_proxy), NF4 QLoRA nights. Every try and phase is resumable:
a run that does not finish in one session (lanes are killed at --box-h, before Kaggle's 12 h cut, which saves no output) is continued by a second kernel
built with --resume-from <first slug>, which copies the first run's output in and carries on.
  python -m practice.kaggle.build_p2 --out /tmp/kern --skill zebra_puzzles [--slug practice2-zebra] [--resume-from practice2-zebra]
Nothing is pushed. To launch: `KAGGLE_API_TOKEN=... kaggle kernels push -p DIR --accelerator NvidiaTeslaT4` (T4 x2)."""
import argparse
import base64
import io
import json
import sys
import tarfile
from pathlib import Path

from practice.kaggle.build_job import ASK_FILES, ASKONCE, KERNEL_BOX, OWNER, PRACTICE, SLEEP2, TEST_KEEP, add, add_bytes
from sleep2.askonce.kaggle.build_job import LIMIT_KB

SKIP = {"mac_run.py", "mlx_server.py", "mlx_train.py", "k2_horizon_mlx.py", "analyze_mac.py", "smoke.py"}  # Mac-only
DATA_FILES = ["practice_pool.jsonl", "sonnet_pool.jsonl", "sibling60.jsonl", "library_wiki.json"]
BOX_H = 11.0

# Runs after the pinned transformers/peft install and the vLLM venv step of the Practice-1 box: Practice-2 deps, Node + OpenCode, the resume copy, a warm try.
P2_STEP = r'''
r = sh("pip install -q 'reasoning-gym==0.1.25' bitsandbytes", tail=600)
if r.returncode != 0:
    raise SystemExit("pip install of reasoning-gym / bitsandbytes failed")
NODE = "/tmp/node22"; NPM = "/tmp/p2npm"
sh("mkdir -p " + NODE + " && curl -fsSL https://nodejs.org/dist/v22.11.0/node-v22.11.0-linux-x64.tar.gz | tar xz -C " + NODE + " --strip-components=1", tail=400)
env["PATH"] = NPM + "/bin:" + NODE + "/bin:" + env.get("PATH", "")
sh("npm install -g --prefix " + NPM + " opencode-ai@1.19.4", tail=400)
r = sh("node --version && opencode --version", tail=200)
if r.returncode != 0 or "VLLM_PY" not in env:
    raise SystemExit("OpenCode or vLLM is not available; the OpenCode harness cannot run")
if CFG.get("resume"):
    hits = subprocess.run("find /kaggle/input -name 'rg_config_P.json' -path '*practice2*'", shell=True, capture_output=True, text=True).stdout.split()
    say("resume: found", hits)
    if not hits:
        raise SystemExit("--resume-from: no earlier practice2 output under /kaggle/input")
    src = os.path.dirname(hits[0])
    sh("mkdir -p " + OUT + "/practice2 && cp -a " + src + "/. " + OUT + "/practice2/ && find " + OUT + "/practice2 -maxdepth 3 -name results", tail=600)
r = sh("python -m practice.oc_cuda --warm", tail=800)
if r.returncode != 0:
    raise SystemExit("OpenCode warm try failed")
'''
CLEANUP = r'''
sh("find " + OUT + " -type d -name proxy_logs -prune -exec rm -rf {} +", tail=200)   # per-call proxy logs (big, many files); every try keeps its own segs
sh("python -m practice.analyze_rg " + OUT + "/practice2 --night " + str(CFG["nights"]) + " > " + OUT + "/verdicts.json", tail=600)
'''
P2_BOX = KERNEL_BOX.replace('sh("nvidia-smi', P2_STEP + 'sh("nvidia-smi', 1)
P2_BOX = P2_BOX.replace('STATUS["expected_files"]', CLEANUP + 'STATUS["expected_files"]', 1)
assert P2_STEP in P2_BOX and CLEANUP in P2_BOX


def payload():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz", preset=9) as t:
        add(t, SLEEP2 / "__init__.py", "sleep2/__init__.py")
        for f in ASK_FILES:
            add(t, ASKONCE / f, f"sleep2/askonce/{f}")
        add(t, ASKONCE / "data" / "arc_easy_500.json", "sleep2/askonce/data/arc_easy_500.json")
        for p in sorted(PRACTICE.glob("*.py")):
            if p.name not in SKIP:
                add(t, p, f"practice/{p.name}")
        add(t, PRACTICE / "k2_nothink.jinja", "practice/k2_nothink.jinja")
        for f in ("__init__.py", "k2_fake_upstream.py"):  # practice.oc_cuda --warm runs one try against this fake model server
            add(t, PRACTICE.parent / "tests" / f, f"tests/{f}")
        for f in DATA_FILES:
            if (PRACTICE / "data" / f).exists():
                add(t, PRACTICE / "data" / f, f"practice/data/{f}")
        rows = [json.loads(l) for l in open(PRACTICE / "data" / "test100.jsonl") if l.strip()]
        txt = "".join(json.dumps({k: r[k] for k in TEST_KEEP if k in r}, ensure_ascii=False) + "\n" for r in rows)
        add_bytes(t, txt.encode(), "practice/data/test100.jsonl")
    return buf.getvalue()


def lane_cmd(arm, port, a):
    return (f"python -m practice.job --rg-skills {a.skill} --rg-arm {arm} --out $OUT/practice2 --backend auto --harness opencode --nf4 --oc-eager "
            f"--oc-port {port} --oc-concurrency {a.conc} --oc-util {a.util} --oc-max-len 12288 --oc-max-seqs {a.conc * 2} --oc-train-tokens {a.train_tokens} "
            f"--rg-day-n {a.day_n} --tries 4 --rg-test-n 300 --test-tries 2 --nights {a.nights} --eval-nights 1,{a.nights}")


def build(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = base64.b64encode(payload()).decode()
    slug = a.slug or f"practice2-{a.skill.split('_')[0]}" + ("-b" if a.resume_from else "")
    lanes = [lane_cmd("P", 18081, a), lane_cmd("C", 18082, a)]
    sd = f"practice2/{a.skill}"
    expect = [f"{sd}/P/results/A0.json", f"{sd}/P/results/P1.json", f"{sd}/P/results/P{a.nights}.json", f"{sd}/C/results/C{a.nights}.json"]
    cfg = {"lanes": lanes, "env": {}, "deadline_s": int(a.box_h * 3600), "expect": expect, "vllm": True, "resume": bool(a.resume_from), "nights": a.nights}
    src = f"CFG_JSON = {json.dumps(json.dumps(cfg))}\nPAYLOAD = {data!r}\n" + P2_BOX
    nb_name = f"{slug}.ipynb"
    nb = {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
          "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}]}
    (out / nb_name).write_text(json.dumps(nb))
    meta = {"id": f"{OWNER}/{slug}", "title": slug, "code_file": nb_name, "language": "python", "kernel_type": "notebook", "is_private": "true",
            "enable_gpu": "true", "enable_internet": "true", "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [f"{OWNER}/{a.resume_from}"] if a.resume_from else []}
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    kb = len(data) * 3 // 4 // 1024
    if kb > LIMIT_KB:
        print(f"WARNING: payload {kb} KB exceeds the ~{LIMIT_KB} KB target", file=sys.stderr)
    return {"dir": str(out), "id": meta["id"], "payload_kb": kb, "notebook_kb": (out / nb_name).stat().st_size // 1024, "lanes": lanes, "expect": expect,
            "kernel_sources": meta["kernel_sources"]}


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--skill", default="zebra_puzzles")
    ap.add_argument("--slug")
    ap.add_argument("--resume-from", help="slug of the earlier kernel of this run (its output is attached as input and copied in)")
    ap.add_argument("--box-h", type=float, default=BOX_H)
    ap.add_argument("--conc", type=int, default=12, help="OpenCode tries at once per lane (4 vCPUs on the box)")
    ap.add_argument("--util", type=float, default=0.88)
    ap.add_argument("--train-tokens", type=int, default=6144)
    ap.add_argument("--day-n", type=int, default=500)
    ap.add_argument("--nights", type=int, default=3)
    return ap


if __name__ == "__main__":
    print(json.dumps(build(build_parser().parse_args()), indent=1))
