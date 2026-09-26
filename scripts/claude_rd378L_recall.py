#!/usr/bin/env python3
"""rd-378L: do the note writer's notes help find evidence across a WHOLE multi-session chat? (reading thread, 09-26)
Development measurement on LoCoMo PRACTICE ("after using LoCoMo for development"): nothing is trained on LoCoMo and no
question, answer, turn or note text is printed. rd-378's own finding test searched inside one 12-16 turn dialog, where
top 10 is most of the dialog; this one searches a whole LoCoMo chat (hundreds of turns, many sessions).

dialogs: python claude_rd378L_recall.py dialogs --data DATA --convs 0-4 --out DIALOGS.jsonl
         one writer dialog per LoCoMo session: {"dialog": "<sample_id>#<session>", "kind": "overheard", "speakers",
         "date", "turns": [{"t", "speaker", "text"}]} with t = the turn's position in the whole chat and text as the
         ep-382 store keeps it (text + " [shared <caption>]"). Feed it to claude_rd378_write.py.
score:   python claude_rd378L_recall.py score --data DATA --convs 0-4 --notes NOTES.jsonl --out OUT_DIR [--modes fused,bm25]
         per chat, one ep-382 MemoryStore: every turn as source "heard" (exactly bm-393b's rows), plus every note as
         source "note" with turn_ids = its cited turns (cites are offsets <= 0 from the note's turn, within its session;
         none valid -> the note's own turn), said_at = the session date. For each question with evidence, recall(k=20)
         over (A) heard only and (B) heard + notes, modes fused and bm25. An evidence turn is found@k when it is in the
         union of turn_ids of the top k items. Reports any@k / all@k (k 5, 10, 20) per category and 1-4.
         Addendum B (PASSMARKS-B.md): also turns@k (distinct turns covered by the top k items, summed) and anyT@k
         (evidence among the first k distinct turns reached in rank order: the same turn budget for both stores).
selftest: python claude_rd378L_recall.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_bm390 as B  # noqa: E402
import claude_ep382_store as M  # noqa: E402

MODES = ("fused", "bm25")
KS = (5, 10, 20)
T0 = "2026-09-26T00:00:00+00:00"


def conv_range(s):
    a, b = (int(x) for x in s.split("-"))
    return list(range(a, b + 1))


def load(data, convs):
    lc = json.loads((Path(data) / "locomo10.json").read_text(encoding="utf-8"))
    return [lc[i] for i in convs]


def chat_turns(conv):
    """[(session_no, date, position, dia_id, speaker, text)] in chat order."""
    out = []
    for s_no, (date, turns) in enumerate(B.sessions(conv)):
        for t in turns:
            text = t["text"] + (f" [shared {t['blip_caption']}]" if t.get("blip_caption") else "")
            out.append((s_no, date, len(out), t.get("dia_id"), t["speaker"], text))
    return out


def dialogs(a):
    n = 0
    with open(a.out, "w", encoding="utf-8") as fh:
        for conv in load(a.data, conv_range(a.convs)):
            by = defaultdict(list)
            for s_no, date, p, _dia, spk, text in chat_turns(conv):
                by[(s_no, date)].append({"t": p, "speaker": spk, "text": text})
            for (s_no, date), turns in by.items():
                fh.write(json.dumps({"dialog": f"{conv['sample_id']}#{s_no}", "kind": "overheard",
                                     "speakers": sorted({t["speaker"] for t in turns}), "date": date,
                                     "turns": turns}, ensure_ascii=False) + "\n")
                n += len(turns)
    print(json.dumps({"turns": n}))


def note_rows(notes_path):
    """{sample_id: [(t, note)]} from claude_rd378_write.py output rows."""
    by = defaultdict(list)
    c = defaultdict(int)
    for line in Path(notes_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        c["turns"] += 1
        c["unparsed"] += r.get("notes") is None
        for n in r.get("notes") or []:
            by[r["dialog"].split("#")[0]].append((int(r["t"]), r["dialog"], n))
            c["notes"] += 1
    return by, dict(c)


def build_store(d, turns, notes, with_notes):
    s = M.MemoryStore(d)
    sess_pos = defaultdict(list)
    for s_no, date, p, _dia, spk, text in turns:
        s.remember(text, source="heard", speaker=spk, turn_ids=[p], said_at=date, logged_at=T0)
        sess_pos[s_no].append(p)
    if with_notes:
        date_of = {p: date for _s, date, p, *_ in turns}
        sess_of = {p: s_no for s_no, _d, p, *_ in turns}
        spk_of = {p: spk for _s, _d, p, _dia, spk, _t in turns}
        for t, _dlg, n in notes:
            ps = sess_pos[sess_of[t]]
            k = ps.index(t)
            ids = sorted({ps[k + c] for c in (n.get("cites") or [0]) if isinstance(c, int) and 0 <= k + c <= k})
            when = f" ({n['when']})" if n.get("when") else ""
            s.remember(n["text"] + when, source="note", speaker=spk_of[t], turn_ids=ids or [t], said_at=date_of[t],
                       logged_at=T0)
    return s


def budget_turns(hits, k):
    """Addendum B: the first k DISTINCT turns reached by walking the ranked items in order (a note's cited turns are
    taken from its own turn backwards), so both stores are compared at the same number of turns shown."""
    seen = []
    for h in hits:
        for t in sorted(h["turn_ids"], reverse=True):
            if t not in seen:
                seen.append(t)
                if len(seen) == k:
                    return set(seen)
    return set(seen)


def score(a):
    modes = tuple(a.modes.split(","))
    notes, nc = note_rows(a.notes)
    rows = []
    for conv in load(a.data, conv_range(a.convs)):
        turns = chat_turns(conv)
        pos = {dia: p for _s, _d, p, dia, _spk, _t in turns}
        for arm, with_notes in (("A", False), ("B", True)):
            with tempfile.TemporaryDirectory() as d:
                s = build_store(d, turns, notes.get(conv["sample_id"], []), with_notes)
                for i, qa in enumerate(conv["qa"]):
                    ev = {pos[e] for e in qa.get("evidence", []) if e in pos}
                    if not ev or qa["category"] not in (1, 2, 3, 4):
                        continue
                    r = {"qid": f"{conv['sample_id']}#{i}", "cat": qa["category"], "arm": arm}
                    for mode in modes:
                        hits = s.recall(qa["question"], k=3 * max(KS), mode=mode)
                        for k in KS:
                            got = set().union(*[h["turn_ids"] for h in hits[:k]]) if hits else set()
                            r[f"{mode}_any@{k}"] = int(bool(ev & got))
                            r[f"{mode}_all@{k}"] = int(ev <= got)
                            r[f"{mode}_turns@{k}"] = len(got)
                            r[f"{mode}_anyT@{k}"] = int(bool(ev & budget_turns(hits, k)))
                    rows.append(r)
    summary = {}
    for arm in ("A", "B"):
        for cat in ("1", "2", "3", "4", "1-4"):
            sel = [r for r in rows if r["arm"] == arm and (cat == "1-4" or str(r["cat"]) == cat)]
            s = {"questions": len(sel)}
            for key in [f"{m}_{kind}@{k}" for m in modes for kind in ("any", "all", "anyT", "turns") for k in KS]:
                s[key] = sum(r[key] for r in sel)
            summary[f"{arm}:{cat}"] = s
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = {"label": "after using LoCoMo for development", "convs": a.convs, "notes": nc, "summary": summary}
    (out / "notes_recall.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    (out / "notes_recall_per_question.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({"notes": nc, "A:1-4": summary["A:1-4"], "B:1-4": summary["B:1-4"]}))


def selftest(_a):
    conv = {"sample_id": "x", "qa": [{"question": "Where did Wren move?", "evidence": ["D1:1"], "category": 4}],
            "conversation": {"session_1_date_time": "1 May 2023", "session_1": [
                {"speaker": "Wren", "dia_id": "D1:1", "text": "I moved to Oakvale in May."},
                {"speaker": "Tobin", "dia_id": "D1:2", "text": "Nice, my dog Pip loves the beach."}]}}
    turns = chat_turns(conv)
    ok = {"positions": [t[2] for t in turns] == [0, 1]}
    with tempfile.TemporaryDirectory() as d:
        s = build_store(d, turns, [(1, "x#0", {"text": "Tobin has a dog named Pip.", "cites": [0, -1]})], True)
        note = [r for r in s.rows if r["source"] == "note"]
        ok["note_cites"] = len(note) == 1 and note[0]["turn_ids"] == [0, 1]
        ok["recall"] = bool(s.recall("Where did Wren move?", k=1, mode="bm25"))
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD378L-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dialogs", "score", "selftest"])
    ap.add_argument("--data")
    ap.add_argument("--convs", default="0-4")
    ap.add_argument("--notes")
    ap.add_argument("--out")
    ap.add_argument("--modes", default=",".join(MODES))
    a = ap.parse_args()
    return {"dialogs": dialogs, "score": score, "selftest": selftest}[a.mode](a) or 0


if __name__ == "__main__":
    sys.exit(main())
