#!/usr/bin/env python3
"""bm-398r data (benchmarks thread, 2026-09-26): code-made practice for the evidence-trained reader adapter.

bm-398d showed that the plain 1B loses right answers both when it must find the right lines in a whole LoCoMo chat
(whole chat 109 of 297 blind-right, the right lines alone 137) and when it reads the right lines (160 of 297 still
not fully right; dates 17%, multi-part 23%). bm-397t's practice was short (median 1.6k tokens against LoCoMo's
~24k), had three question kinds and one date template, and taught brevity rather than right answers. This file makes
practice that targets the losses instead. Everything is made by code from word lists with fictional names; no
benchmark item, model output, teacher or Claude-written text is used. Every answer is known by construction.

Chats: 22-38 dated sessions of 22-36 turns of one to three sentences, about 15k-28k tokens in the bm-390 layout
(median about 21k; LoCoMo's are 14k-26k, median 24k), in LoCoMo's own file layout. Small talk comes from a template grammar (thousands of distinct lines, not a short list).
Each speaker gets about 14 facts of the same kinds with different values, plus facts about named relatives, so the
right answer always sits beside look-alike lines about the other speaker or someone else.

Question kinds (category as LoCoMo numbers them):
  single   (4)  one stated fact (job, pet's name, bought, went with, favourite dish, where a relative lives, book,
                club, volunteering place)
  why      (4)  the reason given for a move or a change
  how      (4)  how someone got somewhere
  opinion  (4)  what someone thought of something
  current  (4)  where someone lives now, after moving twice (the old town is a look-alike)
  before   (1)  where someone lived before the second move (two lines, two sessions)
  choice   (4)  what someone chose after nearly choosing something else (the rejected one is a look-alike)
  when     (2)  a dated event, said as today, this morning, yesterday, two days ago, last <weekday>, last weekend,
                last week, a couple of weeks ago, last month or last year; the answer is the calendar date when
                one day is meant ("7 May 2023"), else "the week before 9 June 2023", "the weekend before ...",
                "two weeks before ...", "May 2023" or "2022"
  list     (1)  two to five things of one kind said in different sessions, "a, b, c" in the order they were said
  multihop (1)  a relative is named in one session and that person's news comes in another
  missing  (5)  a fact the other speaker has but this one never gave: "Not mentioned in the conversation"
Held out for the dev set only (report only; never in training): half of the names, towns, pet names and events
(split by position), the phrasings "the day before yesterday" and "three days ago", and one question wording for
single, why, how and opinion questions.

Layouts of one example (the answer target is the same in all three):
  whole  the bm-390 harness input: claude_bm390.full_context + QA_PROMPT (with its category-2 date hint), system
         LOCOMO_SYSTEM. This is the input T and Qwen's whole-chat rows use.
  alt    bm-397t's layout ("[Session n - date]", "Name: text") with one of its six instructions, so the adapter is
         not tied to one wording.
  lines  bm-395's store layout (claude_bm398d_evidence.context): the evidence lines alone, or with other lines of
         the same chat up to 10 or 20 (look-alike facts first), then QA_PROMPT. This is the input of G, GD and E20.
Per chat: 3 whole + 1 alt + 8 lines examples (12 questions), drawn in a random order that puts date and multi-part
questions (when, list, multihop, before) first three times as often as the rest.

  python -B scripts/claude_bm398r_data.py --part train --seed 3990 --convs 150 --out train.jsonl
  python -B scripts/claude_bm398r_data.py --part dev --seed 3991 --convs 20 --out dev.jsonl
  python -B scripts/claude_bm398r_data.py selftest
Each line: {"id", "system", "user", "answer", "kind", "category", "layout"}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm397t_data as P  # noqa: E402  (word lists, layout of the alt examples)
import claude_bm398d_evidence as D  # noqa: E402  (store layout)
import claude_bm398e_data as E  # noqa: E402  (reasons, travel, opinions, changes)

N_SESS, N_TURNS = (22, 38), (22, 36)
PER_CHAT = {"whole": 3, "alt": 1, "lines": 8}
PRIORITY = 3.0
MISSING_ANSWER = "Not mentioned in the conversation"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

EXTRA_TOWNS = ["Coldharbour", "Pennick", "Ravensworth", "Tillmouth", "Oakridge Vale", "Saltmarsh", "Brindle",
               "Hollowcombe", "Westerby", "Carrow", "Dunmere", "Skelby"]
EXTRA_EVENTS = [("repainted the front door", "repaint the front door"), ("swam in the lake", "swim in the lake"),
                ("fixed the old radio", "fix the old radio"), ("climbed Beacon Hill", "climb Beacon Hill"),
                ("ran the charity fun run", "run the charity fun run"), ("learned to juggle", "learn to juggle"),
                ("sold my first painting", "sell a painting"), ("hosted a board game night", "host a board game night"),
                ("visited the planetarium", "visit the planetarium"), ("built a bird box", "build a bird box")]
BOOKS = ["The Salt Road", "Winter Orchard", "A Map of Small Hours", "The Glass Heron", "Nine Lanterns",
         "The Quiet Engine", "Harbour Lights", "The Paper Fox", "Under the Linden", "The Long Tide"]
CLUBS = ["chess club", "running club", "choir", "book club", "pottery group", "cycling club", "quiz team",
         "gardening club", "film society", "swimming club"]
VOLUNTEER = ["the animal shelter", "the food bank", "the community garden", "the children's library",
             "the charity shop", "the river clean-up group", "the youth football club", "the care home"]
PETS = [("cat", "dog"), ("rabbit", "hamster"), ("parrot", "budgie"), ("tortoise", "ferret"), ("dog", "cat"),
        ("goldfish", "guinea pig")]
CHOICES = [("for the new flat", "a sofa", "two armchairs"), ("for the camping trip", "a tent", "a hammock"),
           ("for my commute", "an electric scooter", "a folding bike"), ("for the garden", "a pizza oven",
           "a barbecue"), ("for my niece's birthday", "a kite", "a telescope"), ("for the kitchen", "a toaster",
           "a waffle maker"), ("for the winter", "a wool coat", "a down jacket"), ("for the hallway", "a mirror",
           "a coat stand")]
FILL = {
    "feel": ["tired", "a bit flat", "really cheerful", "stressed", "oddly calm", "full of energy", "sleepy",
             "restless", "pretty good", "worn out"],
    "why_small": ["work ran late", "I slept badly", "the sun finally came out", "the kids were up early",
                  "I skipped lunch", "the heating broke again", "I had a long call with the bank",
                  "the neighbours had a party", "I drank too much tea", "the deadline moved"],
    "weather": ["rainy", "windy", "freezing", "muggy", "grey", "bright but cold", "stormy", "mild", "foggy"],
    "show": ["that baking competition", "the new detective series", "a documentary about glaciers",
             "the quiz show", "an old western", "a cartoon with my niece", "the late film",
             "a series about deep-sea divers", "a nature programme about owls"],
    "snack": ["toast with jam", "a bowl of noodles", "leftover rice", "a cheese sandwich", "porridge", "a pear",
              "some crackers", "a big salad", "beans on toast"],
    "chore": ["sorted the laundry", "fixed the squeaky door", "cleared out the fridge", "washed the windows",
              "paid the bills", "tidied the shed", "ironed a mountain of shirts", "defrosted the freezer",
              "swept the yard"],
    "commute": ["The bus", "The tram", "The train", "The ring road", "The ferry", "The underground"],
    "commute_adj": ["packed", "late again", "surprisingly quiet", "cancelled", "freezing", "full of students"],
    "react": ["That sounds lovely!", "Oh no, that's rough.", "Ha, classic.", "Nice one!", "I can imagine.",
              "Sounds like a lot.", "Good for you!", "That's so annoying.", "Wow, really?", "Fair enough.",
              "I love that.", "Same here, honestly."],
    "ask": ["How was your week?", "What have you been up to?", "Any plans for the weekend?",
            "How are things at work?", "Did you sleep better?", "How's the family?", "Seen anything good lately?",
            "How was the weekend?", "What's new with you?"],
    "plan": ["probably stay in and rest", "maybe see a film", "clean the flat, sadly", "walk along the river",
             "try a new recipe", "go for a long walk", "catch up on sleep", "finish a jigsaw", "sort my photos"],
    "gadget": ["My phone", "The washing machine", "My old laptop", "The car radio", "The printer", "My bike lock",
               "The kettle"],
    "broke": ["stopped working", "is making a weird noise", "finally died", "keeps freezing", "needs a new part"],
    "podcast": ["about old maps", "about space missions", "on gardening", "about famous trials",
                "on bread baking", "about sea birds", "about forgotten inventors"],
    "work_adj": ["hectic", "slow", "fine", "a bit chaotic", "better than last month", "all meetings"],
    "local": ["new roundabout", "roadworks on the high street", "power cut", "school bake sale",
              "lost dog posters", "summer fair"],
    "thought": ["I should drink more water", "I need a proper holiday", "we should all walk more",
                "I should call my old friends more", "I'd like to learn another language"],
    "caption": ["a photo of a sunset over the water", "a photo of a cup of coffee", "a photo of a rainy street",
                "a photo of a messy desk", "a photo of a cake", "a photo of a dog in a park",
                "a photo of a mountain path", "a photo of a bookshelf"],
}
TEMPLATES = ["I'm feeling {feel} today, {why_small}.", "It's been so {weather} here all week.",
             "I watched {show} last night.", "I had {snack} for lunch, nothing exciting.", "I finally {chore}.",
             "{commute} was {commute_adj} this morning.", "{ask}", "{react}", "This weekend I'll {plan}.",
             "{gadget} {broke}, so annoying.", "I've been listening to a podcast {podcast}.",
             "Work has been {work_adj} lately.", "Did you hear about the {local}?",
             "I keep thinking {thought}.", "Honestly, {thought}."]
# question wordings: the last one of each list is held out for the dev set
QW = {
    "moved": ["Where did {w} move to?", "Which town did {w} move to?"],
    "job": ["What job did {w} start?", "What is {w}'s new job?"],
    "pet": ["What is the name of {w}'s {x}?", "What did {w} name the {x}?"],
    "bought": ["What did {w} buy at the Saturday market?", "What did {w} pick up at the Saturday market?"],
    "with": ["Who did {w} go {x} with?", "Who went {x} with {w}?"],
    "dish": ["What is {w}'s favourite dish?", "Which dish does {w} like best?"],
    "rel_lives": ["Where does {w}'s {x} live?", "In which town does {w}'s {x} live?"],
    "book": ["What book is {w} reading?", "Which novel was {w} reading?"],
    "club": ["What did {w} join?", "Which group did {w} join?"],
    "volunteer": ["Where does {w} volunteer?", "Where does {w} help out on Sundays?"],
    "why_move": ["Why did {w}'s {x} move to {y}?", "What made {w}'s {x} move to {y}?"],
    "why_change": ["Why did {w} {x}?", "What was {w}'s reason to {x}?"],
    "how": ["How did {w} get to {x}?", "How did {w} travel to {x}?"],
    "opinion": ["What did {w} think of the {x}?", "How did {w} find the {x}?"],
}


def half(pool: list, part: str) -> list:
    return list(pool[0::2]) if part == "train" else list(pool[1::2])


def filler(rng: random.Random) -> str:
    def one() -> str:
        t = rng.choice(TEMPLATES)
        return re.sub(r"\{(\w+)\}", lambda m: rng.choice(FILL[m.group(1)]), t)
    x = rng.random()
    return one() if x < 0.35 else one() + " " + one() if x < 0.75 else one() + " " + one() + " " + one()


def when_answer(phrase: str, d: dt.date) -> str:
    if phrase in ("today", "this morning"):
        return P.fmt(d)
    if phrase == "yesterday":
        return P.fmt(d - dt.timedelta(days=1))
    if phrase in ("two days ago", "the day before yesterday"):
        return P.fmt(d - dt.timedelta(days=2))
    if phrase == "three days ago":
        return P.fmt(d - dt.timedelta(days=3))
    if phrase.startswith("last ") and phrase[5:] in WEEKDAYS:
        back = (d.weekday() - WEEKDAYS.index(phrase[5:])) % 7 or 7
        return P.fmt(d - dt.timedelta(days=back))
    if phrase == "last weekend":
        return f"the weekend before {P.fmt(d)}"
    if phrase == "last week":
        return f"the week before {P.fmt(d)}"
    if phrase == "a couple of weeks ago":
        return f"two weeks before {P.fmt(d)}"
    if phrase == "last month":
        m = d.replace(day=1) - dt.timedelta(days=1)
        return f"{P.MONTHS[m.month - 1]} {m.year}"
    if phrase == "last year":
        return str(d.year - 1)
    raise ValueError(phrase)


def when_phrases(part: str) -> list[str]:
    common = ["today", "this morning", "yesterday", "two days ago", "last weekend", "last week",
              "a couple of weeks ago", "last month", "last year"] + [f"last {w}" for w in WEEKDAYS]
    return common if part == "train" else common + ["the day before yesterday", "three days ago"]


def conversation(rng: random.Random, cid: str, part: str) -> dict:
    names = half(P.NAMES, part)
    towns = half(P.TOWNS + EXTRA_TOWNS, part)
    petnames = half(P.PETNAMES, part)
    events = half(P.EVENTS + EXTRA_EVENTS, part)
    qpick = (lambda k: rng.choice(QW[k][:-1])) if part == "train" else (lambda k: QW[k][-1])
    a, b = rng.sample(names, 2)
    n_sess = rng.randint(*N_SESS)
    day = dt.date(rng.randint(2020, 2025), rng.randint(1, 12), rng.randint(1, 28))
    dates = []
    for _ in range(n_sess):
        dates.append(day)
        day = day + dt.timedelta(days=rng.randint(3, 20))
    placed: list[list] = []          # [session, speaker, text]
    qs: list[dict] = []
    used: dict = {}

    def relation(who) -> str:
        return take(P.RELATIONS, "rel:" + who)       # each relation once per speaker, so no two facts share one

    def take(pool, key):
        free = [x for x in pool if x not in used.setdefault(key, set())] or list(pool)
        x = rng.choice(free)
        used[key].add(x)
        return x

    def put(who, text, s=None) -> int:
        placed.append([rng.randrange(n_sess) if s is None else s, who, text])
        return len(placed) - 1

    def ask(q, ans, kind, cat, lines):
        qs.append({"question": q, "answer": ans, "category": cat, "kind": kind, "lines": list(lines)})

    others = [n for n in names if n not in (a, b)]
    has_pet = {a: False, b: False}
    for who in (a, b):
        # single facts (four of ten, fixed per speaker)
        singles = rng.sample(["job", "pet", "bought", "with", "dish", "rel_lives", "book", "club", "volunteer"], 4)
        for k in singles:
            if k == "job":
                j = take(P.JOBS, "job")
                ask(qpick(k).format(w=who), j, "single", 4,
                    [put(who, f"I started a new job as a {j} at {rng.choice(P.PLACES)}.")])
            elif k == "pet":
                an, pn = take(P.ANIMALS, "animal"), take(petnames, "pet")
                ask(qpick(k).format(w=who, x=an), pn, "single", 4,
                    [put(who, f"We adopted a {an} and named it {pn}.")])
                has_pet[who] = True
            elif k == "bought":
                it = take(P.ITEMS, "item")
                ask(qpick(k).format(w=who), it, "single", 4, [put(who, f"I bought a {it} at the Saturday market.")])
            elif k == "with":
                act, fr, rel = take(P.ACTIVITIES, "act"), take(others, "friend"), relation(who)
                ask(qpick(k).format(w=who, x=act), fr, "single", 4,
                    [put(who, f"I went {act} with my {rel} {fr} last weekend.")])
            elif k == "dish":
                di = take(P.DISHES, "dish")
                ask(qpick(k).format(w=who), di, "single", 4, [put(who, f"Honestly my favourite dish is {di}.")])
            elif k == "rel_lives":
                rel, t = relation(who), take(towns, "town")
                ask(qpick(k).format(w=who, x=rel), t, "single", 4,
                    [put(who, f"My {rel} lives in {t}, I visit whenever I can.")])
            elif k == "book":
                bk = take(BOOKS, "book")
                ask(qpick(k).format(w=who), bk, "single", 4,
                    [put(who, f"I'm reading a novel called {bk}, it's gripping.")])
            elif k == "club":
                cl = take(CLUBS, "club")
                ask(qpick(k).format(w=who), f"the {cl}" if cl != "choir" else "a choir", "single", 4,
                    [put(who, f"I joined {'a choir' if cl == 'choir' else 'the ' + cl} this month.")])
            else:
                vo = take(VOLUNTEER, "vol")
                ask(qpick(k).format(w=who), vo, "single", 4,
                    [put(who, f"I volunteer at {vo} on Sundays now.")])
        # why (a relative's move, or a change), how, opinion
        if rng.random() < 0.5:
            rel, t, why = relation(who), take(towns, "town"), rng.choice(E.REASONS)
            ask(qpick("why_move").format(w=who, x=rel, y=t), why, "why", 4,
                [put(who, f"My {rel} moved to {t} because {why}.")])
        else:
            said, asked, reason = rng.choice(E.CHANGES)
            ask(qpick("why_change").format(w=who, x=asked), reason, "why", 4,
                [put(who, f"I {said} because {reason}.")])
        place, mode = rng.choice(E.TRAVEL)
        ask(qpick("how").format(w=who, x=place), mode, "how", 4,
            [put(who, f"I got to {place} {mode}, what an adventure.")])
        thing, view = rng.choice(E.THINGS)
        ask(qpick("opinion").format(w=who, x=thing), view, "opinion", 4, [put(who, f"The {thing} was {view}.")])
        # current vs former home (two sessions, in order)
        s1, s2 = sorted(rng.sample(range(n_sess), 2))
        t1, t2 = take(towns, "town"), take(towns, "town")
        l1 = put(who, f"We've settled into our flat in {t1} at last.", s1)
        l2 = put(who, f"We moved again, we're living in {t2} now.", s2)
        if rng.random() < 0.6:
            ask(f"Where does {who} live now?", t2, "current", 4, [l2])
        else:
            ask(f"Where did {who} live before moving to {t2}?", t1, "before", 1, [l1, l2])
        # a choice after nearly choosing something else
        if not has_pet[who] and rng.random() < 0.4:
            x, y = rng.choice(PETS)
            ask(f"What pet did {who} get in the end?", f"a {y}", "choice", 4,
                [put(who, f"We nearly got a {x}, but in the end we got a {y}.")])
            has_pet[who] = True
        else:
            (for_said, x, y) = take(CHOICES, "choice")
            ask(f"What did {who} end up buying {for_said}?", y, "choice", 4,
                [put(who, f"I almost bought {x} {for_said}, but I went with {y} instead.")])
        # two dated events
        for _ in range(2):
            (ev, ev_q), phrase = take(events, "event"), rng.choice(when_phrases(part))
            s = rng.randrange(n_sess)
            lead = {"today": "Guess what, today I", "this morning": "This morning I", "yesterday": "Yesterday I",
                    "the day before yesterday": "The day before yesterday I"}.get(phrase)
            text = f"{lead} {ev}!" if lead else f"{phrase[0].upper() + phrase[1:]} I {ev}."
            ask(f"When did {who} {ev_q}?", when_answer(phrase, dates[s]), "when", 2, [put(who, text, s)])
            qs[-1]["phrase"] = phrase
        # a list of 2-5 over different sessions
        pool, noun, _verb, tmpl, qt = rng.choice(E.LISTS)
        pool = towns if noun == "towns" else pool
        free = [p for p in pool if p not in used.setdefault("list:" + noun, set())] or list(pool)
        items = rng.sample(free, min(rng.randint(2, 5), len(free)))
        used["list:" + noun].update(items)
        said = sorted(zip(rng.sample(range(n_sess), len(items)), items))     # the answer lists them in chat order
        ask(qt.format(w=who), ", ".join(x for _s, x in said), "list", 1,
            [put(who, tmpl.format(x=x), s) for s, x in said])
        # multihop: a named relative, then that person's news in a later session
        rel, rn = relation(who), take(others, "friend")
        s1, s2 = sorted(rng.sample(range(n_sess), 2))
        l1 = put(who, f"My {rel} {rn} came over for dinner.", s1)
        if rng.random() < 0.5:
            j = take(P.JOBS, "job")
            ask(f"What job did {who}'s {rel} start?", j, "multihop", 1,
                [l1, put(who, f"{rn} just started working as a {j}.", s2)])
        else:
            t = take(towns, "town")
            ask(f"Where did {who}'s {rel} move?", t, "multihop", 1,
                [l1, put(who, f"{rn} has moved to {t}, can you believe it.", s2)])
    # missing: a pet's name only the other speaker gave, asked about the speaker with no pet
    if has_pet[a] != has_pet[b] and rng.random() < 0.5:
        ask(f"What is the name of {b if has_pet[a] else a}'s pet?", MISSING_ANSWER, "missing", 5, [])
    # lay out the sessions
    conv = {"speaker_a": a, "speaker_b": b}
    line_id: dict[int, str] = {}
    for s in range(n_sess):
        mine = [(w, t, i) for i, (ss, w, t) in enumerate(placed) if ss == s]
        turns = [(None, filler(rng), None) for _ in range(rng.randint(*N_TURNS))]
        for f in mine:
            turns.insert(rng.randint(0, len(turns)), f)
        spk, body = rng.choice([a, b]), []
        for w, t, i in turns:
            if w is not None and w != spk:
                body.append({"speaker": spk, "dia_id": f"D{s + 1}:{len(body) + 1}", "text": filler(rng)})
                spk = w
            turn = {"speaker": spk, "dia_id": f"D{s + 1}:{len(body) + 1}", "text": t}
            if i is None and rng.random() < 0.05:
                turn["blip_caption"] = rng.choice(FILL["caption"])
            body.append(turn)
            if i is not None:
                line_id[i] = turn["dia_id"]
            spk = b if spk == a else a
        conv[f"session_{s + 1}_date_time"] = E._date_str(rng, dates[s])
        conv[f"session_{s + 1}"] = body
    qa = [{"question": q["question"], "answer": q["answer"], "category": q["category"], "kind": q["kind"],
           "evidence": [line_id[i] for i in q["lines"]], **({"phrase": q["phrase"]} if "phrase" in q else {})}
          for q in qs]
    return {"sample_id": cid, "conversation": conv, "qa": qa}


def alt_text(c: dict) -> str:
    conv, lines = c["conversation"], []
    for n, (date, turns) in enumerate(B.sessions(c)):
        d = date.split(" on ")[-1].replace(",", "")
        lines.append(f"[Session {n + 1} - {d}]\n" + "\n".join(f"{t['speaker']}: {t['text']}" for t in turns))
    return f"Chat log between {conv['speaker_a']} and {conv['speaker_b']}.\n\n" + "\n\n".join(lines)


def lines_positions(rng: random.Random, c: dict, qa: dict, items: list) -> list[int]:
    ev = D.evidence(c, qa)
    want = rng.choice([len(ev), 10, 20]) if ev else rng.choice([10, 20])   # a missing question still gets lines
    look = [p for p, it in enumerate(items) if p not in ev and any(
        w in it[2]["text"] for w in (" moved ", " lives in ", " named it ", " bought ", " started ", " joined ",
                                     " went ", " because ", " got to ", " nearly ", " almost "))]
    rest = [p for p in range(len(items)) if p not in ev and p not in look]
    rng.shuffle(look)
    rng.shuffle(rest)
    return sorted(ev + (look + rest)[:max(0, want - len(ev))])


def examples(c: dict, rng: random.Random) -> list[dict]:
    # dates and multi-part questions first more often (bm-398d: the 1B reads them worst): a weighted random order
    w = {q: PRIORITY if c["qa"][q]["kind"] in ("when", "list", "multihop", "before") else 1.0
         for q in range(len(c["qa"]))}
    order = sorted(w, key=lambda q: -(rng.random() ** (1.0 / w[q])))
    # the missing question, when present, goes to a lines example so whole-chat examples stay answerable
    miss = [i for i in order if c["qa"][i]["kind"] == "missing"]
    order = [i for i in order if i not in miss]
    n_long = PER_CHAT["whole"] + PER_CHAT["alt"]
    plan = [(i, "whole") for i in order[:PER_CHAT["whole"]]] + [(i, "alt") for i in order[PER_CHAT["whole"]:n_long]]
    rest = miss + order[n_long:]
    plan += [(i, "lines") for i in rest[:PER_CHAT["lines"]]]
    items = D.items_of(c)
    out = []
    for i, layout in plan:
        qa = c["qa"][i]
        if layout == "alt":
            system = rng.choice(P.SYSTEMS)
            user = alt_text(c) + "\n\n" + rng.choice(P.INSTRUCTIONS).format(q=qa["question"])
        else:
            ctx = B.full_context(c) if layout == "whole" else D.context(c, items, lines_positions(rng, c, qa, items))
            system = B.LOCOMO_SYSTEM
            user = ctx + "\n\n" + B.QA_PROMPT.format(B.question_text(c["sample_id"], i, {**qa, "category": min(
                qa["category"], 4)}))
        out.append({"id": f"{c['sample_id']}#{i}", "system": system, "user": user, "answer": qa["answer"],
                    "kind": qa["kind"], "category": qa["category"], "layout": layout})
    return out


def build(part: str, seed: int, convs: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    chats = [conversation(rng, f"r{seed}c{n:03d}", part) for n in range(convs)]
    return chats, [row for c in chats for row in examples(c, rng)]


def selftest() -> None:
    ok = {}
    chats, rows = build("train", 5, 8)
    dchats, drows = build("dev", 6, 8)
    ok["same seed, same data"] = json.dumps(build("train", 5, 8)[1]) == json.dumps(rows)
    ok["12 examples a chat: 3 whole, 1 alt, 8 lines"] = all(
        [r["layout"] for r in rows if r["id"].startswith(c["sample_id"] + "#")].count(x) == n
        for c in chats for x, n in PER_CHAT.items())
    ids = {t["dia_id"]: t["text"] for c in chats for _, ts in B.sessions(c) for t in ts}
    ok["every evidence line exists"] = all(e in ids for c in chats for q in c["qa"] for e in q["evidence"])
    said = lambda c, q: " ".join(t["text"] for _, ts in B.sessions(c) for t in ts if t["dia_id"] in q["evidence"])
    ok["copied answers are said in their evidence lines"] = all(
        all(part.lower() in said(c, q).lower() for part in q["answer"].split(", "))
        for c in chats + dchats for q in c["qa"] if q["kind"] not in ("when", "missing"))
    d = dt.date(2023, 6, 9)   # a Friday
    ok["date answers"] = (when_answer("yesterday", d) == "8 June 2023" and when_answer("last Friday", d) == "2 June 2023"
                          and when_answer("last Thursday", d) == "8 June 2023"
                          and when_answer("last month", d) == "May 2023" and when_answer("last year", d) == "2022"
                          and when_answer("last week", d) == "the week before 9 June 2023"
                          and when_answer("three days ago", d) == "6 June 2023"
                          and when_answer("last month", dt.date(2023, 1, 3)) == "December 2022")
    ok["when answers match their line's session date and phrase"] = all(
        when_answer(q["phrase"], dt.datetime.strptime(date.split(" on ")[-1], "%d %B, %Y").date()) == q["answer"]
        and q["phrase"].lower() in t["text"].lower()
        for c in chats + dchats for q in c["qa"] if q["kind"] == "when"
        for date, ts in B.sessions(c) for t in ts if t["dia_id"] == q["evidence"][0])
    tr_names = {c["conversation"][k] for c in chats for k in ("speaker_a", "speaker_b")}
    dv_names = {c["conversation"][k] for c in dchats for k in ("speaker_a", "speaker_b")}
    ok["train and dev names are disjoint"] = not (tr_names & dv_names) and tr_names <= set(P.NAMES)
    big_chats, big_tr = build("train", 7, 40)
    rx = lambda t: re.compile(re.sub(r"\\\{\w\\\}", ".+", re.escape(t)) + "$")
    held = [rx(QW[k][-1]) for k in QW]
    kept = [rx(v) for k in QW for v in QW[k][:-1]]
    ok["held-out wordings and phrasings never in train"] = not any(
        x in r["user"] for r in big_tr for x in ("day before yesterday", "hree days ago")) and not any(
        h.match(q["question"]) and not any(k.match(q["question"]) for k in kept)
        for c in big_chats for q in c["qa"] for h in held)
    ok["dev uses the held-out wordings"] = any(h.match(q["question"]) for c in dchats for q in c["qa"] for h in held)
    rels = [(c["sample_id"], w, r) for c in big_chats for q in c["qa"] for w in (c["conversation"]["speaker_a"],
            c["conversation"]["speaker_b"]) for r in P.RELATIONS if q["question"].startswith(("Where did " + w + "'s " + r + " ", "Why did " + w + "'s " + r + " ", "Where does " + w + "'s " + r + " ", "What job did " + w + "'s " + r + " "))]
    ok["one fact per relative"] = len(rels) == len(set(rels))
    kinds = {r["kind"] for r in big_tr}
    ok["all kinds present"] = kinds == {"single", "why", "how", "opinion", "current", "before", "choice", "when",
                                        "list", "multihop", "missing"}
    c0 = chats[0]
    by_id = {c["sample_id"]: c for c in chats}
    ok["whole layout is the bm-390 harness input"] = all(
        r["user"].startswith(B.full_context(by_id[r["id"].split("#")[0]])) and r["system"] == B.LOCOMO_SYSTEM
        and r["user"].endswith(B.QA_PROMPT.format(B.question_text("x", 0, {**by_id[r["id"].split("#")[0]]["qa"][
            int(r["id"].split("#")[1])], "category": min(4, r["category"])})))
        for r in rows if r["layout"] == "whole")
    ok["lines examples hold every evidence line"] = all(
        all(B.turn_text(t) in r["user"] for c in chats if r["id"].startswith(c["sample_id"] + "#")
            for _, ts in B.sessions(c) for t in ts if t["dia_id"] in c["qa"][int(r["id"].split("#")[1])]["evidence"])
        for r in rows if r["layout"] == "lines")
    ok["missing questions get 10 or 20 lines"] = all(r["user"].count(' said, "') in (10, 20)
                                                     for r in big_tr if r["kind"] == "missing")
    ok["date hint on category-2 questions only"] = all(
        (B.CAT2_SUFFIX in r["user"]) == (r["category"] == 2) for r in rows if r["layout"] != "alt")
    words = sorted(len(B.full_context(c).split()) for c in chats)
    ok["whole chats are long (every one 5,000+ words)"] = words[0] >= 5000
    print("chat words min/median/max:", words[0], words[len(words) // 2], words[-1], "| context", len(c0["qa"]))
    for k, v in ok.items():
        print(("PASS " if v else "FAIL ") + k)
    print("BM398R-DATA-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    if not all(ok.values()):
        raise SystemExit(1)


def main() -> int:
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["train", "dev"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--convs", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    _chats, rows = build(a.part, a.seed, a.convs)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    count: dict = {}
    for r in rows:
        count[r["layout"] + ":" + r["kind"]] = count.get(r["layout"] + ":" + r["kind"], 0) + 1
    print(json.dumps({"rows": len(rows), "by_layout_kind": dict(sorted(count.items()))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
