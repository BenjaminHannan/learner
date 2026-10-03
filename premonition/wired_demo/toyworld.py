"""Toy world: plumbing data written for tests. NOT an evaluation, not drawn from any panel.
No result on it supports a capability claim.

T1 calc+read: the notebook says which colour a person likes; the question holds both counts; the verb picks the op.
T2 two calls + read: the second call uses the first result.
T3 write then read: a "Remember : ..." turn writes or edits a note; a later T1 turn reads it.
Pairs: same question bytes, notebooks differing in exactly one fact (red <-> blue), different gold operands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import random

from .actions import Action

NAMES = ["ana", "ben", "cy", "dee"]
COLOURS = ["red", "blue"]
ITEMS = ["pens", "cards"]
OPS = ["ADD", "SUB", "MUL", "DIV"]
CLAIMS = "toy data written for plumbing tests; not an eval"


@dataclass
class Episode:
    family: str                  # "T1" | "T2" | "T3A"
    question: str
    notebook: list               # initial notebook fact texts
    gold: list                   # list[Action], executed by the host in order
    key: Fraction | None         # generator's key answer (None for statement turns)
    meta: dict = field(default_factory=dict)


def _facts(rng, liker, colour, distractors=0):
    """One fact by default: with distractors the lookup needs a name match, which 600 CPU steps do not learn."""
    others = [n for n in NAMES if n != liker]
    rng.shuffle(others)
    facts = [f"{liker} likes {colour} ."] + [f"{n} likes {rng.choice(COLOURS)} ." for n in others[:distractors]]
    rng.shuffle(facts)
    return facts


def _two_counts(rng, item, x_red, x_blue):
    """Return clause text and the literal index of each colour (order of clauses is random)."""
    order = COLOURS[:]; rng.shuffle(order)
    val = {"red": x_red, "blue": x_blue}
    text = f"has {val[order[0]]} {order[0]} {item} and {val[order[1]]} {order[1]} {item}"
    return text, {order[0]: 0, order[1]: 1}


def _t1(rng, colour=None, op=None, liker=None, notebook=None):
    op = op or rng.choice(OPS)
    n = liker or rng.choice(NAMES)
    colour = colour or rng.choice(COLOURS)
    item = rng.choice(ITEMS)
    while True:
        xr, xb = rng.randint(1, 20), rng.randint(1, 20)
        if xr == xb: continue
        c = {"ADD": rng.randint(1, 20), "SUB": rng.randint(1, 8), "MUL": rng.randint(2, 9), "DIV": rng.randint(2, 7)}[op]
        clause, idx = _two_counts(rng, item, xr, xb)
        x = {"red": xr, "blue": xb}
        if op == "SUB" and min(xr, xb) < c: continue
        vals = {o: {"ADD": x[o] + c, "SUB": x[o] - c, "MUL": x[o] * c, "DIV": Fraction(x[o], c)}[op] for o in COLOURS}
        if len({xr, xb, c} | {vals["red"], vals["blue"]}) != 5: continue   # answers differ and never equal a literal
        break
    tail = {"ADD": f"{n} buys {c} more {item} of the colour {n} likes",
            "SUB": f"{n} loses {c} {item} of the colour {n} likes",
            "MUL": f"{n} gets {c} times as many {item} of the colour {n} likes",
            "DIV": f"{n} shares the {item} of the colour {n} likes equally between {c} friends"}[op]
    q = f"{n} {clause} . {tail} . How many {item} of that colour ?" if op != "DIV" else \
        f"{n} {clause} . {tail} . How many {item} does each friend get ?"
    gold = [Action("CALC", op, idx[colour], 2), Action("ANSWER", ptr_a=3)]
    nb = notebook if notebook is not None else _facts(rng, n, colour)
    return Episode("T1", q, nb, gold, Fraction(vals[colour]), {"liker": n, "colour": colour, "op": op, "idx": idx})


def _t2(rng, colour=None):
    n, m = rng.choice(NAMES), rng.choice(NAMES)
    colour = colour or rng.choice(COLOURS)
    item = rng.choice(ITEMS)
    while True:
        xr, xb, c, d = (rng.randint(1, 20) for _ in range(4))
        x = {"red": xr, "blue": xb}
        if xr == xb or min(xr, xb) < c: continue
        fin = {o: x[o] - c + d for o in COLOURS}
        if len({xr, xb, c, d} | {fin["red"], fin["blue"], x["red"] - c, x["blue"] - c}) != 8: continue
        break
    clause, idx = _two_counts(rng, item, xr, xb)
    q = (f"{n} {clause} . {n} gives away {c} {item} of the colour {m} likes , then gets {d} more . "
         f"How many {item} of that colour ?")
    gold = [Action("CALC", "SUB", idx[colour], 2), Action("CALC", "ADD", 4, 3), Action("ANSWER", ptr_a=5)]
    return Episode("T2", q, _facts(rng, m, colour), gold, Fraction(fin[colour]), {"liker": m, "colour": colour, "idx": idx})


def _t3(rng):
    """Turn A (write) and turn B (a T1 question about the same person, run on the notebook A leaves behind)."""
    n = rng.choice(NAMES)
    nb = [f"{p} likes {rng.choice(COLOURS)} ." for p in rng.sample(NAMES, rng.randint(1, 3))]
    old = next((t.split()[2] for t in nb if t.startswith(f"{n} likes")), None)
    new_c = rng.choice([c for c in COLOURS if c != old])    # an edit always changes the colour
    slot = next((i for i, t in enumerate(nb) if t.startswith(f"{n} likes")), len(nb))
    a = Episode("T3A", f"Remember : {n} likes {new_c} .", nb,
                [Action("NOTE_WRITE", slot=slot, start=2, end=5), Action("DONE")], None, {"liker": n, "colour": new_c})
    after = list(nb)
    text = f"{n} likes {new_c} ."
    if slot == len(nb): after.append(text)
    else: after[slot] = text
    b = _t1(rng, colour=new_c, liker=n, notebook=after)
    return a, b


def generate(rng, family):
    if family == "T1": return _t1(rng)
    if family == "T2": return _t2(rng)
    if family == "T3": return _t3(rng)
    raise ValueError(family)


def make_pair(rng, family="T1"):
    """Two episodes with the identical question and notebooks differing in exactly one fact."""
    e = generate(rng, family)
    colour, liker = e.meta["colour"], e.meta["liker"]
    other = [c for c in COLOURS if c != colour][0]
    nb2 = [t.replace(f"{liker} likes {colour}", f"{liker} likes {other}") for t in e.notebook]
    if family == "T1": f = _t1_from(e, other, nb2)
    else: f = _t2_from(e, other, nb2)
    assert e.question == f.question and sum(a != b for a, b in zip(e.notebook, nb2)) == 1
    assert e.key != f.key
    return e, f


def _recompute(e, other, nb2):
    import re
    nums = [int(x) for x in re.findall(r"\d+", e.question)]
    idx = e.meta["idx"]
    x = nums[idx[other]]
    if e.family == "T1":
        op, c = e.meta["op"], nums[2]
        key = {"ADD": x + c, "SUB": x - c, "MUL": x * c, "DIV": Fraction(x, c)}[op]
        gold = [Action("CALC", op, idx[other], 2), Action("ANSWER", ptr_a=3)]
    else:
        c, d = nums[2], nums[3]
        key = x - c + d
        gold = [Action("CALC", "SUB", idx[other], 2), Action("CALC", "ADD", 4, 3), Action("ANSWER", ptr_a=5)]
    return Episode(e.family, e.question, nb2, gold, Fraction(key), {**e.meta, "colour": other})


_t1_from = _t2_from = _recompute


def corpus_texts(rng, n=150):
    """Sentences for the one-off TinyLM pretrain (a fixture, not the system under test)."""
    out = []
    for i in range(n):
        for fam in ("T1", "T2"):
            e = generate(rng, fam)
            out += [e.question, *e.notebook, f"= {e.key.numerator}" if e.key.denominator == 1
                    else f"= {e.key.numerator}/{e.key.denominator}", str(e.key.numerator) if e.key.denominator == 1
                    else f"{e.key.numerator}/{e.key.denominator}"]
        out.append(generate(rng, "T3")[0].question)
    return out
