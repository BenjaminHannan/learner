"""Three one-change variants of the canonical-operator screen (Fable, 2026-09-20 EDT). Additive only.

Same runner (``astra_canonical_operator_run``), same model/init/AdamW/clipping, same
``random.Random(1101)`` world stream consumed identically, same v3r lr-decay schedule,
6,000 updates, 1,500 s training cap, same ten panels/cutoffs and final-checkpoint-only
scoring of R and M. One variant is selected per process with ``--variant``:

``balance``  ONE change vs v3r: the two one-hop canonical records per visit are rebuilt
             as fresh one-hop questions whose entity is uniform over the world's six
             people and whose relation is drawn (r8, r9, r10) = (1/6, 1/6, 2/3), so that
             in expectation every attribute relation receives 4/3 canonical records per
             visit instead of relation 10 receiving ~2.5x fewer.  Answer and supporting
             line are read off the visible fact row; the record keeps the causal
             eligibility (``where``) of the one-hop question it replaces.  Losses,
             weights and record counts are unchanged.  Relation 10 is still never the
             terminal of a two-hop-derived record.

``e0``       ONE change vs v3r: the 0.5 x supporting-line attention term is removed from
             every record (canonical and monolithic); only the answer cross-entropy
             remains.  Gold intermediate entities still build the LINK/terminal records.

``marg``     No intermediate labels and no evidence loss on the two-hop path.  Each
             practised two-hop question (asker x, terminal relation r) contributes
             -log P(y) with P(y) = sum_e p1[e] * P(y | S, e, r), where p1 is the softmax
             of the canonical LINK call [4, x, 11, 5] restricted to the sixteen entity
             tokens 52..67 WITHOUT renormalisation (mass on non-entity tokens is simply
             lost, and therefore penalised), and P(y | S, e, r) is the softmax of the
             canonical terminal call [4, e, r, 5] on the same story.  Gradients flow into
             both calls.  ``row.gold`` is never read anywhere in this variant.
             Per-visit record accounting: 2 one-hop (answer CE) + 2 marginalised two-hop
             (each costing 1 + 16 canonical forwards) + 2 monolithic (answer CE ONLY in
             this variant -- a documented deviation from v3r's evidence-bearing
             monolithic loss, required by "no evidence loss anywhere on this variant's
             two-hop path").  The three groups are weighted as equal records, i.e. the
             plain mean over the six per-visit losses.  FLOPs are counted per forward
             with the module's own counter, so the sixteen-way expansion is charged in
             full.

Any EXTRA randomness a variant needs is drawn from a separate
``random.Random(f"fable-variant-{variant}:{seed}")``; the ``random.Random(1101)`` world
stream is consumed exactly as in v3r (only ``toy_ladder.visit`` plus the trailing
``randrange`` per batch), so worlds, memories and the generator's own questions match
v3r batch for batch.

Location note: this file lives in the ``card-experiment-handoff-7c5b27`` worktree
because the harness refuses writes to the base checkout.  ``BASE``/scripts and ``BASE``
are prepended to ``sys.path`` below so every registered module, the frozen
``premonition`` package, ``ROOT``, the panels and the artifacts folder are the BASE
repository's, exactly as for ``scripts/fable_canonical_v3r.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
if Path(__file__).resolve().parent != (BASE/'scripts'):
    # Registered modules, ROOT, artifacts and the frozen premonition package must all
    # come from BASE even when this wrapper is executed from a worktree copy.
    for entry in (str(BASE), str(BASE/'scripts')):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import datetime
from dataclasses import dataclass
import json
import os
import random
import subprocess
import time

import astra_canonical_operator_run as R

A, P, C, torch, ROOT = R.A, R.P, R.C, R.torch, R.ROOT
assert ROOT == BASE, (ROOT, BASE)
E, T, data = A.E, A.T, A.data
F = T.F
V1 = P.OUT
QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ENTITIES = ENTITY_MAX - ENTITY_MIN
VARIANTS = ('balance', 'e0', 'marg')
ATTRIBUTE_RELATIONS = (8, 9, 10)
COUNTED_OPERATIONS = ATTRIBUTE_RELATIONS + (LINK,)
ORIGINAL_BATCH = A.training_batch
ORIGINAL_FLOPS = A.training_flops

# Process-local wiring; never serialized, never part of the registered manifest.
STATE = dict(variant=None, vrng=None, seed=None, marg_visits=0,
             running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))


def out_for(variant):
    assert variant in VARIANTS, variant
    return ROOT/f'artifacts/fable-operator-{variant}-20260920'


def lr_at(step):
    """v3r's schedule verbatim: warmup to 1e-3, flat to 4,000, linear to 1e-4 at 6,000."""
    if step < 4000:
        return 1e-3 * min(1., (step+1)/100)
    return 1e-3 + (1e-4 - 1e-3) * (step - 4000) / 2000


# --------------------------------------------------------------------------- data

def _relation_counts(*question_tensors):
    counts = dict.fromkeys(map(str, COUNTED_OPERATIONS), 0)
    for q in question_tensors:
        for op in q[:, 2].tolist():
            counts[str(op)] = counts.get(str(op), 0) + 1
    return counts


def _augment(batch):
    """Add the per-relation canonical-record census to an otherwise untouched batch."""
    batch.accounting['relations'] = _relation_counts(batch.canonical.questions)
    return batch


def training_batch_e0(rng, visits=16, forbidden=frozenset()):
    """Astra's eight-record batch, untouched. e0 changes only the loss."""
    return _augment(ORIGINAL_BATCH(rng, visits, forbidden))


def _fact_row(memory, entity, relation):
    """Locate the one visible attribute row for (entity, relation). Visible tokens only."""
    found = [(k, row[3]) for k, row in enumerate(memory)
             if len(row) >= 4 and row[0] == WORLD and row[1] == entity and row[2] == relation]
    if len(found) != 1:
        raise RuntimeError(f'expected exactly one visible fact row, found {len(found)}')
    return found[0]


def training_batch_balance(rng, visits=16, forbidden=frozenset()):
    """Astra's training_batch verbatim except the two one-hop canonical records."""
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    vrng = STATE['vrng']
    assert vrng is not None, 'balance needs its own variant RNG; call configure_variant(seed=...)'
    memories = []
    c, m = (dict(q=[], owner=[], where=[], answer=[], evidence=[]) for _ in range(2))
    kinds = dict(one_hop=0, link=0, terminal=0, monolithic=0)
    checked = 0

    def add(dst, q, owner, where, answer, evidence, kind):
        nonlocal checked
        if forbidden and A.visible_signature(memories[owner], q) in forbidden:
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
                # THE ONE CHANGE: a fresh one-hop question over this visit's own visible
                # facts. Entity uniform over the world's people; relation 1/6, 1/6, 2/3.
                entity = spec.vocab_size + world.ents[vrng.randrange(len(world.ents))]
                draw = vrng.randrange(6)
                relation = spec.relation(0 if draw == 0 else 1 if draw == 1 else 2)
                line, answer = _fact_row(memories[v], entity, relation)
                # Same causal eligibility as the one-hop question this record replaces.
                assert line < j and not rows[line].question, 'supporting fact not eligible'
                assert ENTITY_MIN <= entity < ENTITY_MAX and relation in ATTRIBUTE_RELATIONS
                add(c, [QUESTION, entity, relation, ANSWER], v, j, answer, [line]*3, "one_hop")
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
    # Records 3 and 5 of every six are the two-hop terminals; relation 10 is never one.
    terminals = cx.questions[[i for i in range(6*visits) if i % 6 in (3, 5)], 2]
    assert not bool((terminals == 10).any()), 'relation 10 must never be a two-hop terminal'
    return _augment(A.TrainingBatch(cx, cy, mx, my, dict(
        visits=visits, records=checked, kinds=kinds, heldout_compositions=0, three_hop=0,
        twelve_person=0, overlap_checks=checked if forbidden else 0)))


@dataclass
class MargBatch:
    one_hop: data.Inputs
    one_hop_answers: torch.Tensor
    link: data.Inputs
    terminal: data.Inputs               # [two_hop_records * 16, 4], record-major
    two_hop_answers: torch.Tensor       # [two_hop_records]
    monolithic: data.Inputs
    monolithic_answers: torch.Tensor
    accounting: dict


def training_batch_marg(rng, visits=16, forbidden=frozenset()):
    """Same world stream; no gold intermediate entity and no supporting line is read."""
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    limit = STATE['marg_visits'] or visits
    memories = []
    one = dict(q=[], owner=[], where=[])
    link = dict(q=[], owner=[], where=[])
    term = dict(q=[], owner=[], where=[])
    mono = dict(q=[], owner=[], where=[])
    one_answers, two_answers, mono_answers = [], [], []
    kinds = dict(one_hop=0, marginalised_two_hop=0, monolithic=0)
    relations = dict.fromkeys(map(str, COUNTED_OPERATIONS), 0)
    checked = 0

    def check(owner, q):
        nonlocal checked
        if forbidden and A.visible_signature(memories[owner], q) in forbidden:
            raise RuntimeError("training/validation semantic overlap; run invalid")
        checked += 1

    for v in range(visits):
        rows, world, _ = visit(spec, rng, training=True)
        assert len(world.ents) == 6
        memories.append([[] if row.question else list(row.tokens) for row in rows])
        questions = [(j, row) for j, row in enumerate(rows) if row.question]
        assert len(questions) == 4
        for j, row in questions:
            # Only visible question tokens and the final answer are read. row.gold and
            # row.supplied are never touched anywhere in this function.
            q = row.tokens[:row.tokens.index(ANSWER)+1]
            assert row.hops in (1, 2)
            assert not (row.hops == 2 and row.relation == spec.heldout_relation)
            if row.hops == 1:
                assert len(q) == 4
                check(v, q)
                one['q'].append(q); one['owner'].append(v); one['where'].append(j)
                one_answers.append(row.answer[0])
                kinds['one_hop'] += 1
                relations[str(q[2])] += 1
            else:
                assert len(q) == 5 and q[2] == LINK and q[3] in (8, 9)
                check(v, q)
                mono['q'].append(q); mono['owner'].append(v); mono['where'].append(j)
                mono_answers.append(row.answer[0])
                kinds['monolithic'] += 1
                if v >= limit:
                    continue
                lq = [QUESTION, q[1], LINK, ANSWER]
                check(v, lq)
                link['q'].append(lq); link['owner'].append(v); link['where'].append(j)
                relations[str(LINK)] += 1
                for entity in range(ENTITY_MIN, ENTITY_MAX):
                    tq = [QUESTION, entity, q[3], ANSWER]
                    check(v, tq)
                    term['q'].append(tq); term['owner'].append(v); term['where'].append(j)
                relations[str(q[3])] += 1        # the marginalised record, counted ONCE
                two_answers.append(row.answer[0])
                kinds['marginalised_two_hop'] += 1
    rng.randrange(1 << 30)

    def pack(d):
        return data.pack(memories, d['q'], d['owner'], d['where'])

    ox, lx, tx, mx = pack(one), pack(link), pack(term), pack(mono)
    two = 2*min(limit, visits)
    assert ox.questions.shape == (2*visits, 4)
    assert mx.questions.shape == (2*visits, 5)
    assert lx.questions.shape == (two, 4)
    assert tx.questions.shape == (ENTITIES*two, 4)
    assert kinds['one_hop'] == kinds['monolithic'] == 2*visits
    assert kinds['marginalised_two_hop'] == two
    assert not bool((tx.questions[:, 2] == 10).any()), 'relation 10 must never be a two-hop terminal'
    records = kinds['one_hop'] + kinds['marginalised_two_hop'] + kinds['monolithic']
    accounting = dict(visits=visits, records=records, kinds=kinds, relations=relations,
                      heldout_compositions=0, three_hop=0, twelve_person=0,
                      overlap_checks=checked if forbidden else 0,
                      marg_visits=limit, gold_entities_used=0, evidence_lines_used=0,
                      forwards=dict(one_hop=kinds['one_hop'], link=two,
                                    terminal=ENTITIES*two, monolithic=kinds['monolithic']))
    return MargBatch(ox, torch.tensor(one_answers), lx, tx, torch.tensor(two_answers),
                     mx, torch.tensor(mono_answers), accounting)


def training_flops_marg(batch, model):
    """Honest per-forward count; the sixteen-way terminal expansion is charged in full."""
    return sum(T.training_flops(x, model)
               for x in (batch.one_hop, batch.link, batch.terminal, batch.monolithic))


# --------------------------------------------------------------------------- losses

def marginal_probability(model, batch, *, trace=False):
    """P(y) = sum_e p1[e] * P(y | S, e, r). p1 is NOT renormalised over the entities."""
    link_logits = model(batch.link)
    terminal_logits = model(batch.terminal)
    n = link_logits.shape[0]
    assert terminal_logits.shape[0] == n * ENTITIES
    p1 = link_logits.softmax(-1)[:, ENTITY_MIN:ENTITY_MAX]                   # [n, 16]
    pt = terminal_logits.softmax(-1).reshape(n, ENTITIES, -1)                # [n, 16, V]
    index = batch.two_hop_answers[:, None, None].expand(n, ENTITIES, 1)
    conditional = pt.gather(2, index).squeeze(2)                             # [n, 16]
    probability = (p1 * conditional).sum(1)                                  # [n]
    if trace:
        return probability, dict(link_logits=link_logits, terminal_logits=terminal_logits,
                                 p1=p1, conditional=conditional)
    return probability


def marg_losses(model, batch):
    one = F.cross_entropy(model(batch.one_hop), batch.one_hop_answers)
    mono = F.cross_entropy(model(batch.monolithic), batch.monolithic_answers)
    marg = -marginal_probability(model, batch).clamp_min(1e-12).log().mean()
    return one, marg, mono


def marg_weights(batch):
    """Equal weight per record: with the default 16 visits this is exactly (1/3, 1/3, 1/3)."""
    k = batch.accounting['kinds']
    total = k['one_hop'] + k['marginalised_two_hop'] + k['monolithic']
    return (k['one_hop']/total, k['marginalised_two_hop']/total, k['monolithic']/total)


def _answer_ce(model, inputs, targets):
    return F.cross_entropy(model(inputs), targets.answer)


def _finish(model, optimizer):
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
    if not bool(torch.isfinite(norm)):
        raise RuntimeError("nonfinite gradient")
    optimizer.step()


def _step_balance(model, optimizer, batch, step):
    """v3r's step verbatim (answer CE + 0.5 x supporting-line attention, .75/.25)."""
    for group in optimizer.param_groups:
        group['lr'] = lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    for x, y, weight in ((batch.canonical, batch.canonical_targets, .75),
                         (batch.monolithic, batch.monolithic_targets, .25)):
        loss = E.loss_for(model, x, y)[0] * weight
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
    _finish(model, optimizer)


def _step_e0(model, optimizer, batch, step):
    """Identical to _step_balance except that the evidence term carries weight zero."""
    for group in optimizer.param_groups:
        group['lr'] = lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    for x, y, weight in ((batch.canonical, batch.canonical_targets, .75),
                         (batch.monolithic, batch.monolithic_targets, .25)):
        loss = _answer_ce(model, x, y) * weight
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
    _finish(model, optimizer)


def _step_marg(model, optimizer, batch, step):
    for group in optimizer.param_groups:
        group['lr'] = lr_at(step)
    optimizer.zero_grad(set_to_none=True)
    one, marg, mono = marg_losses(model, batch)
    w1, w2, w3 = marg_weights(batch)
    loss = w1*one + w2*marg + w3*mono
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("nonfinite training loss")
    loss.backward()
    _finish(model, optimizer)


# --------------------------------------------------------------------------- logging

@torch.no_grad()
def _probe(model, batch):
    if isinstance(batch, MargBatch):
        one = (model(batch.one_hop).argmax(-1) == batch.one_hop_answers).float().mean()
        mono = (model(batch.monolithic).argmax(-1) == batch.monolithic_answers).float().mean()
        p = marginal_probability(model, batch)
        return dict(one_hop_acc=round(float(one), 4), monolithic_acc=round(float(mono), 4),
                    mean_marginal_probability=round(float(p.mean()), 4))
    c = (model(batch.canonical).argmax(-1) == batch.canonical_targets.answer).float().mean()
    m = (model(batch.monolithic).argmax(-1) == batch.monolithic_targets.answer).float().mean()
    return dict(canonical_acc=round(float(c), 4), monolithic_acc=round(float(m), 4))


def _logged(step_fn):
    def logged_step(model, optimizer, batch, step):
        step_fn(model, optimizer, batch, step)
        for key, value in batch.accounting.get('relations', {}).items():
            STATE['running'][key] = STATE['running'].get(key, 0) + value
        if (step+1) % 500 == 0:
            was = model.training
            model.eval()
            probe = _probe(model, batch)
            model.train(was)
            print(json.dumps(dict(variant=STATE['variant'], train_batch=step+1, **probe,
                                  canonical_records_by_relation=dict(STATE['running']))), flush=True)
    return logged_step


def configure_variant(variant, seed=None, marg_visits=0):
    """Point the unchanged runner at this variant's folder, batch, loss and FLOP counter."""
    assert variant in VARIANTS, variant
    STATE.update(variant=variant, seed=seed, marg_visits=marg_visits,
                 vrng=None if seed is None else random.Random(f'fable-variant-{variant}:{seed}'),
                 running=dict.fromkeys(map(str, COUNTED_OPERATIONS), 0))
    R.OUT = out_for(variant)
    A.training_flops = ORIGINAL_FLOPS
    if variant == 'balance':
        A.training_batch, A.training_step = training_batch_balance, _logged(_step_balance)
    elif variant == 'e0':
        A.training_batch, A.training_step = training_batch_e0, _logged(_step_e0)
    else:
        A.training_batch, A.training_step = training_batch_marg, _logged(_step_marg)
        A.training_flops = training_flops_marg
    return R.OUT


# --------------------------------------------------------------------------- commands

def _register_key(path):
    """Manifest key that ``check_manifest`` can resolve: ROOT-relative, else absolute.

    ``Path(ROOT)/'<absolute>'`` yields the absolute path, so a wrapper living outside
    the base checkout is still hash-verified before every worker and every wave.
    """
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def freeze(variant, updates, training_seconds, marg_visits=0):
    OUT = out_for(variant)
    v1 = json.loads((V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    for extra in (Path(__file__).resolve(), OUT/'PREREGISTRATION.md'):
        files[_register_key(extra)] = C.sha(extra)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    variant=variant, marg_visits=marg_visits,
                    # v3r's 1500/1740/1770 exactly at the default; the same +240/+270
                    # margins follow a raised cap without editing this file.
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
             '--seed', str(seed), '--wave-start', str(start),
             '--marg-visits', str(manifest.get('marg_visits', 0) or 0)],
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


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['freeze', 'wave', 'worker'])
    ap.add_argument('--variant', required=True, choices=list(VARIANTS))
    ap.add_argument('--seeds', default='0,1,2'); ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int); ap.add_argument('--wave-start', type=float)
    ap.add_argument('--updates', type=int, default=6000)
    ap.add_argument('--training-seconds', type=int, default=1500)
    # OFF by default (0 = all 16 visits marginalised). Only `marg`, and only if Ben
    # registers a reduced marginalised fan-out: the first N visits of each update
    # contribute marginalised two-hop records; one-hop and monolithic records still
    # cover all 16 visits, and the record weights stay proportional to the counts.
    ap.add_argument('--marg-visits', type=int, default=0)
    args = ap.parse_args()
    R.configure()
    configure_variant(args.variant, seed=args.seed, marg_visits=args.marg_visits)
    if args.command == 'freeze':
        freeze(args.variant, args.updates, args.training_seconds, args.marg_visits)
    elif args.command == 'wave':
        wave(args.variant, [int(s) for s in args.seeds.split(',')], args.name)
    else:
        R.worker(args.seed, args.wave_start)
