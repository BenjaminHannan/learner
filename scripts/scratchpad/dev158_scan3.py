#!/usr/bin/env python3
"""DEV-ONLY pre-seal gate checks for exp 158 (not a registered run).

For each eligible input, run the CANDIDATE through BASE loop150 ears:
ask => mixin changes behavior (must predict); else identical.
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

C150 = copy.deepcopy(L150.DEFAULT_CONFIG150)


def base_hear(teaches, text):
    tmp = tempfile.mkdtemp()
    c = dict(C150)
    c["state_dir"] = tmp
    c["sleep_threshold"] = 100000
    loop = L150.build_agent150(c)
    for t in teaches:
        loop.turn(t)
    acts = loop.ears.hear(text)
    reply = " ".join(loop.turn(text))
    return acts, reply


CASES = [
    ("gibson", ["William Gibson is famous for Little Busters!"],
     "William Gibson is famous for Little Busters!"),
    ("thanks", [], "thanks!"),
    ("hi", [], "hi!!"),
    ("bye", [], "bye!!"),
    ("ty", [], "ty, very helpful!"),
    ("s5n5", ["Tess's city is Omaha."], "what's tess's city?"),
    ("s5n6", ["Tess's city is Omaha."], "tell me tess's city"),
    ("s5n9", ["Rosa's mother is Vera.", "vera's city is lima."],
     "Who is Rosa's mother's city???"),
    ("rt110s2", ["Mira's city is Lisbon."],
     "Who is Mira's city? also Mira's pet is a cat."),
    ("rt110s4", ["Mira's city is Lisbon."],
     "How many facts do you know? Mira's city is Lisbon."),
    ("rt110s6", ["Mira's city is Lisbon."],
     "Is Mira's city Lisbon? Also teach Mira's pet is a cat."),
    ("rt81tell", ["Mira's city is Lisbon."], "Tell me Mira's city."),
    ("rt136tom", [], "Tom's city is Rome!!!"),
    ("rt136ann", [], "Ann's child is Bob!"),
]

for tag, teaches, orig in CASES:
    cand, fired = Q.normalize_question_surface(orig)
    elig = Q.eligibility_ok(orig, cand, fired) if cand else False
    if cand is None:
        print(f"{tag}: NO-CANDIDATE")
        continue
    acts, reply = base_hear(teaches, cand)
    is_ask = any(isinstance(a, dict) and a.get("act") == "ask" for a in acts)
    print(f"{tag}: elig={elig} fired={fired} cand={cand!r}")
    print(f"   base_acts={acts} is_ask={is_ask} reply={reply!r}")
