#!/usr/bin/env python3
"""Exp 143 runner: sealed question red-team cases vs loop132 (single arm).

Each case runs in a FRESH daemon dir through the mailbox (inbox file written,
daemon.process_file, reply read from outbox): teach sentences first, then the
question. Verdicts come ONLY from the sealed expectations.

Verdicts per case:
  OK           reply matches the sealed expectation
  WRONG-ANSWER a confident reply that is not the expected answer (critical)
  MISSED       answer exists but it abstained / said it didn't understand
  HARNESS-ERROR exception, or any teach rejected (unfair to judge the question)

"Saved:" acknowledgements are never answers (they only occur on teach turns).

Run (ONLY after PASSMARKS sealed; Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_redteam143_run.py
"""

from __future__ import annotations

import copy
import json
import string
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fable_loop132_agent import (  # noqa: E402 (read-only target)
    DEFAULT_CONFIG132, Loop132Daemon)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam143-20260922"
CASES_PATH = ART / "fable_redteam143_cases.json"

DUP_ACK = "I already have that."


def norm(s: str) -> str:
    s = (s or "").lower().replace("\u2019", "'")
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(t for t in s.split() if t not in ("a", "an", "the"))


def extract_answer(reply: str) -> str:
    low = (reply or "").lower()
    hits = [low.rfind(" is "), low.rfind(" are ")]
    idx = max(hits)
    tail = reply[idx + 4:] if idx >= 0 else (reply or "")
    return tail.strip().rstrip(".").strip()


def teach_accepted(reply: str) -> bool:
    r = (reply or "").strip()
    return r.startswith("Saved:") or r == DUP_ACK


def run_case(case: dict, workdir: Path, markers: list[str]) -> dict:
    rec = {"id": case["id"], "family": case["family"],
           "confirm": bool(case.get("confirm", False)),
           "expected": case["expected"], "verdict": "OK",
           "teach_replies": [], "reply": "", "extracted": "",
           "stage": "", "reasons": []}
    if workdir.exists():
        import shutil
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        daemon = Loop132Daemon(
            str(workdir), cfg=dict(copy.deepcopy(DEFAULT_CONFIG132)))
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
                if not teach_accepted(reply):
                    rec["verdict"] = "HARNESS-ERROR"
                    rec["reasons"].append(
                        f"teach {i} rejected: {reply!r}")
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
    rec["extracted"] = extract_answer(reply)
    if exp == "abstain":
        if abst:
            rec["verdict"] = "OK"
        else:
            rec["verdict"] = "WRONG-ANSWER"
            rec["reasons"].append(
                f"confident reply where abstain sealed: {reply!r}")
    else:
        if norm(rec["extracted"]) == norm(exp) and norm(exp):
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


def main() -> int:
    suite = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    markers = suite["abstain_markers"]
    scratch = ART / "scratch143"
    t0 = time.time()
    rows: list[dict] = []
    for case in suite["cases"]:
        rec = run_case(case, scratch / case["id"], markers)
        rows.append(rec)
        print(f"{case['id']} [{case['family']}]: {rec['verdict']} "
              f"stage={rec['stage']} reply={rec['reply'][:90]!r}", flush=True)
    seconds = round(time.time() - t0, 1)
    (ART / "fable_redteam143_results.json").write_text(
        json.dumps({"seconds": seconds, "rows": rows}, indent=1,
                   ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print(f"done: {Counter(r['verdict'] for r in rows)} in {seconds} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
