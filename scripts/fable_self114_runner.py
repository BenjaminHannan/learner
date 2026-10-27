#!/usr/bin/env python3
"""114 -- REGISTERED blind-panel run of the frozen scope-guarded router.

Reads artifacts/fable-self114panel-20260922/panel.json (sealed by its author;
opened here only AFTER scripts/fable_self114.py was frozen, hashed into
artifacts/fable-self114-20260922/PASSMARKS.md, and sealed). Rebuilds the exact
exp-99 scripted session via the frozen guard agent, asks the 100 panel
questions via answer_self() WITHOUT logging new turns, and scores by script
(same sealed rules as exp 105, exp-100 scorer reused read-only):

  existing C-intent -> CORRECT (own C-check) / WRONG (other C-check) /
    DECLINE (marker) / else WRONG;
  existing D-intent -> DECLINE (strict decline check) / else WRONG;
  new (NEW1..NEW20) -> exp-100 NEW rule (any C-check pass -> WRONG);
  trick (TRICK) -> strict decline check (any confident answer -> WRONG).

K4 regressions run in the same invocation: exp-99 check_all (40/40) and the
exp-100 80-question rescoring (WRONG == 0). The exp-105 panel re-score is
reported in the same invocation as UNREGISTERED dev context (it is dev data
for exp 114, not a mark).

Run (Mac CPU, offline; only AFTER PASSMARKS sealed + ledger P114.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self114_runner.py --run --out artifacts/fable-self114-20260922
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_self100_runner as R100  # noqa: E402 (read-only scoring)
import fable_self114 as S114  # noqa: E402 (frozen router under test)

ART_SUBDIR = "fable-self114-20260922"
PANEL_SUBDIR = "fable-self114panel-20260922"
FROZEN_ROUTER_SHA = "c7762e22ae594b48bea4986e9cae32024835a6472a9714184dd612425dbbbef6"
GATE = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
        "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(q: dict) -> tuple[str, str, str, str]:
    qid = q["id"]
    group = q["group"]
    intent = q["intent"]
    text = q.get("question", q.get("text", q.get("q")))
    if group == "existing" and intent.startswith("C"):
        cls = intent
    elif group == "existing":
        cls = intent  # D1..D10: strict decline branch
    elif group == "new":
        cls = "NEW"
    else:
        cls = "D0"  # trick: strict decline check, no CORRECT outcome
    return qid, group, intent, text, cls


def run_registered(out: Path, repo: Path) -> dict:
    t0 = time.monotonic()
    # -- frozen-code + sealed-panel preconditions (fail loudly, no run) --
    router_sha = sha256_file(SCRIPTS / "fable_self114.py")
    assert router_sha == FROZEN_ROUTER_SHA, (
        f"router changed since freeze: {router_sha}")
    seal = subprocess.run(
        ["shasum", "-c", "SEAL.sha256.txt"],
        capture_output=True, text=True,
        cwd=repo / "artifacts" / PANEL_SUBDIR)
    assert seal.returncode == 0, f"panel seal broken: {seal.stdout}{seal.stderr}"

    import shutil
    state = out / "self114-notebook"
    if state.exists():
        shutil.rmtree(state)
    agent = S114.Self114Agent(str(state))
    agent.run_session()
    s = agent.snapshot()
    gate_ok = all(s[k] == v for k, v in GATE.items())

    panel = json.loads((repo / "artifacts" / PANEL_SUBDIR / "panel.json")
                       .read_text(encoding="utf-8"))
    questions = panel["questions"] if isinstance(panel, dict) else panel
    assert len(questions) == 100, len(questions)

    per = []
    for q in questions:
        qid, group, intent, text, cls = classify(q)
        ans = agent.answer_self(text)
        routed, _ = S114.route114(text)
        if gate_ok:
            verdict, note = R100.score(agent, qid, cls, ans, s)
        else:
            verdict, note = "WRONG", "session gate failed; run void"
        per.append({"id": qid, "group": group, "intent": intent,
                    "question": text, "routed": routed, "answer": ans,
                    "verdict": verdict, "note": note})

    # -- K4 regressions on dev data, same invocation --
    checked = agent.check_all()
    k4a = {"s1": checked["correct"], "s2": len(checked["hallucinations"]),
           "s3": sum(1 for p in checked["per_question"]
                     if p["id"].startswith("D") and p["pass"])}
    wrong100, c100, new100 = 0, 0, {"CORRECT": 0, "DECLINE": 0, "WRONG": 0}
    per100 = []
    for qid, intent, text in R100.BLIND:
        ans = agent.answer_self(text)
        verdict, note = R100.score(agent, qid, intent, ans, s)
        per100.append({"id": qid, "intent": intent, "verdict": verdict,
                       "question": text, "answer": ans, "note": note})
        wrong100 += verdict == "WRONG"
        c100 += (qid <= "Q60" and verdict == "CORRECT")
        if qid >= "Q61":
            new100[verdict] += 1
    k4b = {"wrong": wrong100, "rephrasing_correct": c100, "new": new100}

    # -- unregistered dev context: exp-105 panel re-score (NOT a mark) --
    panel105 = json.loads((repo / "artifacts" / "fable-self105panel-20260921"
                           / "panel.json").read_text(encoding="utf-8"))
    per105, wrong105 = [], 0
    for q in panel105["questions"]:
        qid, group, intent, text, cls = classify(q)
        ans = agent.answer_self(text)
        routed, _ = S114.route114(text)
        verdict, note = R100.score(agent, qid, cls, ans, s)
        wrong105 += verdict == "WRONG"
        per105.append({"id": qid, "group": group, "intent": intent,
                       "question": text, "routed": routed, "answer": ans,
                       "verdict": verdict, "note": note})

    existing = [p for p in per if p["group"] == "existing"]
    trick = [p for p in per if p["group"] == "trick"]
    k1_wrong = sum(1 for p in per if p["verdict"] == "WRONG")
    k2_correct = sum(1 for p in existing if p["verdict"] == "CORRECT")
    k3_decline = sum(1 for p in trick if p["verdict"] == "DECLINE")
    marks = {
        "K1": {"wrong": k1_wrong, "of": 100, "pass": k1_wrong == 0},
        "K2": {"got": k2_correct, "need": 45, "of": len(existing),
               "pass": k2_correct >= 45},
        "K3": {"got": k3_decline, "need": 10, "of": len(trick),
               "pass": k3_decline == 10 and len(trick) == 10},
        "K4": {"exp99": k4a, "exp100": k4b,
               "pass": bool(k4a["s1"] == 40 and k4a["s2"] == 0
                            and k4a["s3"] == 10 and k4b["wrong"] == 0)},
    }
    wall = round(time.monotonic() - t0, 1)
    rep = {"marks": marks,
           "pass": bool(gate_ok and all(m["pass"] for m in marks.values())),
           "seconds": wall, "gate_ok": gate_ok, "gate": GATE,
           "router_sha": router_sha, "snapshot": s, "per_question": per,
           "k4_exp100_detail": per100,
           "dev105_rescore": {"wrong": wrong105, "per_question": per105,
                              "registered": False},
           "origins": agent.origin, "web_filings": agent.web_filings}
    (out / "self114-results.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 114 registered run")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--out", default=f"artifacts/{ART_SUBDIR}")
    args = parser.parse_args(argv)
    if args.run:
        repo = Path(__file__).resolve().parent.parent
        out = Path(args.out)
        if not out.is_absolute():
            out = repo / out
        out.mkdir(parents=True, exist_ok=True)
        rep = run_registered(out, repo)
        for p in rep["per_question"]:
            print(f"{p['id']}({p['group']}/{p['intent']}->{p['routed']}): "
                  f"{p['verdict']} Q={p['question'][:56]} :: "
                  f"A={p['answer'][:76]} ({p['note']})", flush=True)
        m = rep["marks"]
        print(f"K1 wrong={m['K1']['wrong']}/100 K2 {m['K2']['got']}/{m['K2']['of']} "
              f"K3 {m['K3']['got']}/{m['K3']['of']} K4a {m['K4']['exp99']} "
              f"K4b wrong={m['K4']['exp100']['wrong']} gate={rep['gate_ok']} "
              f"{rep['seconds']}s -> {'PASS' if rep['pass'] else 'FAIL'}",
              flush=True)
        d = rep["dev105_rescore"]
        print(f"dev105-rescore (unregistered): WRONG={d['wrong']}/100",
              flush=True)
        for p in d["per_question"]:
            if p["verdict"] == "WRONG":
                print(f"  STILL-WRONG {p['id']}({p['group']}/{p['intent']}) "
                      f"Q={p['question']} A={p['answer']}", flush=True)
        return 0 if rep["pass"] else 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
