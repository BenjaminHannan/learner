"""Dispatcher v3: train through three hops, test four through eight.

Motivation.  v1/v2 trained the 15,522-parameter pointer/copy dispatcher on 1- and
2-hop questions.  Every seed reached 64/64 on 1-hop, practised 2-hop and held-out
2-hop, and every seed failed 3-hop -- including a supervised-action ceiling arm,
which after two correct calls selected a transcript RESULT as its third OPERATION.
On minimal 1-2-hop executions "use the FIRST intermediate result" and "use the
LATEST intermediate result" are indistinguishable, so that training stream cannot
teach the right rule.  v3 trains through k = 3 and evaluates k = 1..8 in worlds
with enough people that the two rules disagree.

WRAPPED FROM v1/v2 (imported, never edited, never monkey-patched)
  V1.Dispatcher                the model itself, unchanged (the ablations below are
                               FEATURE-level, so no parameter changes)
  V1.FrozenOperator / V1.OracleOperator / V1.make_operator / V1.direct_call
  V1.fact_table / V1.walk      the exact interpreter (one of the two used in audits)
  V1.rloo_advantage, V1.pad_questions, V1.representatives, V1.configure,
  V1.sha, V1.write_new, V1.fingerprint, V1.OP_INDEX
  V2.shaped_signal             the --call-cost learning signal, carried over unchanged

COPIED AND CHANGED (and only these)
  candidate_features -> `candidate_features_v3`
      v1 hard-codes MAX_CALLS = 4 as the number of result slots.  v3 takes `cap`,
      and adds the two ablation switches (`no_recent`, `no_offsets`).
  rollout            -> `rollout_v3`
      v1 hard-codes MAX_CALLS = 4 as the result-tensor width, the loop bound and the
      write slot.  v3 takes `cap`, and its `policy` callback may force a component
      on a PER-ROW basis (v1's forced `subject`/`operation`/`stop` were whole-batch),
      which is what fixes the v2 `force_subject` artefact described under `diagnose`.
  train              -> `train`     (new world/question stream, caps, ablations)
  score              -> `score`     (new panels, eval cap, strict path, diagnosis)

CAPS WITHOUT RETRAINING.  The primary (relative-offset) model has no per-slot
parameter: a result candidate's features are its token, a source flag, an "is most
recent" flag and two relative offsets that are the N/A slot for every result.  So a
model trained at cap 4 can be evaluated at cap 16 simply by widening the result
tensor; the unused slots are marked not-present and their logits are -inf.
`tests/test_fable_dispatcher_v3.py` checks that the step-1..4 logits are bitwise
identical under cap 4 and cap 16.  The `--absolute-positions` ablation DOES have a
per-slot embedding (`ABSOLUTE_SLOTS = 16`); for it v3 clamps the slot index exactly
as v1 does, so result slots beyond the 12th collide.  That is stated in the score
output as `absolute_position_slots_clamped`.

Everything written here is additive and lives under its own --out directory.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, field
import json
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v2 as V2                                            # noqa: E402

A = V1.A
torch = V1.torch
nn = V1.nn

sha = V1.sha
write_new = V1.write_new
fingerprint = V1.fingerprint
configure = V1.configure
fact_table = V1.fact_table
walk = V1.walk
Dispatcher = V1.Dispatcher
FrozenOperator = V1.FrozenOperator
OracleOperator = V1.OracleOperator
make_operator = V1.make_operator
rloo_advantage = V1.rloo_advantage
pad_questions = V1.pad_questions
representatives = V1.representatives
shaped_signal = V2.shaped_signal

QUESTION, ANSWER, WORLD, LINK = V1.QUESTION, V1.ANSWER, V1.WORLD, V1.LINK
ENTITY_MIN, ENTITY_MAX = V1.ENTITY_MIN, V1.ENTITY_MAX
OPS, VOCAB = V1.OPS, V1.VOCAB
OFFSET_CLIP, OFFSET_NA, OFFSET_SLOTS = V1.OFFSET_CLIP, V1.OFFSET_NA, V1.OFFSET_SLOTS
ABSOLUTE_SLOTS = V1.ABSOLUTE_SLOTS

# the visible token grammar of premonition.toy_ladder (LadderSpec defaults), which is
# the grammar the frozen operator was trained on
NEWLINE = 7
FIRST_REL, RELATIONS, VALUES, FILLERS = 8, 3, 16, 24
VOCAB_SIZE, N_ENT = 52, 16
HELDOUT_REL = FIRST_REL + 2                      # 10
PRACTISED_RELS = (FIRST_REL, FIRST_REL + 1)      # 8, 9
BASE_DISTRACTORS, BASE_GAP = 4, 128

PANEL_NAMESPACE = 'fable-dispatcher-v3-panel'
TRAIN_NAMESPACE = 'fable-dispatcher-v3-train'
PANEL_N = 64
PANEL_PEOPLE = 16
TRAIN_PEOPLE = 6
TRAIN_HOPS = (1, 2, 3)
QUESTIONS_PER_WORLD = 4
TRAIN_CAP = 4
EVAL_CAP = 16
PAIR_HOPS = 5
CELL_MARK = 58                                   # the "drops below" threshold of the report


def _single_cells():
    cells = {}
    for k in range(1, 9):
        cells[f'k{k}-prac'] = dict(kind='single', hops=k, people=PANEL_PEOPLE, terminal='practised',
                                   edit=None, invariant=False, distinct=True,
                                   title=f'{k}-hop, practised terminal relation, 16 people')
        cells[f'k{k}-held'] = dict(kind='single', hops=k, people=PANEL_PEOPLE, terminal='heldout',
                                   edit=None, invariant=False, distinct=True,
                                   title=f'{k}-hop, held-out terminal relation 10, 16 people')
    for k in range(1, 4):
        cells[f'p6-k{k}-prac'] = dict(kind='single', hops=k, people=TRAIN_PEOPLE,
                                      terminal='practised', edit=None, invariant=False,
                                      distinct=True,
                                      title=f'{k}-hop, practised terminal, 6 people (trained regime)')
        cells[f'p6-k{k}-held'] = dict(kind='single', hops=k, people=TRAIN_PEOPLE,
                                      terminal='heldout', edit=None, invariant=False, distinct=True,
                                      title=f'{k}-hop, held-out terminal, 6 people (trained regime)')
    return cells


CELLS = dict(_single_cells())
CELLS['pair-link'] = dict(kind='pair', hops=PAIR_HOPS, people=PANEL_PEOPLE, terminal='heldout',
                          edit='link', invariant=False, distinct=True,
                          title='5-hop held-out changed-link twin pair, 16 people')
CELLS['pair-value'] = dict(kind='pair', hops=PAIR_HOPS, people=PANEL_PEOPLE, terminal='heldout',
                           edit='value', invariant=False, distinct=True,
                           title='5-hop held-out changed-endpoint-value twin pair, 16 people')
CELLS['pair-irrelevant'] = dict(kind='pair', hops=PAIR_HOPS, people=PANEL_PEOPLE,
                                terminal='heldout', edit='irrelevant', invariant=True,
                                distinct=True,
                                title='5-hop held-out irrelevant-edit twin pair, 16 people')

# the order the report prints
CELL_ORDER = ([f'k{k}-{t}' for k in range(1, 9) for t in ('prac', 'held')]
              + [f'p6-k{k}-{t}' for k in range(1, 4) for t in ('prac', 'held')]
              + ['pair-link', 'pair-value', 'pair-irrelevant'])
assert sorted(CELL_ORDER) == sorted(CELLS)


# --------------------------------------------------------------------------- worlds


@dataclass
class World:
    """A world of `people` people plus the FIXED LAYOUT of its visible rows.

    Separating the layout from the facts is what makes a twin pair exact: an edited
    world re-renders through the same layout, so the only tokens that can differ are
    the fact tokens the edit moved.  (v1 achieved the same by replaying
    `toy_ladder.visit` with a recorded plan; that generator cannot make 16-person
    worlds or chains longer than three hops, so v3 renders its own rows in the same
    grammar -- see `render`.)
    """
    ents: list
    attr: dict                      # (entity token, relation token) -> value token
    friend: dict                    # entity token -> entity token, exactly one per person
    layout: list = field(default_factory=list)


def build_world(rng, people):
    """A world in the exact visible token format the frozen operator was trained on.

    Fact rows are `[3, entity, relation_or_LINK, value_or_entity] + fillers + [newline]`.
    Every person gets one attribute row per relation 8/9/10 and exactly one LINK row.
    Filler and gap rows carry no entity token, so they are semantically inert.
    """
    if not 2 <= people <= N_ENT:
        raise ValueError(f'people must be between 2 and {N_ENT}')
    ents = [VOCAB_SIZE + e for e in rng.sample(range(N_ENT), people)]
    attr = {(e, FIRST_REL + r): FIRST_REL + RELATIONS + 1 + rng.randrange(VALUES)
            for e in ents for r in range(RELATIONS)}
    friend = {e: rng.choice([x for x in ents if x != e]) for e in ents}
    block = ([('attr', e, FIRST_REL + r) for e in ents for r in range(RELATIONS)]
             + [('link', e, None) for e in ents]
             + [('filler', None, None)] * BASE_DISTRACTORS)
    order = rng.sample(range(len(block)), len(block))
    fill = lambda n: [FIRST_REL + RELATIONS + 1 + VALUES + rng.randrange(FILLERS) for _ in range(n)]
    layout = []
    for index in order:
        kind, e, r = block[index]
        layout.append((kind, e, r, fill(rng.randint(0, 2) if kind != 'filler'
                                       else rng.randint(3, 6))))
    gap = 0
    while gap < BASE_GAP:
        tokens = fill(rng.randint(4, 8))
        layout.append(('filler', None, None, tokens))
        gap += len(tokens) + 2
    return World(ents=ents, attr=attr, friend=friend, layout=layout)


def render(world):
    """The world's visible memory rows, in layout order."""
    rows = []
    for kind, e, r, fillers in world.layout:
        if kind == 'attr':
            rows.append([WORLD, e, r, world.attr[(e, r)]] + list(fillers) + [NEWLINE])
        elif kind == 'link':
            rows.append([WORLD, e, LINK, world.friend[e]] + list(fillers) + [NEWLINE])
        else:
            rows.append([WORLD] + list(fillers) + [NEWLINE])
    return rows


def chain_people(friend, asker, hops):
    """The `hops` people a k-hop question walks: asker, f(asker), ..., f^(k-1)(asker)."""
    people = [asker]
    for _ in range(hops - 1):
        people.append(friend[people[-1]])
    return people


def distinct_askers(world, hops):
    """People whose k-person chain is PAIRWISE DISTINCT (possible whenever N >= k)."""
    return [a for a in world.ents if len(set(chain_people(world.friend, a, hops))) == hops]


def question_tokens(asker, hops, terminal):
    """A k-hop raw question: k-1 LINKs then a terminal attribute relation."""
    return [QUESTION, asker] + [LINK] * (hops - 1) + [terminal, ANSWER]


def true_chain(world, asker, hops, terminal):
    """The (subject, operation, result) chain, straight from the world's facts."""
    people = chain_people(world.friend, asker, hops)
    chain = [[people[i], LINK, people[i + 1]] for i in range(hops - 1)]
    chain.append([people[-1], terminal, world.attr[(people[-1], terminal)]])
    return chain, people


def make_side(world, asker, hops, terminal):
    """One evaluation unit side: visible memory, raw question, answer, true chain."""
    rows = render(world)
    chain, people = true_chain(world, asker, hops, terminal)
    return dict(memory=[list(row) for row in rows] + [[]], question=question_tokens(asker, hops,
                                                                                    terminal),
                where=len(rows), answer=chain[-1][2], chain=chain, people=people,
                terminal=terminal, hops=hops,
                distinct=bool(len(set(people)) == len(people)))


# --------------------------------------------------------------------------- interpreters


def interpret(rows, eligible, question):
    """An INDEPENDENT evaluator-only interpreter: separate link/attribute tables and
    explicit entity type checks.  Audited against `V1.walk(V1.fact_table(...))`, which
    is a single (subject, relation) dictionary -- two different parses of the same rows.
    No model, no checkpoint, no label.
    """
    links, attrs = {}, {}
    for row, ok in zip(rows, eligible):
        if not ok:
            continue
        row = list(row)
        if len(row) < 4 or row[0] != WORLD:
            continue
        subject, relation = row[1], row[2]
        if not ENTITY_MIN <= subject < ENTITY_MAX:
            continue
        if relation == LINK:
            if subject in links:
                raise ValueError('duplicate link fact')
            if not ENTITY_MIN <= row[3] < ENTITY_MAX:
                raise ValueError('link target is not an entity')
            links[subject] = row[3]
        elif FIRST_REL <= relation < FIRST_REL + RELATIONS:
            if (subject, relation) in attrs:
                raise ValueError('duplicate attribute fact')
            attrs[(subject, relation)] = row[3]
    q = [t for t in question if t]
    if len(q) < 4 or q[0] != QUESTION or q[-1] != ANSWER:
        raise ValueError('malformed question')
    if not ENTITY_MIN <= q[1] < ENTITY_MAX:
        raise ValueError('question subject is not an entity')
    x, chain = q[1], []
    for op in q[2:-1]:
        y = links[x] if op == LINK else attrs[(x, op)]
        chain.append([x, op, y])
        x = y
    return chain


def side_eligible(side):
    return [bool(row) and index < side['where'] for index, row in enumerate(side['memory'])]


def audit_side(cell, side):
    """Exact-interpreter audit of one unit side.  Returns a list of problems."""
    cfg = CELLS[cell]
    problems = []
    eligible = side_eligible(side)
    if any(row and not eligible[index] for index, row in enumerate(side['memory'])):
        problems.append('a non-empty memory row is not causally eligible')
    links = [row for row in side['memory'] if len(row) >= 4 and row[0] == WORLD and row[2] == LINK]
    owners = [row[1] for row in links]
    if len(owners) != len(set(owners)):
        problems.append('a person has more than one LINK fact')
    people_in_rows = {row[1] for row in side['memory']
                      if len(row) >= 4 and row[0] == WORLD and ENTITY_MIN <= row[1] < ENTITY_MAX}
    if set(owners) != people_in_rows:
        problems.append('some person has no LINK fact')
    if len(people_in_rows) != cfg['people']:
        problems.append(f'{len(people_in_rows)} people in the rows, expected {cfg["people"]}')
    mine = interpret(side['memory'], eligible, side['question'])
    theirs = walk(fact_table(side['memory'], eligible), side['question'])
    if mine != theirs:
        problems.append('the two independent interpreters disagree')
    if mine != side['chain']:
        problems.append('the recorded chain disagrees with the interpreter')
    if mine[-1][2] != side['answer']:
        problems.append('the recorded answer disagrees with the interpreter')
    ops = list(side['question'][2:-1])
    if len(ops) != cfg['hops']:
        problems.append(f'{len(ops)} operations, expected {cfg["hops"]}')
    if ops[:-1] != [LINK] * (cfg['hops'] - 1):
        problems.append(f'the non-terminal operations are not all LINK: {ops}')
    if cfg['terminal'] == 'heldout' and ops[-1] != HELDOUT_REL:
        problems.append(f'terminal relation {ops[-1]}, expected the held-out {HELDOUT_REL}')
    if cfg['terminal'] == 'practised' and ops[-1] not in PRACTISED_RELS:
        problems.append(f'terminal relation {ops[-1]} is not practised')
    people = [step[0] for step in mine]
    if cfg['distinct'] and len(set(people)) != cfg['hops']:
        problems.append(f'the chain revisits a person: {people}')
    if side['people'] != people:
        problems.append('the recorded people disagree with the interpreter')
    return problems


def memory_diffs(memory_a, memory_b):
    if [len(row) for row in memory_a] != [len(row) for row in memory_b]:
        return None
    return sum(x != y for ra, rb in zip(memory_a, memory_b) for x, y in zip(ra, rb))


def audit_unit(unit):
    cfg = CELLS[unit['cell']]
    sides = ['a'] + (['b'] if unit['kind'] == 'pair' else [])
    problems = [f'{name}: {p}' for name in sides for p in audit_side(unit['cell'], unit[name])]
    if unit['kind'] != 'pair':
        return problems
    expected = 1 if cfg['edit'] == 'link' else 2
    diffs = memory_diffs(unit['a']['memory'], unit['b']['memory'])
    if diffs != expected:
        problems.append(f'pair: {diffs} differing memory tokens, expected {expected}')
    if unit['a']['question'] != unit['b']['question']:
        problems.append('pair: the twins ask different questions')
    same = unit['a']['answer'] == unit['b']['answer']
    if cfg['invariant'] and not same:
        problems.append('pair: the irrelevant edit changed the answer')
    if not cfg['invariant'] and same:
        problems.append('pair: the edit did not change the answer')
    moved = [unit['a']['memory'][i] for i, (ra, rb)
             in enumerate(zip(unit['a']['memory'], unit['b']['memory'])) if ra != rb]
    if cfg['edit'] == 'link' and [row[2] for row in moved] != [LINK]:
        problems.append('pair: the changed-link edit did not move exactly one link row')
    if cfg['edit'] in ('value', 'irrelevant') and sorted(row[2] for row in moved) != [HELDOUT_REL] * 2:
        problems.append(f'pair: the {cfg["edit"]} edit did not move exactly two relation-10 rows')
    touched = {row[1] for row in moved}
    on_chain = set(unit['a']['people'])
    if cfg['edit'] == 'irrelevant' and touched & on_chain:
        problems.append('pair: the irrelevant edit touched a person on the chain')
    if cfg['edit'] == 'value' and unit['a']['people'][-1] not in touched:
        problems.append('pair: the value edit did not touch the chain endpoint')
    if cfg['edit'] == 'link' and not touched <= on_chain:
        problems.append('pair: the changed-link edit was not on the chain')
    return problems


# --------------------------------------------------------------------------- panel units


def _bump(counter, key):
    counter[key] = counter.get(key, 0) + 1


def _terminal(rng, kind):
    return HELDOUT_REL if kind == 'heldout' else rng.choice(PRACTISED_RELS)


def _edit_world(world, asker, edit, rng, rejections, hops, terminal):
    """An edited copy of the world plus a description of what the edit moved."""
    people = chain_people(world.friend, asker, hops)
    answer = world.attr[(people[-1], terminal)]
    off_chain = [e for e in world.ents if e not in people]
    edited = copy.deepcopy(world)
    if edit == 'link':
        steps = list(range(hops - 1))
        rng.shuffle(steps)
        for step in steps:
            source = people[step]
            options = [x for x in world.ents if x != source and x != world.friend[source]]
            rng.shuffle(options)
            for target in options:
                trial = copy.deepcopy(world)
                trial.friend[source] = target
                new_people = chain_people(trial.friend, asker, hops)
                if len(set(new_people)) != hops:
                    continue
                if trial.attr[(new_people[-1], terminal)] == answer:
                    continue
                return trial, dict(edit='link', step=step, person=source,
                                   old=world.friend[source], new=target)
        _bump(rejections, 'no_usable_link_edit')
        return None
    if edit == 'value':
        options = [x for x in off_chain if world.attr[(x, terminal)] != answer]
        if not options:
            _bump(rejections, 'no_endpoint_swap_partner')
            return None
        other = rng.choice(options)
        end = people[-1]
        edited.attr[(end, terminal)], edited.attr[(other, terminal)] = \
            world.attr[(other, terminal)], world.attr[(end, terminal)]
        return edited, dict(edit='value', person=end, swapped_with=other)
    if edit == 'irrelevant':
        pairs = [(x, y) for i, x in enumerate(off_chain) for y in off_chain[i + 1:]
                 if world.attr[(x, terminal)] != world.attr[(y, terminal)]]
        if not pairs:
            _bump(rejections, 'no_irrelevant_swap_pair')
            return None
        x, y = rng.choice(pairs)
        edited.attr[(x, terminal)], edited.attr[(y, terminal)] = \
            world.attr[(y, terminal)], world.attr[(x, terminal)]
        return edited, dict(edit='irrelevant', swapped=[x, y])
    raise ValueError(edit)


def make_unit(cell, index):
    """One frozen panel unit from its own frozen RNG namespace."""
    cfg = CELLS[cell]
    rng = random.Random(f'{PANEL_NAMESPACE}:{cell}:{index}')
    rejections = {}
    hops = cfg['hops']
    while True:
        world = build_world(rng, cfg['people'])
        askers = distinct_askers(world, hops) if cfg['distinct'] else list(world.ents)
        if not askers:
            _bump(rejections, 'no_distinct_chain')
            continue
        asker = rng.choice(askers)
        terminal = _terminal(rng, cfg['terminal'])
        side_a = make_side(world, asker, hops, terminal)
        if cfg['kind'] == 'single':
            return dict(cell=cell, index=index, kind='single', a=side_a, rejections=rejections)
        made = _edit_world(world, asker, cfg['edit'], rng, rejections, hops, terminal)
        if made is None:
            continue
        edited, detail = made
        if cfg['distinct'] and asker not in distinct_askers(edited, hops):
            _bump(rejections, 'edit_broke_the_distinct_chain')
            continue
        side_b = make_side(edited, asker, hops, terminal)
        if side_b['question'] != side_a['question'] or side_b['where'] != side_a['where']:
            _bump(rejections, 'the_edit_moved_the_question')
            continue
        expected = 1 if cfg['edit'] == 'link' else 2
        if memory_diffs(side_a['memory'], side_b['memory']) != expected:
            _bump(rejections, 'unexpected_token_diffs')
            continue
        changed = side_b['answer'] != side_a['answer']
        if cfg['invariant'] and changed:
            _bump(rejections, 'irrelevant_edit_changed_the_answer')
            continue
        if not cfg['invariant'] and not changed:
            _bump(rejections, 'edit_left_the_answer_alone')
            continue
        if sorted(world.attr.values()) != sorted(edited.attr.values()):
            _bump(rejections, 'value_inventory_not_preserved')
            continue
        return dict(cell=cell, index=index, kind='pair', a=side_a, b=side_b,
                    edit_detail=detail, rejections=rejections)


def unit_signatures(unit):
    out = []
    for name in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
        side = unit[name]
        rows = [row for index, row in enumerate(side['memory'])
                if row and index < side['where']]
        out.append((A.visible_signature(rows, side['question']),
                    A.tensor_signature(rows, side['question'])))
    return out


def pack_side(units, side):
    return A.data.pack([unit[side]['memory'] for unit in units],
                       [unit[side]['question'] for unit in units],
                       list(range(len(units))),
                       [unit[side]['where'] for unit in units]), \
        [unit[side]['question'] for unit in units]


@torch.no_grad()
def operator_on_chains(operator, units, side, block=32):
    """Does the FROZEN OPERATOR itself answer every stage of every chain correctly?

    Recorded per cell so that operator errors are separable from dispatcher errors.
    """
    per_unit = []
    for start in range(0, len(units), block):
        chunk = units[start:start + block]
        inputs, _ = pack_side(chunk, side)
        entities, operations, indices, truth = [], [], [], []
        for i, unit in enumerate(chunk):
            for subject, op, target in unit[side]['chain']:
                entities.append(subject)
                operations.append(op)
                indices.append(i)
                truth.append(target)
        if isinstance(operator, OracleOperator):
            hits = [1] * len(truth)
        else:
            x = A.canonical_input(inputs, entities, operations, indices)
            hits = [int(p == t) for p, t in zip(operator.model(x).argmax(-1).tolist(), truth)]
        cursor = 0
        for unit in chunk:
            n = len(unit[side]['chain'])
            per_unit.append(hits[cursor:cursor + n])
            cursor += n
    return per_unit


def build_panels(out, operator_spec, n=PANEL_N):
    configure()
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=False)
    operator = make_operator(operator_spec)
    before = operator.fingerprint
    manifest = dict(created_unix=time.time(), namespace=PANEL_NAMESPACE, n=n,
                    source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                    frozen_before_any_training=True, cells={}, cell_order=CELL_ORDER,
                    evaluation='greedy (argmax) episodes, final update only',
                    operator=operator.describe(), operator_audit={})
    semantic, tensors = set(), set()
    totals = dict(units=0, stages=0, stages_correct=0, units_all_steps=0)
    for cell in CELL_ORDER:
        cfg = CELLS[cell]
        units, rejections = [], {}
        for index in range(n):
            unit = make_unit(cell, index)
            found = audit_unit(unit)
            if found:
                raise RuntimeError(f'{cell}:{index}: panel audit failed: {found}')
            for key, value in unit.pop('rejections').items():
                rejections[key] = rejections.get(key, 0) + value
            for sem, ts in unit_signatures(unit):
                if sem in semantic:
                    raise RuntimeError(f'{cell}:{index}: duplicate/overlapping semantic signature')
                if ts in tensors:
                    raise RuntimeError(f'{cell}:{index}: duplicate tensor signature')
                semantic.add(sem)
                tensors.add(ts)
            units.append(unit)
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        hits = {side: operator_on_chains(operator, units, side) for side in sides}
        stages = sum(len(h) for side in sides for h in hits[side])
        correct = sum(sum(h) for side in sides for h in hits[side])
        all_steps = sum(all(all(hits[side][i]) for side in sides) for i in range(n))
        audit = dict(stages=stages, stages_correct=correct, units=n, units_all_steps=all_steps,
                     operator_perfect=bool(correct == stages))
        for key in ('units', 'stages', 'stages_correct', 'units_all_steps'):
            totals[key] += audit[key]
        path = folder / f'{cell}.json'
        write_new(path, dict(cell=cell, n=n, namespace=PANEL_NAMESPACE, kind=cfg['kind'],
                             title=cfg['title'], hops=cfg['hops'], people=cfg['people'],
                             terminal=cfg['terminal'], distinct=cfg['distinct'],
                             invariant=cfg['invariant'], edit=cfg['edit'], units=units,
                             rejections=rejections,
                             operator_chain_hits={side: hits[side] for side in sides}))
        manifest['cells'][cell] = dict(path=str(path), sha256=sha(path), n=n, kind=cfg['kind'],
                                       hops=cfg['hops'], people=cfg['people'],
                                       terminal=cfg['terminal'], title=cfg['title'],
                                       rejections=rejections)
        manifest['operator_audit'][cell] = audit
        print(json.dumps(dict(cell=cell, n=n, **audit)), flush=True)
    assert operator.fingerprint == before, 'the frozen operator changed while auditing the panels'
    forbidden = folder / 'forbidden-semantics.json'
    write_new(forbidden, sorted(semantic))
    manifest.update(exclusion_path=str(forbidden), exclusion_sha256=sha(forbidden),
                    exclusion_count=len(semantic), unique_tensor_inputs=len(tensors),
                    duplicate_or_overlap_failures=0, all_audits_passed=True,
                    operator_totals=totals,
                    operator_perfect_on_every_audited_chain=bool(
                        totals['stages_correct'] == totals['stages']),
                    operator_weights_unchanged=True)
    write_new(folder / 'manifest.json', manifest)
    return dict(panels=str(folder.resolve()), cells=len(CELLS), n=n,
                exclusion_count=len(semantic), unique_tensor_inputs=len(tensors),
                operator_totals=totals,
                operator_perfect_on_every_audited_chain=manifest[
                    'operator_perfect_on_every_audited_chain'],
                manifest_sha256=sha(folder / 'manifest.json'))


def load_panels(panels):
    folder = Path(panels)
    manifest = json.loads((folder / 'manifest.json').read_text())
    loaded = {}
    for cell, row in manifest['cells'].items():
        path = folder / f'{cell}.json'
        if sha(path) != row['sha256']:
            raise RuntimeError(f'panel changed on disk: {path}')
        loaded[cell] = json.loads(path.read_text())
    if sha(folder / 'forbidden-semantics.json') != manifest['exclusion_sha256']:
        raise RuntimeError('forbidden-semantics.json changed on disk')
    return manifest, loaded, frozenset(json.loads((folder / 'forbidden-semantics.json').read_text()))


# --------------------------------------------------------------------------- training stream


def sample_training_question(rng, world, hops):
    """(asker, terminal) for one training question.

    Terminal relation is uniform over {8, 9, 10} for a one-hop question and uniform
    over {8, 9} for k >= 2, so relation 10 is NEVER the terminal relation of a
    multi-hop training question.  Chains of length >= 2 use pairwise-distinct people.
    """
    askers = world.ents if hops == 1 else distinct_askers(world, hops)
    if not askers:
        return None
    asker = rng.choice(askers)
    terminal = rng.choice([FIRST_REL, FIRST_REL + 1, HELDOUT_REL]) if hops == 1 \
        else rng.choice(list(PRACTISED_RELS))
    assert not (hops >= 2 and terminal == HELDOUT_REL), \
        'relation 10 must never be the terminal relation of a multi-hop training question'
    return asker, terminal


def training_visits(rng, visits=16, people=TRAIN_PEOPLE, hops_choices=TRAIN_HOPS,
                    forbidden=frozenset(), questions_per_world=QUESTIONS_PER_WORLD):
    """`visits` worlds, `questions_per_world` questions each, hop counts uniform over
    `hops_choices`.  The dispatcher only ever sees the raw question tokens."""
    hops_choices = list(hops_choices)
    if any(h < 1 for h in hops_choices):
        raise ValueError('hop counts must be >= 1')
    if max(hops_choices) > people:
        raise ValueError('a pairwise-distinct k-chain needs at least k people')
    memories, questions, owners, lines_at, answers, meta = [], [], [], [], [], []
    for v in range(visits):
        for _world_attempt in range(256):
            world = build_world(rng, people)
            asked, drawn = set(), []
            for _ in range(questions_per_world):
                # the hop count is drawn exactly ONCE per question, so its distribution
                # is exactly uniform over `hops_choices`; only the asker/terminal are
                # re-drawn when the same (hops, asker, terminal) triple comes up twice
                hops = rng.choice(hops_choices)
                placed = False
                for _attempt in range(64):
                    made = sample_training_question(rng, world, hops)
                    if made is None:
                        break
                    asker, terminal = made
                    if (hops, asker, terminal) in asked:
                        continue
                    asked.add((hops, asker, terminal))
                    drawn.append((hops, asker, terminal))
                    placed = True
                    break
                if not placed:
                    break
            if len(drawn) == questions_per_world:
                break
        else:
            raise RuntimeError('could not draw a usable training world')
        rows = render(world)
        memory = [list(row) for row in rows] + [[] for _ in range(questions_per_world)]
        memories.append(memory)
        for j, (hops, asker, terminal) in enumerate(drawn):
            q = question_tokens(asker, hops, terminal)
            assert len(q) == 3 + hops
            chain, people_on_chain = true_chain(world, asker, hops, terminal)
            if hops >= 2:
                assert len(set(people_on_chain)) == hops, 'multi-hop training chains must be distinct'
            where = len(rows) + j
            if forbidden:
                visible = [row for index, row in enumerate(memory) if row and index < where]
                if A.visible_signature(visible, q) in forbidden:
                    raise RuntimeError('training/panel semantic overlap; run invalid')
            questions.append(q)
            owners.append(v)
            lines_at.append(where)
            answers.append(chain[-1][2])
            meta.append(dict(hops=hops, terminal=terminal, people=people_on_chain))
    rng.randrange(1 << 30)
    return (A.data.pack(memories, questions, owners, lines_at), questions, owners,
            torch.tensor(answers, dtype=torch.long), meta)


def train_table(operator, inputs, reps, cap):
    """The operator's lookup table for a training batch.

    v1's `reachable_table` iterates its closure `V1.MAX_CALLS` times; that is exact
    here whatever the cap, because in these worlds EVERY person's entity token already
    appears in a visible memory row, so the closure is complete after one round.  The
    guard below falls back to the full grid if a cap ever exceeds v1's loop bound.
    """
    if cap <= V1.MAX_CALLS:
        return operator.reachable_table(inputs, reps)
    return operator.table(inputs, reps)


# --------------------------------------------------------------------------- features


def candidate_features_v3(tokens, present, results, n_results, previous_op, previous_subject,
                          cap, absolute_positions=False, no_recent=False, no_offsets=False):
    """v1.candidate_features with the result-slot count as a PARAMETER, plus ablations.

    Candidates = the question token positions plus the transcript's result slots.
    Each carries its token id, a source flag, an "is most recent result" flag and --
    in the primary model -- two RELATIVE offsets clipped to [-3, 3] with one extra
    "not applicable" slot.  No absolute index is used.

      no_recent   the "is most recent result" flag is 0 for every candidate
      no_offsets  both relative offsets are the N/A slot for every candidate
    """
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    position = torch.arange(width, device=device)[None].expand(batch, width)
    slot = torch.arange(cap, device=device)[None].expand(batch, cap)
    live = torch.cat((present, slot < n_results[:, None]), 1)
    token = torch.cat((tokens, results), 1) * live
    source = torch.cat((torch.zeros_like(tokens), torch.ones_like(results)), 1)
    if no_recent:
        recent = torch.zeros_like(token)
    else:
        recent = torch.cat((torch.zeros_like(tokens),
                            (slot == (n_results[:, None] - 1)).long()), 1) * live
    features = dict(token=token, source=source, recent=recent, present=live, rows=rows)
    if absolute_positions:
        # per-slot embeddings: v1 clamps the index, so result slots past the table's
        # width collide.  Kept identical to v1 on purpose (see the module docstring).
        features['absolute'] = (torch.cat((position, width + slot), 1)
                                .clamp(max=ABSOLUTE_SLOTS - 1)) * live
    else:
        for name, previous in (('offset_op', previous_op), ('offset_subject', previous_subject)):
            if no_offsets:
                features[name] = torch.full((batch, width + cap), OFFSET_NA, dtype=torch.long,
                                            device=device)
                continue
            offsets = (position - previous[:, None]).clamp(-OFFSET_CLIP, OFFSET_CLIP) + OFFSET_CLIP
            offsets = torch.where((previous >= 0)[:, None], offsets,
                                  torch.full_like(offsets, OFFSET_NA))
            features[name] = torch.cat((offsets, torch.full_like(slot, OFFSET_NA)), 1)
    return features


@dataclass(frozen=True)
class FeatureFlags:
    no_recent: bool = False
    no_offsets: bool = False

    def as_dict(self):
        return dict(no_recent=self.no_recent, no_offsets=self.no_offsets)


# --------------------------------------------------------------------------- executor


def rollout_v3(model, tokens, present, table, visit_of, cap, *, mode='sample', generator=None,
               policy=None, flags=FeatureFlags(), record=None):
    """v1.rollout with the call cap as a PARAMETER and a per-row `policy`.

    The executor validates the action, looks the call up in the operator's cached
    table, appends the result token and asks CONTINUE/STOP.  It performs no repair,
    never slices the question, never chooses a subject, and ends an episode only on the
    dispatcher's own STOP bit, an invalid action, or the cap.  An episode that reaches
    the cap without stopping is `over_cap`, which counts as a failure.

    `policy(step, tokens, results, n_results)` may return a dict with any of the keys
    'subject', 'operation', 'stop', each mapped to (values [B], mask [B] bool).  Where
    the mask is False the model acts freely.  v1's forced actions were whole-batch and
    applied at every step, which is what produced the v2 `force_subject` artefact.
    (v1 skipped the sampling draw entirely when an action was forced; v3 draws first and
    then overrides, so a FORCED sampling rollout would consume random numbers v1 would
    not.  Forcing is only ever used in greedy evaluation, which draws none.)

    `record`, if a list, receives the raw logits of every step -- used by the cap
    equivalence test, never by training or scoring.
    """
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    op_index = V1.OP_INDEX.to(device)
    results = torch.zeros(batch, cap, dtype=torch.long, device=device)
    n_results = torch.zeros(batch, dtype=torch.long, device=device)
    previous_op = torch.full((batch,), -1, dtype=torch.long, device=device)
    previous_subject = torch.full((batch,), -1, dtype=torch.long, device=device)
    active = torch.ones(batch, dtype=torch.bool, device=device)
    answer = torch.zeros(batch, dtype=torch.long, device=device)
    calls = torch.zeros(batch, dtype=torch.long, device=device)
    logprob = torch.zeros(batch, device=device)
    entropy = torch.zeros(batch, device=device)
    decisions = torch.zeros(batch, device=device)
    status = ['over_cap'] * batch
    transcripts = [[] for _ in range(batch)]
    pointers = [[] for _ in range(batch)]
    state = model.question_state(tokens, present)

    def pick(logits, forced):
        distribution = torch.distributions.Categorical(logits=logits)
        if mode == 'greedy':
            choice = logits.argmax(-1)
        elif generator is None:
            choice = distribution.sample()
        else:
            choice = torch.multinomial(distribution.probs, 1, generator=generator).squeeze(-1)
        if forced is not None:
            values, mask = forced
            choice = torch.where(mask, values.to(choice.device), choice)
        return choice, distribution.log_prob(choice), distribution.entropy()

    for step in range(cap):
        if not bool(active.any()):
            break
        features = candidate_features_v3(tokens, present, results, n_results, previous_op,
                                         previous_subject, cap, model.absolute_positions,
                                         flags.no_recent, flags.no_offsets)
        slots = features['present']
        keys = model.candidate_keys(features)
        forced = policy(step, tokens, results, n_results) if policy is not None else {}
        live = active.clone()
        subject_scores = model.subject_logits(state, keys, slots)
        subject, subject_logprob, subject_entropy = pick(subject_scores, forced.get('subject'))
        chosen = keys[rows, subject]
        operation_scores = model.operation_logits(state, chosen, keys, slots)
        operation, operation_logprob, operation_entropy = pick(operation_scores,
                                                               forced.get('operation'))
        subject_token = features['token'][rows, subject]
        operation_token = features['token'][rows, operation]
        logprob = logprob + live * (subject_logprob + operation_logprob)
        entropy = entropy + live * (subject_entropy + operation_entropy)
        decisions = decisions + 2 * live.float()
        legal = (subject_token >= ENTITY_MIN) & (subject_token < ENTITY_MAX) \
            & (op_index[operation_token.clamp(0, VOCAB - 1)] >= 0)
        for index in (live & ~legal).nonzero().flatten().tolist():
            status[index] = 'invalid_action'
            pointers[index].append([int(subject[index]), int(operation[index]), -1])
        active = active & legal
        live = active.clone()
        if not bool(live.any()):
            break
        looked_up = table[visit_of,
                          (subject_token - ENTITY_MIN).clamp(0, ENTITY_MAX - ENTITY_MIN - 1),
                          op_index[operation_token.clamp(0, VOCAB - 1)].clamp(min=0)]
        result = torch.where(live, looked_up, torch.zeros_like(looked_up))
        target = n_results.clamp(max=cap - 1)
        results = results.clone()
        results[rows, target] = torch.where(live, result, results[rows, target])
        n_results = n_results + live.long()
        calls = calls + live.long()
        on_question = subject < width
        previous_subject = torch.where(live, torch.where(on_question, subject,
                                                         torch.full_like(subject, -1)),
                                       previous_subject)
        on_question = operation < width
        previous_op = torch.where(live, torch.where(on_question, operation,
                                                    torch.full_like(operation, -1)), previous_op)
        state = torch.where(live[:, None],
                            model.advance(state, subject_token, operation_token, result), state)
        stop_scores = model.stop_logits(state)
        stop, stop_logprob, stop_entropy = pick(stop_scores, forced.get('stop'))
        if record is not None:
            record.append(dict(step=step, active=live.clone(),
                               subject=subject_scores.detach().clone(),
                               operation=operation_scores.detach().clone(),
                               stop=stop_scores.detach().clone(),
                               state=state.detach().clone()))
        logprob = logprob + live * stop_logprob
        entropy = entropy + live * stop_entropy
        decisions = decisions + live.float()
        for index in live.nonzero().flatten().tolist():
            transcripts[index].append([int(subject_token[index]), int(operation_token[index]),
                                       int(result[index])])
            pointers[index].append([int(subject[index]), int(operation[index]), int(stop[index])])
        stopping = live & stop.bool()
        answer = torch.where(stopping, result, answer)
        for index in stopping.nonzero().flatten().tolist():
            status[index] = 'answered'
        active = active & ~stopping
    return V1.Rollout(logprob=logprob, entropy=entropy, decisions=decisions, answer=answer,
                      status=status, calls=calls, transcripts=transcripts, pointers=pointers)


# --------------------------------------------------------------------------- hand policies


def correct_policy(hops, width, left=0, use_first_result=False):
    """The minimal correct decomposition, as an explicit `rollout_v3` policy.

    step t (0-based), for t < hops:
      subject   question position left+1 at t = 0, else the LATEST result slot
                (width + t - 1); with `use_first_result` the FIRST result slot
                (width + 0) instead -- the rule 1- and 2-hop training cannot rule out
      operation question position left + 2 + t
      stop      1 exactly at t = hops - 1
    Beyond the true length nothing is forced (the episode has already stopped).
    """
    hops = torch.as_tensor(hops, dtype=torch.long)

    def policy(step, tokens, results, n_results):
        batch = tokens.shape[0]
        within = (torch.full((batch,), step, dtype=torch.long) < hops)
        if step == 0:
            subject = torch.full((batch,), left + 1, dtype=torch.long)
        elif use_first_result:
            subject = torch.full((batch,), width, dtype=torch.long)
        else:
            subject = torch.full((batch,), width + step - 1, dtype=torch.long)
        operation = torch.full((batch,), left + 2 + step, dtype=torch.long)
        stop = (torch.full((batch,), step, dtype=torch.long) == hops - 1).long()
        return dict(subject=(subject, within), operation=(operation, within),
                    stop=(stop, within))
    return policy


INTERVENTIONS = ('none', 'force_operation', 'force_subject', 'force_stop',
                 'force_operation+subject')


def intervention_policy(kind, hops, width, left=0):
    """An evaluator-only intervention that forces ONLY the named component(s), and
    ONLY at steps inside the true chain.

    This is the v2 fix.  v2 forced its component at every step up to the cap, with
    `force_operation` clamped to the last true operation and `force_subject` pointing
    at the most recent result.  On an episode that ran past the true length that made
    the executor force a VALUE token as the next subject, which is an artefact of the
    instrument rather than a fact about the policy.  v3 forces a component only while
    `step < hops`; from `step == hops` on, every component is the model's own greedy
    choice, so the model is free to keep calling, stop, or act illegally, and whatever
    it does is recorded as its own behaviour.
    """
    if kind not in INTERVENTIONS:
        raise ValueError(kind)
    do_op = 'operation' in kind
    do_subject = 'subject' in kind
    do_stop = 'stop' in kind
    hops = torch.as_tensor(hops, dtype=torch.long)

    def policy(step, tokens, results, n_results):
        batch = tokens.shape[0]
        here = torch.full((batch,), step, dtype=torch.long)
        within = here < hops
        out = {}
        if do_subject:
            subject = torch.where(n_results > 0, width + n_results - 1,
                                  torch.full((batch,), left + 1, dtype=torch.long))
            out['subject'] = (subject, within)
        if do_op:
            out['operation'] = (left + 2 + here, within)
        if do_stop:
            out['stop'] = ((here >= hops - 1).long(), within)
        return out
    return policy


# --------------------------------------------------------------------------- training


def parse_hops(text):
    values = tuple(int(part) for part in str(text).split(',') if part.strip())
    if not values:
        raise ValueError('--train-hops must list at least one hop count')
    return values


def policy_gradient_loss(episodes, reward, k, call_cost, beta):
    """The rl arm's update, factored out so the tests can compare it with v1's.

    Learning signal = correct - call_cost * calls (v2's `shaped_signal`, unchanged).
    The logged reward stays pure correctness.
    """
    shaped = shaped_signal(reward, episodes.calls, call_cost)
    advantage = rloo_advantage(shaped, k)
    mean_entropy = episodes.entropy.sum() / episodes.decisions.sum().clamp_min(1)
    loss = -(advantage.detach() * episodes.logprob).mean() - beta * mean_entropy
    return loss, shaped, mean_entropy


def train(args):
    configure()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    hops_choices = parse_hops(args.train_hops)
    flags = FeatureFlags(no_recent=bool(args.no_recent_flag), no_offsets=bool(args.no_offsets))
    if flags.no_offsets and args.absolute_positions:
        raise SystemExit('--no-offsets is meaningless for the absolute-position variant')
    record = dict(dispatcher_version='v3', arm=args.arm, seed=args.seed,
                  updates_requested=args.updates,
                  absolute_positions=bool(args.absolute_positions), operator=str(args.operator),
                  visits_per_update=args.visits, questions_per_world=QUESTIONS_PER_WORLD,
                  train_hops=list(hops_choices), train_people=args.train_people,
                  train_cap=args.train_cap, k=args.k, width=args.width,
                  entropy_bonus=[args.entropy, args.entropy_final], lr=args.lr,
                  warmup=args.warmup, clip=args.clip, time_cap=args.time_cap, panels=args.panels,
                  call_cost=float(args.call_cost), ablations=flags.as_dict(),
                  reward_shaping=('correct - call_cost * calls (rl learning signal only; '
                                  'mean_reward stays pure correctness)'),
                  source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                  v2_source_sha256=sha(V2.__file__),
                  registered_test=bool(args.arm == 'rl'),
                  note='primary arm: final-answer reward only')
    updates_done = 0
    log = None
    try:
        forbidden = frozenset()
        if args.panels:
            _, _, forbidden = load_panels(args.panels)
        operator = make_operator(args.operator)
        record['operator_detail'] = operator.describe()
        operator_before = operator.fingerprint
        torch.manual_seed(args.seed)
        model = Dispatcher(width=args.width, absolute_positions=args.absolute_positions)
        record['dispatcher_parameters'] = model.parameters_count()
        print(json.dumps(dict(event='start', arm=args.arm, seed=args.seed,
                              dispatcher_parameters=model.parameters_count(),
                              train_hops=list(hops_choices), train_people=args.train_people,
                              train_cap=args.train_cap, call_cost=float(args.call_cost),
                              ablations=flags.as_dict(), operator=operator.kind)), flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=.01)
        rng = random.Random(f'{TRAIN_NAMESPACE}:{args.seed}')
        generator = torch.Generator().manual_seed(9_000_000 + args.seed)
        log = (out / 'train_log.jsonl').open('x')
        window = dict(reward=0., shaped=0., invalid=0., over_cap=0., calls=0., entropy=0.,
                      updates=0)
        capped = False
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = args.lr * min(1., (update + 1) / max(1, args.warmup))
            inputs, questions, owners, answers, _meta = training_visits(
                rng, args.visits, args.train_people, hops_choices, forbidden)
            reps, visit_of = representatives(owners)
            table = train_table(operator, inputs, reps, args.train_cap)
            tokens, present = pad_questions(questions)
            k = args.k
            repeat = torch.arange(len(questions)).repeat_interleave(k)
            episodes = rollout_v3(model, tokens[repeat], present[repeat], table, visit_of[repeat],
                                  args.train_cap, mode='sample', generator=generator, flags=flags)
            reward = (episodes.answer == answers[repeat]).float()
            beta = args.entropy + (args.entropy_final - args.entropy) * \
                (update / max(1, args.updates - 1))
            loss, shaped, mean_entropy = policy_gradient_loss(episodes, reward, k,
                                                              float(args.call_cost), beta)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
            if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
                raise RuntimeError('nonfinite dispatcher loss or gradient')
            optimizer.step()
            updates_done += 1
            window['updates'] += 1
            window['reward'] += float(reward.mean())
            window['shaped'] += float(shaped.mean())
            window['invalid'] += sum(s == 'invalid_action' for s in episodes.status) \
                / len(episodes.status)
            window['over_cap'] += sum(s == 'over_cap' for s in episodes.status) \
                / len(episodes.status)
            window['calls'] += float(episodes.calls.float().mean())
            window['entropy'] += float(mean_entropy.detach())
            if updates_done % 100 == 0 or updates_done == 1:
                n = window['updates']
                line = dict(update=updates_done, mean_reward=window['reward'] / n,
                            invalid_fraction=window['invalid'] / n,
                            over_cap_fraction=window['over_cap'] / n,
                            mean_calls=window['calls'] / n, entropy=window['entropy'] / n,
                            seconds=time.monotonic() - started,
                            mean_shaped=window['shaped'] / n, call_cost=float(args.call_cost))
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, arm=args.arm, **line)), flush=True)
                window = dict(reward=0., shaped=0., invalid=0., over_cap=0., calls=0.,
                              entropy=0., updates=0)
        log.close()
        log = None
        assert operator.fingerprint == operator_before, 'the frozen operator changed during training'
        checkpoint = out / 'dispatcher.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng_state=torch.get_rng_state(),
                        generator_state=generator.get_state(), python_rng_state=rng.getstate(),
                        updates=updates_done, seed=args.seed, arm=args.arm, width=args.width,
                        call_cost=float(args.call_cost), train_cap=args.train_cap,
                        train_hops=list(hops_choices), train_people=args.train_people,
                        ablations=flags.as_dict(),
                        absolute_positions=bool(args.absolute_positions)), checkpoint)
        seconds = time.monotonic() - started
        record.update(updates=updates_done, seconds=seconds,
                      updates_per_second=updates_done / max(1e-9, seconds),
                      checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint),
                      operator_fingerprint_before=operator_before,
                      operator_fingerprint_after=operator.fingerprint,
                      operator_weights_unchanged=True, complete=not capped, time_capped=capped,
                      final_update_only=True, no_resume=True, no_checkpoint_selection=True)
        write_new(out / ('failure.json' if capped else 'training.json'), record)
        print(json.dumps(dict(event='done', arm=args.arm, seed=args.seed, updates=updates_done,
                              time_capped=capped,
                              updates_per_second=record['updates_per_second'])), flush=True)
    except BaseException as exc:
        if log is not None:
            log.close()
        record.update(updates=updates_done, seconds=time.monotonic() - started, complete=False,
                      time_capped=False, error=repr(exc), traceback=traceback.format_exc())
        path = out / 'failure.json'
        if not path.exists():
            write_new(path, record)
        raise


# --------------------------------------------------------------------------- scoring


@torch.no_grad()
def prepare_side(operator, units, side, block=32):
    """(inputs, questions, operator table) for each block of one side of a cell.

    Computed once and reused by every intervention, so the operator sees byte-identical
    inputs whatever the dispatcher does, and the frozen operator's forward passes are
    not repeated five times per cell.
    """
    out = []
    for start in range(0, len(units), block):
        chunk = units[start:start + block]
        inputs, questions = pack_side(chunk, side)
        out.append((inputs, questions, operator.table(inputs, list(range(len(chunk))))))
    return out


class TableCache:
    """One prepared table per (operator label, cell, side)."""

    def __init__(self, operators, block=32):
        self.operators = operators
        self.block = block
        self.store = {}

    def get(self, label, cell, units, side):
        key = (label, cell, side)
        if key not in self.store:
            self.store[key] = prepare_side(self.operators[label], units, side, self.block)
        return self.store[key]


@torch.no_grad()
def score_side(model, operator, units, side, cap, flags=FeatureFlags(), policy_factory=None,
               block=32, chain_hits=None, prepared=None):
    """Label-free greedy execution of one side of a cell.

    Per unit: the returned answer, STRICT path correctness (subjects, operations, stop
    point AND every returned token equal the true chain's), the v1-comparable LOOSE
    path (subjects/operations/stop only, returned tokens ignored), the status and the
    number of calls.
    """
    out = []
    if prepared is None:
        prepared = prepare_side(operator, units, side, block)
    for block_index, start in enumerate(range(0, len(units), block)):
        chunk = units[start:start + block]
        _inputs, questions, table = prepared[block_index]
        tokens, present = pad_questions(questions)
        policy = None
        if policy_factory is not None:
            hops = torch.tensor([len(unit[side]['chain']) for unit in chunk], dtype=torch.long)
            policy = policy_factory(hops, tokens.shape[1])
        episodes = rollout_v3(model, tokens, present, table, torch.arange(len(chunk)), cap,
                              mode='greedy', policy=policy, flags=flags)
        for i, unit in enumerate(chunk):
            chain = unit[side]['chain']
            transcript = episodes.transcripts[i]
            answered = episodes.status[i] == 'answered'
            hits = None
            if chain_hits is not None:
                hits = chain_hits[side][start + i]
            out.append(dict(index=unit['index'], side=side, answer=int(episodes.answer[i]),
                            target=unit[side]['answer'],
                            correct=int(int(episodes.answer[i]) == unit[side]['answer']),
                            status=episodes.status[i], calls=int(episodes.calls[i]),
                            hops=len(chain), transcript=transcript,
                            pointers=episodes.pointers[i], truth_chain=chain,
                            strict_path=int(transcript == chain and answered),
                            loose_path=int([[s, o] for s, o, _ in transcript]
                                           == [[s, o] for s, o, _ in chain] and answered),
                            operator_chain_hits=hits,
                            operator_chain_all=None if hits is None else int(all(hits))))
    return out


def aggregate(per_side, n, cfg):
    sides = list(per_side)
    both = [all(per_side[s][i]['correct'] for s in sides) for i in range(n)]
    identical = [len({per_side[s][i]['answer'] for s in sides}) == 1 for i in range(n)]
    return dict(
        answers=sum(both),
        strict=sum(all(per_side[s][i]['strict_path'] for s in sides) for i in range(n)),
        loose=sum(all(per_side[s][i]['loose_path'] for s in sides) for i in range(n)),
        identical_twin_answers=sum(identical),
        unit_pass=sum(c and (i or not cfg['invariant']) for c, i in zip(both, identical)),
        answered=sum(r['status'] == 'answered' for s in sides for r in per_side[s]),
        over_cap=sum(r['status'] == 'over_cap' for s in sides for r in per_side[s]),
        invalid=sum(r['status'] == 'invalid_action' for s in sides for r in per_side[s]),
        rows=sum(len(per_side[s]) for s in sides),
        mean_calls=sum(r['calls'] for s in sides for r in per_side[s])
        / max(1, sum(len(per_side[s]) for s in sides)))


def diagnose(model, operators, panels, cap, flags, note, tables=None):
    """Every cell under each evaluation-time intervention, for each operator."""
    out = dict(note=note, interventions=list(INTERVENTIONS),
               definition=dict(
                   force_operation='the correct operation pointer at every step INSIDE the '
                                   'true chain; subject and stop are the model\'s own greedy '
                                   'choices, and beyond the true length nothing is forced',
                   force_subject='question position 1, then the most recent result, for steps '
                                 'inside the true chain only; operation and stop free',
                   force_stop='CONTINUE until the true chain length then STOP, for steps inside '
                              'the true chain only; others free',
                   **{'force_operation+subject': 'both pointers forced inside the true chain; '
                                                 'only stopping is free'}),
               fix=('v2 forced its component at EVERY step up to the cap, so an episode that ran '
                    'past the true length was forced to take a value token as its next subject. '
                    'v3 forces a component only while step < hops; from step == hops on the model '
                    'acts freely and whatever it does is recorded as its own behaviour.'),
               source='the truth chain of the exact interpreter, frozen in the panel', cells={})
    if tables is None:
        tables = TableCache(operators)
    for cell in CELL_ORDER:
        cfg = CELLS[cell]
        units = panels[cell]['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        cell_out = {}
        for label, operator in operators.items():
            rows = {}
            for kind in INTERVENTIONS:
                factory = None if kind == 'none' else (
                    lambda hops, width, _k=kind: intervention_policy(_k, hops, width))
                per_side = {s: score_side(model, operator, units, s, cap, flags, factory,
                                          prepared=tables.get(label, cell, units, s))
                            for s in sides}
                rows[kind] = aggregate(per_side, len(units), cfg)
            cell_out[label] = rows
        out['cells'][cell] = dict(n=len(units), sides=len(sides), title=cfg['title'], **cell_out)
        print(json.dumps(dict(diagnose=cell,
                              **{k: dict(answers=v['answers'], strict=v['strict'],
                                         over_cap=v['over_cap'])
                                 for k, v in cell_out['trained_operator'].items()})), flush=True)
    return out


def score(args):
    configure()
    run = Path(args.run)
    config_path = run / 'training.json'
    if not config_path.exists():
        config_path = run / 'failure.json'
    if not config_path.exists():
        raise SystemExit(f'no training.json or failure.json in {run}')
    config = json.loads(config_path.read_text())
    checkpoint = run / 'dispatcher.pt'
    if not checkpoint.exists():
        raise SystemExit(f'no dispatcher checkpoint in {run}')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    model = Dispatcher(width=saved['width'], absolute_positions=saved['absolute_positions'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    flags = FeatureFlags(**saved.get('ablations', {}))
    manifest, panels, _ = load_panels(args.panels)
    operator = make_operator(args.operator or config.get('operator'))
    oracle = OracleOperator()
    before = operator.fingerprint
    out = Path(args.score_out) if args.score_out else run / 'score'
    out.mkdir(parents=True, exist_ok=False)
    cap = args.eval_cap
    summary = dict(dispatcher_version='v3', run=str(run), arm=config.get('arm'),
                   seed=config.get('seed'), registered_test=config.get('registered_test'),
                   dispatcher_parameters=model.parameters_count(), updates=config.get('updates'),
                   time_capped=config.get('time_capped'), operator=operator.describe(),
                   train_cap=config.get('train_cap'), eval_cap=cap, ablations=flags.as_dict(),
                   train_hops=config.get('train_hops'), train_people=config.get('train_people'),
                   call_cost=config.get('call_cost'),
                   absolute_position_note=(
                       'the absolute-position variant has one embedding per slot and v1 clamps '
                       f'the index at {ABSOLUTE_SLOTS - 1}, so with a question of W tokens every '
                       f'result slot past index {ABSOLUTE_SLOTS - 1} - W collides; the relative '
                       'model has no per-slot parameter and is cap-free'
                       if saved['absolute_positions'] else
                       'relative-offset model: no per-slot parameter, so the eval cap is free'),
                   panels=str(Path(args.panels).resolve()),
                   panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
                   evaluation='greedy (argmax) episodes, final update only',
                   strict_path='subjects, operations, stop point AND every returned token',
                   loose_path='subjects, operations and stop point only (v1 full_path)',
                   cell_order=CELL_ORDER, cells={})
    operators = {'trained_operator': operator, 'oracle_operator': oracle}
    tables = TableCache(operators)
    transcripts = {}
    for cell in CELL_ORDER:
        cfg = CELLS[cell]
        panel = panels[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        hits = panel.get('operator_chain_hits')
        scored = {'trained_operator': {
            s: score_side(model, operator, units, s, cap, flags, chain_hits=hits,
                          prepared=tables.get('trained_operator', cell, units, s))
            for s in sides},
            'oracle_operator': {
            s: score_side(model, oracle, units, s, cap, flags,
                          prepared=tables.get('oracle_operator', cell, units, s))
            for s in sides}}
        counts = dict(n=len(units), sides=len(sides), hops=cfg['hops'], people=cfg['people'],
                      terminal=cfg['terminal'], kind=cfg['kind'])
        for label, rows in scored.items():
            counts[label] = aggregate(rows, len(units), cfg)
        counts['frozen_operator_on_true_chains'] = manifest['operator_audit'][cell]
        summary['cells'][cell] = counts
        transcripts[cell] = scored
        print(json.dumps(dict(cell=cell, hops=cfg['hops'],
                              trained=dict(answers=counts['trained_operator']['answers'],
                                           strict=counts['trained_operator']['strict'],
                                           over_cap=counts['trained_operator']['over_cap']),
                              oracle=dict(answers=counts['oracle_operator']['answers'],
                                          strict=counts['oracle_operator']['strict'],
                                          over_cap=counts['oracle_operator']['over_cap']))),
              flush=True)
    assert operator.fingerprint == before, 'the frozen operator changed during scoring'
    summary['operator_weights_unchanged'] = True
    write_new(out / 'scores.json', summary)
    write_new(out / 'transcripts.json', transcripts)
    note = (args.note or 'diagnosis written beside this run\'s own score')
    if args.diagnose:
        report = diagnose(model, operators, panels, cap, flags, note, tables)
        report.update(run=str(run), eval_cap=cap, operator=operator.describe(),
                      panels=str(Path(args.panels).resolve()))
        write_new(out / 'diagnosis.json', report)
    assert operator.fingerprint == before, 'the frozen operator changed during diagnosis'
    write_new(out / 'score_meta.json',
              dict(dispatcher_version='v3', run=str(run), score_out=str(out.resolve()),
                   eval_cap=cap, diagnose=bool(args.diagnose), ablations=flags.as_dict(),
                   source_sha256=sha(__file__), v1_source_sha256=sha(V1.__file__),
                   v2_source_sha256=sha(V2.__file__),
                   label_free_outputs=['scores.json', 'transcripts.json'],
                   evaluator_only_outputs=['diagnosis.json'], created_unix=time.time()))
    return summary


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('panels', help='generate, audit and freeze the evaluation panels')
    p.add_argument('--out', required=True)
    p.add_argument('--operator', required=True,
                   help='the frozen operator whose per-stage accuracy is recorded in the manifest')
    p.add_argument('--n', type=int, default=PANEL_N)

    p = sub.add_parser('train')
    p.add_argument('--arm', choices=('rl',), default='rl')
    p.add_argument('--absolute-positions', action='store_true')
    p.add_argument('--operator', required=True,
                   help='"oracle" or a CanonicalOperator checkpoint path')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=6000)
    p.add_argument('--out', required=True)
    p.add_argument('--time-cap', type=float, default=1500)
    p.add_argument('--panels', default=None,
                   help='panel directory whose visible semantics the training stream must avoid')
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--train-hops', default=','.join(str(h) for h in TRAIN_HOPS))
    p.add_argument('--train-people', type=int, default=TRAIN_PEOPLE)
    p.add_argument('--train-cap', type=int, default=TRAIN_CAP)
    p.add_argument('--k', type=int, default=16)
    p.add_argument('--width', type=int, default=32)
    p.add_argument('--lr', type=float, default=3e-3)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--entropy', type=float, default=.2)
    p.add_argument('--entropy-final', type=float, default=.02)
    p.add_argument('--call-cost', type=float, default=0.0,
                   help='charge per executed operator call in the rl LEARNING signal only')
    p.add_argument('--no-recent-flag', action='store_true',
                   help='ablation: zero the "is most recent result" feature at train and eval')
    p.add_argument('--no-offsets', action='store_true',
                   help='ablation: both relative offsets become the N/A slot everywhere')

    p = sub.add_parser('score')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--operator', default=None)
    p.add_argument('--eval-cap', type=int, default=EVAL_CAP)
    p.add_argument('--score-out', default=None)
    p.add_argument('--diagnose', action='store_true')
    p.add_argument('--note', default=None)

    args = parser.parse_args(argv)
    if args.command == 'panels':
        print(json.dumps(build_panels(args.out, args.operator, args.n)), flush=True)
    elif args.command == 'train':
        train(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
