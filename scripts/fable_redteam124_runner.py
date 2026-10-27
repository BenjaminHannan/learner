#!/usr/bin/env python3
"""Exp 124 runner: 62 sealed composer red-team cases vs loop113b and loop102.

Each case runs in a FRESH daemon dir through the mailbox (inbox file written,
daemon.process_file, reply read from outbox). Verdicts come ONLY from the
sealed expectations in fable_redteam124_cases.json.

Run (ONLY after PASSMARKS sealed; Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_redteam124_runner.py
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam124-20260922"
CASES_PATH = ART / "fable_redteam124_cases.json"

import fable_loop102_agent as L102  # noqa: E402 (read-only)
import fable_loop113b_agent as L113b  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)


def load_cfg(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


CFG102 = load_cfg(ROOT / "artifacts" / "fable-loop102-20260921"
                  / "loop102-config.json")
CFG113B = load_cfg(ROOT / "artifacts" / "fable-bench113b-20260922"
                   / "loop113b-config.json")


def make_daemon(arm: str, workdir: Path):
    cfg = copy.deepcopy(CFG102 if arm == "loop102" else CFG113B)
    cfg["state_dir"] = str(workdir)
    if arm == "loop102":
        return L102.Loop102Daemon(str(workdir), cfg=cfg, idle_seconds=30.0)
    return L113b.Loop113bDaemon(str(workdir), cfg=cfg, idle_seconds=30.0)


def triples_set(nb) -> set[list]:
    return set(tuple(t) for t in L90.notebook_triples(nb))


def run_case(case: dict, arm: str, workdir: Path) -> dict:
    rec = {"id": case["id"], "family": case["family"], "arm": arm,
           "turns": [], "verdict": "OK", "reasons": []}
    try:
        daemon = make_daemon(arm, workdir)
    except Exception as exc:  # noqa: BLE001
        rec["verdict"] = "HARNESS-ERROR"
        rec["reasons"].append(f"boot failed: {exc!r}")
        return rec
    nb = daemon.loop.nb
    allowed = set(tuple(f) for f in case.get("allowed_facts", []))
    for i, step in enumerate(case["steps"]):
        text = step["text"]
        before = triples_set(nb)
        fname = f"t{i:02d}.txt"
        try:
            (workdir / "inbox" / fname).write_text(text, encoding="utf-8")
            daemon.process_file(workdir / "inbox" / fname)
            reply = (workdir / "outbox" / fname).read_text(
                encoding="utf-8").strip()
        except Exception as exc:  # noqa: BLE001
            rec["turns"].append({"i": i, "text": text, "reply": "",
                                 "error": repr(exc)})
            rec["verdict"] = "HARNESS-ERROR"
            rec["reasons"].append(f"turn {i} raised {exc!r}")
            return rec
        after = triples_set(nb)
        added = sorted(list(after - before))
        wrong = [t for t in added if tuple(t) not in allowed]
        t = {"i": i, "text": text, "reply": reply, "added": added,
             "wrong_writes": wrong}
        rec["turns"].append(t)
    return rec


def check_case(case: dict, rec: dict, markers: list[str]) -> dict:
    """Apply sealed expectations; returns verdict + reasons (mutates rec)."""
    arm = rec["arm"]
    exp = case["expect"]
    abstain_extra = set(case.get("ask_abstain_102", [])) if arm == "loop102" \
        else set()
    reasons: list[str] = []
    low_markers = [m.lower() for m in markers]

    def is_abstain(reply: str) -> bool:
        rl = reply.lower()
        return any(m in rl for m in low_markers)

    for t in rec["turns"]:
        i, reply = t["i"], t["reply"]
        # wrong writes are arm-independent
        if t["wrong_writes"]:
            reasons.append(f"turn {i} wrong writes {t['wrong_writes']}")
        if i in abstain_extra:
            if not is_abstain(reply):
                reasons.append(f"turn {i} 102-sealed clarify missed: {reply!r}")
            for bad in exp.get("absent_everywhere", []):
                if bad.lower() in reply.lower() and bad:
                    reasons.append(f"turn {i} 102 contains absent {bad!r}")
            continue
        if i in exp.get("abstain_on", []):
            if not is_abstain(reply):
                reasons.append(f"turn {i} abstain missed: {reply!r}")
        if i in exp.get("zero_fact_writes_on", []):
            if t["added"]:
                reasons.append(f"turn {i} unexpected writes {t['added']}")
    for ch in exp.get("checks", []):
        i = ch["turn"]
        if i in abstain_extra:
            continue
        reply = rec["turns"][i]["reply"]
        rl = reply.lower()
        for good in ch.get("contains", []):
            if good.lower() not in rl:
                reasons.append(f"turn {i} missing {good!r} in {reply!r}")
        for bad in ch.get("absent", []):
            if bad and bad.lower() in rl:
                reasons.append(f"turn {i} contains absent {bad!r}")
    for bad in exp.get("absent_everywhere", []):
        if not bad:
            continue
        for t in rec["turns"]:
            if t["i"] in abstain_extra:
                continue
            if bad.lower() in t["reply"].lower():
                # allowed when the turn's own check requires it
                need = any(bad.lower() in (g.lower())
                           for ch in exp.get("checks", [])
                           if ch["turn"] == t["i"]
                           for g in ch.get("contains", []))
                if not need:
                    reasons.append(
                        f"turn {t['i']} reply contains globally-absent "
                        f"{bad!r}")
    rec["reasons"] = reasons
    rec["verdict"] = "OK" if not reasons else "BUG"
    return rec


def main() -> int:
    suite = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch"
    out: dict = {"cases": [], "t0": time.time()}
    for arm in ("loop113b", "loop102"):
        for case in suite["cases"]:
            workdir = scratch / arm / case["id"]
            if workdir.exists():
                import shutil
                shutil.rmtree(workdir)
            workdir.mkdir(parents=True, exist_ok=True)
            rec = run_case(case, arm, workdir)
            if rec["verdict"] != "HARNESS-ERROR":
                check_case(case, rec, markers)
            out["cases"].append(rec)
            print(f"{arm} {case['id']}: {rec['verdict']}", flush=True)
    out["seconds"] = round(time.time() - out["t0"], 1)
    (ART / "fable_redteam124_results.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    n = len(out["cases"])
    nbug = sum(1 for r in out["cases"] if r["verdict"] == "BUG")
    nerr = sum(1 for r in out["cases"] if r["verdict"] == "HARNESS-ERROR")
    print(f"done: {n} runs, {n - nbug - nerr} OK, {nbug} BUG, "
          f"{nerr} HARNESS-ERROR in {out['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
