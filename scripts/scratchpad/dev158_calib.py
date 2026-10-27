#!/usr/bin/env python3
"""DEV-ONLY pre-seal calibration for exp 158 (not a registered run).

Builds the candidate Q1 pair/nonquestion lists and checks each against
loop158 (new) and loop150 (base) in-process. Prints a table; the SEALED
cases158.json is written by hand afterwards from passing rows only.
"""

import copy
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix158_qform as Q
import fable_loop150_agent as L150
import fable_loop158_agent as L158

C158 = copy.deepcopy(L158.DEFAULT_CONFIG158)
C150 = copy.deepcopy(L150.DEFAULT_CONFIG150)


def fresh(build, cfg):
    tmp = tempfile.mkdtemp()
    c = dict(cfg)
    c["state_dir"] = tmp
    c["sleep_threshold"] = 100000
    return build(c)


def facts(loop):
    return sum(1 for e in loop.nb.events if e.get("kind") == "FACT")


TEACHES = {
    "tess": ["Tess's city is Omaha."],
    "vera": ["Rosa's mother is Vera.", "vera's city is lima."],
    "ned": ["Rosa's brother is Ned.", "ned's teacher is quinn."],
    "friend": ["Rosa's friend is Tess.", "Tess's city is Omaha."],
    "momcity": ["Rosa's mother is Vera.", "vera's city is lima."],
    "sis": ["Rosa's sister is Pia."],
    "none": [],
}

PAIRS = [
    ("tess", "What's Tess's city?", "What is Tess's city?", "Omaha"),
    ("friend", "Who's Rosa's friend?", "What is Rosa's friend?", "Tess"),
    ("vera", "Where's Vera's city?", "What is Vera's city?", "lima"),
    ("momcity", "What's Rosa's mother's city?", "What is Rosa's mother's city?", "lima"),
    ("ned", "Who's Ned's teacher?", "What is Ned's teacher?", "quinn"),
    ("ned", "What's Rosa's brother's teacher?", "What is Rosa's brother's teacher?", "quinn"),
    ("momcity", "Who's Rosa's mother's city?", "What is Rosa's mother's city?", "lima"),
    ("friend", "Where's Rosa's friend's city?", "What is Rosa's friend's city?", "Omaha"),
    ("tess", "Tell me Tess's city", "What is Tess's city?", "Omaha"),
    ("tess", "Tell me Tess's city?", "What is Tess's city?", "Omaha"),
    ("vera", "Show me Vera's city", "What is Vera's city?", "lima"),
    ("ned", "Give me Ned's teacher", "What is Ned's teacher?", "quinn"),
    ("momcity", "Tell me Rosa's mother's city", "What is Rosa's mother's city?", "lima"),
    ("vera", "Tell me who is Rosa's mother?", "What is Rosa's mother?", "Vera"),
    ("tess", "Tell me what is Tess's city?", "What is Tess's city?", "Omaha"),
    ("ned", "Show me Rosa's brother's teacher", "What is Rosa's brother's teacher?", "quinn"),
    ("momcity", "Who is Rosa's mother's city???", "Who is Rosa's mother's city?", "lima"),
    ("tess", "What is Tess's city?!", "What is Tess's city?", "Omaha"),
    ("ned", "Who is Ned's teacher!!", "Who is Ned's teacher?", "quinn"),
    ("vera", "What is Vera's city???", "What is Vera's city?", "lima"),
    ("friend", "Who is Rosa's friend????", "Who is Rosa's friend?", "Tess"),
    ("friend", "Where is Rosa's friend's city?!?", "Where is Rosa's friend's city?", "Omaha"),
    ("tess", "Who's Tess's city?!", "Who is Tess's city?", "Omaha"),
    ("tess", "Tell me Tess's city?!", "What is Tess's city?", "Omaha"),
    ("tess", "  What's Tess's city?  ", "What is Tess's city?", "Omaha"),
    ("tess", "What\u2019s Tess\u2019s city?", "What is Tess's city?", "Omaha"),
    ("none", "What's Zane's city?", "What is Zane's city?", "Zane"),
    ("none", "Tell me Zane's city", "What is Zane's city?", "Zane"),
    ("none", "Who is Pia's city?", "What is Pia's city?", "Pia"),
    ("sis", "Who is Rosa's sister's city???", "What is Rosa's sister's city?", "Pia"),
    ("none", "Tell me who is Zane's city?", "What is Zane's city?", "Zane"),
    ("vera", "Where's Ned's teacher?", "Where is Ned's teacher?", "quinn"),
    ("vera", "Who's Vera's city?", "Who is Vera's city?", "lima"),
    ("friend", "What's Rosa's friend?", "What is Rosa's friend?", "Tess"),
    ("tess", "Show me Tess's city?", "What is Tess's city?", "Omaha"),
    ("vera", "Give me Rosa's mother?", "What is Rosa's mother?", "Vera"),
    ("ned", "Tell me Rosa's brother's teacher?", "What is Rosa's brother's teacher?", "quinn"),
    ("vera", "Who is Vera's city??!?", "Who is Vera's city?", "lima"),
    ("ned", "What is Ned's teacher??", "What is Ned's teacher?", "quinn"),
    ("ned", "What's Ned's teacher??", "What is Ned's teacher?", "quinn"),
    ("vera", "Tell me where is Vera's city?", "What is Vera's city?", "lima"),
    ("ned", "Who's Rosa's brother?", "What is Rosa's brother?", "Ned"),
    ("vera", "Liv's city is Boston.", "PLACEHOLDER", "Boston"),
]

NONQ = [
    ("none", "what's done is done?"),
    ("none", "Who's Who's editor is Bob."),
    ("none", "tell me more"),
    ("none", "Tell me more?"),
    ("none", "show me the money"),
    ("none", "give me a break"),
    ("none", "when's the party?"),
    ("none", "Tell me about Tess"),
    ("none", "what scares me is spiders."),
    ("none", "Who's afraid of Virginia Woolf?"),
    ("none", "Guess who's coming to dinner?"),
    ("none", "tell them Tess's city"),
    ("none", "Where's Waldo."),
    ("tess", "What is Tess's city"),
    ("none", "What's the time, Mr Wolf?"),
    ("none", "tell me when it started"),
]


def run(build, cfg, teaches, text):
    loop = fresh(build, cfg)
    for t in teaches:
        loop.turn(t)
    before = facts(loop)
    reply = " ".join(loop.turn(text))
    return reply, facts(loop) - before


print("=== PAIRS (loop158 variant vs loop158 canonical) ===")
for key, var, can, want in PAIRS:
    if can == "PLACEHOLDER":
        print(f"SKIP {var!r}")
        continue
    rv, wv = run(L158.build_agent158, C158, TEACHES[key], var)
    rc, wc = run(L158.build_agent158, C158, TEACHES[key], can)
    flag = "OK" if (rv == rc and want.lower() in rv.lower()
                    and wv == 0 and wc == 0) else "FAIL"
    print(f"{flag} var={var!r} -> {rv!r} w={wv} | can -> {rc!r} w={wc}")

print("=== NONQ (loop158 vs loop150) ===")
for key, text in NONQ:
    r158, w158 = run(L158.build_agent158, C158, TEACHES[key], text)
    r150, w150 = run(L150.build_agent150, C150, TEACHES[key], text)
    flag = "OK" if (r158 == r150 and w158 == w150 == 0) else "CHECK"
    print(f"{flag} {text!r} |158:{r158!r} w={w158} |150:{r150!r} w={w150}")
