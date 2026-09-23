#!/usr/bin/env python3
"""Exp 161 registered marks S1-S4 (loop161 + self card).

S1: panel proper-noun leak check on scripts/fable_selfcard161.py.
S2: sealed fresh panel (cases161.json, 69 cases, 3 notebook states) through
    SelfCard161.answer_self direct on live loop161 state (teaches enter via
    loop.turn; answers do not log turns, exp-100 method).
S3: sealed exp-127 blind panel through the loop161 turn path, scored with
    fable_self100_runner.score against the live post-turn snapshot.
S4: bench121-new 200 questions through fresh loop161 turn paths; 0 content
    answers served by the card.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed + ledger P161.*):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_selfcard161_marks.py
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-selfcard161-20260922"

import fable_loop161_agent as L161  # noqa: E402 (agent under test)
import fable_notebook_contract as C  # noqa: E402 (read-only)
import fable_self100_runner as R100  # noqa: E402 (S3 scorer, read-only)
import fable_self122_runner as R122  # noqa: E402 (classify, read-only)
import fable_self99 as S99  # noqa: E402 (session, facade, read-only)
import fable_selfcard161 as SC161  # noqa: E402 (card under test)

PANEL_SUBS = ("fable-self105panel-20260921", "fable-self114panel-20260922",
              "fable-self122panel-20260922", "fable-self127panel-20260922")
TRAIN122 = ("artifacts/fable-self122-20260922/train122.jsonl",
            "artifacts/fable-self122-20260922/heldout122.jsonl")

# Frozen S1 allow-list: generic intent-keyword / template words that also
# occur as panel proper nouns. No person, place, or panel entity is listed.
S1_ALLOW = {"BELIEVE", "CAN", "COUNT", "FACT", "FACTS", "Like", "PEOPLE",
            "SLEEP", "TEACH", "UNKNOWN", "What"}

# Frozen S2 sentence-starter allow-list (generic words only).
S2_ALLOW = {"I", "You", "Your", "My", "No", "Yes", "Only", "Nothing",
            "None", "Right", "Just", "We", "The", "A", "Every", "Like"}


def panel_proper_nouns() -> set[str]:
    texts = [q["text"] for q in S99.QUESTIONS]
    for sub in PANEL_SUBS:
        panel = json.loads((ROOT / "artifacts" / sub / "panel.json")
                           .read_text(encoding="utf-8"))
        qs = panel["questions"] if isinstance(panel, dict) else panel
        for q in qs:
            texts.append(q.get("question", q.get("text", q.get("q", ""))))
    texts += [t for _, _, t in R100.BLIND]
    for rel in TRAIN122:
        path = ROOT / rel
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    texts.append(json.loads(line).get("text", ""))
    out = set()
    for t in texts:
        toks = re.findall(r"[A-Za-z][A-Za-z']*", t)
        for i, w in enumerate(toks):
            if i > 0 and w[0].isupper() and w != "I" and len(w) >= 2:
                out.add(w)
    return out


def mark_s1() -> dict:
    prop = panel_proper_nouns()
    src = (SCRIPTS / "fable_selfcard161.py").read_text(encoding="utf-8")
    code = set(re.findall(r"[A-Za-z][A-Za-z0-9]*", src))
    hit = sorted(prop & code)
    unlisted = [w for w in hit if w not in S1_ALLOW]
    return {"n_panel_nouns": len(prop), "intersections": hit,
            "unlisted": unlisted, "pass": not unlisted}


# ------------------------------------------------------------- S2 helpers
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


def snapshot(loop) -> dict:
    card = loop.self_card
    c = loop.counters
    return {
        "n_taught": len(card.taught()),
        "n_entities": len(loop.nb.entities),
        "entity_names": card.entity_names(),
        "n_quarantine": len(card.rows_of("web-quarantine")),
        "n_proposed": len(card.rows_of("proposed")),
        "n_inferred": len(card.rows_of("inferred")),
        "n_sleep_derived": len(card.rows_of("sleep-derived")),
        "n_forgotten": len(card.retracted()),
        "n_superseded": len(loop.nb.superseded),
        "turns": len(loop.self_turn_log),
        "answers": int(c.get("answers", 0)),
        "writes": int(c.get("writes", 0)),
        "clarifications": int(c.get("clarifications", 0)),
        "sleeps": int(c.get("sleeps", 0)),
        "mode": loop.mode,
    }


def state_ints(s: dict) -> set[int]:
    ints = {0, 1, s["n_taught"], s["n_entities"], s["n_quarantine"],
            s["n_proposed"], s["n_inferred"], s["n_sleep_derived"],
            s["n_forgotten"], s["n_superseded"], s["turns"], s["answers"],
            s["writes"], s["clarifications"], s["sleeps"]}
    ints.update(range(0, s["turns"] + 1))
    return ints


def state_names(loop, s: dict) -> set[str]:
    names = set()
    for n in s["entity_names"]:
        names.update(n.split())
    card = loop.self_card
    for f in loop.nb.facts.values():
        v = card.show(f["value"])
        for w in re.split(r"\s+", v):
            if w[:1].isupper():
                names.add(w.strip(".,"))
    return names


def hall_scan(loop, s: dict, ans: str) -> list[dict]:
    bad = []
    for n in (int(x) for x in re.findall(r"\d+", ans)):
        if n not in state_ints(s):
            bad.append({"token": str(n), "kind": "number"})
    names = state_names(loop, s)
    for m in re.finditer(r"[A-Z][a-z]+|[A-Z]{2,}", ans):
        w = m.group(0)
        if w not in names and w not in S2_ALLOW:
            bad.append({"token": w, "kind": "name"})
    return bad


def check_s2(loop, s: dict, case: dict, ans: str) -> tuple[bool, str]:
    exp = case["expect"]
    card = loop.self_card
    nums = [int(x) for x in re.findall(r"\d+", ans)]
    if exp == "identity-exact":
        ok = ans == SC161.IDENTITY
        return ok, "exact identity sentence"
    if exp == "canlist-exact":
        ok = ans == "I can: " + "; ".join(SC161.CAP_CAN) + "."
        return ok, "exact capability list"
    if exp == "cannotlist-exact":
        ok = ans == "I cannot: " + "; ".join(SC161.CAP_CANNOT) + "."
        return ok, "exact cannot list"
    if exp == "username-decline":
        return ("never told me your name" in ans,
                "user-name decline from empty notebook")
    if exp == "age-you-decline":
        return ("never told me your age" in ans, "user-age decline")
    if exp == "count-facts":
        ok = (s["n_taught"] in nums and s["n_quarantine"] in nums
              and "web" in ans)
        return ok, "taught + quarantine counts"
    if exp == "count-people":
        ok = (s["n_entities"] in nums
              and all(n in ans for n in s["entity_names"]))
        return ok, "entity count + names"
    if exp == "count-turns":
        return (nums == [s["turns"]], "turn count")
    if exp == "web0":
        return (0 in nums and "web" in ans, "zero web rows")
    if exp in ("belief-marker", "dream-marker", "opinion-marker",
               "future-marker", "reasons-marker"):
        return (R100.has_marker(ans), "plain-words marker")
    if exp == "sleep0":
        return ("slept 0" in ans, "zero sleeps")
    if exp in ("first-empty", "last-empty"):
        return ("not taught me anything yet" in ans, "empty-notebook edge")
    if exp == "first-fact":
        evs = card.taught_events()
        first = loop.nb.facts[evs[0]["fact_id"]]
        return (card.display(first) in ans, "first taught fact")
    if exp == "last-fact":
        evs = card.taught_events()
        last = loop.nb.facts[evs[-1]["fact_id"]]
        t = loop.self_origin.get(last["fact_id"], {}).get("turn", "?")
        return (card.display(last) in ans and t in nums,
                "last taught fact + turn")
    if exp == "prov-turn":
        name = card._known_entity_in(case["question"])
        rels = card._relations_in(case["question"])
        eid = loop.nb.resolve(name).detail["entity_id"]
        cur = loop.nb.current(eid, rels[0])
        t = loop.self_origin.get(cur[0]["fact_id"], {}).get("turn", "?")
        old_vals = [card.show(loop.nb.facts[o]["value"])
                    for o in loop.nb.superseded
                    if loop.nb.superseded[o] == cur[0]["fact_id"]]
        ok = (t in nums and "You did" in ans
              and all(v in ans for v in old_vals)
              and card.show(cur[0]["value"]) in ans)
        return ok, "origin turn + old/new values"
    if exp == "prov-missing":
        name = card._known_entity_in(case["question"])
        rels = card._relations_in(case["question"])
        eid = loop.nb.resolve(name).detail["entity_id"]
        cur = loop.nb.current(eid, rels[0])
        ok = (R100.has_marker(ans)
              and card.display(cur[0]) in ans)
        return ok, "no-record + current value"
    if exp == "confirm-yes":
        name = card._known_entity_in(case["question"])
        rels = card._relations_in(case["question"])
        eid = loop.nb.resolve(name).detail["entity_id"]
        cur = loop.nb.current(eid, rels[0])
        ok = (ans.startswith("Yes") and card.show(cur[0]["value"]) in ans
              and "Nothing you taught contradicts it" in ans)
        return ok, "confirm current value"
    if exp == "confirm-no":
        name = card._known_entity_in(case["question"])
        rels = card._relations_in(case["question"])
        eid = loop.nb.resolve(name).detail["entity_id"]
        cur = loop.nb.current(eid, rels[0])
        olds = [card.show(loop.nb.facts[o]["value"])
                for o, n in loop.nb.superseded.items()
                if n == cur[0]["fact_id"]]
        t = loop.self_origin.get(cur[0]["fact_id"], {}).get("turn", "?")
        ok = (ans.startswith("No") and card.show(cur[0]["value"]) in ans
              and all(v in ans for v in olds) and t in nums)
        return ok, "deny + correction trail"
    if exp == "speakers-named":
        name = card._known_entity_in(case["question"])
        ok = (name in ans and "has never spoken" in ans
              and s["turns"] in nums)
        return ok, "named non-speaker + turn count"
    if exp == "age-me":
        return (s["turns"] in nums and "turns ago" in ans, "agent age")
    if exp == "age-value":
        name = card._known_entity_in(case["question"])
        eid = loop.nb.resolve(name).detail["entity_id"]
        cur = loop.nb.current(eid, "age")
        return (card.show(cur[0]["value"]) in ans, "taught age value")
    if exp == "trail":
        name = card._known_entity_in(case["question"])
        rels = card._relations_in(case["question"])
        res = loop.nb.ask(name, rels[:3])
        hops = [card.display(loop.nb.facts[f])
                for f in res.detail.get("trail", [])]
        ok = (res.detail["answer"] in ans
              and all(h in ans for h in hops))
        return ok, "hop trail from notebook"
    if exp == "corrections-none":
        return ("not corrected anything" in ans, "no corrections yet")
    if exp == "corrections-one":
        olds = [(loop.nb.facts[o], loop.nb.facts[n])
                for o, n in loop.nb.superseded.items()]
        ok = (len(olds) == 1 and "1 thing" in ans
              and card.show(olds[0][0]["value"]) in ans
              and card.show(olds[0][1]["value"]) in ans)
        return ok, "single correction pair"
    if exp == "forgotten-none":
        return ("never asked me to forget" in ans, "no retractions")
    if exp == "decline-text":
        return (ans == SC161.CARD_DECLINE, "card-level decline")
    return False, f"unknown expect kind {exp}"


def build_state(tag: str, teaches: list[str], correction: str | None):
    st = ART / f"scratch-s2-{tag}"
    if st.exists():
        shutil.rmtree(st)
    loop = L161.build_agent161({"state_dir": str(st),
                                "sleep_threshold": 100000})
    for line in teaches:
        loop.turn(line)
    if correction:
        loop.turn(correction)
    return loop


def mark_s2() -> dict:
    doc = json.loads((ART / "cases161.json").read_text(encoding="utf-8"))
    teaches = doc["meta"]["teaches"]
    correction = doc["meta"]["correction"]
    loops = {"A": build_state("A", [], None),
             "B": build_state("B", teaches, None),
             "C": build_state("C", teaches, correction)}
    snaps = {k: snapshot(v) for k, v in loops.items()}
    per, wrong, halls = [], [], []
    for case in doc["cases"]:
        loop = loops[case["state"]]
        s = snaps[case["state"]]
        ans = loop.self_card.answer_self(case["question"])
        route = loop.self_card.route(case["question"])
        hall = hall_scan(loop, s, ans)
        if hall:
            halls.append({"id": case["id"], "hall": hall})
        ok, note = check_s2(loop, s, case, ans)
        if hall:
            ok, note = False, f"hallucination: {hall} // {note}"
        per.append({"id": case["id"], "state": case["state"],
                    "expect": case["expect"],
                    "question": case["question"], "route": route,
                    "answer": ans, "pass": ok, "note": note})
        if not ok:
            wrong.append(case["id"])
    return {"n": len(per), "wrong": len(wrong), "wrong_ids": wrong,
            "hallucinations": len(halls), "hall_ids": [h["id"] for h in halls],
            "pass": len(wrong) <= 2 and not halls, "per": per,
            "snapshots": snaps}


# ------------------------------------------------------------- S3 + S4
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


GATE = {"n_taught": 19, "n_entities": 6, "n_quarantine": 1,
        "n_superseded": 2, "n_forgotten": 1, "sleeps": 0, "turns": 26}


def mark_s3() -> dict:
    st = ART / "scratch-s3-panel"
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
    helper = facade(loop)
    gate_ok = all(helper.snapshot()[k] == v for k, v in GATE.items())
    panel = json.loads((ROOT / "artifacts" / "fable-self127panel-20260922"
                        / "panel.json").read_text(encoding="utf-8"))
    questions = panel["questions"] if isinstance(panel, dict) else panel
    assert len(questions) == 100, len(questions)
    per = []
    for q in questions:
        qid, group, intent, text, cls = R122.classify(q)
        said = loop.turn(text)
        ans = " ".join(said)
        routed = dict(loop.last_routed) if loop.last_routed else None
        s_live = facade(loop).snapshot()
        if gate_ok:
            verdict, note = R100.score(helper, qid, cls, ans, s_live)
        else:
            verdict, note = "WRONG", "session gate failed; run void"
        per.append({"id": qid, "group": group, "intent": intent,
                    "cls": cls, "question": text,
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
    return {"gate_ok": gate_ok, "n": 100, "wrong": len(wrong),
            "wrong_ids": [p["id"] for p in wrong], "by_group": by_group,
            "pass": len(wrong) <= 6, "per": per}


def mark_s4() -> dict:
    import fable_bench121_run as B  # noqa: E402 (items, read-only)
    items = [json.loads(line) for line in B.DATA_NEW.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    assert len(items) == 200, len(items)
    content, decline, routed_ids, decline_ids = 0, 0, [], []
    for it in items:
        tag = re.sub(r"[^A-Za-z0-9_-]+", "_", it["id"])
        loop = L161.build_agent161(
            {"state_dir": str(ART / "scratch-s4" / tag),
             "sleep_threshold": 100000})
        for t in it["taught"]:
            loop.turn(str(t["sentence_en"]))
        loop.turn(str(it["question"]))
        if loop.last_routed is not None:
            if loop.last_routed["intent"] == "DECLINE":
                decline += 1
                decline_ids.append(it["id"])
            else:
                content += 1
                routed_ids.append(
                    {"id": it["id"],
                     "intent": loop.last_routed["intent"],
                     "answer": loop.last_routed["answer"][:200]})
    shutil.rmtree(ART / "scratch-s4", ignore_errors=True)
    return {"n": 200, "content_routed": content, "routed_ids": routed_ids,
            "decline_served": decline, "decline_ids": decline_ids,
            "pass": content == 0}


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    out: dict = {}
    s1 = mark_s1()
    out["S1"] = s1
    print(f"S1 panel-nouns={s1['n_panel_nouns']} "
          f"intersections={s1['intersections']} "
          f"unlisted={s1['unlisted']} -> "
          f"{'PASS' if s1['pass'] else 'FAIL'}", flush=True)
    s2 = mark_s2()
    out["S2"] = s2
    print(f"S2 n={s2['n']} wrong={s2['wrong']} {s2['wrong_ids']} "
          f"hall={s2['hallucinations']} {s2['hall_ids']} -> "
          f"{'PASS' if s2['pass'] else 'FAIL'}", flush=True)
    for c in s2["per"]:
        if not c["pass"]:
            print(f"  S2-WRONG {c['id']} [{c['expect']}] route={c['route']} "
                  f"Q={c['question'][:70]}", flush=True)
            print(f"    A={c['answer'][:150]} ({c['note'][:130]})",
                  flush=True)
    s3 = mark_s3()
    out["S3"] = s3
    print(f"S3 n=100 wrong={s3['wrong']} {s3['wrong_ids']} "
          f"groups={s3['by_group']} gate={s3['gate_ok']} -> "
          f"{'PASS' if s3['pass'] else 'FAIL'}", flush=True)
    for p in s3["per"]:
        if p["verdict"] == "WRONG":
            print(f"  S3-WRONG {p['id']} [{p['group']}/{p['intent']}] "
                  f"routed={p['routed']} :: {p['question'][:75]}",
                  flush=True)
            print(f"    ans={p['answer'][:150]} ({p['note'][:120]})",
                  flush=True)
    s4 = mark_s4()
    out["S4"] = s4
    print(f"S4 n=200 content_routed={s4['content_routed']} "
          f"{s4['routed_ids']} decline_served={s4['decline_served']} -> "
          f"{'PASS' if s4['pass'] else 'FAIL'}", flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    out["pass"] = all(out[k]["pass"] for k in ("S1", "S2", "S3", "S4"))
    (ART / "selfcard161-marks.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"S1-S4 {out['seconds']}s -> "
          f"{'PASS' if out['pass'] else 'FAIL'}", flush=True)
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
