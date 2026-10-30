"""Build the Kaggle kernel directory for Practice-1 (one-cell NOTEBOOK kernel; payload = practice/ code + data + needed sleep2 modules, base64 xz).
  python -m practice.kaggle.build_job --out /tmp/kern [--pilot] [--practice-n N] [--lane-h 10] [--slug NAME] [--no-vllm]
Two lanes (GPU0 = arm P, GPU1 = arm C). Nothing is pushed. To launch: `kaggle kernels push -p DIR --accelerator NvidiaTeslaT4` (T4 x2)."""
import argparse
import base64
import io
import json
import sys
import tarfile
from pathlib import Path

from sleep2.askonce.kaggle.build_job import BOX, LIMIT_KB

HERE = Path(__file__).resolve().parent
PRACTICE = HERE.parent
REPO = PRACTICE.parent
SLEEP2 = REPO / "sleep2"
ASKONCE = SLEEP2 / "askonce"
OWNER = "benhannanjfkldsfds"
DATA_FILES = ["practice_pool.jsonl", "sonnet_pool.jsonl", "sibling60.jsonl", "library_wiki.json"]
TEST_KEEP = ("id", "kind", "prompt", "answer", "answer_type", "difficulty")
ASK_FILES = ["__init__.py", "config.py", "model_io.py", "train_core.py", "compute_ledger.py", "eval_moves.py", "job_common.py", "tools_mock.py", "world.py"]
CODE = ["__init__.py", "gen.py", "grade.py", "harness.py", "job.py", "lessons.py", "library.py", "night.py", "tools.py", "web.py"]
PILOT_LANE_S = 3000  # pilot lane deadline: 50 min
PILOT_BOX_H = 1.25   # box cap for the pilot: vLLM install (<= 25 min) + the 50 min lane
LANE_H = 10.0       # the lane's own deadline (hours)
BOX_H = 11.0        # hard kill by the box (the prereg's 11 h cut)


# Optional vLLM, in its OWN venv so the pinned transformers/peft of the HF training path stay untouched. If anything here fails, VLLM_PY stays unset and the
# lanes use HF generate (the lane logs which backend it uses). Versions of both environments are logged.
VLLM_STEP = r'''
if CFG.get("vllm"):
    VENV = "/tmp/vllm_env"; VPY = VENV + "/bin/python"
    r = sh("pip install -q uv && uv venv " + VENV + " && timeout 1500 uv pip install -q --python " + VPY + " vllm", tail=600)
    if r.returncode != 0:
        r = sh("python -m venv " + VENV + " && timeout 1500 " + VPY + " -m pip install -q vllm", tail=600)
    if r.returncode == 0:
        chk = sh(VPY + " -c \"import vllm, torch, transformers; print('vllm', vllm.__version__, 'torch', torch.__version__, 'transformers', transformers.__version__); "
                 "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('IFM/K2-Horizon-3.7B', trust_remote_code=True); print('K2 tokenizer ok')\"", tail=800)
        if chk.returncode == 0:
            env["VLLM_PY"] = VPY
    say("vLLM setup:", "enabled (" + env.get("VLLM_PY", "") + ")" if "VLLM_PY" in env else "NOT available; lanes will use HF generate")
sh("python -c \"import torch, transformers, peft; print('main env: torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__); "
   "from transformers import AutoConfig; AutoConfig.from_pretrained('IFM/K2-Horizon-3.7B', trust_remote_code=True); print('K2 remote code ok')\"", tail=800)
'''
KERNEL_BOX = BOX.replace('sh("nvidia-smi', VLLM_STEP + 'sh("nvidia-smi', 1)
assert VLLM_STEP in KERNEL_BOX


def add(tar, src, arc):
    tar.add(src, arcname=arc, filter=lambda ti: None if "__pycache__" in ti.name else ti)


def add_bytes(tar, data, arc):
    ti = tarfile.TarInfo(arc)
    ti.size = len(data)
    tar.addfile(ti, io.BytesIO(data))


def payload():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz", preset=9) as t:
        add(t, SLEEP2 / "__init__.py", "sleep2/__init__.py")
        for f in ASK_FILES:
            add(t, ASKONCE / f, f"sleep2/askonce/{f}")
        add(t, ASKONCE / "data" / "arc_easy_500.json", "sleep2/askonce/data/arc_easy_500.json")
        for f in CODE:
            add(t, PRACTICE / f, f"practice/{f}")
        for f in DATA_FILES:
            if (PRACTICE / "data" / f).exists():
                add(t, PRACTICE / "data" / f, f"practice/data/{f}")
        # sealed test: only the fields the job needs (no reference solvers)
        rows = [json.loads(l) for l in open(PRACTICE / "data" / "test100.jsonl") if l.strip()]
        txt = "".join(json.dumps({k: r[k] for k in TEST_KEEP if k in r}, ensure_ascii=False) + "\n" for r in rows)
        add_bytes(t, txt.encode(), "practice/data/test100.jsonl")
    return buf.getvalue()


def build(out, pilot=False, practice_n=None, lane_h=LANE_H, slug=None, vllm=True, nights=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    data = base64.b64encode(payload()).decode()
    slug = slug or ("practice1-pilot" if pilot else "practice1")
    n = f" --practice-n {practice_n}" if practice_n else ""
    backend = " --backend auto" if vllm else " --backend hf"
    if nights:
        backend += f" --nights {nights} --eval-nights {nights}"
    extra = f" --pilot --deadline-s {PILOT_LANE_S}{n}{backend}" if pilot else f" --deadline-s {int(lane_h * 3600)}{n}{backend}"
    lanes = [f"python -m practice.job --arm {arm} --lane {i} --out $OUT/practice1{extra}" for i, arm in enumerate(("P", "C"))]
    expect = [f"practice1/{a}/pilot.json" for a in ("P", "C")] if pilot else \
        [f"practice1/{a}/results/{a}{k}.json" for a in ("P", "C") for k in ((nights,) if nights else (1, 3))] + [f"practice1/{a}/results/A0.json" for a in ("P", "C")] + [f"practice1/{a}/timing.json" for a in ("P", "C")]
    deadline_h = PILOT_BOX_H if pilot else (min(BOX_H, lane_h + 0.75) if nights else BOX_H)
    cfg = {"lanes": lanes, "env": {}, "deadline_s": int(deadline_h * 3600), "expect": expect, "vllm": bool(vllm)}
    src = f"CFG_JSON = {json.dumps(json.dumps(cfg))}\nPAYLOAD = {data!r}\n" + KERNEL_BOX
    nb_name = f"{slug}.ipynb"
    nb = {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
          "cells": [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": src}]}
    (out / nb_name).write_text(json.dumps(nb))
    meta = {"id": f"{OWNER}/{slug}", "title": slug, "code_file": nb_name, "language": "python", "kernel_type": "notebook",
            "is_private": "true", "enable_gpu": "true", "enable_internet": "true", "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    kb = len(data) * 3 // 4 // 1024
    if kb > LIMIT_KB:
        print(f"WARNING: payload {kb} KB exceeds the ~{LIMIT_KB} KB target", file=sys.stderr)
    return {"dir": str(out), "id": meta["id"], "payload_kb": kb, "notebook_kb": (out / nb_name).stat().st_size // 1024, "lanes": lanes, "expect": expect}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--practice-n", type=int)
    ap.add_argument("--lane-h", type=float, default=LANE_H)
    ap.add_argument("--slug")
    ap.add_argument("--no-vllm", action="store_true")
    ap.add_argument("--nights", type=int, help="day/night rounds (evals at A0 and after the last night only)")
    a = ap.parse_args()
    print(json.dumps(build(a.out, a.pilot, a.practice_n, a.lane_h, a.slug, not a.no_vllm, a.nights), indent=1))
