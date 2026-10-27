"""Simulator-verified counterfactual triplets on the toy ladder, for the optional H1 objective (milestone 3).

Spec: design/research/final-sweep-2026-09-19/03-learning.md, "H1". Declared diagnostic: synthetic vocabulary,
supplied gold-evidence cards (privileged), single-token answers, fixed wording.

For one fixed question q* of a fresh visit (its FIRST 1-hop question "ENT_e REL_r?", whose four supplied cards are
A(e,r)*, A(e,r'), A(x,r), A(x,r')) three complete worlds are rendered with the same plan (every other draw
identical, so the three visits are token-aligned):

  x  the original world; q* answers a = value(e, r)
  u  an IRRELEVANT change, q* still answers a:
       decoy_swap   swap the values of two decoy cards (the word inventory is unchanged)
       decoy_value  give one decoy card a new value (not a, not its old value)
  v  a RELEVANT change, q* answers b != a; both kinds preserve the word inventory:
       subject_swap   swap the values of A(e,r) and A(x,r)   (same relation, other person)
       relation_swap  swap the values of A(e,r) and A(e,r')  (same person, other relation)

Every question of every sibling is re-rendered from its edited world by the generator and then checked against an
independent oracle (`verify`), as are the intended fact edits and, for swaps, the unchanged word inventory.

Roles, change kinds, q* indices and a/b are LOSS-SIDE METADATA (`TripletMeta`). They are never written into the
batch: visits of a minibatch are shuffled, and question ids carry only a neutral serial. Training triplets use
training visits, so no held-out 2-hop question is ever generated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Optional

import torch

from .toy_ladder import ANSWER, FIRST_FREE, LadderSpec, Line, World, assemble, visit

RELEVANT_KINDS = ("subject_swap", "relation_swap")
IRRELEVANT_KINDS = ("decoy_swap", "decoy_value")
VERSION = 1


@dataclass
class Triplet:
    x: list
    u: list
    v: list
    q_line: int                  # line index of q* (identical in the three visits)
    answer_a: int                # value index (not token id)
    answer_b: int
    kind_u: str
    kind_v: str
    changed_u: tuple             # (entity, relation) keys edited in u
    changed_v: tuple             # (entity, relation) keys edited in v
    worlds: tuple = field(repr=False, default=())


@dataclass(frozen=True)
class TripletMeta:
    """Loss-side metadata for one assembled minibatch. NEVER a model input."""
    x_q: torch.Tensor            # [T] question index of q* in the x visit
    u_q: torch.Tensor
    v_q: torch.Tensor
    a: torch.Tensor              # [T] token id of the original answer
    b: torch.Tensor              # [T] token id of the changed answer
    kind_u: tuple
    kind_v: tuple
    rows: torch.Tensor           # [T, 3] batch rows of (x, u, v): the visit permutation, for clustering/audit


def _key(spec: LadderSpec, line: Line) -> tuple:
    return line.tokens[1] - spec.vocab_size, line.tokens[2] - FIRST_FREE


def _swap(world: World, p: tuple, q: tuple) -> World:
    attr = dict(world.attr)
    attr[p], attr[q] = world.attr[q], world.attr[p]
    return World(list(world.ents), attr, dict(world.friend))


def _set(world: World, p: tuple, value: int) -> World:
    attr = dict(world.attr)
    attr[p] = value
    return World(list(world.ents), attr, dict(world.friend))


def oracle_answer(world: World, line: Line) -> int:
    """Independent answer rule (value index) for a rendered question line."""
    e, r = line.ents[0], line.relation
    return world.attr[(e, r)] if line.hops == 1 else world.attr[(world.friend[e], r)]


def make_triplet(spec: LadderSpec, rng: random.Random, edit_rng: random.Random, *, training: bool) -> Triplet:
    """One verified triplet from a fresh visit (visits whose drawn edit cannot change/keep the answer are
    redrawn: a 1-in-16 value collision)."""
    while True:
        lines, world, plan = visit(spec, rng, training=training)
        q_line = next(i for i, line in enumerate(lines) if line.question and line.hops == 1)
        question = lines[q_line]
        gold, same_person, same_relation, other = (_key(spec, lines[i]) for i in question.supplied)
        if gold != (question.ents[0], question.relation):
            raise AssertionError("supplied cards out of order")
        a = world.attr[gold]
        kind_v = edit_rng.choice(RELEVANT_KINDS)
        partner = same_relation if kind_v == "subject_swap" else same_person
        kind_u = edit_rng.choice(IRRELEVANT_KINDS)
        decoys = [same_person, same_relation, other]
        if world.attr[partner] == a:
            continue
        if kind_u == "decoy_swap":
            pairs = [(p, q) for i, p in enumerate(decoys) for q in decoys[i + 1:] if world.attr[p] != world.attr[q]]
            if not pairs:
                continue
            p, q = edit_rng.choice(pairs)
            world_u, changed_u = _swap(world, p, q), (p, q)
        else:
            d = edit_rng.choice(decoys)
            new = edit_rng.choice([value for value in range(spec.values) if value not in (world.attr[d], a)])
            world_u, changed_u = _set(world, d, new), (d,)
        world_v = _swap(world, gold, partner)
        u = visit(spec, rng, training=training, world=world_u, plan=plan)[0]
        v = visit(spec, rng, training=training, world=world_v, plan=plan)[0]
        triplet = Triplet(lines, u, v, q_line, a, world.attr[partner], kind_u, kind_v, changed_u, (gold, partner),
                          (world, world_u, world_v))
        verify(spec, triplet)
        return triplet


def _fact_lines(spec: LadderSpec, lines: list) -> dict:
    return {_key(spec, line): i for i, line in enumerate(lines)
            if not line.question and len(line.tokens) > 3 and line.tokens[2] != spec.link
            and FIRST_FREE <= line.tokens[2] < FIRST_FREE + spec.relations}


def verify(spec: LadderSpec, t: Triplet) -> None:
    """Raise AssertionError unless the triplet is exactly what its metadata says (independent oracle)."""
    x, u, v = t.x, t.u, t.v
    if not (len(x) == len(u) == len(v)):
        raise AssertionError("sibling line counts differ")
    for lines, world in zip((x, u, v), t.worlds):
        for line in lines:
            if line.question and line.answer != [spec.value(oracle_answer(world, line))]:
                raise AssertionError("a rendered answer disagrees with the oracle")
    qx, qu, qv = x[t.q_line], u[t.q_line], v[t.q_line]
    ask = lambda line: line.tokens[:line.tokens.index(ANSWER) + 1]     # through [answer]: identical wording
    if not (ask(qx) == ask(qu) == ask(qv)) or not (qx.supplied == qu.supplied == qv.supplied):
        raise AssertionError("q* wording or supplied cards differ between siblings")
    if not (qx.answer == qu.answer == [spec.value(t.answer_a)] and qv.answer == [spec.value(t.answer_b)]):
        raise AssertionError("q* answers do not follow the triplet roles")
    if t.answer_a == t.answer_b:
        raise AssertionError("relevant change kept the answer")
    facts = _fact_lines(spec, x)
    for sibling, changed in ((u, t.changed_u), (v, t.changed_v)):
        differ = {i for i, (p, q) in enumerate(zip(x, sibling)) if p.tokens != q.tokens and not p.question}
        if differ != {facts[key] for key in changed}:
            raise AssertionError("the edit touched other fact lines")
    inventory = lambda lines: sorted(tok for line in lines if not line.question for tok in line.tokens)
    if inventory(v) != inventory(x):
        raise AssertionError("relevant swap changed the word inventory")
    if t.kind_u == "decoy_swap" and inventory(u) != inventory(x):
        raise AssertionError("decoy swap changed the word inventory")


def assemble_triplets(spec: LadderSpec, triplets: list, rng: random.Random, *, prefix: str):
    """((batch, supplied, hops), TripletMeta): the 3T visits in a random row order, one ordinary ladder batch."""
    count = len(triplets)
    rows = [t.x for t in triplets] + [t.u for t in triplets] + [t.v for t in triplets]
    permutation = list(range(3 * count))
    rng.shuffle(permutation)                                   # row position carries no role
    batch, supplied, hops = assemble(spec, [rows[i] for i in permutation], prefix=prefix)
    where = {source: row for row, source in enumerate(permutation)}
    star = []
    for source in range(3 * count):
        row = where[source]
        index = ((batch.q_visit == row) & (batch.q_line == triplets[source % count].q_line)).nonzero()
        star.append(int(index[0]))
    star = torch.tensor(star).view(3, count)
    meta = TripletMeta(x_q=star[0], u_q=star[1], v_q=star[2],
                       a=torch.tensor([spec.value(t.answer_a) for t in triplets]),
                       b=torch.tensor([spec.value(t.answer_b) for t in triplets]),
                       kind_u=tuple(t.kind_u for t in triplets), kind_v=tuple(t.kind_v for t in triplets),
                       rows=torch.tensor([[where[i], where[count + i], where[2 * count + i]] for i in range(count)]))
    return (batch, supplied, hops), meta


def triplet_batches(spec: LadderSpec, seed: int, *, per_batch: int, training: bool, prefix: str = "triplets"):
    """Endless deterministic stream of (item, meta) minibatches of `per_batch` verified triplets."""
    rng, edit_rng, order_rng = random.Random(seed), random.Random(seed + 1), random.Random(seed + 2)
    serial = 0
    while True:
        triplets = [make_triplet(spec, rng, edit_rng, training=training) for _ in range(per_batch)]
        yield assemble_triplets(spec, triplets, order_rng, prefix=f"{prefix}-{seed}-{serial}")
        serial += 1


def shared_order(meta: TripletMeta, questions: int, generator: torch.Generator, width: int = 6) -> torch.Tensor:
    """[Q, width] supplied-card orders: random per question, but IDENTICAL for a triplet's three q* (and for
    corresponding questions of the three siblings), so siblings differ only by the edited facts."""
    order = torch.rand(questions, width, generator=generator).argsort(1)
    per_visit = questions // (3 * len(meta.a)) if len(meta.a) else 0
    if per_visit * 3 * len(meta.a) != questions:
        raise ValueError("questions are not 3T visits of equal question count")
    for t in range(len(meta.a)):
        rx, ru, rv = (int(r) for r in meta.rows[t])
        for k in range(per_visit):
            order[ru * per_visit + k] = order[rx * per_visit + k]
            order[rv * per_visit + k] = order[rx * per_visit + k]
    return order


__all__ = ["IRRELEVANT_KINDS", "RELEVANT_KINDS", "Triplet", "TripletMeta", "VERSION", "assemble_triplets",
           "make_triplet", "oracle_answer", "shared_order", "triplet_batches", "verify"]
