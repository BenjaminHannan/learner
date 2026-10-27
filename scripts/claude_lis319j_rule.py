#!/usr/bin/env python3
"""lis-319j: job + place rule (reading thread, 2026-09-26). A save-time hold rule, no retraining.

Ben's 12:00 report: some wrong saves mix up "works in" and "lives in" when a job and a place share a sentence.
Rule (applied to the reader's own frame, per fact):
  - a home-place fact (rel city or home) is HELD when the clause holding its value has a job cue and no home cue;
  - a work-place fact (rel work_location) is HELD when that clause has a home cue and no job cue.
  Job cue = a work word (JOB_WORDS) or the value of one of the frame's own job facts (occupation, employer, job,
  school_job) in the same clause. Home cue = HOME_WORDS. Clause = the turn split at . ! ? ; , and at
  but / and / though / while / whereas. A fact whose value is not found in the turn is left alone.
Held = its confidence is set to 0.0, so every scorer at any bar skips it.

hold:     python claude_lis319j_rule.py hold --reads R --rows ROWS --out R_J.jsonl   (ROWS: id, turn; counts only)
selftest: python claude_lis319j_rule.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_lis319_fullclaim import load  # noqa: E402

HOME_RELS = {"city", "home"}
WORK_RELS = {"work_location"}
JOB_RELS = {"occupation", "employer", "job"}
JOB_WORDS = re.compile(r"\b(work|works|working|job|jobs|office|shift|shifts|employed|commute|commutes|intern|"
                       r"internship|hired|career|placement)\b", re.I)
HOME_WORDS = re.compile(r"\b(live|lives|living|lived|moved|move|home|house|flat|apartment|rent|renting|neighbou?rs?|"
                        r"settled)\b", re.I)
SPLIT = re.compile(r"[.!?;,]+|\s(?:but|and|though|although|while|whereas)\s", re.I)


def clause_of(turn, value):
    v = str(value or "").strip().lower()
    if not v:
        return None
    for cl in SPLIT.split(turn or ""):
        if v in cl.lower():
            return cl
    return None


def held(f, facts, turn):
    rel = f.get("rel")
    if rel not in HOME_RELS | WORK_RELS:
        return False
    cl = clause_of(turn, f.get("value"))
    if cl is None:
        return False
    low = cl.lower()
    job = bool(JOB_WORDS.search(cl)) or any(
        x is not f and isinstance(x, dict) and x.get("rel") in JOB_RELS and str(x.get("value", "")).strip()
        and str(x.get("value")).strip().lower() in low for x in facts)
    home = bool(HOME_WORDS.search(cl))
    return (rel in HOME_RELS and job and not home) or (rel in WORK_RELS and home and not job)


def apply(reads, rows):
    turn = {r["id"]: r["turn"] for r in rows}
    c, out = Counter(), []
    for r in reads:
        facts = ((r.get("frame") or {}).get("facts") or [])
        confs = list(r.get("conf") or [])
        for i, f in enumerate(facts):
            if isinstance(f, dict) and f.get("rel") in HOME_RELS | WORK_RELS:
                c["place_facts"] += 1
                if i < len(confs) and held(f, facts, turn.get(r["id"], "")):
                    c[f"held:{f.get('rel')}"] += 1
                    confs[i] = 0.0
        out.append(dict(r, conf=confs))
    return out, c


def hold(a):
    out, c = apply(load(a.reads), load(a.rows))
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(json.dumps(dict(c) | {"reads": len(out)}))


def selftest(_a):
    cases = [  # (turn, facts, index, expect held)
        ("I'm a nurse in Leeds", [{"rel": "occupation", "value": "nurse"}, {"rel": "city", "value": "Leeds"}], 1, True),
        ("I live in Leeds and work at a bakery", [{"rel": "city", "value": "Leeds"}], 0, False),
        ("She works in Harrow", [{"rel": "city", "value": "Harrow"}], 0, True),
        ("She works in Harrow", [{"rel": "work_location", "value": "Harrow"}], 0, False),
        ("we moved to Vell last year", [{"rel": "work_location", "value": "Vell"}], 0, True),
        ("my brother lives in Oakvale, he's a pilot", [{"rel": "city", "value": "Oakvale"}], 0, False),
        ("Tom has a dog", [{"rel": "pet_name", "value": "dog"}], 0, False),
    ]
    ok = [held(fs[i], fs, t) == want for t, fs, i, want in cases]
    for (t, _fs, _i, want), g in zip(cases, ok):
        print(("PASS " if g else "FAIL ") + f"{t!r} held={want}")
    print("LIS319J-SELFTEST " + ("PASS" if all(ok) else "FAIL"))
    return 0 if all(ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hold", "selftest"])
    ap.add_argument("--reads")
    ap.add_argument("--rows")
    ap.add_argument("--out")
    a = ap.parse_args()
    return {"hold": hold, "selftest": selftest}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
