#!/usr/bin/env python3
"""Dev-only probe for exp 161 (never touches sealed panels or ledger).

Builds the exp-99 session on loop161, then scores the card's direct
answers on PUBLIC dev sets (exp-99 canonical 40, exp-100 blind 80,
panels 105/114) with fable_self100_runner.score. Prints fire/correct
rates per group. The sealed 127 panel and the S2 panel are never read.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent

import fable_loop161_agent as L161  # noqa: E402
import fable_notebook_contract as C  # noqa: E402
import fable_self100_runner as R100  # noqa: E402
import fable_self122_runner as R122  # noqa: E402
import fable_self99 as S99  # noqa: E402


def facade(loop) -> S99.Self99Agent:
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
    leo = loop.nb.resolve("Leo")
    assert leo.status == C.OK
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


def build_session():
    st = SCRIPTS / "scratchpad" / "probe161dev"
    if st.exists():
        shutil.rmtree(st)
    loop = L161.build_agent161({"state_dir": str(st),
                                "sleep_threshold": 100000})
    for line in S99.TEACHES:
        loop.turn(line)
    for line in S99.CORRECTIONS:
        loop.turn(line)
    doorway_forget(loop, S99.FORGET_LINE)
    for line in S99.ASKS:
        loop.turn(line)
    file_web_row(loop)
    return loop


def score_set(loop, helper, items, tag):
    s = helper.snapshot()
    n = len(items)
    res = {"CORRECT": 0, "DECLINE": 0, "WRONG": 0}
    wrongs = []
    for qid, intent, text in items:
        ans = loop.self_card.answer_self(text)
        verdict, note = R100.score(helper, qid, intent, ans, s)
        res[verdict] += 1
        if verdict == "WRONG":
            wrongs.append((qid, intent, text, ans, note,
                           loop.self_card.route(text)))
    print(f"{tag}: n={n} {res}", flush=True)
    for qid, intent, text, ans, note, rt in wrongs:
        print(f"  WRONG {qid} [{intent}] route={rt} Q={text[:70]}", flush=True)
        print(f"    A={ans[:130]} ({note[:100]})", flush=True)
    return res, wrongs


def main() -> int:
    loop = build_session()
    helper = facade(loop)
    s = helper.snapshot()
    print("gate:", {k: s[k] for k in
                    ("n_taught", "n_entities", "n_quarantine",
                     "n_superseded", "n_forgotten", "sleeps", "turns")},
          flush=True)
    items99 = [(q["id"], q["id"], q["text"]) for q in S99.QUESTIONS]
    score_set(loop, helper, items99, "exp99-40")
    score_set(loop, helper, R100.BLIND, "exp100-80")
    for sub in ("fable-self105panel-20260921", "fable-self114panel-20260922"):
        panel = json.loads((ROOT / "artifacts" / sub / "panel.json")
                           .read_text(encoding="utf-8"))
        qs = panel["questions"] if isinstance(panel, dict) else panel
        items = []
        for q in qs:
            qid, group, intent, text, cls = R122.classify(q)
            items.append((qid, cls, text))
        score_set(loop, helper, items, sub)
    return 0


if __name__ == "__main__":
    sys.exit(main())
