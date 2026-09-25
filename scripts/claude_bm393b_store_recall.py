#!/usr/bin/env python3
"""bm-393b: evidence recall through the ep-382 store's recall() on LoCoMo practice (benchmarks thread, 2026-09-25).
New file only. $0, CPU, no language model; development measurement, labelled "after using LoCoMo for development".
Nothing is trained on LoCoMo; no question, answer or turn text is printed or written.

For each chat: a fresh MemoryStore in a temp folder; every turn is remembered as source="heard", word for word
(an image turn adds " [shared <caption>]"), speaker = the LoCoMo speaker, turn_ids = [position in the chat],
said_at = the session's date as LoCoMo gives it. For each question (the bare question text), recall(k=20) in three
modes (fused, minilm, bm25); an evidence turn is found if its position is in the top k.

  python -B scripts/claude_bm393b_store_recall.py selftest
  python -B scripts/claude_bm393b_store_recall.py run --data DATA --out artifacts/claude-bm393b-20260925
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402
import claude_ep382_store as M  # noqa: E402

MODES = ("fused", "minilm", "bm25")
KS = (5, 10, 20)
T0 = "2026-09-25T00:00:00+00:00"


def selftest() -> int:
    ok = {}
    with tempfile.TemporaryDirectory() as d:
        s = M.MemoryStore(d)
        a = s.remember("I moved to Oakvale in May.", source="heard", speaker="Wren", turn_ids=[1], said_at="2023-05-08",
                       logged_at=T0)
        b = s.remember("My dog Pip loves the beach.", source="heard", speaker="Tobin", turn_ids=[2],
                       said_at="2023-06-01", logged_at=T0)
        c = s.remember("Wren moved to Oakvale in May.", source="note", speaker="Wren", turn_ids=[1],
                       said_at="2023-05-08", logged_at=T0)
        ok["ids"] = (a, b, c) == ("h0000001", "h0000002", "n0000001")
        again = M.MemoryStore(d)
        ok["reload"] = [r["id"] for r in again.rows] == [a, b, c]
        d_id = again.remember("Actually Pip is a cat.", source="heard", speaker="Tobin", turn_ids=[3],
                              said_at="2023-06-02", logged_at=T0)
        ok["append_after_reload"] = d_id == "h0000003" and len(M.MemoryStore(d).rows) == 4
        top = again.recall("Where did Wren move?", k=2)
        ok["recall_finds"] = top[0]["turn_ids"] == [1] and "score" in top[0]
        ok["sources"] = all(r["source"] == "heard" for r in again.recall("Wren", k=4, sources={"heard"}))
        ok["before"] = [r["id"] for r in again.recall("dog", k=4, before="2023-06-01")] in (["h0000001", "n0000001"],
                                                                                        ["n0000001", "h0000001"])
        ok["modes"] = all(len(again.recall("Pip", k=3, mode=m)) == 3 for m in MODES)
        raw = (Path(d) / "memory382" / "entries.jsonl").read_bytes()
        ok["append_only_lf"] = raw.count(b"\n") == 4 and b"\r\n" not in raw
        try:
            again.remember("x", source="dream", speaker="", turn_ids=[], said_at=None, logged_at=T0)
            ok["rejects_bad_source"] = False
        except ValueError:
            ok["rejects_bad_source"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("EP382-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def run(data: Path, out: Path) -> int:
    lc = json.loads((data / "locomo10.json").read_text(encoding="utf-8"))
    rows = []
    for conv in lc:
        cid = conv["sample_id"]
        with tempfile.TemporaryDirectory() as d:
            s = M.MemoryStore(d)
            pos = {}
            for date, turns in B.sessions(conv):
                for t in turns:
                    text = t["text"] + (f" [shared {t['blip_caption']}]" if t.get("blip_caption") else "")
                    p = len(pos)
                    pos[t.get("dia_id")] = p
                    s.remember(text, source="heard", speaker=t["speaker"], turn_ids=[p], said_at=date, logged_at=T0)
            for i, qa in enumerate(conv["qa"]):
                ev = {pos[e] for e in qa.get("evidence", []) if e in pos}
                r = {"qid": f"{cid}#{i}", "cat": qa["category"], "n_ev": len(ev)}
                if ev:
                    for mode in MODES:
                        got = [h["turn_ids"][0] for h in s.recall(qa["question"], k=max(KS), mode=mode)]
                        for k in KS:
                            top = set(got[:k])
                            r[f"{mode}_any@{k}"] = int(bool(ev & top))
                            r[f"{mode}_all@{k}"] = int(ev <= top)
                rows.append(r)
    summary = {}
    for cat in ("1", "2", "3", "4", "1-4"):
        sel = [r for r in rows if r["n_ev"] and (str(r["cat"]) == cat or (cat == "1-4" and r["cat"] in (1, 2, 3, 4)))]
        s = {"questions": len(sel)}
        for mode in MODES:
            for k in KS:
                for kind in ("any", "all"):
                    key = f"{mode}_{kind}@{k}"
                    s[key] = round(100 * sum(r[key] for r in sel) / max(1, len(sel)), 1)
        summary[cat] = s
    out.mkdir(parents=True, exist_ok=True)
    (out / "store_recall.json").write_text(json.dumps({"label": "after using LoCoMo for development",
                                                       "summary": summary}, indent=1), encoding="utf-8")
    (out / "store_recall_per_question.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows),
                                                         encoding="utf-8")
    print(json.dumps({"1-4": summary["1-4"]}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    if len(sys.argv) >= 2 and sys.argv[1] == "run":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--data", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args()
        sys.exit(run(Path(a.data), Path(a.out)))
    raise SystemExit("usage: claude_bm393b_store_recall.py selftest | run --data DATA --out OUT")
