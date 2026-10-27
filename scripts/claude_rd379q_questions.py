#!/usr/bin/env python3
"""rd-379q: question notes (Trustworthy notes, 09-26). The plain MiniCPM5-1B (thinking off, greedy, no training) writes
up to 3 short questions that each turn answers; each question is stored as a note pointing to its own turn.

Why: rd-378's fact notes were 31% unsupported. A question states nothing, so it cannot store an untrue fact; answers
still come only from the original turns (Ben's design: notes are pointers to the raw chat). rd-379q measures whether
such pointers help find evidence across whole LoCoMo practice chats, with rd-378L's unchanged scorer and marks.

write:    python claude_rd379q_questions.py write --model BASE --dialogs DIALOGS.jsonl --out NOTES.jsonl
          DIALOGS = claude_rd378L_recall.py dialogs output (same as rd-378L); OUT rows use claude_rd378_write.py's
          format {"dialog","t","notes":[{"text","cites":[0],"when":null}],"raw","ms"}, so
          claude_rd378L_recall.py score reads them unchanged. Prints a progress line every 100 turns.
selftest: python claude_rd379q_questions.py selftest   (CPU, no model: prompt and parser)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HIST = 6          # earlier turns shown, as the rd-378 writer (claude_rd378_common.HIST)
MAXQ = 3
MAX_NEW = 96
QSYS = "You index a conversation so that it can be searched later."


def build_qprompt(date, earlier, latest):
    lines = [f"{t['speaker']}: {t['text'].strip()}" for t in earlier[-HIST:]]
    return (f"Date: {date or '(unknown)'}\nEarlier messages:\n" + ("\n".join(lines) if lines else "(none)") +
            f"\nLatest message ({latest['speaker']}): {latest['text'].strip()}\n\n"
            f"Write up to {MAXQ} short questions that the latest message answers, the way someone might ask them "
            "weeks later. Use names, not pronouns. Write only the questions, one per line.")


def parse_questions(raw):
    out = []
    for line in raw.splitlines():
        s = re.sub(r"^\s*(?:[-*•]|\d+[.):]|Q\d*[.):])\s*", "", line).strip().strip('"').strip()
        if s.endswith("?") and 3 <= len(s.split()) <= 30 and s.lower() not in {o.lower() for o in out}:
            out.append(s)
        if len(out) == MAXQ:
            break
    return out


def write(a):
    import claude_bm390 as B
    n = 0
    t0 = time.time()
    with open(a.out, "w", encoding="utf-8") as fh:
        for line in Path(a.dialogs).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            for k, t in enumerate(d["turns"]):
                if d["kind"] == "chat" and t["speaker"] == "assistant":
                    continue
                s = time.perf_counter()
                raw, _ = B.generate(a.model, QSYS, build_qprompt(d.get("date", ""), d["turns"][:k], t), MAX_NEW)
                qs = parse_questions(raw)
                fh.write(json.dumps({"dialog": d["dialog"], "t": t["t"],
                                     "notes": [{"text": q, "cites": [0], "when": None} for q in qs],
                                     "raw": raw, "ms": round((time.perf_counter() - s) * 1000, 1)},
                                    ensure_ascii=False) + "\n")
                n += 1
                if n % 100 == 0:
                    fh.flush()
                    print(json.dumps({"turns": n, "min": round((time.time() - t0) / 60, 1)}), flush=True)
    print(f"wrote questions for {n} turns", flush=True)


def selftest():
    ok = {}
    p = build_qprompt("8 May 2023", [{"speaker": "Wren", "text": "Hi!"}] * 8,
                      {"speaker": "Tobin", "text": "I adopted a dog named Pip last week."})
    ok["prompt_hist"] = p.count("Wren: Hi!") == HIST and "Latest message (Tobin): I adopted" in p
    ok["prompt_empty"] = "(none)" in build_qprompt("", [], {"speaker": "Wren", "text": "x"})
    raw = ("1. What is the name of Tobin's dog?\n- When did Tobin adopt Pip?\nTobin adopted a dog.\n"
           "Q3: What did Tobin adopt?\n4. Who is Pip?\n")
    ok["parse_numbered_bullets"] = parse_questions(raw) == [
        "What is the name of Tobin's dog?", "When did Tobin adopt Pip?", "What did Tobin adopt?"]
    ok["parse_skips_statements"] = parse_questions("Tobin adopted a dog.\nNothing else.") == []
    ok["parse_dedup_and_short"] = parse_questions("Why?\nWhat did Tobin adopt?\nwhat did tobin adopt?") == [
        "What did Tobin adopt?"]
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD379Q-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "selftest"])
    ap.add_argument("--model")
    ap.add_argument("--dialogs")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest()
    write(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
