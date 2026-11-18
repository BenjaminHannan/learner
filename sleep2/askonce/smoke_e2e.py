"""End-to-end CPU smoke of job 1 + the container steps + job 2 on a tiny random Llama (no download, no API). Same code paths as the Kaggle runs.
  python -m sleep2.askonce.smoke_e2e --out DIR [--scale 0.12]
Job 1 day logs use a scripted policy (a random model cannot ASK/ACT); everything else (generation, training, DPO, eval, grading, report) is the real code."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.12)
    ap.add_argument("--nights", type=int, default=2)
    a = ap.parse_args(argv)
    os.environ.update(ASKONCE_SCALE=str(a.scale), ASKONCE_NIGHT_SCALE="1.0", ASKONCE_OPT_STEPS="3", ASKONCE_REPEAT="3", ASKONCE_NIGHTS=str(a.nights))
    out = Path(a.out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    from . import job1, job2
    from .build_night_data import build
    from .config import jl_read, jl_write
    from .grade import grade_all
    from .model_io import get_tokenizer
    from .report import build as rbuild, to_markdown
    from .tagger import tag_all
    from .report_tagger import prf
    from .oracle_labels import oracle_labels
    j1 = out / "job1"
    job1.main(["--out", str(j1), "--smoke", "--bs", "4"])
    tags = tag_all(j1 / "diary")
    jl_write(out / "tags.jsonl", tags)
    rep = prf(tags, oracle_labels(j1 / "oracle"))
    (out / "tagger_report.json").write_text(json.dumps(rep, indent=1))
    print("tagger:", json.dumps(rep["all"]))
    tok = get_tokenizer("tiny:" + str(j1 / "tiny"))
    nd = out / "nightdata"
    build(j1 / "diary", tags, tok, nd, nights=a.nights)
    from .config import DATA
    for f in ("phrasings.json", "arc_easy_500.json"):
        shutil.copy(DATA / f, nd / f)
    res = out / "job2"
    job2.main(["--seed", "1", "--nightdata", str(nd), "--out", str(out / "job2_pilot"), "--smoke", "--bs", "4", "--pilot"])  # pilot health asserts + projection
    assert (out / "job2_pilot" / "pilot_seed1.json").exists()
    for seed in (1, 2):
        job2.main(["--seed", str(seed), "--nightdata", str(nd), "--out", str(res), "--smoke", "--bs", "4"])
    shutil.copy(j1 / "results" / "P_1.json", res / "results" / "P_1.json")
    graded, agree = grade_all(res / "results", nd / "eval_inputs.jsonl", out / "grade", use_api=False)
    o = rbuild(res / "results", out / "grade" / "graded", agree, nd, out / "tagger_report.json")
    (out / "REPORT.md").write_text(to_markdown(o, valid=False))
    print((out / "REPORT.md").read_text())
    return o


if __name__ == "__main__":
    main()
