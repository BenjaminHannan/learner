"""Shared eight-record training and a stateless canonical-query executor.

Only the evaluator/training adapter parses facts. The executor consumes visible
question tokens and never receives an answer, evidence line or parsed story.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import premonition_token_evidence as E
import premonition_token_initialization_probe as I

T, data, torch = E.T, E.data, E.torch
QUESTION, ANSWER, WORLD, LINK = 4, 5, 3, 11
ENTITY_MIN, ENTITY_MAX = 52, 68


class CanonicalOperator(T.TokenMemoryReasoner):
    """Naming-only subclass: original forward and state-dict schema unchanged."""


def new_model(seed):
    torch.manual_seed(seed)
    model = CanonicalOperator()
    I.rescale(model)
    return model


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def visible_signature(memory, question):
    """Ignore order/filler, retain exact entity identities, facts and query."""
    facts = sorted(tuple(row[:4]) for row in memory
                   if len(row) >= 4 and row[0] == WORLD
                   and ENTITY_MIN <= row[1] < ENTITY_MAX and 8 <= row[2] <= LINK)
    return digest([facts, [t for t in question if t]])


def tensor_signature(memory, question):
    return digest([[list(filter(None, r)) for r in memory if any(r)],
                   list(filter(None, question))])


@dataclass
class TrainingBatch:
    canonical: data.Inputs
    canonical_targets: E.Targets
    monolithic: data.Inputs
    monolithic_targets: E.Targets
    accounting: dict


def training_batch(rng, visits=16, forbidden=frozenset()):
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    memories = []
    c, m = (dict(q=[], owner=[], where=[], answer=[], evidence=[]) for _ in range(2))
    kinds = dict(one_hop=0, link=0, terminal=0, monolithic=0)
    checked = 0

    def add(dst, q, owner, where, answer, evidence, kind):
        nonlocal checked
        if forbidden and visible_signature(memories[owner], q) in forbidden:
            raise RuntimeError("training/validation semantic overlap; run invalid")
        checked += 1
        for key, val in zip(dst, (q, owner, where, answer, evidence)):
            dst[key].append(val)
        kinds[kind] += 1

    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        memories.append([[] if row.question else list(row.tokens) for row in rows])
        questions = [(j, row) for j, row in enumerate(rows) if row.question]
        assert len(questions) == 4
        for j, row in questions:
            q = row.tokens[:row.tokens.index(ANSWER)+1]
            assert row.hops in (1, 2)
            assert not (row.hops == 2 and row.relation == spec.heldout_relation)
            if row.hops == 1:
                assert len(q) == 4
                add(c, q, v, j, row.answer[0], [row.gold[0]]*3, "one_hop")
            else:
                assert len(q) == 5 and q[2] == LINK and q[3] in (8, 9)
                link_line, endpoint_line = row.gold
                entity = rows[link_line].tokens[3]
                assert ENTITY_MIN <= entity < ENTITY_MAX
                assert rows[link_line].tokens[:3] == [WORLD, q[1], LINK]
                assert rows[endpoint_line].tokens[:3] == [WORLD, entity, q[3]]
                add(c, [QUESTION, q[1], LINK, ANSWER], v, j, entity, [link_line]*3, "link")
                add(c, [QUESTION, entity, q[3], ANSWER], v, j, row.answer[0],
                    [endpoint_line]*3, "terminal")
                add(m, q, v, j, row.answer[0], [link_line, endpoint_line, endpoint_line], "monolithic")
    rng.randrange(1 << 30)

    def pack(d):
        return (data.pack(memories, d['q'], d['owner'], d['where']),
                E.Targets(torch.tensor(d['answer']), torch.tensor(d['evidence'])))

    cx, cy = pack(c)
    mx, my = pack(m)
    assert cx.questions.shape == (6*visits, 4)
    assert mx.questions.shape == (2*visits, 5)
    assert kinds == dict.fromkeys(kinds, 2*visits)
    return TrainingBatch(cx, cy, mx, my, dict(visits=visits, records=checked, kinds=kinds,
        heldout_compositions=0, three_hop=0, twelve_person=0,
        overlap_checks=checked if forbidden else 0))


def training_step(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = .001 * min(1., (step+1)/100)
    optimizer.zero_grad(set_to_none=True)
    # Separate four/five-token batches keep every canonical query width four.
    # Sum the gradients of the exact eight-record mean before one optimizer step.
    for x, y, weight in ((batch.canonical, batch.canonical_targets, .75),
                          (batch.monolithic, batch.monolithic_targets, .25)):
        loss = E.loss_for(model, x, y)[0] * weight
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not bool(torch.isfinite(norm)):
        raise RuntimeError("nonfinite gradient")
    optimizer.step()
    # Deliberately return no loss/accuracy, including during the timing rehearsal.


def training_flops(batch, model):
    return sum(T.training_flops(x, model) for x in (batch.canonical, batch.monolithic))


def inference_flops(inputs, model):
    # Original hand count is exactly three times forward-only matmul FLOPs.
    return T.training_flops(inputs, model) // 3


def select(inputs, indices, questions=None):
    ix = torch.as_tensor(indices, dtype=torch.long)
    return data.Inputs(inputs.memory, inputs.questions[ix] if questions is None else questions,
                       inputs.owner[ix], inputs.eligible[ix])


def canonical_input(inputs, entities, operations, indices=None):
    if indices is None:
        indices = list(range(len(entities)))
    q = torch.tensor([[QUESTION, int(e), int(op), ANSWER] for e, op in zip(entities, operations)],
                     dtype=torch.long)
    return select(inputs, indices, q)


@torch.no_grad()
def execute(model, inputs, observer=None):
    """Generic visible-path executor. Returned traces are never fed into a call."""
    programs = []
    for q in inputs.questions.tolist():
        q = [t for t in q if t]
        if len(q) < 4 or q[0] != QUESTION or q[-1] != ANSWER or not ENTITY_MIN <= q[1] < ENTITY_MAX:
            raise ValueError("malformed question")
        programs.append((q[1], q[2:-1]))
    n = len(programs)
    predictions, emitted = [-1]*n, [[] for _ in range(n)]
    active, entities = list(range(n)), [p[0] for p in programs]
    calls, batches, flops, depth = 0, 0, 0, 0
    while active:
        ops = [programs[i][1][depth] for i in active]
        x = canonical_input(inputs, entities, ops, active)
        logits = model(x)
        if observer is not None:
            observer(x, logits)
        pred = logits.argmax(-1).tolist()
        calls += len(active)
        batches += 1
        flops += inference_flops(x, model)
        following, next_entities = [], []
        for i, token in zip(active, pred):
            emitted[i].append(token)
            if depth+1 == len(programs[i][1]):
                predictions[i] = token
            elif ENTITY_MIN <= token < ENTITY_MAX:
                following.append(i)
                next_entities.append(token)
            # Early non-entity output leaves prediction -1. No replacement.
        active, entities = following, next_entities
        depth += 1
    return dict(predictions=predictions, emitted=emitted, calls=calls, batches=batches, flops=flops)


def truth_paths(inputs):
    """Evaluator-only interpreter of eligible visible facts; no model invoked."""
    memory = inputs.memory.tolist()
    result = []
    for owner, valid, raw in zip(inputs.owner.tolist(), inputs.eligible.tolist(), inputs.questions.tolist()):
        facts = {}
        for row, allowed in zip(memory[owner], valid):
            if allowed and len(row) >= 4 and row[0] == WORLD and ENTITY_MIN <= row[1] < ENTITY_MAX:
                if 8 <= row[2] <= LINK:
                    key = (row[1], row[2])
                    if key in facts:
                        raise ValueError("duplicate semantic fact")
                    facts[key] = row[3]
        q = [t for t in raw if t]
        x, stages = q[1], []
        for op in q[2:-1]:
            y = facts[(x, op)]
            stages.append(dict(entity=x, operation=op, target=y))
            x = y
        result.append(stages)
    return result


@torch.no_grad()
def oracle_inputs(model, inputs, paths):
    outputs = [[] for _ in paths]
    calls = batches = flops = 0
    for depth in range(max(map(len, paths))):
        ids = [i for i, p in enumerate(paths) if depth < len(p)]
        x = canonical_input(inputs, [paths[i][depth]['entity'] for i in ids],
                             [paths[i][depth]['operation'] for i in ids], ids)
        pred = model(x).argmax(-1).tolist()
        calls += len(ids)
        batches += 1
        flops += inference_flops(x, model)
        for i, token in zip(ids, pred):
            outputs[i].append(token)
    return dict(predictions=outputs, calls=calls, batches=batches, flops=flops)
