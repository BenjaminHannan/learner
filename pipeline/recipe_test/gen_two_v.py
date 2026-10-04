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


def train_frames(n=12000):
    fr = list(set(compose(random.Random(4_000_001), n)))
    ev = g3.all_eval_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    return [f for f in fr if not (gen2.grams(f[2]) & evg or gen2.sentences(f[2]) & evs)]
