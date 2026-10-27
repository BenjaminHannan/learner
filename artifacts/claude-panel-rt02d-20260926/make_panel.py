#!/usr/bin/env python3
"""rt-02d blind TEST-ONLY panel (written 2026-09-26 by a blind panel writer).

TEST-ONLY: never opened, printed or quoted except by the runner and scorer.

Writes, next to this file:
  chat_puzzles.jsonl  100 fresh puzzles from claude_blurt2.puzzles(4797, 1000), minus every day, TEST and chat puzzle
                      of 0.2c (mirrors claude_sleep02c.run with its default arguments), phrased by 10 held-out
                      wordings, 10 puzzles per wording (puzzle i gets wording i // 10).
  negatives.jsonl     100 ordinary chat messages that contain numbers but are not number puzzles.

Deterministic: stdlib only, plus claude_blurt2 from scripts/. Run: python -B make_panel.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import claude_blurt2 as B2  # noqa: E402

PANEL_SEED = 4797
PANEL_POOL = 1000
N_PUZZLES = 100

# claude_sleep02c constants and run() defaults (--nights 3 --n-day 150 --n-test 100 --n-chat 40)
DAY_SEED02C, TEST_SEED02C, CHAT_SEED02C = 4700, 4790, 4795
NIGHTS, N_DAY, N_TEST, N_CHAT = 3, 150, 100, 40


def key(p):
    return (tuple(p["nums"]), p["target"])


def excluded_keys():
    # exact mirror of claude_sleep02c.run: nights d = 1..NIGHTS use puzzles(DAY_SEED02C + d, N_DAY)
    day_keys = {key(p) for d in range(1, NIGHTS + 1) for p in B2.puzzles(DAY_SEED02C + d, N_DAY)}
    test = [p for p in B2.puzzles(TEST_SEED02C, N_TEST + 300) if key(p) not in day_keys][:N_TEST]
    tkeys = day_keys | {key(p) for p in test}
    chat = [p for p in B2.puzzles(CHAT_SEED02C, N_CHAT + 300) if key(p) not in tkeys][:N_CHAT]
    mirror = tkeys | {key(p) for p in chat}
    # belt and braces: PASSMARKS names seeds 4700-4702, so seed 4700 (d = 0) is excluded as well
    extra = {key(p) for p in B2.puzzles(DAY_SEED02C, N_DAY)}
    return mirror | extra


# ---- number formats -------------------------------------------------------------------------------------------
def f_csv(ns):
    return ", ".join(map(str, ns))


def f_and(ns):
    s = list(map(str, ns))
    return ", ".join(s[:-1]) + " and " + s[-1]


def f_space(ns):
    return " ".join(map(str, ns))


def f_bracket(ns):
    return "[" + ", ".join(map(str, ns)) + "]"


def f_bullets(ns):
    return "\n".join(f"- {n}" for n in ns)


WORDINGS = [
    lambda ns, t: f"hey how do i get {t} out of {f_and(ns)}? each number once, adding subtracting multiplying "
                  f"dividing whatever works",
    lambda ns, t: f"Numbers: {f_csv(ns)}\nTarget: {t}\nEvery number exactly one time, parentheses allowed.",
    lambda ns, t: f"my kid's homework says make {t} using {f_and(ns)}. plus minus times divide are all ok. "
                  f"we're both stuck lol",
    lambda ns, t: f"Is it possible to combine {f_csv(ns)} with basic arithmetic so that the result equals {t}? "
                  f"Each number should appear once.",
    lambda ns, t: f"{f_space(ns)} -> {t}\nany ideas? +-*/ and brackets fine, no reusing numbers",
    lambda ns, t: f"trying to hit {t} with the numbers {f_csv(ns)}. can't use any of them twice. what's the trick",
    lambda ns, t: f"Could you help me find a calculation that comes out to {t}? I have to use all of these: "
                  f"{f_bracket(ns)}",
    lambda ns, t: f"game night question!! we've got {f_and(ns)} and need to reach {t}. add, subtract, multiply "
                  f"or divide, all cards used once",
    lambda ns, t: f"Using only {f_and(ns)} (one time each) and ordinary arithmetic, what calculation gives "
                  f"exactly {t}?",
    lambda ns, t: f"whats a way to make {t} from these\n{f_bullets(ns)}\nuse them all, once each, brackets are ok",
]

NEGATIVES = [
    # ages, prices, dates, times, counts, recipes, scores, everyday talk
    "My sister Maribel just turned 17 and she wants a car already, is that normal?",
    "The jacket was $89 but it's 30% off this weekend. Worth it or wait for a better sale?",
    "Can you remind me what day of the week March 14 falls on this year?",
    "I have a dentist appointment at 3:45 tomorrow and I always forget, any tips for remembering?",
    "We adopted 2 kittens last month and they already knocked over 5 plants.",
    "The recipe says 2 cups of flour and 3 eggs but I only have 2 eggs. Will it still work?",
    "Our team won 4-2 last night!! Tobin scored twice.",
    "Is 8 hours of sleep really necessary or is 6 fine if I nap?",
    "My grandpa Ezequiel is 81 and still walks 3 miles every morning.",
    "How long should I boil 6 eggs for soft yolks?",
    "The bus leaves at 7:10 and school starts at 7:50, is 40 minutes enough time if there's traffic?",
    "I read 12 books this summer, what should I read next if I liked mysteries?",
    "Rent went up from 1400 to 1550 this year and I'm not sure how to bring it up with my landlord.",
    "My phone battery is at 14% and it's only noon, why does it drain so fast?",
    "We're driving 5 hours to see my aunt Rosalind on the 22nd, any good road trip snacks?",
    "Is it weird to give a 10 year old a phone?",
    "My dog Pickle is 3 and still chews on everything. When do they grow out of it?",
    "The concert tickets were $65 each plus a $12 fee, which feels like a lot.",
    "I got a 91 on my chem test! Finally.",
    "It's been 2 weeks since I started running and my knees hurt a bit. Should I rest?",
    "Can you suggest a movie under 2 hours for tonight? Something funny.",
    "The pizza place has a deal: 2 large pizzas for $22. Is that good?",
    "Our wifi says 300 Mbps but speed tests show like 40. What's going on?",
    "I planted 15 tomato seedlings and only 9 made it. What did I do wrong?",
    "My cousin Delphine is getting married on June 7th and I need a gift idea.",
    "How many calories are in 1 banana roughly?",
    "The game starts at 8 but I work until 7:30, think I can make it?",
    "My landlord says the heat will be fixed in 3 to 5 business days. Is that reasonable in winter?",
    "We have 4 people coming for dinner Saturday, what's an easy main dish?",
    "I've been learning guitar for 6 months and still can't do barre chords.",
    "Room 204 has the best view in the whole dorm, I got lucky.",
    "My score on the practice SAT was 1340, is that decent for a first try?",
    "Can you convert 350 degrees Fahrenheit to Celsius for my oven?",
    "The flight is at 6am so I need to leave by 4. Ugh.",
    "Leticia ran the 5k in 27 minutes, her personal best!",
    "I bought 3 plants for my apartment, which ones need the least light?",
    "The meeting got moved to Thursday at 2, can you help me write a quick note to my team about it?",
    "It's 34 degrees outside, do I need a heavy coat or is a hoodie fine?",
    "My brother is 14 and plays video games like 5 hours a day. Should my parents worry?",
    "The library fine is 25 cents a day and my book is 9 days late. Oops.",
    "I'm on chapter 11 of 20 and the story finally picked up.",
    "Our basketball team is 7 and 3 this season, best start in years.",
    "The printer jammed again on page 12. Any fixes?",
    "My great aunt Philippa collected over 200 teacups, what do we do with them now?",
    "Is it safe to leave cooked rice out for 4 hours?",
    "I need to be up at 5:30 tomorrow, what time should I go to bed?",
    "The package says delivery in 3-5 days but it's been 8.",
    "I have 2 tests and 1 essay due next week and I'm panicking.",
    "My car needs an oil change every 5000 miles, I'm at 4700 since the last one.",
    "The bakery sells croissants for $3.50, which is kind of steep but they're amazing.",
    "Happy 40th anniversary to my parents Ignatius and Marisol!",
    "Why do some months have 31 days and others 30?",
    "Coach said practice is at 6 tomorrow instead of 5.",
    "My sourdough starter is 10 days old, is it ready to bake with?",
    "The hike is 7 miles round trip with 1200 feet of climbing. Doable for a beginner?",
    "Can you recommend a board game for 6 players?",
    "We scored 112 points in the trivia night and still came in 3rd.",
    "I drank like 4 coffees today and I feel jittery.",
    "My shift got changed to 11 to 7 and I hate it.",
    "The apartment is 650 square feet, is that enough for 2 people?",
    "Grandma's lasagna recipe uses 1 pound of ricotta and 2 jars of sauce, can I freeze it?",
    "Lucian got 3 speeding tickets this year, his insurance is going to skyrocket.",
    "I've watched season 2 twice now, is season 3 any good?",
    "My laptop is 6 years old and super slow, upgrade or replace?",
    "Tuesday the 9th works better for me than Monday.",
    "The soup needs to simmer for 45 minutes, can I leave the house?",
    "Our class has 28 students and only 1 teacher, it's chaos.",
    "My high score in that game is 48210 and nobody can beat it.",
    "The yoga class is 60 minutes and I usually leave after 40, is that rude?",
    "Can you help me write a birthday message for my friend Oriana who's turning 30?",
    "I walked 11000 steps today without even trying.",
    "We split the bill 5 ways and somehow I still paid the most.",
    "The museum is free on the first Sunday of the month, and parking is 8 dollars.",
    "My plant has 3 yellow leaves, is it overwatered?",
    "Apartment 3B keeps playing loud music past midnight.",
    "Winning streak is at 6 games now, the whole town is excited.",
    "The cookie recipe makes 24 but I only need about a dozen. Any tips for storing the extra dough?",
    "I'm 5 foot 4, would a 26 inch bike fit me?",
    # near-misses: numbers and a goal, but not asking to combine numbers into a target
    "I need 3 more to get to 10 pushups in a row, any tips for building strength?",
    "We have 4 people and 12 slices, is that enough pizza or should we order another?",
    "I want to get to 100 followers by December, I'm at 64 now. How do I grow my page?",
    "Trying to hit 8 hours of sleep but I keep waking up at 3 and 5.",
    "I have 2 quarters, 3 dimes and a nickel, can I get a snack from a machine that costs 75 cents?",
    "My goal is to read 24 books this year and I'm on 9, is it realistic to catch up?",
    "We need 5 more signatures to reach 50 for the petition, how should we ask people?",
    "Coach wants us to make 20 free throws out of 25 before we leave practice.",
    "If I save 15 dollars a week, will I reach my goal of 400 by summer? Just roughly.",
    "I'm at 7 out of 10 on my habit tracker this week, how do I stay motivated for the last 3 days?",
    "The recipe serves 4 but we're 6, how do I scale it up without it tasting weird?",
    "We have 3 cars and 14 people, how do we fit everyone for the trip?",
    "I need to make 30 cupcakes for the bake sale but my pan only holds 12 at a time. How long will this take me?",
    "My test average is 84 and I want to get to a 90, is it even possible with 2 tests left?",
    "Our team needs 2 more wins to make the playoffs, 4 games left. Think we can do it?",
    "I have 6 hours of homework and 4 hours of free time tonight, what should I prioritize?",
    "Trying to reach 10000 steps but I'm stuck at 6000 most days.",
    "We've got 18 chairs and 24 guests coming, where do people usually rent chairs?",
    "I need to lose 5 pounds before the wedding on the 20th, is that healthy in 3 weeks?",
    "Our fundraiser made 820 dollars and the goal was 1000, how do we thank donors anyway?",
    "Hit 3 of my 5 goals this month, not bad.",
    "I need 12 credits to graduate and I have 9, should I take a summer class?",
]


def main() -> None:
    excl = excluded_keys()
    chosen = [p for p in B2.puzzles(PANEL_SEED, PANEL_POOL) if key(p) not in excl][:N_PUZZLES]
    assert len(chosen) == N_PUZZLES, len(chosen)
    rows = []
    for i, p in enumerate(chosen):
        w = i // 10
        shown = list(p["nums"])
        random.Random(PANEL_SEED * 1000 + i).shuffle(shown)   # people do not type the numbers sorted
        rows.append({"id": f"rt02d-pz-{i + 1:03d}", "wording_id": w, "text": WORDINGS[w](shown, p["target"]),
                     "nums": list(p["nums"]), "target": p["target"]})
    (HERE / "chat_puzzles.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert len(NEGATIVES) == 100 and len(set(NEGATIVES)) == 100, len(NEGATIVES)
    neg = [{"id": f"rt02d-neg-{i + 1:03d}", "text": t} for i, t in enumerate(NEGATIVES)]
    (HERE / "negatives.jsonl").write_text("".join(json.dumps(r) + "\n" for r in neg), encoding="utf-8")
    print(f"puzzles {len(rows)} (excluded keys {len(excl)}), negatives {len(neg)}")


if __name__ == "__main__":
    main()
