"""The read / choose / combine ladder (overnight run ovn-20260918-235851): a far-fact toy whose questions need one
fact (1-hop) or two facts joined by a link (2-hop), with the evidence cards SUPPLIED per question.

A visit is
  1. a fact block, shuffled: for each of `entities` people and each of `relations` attributes, an attribute
     line "[world] ENT_e REL_r VAL_v f?\\n"; for each person one link line "[world] ENT_a LINK ENT_b f?\\n"
     (b = a's friend, a random other person); `distractors` filler lines;
  2. a filler block of at least `gap` tokens (beyond the reader's 64-token attention window);
  3. questions (label-free once `train.label_free` runs):
       1-hop  "[question] ENT_e REL_r [answer] VAL [feedback] f\\n"         -> the value of (e, r)
       2-hop  "[question] ENT_a LINK REL_r [answer] VAL [feedback] f\\n"    -> the value of (friend(a), r)

Supplied cards (a privileged gold-evidence diagnostic; order shuffled by the caller). The distractors MIRROR the
evidence, so the question's own person is the only thing that tells the right card from a decoy:
  1-hop (e, r):  A(e, r)*, A(e, r'), A(x, r), A(x, r')                      x != e, r' != r          (4 cards)
  2-hop (a, r):  L(a)*, A(b, r)*, A(a, r),  L(c), A(d, r), A(c, r)          b = friend(a); c, d = friend(c)
                 are both outside {a, b}                                                            (6 cards)
Any rule that ignores the question's person (relation match, "object of a link", "entity not asked about", link
structure) leaves two symmetric candidates, so it scores at most about 50%; matching only the person gives the
1-hop answer A(a, r), which is wrong for a 2-hop question. Ceilings are measured on the frozen validation split.
Worlds are re-drawn until every person a has such a c. Reading level: the gold cards only.

Values are uniform over `values` ids (chance 1 / values). In TRAINING visits no 2-hop question uses the held-out
relation, so held-out 2-hop questions are familiar operations (the link, and that attribute via 1-hop questions) in
an unseen combination.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Optional

import torch

from .batch import MAX_ANSWER, MAX_GOLD, MAX_LINE_ENTS, N_ENT, PAD_ID, NameTable, VisitBatch

IGNORE = -100
PAD, BOS, EOS, WORLD, QUESTION, ANSWER, FEEDBACK, NEWLINE = range(8)
FIRST_FREE = 8
SUPPLIED = 6


@dataclass(frozen=True)
class LadderSpec:
    entities: int = 6
    relations: int = 3
    values: int = 16
    fillers: int = 24
    distractors: int = 4
    gap: int = 128
    one_hop: int = 2
    two_hop: int = 2
    heldout_relation: int = 2

    @property
    def link(self) -> int:
        return FIRST_FREE + self.relations

    @property
    def vocab_size(self) -> int:
        return FIRST_FREE + self.relations + 1 + self.values + self.fillers

    def relation(self, r: int) -> int:
        return FIRST_FREE + r

    def value(self, v: int) -> int:
        return FIRST_FREE + self.relations + 1 + v

    def filler(self, f: int) -> int:
        return FIRST_FREE + self.relations + 1 + self.values + f

    @property
    def chance(self) -> float:
        return 1.0 / self.values


@dataclass
class Line:
    tokens: list
    question: bool = False
    ents: tuple = ()
    answer: Optional[list] = None
    gold: tuple = ()               # question lines: evidence line indices
    supplied: tuple = ()           # question lines: the supplied card lines (gold first, unshuffled)
    hops: int = 0
    relation: int = -1


@dataclass
class World:
    ents: list
    attr: dict                      # (e, r) -> value index
    friend: dict                    # e -> e'


def visit(spec: LadderSpec, rng: random.Random, *, training: bool, world: Optional[World] = None,
          plan: Optional[list] = None) -> tuple[list, World, list]:
    """(lines, world, plan). `world`/`plan` replay a visit with edited facts (the plan fixes every other draw)."""
    replay = plan is not None
    draws = iter(plan) if replay else None
    record: list = []

    def draw(fn):
        value = next(draws) if replay else fn()
        if not replay:
            record.append(value)
        return value

    if world is None:
        ents = rng.sample(range(N_ENT), spec.entities)
        attr = {(e, r): rng.randrange(spec.values) for e in ents for r in range(spec.relations)}
        while True:
            friend = {e: rng.choice([x for x in ents if x != e]) for e in ents}
            if all(any(x not in (a, friend[a]) and friend[x] not in (a, friend[a]) for x in ents) for a in ents):
                break
        world = World(ents, attr, friend)
    ents, attr, friend = world.ents, world.attr, world.friend
    fillers = lambda n: [spec.filler(draw(lambda: rng.randrange(spec.fillers))) for _ in range(n)]
    block = [("attr", e, r) for e in ents for r in range(spec.relations)] + [("link", e, -1) for e in ents] \
        + [("filler", -1, -1)] * spec.distractors
    order = draw(lambda: rng.sample(range(len(block)), len(block)))
    lines: list = []
    where: dict = {}
    for index in order:
        kind, e, r = block[index]
        if kind == "attr":
            where[("attr", e, r)] = len(lines)
            lines.append(Line([WORLD, spec.vocab_size + e, spec.relation(r), spec.value(attr[(e, r)])]
                              + fillers(draw(lambda: rng.randint(0, 2))) + [NEWLINE], ents=(e,)))
        elif kind == "link":
            where[("link", e)] = len(lines)
            lines.append(Line([WORLD, spec.vocab_size + e, spec.link, spec.vocab_size + friend[e]]
                              + fillers(draw(lambda: rng.randint(0, 2))) + [NEWLINE], ents=(e, friend[e])))
        else:
            lines.append(Line([WORLD] + fillers(draw(lambda: rng.randint(3, 6))) + [NEWLINE]))
    gap = 0
    while gap < spec.gap:
        line = [WORLD] + fillers(draw(lambda: rng.randint(4, 8))) + [NEWLINE]
        lines.append(Line(line))
        gap += len(line)
    two_rel = [r for r in range(spec.relations) if not (training and r == spec.heldout_relation)]
    asked = set()
    questions = []
    for hops in [1] * spec.one_hop + [2] * spec.two_hop:
        while True:
            e = draw(lambda: rng.choice(ents))
            r = draw(lambda: rng.choice(range(spec.relations) if hops == 1 else two_rel))
            if (hops, e, r) not in asked:
                asked.add((hops, e, r))
                break
        if hops == 1:
            r2 = draw(lambda: rng.choice([x for x in range(spec.relations) if x != r]))
            x = draw(lambda: rng.choice([y for y in ents if y != e]))
            gold = (where[("attr", e, r)],)
            supplied = gold + (where[("attr", e, r2)], where[("attr", x, r)], where[("attr", x, r2)])
            value = attr[(e, r)]
            ask = [QUESTION, spec.vocab_size + e, spec.relation(r), ANSWER]
        else:
            b = friend[e]
            c = draw(lambda: rng.choice([y for y in ents if y not in (e, b) and friend[y] not in (e, b)]))
            gold = (where[("link", e)], where[("attr", b, r)])
            supplied = gold + (where[("attr", e, r)], where[("link", c)], where[("attr", friend[c], r)],
                               where[("attr", c, r)])
            value = attr[(b, r)]
            ask = [QUESTION, spec.vocab_size + e, spec.link, spec.relation(r), ANSWER]
        questions.append(Line(ask + [spec.value(value), FEEDBACK] + fillers(1) + [NEWLINE], question=True,
                              ents=(e,), answer=[spec.value(value)], gold=gold, supplied=supplied, hops=hops,
                              relation=r))
    lines.extend(questions)
    return lines, world, record


def assemble(spec: LadderSpec, rows: list, *, prefix: str) -> tuple[VisitBatch, torch.Tensor, torch.Tensor]:
    """(batch, supplied [Q, 6] line indices with gold first and -1 padding, hops [Q]) for visits given as lines."""
    sizes = [sum(len(line.tokens) for line in lines) for lines in rows]
    width, height = max(sizes), max(len(lines) for lines in rows)
    visits = len(rows)
    tokens = torch.full((visits, width), PAD_ID, dtype=torch.long)
    line_of = torch.full((visits, width), -1, dtype=torch.long)
    card_end = torch.zeros(visits, width, dtype=torch.bool)
    lm_mask = torch.zeros(visits, width, dtype=torch.bool)
    line_is_question = torch.zeros(visits, height, dtype=torch.bool)
    line_start = torch.full((visits, height), -1, dtype=torch.long)
    line_ents = torch.full((visits, height, MAX_LINE_ENTS), -1, dtype=torch.long)
    q_visit, q_line, q_span, answers, golds, supplied, hops, heldout, relation = [], [], [], [], [], [], [], [], []
    for row, lines in enumerate(rows):
        position = 0
        for k, line in enumerate(lines):
            n = len(line.tokens)
            tokens[row, position:position + n] = torch.tensor(line.tokens)
            line_of[row, position:position + n] = k
            line_start[row, k] = position
            line_is_question[row, k] = line.question
            if line.ents:
                line_ents[row, k, :len(line.ents)] = torch.tensor(line.ents)
            lm_mask[row, position:position + n] = True
            if line.question:
                end = position + line.tokens.index(ANSWER) + 1
                lm_mask[row, end - 1:end - 1 + len(line.answer)] = False
                q_visit.append(row)
                q_line.append(k)
                q_span.append((position, end))
                answers.append(line.answer + [EOS])
                golds.append(line.gold)
                supplied.append(line.supplied)
                hops.append(line.hops)
                heldout.append(line.hops == 2 and line.relation == spec.heldout_relation)
                relation.append(line.relation)
            else:
                card_end[row, position + n - 1] = True
            position += n
        lm_mask[row, position - 1:] = False
    count = len(q_visit)
    answer = torch.full((count, MAX_ANSWER), IGNORE, dtype=torch.long)
    gold_lines = torch.full((count, MAX_GOLD), -1, dtype=torch.long)
    for i, (ids, gold) in enumerate(zip(answers, golds)):
        answer[i, :len(ids)] = torch.tensor(ids)
        gold_lines[i, :len(gold)] = torch.tensor(gold)
    hop = torch.tensor(hops, dtype=torch.long)
    batch = VisitBatch(
        tokens=tokens, line_of=line_of, card_end=card_end, lengths=torch.tensor(sizes), lm_mask=lm_mask,
        line_is_question=line_is_question, line_start=line_start, line_ents=line_ents,
        q_visit=torch.tensor(q_visit, dtype=torch.long), q_line=torch.tensor(q_line, dtype=torch.long),
        q_span=torch.tensor(q_span, dtype=torch.long).view(count, 2), answer=answer, gold_lines=gold_lines,
        depth=hop.clone(), question_ids=[f"{prefix}-{i}" for i in range(count)],
        names=[NameTable({e: f"Ent{e}" for e in range(N_ENT)}) for _ in rows],
        slices={"two_hop": hop == 2, "heldout": torch.tensor(heldout, dtype=torch.bool),
                **{f"relation{r}": torch.tensor([x == r for x in relation]) for r in range(spec.relations)}})
    padded = torch.full((count, SUPPLIED), -1, dtype=torch.long)
    for i, lines in enumerate(supplied):
        padded[i, :len(lines)] = torch.tensor(lines)
    return batch, padded, hop


def make(spec: LadderSpec, visits: int, rng: random.Random, *, training: bool, prefix: str = "ladder"):
    rows = [visit(spec, rng, training=training)[0] for _ in range(visits)]
    serial = rng.randrange(1 << 30)
    return assemble(spec, rows, prefix=f"{prefix}-{serial}")


__all__ = ["LadderSpec", "Line", "SUPPLIED", "World", "assemble", "make", "visit"]
