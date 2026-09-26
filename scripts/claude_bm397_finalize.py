#!/usr/bin/env python3
"""bm-397 (benchmarks thread, 2026-09-26): a copy-only answer finaliser on replies that already exist.

The frozen plain MiniCPM5-1B (greedy, thinking off) sees only the question and one arm's existing reply (the draft),
never the gold, the chat or any evidence. It writes the shortest answer using only words from the draft. Code then
enforces "copy only": if any word of the new answer is not in the draft, or the draft abstains, or the new answer
is empty, the draft is kept unchanged. Nothing is trained. See artifacts/claude-bm397-20260926/PLAN.md.

  python -B scripts/claude_bm397_finalize.py run --data DATA --runs DIR --arms T,E20 --model BASE --out OUT
  python -B scripts/claude_bm397_finalize.py selftest

Writes OUT/locomo_<arm>F.jsonl (same rows and fields as the draft file, reply replaced when allowed, plus
"final_kept": why the draft was kept or "changed"). Counts only are printed; nothing is quoted.
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

SYSTEM397 = "You shorten answers. You never add information."
PROMPT397 = ("Question: {q}\nDraft answer: {d}\n\nWrite the shortest answer to the question that uses only words "
             "from the draft answer. Keep every name, date, number and list item the question needs. If the draft "
             "does not answer the question, says it does not know, or gives more than one possible answer, write "
             "the draft unchanged.\nShort answer:")
MAX_NEW397 = 32
WORD = re.compile(r"[a-z0-9]+")


def words(s: str) -> list[str]:
    return WORD.findall(s.lower())


def finalise(question: str, draft: str, gen) -> tuple[str, str]:
    """Return (reply, reason). reason is "changed" or why the draft was kept."""
    d = " ".join(x.strip() for x in draft.split("\n") if x.strip())
    if not d:
        return draft, "empty_draft"
    if SC.ABSTAIN.search(d.lower()):
        return draft, "abstains"
    out = gen(SYSTEM397, PROMPT397.format(q=question.strip(), d=d))
    lines = [x.strip() for x in out.split("\n") if x.strip()]
    new = lines[0] if lines else ""
    if not words(new):
        return draft, "empty_final"
    if Counter(words(new)) - Counter(words(d)):
        return draft, "not_copy"
    if words(new) == words(d):
        return draft, "same"
    return new, "changed"


def run(a) -> None:
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    qs = {f"{c['sample_id']}#{i}": qa for c in lc for i, qa in enumerate(c["qa"])}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    def gen(system: str, user: str) -> str:
        return B.generate(a.model, system, user, MAX_NEW397)[0]

    for arm in a.arms.split(","):
        rows = [json.loads(x) for x in (Path(a.runs) / f"locomo_{arm}.jsonl").read_text(encoding="utf-8").splitlines()
                if x.strip()]
        res, reasons, t0 = [], Counter(), time.time()
        for r in rows:
            r2 = dict(r)
            if r["category"] in (1, 2, 3, 4):
                r2["reply"], why = finalise(qs[r["qid"]]["question"], r["reply"], gen)
            else:
                why = "category_5_untouched"
            r2["final_kept"] = why
            reasons[why] += 1
            res.append(r2)
        with open(out / f"locomo_{arm}F.jsonl", "w", encoding="utf-8", newline="\n") as fh:
            for r2 in res:
                fh.write(json.dumps(r2, ensure_ascii=False) + "\n")
        print(json.dumps({"arm": arm + "F", "rows": len(res), "reasons": dict(reasons),
                          "seconds": round(time.time() - t0, 1)}), flush=True)


def selftest() -> None:
    ok = 0

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'} {name}")
        ok += int(cond)

    q = "Where did Mara go in June?"
    check("shortens a copy", finalise(q, "Mara went to the lake near Oslo in June.", lambda s, u: "the lake near Oslo")
          == ("the lake near Oslo", "changed"))
    check("refuses new words", finalise(q, "Mara went to the lake in June.", lambda s, u: "Lake Tahoe")
          == ("Mara went to the lake in June.", "not_copy"))
    check("keeps an abstaining draft", finalise(q, "I don't know.", lambda s, u: "know")[1] == "abstains")
    check("keeps on empty output", finalise(q, "The lake.", lambda s, u: "\n\n")[1] == "empty_final")
    check("counts repeats", finalise(q, "the lake", lambda s, u: "the the lake")[1] == "not_copy")
    check("same words kept as same", finalise(q, "The lake.", lambda s, u: "the lake")[1] == "same")
    check("uses first output line", finalise(q, "Mara went to the lake.", lambda s, u: "the lake\nextra words")
          == ("the lake", "changed"))
    print(f"BM397-SELFTEST {'PASS' if ok == 7 else 'FAIL'} {ok}/7")
    if ok != 7:
        raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest"])
    ap.add_argument("--data", default="")
    ap.add_argument("--runs", default="")
    ap.add_argument("--arms", default="T,E20")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        import os
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        run(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
