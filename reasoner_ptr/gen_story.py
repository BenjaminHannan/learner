"""Short-story reading task for the two-doors test (design/info-paths/information-paths.md, T1/T2).

Stories: 3 people, 2 objects, 2 places. Questions are one-hop (who took X / where did P go / what did P take) or
two-hop (who has X now, after a hand-over / where is X, via the person who took it). Every answer is one word that
appears in the story and is one LFM2.5 token with a leading space. Each word list is split once (SPLIT_SEED) into
train words and held-out words. Training stories use only train words and train wording. Eval cells:
answers seen/unseen x wording train/new x hop one/two. Unseen-answer stories use only held-out words, so their
answers were never inputs or outputs in training.
"""
import json, random

SPLIT_SEED, EVAL_SEED = 20261003, 777
NAMES = ['Leo', 'Ana', 'Bo', 'Sam', 'Max', 'Eva', 'Tom', 'Ben', 'Kim', 'Liz', 'Jon', 'Amy', 'Ian', 'Ray', 'Joe', 'Kai',
         'Eli', 'Noah', 'Emma', 'Owen', 'Ruby', 'Jack', 'Lily', 'Ella', 'Finn', 'Nina', 'Omar', 'Rosa', 'Hugo', 'Lucy',
         'Paul', 'Sara', 'Dan', 'Ted', 'Alex', 'Kate', 'Mark', 'Anna', 'Luke', 'Jane', 'Rose', 'Adam', 'Carl', 'Fred',
         'Hans', 'Iris', 'Karl', 'Nell', 'Otto', 'Pete', 'Rita', 'Seth', 'Vera', 'Walt', 'Bill', 'Cole', 'Dave', 'Hope',
         'Kurt', 'Lisa', 'Neil', 'Olga', 'Phil', 'Ruth', 'Sean', 'Wade']
OBJS = ['cup', 'key', 'book', 'ball', 'hat', 'pen', 'box', 'bag', 'coin', 'lamp', 'map', 'rope', 'bell', 'drum', 'fork',
        'doll', 'shoe', 'sock', 'coat', 'ring', 'card', 'jar', 'spoon', 'bowl', 'brush', 'clock', 'toy', 'cake', 'egg',
        'apple', 'shell', 'stone', 'stick', 'flag', 'mask', 'glove', 'plate', 'knife']
PLACES = ['kitchen', 'garden', 'park', 'library', 'school', 'beach', 'market', 'barn', 'office', 'station', 'shop', 'yard',
          'forest', 'bridge', 'church', 'harbor', 'porch', 'tower', 'lake', 'farm', 'hall', 'garage', 'museum', 'hotel',
          'castle', 'river', 'field']

W = {  # wording: 'train' frames are used in training, 'new' frames only in eval
    "open": {"train": ["Yesterday,", "On Monday,", "In the morning,", "After lunch,", "That day,", "At noon,"],
             "new": ["Late at night,", "Before dinner,"]},
    "take": {"train": ["{p} took the {o}.", "{p} picked up the {o}.", "{p} grabbed the {o}.", "The {o} was taken by {p}."],
             "new": ["{p} collected the {o}.", "{p} reached for the {o} and kept it."]},
    "go": {"train": ["{p} went to the {l}.", "{p} walked to the {l}.", "{p} headed to the {l}.", "Then {p} ran to the {l}."],
           "new": ["{p} hurried over to the {l}.", "Soon {p} arrived at the {l}."]},
    "give": {"train": ["{p} gave the {o} to {q}.", "{p} handed the {o} to {q}.", "The {o} was given to {q} by {p}."],
             "new": ["{p} passed the {o} over to {q}.", "{q} got the {o} from {p}."]},
    "q_taker": {"train": ["Who took the {o}?", "Who picked up the {o} first?"], "new": ["Which person took the {o} first?"]},
    "q_went": {"train": ["Where did {p} go?", "To which place did {p} go?"], "new": ["Where did {p} end up?"]},
    "q_what": {"train": ["What did {p} take?", "What did {p} pick up?"], "new": ["Which thing did {p} take?"]},
    "q_holder": {"train": ["Who has the {o} now?", "Who is holding the {o} now?"], "new": ["Which person ends up with the {o}?"]},
    "q_where_obj": {"train": ["Where is the {o} now?", "In which place is the {o}?"], "new": ["Where would you find the {o}?"]},
}
ONE_HOP, TWO_HOP = ("q_taker", "q_went", "q_what"), ("q_holder", "q_where_obj")


def split():
    r = random.Random(SPLIT_SEED)
    out = {}
    for name, lst in (("names", NAMES), ("objs", OBJS), ("places", PLACES)):
        l = list(lst); r.shuffle(l); k = len(l) // 3
        out[name] = {"heldout": sorted(l[:k]), "train": sorted(l[k:])}
    return out


def story(r, words, wording, qkind):
    """One story + question. qkind in ONE_HOP + TWO_HOP. Returns dict(text, answer, qkind)."""
    pick = lambda key: r.choice(W[key][wording])
    a, b, c = r.sample(words["names"], 3)
    o1, o2 = r.sample(words["objs"], 2)
    l1, l2 = r.sample(words["places"], 2)
    give = qkind == "q_holder" or (qkind not in ("q_where_obj",) and r.random() < 0.5)
    # events: a takes o1, b takes o2, a goes l1, b goes l2, optional a gives o1 to c (after a took it)
    takes = [pick("take").format(p=a, o=o1), pick("take").format(p=b, o=o2)]
    goes = [pick("go").format(p=a, l=l1), pick("go").format(p=b, l=l2)]
    r.shuffle(takes)
    ev = []
    # keep "b takes o2" before "b goes l2" so "where is o2" is well defined; a's give happens after a's take
    order = r.choice([0, 1])
    if order == 0:
        ev = takes + goes
    else:
        ev = [takes[0], goes[0], takes[1], goes[1]] if takes[0].find(a) >= 0 else [takes[0], goes[1], takes[1], goes[0]]
        # ensure each person's take precedes their go
        ia_t = next(i for i, s in enumerate(ev) if a in s and o1 in s); ia_g = next(i for i, s in enumerate(ev) if l1 in s)
        ib_t = next(i for i, s in enumerate(ev) if b in s and o2 in s); ib_g = next(i for i, s in enumerate(ev) if l2 in s)
        if ia_t > ia_g or ib_t > ib_g:
            ev = takes + goes
    if give:
        g = pick("give").format(p=a, o=o1, q=c)
        ia_t = next(i for i, s in enumerate(ev) if a in s and o1 in s)
        ev.insert(r.randint(ia_t + 1, len(ev)), g)
    q, ans = {
        "q_taker": (pick("q_taker").format(o=r.choice([o1, o2])), None),
        "q_went": (None, None), "q_what": (None, None), "q_holder": (None, None), "q_where_obj": (None, None)}[qkind]
    if qkind == "q_taker":
        oo = o1 if o1 in q else o2; ans = a if oo == o1 else b
    elif qkind == "q_went":
        p = r.choice([a, b]); q = pick("q_went").format(p=p); ans = l1 if p == a else l2
    elif qkind == "q_what":
        p = r.choice([a, b]); q = pick("q_what").format(p=p); ans = o1 if p == a else o2
    elif qkind == "q_holder":
        q = pick("q_holder").format(o=o1); ans = c
    else:  # q_where_obj: o2 is with b, who went to l2 (no give in these stories)
        q = pick("q_where_obj").format(o=o2); ans = l2
    if ev[0].split()[0] in ("The", "Then", "Soon"):
        ev[0] = ev[0][0].lower() + ev[0][1:]
    text = pick("open") + " " + " ".join(ev) + " " + q
    return {"text": text, "answer": ans, "qkind": qkind}


def stream(seed, n, words, exclude):
    r = random.Random(seed); out, seen = [], set(exclude)
    while len(out) < n:
        s = story(r, words, "train", r.choice(ONE_HOP + TWO_HOP))
        if s["text"] in seen:
            continue
        seen.add(s["text"]); out.append(s)
    return out


def eval_form():
    sp = split(); r = random.Random(EVAL_SEED); rows = []
    for ans_cell in ("seen", "unseen"):
        words = {k: v["train" if ans_cell == "seen" else "heldout"] for k, v in sp.items()}
        for wording in ("train", "new"):
            for hop, kinds in (("one", ONE_HOP), ("two", TWO_HOP)):
                for i in range(48):
                    s = story(r, words, wording, kinds[i % len(kinds)])
                    s.update(cell=f"{ans_cell}-{wording}-{hop}", id=f"{ans_cell}-{wording}-{hop}-{i:02d}")
                    rows.append(s)
    return rows


if __name__ == "__main__":
    import sys, collections
    sp = split(); print(json.dumps({k: {kk: len(vv) for kk, vv in v.items()} for k, v in sp.items()}))
    form = eval_form()
    assert len({x["text"] for x in form}) == len(form)
    for x in form:
        assert (" " + x["answer"]) in (" " + x["text"].rsplit(" ", 1)[0] if False else " " + x["text"]), x
    print(collections.Counter(x["cell"] for x in form))
    for x in form[:3] + form[-3:]:
        print(x)
    tr = stream(0, 5, {k: v["train"] for k, v in sp.items()}, set())
    for x in tr: print(x)
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(json.dumps(form, indent=0))
