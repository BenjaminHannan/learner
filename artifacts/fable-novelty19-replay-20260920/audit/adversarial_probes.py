#!/usr/bin/env python3
"""Adversarial probes: make each guard FIRE, and try to defeat each lockout."""
import copy
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parent.parent.parent.parent
sys.path.insert(0, str(WORKTREE / 'scripts'))

import fable_dispatcher_v3 as V3                     # noqa: E402
import fable_baseline_transformer as B1              # noqa: E402
import fable_novelty19_data as D                     # noqa: E402

OUT = {}


def probe(name):
    def deco(fn):
        try:
            OUT[name] = fn()
        except Exception as exc:                      # noqa: BLE001
            OUT[name] = dict(raised=f'{type(exc).__name__}: {exc}')
        return fn
    return deco


# --- 1. does propose_string EVER emit a composite r=10 if the counts allowed it? ----
@probe('poisoned_counts_composite_r10_is_generated_then_rejected')
def _():
    counts = [[0] * 6 for _ in range(6)]
    I = D.ALPHABET_INDEX
    counts[I['BOS']][I['LINK']] = 100
    counts[I['LINK']][I['LINK']] = 30
    counts[I['LINK']][I['10']] = 70          # the edge the real table never has
    counts[I['10']][I['EOS']] = 100
    made = {}
    for k in range(4000):
        names, reason = D.propose_string(random.Random(f'poison:{k}'), counts)
        if reason is None:
            made[' '.join(names)] = made.get(' '.join(names), 0) + 1
    composite = {k: v for k, v in made.items() if D.composite_r10(k.split())}
    return dict(syntactically_valid_strings=len(made),
                composite_r10_passed_propose_string=sum(composite.values()),
                examples=sorted(composite)[:5],
                note='propose_string itself does NOT reject composite r10; the guard '
                     'lives one level up in propose_for_world')


@probe('propose_for_world_rejects_poisoned_composite_r10')
def _():
    counts = [[0] * 6 for _ in range(6)]
    I = D.ALPHABET_INDEX
    counts[I['BOS']][I['LINK']] = 100
    counts[I['LINK']][I['LINK']] = 30
    counts[I['LINK']][I['10']] = 70
    counts[I['10']][I['EOS']] = 100
    rng = random.Random('worldfixture')
    world = V3.build_world(rng, 6)
    rows = V3.render(world)
    fake_awake = []
    for a in list(world.ents)[:4]:
        q = [V3.QUESTION, a, 8, V3.ANSWER]
        fake_awake.append(dict(question=q))
    hist = D._new_histograms()
    chosen, fb = D.propose_for_world(9991, 0, rows, counts, arm='G',
                                     questions_per_world=4, awake_items=fake_awake,
                                     histograms=hist)
    leaked = [c for c in chosen if D.composite_r10(c['names'])]
    return dict(accepted=[' '.join(c['names']) for c in chosen],
                composite_r10_accepted=len(leaked),
                rejected_reasons=hist['rejected'],
                fallbacks=len(fb),
                guard_fired=hist['rejected'].get('composite_r10', 0))


# --- 2. does build_buffers' exclusion-collision RuntimeError actually fire? ---------
@probe('buffer_exclusion_collision_aborts')
def _():
    scratch = HERE.parent / 'scratch'
    mem = scratch / 'mem9991'
    if not mem.exists():
        return dict(skipped='no scratch memory')
    manifest, record, table = D.load_memory(mem)
    rows = record['stories'][0]
    q = record['items'][0]['question']
    sig = D.A.visible_signature(rows, q)
    poison = scratch / 'poison-exclusion.json'
    if not poison.exists():
        poison.write_text(json.dumps([sig]))
    target = scratch / 'buf-poison'
    if target.exists():
        return dict(skipped='already run')
    try:
        D.build_buffers(target, 9991, mem, extra_exclusion=[str(poison)], arms=('R',),
                        offline_updates=4)
        return dict(aborted=False, note='NO abort -- the guard did not fire')
    except Exception as exc:                          # noqa: BLE001
        return dict(aborted=True, error=f'{type(exc).__name__}: {str(exc)[:160]}')


# --- 3. does the awake stream abort on a forbidden collision? -----------------------
@probe('awake_training_items_raises_on_forbidden')
def _():
    rng = random.Random('probe-awake')
    stories, items = B1.training_items(rng, visits=1, people=6, hops_choices=(1, 2, 3),
                                       questions_per_world=4, support=True)
    sig = D.A.visible_signature(stories[0], items[0]['question'])
    rng2 = random.Random('probe-awake')
    try:
        B1.training_items(rng2, visits=1, people=6, hops_choices=(1, 2, 3),
                          forbidden=frozenset({sig}), questions_per_world=4, support=True)
        return dict(raised=False, note='DID NOT RAISE -- collision silently accepted')
    except Exception as exc:                          # noqa: BLE001
        return dict(raised=True, error=f'{type(exc).__name__}: {str(exc)[:160]}')


# --- 4. registered_cells: state on exception, and effect on legacy behaviour --------
@probe('registered_cells_state')
def _():
    before = dict(V3.CELLS)
    before_order = list(V3.CELL_ORDER)
    try:
        with D.registered_cells():
            inside = len(V3.CELLS)
            order_inside = list(V3.CELL_ORDER)
            raise ValueError('boom')
    except ValueError:
        pass
    after = dict(V3.CELLS)
    # nested / re-entrant use
    reentrant = None
    try:
        with D.registered_cells():
            with D.registered_cells():
                pass
            reentrant = ('k1-prac' in V3.CELLS, len(V3.CELLS))
    except Exception as exc:                          # noqa: BLE001
        reentrant = f'{type(exc).__name__}: {exc}'
    after2 = dict(V3.CELLS)
    # collision guard
    try:
        with D.registered_cells({'k1-prac': {}}):
            clash = 'NO RAISE'
    except RuntimeError as exc:
        clash = f'RuntimeError: {str(exc)[:80]}'
    after3 = dict(V3.CELLS)
    return dict(cells_before=len(before), cells_inside=inside, cells_after=len(after),
                restored_exactly_after_exception=(after == before),
                cell_order_untouched=(order_inside == before_order == list(V3.CELL_ORDER)),
                reentrant_result=str(reentrant),
                restored_after_reentrant=(after2 == before),
                name_collision_guard=clash,
                restored_after_collision=(after3 == before),
                v3_consumers_that_iterate_CELLS_not_CELL_ORDER='see grep output')


# --- 5. confirmation lockout ------------------------------------------------------
@probe('confirmation_lockout')
def _():
    scratch = HERE.parent / 'scratch'
    res = {}
    # (a) confirm namespace without the flag
    try:
        D.build_dev_panels(scratch / 'lock-a', n=2, namespace=D.NS_CONFIRM,
                           cells={'F-c1-r8': D.DEV_CELLS['F-c1-r8']})
        res['confirm_namespace_without_flag'] = 'ALLOWED'
    except SystemExit as exc:
        res['confirm_namespace_without_flag'] = f'blocked: {exc}'
    # (b) --confirmation with no DEV-PASSED.json
    empty = scratch / 'lock-empty'
    empty.mkdir(exist_ok=True)
    try:
        D.build_dev_panels(scratch / 'lock-b', n=2, namespace=D.NS_CONFIRM,
                           confirmation=True, experiment=str(empty),
                           cells={'F-c1-r8': D.DEV_CELLS['F-c1-r8']})
        res['confirmation_without_flagfile'] = 'ALLOWED'
    except SystemExit as exc:
        res['confirmation_without_flagfile'] = f'blocked: {exc}'
    # (c) an EMPTY, unvalidated DEV-PASSED.json
    (empty / 'DEV-PASSED.json').write_text('')
    try:
        out = D.build_dev_panels(scratch / 'lock-c', n=2, namespace=D.NS_CONFIRM,
                                 confirmation=True, experiment=str(empty), progress=False,
                                 cells={'F-c1-r8': D.DEV_CELLS['F-c1-r8']})
        res['empty_unvalidated_flagfile'] = f'ALLOWED -> {out["cells"]} cell(s) built'
    except SystemExit as exc:
        res['empty_unvalidated_flagfile'] = f'blocked: {exc}'
    # (d) 512-unit panels under the DEV namespace, no flag at all
    try:
        out = D.build_dev_panels(scratch / 'lock-d', n=512, namespace=D.NS_DEV,
                                 progress=False, cells={'F-c1-r8': D.DEV_CELLS['F-c1-r8']})
        res['n512_under_dev_namespace_without_flag'] = (
            f'ALLOWED -> {out["exclusion_count"]} signatures')
    except SystemExit as exc:
        res['n512_under_dev_namespace_without_flag'] = f'blocked: {exc}'
    # (e) does the confirmation build exclude training/replay signatures?
    res['confirmation_exclusion_sources'] = [Path(p).name for p in D.LEGACY_EXCLUSIONS]
    res['confirmation_uses_legacy_only'] = True
    return res


# --- 6. confirmation namespace vs dev namespace: do they collide? ------------------
@probe('dev_vs_confirm_namespace_units_differ')
def _():
    a, _ = D.dev_unit('F-c1-r8', 0, namespace=D.NS_DEV)
    b, _ = D.dev_unit('F-c1-r8', 0, namespace=D.NS_CONFIRM)
    return dict(same_question=(a['a']['question'] == b['a']['question']),
                same_memory=(a['a']['memory'] == b['a']['memory']),
                both_hit_target=(a['a']['answer'] == b['a']['answer'] == 12))


# --- 7. legacy exclusion union completeness ---------------------------------------
@probe('exclusion_union_coverage')
def _():
    union, record = D.build_exclusion_union()
    pilot = WORKTREE / ('artifacts/fable-dispatcher-pilot-20260920/panels/'
                        'forbidden-semantics.json')
    pilot_sigs = set(json.loads(pilot.read_text())) if pilot.exists() else set()
    return dict(union=len(union), sources=[Path(s['path']).parent.name
                                           for s in record['sources']],
                union_sha256=record['union_sha256'],
                pilot_panels_exist=pilot.exists(), pilot_count=len(pilot_sigs),
                pilot_signatures_in_union=len(pilot_sigs & union),
                pilot_signatures_missing_from_union=len(pilot_sigs - union))


# --- 8. what does a scorer actually feed the models from a panel unit? -------------
@probe('panel_unit_fields_reaching_a_model')
def _():
    unit, _ = D.dev_unit('N-c4-p6', 7, namespace=D.NS_DEV)
    import inspect
    src = inspect.getsource(V3.pack_side)
    return dict(unit_top_level_keys=sorted(unit),
                side_keys=sorted(unit['a']),
                target_answer=unit['target_answer'],
                answer=unit['a']['answer'],
                target_equals_answer=(unit['target_answer'] == unit['a']['answer']),
                pack_side_reads=[k for k in ('memory', 'question', 'where', 'answer',
                                             'index', 'target_answer') if f"'{k}'" in src],
                pack_side_source=src)


# --- 9. does the G proposer ever see or depend on anything outcome-related? --------
@probe('proposal_rng_independence')
def _():
    """Same world index + seed -> same candidate strings regardless of world content."""
    counts = json.loads((HERE.parent / 'scratch' / 'mem9991' /
                         'transition-counts.json').read_text())['counts']
    a = [D.propose_string(random.Random(f'{D.NS_PROPOSE}:9991:0:{k}'), counts)[0]
         for k in range(8)]
    b = [D.propose_string(random.Random(f'{D.NS_PROPOSE}:9991:0:{k}'), counts)[0]
         for k in range(8)]
    c = [D.propose_string(random.Random(f'{D.NS_PROPOSE}:9992:0:{k}'), counts)[0]
         for k in range(8)]
    return dict(reproducible=(a == b), seed_changes_stream=(a != c),
                first_eight=[' '.join(x) for x in a])


if __name__ == '__main__':
    print(json.dumps(OUT, indent=2, default=str))
