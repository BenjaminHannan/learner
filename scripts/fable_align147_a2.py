#!/usr/bin/env python3
"""Experiment 147 -- A2 new probe: >= 40 dialogues, answer vs abstain.

Case file (sealed with PASSMARKS): artifacts/fable-align147-20260922/
fable_align147_a2_cases.json -- 1-hop and 2-hop questions in >= 6
non-possessive frames where the taught chain continues past the asked hop
(answer the sealed value), and short-chain questions (asked 2-4 hops,
fewer taught) which must abstain. 0 wrong answers.

Each case runs in a FRESH daemon dir through the mailbox (inbox file
written, daemon.process_file, reply read from outbox): teaches first,
then the question. Verdicts use the sealed 143 abstain markers and the
v2 answer extraction (exact normalised match vs sealed answer).

Run (Mac CPU, offline; registered only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_align147_a2.py --variant all \\
    --out artifacts/fable-align147-20260922/a2
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

import fable_bench121_run as B121  # noqa: E402 (scorer, read-only)

ROOT = SCRIPTS.parent
ART147 = ROOT / "artifacts" / "fable-align147-20260922"
CASES_PATH = ART147 / "fable_align147_a2_cases.json"


def _arms(variant: str):
    if variant == "134":
        import fable_loop147_agent as Var
        return (Var.Loop147Daemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147))
    if variant == "113e":
        import fable_loop147_agent113e as Var
        return (Var.Loop147on113eDaemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147_113E))
    if variant == "132":
        import fable_loop147_agent132 as Var
        return (Var.Loop147on132Daemon,
                copy.deepcopy(Var.DEFAULT_CONFIG147_132))
    raise ValueError(variant)


def run_case(case: dict, workdir: Path, markers: list[str],
             daemon_cls, cfg: dict) -> dict:
    rec = {"id": case["id"], "family": case.get("family", ""),
           "frame": case.get("frame", ""), "expected": case["expected"],
           "verdict": "OK", "teach_replies": [], "reply": "",
           "extracted": "", "stage": "", "reasons": []}
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        daemon = daemon_cls(str(workdir), cfg=dict(copy.deepcopy(cfg)))
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"boot failed: {exc!r}")
        return rec
    try:
        for i, text in enumerate(list(case["teaches"]) + [case["question"]]):
            fname = f"t{i:02d}.txt"
            (workdir / "inbox" / fname).write_text(str(text) + "\n",
                                                   encoding="utf-8")
            daemon.process_file(workdir / "inbox" / fname)
            reply = (workdir / "outbox" / fname).read_text(
                encoding="utf-8").strip()
            if i < len(case["teaches"]):
                rec["teach_replies"].append(reply)
                if not (reply.startswith("Saved:")
                        or reply == "I already have that."):
                    rec["verdict"] = "HARNESS-ERROR"
                    rec["reasons"].append(f"teach {i} rejected: {reply!r}")
                    rec["reply"] = reply
                    return rec
            else:
                rec["reply"] = reply
                try:
                    rec["stage"] = str(
                        getattr(daemon.loop.ears, "last_stage", ""))
                except Exception:  # noqa: BLE001
                    rec["stage"] = ""
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"turn raised {exc!r}")
        return rec
    reply = rec["reply"]
    low = reply.lower()
    abst = any(m.lower() in low for m in markers)
    exp = case["expected"]
    rec["extracted"] = B121.extract_answer(reply)
    if exp == "abstain":
        if abst:
            rec["verdict"] = "OK"
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident reply where abstain sealed: {reply!r}")
    else:
        if B121.norm(rec["extracted"]) == B121.norm(exp) and B121.norm(exp):
            rec["verdict"] = "OK"
        elif abst:
            rec["verdict"] = "MISSED"
            rec["reasons"].append(
                f"abstained though answer sealed ({exp!r}): {reply!r}")
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident {rec['extracted']!r} != sealed {exp!r}: {reply!r}")
    return rec


def run_variant(variant: str, cases: dict, out: Path,
                cases_path: Path | None = None) -> dict:
    t0 = time.time()
    daemon_cls, cfg = _arms(variant)
    markers = cases["abstain_markers"]
    workroot = out / variant / "scratch"
    rows = []
    for case in cases["cases"]:
        rec = run_case(case, workroot / case["id"], markers,
                       daemon_cls, cfg)
        rows.append(rec)
        print(f"a2/{variant} {rec['id']}: {rec['verdict']} "
              f"stage={rec['stage']} reply={rec['reply'][:80]!r}",
              flush=True)
    (out / variant).mkdir(parents=True, exist_ok=True)
    (out / variant / "fable_align147_a2_rows.json").write_text(
        json.dumps({"rows": rows}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    rep = {"variant": variant, "n": len(rows),
           "ok": sum(r["verdict"] == "OK" for r in rows),
           "wrong": [r["id"] for r in rows
                     if r["verdict"] == "WRONG-ANSWER"],
           "missed": [r["id"] for r in rows if r["verdict"] == "MISSED"],
           "harness": [r["id"] for r in rows
                       if r["verdict"] == "HARNESS-ERROR"],
           "seconds": round(time.time() - t0, 1)}
    (out / variant / "fable_align147_a2_summary.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 147 A2 probe")
    ap.add_argument("--variant", default="all",
                    choices=["all", "134", "113e", "132"])
    ap.add_argument("--cases", default=str(CASES_PATH))
    ap.add_argument("--out", default=str(ART147 / "a2"))
    args = ap.parse_args(argv)
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    variants = ["134", "113e", "132"] if args.variant == "all" else [
        args.variant]
    reps = {v: run_variant(v, cases, out) for v in variants}
    ok = all(r["wrong"] == [] and r["missed"] == [] and r["harness"] == []
             for r in reps.values())
    print("A2", "PASS" if ok else "FAIL", json.dumps(reps))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
