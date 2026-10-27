#!/usr/bin/env python3
"""bm-397g (benchmarks thread, 2026-09-26): does the sealed bm-397 finaliser hurt general answers?

Ben's goal for problem #4 says the trim step must cause no drop on GSM8K or MMLU. This applies the sealed
finalise() from scripts/claude_bm397_finalize.py, unchanged, to the plain 1B's existing bm-390 run2 replies on the
300 GSM8K and 300 MMLU items (gsm8k_T, mmlu_T). The "question" the finaliser sees is the exact user message the
plain 1B answered (claude_bm390.general_prompt). Nothing is trained; the gold is used only to score. Counts only.
See artifacts/claude-bm397-20260926/AMEND-general.md.

  python -B scripts/claude_bm397g_general.py run --data DATA --runs DIR --model BASE --out OUT
  python -B scripts/claude_bm397g_general.py score --data DATA --runs DIR --out OUT

run writes OUT/gsm8k_TF.jsonl and OUT/mmlu_TF.jsonl (the draft rows with the reply replaced when allowed, plus
"final_kept"). score checks that T reproduces bm-390's 191 and 50, then prints the marks G1 and G2.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm390_score as SC  # noqa: E402
import claude_bm397_finalize as F  # noqa: E402

TASKS = ("gsm8k", "mmlu")
T_RIGHT = {"gsm8k": 191, "mmlu": 50}      # bm-390 run2, sealed scorer
STRICT = re.compile(r"(?i)answer is\s*[:\$]?\s*(-?\d[\d,]*(?:\.\d+)?)")


def _rows(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _items(data: Path, task: str) -> dict:
    return {r["qid"]: r for r in _rows(data / f"{task}300.jsonl")}


def run(a) -> None:
    import os
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    def gen(system: str, user: str) -> str:
        return B.generate(a.model, system, user, F.MAX_NEW397)[0]

    for task in TASKS:
        items = _items(Path(a.data), task)
        res, reasons, t0 = [], Counter(), time.time()
        for r in _rows(Path(a.runs) / f"{task}_T.jsonl"):
            r2 = dict(r)
            r2["reply"], why = F.finalise(B.general_prompt(task, items[r["qid"]]), r["reply"], gen)
            r2["final_kept"] = why
            reasons[why] += 1
            res.append(r2)
        with open(out / f"{task}_TF.jsonl", "w", encoding="utf-8", newline="\n") as fh:
            for r2 in res:
                fh.write(json.dumps(r2, ensure_ascii=False) + "\n")
        print(json.dumps({"task": task, "arm": "TF", "rows": len(res), "reasons": dict(reasons),
                          "seconds": round(time.time() - t0, 1)}), flush=True)


def _strict_right(data: Path, rows: list[dict]) -> int:
    items = _items(data, "gsm8k")
    n = 0
    for r in rows:
        m = STRICT.findall(r["reply"])
        n += int(bool(m) and abs(float(m[-1].replace(",", "")) - float(items[r["qid"]]["gold"])) < 1e-6)
    return n


def score(a) -> None:
    data = Path(a.data)
    verdict = {}
    for task in TASKS:
        t_rows = _rows(Path(a.runs) / f"{task}_T.jsonl")
        f_rows = _rows(Path(a.out) / f"{task}_TF.jsonl")
        t = SC.score_general(data, task, t_rows)
        f = SC.score_general(data, task, f_rows)
        if t["summary"]["right"] != T_RIGHT[task]:
            raise SystemExit(f"bm397g: BASELINE-MISMATCH {task} T right {t['summary']['right']} != {T_RIGHT[task]}")
        if sorted(r["qid"] for r in f_rows) != sorted(r["qid"] for r in t_rows):
            raise SystemExit(f"bm397g: ROWS-MISMATCH {task}")
        lost = sum(1 for q in t["per"] if t["per"][q] and not f["per"][q])
        gained = sum(1 for q in t["per"] if f["per"][q] and not t["per"][q])
        words = lambda rows: sorted(len(r["reply"].split()) for r in rows)  # noqa: E731
        med = lambda v: v[len(v) // 2] if v else 0  # noqa: E731
        mark = "G1" if task == "gsm8k" else "G2"
        ok = f["summary"]["right"] >= t["summary"]["right"]
        verdict[mark] = ok
        line = {"task": task, "T_right": t["summary"]["right"], "TF_right": f["summary"]["right"], "lost": lost,
                "gained": gained, "reasons": dict(Counter(r.get("final_kept") for r in f_rows)),
                "median_words_T": med(words(t_rows)), "median_words_TF": med(words(f_rows)),
                mark: "PASS" if ok else "FAIL"}
        if task == "gsm8k":
            line["strict_T_right"] = _strict_right(data, t_rows)
            line["strict_TF_right"] = _strict_right(data, f_rows)
        print(json.dumps(line), flush=True)
    print(json.dumps({"no_drop": "PASS" if all(verdict.values()) else "FAIL", **{k: "PASS" if v else "FAIL"
                                                                                 for k, v in verdict.items()}}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "score"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--runs", required=True, help="folder holding bm-390 run2 gsm8k_T.jsonl and mmlu_T.jsonl")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run(a) if a.cmd == "run" else score(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
