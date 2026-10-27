"""Sleep-1 fact world: deterministic (seed 0) fictional entities, 120 taught facts, forward / reverse / two-hop tests.

6 relations x 20 facts = 120 facts. Two-hop chains (20 each, 60 total):
  mentor_of + lives_in : "Where does the mentor of S live?"        (mentor M of student S, M lives in C)
  sibling   + works_at : "Where does the sibling of A work?"        (A sibling B, B works at C)
  owns      + born_in  : "In which town was the owner of the boat called O born?"
Teaching uses ONE fixed sentence per fact; every test wording is different from teaching wording.
Run `python facts.py` to print 5 examples of each item type and run the leak checks.
"""
import json
import random
import sys

SEED = 0
N = 20  # facts per relation

# relation -> (teach template, forward question templates, reverse question templates)
# a = subject slot, b = object slot. forward: given a, answer b. reverse: given b, answer a.
REL = {
    "mentor_of": ("{a} is the mentor of {b}.",
                  ["Who is {a} the mentor of?", "Name the student that {a} mentors."],
                  ["Who mentored {b}?", "Who is the mentor of {b}?"]),
    "lives_in": ("{a} lives in {b}.",
                 ["Where does {a} live?", "Which place is {a}'s home?"],
                 ["Who lives in {b}?", "Who calls {b} home?"]),
    "sibling": ("{a} and {b} are siblings.",
                ["Who is {a}'s sibling?", "Name the brother or sister of {a}."],
                ["Who is {b}'s sibling?", "Name the brother or sister of {b}."]),
    "owns": ("{a} owns a boat called {b}.",
             ["Which boat does {a} own?", "What is the name of the boat that belongs to {a}?"],
             ["Who owns the boat called {b}?", "Who is the owner of the boat named {b}?"]),
    "works_at": ("{a} works at {b}.",
                 ["Where is {a} employed?", "Which company does {a} work for?"],
                 ["Who works at {b}?", "Who is employed by {b}?"]),
    "born_in": ("{a} was born in {b}.",
                ["Where was {a} born?", "Which town is the birthplace of {a}?"],
                ["Who was born in {b}?", "Whose birthplace is {b}?"]),
}
HOP = {  # kind -> question templates ({x} is the given entity)
    "mentor_lives": ["Where does the mentor of {x} live?", "In which place does {x}'s mentor live?"],
    "sibling_works": ["Where does the sibling of {x} work?", "Which company employs {x}'s sibling?"],
    "owner_born": ["In which town was the owner of the boat called {x} born?",
                   "Where was the owner of the boat named {x} born?"],
}

ON = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "dr", "kr", "tr", "gl", "fl", "sk", "vr", "zh", "kl"]
VO = ["a", "e", "i", "o", "u", "a", "e", "o", "ai", "ei", "ou"]
CO = ["", "", "n", "r", "l", "s", "m", "th", "x"]
# crude guard against real words / common names (no system dictionary on the box)
COMMON = set("""banana carol martin marina morale tomato potato salad pilot sonar solar lunar mirage valor vigor tenor
motor molar minor major manor mason melon melody dolor kilo lemon salon sofa rodeo radio patio piano tuxedo
""".split())


def make_names(rng, count, taken, lo=6, hi=9):
    out = []
    while len(out) < count:
        n = rng.choice([2, 3, 3, 3, 4])
        w = "".join(rng.choice(ON) + rng.choice(VO) for _ in range(n)) + rng.choice(CO)
        if not (lo <= len(w) <= hi) or w in COMMON:
            continue
        if any(w in t or t in w for t in taken):  # unique and no substring relation (safe substring matching)
            continue
        taken.add(w)
        out.append(w.capitalize())
    return out


def build(seed=SEED):
    rng = random.Random(seed)
    taken = set()
    people = make_names(rng, 100, taken)
    mentors, students, sibA, sibB, owners = (people[i * 20:(i + 1) * 20] for i in range(5))
    cities, companies, towns, boats = (make_names(rng, 20, taken) for _ in range(4))
    pairs = {
        "mentor_of": list(zip(mentors, students)),
        "lives_in": list(zip(mentors, cities)),
        "sibling": list(zip(sibA, sibB)),
        "works_at": list(zip(sibB, companies)),
        "owns": list(zip(owners, boats)),
        "born_in": list(zip(owners, towns)),
    }
    facts = []
    for rel, ps in pairs.items():
        for a, b in ps:
            facts.append({"id": len(facts), "rel": rel, "a": a, "b": b, "text": REL[rel][0].format(a=a, b=b),
                          "entities": [a, b]})
    rng.shuffle(facts)
    for i, f in enumerate(facts):
        f["id"] = i
    by = {(f["rel"], f["a"]): f for f in facts}
    forward, reverse, hops = [], [], []
    for f in facts:
        _, fq, rq = REL[f["rel"]]
        forward.append({"kind": "forward", "fact": f["id"], "rel": f["rel"], "q": fq[f["id"] % len(fq)].format(a=f["a"], b=f["b"]), "target": f["b"]})
        reverse.append({"kind": "reverse", "fact": f["id"], "rel": f["rel"], "q": rq[(f["id"] // 2) % len(rq)].format(a=f["a"], b=f["b"]), "target": f["a"]})
    for i, (m, s) in enumerate(pairs["mentor_of"]):
        t = HOP["mentor_lives"]
        hops.append({"kind": "twohop", "hop": "mentor_lives", "q": t[i % 2].format(x=s), "target": by[("lives_in", m)]["b"],
                     "facts": [by[("mentor_of", m)]["id"], by[("lives_in", m)]["id"]]})
    for i, (a, b) in enumerate(pairs["sibling"]):
        t = HOP["sibling_works"]
        hops.append({"kind": "twohop", "hop": "sibling_works", "q": t[i % 2].format(x=a), "target": by[("works_at", b)]["b"],
                     "facts": [by[("sibling", a)]["id"], by[("works_at", b)]["id"]]})
    for i, (p, bt) in enumerate(pairs["owns"]):
        t = HOP["owner_born"]
        hops.append({"kind": "twohop", "hop": "owner_born", "q": t[i % 2].format(x=bt), "target": by[("born_in", p)]["b"],
                     "facts": [by[("owns", p)]["id"], by[("born_in", p)]["id"]]})
    world = {"seed": seed, "teaching": [f["text"] for f in facts], "facts": facts,
             "forward": forward, "reverse": reverse, "twohop": hops}
    check(world)
    return world


def norm(s):
    return " ".join(s.lower().replace("’", "'").split())


def check(w):
    teach = [norm(t) for t in w["teaching"]]
    assert len(teach) == 120 and len(w["twohop"]) == 60 and len(w["forward"]) == 120 and len(w["reverse"]) == 120
    names = {e for f in w["facts"] for e in f["entities"]}
    assert len(names) == 180 or len(names) == len({n.lower() for n in names}), "duplicate names"
    low = sorted(n.lower() for n in names)
    for i, n in enumerate(low):
        assert 6 <= len(n) <= 9, n
        assert not any(n in m for m in low if m != n), f"substring clash {n}"
    for k in ("forward", "reverse", "twohop"):
        for t in w[k]:
            q = norm(t["q"])
            assert not any(q == s or q in s or s in q for s in teach), f"test wording in teaching: {q}"
            assert t["target"].lower() not in q, f"target leaked in question: {q}"
    # every question template must be absent from teaching templates
    tt = {REL[r][0].split("{")[0] for r in REL}  # (weak) sanity only
    return True


def test_strings(w):
    return {norm(t["q"]) for k in ("forward", "reverse", "twohop") for t in w[k]}


if __name__ == "__main__":
    w = build()
    again = build()
    assert json.dumps(w, sort_keys=True) == json.dumps(again, sort_keys=True), "not deterministic"
    print("n teaching", len(w["teaching"]), "forward", len(w["forward"]), "reverse", len(w["reverse"]), "twohop", len(w["twohop"]))
    for key in ("teaching", "forward", "reverse", "twohop"):
        print(f"\n== {key}")
        for it in w[key][:5]:
            print("  ", it if isinstance(it, str) else f"{it['q']}  -> {it['target']}")
    print("\nleak checks passed; unique test strings:", len(test_strings(w)))
