"""Learned DISPATCHER pilot: a frozen lookup operator plus a learned decomposer.

A frozen CanonicalOperator F answers canonical width-4 queries [4, x, op, 5] against a
story.  F is never updated here.  A small learned dispatcher must decide, by itself,
which (subject, operation) queries to issue and when to stop.  The dispatcher sees ONLY

  * the raw question tokens, and
  * its own transcript so far: (subject token, operation token, result token) per call.

It never receives the story, an eligibility mask, a hop count, a question-length scalar,
a gold entity, or an unread-token pointer maintained by the executor.  The executor is
deliberately dumb: it checks that the chosen subject is an entity id and the chosen
operation is one of 8/9/10/11, calls F, appends the result token, and asks CONTINUE/STOP.
It never slices the question, tracks unread tokens, picks subjects, or stops because of
the question's length -- only the dispatcher's own STOP bit and the four-call cap end an
episode.

Arms
  rl          PRIMARY.  Final-answer reward only (1 if the returned token equals the
              question's answer).  RLOO policy gradient, K sampled episodes per question.
  supervised  DIAGNOSTIC CEILING, explicitly NOT the registered test.  Cross-entropy on
              the gold action sequence for the 1- and 2-hop training questions only.

Everything written here is additive and lives under its own --out directory.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
import traceback


def _add_project_scripts():
    """Put the checkout that actually holds the project's scripts on sys.path.

    Works both from a normal checkout and from a `.claude/worktrees/<name>` worktree,
    whose untracked dependencies (premonition/, archive/, runtime.local.json) live in
    the base checkout.  Nothing outside sys.path is touched.
    """
    here = Path(__file__).resolve().parent
    candidates = [here]
    for parent in here.parents:
        if parent.name == 'worktrees' and parent.parent.name == '.claude':
            candidates.append(parent.parent.parent / 'scripts')
            break
    for folder in candidates:
        if (folder / 'astra_canonical_operator.py').is_file():
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
            return folder
    raise SystemExit('cannot locate astra_canonical_operator.py; run from the project checkout')


SCRIPTS = _add_project_scripts()

import astra_canonical_operator as A                                        # noqa: E402

torch = A.torch
nn = torch.nn

QUESTION, ANSWER, WORLD, LINK = 4, 5, 3, 11
ENTITY_MIN, ENTITY_MAX = 52, 68
OPS = (8, 9, 10, 11)
VOCAB = 68
MAX_CALLS = 4
OFFSET_CLIP = 3
OFFSET_NA = 2 * OFFSET_CLIP + 1        # index 7: "no previous pointer" / "not a question position"
OFFSET_SLOTS = OFFSET_NA + 1           # 8
ABSOLUTE_SLOTS = 16                    # ablation only

PANEL_NAMESPACE = 'fable-dispatcher-panel-v1'
TRAIN_NAMESPACE = 'fable-dispatcher-train-v1'
PANEL_N = 64
CELLS = {
    'd1': dict(kind='single', hops=1, relation='any', mark=61, path_mark=None, invariant=False,
               title='one-hop, all three relations'),
    'd2': dict(kind='single', hops=2, relation='practised', mark=61, path_mark=None, invariant=False,
               title='practised two-hop'),
    'd3': dict(kind='single', hops=2, relation='heldout', mark=58, path_mark=None, invariant=False,
               title='held-out two-hop (terminal relation 10)'),
    'd4': dict(kind='single', hops=3, relation='heldout', mark=58, path_mark=58, invariant=False,
               title='three-hop held-out, three distinct people'),
    'd5': dict(kind='pair', hops=3, relation='heldout', edit='link', mark=58, path_mark=None,
               invariant=False, title='three-hop held-out changed-link pair'),
    'd6': dict(kind='pair', hops=3, relation='heldout', edit='endpoint', mark=58, path_mark=None,
               invariant=False, title='three-hop held-out changed-endpoint-value pair'),
    'd7': dict(kind='pair', hops=3, relation='heldout', edit='irrelevant', mark=58, path_mark=None,
               invariant=True, title='three-hop held-out irrelevant-edit pair'),
}


# --------------------------------------------------------------------------- small helpers


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False, sort_keys=True)
        handle.write('\n')


def fingerprint(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def configure():
    A.data.bootstrap()
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1:
        # torch refuses a second call once parallel work has started; one thread either way.
        torch.set_num_interop_threads(1)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1


def spec_and_visit():
    from premonition.toy_ladder import LadderSpec, visit
    return LadderSpec(), visit


def entity_token(spec, e):
    return spec.vocab_size + e


# --------------------------------------------------------------------------- exact interpreter


def fact_table(memory_rows, eligible=None):
    """Evaluator-only interpreter of the visible eligible fact rows.  Never reaches a model."""
    facts = {}
    for index, row in enumerate(memory_rows):
        if eligible is not None and not eligible[index]:
            continue
        if len(row) >= 4 and row[0] == WORLD and ENTITY_MIN <= row[1] < ENTITY_MAX and 8 <= row[2] <= LINK:
            key = (row[1], row[2])
            if key in facts:
                raise ValueError('duplicate semantic fact')
            facts[key] = row[3]
    return facts


def walk(facts, question):
    """The true (subject, operation, result) chain of a raw question."""
    q = [t for t in question if t]
    if len(q) < 4 or q[0] != QUESTION or q[-1] != ANSWER or not ENTITY_MIN <= q[1] < ENTITY_MAX:
        raise ValueError('malformed question')
    x, chain = q[1], []
    for op in q[2:-1]:
        y = facts[(x, op)]
        chain.append([x, op, y])
        x = y
    return chain


# --------------------------------------------------------------------------- panel construction


def _first_question_line(lines):
    for k, line in enumerate(lines):
        if line.question:
            return k
    raise ValueError('a visit without questions')


def _distinct_chain_askers(world):
    """People whose two links reach three pairwise distinct people (no return to an earlier one)."""
    return [a for a in world.ents if len({a, world.friend[a], world.friend[world.friend[a]]}) == 3]


def _bump(counter, key):
    counter[key] = counter.get(key, 0) + 1


def _three_hop_side(spec, lines, world, asker):
    """Visible memory, raw question, answer and true chain of one three-hop held-out question."""
    relation = spec.relation(spec.heldout_relation)
    b = world.friend[asker]
    c = world.friend[b]
    answer = spec.value(world.attr[(c, spec.heldout_relation)])
    return dict(memory=[[] if line.question else list(line.tokens) for line in lines],
                question=[QUESTION, entity_token(spec, asker), LINK, LINK, relation, ANSWER],
                where=_first_question_line(lines),
                answer=answer,
                chain=[[entity_token(spec, asker), LINK, entity_token(spec, b)],
                       [entity_token(spec, b), LINK, entity_token(spec, c)],
                       [entity_token(spec, c), relation, answer]],
                people=[asker, b, c])


def _edit_world(spec, world, asker, edit, rng, rejections):
    """An edited copy of the world, plus a description of what the edit moved."""
    r = spec.heldout_relation
    a = asker
    b = world.friend[a]
    c = world.friend[b]
    edited = deepcopy(world)
    ents = world.ents
    if edit == 'link':
        if rng.choice(('first', 'second')) == 'first':
            options = [x for x in ents if x not in (a, b)
                       and len({a, x, world.friend[x]}) == 3
                       and world.attr[(world.friend[x], r)] != world.attr[(c, r)]]
            if not options:
                _bump(rejections, 'no_alternative_first_link')
                return None
            new_b = rng.choice(options)
            edited.friend[a] = new_b
            detail = dict(edited_link='first', person=a, old=b, new=new_b)
        else:
            options = [x for x in ents if x not in (a, b, c)
                       and world.attr[(x, r)] != world.attr[(c, r)]]
            if not options:
                _bump(rejections, 'no_alternative_second_link')
                return None
            new_c = rng.choice(options)
            edited.friend[b] = new_c
            detail = dict(edited_link='second', person=b, old=c, new=new_c)
    elif edit == 'endpoint':
        options = [x for x in ents if x not in (a, b, c) and world.attr[(x, r)] != world.attr[(c, r)]]
        if not options:
            _bump(rejections, 'no_endpoint_swap_partner')
            return None
        x = rng.choice(options)
        edited.attr[(c, r)], edited.attr[(x, r)] = world.attr[(x, r)], world.attr[(c, r)]
        detail = dict(edit='endpoint', person=c, swapped_with=x)
    elif edit == 'irrelevant':
        pool = [x for x in ents if x not in (a, b, c)]
        pairs = [(x, y) for i, x in enumerate(pool) for y in pool[i + 1:]
                 if world.attr[(x, r)] != world.attr[(y, r)]]
        if not pairs:
            _bump(rejections, 'no_irrelevant_swap_pair')
            return None
        x, y = rng.choice(pairs)
        edited.attr[(x, r)], edited.attr[(y, r)] = world.attr[(y, r)], world.attr[(x, r)]
        detail = dict(edit='irrelevant', swapped=[x, y])
    else:
        raise ValueError(edit)
    return edited, detail


def _memory_diffs(memory_a, memory_b):
    if [len(row) for row in memory_a] != [len(row) for row in memory_b]:
        return None
    return sum(x != y for ra, rb in zip(memory_a, memory_b) for x, y in zip(ra, rb))


def make_unit(cell, index):
    """One frozen panel unit, drawn from its own frozen RNG namespace."""
    spec, visit = spec_and_visit()
    cfg = CELLS[cell]
    rng = random.Random(f'{PANEL_NAMESPACE}:{cell}:{index}')
    rejections = {}
    if cfg['hops'] in (1, 2):
        import premonition_pair_suite as PS
        lines, where, _facts, rejected = PS._make_single(spec, rng, cfg['hops'], cfg['relation'])
        for key, value in rejected.items():
            rejections[key] = rejections.get(key, 0) + value
        memory = [[] if line.question else list(line.tokens) for line in lines]
        question = list(lines[where].tokens[:lines[where].tokens.index(ANSWER) + 1])
        side = dict(memory=memory, question=question, where=where, answer=lines[where].answer[0],
                    chain=walk(fact_table(memory), question), people=None)
        return dict(cell=cell, index=index, kind='single', a=side, rejections=rejections)
    while True:
        lines, world, plan = visit(spec, rng, training=False)
        assert len(world.ents) == 6
        askers = _distinct_chain_askers(world)
        if not askers:
            _bump(rejections, 'no_distinct_three_chain')
            continue
        asker = rng.choice(askers)
        side_a = _three_hop_side(spec, lines, world, asker)
        if cfg['kind'] == 'single':
            return dict(cell=cell, index=index, kind='single', a=side_a, rejections=rejections)
        made = _edit_world(spec, world, asker, cfg['edit'], rng, rejections)
        if made is None:
            continue
        edited, detail = made
        if asker not in _distinct_chain_askers(edited):
            _bump(rejections, 'edit_broke_the_distinct_chain')
            continue
        new_lines, _, _ = visit(spec, rng, training=False, world=edited, plan=plan)
        side_b = _three_hop_side(spec, new_lines, edited, asker)
        if side_b['where'] != side_a['where'] or side_b['question'] != side_a['question']:
            _bump(rejections, 'replay_moved_the_question')
            continue
        expected = 1 if cfg['edit'] == 'link' else 2
        if _memory_diffs(side_a['memory'], side_b['memory']) != expected:
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


def audit_unit(unit):
    """Exact interpreter audit: answers, chain distinctness, eligibility, and edit locality."""
    cfg = CELLS[unit['cell']]
    sides = ['a'] + (['b'] if unit['kind'] == 'pair' else [])
    problems = []
    for name in sides:
        side = unit[name]
        eligible = [bool(row) and index < side['where'] for index, row in enumerate(side['memory'])]
        if any(row and not eligible[index] for index, row in enumerate(side['memory'])):
            problems.append(f'{name}: a non-empty memory row is not causally eligible')
        chain = walk(fact_table(side['memory'], eligible), side['question'])
        if chain != side['chain']:
            problems.append(f'{name}: the recorded chain disagrees with the interpreter')
        if chain[-1][2] != side['answer']:
            problems.append(f'{name}: the recorded answer disagrees with the interpreter')
        ops = list(side['question'][2:-1])
        if len(ops) != cfg['hops']:
            problems.append(f'{name}: {len(ops)} operations, expected {cfg["hops"]}')
        if cfg['hops'] == 3:
            if ops != [LINK, LINK, 10]:
                problems.append(f'{name}: three-hop operations {ops}, expected [11, 11, 10]')
            people = [chain[0][0], chain[0][2], chain[1][2]]
            if len(set(people)) != 3:
                problems.append(f'{name}: the chain revisits a person: {people}')
        if cfg['hops'] == 2 and cfg['relation'] == 'heldout' and ops[-1] != 10:
            problems.append(f'{name}: held-out two-hop terminal relation is {ops[-1]}, expected 10')
        if cfg['hops'] == 2 and cfg['relation'] == 'practised' and ops[-1] == 10:
            problems.append(f'{name}: practised two-hop used the held-out relation')
        if cfg['hops'] == 1 and not 8 <= ops[0] <= 10:
            problems.append(f'{name}: one-hop relation is {ops[0]}')
    if unit['kind'] == 'pair':
        expected = 1 if cfg['edit'] == 'link' else 2
        diffs = _memory_diffs(unit['a']['memory'], unit['b']['memory'])
        if diffs != expected:
            problems.append(f'pair: {diffs} differing memory tokens, expected {expected}')
        same = unit['a']['answer'] == unit['b']['answer']
        if cfg['invariant'] and not same:
            problems.append('pair: the irrelevant edit changed the answer')
        if not cfg['invariant'] and same:
            problems.append('pair: the edit did not change the answer')
        moved = [unit['a']['memory'][i] for i, (ra, rb) in
                 enumerate(zip(unit['a']['memory'], unit['b']['memory'])) if ra != rb]
        if cfg['edit'] == 'link' and [row[2] for row in moved] != [LINK]:
            problems.append('pair: the changed-link edit did not move exactly one link row')
        if cfg['edit'] in ('endpoint', 'irrelevant') and sorted(row[2] for row in moved) != [10, 10]:
            problems.append(f'pair: the {cfg["edit"]} edit did not move exactly two relation-10 rows')
        chain_people = {unit['a']['chain'][0][0], unit['a']['chain'][0][2], unit['a']['chain'][1][2]}
        touched = {row[1] for row in moved}
        if cfg['edit'] == 'irrelevant' and touched & chain_people:
            problems.append('pair: the irrelevant edit touched a person on the chain')
        if cfg['edit'] == 'endpoint' and unit['a']['chain'][1][2] not in touched:
            problems.append('pair: the endpoint edit did not touch the chain endpoint')
        if cfg['edit'] == 'link' and not touched <= chain_people:
            problems.append('pair: the changed-link edit was not on the chain')
    return problems


def unit_signatures(unit):
    """(semantic, tensor) signatures of every side, through the project's existing functions."""
    out = []
    for name in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
        side = unit[name]
        rows = [row for index, row in enumerate(side['memory']) if row and index < side['where']]
        out.append((A.visible_signature(rows, side['question']),
                    A.tensor_signature(rows, side['question'])))
    return out


def build_panels(out):
    configure()
    folder = Path(out) / 'panels'
    folder.mkdir(parents=True, exist_ok=False)
    manifest = dict(created_unix=time.time(), namespace=PANEL_NAMESPACE, n=PANEL_N,
                    source_sha256=sha(__file__), frozen_before_any_training=True,
                    evaluation='greedy (argmax) episodes, final update only', cells={}, marks={})
    semantic, tensors, audit = set(), set(), {}
    for cell, cfg in CELLS.items():
        units, rejections = [], {}
        for index in range(PANEL_N):
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
        path = folder / f'{cell}.json'
        write_new(path, dict(cell=cell, n=PANEL_N, namespace=PANEL_NAMESPACE, kind=cfg['kind'],
                             title=cfg['title'], units=units, rejections=rejections))
        manifest['cells'][cell] = dict(path=str(path), sha256=sha(path), n=PANEL_N, kind=cfg['kind'],
                                       title=cfg['title'], rejections=rejections)
        manifest['marks'][cell] = dict(answers=cfg['mark'], full_path=cfg['path_mark'])
        audit[cell] = dict(units=PANEL_N, interpreter_correct=PANEL_N, audit_failures=0)
    forbidden = folder / 'forbidden-semantics.json'
    write_new(forbidden, sorted(semantic))
    manifest.update(exclusion_path=str(forbidden), exclusion_sha256=sha(forbidden),
                    exclusion_count=len(semantic), unique_tensor_inputs=len(tensors), audit=audit,
                    duplicate_or_overlap_failures=0)
    write_new(folder / 'manifest.json', manifest)
    return dict(panels=str(folder), cells=list(CELLS), n=PANEL_N, exclusion_count=len(semantic),
                unique_tensor_inputs=len(tensors), all_audits_passed=True,
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


# --------------------------------------------------------------------------- the operators


OP_INDEX = torch.full((VOCAB,), -1, dtype=torch.long)
for _i, _op in enumerate(OPS):
    OP_INDEX[_op] = _i


class FrozenOperator:
    """A trained CanonicalOperator checkpoint: eval mode, no grad, weights never updated."""

    kind = 'checkpoint'

    def __init__(self, path):
        path = Path(path)
        if path.name == 'test.pt':
            raise ValueError('test.pt is prohibited')
        if not path.is_file():
            raise FileNotFoundError(f'operator checkpoint not found: {path}')
        saved = torch.load(path, map_location='cpu', weights_only=False)
        if not isinstance(saved, dict) or 'state_dict' not in saved:
            raise ValueError(f'{path} is not a CanonicalOperator checkpoint (no state_dict)')
        self.architecture = saved.get('architecture') or dict(vocab=68, width=48, heads=4, steps=3)
        self.model = A.CanonicalOperator(**self.architecture)
        self.model.load_state_dict(saved['state_dict'], strict=True)
        self.model.eval()
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)
        self.path = str(path.resolve())
        self.sha256 = sha(path)
        self.fingerprint = fingerprint(self.model)

    @torch.no_grad()
    def table(self, inputs, representatives):
        """[V, 16, 4]: F's argmax token for every (entity, op) against each story, one batch."""
        entities, operations, indices = [], [], []
        for rep in representatives:
            for e in range(ENTITY_MIN, ENTITY_MAX):
                for op in OPS:
                    entities.append(e)
                    operations.append(op)
                    indices.append(rep)
        x = A.canonical_input(inputs, entities, operations, indices)
        return self.model(x).argmax(-1).reshape(len(representatives), ENTITY_MAX - ENTITY_MIN, len(OPS))

    @torch.no_grad()
    def reachable_table(self, inputs, representatives):
        """The same table, computed only where an episode could ever read it.

        A call's subject is either an entity token of the question or the result of an
        earlier call, so the reachable subjects of a <=4-call episode are the closure of
        {the story's entity tokens} under F, taken MAX_CALLS times.  Entries outside that
        closure can never be looked up, so leaving them at 0 cannot change any episode;
        `tests/test_fable_dispatcher.py` checks that against the full grid.
        """
        memory, eligible = inputs.memory.tolist(), inputs.eligible.tolist()
        owner, questions = inputs.owner.tolist(), inputs.questions.tolist()
        out = torch.zeros(len(representatives), ENTITY_MAX - ENTITY_MIN, len(OPS), dtype=torch.long)
        stories = [owner[rep] for rep in representatives]
        if len(set(stories)) != len(stories):
            raise ValueError('representatives must name one question per story')
        row_of = {story: i for i, story in enumerate(stories)}
        pending = [set() for _ in representatives]
        for i, rep in enumerate(representatives):
            for row, keep in zip(memory[stories[i]], eligible[rep]):
                if keep:
                    pending[i].update(t for t in row if ENTITY_MIN <= t < ENTITY_MAX)
        for question, story in zip(questions, owner):
            if story in row_of:
                pending[row_of[story]].update(
                    t for t in question if ENTITY_MIN <= t < ENTITY_MAX)
        done = [set() for _ in representatives]
        for _round in range(MAX_CALLS):
            entities, operations, indices, slots = [], [], [], []
            for i, rep in enumerate(representatives):
                for e in sorted(pending[i]):
                    for j, op in enumerate(OPS):
                        entities.append(e)
                        operations.append(op)
                        indices.append(rep)
                        slots.append((i, e - ENTITY_MIN, j))
            if not entities:
                break
            x = A.canonical_input(inputs, entities, operations, indices)
            predicted = self.model(x).argmax(-1).tolist()
            fresh = [set() for _ in representatives]
            for (i, e, j), token in zip(slots, predicted):
                out[i, e, j] = token
                if ENTITY_MIN <= token < ENTITY_MAX:
                    fresh[i].add(token)
            for i in range(len(representatives)):
                done[i] |= pending[i]
                pending[i] = fresh[i] - done[i]
        return out

    def describe(self):
        return dict(kind=self.kind, path=self.path, sha256=self.sha256,
                    architecture=self.architecture, fingerprint=self.fingerprint)


class OracleOperator:
    """Exact symbolic lookup from the visible eligible facts; a missing fact returns token 0.

    Development/tuning stand-in and labelled diagnostic arm only.
    """

    kind = 'oracle'
    fingerprint = 'oracle'

    @torch.no_grad()
    def table(self, inputs, representatives):
        memory = inputs.memory.tolist()
        eligible = inputs.eligible.tolist()
        owner = inputs.owner.tolist()
        out = torch.zeros(len(representatives), ENTITY_MAX - ENTITY_MIN, len(OPS), dtype=torch.long)
        for row, rep in enumerate(representatives):
            facts = fact_table(memory[owner[rep]], eligible[rep])
            for e in range(ENTITY_MIN, ENTITY_MAX):
                for j, op in enumerate(OPS):
                    out[row, e - ENTITY_MIN, j] = facts.get((e, op), 0)
        return out

    # the oracle table is a handful of dictionary lookups; there is nothing to restrict
    reachable_table = table

    def describe(self):
        return dict(kind=self.kind, fingerprint=self.fingerprint)


def make_operator(spec):
    return OracleOperator() if str(spec) == 'oracle' else FrozenOperator(spec)


def direct_call(operator, inputs, entity, op, index):
    """One un-cached call against the question's own story, for the cache-equivalence test."""
    if isinstance(operator, OracleOperator):
        facts = fact_table(inputs.memory.tolist()[inputs.owner.tolist()[index]],
                           inputs.eligible.tolist()[index])
        return facts.get((entity, op), 0)
    with torch.no_grad():
        x = A.canonical_input(inputs, [entity], [op], [index])
        return int(operator.model(x).argmax(-1)[0])


# --------------------------------------------------------------------------- the dispatcher


class Dispatcher(nn.Module):
    """Pointer/copy decomposer over the question tokens and its own transcript.

    Its inputs are candidate features and a recurrent state.  No method of this class
    accepts a story, a memory tensor, an eligibility mask, a hop count or a question-length
    scalar; `question_state` reads the raw question tokens themselves.
    """

    def __init__(self, width=32, absolute_positions=False):
        super().__init__()
        self.width = width
        self.absolute_positions = bool(absolute_positions)
        self.token = nn.Embedding(VOCAB, width)
        self.source = nn.Embedding(2, width)          # 0 = question position, 1 = transcript result
        self.recent = nn.Embedding(2, width)          # "is the most recent result"
        if self.absolute_positions:
            self.absolute = nn.Embedding(ABSOLUTE_SLOTS, width)
        else:
            self.offset_op = nn.Embedding(OFFSET_SLOTS, width)
            self.offset_subject = nn.Embedding(OFFSET_SLOTS, width)
        self.key = nn.Linear(width, width)
        self.subject_query = nn.Linear(width, width)
        self.operation_query = nn.Linear(width, width)
        self.transcript = nn.Linear(3 * width, width)
        self.cell = nn.GRUCell(width, width)
        self.stop = nn.Linear(width, 2)
        self.start = nn.Parameter(torch.zeros(width))
        for module in self.modules():
            if isinstance(module, (nn.Embedding, nn.Linear)):
                nn.init.normal_(module.weight, std=.1)
            if isinstance(module, nn.Linear):
                nn.init.zeros_(module.bias)

    def parameters_count(self):
        return sum(p.numel() for p in self.parameters())

    def question_state(self, tokens, present):
        """Read the raw question tokens left to right; padded slots are skipped."""
        state = self.start.expand(tokens.shape[0], self.width).contiguous()
        kind = torch.zeros_like(tokens)
        for position in range(tokens.shape[1]):
            step = self.token(tokens[:, position]) + self.source(kind[:, position])
            state = torch.where(present[:, position, None], self.cell(step, state), state)
        return state

    def candidate_keys(self, features):
        base = self.token(features['token']) + self.source(features['source']) \
            + self.recent(features['recent'])
        if self.absolute_positions:
            base = base + self.absolute(features['absolute'])
        else:
            base = base + self.offset_op(features['offset_op']) \
                + self.offset_subject(features['offset_subject'])
        return self.key(torch.tanh(base))

    def subject_logits(self, state, keys, present):
        scores = torch.einsum('bcw,bw->bc', keys, self.subject_query(state)) / math.sqrt(self.width)
        return scores.masked_fill(~present, -torch.inf)

    def operation_logits(self, state, chosen_key, keys, present):
        query = self.operation_query(state + chosen_key)
        scores = torch.einsum('bcw,bw->bc', keys, query) / math.sqrt(self.width)
        return scores.masked_fill(~present, -torch.inf)

    def advance(self, state, subject, operation, result):
        step = self.transcript(torch.cat((self.token(subject), self.token(operation),
                                          self.token(result)), -1))
        return self.cell(step, state)

    def stop_logits(self, state):
        return self.stop(state)


def candidate_features(tokens, present, results, n_results, previous_op, previous_subject,
                       absolute_positions=False):
    """Candidate features for the pointer heads.

    Candidates = the question token positions plus the transcript's result tokens.  Each
    carries its token id, a source flag, an "is most recent result" flag, and -- in the
    primary model -- two RELATIVE offsets: (this question position) minus (the previously
    chosen op-pointer position) and minus (the previously chosen subject position), clipped
    to [-3, 3].  A single extra slot means "not applicable".  No absolute index is used.
    """
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    position = torch.arange(width, device=device)[None].expand(batch, width)
    slot = torch.arange(MAX_CALLS, device=device)[None].expand(batch, MAX_CALLS)
    live = torch.cat((present, slot < n_results[:, None]), 1)
    token = torch.cat((tokens, results), 1) * live
    source = torch.cat((torch.zeros_like(tokens), torch.ones_like(results)), 1)
    recent = torch.cat((torch.zeros_like(tokens), (slot == (n_results[:, None] - 1)).long()), 1) * live
    features = dict(token=token, source=source, recent=recent, present=live, rows=rows)
    if absolute_positions:
        features['absolute'] = (torch.cat((position, width + slot), 1)
                                .clamp(max=ABSOLUTE_SLOTS - 1)) * live
    else:
        for name, previous in (('offset_op', previous_op), ('offset_subject', previous_subject)):
            offsets = (position - previous[:, None]).clamp(-OFFSET_CLIP, OFFSET_CLIP) + OFFSET_CLIP
            offsets = torch.where((previous >= 0)[:, None], offsets,
                                  torch.full_like(offsets, OFFSET_NA))
            features[name] = torch.cat((offsets, torch.full_like(slot, OFFSET_NA)), 1)
    return features


# --------------------------------------------------------------------------- the executor


@dataclass
class Rollout:
    logprob: torch.Tensor      # [B] summed log-probability of the decisions actually taken
    entropy: torch.Tensor      # [B] summed entropy of the distributions faced
    decisions: torch.Tensor    # [B] number of decisions
    answer: torch.Tensor       # [B] returned token (0 when the episode failed)
    status: list               # [B] 'answered' | 'invalid_action' | 'over_cap'
    calls: torch.Tensor        # [B]
    transcripts: list          # [B] list of [subject token, operation token, result token]
    pointers: list             # [B] list of [subject candidate, operation candidate, stop bit]


def rollout(model, tokens, present, table, visit_of, *, mode='sample', generator=None, gold=None,
            policy=None):
    """One batched episode per row.

    The executor validates the action, looks the call up in the operator's cached table,
    appends the result token and asks CONTINUE/STOP.  It performs no repair, never slices
    the question, never chooses a subject, and ends an episode only on the dispatcher's own
    STOP bit, an invalid action, or the four-call cap.
    """
    batch, width = tokens.shape
    device = tokens.device
    rows = torch.arange(batch, device=device)
    op_index = OP_INDEX.to(device)
    results = torch.zeros(batch, MAX_CALLS, dtype=torch.long, device=device)
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
        if forced is not None:
            choice = forced
        elif mode == 'greedy':
            choice = logits.argmax(-1)
        elif generator is None:
            choice = distribution.sample()
        else:
            choice = torch.multinomial(distribution.probs, 1, generator=generator).squeeze(-1)
        return choice, distribution.log_prob(choice), distribution.entropy()

    for step in range(MAX_CALLS):
        if not bool(active.any()):
            break
        features = candidate_features(tokens, present, results, n_results, previous_op,
                                      previous_subject, model.absolute_positions)
        slots = features['present']
        keys = model.candidate_keys(features)
        forced_subject = forced_op = forced_stop = None
        if gold is not None:
            forced_subject, forced_op = gold['subject'][:, step], gold['operation'][:, step]
            forced_stop = gold['stop'][:, step]
        if policy is not None:
            forced_subject, forced_op, forced_stop = policy(step, tokens, results, n_results)
        live = active.clone()
        subject, subject_logprob, subject_entropy = pick(model.subject_logits(state, keys, slots),
                                                         forced_subject)
        chosen = keys[rows, subject]
        operation, operation_logprob, operation_entropy = pick(
            model.operation_logits(state, chosen, keys, slots), forced_op)
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
        target = n_results.clamp(max=MAX_CALLS - 1)
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
        stop, stop_logprob, stop_entropy = pick(model.stop_logits(state), forced_stop)
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
    return Rollout(logprob=logprob, entropy=entropy, decisions=decisions, answer=answer,
                   status=status, calls=calls, transcripts=transcripts, pointers=pointers)


def rloo_advantage(reward, k):
    """Leave-one-out baseline: each episode is compared with the mean of its K-1 siblings."""
    grouped = reward.reshape(-1, k)
    baseline = ((grouped.sum(1, keepdim=True) - grouped) / (k - 1)) if k > 1 \
        else torch.zeros_like(grouped)
    return (grouped - baseline).reshape(-1)


def pad_questions(questions):
    """Padded question tokens and the mask of positions that actually exist."""
    width = max(len(q) for q in questions)
    tokens = torch.zeros(len(questions), width, dtype=torch.long)
    present = torch.zeros(len(questions), width, dtype=torch.bool)
    for i, q in enumerate(questions):
        tokens[i, :len(q)] = torch.tensor(q, dtype=torch.long)
        present[i, :len(q)] = True
    return tokens, present


# --------------------------------------------------------------------------- the training stream


def training_visits(rng, visits=16, forbidden=frozenset()):
    """Only the one-hop and practised two-hop questions of `visit(spec, rng, training=True)`."""
    spec, visit = spec_and_visit()
    memories, questions, owners, lines_at, answers = [], [], [], [], []
    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6, 'training worlds must have six people'
        memory = [[] if row.question else list(row.tokens) for row in rows]
        memories.append(memory)
        asked = 0
        for j, row in enumerate(rows):
            if not row.question:
                continue
            asked += 1
            assert row.hops in (1, 2), 'the training stream must contain no three-hop question'
            assert not (row.hops == 2 and row.relation == spec.heldout_relation), \
                'the training stream must contain no held-out two-hop composition'
            q = list(row.tokens[:row.tokens.index(ANSWER) + 1])
            assert len(q) == 3 + row.hops
            if forbidden:
                visible = [r for index, r in enumerate(memory) if r and index < j]
                if A.visible_signature(visible, q) in forbidden:
                    raise RuntimeError('training/panel semantic overlap; run invalid')
            questions.append(q)
            owners.append(v)
            lines_at.append(j)
            answers.append(row.answer[0])
        assert asked == 4
    rng.randrange(1 << 30)
    return (A.data.pack(memories, questions, owners, lines_at), questions, owners,
            torch.tensor(answers, dtype=torch.long))


def representatives(owners):
    """One question index per visit (they share a story and eligibility), and each row's visit."""
    first = {}
    for index, owner in enumerate(owners):
        first.setdefault(owner, index)
    order = sorted(first)
    return [first[owner] for owner in order], torch.tensor([order.index(o) for o in owners],
                                                           dtype=torch.long)


def gold_actions(questions, width):
    """The gold pointer sequence: subject = question position 1, then the most recent result;
    operation = the question's operation positions in order; STOP after the last operation."""
    count = len(questions)
    subject = torch.zeros(count, MAX_CALLS, dtype=torch.long)
    operation = torch.zeros(count, MAX_CALLS, dtype=torch.long)
    stop = torch.zeros(count, MAX_CALLS, dtype=torch.long)
    for i, q in enumerate(questions):
        hops = len(q) - 3
        for t in range(MAX_CALLS):
            step = min(t, hops - 1)
            subject[i, t] = 1 if step == 0 else width + (step - 1)
            operation[i, t] = 2 + step
            stop[i, t] = int(step == hops - 1)
    return dict(subject=subject, operation=operation, stop=stop)


# --------------------------------------------------------------------------- training


def train(args):
    configure()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'refusing to overwrite an existing run directory: {out}')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = dict(arm=args.arm, seed=args.seed, updates_requested=args.updates,
                  absolute_positions=bool(args.absolute_positions), operator=str(args.operator),
                  visits_per_update=args.visits, k=args.k, width=args.width,
                  entropy_bonus=[args.entropy, args.entropy_final], lr=args.lr, warmup=args.warmup,
                  clip=args.clip, time_cap=args.time_cap, panels=args.panels,
                  source_sha256=sha(__file__),
                  registered_test=bool(args.arm == 'rl'),
                  note=('DIAGNOSTIC CEILING ARM, not the registered test'
                        if args.arm == 'supervised' else 'primary arm: final-answer reward only'))
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
                              operator=operator.kind)), flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(.9, .99), eps=1e-8,
                                      weight_decay=.01)
        rng = random.Random(f'{TRAIN_NAMESPACE}:{args.seed}')
        generator = torch.Generator().manual_seed(9_000_000 + args.seed)
        log = (out / 'train_log.jsonl').open('x')
        window = dict(reward=0., invalid=0., calls=0., entropy=0., updates=0)
        capped = False
        for update in range(args.updates):
            if time.monotonic() - started >= args.time_cap:
                capped = True
                break
            for group in optimizer.param_groups:
                group['lr'] = args.lr * min(1., (update + 1) / max(1, args.warmup))
            inputs, questions, owners, answers = training_visits(rng, args.visits, forbidden)
            reps, visit_of = representatives(owners)
            table = operator.reachable_table(inputs, reps)
            tokens, present = pad_questions(questions)
            if args.arm == 'rl':
                k = args.k
                repeat = torch.arange(len(questions)).repeat_interleave(k)
                episodes = rollout(model, tokens[repeat], present[repeat], table, visit_of[repeat],
                                   mode='sample', generator=generator)
                reward = (episodes.answer == answers[repeat]).float()
                advantage = rloo_advantage(reward, k)
                beta = args.entropy + (args.entropy_final - args.entropy) * \
                    (update / max(1, args.updates - 1))
                mean_entropy = episodes.entropy.sum() / episodes.decisions.sum().clamp_min(1)
                loss = -(advantage.detach() * episodes.logprob).mean() - beta * mean_entropy
            else:
                episodes = rollout(model, tokens, present, table, visit_of, mode='greedy',
                                   gold=gold_actions(questions, tokens.shape[1]))
                reward = (episodes.answer == answers).float()
                mean_entropy = episodes.entropy.sum() / episodes.decisions.sum().clamp_min(1)
                loss = -episodes.logprob.mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
            if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):
                raise RuntimeError('nonfinite dispatcher loss or gradient')
            optimizer.step()
            updates_done += 1
            window['updates'] += 1
            window['reward'] += float(reward.mean())
            window['invalid'] += sum(s == 'invalid_action' for s in episodes.status) / len(episodes.status)
            window['calls'] += float(episodes.calls.float().mean())
            window['entropy'] += float(mean_entropy.detach())
            if updates_done % 100 == 0 or updates_done == 1:
                n = window['updates']
                line = dict(update=updates_done, mean_reward=window['reward'] / n,
                            invalid_fraction=window['invalid'] / n, mean_calls=window['calls'] / n,
                            entropy=window['entropy'] / n, seconds=time.monotonic() - started,
                            # the supervised arm is teacher-forced, so these describe the GOLD
                            # action sequence executed against F, not the arm's own policy
                            teacher_forced=bool(args.arm == 'supervised'))
                log.write(json.dumps(line) + '\n')
                log.flush()
                print(json.dumps(dict(seed=args.seed, arm=args.arm, **line)), flush=True)
                window = dict(reward=0., invalid=0., calls=0., entropy=0., updates=0)
        log.close()
        log = None
        assert operator.fingerprint == operator_before, 'the frozen operator changed during training'
        checkpoint = out / 'dispatcher.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng_state=torch.get_rng_state(), generator_state=generator.get_state(),
                        python_rng_state=rng.getstate(), updates=updates_done, seed=args.seed,
                        arm=args.arm, width=args.width,
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


def pack_side(units, side):
    return A.data.pack([unit[side]['memory'] for unit in units],
                       [unit[side]['question'] for unit in units],
                       list(range(len(units))),
                       [unit[side]['where'] for unit in units]), \
        [unit[side]['question'] for unit in units]


@torch.no_grad()
def score_side(model, operator, units, side, block=32):
    """Greedy episodes, plus the frozen operator's own accuracy on the true chain."""
    out = []
    for start in range(0, len(units), block):
        chunk = units[start:start + block]
        inputs, questions = pack_side(chunk, side)
        table = operator.table(inputs, list(range(len(chunk))))
        tokens, present = pad_questions(questions)
        episodes = rollout(model, tokens, present, table, torch.arange(len(chunk)), mode='greedy')
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
        for i, unit in enumerate(chunk):
            chain = unit[side]['chain']
            chain_hits = hits[cursor:cursor + len(chain)]
            cursor += len(chain)
            transcript = episodes.transcripts[i]
            out.append(dict(index=unit['index'], side=side, answer=int(episodes.answer[i]),
                            target=unit[side]['answer'],
                            correct=int(int(episodes.answer[i]) == unit[side]['answer']),
                            status=episodes.status[i], calls=int(episodes.calls[i]),
                            transcript=transcript, pointers=episodes.pointers[i], truth_chain=chain,
                            full_path=int([[s, o] for s, o, _ in transcript]
                                          == [[s, o] for s, o, _ in chain]
                                          and episodes.status[i] == 'answered'),
                            operator_chain_hits=chain_hits,
                            operator_chain_all=int(all(chain_hits))))
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
    _manifest, panels, _ = load_panels(args.panels)
    operator = make_operator(args.operator or config.get('operator'))
    oracle = OracleOperator()
    before = operator.fingerprint
    out = run / 'score'
    out.mkdir(exist_ok=False)
    summary = dict(run=str(run), arm=config.get('arm'), seed=config.get('seed'),
                   registered_test=config.get('registered_test'), note=config.get('note'),
                   dispatcher_parameters=model.parameters_count(), updates=config.get('updates'),
                   time_capped=config.get('time_capped'), operator=operator.describe(),
                   panels=str(Path(args.panels).resolve()),
                   panel_manifest_sha256=sha(Path(args.panels) / 'manifest.json'),
                   evaluation='greedy (argmax) episodes, final update only', cells={})
    transcripts = {}
    for cell, panel in panels.items():
        cfg = CELLS[cell]
        units = panel['units']
        sides = ['a'] + (['b'] if cfg['kind'] == 'pair' else [])
        scored = {'trained_operator': {s: score_side(model, operator, units, s) for s in sides},
                  'oracle_operator': {s: score_side(model, oracle, units, s) for s in sides}}
        counts = dict(n=len(units), sides=len(sides))
        for label, rows in scored.items():
            both_correct = [all(rows[s][i]['correct'] for s in sides) for i in range(len(units))]
            identical = [len({rows[s][i]['answer'] for s in sides}) == 1 for i in range(len(units))]
            counts[label] = dict(
                answers=sum(both_correct),
                full_path=sum(all(rows[s][i]['full_path'] for s in sides) for i in range(len(units))),
                identical_twin_answers=sum(identical),
                unit_pass=sum(c and (i or not cfg['invariant'])
                              for c, i in zip(both_correct, identical)),
                invalid=sum(r['status'] == 'invalid_action' for s in sides for r in rows[s]),
                over_cap=sum(r['status'] == 'over_cap' for s in sides for r in rows[s]),
                mean_calls=sum(r['calls'] for s in sides for r in rows[s])
                / max(1, sum(len(rows[s]) for s in sides)))
        trained = scored['trained_operator']
        counts['frozen_operator_on_true_chains'] = dict(
            units_all_steps=sum(all(trained[s][i]['operator_chain_all'] for s in sides)
                                for i in range(len(units))),
            steps_correct=sum(sum(r['operator_chain_hits']) for s in sides for r in trained[s]),
            steps=sum(len(r['operator_chain_hits']) for s in sides for r in trained[s]))
        counts['mark'] = cfg['mark']
        counts['path_mark'] = cfg['path_mark']
        counts['pass'] = bool(counts['trained_operator']['unit_pass'] >= cfg['mark']
                              and (cfg['path_mark'] is None
                                   or counts['trained_operator']['full_path'] >= cfg['path_mark']))
        summary['cells'][cell] = counts
        transcripts[cell] = scored
        print(json.dumps(dict(cell=cell, mark=cfg['mark'], path_mark=cfg['path_mark'],
                              **{k: v for k, v in counts.items()
                                 if k in ('trained_operator', 'oracle_operator',
                                          'frozen_operator_on_true_chains', 'pass')})), flush=True)
    assert operator.fingerprint == before, 'the frozen operator changed during scoring'
    summary['operator_weights_unchanged'] = True
    write_new(out / 'scores.json', summary)
    write_new(out / 'transcripts.json', transcripts)
    return summary


# --------------------------------------------------------------------------- CLI


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('panels', help='generate, audit and freeze the evaluation panels')
    p.add_argument('--out', required=True)

    p = sub.add_parser('train')
    p.add_argument('--arm', choices=('rl', 'supervised'), required=True)
    p.add_argument('--absolute-positions', action='store_true')
    p.add_argument('--operator', required=True, help='"oracle" or a CanonicalOperator checkpoint path')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--updates', type=int, default=6000)
    p.add_argument('--out', required=True)
    p.add_argument('--time-cap', type=float, default=1500)
    p.add_argument('--panels', default=None,
                   help='panel directory whose visible semantics the training stream must avoid')
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--k', type=int, default=8)
    p.add_argument('--width', type=int, default=32)
    p.add_argument('--lr', type=float, default=3e-3)
    p.add_argument('--warmup', type=int, default=100)
    p.add_argument('--clip', type=float, default=1.0)
    p.add_argument('--entropy', type=float, default=.01)
    p.add_argument('--entropy-final', type=float, default=.001)

    p = sub.add_parser('score')
    p.add_argument('--run', required=True)
    p.add_argument('--panels', required=True)
    p.add_argument('--operator', default=None)

    args = parser.parse_args(argv)
    if args.command == 'panels':
        print(json.dumps(build_panels(args.out)), flush=True)
    elif args.command == 'train':
        train(args)
    else:
        score(args)


if __name__ == '__main__':
    main()
