#!/usr/bin/env python3
"""GLM-written instruction frames for Fix-sleep's training runs (Fix-sleep thread, 2026-09-26).

Ben chose "Use GLM" (16:39 UTC 09-26): nothing a model trains on, inputs included, may be written by Claude. The number
puzzle instruction (claude_blurt1.puzzle_prompt) and dl-7's answer suffix were Claude-written. This asks GLM 5.3 Flash
(OpenRouter, Mac only) to write them; code only checks the form and picks, it never edits the text.

  puzzle frame: must contain {NUMS} and {TARGET} exactly once each, no other braces, 40-300 characters.
  answer suffix: 2-60 characters, one line, no braces, no digits.
Five candidates each at temperature 0.7, asked one at a time; the FIRST candidate that passes the check is chosen.
Output: DIR/frames.json with every candidate, the check result and the chosen text. Standard library only.
The request text below is Claude-written; it is never trained on (like dl-3's asking prompts). Only GLM's reply is used.

  python -B scripts/claude_glm_frames.py selftest
  python -B scripts/claude_glm_frames.py write --out DIR [--model M]
Key rules: the key is read from ~/.config/openrouter/key into memory by claude_k1e_teacher's caller pattern; never
printed, logged or written.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_k1e_teacher as T  # noqa: E402

N_CAND = 5
ASK_PUZZLE = ("Write one instruction for a number puzzle. The reader gets some numbers and a target number. They must "
              "use each number exactly once, with + - * / and brackets, to make the target, and reply with only the "
              "arithmetic expression, nothing else. Write the placeholder {NUMS} where the numbers go and {TARGET} "
              "where the target goes, each exactly once. Reply with the instruction only, on one line.")
ASK_SUFFIX = ("Write a very short instruction, a few words, that could be added after a quiz question to ask for only "
              "the answer and nothing else. Reply with the instruction only, on one line.")


def clean(t: str) -> str:
    t = (t or "").strip().split("\n")[0].strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'`":
        t = t[1:-1].strip()
    return t


def ok_puzzle(t: str) -> bool:
    return (t.count("{NUMS}") == 1 and t.count("{TARGET}") == 1 and 40 <= len(t) <= 300
            and len(re.findall(r"[{}]", t)) == 4)


def ok_suffix(t: str) -> bool:
    return 2 <= len(t) <= 60 and not re.search(r"[{}\d]", t)


def write(a, key) -> None:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"model": a.model, "temperature": 0.7, "n_candidates": N_CAND}
    for name, ask, check in (("puzzle", ASK_PUZZLE, ok_puzzle), ("suffix", ASK_SUFFIX, ok_suffix)):
        cands = []
        for i in range(N_CAND):
            txt, use = T.call(key, a.model, ask, 0.7)
            c = clean(txt)
            cands.append({"i": i, "raw": txt, "text": c, "ok": check(c), "usage": use})
            print(f"[glm-frames] {name} {i}: ok={check(c)} {c[:160]!r}", flush=True)
        pick = next((c["text"] for c in cands if c["ok"]), None)
        res[name] = {"candidates": cands, "chosen": pick}
    (out / "frames.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"puzzle": res["puzzle"]["chosen"], "suffix": res["suffix"]["chosen"]}, ensure_ascii=False))


def selftest() -> None:
    assert ok_puzzle("Use every number in {NUMS} once with + - * / and brackets to reach {TARGET}. Reply with only "
                     "the expression.")
    assert not ok_puzzle("Use {NUMS} to reach {TARGET} {TARGET} with + - * / and brackets, expression only.")
    assert not ok_puzzle("Use the numbers to reach the target with + - * / and brackets, expression only please.")
    assert ok_suffix("Answer only, please.") and not ok_suffix("Reply in 3 words.")
    assert clean('"Just the answer."\nextra') == "Just the answer."
    print("glm frames selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["selftest", "write"])
    ap.add_argument("--out", default="")
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest()
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    try:
        write(a, key)
    finally:
        del key


if __name__ == "__main__":
    main()
