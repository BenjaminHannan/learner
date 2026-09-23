"""Eval-only "scale until it breaks" probe for the canonical-operator checkpoints.

Descriptive, not a registered admission test. Nothing here trains, edits or
re-saves a checkpoint: the three final.pt files are loaded read-only and their
weight fingerprints are compared before and after every level.

Two axes:
  HOPS         k = 1..10 operations ([LINK]*(k-1) + terminal relation) in worlds
               of 6, 12 and 16 people, with a practised terminal relation (8/9)
               and the held-out one (10).
  DISTRACTION  6 people, k = 2 and 3, filler/gap volume at x1, x2, x4, x8.

Worlds are built by this file (`build_world`) in the same visible token grammar
that `premonition.toy_ladder.visit` emits, because the existing generator cannot
produce 16-person worlds or chains longer than three hops. `interpret` is an
independent ground-truth interpreter (separate link/attribute tables plus entity
type checks) and is audited against `A.truth_paths` on the registered panels and
on every generated question.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path


def _checkout_root():
    """The main checkout, which holds runtime.local.json, the unstaged scripts and artifacts.

    This file may live in a git worktree that does not carry those gitignored /
    untracked paths, so imports and outputs are resolved against the main checkout.
    """
    override = os.environ.get('FABLE_SCALE_PROBE_REPO')
    if override:
        return Path(override).resolve()
    here = str(Path(__file__).resolve().parents[1])
    return Path(here.split('/.claude/worktrees/')[0])


sys.path.insert(0, str(_checkout_root() / 'scripts'))

import astra_canonical_operator as A            # noqa: E402
import astra_canonical_operator_panels as P     # noqa: E402
import premonition_memnn_compare as C           # noqa: E402

torch, data = A.torch, A.data
ROOT = P.ROOT
OUT = ROOT / 'artifacts/fable-scale-probe-20260920'
SCREEN = ROOT / 'artifacts/astra-canonical-operator-screen-20260920'
SEEDS = (0, 1, 2)

# Fixed in advance; never tuned on an outcome.
BREAK_CUTOFF = 461
N_FULL = 512
N_LONG = 512              # n for k >= LONG_K; lowered only if PLAN.md says so before the run
LONG_K = 6
QUESTIONS_PER_WORLD = 4
WORLDS_PER_CHUNK = 32
NAMESPACE = 'fable-scale-probe-v1'

# Visible token grammar (premonition.toy_ladder, LadderSpec defaults).
WORLD, QUESTION, ANSWER, NEWLINE = 3, 4, 5, 7
LINK, ENTITY_MIN, ENTITY_MAX = 11, 52, 68
FIRST_REL, RELATIONS, VALUES, FILLERS = 8, 3, 16, 24
VOCAB_SIZE, N_ENT = 52, 16
BASE_DISTRACTORS, BASE_GAP = 4, 128
HELDOUT_REL = FIRST_REL + 2
PRACTISED_RELS = (FIRST_REL, FIRST_REL + 1)
PEOPLE_LEVELS = (6, 12, 16)
K_LEVELS = tuple(range(1, 11))
RELATION_KINDS = ('practised', 'heldout')
FILLER_MULTS = (1, 2, 4, 8)
DISTRACTION_KS = (2, 3)


def configure():
    data.bootstrap()
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1


# ----------------------------------------------------------------- world builder
def build_world(rng, people, filler_mult):
    """Rows in the exact visible token format `toy_ladder.visit` emits.

    Every person gets one attribute line per relation and exactly one LINK line;
    filler and gap lines carry no entity token, so they are semantically inert.
    """
    if not 2 <= people <= N_ENT:
        raise ValueError('people must be between 2 and 16')
    ents = rng.sample(range(N_ENT), people)
    attr = {(e, r): rng.randrange(VALUES) for e in ents for r in range(RELATIONS)}
    friend = {e: rng.choice([x for x in ents if x != e]) for e in ents}
    block = ([('attr', e, r) for e in ents for r in range(RELATIONS)]
             + [('link', e, -1) for e in ents]
             + [('filler', -1, -1)] * (BASE_DISTRACTORS * filler_mult))
    order = rng.sample(range(len(block)), len(block))
    fill = lambda n: [FIRST_REL + RELATIONS + 1 + VALUES + rng.randrange(FILLERS) for _ in range(n)]
    rows = []
    for index in order:
        kind, e, r = block[index]
        if kind == 'attr':
            rows.append([WORLD, VOCAB_SIZE + e, FIRST_REL + r,
                         FIRST_REL + RELATIONS + 1 + attr[(e, r)]]
                        + fill(rng.randint(0, 2)) + [NEWLINE])
        elif kind == 'link':
            rows.append([WORLD, VOCAB_SIZE + e, LINK, VOCAB_SIZE + friend[e]]
                        + fill(rng.randint(0, 2)) + [NEWLINE])
        else:
            rows.append([WORLD] + fill(rng.randint(3, 6)) + [NEWLINE])
    gap = 0
    while gap < BASE_GAP * filler_mult:
        line = [WORLD] + fill(rng.randint(4, 8)) + [NEWLINE]
        rows.append(line)
        gap += len(line)
    return rows, ents, attr, friend


def interpret(rows, eligible, question):
    """Independent evaluator-only interpreter. No model, no checkpoint, no labels."""
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
    x, stages = q[1], []
    for op in q[2:-1]:
        y = links[x] if op == LINK else attrs[(x, op)]
        stages.append(dict(entity=x, operation=op, target=y))
        x = y
    return stages


def chain_stats(stages):
    people = [s['entity'] for s in stages]
    return dict(chain=people, distinct_people=len(set(people)),
                revisits=len(people) != len(set(people)))


# ----------------------------------------------------------------- level building
def level_id(people, k, relation, mult):
    return f'p{people}-k{k}-{relation}-f{mult}'


def level_n(k):
    return N_LONG if k >= LONG_K else N_FULL


def all_levels():
    levels = {}
    for people in PEOPLE_LEVELS:
        for k in K_LEVELS:
            for relation in RELATION_KINDS:
                lid = level_id(people, k, relation, 1)
                levels[lid] = dict(id=lid, people=people, k=k, relation=relation,
                                   filler_mult=1, axes=['hops'], n=level_n(k))
    for k in DISTRACTION_KS:
        for relation in RELATION_KINDS:
            levels[level_id(6, k, relation, 1)]['axes'].append('distraction')
            for mult in FILLER_MULTS[1:]:
                lid = level_id(6, k, relation, mult)
                levels[lid] = dict(id=lid, people=6, k=k, relation=relation,
                                   filler_mult=mult, axes=['distraction'], n=level_n(k))
    return levels


def build_level(level):
    """Return (chunks, questions). Chunks hold only the four visible tensors."""
    lid, people, k = level['id'], level['people'], level['k']
    mult, n = level['filler_mult'], level['n']
    if n % QUESTIONS_PER_WORLD:
        raise ValueError('n must be a multiple of the questions per world')
    worlds = n // QUESTIONS_PER_WORLD
    chunks, questions = [], []
    for start in range(0, worlds, WORLDS_PER_CHUNK):
        memories, qs, owners, qlines, metas = [], [], [], [], []
        for w in range(start, min(worlds, start + WORLDS_PER_CHUNK)):
            rng = random.Random(f'{NAMESPACE}:{lid}:{w}')
            rows, ents, attr, friend = build_world(rng, people, mult)
            memory = [list(r) for r in rows] + [[] for _ in range(QUESTIONS_PER_WORLD)]
            owner = len(memories)
            memories.append(memory)
            for j, subject in enumerate(rng.sample(ents, QUESTIONS_PER_WORLD)):
                terminal = (HELDOUT_REL if level['relation'] == 'heldout'
                            else rng.choice(PRACTISED_RELS))
                ops = [LINK] * (k - 1) + [terminal]
                question = [QUESTION, VOCAB_SIZE + subject] + ops + [ANSWER]
                qline = len(rows) + j
                eligible = [i < qline and any(r) for i, r in enumerate(memory)]
                stages = interpret(memory, eligible, question)
                assert len(stages) == k
                meta = dict(index=len(questions), world=w, subject=VOCAB_SIZE + subject,
                            question=question, terminal=terminal, operations=ops,
                            truth_path=[s['target'] for s in stages],
                            target=stages[-1]['target'], memory_rows=len(rows),
                            memory_tokens=sum(len(r) for r in rows),
                            **chain_stats(stages))
                qs.append(question)
                owners.append(owner)
                qlines.append(qline)
                metas.append(meta)
                questions.append(meta)
        x = data.pack(memories, qs, owners, qlines)
        paths = A.truth_paths(x)
        for meta, path in zip(metas, paths):
            if [s['target'] for s in path] != meta['truth_path']:
                raise RuntimeError('builder/truth_paths disagreement')
        chunks.append(dict(inputs=x, meta=metas))
    assert len(questions) == n
    return chunks, questions


def panel_hash(chunks):
    h = hashlib.sha256()
    for chunk in chunks:
        x = chunk['inputs']
        for tensor in (x.memory, x.questions, x.owner, x.eligible):
            h.update(str(tuple(tensor.shape)).encode())
            h.update(tensor.to(torch.long).contiguous().numpy().tobytes())
    return h.hexdigest()


# ----------------------------------------------------------------- audit
def audit_registered(names=('c1', 'c2', 'c3', 's3')):
    """Run registered panels through `interpret` and compare with `A.truth_paths`."""
    manifest = json.loads((SCREEN / 'astra_canonical_operator_panels.json').read_text())
    report = {}
    for name in names:
        row = manifest[name]
        if C.sha(row['path']) != row['sha256']:
            raise RuntimeError(f'registered panel changed: {name}')
        panel = P.load(row['path'])
        checked = mismatches = 0
        for sides in P.chunks(panel):
            for x, _targets in sides.values():
                paths = A.truth_paths(x)
                memory = x.memory.tolist()
                for i, (owner, eligible, question) in enumerate(
                        zip(x.owner.tolist(), x.eligible.tolist(), x.questions.tolist())):
                    mine = interpret(memory[owner], eligible, question)
                    checked += 1
                    if mine != paths[i]:
                        mismatches += 1
        report[name] = dict(path=row['path'], sha256=row['sha256'],
                            questions_checked=checked, mismatches=mismatches)
        if mismatches:
            raise RuntimeError(f'interpreter disagrees with truth_paths on {name}')
    return report


# ----------------------------------------------------------------- scoring
def load_checkpoint(seed):
    path = SCREEN / f'astra_canonical_operator_seed-{seed}/final.pt'
    saved = P.load(path)
    model = A.CanonicalOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    assert model.parameters_count() == 79316
    return model, C.fingerprint(model), C.sha(path)


@torch.no_grad()
def score_level(model, chunks):
    out = []
    for chunk in chunks:
        x = chunk['inputs']
        paths = A.truth_paths(x)
        monolithic = model(x).argmax(-1).tolist()
        recursive = A.execute(model, x)
        oracle = A.oracle_inputs(model, x, paths)
        for i, meta in enumerate(chunk['meta']):
            if [s['target'] for s in paths[i]] != meta['truth_path']:
                raise RuntimeError('truth drift during scoring')
            out.append(dict(index=meta['index'], M=monolithic[i], R=recursive['predictions'][i],
                            emitted=list(recursive['emitted'][i]),
                            oracle=list(oracle['predictions'][i])))
    return out


def first_failure(emitted, truth):
    for j, t in enumerate(truth):
        if j >= len(emitted) or emitted[j] != t:
            return j
    return -1


def summarize(level, questions, records):
    """Pure counting over the per-question records; mirrored by the stdlib re-check."""
    n, k = len(questions), level['k']
    counts = dict(n=n, R=0, M=0, path=0, abort=0, R_correct_path_wrong=0,
                  stage_oracle=[0] * k, first_fail={})
    splits = {'revisits': dict(n=0, R=0, M=0, path=0), 'simple': dict(n=0, R=0, M=0, path=0)}
    by_distinct = {}
    for q, r in zip(questions, records):
        truth = q['truth_path']
        ok_r = int(r['R'] == q['target'])
        ok_m = int(r['M'] == q['target'])
        ok_path = int(r['emitted'] == truth)
        counts['R'] += ok_r
        counts['M'] += ok_m
        counts['path'] += ok_path
        counts['abort'] += int(r['R'] == -1)
        counts['R_correct_path_wrong'] += int(ok_r and not ok_path)
        for j in range(k):
            counts['stage_oracle'][j] += int(r['oracle'][j] == truth[j])
        if not ok_r:
            key = str(first_failure(r['emitted'], truth))
            counts['first_fail'][key] = counts['first_fail'].get(key, 0) + 1
        bucket = splits['revisits' if q['revisits'] else 'simple']
        bucket['n'] += 1
        bucket['R'] += ok_r
        bucket['M'] += ok_m
        bucket['path'] += ok_path
        bucket = by_distinct.setdefault(str(q['distinct_people']), dict(n=0, R=0))
        bucket['n'] += 1
        bucket['R'] += ok_r
    counts['splits'] = splits
    counts['by_distinct_people'] = by_distinct
    product = 1.0
    for c in counts['stage_oracle']:
        product *= c / n
    counts['stage_oracle_rate'] = [c / n for c in counts['stage_oracle']]
    counts['compounding_prediction'] = product * n
    counts['broken'] = counts['R'] < BREAK_CUTOFF
    return counts


# ----------------------------------------------------------------- driver
def run(selected, seeds, verbose=True):
    configure()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'levels').mkdir(exist_ok=True)
    levels = all_levels()
    models = {seed: load_checkpoint(seed) for seed in seeds}
    for lid in selected:
        path = OUT / 'levels' / f'{lid}.json'
        if path.exists():
            if verbose:
                print(json.dumps(dict(level=lid, skipped='exists')), flush=True)
            continue
        level = levels[lid]
        started = time.monotonic()
        chunks, questions = build_level(level)
        payload = dict(level=level, panel_sha256=panel_hash(chunks),
                       build_seconds=time.monotonic() - started, namespace=NAMESPACE,
                       cutoff=BREAK_CUTOFF, questions=questions, seeds={})
        for seed in seeds:
            model, fingerprint, ckpt_sha = models[seed]
            t = time.monotonic()
            records = score_level(model, chunks)
            elapsed = time.monotonic() - t
            if C.fingerprint(model) != fingerprint:
                raise RuntimeError('model weights changed during scoring')
            counts = summarize(level, questions, records)
            payload['seeds'][str(seed)] = dict(seed=seed, checkpoint_sha256=ckpt_sha,
                                               fingerprint=fingerprint, seconds=elapsed,
                                               records=records, counts=counts)
            if verbose:
                print(json.dumps(dict(level=lid, seed=seed, n=counts['n'], R=counts['R'],
                                      M=counts['M'], path=counts['path'],
                                      abort=counts['abort'], seconds=round(elapsed, 1))), flush=True)
        C.write_new(path, payload)
    return True


def collect():
    """Assemble summary.json and SUMMARY.md from the per-level files."""
    levels = all_levels()
    per_level = {}
    for lid in levels:
        path = OUT / 'levels' / f'{lid}.json'
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        qs = payload['questions']
        per_level[lid] = dict(
            level=payload['level'], panel_sha256=payload['panel_sha256'],
            counts={s: v['counts'] for s, v in payload['seeds'].items()},
            fingerprints={s: v['fingerprint'] for s, v in payload['seeds'].items()},
            mean_memory_rows=sum(q['memory_rows'] for q in qs) / len(qs),
            mean_memory_tokens=sum(q['memory_tokens'] for q in qs) / len(qs),
            revisit_fraction=sum(q['revisits'] for q in qs) / len(qs))
    breaking, tested = {}, {}
    for seed in SEEDS:
        s = str(seed)
        breaking[s], tested[s] = {}, {}
        for people in PEOPLE_LEVELS:
            for relation in RELATION_KINDS:
                axis, first, seen = f'hops/people{people}/{relation}', None, []
                for k in K_LEVELS:
                    row = per_level.get(level_id(people, k, relation, 1))
                    if not row or s not in row['counts']:
                        continue
                    seen.append(k)
                    if row['counts'][s]['broken'] and first is None:
                        first = k
                breaking[s][axis], tested[s][axis] = first, seen
        for k in DISTRACTION_KS:
            for relation in RELATION_KINDS:
                axis, first, seen = f'distraction/k{k}/{relation}', None, []
                for mult in FILLER_MULTS:
                    row = per_level.get(level_id(6, k, relation, mult))
                    if not row or s not in row['counts']:
                        continue
                    seen.append(mult)
                    if row['counts'][s]['broken'] and first is None:
                        first = mult
                breaking[s][axis], tested[s][axis] = first, seen
    summary = dict(created_unix=time.time(), cutoff=BREAK_CUTOFF, seeds=list(SEEDS),
                   questions_per_world=QUESTIONS_PER_WORLD, namespace=NAMESPACE,
                   eval_only=True, trained=False, levels=per_level, first_breaking=breaking,
                   axis_tested=tested)
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'SUMMARY.md').write_text(render(summary))
    return summary


def render(summary):
    lines = ['# Scale-until-it-breaks probe - summary', '',
             'Eval-only. Three already-scored checkpoints, loaded read-only; no training and no',
             'checkpoint selection. Breaking point declared in advance: the first level whose',
             f'R count is below {BREAK_CUTOFF}/512. `pred` is the compounding prediction, i.e.',
             'n x the product of the measured per-stage gold-input accuracies, shown for context',
             'only. Cells read R/M/path (pred).', '']
    per_level = summary['levels']

    def table(title, labels, ids, header):
        lines.append(f'## {title}')
        lines.append('')
        lines.append(f'| {header} | n | ' + ' | '.join(
            f'seed {s}' for s in summary['seeds']) + ' |')
        lines.append('| --- | --- | ' + ' | '.join('---' for _ in summary['seeds']) + ' |')
        for label, lid in zip(labels, ids):
            row = per_level.get(lid)
            if not row:
                continue
            cells, n = [], None
            for s in summary['seeds']:
                c = row['counts'].get(str(s))
                if not c:
                    cells.append('-')
                    continue
                n = c['n']
                cells.append(f"{c['R']}/{c['M']}/{c['path']} ({c['compounding_prediction']:.0f})")
            lines.append(f'| {label} | {n} | ' + ' | '.join(cells) + ' |')
        lines.append('')

    for people in PEOPLE_LEVELS:
        for relation in RELATION_KINDS:
            table(f'HOPS - {people} people, {relation} terminal relation',
                  [f'k={k}' for k in K_LEVELS],
                  [level_id(people, k, relation, 1) for k in K_LEVELS], 'level')
    for k in DISTRACTION_KS:
        for relation in RELATION_KINDS:
            table(f'DISTRACTION - 6 people, k={k}, {relation} terminal relation',
                  [f'filler x{m}' for m in FILLER_MULTS],
                  [level_id(6, k, relation, m) for m in FILLER_MULTS], 'level')
    lines.append('## First breaking level (R below cutoff), per seed and axis')
    lines.append('')
    axes = sorted({a for s in summary['first_breaking'].values() for a in s})
    lines.append('| axis | ' + ' | '.join(f'seed {s}' for s in summary['seeds']) + ' |')
    lines.append('| --- | ' + ' | '.join('---' for _ in summary['seeds']) + ' |')
    for axis in axes:
        cells = []
        for s in summary['seeds']:
            value = summary['first_breaking'].get(str(s), {}).get(axis)
            seen = summary.get('axis_tested', {}).get(str(s), {}).get(axis, [])
            unit = 'k=' if axis.startswith('hops') else 'filler x'
            if not seen:
                cells.append('not run')
            elif value is None:
                cells.append(f'never (tested to {unit}{max(seen)})')
            else:
                cells.append(f'{unit}{value}')
        lines.append(f'| {axis} | ' + ' | '.join(cells) + ' |')
    lines.append('')
    lines.append('## Level context (world size)')
    lines.append('')
    lines.append('| level | mean memory rows | mean memory tokens | revisit fraction |')
    lines.append('| --- | --- | --- | --- |')
    for lid, row in per_level.items():
        lines.append(f"| {lid} | {row['mean_memory_rows']:.1f} | {row['mean_memory_tokens']:.1f} | "
                     f"{row['revisit_fraction']:.3f} |")
    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit', 'smoke', 'levels', 'run', 'collect'])
    parser.add_argument('--levels', default='all')
    parser.add_argument('--seeds', default='0,1,2')
    parser.add_argument('--people', type=int, default=6)
    parser.add_argument('--k', type=int, default=2)
    parser.add_argument('--mult', type=int, default=1)
    parser.add_argument('--n', type=int, default=QUESTIONS_PER_WORLD * 8)
    args = parser.parse_args()
    configure()
    if args.command == 'audit':
        print(json.dumps(audit_registered(), indent=2), flush=True)
    elif args.command == 'levels':
        names = list(all_levels())
        print(json.dumps(dict(count=len(names), levels=names)), flush=True)
    elif args.command == 'smoke':
        level = dict(id=f'smoke-p{args.people}-k{args.k}-f{args.mult}', people=args.people,
                     k=args.k, relation='heldout', filler_mult=args.mult, axes=['smoke'], n=args.n)
        t = time.monotonic()
        chunks, questions = build_level(level)
        build_seconds = time.monotonic() - t
        model, fingerprint, _ = load_checkpoint(1)
        t = time.monotonic()
        records = score_level(model, chunks)
        score_seconds = time.monotonic() - t
        assert C.fingerprint(model) == fingerprint
        counts = summarize(level, questions, records)
        print(json.dumps(dict(level=level['id'], n=level['n'], build_seconds=round(build_seconds, 2),
                              score_seconds=round(score_seconds, 2),
                              projected_512_one_seed=round(score_seconds * 512 / level['n'], 1),
                              rows=questions[0]['memory_rows'], tokens=questions[0]['memory_tokens'],
                              R=counts['R'], M=counts['M'], path=counts['path'],
                              hash=panel_hash(chunks)[:16])), flush=True)
    elif args.command == 'run':
        names = list(all_levels()) if args.levels == 'all' else args.levels.split(',')
        run(names, [int(s) for s in args.seeds.split(',')])
    else:
        collect()
