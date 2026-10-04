"""Round 4: composed two-step training frames (many interchangeable parts, 4 layouts) instead of the fixed 3,378-frame set. Run with RT_ROUND=2.
Same idea that lifted one-step wording from 81.6 to 98.1% in the stand-in (and 59 -> 91% new-wording calls in round 2): build training wording from parts.
EVAL is unchanged (gen_two_r3.build_eval). Every composed frame sharing a sentence or word 6-gram with any eval frame is dropped.
"""
import itertools, random
import gen2, gen_two, gen_two_r3 as g3

OPEN = ["{name} had {x} {noun} to begin with.", "{name} owned {x} {noun} at first.", "In the beginning {name} kept {x} {noun}.", "{name}'s collection started at {x} {noun}.",
        "There were {x} {noun} in {name}'s possession.", "{name} was holding {x} {noun}."]
GAIN = ["{name} got {n} more.", "{n} extra ones came to {name}.", "{name} was handed {n} more.", "{name} found {n} additional ones.", "{name} earned {n} more.", "{n} more arrived for {name}."]
LOSS = ["{name} parted with {n}.", "{n} of them went missing.", "{name} traded away {n}.", "{name} broke {n} of them.", "{n} were lost by {name}.", "{name} threw out {n}."]
LINK = ["Then", "After that", "Later on", "Soon after", "Following that", "In the evening"]
Q = ["How many {noun} does {name} hold in the end?", "Count the {noun} that {name} has left.", "What is {name}'s final number of {noun}?",
     "How many {noun} are now with {name}?", "Say how many {noun} {name} finishes with.", "Give the total of {noun} {name} has at the end."]
QSTEM = ["Find how many {noun} {name} finishes with.", "What number of {noun} will {name} end up with?", "Work out {name}'s closing total of {noun}.", "Give the last count of {noun} for {name}.",
         "How many {noun} will {name} be left holding?"]
QFOLLOW = ["Facts: {name} owned {x} {noun}.", "Here is what happened. {name} began with {x} {noun}.", "Details: {name} started off with {x} {noun}.", "{name} started the day with {x} {noun}."]
TAB_HEAD = ["Tally for {name}'s {noun}", "Record of {noun} ({name})", "Count sheet, {noun}, owner {name}", "{name}: running total of {noun}"]
TAB_START = ["begin {x}", "initial {x}", "at start {x}", "starting {x}"]
TAB_G = ["plus {y}", "received {y}", "bought {y}", "collected {y}", "gained {y}"]
TAB_L = ["minus {y}", "sold {y}", "spent {y}", "gave {y}", "lost {y}"]
TAB_SEP = [" | ", " / ", ", ", " -> ", " then "]
TAB_Q = ["How many {noun} are there at the end?", "What is the final count of {noun}?", "Tell me the last count.", "What does {name} end up with?"]
OBJ = ["The canal", "A hiking trail", "The railway line", "A garden fence", "The runway", "A pipeline"]
UNIT = ["kilometres", "miles", "yards", "metres"]
LEN = ["is {x} {u} long.", "measures {x} {u}.", "runs for {x} {u}."]
DG = ["Builders lengthen it by", "An annex adds", "A new stretch adds", "Engineers extend it by"]
DL = ["Erosion takes away", "A closure trims", "A diversion cuts", "Crews shorten it by"]
DQ = ["What is its length at the end?", "How long is it now?", "Give its final length."]


def low(t): return t[0].lower() + t[1:]


def compose(rng, n):
    out = []
    for i in range(n):
        o1, o2 = rng.choice(("ADD", "SUB")), rng.choice(("ADD", "SUB"))
        k = rng.random()
        g = lambda o, a, b: rng.choice(a if o == "ADD" else b)
        if k < 0.25:   # narrative
            t = " ".join([rng.choice(OPEN), g(o1, GAIN, LOSS).replace("{n}", "{y}"), rng.choice(LINK) + ", " + low(g(o2, GAIN, LOSS).replace("{n}", "{z}")), rng.choice(Q)])
        elif k < 0.55:  # question first
            t = " ".join([rng.choice(QSTEM), rng.choice(QFOLLOW), g(o1, GAIN, LOSS).replace("{n}", "{y}"), rng.choice(LINK) + ", " + low(g(o2, GAIN, LOSS).replace("{n}", "{z}"))])
        elif k < 0.85:  # table
            sep = rng.choice(TAB_SEP)
            body = sep.join([rng.choice(TAB_START), g(o1, TAB_G, TAB_L), g(o2, TAB_G, TAB_L).replace("{y}", "{z}")])
            t = f"{rng.choice(TAB_HEAD)}: {body}. {rng.choice(TAB_Q)}" if rng.random() < 0.7 else f"{rng.choice(TAB_Q)} {rng.choice(TAB_HEAD)}: {body}."
        else:           # distance
            u = rng.choice(UNIT)
            t = (f"{rng.choice(OBJ)} {rng.choice(LEN).replace('{u}', u)} {g(o1, DG, DL)} {{y}} {u}. {rng.choice(LINK)}, "
                 f"{low(g(o2, DG, DL))} {{z}} {u}. {rng.choice(DQ)}")
        out.append((o1, o2, t))
    return out


# ---- round 5: extra table-style variety (authored by the design model, after seeing only the KINDS of the blind layouts, not their wording)
TV_HEAD = ["INVENTORY {noun}", "{noun} count", "Daily tally ({noun})", "Notebook page: {noun}", "Sheet 2 - {noun}", "{name}'s {noun} list", "Register of {noun}", "Chart: {noun}"]
TV_START = ["start: {x}", "day-open {x}", "initial amount = {x}", "base {x}", "carried over {x}", "x0 {x}"]
TV_GAIN = ["+{y}", "arrived {y}", "IN {y}", "topped up by {y}", "credit {y}", "plus {y} added", "supplied {y}"]
TV_LOSS = ["-{y}", "left {y}", "OUT {y}", "drawn down by {y}", "debit {y}", "minus {y} removed", "withdrawn {y}"]
TV_SEP = [" ; ", " | ", " || ", " / ", " :: ", " -- ", " > "]
TV_ASK = ["total now?", "balance =", "how many at the end?", "end value?", "what remains?", "sum at close:", "closing figure?"]
TV_LABELS = [("row 1", "row 2"), ("step a", "step b"), ("mon", "tue"), ("first", "then"), ("entry #1", "entry #2"), ("early", "late")]


def tab_extra(rng, n):
    out = []
    for _ in range(n):
        o1, o2 = rng.choice(("ADD", "SUB")), rng.choice(("ADD", "SUB"))
        g = lambda o, a, b: rng.choice(a if o == "ADD" else b)
        l1, l2 = rng.choice(TV_LABELS)
        c1 = f"{l1} {g(o1, TV_GAIN, TV_LOSS)}"; c2 = f"{l2} {g(o2, TV_GAIN, TV_LOSS)}".replace("{y}", "{z}")
        st, hd, ask = rng.choice(TV_START), rng.choice(TV_HEAD), rng.choice(TV_ASK)
        k = rng.random()
        if k < 0.4:    # one line
            sep = rng.choice(TV_SEP); t = f"{hd}{sep}{st}{sep}{c1}{sep}{c2}{sep}{ask}"
        elif k < 0.8:  # rows on separate lines
            t = f"{hd}\n{st}\n{c1}\n{c2}\n{ask}"
        else:          # question or ask line first
            sep = rng.choice(TV_SEP); t = f"{ask} {hd}{sep}{st}{sep}{c1}{sep}{c2}"
        out.append((o1, o2, t))
    return out


def blind_frames():
    import os, json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_layouts_r5_blind.json")
    if not os.path.exists(p): return []
    return [(0, 0, t) for f in json.load(open(p))["families"] for v in f["frames"].values() for t in v]


def train_frames(n=12000, tab=0):
    fr = list(set(compose(random.Random(4_000_001), n)))
    if tab: fr += list(set(tab_extra(random.Random(5_000_001), tab)))
    ev = g3.all_eval_frames() + blind_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    return [f for f in fr if not (gen2.grams(f[2]) & evg or gen2.sentences(f[2]) & evs)]
