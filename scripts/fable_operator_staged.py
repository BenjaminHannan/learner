"""Staged marginalisation on the grow-blind base (Fable, 2026-09-20 EDT). Additive only.

WHY. ``grow-blind`` (answer CE only, no supporting-line loss ever, random-subset
small-story curriculum growing to full size by update 3,000, gold intermediates used to
build the LINK/terminal single-call records) learns a PERFECT lookup in 3/3 seeds: one-hop
train accuracy reaches 1.0 around update 1,500-3,000. ``marg-full --startup grow-blind``
(same curriculum, but two-hop questions train ONLY through the exact marginal
-log sum_e P(e | S, x, LINK) * P(y | S, e, r); no gold intermediates, so the only
single-call records per visit are the 2 generator one-hop questions) FAILS in 3/3 seeds:
one-hop train accuracy never exceeds ~0.4 and ends at 0.12-0.19, mean marginal probability
~0.22, terminal-with-gold-person ~25-30%, LINK ~6%. Adding the marginal term from update 0
prevents even the one-hop attribute lookup from forming.

Two hypotheses, one variant each:

(i)  the marginal term is pure noise until the terminal attribute lookup is sharp, and it
     dominates the shared weights;
(ii) single-call practice dropped from 6 records per visit (grow-blind) to 2 (marg-full).

``marg-staged``        ONE change vs ``marg-full --startup grow-blind``: the marginal
                       two-hop term carries weight EXACTLY 0 for updates < M
                       (``--marg-start``, default 2500) and its normal weight afterwards.
                       Hard switch, no ramp. Before M the loss is
                       ``w1*one_hop_CE + w3*monolithic_CE`` with w1 and w3 exactly the
                       record weights ``marg-full`` uses on the same batch (the marginal
                       term is removed, NOT renormalised away -- see "Weights" below).
                       The monolithic records are kept exactly as ``marg-full`` has them:
                       answer CE on the full two-hop question, which is label-free.
                       Before M the 16-way terminal expansion and the LINK call are NOT
                       forwarded during training, which is where the time is saved; FLOPs
                       count only the forwards actually performed.

``marg-staged-dense``  ``marg-staged`` plus ONE more change, aimed at (ii): before AND
                       after M, K extra label-free one-hop attribute records per visit
                       (``--extra-onehop``, default 4), built from that visit's own KEPT
                       visible facts with ``fable_operator_startup._one_hop_record`` -- the
                       ``balance`` constructor with entity uniform over the world's six
                       people and relation uniform over (8, 9, 10), rejecting draws whose
                       fact line is not kept. With K = 4 the single-call attribute practice
                       is 6 records per visit, matching ``grow-blind``. These are ordinary
                       final-answer questions about visible facts: no intermediate label.
                       A LINK question is NEVER constructed -- a made-up ``[4, x, 11, 5]``
                       record with its entity answer would be exactly the intermediate
                       label this family is trying to remove. Asserted at construction and
                       again on the packed tensor.

LABEL-FREE IN THE STRICT SENSE, both variants. No gold intermediate entity and no
supporting line ever enters any loss or is used to construct any record. ``row.gold``,
``row.supplied``, ``row.answer``, ``row.hops`` and ``row.relation`` are never read; hop
count and relation come from the visible question tokens, and every answer is read off a
kept visible fact row. The check suite poisons all five fields and asserts the batch, the
losses and every gradient are identical.

DIAGNOSTICS (evaluator-only, logged every 250 updates, never in a loss). Alongside one-hop
train accuracy and mean marginal probability, the log carries the LINK call's argmax
accuracy against the true intermediate and the terminal call's accuracy GIVEN the true
intermediate, on the training batch, so the moment LINK starts to form is visible. The
true intermediate is read off the visit's kept visible ``[world] a LINK b`` row while the
batch is built and stored in ``batch.diagnostics``; no loss function references that field,
which the check suite proves by scrambling it and comparing losses and gradients. The
probe's forwards run under ``torch.no_grad()`` and are NOT counted in training FLOPs,
exactly as ``marg-full``'s probe is not.

CURRICULUM RNG. Extra randomness for the curriculum and for record construction is drawn
from ``random.Random("fable-startup-marg-full:<seed>")`` -- deliberately ``marg-full``'s
own namespace, NOT this module's name, so that the story subsets and the constructed
records are identical to ``marg-full --startup grow-blind`` batch for batch and the "one
change" claim is exact (checked over the first 20 batches). The K extra one-hop records of
``marg-staged-dense`` draw from a SEPARATE stream,
``random.Random("fable-staged-extra-<variant>:<seed>")``, so that adding them does not
shift the curriculum either. The ``random.Random(1101)`` world stream is consumed exactly
as in the base recipe (``toy_ladder.visit`` per visit plus the trailing ``randrange`` per
batch).

WEIGHTS. ``marg_weights`` (reused from ``fable_operator_startup``) gives every RECORD equal
weight. Before M the marginal group's weight is set to zero and the other two keep the
weights they had, so the pre-M loss is literally "``marg-full``'s loss with the marginal
term removed" (total scale 2/3 of a mean, not renormalised to 1). This is the reading of
"weight 0 ... hard switch" that makes the post-M loss byte-for-byte ``marg-full``'s; both
readings are equivalent up to a constant factor under Adam except through gradient
clipping. In ``marg-staged-dense`` the K extra records enlarge the one-hop group, so by the
same equal-weight-per-record rule the groups become (2+K, 2, 2)/(6+K) instead of
(1/3, 1/3, 1/3): with K = 4 that is (0.6, 0.2, 0.2), which mirrors ``grow-blind``'s own
.75/6 = .25/2 = equal weight per record. This is a consequence of the added records, not a
separate choice.

Everything else is unchanged: the same runner (``astra_canonical_operator_run``), the same
model/init/AdamW/clipping, the v3r lr-decay schedule, 6,000 updates, 16 visits per update,
the ``grow-blind`` curriculum (``--blind-lines`` 16 of the 24 fact lines, grown back over
[G1, G2) = [1500, 3000)), the exact 16-way marginal with both EXACT reductions
(``--terminal-dedupe``, ``--single-forward``) on, the same ten panels/cutoffs with
final-checkpoint-only scoring, and the same manifest format.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because
the harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are
prepended to ``sys.path`` so every registered module, the frozen ``premonition`` package,
``ROOT``, the panels and the artifacts folder are the BASE repository's, exactly as for
``scripts/fable_operator_startup.py``. ``fable_operator_startup`` and
``fable_operator_variants`` are imported READ-ONLY and are never modified.
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
VARIANTS = ('marg-staged', 'marg-staged-dense')
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS            # (8, 9, 10)
TWO_HOP_RELATIONS = S.TWO_HOP_RELATIONS                # (8, 9)
COUNTED_OPERATIONS = S.COUNTED_OPERATIONS
ORIGINAL_FLOPS = S.ORIGINAL_FLOPS
LOG_EVERY = S.LOG_EVERY                                # 250
STARTUP = 'grow-blind'
# marg-full's OWN namespace on purpose: the curriculum must match it batch for batch.
CURRICULUM_NAMESPACE = 'fable-startup-marg-full'
EXTRA_NAMESPACE = 'fable-staged-extra'

DEFAULTS = dict(balance=False, grow_g1=1500, grow_g2=3000, blind_lines=16,
                startup=STARTUP, marg_start=2500, extra_onehop=4, marg_visits=0,
                terminal_dedupe=True, single_forward=True)

# Process-local wiring; never serialized, never part of the registered manifest.
STATE = dict(variant=None, seed=None, vrng=None, xrng=None, step=0, params=dict(DEFAULTS),
             running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))


def out_for(variant):
    assert variant in VARIANTS, variant
    return ROOT/f'artifacts/fable-operator-{variant}-20260920'


def normalize_params(variant, params):
    """Merge over DEFAULTS and force the per-variant constants, so freeze and worker agree."""
    assert variant in VARIANTS, variant
    unknown = set(params) - set(DEFAULTS)
    assert not unknown, unknown
    merged = dict(DEFAULTS, **params)
    merged['startup'] = STARTUP
    if variant == 'marg-staged':
        # The one change is the schedule alone: no extra records in this arm, ever.
        merged['extra_onehop'] = 0
    assert 0 <= merged['grow_g1'] <= merged['grow_g2'], (merged['grow_g1'], merged['grow_g2'])
    assert merged['marg_start'] >= 0, merged['marg_start']
    assert merged['extra_onehop'] >= 0, merged['extra_onehop']
    assert merged['blind_lines'] >= 1, merged['blind_lines']
    return merged


# ------------------------------------------------------------------------------- the batch

@dataclass
class StagedBatch(S.StartupMargBatch):
    """``marg-full``'s batch plus (a) K extra one-hop records and (b) evaluator-only fields.

    ``diagnostics`` holds the true intermediate entity of every marginalised two-hop record,
    read off the visit's KEPT VISIBLE ``[world] a LINK b`` row (never from ``row.gold``).
    It exists solely so the 250-update log can show when the LINK call starts to form. No
    loss function in this module -- or in ``fable_operator_startup`` -- reads it.
    """
    diagnostics: dict = field(default_factory=dict)


def training_batch_staged(rng, visits=16, forbidden=frozenset()):
    """``marg-full --startup grow-blind``'s batch, with K extra label-free one-hop records.

    With ``--extra-onehop 0`` this reproduces ``S.training_batch_margfull`` under
    ``--startup grow-blind`` tensor for tensor (checked over the first 20 batches); the
    only differences are the added ``diagnostics`` field and the ``plan['marginal']`` flag
    that tells the loss whether to forward the LINK/terminal groups at all.

    ``row.gold``, ``row.supplied``, ``row.answer``, ``row.hops`` and ``row.relation`` are
    never read. Hop count and relation come from the visible question tokens; every answer
    is read off a kept visible fact row.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng, xrng, p = STATE['vrng'], STATE['xrng'], STATE['params']
    assert vrng is not None and xrng is not None, 'call configure_variant(seed=...) first'
    assert p['startup'] == STARTUP, p['startup']
    extra = p['extra_onehop']
    limit = p['marg_visits'] or visits
    fraction = S.grow_fraction(STATE['step'], p['grow_g1'], p['grow_g2'])
    marginal = STATE['step'] >= p['marg_start']

    memories = []
    one = dict(q=[], owner=[], where=[], answer=[], evidence=[])
    link = dict(q=[], owner=[], where=[])
    term = dict(q=[], owner=[], where=[])
    mono = dict(q=[], owner=[], where=[])
    terminal_rows, two_answers, mono_answers, intermediates = [], [], [], []
    kinds = dict(one_hop=0, marginalised_two_hop=0, monolithic=0)
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0, kept_generator_two_hop=0,
                  replaced_two_hop=0, degraded_two_hop=0, deduped_terminal_calls=0,
                  extra_one_hop=0)
    kept_lines, checked, lines_per_visit = [], 0, 0

    def check(full, q):
        nonlocal checked
        if forbidden and A.visible_signature(full, q) in forbidden:
            raise RuntimeError("training/validation semantic overlap; run invalid")
        checked += 1

    def add_one_hop(entity, relation, answer, line, where, full):
        assert relation in ATTRIBUTE_RELATIONS and relation != LINK, relation
        oq = [QUESTION, entity, relation, ANSWER]
        assert len(oq) == 4 and oq[2] != LINK, oq
        check(full, oq)
        one['q'].append(oq); one['owner'].append(len(memories)-1); one['where'].append(where)
        one['answer'].append(answer); one['evidence'].append([line]*3)
        kinds['one_hop'] += 1

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
        attr, links = S._visible_facts(full, keep)
        attr = {k: (val, index[line]) for k, (val, line) in attr.items()}
        links = {k: (val, index[line]) for k, (val, line) in links.items()}
        terminal_key = {}

        for j, q in asks:
            where = sum(1 for old in keep if old < j)
            if len(q) == 4:
                assert q[2] in ATTRIBUTE_RELATIONS
                entity, relation, (answer, line), replaced = S._one_hop_record(
                    vrng, spec, world, attr, p['balance'], (q[1], q[2]))
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
                add_one_hop(entity, relation, answer, line, where, full)
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
                        S._same_eligibility(memories[v], term['where'][hit], where):
                    census['deduped_terminal_calls'] += 1
                    row_ids.append(hit)
                    continue
                term['q'].append(tq); term['owner'].append(v); term['where'].append(where)
                terminal_key[key] = len(term['q']) - 1
                row_ids.append(len(term['q']) - 1)
            terminal_rows.append(row_ids)
            two_answers.append(answer)
            # EVALUATOR-ONLY, never a target: the true intermediate, read off the kept
            # visible LINK row of this visit. Used by _probe under no_grad; no loss reads it.
            assert ENTITY_MIN <= target < ENTITY_MAX, target
            intermediates.append(target)
            kinds['marginalised_two_hop'] += 1

        # ---- CHANGE (ii), marg-staged-dense only: K extra label-free one-hop records.
        if extra:
            first_question = min(j for j, _ in asks)
            base_where = sum(1 for old in keep if old < first_question)
            # Every kept fact must already be eligible at the first question line; checked
            # directly rather than assumed from the generator's line order.
            assert all(old < first_question for old in keep if S._is_fact(full[old])), \
                'a kept fact line does not precede the first question of this visit'
            for _ in range(extra):
                # ``balance=False`` on purpose: relation uniform over (8, 9, 10). Entity
                # uniform over the world's six people, rejecting draws whose fact line is
                # not kept. ``asked=None`` so no generator question is reused.
                entity, relation, (answer, line), _ = S._one_hop_record(
                    xrng, spec, world, attr, False, None)
                row = memories[v][line]
                assert row[:4] == [WORLD, entity, relation, answer], (row, entity, relation)
                assert relation != LINK, 'a constructed LINK record would be an intermediate label'
                add_one_hop(entity, relation, answer, line, base_where, full)
                census['extra_one_hop'] += 1
    rng.randrange(1 << 30)

    def pack(d):
        return data.pack(memories, d['q'], d['owner'], d['where'])

    ox, lx, tx, mx = pack(one), pack(link), pack(term), pack(mono)
    assert not bool((tx.questions[:, 2] == 10).any()), 'relation 10 must never be a two-hop terminal'
    # The whole point of (ii): extra records are ATTRIBUTE questions. Never a LINK question.
    assert not bool((ox.questions[:, 2] == LINK).any()), 'no constructed one-hop record may be a LINK call'
    assert ox.questions.shape == (kinds['one_hop'], 4)
    assert kinds['one_hop'] == (2 + extra)*visits, (kinds['one_hop'], extra, visits)
    one_targets = E.Targets(torch.tensor(one['answer']), torch.tensor(one['evidence']))
    terminal_index = torch.tensor(terminal_rows, dtype=torch.long) if terminal_rows \
        else torch.zeros(0, ENTITIES, dtype=torch.long)
    assert terminal_index.shape == (kinds['marginalised_two_hop'], ENTITIES)
    # THE ONE CHANGE (i): before M the LINK and terminal groups are not forwarded at all.
    parts = [('one_hop', ox), ('monolithic', mx)] if not marginal else \
        [('one_hop', ox), ('link', lx), ('terminal', tx), ('monolithic', mx)]
    combined, slices = S._concat_inputs(parts) if p['single_forward'] else (None, {})
    plan = dict(single_forward=bool(p['single_forward']), hint=False, slices=slices,
                startup=STARTUP, fraction=round(fraction, 6), marginal=bool(marginal),
                marg_start=int(p['marg_start']))
    records = kinds['one_hop'] + kinds['marginalised_two_hop'] + kinds['monolithic']
    accounting = dict(visits=visits, records=records, kinds=kinds,
                      relations=V._relation_counts(ox.questions, lx.questions, tx.questions),
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0, marg_visits=limit,
                      gold_entities_used=0, gold_fields_used=0, evidence_lines_used=0,
                      marginal_active=bool(marginal), marg_start=int(p['marg_start']),
                      extra_onehop=int(extra), blind=dict(census),
                      diagnostics_are_evaluator_only=True,
                      curriculum=dict(fraction=round(fraction, 6), reduced=True,
                                      kept_lines=kept_lines, original_lines=lines_per_visit),
                      forwards=dict(combined=1 if p['single_forward'] else 0,
                                    separate=len(parts) if not p['single_forward'] else 0,
                                    groups=[name for name, _ in parts]),
                      terminal_calls=int(tx.questions.shape[0]),
                      terminal_calls_undeduped=ENTITIES*kinds['marginalised_two_hop'])
    return StagedBatch(ox, one_targets, lx, tx, terminal_index, torch.tensor(two_answers),
                       mx, torch.tensor(mono_answers), combined, plan, accounting,
                       dict(intermediate=torch.tensor(intermediates, dtype=torch.long)))


def training_flops_staged(batch, model):
    """Honest per-forward count of exactly the forwards ``staged_losses`` performs.

    Before M the LINK and 16-way terminal groups are never forwarded, so they are never
    charged. The every-250-update diagnostic probe is evaluator-only (``torch.no_grad``)
    and is not counted, exactly as ``marg-full``'s probe is not.
    """
    if batch.plan['single_forward']:
        return T.training_flops(batch.combined, model)
    groups = dict(one_hop=batch.one_hop, link=batch.link, terminal=batch.terminal,
                  monolithic=batch.monolithic)
    return sum(T.training_flops(groups[name], model)
               for name in batch.accounting['forwards']['groups'])


# --------------------------------------------------------------------------------- losses

def staged_losses(model, batch):
    """(one, marg, mono); ``marg`` is None before M and is never computed there.

    From M on this delegates to ``S.margfull_losses`` unchanged, so the post-M loss is
    ``marg-full``'s loss on the same batch, expression for expression.
    """
    if batch.plan['marginal']:
        return S.margfull_losses(model, batch)
    assert not batch.plan['hint']
    plan, pieces = batch.plan, {}
    if plan['single_forward']:
        logits = model(batch.combined)
        for name, (start, stop) in plan['slices'].items():
            pieces[name] = logits[start:stop]
    one_logits = pieces.get('one_hop')
    if one_logits is None:
        one_logits = model(batch.one_hop)
    mono_logits = pieces.get('monolithic')
    if mono_logits is None:
        mono_logits = model(batch.monolithic)
    one = F.cross_entropy(one_logits, batch.one_hop_targets.answer)
    mono = F.cross_entropy(mono_logits, batch.monolithic_answers)
    return one, None, mono


def _step_staged(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = V.lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    one, marg, mono = staged_losses(model, batch)
    w1, w2, w3 = S.marg_weights(batch)
    # Post-M this is marg-full's expression verbatim; pre-M it is the same expression with
    # the marginal term at weight zero (w1 and w3 unchanged -- see WEIGHTS in the docstring).
    loss = w1*one + w3*mono if marg is None else w1*one + w2*marg + w3*mono
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    S._finish(model, optimizer)


# -------------------------------------------------------------------------------- logging

@torch.no_grad()
def _probe(model, batch):
    """Evaluator-only. Reads ``batch.diagnostics``; nothing here touches a loss or a grad."""
    one = (model(batch.one_hop).argmax(-1) == batch.one_hop_targets.answer).float().mean()
    mono = (model(batch.monolithic).argmax(-1) == batch.monolithic_answers).float().mean()
    out = dict(one_hop_acc=round(float(one), 4), monolithic_acc=round(float(mono), 4))
    n = int(batch.terminal_index.shape[0])
    if n == 0:
        return dict(out, mean_marginal_probability=None, link_argmax_acc=None,
                    terminal_given_true_acc=None)
    link_logits = model(batch.link)
    terminal_logits = model(batch.terminal)
    probability = S.marginal_probability(model, batch, link_logits, terminal_logits)
    inter = batch.diagnostics['intermediate']
    assert inter.shape == (n,), (inter.shape, n)
    link_acc = (link_logits.argmax(-1) == inter).float().mean()
    rows = batch.terminal_index.gather(1, (inter - ENTITY_MIN)[:, None]).squeeze(1)
    terminal_acc = (terminal_logits[rows].argmax(-1) == batch.two_hop_answers).float().mean()
    return dict(out, mean_marginal_probability=round(float(probability.mean()), 4),
                link_argmax_acc=round(float(link_acc), 4),
                terminal_given_true_acc=round(float(terminal_acc), 4))


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
                                  marginal_active=batch.plan['marginal'],
                                  marg_start=batch.plan['marg_start'],
                                  extra_onehop=batch.accounting['extra_onehop'],
                                  kept_fraction=curriculum.get('fraction'),
                                  mean_kept_lines=round(sum(kept)/len(kept), 2) if kept else None,
                                  canonical_records_by_relation=dict(STATE['running']))), flush=True)
    return logged_step


def configure_variant(variant, seed=None, **params):
    """Point the unchanged runner at this variant's folder, batch, loss and FLOP counter."""
    merged = normalize_params(variant, params)
    STATE.update(
        variant=variant, seed=seed, step=0, params=merged,
        vrng=None if seed is None else random.Random(f'{CURRICULUM_NAMESPACE}:{seed}'),
        xrng=None if seed is None else random.Random(f'{EXTRA_NAMESPACE}-{variant}:{seed}'),
        running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    R.OUT = out_for(variant)
    A.training_batch = training_batch_staged
    A.training_step = _logged(_step_staged)
    A.training_flops = training_flops_staged
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
    for extra in (Path(V.__file__).resolve(), Path(S.__file__).resolve(),
                  Path(__file__).resolve(), OUT/'PREREGISTRATION.md'):
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
    return normalize_params(variant, manifest.get('startup', {}))


def _params_from(args):
    return normalize_params(args.variant, dict(
        balance=args.balance, grow_g1=args.grow_g1, grow_g2=args.grow_g2,
        blind_lines=args.blind_lines, startup=STARTUP, marg_start=args.marg_start,
        extra_onehop=args.extra_onehop, marg_visits=args.marg_visits,
        terminal_dedupe=args.terminal_dedupe, single_forward=args.single_forward))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['freeze', 'wave', 'worker'])
    ap.add_argument('--variant', required=True, choices=list(VARIANTS))
    ap.add_argument('--seeds', default='0,1,2'); ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int); ap.add_argument('--wave-start', type=float)
    ap.add_argument('--updates', type=int, default=6000)
    ap.add_argument('--training-seconds', type=int, default=1500)
    # OFF by default, as in fable_operator_startup: rebalancing is not a net win.
    ap.add_argument('--balance', action='store_true', default=DEFAULTS['balance'])
    ap.add_argument('--grow-g1', type=int, default=DEFAULTS['grow_g1'])
    ap.add_argument('--grow-g2', type=int, default=DEFAULTS['grow_g2'])
    ap.add_argument('--blind-lines', type=int, default=DEFAULTS['blind_lines'])
    # THE staged switch: marginal weight 0 before this update, normal weight from it on.
    ap.add_argument('--marg-start', type=int, default=DEFAULTS['marg_start'])
    # Extra label-free one-hop records per visit; forced to 0 for variant marg-staged.
    ap.add_argument('--extra-onehop', type=int, default=DEFAULTS['extra_onehop'])
    # OFF by default (0 = all 16 visits marginalised): the only approximation available.
    ap.add_argument('--marg-visits', type=int, default=DEFAULTS['marg_visits'])
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
