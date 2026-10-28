#!/usr/bin/env python3
"""Fresh rows, scored once (PREREG-think2 Addendum G, "the fresh rows are then scored once for each passing arm"; Addendum I, item 4).

  python backbone/think/fresh_hops.py RUNS --data DATA --out FRESH --arms hplains,hloops --seeds 0,1 [--smoke]

RUNS holds the think1 runs (RUNS/<arm>_s<seed>/{adapter/, inject.pt, result_<arm>_s<seed>.json}: where think1.py --out RUNS/<arm>_s<seed> saves them).
DATA holds fresh.jsonl (build_hops.py); its sha256 must equal the "fresh" one in the committed backbone/results/hops/HOPS_REPORT.json, or nothing runs.
For each (arm, seed) it scores the saved adapter on the fresh rows with eval_adapter.main (looped arms: r = 1-12 with the answers and log-probs kept, so
the stop rules can be rebuilt; plain arms: one pass; model and max_len as the arm's own validation result recorded them), and writes FRESH/<arm>_s<seed>/result_<arm>_s<seed>.json, shaped like a think1 result with the
scores under eval["fresh"] so that `summarize_hops.py FRESH --data DATA --split fresh --validation RUNS` applies the same marks to them and holds each against its validation read:
  {arm, seed, source: "fresh", steps_stage1 (from the arm's own validation result), inject, adapter_sha, data_sha256, env, eval: {fresh: {r1..r12, main}}}
A looped arm's main is its r6 entry without the answers, as think1 builds it. FRESH/<arm>_s<seed>/eval_<arm>_s<seed>.json keeps eval_adapter's own
output. An (arm, seed) whose result file exists is skipped, so each is scored once. A missing adapter (or one that is not the adapter the arm's
validation result describes, or an injection arm's missing inject.pt, which eval_adapter would silently score without W), an eval_adapter that exits
nonzero or raises (a corrupt adapter, out of memory), and an output it left unreadable are reported and the other arms still run; the exit code is then 1. A fresh.jsonl that is not the committed one exits 2 before anything is read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import eval_adapter as EA  # noqa: E402
import think1 as K  # noqa: E402

REPORT = HERE.parent / "results" / "hops" / "HOPS_REPORT.json"  # the committed report: its "fresh" sha256 names the only fresh file a claim may use


def sha256(path):
    h, buf = hashlib.sha256(), memoryview(bytearray(1 << 20))
    with open(path, "rb") as fh:
        while n := fh.readinto(buf):
            h.update(buf[:n])
    return h.hexdigest()


def fresh_sha(data):
    """(sha256, None) of DATA/fresh.jsonl when it equals the committed one, else (None, why)."""
    f = Path(data) / "fresh.jsonl"
    if not f.is_file():
        return None, f"{f} not found"
    want, got = json.loads(REPORT.read_text())["files"]["fresh"]["sha256"], sha256(f)
    if got != want:
        return None, f"{f} has sha256 {got}, the committed HOPS_REPORT.json says {want}: not the fresh rows, not scoring anything"
    return got, None


def score(arm, seed, runs, data, out, smoke, dsha):
    """Score one (arm, seed). Returns (status, text): done, skipped, or a failure (missing adapter, no validation result, wrong adapter, no inject.pt, eval error)."""
    run = Path(runs) / f"{arm}_s{seed}"
    adapter, val = run / "adapter", run / f"result_{arm}_s{seed}.json"  # think1: pm.save_pretrained(out / "adapter"), result_{arm}_s{seed}.json in out
    d = Path(out) / f"{arm}_s{seed}"
    res_path, raw_path = d / f"result_{arm}_s{seed}.json", d / f"eval_{arm}_s{seed}.json"
    if res_path.exists():
        return "skipped", f"{arm} seed {seed}: already scored ({res_path})"
    if not all((adapter / f).is_file() for f in ("adapter_config.json", "adapter_model.safetensors")):
        return "failed", f"{arm} seed {seed}: no adapter at {adapter}"
    if not val.is_file():
        return "failed", f"{arm} seed {seed}: no validation result {val} (its steps_stage1 and adapter_sha are copied from it)"
    v = json.loads(val.read_text())
    if v.get("aborted"):
        return "failed", f"{arm} seed {seed}: the run was aborted ({v['aborted']}): nothing to score"
    if v.get("adapter_sha") and K.adapter_sha(adapter) != v["adapter_sha"]:
        return "failed", f"{arm} seed {seed}: the adapter at {adapter} is not the one {val.name} was scored with (adapter_sha differs)"
    if v.get("inject") and not (run / "inject.pt").is_file():  # eval_adapter loads W from Path(adapter).parent / "inject.pt", and skips it silently if absent
        return "failed", f"{arm} seed {seed}: {run / 'inject.pt'} is missing: eval_adapter would score the arm without its W"
    looped = arm in K.HOPS_LOOPED
    argv = ["--adapter", str(adapter), "--data", str(data), "--file", "fresh.jsonl", "--out", str(raw_path),
            *(["--model", v["model"]] if v.get("model") else []), *(["--max-len", str(v["max_len"])] if v.get("max_len") else []),  # as the arm was scored
            *(["--loops", ",".join(map(str, K.HOPS_EVAL_LOOPS)), "--keep-preds"] if looped else []), *(["--smoke"] if smoke else [])]
    t0 = time.time()
    try:  # a corrupt adapter (PeftModel.from_pretrained raising), a CUDA OOM or an argparse exit on one arm must not stop the other arms from being scored
        rc = EA.main(argv)
    except (Exception, SystemExit) as e:  # not KeyboardInterrupt: Ctrl-C and a kill still stop the whole run
        return "failed", f"{arm} seed {seed}: eval_adapter raised {e!r}"
    if rc:
        return "failed", f"{arm} seed {seed}: eval_adapter exited {rc}"
    try:
        raw = json.loads(raw_path.read_text())
        tags, n_rows = dict(raw["eval"]), raw["n"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return "failed", f"{arm} seed {seed}: eval_adapter's output {raw_path} is unreadable or incomplete ({e!r})"
    want = [f"r{r}" for r in K.HOPS_EVAL_LOOPS] if looped else ["main"]
    if gone := [t for t in want if t not in tags]:
        return "failed", f"{arm} seed {seed}: eval_adapter's output lacks {', '.join(gone)}"
    if looped:  # as think1: main = the r6 entry without the answers
        tags["main"] = {k: x for k, x in tags[f"r{K.HOPS_MAIN}"].items() if k != "preds"}
    res = dict(arm=arm, seed=seed, source="fresh", steps_stage1=v.get("steps_stage1"), inject=raw.get("inject"), adapter_sha=raw.get("adapter_sha"),
               data_sha256=dsha, env=raw.get("env"), eval={"fresh": tags})
    tmp = res_path.with_name(res_path.name + ".tmp")  # written whole, then moved: a crash never leaves a half file that a rerun would skip
    tmp.write_text(json.dumps(res))
    tmp.replace(res_path)
    return "done", f"{arm} seed {seed}: scored {n_rows} fresh rows in {time.time() - t0:.0f}s -> {res_path}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", help="RUNS: holds <arm>_s<seed>/adapter, inject.pt and the validation result_<arm>_s<seed>.json")
    ap.add_argument("--data", required=True, help="dir holding fresh.jsonl (build_hops.py)")
    ap.add_argument("--out", required=True, help="FRESH: one <arm>_s<seed>/ directory per arm and seed")
    ap.add_argument("--arms", required=True, help="comma list of hops arms")
    ap.add_argument("--seeds", default="0", help="comma list of seeds")
    ap.add_argument("--smoke", action="store_true", help="the tiny CPU model (tests this script)")
    a = ap.parse_args(argv)
    arms, seeds = [x for x in a.arms.split(",") if x], [int(x) for x in a.seeds.split(",") if x]
    if bad := [x for x in arms if x not in K.HOPS]:
        ap.error(f"not hops arms: {', '.join(bad)} (use {', '.join(K.HOPS)})")
    dsha, why = fresh_sha(a.data)  # before anything else
    if why:
        print(f"[fresh_hops] REFUSED: {why}", file=sys.stderr, flush=True)
        return 2
    n = {"done": 0, "skipped": 0, "failed": 0}
    for arm in arms:
        for seed in seeds:
            status, text = score(arm, seed, a.runs, a.data, a.out, a.smoke, dsha)
            n[status] += 1
            print(f"[fresh_hops] {status.upper()}: {text}", file=sys.stderr if status == "failed" else sys.stdout, flush=True)
    print(f"[fresh_hops] {n['done']} scored, {n['skipped']} already done, {n['failed']} failed", flush=True)
    return 1 if n["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
