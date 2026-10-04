"""Round 3: two-step (two chained calculator calls) problems on the real pipeline. Run with RT_ROUND=2 (answer split seed 20261201).

TRAIN frames = gen_two TRAIN narrative frames + gen_two2 weak_train variants (table / question-first / distance), as in the stand-in test; 70% two-step items
plus 30% one-step items (round-2 stream_w wording). EVAL = 192 NEW two-step questions in four structures with wording authored for this round
(narrative, question-first, table layout, distance), pruned-against: no training frame shares a sentence or word 6-gram with any eval frame.
Finals: 'unseen' finals in held-out answers H, 'seen' finals in train answers T. Intermediate results may be any two-digit value.
"""
import itertools, json, random
import gen, gen2, gen_two, gen_two2

assert gen.ROUND == "2", "run with RT_ROUND=2"

# ---------------- EVAL wording (new this round)
N_OPEN = ["A shelf began the week with {x} {noun}.", "The cupboard started out holding {x} {noun}."]
N1_GAIN = ["On Tuesday, {y} more were stocked.", "On Tuesday, {y} fresh ones arrived."]
N1_LOSS = ["On Tuesday, {y} were removed.", "On Tuesday, {y} were carted off."]
N2_GAIN = ["On Friday, {z} more were stocked.", "On Friday, {z} fresh ones arrived."]
N2_LOSS = ["On Friday, {z} were removed.", "On Friday, {z} were carted off."]
N_Q = ["How many {noun} does the shelf hold afterwards?", "Report the number of {noun} on the shelf at the end."]
Q_STEM = ["What is the final tally of {noun} in the crate?", "State how many {noun} the crate holds in the end."]
Q_OPEN = ["The crate began with {x} {noun}."]
Q_GAIN = ["Next, {n} more went in.", "Then {n} more were added."]
Q_LOSS = ["Next, {n} were taken out.", "Then {n} were pulled out."]
T_TAB = ["Stock sheet for {noun}: opening {x} ; {a} {y} ; {b} {z}. What is the closing stock of {noun}?",
         "Inventory card, {noun}: opening {x} ; {a} {y} ; {b} {z}. Give the closing stock."]
T_G = ["restocked", "delivered"]; T_L = ["shipped", "discarded"]
D_TXT = ["A cycle path is {x} metres long. {a} {y} metres. After that, {b} {z} metres. How long is the cycle path at the end?",
         "The towpath stretches {x} metres. {a} {y} metres. Later, {b} {z} metres. What is the towpath's final length?"]
D_G = ["Repairs extend it by", "A new section adds"]; D_L = ["A barrier cuts off", "A closure removes"]


def low(t): return t[0].lower() + t[1:]


def eval_frames():
    res = {"narrative": [], "question_first": [], "table": [], "distance": []}
    for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
        for s, a, b, q in itertools.product(N_OPEN, N1_GAIN if o1 == "ADD" else N1_LOSS, N2_GAIN if o2 == "ADD" else N2_LOSS, N_Q):
            res["narrative"].append((o1, o2, f"{s} {a} {b} {q}"))
        for st, s, a, b in itertools.product(Q_STEM, Q_OPEN, Q_GAIN if o1 == "ADD" else Q_LOSS, Q_GAIN if o2 == "ADD" else Q_LOSS):
            res["question_first"].append((o1, o2, f"{st} {s} {a.replace('{n}', '{y}')} {b.replace('{n}', '{z}')}"))
        for t, a, b in itertools.product(T_TAB, T_G if o1 == "ADD" else T_L, T_G if o2 == "ADD" else T_L):
            res["table"].append((o1, o2, t.replace("{a}", a).replace("{b}", b)))
        for t, a, b in itertools.product(D_TXT, D_G if o1 == "ADD" else D_L, D_G if o2 == "ADD" else D_L):
            res["distance"].append((o1, o2, t.replace("{a}", a).replace(", {b}", ", " + low(b))))
    return res


def all_eval_frames():
    return [f for v in eval_frames().values() for f in v]


def train_frames():
    fr = gen_two.frames("train") + gen_two2.weak_train()
    ev = all_eval_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    return [f for f in fr if not (gen2.grams(f[2]) & evg or gen2.sentences(f[2]) & evs)]


def disjointness():
    ev = all_eval_frames(); kept = train_frames()
    evg = set().union(*(gen2.grams(t) for _, _, t in ev)); evs = set().union(*(gen2.sentences(t) for _, _, t in ev))
    raw = gen_two.frames("train") + gen_two2.weak_train()
    tr = gen.load("templates_train.json"); e2 = gen.load(gen.EVAL_FILE)
    return {"train_frames_raw": len(raw), "train_frames_kept": len(kept), "dropped": len(raw) - len(kept),
            "kept_sharing_6gram": sum(1 for _, _, t in kept if gen2.grams(t) & evg), "kept_sharing_sentence": sum(1 for _, _, t in kept if gen2.sentences(t) & evs),
            "eval_frames": {k: len(v) for k, v in eval_frames().items()}, "name_overlap": sorted(set(tr["names"]) & set(e2["names"])),
            "noun_overlap": sorted(set(tr["nouns"]) & set(e2["nouns"]))}


def build_eval(per_cell=6, seed=20261301, fits=lambda t: True):
    T, H = gen.answer_split(); rng = random.Random(seed)
    e2 = gen.load(gen.EVAL_FILE); ef = eval_frames(); rows = []; used = set()
    for sname, frames in ef.items():
        for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
            fr = [f for f in frames if (f[0], f[1]) == (o1, o2)]
            for cell, finals in (("unseen", set(H)), ("seen", set(T))):
                for k in range(per_cell):
                    while True:
                        x, y, z = (rng.randint(10, 99) for _ in range(3))
                        v = gen_two.ok_values(x, y, z, o1, o2)
                        if v and v[1] in finals and (x, y, z) not in used: break
                    used.add((x, y, z))
                    while True:  # resample wording slots until the question fits the real core's 49-token cap (with EOS)
                        text = rng.choice(fr)[2].format(name=rng.choice(e2["names"]), noun=rng.choice(e2["nouns"]), x=x, y=y, z=z)
                        if fits(text): break
                    rows.append({"id": f"{sname}-{o1}{o2}-{cell}-{k}", "cell": f"{cell}/{sname}", "structure": sname, "steps": 2, "op1": o1, "op2": o2,
                                 "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
    return rows


def stream(excluded_triples, excluded_pairs, seed, n, one_step_frac=0.3, fits=lambda t: True, frames="base"):
    T, _ = gen.answer_split(); Ts = set(T)
    tr = gen.load("templates_train.json"); rng = random.Random(9_600_000 + seed)
    fr = train_frames()
    if frames == "comp":
        import gen_two_v
        fr = fr + gen_two_v.train_frames()
    elif frames == "tabv":
        import gen_two_v
        fr = fr + gen_two_v.train_frames(tab=6000)
    one = iter(gen2.stream_w(excluded_pairs, 700 + seed, int(n * one_step_frac) + 2000))
    out, seen = [], set()
    while len(out) < n:
        if rng.random() < one_step_frac:
            r = next(one)
            if r["text"] in seen or not fits(r["text"]): continue
            r = dict(r); r["steps"] = 1; seen.add(r["text"]); out.append(r); continue
        while True:
            x, y, z = (rng.randint(10, 99) for _ in range(3))
            o1, o2, frame = rng.choice(fr)
            v = gen_two.ok_values(x, y, z, o1, o2)
            if v is None or v[1] not in Ts or (x, y, z) in excluded_triples: continue
            text = frame.format(name=rng.choice(tr["names"]), noun=rng.choice(tr["nouns"]), place=rng.choice(gen_two.EV_PLACES), x=x, y=y, z=z)
            if text in seen or not fits(text): continue
            break
        seen.add(text)
        out.append({"steps": 2, "op1": o1, "op2": o2, "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
    return out


def build_blind(per_cell=2, seed=20261501, fits=lambda t: True, used=frozenset()):
    """Round 5: 12 independently written layout families (eval_layouts_r5_blind.json, written by a separate worker given only the task description).
    12 families x 4 op pairs x (per_cell unseen + per_cell seen finals) = 192 questions."""
    import json, os
    T, H = gen.answer_split(); rng = random.Random(seed)
    e2 = gen.load(gen.EVAL_FILE); rows = []; used = set(used)
    fams = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_layouts_r5_blind.json")))["families"]
    for fam in fams:
        for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
            texts = fam["frames"][f"{o1}-{o2}"]; k = 0
            for cell, finals in (("unseen", set(H)), ("seen", set(T))):
                for j in range(per_cell):
                    while True:
                        x, y, z = (rng.randint(10, 99) for _ in range(3))
                        v = gen_two.ok_values(x, y, z, o1, o2)
                        if v and v[1] in finals and (x, y, z) not in used: break
                    used.add((x, y, z))
                    text = None
                    for _ in range(200):
                        c = texts[k % len(texts)].format(name=rng.choice(e2["names"]), noun=rng.choice(e2["nouns"]), x=x, y=y, z=z)
                        if fits(c): text = c; break
                    assert text, ("cannot fit 49 tokens", fam["name"])
                    k += 1
                    rows.append({"id": f"{fam['name']}-{o1}{o2}-{cell}-{j}", "cell": f"{cell}/{fam['name']}", "structure": fam["kind"], "steps": 2, "op1": o1, "op2": o2,
                                 "x": x, "y": y, "z": z, "r1": v[0], "answer": v[1], "text": text})
    return rows
