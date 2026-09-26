#!/usr/bin/env python3
"""bm-398e data (benchmarks thread, 2026-09-26): code-made chats in LoCoMo's own file layout, for fitting the
copy-only span trimmer. Nothing here is a benchmark item, a model output or a teacher's text: every chat,
question and answer is made by code from fixed word lists (claude_bm397t_data's, plus new ones below), with
fictional names. The answer is known by construction.

Unlike bm-397t's practice, the chats use the LoCoMo layout that claude_bm390.full_context renders
(speaker_a/b, session_N_date_time, session_N turns with dia_id), so the plain 1B's drafts to these questions are
written exactly as its LoCoMo drafts are. The question kinds are wider (the Mac report found bm-397t's too narrow):
  single  (category 4)  bm-397t's seven fact kinds
  why     (category 4)  a reason given for a move, a change or a choice ("because ..." answers)
  how     (category 4)  how someone travelled or did something ("by train", "with a friend's help")
  opinion (category 4)  what someone thought of something ("too slow", "really moving")
  when    (category 2)  today, yesterday, last week, two days ago, last month, last Saturday, this morning,
                        with the answer in several phrasings (a date, "the day before <date>", "the week before
                        <date>", "two days before <date>", "the month before <date>", "the Saturday before <date>")
  list    (category 1)  two to four items of one kind said in different sessions
Chats have 6-9 sessions with 12-18 turns each, so they run to a few thousand tokens.

  python -B scripts/claude_bm398e_data.py --seed 3980 --convs 40 --out made.json
  python -B scripts/claude_bm398e_data.py selftest
The output is a JSON list shaped like locomo10.json: {"sample_id", "conversation", "qa": [{"question", "answer",
"category", "kind", "evidence"}]}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm397t_data as P  # noqa: E402  (word lists only)

REASONS = ["the rent was much cheaper there", "the new job was too good to turn down", "it is closer to the sea",
           "the commute was wearing everyone out", "the schools there are better", "it is quieter at night",
           "the old flat had a leaking roof", "it is nearer the rest of the family"]
CHANGES = [("quit the choir", "quit the choir", "the rehearsals clashed with night shifts"),   # (said, asked, why)
           ("sold the car", "sell the car", "the bus goes everywhere now"),
           ("stopped drinking coffee", "stop drinking coffee", "it was ruining sleep"),
           ("switched to the early shift", "switch to the early shift", "the evenings are free that way"),
           ("gave up the allotment", "give up the allotment", "the plot flooded every spring")]
TRAVEL = [("the folk festival", "by train"), ("the coast", "on a borrowed bike"), ("the wedding", "by ferry"),
          ("the book fair", "on the night bus"), ("the mountain hut", "on foot"), ("the concert", "in a shared taxi")]
THINGS = [("new library building", "far too cold inside"), ("film about the lighthouse keeper", "slow but moving"),
          ("cooking class", "fun but chaotic"), ("museum's night opening", "worth every penny"),
          ("new bakery", "overpriced"), ("choir concert", "really moving"), ("hiking app", "confusing at first")]
WHEN = [  # (phrase in the chat, how the answer is written given the session date d)
    ("today", lambda d: P.fmt(d)), ("this morning", lambda d: P.fmt(d)),
    ("yesterday", lambda d: f"the day before {P.fmt(d)}"), ("yesterday", lambda d: P.fmt(d - dt.timedelta(days=1))),
    ("two days ago", lambda d: f"two days before {P.fmt(d)}"), ("last week", lambda d: f"the week before {P.fmt(d)}"),
    ("last month", lambda d: f"the month before {P.fmt(d)}"),
    ("last Saturday", lambda d: f"the Saturday before {P.fmt(d)}")]
LISTS = [(P.INSTRUMENTS, "instruments", "play", "I've started learning the {x}.", "Which instruments does {w} play?"),
         (P.SPORTS, "sports", "do", "I've taken up {x} this month.", "Which sports does {w} do?"),
         (P.DISHES, "dishes", "cook", "I cooked {x} for friends this weekend.", "What dishes has {w} cooked for friends?"),
         (P.TOWNS, "towns", "visit", "We spent a day in {x}, it was lovely.", "Which towns has {w} visited?")]


def _date_str(rng: random.Random, d: dt.date) -> str:
    h, m = rng.randint(1, 12), rng.choice([0, 5, 12, 20, 31, 45, 56])
    return f"{h}:{m:02d} {rng.choice(['am', 'pm'])} on {d.day} {P.MONTHS[d.month - 1]}, {d.year}"


def conversation(rng: random.Random, cid: str) -> dict:
    a, b = rng.sample(P.NAMES, 2)
    n_sess = rng.randint(6, 9)
    day = dt.date(rng.randint(2021, 2025), rng.randint(1, 12), rng.randint(1, 28))
    dates = []
    for _ in range(n_sess):
        dates.append(day)
        day = day + dt.timedelta(days=rng.randint(4, 25))
    placed: list[tuple[int, str, str, int]] = []   # (session, speaker, text, fact index)
    qs: list[dict] = []
    used: dict = {}

    def put(who: str, text: str, q: str, ans: str, kind: str, cat: int, s: int | None = None) -> None:
        k = len(qs)
        s = rng.randrange(n_sess) if s is None else s
        placed.append((s, who, text, k))
        qs.append({"question": q, "answer": ans, "category": cat, "kind": kind, "facts": [len(placed) - 1]})

    for who in (a, b):
        other = b if who == a else a
        for f in rng.sample(P._facts(rng, who, other, used), 3):
            put(who, f["said"], f["q"], f["a"], "single", 4)
        town, rel = rng.choice(P.TOWNS), rng.choice(P.RELATIONS)
        why = rng.choice(REASONS)
        put(who, f"My {rel} moved to {town} because {why}.", f"Why did {who}'s {rel} move to {town}?", why, "why", 4)
        said, asked, reason = rng.choice(CHANGES)
        put(who, f"I {said} because {reason}.", f"Why did {who} {asked}?", reason, "why", 4)
        place, mode = rng.choice(TRAVEL)
        put(who, f"I got to {place} {mode}, what an adventure.", f"How did {who} get to {place}?", mode, "how", 4)
        thing, view = rng.choice(THINGS)
        put(who, f"The {thing} was {view}.", f"What did {who} think of the {thing}?", view, "opinion", 4)
        ev, ev_q = rng.choice(P.EVENTS)
        phrase, ans = rng.choice(WHEN)
        s = rng.randrange(n_sess)
        text = {"today": f"Guess what, today I {ev}!", "this morning": f"This morning I {ev}!",
                "yesterday": f"Yesterday I {ev}!", "two days ago": f"Two days ago I {ev}.",
                "last week": f"Last week I {ev}.", "last month": f"Last month I {ev}.",
                "last Saturday": f"Last Saturday I {ev}."}[phrase]
        put(who, text, f"When did {who} {ev_q}?", ans(dates[s]), "when", 2, s)
        pool, noun, verb, tmpl, qt = rng.choice(LISTS)
        n_items = rng.randint(2, 4)
        free = [p for p in pool if p not in used.setdefault("list:" + noun, set())] or list(pool)
        items = rng.sample(free, min(n_items, len(free)))
        used["list:" + noun].update(items)
        sess = sorted(rng.sample(range(n_sess), min(len(items), n_sess)))
        k = len(qs)
        facts = []
        for x, s in zip(items, sess):
            placed.append((s, who, tmpl.format(x=x), k))
            facts.append(len(placed) - 1)
        qs.append({"question": qt.format(w=who), "answer": ", ".join(items), "category": 1, "kind": "list",
                   "facts": facts})
    conv = {"speaker_a": a, "speaker_b": b}
    evidence: dict[int, str] = {}
    for s in range(n_sess):
        mine = [(w, t, i) for i, (ss, w, t, _k) in enumerate(placed) if ss == s]
        turns = [(None, rng.choice(P.FILLER), None) for _ in range(rng.randint(12, 18))]
        for fact in mine:
            turns.insert(rng.randint(0, len(turns)), fact)
        spk, body = rng.choice([a, b]), []
        for w, t, i in turns:
            if w is not None and w != spk:
                body.append({"speaker": spk, "dia_id": f"D{s + 1}:{len(body) + 1}", "text": rng.choice(P.FILLER)})
                spk = w
            body.append({"speaker": spk, "dia_id": f"D{s + 1}:{len(body) + 1}", "text": t})
            if i is not None:
                evidence[i] = body[-1]["dia_id"]
            spk = b if spk == a else a
        conv[f"session_{s + 1}_date_time"] = _date_str(rng, dates[s])
        conv[f"session_{s + 1}"] = body
    qa = [{"question": q["question"], "answer": q["answer"], "category": q["category"], "kind": q["kind"],
           "evidence": [evidence[i] for i in q["facts"]]} for q in qs]
    rng.shuffle(qa)
    return {"sample_id": cid, "conversation": conv, "qa": qa}


def build(seed: int, convs: int) -> list[dict]:
    rng = random.Random(seed)
    return [conversation(rng, f"m{seed}c{c:03d}") for c in range(convs)]


def selftest() -> None:
    import claude_bm390 as B
    ok = {}
    data = build(1, 6)
    ok["same seed, same data"] = json.dumps(build(1, 6)) == json.dumps(data)
    ok["LoCoMo layout renders"] = all(len(B.sessions(c)) >= 6 and B.full_context(c).count("DATE: ") >= 6 for c in data)
    kinds = {q["kind"] for c in data for q in c["qa"]}
    ok["all six kinds present"] = kinds == {"single", "why", "how", "opinion", "when", "list"}
    ids = {t["dia_id"]: t["text"] for c in data for _, ts in B.sessions(c) for t in ts}
    ok["every evidence line exists"] = all(e in ids for c in data for q in c["qa"] for e in q["evidence"])
    ok["single, why, how and opinion answers are said in their evidence line"] = all(
        q["answer"].lower() in " ".join(
            t["text"] for _, ts in B.sessions(c) for t in ts if t["dia_id"] in q["evidence"]).lower()
        for c in data for q in c["qa"] if q["kind"] in ("single", "why", "how", "opinion"))
    ok["list answers name 2-4 items, one evidence line each"] = all(
        2 <= len(q["answer"].split(", ")) <= 4 and len(q["evidence"]) == len(q["answer"].split(", "))
        for c in data for q in c["qa"] if q["kind"] == "list")
    ok["categories are 1, 2 or 4"] = {q["category"] for c in data for q in c["qa"]} <= {1, 2, 4}
    names = {c["conversation"]["speaker_a"] for c in data} | {c["conversation"]["speaker_b"] for c in data}
    ok["names come from the fictional list"] = names <= set(P.NAMES)
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398E-DATA-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="build", choices=["build", "selftest"])
    ap.add_argument("--seed", type=int, default=3980)
    ap.add_argument("--convs", type=int, default=40)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
        return 0
    data = build(a.seed, a.convs)
    Path(a.out).write_text(json.dumps(data), encoding="utf-8")
    print(json.dumps({"convs": len(data), "questions": sum(len(c["qa"]) for c in data)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
