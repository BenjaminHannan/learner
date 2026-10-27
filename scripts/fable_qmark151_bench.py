#!/usr/bin/env python3
"""Experiment 151, Q3: bench suites per variant (scorer v2, imported).

Scorer (classify_v2 / extract_answer / teach_accepted / summarize /
misunderstood) is imported from the sealed bench132 runner (read-only);
only the daemon factory differs per arm. One item runs through one FRESH
daemon dir, English only, teaches verbatim.

Suites: bench121-new (200), bench121-old/s2fresh (200), bench132-new (200),
fable_edit_200 (200). Variant A (loop134+qmark) compares against sealed
loop134 rows where they exist (bench121 new/old, fable_edit_200) and a
same-process loop134 baseline for bench132-new; variant B
(loop132+wordmatch149+qmark) compares against sealed loop132 rows for
bench132-new and a same-process qrewrite149 baseline for the rest.
Prediction: 0 verdict diffs everywhere (all 800 questions end in "?";
dev scan: 0 bench teaches trigger the qmark predicate with both teach
parsers rejecting).

Process hygiene: variant A runs patch-free (this module never applies the
149 wordmatch patch at import); variant B re-applies it at bind. The two
variants run in SEPARATE processes (separate invocations).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_qmark151_bench.py --variant 151
  (... --variant qrewrite)
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

ROOT = SCRIPTS.parent
MY_ART = ROOT / "artifacts" / "fable-qmark151-20260922"

import fable_bench132_run as B132  # noqa: E402 (sealed scorer, read-only)

SUITES = {
    "bench121-new": ROOT / "data" / "open" / "bench121"
    / "fable_edit121_4hop.jsonl",
    "bench121-old": ROOT / "data" / "open" / "bench103"
    / "fable_edit103_s2fresh_4hop.jsonl",
    "bench132-new": ROOT / "data" / "open" / "bench132"
    / "fable_edit132_4hop.jsonl",
    "fable_edit_200": ROOT / "data" / "open" / "bench65"
    / "fable_edit_200.jsonl",
}

# Sealed reference rows: (suite, sealed_row_file, verdict_key).
SEALED_REFS = {
    ("151", "bench121-new"): (ROOT / "artifacts" / "fable-loop134-20260922"
                              / "fable_bench121_loop134_new_121_4hop_rows.jsonl"),
    ("151", "bench121-old"): (ROOT / "artifacts" / "fable-loop134-20260922"
                              / "fable_bench121_loop134_old_s2fresh_4hop_rows.jsonl"),
    ("151", "fable_edit_200"): (ROOT / "artifacts" / "fable-loop134-20260922"
                                / "marks134" / "bench-rows-fable_edit_200.jsonl"),
    ("qrewrite", "bench132-new"): (ROOT / "artifacts"
                                   / "fable-bench132-20260922"
                                   / "fable_bench132_loop132_new_132_4hop_rows.jsonl"),
}


def run_item(item: dict, workroot: Path, daemon_cls, cfg: dict) -> dict:
    ddir = workroot / item["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = daemon_cls(str(ddir), cfg=dict(copy.deepcopy(cfg)))
    teach_replies: list[str] = []
    n_reject = 0
    n = 0
    for t in item["taught"]:
        n += 1
        name = f"t{n:03d}.txt"
        sent = t["sentence_en"] if isinstance(t, dict) else str(t)
        (ddir / "inbox" / name).write_text(str(sent) + "\n", encoding="utf-8")
        daemon.process_file(ddir / "inbox" / name)
        reply = (ddir / "outbox" / name).read_text(encoding="utf-8").strip()
        teach_replies.append(reply)
        n_reject += 0 if B132.teach_accepted(reply) else 1
    n += 1
    qname = f"t{n:03d}.txt"
    (ddir / "inbox" / qname).write_text(str(item["question"]) + "\n",
                                       encoding="utf-8")
    daemon.process_file(ddir / "inbox" / qname)
    reply = (ddir / "outbox" / qname).read_text(encoding="utf-8").strip()
    golds = [str(g) for g in list(item.get("gold", []))
             + list(item.get("gold_aliases", []))]
    verdict, exact, contains = B132.classify_v2(reply, golds)
    try:
        stage = str(getattr(daemon.loop.ears, "last_stage", ""))
    except Exception:  # noqa: BLE001
        stage = ""
    return {"id": item["id"], "type": str(item.get("type", "?")),
            "expected": str(item.get("expected", "?")),
            "verdict": verdict,
            "exact": bool(exact), "contains_gold": bool(contains),
            "misunderstood": bool(B132.misunderstood(reply)),
            "extracted": B132.extract_answer(reply), "ears_stage": stage,
            "n_teach": len(teach_replies), "n_teach_reject": n_reject,
            "reply": reply}


def run_suite(suite: str, daemon_cls, cfg: dict, tag: str) -> list[dict]:
    items = [json.loads(line) for line in
             SUITES[suite].read_text(encoding="utf-8").splitlines()
             if line.strip()]
    workroot = MY_ART / f"scratchbench-{tag}" / suite
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    rows = [run_item(it, workroot, daemon_cls, cfg) for it in items]
    (MY_ART / f"fable_qmark151_bench_{tag}_{suite}_rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                   for r in rows) + "\n", encoding="utf-8")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 151 Q3 benches")
    ap.add_argument("--variant", default="151", choices=["151", "qrewrite"])
    ap.add_argument("--suites", default="",
                    help="comma list overriding the variant default")
    args = ap.parse_args(argv)

    import fable_loop151_agent as M151  # noqa: E402 (this exp)
    if args.variant == "151":
        import fable_loop134_agent as MB  # noqa: E402 (read-only base)
        base_cls, base_cfg = MB.Loop134Daemon, MB.DEFAULT_CONFIG134
        var_cls, var_cfg = M151.Loop151Daemon, M151.DEFAULT_CONFIG151
    else:
        import fable_loop149_agent as MB  # noqa: E402 (read-only 132+149)
        base_cls, base_cfg = MB.Qrewrite149Daemon, MB.QREWRITE149_CONFIG
        var_cls, var_cfg = M151.Qmark151Daemon, M151.QMARK151_CONFIG
    tag = "151" if args.variant == "151" else "qrewrite151"
    default_suites = ["bench121-new", "bench121-old", "bench132-new",
                      "fable_edit_200"]
    suites = [s for s in (args.suites.split(",") if args.suites else
                          default_suites) if s in SUITES]

    t0 = time.time()
    out: dict = {"seconds": 0.0, "scorer": "v2-imported", "variant": tag,
                 "suites": {}}
    for suite in suites:
        key = (args.variant, suite)
        if key in SEALED_REFS:
            var_rows = run_suite(suite, var_cls, var_cfg, tag)
            ref_rows = [json.loads(line) for line in
                        SEALED_REFS[key].read_text(
                            encoding="utf-8").splitlines() if line.strip()]
            ref = {r["id"]: r.get("verdict") for r in ref_rows}
            diffs = [r["id"] for r in var_rows
                     if ref.get(r["id"]) != r["verdict"]]
            out["suites"][suite] = {
                "n": len(var_rows), "table": B132.summarize(var_rows),
                "base": f"sealed:{SEALED_REFS[key].name}",
                "verdict_diffs": diffs}
        else:
            base_rows = run_suite(suite, base_cls, base_cfg, tag + "-base")
            var_rows = run_suite(suite, var_cls, var_cfg, tag)
            base = {r["id"]: r.get("verdict") for r in base_rows}
            diffs = [r["id"] for r in var_rows
                     if base.get(r["id"]) != r["verdict"]]
            out["suites"][suite] = {
                "n": len(var_rows), "table": B132.summarize(var_rows),
                "base_table": B132.summarize(base_rows),
                "base": "same-process-baseline",
                "verdict_diffs": diffs}
        print(f"{tag} {suite}: verdict_diffs={out['suites'][suite]['verdict_diffs']}",
              flush=True)
        for typ, cell in sorted(out["suites"][suite]["table"].items()):
            print(f"  {typ}: {cell}")
    out["seconds"] = round(time.time() - t0, 1)
    (MY_ART / f"fable_qmark151_bench_{tag}_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
