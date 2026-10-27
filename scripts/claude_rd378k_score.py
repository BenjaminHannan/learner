#!/usr/bin/env python3
"""rd-378k scorer (Trustworthy notes, 09-26): old note writer vs the cut-only writer on the TEST-ONLY notepanel378k,
graded by blind judges who see each writer's notes as an unnamed set (P or Q). Prints counts only, never text.

judgein: python claude_rd378k_score.py judgein --panel DIALOGS --notes NOTES --out JUDGE_IN
         panel dialogs with each writer row's notes on its turn ("notes": [] for an unparsed turn), the judge's input
         format (artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md).
score:   python claude_rd378k_score.py score --panel DIALOGS --dir DIR --map MAP.json [--confirm-old C --confirm-new C]
         DIR holds notes_old.jsonl, notes_new.jsonl, judge_in_P.jsonl, judge_in_Q.jsonl and judge_{A,B}_{P,Q}.jsonl;
         MAP = {"P": "old"|"new", "Q": the other}. Writes nothing; prints one JSON object of counts and the marks
         (artifacts/claude-rd378k-20260926/PASSMARKS.md). --confirm-*: rd-378u-style notes_confirm.json for mark K5.
selftest: python claude_rd378k_score.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

JUDGES = ("A", "B")
VERDICTS = ("ok", "unsupported", "bad_cite", "bad_when", "bad_form")


def read_jsonl(p):
    return [json.loads(line) for line in Path(p).read_text(encoding="utf-8").splitlines() if line.strip()]


def judge_input(panel, notes):
    got = {(r["dialog"], int(r["t"])): r["notes"] for r in notes}
    out, c = [], Counter()
    for d in panel:
        turns = []
        for t in d["turns"]:
            t = {k: v for k, v in t.items() if k != "notes"}
            if d["kind"] == "chat" and t["speaker"] == "assistant":
                turns.append(t)
                continue
            key = (d["dialog"], int(t["t"]))
            if key not in got:
                raise SystemExit(f"no writer row for {key}")
            ns = got[key]
            c["turns"] += 1
            c["unparsed"] += ns is None
            t["notes"] = [{"text": n["text"], "cites": n.get("cites") or [0], "when": n.get("when")} for n in ns or []]
            c["notes"] += len(t["notes"])
            turns.append(t)
        out.append(dict(d, turns=turns))
    return out, dict(c)


def judged_counts(jin, judged):
    v = {(r["dialog"], int(r["t"])): r for r in judged}
    c = Counter()
    for d in jin:
        for t in d["turns"]:
            if "notes" not in t:
                continue
            key = (d["dialog"], int(t["t"]))
            if key not in v:
                raise SystemExit(f"judge skipped {key}")
            vs = v[key]["verdicts"]
            if len(vs) != len(t["notes"]):
                raise SystemExit(f"verdicts do not line up with notes at {key}")
            for x in vs:
                c[x if x in VERDICTS else "other"] += 1
            c["notes"] += len(vs)
            c["turns"] += 1
            m = int(v[key].get("missed", 0) or 0)
            c["missed"] += m
            c["turns_missed"] += m > 0
    return dict(c)


def score(a):
    panel = read_jsonl(a.panel)
    d = Path(a.dir)
    sets = json.loads(Path(a.map).read_text(encoding="utf-8"))
    if sorted(sets.values()) != ["new", "old"] or sorted(sets) != ["P", "Q"]:
        raise SystemExit("map must be {P, Q} -> {old, new}")
    res = {}
    for s, writer in sets.items():
        built, wc = judge_input(panel, read_jsonl(d / f"notes_{writer}.jsonl"))
        jin = read_jsonl(d / f"judge_in_{s}.jsonl")
        if built != jin:
            raise SystemExit(f"judge_in_{s} is not built from notes_{writer}")
        runs = {j: judged_counts(jin, read_jsonl(d / f"judge_{j}_{s}.jsonl")) for j in JUDGES}
        mean = lambda f: sum(f(runs[j]) for j in JUDGES) / len(JUDGES)  # noqa: E731
        res[writer] = {"set": s, "writer": wc, "judges": runs,
                       "untrue_share": round(mean(lambda r: r.get("unsupported", 0) / max(1, r["notes"])), 4),
                       "ok_notes": mean(lambda r: r.get("ok", 0)),
                       "missed": mean(lambda r: r["missed"]),
                       "unparsed_share": round(wc["unparsed"] / max(1, wc["turns"]), 4)}
    o, n = res["old"], res["new"]
    drop = round(100 * (o["untrue_share"] - n["untrue_share"]), 1)
    marks = {"K1 untrue share drop >= 15 points": drop >= 15,
             "K2 ok notes >= 85% of old": n["ok_notes"] >= 0.85 * o["ok_notes"],
             "K3 missed <= 1.10 x old": n["missed"] <= 1.10 * o["missed"],
             "K4 unparsed turns <= 2%": n["unparsed_share"] <= 0.02}
    if a.confirm_old and a.confirm_new:
        co = json.loads(Path(a.confirm_old).read_text())["summary"]["B:1-4"]
        cn = json.loads(Path(a.confirm_new).read_text())["summary"]["B:1-4"]
        k5 = {"old_any@10": co["any@10"], "new_any@10": cn["any@10"], "questions": cn["questions"],
              "diff_points": round(100 * (cn["any@10"] - co["any@10"]) / max(1, cn["questions"]), 1)}
        if co["questions"] != cn["questions"]:
            raise SystemExit("K5 files cover different questions")
        res["K5"] = k5
        marks["K5 LoCoMo 5-9 any@10 >= old - 2 points"] = k5["diff_points"] >= -2
    out = {"old": o, "new": n, "untrue_drop_points": drop, "marks": marks,
           "PASS": all(marks.values()), "proved_wrong": drop < 5}
    print(json.dumps(out))
    return out


def selftest(_a):
    panel = [{"dialog": "x1", "kind": "chat", "speakers": ["user", "assistant"], "date": "8 May 2023", "turns": [
        {"t": 1, "speaker": "user", "text": "I adopted a cat named Miso last week."},
        {"t": 2, "speaker": "assistant", "text": "Congrats!"},
        {"t": 3, "speaker": "user", "text": "Maybe I'll get a second one someday."}]}]
    old = [{"dialog": "x1", "t": 1, "notes": [{"text": "The user adopted a cat named Miso.", "cites": [0],
                                               "when": "last week"}, {"text": "The user loves cats.", "cites": [0]}]},
           {"dialog": "x1", "t": 3, "notes": [{"text": "The user has two cats.", "cites": [0]}]}]
    new = [{"dialog": "x1", "t": 1, "notes": [{"text": "The user adopted a cat named Miso.", "cites": [0],
                                               "when": "last week"}]},
           {"dialog": "x1", "t": 3, "notes": None}]
    ok = {}
    with tempfile.TemporaryDirectory() as tdir:
        d = Path(tdir)
        w = lambda name, rows: (d / name).write_text("".join(json.dumps(r) + "\n" for r in rows))  # noqa: E731
        w("notes_old.jsonl", old)
        w("notes_new.jsonl", new)
        jo, co = judge_input(panel, old)
        jn, cn = judge_input(panel, new)
        ok["judge input: assistant turn has no notes key"] = "notes" not in jo[0]["turns"][1]
        ok["judge input: unparsed turn gets []"] = jn[0]["turns"][2]["notes"] == [] and cn["unparsed"] == 1
        w("judge_in_P.jsonl", jn)
        w("judge_in_Q.jsonl", jo)
        (d / "map.json").write_text(json.dumps({"P": "new", "Q": "old"}))
        w("judge_A_Q.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok", "unsupported"], "missed": 0},
                              {"dialog": "x1", "t": 3, "verdicts": ["unsupported"], "missed": 0}])
        w("judge_B_Q.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok", "ok"], "missed": 0},
                              {"dialog": "x1", "t": 3, "verdicts": ["unsupported"], "missed": 0}])
        w("judge_A_P.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok"], "missed": 0},
                              {"dialog": "x1", "t": 3, "verdicts": [], "missed": 0}])
        w("judge_B_P.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok"], "missed": 1},
                              {"dialog": "x1", "t": 3, "verdicts": [], "missed": 0}])
        args = argparse.Namespace(panel=None, dir=tdir, map=str(d / "map.json"), confirm_old=None, confirm_new=None)
        w("panel.jsonl", panel)
        args.panel = str(d / "panel.jsonl")
        r = score(args)
        ok["old untrue share = mean of judges (2/3, 1/3)"] = abs(r["old"]["untrue_share"] - 0.5) < 1e-9
        ok["new untrue share 0, drop 50 points"] = r["new"]["untrue_share"] == 0 and r["untrue_drop_points"] == 50.0
        ok["ok notes mean (1.5 old, 1 new)"] = r["old"]["ok_notes"] == 1.5 and r["new"]["ok_notes"] == 1.0
        ok["K2 fails at 1 vs 1.5"] = r["marks"]["K2 ok notes >= 85% of old"] is False
        ok["K3 fails when missed rises 0 -> 0.5"] = r["marks"]["K3 missed <= 1.10 x old"] is False
        ok["K4 fails at 1 of 2 unparsed"] = r["marks"]["K4 unparsed turns <= 2%"] is False
        w("judge_B_P.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok", "ok"], "missed": 0},
                              {"dialog": "x1", "t": 3, "verdicts": [], "missed": 0}])
        try:
            score(args)
            ok["misaligned verdicts stop"] = False
        except SystemExit:
            ok["misaligned verdicts stop"] = True
        w("judge_B_P.jsonl", [{"dialog": "x1", "t": 1, "verdicts": ["ok"], "missed": 1},
                              {"dialog": "x1", "t": 3, "verdicts": [], "missed": 0}])
        (d / "map.json").write_text(json.dumps({"P": "old", "Q": "new"}))
        try:
            score(args)
            ok["judge input built from the wrong writer stops"] = False
        except SystemExit:
            ok["judge input built from the wrong writer stops"] = True
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("RD378K-SCORE-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL"))
    return 0 if all(ok.values()) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["judgein", "score", "selftest"])
    ap.add_argument("--panel")
    ap.add_argument("--notes")
    ap.add_argument("--out")
    ap.add_argument("--dir")
    ap.add_argument("--map")
    ap.add_argument("--confirm-old")
    ap.add_argument("--confirm-new")
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest(a)
    if a.mode == "judgein":
        jin, c = judge_input(read_jsonl(a.panel), read_jsonl(a.notes))
        Path(a.out).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in jin), encoding="utf-8")
        print(json.dumps(c))
        return 0
    score(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
