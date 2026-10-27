#!/usr/bin/env python3
"""y1t-H1 runner (Answering-from-memory thread, 2026-09-26, for the wrong-as-fact thread's sealed marks,
artifacts/claude-y1tH1-20260926/PASSMARKS-y1t-H1.md). New file.

Answers every ask of a bank-format panel (turns.jsonl: life_id, turn_index, kind, user_text) with one model, in
y1t's registered answer config (y1t PLAN.md step 5, A1): every earlier user turn of the life in time order, y1f's L1
layout, one greedy answer, y1f's checks, "I don't know." when a check fails or the answer abstains. The same code runs
arm A (plain MiniCPM5-1B) and arm B (y1t's merged model). Writes one row per ask in the 336 runner's row format
({"life_id", "turn_index", "kind", "reply"}); prints counts only (the panel is TEST-ONLY: no item, answer or reply is
ever printed).

  python -B scripts/claude_y1t_h1run.py --model DIR --panel PANEL_DIR --out ROWS.jsonl
  python -B scripts/claude_y1t_h1run.py --selftest       (DEV bank, CPU fake model)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_y1d_readchat as Y  # noqa: E402  (sealed: load, all_rows, Gen, FALLBACK)
import claude_y1f_layout as F  # noqa: E402  (sealed: messages, checked)


def answer_a1(gen, text: str, rows: list[dict]) -> str:
    import claude_chat338_agent as C38
    if not rows:
        return Y.FALLBACK
    raw = C38.trim(gen.greedy_chat(F.messages("L1", text, rows)))
    known = C38._words([text] + [r["text"] for r in rows])
    return raw if F.checked(raw, text, known) is None else Y.FALLBACK


def run(gen, panel: str, out: Path, log=print) -> dict:
    turns = Y.load(Path(panel) / "turns.jsonl")
    lives = defaultdict(list)
    for t in turns:
        lives[t["life_id"]].append(t)
    n = sum(t["kind"] == "ask" for t in turns)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("", encoding="utf-8")
    c, k, t0 = Counter(), 0, time.time()
    for life_id in sorted(lives):
        life = sorted(lives[life_id], key=lambda t: t["turn_index"])
        for t in life:
            if t["kind"] != "ask":
                continue
            k += 1
            reply = answer_a1(gen, t["user_text"], Y.all_rows(t, life))
            c["fallback"] += reply == Y.FALLBACK
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"life_id": life_id, "turn_index": t["turn_index"], "kind": t["kind"],
                                     "reply": reply}, ensure_ascii=False) + "\n")
            if k % 20 == 0:
                log(f"[y1tH1] {k}/{n}")
    res = {"asks": k, "fallback_replies": c["fallback"], "minutes": round((time.time() - t0) / 60, 1)}
    return res


def selftest() -> None:
    import claude_y1g_doubt as G
    with tempfile.TemporaryDirectory() as d:
        res = run(G._FakeGen(), str(SCRIPTS.parent / Y.BANK), Path(d) / "rows.jsonl", log=lambda s: None)
        rows = Y.load(Path(d) / "rows.jsonl")
    assert res["asks"] == 71 == len(rows) and all(set(r) == {"life_id", "turn_index", "kind", "reply"} for r in rows)
    assert all(r["kind"] == "ask" for r in rows) and 0 <= res["fallback_replies"] <= 71
    assert answer_a1(G._FakeGen(), "q?", []) == Y.FALLBACK
    assert answer_a1(G._FakeGen(), "what's my dog called?", [{"id": 0, "text": "my dog is Rex", "said_at": None}]) \
        == "Rex."
    print("selftest ok")


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(json.dumps(run(Y.Gen(a.model), a.panel, Path(a.out), log=lambda s: print(s, flush=True))), flush=True)


if __name__ == "__main__":
    main()
