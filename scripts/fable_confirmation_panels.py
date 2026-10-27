"""Fresh CONFIRMATION panels + outcome-independent audit (swap/confirmation v2 draft).

The existing ten operator cells and 25 dispatcher/baseline cells are DEVELOPMENT
benchmarks: recipes, curricula, schedules, seeds and checkpoints were chosen partly by
their outcomes on them.  This module builds an untouched replacement suite so that a
later, once-only read on FIXED checkpoints can support a generalisation claim.

  operator suite    10 cells x 512 units, namespace `astra-confirm-operator-v2-20260920`
                    six-person c1 / c2 / c3, the changed-link / changed-endpoint-value /
                    irrelevant-edit pairs, 12-person one-hop / practised two-hop /
                    held-out two-hop, and the three-hop held-out cell.
  dispatcher suite  25 cells x 512 units, namespace `astra-confirm-dispatch-v2-20260920`
                    the exact v3 cell definitions: 16-person lengths 1-8 (practised and
                    held-out terminal), six-person lengths 1-3, and the three five-hop
                    pair cells.

NOTHING HERE RUNS A MODEL.  Generation, auditing and the overlap checks are pure data
work; no checkpoint is loaded and no panel is filtered by any model's correctness.  The
frozen operator's per-stage accuracy on these cells is DELIBERATELY not computed here:
that would be a read of a registered checkpoint on a confirmation panel, which belongs
to the single confirmation evaluation after the freeze.

GENERATOR SEMANTICS ARE THE OLD ONES.  `operator_cell` mirrors
`astra_canonical_operator_panels.generate` and `dispatcher_unit` mirrors
`fable_dispatcher_v3.make_unit`, in both cases taking the namespace (and, for the
operator suite, the seed) as an EXPLICIT argument instead of reading a module global, so
no registered module's globals are mutated and no registered file is edited.
`tests/test_fable_confirmation_panels.py` checks that, given the ORIGINAL namespace and
seed, both reproduce the registered generators exactly.

SIGNATURES (all evaluator-only; never supplied to a model)
  full question   `A.visible_signature(eligible rows, question)` -- sorted eligible
                  visible fact tuples plus the visible question, so row order and filler
                  are stripped -- and `A.tensor_signature` of the same input.
  both twins      every side of every pair, never only side a.
  canonical       every world x all 16 entity IDs x the four canonical operations
  sub-queries     (8, 9, 10, LINK), covering primitive calls and calls no correct
                  execution would make.  Exclusion only.
  world only      the sorted eligible fact set on its own, question dropped.
  presented input where a curriculum shrinks the story (grow-blind), the REDUCED rows
                  actually presented are indexed as well as the full parent world; a
                  full-world hash is not a substitute for the reduced input's hash.

KNOWN LIMITATION, kept explicit: these are exact task-semantic identities over literal
entity IDs.  They are not alpha-equivalence and not a proof against isomorphic or merely
related examples.

    generate      build and freeze both suites (pure data; safe to run now)
    audit         signatures, within/cross-suite duplicates, overlap against every
                  development panel and exclusion file found
    replay        index the TRAINING signatures of a data builder by deterministic
                  replay, with no model computation (see the warning on `--updates`)
    check-index   compare the frozen confirmation signatures against a replayed index

Nothing outside --out is written and --out must not already exist.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fable_dispatcher as V1                                               # noqa: E402
import fable_dispatcher_v3 as V3                                            # noqa: E402
import astra_canonical_operator as A                                        # noqa: E402
import astra_canonical_operator_panels as P                                 # noqa: E402

torch, data = A.torch, A.data
sha = V3.sha
write_new = V3.write_new

QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
CANONICAL_OPS = (8, 9, 10, LINK)

OPERATOR_NAMESPACE = 'astra-confirm-operator-v2-20260920'
DISPATCH_NAMESPACE = 'astra-confirm-dispatch-v2-20260920'
CONFIRM_N = 512
OPERATOR_SEED_BASE = 202609205000
DEFAULT_OUT = WORKTREE / 'artifacts/fable-confirmation-panels-20260920'

# the ten operator cells.  `source` names the registered cell definition reused, `spec`
# the LadderSpec entity count, `cutoff` the registered pass mark at n = 512.
OPERATOR_CELLS = {
    'c1':    dict(source='c1_own_one_hop',            entities=6,  seed_offset=1,  cutoff=487),
    'c2':    dict(source='c2_own_practised_two_hop',  entities=6,  seed_offset=2,  cutoff=487),
    'c3':    dict(source='c3_own_heldout_two_hop',    entities=6,  seed_offset=3,  cutoff=461),
    'c4':    dict(source='c4_changed_link',           entities=6,  seed_offset=4,  cutoff=461),
    'c5':    dict(source='c5_changed_endpoint_value', entities=6,  seed_offset=5,  cutoff=461),
    'c6':    dict(source='c6_irrelevant_edit',        entities=6,  seed_offset=6,  cutoff=461),
    'p12-1': dict(source='c1_own_one_hop',            entities=12, seed_offset=11, cutoff=487),
    'p12-2': dict(source='c2_own_practised_two_hop',  entities=12, seed_offset=12, cutoff=487),
    'p12-3': dict(source='c3_own_heldout_two_hop',    entities=12, seed_offset=13, cutoff=461),
    's3':    dict(source='three-hop-heldout',         entities=6,  seed_offset=14, cutoff=461),
}
# the draft's 487 marks are c1, c2, p12-1 and p12-2; every other answer cell is 461.
DISPATCH_CUTOFF = 464                    # preserves the original 58/64 acceptance fraction
OPERATOR_CELL_ORDER = tuple(OPERATOR_CELLS)

SECONDARY_DIAGNOSTICS = dict(
    per_stage_link_and_gold_endpoint_terminal=487,
    native_three_hop_path_and_answer=461,
    note='note 17 diagnostics, applicable cells only; read at confirmation time')


# --------------------------------------------------------------------------- signatures


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def fact_tuples(rows):
    """The sorted eligible visible fact tuples -- `A.visible_signature`'s first element.

    Computing this once per story and reusing it for many questions is what makes the
    16 x 4 canonical expansion affordable; the digest is bit-for-bit
    `A.visible_signature(rows, question)`.
    """
    return sorted(tuple(row[:4]) for row in rows
                  if len(row) >= 4 and row[0] == WORLD
                  and ENTITY_MIN <= row[1] < ENTITY_MAX and 8 <= row[2] <= LINK)


def signature_from_facts(facts, question):
    return digest([facts, [t for t in question if t]])


def world_signature(facts):
    """The eligible fact set on its own, with no question."""
    return digest([facts])


def canonical_questions():
    return [[QUESTION, e, op, ANSWER]
            for e in range(ENTITY_MIN, ENTITY_MAX) for op in CANONICAL_OPS]


CANONICAL_QUESTIONS = canonical_questions()


def side_signatures(rows, question, canonical=True):
    """Every signature one presented (story, question) side contributes."""
    facts = fact_tuples(rows)
    out = dict(full=signature_from_facts(facts, question),
               tensor=A.tensor_signature(rows, question),
               world=world_signature(facts))
    out['canonical'] = ([signature_from_facts(facts, q) for q in CANONICAL_QUESTIONS]
                        if canonical else [])
    return out


# --------------------------------------------------------------------------- operator suite


def operator_cell(name, n, namespace, seed, spec=None, extra_link=False):
    """`astra_canonical_operator_panels.generate` with namespace AND seed explicit.

    Identical body to the registered generator except that `seed` is an argument rather
    than `202609202000 + CELLS[name]['cell']`, so no module global is mutated.  Its
    rejection/retry rule is the registered one: one `random.Random` per unit, rejections
    consume that same fixed stream and are logged with their reason.  No rejection ever
    consults a model, an attention map, a margin or a confidence.
    """
    data.bootstrap()
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec
    spec = spec or LadderSpec()
    cfg = PS.CELLS[name]
    sides = ['a', 'b'] if cfg['kind'] == 'pair' else ['a']
    records, rejections = [], Counter()
    for i in range(n):
        rng = random.Random(f'{namespace}:{name}:{seed}:{i}')
        if len(sides) == 2:
            ra, rb, where, _facts, rej = PS._make_pair(spec, rng, cfg['edit'])
            rows = {'a': ra, 'b': rb}
        else:
            ra, where, _facts, rej = PS._make_single(spec, rng, cfg['hops'], cfg['relation'])
            rows = {'a': ra}
        rejections.update(rej)
        converted = {}
        for side, lines in rows.items():
            question = lines[where].tokens[:lines[where].tokens.index(ANSWER) + 1]
            if extra_link:
                assert len(question) == 5
                question = question[:3] + [LINK] + question[3:]
            memory = [[] if line.question else list(line.tokens) for line in lines]
            converted[side] = (memory, question, where, lines[where].answer[0])
        if len(sides) == 2:
            xa, xb = converted['a'][0], converted['b'][0]
            assert [len(r) for r in xa] == [len(r) for r in xb]
            assert sum(a != b for la, lb in zip(xa, xb)
                       for a, b in zip(la, lb)) == cfg['token_diffs']
            vals = lambda mem: sorted(r[3] for r in mem
                                      if len(r) >= 4 and r[0] == WORLD and 8 <= r[2] <= 10)
            assert vals(xa) == vals(xb)
        records.append(converted)
    packed = []
    for start in range(0, n, 32):
        block = records[start:start + 32]
        item = {}
        for side in sides:
            vals = [r[side] for r in block]
            x = data.pack([r[0] for r in vals], [r[1] for r in vals],
                          list(range(len(vals))), [r[2] for r in vals])
            targets = [p[-1]['target'] for p in A.truth_paths(x)]
            if not extra_link:
                assert targets == [r[3] for r in vals]
            item[side] = (x, targets)
        if len(sides) == 2:
            same = [a == b for a, b in zip(item['a'][1], item['b'][1])]
            assert all(same) if cfg['invariant'] else not any(same)
        packed.append({'sides': item})
    return dict(name=name, n=n, kind=cfg['kind'], invariant=bool(cfg.get('invariant')),
                chunks=packed, namespace=namespace, seed=seed, entities=spec.entities,
                rejections=dict(rejections))


def three_hop_cell(n, namespace, seed, spec=None):
    """The three-hop held-out cell, as `premonition_token_memory_stress.generate` builds it.

    The extra LINK token changes both depth and question syntax; the target is read off
    the visible lines by the evaluator-only graph walk, never from a label.
    """
    data.bootstrap()
    import premonition_pair_suite as PS
    from premonition.toy_ladder import LadderSpec, FIRST_FREE
    spec = spec or LadderSpec()
    memories, questions, truth, lines_at = [], [], [], []
    rejections = Counter()
    for index in range(n):
        rng = random.Random(f'{namespace}:three-hop-heldout:{seed}:{index}')
        rows, where, facts, rej = PS._make_single(spec, rng, 2, 'heldout')
        rejections.update(rej)
        links, attributes = {}, {}
        for line in rows:
            t = line.tokens
            if line.question or len(t) < 4 or t[0] != WORLD or t[1] < spec.vocab_size:
                continue
            if t[2] == spec.link:
                links[t[1]] = t[3]
            elif FIRST_FREE <= t[2] < FIRST_FREE + spec.relations:
                attributes[(t[1], t[2])] = t[3]
        subject = spec.vocab_size + facts['subject']
        relation = spec.relation(spec.heldout_relation)
        target = attributes[(links[links[subject]], relation)]
        memories.append([[] if r.question else list(r.tokens) for r in rows])
        questions.append([QUESTION, subject, spec.link, spec.link, relation, ANSWER])
        truth.append(target)
        lines_at.append(where)
    chunks = []
    for begin in range(0, n, 32):
        end = min(n, begin + 32)
        x = data.pack(memories[begin:end], questions[begin:end], list(range(end - begin)),
                      lines_at[begin:end])
        assert [p[-1]['target'] for p in A.truth_paths(x)] == truth[begin:end]
        chunks.append({'sides': {'a': (x, truth[begin:end])}})
    return dict(name='three-hop-heldout', n=n, kind='single', invariant=False, chunks=chunks,
                namespace=namespace, seed=seed, entities=spec.entities,
                rejections=dict(rejections),
                changes='extra LINK changes depth and syntax')


def operator_panel_signatures(panel, canonical=True):
    """Every side of a packed operator panel, in stable order."""
    out = []
    for side_group in P.chunks(panel):
        for side, (x, targets) in sorted(side_group.items()):
            paths = A.truth_paths(x)
            assert [p[-1]['target'] for p in paths] == list(targets), 'interpreter disagreement'
            memory = x.memory.tolist()
            for owner, valid, q in zip(x.owner.tolist(), x.eligible.tolist(),
                                       x.questions.tolist()):
                rows = [r for r, ok in zip(memory[owner], valid) if ok]
                out.append(side_signatures(rows, q, canonical))
    return out


def build_operator_suite(folder, n=CONFIRM_N, namespace=OPERATOR_NAMESPACE,
                         seed_base=OPERATOR_SEED_BASE, cells=None, verbose=True):
    V3.configure()
    from premonition.toy_ladder import LadderSpec
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    order = [c for c in OPERATOR_CELL_ORDER if cells is None or c in cells]
    manifest = dict(suite='operator', namespace=namespace, n=n, cells={},
                    cell_order=order, seed_base=seed_base,
                    created_unix=time.time(), cutoffs={},
                    secondary_diagnostics=SECONDARY_DIAGNOSTICS,
                    generator='astra_canonical_operator_panels.generate semantics, '
                              'namespace and seed explicit',
                    model_free=True, filtered_by_model_correctness=False,
                    operator_audit=None,
                    operator_audit_note='deliberately not computed: running a registered '
                                        'checkpoint on a confirmation panel is the single '
                                        'confirmation read, taken after the freeze')
    semantic, tensors = set(), set()
    for key in order:
        cfg = OPERATOR_CELLS[key]
        seed = seed_base + cfg['seed_offset']
        spec = LadderSpec(entities=cfg['entities'])
        if key == 's3':
            panel = three_hop_cell(n, namespace, seed, spec)
        else:
            panel = operator_cell(cfg['source'], n, namespace, seed, spec)
        sigs = operator_panel_signatures(panel, canonical=False)
        full = [s['full'] for s in sigs]
        ts = [s['tensor'] for s in sigs]
        if len(set(full)) != len(full) or len(set(ts)) != len(ts):
            raise RuntimeError(f'{key}: duplicate signature inside the cell')
        if semantic & set(full) or tensors & set(ts):
            raise RuntimeError(f'{key}: overlap with an earlier confirmation cell')
        semantic |= set(full)
        tensors |= set(ts)
        path = folder / f'{key}.pt'
        torch.save(panel, path)
        manifest['cells'][key] = dict(path=str(path.resolve()), sha256=sha(path), n=n,
                                      kind=panel['kind'], invariant=panel['invariant'],
                                      source_cell=cfg['source'], entities=cfg['entities'],
                                      namespace=namespace, seed=seed, cutoff=cfg['cutoff'],
                                      sides=len(sigs) // n, rejections=panel['rejections'])
        manifest['cutoffs'][key] = cfg['cutoff']
        if verbose:
            print(json.dumps(dict(suite='operator', cell=key, n=n, sides=len(sigs),
                                  cutoff=cfg['cutoff'],
                                  rejections=panel['rejections'])), flush=True)
    excluded = folder / 'forbidden-semantics.json'
    write_new(excluded, sorted(semantic))
    manifest.update(exclusion_path=str(excluded.resolve()), exclusion_sha256=sha(excluded),
                    exclusion_count=len(semantic), unique_tensor_inputs=len(tensors),
                    duplicate_or_overlap_failures=0)
    write_new(folder / 'manifest.json', manifest)
    return manifest


# --------------------------------------------------------------------------- dispatcher suite


def dispatcher_unit(cell, index, namespace):
    """`fable_dispatcher_v3.make_unit` with the namespace as an EXPLICIT argument.

    Every primitive (`build_world`, `distinct_askers`, `_terminal`, `make_side`,
    `_edit_world`, `memory_diffs`) is v3's own, imported and unmodified; only the RNG
    key's namespace differs, so the world/question/edit semantics and the fixed
    rejection sequence are byte-for-byte the registered ones.
    """
    cfg = V3.CELLS[cell]
    rng = random.Random(f'{namespace}:{cell}:{index}')
    rejections = {}
    hops = cfg['hops']
    while True:
        world = V3.build_world(rng, cfg['people'])
        askers = V3.distinct_askers(world, hops) if cfg['distinct'] else list(world.ents)
        if not askers:
            V3._bump(rejections, 'no_distinct_chain')
            continue
        asker = rng.choice(askers)
        terminal = V3._terminal(rng, cfg['terminal'])
        side_a = V3.make_side(world, asker, hops, terminal)
        if cfg['kind'] == 'single':
            return dict(cell=cell, index=index, kind='single', a=side_a, rejections=rejections)
        made = V3._edit_world(world, asker, cfg['edit'], rng, rejections, hops, terminal)
        if made is None:
            continue
        edited, detail = made
        if cfg['distinct'] and asker not in V3.distinct_askers(edited, hops):
            V3._bump(rejections, 'edit_broke_the_distinct_chain')
            continue
        side_b = V3.make_side(edited, asker, hops, terminal)
        if side_b['question'] != side_a['question'] or side_b['where'] != side_a['where']:
            V3._bump(rejections, 'the_edit_moved_the_question')
            continue
        expected = 1 if cfg['edit'] == 'link' else 2
        if V3.memory_diffs(side_a['memory'], side_b['memory']) != expected:
            V3._bump(rejections, 'unexpected_token_diffs')
            continue
        changed = side_b['answer'] != side_a['answer']
        if cfg['invariant'] and changed:
            V3._bump(rejections, 'irrelevant_edit_changed_the_answer')
            continue
        if not cfg['invariant'] and not changed:
            V3._bump(rejections, 'edit_left_the_answer_alone')
            continue
        if sorted(world.attr.values()) != sorted(edited.attr.values()):
            V3._bump(rejections, 'value_inventory_not_preserved')
            continue
        return dict(cell=cell, index=index, kind='pair', a=side_a, b=side_b,
                    edit_detail=detail, rejections=rejections)


def unit_sides(unit):
    """(side name, presented eligible rows, question) for every side of a unit."""
    out = []
    for name in ['a'] + (['b'] if unit['kind'] == 'pair' else []):
        side = unit[name]
        rows = [row for index, row in enumerate(side['memory'])
                if row and index < side['where']]
        out.append((name, rows, side['question']))
    return out


def dispatcher_unit_signatures(unit, canonical=True):
    return [side_signatures(rows, question, canonical)
            for _name, rows, question in unit_sides(unit)]


def build_dispatcher_suite(folder, n=CONFIRM_N, namespace=DISPATCH_NAMESPACE, cells=None,
                           verbose=True):
    V3.configure()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    order = [c for c in V3.CELL_ORDER if cells is None or c in cells]
    manifest = dict(suite='dispatcher', namespace=namespace, n=n, cells={}, cell_order=order,
                    created_unix=time.time(), cutoff=DISPATCH_CUTOFF,
                    cutoff_metrics=['answers', 'strict', 'unit_pass'],
                    cutoff_note='464/512 preserves the original 58/64 acceptance fraction; '
                                'answer-only baseline arms have no comparable intermediate '
                                'path metric and must be labelled accordingly',
                    source_sha256=sha(__file__), v3_source_sha256=sha(V3.__file__),
                    v1_source_sha256=sha(V1.__file__),
                    generator='fable_dispatcher_v3.make_unit semantics, namespace explicit',
                    evaluation='greedy (argmax) episodes, final fixed checkpoints only, '
                               'eval cap 16',
                    model_free=True, filtered_by_model_correctness=False,
                    operator_audit=None,
                    operator_audit_note='deliberately not computed: see the operator suite')
    semantic, tensors = set(), set()
    for cell in order:
        cfg = V3.CELLS[cell]
        units, rejections = [], {}
        for index in range(n):
            unit = dispatcher_unit(cell, index, namespace)
            problems = V3.audit_unit(unit)
            if problems:
                raise RuntimeError(f'{cell}:{index}: panel audit failed: {problems}')
            for key, value in unit.pop('rejections').items():
                rejections[key] = rejections.get(key, 0) + value
            for sig in dispatcher_unit_signatures(unit, canonical=False):
                if sig['full'] in semantic:
                    raise RuntimeError(f'{cell}:{index}: duplicate/overlapping semantics')
                if sig['tensor'] in tensors:
                    raise RuntimeError(f'{cell}:{index}: duplicate tensor signature')
                semantic.add(sig['full'])
                tensors.add(sig['tensor'])
            units.append(unit)
        path = folder / f'{cell}.json'
        write_new(path, dict(cell=cell, n=n, namespace=namespace, kind=cfg['kind'],
                             title=cfg['title'], hops=cfg['hops'], people=cfg['people'],
                             terminal=cfg['terminal'], distinct=cfg['distinct'],
                             invariant=cfg['invariant'], edit=cfg['edit'], units=units,
                             rejections=rejections))
        manifest['cells'][cell] = dict(path=str(path.resolve()), sha256=sha(path), n=n,
                                       kind=cfg['kind'], hops=cfg['hops'],
                                       people=cfg['people'], terminal=cfg['terminal'],
                                       title=cfg['title'], cutoff=DISPATCH_CUTOFF,
                                       rejections=rejections)
        if verbose:
            print(json.dumps(dict(suite='dispatcher', cell=cell, n=n,
                                  rejections=rejections)), flush=True)
    excluded = folder / 'forbidden-semantics.json'
    write_new(excluded, sorted(semantic))
    manifest.update(exclusion_path=str(excluded.resolve()), exclusion_sha256=sha(excluded),
                    exclusion_count=len(semantic), unique_tensor_inputs=len(tensors),
                    duplicate_or_overlap_failures=0)
    write_new(folder / 'manifest.json', manifest)
    return manifest


# --------------------------------------------------------------------------- development sources


def development_sources():
    """Every development panel / exclusion file the new suites must be disjoint from.

    Missing entries are recorded as `missing`, never silently skipped: an unchecked
    source means disjointness against it is UNVERIFIED, not guaranteed.
    """
    v3 = WORKTREE / 'artifacts/fable-dispatcher-v3-20260920/panels'
    pilot = WORKTREE / 'artifacts/fable-dispatcher-pilot-20260920/panels'
    screen = (BASE / 'artifacts/astra-canonical-operator-screen-20260920'
              / 'astra_canonical_operator_panels')
    stress = BASE / 'artifacts/codex-token-memory-20260920/stress/manifest.json'
    found = [dict(name='fable-dispatcher-v3-panels', kind='dispatcher-json', path=str(v3)),
             dict(name='fable-dispatcher-pilot-panels', kind='dispatcher-json',
                  path=str(pilot)),
             dict(name='astra-canonical-operator-screen-panels', kind='packed-panel-dir',
                  path=str(screen)),
             dict(name='codex-token-memory-stress', kind='packed-panel-manifest',
                  path=str(stress))]
    for row in found:
        row['exists'] = Path(row['path']).exists()
    plan = BASE / 'artifacts/codex-token-memory-20260920/plan.json'
    if plan.exists():
        rows = json.loads(plan.read_text())['fresh_panels']
        found.append(dict(name='codex-token-memory-fresh-panels', kind='packed-panel-paths',
                          path=str(plan), exists=True,
                          paths=[row['path'] for row in rows.values()]))
    else:
        found.append(dict(name='codex-token-memory-fresh-panels', kind='packed-panel-paths',
                          path=str(plan), exists=False, paths=[]))
    pairsuite = BASE / 'artifacts/claude-pairsuite-20260919/manifest.json'
    if pairsuite.exists():
        rows = json.loads(pairsuite.read_text())['cells']
        found.append(dict(name='claude-pairsuite-original-panels', kind='packed-panel-paths',
                          path=str(pairsuite), exists=True,
                          paths=[str(BASE / row['file']) for row in rows.values()]))
    else:
        found.append(dict(name='claude-pairsuite-original-panels', kind='packed-panel-paths',
                          path=str(pairsuite), exists=False, paths=[]))
    for name, path in (('fable-dispatcher-v3-exclusion', v3 / 'forbidden-semantics.json'),
                       ('fable-dispatcher-pilot-exclusion',
                        pilot / 'forbidden-semantics.json'),
                       ('astra-operator-screen-exclusion',
                        screen / 'forbidden-semantics.json')):
        found.append(dict(name=name, kind='exclusion-json', path=str(path),
                          exists=path.exists()))
    return found


def source_signatures(row):
    """(full-question signatures, tensor signatures) of one development source."""
    path = Path(row['path'])
    if row['kind'] == 'exclusion-json':
        return set(json.loads(path.read_text())), set()
    if row['kind'] == 'dispatcher-json':
        semantic, tensors = set(), set()
        manifest = json.loads((path / 'manifest.json').read_text())
        for cell in manifest['cells']:
            panel = json.loads((path / f'{cell}.json').read_text())
            for unit in panel['units']:
                for sig in dispatcher_unit_signatures(unit, canonical=False):
                    semantic.add(sig['full'])
                    tensors.add(sig['tensor'])
        return semantic, tensors
    semantic, tensors = set(), set()
    if row['kind'] == 'packed-panel-dir':
        paths = sorted(path.glob('*.pt'))
    elif row['kind'] == 'packed-panel-paths':
        paths = [Path(item) for item in row['paths']]
    else:
        manifest = json.loads(path.read_text())
        paths = [Path(item['path']) for item in manifest['panels'].values()]
    for item in paths:
        panel = torch.load(item, map_location='cpu', weights_only=False)
        for sig in operator_panel_signatures(panel, canonical=False):
            semantic.add(sig['full'])
            tensors.add(sig['tensor'])
    return semantic, tensors


# --------------------------------------------------------------------------- audit


def collect_signatures(out, canonical=True, verbose=True):
    """Every signature of both frozen suites, grouped by kind."""
    out = Path(out)
    full, tensors, world, canon = set(), set(), set(), set()
    per_cell = {}
    dispatcher = json.loads((out / 'dispatcher/manifest.json').read_text())
    for cell in dispatcher['cell_order']:
        panel = json.loads((out / f'dispatcher/{cell}.json').read_text())
        sigs = [s for unit in panel['units'] for s in dispatcher_unit_signatures(unit, canonical)]
        per_cell[f'dispatcher/{cell}'] = _absorb(sigs, full, tensors, world, canon)
        if verbose:
            print(json.dumps(dict(signatures=f'dispatcher/{cell}',
                                  **per_cell[f'dispatcher/{cell}'])), flush=True)
    operator = json.loads((out / 'operator/manifest.json').read_text())
    for cell in operator['cell_order']:
        panel = torch.load(out / f'operator/{cell}.pt', map_location='cpu', weights_only=False)
        sigs = operator_panel_signatures(panel, canonical)
        per_cell[f'operator/{cell}'] = _absorb(sigs, full, tensors, world, canon)
        if verbose:
            print(json.dumps(dict(signatures=f'operator/{cell}',
                                  **per_cell[f'operator/{cell}'])), flush=True)
    return dict(per_cell=per_cell, full=full, tensors=tensors, world=world, canonical=canon)


def _absorb(sigs, full, tensors, world, canon):
    before = (len(full), len(tensors))
    for sig in sigs:
        full.add(sig['full'])
        tensors.add(sig['tensor'])
        world.add(sig['world'])
        canon.update(sig['canonical'])
    return dict(sides=len(sigs), new_full=len(full) - before[0],
                new_tensor=len(tensors) - before[1],
                duplicate_full=len(sigs) - (len(full) - before[0]))


def audit(args):
    V3.configure()
    out = Path(args.out)
    folder = out / 'audit'
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    collected = collect_signatures(out, canonical=not args.no_canonical, verbose=True)
    full, tensors = collected['full'], collected['tensors']
    canon, world = collected['canonical'], collected['world']
    sides = sum(row['sides'] for row in collected['per_cell'].values())
    duplicates = sum(row['duplicate_full'] for row in collected['per_cell'].values())
    report = dict(created_unix=time.time(), out=str(out.resolve()),
                  source_sha256=sha(__file__),
                  sides=sides, unique_full_question_signatures=len(full),
                  unique_tensor_signatures=len(tensors),
                  unique_world_only_signatures=len(world),
                  canonical_subquery_signatures=len(canon),
                  canonical_expansion='16 entity IDs x (8, 9, 10, LINK) per presented world',
                  canonical_included=not args.no_canonical,
                  within_suite_duplicate_full_signatures=duplicates,
                  per_cell=collected['per_cell'],
                  reduced_input_note='these panels present the full story, so the presented '
                                     'input and the parent world coincide; the reduced/'
                                     'presented signatures that matter are the grow-blind '
                                     'training ones, indexed by `replay`',
                  limitation='exact task-semantic identity over literal entity IDs; not '
                             'alpha-equivalence, not a proof against isomorphic examples',
                  sources=[])
    combined = full | canon
    failures = []
    if duplicates:
        failures.append(f'{duplicates} duplicate full-question signatures inside the suites')
    for row in development_sources():
        entry = dict(row)
        if not row['exists']:
            entry.update(checked=False, reason='path not found',
                         disjointness='UNVERIFIED')
            failures.append(f'unchecked development source: {row["name"]}')
        else:
            sem, ts = source_signatures(row)
            overlap_full = len(combined & sem)
            overlap_tensor = len(tensors & ts)
            entry.update(checked=True, signatures=len(sem), tensor_signatures=len(ts),
                         overlap_full_or_canonical=overlap_full,
                         overlap_tensor=overlap_tensor,
                         disjointness='clean' if not (overlap_full or overlap_tensor)
                         else 'OVERLAP')
            if overlap_full or overlap_tensor:
                failures.append(f'overlap against {row["name"]}: '
                                f'{overlap_full} semantic, {overlap_tensor} tensor')
        report['sources'].append(entry)
    exclusion = folder / 'forbidden-semantics.json'
    write_new(exclusion, sorted(full))
    canonical_path = folder / 'canonical-subquery-semantics.txt'
    with canonical_path.open('x') as handle:
        for value in sorted(canon):
            handle.write(value + '\n')
    tensor_path = folder / 'tensor-signatures.txt'
    with tensor_path.open('x') as handle:
        for value in sorted(tensors):
            handle.write(value + '\n')
    report.update(
        exclusion_path=str(exclusion.resolve()), exclusion_sha256=sha(exclusion),
        canonical_path=str(canonical_path.resolve()),
        canonical_sha256=sha(canonical_path),
        tensor_path=str(tensor_path.resolve()), tensor_sha256=sha(tensor_path),
        exclusion_union_count=len(combined),
        exclusion_union_note='future training must freeze the UNION of '
                             'forbidden-semantics.json and canonical-subquery-semantics.txt '
                             'before its first update and fail on collision; do not skip a '
                             'colliding training record, which would change the frozen RNG '
                             'stream',
        audit_failures=failures, all_clear=not failures,
        seconds=round(time.monotonic() - started, 1))
    write_new(folder / 'audit.json', report)
    print(json.dumps(dict(sides=sides, unique_full=len(full), canonical=len(canon),
                          union=len(combined), all_clear=report['all_clear'],
                          failures=failures,
                          audit_sha256=sha(folder / 'audit.json'),
                          seconds=report['seconds'])), flush=True)
    return report


# --------------------------------------------------------------------------- training replay


def _eligible_rows(rows, where):
    """`premonition_memnn.pack`'s own rule: non-empty rows strictly before `where`."""
    return [row for index, row in enumerate(rows) if any(row) and index < where]


def _packed_records(inputs):
    """(presented eligible rows, question) for every question of a packed batch."""
    memory = inputs.memory.tolist()
    out = []
    for owner, eligible, q in zip(inputs.owner.tolist(), inputs.eligible.tolist(),
                                  inputs.questions.tolist()):
        out.append(([row for row, ok in zip(memory[owner], eligible) if ok and any(row)],
                    [t for t in q if t]))
    return out


BUILDERS = ('v3-dispatcher', 'canonical-base', 'grow-blind')


def replay_records(builder, seed, updates, visits=16, verbose=True):
    """Yield every TRAINING record of a deterministic data builder, with no model work.

    Each record is (presented eligible rows, parent-world rows, question).  For builders
    that always show the whole story the two row lists coincide; for `grow-blind`, whose
    curriculum shrinks the story, `presented` is the REDUCED input the model actually saw
    and `parent` is the full unreduced world it was carved from.  A full-world hash is not
    a substitute for the reduced input's hash, so both are indexed.

      v3-dispatcher   `fable_dispatcher_v3.training_visits`, stream
                      `fable-dispatcher-v3-train:<seed>`
      canonical-base  `astra_canonical_operator.training_batch`, stream
                      `random.Random(1101)` -- the ORIGINAL (hinted) operator's data
      grow-blind      the registered `fable_operator_startup` grow-blind loop, streams
                      `random.Random(1101)` and `fable-startup-grow-blind:<seed>`, with
                      the frozen hyper-parameters read from its launch manifest

    NO MODEL COMPUTATION: no forward, no backward, no optimizer, no checkpoint is loaded.
    """
    if builder == 'v3-dispatcher':
        rng = random.Random(f'{V3.TRAIN_NAMESPACE}:{seed}')
        for update in range(updates):
            inputs, _questions, _owners, _answers, _meta = V3.training_visits(
                rng, visits, V3.TRAIN_PEOPLE, V3.TRAIN_HOPS, frozenset())
            for rows, q in _packed_records(inputs):
                yield rows, rows, q
            _progress(verbose, builder, update)
        return
    data.bootstrap()
    torch.set_num_threads(1)
    if builder == 'canonical-base':
        rng = random.Random(1101)
        for update in range(updates):
            batch = A.training_batch(rng, visits, frozenset())
            for inputs in (batch.canonical, batch.monolithic):
                for rows, q in _packed_records(inputs):
                    yield rows, rows, q
            _progress(verbose, builder, update)
        return
    if builder != 'grow-blind':
        raise ValueError(builder)
    yield from _replay_grow_blind(seed, updates, visits, verbose)


def _progress(verbose, builder, update, every=50):
    if verbose and (update + 1) % every == 0:
        print(json.dumps(dict(builder=builder, update=update + 1)), flush=True)


def _replay_grow_blind(seed, updates, visits, verbose=True):
    """The grow-blind record loop, replayed exactly, keeping the FULL parent world.

    `fable_operator_startup.training_batch_blind` packs only the REDUCED story, so a
    replay that just called it could never index the parent world the spec asks for.
    This walks the identical loop, drawing from the identical streams in the identical
    order and calling that module's OWN helpers (`grow_fraction`, `_blind_keep`,
    `_visible_facts`, `_one_hop_record`, `_two_hop_record`), so the records it yields are
    the records that run produced.  `tests/test_fable_confirmation_panels.py` checks that
    against `training_batch_blind` itself.
    """
    import fable_operator_startup as S
    from premonition.toy_ladder import LadderSpec, visit
    params = S.registered_params('grow-blind')
    S.configure_variant('grow-blind', seed=seed, **params)
    spec = LadderSpec()
    rng, vrng = random.Random(1101), S.STATE['vrng']
    for step in range(updates):
        S.STATE['step'] = step
        fraction = S.grow_fraction(step, params['grow_g1'], params['grow_g2'])
        for _v in range(visits):
            rows, world, _plan = visit(spec, rng, training=True)
            full = [[] if row.question else list(row.tokens) for row in rows]
            asks = [(j, row.tokens[:row.tokens.index(ANSWER) + 1])
                    for j, row in enumerate(rows) if row.question]
            keep = S._blind_keep(vrng, full, params['blind_lines'], fraction)
            index = {old: new for new, old in enumerate(keep)}
            presented = [full[old] for old in keep]
            attr, links = S._visible_facts(full, keep)
            attr = {k: (val, index[line]) for k, (val, line) in attr.items()}
            links = {k: (val, index[line]) for k, (val, line) in links.items()}
            for j, q in asks:
                where = sum(1 for old in keep if old < j)
                seen = _eligible_rows(presented, where)
                parent = _eligible_rows(full, j)
                if len(q) == 4:
                    entity, relation, _answer, _replaced = S._one_hop_record(
                        vrng, spec, world, attr, params['balance'], (q[1], q[2]))
                    yield seen, parent, [QUESTION, entity, relation, ANSWER]
                    continue
                pick, _replaced = S._two_hop_record(vrng, attr, links, q[1], q[3])
                if pick is None:
                    entity, relation, _answer, _r = S._one_hop_record(
                        vrng, spec, world, attr, params['balance'], None)
                    query = [QUESTION, entity, relation, ANSWER]
                    yield seen, parent, query            # the one-hop canonical record
                    yield seen, parent, list(query)      # and its monolithic stand-in
                    continue
                asker, relation = pick
                target, _link_line = links[asker]
                yield seen, parent, [QUESTION, asker, LINK, ANSWER]
                yield seen, parent, [QUESTION, target, relation, ANSWER]
                yield seen, parent, [QUESTION, asker, LINK, relation, ANSWER]
        rng.randrange(1 << 30)
        _progress(verbose, 'grow-blind', step)


def replay_stream(builder, seed, updates, visits=16, verbose=True):
    """Index one data builder's training signatures.  Returns (detail, presented, parent,
    tensor) where `presented` are the signatures of the inputs actually shown.

    WARNING: a full 6,000-update replay is a long single-process job.  Run it only when
    the Mac is idle; a few hundred updates verifies the mechanism, and a partial index
    certifies only the updates it replayed.
    """
    presented, parent, tensors = set(), set(), set()
    counts = Counter()
    detail = dict(builder=builder, seed=seed, updates=updates, visits=visits,
                  model_computation=False)
    if builder == 'v3-dispatcher':
        detail.update(namespace=V3.TRAIN_NAMESPACE, people=V3.TRAIN_PEOPLE,
                      hops=list(V3.TRAIN_HOPS), stories='full (no curriculum)')
    elif builder == 'canonical-base':
        detail.update(world_stream='random.Random(1101)', variant='base eight-record',
                      stories='full (no curriculum)')
    else:
        import fable_operator_startup as S
        detail.update(world_stream='random.Random(1101)',
                      extra_stream=f'fable-startup-grow-blind:{seed}',
                      registered_params=S.registered_params('grow-blind'),
                      variant='grow-blind',
                      stories='REDUCED by the grow curriculum; both the presented and the '
                              'parent world are indexed')
    for seen, world_rows, question in replay_records(builder, seed, updates, visits, verbose):
        presented.add(signature_from_facts(fact_tuples(seen), question))
        parent.add(signature_from_facts(fact_tuples(world_rows), question))
        tensors.add(A.tensor_signature(seen, question))
        counts['records'] += 1
        if seen is not world_rows and len(seen) != len(world_rows):
            counts['reduced_records'] += 1
    detail.update(records=counts['records'], reduced_records=counts['reduced_records'],
                  unique_presented=len(presented), unique_parent=len(parent),
                  unique_tensor=len(tensors))
    return detail, presented, parent, tensors


def replay(args):
    path = Path(args.out)
    if path.exists():
        raise SystemExit(f'refusing to overwrite {path}')
    started = time.monotonic()
    detail, presented, parent, tensors = replay_stream(args.builder, args.seed, args.updates,
                                                       args.visits)
    detail.update(seconds=round(time.monotonic() - started, 1),
                  source_sha256=sha(__file__),
                  partial=bool(args.updates < args.full_updates),
                  full_updates=args.full_updates,
                  provenance='deterministic replay of the registered data builder; if the '
                             'exact replay cannot be reconstructed, disjointness is NOT '
                             'certified and a new RNG namespace alone is not an '
                             'exact-overlap audit')
    payload = dict(detail, signatures=sorted(presented | parent),
                   presented_signatures=len(presented), parent_signatures=len(parent),
                   tensor_signatures=sorted(tensors))
    write_new(path, payload)
    print(json.dumps(dict(detail, index=str(path.resolve()), index_sha256=sha(path))),
          flush=True)
    return detail


def check_index(args):
    """Compare the frozen confirmation signatures against a replayed training index."""
    out = Path(args.out)
    audit_path = out / 'audit/audit.json'
    report = json.loads(audit_path.read_text())
    training = set()
    indexes = []
    for item in args.index:
        payload = json.loads(Path(item).read_text())
        training |= set(payload['signatures'])
        indexes.append(dict(path=str(Path(item).resolve()), sha256=sha(item),
                            builder=payload['builder'], seed=payload['seed'],
                            updates=payload['updates'], partial=payload.get('partial'),
                            signatures=len(payload['signatures'])))
    panel = set(json.loads(Path(report['exclusion_path']).read_text()))
    if report.get('canonical_included'):
        panel |= set(Path(report['canonical_path']).read_text().split())
    overlap = sorted(panel & training)
    result = dict(created_unix=time.time(), indexes=indexes, panel_signatures=len(panel),
                  training_signatures=len(training), overlap=len(overlap),
                  overlap_examples=overlap[:16], clean=not overlap,
                  partial_indexes=[i['path'] for i in indexes if i.get('partial')],
                  note='a PARTIAL index certifies only the updates it replayed; the '
                       'remainder is unverified, not "probably guaranteed by the seed"')
    write_new(out / 'audit' / args.name, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'overlap_examples'}), flush=True)
    return result


# --------------------------------------------------------------------------- CLI


def generate(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifests = {}
    if args.suite in ('operator', 'both'):
        manifests['operator'] = build_operator_suite(out / 'operator', args.n)
    if args.suite in ('dispatcher', 'both'):
        manifests['dispatcher'] = build_dispatcher_suite(out / 'dispatcher', args.n)
    top = dict(created_unix=time.time(), seconds=round(time.monotonic() - started, 1),
               n=args.n, suites=sorted(manifests),
               operator_namespace=OPERATOR_NAMESPACE, dispatch_namespace=DISPATCH_NAMESPACE,
               source_sha256=sha(__file__), v3_source_sha256=sha(V3.__file__),
               astra_panels_source_sha256=sha(P.__file__),
               model_free=True, scored_by_any_checkpoint=False,
               filtered_by_model_correctness=False,
               operator_cutoffs={k: v['cutoff'] for k, v in OPERATOR_CELLS.items()},
               dispatcher_cutoff=DISPATCH_CUTOFF,
               secondary_diagnostics=SECONDARY_DIAGNOSTICS,
               files={})
    for name in sorted(manifests):
        folder = out / name
        for path in sorted(folder.iterdir()):
            top['files'][f'{name}/{path.name}'] = sha(path)
    write_new(out / 'manifest.json', top)
    print(json.dumps(dict(out=str(out.resolve()), suites=sorted(manifests), n=args.n,
                          files=len(top['files']),
                          manifest_sha256=sha(out / 'manifest.json'),
                          seconds=top['seconds'])), flush=True)
    return top


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('generate', help='build and freeze both confirmation suites')
    p.add_argument('--out', default=str(DEFAULT_OUT))
    p.add_argument('--n', type=int, default=CONFIRM_N)
    p.add_argument('--suite', choices=('operator', 'dispatcher', 'both'), default='both')

    p = sub.add_parser('audit', help='signatures and the outcome-independent overlap audit')
    p.add_argument('--out', default=str(DEFAULT_OUT))
    p.add_argument('--no-canonical', action='store_true',
                   help='skip the 16 x 4 canonical sub-query expansion (audit is then '
                        'weaker and says so)')

    p = sub.add_parser('replay', help='index a training stream by deterministic replay')
    p.add_argument('--builder', required=True,
                   choices=BUILDERS)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--updates', type=int, required=True)
    p.add_argument('--visits', type=int, default=16)
    p.add_argument('--full-updates', type=int, default=6000,
                   help='the run\'s real update count, so a partial index is labelled')
    p.add_argument('--out', required=True)

    p = sub.add_parser('check-index', help='confirmation signatures vs a replayed index')
    p.add_argument('--out', default=str(DEFAULT_OUT))
    p.add_argument('--index', nargs='+', required=True)
    p.add_argument('--name', default='training-overlap.json')

    args = parser.parse_args(argv)
    if args.command == 'generate':
        generate(args)
    elif args.command == 'audit':
        audit(args)
    elif args.command == 'replay':
        replay(args)
    else:
        check_index(args)


if __name__ == '__main__':
    main()
