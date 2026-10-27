#!/usr/bin/env python3
"""Experiment 147 -- bench comparisons: each variant vs its own base.

Splits (all read-only sealed inputs):
  bench121-new / bench121-old (data/open/bench121 + bench103, scorer v2
    from scripts/fable_bench121_run.py, imported read-only),
  fable-edit-200 / s2fresh-4hop (scripts/fable_bench113_run.run_item with a
    daemon factory, read-only),
  bench132-new (data/open/bench132, scorer v2 from fable_bench132_run.py).

One item, one FRESH in-process daemon dir per arm. Per-item verdict pairs
(base vs variant) give: new_wrong (variant wrong where base not wrong --
must be 0), correct_lost (base correct -> variant non-correct, every item
listed), fixed, moves. Nothing sealed is written; rows go to --out.

Run (Mac CPU, offline; registered only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_align147_bench.py --variant all \\
    --out artifacts/fable-align147-20260922/bench
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench113_run as B113  # noqa: E402 (run_item, read-only)
import fable_bench121_run as B121  # noqa: E402 (scorer v2, read-only)
import fable_bench132_run as B132  # noqa: E402 (scorer v2, read-only)

ROOT = SCRIPTS.parent

SPLITS = {
    "bench121-new": ROOT / "data" / "open" / "bench121"
    / "fable_edit121_4hop.jsonl",
    "bench121-old": ROOT / "data" / "open" / "bench103"
    / "fable_edit103_s2fresh_4hop.jsonl",
    "fable-edit-200": B113.DATA_A,
    "s2fresh-4hop": B113.DATA_B,
    "bench132-new": ROOT / "data" / "open" / "bench132"
    / "fable_edit132_4hop.jsonl",
}


def _load(name: str) -> list[dict]:
    return [json.loads(l) for l in SPLITS[name].read_text(
        encoding="utf-8").splitlines() if l.strip()]


def _arms(variant: str):
    if variant == "134":
        import fable_loop134_agent as Base
        import fable_loop147_agent as Var
        base_cfg = json.loads(
            (ROOT / "artifacts" / "fable-loop134-20260922"
             / "loop134-config.json").read_text(encoding="utf-8"))
        return ("loop134", Base.Loop134Daemon, base_cfg,
                "loop147", Var.Loop147Daemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147))
    if variant == "113e":
        import fable_loop113e_agent as Base
        import fable_loop147_agent113e as Var
        base_cfg = json.loads(
            (ROOT / "artifacts" / "fable-bench113e-20260922"
             / "loop113e-config.json").read_text(encoding="utf-8"))
        return ("loop113e", Base.Loop113eDaemon, base_cfg,
                "loop147-113e", Var.Loop147on113eDaemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147_113E))
    if variant == "132":
        import fable_loop132_agent as Base
        import fable_loop147_agent132 as Var
        base_cfg = json.loads(
            (ROOT / "artifacts" / "fable-bench132-20260922"
             / "loop132-config.json").read_text(encoding="utf-8"))
        return ("loop132", Base.Loop132Daemon, base_cfg,
                "loop147-132", Var.Loop147on132Daemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147_132))
    raise ValueError(variant)


def _factory(daemon_cls, cfg):
    outer = cfg

    def build(ddir, cfg=None, **_kw):
        full = copy.deepcopy(outer)
        if isinstance(cfg, dict):
            full.update(cfg)
        full["state_dir"] = str(ddir)
        return daemon_cls(str(ddir), cfg=full, idle_seconds=3600.0)
    return build


def _run_v2(item: dict, workroot: Path, build, classify) -> dict:
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = build(ddir)
    teach_replies: list[str] = []
    n_reject = 0
    n = 0
    taught = item["taught"] if isinstance(item.get("taught"), list) else []
    for t in taught:
        s = t["sentence_en"] if isinstance(t, dict) else str(t)
        n += 1
        name = f"t{n:03d}.txt"
        (ddir / "inbox" / name).write_text(s + "\n", encoding="utf-8")
        daemon.process_file(ddir / "inbox" / name)
        reply = (ddir / "outbox" / name).read_text(encoding="utf-8").strip()
        teach_replies.append(reply)
        n_reject += 0 if B121.teach_accepted(reply) else 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                        encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = classify(reply, golds)
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:
        stage = ""
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "verdict": verdict, "exact": bool(exact),
            "contains_gold": bool(contains),
            "extracted": B121.extract_answer(reply), "ears_stage": stage,
            "n_teach_reject": n_reject, "teach_replies": teach_replies,
            "reply": reply}


def run_split(variant: str, split: str, out: Path) -> dict:
    t0 = time.time()
    bname, bcls, bcfg, vname, vcls, vcfg = _arms(variant)
    items = _load(split)
    workroot = out / variant / split
    if workroot.exists():
        shutil.rmtree(workroot)
    (workroot / "base").mkdir(parents=True)
    (workroot / "var").mkdir(parents=True)
    bf, vf = _factory(bcls, bcfg), _factory(vcls, vcfg)
    if split in ("fable-edit-200", "s2fresh-4hop"):
        Brows = [B113.run_item(it, workroot / "base", dict(bcfg), bf)
                 for it in items]
        Vrows = [B113.run_item(it, workroot / "var", dict(vcfg), vf)
                 for it in items]
    elif split == "bench132-new":
        Brows = [_run_v2(it, workroot / "base", bf, B132.classify_v2)
                 for it in items]
        Vrows = [_run_v2(it, workroot / "var", vf, B132.classify_v2)
                 for it in items]
    else:
        Brows = [_run_v2(it, workroot / "base", bf, B121.classify_v2)
                 for it in items]
        Vrows = [_run_v2(it, workroot / "var", vf, B121.classify_v2)
                 for it in items]
    (out / variant / f"rows-{split}-base.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in Brows) + "\n", encoding="utf-8")
    (out / variant / f"rows-{split}-var.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in Vrows) + "\n", encoding="utf-8")
    B = {r["id"]: r["verdict"] for r in Brows}
    V = {r["id"]: r["verdict"] for r in Vrows}
    new_wrong = sorted(i for i in B
                       if V[i] == "wrong" and B[i] != "wrong")
    correct_lost = sorted(i for i in B
                          if B[i] == "correct" and V[i] != "correct")
    fixed = sorted(i for i in B
                   if B[i] != "correct" and V[i] == "correct")
    abstain_to_wrong = sorted(i for i in B
                              if B[i] == "abstain" and V[i] == "wrong")
    rep = {"variant": variant, "split": split, "n": len(items),
           "base_table": _tally(Brows), "var_table": _tally(Vrows),
           "new_wrong": new_wrong, "correct_lost": correct_lost,
           "fixed": fixed, "abstain_to_wrong": abstain_to_wrong,
           "seconds": round(time.time() - t0, 1)}
    (out / variant / f"pair-{split}.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"{variant}/{split}: n={len(items)} new_wrong={new_wrong} "
          f"correct_lost={correct_lost} fixed={fixed} "
          f"({rep['seconds']}s)", flush=True)
    return rep


def _tally(rows: list[dict]) -> dict:
    t: dict = {}
    for r in rows:
        cell = t.setdefault(r.get("type", "?"), {"correct": 0, "abstain": 0,
                                                 "wrong": 0})
        cell[r["verdict"]] = cell.get(r["verdict"], 0) + 1
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 147 bench comparisons")
    ap.add_argument("--variant", default="all",
                    choices=["all", "134", "113e", "132"])
    ap.add_argument("--splits", default=",".join(SPLITS))
    ap.add_argument("--out", default=str(
        ROOT / "artifacts" / "fable-align147-20260922" / "bench"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    variants = ["134", "113e", "132"] if args.variant == "all" else [
        args.variant]
    splits = [s for s in args.splits.split(",") if s in SPLITS]
    summary = {}
    for v in variants:
        for s in splits:
            rep = run_split(v, s, out)
            summary[f"{v}/{s}"] = {
                "n": rep["n"], "new_wrong": rep["new_wrong"],
                "correct_lost": rep["correct_lost"], "fixed": rep["fixed"],
                "abstain_to_wrong": rep["abstain_to_wrong"],
                "seconds": rep["seconds"]}
    prior: dict = {}
    try:
        prior = json.loads((out / "bench147_summary.json").read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        prior = {}
    prior.update(summary)
    (out / "bench147_summary.json").write_text(
        json.dumps(prior, indent=1), encoding="utf-8")
    ok = all(not v["new_wrong"] for v in prior.values())
    print("BENCH", "PASS(new_wrong==0)" if ok else "FAIL(new_wrong>0)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
