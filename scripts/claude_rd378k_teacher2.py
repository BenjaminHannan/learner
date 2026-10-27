#!/usr/bin/env python3
"""rd-378k teacher labeller, version 2 (Trustworthy notes thread, 2026-09-26). New file; claude_rd378k_teacher.py stays.

Why: in the label gate (artifacts/claude-rd378k-20260926/VERIFY-gate.md) the teacher's output was unusable for 10 of 39
dialogs, and all 10 were overheard dialogs (0 of 23 chat dialogs failed; 10 of 16 overheard failed). An overheard dialog
asks for a grade on every turn (12-16 at once); a chat dialog on about 7. The one change: the teacher grades at most 7
turns per call. Each call shows the dialog up to the last turn of its window, and only the window's turns carry their
"notes" list (earlier turns are context only). Prompt words, verdicts, checks and output format are claude_rd378k_teacher's.
Failed calls are logged with the teacher's raw answer (training data only, never a key) so a failure can be read.

label  python -B scripts/claude_rd378k_teacher2.py label --judge-in J.jsonl --out DIR [--only-hash K] [--window 7]
       writes DIR/labels.jsonl {dialog, t, verdicts, missed} and DIR/failures.jsonl; prints one JSON line of counts
       (per kind as well).
selftest (no network)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378k_teacher import JUDGE, VERDICTS, call, check_labels, json_list, load, picked  # noqa: E402


def windows(d, size):
    """Yield (window_dialog, n_turns_graded): the dialog cut after the window's last turn, notes kept only in the window."""
    graded = [k for k, t in enumerate(d["turns"]) if "notes" in t]
    for s in range(0, len(graded), size):
        keep = set(graded[s:s + size])
        last = max(keep)
        turns = [t if k in keep else {x: v for x, v in t.items() if x != "notes"}
                 for k, t in enumerate(d["turns"][:last + 1])]
        yield dict(d, turns=turns), len(keep)


def label(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dialogs = [d for d in load(a.judge_in) if picked(d["dialog"], a.only_hash)]
    rows, usage, failed, fails = [], [], [], []
    per_kind = {}
    for d in dialogs:
        got_all = []
        for wi, (w, _n) in enumerate(windows(d, a.window)):
            got = None
            for tr in range(3):
                txt, u = call(key, a.model, JUDGE + json.dumps(w, ensure_ascii=False), 0)
                usage.append(u)
                got = check_labels(w, json_list(txt))
                if got is not None:
                    break
                fails.append({"dialog": d["dialog"], "window": wi, "try": tr + 1, "raw": (txt or "")[:4000]})
            if got is None:
                got_all = None
                break
            got_all += got
        k = per_kind.setdefault(d["kind"], {"dialogs": 0, "unusable": 0})
        k["dialogs"] += 1
        if got_all is None:
            k["unusable"] += 1
            failed.append(d["dialog"])
            print(f"[rd378k-teacher2] {d['dialog']} unparsed", flush=True)
            continue
        rows += got_all
        print(f"[rd378k-teacher2] {d['dialog']} ok", flush=True)
    (out / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    (out / "failures.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in fails),
                                        encoding="utf-8")
    cost = sum(float(u.get("cost", 0) or 0) for u in usage)
    verdicts = [x for r in rows for x in r["verdicts"]]
    print(json.dumps({"dialogs": len(dialogs), "labelled": len(dialogs) - len(failed), "unparsed": len(failed),
                      "per_kind": per_kind, "calls": len(usage), "failed_calls": len(fails), "notes": len(verdicts),
                      **{v: verdicts.count(v) for v in VERDICTS}, "cost_usd": round(cost, 4)}))


def selftest():
    d = {"dialog": "x", "kind": "overheard", "turns": [
        {"t": k, "speaker": "AB"[k % 2], "text": f"m{k}", "notes": [{"text": f"n{k}"}] if k % 3 else []}
        for k in range(15)]}
    ws = list(windows(d, 7))
    assert [n for _w, n in ws] == [7, 7, 1]
    w0, w1 = ws[0][0], ws[1][0]
    assert len(w0["turns"]) == 7 and all("notes" in t for t in w0["turns"])
    assert len(w1["turns"]) == 14 and [("notes" in t) for t in w1["turns"]] == [False] * 7 + [True] * 7
    good = [{"t": t["t"], "verdicts": ["ok"] * len(t["notes"]), "missed": 0} for t in w1["turns"] if "notes" in t]
    assert len(check_labels(w1, good)) == 7
    c = {"dialog": "c", "kind": "chat", "turns": [
        {"t": k, "speaker": "user", "text": "u", "notes": []} if k % 2 == 0 else {"t": k, "speaker": "assistant",
                                                                                   "text": "a"} for k in range(14)]}
    assert [n for _w, n in windows(c, 7)] == [7]           # a chat dialog stays one call, as in version 1
    print("rd378k teacher2 selftest 1/1 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["label", "selftest"])
    ap.add_argument("--judge-in", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--only-hash", type=int, default=1)
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--model", default="z-ai/glm-5.3-flash")
    a = ap.parse_args()
    if a.mode == "selftest":
        selftest()
        return
    key = (Path.home() / ".config" / "openrouter" / "key").read_text().strip()
    try:
        label(a, key)
    finally:
        del key


if __name__ == "__main__":
    main()
