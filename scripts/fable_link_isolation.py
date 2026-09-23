"""Isolating the LINK call from the terminal lookup (Fable, 2026-09-20 EDT). Additive only.

WHY. Two attempts to learn the LINK call with NO label for the middle person -- only the
final answer y, through the exact marginal ``-log sum_e p_link(e) * p_term(y | e)`` -- have
failed (``marg-full --startup grow-blind``: one-hop train accuracy collapses to 0.12-0.19
and LINK never exceeds ~6%; ``marg-staged``: same marginal switched on at update 2,500).
A reviewer's hypothesis is MUTUAL INTERFERENCE: both calls are the same 79,316-parameter
model, so the terminal lookup is dragged around by LINK's uncertain choices at the same
time as LINK needs a terminal lookup that already tells the sixteen candidates apart.
Detaching the gradient is not enough, because the shared weights still move.

This module tests that hypothesis the only way that settles it: by making the terminal
distribution literally unable to move.

TWO STAGES.

``stage-a``  Train the lookup on SINGLE-CALL ATTRIBUTE questions ONLY -- relations 8, 9, 10,
             never a LINK query, never a two-hop or monolithic record, no evidence loss, no
             gold intermediate. The ``grow-blind`` curriculum (a uniformly random subset of
             the visit's fact lines, recognised from visible tokens only, grown back to the
             full story over [G1, G2)) and the v3r lr shape, both rescaled to the stage
             length (default 3,000 updates). Per visit the batch has one attribute record at
             each of the visit's four question lines -- the generator's own two one-hop
             questions where their fact line is kept, plus a REPLACEMENT attribute question
             at each of the two two-hop question lines -- and K further attribute records
             (``--stage-a-extra``, default 2) at the first question line, i.e. 6 single-call
             attribute records per visit, exactly ``grow-blind``'s record count. The final
             model, the optimizer state and every RNG state are written to ``stage_a.pt``.

``stage-b``  Three arms, each starting from the SAME ``stage_a.pt`` and seeing byte-for-byte
             IDENTICAL batches (the batch builder does not know which arm it is serving; the
             curriculum RNG namespace does not contain the arm; the world RNG continues from
             the state saved in ``stage_a.pt``). Each batch is ``marg-full --startup
             grow-blind``'s batch at curriculum fraction 1 with the MONOLITHIC group removed:
             2 one-hop attribute records and 2 marginalised two-hop records per visit.

  ``shared``            One model. ``loss = w1 * one_hop_CE + w2 * marginal``, both calls
                        inside the trainable model, both receiving gradient. This is the
                        current approach minus the monolithic records.
  ``frozen-terminal``   ``p_term(y | e)`` comes from a deep-copied, ``eval()``,
                        ``requires_grad_(False)`` copy of the stage-A model that is NEVER
                        given to the optimizer and never updated. Only the trainable model's
                        LINK call receives gradient from the marginal term. The one-hop CE on
                        the trainable model stays on, so the ONLY difference from ``shared``
                        is where ``p_term`` comes from.
  ``frozen-terminal-6`` ``frozen-terminal``, plus: the marginal sums only over the people
                        PRESENT in that world -- read from the visible story rows (an entity
                        token that appears as the subject of a visible fact row or as the
                        object of a visible LINK row), never from a label -- and ``p_link`` is
                        RENORMALISED over those people. This tests the reviewer's second
                        point, that 10 of the 16 summed identities are not in the story at all.

WEIGHTS. ``(w1, w2)`` is ``marg-full``'s equal-weight-per-record rule with the monolithic
group REMOVED, not renormalised away: the denominator still counts the monolithic record
that every two-hop question carries in ``marg-full``. At 16 visits that is exactly
``(1/3) * one_hop_CE + (1/3) * marginal``, so the one-hop term keeps the weight it has in
``marg-full`` and the check suite can compare the two expressions at tolerance 0. This is
the same reading ``marg-staged`` used when it dropped the marginal term.

LABEL-FREE IN THE STRICT SENSE. ``row.gold``, ``row.supplied``, ``row.answer``, ``row.hops``
and ``row.relation`` are never read in either stage. Hop count and relation come from the
visible question tokens; every answer is read off a visible fact row. No LINK record ever
receives a target. The check suite poisons all five fields and asserts the batches, the
losses and every gradient are identical.

DIAGNOSTICS (evaluator-only). Every 100 updates of stage B a line is appended to
``diagnostics.jsonl``, and the same measurements are taken on a FIXED held-out probe set
before the first stage-B update and after the last one. The probe sets are 512 fresh two-hop
questions over six-person worlds and 512 over sixteen-person worlds, built before training
starts, checked against the registered exclusion set, and never touched by any loss. The
measurements are: LINK argmax accuracy against the true middle person; the p_link mass on the
true person / wrong-but-present people / absent identities / non-entity tokens; terminal
discriminability ``p_term(y | true e)`` against the mean ``p_term(y | wrong present e)`` and
the fraction of questions where some wrong present person happens to share the answer value
(the "right answer through the wrong person" rate); one-hop accuracy per relation (8, 9, 10)
of the TRAINABLE model; and the two-hop answer accuracy under real two-call execution
(``astra_canonical_operator.execute``), split into right-via-right-person and
right-via-wrong-person. Every label read (the true middle person, the shared-answer rate)
happens in the diagnostic code path and lands in ``batch.diagnostics`` / the probe's own
fields; no loss function reads them, which the check suite proves by scrambling them and
comparing every gradient. ``batch.present`` is NOT a diagnostic: ``frozen-terminal-6`` uses
it in its loss, and it is derived from visible rows only.

COST. The 16-way terminal expansion is the price. Both EXACT reductions from ``marg-full``
are on by default (``--terminal-dedupe``, ``--single-forward``); the frozen arms are cheaper
than ``shared`` because the 16-way expansion is a forward-only ``no_grad`` pass through the
frozen copy and never enters the trainable model's backward.

REGISTERED-RUN PLUMBING. Same discipline as ``fable_operator_staged``: ``freeze`` hashes
every registered source of the v1 launch manifest plus ``fable_operator_variants``,
``fable_operator_startup``, this file and ``PREREGISTRATION.md``; ``check_manifest`` re-
verifies every hash before every worker and every wave and refuses to run on a mismatch.
Unlike the earlier wrappers this module does NOT monkeypatch ``astra_canonical_operator``:
it has its own two-stage worker, so the registered runner's panel scoring is not used here
and the stage-B result is read from the diagnostics, not from the ten panels.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because
the harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are prepended
to ``sys.path`` so every registered module, the frozen ``premonition`` package, ``ROOT``, the
panels and the artifacts folder are the BASE repository's. ``fable_operator_variants`` and
``fable_operator_startup`` are imported READ-ONLY and are never modified.
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
import copy
from dataclasses import dataclass, field
import datetime
import json
import os
import random
import resource
import subprocess
import time
import traceback

import astra_canonical_operator_run as R
import fable_operator_variants as V
import fable_operator_startup as S

A, P, C, torch, ROOT = R.A, R.P, R.C, R.torch, R.ROOT
assert ROOT == BASE, (ROOT, BASE)
assert Path(V.__file__).resolve().parent == BASE/'scripts', V.__file__
assert Path(S.__file__).resolve().parent in (BASE/'scripts', Path(__file__).resolve().parent), S.__file__
E, T, data = A.E, A.T, A.data
F = T.F
V1 = P.OUT
QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS            # (8, 9, 10)
TWO_HOP_RELATIONS = S.TWO_HOP_RELATIONS                # (8, 9)
COUNTED_OPERATIONS = S.COUNTED_OPERATIONS
STAGES = ('a', 'b')
ARMS = ('shared', 'frozen-terminal', 'frozen-terminal-6')
NAME = 'fable-link-isolation-20260920'
# ``FABLE_LINK_ISOLATION_OUT`` exists for ONE purpose: the check suite's 10-update smoke runs
# every subcommand -- including a real ``wave`` with real subprocesses -- into a temporary
# directory, so that nothing is written into the BASE checkout. A registered run never sets
# it; ``freeze`` records which mode it was in and ``wave``/``worker`` refuse to mix the two.
DEV_OUT = os.environ.get('FABLE_LINK_ISOLATION_OUT') or None
OUT = Path(DEV_OUT) if DEV_OUT else ROOT/f'artifacts/{NAME}'
# The preregistration draft lives beside this file's worktree copy; ``freeze`` hashes
# whichever of the two paths exists, and records it by absolute path when it is not in ROOT.
LOCAL_ARTIFACTS = Path(__file__).resolve().parent.parent/'artifacts'/NAME
V3R_UPDATES = 6000                                     # the length the v3r lr shape was written for
LOG_EVERY_A = 250
LOG_EVERY_B = 100
ARCHITECTURE = dict(vocab=68, width=48, heads=4, steps=3)
PARAMETERS = 79316
# Curriculum RNG namespaces. NEITHER contains the arm: the three stage-B arms must draw the
# same story subsets and the same records, batch for batch.
NAMESPACE_A = 'fable-link-isolation-a'
NAMESPACE_A_EXTRA = 'fable-link-isolation-a-extra'
NAMESPACE_B = 'fable-link-isolation-b'
NAMESPACE_PROBE = 'fable-link-isolation-probe'

DEFAULTS = dict(balance=False, blind_lines=16, grow_g1=750, grow_g2=1500, stage_a_extra=2,
                terminal_dedupe=True, single_forward=True,
                probe_six=512, probe_sixteen=512, probe_per_visit=4)

# Process-local wiring; never serialized, never part of the registered manifest.
STATE = dict(stage=None, arm=None, seed=None, step=0, params=dict(DEFAULTS),
             vrng=None, xrng=None, frozen=None,
             running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))


def prereg_path():
    local = LOCAL_ARTIFACTS/'PREREGISTRATION.md'
    return local if local.exists() else OUT/'PREREGISTRATION.md'


def normalize_params(params):
    unknown = set(params) - set(DEFAULTS)
    assert not unknown, unknown
    merged = dict(DEFAULTS, **params)
    assert 0 <= merged['grow_g1'] <= merged['grow_g2'], (merged['grow_g1'], merged['grow_g2'])
    assert merged['blind_lines'] >= 1, merged['blind_lines']
    assert merged['stage_a_extra'] >= 0, merged['stage_a_extra']
    assert merged['probe_six'] >= 1 and merged['probe_sixteen'] >= 1
    assert 1 <= merged['probe_per_visit'] <= 12, merged['probe_per_visit']
    return merged


def lr_at_scaled(step, updates):
    """v3r's lr shape (``fable_operator_variants.lr_at``) rescaled to ``updates`` updates.

    ``lr_at_scaled(s, 6000) == lr_at(s)`` for every integer s, so a 6,000-update stage is
    v3r's schedule verbatim and a 3,000-update stage passes through the same lr at the same
    FRACTION of the run (warm-up over the first 50 updates, flat 1e-3 to 2/3 of the run,
    then linear to 1e-4 at the end).
    """
    assert updates > 0, updates
    return V.lr_at(step * (V3R_UPDATES/updates))


# --------------------------------------------------------------------- visible-row helpers

def _people_present(rows):
    """Entity tokens visible in this visit's KEPT rows. No label, no ``world.ents``.

    A person counts as present when they are the subject of a visible fact row or the object
    of a visible LINK row -- exactly the information ``astra_canonical_operator.truth_paths``
    would read off the same rows.
    """
    people = set()
    for row in rows:
        if not S._is_fact(row):
            continue
        people.add(row[1])
        if row[2] == LINK:
            people.add(row[3])
    return sorted(people)


def _present_mask(people):
    return [1 if entity in people else 0 for entity in range(ENTITY_MIN, ENTITY_MAX)]


# -------------------------------------------------------------------------- stage A batch

@dataclass
class StageABatch:
    one_hop: data.Inputs
    one_hop_targets: E.Targets
    plan: dict
    accounting: dict = field(default_factory=dict)


def training_batch_stage_a(rng, visits=16, forbidden=frozenset()):
    """Single-call ATTRIBUTE records only, on the grow-blind curriculum.

    Per visit: one attribute record at each of the four generator question lines (the
    generator's own one-hop question when its fact line is kept, a replacement drawn from the
    kept facts otherwise, and always a replacement at the two two-hop question lines), plus K
    further attribute records at the first question line. A LINK query is NEVER constructed:
    a ``[4, x, 11, 5]`` record with its entity answer would be exactly the intermediate label
    this whole family is trying to remove. Asserted at construction and on the packed tensor.

    ``row.gold``, ``row.supplied``, ``row.answer``, ``row.hops`` and ``row.relation`` are
    never read; hop count comes from the visible question tokens and every answer is read off
    a kept visible fact row.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng, xrng, p = STATE['vrng'], STATE['xrng'], STATE['params']
    assert vrng is not None and xrng is not None, 'call configure(stage="a", seed=...) first'
    extra = p['stage_a_extra']
    fraction = S.grow_fraction(STATE['step'], p['grow_g1'], p['grow_g2'])

    memories = []
    one = dict(q=[], owner=[], where=[], answer=[], evidence=[])
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0, at_two_hop_line=0,
                  extra_one_hop=0)
    kept_lines, checked, lines_per_visit = [], 0, 0

    def add_one_hop(owner, entity, relation, answer, line, where, full):
        nonlocal checked
        assert relation in ATTRIBUTE_RELATIONS and relation != LINK, relation
        oq = [QUESTION, entity, relation, ANSWER]
        assert len(oq) == 4 and oq[2] != LINK, oq
        if forbidden and A.visible_signature(full, oq) in forbidden:
            raise RuntimeError("training/validation semantic overlap; run invalid")
        checked += 1
        one['q'].append(oq); one['owner'].append(owner); one['where'].append(where)
        one['answer'].append(answer); one['evidence'].append([line]*3)

    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        full = [[] if row.question else list(row.tokens) for row in rows]
        lines_per_visit = len(full)
        asks = [(j, row.tokens[:row.tokens.index(ANSWER)+1])
                for j, row in enumerate(rows) if row.question]
        assert len(asks) == 4
        keep = S._blind_keep(vrng, full, p['blind_lines'], fraction)
        kept_lines.append(len(keep))
        index = {old: new for new, old in enumerate(keep)}
        memories.append([full[old] for old in keep])
        attr, _links = S._visible_facts(full, keep)
        attr = {k: (val, index[line]) for k, (val, line) in attr.items()}

        for j, q in asks:
            where = sum(1 for old in keep if old < j)
            # Two-hop question lines contribute an ATTRIBUTE record, never the two-hop
            # question itself and never its LINK call: ``asked=None`` draws a fresh one.
            asked = (q[1], q[2]) if len(q) == 4 else None
            if asked is None:
                assert len(q) == 5 and q[2] == LINK
                census['at_two_hop_line'] += 1
            entity, relation, (answer, line), replaced = S._one_hop_record(
                vrng, spec, world, attr, p['balance'], asked)
            if asked is not None:
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
            add_one_hop(v, entity, relation, answer, line, where, full)

        if extra:
            first_question = min(j for j, _ in asks)
            base_where = sum(1 for old in keep if old < first_question)
            assert all(old < first_question for old in keep if S._is_fact(full[old])), \
                'a kept fact line does not precede the first question of this visit'
            for _ in range(extra):
                entity, relation, (answer, line), _ = S._one_hop_record(
                    xrng, spec, world, attr, False, None)
                row = memories[v][line]
                assert row[:4] == [WORLD, entity, relation, answer], (row, entity, relation)
                assert relation != LINK, 'a constructed LINK record would be an intermediate label'
                add_one_hop(v, entity, relation, answer, line, base_where, full)
                census['extra_one_hop'] += 1
    rng.randrange(1 << 30)

    ox = data.pack(memories, one['q'], one['owner'], one['where'])
    assert ox.questions.shape == (checked, 4), (ox.questions.shape, checked)
    assert not bool((ox.questions[:, 2] == LINK).any()), 'stage A must never build a LINK query'
    assert set(ox.questions[:, 2].tolist()) <= set(ATTRIBUTE_RELATIONS)
    assert checked == (4 + extra)*visits, (checked, extra, visits)
    targets = E.Targets(torch.tensor(one['answer']), torch.tensor(one['evidence']))
    plan = dict(stage='a', fraction=round(fraction, 6), single_forward=True)
    accounting = dict(visits=visits, records=checked,
                      kinds=dict(one_hop=checked, marginalised_two_hop=0, monolithic=0,
                                 link=0, terminal=0),
                      relations=V._relation_counts(ox.questions),
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0,
                      gold_entities_used=0, gold_fields_used=0, evidence_lines_used=0,
                      stage_a_extra=int(extra), blind=dict(census),
                      diagnostics_are_evaluator_only=True,
                      curriculum=dict(fraction=round(fraction, 6), reduced=True,
                                      kept_lines=kept_lines, original_lines=lines_per_visit))
    return StageABatch(ox, targets, plan, accounting)


def training_flops_stage_a(batch, model):
    """One forward of one group; the logging probe is ``no_grad`` and is not charged."""
    return T.training_flops(batch.one_hop, model)


def stage_a_loss(model, batch):
    """Plain answer cross-entropy over the single record group -- equal weight per record.

    ``grow-blind``'s .75/.25 split is between its canonical and monolithic groups; with the
    monolithic group removed there is one group left, and equal weight per record is its mean.
    """
    return F.cross_entropy(model(batch.one_hop), batch.one_hop_targets.answer)


def _step_stage_a(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = lr_at_scaled(step, STATE['params']['stage_a_updates'])
    optimizer.zero_grad(set_to_none=True)
    loss = stage_a_loss(model, batch)
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    S._finish(model, optimizer)


# -------------------------------------------------------------------------- stage B batch

@dataclass
class StageBBatch:
    one_hop: data.Inputs
    one_hop_answers: torch.Tensor
    link: data.Inputs
    terminal: data.Inputs                # [distinct terminal calls, 4]
    terminal_index: torch.Tensor         # [two_hop_records, 16] -> row of ``terminal``
    two_hop_answers: torch.Tensor
    present: torch.Tensor                # [two_hop_records, 16] bool; VISIBLE-derived, in the loss
    combined_all: object                 # one_hop + link + terminal, for ``shared``
    combined_head: object                # one_hop + link, for the frozen arms
    plan: dict
    accounting: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)   # evaluator-only; no loss reads this


def training_batch_stage_b(rng, visits=16, forbidden=frozenset()):
    """``marg-full --startup grow-blind`` at curriculum fraction 1, minus the monolithic group.

    ARM-INDEPENDENT BY CONSTRUCTION: nothing in this function reads ``STATE['arm']``, and the
    curriculum RNG namespace does not contain the arm, so the three arms see byte-for-byte
    identical batches from the same starting RNG states. The check suite asserts it.

    ``S._blind_keep(..., fraction=1.)`` is called rather than ``range(len(full))`` so the
    kept-line set, the vrng consumption and therefore every record match ``marg-full
    --startup grow-blind`` past its growth window exactly; the check suite compares the two
    batches tensor for tensor and the two losses at tolerance 0.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng, p = STATE['vrng'], STATE['params']
    assert vrng is not None, 'call configure(stage="b", seed=...) first'

    memories = []
    one = dict(q=[], owner=[], where=[], answer=[])
    link = dict(q=[], owner=[], where=[])
    term = dict(q=[], owner=[], where=[])
    terminal_rows, two_answers, present, intermediates, shares = [], [], [], [], []
    kinds = dict(one_hop=0, marginalised_two_hop=0, monolithic=0)
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0, kept_generator_two_hop=0,
                  replaced_two_hop=0, degraded_two_hop=0, deduped_terminal_calls=0)
    people_counts, checked, lines_per_visit = [], 0, 0

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
        keep = S._blind_keep(vrng, full, p['blind_lines'], 1.)
        index = {old: new for new, old in enumerate(keep)}
        memories.append([full[old] for old in keep])
        attr, links = S._visible_facts(full, keep)
        attr = {k: (val, index[line]) for k, (val, line) in attr.items()}
        links = {k: (val, index[line]) for k, (val, line) in links.items()}
        people = _people_present(memories[v])
        people_counts.append(len(people))
        mask = _present_mask(people)
        terminal_key = {}

        for j, q in asks:
            where = sum(1 for old in keep if old < j)
            if len(q) == 4:
                assert q[2] in ATTRIBUTE_RELATIONS
                entity, relation, (answer, line), replaced = S._one_hop_record(
                    vrng, spec, world, attr, p['balance'], (q[1], q[2]))
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
                oq = [QUESTION, entity, relation, ANSWER]
                check(full, oq)
                one['q'].append(oq); one['owner'].append(v); one['where'].append(where)
                one['answer'].append(answer)
                kinds['one_hop'] += 1
                continue
            assert len(q) == 5 and q[2] == LINK and q[3] in TWO_HOP_RELATIONS
            pick, replaced = S._two_hop_record(vrng, attr, links, q[1], q[3])
            if pick is None:
                census['degraded_two_hop'] += 1
                continue
            census['replaced_two_hop' if replaced else 'kept_generator_two_hop'] += 1
            asker, relation = pick
            target, _ = links[asker]
            answer, _ = attr[(target, relation)]
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
                        S._same_eligibility(memories[v], term['where'][hit], where):
                    census['deduped_terminal_calls'] += 1
                    row_ids.append(hit)
                    continue
                term['q'].append(tq); term['owner'].append(v); term['where'].append(where)
                terminal_key[key] = len(term['q']) - 1
                row_ids.append(len(term['q']) - 1)
            terminal_rows.append(row_ids)
            two_answers.append(answer)
            present.append(list(mask))
            kinds['marginalised_two_hop'] += 1
            # ---- EVALUATOR-ONLY from here to the end of the block. The true middle person
            # and the shared-answer flag are labels; no loss function reads them.
            assert ENTITY_MIN <= target < ENTITY_MAX, target
            assert mask[target - ENTITY_MIN], 'the true middle person must be visibly present'
            intermediates.append(target)
            shares.append(int(any(other != target and (other, relation) in attr
                                  and attr[(other, relation)][0] == answer
                                  for other in people)))
    rng.randrange(1 << 30)

    def pack(d):
        return data.pack(memories, d['q'], d['owner'], d['where'])

    ox, lx, tx = pack(one), pack(link), pack(term)
    assert not bool((tx.questions[:, 2] == 10).any()), 'relation 10 must never be a two-hop terminal'
    assert not bool((ox.questions[:, 2] == LINK).any()), 'no one-hop record may be a LINK call'
    assert ox.questions.shape == (kinds['one_hop'], 4) and kinds['one_hop'] == 2*visits
    terminal_index = torch.tensor(terminal_rows, dtype=torch.long) if terminal_rows \
        else torch.zeros(0, ENTITIES, dtype=torch.long)
    assert terminal_index.shape == (kinds['marginalised_two_hop'], ENTITIES)
    parts = [('one_hop', ox), ('link', lx), ('terminal', tx)]
    combined_all, slices_all = S._concat_inputs(parts)
    combined_head, slices_head = S._concat_inputs(parts[:2])
    plan = dict(stage='b', fraction=1., single_forward=bool(p['single_forward']),
                slices_all=slices_all, slices_head=slices_head)
    records = kinds['one_hop'] + kinds['marginalised_two_hop']
    accounting = dict(visits=visits, records=records, kinds=kinds,
                      relations=V._relation_counts(ox.questions, lx.questions, tx.questions),
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0,
                      gold_entities_used=0, gold_fields_used=0, evidence_lines_used=0,
                      blind=dict(census), diagnostics_are_evaluator_only=True,
                      people_per_visit=people_counts,
                      curriculum=dict(fraction=1., reduced=False,
                                      original_lines=lines_per_visit),
                      terminal_calls=int(tx.questions.shape[0]),
                      terminal_calls_undeduped=ENTITIES*kinds['marginalised_two_hop'])
    return StageBBatch(ox, torch.tensor(one['answer']), lx, tx, terminal_index,
                       torch.tensor(two_answers),
                       torch.tensor(present, dtype=torch.bool).reshape(-1, ENTITIES),
                       combined_all, combined_head, plan, accounting,
                       dict(intermediate=torch.tensor(intermediates, dtype=torch.long),
                            shares_answer=torch.tensor(shares, dtype=torch.long)))


# --------------------------------------------------------------------------------- losses

def marginal_from(batch, link_logits, terminal_probabilities, *, restrict=False):
    """P(y) = sum_e p_link[e] * p_term(y | S, e, r) over the sixteen entity tokens.

    ``restrict=False`` is ``fable_operator_startup.marginal_probability`` expression for
    expression: ``p_link`` is the LINK softmax restricted to 52..67 and NOT renormalised, so
    mass on non-entity tokens is lost and therefore penalised.

    ``restrict=True`` (``frozen-terminal-6``) keeps only the people visibly PRESENT in the
    story and renormalises ``p_link`` over them. Mass on absent identities and on non-entity
    tokens is then no longer penalised -- that is the arm, not an oversight.
    """
    n = link_logits.shape[0]
    assert batch.terminal_index.shape == (n, ENTITIES)
    p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]                  # [n, 16]
    pt = terminal_probabilities[batch.terminal_index]                       # [n, 16, V]
    index = batch.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)
    conditional = pt.gather(2, index).squeeze(2)                            # [n, 16]
    if restrict:
        mask = batch.present.to(p1.dtype)
        assert mask.shape == (n, ENTITIES)
        p1 = p1 * mask
        p1 = p1 / p1.sum(1, keepdim=True).clamp_min(1e-12)
        conditional = conditional * mask
    return (p1 * conditional).sum(1)


def stage_b_pieces(model, batch, arm, frozen):
    """(one_logits, link_logits, terminal_probabilities). Only ``shared`` backprops terminals."""
    assert arm in ARMS, arm
    plan = batch.plan
    if arm == 'shared':
        if plan['single_forward']:
            logits = model(batch.combined_all)
            piece = {name: logits[start:stop] for name, (start, stop) in plan['slices_all'].items()}
            one_logits, link_logits, term_logits = (piece['one_hop'], piece['link'],
                                                    piece['terminal'])
        else:
            one_logits = model(batch.one_hop)
            link_logits = model(batch.link)
            term_logits = model(batch.terminal)
        return one_logits, link_logits, term_logits.softmax(-1)
    assert frozen is not None, 'the frozen arms need the frozen stage-A copy'
    assert not frozen.training and not any(q.requires_grad for q in frozen.parameters())
    if plan['single_forward']:
        logits = model(batch.combined_head)
        piece = {name: logits[start:stop] for name, (start, stop) in plan['slices_head'].items()}
        one_logits, link_logits = piece['one_hop'], piece['link']
    else:
        one_logits, link_logits = model(batch.one_hop), model(batch.link)
    with torch.no_grad():
        frozen_terminal = frozen(batch.terminal).softmax(-1)
    return one_logits, link_logits, frozen_terminal


def stage_b_losses(model, batch, arm, frozen=None):
    one_logits, link_logits, terminal_probabilities = stage_b_pieces(model, batch, arm, frozen)
    one = F.cross_entropy(one_logits, batch.one_hop_answers)
    marg = -marginal_from(batch, link_logits, terminal_probabilities,
                          restrict=(arm == 'frozen-terminal-6')).clamp_min(1e-12).log().mean()
    return one, marg


def link_weights(batch):
    """``marg-full``'s equal-weight-per-record rule with the monolithic group REMOVED.

    The denominator still counts the monolithic record every two-hop question carries in
    ``marg-full``, so the one-hop term keeps exactly the weight it has there: at 16 visits
    (32, 32, 32)/96 becomes (1/3, 1/3) and the dropped third is simply absent. Renormalising
    to (1/2, 1/2) would silently double both terms relative to ``marg-full``.
    """
    k = batch.accounting['kinds']
    total = k['one_hop'] + 2*k['marginalised_two_hop']
    assert total > 0
    return k['one_hop']/total, k['marginalised_two_hop']/total


def _step_stage_b(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = lr_at_scaled(step, STATE['params']['stage_b_updates'])
    optimizer.zero_grad(set_to_none=True)
    one, marg = stage_b_losses(model, batch, STATE['arm'], STATE['frozen'])
    w1, w2 = link_weights(batch)
    loss = w1*one + w2*marg
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    S._finish(model, optimizer)


def training_flops_stage_b(batch, model, arm, frozen=None):
    """Honest per-forward count of exactly the forwards ``stage_b_losses`` performs.

    The frozen copy's 16-way expansion is a forward-only ``no_grad`` pass, so it is charged
    at ``A.inference_flops`` (one third of a training forward+backward), not in full.
    """
    if arm == 'shared':
        if batch.plan['single_forward']:
            return T.training_flops(batch.combined_all, model)
        return sum(T.training_flops(x, model)
                   for x in (batch.one_hop, batch.link, batch.terminal))
    head = T.training_flops(batch.combined_head, model) if batch.plan['single_forward'] else \
        T.training_flops(batch.one_hop, model) + T.training_flops(batch.link, model)
    return head + A.inference_flops(batch.terminal, frozen if frozen is not None else model)


# ----------------------------------------------------------------------------- diagnostics

def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


@torch.no_grad()
def link_metrics(link_logits, terminal_probabilities, terminal_index, answers, present,
                 intermediate, shares_answer):
    """Evaluator-only. Every argument but ``intermediate``/``shares_answer`` is visible.

    ``p_link`` masses are reported over the FULL softmax, so true + wrong-present + absent +
    non-entity is exactly 1 whatever the arm does inside its own loss.
    """
    n = int(link_logits.shape[0])
    if n == 0:
        return {}
    p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]
    column = intermediate - ENTITY_MIN
    true_one_hot = F.one_hot(column, ENTITIES).bool()
    present = present.bool()
    assert bool((present & true_one_hot).sum(1).eq(1).all()), 'true person must be present'
    wrong_present = present & ~true_one_hot
    absent = (~present) & ~true_one_hot
    p_true = p1.gather(1, column[:, None]).squeeze(1)
    pt = terminal_probabilities[terminal_index]
    conditional = pt.gather(2, answers[:, None, None].expand(n, ENTITIES, 1)).squeeze(2)
    t_true = conditional.gather(1, column[:, None]).squeeze(1)
    counts = wrong_present.sum(1).clamp_min(1)
    t_wrong = (conditional*wrong_present).sum(1)/counts
    return dict(
        n=n,
        link_accuracy=_round((link_logits.argmax(-1) == intermediate).float().mean()),
        link_accuracy_entity_argmax=_round(((p1.argmax(-1)+ENTITY_MIN) == intermediate).float().mean()),
        p_link_true=_round(p_true.mean()),
        p_link_wrong_present=_round((p1*wrong_present).sum(1).mean()),
        p_link_absent=_round((p1*absent).sum(1).mean()),
        p_link_non_entity=_round((1 - p1.sum(1)).mean()),
        terminal_p_true_person=_round(t_true.mean()),
        terminal_p_wrong_present=_round(t_wrong.mean()),
        terminal_margin=_round((t_true - t_wrong).mean()),
        terminal_true_is_argmax_present=_round(
            (conditional.masked_fill(~present, -1.).argmax(-1) == column).float().mean()),
        shared_answer_rate=_round(shares_answer.float().mean()),
        marginal_probability=_round((p1*conditional).sum(1).mean()))


@torch.no_grad()
def one_hop_by_relation(model, inputs, answers):
    correct = model(inputs).argmax(-1) == answers
    out = dict(one_hop_accuracy=_round(correct.float().mean()))
    for relation in ATTRIBUTE_RELATIONS:
        rows = inputs.questions[:, 2] == relation
        out[f'one_hop_accuracy_r{relation}'] = _round(correct[rows].float().mean()) \
            if bool(rows.any()) else None
    return out


@torch.no_grad()
def train_diagnostics(model, batch, arm, frozen):
    """The every-100-update line. Runs under ``no_grad``; its forwards are not charged."""
    was = model.training
    model.eval()
    try:
        out = one_hop_by_relation(model, batch.one_hop, batch.one_hop_answers)
        if int(batch.terminal_index.shape[0]):
            link_logits = model(batch.link)
            terminal = model(batch.terminal).softmax(-1)
            out.update(link_metrics(link_logits, terminal, batch.terminal_index,
                                    batch.two_hop_answers, batch.present,
                                    batch.diagnostics['intermediate'],
                                    batch.diagnostics['shares_answer']))
            if frozen is not None and arm != 'shared':
                frozen_terminal = frozen(batch.terminal).softmax(-1)
                out['frozen_terminal_margin'] = link_metrics(
                    link_logits, frozen_terminal, batch.terminal_index, batch.two_hop_answers,
                    batch.present, batch.diagnostics['intermediate'],
                    batch.diagnostics['shares_answer'])['terminal_margin']
    finally:
        model.train(was)
    return out


# ------------------------------------------------------------------------ held-out probes

@dataclass
class ProbeChunk:
    link: data.Inputs
    terminal: data.Inputs
    terminal_index: torch.Tensor
    answers: torch.Tensor
    present: torch.Tensor
    monolithic: data.Inputs              # [4, a, 11, r, 5], for real two-call execution
    one_hop: data.Inputs
    one_hop_answers: torch.Tensor
    intermediate: torch.Tensor           # evaluator-only
    shares_answer: torch.Tensor          # evaluator-only


def build_probe(label, n, entities, per_visit, forbidden=frozenset(), chunk_visits=8):
    """A fixed, fresh two-hop probe set. Never enters a loss; built before training starts.

    Full stories (no curriculum reduction), questions drawn by this module's own probe RNG
    from the VISIBLE facts, never the generator's own questions. Every constructed question
    is checked against the registered exclusion set and the run refuses to start on a hit, so
    a collision costs nothing instead of invalidating a finished run.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec(entities=entities)
    prng = random.Random(f'{NAMESPACE_PROBE}:{label}:{entities}:{n}:{per_visit}')
    visits_needed = -(-n // per_visit)
    chunks, overlap, made = [], 0, 0
    for start in range(0, visits_needed, chunk_visits):
        block = min(chunk_visits, visits_needed - start)
        memories = []
        link = dict(q=[], owner=[], where=[])
        term = dict(q=[], owner=[], where=[])
        mono = dict(q=[], owner=[], where=[])
        one = dict(q=[], owner=[], where=[])
        rows_index, answers, present, intermediate, shares, one_answers = [], [], [], [], [], []
        for v in range(block):
            rows, world, _ = visit(spec, prng, training=True)
            assert len(world.ents) == entities
            full = [[] if row.question else list(row.tokens) for row in rows]
            where = len(full)                       # every visible fact line is eligible
            attr, links = S._visible_facts(full, range(len(full)))
            people = _people_present(full)
            assert len(people) == entities, (len(people), entities)
            mask = _present_mask(people)
            memories.append(full)
            terminal_key = {}

            def emit(q):
                nonlocal overlap
                if forbidden and A.visible_signature(full, q) in forbidden:
                    overlap += 1
                return q

            options = sorted((a, r) for a in links for r in TWO_HOP_RELATIONS
                             if (links[a][0], r) in attr)
            take = min(per_visit, len(options), max(0, n - made))
            for asker, relation in prng.sample(options, take):
                target, _ = links[asker]
                answer, _ = attr[(target, relation)]
                lq = emit([QUESTION, asker, LINK, ANSWER])
                link['q'].append(lq); link['owner'].append(v); link['where'].append(where)
                mq = emit([QUESTION, asker, LINK, relation, ANSWER])
                mono['q'].append(mq); mono['owner'].append(v); mono['where'].append(where)
                row_ids = []
                for entity in range(ENTITY_MIN, ENTITY_MAX):
                    tq = emit([QUESTION, entity, relation, ANSWER])
                    key = (relation, entity)
                    hit = terminal_key.get(key)
                    if hit is not None:
                        row_ids.append(hit)
                        continue
                    term['q'].append(tq); term['owner'].append(v); term['where'].append(where)
                    terminal_key[key] = len(term['q']) - 1
                    row_ids.append(len(term['q']) - 1)
                rows_index.append(row_ids)
                answers.append(answer)
                present.append(list(mask))
                intermediate.append(target)
                shares.append(int(any(other != target and (other, relation) in attr
                                      and attr[(other, relation)][0] == answer
                                      for other in people)))
                made += 1
            for relation in ATTRIBUTE_RELATIONS:
                who = people[prng.randrange(len(people))]
                oq = emit([QUESTION, who, relation, ANSWER])
                one['q'].append(oq); one['owner'].append(v); one['where'].append(where)
                one_answers.append(attr[(who, relation)][0])
        if not answers:
            continue

        def pack(d):
            return data.pack(memories, d['q'], d['owner'], d['where'])

        chunks.append(ProbeChunk(
            pack(link), pack(term), torch.tensor(rows_index, dtype=torch.long),
            torch.tensor(answers), torch.tensor(present, dtype=torch.bool),
            pack(mono), pack(one), torch.tensor(one_answers),
            torch.tensor(intermediate, dtype=torch.long),
            torch.tensor(shares, dtype=torch.long)))
    total = sum(int(c.answers.shape[0]) for c in chunks)
    assert total == n, (total, n)
    if overlap:
        raise RuntimeError(f'probe set {label} overlaps the registered exclusion set '
                           f'({overlap} questions); run invalid')
    return dict(label=label, entities=entities, n=total, per_visit=per_visit,
                overlap_with_exclusion_set=0, chunks=chunks)


def _weighted(values, weights):
    """Size-weighted mean over the probe chunks; chunks with no value are left out."""
    pairs = [(v, w) for v, w in zip(values, weights) if v is not None]
    total = sum(w for _, w in pairs)
    if not total:
        return None
    return sum(v*w for v, w in pairs)/total


@torch.no_grad()
def probe_diagnostics(model, probe, frozen=None):
    """Every metric on one fixed probe set, including real two-call execution."""
    was = model.training
    model.eval()
    try:
        rows, sizes, one_rows, one_sizes = [], [], [], []
        execution = dict(n=0, answer_correct=0, via_right_person=0, via_wrong_person=0,
                         link_correct=0, wrong_answer=0, aborted=0)
        frozen_margin = []
        for chunk in probe['chunks']:
            link_logits = model(chunk.link)
            terminal = model(chunk.terminal).softmax(-1)
            row = link_metrics(link_logits, terminal, chunk.terminal_index, chunk.answers,
                               chunk.present, chunk.intermediate, chunk.shares_answer)
            rows.append(row); sizes.append(row['n'])
            if frozen is not None:
                frozen_margin.append(link_metrics(
                    link_logits, frozen(chunk.terminal).softmax(-1), chunk.terminal_index,
                    chunk.answers, chunk.present, chunk.intermediate,
                    chunk.shares_answer)['terminal_margin'])
            one = one_hop_by_relation(model, chunk.one_hop, chunk.one_hop_answers)
            one_rows.append(one); one_sizes.append(int(chunk.one_hop_answers.shape[0]))
            result = A.execute(model, chunk.monolithic)
            for emitted, answer, truth in zip(result['emitted'], chunk.answers.tolist(),
                                              chunk.intermediate.tolist()):
                execution['n'] += 1
                if len(emitted) < 2:
                    execution['aborted'] += 1
                    continue
                execution['link_correct'] += int(emitted[0] == truth)
                if emitted[1] == answer:
                    execution['answer_correct'] += 1
                    execution['via_right_person' if emitted[0] == truth
                              else 'via_wrong_person'] += 1
                else:
                    execution['wrong_answer'] += 1
    finally:
        model.train(was)
    out = dict(label=probe['label'], entities=probe['entities'], n=probe['n'])
    for key in rows[0]:
        if key == 'n':
            continue
        out[key] = _round(_weighted([r[key] for r in rows], sizes))
    for key in one_rows[0]:
        out[key] = _round(_weighted([r[key] for r in one_rows], one_sizes))
    if frozen is not None:
        out['frozen_terminal_margin'] = _round(_weighted(frozen_margin, sizes))
    n = max(1, execution['n'])
    out['execution'] = dict(execution,
                            answer_accuracy=_round(execution['answer_correct']/n),
                            via_right_person_rate=_round(execution['via_right_person']/n),
                            via_wrong_person_rate=_round(execution['via_wrong_person']/n),
                            link_accuracy=_round(execution['link_correct']/n))
    return out


# ------------------------------------------------------------------------------ wiring

def configure(stage, seed=None, arm=None, frozen=None, **params):
    """Set the process-local stage/arm wiring. The arm never reaches the batch builder."""
    assert stage in STAGES, stage
    assert arm is None or arm in ARMS, arm
    merged = normalize_params({k: v for k, v in params.items() if k in DEFAULTS})
    merged['stage_a_updates'] = params.get('stage_a_updates', 3000)
    merged['stage_b_updates'] = params.get('stage_b_updates', 3000)
    namespace = NAMESPACE_A if stage == 'a' else NAMESPACE_B
    STATE.update(stage=stage, arm=arm, seed=seed, step=0, params=merged, frozen=frozen,
                 vrng=None if seed is None else random.Random(f'{namespace}:{seed}'),
                 xrng=None if seed is None else random.Random(f'{NAMESPACE_A_EXTRA}:{seed}'),
                 running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    R.OUT = OUT
    return OUT


def stage_folder(stage, arm=None, seed=None):
    folder = OUT/('stage-a' if stage == 'a' else f'stage-b/{arm}')
    return folder if seed is None else folder/f'seed-{seed}'


# ------------------------------------------------------------------------------- workers

def _save_json(path, value):
    C.write_new(path, value)


def check_manifest():
    """``R.check_manifest`` plus the two invariants this experiment adds."""
    manifest = R.check_manifest()
    assert manifest.get('experiment') == NAME, 'manifest/experiment mismatch'
    assert manifest.get('dev_out') == DEV_OUT, \
        'registered and dev output roots must not be mixed'
    return manifest


def worker_stage_a(seed, wave_start, updates=None, training_seconds=None):
    started = time.monotonic()
    folder = stage_folder('a', seed=seed)
    folder.mkdir(parents=True, exist_ok=False)
    trained = 0
    try:
        manifest = check_manifest()
        schedule = manifest['schedule']['stage_a']
        updates = updates or schedule['updates']
        training_seconds = training_seconds or schedule['training_seconds']
        params = registered_params()
        forbidden = set(json.loads(Path(manifest['exclusion_path']).read_text()))
        configure('a', seed=seed, stage_a_updates=updates, **params)
        model = A.new_model(seed)
        assert model.parameters_count() == PARAMETERS, model.parameters_count()
        initial = C.fingerprint(model)
        optimizer = T.optimizer_for(model)
        rng = random.Random(1101)
        flops = 0
        log = (folder/'log.jsonl').open('x')
        training_start = time.monotonic()
        for step in range(updates):
            R.deadline(wave_start, manifest['schedule']['stage_a']['work_seconds'])
            if time.monotonic()-training_start >= training_seconds:
                raise TimeoutError('registered stage-A training time cap')
            STATE['step'] = step
            batch = training_batch_stage_a(rng, 16, forbidden)
            flops += training_flops_stage_a(batch, model)
            _step_stage_a(model, optimizer, batch, step)
            trained += 1
            for key, value in batch.accounting['relations'].items():
                STATE['running'][key] = STATE['running'].get(key, 0) + value
            if trained % LOG_EVERY_A == 0:
                was = model.training
                model.eval()
                probe = one_hop_by_relation(model, batch.one_hop, batch.one_hop_targets.answer)
                model.train(was)
                line = dict(stage='a', seed=seed, update=trained, **probe,
                            kept_fraction=batch.plan['fraction'],
                            lr=lr_at_scaled(step, updates),
                            seconds=time.monotonic()-training_start,
                            records_by_relation=dict(STATE['running']))
                log.write(json.dumps(line)+'\n'); log.flush()
                print(json.dumps(line), flush=True)
        log.close()
        seconds = time.monotonic()-training_start
        checkpoint = folder/'stage_a.pt'
        torch.save(dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                        torch_rng=torch.get_rng_state(), world_rng=rng.getstate(),
                        vrng=STATE['vrng'].getstate(), xrng=STATE['xrng'].getstate(),
                        seed=seed, updates=trained, params=dict(params),
                        architecture=dict(ARCHITECTURE),
                        launch_sha256=C.sha(OUT/'astra_canonical_operator_launch.json')),
                   checkpoint)
        _save_json(folder/'training.json',
                   dict(stage='a', seed=seed, updates=trained, seconds=seconds, flops=flops,
                        updates_per_second=trained/max(seconds, 1e-9),
                        initial_fingerprint=initial, final_fingerprint=C.fingerprint(model),
                        checkpoint_sha256=C.sha(checkpoint),
                        attribute_records=trained*16*(4+params['stage_a_extra']),
                        link_records=0, two_hop_records=0, monolithic_records=0,
                        gold_entities_used=0, evidence_lines_used=0))
        check_manifest()
        _save_json(folder/'completion.json',
                   dict(stage='a', seed=seed, complete=True, updates=trained,
                        seconds=time.monotonic()-started,
                        wave_elapsed=time.monotonic()-wave_start,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        registered_files_unchanged=True))
    except BaseException as exc:
        _save_json(folder/'failure.json',
                   dict(stage='a', seed=seed, complete=False, updates=trained,
                        seconds=time.monotonic()-started, error=repr(exc),
                        traceback=traceback.format_exc()))
        raise


def load_stage_a(seed):
    path = stage_folder('a', seed=seed)/'stage_a.pt'
    saved = P.load(path)
    assert saved['seed'] == seed, (saved['seed'], seed)
    assert saved['launch_sha256'] == C.sha(OUT/'astra_canonical_operator_launch.json'), \
        'stage_a.pt was produced under a different registered manifest'
    return saved


def worker_stage_b(seed, arm, wave_start, updates=None, training_seconds=None):
    started = time.monotonic()
    folder = stage_folder('b', arm, seed)
    folder.mkdir(parents=True, exist_ok=False)
    trained = 0
    try:
        assert arm in ARMS, arm
        manifest = check_manifest()
        schedule = manifest['schedule']['stage_b']
        updates = updates or schedule['updates']
        training_seconds = training_seconds or schedule['training_seconds']
        params = registered_params()
        forbidden = set(json.loads(Path(manifest['exclusion_path']).read_text()))
        saved = load_stage_a(seed)
        model = A.CanonicalOperator(**saved['architecture'])
        model.load_state_dict(saved['state_dict'], strict=True)
        assert model.parameters_count() == PARAMETERS, model.parameters_count()
        start_fingerprint = C.fingerprint(model)
        # The frozen terminal: a deep copy that the optimizer never sees and nothing updates.
        frozen = copy.deepcopy(model)
        frozen.eval()
        for parameter in frozen.parameters():
            parameter.requires_grad_(False)
        frozen_fingerprint = C.fingerprint(frozen)
        assert frozen_fingerprint == start_fingerprint
        optimizer = T.optimizer_for(model)
        optimizer.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['torch_rng'])
        rng = random.Random()
        rng.setstate(saved['world_rng'])
        configure('b', seed=seed, arm=arm, frozen=frozen, stage_b_updates=updates, **params)
        probes = [build_probe('six', params['probe_six'], 6, params['probe_per_visit'], forbidden),
                  build_probe('sixteen', params['probe_sixteen'], ENTITIES,
                              params['probe_per_visit'], forbidden)]
        diagnostics = (folder/'diagnostics.jsonl').open('x')

        def write(line):
            diagnostics.write(json.dumps(line)+'\n')
            diagnostics.flush()
            print(json.dumps(line), flush=True)

        initial = [probe_diagnostics(model, probe, frozen) for probe in probes]
        write(dict(stage='b', arm=arm, seed=seed, update=0, kind='probe',
                   probes={p['label']: p for p in initial}))
        model.train()
        flops = 0
        training_start = time.monotonic()
        for step in range(updates):
            R.deadline(wave_start, schedule['work_seconds'])
            if time.monotonic()-training_start >= training_seconds:
                raise TimeoutError('registered stage-B training time cap')
            STATE['step'] = step
            batch = training_batch_stage_b(rng, 16, forbidden)
            flops += training_flops_stage_b(batch, model, arm, frozen)
            _step_stage_b(model, optimizer, batch, step)
            trained += 1
            for key, value in batch.accounting['relations'].items():
                STATE['running'][key] = STATE['running'].get(key, 0) + value
            if trained % LOG_EVERY_B == 0:
                write(dict(stage='b', arm=arm, seed=seed, update=trained, kind='train',
                           lr=lr_at_scaled(step, updates),
                           seconds=time.monotonic()-training_start,
                           **train_diagnostics(model, batch, arm, frozen)))
        seconds = time.monotonic()-training_start
        final = [probe_diagnostics(model, probe, frozen) for probe in probes]
        write(dict(stage='b', arm=arm, seed=seed, update=trained, kind='probe',
                   probes={p['label']: p for p in final}))
        diagnostics.close()
        assert C.fingerprint(frozen) == frozen_fingerprint, 'the frozen copy moved'
        assert all(not q.requires_grad for q in frozen.parameters())
        assert all(q.grad is None for q in frozen.parameters())
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, arm=arm, updates=trained,
                        architecture=dict(ARCHITECTURE),
                        launch_sha256=C.sha(OUT/'astra_canonical_operator_launch.json')),
                   checkpoint)
        _save_json(folder/'final_probe.json',
                   dict(stage='b', arm=arm, seed=seed, updates=trained, seconds=seconds,
                        updates_per_second=trained/max(seconds, 1e-9), flops=flops,
                        stage_a_fingerprint=start_fingerprint,
                        frozen_fingerprint=frozen_fingerprint,
                        frozen_unchanged=C.fingerprint(frozen) == frozen_fingerprint,
                        final_fingerprint=C.fingerprint(model),
                        checkpoint_sha256=C.sha(checkpoint),
                        initial={p['label']: p for p in initial},
                        final={p['label']: p for p in final}))
        check_manifest()
        _save_json(folder/'completion.json',
                   dict(stage='b', arm=arm, seed=seed, complete=True, updates=trained,
                        seconds=time.monotonic()-started,
                        wave_elapsed=time.monotonic()-wave_start,
                        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        final_checkpoint_only=True, frozen_weights_unchanged=True,
                        registered_files_unchanged=True))
    except BaseException as exc:
        _save_json(folder/'failure.json',
                   dict(stage='b', arm=arm, seed=seed, complete=False, updates=trained,
                        seconds=time.monotonic()-started, error=repr(exc),
                        traceback=traceback.format_exc()))
        raise


# ------------------------------------------------------------------------------- commands

def _register_key(path):
    """Manifest key that ``check_manifest`` can resolve: ROOT-relative, else absolute."""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def freeze(schedule, params):
    assert DEV_OUT or params['probe_six'] >= 512, \
        'the registered six-person probe set must be >= 512 questions'
    v1 = json.loads((V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    for extra in (Path(V.__file__).resolve(), Path(S.__file__).resolve(),
                  Path(__file__).resolve(), prereg_path()):
        files[_register_key(extra)] = C.sha(extra)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    experiment=NAME, arms=list(ARMS), params=dict(params),
                    schedule=schedule, exclusion_path=v1['exclusion_path'],
                    panels=v1['panels'], files=files, dev_out=DEV_OUT,
                    v1_launch_sha256=C.sha(V1/'astra_canonical_operator_launch.json'))
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_new(OUT/'astra_canonical_operator_launch.json', manifest)
    print(len(files), 'files frozen', NAME, C.sha(OUT/'astra_canonical_operator_launch.json'))


def registered_params():
    """Hyperparameters exactly as frozen, so a worker cannot fall back to a default."""
    manifest = json.loads((OUT/'astra_canonical_operator_launch.json').read_text())
    assert manifest['experiment'] == NAME, 'manifest/experiment mismatch'
    return normalize_params(manifest.get('params', {}))


def wave(stage, arm, seeds, name):
    manifest = check_manifest()
    if stage == 'b':
        assert arm in ARMS, arm
        for seed in seeds:
            assert (stage_folder('a', seed=seed)/'stage_a.pt').exists(), \
                f'stage A has not been run for seed {seed}'
    schedule = manifest['schedule']['stage_a' if stage == 'a' else 'stage_b']
    folder = stage_folder(stage, arm)/name
    folder.mkdir(parents=True, exist_ok=False)
    cap, start = schedule['terminate_seconds'], time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    procs = []
    for seed in seeds:
        handle = (folder/f'seed-{seed}.log').open('x')
        args = [R.PYTHON, '-B', str(Path(__file__).resolve()), 'worker', '--stage', stage,
                '--seed', str(seed), '--wave-start', str(start)]
        if stage == 'b':
            args += ['--arm', arm]
        procs.append(subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, env=env,
                                      start_new_session=True))
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
        (stage_folder(stage, arm, s)/'completion.json').exists() for s in seeds)
    C.write_new(folder/'completion.json',
                dict(seconds=time.monotonic()-start, exit_codes=exits, complete=complete,
                     seeds=list(seeds), stage=stage, arm=arm))
    print(json.dumps(dict(stage=stage, arm=arm, seconds=time.monotonic()-start,
                          exit_codes=exits, complete=complete)), flush=True)


# -------------------------------------------------------------------------------- report

REPORT_COLUMNS = (('link_accuracy', 'LINK acc'), ('p_link_true', 'p(true)'),
                  ('p_link_wrong_present', 'p(wrong)'), ('p_link_absent', 'p(absent)'),
                  ('p_link_non_entity', 'p(non-ent)'), ('terminal_p_true_person', 'pT(true)'),
                  ('terminal_p_wrong_present', 'pT(wrong)'), ('terminal_margin', 'margin'),
                  ('shared_answer_rate', 'shared y'), ('one_hop_accuracy_r8', '1hop r8'),
                  ('one_hop_accuracy_r9', '1hop r9'), ('one_hop_accuracy_r10', '1hop r10'))


def _cell(value):
    return '  --  ' if value is None else f'{value:6.3f}'


def report(seeds, arms=ARMS, root=None):
    """Per-seed, per-arm. Nothing is ever averaged across seeds."""
    root = Path(root) if root else OUT
    for label in ('six', 'sixteen'):
        print(f'\n=== held-out probe: {label}-person worlds '
              f'(initial = stage A, final = after stage B) ===')
        header = f'{"seed":>4} {"arm":<18} {"when":<8} ' + ' '.join(
            f'{title:>10}' for _, title in REPORT_COLUMNS) + f' {"exec":>7} {"via-R":>7} {"via-W":>7}'
        print(header)
        print('-'*len(header))
        for seed in seeds:
            for arm in arms:
                path = root/f'stage-b/{arm}/seed-{seed}/final_probe.json'
                if not path.exists():
                    print(f'{seed:>4} {arm:<18} {"(missing)":<8}')
                    continue
                blob = json.loads(path.read_text())
                for when in ('initial', 'final'):
                    row = blob[when][label]
                    cells = ' '.join(f'{_cell(row.get(key)):>10}' for key, _ in REPORT_COLUMNS)
                    ex = row['execution']
                    print(f'{seed:>4} {arm:<18} {when:<8} {cells} '
                          f'{_cell(ex["answer_accuracy"]):>7} '
                          f'{_cell(ex["via_right_person_rate"]):>7} '
                          f'{_cell(ex["via_wrong_person_rate"]):>7}')
    print('\npass mark: LINK accuracy >= 0.90 on the six-person probe set, PER SEED.')
    for seed in seeds:
        for arm in arms:
            path = root/f'stage-b/{arm}/seed-{seed}/final_probe.json'
            if not path.exists():
                print(f'  seed {seed} {arm:<18} (missing)')
                continue
            value = json.loads(path.read_text())['final']['six']['link_accuracy']
            print(f'  seed {seed} {arm:<18} LINK {_cell(value)} '
                  f'{"PASS" if value is not None and value >= .90 else "fail"}')


# ---------------------------------------------------------------------------------- main

def default_schedule(args):
    return dict(
        visits_per_update=16,
        stage_a=dict(updates=args.stage_a_updates, training_seconds=args.stage_a_seconds,
                     work_seconds=args.stage_a_seconds+240,
                     terminate_seconds=args.stage_a_seconds+270),
        stage_b=dict(updates=args.stage_b_updates, training_seconds=args.stage_b_seconds,
                     work_seconds=args.stage_b_seconds+240,
                     terminate_seconds=args.stage_b_seconds+270))


def _params_from(args):
    return normalize_params(dict(
        balance=args.balance, blind_lines=args.blind_lines, grow_g1=args.grow_g1,
        grow_g2=args.grow_g2, stage_a_extra=args.stage_a_extra,
        terminal_dedupe=args.terminal_dedupe, single_forward=args.single_forward,
        probe_six=args.probe_six, probe_sixteen=args.probe_sixteen,
        probe_per_visit=args.probe_per_visit))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['freeze', 'wave', 'worker', 'report'])
    ap.add_argument('--stage', choices=list(STAGES))
    ap.add_argument('--arm', choices=list(ARMS))
    ap.add_argument('--seeds', default='0,1,2')
    ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int)
    ap.add_argument('--wave-start', type=float)
    ap.add_argument('--root', default=None, help='report only: read from this folder')
    ap.add_argument('--stage-a-updates', type=int, default=3000)
    ap.add_argument('--stage-b-updates', type=int, default=3000)
    # Measured single-process, one torch thread, with the real exclusion set loaded:
    # stage A 25.7 updates/s (117 s for 3,000), stage B 4.17 (shared) / 6.45 / 6.56 updates/s
    # (719 / 465 / 457 s for 3,000). The caps below leave ~1.5x headroom for a 3-seed wave and
    # keep terminate_seconds under the 25-minute wave rule (690 s stage A, 1,470 s stage B).
    ap.add_argument('--stage-a-seconds', type=int, default=420)
    ap.add_argument('--stage-b-seconds', type=int, default=1200)
    ap.add_argument('--balance', action='store_true', default=DEFAULTS['balance'])
    ap.add_argument('--blind-lines', type=int, default=DEFAULTS['blind_lines'])
    ap.add_argument('--grow-g1', type=int, default=DEFAULTS['grow_g1'])
    ap.add_argument('--grow-g2', type=int, default=DEFAULTS['grow_g2'])
    ap.add_argument('--stage-a-extra', type=int, default=DEFAULTS['stage_a_extra'])
    ap.add_argument('--probe-six', type=int, default=DEFAULTS['probe_six'])
    ap.add_argument('--probe-sixteen', type=int, default=DEFAULTS['probe_sixteen'])
    ap.add_argument('--probe-per-visit', type=int, default=DEFAULTS['probe_per_visit'])
    # Both reductions below are EXACT and therefore on by default.
    ap.add_argument('--no-terminal-dedupe', dest='terminal_dedupe', action='store_false')
    ap.add_argument('--no-single-forward', dest='single_forward', action='store_false')
    ap.set_defaults(terminal_dedupe=True, single_forward=True)
    return ap


if __name__ == '__main__':
    args = build_parser().parse_args()
    R.configure()
    R.OUT = OUT
    seeds = [int(s) for s in args.seeds.split(',')]
    if args.command == 'freeze':
        params = _params_from(args)
        assert args.grow_g2 <= args.stage_a_updates, 'the curriculum must finish inside stage A'
        freeze(default_schedule(args), params)
    elif args.command == 'report':
        report(seeds, root=args.root)
    elif args.command == 'worker':
        assert args.stage in STAGES and args.seed is not None
        if args.stage == 'a':
            worker_stage_a(args.seed, args.wave_start)
        else:
            worker_stage_b(args.seed, args.arm, args.wave_start)
    else:
        wave(args.stage, args.arm, seeds, args.name)
