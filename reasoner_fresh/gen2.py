"""Procedurally composed TRAINING wording (arm W). Eval wording is untouched (EVAL-FORM-v1.json, sealed).

Frames are composed from slot lists, then pruned so that no composed frame shares a sentence frame or a word 6-gram
(with {name}/{noun}/{x}/{y} kept as tokens) with any eval new-wording frame in templates_eval.json.
"""
import itertools, json, random, re
import gen

# story kind K1: two quantities in two places/times. A, B are adverbials; pv past verb, ps passive phrase
CONTEXTS = [
 ("counted", "were counted", "on Monday", "on Tuesday"),
 ("sold", "were sold", "at the market", "at the fair"),
 ("collected", "were collected", "in spring", "in autumn"),
 ("painted", "were painted", "on the left wall", "on the right wall"),
 ("spotted", "were spotted", "by the lake", "near the hill"),
 ("stacked", "were stacked", "in the attic", "in the cellar"),
 ("sorted", "were sorted", "before breakfast", "after dinner"),
 ("delivered", "were delivered", "to the school", "to the clinic"),
 ("found", "were found", "under the bed", "behind the couch"),
 ("made", "were made", "in the first week", "in the second week"),
 ("borrowed", "were borrowed", "from the club", "from the town hall"),
 ("received", "were received", "in June", "in July"),
]
INTROS = ["{name} {pv} {x} {noun} {A} and {y} {noun} {B}.",
          "{x} {noun} {ps} {A}, and {y} {noun} {ps} {B}."]
ADD_STEMS = ["How many {noun} are there altogether?", "How many {noun} are there in all?",
             "How many {noun} are there together?", "Find the sum of the {noun} from both places."]
SUB_STEMS = ["How many more {noun} {ps} {A} than {B}?", "How many {noun} more {ps} {A} than {B}?",
             "By how many did the {noun} {ps} {A} outnumber those {ps} {B}?"]
# story kind K3: start, then gain or loss
GAIN = ["received", "was given", "picked up"]
LOSS = ["gave away", "lost", "used up"]
K3_INTRO = ["{name} started with {x} {noun}. Later, {name} {g} {y} more.", "At first {name} owned {x} {noun}. Then {name} {g} {y} more."]
K3_INTRO_L = ["{name} started with {x} {noun}. Later, {name} {g} {y} of them.", "At first {name} owned {x} {noun}. Then {name} {g} {y} of them."]
K3_TAIL = ["How many {noun} does {name} end up with?", "How many {noun} does {name} have at the end?", "How many {noun} are left with {name} now?"]


def raw_frames():
    out = []  # (op, frame)
    for (pv, ps, A, B), intro in itertools.product(CONTEXTS, INTROS):
        base = intro.replace("{pv}", pv).replace("{ps}", ps).replace("{A}", A).replace("{B}", B)
        for st in ADD_STEMS:
            out.append(("ADD", base + " " + st.replace("{ps}", ps)))
        for st in SUB_STEMS:
            out.append(("SUB", base + " " + st.replace("{ps}", ps).replace("{A}", A).replace("{B}", B)))
    for intro, g in itertools.product(K3_INTRO, GAIN):
        for t in K3_TAIL:
            out.append(("ADD", intro.replace("{g}", g) + " " + t))
    for intro, g in itertools.product(K3_INTRO_L, LOSS):
        for t in K3_TAIL:
            out.append(("SUB", intro.replace("{g}", g) + " " + t))
    return out


def toks(s):
    return re.findall(r"\{[a-z0-9]+\}|[A-Za-z']+|[.,?]", s.lower())


def grams(s, n=6):
    t = toks(s)
    return {tuple(t[i:i + n]) for i in range(len(t) - n + 1)}


def eval_frames():
    ev = gen.load("templates_eval.json")
    return [f[k] for f in ev["families"] for k in ("add", "sub")]


def sentences(s):
    return {x.strip().lower() for x in re.split(r"(?<=[.?])\s+", s) if x.strip()}


def pruned_frames():
    evg = set().union(*(grams(f) for f in eval_frames()))
    evs = set().union(*(sentences(f) for f in eval_frames()))
    keep, dropped = [], []
    for op, f in raw_frames():
        if grams(f) & evg or sentences(f) & evs:
            dropped.append((op, f))
        else:
            keep.append((op, f))
    return keep, dropped


def disjointness_report():
    keep, dropped = pruned_frames()
    evg = set().union(*(grams(f) for f in eval_frames()))
    evs = set().union(*(sentences(f) for f in eval_frames()))
    shared_g = sum(1 for _, f in keep if grams(f) & evg)
    shared_s = sum(1 for _, f in keep if sentences(f) & evs)
    tr = gen.load("templates_train.json"); ev = gen.load("templates_eval.json")
    return {"raw_frames": len(keep) + len(dropped), "kept": len(keep), "dropped_for_overlap": len(dropped),
            "kept_sharing_6gram_with_eval": shared_g, "kept_sharing_full_sentence_with_eval": shared_s,
            "name_overlap": sorted(set(tr["names"]) & set(ev["names"])), "noun_overlap": sorted(set(tr["nouns"]) & set(ev["nouns"])),
            "kept_by_op": {o: sum(1 for p, _ in keep if p == o) for o in ("ADD", "SUB")}}


def stream_w(excluded_pairs, seed, n):
    """n unique-text training questions; half old-wording (tr-* families), half composed frames. Answers in T only."""
    T, _ = gen.answer_split(); Ts = set(T)
    tr = gen.load("templates_train.json"); rng = random.Random(8_000_000 + seed)
    keep, _ = pruned_frames()
    byop = {o: [f for p, f in keep if p == o] for o in ("ADD", "SUB")}
    out, seen = [], set()
    while len(out) < n:
        x, y = rng.randint(gen.LO, gen.HI), rng.randint(gen.LO, gen.HI)
        op = rng.choice(("ADD", "SUB"))
        if not gen.valid_pair(x, y) or (x, y) in excluded_pairs:
            continue
        ans = x + y if op == "ADD" else x - y
        if ans not in Ts:
            continue
        name, name2 = rng.sample(tr["names"], 2); noun = rng.choice(tr["nouns"])
        if rng.random() < 0.5:
            fam = rng.choice(tr["families"])
            text = fam[op.lower()].format(name=name, name2=name2, noun=noun, x=x, y=y); fid = fam["id"]
        else:
            text = rng.choice(byop[op]).format(name=name, name2=name2, noun=noun, x=x, y=y); fid = "composed"
        if text in seen:
            continue
        seen.add(text); out.append({"op": op, "x": x, "y": y, "answer": ans, "text": text, "family": fid})
    return out
