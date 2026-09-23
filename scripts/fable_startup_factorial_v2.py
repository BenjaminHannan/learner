"""Start-up factorial v2 (Fable, 2026-09-20 EDT). Additive only; v1 is untouched.

THE SPEC is design/v3/18-startup-factorial-v2-preregistration-draft.md in the BASE
checkout. This file implements it and nothing else. The frozen v1 module
``fable_startup_factorial`` is IMPORTED, never edited: its plan builder, materialiser,
training step, attention/mass helpers and routing-gradient machinery are reused verbatim,
so v1 and v2 compute the same quantities from the same frozen model/data/optimizer code.

WHAT v2 CHANGES vs v1, and why (each item is a correction demanded by the audit
design/v3/18-audit-before-fable-continues.md, section 2):

 1. NEW STREAMS AND SEEDS. Seeds 1300/1301/1302. The world stream is
    ``random.Random('astra-startup-factorial-v2-world:<seed>')`` and the subset/question
    stream is ``random.Random('astra-startup-factorial-v2-plan:<seed>')``. v1 used the
    registered ``random.Random(1101)`` world stream; v2 does not, because the spec
    registers per-seed namespaces. ONE world stream and ONE plan stream per seed, shared
    by all four arms -- that is what makes questions/answers/weights/support identical
    across arms within a seed.
 2. ONSET, not "started at the end". A fixed 512-question ATTRIBUTE-ONLY validation probe
    is scored at updates 0, 50, ..., 2500. First qualified onset is the earliest t >= 200
    at which all five scheduled probes t-200, t-150, t-100, t-50, t exist and each scores
    >= 461/512. Missing probes never qualify. Regressions after onset and the final-window
    status are recorded separately. A SECOND untouched 512-question probe is scored once,
    at the final update, and >= 461/512 there is what "independently confirmed" means.
 3. EXCLUSIONS ARE AUDITED AGAINST THE ACTUAL PRESENTED INPUT. For every training record
    v2 hashes the visible signature of the FULL source story and of the REDUCED story of
    EVERY arm, and refuses the run on any collision with the frozen exclusion union
    (registered forbidden semantics + both validation probes + the routing probe + all 15
    freeze-before-growth transfer cells). v1 checked the full story only.
 4. UNROUNDED DIAGNOSTICS. Gradient inner products, norms and cosines are reduced in
    double precision and written without rounding. Loss components are differentiated
    separately (attribute, LINK, monolithic) and then as the registered 0.75/0.25 sum.
    The analytic plain-SGD derivative is validated by CENTRAL finite differences at
    eta = 1e-3, 1e-4 and 1e-5; disagreement is reported, not resolved.
 5. A SEPARATE AdamW DIAGNOSTIC. One hypothetical AdamW update is taken on a disposable
    copy of BOTH the model and the optimizer state, using an independent
    training-distribution batch, and the change in correct-line mass is reported as an
    optimizer-specific statistic -- never as the SGD derivative. The live training state
    is asserted byte-identical across the measurement.
 6. CAPACITY GUARD AND CHUNKS. ``train`` and ``longrun`` run ONE job in this process and
    refuse to start when the machine already has too many workers (default: 3 audit
    workers, 6 registered training workers in total). Nothing here ever spawns a wave.
    Every chunk is bounded by ``--budget-seconds`` (<= 1200 s) and resumes bit-identically.

WHAT v2 DELIBERATELY KEEPS FROM v1, because the spec says to keep it:
  the shared-plan construction (16 visible fact rows drawn label-free by
  ``fable_operator_startup._blind_keep``; records built from that subset by grow-blind's
  own constructors; arms C/D restore the other 8 fact rows and arms B/D restore the
  filler-only/gap rows, in original order; inline filler inside kept fact rows stays in
  every arm); the 79,316-parameter rescaled operator; 16 worlds per update; pure answer
  cross-entropy at 0.75 canonical / 0.25 monolithic; AdamW and clip 1.0; warmup to 1e-3
  over 100 updates then flat 1e-3 for all 2,500 updates; no context growth.

WHAT THIS EXPERIMENT DOES NOT ESTABLISH. It does not identify the microscopic gradient
mechanism. A positive derivative in every arm does not refute dilution. Failure of average
final-token attention to rise does not prove no head learned retrieval. One D success does
not show "only time matters"; an 18,000-update failure is a finite-budget failure, not an
impossibility result. Effects are conditional on these sizes, streams and budgets.

D is "full context with subset-selected questions", NOT historical e0. Historical e0 and
grow-blind runs are context, not matched controls.

SUBCOMMANDS
  plan            build + hash the per-seed shared streams, both validation probes, the
                  routing probe and the transfer cells; enforce exclusions; audit
                  cross-arm identity; write launch.json. Starts no worker.
  train           one (arm, seed) factorial run, in resumable chunks.
  longrun         the 18,000-update arm-D trajectory, in resumable chunks.
  report          per seed, per arm; never averaged; missing runs print "(missing)".
  transfer        freeze-before-growth evaluation of a final arm-A checkpoint.
  check-manifest  re-verify every hashed source, probe and plan.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree because
the harness refuses writes to the base checkout. ``BASE`` and ``BASE``/scripts are
prepended to ``sys.path``, so every registered module, the frozen ``premonition`` package,
``ROOT``, the panels and the exclusion set are the BASE repository's. Only the output
directory is worktree-local; nothing is ever written inside a registered folder.
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
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import argparse
import copy
import datetime
from dataclasses import dataclass, field
import hashlib
import json
import math
import os
import random
import re
import resource
import subprocess
import time
import traceback

import fable_startup_factorial as F1          # frozen v1: reused, never edited

A, P, C, R, S, V = F1.A, F1.P, F1.C, F1.R, F1.S, F1.V
E, T, data, torch, F, ROOT = F1.E, F1.T, F1.data, F1.torch, F1.F, F1.ROOT
QUESTION, ANSWER, WORLD, LINK = F1.QUESTION, F1.ANSWER, F1.WORLD, F1.LINK
ENTITY_MIN, ENTITY_MAX = F1.ENTITY_MIN, F1.ENTITY_MAX
ATTRIBUTE_RELATIONS = F1.ATTRIBUTE_RELATIONS
assert ROOT == BASE, (ROOT, BASE)
assert Path(F1.__file__).resolve().parent == HERE, F1.__file__

OUT = HERE.parent/'artifacts/fable-startup-factorial-v2-20260920'

# ------------------------------------------------------------------ registered constants
# Every number below is quoted from the spec. tests/ asserts them against the spec text.
EXPERIMENT = 'astra-startup-factorial-v2'
REGISTERED_SEEDS = (1300, 1301, 1302)
ARMS = F1.ARMS                      # A 16/none, B 16/all, C 24/none, D 24/all
ARM_NAMES = F1.ARM_NAMES
BLIND_LINES = F1.BLIND_LINES        # 16 visible fact rows selected label-free
PARAMETERS = 79316
UPDATES = 2500
VISITS = 16                         # worlds per update
CANONICAL_WEIGHT, MONOLITHIC_WEIGHT = .75, .25
PROBE_EVERY = 50                    # validation probe AND routing diagnostics
VALIDATION_N = 512
ONSET_CORRECT = 461                 # >= 461/512
ONSET_WINDOW = 200                  # t-200 .. t, five scheduled probes
ONSET_MIN_UPDATE = 200
WARMUP_UPDATES = 100
FLAT_LR = 1e-3
LONGRUN_ARM = 'D'
LONGRUN_UPDATES = 18000
LONGRUN_FLAT_UNTIL = 16000
LONGRUN_FINAL_LR = 1e-4
LONGRUN_MIDPOINT = 6000             # the frozen checkpoint compared with 18,000
LONGRUN_ROUTING_EVERY = 250         # declared here; see "judgment calls" in the prereg
CHUNK_SECONDS_MAX = 1200
MAX_AUDIT_WORKERS = 3
MAX_TOTAL_WORKERS = 6
CENTRAL_ETAS = (1e-3, 1e-4, 1e-5)
TRANSFER_N = 512
TRANSFER_CORRECT = 461
TRANSFER_CELLS = tuple(
    dict(name=f'e{e}-f{k}-x{int(100*x)}', entities=e, fact_lines=k, filler_fraction=x)
    for e in (6, 16)
    for k in ((16, 24) if e == 6 else (16, 24, 64))
    for x in (0., .5, 1.))


def ns_world(seed):      return f'{EXPERIMENT}-world:{seed}'
def ns_plan(seed):       return f'{EXPERIMENT}-plan:{seed}'
def ns_validation(seed): return f'{EXPERIMENT}-validation:{seed}'
def ns_confirm(seed):    return f'{EXPERIMENT}-confirmation:{seed}'
def ns_routing_world(seed): return f'{EXPERIMENT}-routing-world:{seed}'
def ns_routing_plan(seed):  return f'{EXPERIMENT}-routing-plan:{seed}'
def ns_adam_world(seed, update): return f'{EXPERIMENT}-adam-world:{seed}:{update}'
def ns_adam_plan(seed, update):  return f'{EXPERIMENT}-adam-plan:{seed}:{update}'
NS_TRANSFER = f'{EXPERIMENT}-transfer'

_num = F1._num                      # JSON-safe, rounded to 8 dp: trajectories only


def _raw(x):
    """Full-precision JSON-safe float. Used for every gradient reduction (spec item 2)."""
    x = float(x.detach()) if torch.is_tensor(x) else float(x)
    return x if math.isfinite(x) else None


def streams(seed):
    """The two per-seed streams shared by all four arms. No arm appears in either key."""
    return random.Random(ns_world(seed)), random.Random(ns_plan(seed))


def lr_factorial(step):
    """Warm up to 1e-3 over 100 updates, then hold 1e-3 for all 2,500 updates."""
    return FLAT_LR * min(1., (step+1)/WARMUP_UPDATES)


def lr_longrun(step):
    """Warmup 100, flat to 16,000, linear to 1e-4 at 18,000."""
    return F1.lr_extend(step, LONGRUN_UPDATES, LONGRUN_FLAT_UNTIL)


# ================================================================== exclusion signatures
# A.visible_signature(rows, question) hashes [sorted 4-token fact tuples, visible question].
# The fact part depends only on the presented rows, so it is computed once per (visit,
# condition) and reused for that visit's eight records. _signature reproduces
# A.visible_signature byte for byte; tests/ asserts the equality directly.

def _facts_json(rows):
    facts = sorted(tuple(row[:4]) for row in rows
                   if len(row) >= 4 and row[0] == WORLD
                   and ENTITY_MIN <= row[1] < ENTITY_MAX and 8 <= row[2] <= LINK)
    return json.dumps([list(f) for f in facts], separators=(',', ':'))


def _signature(facts_json, question):
    payload = '[' + facts_json + ',' + json.dumps(
        [t for t in question if t], separators=(',', ':')) + ']'
    return hashlib.sha256(payload.encode()).hexdigest()


def condition_prefixes(full, kept16, facts, others):
    """The five audited conditions: the full source story and each arm's reduced story."""
    plan = F1.VisitPlan(full, kept16, facts, others, [])
    out = {arm: _facts_json([full[old] for old in F1.arm_keep(plan, arm)])
           for arm in ARM_NAMES}
    out['full'] = _facts_json(full)
    return out


def plan_signatures(plan):
    """Every (condition, record) signature of one visit. Used to build and to audit."""
    prefixes = condition_prefixes(plan.full, plan.kept16, plan.facts, plan.others)
    return [(name, _signature(pre, rec['q']))
            for rec in plan.records for name, pre in prefixes.items()]


def audit_plans(plans, forbidden):
    """Refuse the run on ANY collision, in the full story or in any arm's reduced story.

    A collision invalidates the run; the record is never silently skipped, because
    skipping would change the frozen RNG stream (companion draft, semantic-overlap audit).
    """
    checked = 0
    if not forbidden:
        return 0
    for plan in plans:
        for name, sig in plan_signatures(plan):
            if sig in forbidden:
                raise RuntimeError(
                    f'training/validation semantic overlap in condition {name}; run invalid')
            checked += 1
    return checked


def plan_batch(rng, vrng, visits, forbidden):
    """v1's frozen plan builder plus v2's five-condition exclusion audit."""
    plans, info = F1.plan_batch(rng, vrng, visits, frozenset(),
                                blind_lines=BLIND_LINES, balance=False)
    info['signature_checks'] = audit_plans(plans, forbidden)
    return plans, info


def arm_batch(plans, info, arm):
    return F1.materialise(plans, arm, info['records'], info['census'])


def canonical_kinds(plans):
    """Record kinds in the exact order ``F1.materialise`` packs the canonical group."""
    return [rec['kind'] for plan in plans for rec in plan.records if rec['dst'] == 'c']


# ==================================================== the 512-question validation probes
# ATTRIBUTE-ONLY, matched across arms: one world per unit, ONE question per world, drawn
# from the (entity, relation) pairs answerable from that world's label-free 16-fact core.
# The core is a subset of every arm's fact set, so the question, the answer and the
# supporting row are identical in all four arms and only the readable rows differ.

@dataclass
class Unit:
    full: list
    kept16: list
    facts: list
    others: list
    where: int
    q: list
    answer: int


def probe_units(namespace, n=VALIDATION_N, entities=6):
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec(entities=entities)
    units = []
    for i in range(n):
        rng = random.Random(f'{namespace}:{i}')
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == entities
        full = [[] if row.question else list(row.tokens) for row in rows]
        where = next(k for k, row in enumerate(rows) if row.question)
        facts, others = S._row_classes(full)
        kept16 = S._blind_keep(rng, full, BLIND_LINES, 0.)
        attr, _ = S._visible_facts(full, kept16)
        assert attr, 'no attribute fact in the 16-fact core'
        key = sorted(attr)[rng.randrange(len(attr))]
        assert key[1] in ATTRIBUTE_RELATIONS
        units.append(Unit(full, kept16, facts, others, where,
                          [QUESTION, key[0], key[1], ANSWER], attr[key][0]))
    return units


def pack_units(units, arm):
    """One arm's presentation of a block of units. Answers are read by the evaluator."""
    memories, qs, owners, wheres, answers = [], [], [], [], []
    for u in units:
        keep = F1.arm_keep(F1.VisitPlan(u.full, u.kept16, u.facts, u.others, []), arm)
        memories.append([u.full[old] for old in keep])
        owners.append(len(memories)-1)
        qs.append(list(u.q))
        wheres.append(sum(1 for old in keep if old < u.where))
        answers.append(u.answer)
    x = data.pack(memories, qs, owners, wheres)
    assert [p[-1]['target'] for p in A.truth_paths(x)] == answers, \
        'the evaluator must re-derive every probe answer from the presented rows'
    return x, torch.tensor(answers)


@dataclass
class Panel:
    name: str
    arm: str
    n: int
    chunks: list            # (Inputs, answers, lines, mask, uniform)


def prepare_panel(name, arm, units, block=32):
    chunks = []
    for start in range(0, len(units), block):
        x, answers = pack_units(units[start:start+block], arm)
        lines = F1.supporting_lines(x)
        mask = F1.line_token_mask(x, lines)
        chunks.append((x, answers, lines, mask, F1.uniform_line_mass(x, lines)))
    return Panel(name, arm, len(units), chunks)


@torch.no_grad()
def score_panel(model, panel):
    """Correct count, correct-line attention and the prediction distribution. Read-only."""
    n = correct = 0
    mass_sum = uniform_sum = 0.
    per_step = None
    counts, per_relation = {}, {str(r): [0, 0] for r in ATTRIBUTE_RELATIONS}
    for x, answers, lines, mask, uniform in panel.chunks:
        logits, mass = F1.correct_line_mass(model, x, mask)
        predictions = logits.argmax(-1)
        hit = predictions == answers
        correct += int(hit.sum())
        n += int(answers.numel())
        mass_sum += float(mass.mean()) * int(answers.numel())
        uniform_sum += float(uniform.mean()) * int(answers.numel())
        block = mass.mean((0, 2)) * int(answers.numel())
        per_step = block if per_step is None else per_step + block
        for token in predictions.tolist():
            counts[token] = counts.get(token, 0) + 1
        for r, ok in zip(x.questions[:, 2].tolist(), hit.tolist()):
            per_relation[str(r)][0] += 1
            per_relation[str(r)][1] += int(ok)
    shares = [c/n for c in counts.values()]
    return dict(
        panel=panel.name, arm=panel.arm, n=n, correct=correct, accuracy=_num(correct/n),
        correct_line_mass=_num(mass_sum/n), uniform_line_mass=_num(uniform_sum/n),
        mass_by_step=[_num(v) for v in (per_step/n).tolist()],
        distinct_predictions=len(counts), top1_share=_num(max(shares)),
        prediction_entropy=_num(max(0., -sum(p*math.log(p) for p in shares))),
        acc_by_relation={k: dict(n=v[0], correct=v[1],
                                 acc=_num(v[1]/v[0]) if v[0] else None)
                         for k, v in per_relation.items()})


# ======================================= the small fixed routing probe (v1-style, shared)

def routing_plans(seed, visits):
    """The routing probe's question plan: drawn once, shared by all four arms."""
    return F1.plan_batch(random.Random(ns_routing_world(seed)),
                         random.Random(ns_routing_plan(seed)), visits, frozenset(),
                         blind_lines=BLIND_LINES, balance=False)


def routing_probe(plans, info, arm):
    batch = arm_batch(plans, info, arm)
    x, y = batch.canonical, batch.canonical_targets
    mask = F1.line_token_mask(x, y.lines[:, 0])
    uniform = F1.uniform_line_mass(x, y.lines[:, 0])
    relation = x.questions[:, 2]
    return F1.Probe(batch, mask, uniform, relation != LINK, relation, arm, len(plans))


# ================================================ freeze-before-growth transfer cells
# Paired and NESTED: one question per unit, fixed across every cell of that unit, always
# answerable from the common 16-fact core, with facts 16 < 24 < 64 and filler 0 < .5 < 1
# nested by construction. The genuine full 64-fact 16-person world is the e16-f64-x100
# cell. Signatures of every presented cell are frozen before training and excluded.

@dataclass
class TransferUnit:
    full: list
    core: list              # the common 16-fact core (sorted original indices)
    fact_order: list        # the remaining fact rows, in a fixed random order
    filler_order: list      # the filler/gap rows, in a fixed random order
    others: int
    where: int
    q: list
    answer: int


def transfer_units(entities, n=TRANSFER_N, namespace=NS_TRANSFER):
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec(entities=entities)
    units = []
    for i in range(n):
        rng = random.Random(f'{namespace}:e{entities}:{i}')
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == entities
        full = [[] if row.question else list(row.tokens) for row in rows]
        where = next(k for k, row in enumerate(rows) if row.question)
        facts, others = S._row_classes(full)
        assert len(facts) == 4*entities, (len(facts), entities)
        core = sorted(rng.sample(facts, BLIND_LINES))
        attr, _ = S._visible_facts(full, core)
        assert attr
        key = sorted(attr)[rng.randrange(len(attr))]
        rest = [k for k in facts if k not in set(core)]
        rng.shuffle(rest)
        order = list(others)
        rng.shuffle(order)
        units.append(TransferUnit(full, core, rest, order, len(others), where,
                                  [QUESTION, key[0], key[1], ANSWER], attr[key][0]))
    return units


def transfer_keep(unit, fact_lines, filler_fraction):
    assert fact_lines >= BLIND_LINES
    keep = set(unit.core) | set(unit.fact_order[:fact_lines-BLIND_LINES])
    keep.update(unit.filler_order[:int(round(filler_fraction*unit.others))])
    return sorted(keep)


def transfer_panel(cell, units, block=32):
    chunks = []
    for start in range(0, len(units), block):
        memories, qs, owners, wheres, answers = [], [], [], [], []
        for u in units[start:start+block]:
            keep = transfer_keep(u, cell['fact_lines'], cell['filler_fraction'])
            memories.append([u.full[old] for old in keep])
            owners.append(len(memories)-1)
            qs.append(list(u.q))
            wheres.append(sum(1 for old in keep if old < u.where))
            answers.append(u.answer)
        x = data.pack(memories, qs, owners, wheres)
        assert [p[-1]['target'] for p in A.truth_paths(x)] == answers
        answers = torch.tensor(answers)
        lines = F1.supporting_lines(x)
        mask = F1.line_token_mask(x, lines)
        chunks.append((x, answers, lines, mask, F1.uniform_line_mass(x, lines)))
    return Panel(cell['name'], 'A', len(units), chunks)


# =================================================================== routing diagnostics
# EVERYTHING here runs under torch.no_grad or on a deepcopy. The live model, its .grad and
# the live optimizer state are never touched; tests/ proves it with poisoned gradients.

def _grad(scalar, params, retain=False):
    """Gradient with unused parameters reported as exact zeros, not None."""
    raw = torch.autograd.grad(scalar, params, allow_unused=True, retain_graph=retain)
    return [torch.zeros_like(p) if g is None else g for p, g in zip(params, raw)]


def _norm(vectors):
    return math.sqrt(sum(float((g.double()*g.double()).sum()) for g in vectors))


def _dot(a, b):
    return sum(float((x.double()*y.double()).sum()) for x, y in zip(a, b))


def mass_selections(probe, kinds):
    """The three mass groups and the three record groups, from VISIBLE question tokens."""
    relation = probe.relation
    kind = list(kinds)
    attribute = relation != LINK
    link = relation == LINK
    one_hop = torch.tensor([k == 'one_hop' for k in kind])
    terminal = torch.tensor([k == 'terminal' for k in kind])
    assert int(attribute.sum()) == int(one_hop.sum()) + int(terminal.sum())
    return dict(all=None, attribute=attribute, link=link), \
        dict(one_hop=one_hop, terminal=terminal, link=link)


def _mass_scalars(model, x, mask, selects):
    """All three mass means from ONE forward pass, with graph."""
    _, mass = F1.correct_line_mass(model, x, mask)
    return {name: (mass.mean() if sel is None else mass[sel].mean())
            for name, sel in selects.items()}


def component_losses(model, batch, attribute, link):
    """attribute / LINK / monolithic answer CE, and the registered 0.75/0.25 sum."""
    canonical = model(batch.canonical)
    monolithic = model(batch.monolithic)
    ya = batch.canonical_targets.answer
    ym = batch.monolithic_targets.answer
    ce_canonical = F.cross_entropy(canonical, ya)
    out = dict(attribute=F.cross_entropy(canonical[attribute], ya[attribute]),
               link=F.cross_entropy(canonical[link], ya[link]),
               monolithic=F.cross_entropy(monolithic, ym),
               canonical=ce_canonical)
    out['registered'] = CANONICAL_WEIGHT*ce_canonical + MONOLITHIC_WEIGHT*out['monolithic']
    return out


@torch.no_grad()
def attention_report(model, probe, kinds):
    """Diagnostics (1) and (5): raw mass and mass/uniform by read, head and question
    position, plus separate prediction distributions and per-relation accuracy."""
    x, y = probe.batch.canonical, probe.batch.canonical_targets
    logits, attention = model(x, trace=True)
    q, steps, heads, qtokens, width = attention.shape
    real = x.questions.ne(0)
    last = real.sum(-1) - 1
    read = attention.gather(3, last[:, None, None, None, None].expand(
        q, steps, heads, 1, width)).squeeze(3)
    mass = (read * probe.mask[:, None, None, :]).sum(-1)                  # [q, steps, heads]
    by_position = (attention * probe.mask[:, None, None, None, :]).sum(-1)  # [q,s,h,qtok]
    _, groups = mass_selections(probe, kinds)
    predictions = logits.argmax(-1)
    correct = predictions == y.answer
    row = dict(probe_loss=_num(F.cross_entropy(logits, y.answer)),
               probe_acc=_num(correct.float().mean()),
               uniform_line_mass=_num(probe.uniform.mean()),
               correct_line_mass=_num(mass.mean()),
               mass_over_uniform=_num(
                   mass.mean((1, 2)).double().div(probe.uniform).mean()),
               mass_by_step=[_num(mass[:, s].mean()) for s in range(steps)],
               mass_by_step_head=[[_num(mass[:, s, h].mean()) for h in range(heads)]
                                  for s in range(steps)],
               mass_by_position=[[[_num(by_position[real[:, p], s, h, p].mean())
                                   if bool(real[:, p].any()) else None
                                   for p in range(qtokens)]
                                  for h in range(heads)] for s in range(steps)])
    for name, select in groups.items():
        n = int(select.sum())
        picked = predictions[select].tolist()
        counts = {}
        for token in picked:
            counts[token] = counts.get(token, 0) + 1
        shares = [c/max(1, n) for c in counts.values()] or [1.]
        row[f'{name}_n'] = n
        row[f'{name}_acc'] = _num(correct[select].float().mean()) if n else None
        row[f'{name}_correct_line_mass'] = _num(mass[select].mean()) if n else None
        row[f'{name}_mass_over_uniform'] = _num(
            mass[select].mean((1, 2)).double().div(probe.uniform[select]).mean()) if n else None
        row[f'{name}_distinct_predictions'] = len(counts)
        row[f'{name}_top1_share'] = _num(max(shares))
        row[f'{name}_prediction_entropy'] = _num(
            max(0., -sum(p*math.log(p) for p in shares)))
    per_relation = {}
    for r in ATTRIBUTE_RELATIONS:
        pick = (probe.relation == r)
        n = int(pick.sum())
        per_relation[str(r)] = dict(n=n, correct=int(correct[pick].sum()),
                                    acc=_num(correct[pick].float().mean()) if n else None)
    row['acc_by_relation'] = per_relation
    return row


def routing_report(model, probe, kinds, etas=CENTRAL_ETAS):
    """Diagnostics (2) and (3): unrounded gradient reductions and central differences.

    ``directional_<loss>_<mass>`` is the exact plain-SGD derivative
    d/d(eta) mass(theta - eta * grad L) at eta = 0, i.e. -<grad L, grad mass>.
    ``central_<loss>_<mass>_<eta>`` is (mass(theta - eta g) - mass(theta + eta g)) / (2 eta)
    on disposable copies. Disagreement and cancellation are reported, not resolved.
    """
    selects, _ = mass_selections(probe, kinds)
    clone = copy.deepcopy(model)
    clone.eval()
    params = list(clone.parameters())
    x = probe.batch.canonical
    out = {}

    scalars = _mass_scalars(clone, x, probe.mask, selects)
    names = list(scalars)
    mass_grads = {}
    for i, name in enumerate(names):
        mass_grads[name] = _grad(scalars[name], params, retain=i < len(names)-1)
        out[f'mass_{name}'] = _raw(scalars[name])
        out[f'grad_norm_mass_{name}'] = _raw(_norm(mass_grads[name]))

    attribute, link = selects['attribute'], selects['link']
    losses = component_losses(clone, probe.batch, attribute, link)
    keys = list(losses)
    loss_grads = {}
    for i, key in enumerate(keys):
        loss_grads[key] = _grad(losses[key], params, retain=i < len(keys)-1)
        out[f'loss_{key}'] = _raw(losses[key])
        out[f'grad_norm_loss_{key}'] = _raw(_norm(loss_grads[key]))

    for key, g_loss in loss_grads.items():
        norm_loss = _norm(g_loss)
        for name, g_mass in mass_grads.items():
            dot = _dot(g_loss, g_mass)
            norm_mass = _norm(g_mass)
            out[f'directional_{key}_{name}'] = _raw(-dot)
            out[f'cosine_{key}_{name}'] = (
                _raw(-dot/(norm_loss*norm_mass)) if norm_loss and norm_mass else None)

    # Central finite differences validate the analytic derivative of the REGISTERED loss.
    g = loss_grads['registered']
    for eta in etas:
        minus, plus = copy.deepcopy(clone), copy.deepcopy(clone)
        with torch.no_grad():
            for p, q_, d in zip(minus.parameters(), plus.parameters(), g):
                p.sub_(eta*d)
                q_.add_(eta*d)
            low = _mass_scalars(minus, x, probe.mask, selects)
            high = _mass_scalars(plus, x, probe.mask, selects)
        tag = f'{eta:g}'
        for name in names:
            central = (float(low[name]) - float(high[name])) / (2*eta)
            out[f'central_registered_{name}_eta{tag}'] = _raw(central)
            analytic = out[f'directional_registered_{name}']
            out[f'central_minus_analytic_{name}_eta{tag}'] = (
                _raw(central - analytic) if analytic is not None else None)
        del minus, plus
    del clone, mass_grads, loss_grads
    return out


def adam_report(model, optimizer, probe, kinds, seed, update, arm, lr, visits):
    """Diagnostic (4): ONE hypothetical AdamW update on a disposable model AND optimizer.

    This is OPTIMIZER-SPECIFIC and is not the plain-SGD derivative above. The batch comes
    from an independent training-distribution stream keyed by (seed, update), so it
    consumes no training randomness and a resumed run measures the identical thing.
    """
    selects, _ = mass_selections(probe, kinds)
    before_fingerprint = C.fingerprint(model)
    clone = copy.deepcopy(model)
    clone_optimizer = A.T.optimizer_for(clone)
    clone_optimizer.load_state_dict(copy.deepcopy(optimizer.state_dict()))
    plans, info = F1.plan_batch(random.Random(ns_adam_world(seed, update)),
                                random.Random(ns_adam_plan(seed, update)), visits,
                                frozenset(), blind_lines=BLIND_LINES, balance=False)
    batch = arm_batch(plans, info, arm)
    with torch.no_grad():
        before = {k: float(v) for k, v in
                  _mass_scalars(clone, probe.batch.canonical, probe.mask, selects).items()}
    clone.train()
    step = F1.training_step(clone, clone_optimizer, batch, lr)
    clone.eval()
    with torch.no_grad():
        after = {k: float(v) for k, v in
                 _mass_scalars(clone, probe.batch.canonical, probe.mask, selects).items()}
    assert C.fingerprint(model) == before_fingerprint, \
        'the AdamW diagnostic must leave the live model byte-identical'
    out = dict(adam_lr=_raw(lr), adam_visits=visits,
               adam_batch_loss=step['train_loss'], adam_grad_norm=step['grad_norm'])
    for name in before:
        out[f'adam_mass_before_{name}'] = _raw(before[name])
        out[f'adam_mass_delta_{name}'] = _raw(after[name] - before[name])
    del clone, clone_optimizer, batch
    return out


# ========================================================================= onset detector

def first_qualified_onset(points, threshold=ONSET_CORRECT, window=ONSET_WINDOW,
                          every=PROBE_EVERY, minimum=ONSET_MIN_UPDATE):
    """Earliest t >= minimum whose five scheduled probes t-200..t all reach the threshold.

    ``points`` maps a scheduled update to the number correct out of 512, or to None.
    A MISSING probe never qualifies; it is not interpolated and not ignored.
    """
    scheduled = sorted(points)
    for t in scheduled:
        if t < minimum:
            continue
        needed = [t - window + k*every for k in range(window//every + 1)]
        if all(points.get(u) is not None and points[u] >= threshold for u in needed):
            return t
    return None


def onset_summary(points, updates=UPDATES, threshold=ONSET_CORRECT,
                  window=ONSET_WINDOW, every=PROBE_EVERY):
    """First onset, regressions AFTER it, and the final-window status -- kept separate."""
    onset = first_qualified_onset(points, threshold, window, every)
    regressions = sorted(t for t, v in points.items()
                         if onset is not None and t > onset
                         and (v is None or v < threshold))
    final_window = [updates - window + k*every for k in range(window//every + 1)]
    final_ok = all(points.get(u) is not None and points[u] >= threshold
                   for u in final_window)
    return dict(first_qualified_onset=onset, regressions_after_onset=regressions,
                final_window=final_window, final_window_qualified=bool(final_ok),
                probes_present=len([v for v in points.values() if v is not None]),
                threshold=threshold, window=window)


# ================================================================== capacity guard/queue

WORKER_VERBS = ('worker', 'train', 'wave', 'longrun', 'extend', 'supervise')


def worker_processes():
    """Worker PROCESSES on this machine, not shell wrappers.

    A process counts when its command line runs a repository ``scripts/*.py`` under a
    python interpreter with one of the worker verbs. ``ps`` output is data, never a
    command: only the pid, the script name and the verb are used.
    """
    try:
        raw = subprocess.run(['ps', '-Ao', 'pid=,ppid=,command='], capture_output=True,
                             text=True, timeout=20).stdout
    except Exception:
        return None
    mine = {os.getpid(), os.getppid()}
    found = []
    for line in raw.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, _, command = int(parts[0]), parts[1], parts[2]
        if pid in mine or 'python' not in command:
            continue
        script = re.search(r'([\w./-]*scripts/(\w+)\.py)', command)
        if not script:
            continue
        tokens = set(command.split())
        verb = sorted(tokens & set(WORKER_VERBS))
        if not verb:
            continue
        found.append(dict(pid=pid, script=script.group(2), verb=verb[0],
                          audit=script.group(2).startswith('fable_startup_factorial')))
    return found


def capacity_report(max_audit=MAX_AUDIT_WORKERS, max_total=MAX_TOTAL_WORKERS):
    found = worker_processes()
    if found is None:
        return dict(available=False, reason='ps unavailable')
    audit = [p for p in found if p['audit']]
    return dict(available=True, workers=found, total=len(found), audit=len(audit),
                max_audit=max_audit, max_total=max_total,
                admits_one_more=len(audit) < max_audit and len(found) < max_total)


def require_capacity(max_audit=MAX_AUDIT_WORKERS, max_total=MAX_TOTAL_WORKERS, force=False):
    """Refuse to start when the machine is full. A refusal is a SCHEDULING result."""
    report = capacity_report(max_audit, max_total)
    if force or not report['available'] or report['admits_one_more']:
        return report
    print(json.dumps(dict(refused='capacity', **{k: report[k] for k in
                          ('total', 'audit', 'max_audit', 'max_total')},
                          workers=[f"{p['pid']}:{p['script']}:{p['verb']}"
                                   for p in report['workers']],
                          note='scheduling result, not a model failure')), flush=True)
    raise SystemExit(3)


# ========================================================================= chunked runner

@dataclass
class RunConfig:
    seed: int
    arm: str
    updates: int = UPDATES
    visits: int = VISITS
    probe_every: int = PROBE_EVERY
    routing_every: int = PROBE_EVERY
    validation_n: int = VALIDATION_N
    routing_visits: int = VISITS
    adam_visits: int = VISITS
    schedule: str = 'factorial'          # 'factorial' | 'longrun'
    milestones: tuple = ()
    routing: bool = True
    adam: bool = True

    def lr(self, step):
        return lr_factorial(step) if self.schedule == 'factorial' else lr_longrun(step)


def _latest_resume(folder):
    files = sorted(Path(folder).glob('resume-*.pt'))
    return files[-1] if files else None


def _rng_state(rng, vrng):
    return dict(world=rng.getstate(), plan=vrng.getstate(), torch=torch.get_rng_state())


def _restore(state, rng, vrng):
    rng.setstate(state['world'])
    vrng.setstate(state['plan'])
    torch.set_rng_state(state['torch'])


def run_chunk(folder, cfg, forbidden, budget_seconds=None, chunk_updates=None,
              validation=None, routing=None, kinds=None, quiet=False):
    """One resumable chunk. A resume restores the model, the optimizer, BOTH data streams,
    the torch RNG, the data cursor and the diagnostics, so chunked == unchunked."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if validation is None:
        validation = prepare_panel('validation', cfg.arm,
                                   probe_units(ns_validation(cfg.seed), cfg.validation_n))
    if routing is None:
        plans, info = routing_plans(cfg.seed, cfg.routing_visits)
        routing, kinds = routing_probe(plans, info, cfg.arm), canonical_kinds(plans)

    model = A.new_model(cfg.seed)          # identical init per seed across all four arms
    assert model.parameters_count() == PARAMETERS, model.parameters_count()
    optimizer = A.T.optimizer_for(model)
    rng, vrng = streams(cfg.seed)
    step, rows = 0, []
    previous = _latest_resume(folder)
    if previous is not None:
        state = P.load(previous)
        model.load_state_dict(state['state_dict'], strict=True)
        optimizer.load_state_dict(state['optimizer'])
        _restore(state['rng'], rng, vrng)
        step, rows = state['step'], list(state['rows'])
    started, first = time.monotonic(), step

    def measure(at):
        was = model.training
        model.eval()
        row = dict(arm=cfg.arm, seed=cfg.seed, update=at, lr=_raw(cfg.lr(at)),
                   validation=score_panel(model, validation),
                   **attention_report(model, routing, kinds))
        if cfg.routing and at % cfg.routing_every == 0:
            row.update(routing_report(model, routing, kinds))
            if cfg.adam:
                row.update(adam_report(model, optimizer, routing, kinds, cfg.seed, at,
                                       cfg.arm, cfg.lr(at), cfg.adam_visits))
        row['elapsed'] = _num(time.monotonic()-started)
        model.train(was)
        return row

    while True:
        if step % cfg.probe_every == 0 and (not rows or rows[-1]['update'] != step):
            rows.append(measure(step))
            if not quiet:
                print(json.dumps(dict(update=step, arm=cfg.arm, seed=cfg.seed,
                                      correct=rows[-1]['validation']['correct'],
                                      probe_acc=rows[-1]['probe_acc'])), flush=True)
        if step in cfg.milestones:
            path = folder/f'checkpoint-{step:06d}.pt'
            if not path.exists():
                torch.save(dict(state_dict=model.state_dict(), seed=cfg.seed, arm=cfg.arm,
                                updates=step, architecture=dict(vocab=68, width=48,
                                                                heads=4, steps=3)), path)
        if step >= cfg.updates:
            break
        if chunk_updates is not None and step - first >= chunk_updates:
            break
        if budget_seconds is not None and time.monotonic()-started >= budget_seconds:
            break
        plans, info = plan_batch(rng, vrng, cfg.visits, forbidden)
        batch = arm_batch(plans, info, cfg.arm)
        last = F1.training_step(model, optimizer, batch, cfg.lr(step))
        step += 1
        if rows and rows[-1]['update'] == step - 1:
            rows[-1].update(train_loss=last['train_loss'], train_acc=last['train_acc'],
                            grad_norm=last['grad_norm'],
                            mean_kept_lines=_num(sum(
                                batch.accounting['curriculum']['kept_lines'])/cfg.visits))

    payload = dict(state_dict=model.state_dict(), optimizer=optimizer.state_dict(),
                   rng=_rng_state(rng, vrng), step=step, rows=rows, seed=cfg.seed,
                   arm=cfg.arm, updates=cfg.updates, schedule=cfg.schedule,
                   architecture=dict(vocab=68, width=48, heads=4, steps=3))
    torch.save(payload, folder/f'resume-{step:06d}.pt')
    with (folder/'trace.jsonl').open('w') as handle:      # rewritten from the saved rows
        for row in rows:
            handle.write(json.dumps(row)+'\n')
    return dict(step=step, first_step=first, updates=cfg.updates, done=step >= cfg.updates,
                fingerprint=C.fingerprint(model), seconds=_num(time.monotonic()-started),
                rows=len(rows),
                updates_per_second=_num((step-first)/max(1e-9, time.monotonic()-started)))


# ============================================================================ plan/freeze

def _register_key(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def registered_forbidden():
    v1 = json.loads((P.OUT/'astra_canonical_operator_launch.json').read_text())
    path = Path(v1['exclusion_path'])
    return set(json.loads(path.read_text())), v1, path


def cross_arm_audit(seed, forbidden, updates=3, visits=VISITS):
    """Prove that within a seed the arms differ ONLY in which story rows are readable."""
    rng, vrng = streams(seed)
    checks, rows_seen = [], {}
    for update in range(updates):
        plans, info = plan_batch(rng, vrng, visits, forbidden)
        batches = {arm: arm_batch(plans, info, arm) for arm in ARM_NAMES}
        reference = batches['A']
        identical = True
        for arm, b in batches.items():
            for part in ('canonical', 'monolithic'):
                x, rx = getattr(b, part), getattr(reference, part)
                y = b.canonical_targets if part == 'canonical' else b.monolithic_targets
                ry = (reference.canonical_targets if part == 'canonical'
                      else reference.monolithic_targets)
                identical &= bool(torch.equal(x.questions, rx.questions))
                identical &= bool(torch.equal(x.owner, rx.owner))
                identical &= bool(torch.equal(y.answer, ry.answer))
            identical &= b.accounting['kinds'] == reference.accounting['kinds']
        nested = True
        for plan in plans:
            keeps = {arm: set(F1.arm_keep(plan, arm)) for arm in ARM_NAMES}
            nested &= (keeps['A'] < keeps['B'] < keeps['D'] and keeps['A'] < keeps['C'] < keeps['D']
                       and keeps['A'] == set(plan.kept16)
                       and keeps['C'] == set(plan.facts)
                       and keeps['D'] == set(plan.facts) | set(plan.others))
        # The SAME original row supports every record in every arm, only renumbered.
        supported = True
        for part in ('canonical', 'monolithic'):
            maps = {arm: [F1.arm_keep(p, arm) for p in plans] for arm in ARM_NAMES}
            base = getattr(reference, part)
            ry = (reference.canonical_targets if part == 'canonical'
                  else reference.monolithic_targets)
            for arm in ARM_NAMES:
                y = (batches[arm].canonical_targets if part == 'canonical'
                     else batches[arm].monolithic_targets)
                for owner, la, lb in zip(base.owner.tolist(), ry.lines.tolist(),
                                         y.lines.tolist()):
                    supported &= ([maps['A'][owner][i] for i in la]
                                  == [maps[arm][owner][i] for i in lb])
        rows_seen = {arm: int(batches[arm].canonical.memory.shape[1]) for arm in ARM_NAMES}
        checks.append(dict(update=update, questions_answers_weights_identical=identical,
                           story_rows_nested=nested, support_rows_identical=supported,
                           rows_per_visit=rows_seen,
                           signature_checks=info['signature_checks'],
                           census=info['census']))
        if not (identical and nested and supported):
            raise RuntimeError(f'cross-arm identity audit failed at update {update}')
    return dict(updates=updates, visits=visits, checks=checks,
                initial_fingerprint=C.fingerprint(A.new_model(seed)),
                parameters=A.new_model(seed).parameters_count())


def build_plan(out, seed, forbidden, audit_updates=3, validation_n=VALIDATION_N,
               transfer_signatures=()):
    """Everything frozen before the first update of this seed, with its hashes."""
    folder = out/'plan'
    folder.mkdir(parents=True, exist_ok=True)
    probes = {}
    union = set(forbidden) | set(transfer_signatures)
    for name, namespace in (('validation', ns_validation(seed)),
                            ('confirmation', ns_confirm(seed))):
        units = probe_units(namespace, validation_n)
        signatures, per_arm = [], {}
        for u in units:
            prefixes = condition_prefixes(u.full, u.kept16, u.facts, u.others)
            for condition, pre in prefixes.items():
                sig = _signature(pre, u.q)
                signatures.append(sig)
                per_arm.setdefault(condition, []).append(sig)
        collisions = sorted(set(signatures) & set(forbidden))
        probes[name] = dict(namespace=namespace, n=len(units),
                            questions=A.digest([u.q for u in units]),
                            answers=A.digest([u.answer for u in units]),
                            signature_digest=A.digest(sorted(set(signatures))),
                            signatures=len(set(signatures)),
                            registered_panel_collisions=len(collisions),
                            attribute_only=all(u.q[2] in ATTRIBUTE_RELATIONS for u in units))
        union |= set(signatures)
    plans, info = routing_plans(seed, VISITS)
    routing_signatures = [sig for plan in plans for _, sig in plan_signatures(plan)]
    union |= set(routing_signatures)
    probes['routing'] = dict(world_namespace=ns_routing_world(seed),
                             plan_namespace=ns_routing_plan(seed), visits=VISITS,
                             records=info['records'], census=info['census'],
                             kinds=canonical_kinds(plans),
                             signature_digest=A.digest(sorted(set(routing_signatures))))
    audit = cross_arm_audit(seed, union, audit_updates)
    exclusions = sorted(union)
    C.write_new(folder/f'exclusions-seed-{seed}.json', exclusions)
    record = dict(experiment=EXPERIMENT, seed=seed,
                  world_namespace=ns_world(seed), plan_namespace=ns_plan(seed),
                  probes=probes, exclusion_count=len(exclusions),
                  exclusion_digest=A.digest(exclusions),
                  registered_forbidden=len(forbidden),
                  transfer_signatures=len(set(transfer_signatures)),
                  cross_arm_audit=audit)
    C.write_new(folder/f'plan-seed-{seed}.json', record)
    return record, exclusions


def build_transfer_plan(out, n=TRANSFER_N):
    folder = out/'plan'
    folder.mkdir(parents=True, exist_ok=True)
    signatures, cells = [], {}
    units = {e: transfer_units(e, n) for e in (6, 16)}
    for cell in TRANSFER_CELLS:
        picked = units[cell['entities']]
        sigs = []
        for u in picked:
            keep = transfer_keep(u, cell['fact_lines'], cell['filler_fraction'])
            sigs.append(_signature(_facts_json([u.full[old] for old in keep]), u.q))
        cells[cell['name']] = dict(cell, n=len(picked), signature_digest=A.digest(sorted(set(sigs))))
        signatures.extend(sigs)
    for entities, picked in units.items():
        signatures.extend(_signature(_facts_json(u.full), u.q) for u in picked)
    signatures = sorted(set(signatures))
    C.write_new(folder/'transfer-signatures.json', signatures)
    C.write_new(folder/'transfer-plan.json',
                dict(namespace=NS_TRANSFER, n=n, cells=cells,
                     questions={str(e): A.digest([u.q for u in picked])
                                for e, picked in units.items()},
                     signatures=len(signatures), digest=A.digest(signatures),
                     threshold=TRANSFER_CORRECT))
    return signatures


def plan(args):
    out = Path(args.out) if args.out else OUT
    prereg = out/'PREREGISTRATION.md'
    if not prereg.exists():
        raise RuntimeError(f'write {prereg} before planning; plan hashes it')
    forbidden, v1, exclusion_path = registered_forbidden()
    seeds = [int(s) for s in args.seeds.split(',')] if args.seeds else list(REGISTERED_SEEDS)
    transfer = build_transfer_plan(out, args.transfer_n)
    records = {}
    for seed in seeds:
        record, _ = build_plan(out, seed, forbidden, args.audit_updates,
                               args.validation_n, transfer)
        records[str(seed)] = dict(
            exclusion_digest=record['exclusion_digest'],
            exclusion_count=record['exclusion_count'],
            validation=record['probes']['validation']['signature_digest'],
            confirmation=record['probes']['confirmation']['signature_digest'],
            routing=record['probes']['routing']['signature_digest'],
            initial_fingerprint=record['cross_arm_audit']['initial_fingerprint'])
        print(json.dumps(dict(seed=seed, **records[str(seed)])), flush=True)
    files = {_register_key(p): C.sha(p) for p in (
        Path(__file__).resolve(), HERE.parent/'tests/test_fable_startup_factorial_v2.py',
        Path(F1.__file__).resolve(), Path(S.__file__).resolve(),
        Path(V.__file__).resolve(), Path(T.__file__).resolve(), Path(E.__file__).resolve(),
        Path(A.__file__).resolve(), Path(R.__file__).resolve(), Path(P.__file__).resolve(),
        Path(C.__file__).resolve(), Path(data.__file__).resolve(),
        ROOT/'premonition/toy_ladder.py', ROOT/'premonition/batch.py',
        ROOT/'scripts/premonition_pair_suite.py',
        ROOT/'scripts/premonition_token_initialization_probe.py',
        BASE/'design/v3/18-startup-factorial-v2-preregistration-draft.md', prereg)}
    for seed in seeds:
        for name in (f'plan-seed-{seed}.json', f'exclusions-seed-{seed}.json'):
            files[_register_key(out/'plan'/name)] = C.sha(out/'plan'/name)
    for name in ('transfer-plan.json', 'transfer-signatures.json'):
        files[_register_key(out/'plan'/name)] = C.sha(out/'plan'/name)
    manifest = dict(
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        experiment=EXPERIMENT, seeds=seeds, arms={k: dict(v) for k, v in ARMS.items()},
        blind_lines=BLIND_LINES, parameters=PARAMETERS,
        schedule=dict(updates=UPDATES, visits_per_update=VISITS,
                      warmup_updates=WARMUP_UPDATES, flat_lr=FLAT_LR,
                      loss=f'{CANONICAL_WEIGHT} canonical + {MONOLITHIC_WEIGHT} monolithic',
                      probe_every=PROBE_EVERY, routing_every=PROBE_EVERY,
                      chunk_seconds_max=CHUNK_SECONDS_MAX),
        onset=dict(metric='attribute-only 512-question validation probe',
                   threshold_correct=ONSET_CORRECT, n=VALIDATION_N,
                   window_updates=ONSET_WINDOW, minimum_update=ONSET_MIN_UPDATE,
                   definition='earliest t>=200 with t-200,t-150,t-100,t-50,t all present '
                              'and each >= 461/512; missing probes do not qualify'),
        longrun=dict(arm=LONGRUN_ARM, updates=LONGRUN_UPDATES,
                     flat_until=LONGRUN_FLAT_UNTIL, final_lr=LONGRUN_FINAL_LR,
                     midpoint=LONGRUN_MIDPOINT, routing_every=LONGRUN_ROUTING_EVERY),
        transfer=dict(cells=[dict(c) for c in TRANSFER_CELLS], n=args.transfer_n,
                      threshold_correct=TRANSFER_CORRECT),
        capacity=dict(max_audit_workers=MAX_AUDIT_WORKERS,
                      max_total_workers=MAX_TOTAL_WORKERS),
        exclusion_path=str(exclusion_path), plans=records,
        v1_launch_sha256=C.sha(P.OUT/'astra_canonical_operator_launch.json'), files=files)
    C.write_new(out/'launch.json', manifest)
    capacity = capacity_report()
    print(json.dumps(dict(files=len(files), launch=C.sha(out/'launch.json'),
                          transfer_signatures=len(transfer),
                          capacity={k: capacity[k] for k in capacity
                                    if k != 'workers'})), flush=True)
    print('launch plan tested; no worker started', flush=True)


def check_manifest(out=None):
    out = Path(out) if out else OUT
    manifest = json.loads((out/'launch.json').read_text())
    for name, expected in manifest['files'].items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT/name
        if C.sha(path) != expected:
            raise RuntimeError(f'registered file changed: {name}')
    return manifest


def load_exclusions(out, seed):
    return set(json.loads((Path(out)/'plan'/f'exclusions-seed-{seed}.json').read_text()))


# ================================================================== train / longrun / CLI

def _points(rows):
    return {int(r['update']): (r['validation']['correct']
                               if r.get('validation') else None) for r in rows}


def _finish(folder, cfg, rows, manifest, out, result, seconds):
    """Final checkpoint, the SECOND untouched probe, and the onset summary."""
    checkpoint = folder/'final.pt'
    state = P.load(_latest_resume(folder))
    if not checkpoint.exists():
        torch.save(dict(state_dict=state['state_dict'], seed=cfg.seed, arm=cfg.arm,
                        updates=state['step'],
                        architecture=dict(vocab=68, width=48, heads=4, steps=3),
                        launch_sha256=C.sha(out/'launch.json')), checkpoint)
    model = A.CanonicalOperator(**dict(vocab=68, width=48, heads=4, steps=3))
    model.load_state_dict(P.load(checkpoint)['state_dict'], strict=True)
    model.eval()
    fingerprint = C.fingerprint(model)
    confirmation = score_panel(model, prepare_panel(
        'confirmation', cfg.arm, probe_units(ns_confirm(cfg.seed), cfg.validation_n)))
    validation_final = rows[-1]['validation'] if rows else None
    summary = onset_summary(_points(rows), cfg.updates)
    assert C.fingerprint(model) == fingerprint, 'the final checkpoint must not change'
    payload = dict(experiment=EXPERIMENT, seed=cfg.seed, arm=cfg.arm, complete=True,
                   updates=state['step'], schedule=cfg.schedule,
                   seconds=_num(seconds), fingerprint=fingerprint,
                   checkpoint_sha256=C.sha(checkpoint),
                   onset=summary, validation_final=validation_final,
                   confirmation=confirmation,
                   onset_independently_confirmed=bool(
                       summary['first_qualified_onset'] is not None
                       and confirmation['correct'] >= ONSET_CORRECT),
                   peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   updates_per_second=result.get('updates_per_second'),
                   launch_sha256=C.sha(out/'launch.json'))
    if not (folder/'completion.json').exists():
        C.write_new(folder/'completion.json', payload)
    return payload


def _run(args, cfg, folder, out, manifest):
    require_capacity(force=args.force_capacity)
    budget = args.budget_seconds
    assert budget is None or budget <= CHUNK_SECONDS_MAX, \
        f'a chunk must stay under {CHUNK_SECONDS_MAX} s of compute'
    forbidden = load_exclusions(out, cfg.seed)
    started = time.monotonic()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        result = run_chunk(folder, cfg, forbidden, budget_seconds=budget,
                           chunk_updates=args.chunk_updates)
        record = folder/f'chunk-{result["step"]:06d}.json'
        if not record.exists():
            C.write_new(record, dict(result, budget_seconds=budget,
                                     launch_sha256=C.sha(out/'launch.json')))
        if result['done']:
            rows = P.load(_latest_resume(folder))['rows']
            done = _finish(folder, cfg, rows, manifest, out, result,
                           time.monotonic()-started)
            print(json.dumps(dict(arm=cfg.arm, seed=cfg.seed, complete=True,
                                  onset=done['onset']['first_qualified_onset'],
                                  confirmation=done['confirmation']['correct'],
                                  final=done['validation_final']['correct'])), flush=True)
        else:
            print(json.dumps(result), flush=True)
            print(f'INCOMPLETE: rerun the same command to continue from update '
                  f'{result["step"]}', flush=True)
        check_manifest(out)
        return result
    except BaseException as exc:
        failure = folder/f'failure-{int(time.time())}.json'
        C.write_new(failure, dict(seed=cfg.seed, arm=cfg.arm, complete=False,
                                  error=repr(exc), traceback=traceback.format_exc()))
        raise


def train(args):
    out = Path(args.out) if args.out else OUT
    manifest = check_manifest(out)
    assert args.arm in ARMS, args.arm
    cfg = RunConfig(seed=args.seed, arm=args.arm, updates=args.updates,
                    visits=args.visits, probe_every=args.probe_every,
                    routing_every=args.probe_every, validation_n=args.validation_n,
                    routing_visits=args.routing_visits, adam_visits=args.routing_visits,
                    schedule='factorial')
    return _run(args, cfg, out/f'seed-{cfg.seed}'/cfg.arm, out, manifest)


def longrun(args):
    """The 18,000-update arm-D trajectory: a declared EXTENSION, not a continuation of e0."""
    out = Path(args.out) if args.out else OUT
    manifest = check_manifest(out)
    updates = args.updates if args.updates != UPDATES else LONGRUN_UPDATES
    midpoint = args.midpoint
    cfg = RunConfig(seed=args.seed, arm=LONGRUN_ARM, updates=updates, visits=args.visits,
                    probe_every=args.probe_every, routing_every=args.routing_every,
                    validation_n=args.validation_n, routing_visits=args.routing_visits,
                    adam_visits=args.routing_visits, schedule='longrun',
                    milestones=(midpoint, updates))
    return _run(args, cfg, out/f'longrun-seed-{cfg.seed}', out, manifest)


def transfer(args):
    """Freeze-before-growth: evaluate a FINAL arm-A checkpoint with no updates at all."""
    out = Path(args.out) if args.out else OUT
    check_manifest(out)
    checkpoint = Path(args.checkpoint) if args.checkpoint \
        else out/f'seed-{args.seed}/A/final.pt'
    saved = P.load(checkpoint)
    assert saved['arm'] == 'A', f"transfer expects an arm-A checkpoint, got {saved['arm']}"
    model = A.CanonicalOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    fingerprint = C.fingerprint(model)
    units = {e: transfer_units(e, args.transfer_n) for e in (6, 16)}
    cells = {}
    for cell in TRANSFER_CELLS:
        panel = transfer_panel(cell, units[cell['entities']])
        raw = score_panel(model, panel)
        scored = dict(raw, **cell, passes=raw['correct'] >= TRANSFER_CORRECT)
        cells[cell['name']] = scored
        print(json.dumps({k: scored[k] for k in
                          ('panel', 'n', 'correct', 'accuracy', 'correct_line_mass',
                           'uniform_line_mass', 'passes')}), flush=True)
    assert C.fingerprint(model) == fingerprint, 'the checkpoint must not change'
    folder = out/'transfer'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/f'seed-{args.seed}.json'
    C.write_new(path, dict(checkpoint=str(checkpoint), checkpoint_sha256=C.sha(checkpoint),
                           seed=args.seed, arm='A', trained_updates=saved['updates'],
                           fingerprint_before=fingerprint,
                           fingerprint_after=C.fingerprint(model),
                           n=args.transfer_n, threshold=TRANSFER_CORRECT,
                           no_training=True, cells=cells))
    print('wrote', path, flush=True)


# ==================================================================== report (per seed)

MISSING = '(missing)'


def _load_run(out, seed, arm):
    folder = Path(out)/f'seed-{seed}'/arm
    trace, completion = folder/'trace.jsonl', folder/'completion.json'
    if not trace.exists():
        return None
    rows = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    done = json.loads(completion.read_text()) if completion.exists() else None
    return dict(rows=rows, completion=done, folder=folder)


def _cell(value, width=9):
    return (MISSING if value is None else str(value)).rjust(width)


def _effect(a, b):
    """b - a, or a censoring note when either side never qualified."""
    if a is None and b is None:
        return 'both censored'
    if a is None:
        return f'censored->{b}'
    if b is None:
        return f'{a}->censored'
    return f'{b-a:+d}'


def report(args):
    out = Path(args.out) if args.out else OUT
    seeds = [int(s) for s in args.seeds.split(',')] if args.seeds else list(REGISTERED_SEEDS)
    updates = args.updates
    print(f'# {EXPERIMENT} — per seed, per arm, never averaged')
    print(f'# onset: earliest t>={ONSET_MIN_UPDATE} with the five probes t-{ONSET_WINDOW}..t '
          f'each >= {ONSET_CORRECT}/{VALIDATION_N}; missing probes do not qualify')
    for seed in seeds:
        runs = {arm: _load_run(out, seed, arm) for arm in ARM_NAMES}
        print(f'\n## seed {seed}')
        print('arm  facts filler       onset regressions final-window   final/512'
              ' confirm/512   confirmed')
        onsets, finals = {}, {}
        for arm in ARM_NAMES:
            run = runs[arm]
            if run is None:
                print(f'{arm}    {ARMS[arm]["facts"]:>5} {str(ARMS[arm]["filler"]):>6} '
                      + ' '.join(_cell(None, 11) for _ in range(6)))
                onsets[arm] = finals[arm] = None
                continue
            points = _points(run['rows'])
            summary = onset_summary(points, updates)
            onsets[arm] = summary['first_qualified_onset']
            last = run['rows'][-1]['validation']['correct'] if run['rows'] else None
            finals[arm] = last
            done = run['completion']
            confirm = done['confirmation']['correct'] if done else None
            confirmed = done['onset_independently_confirmed'] if done else None
            print(f'{arm}    {ARMS[arm]["facts"]:>5} {str(ARMS[arm]["filler"]):>6} '
                  f'{_cell(onsets[arm], 11)} '
                  f'{len(summary["regressions_after_onset"]):>11} '
                  f'{str(summary["final_window_qualified"]):>11} {_cell(last, 11)} '
                  f'{_cell(confirm, 11)} {_cell(confirmed, 11)}')
        print('\npre-stated readings (paired within this seed; conditional on these sizes'
              ' and this 2,500-update budget):')
        for label, left, right in (('filler effect  B-A', 'A', 'B'),
                                   ('filler effect  D-C', 'C', 'D'),
                                   ('fact effect    C-A', 'A', 'C'),
                                   ('fact effect    D-B', 'B', 'D')):
            print(f'  {label}: onset {_effect(onsets[left], onsets[right])}, '
                  f'final/512 {_effect(finals[left], finals[right])}')
        if all(onsets[a] is not None for a in ARM_NAMES):
            print(f'  interaction (D-C)-(B-A): onset '
                  f'{(onsets["D"]-onsets["C"])-(onsets["B"]-onsets["A"]):+d}')
        else:
            print('  interaction (D-C)-(B-A): onset censored (an arm never qualified)')
        if all(finals[a] is not None for a in ARM_NAMES):
            print(f'  interaction (D-C)-(B-A): final/512 '
                  f'{(finals["D"]-finals["C"])-(finals["B"]-finals["A"]):+d}')
        else:
            print(f'  interaction (D-C)-(B-A): final/512 {MISSING}')
        if args.trajectories:
            print('\ntrajectory, validation correct out of 512')
            print('update ' + ' '.join(a.rjust(9) for a in ARM_NAMES))
            grid = sorted({u for arm in ARM_NAMES if runs[arm]
                           for u in _points(runs[arm]['rows'])})
            for u in grid:
                cells = [_points(runs[a]['rows']).get(u) if runs[a] else None
                         for a in ARM_NAMES]
                print(f'{u:>6} ' + ' '.join(_cell(c) for c in cells))
        print('\nrouting diagnostics (unrounded; SGD derivative and the separate AdamW step)')
        print('update arm  mass/uniform  d(mass)/d(eta) registered  cos  AdamW delta mass')
        for arm in ARM_NAMES:
            run = runs[arm]
            if run is None:
                print(f'{MISSING:>6} {arm}')
                continue
            for row in run['rows']:
                if row['update'] not in args.routing_at:
                    continue
                print(f"{row['update']:>6} {arm}  {row.get('mass_over_uniform')}  "
                      f"{row.get('directional_registered_all')}  "
                      f"{row.get('cosine_registered_all')}  "
                      f"{row.get('adam_mass_delta_all')}")
    # -------------------------------------------------------------- separate questions
    print('\n## long run (separate question; an extension under a declared schedule, '
          'NOT a continuation of historical e0)')
    for seed in seeds:
        folder = out/f'longrun-seed-{seed}'
        trace = folder/'trace.jsonl'
        if not trace.exists():
            print(f'seed {seed}: {MISSING}')
            continue
        rows = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        points = _points(rows)
        summary = onset_summary(points, LONGRUN_UPDATES)
        mid = points.get(LONGRUN_MIDPOINT)
        end = points.get(LONGRUN_UPDATES)
        midpoint_checkpoint = folder/f'checkpoint-{LONGRUN_MIDPOINT:06d}.pt'
        final_checkpoint = folder/'final.pt'
        print(f'seed {seed}: arm D, onset {_cell(summary["first_qualified_onset"], 1)}, '
              f'{LONGRUN_MIDPOINT} -> {_cell(mid, 1)}/512, '
              f'{LONGRUN_UPDATES} -> {_cell(end, 1)}/512, '
              f'frozen midpoint checkpoint '
              f'{C.sha(midpoint_checkpoint) if midpoint_checkpoint.exists() else MISSING}, '
              f'final {C.sha(final_checkpoint) if final_checkpoint.exists() else MISSING}')
    print('\n## freeze-before-growth transfer of the final arm-A checkpoint '
          f'(no updates; pass = >= {TRANSFER_CORRECT}/512 per cell)')
    for seed in seeds:
        path = out/'transfer'/f'seed-{seed}.json'
        if not path.exists():
            print(f'seed {seed}: {MISSING}')
            continue
        saved = json.loads(path.read_text())
        print(f'seed {seed}: checkpoint {saved["checkpoint_sha256"][:16]}')
        for cell in TRANSFER_CELLS:
            got = saved['cells'].get(cell['name'])
            print(f"  {cell['name']:<14} entities={cell['entities']:>2} "
                  f"facts={cell['fact_lines']:>2} filler={cell['filler_fraction']:<4} "
                  f"{_cell(got['correct'] if got else None, 4)}/{got['n'] if got else '?'} "
                  f"{'pass' if got and got['passes'] else 'fail' if got else MISSING}")
    print('\nScope: these are effects at the tested row counts, streams and budgets. '
          'A/C success would show filler removal sufficient in these cells, not that '
          'competing facts never matter; D successes do not eliminate an optimization '
          'barrier; all-four success does not mean the question was wrong.')


# ==================================================================================== CLI

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['plan', 'train', 'longrun', 'report',
                                        'transfer', 'check-manifest', 'capacity'])
    ap.add_argument('--arm', choices=list(ARM_NAMES))
    ap.add_argument('--seed', type=int, default=REGISTERED_SEEDS[0])
    ap.add_argument('--seeds', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--updates', type=int, default=UPDATES)
    ap.add_argument('--visits', type=int, default=VISITS)
    ap.add_argument('--probe-every', type=int, default=PROBE_EVERY)
    ap.add_argument('--routing-every', type=int, default=LONGRUN_ROUTING_EVERY)
    ap.add_argument('--validation-n', type=int, default=VALIDATION_N)
    ap.add_argument('--routing-visits', type=int, default=VISITS)
    ap.add_argument('--budget-seconds', type=int, default=None)
    ap.add_argument('--chunk-updates', type=int, default=None)
    ap.add_argument('--midpoint', type=int, default=LONGRUN_MIDPOINT)
    ap.add_argument('--audit-updates', type=int, default=3)
    ap.add_argument('--transfer-n', type=int, default=TRANSFER_N)
    ap.add_argument('--checkpoint', default=None)
    ap.add_argument('--trajectories', action='store_true', default=True)
    ap.add_argument('--no-trajectories', dest='trajectories', action='store_false')
    ap.add_argument('--routing-at', default='0,500,1000,2500')
    ap.add_argument('--force-capacity', action='store_true', default=False)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.routing_at = {int(v) for v in str(args.routing_at).split(',') if v != ''}
    R.configure()
    if args.command == 'plan':
        plan(args)
    elif args.command == 'train':
        assert args.arm, '--arm is required for train'
        train(args)
    elif args.command == 'longrun':
        longrun(args)
    elif args.command == 'report':
        report(args)
    elif args.command == 'transfer':
        transfer(args)
    elif args.command == 'capacity':
        print(json.dumps(capacity_report(), indent=2), flush=True)
    else:
        manifest = check_manifest(Path(args.out) if args.out else OUT)
        print(json.dumps(dict(experiment=manifest['experiment'],
                              files=len(manifest['files']), seeds=manifest['seeds'],
                              unchanged=True)), flush=True)


if __name__ == '__main__':
    main()
