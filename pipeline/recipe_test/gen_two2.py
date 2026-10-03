"""Two-step frames, extended: composed narrative frames + three structures that failed before (table layout, question-first, distance-with-units).
TRAIN variants and held-out EVAL variants use different wording; pruned so no train frame shares a sentence or 6-gram with any eval frame."""
import itertools, json, random
import gen, gen2, gen_two

# ---- weak structures: TRAIN variants
TQ_STEM = ["Work out how many {noun} {name} ends up with.", "Find the final number of {noun} that {name} has."]
T_GAIN_L = ["added", "received", "bought"]; T_LOSS_L = ["removed", "sold", "spent"]
T_TABLE = ["Log for {name}'s {noun}: start {x} | {a} {y} | {b} {z}. How many {noun} are there at the end?",
           "Record of {name}'s {noun}: start {x}; {a} {y}; {b} {z}. What is the final count of {noun}?"]
D_GAIN = ["Roadworks add", "A detour adds", "An extra loop adds"]; D_LOSS = ["A new bridge cuts", "A shortcut saves", "A tunnel removes"]
D_TRAIN = ["A route is {x} kilometres long. {a} {y} kilometres. Later, {b} {z} kilometres. How long is the route now?",
           "The trail measures {x} kilometres. {a} {y} kilometres. After that, {b} {z} kilometres. How long is the trail at the end?"]
# ---- EVAL variants (held out)
EQ_STEM = ["Tell me the closing number of {noun} owned by {name}.", "Determine how many {noun} {name} owns once everything is done."]
E_OPEN = ["{name} began with {x} {noun}.", "{name} held {x} {noun} at the start."]
E_GAIN = ["Then {name} obtained {n} extra.", "Next {name} collected {n} extra."]; E_LOSS = ["Then {name} handed over {n}.", "Next {name} donated {n}."]
E_TABLE = ["Ledger for {name}'s {noun}: opening count {x} / {a} {y} / {b} {z}. What is the closing count of {noun}?",
           "Tally for {name}'s {noun}: opening count {x} / {a} {y} / {b} {z}. Report the closing count of {noun}."]
E_GAIN_L = ["brought in", "gained"]; E_LOSS_L = ["taken out", "given away"]
ED_GAIN = ["Flooding adds", "A ring road adds"]; ED_LOSS = ["A viaduct trims", "A cut-through removes"]
ED_TEXT = ["The road is {x} kilometres in length. {a} {y} kilometres. Then, {b} {z} kilometres. Give the road's length at the end.",
           "The path runs for {x} kilometres. {a} {y} kilometres. Next, {b} {z} kilometres. What is the path's final length?"]


def low(t): return t[0].lower() + t[1:]


def weak_train():
    out = []
    S, K = gen_two.TR_START, gen_two.TR_LINK
    for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
        G = lambda o: gen_two.TR_GAIN if o == "ADD" else gen_two.TR_LOSS
        for st, s, k1, k2, a, b in itertools.product(TQ_STEM, S, K, K, G(o1), G(o2)):
            if k1 != k2:
                out.append((o1, o2, f"{st} {s} {k1}, {low(a.replace('{n}', '{y}'))} {k2}, {low(b.replace('{n}', '{z}'))}"))
        L = lambda o: T_GAIN_L if o == "ADD" else T_LOSS_L
        for t, a, b in itertools.product(T_TABLE, L(o1), L(o2)):
            out.append((o1, o2, t.replace("{a}", a).replace("{b}", b)))
        DL = lambda o: D_GAIN if o == "ADD" else D_LOSS
        for t, a, b in itertools.product(D_TRAIN, DL(o1), DL(o2)):
            out.append((o1, o2, t.replace("{a}", a).replace(", {b}", ", " + low(b))))
    return out


def weak_eval():
    """Held-out variants, grouped: returns dict structure -> list of (o1,o2,text)."""
    res = {"question_first": [], "table": [], "distance": []}
    for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
        G = lambda o: E_GAIN if o == "ADD" else E_LOSS
        for st, s, a, b in itertools.product(EQ_STEM, E_OPEN, G(o1), G(o2)):
            res["question_first"].append((o1, o2, f"{st} {s} {a.replace('{n}', '{y}')} {b.replace('{n}', '{z}')}"))
        L = lambda o: E_GAIN_L if o == "ADD" else E_LOSS_L
        for t, a, b in itertools.product(E_TABLE, L(o1), L(o2)):
            res["table"].append((o1, o2, t.replace("{a}", a).replace("{b}", b)))
        DL = lambda o: ED_GAIN if o == "ADD" else ED_LOSS
        for t, a, b in itertools.product(ED_TEXT, DL(o1), DL(o2)):
            res["distance"].append((o1, o2, t.replace("{a}", a).replace(", {b}", ", " + low(b))))
    return res


def eval_all_frames():
    f = gen_two.frames("eval")
    for v in weak_eval().values(): f += v
    return f


def train_frames(varied):
    base = [f for f in gen_two.frames("train")]
    fr = base + (weak_train() if varied else [])
    ev = eval_all_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    return [f for f in fr if not (gen2.grams(f[2]) & evg or gen2.sentences(f[2]) & evs)]


def disjointness():
    ev = eval_all_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    allf = gen_two.frames("train") + weak_train()
    kept = train_frames(True)
    return {"train_frames_raw": len(allf), "train_frames_kept": len(kept), "dropped": len(allf) - len(kept),
            "kept_sharing_6gram": sum(1 for _, _, t in kept if gen2.grams(t) & evg), "kept_sharing_sentence": sum(1 for _, _, t in kept if gen2.sentences(t) & evs),
            "weak_train_kept": sum(1 for f in kept if f in set(weak_train()))}


def stream(excluded, seed, n, varied, one_step_frac=0.3):
    T, _ = gen.answer_split(); Ts = set(T)
    tr = gen.load("templates_train.json"); rng = random.Random(9_500_000 + seed)
    fr = train_frames(varied); one = gen.train_sampler(excluded, 5_000_000 + seed)
    out, seen = [], set()
    while len(out) < n:
        if rng.random() < one_step_frac:
            r = next(one); r["steps"] = 1
            if r["text"] in seen: continue
            seen.add(r["text"]); out.append(r); continue
        while True:
            x, y, z = (rng.randint(10, 99) for _ in range(3))
            o1, o2, frame = rng.choice(fr)
            v = gen_two.ok_values(x, y, z, o1, o2)
            if v is None or v[1] not in Ts or (x, y, z) in excluded: continue
            text = frame.format(name=rng.choice(tr["names"]), noun=rng.choice(tr["nouns"]), place=rng.choice(gen_two.EV_PLACES), x=x, y=y, z=z)
            if text in seen: continue
            break
        seen.add(text)
        out.append({"steps": 2, "op1": o1, "op2": o2, "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
    return out
