#!/usr/bin/env python3
"""Exp 138c B3 driver -- blind panel through loop138c's turn path.

Same shape as artifacts/fable-agent138-20260922/fable_loop138_selfcheck.py:
ONE loop138c agent replays the exact exp-99 session (20 teaches, 2
corrections, 1 doorway forget, 3 asks, 1 quarantined web row) through
loop.turn, checks the session gate, then runs the 100 sealed blind panel
questions (artifacts/fable-self127panel-20260922/panel.json, read-only)
as successive turns, scoring each answer against the LIVE post-turn
snapshot with fable_self100_runner.score.

138c JUDGE CHANGE (stated in PASSMARKS.md before the run): for panel items
whose expected behaviour is a decline (cls D0 / D* / NEW), a reply exactly
equal to a sealed BASE_DECLINE_PHRASES entry counts as a correct decline
(verdict DECLINE). Rationale: loop138c serves the base loop's honest
abstains verbatim on those turns; the exp-100 scorer would flag their
capitalised words ("Could", "Was") as hallucinations, so without this rule
honest abstains score WRONG. The phrase list has exactly one entry (the
base loop's only clarify on these turns, enumerated pre-seal over all 40
decline-expected items on twin builds): "I didn't understand that. Could
you say it another way?". C-intent items are unaffected (Q059 stays scored
by the unchanged scorer).

Also counts, over all 200 bench121-new questions (fresh loop138c per
item, teaches replayed), how many turns SERVE self content
(entry served == "self") vs serve base -- informational, no bar.

Outputs into --out (default artifacts/fable-self138c-20260922/). Run
(Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138c_selfcheck.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop138c_agent as L138C  # noqa: E402 (agent under test)
import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_self100_runner as R100  # noqa: E402 (scorer, read-only)
import fable_self122_runner as R122  # noqa: E402 (classify, read-only)
import fable_self99 as S99  # noqa: E402 (session + facade, read-only)

GATE = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
        "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}

# Sealed base-decline phrase list (PASSMARKS.md): the base loop's only
# clarify text on decline-expected panel turns, enumerated pre-seal.
BASE_DECLINE_PHRASES = (
    "I didn't understand that. Could you say it another way?",
)


def is_decline_expected(cls: str) -> bool:
    return cls == "NEW" or cls == "D0" or (
        isinstance(cls, str) and cls.startswith("D"))


def facade(loop) -> S99.Self99Agent:
    """Self99Agent facade over live loop138c state (scoring only)."""
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
    """Mirror Self99Agent.doorway_direct on the loop138c loop (forget line)."""
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
    """Mirror Self99Agent.file_web_row on the loop138c notebook."""
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


def build_fresh(out: Path, tag: str):
    state = out / f"scratch-self138c-{tag}"
    if state.exists():
        shutil.rmtree(state)
    return L138C.build_agent138c({"state_dir": str(state),
                                  "sleep_threshold": 100000})


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 138c B3 panel driver")
    ap.add_argument("--out", default=str(
        ROOT / "artifacts" / "fable-self138c-20260922"))
    args = ap.parse_args()
    out = Path(args.out)
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    loop = build_fresh(out, "panel")
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
    accept_hits = 0
    for q in questions:
        qid, group, intent, text, cls = R122.classify(q)
        said = loop.turn(text)
        ans = " ".join(said)
        routed = (dict(loop.last_routed) if loop.last_routed else None)
        s_live = facade(loop).snapshot()
        if not gate_ok:
            verdict, note = "WRONG", "session gate failed; run void"
        elif is_decline_expected(cls) and ans in BASE_DECLINE_PHRASES:
            verdict, note = ("DECLINE",
                             "138c accept rule: base-loop honest abstain")
            accept_hits += 1
        else:
            verdict, note = R100.score(helper, qid, cls, ans, s_live)
        per.append({"id": qid, "group": group, "intent": intent,
                    "question": text,
                    "routed": (routed["intent"] if routed else None),
                    "served": (routed["served"] if routed else None),
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
    print(f"panel: n=100 wrong={len(wrong)} accept_hits={accept_hits} "
          f"groups={by_group}", flush=True)
    for p in wrong:
        print(f"  WRONG {p['id']} [{p['group']}/{p['intent']}] "
              f"routed={p['routed']} served={p['served']} :: "
              f"{p['question'][:80]}", flush=True)
        print(f"    ans={p['answer'][:160]} ({p['note'][:120]})", flush=True)

    # -- bench121-new served-content count: fresh loop per item.
    import fable_bench121_run as B  # noqa: E402 (items, read-only)

    items = [json.loads(line) for line in B.DATA_NEW.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    assert len(items) == 200, len(items)
    served_self, served_base, served_ids = 0, 0, []
    for it in items:
        loop2 = L138C.build_agent138c(
            {"state_dir": str(out / "scratch-self138c-bq" / it["id"]),
             "sleep_threshold": 100000})
        for t in it["taught"]:
            loop2.turn(str(t["sentence_en"]))
        said = loop2.turn(str(it["question"]))
        _ = " ".join(said)
        if loop2.last_routed is not None:
            if loop2.last_routed["served"] == "self":
                served_self += 1
                served_ids.append(it["id"])
            else:
                served_base += 1
    shutil.rmtree(out / "scratch-self138c-bq", ignore_errors=True)
    print(f"bench121-new served: self={served_self} base={served_base} "
          f"ids={served_ids}", flush=True)

    rep = {"seconds": round(time.time() - t0, 1),
           "gate_ok": gate_ok, "snapshot": s,
           "accept_rule_hits": accept_hits,
           "panel": {"n": 100, "wrong": len(wrong),
                     "wrong_ids": [p["id"] for p in wrong],
                     "by_group": by_group, "per": per},
           "bench121_new": {"n": 200, "served_self": served_self,
                            "served_base": served_base,
                            "served_ids": served_ids}}
    (out / "fable_self138c_panel.json").write_text(
        json.dumps(rep, indent=1), encoding="utf-8")
    print(f"B3 {rep['seconds']}s wrong={len(wrong)} "
          f"served_self={served_self} -> "
          f"{out / 'fable_self138c_panel.json'}", flush=True)
    rc = 0
    if len(wrong) > 6:
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
