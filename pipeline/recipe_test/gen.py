"""Data for the fresh-data (never-repeating) reasoner test.

Answers are two-digit (10..99), one LM token each. The 90 possible answers are split once, by a
fixed seed, into TRAIN answers T (60) and HELD-OUT answers H (30). No training problem has an
answer in H, in either arm. Every eval operand pair is excluded from every training stream.
"""
import hashlib, json, random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPLIT_SEED, POOL_SEED, EVAL_SEED = 20261101, 20261102, 20261103
LO, HI = 10, 99


def load(name):
    return json.loads((HERE / name).read_text())


def answer_split():
    vals = list(range(LO, HI + 1))
    random.Random(SPLIT_SEED).shuffle(vals)
    return sorted(vals[:60]), sorted(vals[60:])  # T, H


def valid_pair(x, y):
    return x >= LO and y >= LO and x - y >= LO and x + y <= HI


def render(fam, op, names, nouns, x, y, rng):
    name, name2 = rng.sample(names, 2)
    noun = rng.choice(nouns)
    return fam[op].format(name=name, name2=name2, noun=noun, x=x, y=y)


def eval_form(n_per_cell=24):
    T, H = answer_split(); Ts, Hs = set(T), set(H)
    tr, ev = load("templates_train.json"), load("templates_eval.json")
    rng = random.Random(EVAL_SEED)
    pairs = [(x, y) for x in range(LO, HI) for y in range(LO, HI) if valid_pair(x, y)]
    unseen = [p for p in pairs if p[0] + p[1] in Hs and p[0] - p[1] in Hs]
    seen = [p for p in pairs if p[0] + p[1] in Ts and p[0] - p[1] in Ts]
    rng.shuffle(unseen); rng.shuffle(seen)
    rows, used = [], set()
    for ans_cell, pool in (("unseen", unseen), ("seen", seen)):
        for wording, src in (("train_wording", tr), ("new_wording", ev)):
            cell = f"{ans_cell}/{wording}"
            k = 0
            while k < n_per_cell:
                x, y = pool.pop()
                if (x, y) in used:
                    continue
                used.add((x, y))
                fam = src["families"][k % len(src["families"])]
                # same names and noun for both questions of a pair
                st = random.Random(f"{EVAL_SEED}-{cell}-{k}")
                name, name2 = st.sample(src["names"], 2); noun = st.choice(src["nouns"])
                for op in ("add", "sub"):
                    rows.append({"id": f"{cell.replace('/', '-')}-{k:02d}-{op}", "pair_id": f"{cell.replace('/', '-')}-{k:02d}",
                                 "cell": cell, "family": fam["id"], "op": op.upper(), "x": x, "y": y,
                                 "answer": x + y if op == "add" else x - y,
                                 "text": fam[op].format(name=name, name2=name2, noun=noun, x=x, y=y)})
                k += 1
    return rows


def eval_pair_set(rows):
    return {(r["x"], r["y"]) for r in rows}


def train_sampler(excluded_pairs, seed):
    """Yields single training questions with answers in T, excluding eval operand pairs."""
    T, _ = answer_split(); Ts = set(T)
    tr = load("templates_train.json"); rng = random.Random(seed)
    fams = tr["families"]
    while True:
        x, y = rng.randint(LO, HI), rng.randint(LO, HI)
        op = rng.choice(("ADD", "SUB"))
        if not valid_pair(x, y) or (x, y) in excluded_pairs:
            continue
        ans = x + y if op == "ADD" else x - y
        if ans not in Ts:
            continue
        fam = rng.choice(fams)
        text = render(fam, op.lower(), tr["names"], tr["nouns"], x, y, rng)
        yield {"op": op, "x": x, "y": y, "answer": ans, "text": text, "family": fam["id"]}


def pool_a(excluded_pairs, size=256):
    g = train_sampler(excluded_pairs, POOL_SEED); out, seen = [], set()
    while len(out) < size:
        r = next(g)
        if r["text"] not in seen:
            seen.add(r["text"]); out.append(r)
    return out


def stream_b(excluded_pairs, seed, n):
    """n never-repeating training questions (unique text) for arm B, per run seed."""
    g = train_sampler(excluded_pairs, 7_100_000 + seed); out, seen = [], set()
    while len(out) < n:
        r = next(g)
        if r["text"] not in seen:
            seen.add(r["text"]); out.append(r)
    return out


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
