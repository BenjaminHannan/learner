#!/usr/bin/env python3
"""bm-395, ep-382's answering test (benchmarks thread, 2026-09-25): the plain MiniCPM5-1B answers LoCoMo
questions from the chat lines the shared memory store recalls, against bm-390's Rb arm (the same model shown
the 10 lines BM25 ranks highest). Plan and pass mark: artifacts/claude-bm395-20260925/PLAN.md.
New file only. Development measurement on LoCoMo practice, labelled "after using LoCoMo for development".
Nothing is trained; no question, answer or reply text is printed.

One change against Rb: WHICH turns are shown. Everything else is bm-390's sealed code, called unchanged:
the system prompt, the conversation header, the "DATE: / CONVERSATION:" layout with sessions in time order,
each turn as '<speaker> said, "<text>"' (claude_bm390.turn_text), the QA prompt, the category-2 date hint and
category-5 options (claude_bm390.question_text), greedy decoding, 50 new tokens, thinking off
(claude_bm390.generate). The store is scripts/claude_ep382_store_v2.py, used as bm-393c used it: a fresh store
per chat; every turn remembered as "heard", word for word (an image turn adds " [shared <caption>]"), speaker,
turn_ids = [position in the chat], said_at = the session date. The query is the question exactly as the model
is asked it (question_text), which is also Rb's BM25 query; recall() uses its default mode (fused).

One store build serves several k: recall(k = max k) once, the first k lines go to arm k (fused ranking is a
fixed sort, so its top 10 is the first 10 of its top 20). Rows add "turns": the recalled positions in rank
order (numbers only).

  python -B scripts/claude_bm395_store_answer.py selftest [--data DATA]
  python -B scripts/claude_bm395_store_answer.py locomo --data DATA --model BASE --ks 10,20 --names E,E20 --out OUT
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402
import claude_ep382_store_v2 as M  # noqa: E402

T0 = "2026-09-25T00:00:00+00:00"
CPU_THREADS = 8          # MiniLM runs on the CPU; the rent kit sets OMP_NUM_THREADS=1, which only slows it


def build_store(conv: dict, state_dir: str):
    """Fresh store for one chat. Returns (store, items) with items[position] = (session_index, date, turn)."""
    s = M.MemoryStore(state_dir)
    items = []
    for si, (date, turns) in enumerate(B.sessions(conv)):
        for t in turns:
            text = t["text"] + (f" [shared {t['blip_caption']}]" if t.get("blip_caption") else "")
            p = len(items)
            items.append((si, date, t))
            s.remember(text, source="heard", speaker=t["speaker"], turn_ids=[p], said_at=date, logged_at=T0)
    return s, items


def store_context(conv: dict, items: list, positions: list[int]) -> str:
    """The recalled turns laid out exactly as claude_bm390.bm25_context lays out its top k."""
    out = B.start_text(conv)
    cur = None
    for p in sorted(set(positions)):
        si, date, t = items[p]
        if si != cur:
            out += "\nDATE: " + date + "\n" + "CONVERSATION:\n"
            cur = si
        out += B.turn_text(t) + "\n"
    return out


def selftest(data: Path | None) -> int:
    ok = {}
    sets = [("smoke", B.load_locomo(B.EXP / "smoke", ""))]
    if data is not None:
        sets.append(("locomo", B.load_locomo(data, "")))
    for label, convs in sets:
        same, n = True, 0
        for conv in convs:
            with tempfile.TemporaryDirectory() as d:
                s, items = build_store(conv, d)
                # every turn shown -> identical to bm390's BM25 layout with k = every turn
                if store_context(conv, items, list(range(len(items)))) != B.bm25_context(conv, "x", k=len(items)):
                    same = False
                ok[f"{label}_rows_match_turns"] = ok.get(f"{label}_rows_match_turns", True) and len(s.rows) == len(items)
                q = B.question_text(conv["sample_id"], 0, conv["qa"][0])
                top20 = [h["turn_ids"][0] for h in s.recall(q, k=20)]
                top10 = [h["turn_ids"][0] for h in s.recall(q, k=10)]
                ok[f"{label}_top10_is_prefix"] = ok.get(f"{label}_top10_is_prefix", True) and top20[:10] == top10
                n += 1
        ok[f"{label}_layout_identical_to_bm25_context"] = same and n > 0
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM395-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def run(args) -> int:
    import torch
    torch.set_num_threads(max(1, min(CPU_THREADS, os.cpu_count() or 1)))
    ks = [int(x) for x in args.ks.split(",")]
    names = args.names.split(",")
    assert len(ks) == len(names) and len(set(names)) == len(names)
    convs = B.load_locomo(Path(args.data), args.convs)
    rows = {n: [] for n in names}
    for conv in convs:
        cid = conv["sample_id"]
        t_build = time.time()
        with tempfile.TemporaryDirectory() as d:
            s, items = build_store(conv, d)
            for i, qa in enumerate(conv["qa"][: args.limit_q or None]):
                qtext = B.question_text(cid, i, qa)
                t0 = time.time()
                ranked = [h["turn_ids"][0] for h in s.recall(qtext, k=max(ks))]
                rec_ms = (time.time() - t0) * 1000
                for k, name in zip(ks, names):
                    t1 = time.time()
                    user = store_context(conv, items, ranked[:k]) + "\n\n" + B.QA_PROMPT.format(qtext)
                    reply, n = B.generate(args.model, B.LOCOMO_SYSTEM, user, B.ANS_TOKENS)
                    rows[name].append({"qid": f"{cid}#{i}", "category": qa["category"], "reply": reply,
                                       "ms": round((time.time() - t1) * 1000 + rec_ms, 1), "prompt_tokens": n,
                                       "turns": ranked[:k]})
        print(f"[bm395] {cid} store_rows={len(items)} questions={len(rows[names[0]])} "
              f"seconds={time.time() - t_build:.0f}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        B._write(out / B.fname("locomo", name, args.part), rows[name])
        print(f"wrote {B.fname('locomo', name, args.part)} rows={len(rows[name])} convs={len(convs)}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest", "locomo"])
    ap.add_argument("--data", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--ks", default="10,20")
    ap.add_argument("--names", default="E,E20")
    ap.add_argument("--out", default="")
    ap.add_argument("--convs", default="")
    ap.add_argument("--part", default="")
    ap.add_argument("--limit-q", type=int, default=0, help="smoke tests only")
    a = ap.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if a.cmd == "selftest":
        return selftest(Path(a.data) if a.data else None)
    if not (a.data and a.model and a.out):
        raise SystemExit("bm395: --data, --model and --out are required")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
