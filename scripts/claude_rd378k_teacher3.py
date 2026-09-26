#!/usr/bin/env python3
"""rd-378k teacher labeller, version 3 (Trustworthy notes thread, 2026-09-26). New file; versions 1 and 2 stay.

gate2 (labeller v2, artifacts/claude-rd378k-20260926/gate2) failed: agreement 471/555 = 84.9% (bar 85%) and overheard
coverage 11/16 (bar 90%). Shown from gate2/failures.jsonl: every one of the 27 failed calls was the teacher leaving out
turns whose notes list is empty (25) or adding context turns it was not asked about (2); a parser that allows exactly that
accepts all 27. Two changes, both fixed in PASSMARKS-E.md before this runs:
1. parser (a bug fix; verdicts untouched): items for turns outside the window are ignored; a turn WITH notes must be
   present with one verdict per note; a turn with NO notes may be left out, and then its "missed" is unknown, written
   as -1 so every builder treats it as "something may be missed" (never taught as "no note here").
2. teacher (the sealed fallback of PASSMARKS-B/C): two passes per window, pass A as shown and pass B with each turn's
   notes in reverse order (so a note's position cannot decide its grade twice); a note is "ok" only if both passes say
   "ok", else pass A's non-ok verdict, else pass B's. missed = the larger of the two when both are known, else -1.
Prompt words, verdict words and output format are claude_rd378k_teacher's; windows of at most 7 graded turns are v2's.

label  python -B scripts/claude_rd378k_teacher3.py label --judge-in J.jsonl --out DIR [--only-hash K] [--hash-rem R]
       (--hash-rem R with --only-hash K keeps dialogs with sha256(id) % K == R). Writes DIR/labels.jsonl
       {dialog, t, verdicts, missed}, DIR/labels_passA.jsonl (pass A alone, same rows; a report-only row that separates
       the parser fix from the second pass) and DIR/failures.jsonl; prints one JSON line of counts (per kind too).
selftest (no network)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_rd378k_teacher import JUDGE, VERDICTS, call, json_list, load  # noqa: E402
from claude_rd378k_teacher2 import windows  # noqa: E402


def parse(w, v):
    """{t: (verdicts, missed)} for the window's graded turns, or None."""
    if not isinstance(v, list):
        return None
    graded = {int(t["t"]): len(t["notes"]) for t in w["turns"] if "notes" in t}
    got = {}
    for r in v:
        if not isinstance(r, dict) or not isinstance(r.get("t"), int):
            return None
        if r["t"] not in graded:
            continue
        if r["t"] in got:
            return None
        got[r["t"]] = r
    out = {}
    for t, n in graded.items():
        r = got.get(t)
        if r is None:
            if n:
                return None
            out[t] = ([], -1)
            continue
        vs = r.get("verdicts")
        if not isinstance(vs, list) or len(vs) != n or any(x not in VERDICTS for x in vs):
            return None
        try:
            m = max(0, int(r.get("missed") or 0))
        except (TypeError, ValueError):
            m = -1
        out[t] = (list(vs), m)
    return out


def reverse_notes(w):
    return dict(w, turns=[dict(t, notes=list(reversed(t["notes"]))) if "notes" in t else t for t in w["turns"]])


def combine(a, b):
    out = {}
    for t, (va, ma) in a.items():
        vb, mb = b[t]
        vb = list(reversed(vb))                        # pass B saw this turn's notes in reverse order
        vs = ["ok" if x == "ok" and y == "ok" else (x if x != "ok" else y) for x, y in zip(va, vb)]
        out[t] = (vs, max(ma, mb) if ma >= 0 and mb >= 0 else -1)
    return out


def one_pass(key, model, w, dialog, wi, tag, fails):
    for tr in range(3):
        txt, u = call(key, model, JUDGE + json.dumps(w, ensure_ascii=False), 0)
        got = parse(w, json_list(txt))
        if got is not None:
            return got, u
        fails.append({"dialog": dialog, "window": wi, "pass": tag, "try": tr + 1, "raw": (txt or "")[:4000]})
    return None, u


def picked(dialog_id, k, rem):
    return k <= 1 or int(hashlib.sha256(dialog_id.encode()).hexdigest(), 16) % k == rem


def label(a, key):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dialogs = [d for d in load(a.judge_in) if picked(d["dialog"], a.only_hash, a.hash_rem)]
    rows, rows_a, costs, fails, failed, per_kind = [], [], [], [], [], {}
    for d in dialogs:
        res, res_a = {}, {}
        for wi, (w, _n) in enumerate(windows(d, 7)):
            pa, ua = one_pass(key, a.model, w, d["dialog"], wi, "A", fails)
            pb, ub = one_pass(key, a.model, reverse_notes(w), d["dialog"], wi, "B", fails) if pa else (None, {})
            costs += [ua, ub]
            if pa is None or pb is None:
                res = None
                break
            res.update(combine(pa, pb))
            res_a.update(pa)
        k = per_kind.setdefault(d["kind"], {"dialogs": 0, "unusable": 0})
        k["dialogs"] += 1
        if res is None:
            k["unusable"] += 1
            failed.append(d["dialog"])
            print(f"[rd378k-teacher3] {d['dialog']} unparsed", flush=True)
            continue
        rows += [{"dialog": d["dialog"], "t": t, "verdicts": vs, "missed": m} for t, (vs, m) in sorted(res.items())]
        rows_a += [{"dialog": d["dialog"], "t": t, "verdicts": vs, "missed": m} for t, (vs, m) in sorted(res_a.items())]
        print(f"[rd378k-teacher3] {d['dialog']} ok", flush=True)
    (out / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    (out / "labels_passA.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows_a), encoding="utf-8")
    (out / "failures.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in fails),
                                        encoding="utf-8")
    verdicts = [x for r in rows for x in r["verdicts"]]
    cost = sum(float(u.get("cost", 0) or 0) for u in costs if u)
    print(json.dumps({"dialogs": len(dialogs), "labelled": len(dialogs) - len(failed), "unparsed": len(failed),
                      "per_kind": per_kind, "failed_calls": len(fails), "notes": len(verdicts),
                      **{v: verdicts.count(v) for v in VERDICTS},
                      "missed_unknown_turns": sum(r["missed"] == -1 for r in rows), "cost_usd": round(cost, 4)}))


def selftest():
    w = {"turns": [{"t": 0, "speaker": "A", "text": "x", "notes": [{"text": "n1"}, {"text": "n2"}]},
                   {"t": 1, "speaker": "B", "text": "y"},
                   {"t": 2, "speaker": "A", "text": "z", "notes": []}]}
    assert parse(w, [{"t": 0, "verdicts": ["ok", "unsupported"], "missed": 1}]) == {0: (["ok", "unsupported"], 1),
                                                                                    2: ([], -1)}
    assert parse(w, [{"t": 0, "verdicts": ["ok", "ok"], "missed": 0}, {"t": 1, "verdicts": [], "missed": 0},
                     {"t": 2, "verdicts": [], "missed": 0}]) == {0: (["ok", "ok"], 0), 2: ([], 0)}
    assert parse(w, [{"t": 2, "verdicts": [], "missed": 0}]) is None            # a turn with notes left out
    assert parse(w, [{"t": 0, "verdicts": ["ok"], "missed": 0}]) is None        # wrong verdict count
    assert parse(w, [{"t": 0, "verdicts": ["ok", "ok"]}, {"t": 0, "verdicts": ["ok", "ok"]}]) is None
    a = {0: (["ok", "unsupported"], 0), 2: ([], -1)}
    b = {0: (["bad_cite", "ok"], 1), 2: ([], 0)}                                 # B saw [n2, n1]
    assert combine(a, b) == {0: (["ok", "unsupported"], 1), 2: ([], -1)}
    b2 = {0: (["ok", "bad_when"], 0), 2: ([], 0)}                                # B: n2 ok, n1 bad_when
    assert combine(a, b2) == {0: (["bad_when", "unsupported"], 0), 2: ([], -1)}
    assert reverse_notes(w)["turns"][0]["notes"] == [{"text": "n2"}, {"text": "n1"}]
    print("rd378k teacher3 selftest 1/1 ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["label", "selftest"])
    ap.add_argument("--judge-in", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--only-hash", type=int, default=1)
    ap.add_argument("--hash-rem", type=int, default=0)
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
