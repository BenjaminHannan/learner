"""Start-up variants of the canonical-operator screen (Fable, 2026-09-20 EDT). Additive only.

Context. With the 0.5 x supporting-line attention loss the lookup learns reliably. Without
it, answer-only learning has a START-UP problem: variant ``e0`` (answer CE only, gold
intermediates kept) learns perfectly on seed 0 and never starts on seeds 1 and 2 (~8%
one-hop); variant ``marg`` (Ben's 16-way marginalisation, no evidence loss, no gold
intermediates) never starts on any seed (3-16% one-hop). Finding the right fact among ~45
lines / ~300 tokens from answer feedback alone is the bottleneck. Each variant below
attacks that start-up problem with ONE change on top of the base recipe.

BASE RECIPE. v3r, exactly as ``e0`` and ``marg`` in ``fable_operator_variants`` are built:
the same runner (``astra_canonical_operator_run``), the same model/init/AdamW/clipping, the
same ``random.Random(1101)`` world stream consumed identically, the v3r lr-decay schedule
(warmup to 1e-3 over 100 steps, flat to update 4,000, linear to 1e-4 at 6,000), 6,000
updates, 16 visits per update, the GENERATOR'S OWN two one-hop questions per visit plus 2
LINK + 2 terminal + 2 monolithic records, and the same ten panels/cutoffs with
final-checkpoint-only scoring.

``--balance`` (DEFAULT OFF) swaps the two one-hop canonical records for variant
``balance``'s relation-balanced fresh questions (entity uniform over the world's six
people, relation (r8, r9, r10) = (1/6, 1/6, 2/3)). It is off by default because fresh
seeds 3-5 showed that rebalancing is NOT a net improvement -- it degrades 12-person
one-hop in seeds that were perfect without it. The flag is recorded in the launch
manifest, so a frozen run always states which base it used.

``hintwarm``    ONE change vs the base recipe: the supporting-line attention term has
                weight 0.5 for updates < H (``--hint-updates``, default 1000) and EXACTLY 0
                afterwards. Hard switch, no ramp. Before H the loss is byte-for-byte v3r's
                (answer CE + 0.5 x supporting-line attention, .75/.25); from H on it is
                byte-for-byte ``e0``'s (pure answer CE, same .75/.25, no attention trace
                taken at all). Gold intermediates still build the LINK/terminal records.
                Train-batch accuracy is logged every 250 updates so the switch is visible.

``grow``        Curriculum on STORY SIZE. ONE change vs ``e0``: there is NO supporting-line
                loss at any time (pure answer CE at .75/.25, i.e. ``e0``'s step); instead
                the memory each record reads is reduced early and grown back. For updates <
                G1 (``--grow-g1``, default 1500) each visit keeps only the fact lines on its
                records' truth chains plus D (``--distractors``, default 2) further fact
                lines per record drawn uniformly from that world's other fact lines; every
                other line, including all filler and gap lines, is dropped. Between G1 and
                G2 (``--grow-g2``, default 3000) the kept fraction of the remaining lines
                rises linearly to 1. From G2 on the batch is the un-reduced base-recipe
                batch, returned untouched.

                HONESTY NOTE, implemented and documented: choosing which lines to keep
                reads each record's truth chain (for the two-hop records that chain comes
                from the generator's ``row.gold`` by way of the base batch's evidence
                targets). NO label enters the loss -- the loss is pure answer CE -- but
                label information is used to BUILD an easier curriculum. ``grow`` is
                therefore "label-free loss, label-informed curriculum", not label-free.

``grow-blind``  The fully label-free alternative to ``grow``. The kept lines are a
                uniformly random subset of that world's fact lines of the scheduled size
                (``--blind-lines``, default 16 of the 24 fact lines), grown back over
                [G1, G2) exactly as in ``grow``. Fact lines are recognised from VISIBLE
                tokens only (``row[0] == WORLD``, ``row[1]`` an entity token, ``row[2]`` in
                8..11), the same visible-structure test ``A.visible_signature`` uses. Every
                record is then built from the KEPT facts: a generator question is used
                unchanged when its chain is inside the kept subset, and otherwise replaced.
                A replacement one-hop uses ``balance``'s CONSTRUCTOR (entity uniform over
                the world's six people) with relation uniform 1/3 each, or (1/6, 1/6, 2/3)
                under ``--balance``, rejecting draws whose fact line is not kept. A
                replacement two-hop is a fresh ``[4, a, 11, r, 5]`` drawn uniformly from the
                (a, r), r in {8, 9}, that ARE answerable from the kept facts, i.e. a's LINK
                line and the target's r line are both kept. ``row.gold``, ``row.supplied``,
                ``row.answer``, ``row.hops`` and ``row.relation`` are never read; hop count
                and relation come from the visible question tokens and every answer is read
                off a kept visible fact row.

                WHAT IS STILL NOT LABEL-FREE: the LINK/terminal decomposition supplies the
                true intermediate entity as a target. ``grow-blind`` obtains it by reading
                the kept ``[world] a LINK b`` row instead of from ``row.gold``, which
                removes the annotation but not the supervision. Only ``marg-full`` removes
                the intermediate target itself.

``marg-full``   Ben's marginalisation at FULL strength on top of a start-up aid.
                ``--startup {hintwarm-onehop, grow, grow-blind}``. Two-hop questions carry
                NO gold intermediate and NO supporting line ever: the loss is
                -log sum_e P(e | S, x, LINK) * P(y | S, e, r) over the sixteen entity
                tokens 52..67, p1 un-renormalised (mass on non-entity tokens is lost and
                therefore penalised), gradients flowing into both calls, all 16 visits.
                ``row.gold`` is not read anywhere in this variant, for any startup base.
                ``hintwarm-onehop`` applies the 0.5 supporting-line hint ONLY to the two
                one-hop canonical records and only for updates < H; never to anything on
                the two-hop path. Monolithic records carry answer CE only (as in ``marg``).

                COST. 16 marginalised visits project to ~2,670 s for 6,000 updates, over the
                30-minute wave rule. Two EXACT reductions are on by default:
                ``--terminal-dedupe``  the 16 terminal calls are shared between the two
                    two-hop records of a visit whenever the relation coincides. The two
                    records differ only in ``where``; the reduction is taken only after
                    checking directly that no visible memory row lies between the two
                    ``where`` values, i.e. that the two eligibility masks are identical.
                    Nothing is approximated and no entity is dropped.
                ``--single-forward``  ``TokenMemoryReasoner`` already encodes the memory
                    once per visit inside one forward and reuses the cached cross-attention
                    key/value projections for every question of that visit, so packing the
                    one-hop, LINK, 16-way terminal and monolithic queries into ONE forward
                    encodes the story once per update instead of four times. Width-4
                    questions are right-padded to width 5 and masked out, which the model
                    handles identically (tested to 1e-6 against separate forwards).
                Both can be turned off with ``--no-terminal-dedupe`` / ``--no-single-
                forward``; they are exact, so OFF is only for auditing. Any APPROXIMATION is
                default-OFF: the only one available is ``--marg-visits N`` (N > 0
                marginalises the first N visits of each update instead of all 16).

Any EXTRA randomness a variant needs is drawn from a separate
``random.Random(f"fable-startup-{variant}:{seed}")``; the ``random.Random(1101)`` world
stream is consumed exactly as in the base recipe (``toy_ladder.visit`` per visit plus the
trailing ``randrange`` per batch), so worlds, memories and the generator's own questions
match the base recipe batch for batch.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because
the harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are
prepended to ``sys.path`` so every registered module, the frozen ``premonition`` package,
``ROOT``, the panels and the artifacts folder are the BASE repository's, exactly as for
``scripts/fable_operator_variants.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
if Path(__file__).resolve().parent != (BASE/'scripts'):
    for entry in (str(BASE), str(BASE/'scripts')):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import datetime
from dataclasses import dataclass, field
import json
import os
import random
import subprocess
import time

import astra_canonical_operator_run as R
import fable_operator_variants as V

A, P, C, torch, ROOT = R.A, R.P, R.C, R.torch, R.ROOT
assert ROOT == BASE, (ROOT, BASE)
assert Path(V.__file__).resolve().parent == BASE/'scripts', V.__file__
E, T, data = A.E, A.T, A.data
F = T.F
V1 = P.OUT
QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN
VARIANTS = ('hintwarm', 'grow', 'grow-blind', 'marg-full')
STARTUPS = ('hintwarm-onehop', 'grow', 'grow-blind')
ATTRIBUTE_RELATIONS = (8, 9, 10)
TWO_HOP_RELATIONS = (8, 9)
COUNTED_OPERATIONS = ATTRIBUTE_RELATIONS + (LINK,)
ORIGINAL_FLOPS = V.ORIGINAL_FLOPS
LOG_EVERY = 250

DEFAULTS = dict(balance=False, hint_updates=1000, grow_g1=1500, grow_g2=3000,
                distractors=2, blind_lines=16, startup='hintwarm-onehop', marg_visits=0,
                terminal_dedupe=True, single_forward=True)

# Process-local wiring; never serialized, never part of the registered manifest.
STATE = dict(variant=None, seed=None, vrng=None, step=0, params=dict(DEFAULTS),
             running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))


def out_for(variant):
    assert variant in VARIANTS, variant
    return ROOT/f'artifacts/fable-operator-{variant}-20260920'


def grow_fraction(step, g1, g2):
    """0 before G1, linear on [G1, G2), 1 from G2 on."""
    assert 0 <= g1 <= g2, (g1, g2)
    if step < g1:
        return 0.
    if step >= g2:
        return 1.
    return (step - g1) / (g2 - g1)


# ------------------------------------------------------------------ visible row classes

def _is_fact(row):
    """Visible-token test. No semantic field, label, gold or supplied card is consulted."""
    return (len(row) >= 4 and row[0] == WORLD and ENTITY_MIN <= row[1] < ENTITY_MAX
            and 8 <= row[2] <= LINK)


def _row_classes(rows):
    """(fact line indices, other non-empty line indices) for one visit's visible rows."""
    facts, others = [], []
    for k, row in enumerate(rows):
        if not any(row):
            continue                       # question lines are blanked before packing
        (facts if _is_fact(row) else others).append(k)
    return facts, others


def _visible_facts(rows, keep):
    """attr[(entity, relation)] -> (value, line); link[entity] -> (target, line). Kept rows only."""
    attr, links = {}, {}
    for k in keep:
        row = rows[k]
        if not _is_fact(row):
            continue
        if row[2] == LINK:
            links[row[1]] = (row[3], k)
        else:
            attr[(row[1], row[2])] = (row[3], k)
    return attr, links


# --------------------------------------------------------- tensor-level story reduction

def _reduce_inputs(x, keep):
    """Drop every line not in ``keep`` from the packed memory, preserving eligibility.

    ``keep[v]`` is the sorted list of original line indices retained for visit v. A kept
    line is eligible for a question iff it was eligible for that question in the original
    visit: the new eligibility is the old one gathered through the kept-line map, never
    recomputed. Trailing all-zero token columns are trimmed; that changes no value.
    """
    visits, lines, width = x.memory.shape
    assert len(keep) == visits
    k = max((len(rows) for rows in keep), default=0) or 1
    memory = x.memory.new_zeros(visits, k, width)
    index = x.memory.new_full((visits, k), -1)
    for i, rows in enumerate(keep):
        if not rows:
            continue
        sel = torch.tensor(rows, dtype=torch.long)
        memory[i, :len(rows)] = x.memory[i].index_select(0, sel)
        index[i, :len(rows)] = sel
    columns = memory.ne(0).any(0).any(0)
    stop = int(columns.nonzero().max()) + 1 if bool(columns.any()) else 1
    memory = memory[:, :, :stop].contiguous()
    owned = index[x.owner]
    eligible = x.eligible.gather(1, owned.clamp_min(0)) & (owned >= 0)
    return data.Inputs(memory, x.questions, x.owner, eligible)


def _record_chains(batch):
    """(owner, sorted truth-chain line indices) per record, from the base recipe's targets.

    LABEL USE: for two-hop-derived records these line indices came from the generator's
    ``row.gold``. Only ``grow`` uses this function.
    """
    chains = []
    for x, y in ((batch.canonical, batch.canonical_targets),
                 (batch.monolithic, batch.monolithic_targets)):
        for owner, lines in zip(x.owner.tolist(), y.lines.tolist()):
            chains.append((owner, sorted(set(lines))))
    return chains


def _keep_from_chains(vrng, classes, chains, fraction, distractors):
    """Shared selection rule: every chain line, D extra fact lines per chain, then growth."""
    keep = [set() for _ in classes]
    for owner, chain in chains:
        keep[owner].update(chain)
        pool = [line for line in classes[owner][0] if line not in chain]
        keep[owner].update(vrng.sample(pool, min(distractors, len(pool))))
    for i, (facts, others) in enumerate(classes):
        remaining = sorted(line for line in facts + others if line not in keep[i])
        keep[i].update(vrng.sample(remaining, int(round(fraction*len(remaining)))))
    return [sorted(rows) for rows in keep]


def _grow_keep(batch, vrng, fraction, distractors):
    classes = [_row_classes(rows) for rows in batch.canonical.memory.tolist()]
    return _keep_from_chains(vrng, classes, _record_chains(batch), fraction, distractors)


def _reduce_batch(batch, keep, fraction):
    remap = [{old: new for new, old in enumerate(rows)} for rows in keep]

    def rebuilt(x, y):
        lines = torch.tensor([[remap[owner][line] for line in row]
                              for owner, row in zip(x.owner.tolist(), y.lines.tolist())])
        return _reduce_inputs(x, keep), E.Targets(y.answer, lines)

    cx, cy = rebuilt(batch.canonical, batch.canonical_targets)
    mx, my = rebuilt(batch.monolithic, batch.monolithic_targets)
    accounting = dict(batch.accounting)
    accounting['curriculum'] = dict(
        fraction=round(fraction, 6), reduced=True,
        original_lines=int(batch.canonical.memory.shape[1]),
        kept_lines=[len(rows) for rows in keep],
        kept_tokens=[int(cx.memory[i].ne(0).sum()) for i in range(cx.memory.shape[0])],
        original_tokens=[int(batch.canonical.memory[i].ne(0).sum())
                         for i in range(batch.canonical.memory.shape[0])])
    return A.TrainingBatch(cx, cy, mx, my, accounting)


# --------------------------------------------------------- base recipe and its one change

def _base_batch(rng, visits, forbidden):
    """v3r's eight records by default; ``balance``'s relation-balanced one-hop with --balance."""
    if STATE['params']['balance']:
        return V.training_batch_balance(rng, visits, forbidden)
    return V.training_batch_e0(rng, visits, forbidden)


def training_batch_hintwarm(rng, visits=16, forbidden=frozenset()):
    """The base recipe, untouched. ``hintwarm`` changes only the loss schedule."""
    return _base_batch(rng, visits, forbidden)


def training_batch_grow(rng, visits=16, forbidden=frozenset()):
    """The base recipe's records, read against a story that starts small and grows."""
    batch = _base_batch(rng, visits, forbidden)
    p = STATE['params']
    fraction = grow_fraction(STATE['step'], p['grow_g1'], p['grow_g2'])
    if fraction >= 1.:
        batch.accounting['curriculum'] = dict(fraction=1., reduced=False)
        return batch
    keep = _grow_keep(batch, STATE['vrng'], fraction, p['distractors'])
    return _reduce_batch(batch, keep, fraction)


# ------------------------------------------------- label-free record construction helpers

def _blind_keep(vrng, rows, blind_lines, fraction):
    facts, others = _row_classes(rows)
    chosen = set(vrng.sample(facts, min(blind_lines, len(facts))))
    remaining = sorted(line for line in facts + others if line not in chosen)
    chosen.update(vrng.sample(remaining, int(round(fraction*len(remaining)))))
    return sorted(chosen)


def _one_hop_record(vrng, spec, world, attr, balance, asked, tries=64):
    """(entity, relation, (answer, line), replaced) read off the KEPT visible facts.

    Default base: the generator's own one-hop question is used whenever its fact line is
    kept. Otherwise -- and always under ``--balance`` -- ``balance``'s constructor draws a
    replacement (entity uniform over the world's six people; relation uniform 1/3 each, or
    (1/6, 1/6, 2/3) under ``--balance``), rejecting draws whose fact line is not kept.
    """
    if not attr:
        raise RuntimeError('no attribute fact kept for this visit')
    if not balance and asked is not None and asked in attr:
        return asked[0], asked[1], attr[asked], False
    for _ in range(tries):
        entity = spec.vocab_size + world.ents[vrng.randrange(len(world.ents))]
        if balance:
            draw = vrng.randrange(6)
            relation = spec.relation(0 if draw == 0 else 1 if draw == 1 else 2)
        else:
            relation = spec.relation(vrng.randrange(3))
        if (entity, relation) in attr:
            return entity, relation, attr[(entity, relation)], True
    keys = sorted(attr)
    key = keys[vrng.randrange(len(keys))]
    return key[0], key[1], attr[key], True


def _two_hop_record(vrng, attr, links, asked, relation):
    """((asker, relation), replaced) answerable from the KEPT facts; the generator's if kept."""
    if asked is not None and asked in links and (links[asked][0], relation) in attr:
        return (asked, relation), False
    options = sorted((a, r) for a in links for r in TWO_HOP_RELATIONS
                     if (links[a][0], r) in attr)
    if not options:
        return None, False
    return options[vrng.randrange(len(options))], True


# ------------------------------------------------------------------------ batch: grow-blind

def training_batch_blind(rng, visits=16, forbidden=frozenset()):
    """Label-free curriculum and label-free record construction; ``row.gold`` never read.

    The semantic-overlap ``forbidden`` check is taken against the FULL story, not the
    reduced one: the reduced story is a subset of it, so checking the full story is the
    conservative test (a reduced story could never match a full panel signature).
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng, p = STATE['vrng'], STATE['params']
    assert vrng is not None, 'grow-blind needs its own RNG; call configure_variant(seed=...)'
    fraction = grow_fraction(STATE['step'], p['grow_g1'], p['grow_g2'])
    memories = []
    c, m = (dict(q=[], owner=[], where=[], answer=[], evidence=[]) for _ in range(2))
    kinds = dict(one_hop=0, link=0, terminal=0, monolithic=0)
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0,
                  kept_generator_two_hop=0, replaced_two_hop=0, degraded_two_hop=0)
    kept_lines, checked, lines_per_visit = [], 0, 0

    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        full = [[] if row.question else list(row.tokens) for row in rows]
        lines_per_visit = len(full)
        # Hops and relation come from the VISIBLE question tokens, not row.hops/row.relation.
        asks = [(j, row.tokens[:row.tokens.index(ANSWER)+1])
                for j, row in enumerate(rows) if row.question]
        assert len(asks) == 4
        keep = _blind_keep(vrng, full, p['blind_lines'], fraction)
        kept_lines.append(len(keep))
        index = {old: new for new, old in enumerate(keep)}
        memories.append([full[old] for old in keep])
        attr, links = _visible_facts(full, keep)
        attr = {k: (val, index[line]) for k, (val, line) in attr.items()}
        links = {k: (val, index[line]) for k, (val, line) in links.items()}

        def add(dst, q, where, answer, evidence, kind):
            nonlocal checked
            if forbidden and A.visible_signature(full, q) in forbidden:
                raise RuntimeError("training/validation semantic overlap; run invalid")
            checked += 1
            for key, val in zip(dst, (q, v, where, answer, evidence)):
                dst[key].append(val)
            kinds[kind] += 1

        for j, q in asks:
            where = sum(1 for old in keep if old < j)
            if len(q) == 4:
                assert q[2] in ATTRIBUTE_RELATIONS
                entity, relation, (answer, line), replaced = _one_hop_record(
                    vrng, spec, world, attr, p['balance'], (q[1], q[2]))
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
                add(c, [QUESTION, entity, relation, ANSWER], where, answer, [line]*3, 'one_hop')
                continue
            assert len(q) == 5 and q[2] == LINK and q[3] in TWO_HOP_RELATIONS
            pick, replaced = _two_hop_record(vrng, attr, links, q[1], q[3])
            if pick is None:
                # Safety valve: nothing two-hop is answerable from the kept facts. Emit a
                # one-hop record in its place and count it; never silently drop a record.
                census['degraded_two_hop'] += 1
                entity, relation, (answer, line), _ = _one_hop_record(
                    vrng, spec, world, attr, p['balance'], None)
                add(c, [QUESTION, entity, relation, ANSWER], where, answer, [line]*3, 'one_hop')
                add(m, [QUESTION, entity, relation, ANSWER], where, answer, [line]*3, 'monolithic')
                continue
            census['replaced_two_hop' if replaced else 'kept_generator_two_hop'] += 1
            asker, relation = pick
            target, link_line = links[asker]
            answer, endpoint_line = attr[(target, relation)]
            add(c, [QUESTION, asker, LINK, ANSWER], where, target, [link_line]*3, 'link')
            add(c, [QUESTION, target, relation, ANSWER], where, answer, [endpoint_line]*3, 'terminal')
            add(m, [QUESTION, asker, LINK, relation, ANSWER], where, answer,
                [link_line, endpoint_line, endpoint_line], 'monolithic')
    rng.randrange(1 << 30)

    def pack(d):
        return (data.pack(memories, d['q'], d['owner'], d['where']),
                E.Targets(torch.tensor(d['answer']), torch.tensor(d['evidence'])))

    cx, cy = pack(c)
    mx, my = pack(m)
    assert kinds['link'] == kinds['terminal']
    assert kinds['one_hop'] + kinds['link'] + kinds['terminal'] == cx.questions.shape[0]
    accounting = dict(visits=visits, records=checked, kinds=kinds,
                      relations=V._relation_counts(cx.questions),
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0,
                      gold_fields_used=0, blind=dict(census),
                      curriculum=dict(fraction=round(fraction, 6), reduced=True,
                                      kept_lines=kept_lines, original_lines=lines_per_visit))
    return A.TrainingBatch(cx, cy, mx, my, accounting)


# ------------------------------------------------------------------------ batch: marg-full

@dataclass
class StartupMargBatch:
    one_hop: data.Inputs
    one_hop_targets: E.Targets
    link: data.Inputs
    terminal: data.Inputs                # [distinct terminal calls, 4]
    terminal_index: torch.Tensor         # [two_hop_records, 16] -> row of ``terminal``
    two_hop_answers: torch.Tensor
    monolithic: data.Inputs
    monolithic_answers: torch.Tensor
    combined: object
    plan: dict
    accounting: dict = field(default_factory=dict)


def _pad_questions(questions, width):
    if questions.shape[1] == width:
        return questions
    out = questions.new_zeros(questions.shape[0], width)
    out[:, :questions.shape[1]] = questions
    return out


def _concat_inputs(parts):
    """One Inputs over the same memory; returns (inputs, {name: (start, stop)})."""
    memory = parts[0][1].memory
    for _, x in parts[1:]:
        assert torch.equal(x.memory, memory), 'combined forward needs one shared memory'
    width = max(x.questions.shape[1] for _, x in parts)
    questions = torch.cat([_pad_questions(x.questions, width) for _, x in parts], 0)
    owner = torch.cat([x.owner for _, x in parts], 0)
    eligible = torch.cat([x.eligible for _, x in parts], 0)
    slices, at = {}, 0
    for name, x in parts:
        slices[name] = (at, at + x.questions.shape[0])
        at += x.questions.shape[0]
    return data.Inputs(memory, questions, owner, eligible), slices


def _same_eligibility(rows, w1, w2):
    """True iff question-line indices w1 and w2 give the same eligible-row mask.

    ``eligible = visible(row) & (row_index < where)``, so the masks agree iff no VISIBLE
    row index lies between the two ``where`` values. In this generator every fact and
    filler line precedes every question line, so this holds for all questions of a visit;
    it is checked directly rather than assumed.
    """
    lo, hi = sorted((w1, w2))
    return not any(any(rows[k]) for k in range(lo, hi))


def _grow_keep_visible(vrng, full, asks, fraction, distractors):
    """``grow``'s curriculum with chains read off the VISIBLE facts of the full story.

    Same selection rule as ``_grow_keep``; used by ``marg-full --startup grow`` so that no
    generator annotation is read anywhere in that variant. The curriculum is still
    chain-informed, and therefore still not label-free.
    """
    attr, links = _visible_facts(full, range(len(full)))
    classes = [_row_classes(full)]
    chains = []
    for _, q in asks:
        if len(q) == 4:
            chains.append((0, [attr[(q[1], q[2])][1]]))
        else:
            target, line = links[q[1]]
            chains.append((0, [line, attr[(target, q[3])][1]]))
    return _keep_from_chains(vrng, classes, chains, fraction, distractors)[0]


def training_batch_margfull(rng, visits=16, forbidden=frozenset()):
    """Relation-balanced-optional one-hop + marginalised two-hop + monolithic, on the chosen base.

    ``row.gold``, ``row.supplied``, ``row.answer``, ``row.hops`` and ``row.relation`` are
    never read. Chains used by the ``grow`` curriculum are derived from the VISIBLE facts of
    the full story (the same interpretation ``A.truth_paths`` performs for scoring), so no
    generator annotation is consulted anywhere in this variant.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng, p = STATE['vrng'], STATE['params']
    assert vrng is not None, 'marg-full needs its own RNG; call configure_variant(seed=...)'
    startup = p['startup']
    assert startup in STARTUPS, startup
    limit = p['marg_visits'] or visits
    fraction = 1. if startup == 'hintwarm-onehop' else \
        grow_fraction(STATE['step'], p['grow_g1'], p['grow_g2'])
    hint = startup == 'hintwarm-onehop' and STATE['step'] < p['hint_updates']

    memories = []
    one = dict(q=[], owner=[], where=[], answer=[], evidence=[])
    link = dict(q=[], owner=[], where=[])
    term = dict(q=[], owner=[], where=[])
    mono = dict(q=[], owner=[], where=[])
    terminal_rows, two_answers, mono_answers = [], [], []
    kinds = dict(one_hop=0, marginalised_two_hop=0, monolithic=0)
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0, kept_generator_two_hop=0,
                  replaced_two_hop=0, degraded_two_hop=0, deduped_terminal_calls=0)
    kept_lines, checked, lines_per_visit = [], 0, 0

    def check(full, q):
        nonlocal checked
        if forbidden and A.visible_signature(full, q) in forbidden:
            raise RuntimeError("training/validation semantic overlap; run invalid")
        checked += 1

    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        full = [[] if row.question else list(row.tokens) for row in rows]
        lines_per_visit = len(full)
        asks = [(j, row.tokens[:row.tokens.index(ANSWER)+1])
                for j, row in enumerate(rows) if row.question]
        assert len(asks) == 4
        if startup == 'hintwarm-onehop':
            keep = list(range(len(full)))
        elif startup == 'grow-blind':
            keep = _blind_keep(vrng, full, p['blind_lines'], fraction)
        else:
            keep = _grow_keep_visible(vrng, full, asks, fraction, p['distractors'])
        kept_lines.append(len(keep))
        index = {old: new for new, old in enumerate(keep)}
        memories.append([full[old] for old in keep])
        attr, links = _visible_facts(full, keep)
        attr = {k: (val, index[line]) for k, (val, line) in attr.items()}
        links = {k: (val, index[line]) for k, (val, line) in links.items()}
        terminal_key = {}

        for j, q in asks:
            where = sum(1 for old in keep if old < j)
            if len(q) == 4:
                assert q[2] in ATTRIBUTE_RELATIONS
                entity, relation, (answer, line), replaced = _one_hop_record(
                    vrng, spec, world, attr, p['balance'], (q[1], q[2]))
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
                oq = [QUESTION, entity, relation, ANSWER]
                check(full, oq)
                one['q'].append(oq); one['owner'].append(v); one['where'].append(where)
                one['answer'].append(answer); one['evidence'].append([line]*3)
                kinds['one_hop'] += 1
                continue
            assert len(q) == 5 and q[2] == LINK and q[3] in TWO_HOP_RELATIONS
            pick, replaced = _two_hop_record(vrng, attr, links, q[1], q[3])
            if pick is None:
                census['degraded_two_hop'] += 1
                continue
            if startup != 'grow-blind':
                assert not replaced, 'hintwarm-onehop/grow must keep every generator chain'
            census['replaced_two_hop' if replaced else 'kept_generator_two_hop'] += 1
            asker, relation = pick
            target, _ = links[asker]
            answer, _ = attr[(target, relation)]
            mq = [QUESTION, asker, LINK, relation, ANSWER]
            check(full, mq)
            mono['q'].append(mq); mono['owner'].append(v); mono['where'].append(where)
            mono_answers.append(answer)
            kinds['monolithic'] += 1
            if v >= limit:
                continue
            lq = [QUESTION, asker, LINK, ANSWER]
            check(full, lq)
            link['q'].append(lq); link['owner'].append(v); link['where'].append(where)
            row_ids = []
            for entity in range(ENTITY_MIN, ENTITY_MAX):
                tq = [QUESTION, entity, relation, ANSWER]
                check(full, tq)
                key = (relation, entity)
                hit = terminal_key.get(key)
                if p['terminal_dedupe'] and hit is not None and \
                        _same_eligibility(memories[v], term['where'][hit], where):
                    census['deduped_terminal_calls'] += 1
                    row_ids.append(hit)
                    continue
                term['q'].append(tq); term['owner'].append(v); term['where'].append(where)
                terminal_key[key] = len(term['q']) - 1
                row_ids.append(len(term['q']) - 1)
            terminal_rows.append(row_ids)
            two_answers.append(answer)
            kinds['marginalised_two_hop'] += 1
    rng.randrange(1 << 30)

    def pack(d):
        return data.pack(memories, d['q'], d['owner'], d['where'])

    ox, lx, tx, mx = pack(one), pack(link), pack(term), pack(mono)
    assert not bool((tx.questions[:, 2] == 10).any()), 'relation 10 must never be a two-hop terminal'
    assert ox.questions.shape[0] == kinds['one_hop'] == 2*visits
    one_targets = E.Targets(torch.tensor(one['answer']), torch.tensor(one['evidence']))
    terminal_index = torch.tensor(terminal_rows, dtype=torch.long) if terminal_rows \
        else torch.zeros(0, ENTITIES, dtype=torch.long)
    assert terminal_index.shape == (kinds['marginalised_two_hop'], ENTITIES)
    parts = [('link', lx), ('terminal', tx), ('monolithic', mx)]
    if not hint:
        parts.insert(0, ('one_hop', ox))
    combined, slices = _concat_inputs(parts) if p['single_forward'] else (None, {})
    plan = dict(single_forward=bool(p['single_forward']), hint=bool(hint), slices=slices,
                startup=startup, fraction=round(fraction, 6))
    records = kinds['one_hop'] + kinds['marginalised_two_hop'] + kinds['monolithic']
    accounting = dict(visits=visits, records=records, kinds=kinds,
                      relations=V._relation_counts(ox.questions, lx.questions, tx.questions),
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0, marg_visits=limit,
                      gold_entities_used=0, gold_fields_used=0,
                      evidence_lines_used=kinds['one_hop'] if hint else 0,
                      blind=dict(census),
                      curriculum=dict(fraction=round(fraction, 6),
                                      reduced=startup != 'hintwarm-onehop',
                                      kept_lines=kept_lines, original_lines=lines_per_visit),
                      forwards=dict(combined=1 if p['single_forward'] else 0,
                                    one_hop=1 if (hint or not p['single_forward']) else 0,
                                    separate=3 if not p['single_forward'] else 0),
                      terminal_calls=int(tx.questions.shape[0]),
                      terminal_calls_undeduped=ENTITIES*kinds['marginalised_two_hop'])
    return StartupMargBatch(ox, one_targets, lx, tx, terminal_index,
                            torch.tensor(two_answers), mx, torch.tensor(mono_answers),
                            combined, plan, accounting)


def training_flops_margfull(batch, model):
    """Honest per-forward count of exactly the forwards ``margfull_losses`` performs."""
    if batch.plan['single_forward']:
        total = T.training_flops(batch.combined, model)
        if batch.plan['hint']:
            total += T.training_flops(batch.one_hop, model)
        return total
    return sum(T.training_flops(x, model) for x in
               (batch.one_hop, batch.link, batch.terminal, batch.monolithic))


# --------------------------------------------------------------------------------- losses

def marginal_probability(model, batch, link_logits=None, terminal_logits=None):
    """P(y) = sum_e p1[e] * P(y | S, e, r); p1 is NOT renormalised over the entities."""
    if link_logits is None:
        link_logits = model(batch.link)
    if terminal_logits is None:
        terminal_logits = model(batch.terminal)
    n = link_logits.shape[0]
    assert batch.terminal_index.shape == (n, ENTITIES)
    p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]                  # [n, 16]
    pt = terminal_logits.softmax(-1)[batch.terminal_index]                  # [n, 16, V]
    index = batch.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)
    conditional = pt.gather(2, index).squeeze(2)                            # [n, 16]
    return (p1 * conditional).sum(1)


def margfull_logits(model, batch):
    """Logits for the four record groups under whichever forward plan the batch declares."""
    plan, pieces = batch.plan, {}
    if plan['single_forward']:
        logits = model(batch.combined)
        for name, (start, stop) in plan['slices'].items():
            pieces[name] = logits[start:stop]
    for name, x in (('one_hop', batch.one_hop), ('link', batch.link),
                    ('terminal', batch.terminal), ('monolithic', batch.monolithic)):
        if name not in pieces:
            pieces[name] = model(x)
    return pieces


def margfull_losses(model, batch):
    plan, pieces = batch.plan, {}
    if plan['single_forward']:
        logits = model(batch.combined)
        for name, (start, stop) in plan['slices'].items():
            pieces[name] = logits[start:stop]
    if plan['hint']:
        # The supporting-line hint needs the attention trace, so the one-hop records take
        # their own forward while it is active. It is never applied to anything else.
        one = E.loss_for(model, batch.one_hop, batch.one_hop_targets)[0]
    else:
        one_logits = pieces.get('one_hop')
        if one_logits is None:
            one_logits = model(batch.one_hop)
        one = F.cross_entropy(one_logits, batch.one_hop_targets.answer)
    link_logits = pieces.get('link')
    if link_logits is None:
        link_logits = model(batch.link)
    terminal_logits = pieces.get('terminal')
    if terminal_logits is None:
        terminal_logits = model(batch.terminal)
    mono_logits = pieces.get('monolithic')
    if mono_logits is None:
        mono_logits = model(batch.monolithic)
    mono = F.cross_entropy(mono_logits, batch.monolithic_answers)
    marg = -marginal_probability(model, batch, link_logits,
                                 terminal_logits).clamp_min(1e-12).log().mean()
    return one, marg, mono


def marg_weights(batch):
    """Equal weight per record: with the default 16 visits this is exactly (1/3, 1/3, 1/3)."""
    k = batch.accounting['kinds']
    total = k['one_hop'] + k['marginalised_two_hop'] + k['monolithic']
    return (k['one_hop']/total, k['marginalised_two_hop']/total, k['monolithic']/total)


def _finish(model, optimizer):
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not bool(torch.isfinite(norm)):
        raise RuntimeError("nonfinite gradient")
    optimizer.step()


def _step_hintwarm(model, optimizer, batch, step):
    """v3r's step for step < H; ``e0``'s step (pure answer CE) from H on."""
    for group in optimizer.param_groups:
        group['lr'] = V.lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    warm = step < STATE['params']['hint_updates']
    for x, y, weight in ((batch.canonical, batch.canonical_targets, .75),
                         (batch.monolithic, batch.monolithic_targets, .25)):
        loss = (E.loss_for(model, x, y)[0] if warm else V._answer_ce(model, x, y)) * weight
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
    _finish(model, optimizer)


def _step_answer_only(model, optimizer, batch, step):
    """``e0``'s step verbatim: answer CE only, .75/.25, no evidence term at any time."""
    V._step_e0(model, optimizer, batch, step)


def _step_margfull(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = V.lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    one, marg, mono = margfull_losses(model, batch)
    w1, w2, w3 = marg_weights(batch)
    loss = w1*one + w2*marg + w3*mono
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    _finish(model, optimizer)


# -------------------------------------------------------------------------------- logging

@torch.no_grad()
def _probe(model, batch):
    if isinstance(batch, StartupMargBatch):
        one = (model(batch.one_hop).argmax(-1) == batch.one_hop_targets.answer).float().mean()
        mono = (model(batch.monolithic).argmax(-1) == batch.monolithic_answers).float().mean()
        p = marginal_probability(model, batch)
        return dict(one_hop_acc=round(float(one), 4), monolithic_acc=round(float(mono), 4),
                    mean_marginal_probability=round(float(p.mean()), 4))
    correct = model(batch.canonical).argmax(-1) == batch.canonical_targets.answer
    mono = (model(batch.monolithic).argmax(-1) == batch.monolithic_targets.answer).float().mean()
    is_link = batch.canonical.questions[:, 2] == LINK
    return dict(canonical_acc=round(float(correct.float().mean()), 4),
                one_hop_acc=round(float(correct[~is_link].float().mean()), 4),
                link_acc=round(float(correct[is_link].float().mean()), 4),
                monolithic_acc=round(float(mono), 4))


def _hint_active(batch, step):
    if isinstance(batch, StartupMargBatch):
        return bool(batch.plan['hint'])
    return STATE['variant'] == 'hintwarm' and step < STATE['params']['hint_updates']


def _logged(step_fn):
    def logged_step(model, optimizer, batch, step):
        assert step == STATE['step'], (step, STATE['step'])
        step_fn(model, optimizer, batch, step)
        STATE['step'] = step + 1
        for key, value in batch.accounting.get('relations', {}).items():
            STATE['running'][key] = STATE['running'].get(key, 0) + value
        if (step+1) % LOG_EVERY == 0:
            was = model.training
            model.eval()
            probe = _probe(model, batch)
            model.train(was)
            curriculum = batch.accounting.get('curriculum', {})
            kept = curriculum.get('kept_lines')
            print(json.dumps(dict(variant=STATE['variant'], train_batch=step+1, **probe,
                                  hint_active=_hint_active(batch, step),
                                  kept_fraction=curriculum.get('fraction'),
                                  mean_kept_lines=round(sum(kept)/len(kept), 2) if kept else None,
                                  canonical_records_by_relation=dict(STATE['running']))), flush=True)
    return logged_step


def configure_variant(variant, seed=None, **params):
    """Point the unchanged runner at this variant's folder, batch, loss and FLOP counter."""
    assert variant in VARIANTS, variant
    unknown = set(params) - set(DEFAULTS)
    assert not unknown, unknown
    merged = dict(DEFAULTS, **params)
    assert merged['startup'] in STARTUPS, merged['startup']
    assert 0 <= merged['grow_g1'] <= merged['grow_g2']
    STATE.update(variant=variant, seed=seed, step=0, params=merged,
                 vrng=None if seed is None else random.Random(f'fable-startup-{variant}:{seed}'),
                 running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    # training_batch_balance reads fable_operator_variants' own STATE for its RNG; give it
    # this module's stream so every extra draw comes from fable-startup-<variant>:<seed>.
    V.STATE.update(variant=variant, seed=seed, vrng=STATE['vrng'], marg_visits=0)
    R.OUT = out_for(variant)
    A.training_flops = ORIGINAL_FLOPS
    if variant == 'hintwarm':
        A.training_batch, A.training_step = training_batch_hintwarm, _logged(_step_hintwarm)
    elif variant == 'grow':
        A.training_batch, A.training_step = training_batch_grow, _logged(_step_answer_only)
    elif variant == 'grow-blind':
        A.training_batch, A.training_step = training_batch_blind, _logged(_step_answer_only)
    else:
        A.training_batch, A.training_step = training_batch_margfull, _logged(_step_margfull)
        A.training_flops = training_flops_margfull
    return R.OUT


# ------------------------------------------------------------------------------- commands

def _register_key(path):
    """Manifest key that ``check_manifest`` can resolve: ROOT-relative, else absolute."""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def freeze(variant, updates, training_seconds, params):
    OUT = out_for(variant)
    v1 = json.loads((V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    for extra in (Path(V.__file__).resolve(), Path(__file__).resolve(), OUT/'PREREGISTRATION.md'):
        files[_register_key(extra)] = C.sha(extra)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    variant=variant, startup=dict(params),
                    schedule=dict(updates=updates, training_seconds=training_seconds,
                                  work_seconds=training_seconds+240,
                                  terminate_seconds=training_seconds+270, visits_per_update=16),
                    exclusion_path=v1['exclusion_path'], panels=v1['panels'], files=files,
                    v1_launch_sha256=C.sha(V1/'astra_canonical_operator_launch.json'))
    C.write_new(OUT/'astra_canonical_operator_launch.json', manifest)
    print(len(files), 'files frozen', variant, C.sha(OUT/'astra_canonical_operator_launch.json'))


def wave(variant, seeds, name):
    OUT = out_for(variant)
    manifest = R.check_manifest()
    assert manifest.get('variant') == variant, 'manifest/variant mismatch'
    folder = OUT/name
    folder.mkdir(exist_ok=False)
    cap, start = manifest['schedule']['terminate_seconds'], time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    procs = []
    for seed in seeds:
        handle = (folder/f'seed-{seed}.log').open('x')
        procs.append(subprocess.Popen(
            [R.PYTHON, '-B', str(Path(__file__).resolve()), 'worker', '--variant', variant,
             '--seed', str(seed), '--wave-start', str(start)],
            stdout=handle, stderr=subprocess.STDOUT, env=env, start_new_session=True))
    while any(p.poll() is None for p in procs):
        if time.monotonic()-start >= cap-2:
            for p in procs:
                if p.poll() is None: p.terminate()
            time.sleep(.5)
            for p in procs:
                if p.poll() is None: p.kill()
            break
        time.sleep(.5)
    exits = [p.wait() for p in procs]
    complete = all(c == 0 for c in exits) and all(
        (OUT/f'astra_canonical_operator_seed-{s}/completion.json').exists() for s in seeds)
    C.write_new(folder/'completion.json', dict(seconds=time.monotonic()-start, exit_codes=exits,
                complete=complete, seeds=list(seeds), variant=variant))
    print(json.dumps(dict(variant=variant, seconds=time.monotonic()-start,
                          exit_codes=exits, complete=complete)), flush=True)


def registered_params(variant):
    """Hyperparameters exactly as frozen, so a worker cannot silently fall back to a default."""
    manifest = json.loads((out_for(variant)/'astra_canonical_operator_launch.json').read_text())
    assert manifest['variant'] == variant, 'manifest/variant mismatch'
    return dict(DEFAULTS, **manifest.get('startup', {}))


def _params_from(args):
    return dict(balance=args.balance, hint_updates=args.hint_updates, grow_g1=args.grow_g1,
                grow_g2=args.grow_g2, distractors=args.distractors,
                blind_lines=args.blind_lines, startup=args.startup,
                marg_visits=args.marg_visits, terminal_dedupe=args.terminal_dedupe,
                single_forward=args.single_forward)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['freeze', 'wave', 'worker'])
    ap.add_argument('--variant', required=True, choices=list(VARIANTS))
    ap.add_argument('--seeds', default='0,1,2'); ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int); ap.add_argument('--wave-start', type=float)
    ap.add_argument('--updates', type=int, default=6000)
    ap.add_argument('--training-seconds', type=int, default=1500)
    # OFF by default: fresh seeds 3-5 showed the balance rebalancing is not a net win.
    ap.add_argument('--balance', action='store_true', default=DEFAULTS['balance'])
    ap.add_argument('--hint-updates', type=int, default=DEFAULTS['hint_updates'])
    ap.add_argument('--grow-g1', type=int, default=DEFAULTS['grow_g1'])
    ap.add_argument('--grow-g2', type=int, default=DEFAULTS['grow_g2'])
    ap.add_argument('--distractors', type=int, default=DEFAULTS['distractors'])
    ap.add_argument('--blind-lines', type=int, default=DEFAULTS['blind_lines'])
    ap.add_argument('--startup', default=DEFAULTS['startup'], choices=list(STARTUPS))
    # OFF by default (0 = all 16 visits marginalised): the only approximation available.
    ap.add_argument('--marg-visits', type=int, default=0)
    # Both reductions below are EXACT and therefore on by default.
    ap.add_argument('--no-terminal-dedupe', dest='terminal_dedupe', action='store_false')
    ap.add_argument('--no-single-forward', dest='single_forward', action='store_false')
    ap.set_defaults(terminal_dedupe=True, single_forward=True)
    return ap


if __name__ == '__main__':
    args = build_parser().parse_args()
    R.configure()
    R.OUT = out_for(args.variant)
    if args.command == 'worker':
        configure_variant(args.variant, seed=args.seed, **registered_params(args.variant))
        R.worker(args.seed, args.wave_start)
    elif args.command == 'freeze':
        configure_variant(args.variant, seed=None, **_params_from(args))
        freeze(args.variant, args.updates, args.training_seconds, _params_from(args))
    else:
        configure_variant(args.variant, seed=None, **registered_params(args.variant))
        wave(args.variant, [int(s) for s in args.seeds.split(',')], args.name)
