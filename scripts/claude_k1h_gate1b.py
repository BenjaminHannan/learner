#!/usr/bin/env python3
"""k1h gate 1, with list numbers not counted as sentences (Creative answers in chat thread, 2026-09-27; k1h ADDENDUM-6,
DRAFT until sealed).

Why: the sealed gate 1 (claude_k1h_train.gate1) splits an answer into sentences at ". ", so each item marker of a
numbered list ("1.", "2.", "3.") becomes a "sentence". In the Luna pilot, "1." was in 14 of 39 kept answers (bar: 1),
and in GLM's 240 k1e answers "2." was in 72 of 225 (bar: 4.5). Any teacher that numbers its ideas fails the sentence
bar, whatever else it writes. Counting only pieces that contain a letter, the most repeated sentence is in 1 of 39
(Luna) and 3 of 225 (GLM).
The one change: a piece counts as a sentence only if it contains a letter (a to z, after lowercasing). The openings
rule, both bars (25% and 2%), the splitter and the "kept answers" input are claude_k1h_train's, unchanged.
Prints counts and the top openings only, never an answer.
  python3 -B scripts/claude_k1h_gate1b.py --kept KEPT.jsonl [--by-writer]
  python3 -B scripts/claude_k1h_gate1b.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_k1h_train as TR      # noqa: E402  (its gate constants, opening() and sentences())

WRITERS = {"kt-": "glm-k1e", "kh-": "glm-k1h", "kl-": "luna"}      # as in claude_k1h_luna.WRITERS


def sentences_b(a: str) -> set:
    return {s for s in TR.sentences(a) if re.search(r"[a-z]", s)}


def gate1b(answers: list) -> dict:
    n = len(answers)
    op = Counter(TR.opening(a) for a in answers)
    se = Counter(s for a in answers for s in sentences_b(a))
    top_o = op.most_common(1)[0] if op else ("", 0)
    top_s = se.most_common(1)[0][1] if se else 0
    return {"answers": n, "top_openings": op.most_common(8), "top_opening_share": round(top_o[1] / max(1, n), 3),
            "top_sentence_count": top_s, "top_sentence_share": round(top_s / max(1, n), 3),
            "pass": n > 0 and top_o[1] <= TR.FRAME_OPEN_SHARE * n and top_s <= max(1.0, TR.FRAME_SENT_SHARE * n)}


def writer_of(item_id: str) -> str:
    return next((w for p, w in WRITERS.items() if item_id.startswith(p)), "unknown")


def selftest() -> None:
    a = ["Here you go:\n1. Make a card. 2. Bake a cake. 3. Sing a song.",
         "1. Plant a tree. 2. Paint a mug. 3. Write a poem.",
         "Try these. 1. Tidewater. 2. Loom. 3. Ember Street.",
         "What fun! 1. Fly a kite. 2. Bake bread. 3. Swim."]         # 4 different openings: the openings rule passes
    old = TR.gate1(a)
    new = gate1b(a)
    assert old["top_sentence_count"] == 4 and not old["pass"], old          # "1." is in all four
    assert new["top_sentence_count"] == 1 and new["pass"], new              # every real sentence is unique
    same = ["Happy birthday, Wren! 1. Cake.", "Happy birthday, Wren! 1. Kite.", "Happy birthday, Wren! 1. Boat."]
    assert gate1b(same)["top_sentence_count"] == 3 and not gate1b(same)["pass"], "a real repeated sentence still fails"
    assert gate1b(a)["top_opening_share"] == old["top_opening_share"], "openings rule unchanged"
    assert writer_of("kl-a0001") == "luna" and writer_of("kt-001") == "glm-k1e" and writer_of("kh-0001") == "glm-k1h"
    print("k1h gate1b selftest 1/1 ok")


def main() -> None:
    if sys.argv[1:2] == ["selftest"]:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("--kept", required=True)
    ap.add_argument("--by-writer", action="store_true")
    a = ap.parse_args()
    kept = [json.loads(x) for x in Path(a.kept).read_text(encoding="utf-8").splitlines() if x.strip()]
    res = {"gate1b": gate1b([k["answer"] for k in kept])}
    if a.by_writer:
        by: dict = {}
        for k in kept:
            by.setdefault(writer_of(k["item_id"]), []).append(k["answer"])
        res["gate1b_by_writer"] = {w: {kk: g[kk] for kk in ("answers", "top_opening_share", "top_sentence_count",
                                                            "top_sentence_share", "pass")}
                                   for w, g in ((w, gate1b(v)) for w, v in sorted(by.items()))}
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
