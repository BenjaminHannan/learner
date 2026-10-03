"""Two-step problems (two chained calculator calls). TRAIN composer and a separately worded EVAL composer, disjoint by 6-gram check.

Problem: r1 = x op1 y ; final = r1 op2 z, all values two-digit (10..99). Final answers split with gen.answer_split(): train finals in T only,
eval 'unseen' finals in H, 'seen' finals in T. Intermediate r1 is any two-digit value (so H values can appear as intermediates in training).
One-step problems (gen.py style) are mixed into training (30%) so the model must decide whether to make a second call.
"""
import itertools, random
import gen, gen2

TR_START = ["{name} had {x} {noun}.", "{name} started with {x} {noun}.", "At first {name} owned {x} {noun}."]
TR_GAIN = ["{name} received {n} more.", "A friend gave {name} {n} more.", "{name} picked up {n} more."]
TR_LOSS = ["{name} gave away {n} of them.", "{name} lost {n} of them.", "{name} used up {n} of them."]
TR_LINK = ["Then", "Later", "After that"]
TR_Q = ["How many {noun} does {name} have now?", "How many {noun} does {name} have at the end?", "How many {noun} are left with {name} now?"]

EV_START = ["There were {x} {noun} in the {place}.", "The {place} held {x} {noun}.", "Inside the {place} you could find {x} {noun}."]
EV_GAIN = ["Workers brought in {n} additional ones.", "A truck added {n} extra ones.", "A delivery of {n} more came in."]
EV_LOSS = ["Customers took {n} of them.", "Visitors carried off {n} of them.", "A storm destroyed {n} of them."]
EV_LINK = ["By noon", "Next", "At closing time"]
EV_Q = ["What is the count of {noun} in the {place} by the end?", "How many {noun} remain in the {place} at the end of the day?", "Tell me how many {noun} the {place} ends up with."]
EV_PLACES = ["warehouse", "pantry", "cellar", "garage", "boathouse", "greenhouse"]
EV_NAMES = None  # eval frames use no names


def low(t):
    return t[0].lower() + t[1:]


def frames(kind):
    out = []
    S, G, L, K, Q = (TR_START, TR_GAIN, TR_LOSS, TR_LINK, TR_Q) if kind == "train" else (EV_START, EV_GAIN, EV_LOSS, EV_LINK, EV_Q)
    for s, o1, o2, k1, k2, q in itertools.product(S, ("ADD", "SUB"), ("ADD", "SUB"), K, K, Q):
        if k1 == k2:
            continue
        for a, b in itertools.product(G if o1 == "ADD" else L, G if o2 == "ADD" else L):
            text = f"{s} {k1}, {low(a.replace('{n}', '{y}'))} {k2}, {low(b.replace('{n}', '{z}'))} {q}"
            out.append((o1, o2, text))
    return out


def ok_values(x, y, z, o1, o2):
    r1 = x + y if o1 == "ADD" else x - y
    if not (10 <= r1 <= 99):
        return None
    f = r1 + z if o2 == "ADD" else r1 - z
    if not (10 <= f <= 99):
        return None
    return r1, f


def stream_two(excluded, seed, n, kind="train", final_set=None, one_step_frac=0.3):
    T, H = gen.answer_split()
    final_set = set(T if final_set is None else final_set)
    tr = gen.load("templates_train.json"); rng = random.Random(9_000_000 + seed)
    fr = frames(kind); keep = []
    if kind == "train":
        import json
        ev = frames("eval")
        evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
        fr = [f for f in fr if not (gen2.grams(f[2]) & evg or gen2.sentences(f[2]) & evs)]
    names = tr["names"]; nouns = tr["nouns"]
    one = gen.train_sampler(excluded, 5_000_000 + seed)
    out, seen = [], set()
    while len(out) < n:
        if kind == "train" and rng.random() < one_step_frac:
            r = next(one); r["steps"] = 1
            if r["text"] in seen: continue
            seen.add(r["text"]); out.append(r); continue
        while True:
            x, y, z = (rng.randint(10, 99) for _ in range(3))
            o1, o2, frame = rng.choice(fr)
            v = ok_values(x, y, z, o1, o2)
            if v is None or v[1] not in final_set or (x, y, z) in excluded:
                continue
            name = rng.choice(names); noun = rng.choice(nouns); place = rng.choice(EV_PLACES)
            text = frame.format(name=name, noun=noun, place=place, x=x, y=y, z=z)
            if text in seen: continue
            break
        seen.add(text)
        out.append({"steps": 2, "op1": o1, "op2": o2, "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
    return out
