"""Build the Kaggle kernel directory for Practice-1 (one-cell NOTEBOOK kernel; payload = practice/ code + data + needed sleep2 modules, base64 xz).
  python -m practice.kaggle.build_job --out /tmp/kern [--pilot] [--practice-n N] [--lane-h 10]
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
CODE = ["__init__.py", "grade.py", "harness.py", "job.py", "library.py", "night.py", "tools.py"]
LANE_H = 10.0       # the lane's own deadline (hours)
BOX_H = 11.0        # hard kill by the box (the prereg's 11 h cut)


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


def build(out, pilot=False, practice_n=None, lane_h=LANE_H):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    data = base64.b64encode(payload()).decode()
    slug = "practice1-pilot" if pilot else "practice1"
    n = f" --practice-n {practice_n}" if practice_n else ""
    extra = " --pilot" if pilot else f" --deadline-s {int(lane_h * 3600)}{n}"
    if pilot:
        n_ = f" --practice-n {practice_n}" if practice_n else ""
        extra += n_
    lanes = [f"python -m practice.job --arm {arm} --lane {i} --out $OUT/practice1{extra}" for i, arm in enumerate(("P", "C"))]
    expect = [f"practice1/{a}/pilot.json" for a in ("P", "C")] if pilot else \
        [f"practice1/{a}/results/{a}{k}.json" for a in ("P", "C") for k in (1, 2, 3)] + [f"practice1/{a}/results/A0.json" for a in ("P", "C")] + [f"practice1/{a}/timing.json" for a in ("P", "C")]
    deadline_h = 1.0 if pilot else BOX_H
    cfg = {"lanes": lanes, "env": {}, "deadline_s": int(deadline_h * 3600), "expect": expect}
    src = f"CFG_JSON = {json.dumps(json.dumps(cfg))}\nPAYLOAD = {data!r}\n" + BOX
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
    a = ap.parse_args()
    print(json.dumps(build(a.out, a.pilot, a.practice_n, a.lane_h), indent=1))
