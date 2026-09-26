#!/usr/bin/env python3
"""rd-378u: does rd-378L's notes gain hold on UNSEEN LoCoMo practice chats, through the store the build would use?
(Trustworthy notes thread, 2026-09-26.) Development measurement on LoCoMo PRACTICE ("after using LoCoMo for
development"); nothing is trained on it and no question, answer, turn or note text is printed.

A = store v3 (claude_ep382_store_v3, what 0.2c ships), heard rows only, recall() with its defaults.
B = store v4 (claude_ep382_store_v4), heard rows + the rd-378 writer's notes, recall() with its defaults: notes are
    ranked with the heard rows and resolved to the raw lines they cite; only heard rows come back.
Both return raw lines only, one row per turn, so found@k compares the same number of lines shown. Stores are built
exactly as rd-378L's scorer builds them (claude_rd378L_recall.build_store: same rows, same note pointers).

score:    python claude_rd378u_confirm.py score --data DATA --convs 5-9 --notes NOTES.jsonl --out OUT_DIR
          writes notes_confirm.json (counts), ranked_turns.jsonl (per question and store, the first 20 line positions,
          positions only) and per_question.jsonl (keep private). Prints one JSON line of counts.
selftest: python claude_rd378u_confirm.py selftest   (CPU, BM25, no model)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ep382_store_v3 as V3  # noqa: E402
import claude_ep382_store_v4 as V4  # noqa: E402
import claude_rd378L_recall as R  # noqa: E402

KS = (5, 10, 20)
ARMS = (("A", V3, False), ("B", V4, True))


def build(module, d, turns, notes, with_notes):
    R.M = module
    return R.build_store(d, turns, notes, with_notes)


def score(a):
    notes, nc = R.note_rows(a.notes)
    rows, ranked = [], []
    for conv in R.load(a.data, R.conv_range(a.convs)):
        turns = R.chat_turns(conv)
        pos = {dia: p for _s, _d, p, dia, _spk, _t in turns}
        for arm, module, with_notes in ARMS:
            with tempfile.TemporaryDirectory() as d:
                s = build(module, d, turns, notes.get(conv["sample_id"], []), with_notes)
                for i, qa in enumerate(conv["qa"]):
                    ev = {pos[e] for e in qa.get("evidence", []) if e in pos}
                    if not ev or qa["category"] not in (1, 2, 3, 4):
                        continue
                    hits = s.recall(qa["question"], k=max(KS))
                    if any(h["source"] != "heard" for h in hits):
                        raise SystemExit("a recall() default returned a non-heard row")
                    r = {"qid": f"{conv['sample_id']}#{i}", "cat": qa["category"], "arm": arm,
                         "lines@10": len(hits[:10]), "via_note@10": sum(1 for h in hits[:10] if h.get("via"))}
                    for k in KS:
                        got = set().union(*[h["turn_ids"] for h in hits[:k]]) if hits else set()
                        r[f"any@{k}"] = int(bool(ev & got))
                        r[f"all@{k}"] = int(ev <= got)
                    rows.append(r)
                    ranked.append({"qid": r["qid"], "arm": arm, "turns": [h["turn_ids"][0] for h in hits]})
    summary = {}
    for arm, _m, _w in ARMS:
        for cat in ("1", "2", "3", "4", "1-4"):
            sel = [r for r in rows if r["arm"] == arm and (cat == "1-4" or str(r["cat"]) == cat)]
            s = {"questions": len(sel)}
            for key in [f"{kind}@{k}" for kind in ("any", "all") for k in KS] + ["lines@10", "via_note@10"]:
                s[key] = sum(r[key] for r in sel)
            summary[f"{arm}:{cat}"] = s
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"label": "after using LoCoMo for development", "convs": a.convs, "notes": nc, "summary": summary}
    (out / "notes_confirm.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    (out / "ranked_turns.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ranked), encoding="utf-8")
    (out / "per_question.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"notes": nc, "A:1-4": summary["A:1-4"], "B:1-4": summary["B:1-4"]}))


def selftest(_a):
    conv = {"sample_id": "x", "qa": [], "conversation": {"session_1_date_time": "1 May 2023", "session_1": [
        {"speaker": "Wren", "dia_id": "D1:1", "text": "I moved to Oakvale in May."},
        {"speaker": "Tobin", "dia_id": "D1:2", "text": "Nice, my dog Pip loves the beach."},
        {"speaker": "Wren", "dia_id": "D1:3", "text": "The library there hired me."}]}}
    turns = R.chat_turns(conv)
    note = [(2, "x#0", {"text": "Wren works at the Oakvale library.", "cites": [0]})]
    ok = {}
    with tempfile.TemporaryDirectory() as d:
        a = build(V3, d + "/a", turns, note, False)
        b = build(V4, d + "/b", turns, note, True)
        ok["A is v3, B is v4"] = type(a) is V3.MemoryStore and type(b) is V4.MemoryStore
        ha = a.recall("Where does Wren work?", k=3, mode="bm25")
        hb = b.recall("Where does Wren work?", k=3, mode="bm25")
        ok["heard rows only"] = all(h["source"] == "heard" for h in ha + hb)
        ok["B reaches the line through the note"] = hb[0]["turn_ids"] == [2] and hb[0].get("via") == "n0000001"
        ok["one row per line"] = len({h["id"] for h in hb}) == len(hb) == 3
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD378U-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["score", "selftest"])
    ap.add_argument("--data")
    ap.add_argument("--convs", default="5-9")
    ap.add_argument("--notes")
    ap.add_argument("--out")
    a = ap.parse_args()
    return {"score": score, "selftest": selftest}[a.mode](a) or 0


if __name__ == "__main__":
    sys.exit(main())
