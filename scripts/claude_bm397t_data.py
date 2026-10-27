#!/usr/bin/env python3
"""bm-397t data (benchmarks thread, 2026-09-26): code-made practice for answering short about a long chat.

Every conversation, question and answer here is made by code from fixed word lists and sentence templates, with
fictional names and invented places; no benchmark item, no model output and no teacher is used. The answer to each
question is known by construction (a code-made label). Training puts loss on the answer tokens only, so the model
is never trained to write the chat text itself.

Rendering and instructions are deliberately NOT the LoCoMo harness's: sessions are "[Session n - date]" with
"Name: text" lines (the harness uses 'DATE:' / 'CONVERSATION:' and 'Name said, "..."'), and the question comes with
one of six brevity instructions, none of them the harness's QA prompt. So the LoCoMo test measures transfer.

Question kinds (answer = the exact label):
  single   where someone moved, their new job, their pet's name, what they bought, whose name they went out with,
           their favourite dish, where a relative lives
  when     an event said to happen "today", "yesterday" or "last week" in a dated session: the date, the day
           before, or "the week before <date>"
  list     two items of one kind said in two different sessions: "a, b"
Both speakers get facts of the same kinds with different values (distractors), plus small-talk turns.

  python -B scripts/claude_bm397t_data.py --seed 3970 --convs 180 --out train.jsonl
  python -B scripts/claude_bm397t_data.py --seed 3971 --convs 20 --out dev.jsonl
  python -B scripts/claude_bm397t_data.py selftest
Each line: {"id", "system", "user", "answer", "kind"}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys

NAMES = ["Mara", "Tobin", "Wren", "Idris", "Selka", "Orrin", "Juno", "Pell", "Varo", "Nessa", "Calder", "Brisa",
         "Rook", "Liesl", "Taavi", "Oona", "Fenn", "Quill", "Soren", "Ilse", "Dace", "Mirel", "Ansel", "Thora",
         "Bram", "Yara", "Corin", "Elka", "Havel", "Rune", "Senna", "Tavi", "Ulla", "Veda", "Zeno", "Ottla"]
TOWNS = ["Varnholt", "Eskbridge", "Pellmoor", "Duncairn", "Ostervale", "Brackenfield", "Lowmere", "Castral",
         "Wendle Bay", "Fairhollow", "Graymouth", "Tessary", "Kilnford", "Marrowgate", "Ashcombe", "Rilling",
         "Southwold Cross", "Quenby", "Harrowdene", "Elmsgarth"]
JOBS = ["baker", "bus driver", "librarian", "dental nurse", "sound engineer", "park ranger", "tailor", "welder",
        "maths tutor", "florist", "night nurse", "bike mechanic", "museum guide", "lab technician", "carpenter"]
PLACES = ["the old mill", "a small bakery", "the city library", "a dental clinic", "the harbour office",
          "a garden centre", "the town museum", "a repair shop", "the community college", "a hotel kitchen"]
ANIMALS = ["cat", "dog", "rabbit", "parrot", "tortoise", "hamster", "ferret", "goldfish"]
PETNAMES = ["Biscuit", "Pepper", "Moss", "Juniper", "Tofu", "Clementine", "Nimbus", "Pickle", "Sable", "Waffles",
            "Olive", "Bramble", "Comet", "Fig", "Marble", "Noodle"]
ITEMS = ["blue teapot", "second-hand bicycle", "wool blanket", "cast iron pan", "bird feeder", "reading lamp",
         "pair of hiking boots", "vintage camera", "set of paintbrushes", "wooden chess set", "rain jacket",
         "herb planter", "record player", "sewing machine"]
ACTIVITIES = ["hiking", "kayaking", "bowling", "fishing", "rock climbing", "ice skating", "cycling", "camping"]
RELATIONS = ["sister", "brother", "cousin", "neighbour", "old roommate", "coworker", "uncle", "aunt"]
DISHES = ["mushroom risotto", "lentil soup", "fish tacos", "spinach pie", "lamb stew", "pumpkin curry",
          "cheese dumplings", "grilled aubergine", "plum cake", "pea and mint pasta"]
INSTRUMENTS = ["violin", "ukulele", "drums", "cello", "harmonica", "piano", "flute", "banjo", "trumpet"]
SPORTS = ["tennis", "volleyball", "badminton", "swimming", "table tennis", "rowing", "archery", "fencing"]
EVENTS = [("ran my first half marathon", "run a half marathon"), ("passed my driving test", "pass a driving test"),
          ("gave a talk at the library", "give a talk at the library"), ("planted an apple tree", "plant an apple tree"),
          ("finished my first quilt", "finish a quilt"), ("sang at an open mic night", "sing at an open mic night"),
          ("baked bread for the school fair", "bake bread for the school fair"),
          ("went to my first pottery class", "go to a pottery class"),
          ("adopted a rescue greyhound", "adopt a rescue greyhound"), ("won the pub quiz", "win the pub quiz")]
FILLER = ["How was your week?", "Pretty busy, but good overall.", "That sounds lovely!", "Haha, I know exactly what you mean.",
          "Tell me more!", "The weather has been so grey lately.", "I've been reading a lot in the evenings.",
          "Did you catch the match on Sunday?", "Not yet, maybe this weekend.", "I'm so tired today, work was long.",
          "Same here, I need a holiday.", "Oh nice, how did that go?", "It went better than I expected.",
          "I made soup for the whole week.", "We should meet up soon.", "Definitely, let me know when you're free.",
          "My neighbour's dog kept barking all night.", "That's so annoying.", "I finally cleaned the garage.",
          "Good for you! Mine is a disaster.", "Have you tried the new cafe on the corner?", "Not yet, is it good?",
          "The coffee is great, the cake less so.", "I'm thinking of repainting the kitchen.", "What colour?",
          "Something warm, maybe yellow.", "The train was late again this morning.", "Typical!",
          "I watched a documentary about octopuses.", "They're so clever.", "Thanks for asking about my knee, it's better.",
          "Glad to hear it.", "I've started going to bed earlier.", "Me too, it helps a lot."]
INSTRUCTIONS = [
    "Answer the question using the chat above. Reply with only the answer, in as few words as possible.\n\nQuestion: {q}",
    "Question: {q}\nGive just the answer: a name, place, date, thing or short list. No full sentence.",
    "Using the conversation, answer briefly (a few words, no explanation).\nQ: {q}",
    "{q}\nAnswer with the key words only.",
    "Read the chat log and answer in at most five words.\n{q}",
    "Q: {q}\nA short answer only, please.",
]
SYSTEMS = ["You are a helpful assistant.", "You answer questions about conversations accurately and briefly."]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def fmt(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _facts(rng: random.Random, who: str, other: str, used: dict) -> list[dict]:
    """Facts for one speaker. Each: {"said": text (first person), "q": question, "a": answer, "kind", "slot"}."""
    def pick(pool, key):
        free = [x for x in pool if x not in used.setdefault(key, set())]
        x = rng.choice(free or pool)
        used[key].add(x)
        return x
    town, job, place = pick(TOWNS, "town"), pick(JOBS, "job"), rng.choice(PLACES)
    animal, pet = pick(ANIMALS, "animal"), pick(PETNAMES, "pet")
    item, act = pick(ITEMS, "item"), pick(ACTIVITIES, "act")
    rel, rel2 = rng.sample(RELATIONS, 2)
    friend = pick([n for n in NAMES if n not in (who, other)], "friend")
    dish, town2 = pick(DISHES, "dish"), pick(TOWNS, "town")
    return [
        {"said": f"Big news: I finally moved to {town}!", "q": f"Where did {who} move to?", "a": town, "kind": "single"},
        {"said": f"I started a new job as a {job} at {place}.", "q": f"What job did {who} start?", "a": job, "kind": "single"},
        {"said": f"We adopted a {animal} and named it {pet}.", "q": f"What is the name of {who}'s {animal}?", "a": pet,
         "kind": "single"},
        {"said": f"I bought a {item} at the Saturday market.", "q": f"What did {who} buy at the Saturday market?",
         "a": item, "kind": "single"},
        {"said": f"I went {act} with my {rel} {friend} last weekend.", "q": f"Who did {who} go {act} with?", "a": friend,
         "kind": "single"},
        {"said": f"Honestly my favourite dish is {dish}.", "q": f"What is {who}'s favourite dish?", "a": dish, "kind": "single"},
        {"said": f"My {rel2} lives in {town2}, I visit whenever I can.", "q": f"Where does {who}'s {rel2} live?", "a": town2,
         "kind": "single"},
    ]


def conversation(rng: random.Random, cid: str, n_q: int = 10) -> list[dict]:
    a, b = rng.sample(NAMES, 2)
    n_sess = rng.randint(7, 10)
    day = dt.date(rng.randint(2021, 2025), rng.randint(1, 12), rng.randint(1, 28))
    dates = []
    for _ in range(n_sess):
        dates.append(day)
        day = day + dt.timedelta(days=rng.randint(4, 25))
    used: dict = {}
    placed: list[tuple[int, str, str]] = []   # (session, speaker, text)
    qs: list[dict] = []
    for who in (a, b):
        for f in _facts(rng, who, b if who == a else a, used):
            s = rng.randrange(n_sess)
            placed.append((s, who, f["said"]))
            qs.append({"q": f["q"], "a": f["a"], "kind": f["kind"]})
        # a dated event
        ev, ev_q = rng.choice(EVENTS)
        s = rng.randrange(n_sess)
        when = rng.choice(["today", "yesterday", "last week"])
        text = {"today": f"Guess what, today I {ev}!", "yesterday": f"Yesterday I {ev}!",
                "last week": f"Last week I {ev}."}[when]
        ans = {"today": fmt(dates[s]), "yesterday": fmt(dates[s] - dt.timedelta(days=1)),
               "last week": f"the week before {fmt(dates[s])}"}[when]
        placed.append((s, who, text))
        qs.append({"q": f"When did {who} {ev_q}?", "a": ans, "kind": "when"})
        # a two-part list across two sessions
        pool, noun, verb = rng.choice([(INSTRUMENTS, "instruments", "play"), (SPORTS, "sports", "do")])
        x, y = rng.sample([p for p in pool if p not in used.setdefault(noun, set())] or pool, 2)
        used[noun].update({x, y})
        s1, s2 = sorted(rng.sample(range(n_sess), 2))
        art = "an" if x[0] in "aeiou" else "a"
        first = f"I've started learning the {x}." if noun == "instruments" else f"I joined {art} {x} club this month."
        second = f"I've also picked up the {y} now!" if noun == "instruments" else f"I've started doing {y} as well."
        placed += [(s1, who, first), (s2, who, second)]
        qs.append({"q": f"Which {noun} does {who} {verb}?", "a": f"{x}, {y}", "kind": "list"})
    lines = []
    for s in range(n_sess):
        mine = [(w, t) for (ss, w, t) in placed if ss == s]
        turns = [(None, rng.choice(FILLER)) for _ in range(rng.randint(10, 14))]
        for fact in mine:
            turns.insert(rng.randint(0, len(turns)), fact)
        spk, body = rng.choice([a, b]), []
        for w, t in turns:
            if w is not None and w != spk:
                body.append(f"{spk}: {rng.choice(FILLER)}")
                spk = w
            body.append(f"{spk}: {t}")
            spk = b if spk == a else a
        lines.append(f"[Session {s + 1} - {fmt(dates[s])}]\n" + "\n".join(body))
    chat = f"Chat log between {a} and {b}.\n\n" + "\n\n".join(lines)
    fixed = [q for q in qs if q["kind"] != "single"]            # both speakers' "when" and "list" questions
    single = [q for q in qs if q["kind"] == "single"]
    rng.shuffle(single)
    qs = fixed + single[:max(0, n_q - len(fixed))]
    rng.shuffle(qs)
    out = []
    for k, q in enumerate(qs):
        out.append({"id": f"{cid}#{k}", "system": rng.choice(SYSTEMS),
                    "user": chat + "\n\n" + rng.choice(INSTRUCTIONS).format(q=q["q"]), "answer": q["a"], "kind": q["kind"]})
    return out


def build(seed: int, convs: int) -> list[dict]:
    rng = random.Random(seed)
    return [row for c in range(convs) for row in conversation(rng, f"s{seed}c{c:03d}")]


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def correct(reply: str, answer: str) -> bool:
    """Every word of every comma part of the answer appears in the reply (dev sanity only, report only)."""
    r = set(words(reply))
    return all(w in r for part in answer.split(",") for w in words(part))


def selftest() -> None:
    ok, total = 0, 0

    def check(name, cond):
        nonlocal ok, total
        total += 1
        ok += int(cond)
        print(f"{'PASS' if cond else 'FAIL'} {name}")

    rows = build(3970, 5)
    check("5 convs x 10 questions", len(rows) == 50)
    check("same seed, same data", build(3970, 5) == rows)
    check("different seed, different data", build(3971, 5) != rows)
    check("every answer is in its chat or is a date/relative date",
          all(r["kind"] == "when" or all(w in words(r["user"]) for w in words(r["answer"])) for r in rows))
    check("no harness wording", not any("CONVERSATION:" in r["user"] or " said, \"" in r["user"]
                                        or "Based on the above conversations" in r["user"] for r in rows))
    check("all three kinds present", {r["kind"] for r in build(3970, 20)} == {"single", "when", "list"})
    check("correct() accepts the answer and rejects another", correct("It was Varnholt.", "Varnholt")
          and not correct("Eskbridge", "Varnholt") and correct("violin and cello", "violin, cello"))
    n_tok = [len(r["user"].split()) for r in build(3970, 20)]
    check("chats are long (median over 500 words)", sorted(n_tok)[len(n_tok) // 2] > 500)
    print(f"BM397T-DATA-SELFTEST {'PASS' if ok == total else 'FAIL'} {ok}/{total}")
    if ok != total:
        raise SystemExit(1)


def main() -> int:
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--convs", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = build(a.seed, a.convs)
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(json.dumps({"rows": len(rows), "kinds": kinds}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
