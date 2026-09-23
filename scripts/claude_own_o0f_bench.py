"""own-O0f: SEALED COMPARISON BENCHMARK generator + rule-based checker (plan 01 sec 7).

Blind to all model code. CPU only. Fictional names only.
Relation names come from artifacts/claude-smolear257-20260922/relation_table_v2.json.

Usage:
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
      scripts/claude_own_o0f_bench.py generate   # writes 5 jsonl files
  ... python -B scripts/claude_own_o0f_bench.py verify    # rule-based re-derivation, read-only

Layout per world (one JSON object per line):
  {world_id, family, names[], conversation[{speaker,text}], facts[{s,r,v}],
   corrections[{s,r,old,new}], questions[{qid,kind,text,gold}]}
Gold "I don't know" marks abstention. Token budget: every conversation <= 900
tokens at ~4 chars each (<= 3600 chars); the verifier reports the max.
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
REL_PATH = os.path.join(REPO, "artifacts", "claude-smolear257-20260922",
                        "relation_table_v2.json")
OUT_DIR = os.path.join(REPO, "artifacts", "claude-own-bench-20260923")

SEED = 20260923
N_PER_FAMILY = 500
IDK = "I don't know"

FAMILIES = ["two_hop", "reversal", "abstention", "mquake_edit", "long_chain"]

# Names seen in the plan / examples: never reuse them.
BLOCKED = {"ada", "bo", "mira", "tal", "oona", "oren", "pip", "fig", "moss",
           "rook", "milan", "farah", "fara", "mira stil", "mira still",
           "anna", "maria", "john", "david", "sarah", "mike", "lisa", "tom",
           "ben", "sam", "alex", "chris", "pat", "kim", "lee", "ali"}

_SYL_A = ["al", "bel", "cor", "dal", "el", "fal", "gar", "hal", "il", "jor",
          "kel", "lor", "mal", "nor", "pel", "quen", "ral", "sel", "tor",
          "ul", "vel", "wil", "xan", "yar", "zel", "bran", "cren", "dren",
          "fen", "glim", "har", "kes", "lun", "mor", "nix", "prin", "quil",
          "ros", "stan", "tarn", "vex", "wren", "ysol", "zor", "thalen",
          "bre", "cal", "dor", "es", "fir", "gor", "hes", "irth"]
_SYL_B = ["a", "e", "i", "o", "av", "en", "il", "or", "an", "el", "ar",
          "is", "on", "uin", "ae", "ia"]
_SYL_C = ["a", "ia", "or", "en", "il", "as", "eth", "ara", "ond", "ith",
          "iel", "wyn", "ock", "ald", "essa", "ir", "am", "ost", "el",
          "una", "ove", "is"]


def make_names(rng, used, n):
    out = []
    while len(out) < n:
        nm = (rng.choice(_SYL_A) + rng.choice(_SYL_B) + rng.choice(_SYL_C))
        nm = nm[0].upper() + nm[1:]
        if nm.lower() in BLOCKED or nm in used:
            continue
        used.add(nm)
        out.append(nm)
    return out


def rel_word(rng, rel):
    if rel.get("aliases") and rng.random() < 0.25:
        return rng.choice(rel["aliases"])
    return rel["name"].replace("_", " ")


# ---------------------------------------------------------------- templates
# Every family owns >= 30 teach and >= 30 ask templates (asserted at runtime).
# All wordings are fresh; none copies the plan's examples.

def _teach_set(leads, cores):
    seen, out = set(), []
    for ld in leads:
        for co in cores:
            t = (ld + " " + co).strip() if ld else co
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


_TEACH_CORES_A = [
    "{S}'s {R} is {V}.",
    "{S} has a {R} named {V}.",
    "{S} has a {R} called {V}.",
    "The {R} of {S} is {V}.",
    "{S}'s {R} goes by the name {V}.",
    "{S} counts {V} as a {R}.",
    "{S} introduced {V} as the {R}.",
]
_TEACH_CORES_B = [
    "{S}'s {R} happens to be {V}.",
    "{S} keeps in touch with {V}, the {R}.",
    "As far as {S} goes, the {R} is {V}.",
    "{S} always names {V} when asked about the {R}.",
    "Where {S} is concerned, {V} is the {R}.",
    "{S} relies on {V} as a {R}.",
    "{S} points to {V} whenever the {R} comes up.",
]
_TEACH_CORES_C = [
    "If you ask {S} about the {R}, the answer is {V}.",
    "{S} will tell you straight away that the {R} is {V}.",
    "The person {S} calls the {R} is {V}.",
    "{S} regards {V} as the {R}.",
    "Around here everybody links {S} with {V} the {R}.",
    "{S} wrote down {V} under {R}.",
    "Ask anyone near {S}: the {R} is {V}.",
]
_TEACH_CORES_D = [
    "{S} confirmed that the {R} is {V}.",
    "Word is that {S}'s {R} is {V}.",
    "{S} let on that {V} is the {R}.",
    "It turns out {S}'s {R} is {V}.",
    "{S} finally admitted the {R} is {V}.",
    "News about {S}: the {R} is {V}.",
    "{S} clarified that {V} holds the {R} spot.",
]
_TEACH_CORES_E = [
    "{S} grew up alongside {V}, the {R}.",
    "These days {S}'s {R} is {V}.",
    "{S} spends most days with {V} the {R}.",
    "Lately {S} keeps mentioning {V} the {R}.",
    "{S} trusts {V} with the whole {R} business.",
    "For {S}, {V} fills the {R} role.",
    "People pair {S} with {V} whenever a {R} is needed.",
]

_LEADS_1 = ["", "Just so you know,", "For the record,", "Remember that",
            "Keep in mind that", "I should mention that", "You should know that"]
_LEADS_2 = ["", "Fun fact:", "Heads up:", "One thing to remember:",
            "Adding to what I said before,", "To keep the story straight,",
            "Since you asked about the household,"]
_LEADS_3 = ["", "Between you and me,", "To fill in the background,",
            "For your notes,", "Small detail:", "Worth remembering:",
            "As background,"]
_LEADS_4 = ["", "Quick update:", "Setting the record straight,",
            "Before I forget,", "A small correction to the picture:",
            "To be precise,", "On that topic,"]
_LEADS_5 = ["", "Story goes that", "As the neighbours tell it,",
            "If it helps,", "Painting the full picture,", "To round things out,",
            "One more piece:"]

TEACH = {
    "two_hop": _teach_set(_LEADS_1, _TEACH_CORES_A),
    "reversal": _teach_set(_LEADS_2, _TEACH_CORES_B),
    "abstention": _teach_set(_LEADS_3, _TEACH_CORES_C),
    "mquake_edit": _teach_set(_LEADS_4, _TEACH_CORES_D),
    "long_chain": _teach_set(_LEADS_5, _TEACH_CORES_E),
}

_TWO_ASK = [
    "Who is {S}'s {R1}'s {R2}?",
    "Tell me the {R2} of {S}'s {R1}.",
    "Name the {R2} of {S}'s {R1}.",
    "{S}'s {R1} has a {R2} -- who is it?",
    "Who does {S}'s {R1} have as a {R2}?",
    "Follow the chain: {S}, then the {R1}, then the {R2}. Who do you reach?",
    "Starting from {S}, go to the {R1}, then to that person's {R2}. Who is that?",
    "Who is the {R2} belonging to {S}'s {R1}?",
    "Can you name {S}'s {R1}'s {R2}?",
    "Do you know who {S}'s {R1}'s {R2} is?",
    "Quick one: who is {S}'s {R1}'s {R2}?",
    "Just checking: the {R2} of {S}'s {R1} is who?",
    "Remind me, who is {S}'s {R1}'s {R2}?",
    "So who ends up as {S}'s {R1}'s {R2}?",
    "Which person is {S}'s {R1}'s {R2}?",
    "Give me the name of {S}'s {R1}'s {R2}.",
    "I need the {R2} of {S}'s {R1}. Who?",
    "Track it down: {S}'s {R1}, and then their {R2}.",
    "From {S}, hop to the {R1}, hop again to the {R2}. Who lands there?",
    "Who sits at the end of the {S} - {R1} - {R2} chain?",
    "Two hops from {S}: first the {R1}, then the {R2}. Who?",
    "Name the person two steps from {S} through the {R1} and the {R2}.",
    "Whose trail is this: {S}'s {R1}, and that one's {R2}?",
    "Tell me who {S} reaches through the {R1} and then the {R2}.",
    "The {R1} of {S} points on to a {R2}. Who?",
    "Going via {S}'s {R1}, whose {R2} shows up?",
    "Connect the dots from {S} past the {R1} to the {R2}. Who?",
    "If {S} sends word through the {R1} to the {R2}, who gets it?",
    "Who is waiting two links down the line from {S}?",
    "Spell it out: {S}, the {R1}, the {R2}. Final name?",
    "One more: the {R2} of the {R1} of {S}?",
    "Last check on this chain: who is {S}'s {R1}'s {R2}?",
]

_REV_ASK = [
    "Whose {R} is {Y}?",
    "Who has {Y} as a {R}?",
    "Who counts {Y} as their {R}?",
    "{Y} is somebody's {R} -- whose?",
    "Tell me whose {R} {Y} is.",
    "Which person has {Y} for a {R}?",
    "Name the person whose {R} is {Y}.",
    "Who is the one whose {R} is {Y}?",
    "Looking at it from the other side: whose {R} is {Y}?",
    "Flip it around -- who holds {Y} as a {R}?",
    "From {Y}'s side, who claims this {R} link?",
    "Who points to {Y} when asked about their {R}?",
    "Somebody lists {Y} as the {R}. Who?",
    "Quick flip: whose {R} is {Y}?",
    "Just checking the reverse: who has {Y} as a {R}?",
    "Can you say whose {R} {Y} is?",
    "Do you know who counts {Y} as their {R}?",
    "Remind me: {Y} is whose {R}?",
    "So {Y} serves as whose {R}?",
    "Which name pairs with {Y} on the {R} link, from the other end?",
    "Give me the name on the far side of {Y}'s {R} link.",
    "Whose {R} slot does {Y} fill?",
    "I need the other side of this: whose {R} is {Y}?",
    "Trace the {R} line back from {Y}. Who do you find?",
    "If {Y} is the {R}, who is on the asking side?",
    "Who names {Y} when the topic is their {R}?",
    "Whose household lists {Y} as the {R}?",
    "Answer from the far end: whose {R} is {Y}?",
    "Read the link backwards: who reaches {Y} through the {R}?",
    "Who stands opposite {Y} across the {R} link?",
    "Name the asker-side of the {Y} {R} fact.",
    "Final flip on this one: whose {R} is {Y}?",
]

_ABS_ASK_SINGLE = [
    "Who is {S}'s {R}?",
    "Tell me the {R} of {S}.",
    "Name the {R} of {S}.",
    "Do you know who {S}'s {R} is?",
    "Quick one: who is {S}'s {R}?",
    "Just checking: the {R} of {S} is who?",
    "Remind me, who is {S}'s {R}?",
    "Can you name {S}'s {R}?",
    "Which person is {S}'s {R}?",
    "Give me the name of {S}'s {R}.",
    "I need {S}'s {R}. Who?",
    "Who does {S} have as a {R}?",
    "So who is {S}'s {R}, then?",
    "Spell it out: who is the {R} of {S}?",
    "One more: the {R} of {S}?",
    "Last check: who is {S}'s {R}?",
]
_ABS_ASK_CHAIN = [
    "Who is {S}'s {R1}'s {R2}?",
    "Tell me the {R2} of {S}'s {R1}.",
    "Name the {R2} of {S}'s {R1}.",
    "Starting from {S}, go to the {R1}, then to that person's {R2}. Who is that?",
    "Follow the chain: {S}, then the {R1}, then the {R2}. Who do you reach?",
    "Two hops from {S}: first the {R1}, then the {R2}. Who?",
    "Who sits at the end of the {S} - {R1} - {R2} chain?",
    "Connect the dots from {S} past the {R1} to the {R2}. Who?",
    "From {S}, hop to the {R1}, hop again to the {R2}. Who lands there?",
    "Track it down: {S}'s {R1}, and then their {R2}.",
    "Quick one: who is {S}'s {R1}'s {R2}?",
    "Just checking: the {R2} of {S}'s {R1} is who?",
    "Remind me, who is {S}'s {R1}'s {R2}?",
    "Can you name {S}'s {R1}'s {R2}?",
    "Which person is {S}'s {R1}'s {R2}?",
    "Give me the name of {S}'s {R1}'s {R2}.",
]
ABS_ASK = _ABS_ASK_SINGLE + _ABS_ASK_CHAIN

_EDIT_ASK = [
    "After the fix, who is {S}'s {R1}'s {R2}?",
    "With the correction in mind, name the {R2} of {S}'s {R1}.",
    "Now that I fixed it, who is {S}'s {R1}'s {R2}?",
    "Taking the update into account, who ends up as {S}'s {R1}'s {R2}?",
    "So after my correction, the {R2} of {S}'s {R1} is who?",
    "Recount the chain with the new link: {S}, {R1}, {R2}. Who?",
    "Who does the fixed chain point to from {S} through the {R1} to the {R2}?",
    "Update applied -- who is {S}'s {R1}'s {R2} now?",
    "Given what I just corrected, who is {S}'s {R1}'s {R2}?",
    "Walk the chain again with the fix: {S} to {R1} to {R2}. Who?",
    "Who lands at the end of the corrected {S} - {R1} - {R2} run?",
    "The link changed, so who is {S}'s {R1}'s {R2} these days?",
    "Recompute it: {S}'s {R1}'s {R2} after the edit?",
    "Tell me the new {R2} of {S}'s {R1}.",
    "Name the current {R2} of {S}'s {R1}.",
    "Who is {S}'s {R1}'s {R2} under the corrected story?",
    "Post-fix check: the {R2} of {S}'s {R1} is who?",
    "With the new fact in place, who is {S}'s {R1}'s {R2}?",
    "Run the updated chain from {S} and tell me who you reach.",
    "Who is at the far end now: {S}, the {R1}, the {R2}?",
    "Correction noted -- now who is {S}'s {R1}'s {R2}?",
    "So the edited chain {S} - {R1} - {R2} ends at who?",
    "Who replaced whom? Just tell me who {S}'s {R1}'s {R2} is now.",
    "Fresh answer needed: who is {S}'s {R1}'s {R2}?",
    "Under the fix, name the {R2} of {S}'s {R1}.",
    "After my update, who sits two hops from {S}?",
    "Who is the latest {R2} down the line from {S}'s {R1}?",
    "Give me the corrected final name for {S}'s {R1}'s {R2}.",
    "One more after the edit: who is {S}'s {R1}'s {R2}?",
    "Last one on the fixed chain: the {R2} of {S}'s {R1}?",
    "Confirm the new endpoint: who is {S}'s {R1}'s {R2}?",
    "All fixed -- who is {S}'s {R1}'s {R2}?",
]
_EDIT_SINGLE = [
    "While you are at it, who is {P}'s {R}?",
    "Separately, name the {R} of {P}.",
    "Unrelated check: who is {P}'s {R}?",
    "And apart from that, who is {P}'s {R}?",
    "One separate thing: the {R} of {P} is who?",
    "Also, remind me who {P}'s {R} is.",
    "Different topic: who does {P} have as a {R}?",
    "Besides that chain, who is {P}'s {R}?",
    "Now something else entirely: name {P}'s {R}.",
    "Leaving the chain aside, who is {P}'s {R}?",
    "Independent question: who is {P}'s {R}?",
    "On another note, tell me the {R} of {P}.",
]

_LONG_ASK_3 = [
    "Who is {S}'s {R1}'s {R2}'s {R3}?",
    "Tell me the {R3} of {S}'s {R1}'s {R2}.",
    "Name the {R3} at the end of the {S} - {R1} - {R2} run.",
    "Three hops from {S}: {R1}, then {R2}, then {R3}. Who?",
    "Starting from {S}, pass the {R1}, the {R2}, the {R3}. Who do you reach?",
    "Who sits three links down the line from {S}?",
    "Follow all three steps from {S} and name who lands there.",
    "Track it: {S}'s {R1}, their {R2}, and that one's {R3}. Who?",
    "Quick one: who is {S}'s {R1}'s {R2}'s {R3}?",
    "Just checking the long chain: the {R3} of {S}'s {R1}'s {R2} is who?",
    "Remind me, who is {S}'s {R1}'s {R2}'s {R3}?",
    "Can you name {S}'s {R1}'s {R2}'s {R3}?",
    "Which person ends the {S} - {R1} - {R2} - {R3} walk?",
    "Give me the final name three hops out from {S}.",
    "Connect all three dots from {S}. Who is at the far end?",
    "Run the whole triple chain from {S}. Who comes out?",
]
_LONG_ASK_4 = [
    "Who is {S}'s {R1}'s {R2}'s {R3}'s {R4}?",
    "Tell me the {R4} of {S}'s {R1}'s {R2}'s {R3}.",
    "Name the {R4} at the end of the {S} run through {R1}, {R2}, {R3}.",
    "Four hops from {S}: {R1}, {R2}, {R3}, {R4}. Who?",
    "Starting from {S}, pass the {R1}, the {R2}, the {R3}, the {R4}. Who?",
    "Who sits four links down the line from {S}?",
    "Follow all four steps from {S} and name who lands there.",
    "Track it: {S}'s {R1}, their {R2}, that one's {R3}, and that one's {R4}. Who?",
    "Quick one: who is {S}'s {R1}'s {R2}'s {R3}'s {R4}?",
    "Just checking the longest chain: who ends the {S} walk?",
    "Remind me, who is {S}'s {R1}'s {R2}'s {R3}'s {R4}?",
    "Can you name the far end of the four-hop run from {S}?",
    "Which person ends the {S} - {R1} - {R2} - {R3} - {R4} walk?",
    "Give me the final name four hops out from {S}.",
    "Connect all four dots from {S}. Who is at the far end?",
    "Run the whole quadruple chain from {S}. Who comes out?",
]
LONG_ASK = _LONG_ASK_3 + _LONG_ASK_4

ASK = {
    "two_hop": _TWO_ASK,
    "reversal": _REV_ASK,
    "abstention": ABS_ASK,
    "mquake_edit": _EDIT_ASK,
    "long_chain": LONG_ASK,
}

ACKS = ["Got it.", "Noted.", "Okay, I'll remember that.",
        "Understood.", "Thanks, saved that.", "Right, keeping track.",
        "Makes sense.", "Copy that.", "I have it down.", "Sure thing."]

FIXES = [
    "Actually, {S}'s {R} is {V2}, not {V1}.",
    "Sorry, I got that wrong -- {S}'s {R} is {V2}.",
    "Small fix: the {R} of {S} is {V2}, I misspoke before.",
    "Hold on, {S}'s {R} is {V2}. Forget {V1}.",
    "Let me correct myself: {S} has a {R} named {V2}.",
    "Update on that: {S}'s {R} turns out to be {V2}.",
    "I need to fix one link: {V2} is {S}'s {R}, not {V1}.",
    "My mistake -- {S}'s {R} is {V2}.",
]


# ---------------------------------------------------------------- noise
def noisy(rng, text, is_question):
    if rng.random() < 0.15:
        text = text.lower()
    if rng.random() < 0.15:
        text = text.replace("\u2019", "").replace("'", "")
    if is_question and rng.random() < 0.20:
        text = text.replace("?", rng.choice(["", ".", ""]))
    return text


# ---------------------------------------------------------------- builders
def load_relations():
    with open(REL_PATH) as f:
        d = json.load(f)
    rels = [r for r in d["relations"] if r.get("value_kind") == "person"]
    assert len(rels) >= 20, "need a healthy person-relation pool"
    return rels


def pick_rels(rng, rels, k):
    idx = rng.sample(range(len(rels)), k)
    return [rels[i] for i in idx]


def teach_turn(rng, templates, S, R, V):
    return noisy(rng, rng.choice(templates).format(S=S, R=R, V=V), False)


def build_two_hop(rng, rels, used, i):
    A, B, C = make_names(rng, used, 3)
    r1, r2 = pick_rels(rng, rels, 2)
    R1, R2 = rel_word(rng, r1), rel_word(rng, r2)
    conv = [{"speaker": "user", "text": teach_turn(rng, TEACH["two_hop"], A, R1, B)},
            {"speaker": "assistant", "text": rng.choice(ACKS)},
            {"speaker": "user", "text": teach_turn(rng, TEACH["two_hop"], B, R2, C)},
            {"speaker": "assistant", "text": rng.choice(ACKS)}]
    q = noisy(rng, rng.choice(ASK["two_hop"]).format(S=A, R1=R1, R2=R2), True)
    conv.append({"speaker": "user", "text": q})
    return {"world_id": "two_hop-%04d" % i, "family": "two_hop",
            "names": [A, B, C], "conversation": conv,
            "facts": [{"s": A, "r": r1["name"], "v": B},
                      {"s": B, "r": r2["name"], "v": C}],
            "corrections": [],
            "questions": [{"qid": "two_hop-%04d-q0" % i, "kind": "two_hop",
                           "text": q, "gold": C}]}


def build_reversal(rng, rels, used, i):
    A, B = make_names(rng, used, 2)
    (r,) = pick_rels(rng, rels, 1)
    R = rel_word(rng, r)
    conv = [{"speaker": "user", "text": teach_turn(rng, TEACH["reversal"], A, R, B)},
            {"speaker": "assistant", "text": rng.choice(ACKS)}]
    q = noisy(rng, rng.choice(ASK["reversal"]).format(R=R, Y=B), True)
    conv.append({"speaker": "user", "text": q})
    return {"world_id": "reversal-%04d" % i, "family": "reversal",
            "names": [A, B], "conversation": conv,
            "facts": [{"s": A, "r": r["name"], "v": B}], "corrections": [],
            "questions": [{"qid": "reversal-%04d-q0" % i, "kind": "reversal",
                           "text": q, "gold": A}]}


def build_abstention(rng, rels, used, i):
    sub = ["untaught", "never_mentioned", "broken"][i % 3]
    if sub == "untaught":
        A, B = make_names(rng, used, 2)
        r1, r2 = pick_rels(rng, rels, 2)
        R1, R2 = rel_word(rng, r1), rel_word(rng, r2)
        conv = [{"speaker": "user",
                 "text": teach_turn(rng, TEACH["abstention"], A, R1, B)},
                {"speaker": "assistant", "text": rng.choice(ACKS)}]
        q = noisy(rng, rng.choice(_ABS_ASK_SINGLE).format(S=A, R=R2), True)
        conv.append({"speaker": "user", "text": q})
        facts = [{"s": A, "r": r1["name"], "v": B}]
        names = [A, B]
        meta = {"sub": sub, "s": A, "r": r2["name"]}
    elif sub == "never_mentioned":
        A, B, P = make_names(rng, used, 3)
        r1, r2 = pick_rels(rng, rels, 2)
        R1, R2 = rel_word(rng, r1), rel_word(rng, r2)
        conv = [{"speaker": "user",
                 "text": teach_turn(rng, TEACH["abstention"], A, R1, B)},
                {"speaker": "assistant", "text": rng.choice(ACKS)}]
        q = noisy(rng, rng.choice(_ABS_ASK_SINGLE).format(S=P, R=R2), True)
        conv.append({"speaker": "user", "text": q})
        facts = [{"s": A, "r": r1["name"], "v": B}]
        names = [A, B, P]
        meta = {"sub": sub, "p": P}
    else:
        A, B, C, D = make_names(rng, used, 4)
        r1, r2 = pick_rels(rng, rels, 2)
        R1, R2 = rel_word(rng, r1), rel_word(rng, r2)
        conv = [{"speaker": "user",
                 "text": teach_turn(rng, TEACH["abstention"], A, R1, B)},
                {"speaker": "assistant", "text": rng.choice(ACKS)},
                {"speaker": "user",
                 "text": teach_turn(rng, TEACH["abstention"], C, R2, D)},
                {"speaker": "assistant", "text": rng.choice(ACKS)}]
        q = noisy(rng, rng.choice(_ABS_ASK_CHAIN).format(S=A, R1=R1, R2=R2), True)
        conv.append({"speaker": "user", "text": q})
        facts = [{"s": A, "r": r1["name"], "v": B},
                 {"s": C, "r": r2["name"], "v": D}]
        names = [A, B, C, D]
        meta = {"sub": sub, "s": A, "r1": r1["name"], "r2": r2["name"]}
    return {"world_id": "abstention-%04d" % i, "family": "abstention",
            "names": names, "conversation": conv, "facts": facts,
            "corrections": [],
            "questions": [{"qid": "abstention-%04d-q0" % i, "kind": "abstention",
                           "text": q, "gold": IDK, "meta": meta}]}


def build_mquake(rng, rels, used, i):
    A, B, C, P, Q, B2 = make_names(rng, used, 6)
    r1, r2, r3 = pick_rels(rng, rels, 3)
    R1, R2, R3 = rel_word(rng, r1), rel_word(rng, r2), rel_word(rng, r3)
    hop = rng.choice([0, 1])
    conv = [{"speaker": "user",
             "text": teach_turn(rng, TEACH["mquake_edit"], A, R1, B)},
            {"speaker": "assistant", "text": rng.choice(ACKS)},
            {"speaker": "user",
             "text": teach_turn(rng, TEACH["mquake_edit"], B, R2, C)},
            {"speaker": "assistant", "text": rng.choice(ACKS)},
            {"speaker": "user",
             "text": teach_turn(rng, TEACH["mquake_edit"], P, R3, Q)},
            {"speaker": "assistant", "text": rng.choice(ACKS)}]
    facts = [{"s": A, "r": r1["name"], "v": B},
             {"s": B, "r": r2["name"], "v": C},
             {"s": P, "r": r3["name"], "v": Q}]
    if hop == 0:
        # A-r1 now points at B2; B2 inherits the onward link.
        facts = [{"s": A, "r": r1["name"], "v": B2},
                 {"s": B2, "r": r2["name"], "v": C},
                 {"s": P, "r": r3["name"], "v": Q}]
        old_v, mid = B, B2
        fix = noisy(rng, rng.choice(FIXES).format(S=A, R=R1, V1=B, V2=B2), False)
        corr = {"s": A, "r": r1["name"], "old": B, "new": B2}
        # keep the onward link taught for the new middle in the fix turn's wake
        conv.append({"speaker": "user", "text": fix})
        conv.append({"speaker": "assistant", "text": rng.choice(ACKS)})
        conv.append({"speaker": "user",
                     "text": teach_turn(rng, TEACH["mquake_edit"], B2, R2, C)})
        conv.append({"speaker": "assistant", "text": rng.choice(ACKS)})
        names = [A, B, C, P, Q, B2]
        gold_main = C
    else:
        fix = noisy(rng, rng.choice(FIXES).format(S=B, R=R2, V1=C, V2=B2), False)
        conv.append({"speaker": "user", "text": fix})
        conv.append({"speaker": "assistant", "text": rng.choice(ACKS)})
        facts = [{"s": A, "r": r1["name"], "v": B},
                 {"s": B, "r": r2["name"], "v": B2},
                 {"s": P, "r": r3["name"], "v": Q}]
        corr = {"s": B, "r": r2["name"], "old": C, "new": B2}
        names = [A, B, C, P, Q, B2]
        gold_main = B2
    qm = noisy(rng, rng.choice(ASK["mquake_edit"]).format(S=A, R1=R1, R2=R2), True)
    conv.append({"speaker": "user", "text": qm})
    qu = noisy(rng, rng.choice(_EDIT_SINGLE).format(P=P, R=R3), True)
    conv.append({"speaker": "user", "text": qu})
    return {"world_id": "mquake_edit-%04d" % i, "family": "mquake_edit",
            "names": names, "conversation": conv, "facts": facts,
            "corrections": [corr],
            "questions": [{"qid": "mquake_edit-%04d-q0" % i, "kind": "edit_chain",
                           "text": qm, "gold": gold_main},
                          {"qid": "mquake_edit-%04d-q1" % i, "kind": "unaffected",
                           "text": qu, "gold": Q}]}


def build_long(rng, rels, used, i):
    n_hops = 3 if i % 2 == 0 else 4
    nodes = make_names(rng, used, n_hops + 1)
    chain = pick_rels(rng, rels, n_hops)
    words = [rel_word(rng, r) for r in chain]
    conv, facts = [], []
    for h in range(n_hops):
        conv.append({"speaker": "user",
                     "text": teach_turn(rng, TEACH["long_chain"], nodes[h],
                                        words[h], nodes[h + 1])})
        conv.append({"speaker": "assistant", "text": rng.choice(ACKS)})
        facts.append({"s": nodes[h], "r": chain[h]["name"], "v": nodes[h + 1]})
    pool = _LONG_ASK_3 if n_hops == 3 else _LONG_ASK_4
    kw = {"S": nodes[0]}
    for h, w in enumerate(words):
        kw["R%d" % (h + 1)] = w
    q = noisy(rng, rng.choice(pool).format(**kw), True)
    conv.append({"speaker": "user", "text": q})
    return {"world_id": "long_chain-%04d" % i, "family": "long_chain",
            "names": nodes, "conversation": conv, "facts": facts,
            "corrections": [],
            "questions": [{"qid": "long_chain-%04d-q0" % i,
                           "kind": "long_%d" % n_hops, "text": q,
                           "gold": nodes[-1]}]}


BUILDERS = {"two_hop": build_two_hop, "reversal": build_reversal,
            "abstention": build_abstention, "mquake_edit": build_mquake,
            "long_chain": build_long}


# ---------------------------------------------------------------- rule checker
def _blob(world):
    return " ".join(t["text"] for t in world["conversation"])


def _norm(t):
    return t.lower().replace("\u2019", "").replace("'", "")


def lookup(facts, s, r):
    for f in facts:
        if f["s"] == s and f["r"] == r:
            return f["v"]
    return None


def derive(world):
    """Re-derive every gold answer from the world's conversation facts."""
    facts = world["facts"]
    out = []
    for q in world["questions"]:
        kind = q["kind"]
        if kind == "two_hop":
            s = world["facts"][0]["s"]
            r1, r2 = facts[0]["r"], facts[1]["r"]
            m = lookup(facts, s, r1)
            g = lookup(facts, m, r2) if m else None
        elif kind == "reversal":
            f = facts[0]
            cands = [x["s"] for x in facts if x["r"] == f["r"] and x["v"] == f["v"]]
            g = cands[0] if len(cands) == 1 else None
        elif kind == "abstention":
            meta = q["meta"]
            if meta["sub"] == "untaught":
                g = IDK if lookup(facts, meta["s"], meta["r"]) is None else "LEAK"
            elif meta["sub"] == "never_mentioned":
                mentioned = {x["s"] for x in facts} | {x["v"] for x in facts}
                g = IDK if meta["p"] not in mentioned else "LEAK"
            else:
                m = lookup(facts, meta["s"], meta["r1"])
                nxt = lookup(facts, m, meta["r2"]) if m else None
                g = IDK if nxt is None else "LEAK"
        elif kind == "edit_chain":
            s = world["facts"][0]["s"]
            r1 = [x["r"] for x in facts if x["s"] == s][0]
            m = lookup(facts, s, r1)
            r2 = [x["r"] for x in facts if x["s"] == m][0] if m else None
            g = lookup(facts, m, r2) if (m and r2) else None
        elif kind == "unaffected":
            g = lookup(facts, world["facts"][-1]["s"], world["facts"][-1]["r"])
        elif kind in ("long_3", "long_4"):
            node, g = facts[0]["s"], None
            ok = True
            for f in facts:
                if f["s"] != node:
                    ok = False
                    break
                node = f["v"]
            g = node if ok else None
        else:
            g = "UNKNOWN-KIND"
        out.append(g)
    return out


def verify_file(path):
    worlds = [json.loads(l) for l in open(path) if l.strip()]
    mism, ungrounded, over = 0, 0, 0
    max_chars = 0
    for w in worlds:
        blob = _norm(_blob(w))
        n_chars = sum(len(t["text"]) for t in w["conversation"])
        max_chars = max(max_chars, n_chars)
        if n_chars > 3600:
            over += 1
        for f in w["facts"]:
            if _norm(f["s"]) not in blob or _norm(f["v"]) not in blob:
                ungrounded += 1
        for c in w.get("corrections", []):
            if _norm(c["new"]) not in blob:
                ungrounded += 1
        for got, q in zip(derive(w), w["questions"]):
            if got != q["gold"]:
                mism += 1
    return {"n": len(worlds), "mismatches": mism,
            "ungrounded": ungrounded, "over_budget": over,
            "max_chars": max_chars,
            "max_tokens": max_chars // 4}


def cmd_generate():
    for fam, t in TEACH.items():
        assert len(t) >= 30, (fam, "teach", len(t))
    for fam, t in ASK.items():
        assert len(t) >= 30, (fam, "ask", len(t))
    rng = random.Random(SEED)
    rels = load_relations()
    used = set()
    os.makedirs(OUT_DIR, exist_ok=True)
    for fam in FAMILIES:
        path = os.path.join(OUT_DIR, fam + ".jsonl")
        if os.path.exists(path):
            print("REFUSE: exists (append-only): %s" % path)
            sys.exit(4)
        b = BUILDERS[fam]
        with open(path, "w") as f:
            for i in range(N_PER_FAMILY):
                w = b(rng, rels, used, i)
                f.write(json.dumps(w) + "\n")
        print("wrote %s (%d worlds)" % (path, N_PER_FAMILY))
    print("template counts per family:")
    for fam in FAMILIES:
        print("  %s teach=%d ask=%d" % (fam, len(TEACH[fam]), len(ASK[fam])))


def cmd_verify():
    total_mism, total = 0, 0
    all_sets = {}
    for fam in FAMILIES:
        path = os.path.join(OUT_DIR, fam + ".jsonl")
        r = verify_file(path)
        total_mism += r["mismatches"]
        total += r["n"]
        print("%s: n=%d mismatches=%d ungrounded=%d over_budget=%d "
              "max_chars=%d max_tokens~%d" % (
                  fam, r["n"], r["mismatches"], r["ungrounded"],
                  r["over_budget"], r["max_chars"], r["max_tokens"]))
        all_sets[fam] = [frozenset(json.loads(l)["names"])
                         for l in open(path) if l.strip()]
    shared = 0
    for a in range(len(FAMILIES)):
        for c in range(a + 1, len(FAMILIES)):
            fa, fb = FAMILIES[a], FAMILIES[c]
            sb = set(all_sets[fb])
            for s in all_sets[fa]:
                if s in sb:
                    shared += 1
    print("cross-family shared name sets: %d" % shared)
    print("TOTAL worlds=%d mismatches=%d" % (total, total_mism))
    if total_mism or shared:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("generate", "verify"):
        print("usage: claude_own_o0f_bench.py [generate|verify]")
        sys.exit(2)
    {"generate": cmd_generate, "verify": cmd_verify}[sys.argv[1]]()
