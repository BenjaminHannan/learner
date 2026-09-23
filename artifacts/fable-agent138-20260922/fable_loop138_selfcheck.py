#!/usr/bin/env python3
"""Exp 138 A3 driver -- self panel through loop138's turn path + bench routing.

1. Builds ONE loop138 agent, replays the exact exp-99 session (20 teaches,
   2 corrections, 1 doorway forget, 3 asks, 1 quarantined web row) through
   loop.turn, checks the session gate (n_taught 19 etc.).
2. Runs the 100 sealed blind panel questions
   (artifacts/fable-self127panel-20260922/panel.json, read-only) as
   successive turns through loop.turn (notebook-first + self fallback),
   scoring each answer against the LIVE post-turn snapshot with
   fable_self100_runner.score (same scorer as exp 127). Reports wrong count
   (bar <= 1) plus the standalone-router comparison.
3. Runs all 200 bench121-new questions (fresh loop138 per item, teaches
   replayed) and counts non-DECLINE routings to the self answerer (bar 0);
   DECLINE servings are counted separately (verdict-neutral abstains).

Outputs into artifacts/fable-agent138-20260922/. Run (Mac CPU, offline;
only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B artifacts/fable-agent138-20260922/fable_loop138_selfcheck.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138_agent as L138  # noqa: E402 (agent under test)
import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_self100_runner as R100  # noqa: E402 (scorer, read-only)
import fable_self122_runner as R122  # noqa: E402 (classify, read-only)
import fable_self99 as S99  # noqa: E402 (session + facade, read-only)

ART = ROOT / "artifacts" / "fable-agent138-20260922"
GATE = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
        "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}


def facade(loop) -> S99.Self99Agent:
    """Self99Agent facade over live loop138 state ( scoring only)."""
    helper = S99.Self99Agent.__new__(S99.Self99Agent)
    helper.loop = loop
    helper.nb = loop.nb
    helper.turn_log = loop.self_turn_log
    helper.mode_log = loop.self_mode_log
    helper.origin = loop.self_origin
    helper.web_filings = loop.self_web_filings
    helper.sleep_history = loop.self_sleep_history
    helper.forget_log = loop.self_forget_log
    helper.tau_hat = float(loop.parts90.get("tau_hat_used", 0.0))
    return helper


def doorway_forget(loop, line: str) -> str:
    """Mirror Self99Agent.doorway_direct on the loop138 loop (forget line)."""
    n = len(loop.self_turn_log) + 1
    before = set(loop.nb.facts)
    active_before = {fid for fid in before if loop.nb.active(fid)}
    try:
        reply = loop.listening.hear(line)
    except C.LogCorrupt as exc:
        reply = f"I could NOT save that ({exc})."
    loop.experience.append({"tick": loop.tick, "kind": "turn", "text": line,
                            "statuses": ["doorway-direct"]})
    after = set(loop.nb.facts)
    for fid in after - before:
        loop.self_origin[fid] = {"by": "Ben", "turn": n}
    for fid in active_before:
        if fid in loop.nb.facts and not loop.nb.active(fid):
            loop.self_forget_log[fid] = n
    loop.self_turn_log.append({
        "n": n, "ben": line, "reply": reply, "records": [],
        "statuses": ["doorway-direct"], "stage": "doorway-direct",
        "score": 1.0, "wrote": True, "via": "doorway-direct",
        "tick": loop.tick, "mode": loop.mode})
    loop.self_mode_log.append({"tick": loop.tick, "mode": loop.mode})
    return reply


def file_web_row(loop) -> str:
    """Mirror Self99Agent.file_web_row on the loop138 notebook."""
    leo = loop.nb.resolve("Leo")
    assert leo.status == C.OK, "Leo must exist before filing the web row"
    res = loop.nb.assert_fact(
        "self99-web-1", "thinking", "web-quarantine",
        leo.detail["entity_id"], "hobby", {"literal": "chess"},
        provenance={"url": S99.WEB_URL, "quoted_span": S99.WEB_SPAN})
    assert res.status == C.SAVED, res.status
    fid = res.detail["fact_id"]
    loop.self_origin[fid] = {"by": "web-quarantine", "turn": None}
    loop.self_web_filings.append({"fact_id": fid, "url": S99.WEB_URL,
                                  "span": S99.WEB_SPAN})
    return fid


def run_session(loop) -> None:
    for line in S99.TEACHES:
        loop.turn(line)
    for line in S99.CORRECTIONS:
        loop.turn(line)
    doorway_forget(loop, S99.FORGET_LINE)
    for line in S99.ASKS:
        loop.turn(line)
    file_web_row(loop)


def build_fresh(tag: str):
    state = ART / f"scratch-self138-{tag}"
    if state.exists():
        shutil.rmtree(state)
    loop = L138.build_agent138({"state_dir": str(state),
                                "sleep_threshold": 100000})
    return loop


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    loop = build_fresh("panel")
    run_session(loop)
    helper = facade(loop)
    s = helper.snapshot()
    gate_ok = all(s[k] == v for k, v in GATE.items())
    print(f"session gate: {gate_ok} "
          f"{ {k: s[k] for k in GATE} }", flush=True)

    panel = json.loads((ROOT / "artifacts" / "fable-self127panel-20260922"
                        / "panel.json").read_text(encoding="utf-8"))
    questions = panel["questions"] if isinstance(panel, dict) else panel
    assert len(questions) == 100, len(questions)
    per = []
    for q in questions:
        qid, group, intent, text, cls = R122.classify(q)
        said = loop.turn(text)
        ans = " ".join(said)
        routed = (dict(loop.last_routed) if loop.last_routed else None)
        s_live = facade(loop).snapshot()
        if gate_ok:
            verdict, note = R100.score(helper, qid, cls, ans, s_live)
        else:
            verdict, note = "WRONG", "session gate failed; run void"
        per.append({"id": qid, "group": group, "intent": intent,
                    "question": text,
                    "routed": (routed["intent"] if routed else None),
                    "answer": ans, "verdict": verdict, "note": note})
    wrong = [p for p in per if p["verdict"] == "WRONG"]
    by_group: dict = {}
    for p in per:
        cell = by_group.setdefault(p["group"], {"n": 0, "correct": 0,
                                                "decline": 0, "wrong": 0})
        cell["n"] += 1
        cell[{"CORRECT": "correct"}.get(p["verdict"],
                                        "wrong" if p["verdict"] == "WRONG"
                                        else "decline")] += 1
    print(f"panel: n=100 wrong={len(wrong)} groups={by_group}", flush=True)
    for p in wrong:
        print(f"  WRONG {p['id']} [{p['group']}/{p['intent']}] "
              f"routed={p['routed']} :: {p['question'][:80]}",
              flush=True)
        print(f"    ans={p['answer'][:160]} ({p['note'][:120]})", flush=True)

    # -- bench121-new routing check: fresh loop per item, teaches + question.
    import fable_bench121_run as B  # noqa: E402 (items, read-only)

    items = [json.loads(line) for line in B.DATA_NEW.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    assert len(items) == 200, len(items)
    content_routed, decline_served, routed_ids = 0, 0, []
    for it in items:
        loop2 = L138.build_agent138(
            {"state_dir": str(ART / "scratch-self138-bq" / it["id"]),
             "sleep_threshold": 100000})
        for t in it["taught"]:
            loop2.turn(str(t["sentence_en"]))
        said = loop2.turn(str(it["question"]))
        _ = " ".join(said)
        if loop2.last_routed is not None:
            if loop2.last_routed["intent"] == "DECLINE":
                decline_served += 1
            else:
                content_routed += 1
                routed_ids.append(it["id"])
    shutil.rmtree(ART / "scratch-self138-bq", ignore_errors=True)
    print(f"bench121-new routing: content_routed={content_routed} "
          f"decline_served={decline_served} ids={routed_ids}", flush=True)

    out = {"seconds": round(time.time() - t0, 1),
           "gate_ok": gate_ok, "snapshot": s,
           "panel": {"n": 100, "wrong": len(wrong),
                     "wrong_ids": [p["id"] for p in wrong],
                     "by_group": by_group, "per": per},
           "bench121_new": {"n": 200, "content_routed": content_routed,
                            "decline_served": decline_served,
                            "routed_ids": routed_ids}}
    (ART / "fable_self138_panel.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"A3 {out['seconds']}s wrong={len(wrong)} "
          f"content_routed={content_routed} -> "
          f"{ART / 'fable_self138_panel.json'}", flush=True)
    rc = 0
    if len(wrong) > 1 or content_routed > 0:
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
