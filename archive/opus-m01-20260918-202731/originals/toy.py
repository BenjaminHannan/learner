"""The far-fact toy task of build step 4 (design/06 §8): facts, distractors, then questions whose fact lies
beyond the reader's attention reach, emitted directly as `premonition.batch.VisitBatch` objects.

A visit is
  1. `facts` fact lines "[world] ENT_e REL_r VAL_v f f\\n" over distinct (entity, relation) pairs, shuffled
     together with `distractors` filler lines "[world] f f f f\\n";
  2. a filler block of at least `gap` tokens (default 2 x the 64-token window: block-local attention reaches at
     most one block back, so no question token can attend to any fact token);
  3. `questions` question lines "[question] ENT_e REL_r [answer] VAL_v [feedback] f\\n", each asking a
     different fact. The facts nobody asks about are the distractor facts: they share entities, relations and
     values with the asked ones, so a fetch must match both the entity and the relation.

Values are uniform over `values` ids, so chance is 1 / values, and every visit states enough facts that most
values occur in it (a "guess a value seen in this visit" strategy stays near chance). Entities are drawn
per visit from the 16 ENT ids, which the collator would permute anyway: nothing but the visit ties an entity
to its values. The gold card of a question is its fact line (depth 1).
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterator, Optional

import torch

from .batch import MAX_ANSWER, MAX_GOLD, MAX_LINE_ENTS, N_ENT, PAD_ID, NameTable, VisitBatch

IGNORE = -100
PAD, BOS, EOS, WORLD, QUESTION, ANSWER, FEEDBACK, NEWLINE = range(8)
FIRST_FREE = 8


@dataclass(frozen=True)
class ToySpec:
    entities: int = 6            # distinct entities per visit (<= N_ENT)
    relations: int = 3
    values: int = 16
    fillers: int = 24
    facts: int = 12              # fact lines per visit, distinct (entity, relation) pairs
    questions: int = 4           # asked facts per visit (the rest are distractor facts)
    distractors: int = 4         # filler lines mixed into the fact block
    gap: int = 128               # minimum tokens from a fact line's end to its question's [answer]

    def __post_init__(self) -> None:
        if not 1 <= self.entities <= N_ENT:
            raise ValueError(f"entities must be in 1..{N_ENT}")
        if not 1 <= self.questions <= self.facts <= self.entities * self.relations:
            raise ValueError("need 1 <= questions <= facts <= entities x relations")
        if min(self.relations, self.values, self.fillers) < 1 or self.gap < 0 or self.distractors < 0:
            raise ValueError("relations, values and fillers must be positive; gap and distractors nonnegative")

    @property
    def vocab_size(self) -> int:
        """Tokenizer-like ids: 8 specials, relations, values, fillers; ENT e is vocab_size + e."""
        return FIRST_FREE + self.relations + self.values + self.fillers

    @property
    def chance(self) -> float:
        return 1.0 / self.values

    def relation(self, r: int) -> int:
        return FIRST_FREE + r

    def value(self, v: int) -> int:
        return FIRST_FREE + self.relations + v

    def filler(self, f: int) -> int:
        return FIRST_FREE + self.relations + self.values + f


@dataclass
class _Line:
    tokens: list[int]
    question: bool = False
    ents: tuple[int, ...] = ()
    answer: Optional[list[int]] = None      # question lines: the answer ids (without <eos>)
    gold: Optional[int] = None              # question lines: the fact's line index


def visit_lines(spec: ToySpec, rng: random.Random) -> list[_Line]:
    """One visit as lines (see the module docstring)."""
    base = spec.vocab_size
    ents = rng.sample(range(N_ENT), spec.entities)
    pairs = rng.sample([(e, r) for e in ents for r in range(spec.relations)], spec.facts)
    values = [rng.randrange(spec.values) for _ in pairs]

    def filler(count: int) -> list[int]:
        return [spec.filler(rng.randrange(spec.fillers)) for _ in range(count)]

    block: list[tuple[str, int]] = [("fact", i) for i in range(spec.facts)] + [("filler", -1)] * spec.distractors
    rng.shuffle(block)
    lines: list[_Line] = []
    where: dict[int, int] = {}
    for kind, index in block:
        if kind == "fact":
            (e, r), v = pairs[index], values[index]
            where[index] = len(lines)
            lines.append(_Line([WORLD, base + e, spec.relation(r), spec.value(v)] + filler(rng.randint(0, 2))
                               + [NEWLINE], ents=(e,)))
        else:
            lines.append(_Line([WORLD] + filler(rng.randint(3, 6)) + [NEWLINE]))
    gap = 0
    while gap < spec.gap:
        line = [WORLD] + filler(rng.randint(4, 8)) + [NEWLINE]
        lines.append(_Line(line))
        gap += len(line)
    for index in rng.sample(range(spec.facts), spec.questions):
        (e, r), v = pairs[index], values[index]
        ask = [QUESTION, base + e, spec.relation(r), ANSWER]
        lines.append(_Line(ask + [spec.value(v), FEEDBACK] + filler(1) + [NEWLINE], question=True, ents=(e,),
                           answer=[spec.value(v)], gold=where[index]))
    return lines


def make_batch(spec: ToySpec, visits: int, rng: random.Random, *, prefix: str = "toy") -> VisitBatch:
    """`visits` fresh toy visits as one `VisitBatch` (questions flattened in visit order)."""
    rows = [visit_lines(spec, rng) for _ in range(visits)]
    sizes = [sum(len(line.tokens) for line in lines) for lines in rows]
    width, height = max(sizes), max(len(lines) for lines in rows)
    tokens = torch.full((visits, width), PAD_ID, dtype=torch.long)
    line_of = torch.full((visits, width), -1, dtype=torch.long)
    card_end = torch.zeros(visits, width, dtype=torch.bool)
    lm_mask = torch.zeros(visits, width, dtype=torch.bool)
    line_is_question = torch.zeros(visits, height, dtype=torch.bool)
    line_start = torch.full((visits, height), -1, dtype=torch.long)
    line_ents = torch.full((visits, height, MAX_LINE_ENTS), -1, dtype=torch.long)
    q_visit, q_line, q_span, answers, gold = [], [], [], [], []
    names = []
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
                # position i predicts i + 1: the answer tokens are never L_lm targets
                lm_mask[row, end - 1:end - 1 + len(line.answer)] = False
                q_visit.append(row)
                q_line.append(k)
                q_span.append((position, end))
                answers.append(line.answer + [EOS])
                gold.append(line.gold)
            else:
                card_end[row, position + n - 1] = True
            position += n
        lm_mask[row, position - 1:] = False
        names.append(NameTable({e: f"Ent{e}" for e in range(N_ENT)}))
    count = len(q_visit)
    answer = torch.full((count, MAX_ANSWER), IGNORE, dtype=torch.long)
    gold_lines = torch.full((count, MAX_GOLD), -1, dtype=torch.long)
    for i, (ids, line) in enumerate(zip(answers, gold)):
        answer[i, :len(ids)] = torch.tensor(ids)
        gold_lines[i, 0] = line
    serial = rng.randrange(1 << 30)
    return VisitBatch(
        tokens=tokens, line_of=line_of, card_end=card_end, lengths=torch.tensor(sizes), lm_mask=lm_mask,
        line_is_question=line_is_question, line_start=line_start, line_ents=line_ents,
        q_visit=torch.tensor(q_visit, dtype=torch.long), q_line=torch.tensor(q_line, dtype=torch.long),
        q_span=torch.tensor(q_span, dtype=torch.long).view(count, 2), answer=answer, gold_lines=gold_lines,
        depth=torch.ones(count, dtype=torch.long),
        question_ids=[f"{prefix}-{serial}-{i}" for i in range(count)], names=names,
        slices={"far": torch.ones(count, dtype=torch.bool)})


def toy_stream(spec: ToySpec, visits: int, seed: int) -> Iterator[VisitBatch]:
    """Endless fresh batches (never repeating a visit in practice)."""
    rng = random.Random(seed)
    while True:
        yield make_batch(spec, visits, rng)


def toy_set(spec: ToySpec, batches: int, visits: int, seed: int) -> list[VisitBatch]:
    """A fixed evaluation set."""
    rng = random.Random(seed)
    return [make_batch(spec, visits, rng, prefix=f"toy-eval{seed}") for _ in range(batches)]


def min_distance(batch: VisitBatch) -> int:
    """The smallest token distance from a question's [answer] back to the last token of its gold line."""
    worst = None
    for q in range(batch.q_visit.shape[0]):
        visit, line = int(batch.q_visit[q]), int(batch.gold_lines[q, 0])
        end_of_fact = int(batch.line_start[visit, line + 1]) - 1
        distance = int(batch.q_span[q, 1]) - 1 - end_of_fact
        worst = distance if worst is None else min(worst, distance)
    return worst if worst is not None else 0


__all__ = ["ToySpec", "make_batch", "min_distance", "toy_set", "toy_stream", "visit_lines"]
