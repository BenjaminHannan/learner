#!/usr/bin/env python3
"""own-O0b frame data generator (plan section 2.4).

World sampler that simulates the notebook and writes turns with EXACT labels
by construction, in the plan section 2.1 output format.

Row (one JSON object per line):
  {id, split, family, frame_id, prev_reply, turn, act, count,
   facts:[{owner, relation, relation_cue_span, value_span, mode}],
   question, spelling_flag, world}

- owner is "ME" | "WE" | [start, end] (char offsets into turn).
- relation is a relation_table_v2 name.
- relation_cue_span / value_span are [start, end] char offsets into turn.
- question is null or {owner_span ("ME"|"WE"|[s,e]), relations[<=3], inverse}.
- world holds construction intent (surfaces, relation, inverse, flags) for the
  INDEPENDENT checker; it never holds the label spans themselves.

Families: tell, ask, chat, act, binding, plural, appositive, correction,
noise, typo. Split BY FRAME before generating: 20% of frame ids held out
(L2), plus 2 openers + 2 closers never trained. L1 = seen frames, new names.
L2 = held-out frames + reserved names. L3 left empty.

Fictional names only. CPU only, no downloads.

Usage:
  gen.py pilot --out <dir> --n 2000
  gen.py full  --out <dir>   (200k train + 5k L1 dev + 5k L2 dev, sharded <5MB)
"""
from __future__ import annotations
import argparse, gzip, json, os, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE_PATH = ROOT / "artifacts/claude-smolear257-20260922/relation_table_v2.json"

ACTS = ["STATE", "CORRECT", "DENY", "ASK", "CHECK", "SUPPOSE", "PLAN", "CHAT", "UNCLEAR"]
MODE_OF = {"STATE": "ASSERT", "CHECK": "CHECK", "SUPPOSE": "SUPPOSE",
           "PLAN": "PLAN", "CORRECT": "CORRECT", "DENY": "DENY"}

# ---------------------------------------------------------------- pools ---
# Fictional name pools. Disjoint by construction: train / L1-new / reserved.
TRAIN_NAMES = ("Aldo Ayers Abel Ashby Anselm Anselma Astrid Odell Odette Oren Orson "
  "Orla Oswald Owen Oona Petra Paloma Pascal Pearl Perry Pilar Pippa Polly "
  "Quinn Quentin Ragna Rasmus Riva Roald Robin Romy Roscoe Rowan Rufus Sabina "
  "Sanna Sasha Selma Soren Stina Suki Tilda Tal Tamara Tansy Tessa Thea Tobin "
  "Tove Ulrik Una Vanna Veda Vera Willa Wren Yara Ysolde Anselm0").split()
TRAIN_NAMES = [n for n in TRAIN_NAMES if n.isalpha()]
TRAIN_NAMES += ["Bram", "Celia", "Dain", "Elif", "Farah", "Garr", "Hazel", "Ivo",
  "Juna", "Kito", "Lena", "Mira", "Nilo", "Sable", "Tilda2", "Vesper"]
TRAIN_NAMES = [n for n in TRAIN_NAMES if n.isalpha()]
L1_NAMES = ("Casper Dorit Eamon Fern Freya Gus Hilde Iben Jesper Kaja Lior "
  "Maren Nils Ottar Pella Runa Siv Trine Vejle Asta Boje").split()
RESERVED_NAMES = ("Xanthe Xaver Ydun Zola Zephyr Quilla Qasim Voss Wrenna Yestin "
  "Zelda Zev Quan Nixie Ulva Tam Ossia Paxon Rill Sarella Tovey Ulf Zima Yorick "
  "Xenia Wystan Qiana Zoran Pell Vayne Umber Yvette Zeke Odhran Quinnell").split()
assert not (set(TRAIN_NAMES) & set(L1_NAMES)), "name pool overlap train/l1"
assert not (set(TRAIN_NAMES) & set(RESERVED_NAMES)), "name pool overlap train/l2"
assert not (set(L1_NAMES) & set(RESERVED_NAMES)), "name pool overlap l1/l2"

PET_NAMES = ("Pip Fig Moss Biscuit Pebble Wicket Nibbles Socks Taffy Bramble "
  "Clover Dandelion Pickles Waffles Ziggy Noodle Miso Pudding").split()
PLACES = ("Rook Mirell Tansford Osprey Lumen Vexford Kallby Norvik Dunmere "
  "Fellsby Harrowgate Lindor Marby Ormskirk Pellham Saltholm").split()
JOBS = ("baker clerk driver nurse pilot mason weaver smith tailor brewer "
  "porter steward librarian").split()
ORGS = ("Harbor Mill Northline Bakery Copper Post Fern Clinic Bluebell Press "
  "Stonebridge Works").split()
FOODS = ("plum pie oat cakes honey loaf mushroom stew apple tart barley soup "
  "berry jam rye bread").split()
COLORS = ("rust teal mustard slate lilac ochre indigo coral moss").split()
HOBBIES = ("whittling birdwatching stargazing fermentation shell collecting "
  "kite flying bread baking").split()
SPORTS = ("curling rowing archery bowls fencing handball orienteering").split()
BOOKS = ("The Salt Road Winter Harbor The Glass Orchard Small Hours North Of "
  "The Mill The Long Thaw").split()
INSTRUMENTS = ("fiddle accordion dulcimer bodhran tin whistle concertina "
  "mandolin cello").split()
SUBJECTS = ("algebra botany cartography grammar astronomy geometry").split()
SEASONS = ("early spring late autumn deep winter first thaw harvest time").split()

OPENERS = ["", "Hey, ", "So, ", "Well, ", "Listen, ", "Guess what, ",
           "By the way, ", "Oh, "]
HELDOUT_OPENERS = {"By the way, ", "Oh, "}
CLOSERS = ["", " you know.", " I think.", " really.", " these days.",
           " right now.", " for sure.", " again."]
HELDOUT_CLOSERS = {" for sure.", " again."}
TRAIN_OPENERS = [o for o in OPENERS if o not in HELDOUT_OPENERS]
TRAIN_CLOSERS = [c for c in CLOSERS if c not in HELDOUT_CLOSERS]

# ------------------------------------------------------- relation kinds ---
# relation -> list of cue surfaces (first is the default cue).
KIN = {
 "mother": ["mother", "mom", "mum"], "father": ["father", "dad"],
 "sister": ["sister", "sis"], "brother": ["brother", "bro"],
 "son": ["son"], "daughter": ["daughter"], "child": ["child", "kid"],
 "parent": ["parent"], "wife": ["wife"], "husband": ["husband"],
 "partner": ["partner"], "grandmother": ["grandmother", "grandma", "granny"],
 "grandfather": ["grandfather", "grandpa"], "aunt": ["aunt"], "uncle": ["uncle"],
 "cousin": ["cousin"], "niece": ["niece"], "nephew": ["nephew"],
 "sister_in_law": ["sister-in-law", "sister in law"],
 "brother_in_law": ["brother-in-law", "brother in law"],
 "mother_in_law": ["mother-in-law", "mother in law"],
 "stepmother": ["stepmother", "stepmom"], "stepfather": ["stepfather", "stepdad"],
 "stepsister": ["stepsister", "step sister"], "half_brother": ["half-brother", "half brother"],
 "godmother": ["godmother", "god mother"], "fiance": ["fiance", "fiancee"],
 "best_friend": ["best friend", "bestie"],
}
SOCIAL = {
 "friend": ["friend"], "boss": ["boss", "manager"], "teacher": ["teacher"],
 "colleague": ["colleague", "coworker"], "neighbour": ["neighbour", "neighbor"],
 "roommate": ["roommate", "flatmate"], "doctor": ["doctor"], "coach": ["coach"],
 "mentor": ["mentor"], "dentist": ["dentist"], "vet": ["vet"],
 "tutor": ["tutor"], "classmate": ["classmate"], "teammate": ["teammate"],
 "babysitter": ["babysitter", "childminder"], "landlord": ["landlord"],
 "therapist": ["therapist"], "apprentice": ["apprentice"], "rival": ["rival"],
}
PET = {
 "dog": ["dog"], "cat": ["cat"], "horse": ["horse", "pony"],
 "rabbit": ["rabbit"], "hamster": ["hamster"], "parrot": ["parrot"],
}
PLACE = {
 "city": ["city", "town"], "hometown": ["hometown", "home town"],
 "home": ["home"], "country": ["country"], "school": ["school"],
 "work_location": ["work location"], "capital": ["capital"],
 "place_of_birth": ["birthplace", "place of birth"],
}
WORK = {
 "employer": ["employer", "workplace", "place of work"],
 "occupation": ["occupation", "job", "profession"], "title": ["title"],
}
THING = {
 "favorite_food": ["favorite food", "favourite food"], "color": ["color", "colour"],
 "favorite_color": ["favorite color", "favourite colour"], "hobby": ["hobby"],
 "car": ["car"], "sport": ["sport"], "allergy": ["allergy"],
 "favorite_book": ["favorite book"], "instrument": ["instrument", "musical instrument"],
 "favorite_sport": ["favorite sport"], "favorite_subject": ["favorite subject"],
 "favorite_season": ["favorite season"], "nickname": ["nickname"],
}
KINDS = {"kin": KIN, "social": SOCIAL, "pet": PET, "place": PLACE,
         "work": WORK, "thing": THING}

def kind_value_pool(kind):
    if kind in ("kin", "social"):
        return None  # person name
    if kind == "pet":
        return PET_NAMES
    if kind == "place":
        return PLACES
    if kind == "work":
        return JOBS + ORGS
    return FOODS + COLORS + HOBBIES + SPORTS + BOOKS + INSTRUMENTS + SUBJECTS + SEASONS

# ------------------------------------------------------ frame patterns ---
# {O} owner, {R} relation cue, {V} value, {OLD} old value (correction only).
# 44+ hand-written frames per act. STATE/CHECK/SUPPOSE/PLAN/CORRECT/DENY use
# {O} {R} {V}; ASK uses {O} {R} (plus {V} in disjunction frames).
P_STATE = [
 "{O}'s {R} is {V}.", "{O}'s {R} is {V}!", "I heard {O}'s {R} is {V}.",
 "{O}'s {R} - it's {V}.", "Just so you know, {O}'s {R} is {V}.",
 "For the record, {O}'s {R} is {V}.", "{O}'s {R} happens to be {V}.",
 "Turns out {O}'s {R} is {V}.", "I can confirm {O}'s {R} is {V}.",
 "Everyone knows {O}'s {R} is {V}.", "{O} has a {R} named {V}.",
 "{O} has this {R} called {V}.", "{V} is {O}'s {R}.", "The {R} of {O} is {V}.",
 "{O}'s {R}: {V}.", "Let me tell you: {O}'s {R} is {V}.",
 "I remember now, {O}'s {R} is {V}.", "As I said, {O}'s {R} is {V}.",
 "Like I told you, {O}'s {R} is {V}.", "{O}'s {R} is definitely {V}.",
 "{O}'s {R} is really {V}.", "Apparently {O}'s {R} is {V}.",
 "I just learned {O}'s {R} is {V}.", "News: {O}'s {R} is {V}.",
 "{O} told me their {R} is {V}.", "{O} mentioned their {R} is {V}.",
 "{O}'s {R} is {V}, in case you forgot.", "Reminder: {O}'s {R} is {V}.",
 "I am telling you {O}'s {R} is {V}.", "Believe me, {O}'s {R} is {V}.",
 "{O}'s one {R} is {V}.", "The story is {O}'s {R} is {V}.",
 "Word is {O}'s {R} is {V}.", "I found out {O}'s {R} is {V}.",
 "{O}'s {R} is {V} - pass it on.", "Heads up: {O}'s {R} is {V}.",
 "Quick fact: {O}'s {R} is {V}.", "Something true: {O}'s {R} is {V}.",
 "I will state it plainly: {O}'s {R} is {V}.", "On record: {O}'s {R} is {V}.",
 "Mark this: {O}'s {R} is {V}.", "It is settled: {O}'s {R} is {V}.",
 "Final answer: {O}'s {R} is {V}.", "I swear {O}'s {R} is {V}.",
 "Honestly, {O}'s {R} is {V}.",
]
P_ASK = [
 "Who is {O}'s {R}?", "Can you tell me who {O}'s {R} is?",
 "Do you know who {O}'s {R} is?", "What is {O}'s {R} called?",
 "Which one is {O}'s {R}?", "Is {V} {O}'s {R}?",
 "Is {O}'s {R} {V}?", "Was {O}'s {R} {V}?",
 "Tell me, who is {O}'s {R}?", "I wonder who {O}'s {R} is?",
 "Any idea who {O}'s {R} is?", "Who might {O}'s {R} be?",
 "So who is {O}'s {R}?", "Then who is {O}'s {R}?",
 "But who is {O}'s {R}?", "Who is {O}'s {R}, then?",
 "What did you say {O}'s {R} was?", "Remind me, who is {O}'s {R}?",
 "Have you met {O}'s {R}?", "Do you remember {O}'s {R}?",
 "Can you name {O}'s {R}?", "Would you know {O}'s {R}?",
 "Is {V} or {V2} {O}'s {R}?", "Is {O}'s {R} {V} or {V2}?",
 "Which is it: is {O}'s {R} {V} or someone else?",
 "Who serves as {O}'s {R}?", "Who fills the role of {O}'s {R}?",
 "Name {O}'s {R} for me?", "Give me the name of {O}'s {R}?",
 "I ask you: who is {O}'s {R}?", "My question is who is {O}'s {R}?",
 "One question: who is {O}'s {R}?", "Just wondering who {O}'s {R} is?",
 "Could {V} be {O}'s {R}?", "Might {V} be {O}'s {R}?",
 "Is it true that {O}'s {R} is {V}?", "Do they say {O}'s {R} is {V}?",
 "Has anyone told you who {O}'s {R} is?", "Did {O} ever name their {R}?",
 "What name did {O} give for their {R}?", "Who did {O} pick as {R}?",
 "Ever heard who {O}'s {R} is?", "Any clue about {O}'s {R}?",
 "Pray, who is {O}'s {R}?", "Kindly tell me {O}'s {R}?",
 "Between us, who is {O}'s {R}?",
]
P_CHECK = [
 "So {O}'s {R} is {V}", "So {O}'s {R} is {V}, right",
 "So {O}'s {R} is {V}, yes", "Wait, {O}'s {R} is {V}",
 "Hold on, {O}'s {R} is {V}", "Let me get this straight, {O}'s {R} is {V}",
 "Just to check, {O}'s {R} is {V}", "Confirming: {O}'s {R} is {V}",
 "So you are saying {O}'s {R} is {V}", "So the story is {O}'s {R} is {V}",
 "If I heard right, {O}'s {R} is {V}", "Correct me if I am wrong, {O}'s {R} is {V}",
 "Did I hear that {O}'s {R} is {V}", "Am I right that {O}'s {R} is {V}",
 "So {V} is {O}'s {R}", "So the {R} of {O} is {V}",
 "Meaning {O}'s {R} is {V}", "In other words {O}'s {R} is {V}",
 "To be clear, {O}'s {R} is {V}", "Just confirming {O}'s {R} is {V}",
 "Double-checking: {O}'s {R} is {V}", "So then {O}'s {R} is {V}",
 "And {O}'s {R} is {V}, if I follow", "Following you: {O}'s {R} is {V}",
 "Got it, {O}'s {R} is {V}", "Okay so {O}'s {R} is {V}",
 "Right, so {O}'s {R} is {V}", "Hmm, so {O}'s {R} is {V}",
 "Interesting, so {O}'s {R} is {V}", "Wow, so {O}'s {R} is {V}",
 "Really, {O}'s {R} is {V}", "Seriously, {O}'s {R} is {V}",
 "So I have it that {O}'s {R} is {V}", "So noted: {O}'s {R} is {V}",
 "For the check: {O}'s {R} is {V}", "Checking my notes, {O}'s {R} is {V}",
 "My notes say {O}'s {R} is {V}", "I wrote down {O}'s {R} is {V}",
 "Before I save it, {O}'s {R} is {V}", "To repeat back, {O}'s {R} is {V}",
 "Echoing you: {O}'s {R} is {V}", "Playing back: {O}'s {R} is {V}",
 "So the record would read {O}'s {R} is {V}", "So the file says {O}'s {R} is {V}",
 "As I understand it {O}'s {R} is {V}", "The way I heard it {O}'s {R} is {V}",
 "That means {O}'s {R} is {V}",
]
P_SUPPOSE = [
 "Suppose {O}'s {R} is {V}.", "Say {O}'s {R} is {V}.",
 "Imagine {O}'s {R} is {V}.", "Let's say {O}'s {R} is {V}.",
 "What if {O}'s {R} is {V}.", "Suppose {O}'s {R} were {V}.",
 "Say, hypothetically, {O}'s {R} is {V}.", "Imagine, just for fun, {O}'s {R} is {V}.",
 "Pretend {O}'s {R} is {V}.", "Assume {O}'s {R} is {V}.",
 "For argument's sake {O}'s {R} is {V}.", "In a story where {O}'s {R} is {V}.",
 "Picture this: {O}'s {R} is {V}.", "Consider a world where {O}'s {R} is {V}.",
 "Let's imagine {O}'s {R} is {V}.", "Let's suppose {O}'s {R} is {V}.",
 "Say it were true that {O}'s {R} is {V}.",
 "If {O}'s {R} were {V}, what then.", "If {O}'s {R} turned out to be {V}.",
 "Even if {O}'s {R} is {V}.", "Whether {O}'s {R} is {V} or not.",
 "Suppose for a minute {O}'s {R} is {V}.", "Grant me that {O}'s {R} is {V}.",
 "Take it as given {O}'s {R} is {V}.", "Hypothesis: {O}'s {R} is {V}.",
 "A theory: {O}'s {R} is {V}.", "Theory time: {O}'s {R} is {V}.",
 "Rumor has it {O}'s {R} is {V}.", "Some say {O}'s {R} is {V}.",
 "Legend says {O}'s {R} is {V}.", "The tale goes {O}'s {R} is {V}.",
 "In the play, {O}'s {R} is {V}.", "In my dream, {O}'s {R} is {V}.",
 "I dreamed {O}'s {R} is {V}.", "In a daydream {O}'s {R} is {V}.",
 "Make-believe: {O}'s {R} is {V}.", "Once upon a time {O}'s {R} was {V}.",
 "Fiction: {O}'s {R} is {V}.", "A novel where {O}'s {R} is {V}.",
 "The script says {O}'s {R} is {V}.", "Stage directions: {O}'s {R} is {V}.",
 "Roleplay: {O}'s {R} is {V}.", "Game plan: {O}'s {R} is {V}.",
 "What if it turned out {O}'s {R} is {V}.", "Just imagine {O}'s {R} is {V}.",
 "Suppose, suppose {O}'s {R} is {V}.",
]
P_PLAN = [
 "{O} wants a {R} called {V}.", "{O} wants their {R} to be {V}.",
 "{O} is planning to get a {R} named {V}.", "{O} dreams of getting a {R} called {V}.",
 "{O} hopes to get a {R} named {V}.", "{O} wants to find a {R} called {V}.",
 "{O} is looking for a {R} named {V}.", "{O} plans to choose {V} as {R}.",
 "{O} intends {V} to be their {R}.", "{O} wishes {V} were their {R}.",
 "{O} is hoping {V} becomes their {R}.", "{O} has plans for a {R} named {V}.",
 "The plan: {O} wants a {R} called {V}.", "Goal: {O} wants a {R} named {V}.",
 "{O}'s wish: a {R} called {V}.", "{O}'s dream: a {R} named {V}.",
 "{O} is saving up for a {R} called {V}.", "{O} will one day have a {R} named {V}.",
 "{O} means to make {V} their {R}.", "{O} aims to get a {R} called {V}.",
 "Someday {O} wants a {R} named {V}.", "Eventually {O} wants a {R} called {V}.",
 "{O} keeps saying they want a {R} named {V}.", "{O} told Santa they want a {R} called {V}.",
 "On the wishlist: {O} wants a {R} named {V}.", "New year's resolution: {O} wants a {R} called {V}.",
 "{O} is dreaming about a {R} named {V}.", "{O} fantasizes about a {R} called {V}.",
 "{O} is set on a {R} named {V}.", "{O} has their heart set on a {R} called {V}.",
 "{O} asked for a {R} named {V} for winter.", "{O} begged for a {R} called {V}.",
 "{O} is campaigning for a {R} named {V}.", "{O} will ask for a {R} called {V}.",
 "{O} wants, more than anything, a {R} named {V}.",
 "{O}'s birthday wish is a {R} called {V}.", "{O}'s big plan: a {R} named {V}.",
 "Step one of the plan: {O} gets a {R} called {V}.",
 "The dream home includes {O} with a {R} named {V}.",
 "Five-year plan: {O} and a {R} called {V}.", "Pinky promise: {O} gets a {R} named {V}.",
 "Scout's honor, {O} wants a {R} called {V}.", "{O} put it on the list: a {R} named {V}.",
 "Top of the list: {O} wants a {R} called {V}.", "{O} can already picture a {R} named {V}.",
]
P_CORRECT = [
 "Actually {O}'s {R} is {V} now.", "Actually, {O}'s {R} is {V}.",
 "{O}'s {R} is {V}, not {OLD}.", "{O}'s {R} is {V} now, not {OLD}.",
 "Correction: {O}'s {R} is {V}.", "Small correction, {O}'s {R} is {V}.",
 "I misspoke: {O}'s {R} is {V}.", "Let me fix that: {O}'s {R} is {V}.",
 "Update: {O}'s {R} is {V} now.", "New info: {O}'s {R} is {V}.",
 "It changed: {O}'s {R} is {V} now.", "Turns out {O}'s {R} is {V} after all.",
 "I was wrong, {O}'s {R} is {V}.", "My mistake, {O}'s {R} is {V}.",
 "Sorry, {O}'s {R} is {V}.", "Oops, {O}'s {R} is {V}.",
 "Wait, {O}'s {R} is actually {V}.", "Hold on, {O}'s {R} is actually {V}.",
 "No wait, {O}'s {R} is {V}.", "Hmm, actually {O}'s {R} is {V}.",
 "Let me correct myself: {O}'s {R} is {V}.", "To correct the record, {O}'s {R} is {V}.",
 "The truth is {O}'s {R} is {V}.", "In fact {O}'s {R} is {V}.",
 "As it happens {O}'s {R} is {V}.", "Come to think of it, {O}'s {R} is {V}.",
 "Now that I check, {O}'s {R} is {V}.", "I double-checked: {O}'s {R} is {V}.",
 "{V}, not {OLD}: that is {O}'s {R}.", "It's {V}, not {OLD}, for {O}'s {R}.",
 "Forget {OLD}: {O}'s {R} is {V}.", "Not {OLD} anymore, {O}'s {R} is {V}.",
 "Out with {OLD}: {O}'s {R} is {V} now.", "{OLD} was yesterday; {O}'s {R} is {V} now.",
 "Replace {OLD} with {V} for {O}'s {R}.", "Swap {OLD} for {V}: {O}'s {R}.",
 "{O}'s {R} changed from {OLD} to {V}.", "{O}'s {R} is {V} as of today.",
 "Latest: {O}'s {R} is {V}.", "Breaking: {O}'s {R} is now {V}.",
 "Edit that: {O}'s {R} is {V}.", "Amendment: {O}'s {R} is {V}.",
 "Retraction: {O}'s {R} is {V}, not {OLD}.", "Erratum: {O}'s {R} reads {V}.",
 "Fixed: {O}'s {R} is {V}.",
]
P_DENY = [
 "No, {O}'s {R} isn't {V}.", "{O}'s {R} isn't {V}.",
 "{O}'s {R} is never {V}.", "No way is {O}'s {R} {V}.",
 "That's wrong: {O}'s {R} isn't {V}.", "False: {O}'s {R} isn't {V}.",
 "Nope, {O}'s {R} isn't {V}.", "Nah, {O}'s {R} isn't {V}.",
 "{O}'s {R} ain't {V}.", "{V} is no {R} of {O}.",
 "{V} is not {O}'s {R}.", "Denied: {O}'s {R} is not {V}.",
 "I deny that {O}'s {R} is {V}.", "Not true: {O}'s {R} is {V}.",
 "Wrong: {O}'s {R} is {V}.", "Incorrect: {O}'s {R} equals {V} - no.",
 "{O}'s {R} is not and never was {V}.", "{V} was never {O}'s {R}.",
 "{O} never had a {R} named {V}.", "{O} has no {R} called {V}.",
 "There is no {V} among {O}'s {RPL}.", "Strike that: {O}'s {R} isn't {V}.",
 "Take it back: {O}'s {R} isn't {V}.", "Forget it, {O}'s {R} isn't {V}.",
 "Absolutely not: {O}'s {R} isn't {V}.", "Definitely not: {O}'s {R} isn't {V}.",
 "How could {O}'s {R} be {V}.", "{O}'s {R} couldn't be {V}.",
 "{O}'s {R} can't be {V}.", "Impossible: {O}'s {R} is {V} - no.",
 "Nobody thinks {O}'s {R} is {V}.", "Don't claim {O}'s {R} is {V}.",
 "Never say {O}'s {R} is {V} again.", "I refuse the claim {O}'s {R} is {V}.",
 "Overruled: {O}'s {R} isn't {V}.", "Vetoed: {O}'s {R} isn't {V}.",
 "Rejected: {O}'s {R} is {V} - false.", "Debunked: {O}'s {R} isn't {V}.",
 "Myth: {O}'s {R} is {V}. Busted.", "Spoiler: {O}'s {R} isn't {V}.",
 "Plot twist: {O}'s {R} isn't {V}.", "Newsflash: {O}'s {R} isn't {V}.",
 "Correction denied: {O}'s {R} isn't {V}.",
]
P_CHAT = [
 "Hey, how are you?", "Hello! Nice to see you.", "Hi, what's up?",
 "Hey, great day isn't it.", "Good morning! Coffee first?",
 "Good night, see you tomorrow.", "Thanks, that helps a lot.",
 "Thank you! Okay, bye.", "Lol, that's funny.", "Haha, cool story.",
 "Nice! Okay, tell me more.", "Cool, cool. Anyway, how was your weekend?",
 "How was your weekend? Any gossip?", "Awful weather today, right?",
 "It's raining again. Oh well.", "So, any gossip from town?",
 "Hey, did you see the game?", "Hi! How are you doing today?",
 "Hello hello, thanks for coming.", "Okay, nice chatting with you.",
 "Bye now, see you soon!", "Good morning, nice weather we're having.",
 "Haha, thanks, I needed that.", "Lol okay, whatever you say.",
 "Cool story, thanks for sharing.", "Nice one! Tell me another.",
 "Hey, thanks for stopping by.", "Hi, good to hear from you.",
 "Any weekend plans? Mine involve coffee.", "This weather, huh? Classic.",
 "Am I rambling? Lol, sorry.", "Okay, thanks, I'm listening.",
 "Haha, you always say that.", "Nice weather for a walk.",
 "Thanks a million, bye!", "See you later, cool?",
 "Hey, all good, thanks!", "Oh hey, I didn't see you there.",
 "Good night! Thanks again.", "Morning! Coffee?",
 "So how have you been lately?", "Anything new? Gossip?",
 "Lol, nice.", "Haha, okay.",
]
P_UNCLEAR = [
 "Hmm, not sure.", "Maybe later.", "I forgot.", "Not sure yet.",
 "Hmm.", "Let me think.", "Kinda.", "Sort of.",
 "Dunno.", "No idea, honestly.", "Hard to say.", "Ask me later.",
]
ACT_PATTERNS = {"STATE": P_STATE, "ASK": P_ASK, "CHECK": P_CHECK,
                "SUPPOSE": P_SUPPOSE, "PLAN": P_PLAN, "CORRECT": P_CORRECT,
                "DENY": P_DENY}
for _a, _p in ACT_PATTERNS.items():
    assert len(_p) >= 40, (_a, len(_p))
del _a, _p

# ------------------------------------------------------------- builder ---
class Ctx:
    def __init__(self, rng, names, openers, closers):
        self.rng = rng
        self.names = names
        self.openers = openers
        self.closers = closers

def pick_value(rng, kind, person_pool):
    pool = kind_value_pool(kind)
    if pool is None:
        v = rng.choice(person_pool)
        while v in ():
            v = rng.choice(person_pool)
        return v
    return rng.choice(pool)

def find(s, sub):
    i = s.find(sub)
    if i < 0:
        raise ValueError(f"surface {sub!r} missing in {s!r}")
    return [i, i + len(sub)]

import re as _re

def wfind(s, sub, start=0):
    m = _re.search(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)", s[start:])
    if not m:
        raise ValueError(f"whole-word {sub!r} missing in {s!r} from {start}")
    return [start + m.start(), start + m.end()]

def wrfind(s, sub):
    ms = list(_re.finditer(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)", s))
    if not ms:
        raise ValueError(f"whole-word {sub!r} missing in {s!r}")
    m = ms[-1]
    return [m.start(), m.end()]

def wfind_cue(s, sub, o_span):
    """Cue usually follows the owner ("{O}'s {R}") but precedes it in
    "The {R} of {O}" shapes: prefer after-owner, else last before-owner."""
    if isinstance(o_span, str):
        return wfind(s, sub, 0)
    m = _re.search(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)", s[o_span[1]:])
    if m:
        return [o_span[1] + m.start(), o_span[1] + m.end()]
    ms = list(_re.finditer(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)",
                           s[:o_span[0]]))
    if not ms:
        raise ValueError(f"whole-word cue {sub!r} missing in {s!r}")
    m = ms[-1]
    return [m.start(), m.end()]

def wfind_cue_multi(s, sub, o_span):
    """Cue surface may be pluralized ({RPL} patterns): try plain, then plural."""
    try:
        return wfind_cue(s, sub, o_span), sub
    except ValueError:
        pl = pluralize(sub)
        return wfind_cue(s, pl, o_span), pl

def wfind_value(s, sub, after, avoid):
    """Value may precede the cue ("{V} is {O}'s {R}."): prefer after-cue,
    else first whole-word occurrence outside the avoided spans."""
    m = _re.search(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)", s[after:])
    if m:
        return [after + m.start(), after + m.end()]
    for m in _re.finditer(r"(?<!\w)" + _re.escape(sub) + r"(?!\w)", s):
        sp = [m.start(), m.end()]
        if all(sp[1] <= a[0] or sp[0] >= a[1] for a in avoid):
            return sp
    raise ValueError(f"whole-word value {sub!r} missing in {s!r}")

def apply_noise(text, rng, tail_start=None, opener=None):
    """Chat noise that preserves whole-word spans. Returns
    (new_text, index_map: new_index -> old_index, removed_old_positions).
    Modes: lowercase / drop trailing ? / drop one apostrophe / double a
    letter inside the closer tail / double a space / drop opener comma /
    swap final . for !. The doubler never touches the core (tail only)."""
    if tail_start is None:
        tail_start = len(text)
    mode = rng.random()
    if mode < 0.25:
        return text.lower(), list(range(len(text))), set()
    if mode < 0.38 and text.endswith("?"):
        return text[:-1], list(range(len(text) - 1)), set()
    if mode < 0.50 and "'" in text:
        drop = rng.choice([i for i, ch in enumerate(text) if ch == "'"])
        out, mp = [], []
        for i, ch in enumerate(text):
            if i == drop:
                continue
            out.append(ch)
            mp.append(i)
        return "".join(out), mp, {drop}
    if mode < 0.62 and tail_start < len(text):
        cands = [i for i in range(tail_start, len(text))
                 if text[i].isalpha()]
        if cands:
            g = rng.choice(cands)
            return text[:g] + text[g] + text[g:], \
                list(range(g)) + [g] + list(range(g, len(text))), set()
    if mode < 0.74 and "  " not in text:
        spaces = [i for i, ch in enumerate(text) if ch == " "]
        if spaces:
            g = rng.choice(spaces)
            return text[:g] + " " + text[g:], \
                list(range(g)) + [g] + list(range(g, len(text))), set()
    if mode < 0.86 and opener and opener.endswith(", ") and \
            opener != "So, " and text.startswith(opener):
        g = len(opener) - 2  # the comma
        return text[:g] + text[g + 1:], \
            list(range(g)) + list(range(g + 1, len(text))), set()
    if text.endswith("."):
        return text[:-1] + "!", list(range(len(text))), set()
    return text.lower(), list(range(len(text))), set()

def remap(span, mp):
    s, e = span
    ns = next(i for i, o in enumerate(mp) if o >= s)
    ne = next((i for i, o in enumerate(mp) if o >= e), len(mp))
    return [ns, ne]

def extend_apos(text, nspan, ospan, removed):
    """After apostrophe removal, a NAME owner span like Robin in "Robins"
    is no longer whole-word: extend it over the possessive s."""
    ns, ne = nspan
    if ospan[1] in removed and ne < len(text) and text[ne] == "s" and \
            (ne + 1 >= len(text) or not _re.match(r"\w", text[ne + 1])):
        return [ns, ne + 1]
    return nspan

def render_owner(pat, owner_kind, owner_name):
    if owner_kind == "ME":
        return pat.replace("{O}'s", "my").replace("{O}", "me") \
                  .replace("their", "my").replace("they", "I")
    if owner_kind == "WE":
        return pat.replace("{O}'s", "our").replace("{O}", "us") \
                  .replace("their", "our").replace("they", "we")
    return pat.replace("{O}", owner_name)

def build_single(rng, ctx, act, kind, rel, cue, owner_kind, owner_name,
                 value, frame_id, family, prev_reply="", opener=None,
                 closer=None, noise=False, typo_of=None):
    O = {"ME": "my", "WE": "our"}.get(owner_kind, owner_name)
    R = cue
    V = value
    if act == "ASK":
        pat = rng.choice([p for p in P_ASK
                          if ("{V2}" not in p and "{V}" not in p)])
        core = render_owner(pat, owner_kind, owner_name).replace("{R}", R)
    elif act in ("CORRECT", "DENY"):
        cands = [p for p in ACT_PATTERNS[act] if "{OLD}" not in p]
        pat = rng.choice(cands)
        core = render_owner(pat, owner_kind, owner_name) \
            .replace("{RPL}", pluralize(R)).replace("{R}", R).replace("{V}", V)
    else:
        cands = [p for p in ACT_PATTERNS[act]
                 if "{OLD}" not in p and "{V2}" not in p]
        pat = rng.choice(cands)
        core = render_owner(pat, owner_kind, owner_name) \
            .replace("{RPL}", pluralize(R)).replace("{R}", R).replace("{V}", V)
    if opener is None:
        opener = rng.choice(ctx.openers)
    if closer is None:
        closer = rng.choice(ctx.closers)
    text = opener + core + closer
    o_span = wfind(text, O, 0) if owner_kind not in ("ME", "WE") else owner_kind
    c_span, R = wfind_cue_multi(text, R, o_span)
    is_ask = (act == "ASK")
    if is_ask:
        v_span = None
    elif isinstance(o_span, str):
        v_span = wfind_value(text, V, c_span[1], [c_span])
    else:
        v_span = wfind_value(text, V, c_span[1], [o_span, c_span])
    world_fact = {"owner_kind": owner_kind,
                  "owner": None if owner_kind in ("ME", "WE") else O,
                  "cue": R, "value": V, "relation": rel}
    if act == "ASK":
        q = {"owner_span": o_span, "relations": [rel], "inverse": False}
        facts, question, count = [], q, 0
        world_q = {"owner_kind": owner_kind,
                   "owner": None if owner_kind in ("ME", "WE") else O,
                   "inverse": False}
    else:
        facts = [{"owner": o_span, "relation": rel,
                  "relation_cue_span": c_span, "value_span": v_span,
                  "mode": MODE_OF[act]}]
        question, count = None, 1
        world_q = None
    if noise:
        o_old = o_span
        text2, mp, removed = apply_noise(text, rng,
                                         len(text) - len(closer), opener)
        text = text2
        for f in facts:
            if isinstance(f["owner"], list):
                f["owner"] = extend_apos(text, remap(f["owner"], mp),
                                         f["owner"], removed)
            f["relation_cue_span"] = remap(f["relation_cue_span"], mp)
            f["value_span"] = remap(f["value_span"], mp)
        if question and isinstance(question["owner_span"], list):
            question["owner_span"] = extend_apos(
                text, remap(question["owner_span"], mp),
                question["owner_span"], removed)
        for f, w in zip(facts, [world_fact]):
            if isinstance(f["owner"], list):
                w["owner"] = text[f["owner"][0]:f["owner"][1]]
            w["cue"] = text[f["relation_cue_span"][0]:f["relation_cue_span"][1]]
            w["value"] = text[f["value_span"][0]:f["value_span"][1]]
        if question and isinstance(question["owner_span"], list):
            o = question["owner_span"]
            world_q["owner"] = text[o[0]:o[1]]
    if typo_of is not None:
        V, world_fact["value"] = value, value  # typed form already in text
    return {"prev_reply": prev_reply, "turn": text, "act": act, "count": count,
            "facts": facts, "question": question,
            "spelling_flag": typo_of is not None,
            "world": {"facts": [world_fact] if not is_ask else [],
                      "question": world_q,
                      "context": {"kind": kind},
                      "typo_canonical": typo_of},
            "family": family, "frame_id": frame_id}

def build_disjunction(rng, ctx, kind, rels_cues, owner_kind, owner_name,
                      v1, v2, frame_id):
    O = {"ME": "my", "WE": "our"}.get(owner_kind, owner_name)
    pat = rng.choice([p for p in P_ASK if "{V2}" in p])
    core = render_owner(pat, owner_kind, owner_name) \
        .replace("{R}", rels_cues[0][1]) \
        .replace("{V}", v1).replace("{V2}", v2)
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    o = wfind(text, O, 0) if owner_kind not in ("ME", "WE") else owner_kind
    return {"prev_reply": "", "turn": text, "act": "ASK", "count": 0,
            "facts": [],
            "question": {"owner_span": o,
                         "relations": [r for r, _ in rels_cues],
                         "inverse": False},
            "spelling_flag": False,
            "world": {"facts": [],
                      "question": {"owner_kind": owner_kind,
                                   "owner": None if owner_kind in ("ME", "WE") else O,
                                   "inverse": False},
                      "context": {"kind": kind}, "typo_canonical": None},
            "family": "ask", "frame_id": frame_id}

def build_inverse_ask(rng, ctx, rel, cue_word, owner_name, frame_id, inverse_rel):
    # "Who is Ada's child?" -> owner Ada, relation mother, inverse True.
    pat = rng.choice([p for p in P_ASK
                      if "{V}" not in p and "{V2}" not in p and "who" in p.lower()])
    core = pat.replace("{O}", owner_name).replace("{R}", cue_word)
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    o = wfind(text, owner_name, 0)
    return {"prev_reply": "", "turn": text, "act": "ASK", "count": 0,
            "facts": [],
            "question": {"owner_span": o, "relations": [inverse_rel],
                         "inverse": True},
            "spelling_flag": False,
            "world": {"facts": [],
                      "question": {"owner_kind": "NAME", "owner": owner_name,
                                   "inverse": True},
                      "context": {"kind": "kin"}, "typo_canonical": None},
            "family": "ask", "frame_id": frame_id}

INVERSE_OF = {"son": "mother", "daughter": "mother", "child": "mother",
              "mother": "daughter", "father": "son"}
INVERSE_CUE = {"son": "son", "daughter": "daughter", "child": "child",
               "mother": "mother", "father": "father"}

def build_binding(rng, ctx, frame_id, family):
    a = rng.choice(ctx.names)
    b = rng.choice([n for n in ctx.names if n != a])
    masc = rng.random() < 0.5
    # fact1: a's son/daughter is b. fact2: pronoun lives in place.
    if masc:
        krel, kcue = "son", "son"
        pro2, pro2b = "he", "she"
    else:
        krel, kcue = "daughter", "daughter"
        pro2, pro2b = "she", "he"
    flip = rng.random() < 0.5
    # Counterfactual minimal pair: the possessive agrees with the referent.
    # flip=False -> "his/her hometown" refers to b; flip=True -> refers to a.
    place = rng.choice(PLACES)
    if flip:
        poss = "her"  # refers to a (she/her in this family)
    else:
        poss = "his" if masc else "her"
    core = (f"{a}'s {kcue} is {b} and {poss} hometown is {place}.")
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    s_a = wfind(text, a, 0)
    s_k = wfind(text, kcue, s_a[1])
    s_b = wfind(text, b, s_k[1])
    s_p = wfind(text, poss, s_b[1])
    s_ht = wfind(text, "hometown", s_p[1])
    s_pl = wfind(text, place, s_ht[1])
    if flip:
        owner2, wowner2 = [s_a[0], s_a[1]], a
    else:
        owner2, wowner2 = [s_p[0], s_p[1]], poss
    row = {"prev_reply": "", "turn": text, "act": "STATE", "count": 2,
           "facts": [
               {"owner": s_a, "relation": krel, "relation_cue_span": s_k,
                "value_span": s_b, "mode": "ASSERT"},
               {"owner": owner2, "relation": "hometown",
                "relation_cue_span": s_ht, "value_span": s_pl,
                "mode": "ASSERT"}],
           "question": None, "spelling_flag": False,
           "world": {"facts": [
               {"owner_kind": "NAME", "owner": a, "cue": kcue,
                "value": b, "relation": krel},
               {"owner_kind": "NAME", "owner": wowner2, "cue": "hometown",
                "value": place, "relation": "hometown"}],
               "question": None, "context": {"kind": "binding"},
               "typo_canonical": None},
           "family": family, "frame_id": frame_id}
    return row

def pluralize(cue):
    words = cue.split(" ")
    w = words[-1]
    if len(w) > 1 and w.endswith("y") and w[-2] not in "aeiou":
        w = w[:-1] + "ies"
    elif w.endswith(("s", "x", "ch", "sh")):
        w = w + "es"
    else:
        w = w + "s"
    words[-1] = w
    return " ".join(words)

def build_plural(rng, ctx, kind, rel, cue, frame_id, family):
    n = rng.choice([2, 2, 2, 3])
    owners = rng.sample(ctx.names, n + 1)
    vals, owner_kind = owners[:n], "ME"
    cue_p = pluralize(cue)
    if rng.random() < 0.5:
        core = f"{' and '.join(vals[:-1]) + ' and ' + vals[-1] if n > 2 else ' and '.join(vals)} are my {cue_p}."
        core = core.replace("  ", " ")
    else:
        core = f"My {cue_p} are {', '.join(vals[:-1]) + ' and ' + vals[-1] if n > 2 else ' and '.join(vals)}."
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    c_span = wfind(text, cue_p, 0)
    facts, wfacts = [], []
    for v in vals:
        vs = wfind(text, v, 0)
        # duplicate values share surface: rescanned in order below
        facts.append({"owner": "ME", "relation": rel,
                      "relation_cue_span": c_span, "value_span": vs,
                      "mode": "ASSERT"})
        wfacts.append({"owner_kind": "ME", "owner": None, "cue": cue_p,
                       "value": v, "relation": rel})
    # fix repeated-value spans: re-scan occurrences in order
    occ = []
    start = 0
    for v in vals:
        o = wfind(text, v, start)
        occ.append(o)
        start = o[1]
    for f, o in zip(facts, occ):
        f["value_span"] = o
    return {"prev_reply": "", "turn": text, "act": "STATE", "count": n,
            "facts": facts, "question": None, "spelling_flag": False,
            "world": {"facts": wfacts, "question": None,
                      "context": {"kind": kind}, "typo_canonical": None},
            "family": family, "frame_id": frame_id}

def build_appositive(rng, ctx, frame_id, family):
    boss = rng.choice([n for n in ctx.names])
    pet = rng.choice(PET_NAMES)
    rcue = rng.choice(["boss", "manager", "teacher", "mentor", "doctor"])
    rel1 = {"boss": "boss", "manager": "boss", "teacher": "teacher",
            "mentor": "mentor", "doctor": "doctor"}[rcue]
    pcue = rng.choice(["dog", "cat", "horse", "rabbit", "hamster", "parrot"])
    core = f"My {rcue}, {boss}, has a {pcue} named {pet}."
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    s_rc = wfind(text, rcue, 0)
    # value 'boss-name': first occurrence after rcue
    s_b = wfind(text, boss, s_rc[1])
    s_pc = wfind(text, pcue, s_b[1])
    s_p = wfind(text, pet, s_pc[1])
    return {"prev_reply": "", "turn": text, "act": "STATE", "count": 2,
            "facts": [
                {"owner": "ME", "relation": rel1,
                 "relation_cue_span": s_rc, "value_span": s_b,
                 "mode": "ASSERT"},
                {"owner": [s_b[0], s_b[1]], "relation": pcue,
                 "relation_cue_span": s_pc, "value_span": s_p,
                 "mode": "ASSERT"}],
            "question": None, "spelling_flag": False,
            "world": {"facts": [
                {"owner_kind": "ME", "owner": None, "cue": rcue,
                 "value": boss, "relation": rel1},
                {"owner_kind": "NAME", "owner": boss, "cue": pcue,
                 "value": pet, "relation": pcue}],
                "question": None, "context": {"kind": "appositive"},
                "typo_canonical": None},
            "family": family, "frame_id": frame_id}

def build_correction(rng, ctx, kind, rel, cue, frame_id, family):
    owner = rng.choice(ctx.names)
    pool = kind_value_pool(kind)
    old = rng.choice(pool if pool is not None else ctx.names)
    new = rng.choice([v for v in (pool if pool is not None else ctx.names)
                      if v != old])
    prev = rng.choice(["Got it.", "Okay.", "Thanks.", "Noted."])
    prev = f"{prev} I saved that {owner}'s {cue} is {old}."
    deny = rng.random() < 0.35
    if deny:
        pat = rng.choice([p for p in P_DENY if "{OLD}" not in p])
        core = pat.replace("{O}", owner).replace("{RPL}", pluralize(cue)) \
                  .replace("{R}", cue).replace("{V}", old)
        world_v, mode, act = old, "DENY", "DENY"
    else:
        cands = [p for p in P_CORRECT if "{OLD}" in p] + \
                [p for p in P_CORRECT if "{OLD}" not in p]
        pat = rng.choice(cands)
        core = pat.replace("{O}", owner).replace("{RPL}", pluralize(cue)) \
                  .replace("{R}", cue) \
                  .replace("{V}", new).replace("{OLD}", old)
        world_v, mode, act = new, "CORRECT", "CORRECT"
    opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
    text = opener + core + closer
    o_span = wfind(text, owner, 0)
    c_span, cue_surf = wfind_cue_multi(text, cue, o_span)
    # value: last whole-word occurrence (dodges OLD/NEW confusion)
    v_span = wrfind(text, world_v)
    return {"prev_reply": prev, "turn": text, "act": act, "count": 1,
            "facts": [{"owner": o_span, "relation": rel,
                       "relation_cue_span": c_span, "value_span": v_span,
                       "mode": mode}],
            "question": None, "spelling_flag": False,
            "world": {"facts": [{"owner_kind": "NAME", "owner": owner,
                                 "cue": cue_surf, "value": world_v,
                                 "relation": rel}],
                      "question": None, "context": {"kind": kind},
                      "typo_canonical": None},
            "family": family, "frame_id": frame_id}

def typo_surface(rng, value):
    v = value
    if len(v) >= 6:
        # drop one of a doubled letter, else drop an interior letter
        for i in range(1, len(v)):
            if v[i] == v[i - 1] and v[i].isalpha():
                return v[:i] + v[i + 1:]
        i = rng.randrange(1, len(v) - 1)
        return v[:i] + v[i + 1:]
    # short value: swap two interior letters
    if len(v) >= 4:
        i = rng.randrange(0, len(v) - 2)
        return v[:i] + v[i + 1] + v[i] + v[i + 2:]
    return v + v[-1:]

# ----------------------------------------------------------------- split ---
def all_frame_ids():
    ids = []
    for kind in KINDS:
        for i in range(48):
            ids.append(f"tell/STATE/{kind}/{i:03d}")
        for i in range(48):
            ids.append(f"ask/ASK/{kind}/{i:03d}")
        for act in ("STATE", "ASK", "CHECK", "CORRECT", "DENY", "SUPPOSE",
                    "PLAN"):
            for i in range(48):
                ids.append(f"act/{act}/{kind}/{i:03d}")
        for act in ("STATE", "ASK", "CHECK"):
            for i in range(48):
                ids.append(f"noise/{act}/{kind}/{i:03d}")
        for i in range(48):
            ids.append(f"plural/{kind}/{i:03d}")
        for i in range(48):
            ids.append(f"correction/{kind}/{i:03d}")
        for i in range(48):
            ids.append(f"typo/{kind}/{i:03d}")
    for i in range(96):
        ids.append(f"chat/chat/all/{i:03d}")
    for i in range(48):
        ids.append(f"binding/bind/all/{i:03d}")
    for i in range(48):
        ids.append(f"appositive/app/all/{i:03d}")
    return ids

def frame_split():
    frames = all_frame_ids()
    rng = random.Random(999)
    l1, l2 = [], []
    groups = {}
    for f in frames:
        parts = f.split("/")
        groups.setdefault("/".join(parts[:2]), []).append(f)
    for g, fs in groups.items():
        fs = sorted(fs)
        rng.shuffle(fs)
        k = max(1, int(round(0.2 * len(fs))))
        l2.extend(fs[:k])
        l1.extend(fs[k:])
    return {"l1": sorted(l1), "l2": sorted(l2)}

# -------------------------------------------------------------- generate ---
GEN_WEIGHTS = [("tell", 10), ("ask", 10), ("chat", 10), ("act", 10),
               ("binding", 10), ("plural", 10), ("appositive", 10),
               ("correction", 10), ("noise", 10), ("typo", 10)]

def gen_row(rng, ctx, split, frame_id, l2set):
    parts = frame_id.split("/")
    fam = parts[0]
    if fam == "tell":
        _, act, kind, _ = parts
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        owner_kind = rng.choice(["NAME", "NAME", "NAME", "ME"])
        owner = rng.choice(ctx.names) if owner_kind == "NAME" else None
        value = pick_value(rng, kind, [n for n in ctx.names if n != owner])
        return build_single(rng, ctx, "STATE", kind, rel, cue, owner_kind,
                            owner, value, frame_id, "tell")
    if fam == "ask":
        _, _act, kind, idx = parts
        r = rng.random()
        if r < 0.15:
            # inverse question
            base = rng.choice(sorted(INVERSE_OF.keys()))
            inv = INVERSE_OF[base]
            owner = rng.choice(ctx.names)
            return build_inverse_ask(rng, ctx, base, INVERSE_CUE[base],
                                     owner, frame_id, inv)
        if r < 0.30:
            rels = rng.sample(sorted(KINDS[kind].keys()), 2)
            cues = [(rel, rng.choice(KINDS[kind][rel])) for rel in rels]
            owner_kind = rng.choice(["NAME", "ME"])
            owner = rng.choice(ctx.names) if owner_kind == "NAME" else None
            v1 = pick_value(rng, kind, ctx.names)
            v2 = pick_value(rng, kind, ctx.names)
            return build_disjunction(rng, ctx, kind, cues, owner_kind, owner,
                                     v1, v2, frame_id)
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        owner_kind = rng.choice(["NAME", "NAME", "ME"])
        owner = rng.choice(ctx.names) if owner_kind == "NAME" else None
        row = build_single(rng, ctx, "ASK", kind, rel, cue, owner_kind,
                           owner, "Unused", frame_id, "ask")
        return row
    if fam == "chat":
        if rng.random() < 0.06:
            core = rng.choice(P_UNCLEAR)
            act = "UNCLEAR"
        else:
            core = rng.choice(P_CHAT)
            act = "CHAT"
        opener = rng.choice(ctx.openers) if rng.random() < 0.3 else ""
        closer = rng.choice(ctx.closers) if rng.random() < 0.3 else ""
        text = opener + core + closer
        return {"prev_reply": rng.choice(["", "Hey!", "Hi there."]),
                "turn": text, "act": act, "count": 0, "facts": [],
                "question": None, "spelling_flag": False,
                "world": {"facts": [], "question": None,
                          "context": {"kind": "chat"},
                          "typo_canonical": None},
                "family": "chat", "frame_id": frame_id}
    if fam == "act":
        _, act, kind, _ = parts
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        owner = rng.choice(ctx.names)
        others = [n for n in ctx.names if n != owner]
        value = pick_value(rng, kind, others)
        if act in ("CORRECT", "DENY"):
            old = pick_value(rng, kind, [n for n in others if n != value])
            prev = f"Okay. I saved that {owner}'s {cue} is {old}."
        else:
            old, prev = None, rng.choice(["", "Got it.", "Okay."])
        O = owner
        if act in ("CORRECT",):
            cands = [p for p in P_CORRECT if "{OLD}" in p] + \
                    [p for p in P_CORRECT if "{OLD}" not in p]
            pat = rng.choice(cands)
            core = pat.replace("{O}", O).replace("{RPL}", pluralize(cue)) \
                      .replace("{R}", cue) \
                      .replace("{V}", value).replace("{OLD}", old or value)
            wv = value
        elif act == "DENY":
            pat = rng.choice([p for p in P_DENY if "{OLD}" not in p])
            core = pat.replace("{O}", O).replace("{RPL}", pluralize(cue)) \
                      .replace("{R}", cue).replace("{V}", old)
            wv, value = old, old
        elif act == "ASK":
            pat = rng.choice([p for p in P_ASK
                              if "{V2}" not in p and "{V}" not in p])
            core = pat.replace("{O}", O).replace("{R}", cue)
            wv = None
        else:
            pat = rng.choice([p for p in ACT_PATTERNS[act]
                              if "{OLD}" not in p and "{V2}" not in p])
            core = pat.replace("{O}", O).replace("{R}", cue).replace("{V}", value)
            wv = value
        opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
        text = opener + core + closer
        o_span = wfind(text, O, 0)
        c_span, cue_surf = wfind_cue_multi(text, cue, o_span)
        if act == "ASK":
            q = {"owner_span": o_span, "relations": [rel], "inverse": False}
            facts, question, count = [], q, 0
            wfacts, wq = [], {"owner_kind": "NAME", "owner": O,
                              "inverse": False}
        else:
            v_span = wrfind(text, wv)
            facts = [{"owner": o_span, "relation": rel,
                      "relation_cue_span": c_span, "value_span": v_span,
                      "mode": MODE_OF[act]}]
            question, count = None, 1
            wfacts, wq = [{"owner_kind": "NAME", "owner": O, "cue": cue_surf,
                           "value": wv, "relation": rel}], None
        return {"prev_reply": prev, "turn": text, "act": act, "count": count,
                "facts": facts, "question": question, "spelling_flag": False,
                "world": {"facts": wfacts, "question": wq,
                          "context": {"kind": kind}, "typo_canonical": None},
                "family": "act", "frame_id": frame_id}
    if fam == "binding":
        return build_binding(rng, ctx, frame_id, "binding")
    if fam == "plural":
        _, kind, _ = parts
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = KINDS[kind][rel][0]
        return build_plural(rng, ctx, kind, rel, cue, frame_id, "plural")
    if fam == "appositive":
        return build_appositive(rng, ctx, frame_id, "appositive")
    if fam == "correction":
        _, kind, _ = parts
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        return build_correction(rng, ctx, kind, rel, cue, frame_id,
                                "correction")
    if fam == "noise":
        _, act, kind, _ = parts
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        owner_kind = rng.choice(["NAME", "NAME", "ME"])
        owner = rng.choice(ctx.names) if owner_kind == "NAME" else None
        value = pick_value(rng, kind, [n for n in ctx.names if n != owner])
        if act == "ASK":
            row = build_single(rng, ctx, "ASK", kind, rel, cue, owner_kind,
                               owner, "Unused", frame_id, "noise",
                               noise=True)
        else:
            row = build_single(rng, ctx, act, kind, rel, cue, owner_kind,
                               owner, value, frame_id, "noise", noise=True)
        return row
    if fam == "typo":
        kind = parts[1]
        rel = rng.choice(sorted(KINDS[kind].keys()))
        cue = rng.choice(KINDS[kind][rel])
        owner = rng.choice(ctx.names)
        pool = kind_value_pool(kind)
        canon = rng.choice(pool if pool is not None else
                           [n for n in ctx.names if n != owner])
        typed = typo_surface(rng, canon)
        if typed == canon:
            typed = canon[:-1]
        O = owner
        pat = rng.choice([p for p in P_STATE if "{OLD}" not in p])
        core = pat.replace("{O}", O).replace("{R}", cue).replace("{V}", typed)
        opener, closer = rng.choice(ctx.openers), rng.choice(ctx.closers)
        text = opener + core + closer
        o_span = wfind(text, O, 0)
        c_span, cue_surf = wfind_cue_multi(text, cue, o_span)
        v_span = wrfind(text, typed)
        return {"prev_reply": rng.choice(["", "Got it.", "Okay."]),
                "turn": text, "act": "STATE", "count": 1,
                "facts": [{"owner": o_span, "relation": rel,
                           "relation_cue_span": c_span, "value_span": v_span,
                           "mode": "ASSERT"}],
                "question": None, "spelling_flag": True,
                "world": {"facts": [{"owner_kind": "NAME", "owner": O,
                                     "cue": cue_surf, "value": typed,
                                     "relation": rel}],
                          "question": None, "context": {"kind": kind},
                          "typo_canonical": canon},
                "family": "typo", "frame_id": frame_id}
    raise ValueError(frame_id)

def make_ctx(rng, split):
    if split == "train":
        names = list(TRAIN_NAMES)
        openers, closers = TRAIN_OPENERS, TRAIN_CLOSERS
    elif split == "l1dev":
        names = list(L1_NAMES)
        openers, closers = TRAIN_OPENERS, TRAIN_CLOSERS
    else:
        names = list(RESERVED_NAMES)
        openers, closers = OPENERS, CLOSERS
    return Ctx(rng, names, openers, closers)

def gen_split(split, n, seed, frames):
    rng = random.Random(seed)
    ctx = make_ctx(rng, split)
    rows = []
    fams = [f for f, w in GEN_WEIGHTS for _ in range(w)]
    for i in range(n):
        fam = fams[i % len(fams)]
        cands = [f for f in frames if f.split("/")[0] == fam]
        fid = rng.choice(cands)
        try:
            row = gen_row(rng, ctx, split, fid, None)
        except ValueError:
            continue
        row["id"] = f"o0b-{split}-{len(rows):06d}"
        row["split"] = split
        rows.append(row)
    return rows

def write_shards(rows, outdir, stem, per=25000):
    import gzip as _g
    paths = []
    for i in range(0, len(rows), per):
        p = outdir / f"{stem}-{i // per:02d}.jsonl.gz"
        with _g.open(p, "wt", encoding="utf-8") as fh:
            for r in rows[i:i + per]:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        paths.append(p)
    return paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pilot", "full"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    sp = frame_split()
    if args.mode == "pilot":
        rng = random.Random(args.seed)
        ctx = make_ctx(rng, "train")
        rows = []
        for i in range(args.n):
            fams = [f for f, w in GEN_WEIGHTS for _ in range(w)]
            fam = fams[i % len(fams)]
            cands = [f for f in sp["l1"] if f.split("/")[0] == fam]
            row = gen_row(rng, ctx, "train", rng.choice(cands), None)
            row["id"] = f"o0b-pilot-{i:06d}"
            row["split"] = "train"
            rows.append(row)
        paths = write_shards(rows, outdir, "pilot", per=100000)
    else:
        allp = []
        train = gen_split("train", 200000, 11, sp["l1"])
        allp += write_shards(train, outdir, "train", per=25000)
        l1 = gen_split("l1dev", 5000, 22, sp["l1"])
        allp += write_shards(l1, outdir, "l1dev", per=100000)
        l2 = gen_split("l2dev", 5000, 33, sp["l2"])
        allp += write_shards(l2, outdir, "l2dev", per=100000)
        from collections import Counter
        counts = {"train": dict(Counter(r["family"] for r in train)),
                  "l1dev": dict(Counter(r["family"] for r in l1)),
                  "l2dev": dict(Counter(r["family"] for r in l2)),
                  "l1_frames": len(sp["l1"]), "l2_frames": len(sp["l2"]),
                  "files": [p.name for p in allp]}
        (outdir / "counts.json").write_text(json.dumps(counts, indent=1))
        (outdir / "frame_split.json").write_text(json.dumps(sp, indent=1))
        (outdir / "name_pools.json").write_text(json.dumps(
            {"train": TRAIN_NAMES, "l1_new": L1_NAMES,
             "reserved_l2_only": RESERVED_NAMES,
             "openers_trained": TRAIN_OPENERS,
             "openers_heldout_l2_only": sorted(HELDOUT_OPENERS),
             "closers_trained": TRAIN_CLOSERS,
             "closers_heldout_l2_only": sorted(HELDOUT_CLOSERS)}, indent=1))
        paths = allp
    for p in paths:
        print("wrote", p, p.stat().st_size, "bytes")

if __name__ == "__main__":
    main()