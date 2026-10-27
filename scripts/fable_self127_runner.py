#!/usr/bin/env python3
"""127 -- REGISTERED blind-panel run of the frozen novelty-guard router.

Two modes:
  --devrescore : DEV ONLY (exp99 + exp100 + panels 105/114/122panel). Never
    touches artifacts/fable-self127panel-20260922/. Prints sha256 of the
    three frozen files (router, bank, deltas) for PASSMARKS.md. Run BEFORE
    the seal.
  --run        : REGISTERED run. Aborts unless router/bank/deltas hashes match
    the frozen values AND the fresh blind panel seal verifies. Rebuilds the
    exact exp-99 session under BOTH the 122 path and the 127 path, scores the
    100 fresh questions under both (the 122->127 table), runs K4 regressions
    (exp99 40 + exp100 80) and unregistered dev rescores (panels 105/114/122),
    and writes self127-results.json. Run ONLY AFTER PASSMARKS sealed with
    shasum AND ledger P127.* appended.

Run (Mac CPU, offline):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_self127_runner.py --run --out artifacts/fable-self127-20260922
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
import fable_self122 as S122  # noqa: E402 (frozen 122 path, comparison)
import fable_self122_runner as R122  # noqa: E402 (frozen classify reuse)
import fable_self127 as S127  # noqa: E402 (frozen 127 router under test)

ART_SUBDIR = "fable-self127-20260922"
PANEL_SUBDIR = "fable-self127panel-20260922"
# Filled after --devrescore, before the seal (must match PASSMARKS.md):
FROZEN_ROUTER_SHA = "6b835c77b5aaefbbdae82755a276781af603dd05e30d9da4d118da5d56ecbe9b"
FROZEN_BANK_SHA = "293d9b0487a5a5427f99a96a9878544a89bc0b6a0bc8be6fbd39deb0f972ea74"
FROZEN_DELTAS_SHA = "8803034b6d46f562de8120b7fc4f76c571ac7f9174db2061b27c6effe83e1636"
GATE = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
        "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_agent(cls, out: Path, tag: str):
    import shutil
    state = out / f"self127-notebook-{tag}"
    if state.exists():
        shutil.rmtree(state)
    agent = cls(str(state))
    agent.run_session()
    return agent


def score_questions(agent, route_fn, s, questions) -> list[dict]:
    per = []
    for q in questions:
        qid, group, intent, text, cls = R122.classify(q)
        ans = agent.answer_self(text)
        routed, _ = route_fn(text)
        verdict, note = R100.score(agent, qid, cls, ans, s)
        per.append({"id": qid, "group": group, "intent": intent,
                    "question": text, "routed": routed, "answer": ans,
                    "verdict": verdict, "note": note})
    return per


def load_panel_questions(repo: Path, subdir: str) -> list[dict]:
    panel = json.loads((repo / "artifacts" / subdir / "panel.json")
                       .read_text(encoding="utf-8"))
    qs = panel["questions"] if isinstance(panel, dict) else panel
    return list(qs)


def summarize(per: list[dict]) -> dict:
    existing = [p for p in per if p["group"] == "existing"]
    trick = [p for p in per if p["group"] == "trick"]
    return {
        "n": len(per),
        "correct": sum(1 for p in per if p["verdict"] == "CORRECT"),
        "decline": sum(1 for p in per if p["verdict"] in (
            "DECLINE", "CLARIFY", "HONEST_DECLINE")),
        "wrong": sum(1 for p in per if p["verdict"] == "WRONG"),
        "existing_correct": sum(1 for p in existing
                                if p["verdict"] == "CORRECT"),
        "existing_n": len(existing),
        "trick_decline": sum(1 for p in trick if p["verdict"] == "DECLINE"),
        "trick_n": len(trick),
    }


def devrescore() -> int:
    repo = Path(__file__).resolve().parent.parent
    print(f"router sha: {sha256_file(SCRIPTS / 'fable_self127.py')}",
          flush=True)
    print(f"bank sha:   {sha256_file(repo / 'artifacts' / ART_SUBDIR / 'bank127.json')}",
          flush=True)
    print(f"deltas sha: {sha256_file(repo / 'artifacts' / ART_SUBDIR / 'deltas127.json')}",
          flush=True)
    print(f"runner sha: {sha256_file(SCRIPTS / 'fable_self127_runner.py')}",
          flush=True)
    out = repo / "scratchpad" / "self127-devrescore"
    out.mkdir(parents=True, exist_ok=True)
    agent = build_agent(S127.Self127Agent, out, "dev")
    s = agent.snapshot()
    gate_ok = all(s[k] == v for k, v in GATE.items())
    print(f"session gate: {gate_ok} {s}", flush=True)
    checked = agent.check_all()
    s1, s2 = checked["correct"], len(checked["hallucinations"])
    s3 = sum(1 for p in checked["per_question"]
             if p["id"].startswith("D") and p["pass"])
    print(f"exp99: S1 {s1}/40 S2 hallucinations={s2} S3 {s3}/10", flush=True)
    # NOTE: exp100 BLIND rows carry cls directly (qid, intent, text):
    per100 = []
    for qid, intent, text in R100.BLIND:
        ans = agent.answer_self(text)
        routed, _ = S127.route127(text)
        verdict, note = R100.score(agent, qid, intent, ans, s)
        per100.append({"id": qid, "intent": intent, "question": text,
                       "routed": routed, "answer": ans,
                       "verdict": verdict, "note": note})
    w100 = sum(1 for p in per100 if p["verdict"] == "WRONG")
    print(f"exp100: WRONG={w100}/80", flush=True)
    for p in per100:
        if p["verdict"] == "WRONG":
            print(f"  STILL-WRONG {p['id']} Q={p['question']} "
                  f"A={p['answer']}", flush=True)
    for subdir in ("fable-self105panel-20260921",
                   "fable-self114panel-20260922",
                   "fable-self122panel-20260922"):
        qs = load_panel_questions(repo, subdir)
        per = score_questions(agent, S127.route127, s, qs)
        sm = summarize(per)
        print(f"{subdir}: CORRECT={sm['correct']} DECLINE={sm['decline']} "
              f"WRONG={sm['wrong']} existing_correct={sm['existing_correct']}"
              f"/{sm['existing_n']}", flush=True)
        for p in per:
            if p["verdict"] == "WRONG":
                print(f"  STILL-WRONG {p['id']}({p['group']}/{p['intent']}) "
                      f"->{p['routed']} Q={p['question']} A={p['answer']}",
                      flush=True)
    ok = gate_ok and s1 == 40 and s2 == 0 and s3 == 10 and w100 == 0
    print("DEVRESCORE " + ("EXPECT-K4-OK" if ok else "K4-REGRESSION"),
          flush=True)
    return 0


def run_registered(out: Path, repo: Path) -> dict:
    t0 = time.monotonic()
    router_sha = sha256_file(SCRIPTS / "fable_self127.py")
    assert router_sha == FROZEN_ROUTER_SHA, (
        f"router changed since freeze: {router_sha}")
    bank_sha = sha256_file(repo / "artifacts" / ART_SUBDIR / "bank127.json")
    assert bank_sha == FROZEN_BANK_SHA, f"bank changed: {bank_sha}"
    deltas_sha = sha256_file(repo / "artifacts" / ART_SUBDIR
                             / "deltas127.json")
    assert deltas_sha == FROZEN_DELTAS_SHA, f"deltas changed: {deltas_sha}"
    seal = subprocess.run(
        ["shasum", "-c", "SEAL.sha256.txt"],
        capture_output=True, text=True,
        cwd=repo / "artifacts" / PANEL_SUBDIR)
    assert seal.returncode == 0, f"panel seal broken: {seal.stdout}{seal.stderr}"

    a127 = build_agent(S127.Self127Agent, out, "127")
    s127 = a127.snapshot()
    gate_ok = all(s127[k] == v for k, v in GATE.items())
    a122 = build_agent(S122.Self122Agent, out, "122")
    s122 = a122.snapshot()
    gate_ok = gate_ok and all(s122[k] == v for k, v in GATE.items())

    fresh = load_panel_questions(repo, PANEL_SUBDIR)
    assert len(fresh) == 100, len(fresh)
    per127 = score_questions(a127, S127.route127, s127, fresh) if gate_ok \
        else []
    per122 = score_questions(a122, S122.route122, s122, fresh) if gate_ok \
        else []
    if not gate_ok:
        for q in fresh:
            qid, group, intent, text, cls = R122.classify(q)
            per127.append({"id": qid, "group": group, "intent": intent,
                           "question": text, "routed": "VOID",
                           "answer": "", "verdict": "WRONG",
                           "note": "session gate failed; run void"})
            per122.append(dict(per127[-1]))

    checked = a127.check_all()
    k4a = {"s1": checked["correct"], "s2": len(checked["hallucinations"]),
           "s3": sum(1 for p in checked["per_question"]
                     if p["id"].startswith("D") and p["pass"])}
    per100, wrong100 = [], 0
    for qid, intent, text in R100.BLIND:
        ans = a127.answer_self(text)
        verdict, note = R100.score(a127, qid, intent, ans, s127)
        per100.append({"id": qid, "intent": intent, "verdict": verdict,
                       "question": text, "answer": ans, "note": note})
        wrong100 += verdict == "WRONG"

    dev = {}
    for subdir in ("fable-self105panel-20260921",
                   "fable-self114panel-20260922",
                   "fable-self122panel-20260922"):
        qs = load_panel_questions(repo, subdir)
        p127 = score_questions(a127, S127.route127, s127, qs)
        dev[subdir] = {"path127": p127, "summary127": summarize(p127),
                       "registered": False}
    qs122 = load_panel_questions(repo, "fable-self122panel-20260922")
    p122on122 = score_questions(a122, S122.route122, s122, qs122)
    dev["fable-self122panel-20260922"]["path122"] = p122on122
    dev["fable-self122panel-20260922"]["summary122"] = summarize(p122on122)

    m127, m122 = summarize(per127), summarize(per122)
    marks = {
        "K1": {"wrong": m127["wrong"], "of": 100,
               "pass": m127["wrong"] == 0},
        "K2": {"got": m127["existing_correct"], "need": 45,
               "of": m127["existing_n"],
               "pass": m127["existing_correct"] >= 45},
        "K3": {"got": m127["trick_decline"], "need": 10,
               "of": m127["trick_n"],
               "pass": m127["trick_decline"] == 10
               and m127["trick_n"] == 10},
        "K4": {"exp99": k4a, "exp100_wrong": wrong100,
               "pass": bool(k4a["s1"] == 40 and k4a["s2"] == 0
                            and k4a["s3"] == 10 and wrong100 == 0)},
    }
    wall = round(time.monotonic() - t0, 1)
    rep = {"marks": marks,
           "pass": bool(gate_ok and all(m["pass"] for m in marks.values())),
           "seconds": wall, "gate_ok": gate_ok, "gate": GATE,
           "router_sha": router_sha, "bank_sha": bank_sha,
           "deltas_sha": deltas_sha,
           "fresh_127": {"summary": m127, "per_question": per127},
           "fresh_122": {"summary": m122, "per_question": per122},
           "k4_exp100_detail": per100,
           "dev_rescores": dev,
           "snapshot": s127}
    (out / "self127-results.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    return rep


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 127 runs")
    parser.add_argument("--devrescore", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--out", default=f"artifacts/{ART_SUBDIR}")
    args = parser.parse_args(argv)
    if args.devrescore:
        return devrescore()
    if args.run:
        repo = Path(__file__).resolve().parent.parent
        out = Path(args.out)
        if not out.is_absolute():
            out = repo / out
        out.mkdir(parents=True, exist_ok=True)
        rep = run_registered(out, repo)
        m = rep["marks"]
        f7, f2 = rep["fresh_127"]["summary"], rep["fresh_122"]["summary"]
        print(f"FRESH-127: CORRECT={f7['correct']} DECLINE={f7['decline']} "
              f"WRONG={f7['wrong']} existing={f7['existing_correct']}/"
              f"{f7['existing_n']} tricks={f7['trick_decline']}/"
              f"{f7['trick_n']}", flush=True)
        print(f"FRESH-122: CORRECT={f2['correct']} DECLINE={f2['decline']} "
              f"WRONG={f2['wrong']} existing={f2['existing_correct']}/"
              f"{f2['existing_n']} tricks={f2['trick_decline']}/"
              f"{f2['trick_n']}", flush=True)
        for p in rep["fresh_127"]["per_question"]:
            if p["verdict"] == "WRONG":
                print(f"  WRONG-127 {p['id']}({p['group']}/{p['intent']})"
                      f"->{p['routed']} Q={p['question']} A={p['answer']}",
                      flush=True)
        print(f"K1 wrong={m['K1']['wrong']}/100 K2 {m['K2']['got']}/"
              f"{m['K2']['of']} K3 {m['K3']['got']}/{m['K3']['of']} "
              f"K4a {m['K4']['exp99']} K4b wrong={m['K4']['exp100_wrong']} "
              f"gate={rep['gate_ok']} {rep['seconds']}s -> "
              f"{'PASS' if rep['pass'] else 'FAIL'}", flush=True)
        for name, d in rep["dev_rescores"].items():
            s7 = d["summary127"]
            print(f"{name} (unregistered, 127-path): CORRECT={s7['correct']}"
                  f" DECLINE={s7['decline']} WRONG={s7['wrong']}",
                  flush=True)
        d122 = rep["dev_rescores"]["fable-self122panel-20260922"]
        print(f"122panel (unregistered, 122-path): {d122['summary122']}",
              flush=True)
        return 0 if rep["pass"] else 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
