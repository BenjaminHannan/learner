"""Why does the short-story curriculum let answer-only learning START? (Fable, 2026-09-20 EDT)

Additive only. Nothing registered is edited; every artefact this file writes goes to
``<worktree>/artifacts/fable-startup-factorial-20260920``.

THE QUESTION. ``e0`` (answer cross-entropy only, full ~45-line stories from update 0)
learns perfectly on seed 0 and never starts on seeds 1 and 2. ``grow-blind`` (the same
loss, but for updates < 1500 each visit keeps only 16 uniformly random fact lines of its
24 and NO filler/gap lines, with the questions rebuilt to be answerable from those 16)
starts on 6/6 seeds. ``grow-blind``'s early phase changes THREE things at once:

  1. the filler and gap lines are gone (~21 lines, ~2/3 of the tokens),
  2. only 16 of the 24 competing fact lines remain,
  3. questions that the kept facts cannot answer are replaced.

This file separates 1 and 2 while holding 3 EXACTLY constant, by construction.

PART 1 -- 2x2 factorial on the early condition, held CONSTANT for the whole run.

    arm   fact lines   filler/gap lines
    A         16             none        (= ``grow-blind``'s early phase, verbatim)
    B         16             all
    C         24             none
    D         24             all         (= the full story, i.e. ``e0``)

  The four arms share ONE plan per (seed, update): the same worlds from the same
  ``random.Random(1101)`` stream, the same 16-fact subset drawn label-free by
  ``fable_operator_startup._blind_keep(vrng, rows, 16, 0.0)``, and the same records built
  from those 16 facts by ``grow-blind``'s own constructors. Arms C/D then add the other 8
  fact lines back; arms B/D add the filler and gap lines back, in original order. So the
  questions, the answers and the supporting facts are BIT-IDENTICAL in all four arms at
  every update, and the arms differ only in which story rows the model may read.

  THE RECORD RECIPE, stated exactly (it is ``grow-blind``'s, unchanged). Per visit, from
  the 16 kept fact lines only:
    * each of the generator's two one-hop questions -> one ``one_hop`` canonical record.
      The generator's question is used unchanged when its fact line is kept; otherwise it
      is replaced by ``balance``'s constructor (entity uniform over the world's six
      people, relation uniform 1/3 each), rejecting draws whose fact line is not kept.
    * each of the generator's two two-hop questions -> a ``link`` record [4, a, 11, 5]
      answered by the kept LINK row, a ``terminal`` record [4, b, r, 5] answered by the
      kept attribute row, and a five-token ``monolithic`` record [4, a, 11, r, 5]. The
      generator's (a, r) is used when both lines are kept, else a fresh (a, r) is drawn
      uniformly from the pairs that ARE answerable from the kept facts.
    * safety valve, counted and never silent: if the kept facts support no two-hop
      question at all, a one-hop record is emitted in its place.
    * hop count and relation come from the VISIBLE question tokens; every answer and
      every supporting line is read off a kept visible fact row. ``row.gold``,
      ``row.supplied``, ``row.answer``, ``row.hops`` and ``row.relation`` are never read.
    * WHAT IS STILL SUPERVISED: the link/terminal decomposition hands the model the true
      intermediate entity as a target. ``grow-blind`` reads it off the visible
      ``[world] a LINK b`` row instead of from ``row.gold``; that removes the annotation,
      not the supervision. This file inherits that exactly and claims nothing more.
  LOSS: pure answer cross-entropy, 0.75 x canonical + 0.25 x monolithic, two backward
  passes, clip 1.0, AdamW as registered -- ``fable_operator_variants._step_e0`` verbatim.
  There is NO supporting-line attention term at any update, in any arm.
  LEARNING RATE: the registered constant phase, ``1e-3 * min(1, (step+1)/100)``, which is
  ``fable_operator_variants.lr_at(step)`` for every step < 4000. The default run is 2,500
  updates, so the whole Part 1 run sits inside that constant phase. There is NO growth:
  the condition is held fixed, because the question is which condition lets learning
  START, not whether a started model survives growth.

  DIAGNOSTICS, every ``--log-every`` (default 50) updates on a FIXED probe batch:
    (1) attention mass on the correct supporting line, per read step and per head, with
        the value expected under uniform-over-eligible-tokens attention for that story;
    (2) the ROUTING GRADIENT: how one plain SGD step on the answer loss alone changes the
        correct-line mass. Reported as the exact directional derivative
        d/d(eta) mass(theta - eta * grad L) |_(eta=0) = -<grad L, grad mass>, and as the
        finite difference mass(theta - eta grad L) - mass(theta) at ``--routing-eta``,
        with both gradient norms and their cosine. This is how we see whether answer-loss
        updates push attention onto the right line BEFORE accuracy moves;
    (3) the distribution of predicted answers (distinct count, top-1 share, entropy) and
        one-hop accuracy per relation;
    (4) train loss/accuracy on that update's real batch, and probe loss/accuracy.
  Every diagnostic runs either under ``torch.no_grad`` or on a ``deepcopy`` of the model.
  The live model's parameters and ``.grad`` are never touched; the check suite poisons
  ``.grad`` with sentinels and proves a logged run and a silent run end bit-identical.

  END OF RUN: the final checkpoint is scored on the registered ``c1`` one-hop panel (512
  full-size 6-person questions), which is READ-ONLY -- the panel file is loaded and its
  sha256 re-verified, and nothing is written inside any registered folder. Its semantics
  are in the registered exclusion set, which this run enforces on every training record,
  so c1 is unseen. A fresh 512-question full-story probe set is scored alongside it.

PART 2 -- ``size-sweep``. Take the arm-A checkpoint (trained only in condition A, no
  growth, no further updates) and evaluate it with NO training on fresh probe sets of
  increasing story size: fact lines {16, 24} x filler fraction {0, 0.5, 1.0}, plus
  16-person worlds at one hop. Reports one-hop accuracy and correct-line attention per
  cell. This asks whether the short-story model already holds a size-independent rule.

PART 3 -- ``extend``. Condition D for 18,000 updates under a declared schedule (warmup to
  1e-3 over 100 updates, constant to update 16,000, linear to 1e-4 at 18,000), with a
  checkpoint every ``--chunk-seconds`` (default 1,200 s) so a wave stays under 30 minutes.
  Resume restores the model, the optimizer, the torch RNG state and BOTH data-stream RNG
  states exactly; the check suite proves a split run equals an unsplit run bit-for-bit.

REPORTING: per seed, never averaged.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because
the harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are
prepended to ``sys.path``, so every registered module, the frozen ``premonition`` package,
``ROOT``, the panels and the exclusion set are the BASE repository's -- exactly as for
``scripts/fable_operator_startup.py``. Only ``OUT`` is worktree-local.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
HERE = Path(__file__).resolve().parent
if HERE != (BASE/'scripts'):
    for entry in (str(BASE), str(BASE/'scripts')):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import copy
import datetime
from dataclasses import dataclass, field
import gc
import json
import math
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
assert Path(S.__file__).resolve().parent == BASE/'scripts', S.__file__
E, T, data = A.E, A.T, A.data
F = T.F
V1 = P.OUT
QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS
TWO_HOP_RELATIONS = S.TWO_HOP_RELATIONS

# OUT is worktree-local on purpose: nothing is ever written inside a registered folder.
OUT = HERE.parent/'artifacts/fable-startup-factorial-20260920'
PREREG = OUT/'PREREGISTRATION.md'

# The 2x2. ``facts`` = how many of the visit's 24 fact lines the model may read;
# ``filler`` = whether the filler and gap lines are present.
ARMS = {'A': dict(facts=16, filler=False, note="grow-blind's early phase"),
        'B': dict(facts=16, filler=True, note='fewer facts, full filler'),
        'C': dict(facts=24, filler=False, note='all facts, no filler'),
        'D': dict(facts=24, filler=True, note='the full story (= e0)')}
ARM_NAMES = tuple(ARMS)
BLIND_LINES = 16                      # grow-blind's --blind-lines default; arms A/B use it
DEFAULT_UPDATES = 2500
DEFAULT_VISITS = 16
DEFAULT_PROBE_VISITS = 16
DEFAULT_LOG_EVERY = 50
DEFAULT_ROUTING_ETA = 1e-2
# "Start" is FIXED here and nowhere else: one-hop TRAIN accuracy >= 0.9 on every logged
# probe of the last 200 updates. See the preregistration.
START_ACCURACY = .9
START_WINDOW = 200


def _num(x):
    """JSON-safe float; C.write_new refuses NaN/Inf."""
    x = float(x.detach()) if torch.is_tensor(x) else float(x)
    return round(x, 8) if math.isfinite(x) else None


# =============================================================================== the plan
# The plan is ARM-INDEPENDENT by construction: it is drawn before any arm is chosen and
# reads only the 16-fact subset. That is what makes the four arms share their questions.

@dataclass
class VisitPlan:
    full: list          # every row of the visit, question rows blanked (original order)
    kept16: list        # sorted ORIGINAL indices of the 16 label-free fact lines
    facts: list         # sorted ORIGINAL indices of all 24 fact lines
    others: list        # sorted ORIGINAL indices of every non-fact, non-empty line
    records: list       # dicts: dst/q/where/answer/lines(ORIGINAL)/kind


def plan_batch(rng, vrng, visits=DEFAULT_VISITS, forbidden=frozenset(),
               blind_lines=BLIND_LINES, balance=False):
    """One update's worlds, 16-fact subsets and records -- identical for all four arms.

    ``rng`` is the registered ``random.Random(1101)`` world stream, consumed exactly as in
    the base recipe (``toy_ladder.visit`` per visit plus the trailing ``randrange``).
    ``vrng`` is the variant stream; every extra draw goes through ``grow-blind``'s own
    helpers, so at fraction 0 this reproduces ``grow-blind``'s early batch bit-for-bit.
    The overlap audit is taken against the FULL story, as in ``grow-blind``: a reduced
    story is a subset of it, so the full-story check is the conservative one.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    plans, checked = [], 0
    census = dict(kept_generator_one_hop=0, replaced_one_hop=0, kept_generator_two_hop=0,
                  replaced_two_hop=0, degraded_two_hop=0)

    for _ in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        full = [[] if row.question else list(row.tokens) for row in rows]
        # Hop count and relation come from the VISIBLE question tokens only.
        asks = [(j, row.tokens[:row.tokens.index(ANSWER)+1])
                for j, row in enumerate(rows) if row.question]
        assert len(asks) == 4
        facts, others = S._row_classes(full)
        # grow-blind's own selector at fraction 0: exactly `blind_lines` fact lines, no
        # filler, no gap line, drawn uniformly and label-free from the visible fact rows.
        kept16 = S._blind_keep(vrng, full, blind_lines, 0.)
        assert kept16 == sorted(set(kept16)) and set(kept16) <= set(facts)
        assert len(kept16) == min(blind_lines, len(facts))
        # ORIGINAL line indices here; each arm remaps them to its own row numbering.
        attr, links = S._visible_facts(full, kept16)
        records = []

        def add(dst, q, where, answer, lines, kind):
            nonlocal checked
            if forbidden and A.visible_signature(full, q) in forbidden:
                raise RuntimeError('training/validation semantic overlap; run invalid')
            checked += 1
            records.append(dict(dst=dst, q=list(q), where=where, answer=answer,
                                lines=list(lines), kind=kind))

        for j, q in asks:
            if len(q) == 4:
                assert q[2] in ATTRIBUTE_RELATIONS
                entity, relation, (answer, line), replaced = S._one_hop_record(
                    vrng, spec, world, attr, balance, (q[1], q[2]))
                census['replaced_one_hop' if replaced else 'kept_generator_one_hop'] += 1
                add('c', [QUESTION, entity, relation, ANSWER], j, answer, [line]*3, 'one_hop')
                continue
            assert len(q) == 5 and q[2] == LINK and q[3] in TWO_HOP_RELATIONS
            pick, replaced = S._two_hop_record(vrng, attr, links, q[1], q[3])
            if pick is None:
                census['degraded_two_hop'] += 1
                entity, relation, (answer, line), _ = S._one_hop_record(
                    vrng, spec, world, attr, balance, None)
                add('c', [QUESTION, entity, relation, ANSWER], j, answer, [line]*3, 'one_hop')
                add('m', [QUESTION, entity, relation, ANSWER], j, answer, [line]*3, 'monolithic')
                continue
            census['replaced_two_hop' if replaced else 'kept_generator_two_hop'] += 1
            asker, relation = pick
            target, link_line = links[asker]
            answer, endpoint_line = attr[(target, relation)]
            add('c', [QUESTION, asker, LINK, ANSWER], j, target, [link_line]*3, 'link')
            add('c', [QUESTION, target, relation, ANSWER], j, answer, [endpoint_line]*3, 'terminal')
            add('m', [QUESTION, asker, LINK, relation, ANSWER], j, answer,
                [link_line, endpoint_line, endpoint_line], 'monolithic')
        plans.append(VisitPlan(full, kept16, facts, others, records))
    rng.randrange(1 << 30)
    return plans, dict(census=census, records=checked)


def arm_keep(plan, arm):
    """Sorted ORIGINAL line indices this arm keeps. Original order is preserved."""
    cfg = ARMS[arm]
    keep = set(plan.kept16) if cfg['facts'] == BLIND_LINES else set(plan.facts)
    assert cfg['facts'] in (BLIND_LINES, len(plan.facts))
    if cfg['filler']:
        keep.update(plan.others)
    return sorted(keep)


def materialise(plans, arm, forbidden_checked=0, census=None):
    """Turn one plan into this arm's ``A.TrainingBatch``. Only the story rows differ."""
    assert arm in ARMS, arm
    memories = []
    c, m = (dict(q=[], owner=[], where=[], answer=[], evidence=[]) for _ in range(2))
    kinds = dict(one_hop=0, link=0, terminal=0, monolithic=0)
    kept_lines, original_lines = [], 0
    for v, plan in enumerate(plans):
        keep = arm_keep(plan, arm)
        index = {old: new for new, old in enumerate(keep)}
        memories.append([plan.full[old] for old in keep])
        kept_lines.append(len(keep))
        original_lines = len(plan.full)
        for rec in plan.records:
            dst = c if rec['dst'] == 'c' else m
            # Causal eligibility exactly as in grow-blind: the question keeps its place in
            # the visit, counted in kept rows. A kept line is eligible iff it was eligible
            # in the original visit (every story row precedes every question row here).
            dst['where'].append(sum(1 for old in keep if old < rec['where']))
            dst['q'].append(rec['q'])
            dst['owner'].append(v)
            dst['answer'].append(rec['answer'])
            dst['evidence'].append([index[line] for line in rec['lines']])
            kinds[rec['kind']] += 1

    def pack(d):
        return (data.pack(memories, d['q'], d['owner'], d['where']),
                E.Targets(torch.tensor(d['answer']), torch.tensor(d['evidence'])))

    cx, cy = pack(c)
    mx, my = pack(m)
    assert kinds['link'] == kinds['terminal']
    assert kinds['one_hop'] + kinds['link'] + kinds['terminal'] == cx.questions.shape[0]
    # Causal eligibility check: in this generator every story row precedes every question
    # row, so a question's eligible set is exactly the REAL kept rows of its visit (the
    # padding rows that equalise ragged visits are correctly excluded).
    for x in (cx, mx):
        real = x.memory.ne(0).any(-1)[x.owner]
        assert bool((x.eligible == real).all()), \
            'every real kept story row must be causally eligible in this generator'
    accounting = dict(visits=len(plans), records=forbidden_checked or (
        cx.questions.shape[0] + mx.questions.shape[0]), kinds=kinds,
        relations=V._relation_counts(cx.questions), arm=arm,
        heldout_compositions=0, three_hop=0, twelve_person=0, gold_fields_used=0,
        blind=dict(census or {}),
        curriculum=dict(fraction=0., reduced=arm != 'D', kept_lines=kept_lines,
                        original_lines=original_lines,
                        fact_lines=ARMS[arm]['facts'], filler=ARMS[arm]['filler']))
    return A.TrainingBatch(cx, cy, mx, my, accounting)


def arm_batch(rng, vrng, arm, visits=DEFAULT_VISITS, forbidden=frozenset(), **kw):
    plans, info = plan_batch(rng, vrng, visits, forbidden, **kw)
    return materialise(plans, arm, info['records'], info['census'])


# ============================================================================ optimisation

def lr_constant(step):
    """The registered constant phase: warmup to 1e-3 over 100 updates, then flat.

    Identical to ``fable_operator_variants.lr_at(step)`` for every step < 4000.
    """
    return 1e-3 * min(1., (step+1)/100)


def lr_extend(step, updates=18000, flat=16000):
    """Part 3's declared schedule: constant 1e-3 after warmup to ``flat``, then linear."""
    if step < flat:
        return 1e-3 * min(1., (step+1)/100)
    return 1e-3 + (1e-4 - 1e-3) * (step - flat) / (updates - flat)


def training_step(model, optimizer, batch, lr):
    """``fable_operator_variants._step_e0`` verbatim, with the lr supplied by the caller.

    Answer cross-entropy only, 0.75 canonical + 0.25 monolithic, one backward per group,
    clip 1.0, one AdamW step. The returned loss/accuracy are read off the SAME forward
    passes under ``no_grad``; nothing extra is computed and no gradient is affected.
    """
    for group in optimizer.param_groups:
        group['lr'] = lr
    optimizer.zero_grad(set_to_none=True)
    total, correct, n = 0., 0, 0
    for x, y, weight in ((batch.canonical, batch.canonical_targets, .75),
                         (batch.monolithic, batch.monolithic_targets, .25)):
        logits = model(x)
        answer = F.cross_entropy(logits, y.answer)
        loss = answer * weight
        if not bool(torch.isfinite(loss)):
            raise RuntimeError('nonfinite training loss')
        loss.backward()
        with torch.no_grad():
            total += float(answer) * weight
            correct += int((logits.argmax(-1) == y.answer).sum())
            n += int(y.answer.numel())
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not bool(torch.isfinite(norm)):
        raise RuntimeError('nonfinite gradient')
    optimizer.step()
    return dict(train_loss=_num(total), train_acc=_num(correct/n), grad_norm=_num(norm))


# =============================================================================== diagnostics
# Everything below is a DIAGNOSTIC-ONLY code path. It runs under torch.no_grad or on a
# deepcopy of the model. It never writes a gradient into, or changes a parameter of, the
# model being trained. tests/test_fable_startup_factorial.py proves this two ways.

def line_token_mask(inputs, lines):
    """[questions, memory tokens+1] mask of the tokens of each question's supporting line.

    Built by the registered ``premonition_token_evidence.evidence_mask``, which also
    checks that the line is visible and causally eligible for that question.
    """
    lines = torch.as_tensor(lines, dtype=torch.long)
    repeated = lines[:, None].expand(lines.shape[0], 3).contiguous()
    mask = E.evidence_mask(inputs, E.Targets(torch.zeros_like(lines), repeated))
    assert bool((mask[:, 0] == mask[:, 1]).all()) and bool((mask[:, 0] == mask[:, 2]).all())
    return mask[:, 0]


def uniform_line_mass(inputs, lines):
    """Correct-line mass expected if attention were uniform over that story's tokens.

    The model's read domain is every token of every causally eligible row, plus one NULL
    key, so the denominator is (eligible real tokens) + 1 for that question.
    """
    lines = torch.as_tensor(lines, dtype=torch.long)
    per_line = inputs.memory.ne(0).sum(-1)                        # [visits, lines]
    owned = per_line[inputs.owner]                                # [questions, lines]
    valid = (owned * inputs.eligible).sum(-1) + 1
    chosen = owned.gather(1, lines[:, None]).squeeze(1)
    return chosen.double() / valid.double()


def correct_line_mass(model, inputs, mask):
    """[questions, steps, heads] attention mass on the supporting line at the last query token."""
    logits, attention = model(inputs, trace=True)
    q, steps, heads, _, width = attention.shape
    last = inputs.questions.ne(0).sum(-1) - 1
    read = attention.gather(3, last[:, None, None, None, None].expand(
        q, steps, heads, 1, width)).squeeze(3)
    return logits, (read * mask[:, None, None, :]).sum(-1)


@dataclass
class Probe:
    batch: object
    mask: torch.Tensor
    uniform: torch.Tensor
    one_hop: torch.Tensor          # bool [canonical questions]
    relation: torch.Tensor         # long [canonical questions]
    arm: str
    visits: int


def build_probe(seed, arm, visits=DEFAULT_PROBE_VISITS, forbidden=frozenset(), **kw):
    """A FIXED probe batch for this seed, drawn from its own streams.

    The probe's questions are the same in every arm (the plan is arm-independent); the
    probe's story rows follow the arm, so the probe measures the model in the condition it
    is actually trained in. Its RNGs are separate from the training streams, so building
    it cannot perturb training.
    """
    rng = random.Random(f'fable-startup-factorial-probe:{seed}')
    vrng = random.Random(f'fable-startup-factorial-probe-v:{seed}')
    batch = arm_batch(rng, vrng, arm, visits, forbidden, **kw)
    x, y = batch.canonical, batch.canonical_targets
    mask = line_token_mask(x, y.lines[:, 0])
    uniform = uniform_line_mass(x, y.lines[:, 0])
    relation = x.questions[:, 2]
    return Probe(batch, mask, uniform, relation != LINK, relation, arm, visits)


@torch.no_grad()
def probe_report(model, probe):
    """Diagnostics (1), (3) and (4). Runs entirely under no_grad on the live model."""
    x, y = probe.batch.canonical, probe.batch.canonical_targets
    logits, mass = correct_line_mass(model, x, probe.mask)
    predictions = logits.argmax(-1)
    correct = predictions == y.answer
    steps, heads = mass.shape[1], mass.shape[2]
    one = probe.one_hop
    report = dict(
        probe_loss=_num(F.cross_entropy(logits, y.answer)),
        probe_acc=_num(correct.float().mean()),
        probe_one_hop_acc=_num(correct[one].float().mean()),
        probe_link_acc=_num(correct[probe.relation == LINK].float().mean()),
        correct_line_mass=_num(mass.mean()),
        correct_line_mass_one_hop=_num(mass[one].mean()),
        uniform_line_mass=_num(probe.uniform.mean()),
        uniform_line_mass_one_hop=_num(probe.uniform[one].mean()),
        mass_over_uniform=_num(mass.mean(( 1, 2)).double().div(probe.uniform).mean()),
        mass_by_step=[_num(mass[:, s].mean()) for s in range(steps)],
        mass_by_step_head=[[_num(mass[:, s, h].mean()) for h in range(heads)]
                           for s in range(steps)],
        mass_by_step_head_one_hop=[[_num(mass[one][:, s, h].mean()) for h in range(heads)]
                                   for s in range(steps)])
    counts = {}
    for token in predictions.tolist():
        counts[token] = counts.get(token, 0) + 1
    total = sum(counts.values())
    shares = [n/total for n in counts.values()]
    report.update(distinct_predictions=len(counts), top1_share=_num(max(shares)),
                  prediction_entropy=_num(max(0., -sum(p*math.log(p) for p in shares))),
                  probe_records=total)
    per_relation = {}
    for r in ATTRIBUTE_RELATIONS:
        pick = one & (probe.relation == r)
        n = int(pick.sum())
        per_relation[str(r)] = dict(n=n, acc=_num(correct[pick].float().mean()) if n else None)
    report['one_hop_acc_by_relation'] = per_relation
    return report


def _mean_mass(model, inputs, mask, select=None):
    _, mass = correct_line_mass(model, inputs, mask)
    return mass[select].mean() if select is not None else mass.mean()


def _answer_loss(model, batch):
    """The training objective's answer loss: 0.75 canonical + 0.25 monolithic CE."""
    return (.75 * F.cross_entropy(model(batch.canonical), batch.canonical_targets.answer)
            + .25 * F.cross_entropy(model(batch.monolithic), batch.monolithic_targets.answer))


def routing_gradient(model, probe, eta=DEFAULT_ROUTING_ETA):
    """Diagnostic (2). Does one plain SGD step on the answer loss raise correct-line mass?

    Runs on a ``deepcopy``: the live model's parameters and ``.grad`` are never touched.
    ``directional`` is the exact derivative d/d(eta) mass(theta - eta grad L) at eta = 0,
    i.e. -<grad L, grad mass>; ``delta`` is the finite difference at the given eta. A
    plain SGD step is used deliberately -- no Adam preconditioner, no clipping -- so the
    sign and size answer the question about the answer loss itself.
    """
    clone = copy.deepcopy(model)
    clone.eval()                       # no dropout or norm statistics in this model
    params = list(clone.parameters())
    x = probe.batch.canonical
    out = dict(eta=eta)
    def gradient(scalar):
        # ``output_bias`` cannot influence an attention mass, so it is legitimately unused
        # in the mass graph; an unused parameter contributes exactly a zero gradient.
        raw = torch.autograd.grad(scalar, params, allow_unused=True)
        return [torch.zeros_like(p) if g is None else g for p, g in zip(params, raw)]

    grads = {}
    for name, select in (('all', None), ('one_hop', probe.one_hop)):
        mass = _mean_mass(clone, x, probe.mask, select)
        grads[name] = gradient(mass)
        out[f'mass_{name}'] = _num(mass)
    loss = _answer_loss(clone, probe.batch)
    g_loss = gradient(loss)
    norm_loss = math.sqrt(sum(float((g*g).sum()) for g in g_loss))
    with torch.no_grad():
        for p, g in zip(params, g_loss):
            p.sub_(eta*g)
    for name, select in (('all', None), ('one_hop', probe.one_hop)):
        g_mass = grads[name]
        directional = -sum(float((a*b).sum()) for a, b in zip(g_loss, g_mass))
        norm_mass = math.sqrt(sum(float((g*g).sum()) for g in g_mass))
        with torch.no_grad():
            after = float(_mean_mass(clone, x, probe.mask, select))
        out[f'routing_directional_{name}'] = _num(directional)
        out[f'routing_delta_{name}'] = _num(after - float(out[f'mass_{name}']))
        out[f'routing_grad_norm_mass_{name}'] = _num(norm_mass)
        out[f'routing_cosine_{name}'] = _num(
            directional/(norm_loss*norm_mass)) if norm_loss and norm_mass else None
    out['routing_answer_loss'] = _num(loss)
    out['routing_grad_norm_loss'] = _num(norm_loss)
    del clone, grads, g_loss
    return out


def diagnostics(model, probe, eta=DEFAULT_ROUTING_ETA, routing=True):
    row = probe_report(model, probe)
    if routing:
        row.update(routing_gradient(model, probe, eta))
    return row


# ================================================================================ panels

def supporting_lines(inputs):
    """The unique eligible visible fact row answering each one-hop question. Evaluator only."""
    memory = inputs.memory.tolist()
    out = []
    for owner, eligible, raw in zip(inputs.owner.tolist(), inputs.eligible.tolist(),
                                    inputs.questions.tolist()):
        q = [t for t in raw if t]
        assert len(q) == 4 and q[0] == QUESTION and q[-1] == ANSWER, q
        hits = [k for k, (row, ok) in enumerate(zip(memory[owner], eligible))
                if ok and len(row) >= 4 and row[0] == WORLD and row[1] == q[1] and row[2] == q[2]]
        if len(hits) != 1:
            raise RuntimeError(f'expected one supporting row, found {len(hits)}')
        out.append(hits[0])
    return torch.tensor(out, dtype=torch.long)


@torch.no_grad()
def score_one_hop(model, chunks):
    """One-hop accuracy and correct-line attention over an iterable of (Inputs, answers)."""
    n = correct = 0
    mass_sum = uniform_sum = 0.
    per_step = None
    counts = {}
    for x, answers in chunks:
        lines = supporting_lines(x)
        mask = line_token_mask(x, lines)
        logits, mass = correct_line_mass(model, x, mask)
        predictions = logits.argmax(-1)
        correct += int((predictions == answers).sum())
        n += int(answers.numel())
        mass_sum += float(mass.mean()) * int(answers.numel())
        uniform_sum += float(uniform_line_mass(x, lines).mean()) * int(answers.numel())
        block = mass.mean((0, 2)) * int(answers.numel())
        per_step = block if per_step is None else per_step + block
        for token in predictions.tolist():
            counts[token] = counts.get(token, 0) + 1
    shares = [c/n for c in counts.values()]
    return dict(n=n, correct=correct, accuracy=_num(correct/n),
                correct_line_mass=_num(mass_sum/n), uniform_line_mass=_num(uniform_sum/n),
                mass_by_step=[_num(v) for v in (per_step/n).tolist()],
                distinct_predictions=len(counts), top1_share=_num(max(shares)),
                prediction_entropy=_num(max(0., -sum(p*math.log(p) for p in shares))))


def registered_c1(manifest):
    """The registered c1 one-hop panel, READ-ONLY, sha-verified. Nothing is written there."""
    row = manifest['panels']['c1']
    assert C.sha(row['path']) == row['sha256'], 'registered c1 panel changed'
    panel = P.load(row['path'])
    chunks = []
    for sides in P.chunks(panel):
        x, targets = sides['a']
        chunks.append((x, torch.tensor(list(targets))))
    return chunks, row


def fresh_one_hop_chunks(name, n=512, entities=6, fact_lines=24, filler_fraction=1.,
                         namespace='fable-startup-factorial-probe-v1', block=32):
    """Fresh one-hop questions on worlds of a chosen size. No training data is touched.

    ``fact_lines`` of the world's fact rows are kept (uniformly, label-free) and
    ``filler_fraction`` of its filler/gap rows; the question is then drawn uniformly from
    the (entity, relation) pairs answerable from the kept facts. ``A.truth_paths``
    re-derives every answer from the visible eligible rows as an independent check.
    """
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec(entities=entities)
    chunks = []
    for start in range(0, n, block):
        memories, qs, owners, wheres, answers = [], [], [], [], []
        for i in range(start, min(n, start+block)):
            rng = random.Random(f'{namespace}:{name}:{i}')
            rows, _, _ = visit(spec, rng, training=True)
            full = [[] if row.question else list(row.tokens) for row in rows]
            j = next(k for k, row in enumerate(rows) if row.question)
            facts, others = S._row_classes(full)
            keep = set(rng.sample(facts, min(fact_lines, len(facts))))
            keep.update(rng.sample(others, int(round(filler_fraction*len(others)))))
            keep = sorted(keep)
            attr, _ = S._visible_facts(full, keep)
            assert attr, 'no attribute fact kept'
            key = sorted(attr)[rng.randrange(len(attr))]
            memories.append([full[old] for old in keep])
            owners.append(len(memories)-1)
            qs.append([QUESTION, key[0], key[1], ANSWER])
            wheres.append(sum(1 for old in keep if old < j))
            answers.append(attr[key][0])
        x = data.pack(memories, qs, owners, wheres)
        assert [p[-1]['target'] for p in A.truth_paths(x)] == answers
        chunks.append((x, torch.tensor(answers)))
    return chunks


SWEEP_CELLS = tuple(
    dict(name=f'e{e}-f{f}-x{int(100*x)}', entities=e, fact_lines=f, filler_fraction=x)
    for e in (6, 16) for f in (16, 24) for x in (0., .5, 1.))


# ================================================================== freeze / wave / worker

def _register_key(path):
    """Manifest key ``check_manifest`` can resolve: ROOT-relative when possible, else absolute."""
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check_manifest():
    """Refuse to run if any registered source, panel, exclusion set or the prereg changed."""
    manifest = json.loads((OUT/'launch.json').read_text())
    for name, expected in manifest['files'].items():
        if C.sha(ROOT/name) != expected:
            raise RuntimeError(f'registered file changed: {name}')
    return manifest


def freeze(args):
    """Hash every imported source, the panels, the exclusion set and the preregistration."""
    OUT.mkdir(parents=True, exist_ok=True)
    if not PREREG.exists():
        raise RuntimeError(f'write {PREREG} before freezing')
    v1 = json.loads((V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    extra = [Path(V.__file__).resolve(), Path(S.__file__).resolve(), Path(__file__).resolve(),
             PREREG, Path(T.__file__).resolve(), Path(E.__file__).resolve(),
             Path(A.__file__).resolve(), Path(R.__file__).resolve(), Path(P.__file__).resolve(),
             Path(C.__file__).resolve(), Path(data.__file__).resolve(),
             ROOT/'premonition/toy_ladder.py', ROOT/'premonition/batch.py',
             ROOT/'scripts/premonition_pair_suite.py',
             ROOT/'scripts/premonition_token_initialization_probe.py']
    for path in extra:
        files[_register_key(path)] = C.sha(path)
    manifest = dict(
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        experiment='fable-startup-factorial', arms={k: dict(v) for k, v in ARMS.items()},
        blind_lines=args.blind_lines, balance=bool(args.balance),
        start_rule=dict(metric='probe one-hop accuracy', threshold=START_ACCURACY,
                        window_updates=START_WINDOW,
                        definition='every logged probe in the last 200 updates >= 0.90'),
        schedule=dict(updates=args.updates, visits_per_update=args.visits,
                      lr='1e-3 * min(1, (step+1)/100)  [registered constant phase]',
                      training_seconds=args.training_seconds,
                      work_seconds=args.training_seconds+240,
                      terminate_seconds=args.training_seconds+270,
                      log_every=args.log_every, probe_visits=args.probe_visits,
                      routing_eta=args.routing_eta),
        extend=dict(arm='D', updates=args.extend_updates, flat_until=args.extend_flat,
                    lr='1e-3 after warmup to 16,000, then linear to 1e-4 at 18,000',
                    chunk_seconds=args.chunk_seconds),
        exclusion_path=v1['exclusion_path'], panels=v1['panels'], files=files,
        v1_launch_sha256=C.sha(V1/'astra_canonical_operator_launch.json'))
    C.write_new(OUT/'launch.json', manifest)
    print(len(files), 'files frozen; launch.json', C.sha(OUT/'launch.json'), flush=True)


def _env():
    return dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')


def wave(args):
    """Launch one worker per (arm, seed). Keep the total at or below 6 processes."""
    manifest = check_manifest()
    arms = [a.strip() for a in args.arms.split(',') if a.strip()]
    seeds = [int(s) for s in args.seeds.split(',')]
    for arm in arms:
        assert arm in ARMS, arm
    folder = OUT/args.name
    folder.mkdir(parents=True, exist_ok=False)
    cap, start = manifest['schedule']['terminate_seconds'], time.monotonic()
    procs = []
    for arm in arms:
        for seed in seeds:
            handle = (folder/f'{arm}-seed-{seed}.log').open('x')
            procs.append(subprocess.Popen(
                [R.PYTHON, '-B', str(Path(__file__).resolve()), 'worker',
                 '--arm', arm, '--seed', str(seed), '--wave-start', str(start)],
                stdout=handle, stderr=subprocess.STDOUT, env=_env(), start_new_session=True))
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
        (OUT/a/f'seed-{s}/completion.json').exists() for a in arms for s in seeds)
    C.write_new(folder/'completion.json',
                dict(seconds=_num(time.monotonic()-start), exit_codes=exits, complete=complete,
                     arms=arms, seeds=seeds))
    print(json.dumps(dict(arms=arms, seeds=seeds, seconds=_num(time.monotonic()-start),
                          exit_codes=exits, complete=complete)), flush=True)


def _started(rows, updates, window=START_WINDOW, threshold=START_ACCURACY):
    """The FIXED start rule: every logged probe in the last ``window`` updates >= threshold."""
    tail = [r for r in rows if r['update'] > updates - window and r.get('probe_one_hop_acc') is not None]
    return bool(tail) and all(r['probe_one_hop_acc'] >= threshold for r in tail)


def worker(args):
    started_at = time.monotonic()
    folder = OUT/args.arm/f'seed-{args.seed}'
    folder.mkdir(parents=True, exist_ok=False)
    updates = 0
    try:
        manifest = check_manifest()
        schedule = manifest['schedule']
        forbidden = set(json.loads(Path(manifest['exclusion_path']).read_text()))
        model = A.new_model(args.seed)        # identical init per seed across all four arms
        assert model.parameters_count() == 79316
        initial = C.fingerprint(model)
        optimizer = A.T.optimizer_for(model)
        rng = random.Random(1101)
        # The variant stream is deliberately NOT keyed by arm: all four arms must draw the
        # same 16-fact subsets and the same questions.
        vrng = random.Random(f'fable-startup-factorial:{args.seed}')
        probe = build_probe(args.seed, args.arm, schedule['probe_visits'], forbidden,
                            blind_lines=manifest['blind_lines'], balance=manifest['balance'])
        rows, log = [], (folder/'trace.jsonl').open('x')
        training_start = time.monotonic()
        last = {}
        for step in range(schedule['updates']):
            if time.monotonic()-args.wave_start >= schedule['work_seconds']:
                raise TimeoutError('wave work deadline')
            if time.monotonic()-training_start >= schedule['training_seconds']:
                raise TimeoutError('registered training time cap')
            batch = arm_batch(rng, vrng, args.arm, schedule['visits_per_update'], forbidden,
                              blind_lines=manifest['blind_lines'], balance=manifest['balance'])
            last = training_step(model, optimizer, batch, lr_constant(step))
            updates += 1
            if updates % schedule['log_every'] == 0 or updates == 1:
                was = model.training
                model.eval()
                row = dict(arm=args.arm, seed=args.seed, update=updates,
                           lr=_num(lr_constant(step)), **last,
                           **diagnostics(model, probe, schedule['routing_eta']),
                           mean_kept_lines=_num(sum(batch.accounting['curriculum']['kept_lines'])
                                                / schedule['visits_per_update']),
                           elapsed=_num(time.monotonic()-training_start))
                model.train(was)
                rows.append(row)
                log.write(json.dumps(row)+'\n')
                log.flush()
                print(json.dumps(row), flush=True)
        log.close()
        train_seconds = time.monotonic()-training_start
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=args.seed, arm=args.arm,
                        updates=updates, architecture=dict(vocab=68, width=48, heads=4, steps=3),
                        launch_sha256=C.sha(OUT/'launch.json')), checkpoint)
        final = C.fingerprint(model)
        C.write_new(folder/'training.json', dict(
            seed=args.seed, arm=args.arm, updates=updates, seconds=_num(train_seconds),
            updates_per_second=_num(updates/train_seconds), initial_fingerprint=initial,
            final_fingerprint=final, checkpoint_sha256=C.sha(checkpoint),
            canonical_records=updates*schedule['visits_per_update']*6,
            monolithic_records=updates*schedule['visits_per_update']*2))
        del optimizer, batch
        gc.collect()
        # Scoring uses the saved final checkpoint only, loaded once.
        saved = P.load(checkpoint)
        scorer = A.CanonicalOperator(**saved['architecture'])
        scorer.load_state_dict(saved['state_dict'], strict=True)
        scorer.eval()
        assert C.fingerprint(scorer) == final
        panels = {}
        c1_chunks, c1_row = registered_c1(manifest)
        panels['c1_registered'] = dict(score_one_hop(scorer, c1_chunks),
                                       path=c1_row['path'], sha256=c1_row['sha256'],
                                       cutoff=c1_row['cutoff'])
        panels['fresh_full_story'] = score_one_hop(scorer, fresh_one_hop_chunks(
            'final-full', 512, 6, 24, 1.))
        assert C.fingerprint(scorer) == final
        assert C.sha(checkpoint) == json.loads((folder/'training.json').read_text())[
            'checkpoint_sha256'], 'the final checkpoint changed during scoring'
        check_manifest()
        C.write_new(folder/'completion.json', dict(
            seed=args.seed, arm=args.arm, complete=True, updates=updates,
            started=_started(rows, updates), start_rule=manifest['start_rule'],
            seconds=_num(time.monotonic()-started_at),
            updates_per_second=_num(updates/train_seconds),
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            final_checkpoint_only=True, registered_files_unchanged=True,
            panels=panels, last_probe=rows[-1] if rows else None))
        print(json.dumps(dict(arm=args.arm, seed=args.seed, complete=True,
                              started=_started(rows, updates),
                              c1=panels['c1_registered']['correct'])), flush=True)
    except BaseException as exc:
        C.write_new(folder/'failure.json', dict(seed=args.seed, arm=args.arm, complete=False,
                    updates=updates, seconds=_num(time.monotonic()-started_at),
                    error=repr(exc), traceback=traceback.format_exc()))
        raise


# ========================================================================= PART 2: size sweep

def size_sweep(args):
    """Freeze-before-growth transfer: evaluate the arm-A checkpoint on bigger stories.

    No training, no optimizer, no gradient: the checkpoint is loaded once and only read.
    """
    checkpoint = Path(args.checkpoint) if args.checkpoint else OUT/f'A/seed-{args.seed}/final.pt'
    saved = P.load(checkpoint)
    assert saved['arm'] == 'A', f"size-sweep expects an arm-A checkpoint, got {saved['arm']}"
    model = A.CanonicalOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    fingerprint = C.fingerprint(model)
    cells = {}
    for cell in SWEEP_CELLS:
        if cell['entities'] != 6 and not args.sixteen_person:
            continue
        chunks = fresh_one_hop_chunks(cell['name'], args.n, cell['entities'],
                                      cell['fact_lines'], cell['filler_fraction'],
                                      namespace=args.namespace)
        cells[cell['name']] = dict(score_one_hop(model, chunks), **cell)
        print(json.dumps(dict(cell=cell['name'], **{k: cells[cell['name']][k]
                              for k in ('n', 'correct', 'accuracy', 'correct_line_mass',
                                        'uniform_line_mass')})), flush=True)
    assert C.fingerprint(model) == fingerprint, 'the checkpoint must not change'
    folder = OUT/'size-sweep'
    folder.mkdir(parents=True, exist_ok=True)
    out = folder/f'seed-{args.seed}-{args.namespace}.json'
    C.write_new(out, dict(checkpoint=str(checkpoint), checkpoint_sha256=C.sha(checkpoint),
                          seed=args.seed, arm='A', trained_updates=saved['updates'],
                          fingerprint=fingerprint, n=args.n, cells=cells,
                          no_training=True, namespace=args.namespace))
    print('wrote', out, flush=True)


# ============================================================ PART 3: extend condition D

def _rng_states(rng, vrng):
    return dict(world=rng.getstate(), variant=vrng.getstate(), torch=torch.get_rng_state())


def _restore(state, rng, vrng):
    rng.setstate(state['world'])
    vrng.setstate(state['variant'])
    torch.set_rng_state(state['torch'])


def _latest_resume(folder):
    files = sorted(folder.glob('resume-*.pt'))
    return files[-1] if files else None


def extend_chunk(folder, seed, updates, flat, visits, log_every, probe_visits, routing_eta,
                 forbidden, arm='D', chunk_seconds=1200, chunk_updates=None,
                 blind_lines=BLIND_LINES, balance=False, quiet=False):
    """Run one resumable chunk of the long condition-D run. Returns the completion dict.

    A resume restores the model, the optimizer, the torch RNG state and BOTH data-stream
    RNG states exactly, so a split run and an unsplit run are bit-identical.
    """
    folder.mkdir(parents=True, exist_ok=True)
    previous = _latest_resume(folder)
    model = A.new_model(seed)
    optimizer = A.T.optimizer_for(model)
    rng, vrng = random.Random(1101), random.Random(f'fable-startup-factorial:{seed}')
    probe = build_probe(seed, arm, probe_visits, forbidden,
                        blind_lines=blind_lines, balance=balance)
    step, rows = 0, []
    if previous is not None:
        state = torch.load(previous, map_location='cpu', weights_only=False)
        model.load_state_dict(state['state_dict'], strict=True)
        optimizer.load_state_dict(state['optimizer'])
        _restore(state['rng'], rng, vrng)
        step, rows = state['step'], list(state['rows'])
    started, first = time.monotonic(), step
    while step < updates:
        batch = arm_batch(rng, vrng, arm, visits, forbidden,
                          blind_lines=blind_lines, balance=balance)
        last = training_step(model, optimizer, batch, lr_extend(step, updates, flat))
        step += 1
        if step % log_every == 0 or step == 1:
            was = model.training
            model.eval()
            row = dict(arm=arm, seed=seed, update=step, lr=_num(lr_extend(step-1, updates, flat)),
                       **last, **diagnostics(model, probe, routing_eta))
            model.train(was)
            rows.append(row)
            if not quiet:
                print(json.dumps(row), flush=True)
        if chunk_updates is not None:
            if step - first >= chunk_updates:
                break
        elif time.monotonic()-started >= chunk_seconds:
            break
    payload = dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                   rng=_rng_states(rng, vrng), step=step, rows=rows, seed=seed, arm=arm,
                   updates=updates, architecture=dict(vocab=68, width=48, heads=4, steps=3))
    torch.save(payload, folder/f'resume-{step:06d}.pt')
    return dict(step=step, first_step=first, updates=updates, done=step >= updates,
                fingerprint=C.fingerprint(model), seconds=_num(time.monotonic()-started),
                rows=len(rows))


def extend(args):
    manifest = check_manifest()
    forbidden = set(json.loads(Path(manifest['exclusion_path']).read_text()))
    schedule, plan = manifest['schedule'], manifest['extend']
    folder = OUT/'extend'/f'seed-{args.seed}'
    result = extend_chunk(folder, args.seed, plan['updates'], plan['flat_until'],
                          schedule['visits_per_update'], schedule['log_every'],
                          schedule['probe_visits'], schedule['routing_eta'], forbidden,
                          arm=plan['arm'], chunk_seconds=args.chunk_seconds,
                          chunk_updates=args.chunk_updates,
                          blind_lines=manifest['blind_lines'], balance=manifest['balance'])
    record = folder/f'chunk-{result["step"]:06d}.json'
    if not record.exists():
        C.write_new(record, result)
    print(json.dumps(result), flush=True)
    if not result['done']:
        print(f'INCOMPLETE: rerun the same command to continue from update {result["step"]}',
              flush=True)


# ==================================================================================== CLI

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['freeze', 'wave', 'worker', 'size-sweep', 'extend'])
    ap.add_argument('--arm', choices=list(ARM_NAMES))
    ap.add_argument('--arms', default=','.join(ARM_NAMES))
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--seeds', default='0,1,2')
    ap.add_argument('--name', default='wave-1')
    ap.add_argument('--wave-start', type=float, default=0.)
    ap.add_argument('--updates', type=int, default=DEFAULT_UPDATES)
    ap.add_argument('--visits', type=int, default=DEFAULT_VISITS)
    ap.add_argument('--training-seconds', type=int, default=900)
    ap.add_argument('--log-every', type=int, default=DEFAULT_LOG_EVERY)
    ap.add_argument('--probe-visits', type=int, default=DEFAULT_PROBE_VISITS)
    ap.add_argument('--routing-eta', type=float, default=DEFAULT_ROUTING_ETA)
    ap.add_argument('--blind-lines', type=int, default=BLIND_LINES)
    ap.add_argument('--balance', action='store_true', default=False)
    ap.add_argument('--extend-updates', type=int, default=18000)
    ap.add_argument('--extend-flat', type=int, default=16000)
    ap.add_argument('--chunk-seconds', type=int, default=1200)
    # Optional exact-update chunking; None means chunk by wall clock (the default).
    ap.add_argument('--chunk-updates', type=int, default=None)
    ap.add_argument('--checkpoint', default=None)
    ap.add_argument('--n', type=int, default=512)
    ap.add_argument('--namespace', default='fable-startup-factorial-probe-v1')
    ap.add_argument('--sixteen-person', action='store_true', default=True)
    ap.add_argument('--no-sixteen-person', dest='sixteen_person', action='store_false')
    return ap


if __name__ == '__main__':
    args = build_parser().parse_args()
    R.configure()
    if args.command == 'freeze':
        freeze(args)
    elif args.command == 'wave':
        wave(args)
    elif args.command == 'worker':
        assert args.arm, '--arm is required for worker'
        worker(args)
    elif args.command == 'size-sweep':
        size_sweep(args)
    else:
        extend(args)
