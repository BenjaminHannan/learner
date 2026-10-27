"""Checks for scripts/fable_story_size_stress.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_story_size_stress.py
Run a group: python3.12 -B tests/test_fable_story_size_stress.py --only nesting
Groups: build, pairing, nesting, filler, exclusion, sanity.

Nothing here trains. ``sanity`` loads the arm-A seed-0 checkpoint READ-ONLY and prints the
1x / F24 accuracy as a reproduction of the known ~99%; it deliberately does NOT assert an
accuracy threshold.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
for entry in (str(BASE), str(BASE/'scripts'), str(HERE.parent/'scripts')):
    if entry not in sys.path:
        sys.path.append(entry)

import fable_story_size_stress as G                                   # noqa: E402

A, S, FSF, torch, data = G.A, G.S, G.FSF, G.torch, G.data
WORLD, LINK, QUESTION, ANSWER = G.WORLD, G.LINK, G.QUESTION, G.ANSWER
ENTITY_MIN, ENTITY_MAX = G.ENTITY_MIN, G.ENTITY_MAX
SMALL = 6                      # worlds used by the structural checks
CHECKS = 0


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def subsequence(small, big):
    """True if the row objects of ``small`` appear, in order, among those of ``big``."""
    it = iter(big)
    return all(any(x is y for y in it) for x in small)


# ------------------------------------------------------------------------------ build

def group_build(grid):
    spec = G._spec()
    check('a base world is a FULL 16-person world with 64 fact rows',
          all(len(w['fact_rows']) == 64 for w in grid),
          f'{[len(w["fact_rows"]) for w in grid]}')
    check('the fixed subset contributes exactly 24 fact rows (6 people x 4 rows)',
          all(len(w['subset_rows']) == 24 for w in grid))
    check('every fact row is a visible fact and every subset row names a subset person',
          all(S._is_fact(r) for w in grid for r in w['fact_rows'])
          and all(r[1] in {spec.vocab_size+e for e in w['subset']}
                  for w in grid for r in w['subset_rows']))
    check('the subset is closed under the friend map, so F24 can answer two-hop',
          all(all(ENTITY_MIN <= mid < ENTITY_MAX
                  and mid in {spec.vocab_size+e for e in w['subset']}
                  for _, _, mid, _ in w['two_hop']) for w in grid))
    counts = {r: 0 for r in G.ATTRIBUTE_RELATIONS}
    for w in grid:
        check_ok = len(w['attribute']) == G.ATTR_PER_WORLD
        assert check_ok, w['index']
        for _, rel, _ in w['attribute']:
            counts[rel] += 1
    check('attribute relations are balanced 3/3/2 per world',
          all(abs(counts[r] - SMALL*G.ATTR_PER_WORLD/3) <= SMALL for r in counts), str(counts))
    check('every world draws 4 distinct LINK questions and 4 two-hop questions',
          all(len({e for e, _, _ in w['link']}) == G.LINK_PER_WORLD
              and len(w['two_hop']) == G.TWO_HOP_PER_WORLD for w in grid))
    again = [G.build_world(w) for w in range(SMALL)]
    same_rows = all(a['fact_rows'] == b['fact_rows'] and a['filler'] == b['filler']
                    and a['attribute'] == b['attribute'] and a['link'] == b['link']
                    and a['two_hop'] == b['two_hop'] for a, b in zip(grid, again))
    cell_a = G.world_cell(grid[0], 'F64', 3)
    cell_b = G.world_cell(again[0], 'F64', 3)
    check('a rebuild from the namespace is bit-identical (rows, questions and tensors)',
          same_rows and bool((cell_a['inputs'].memory == cell_b['inputs'].memory).all())
          and bool((cell_a['inputs'].questions == cell_b['inputs'].questions).all())
          and bool((cell_a['answers'] == cell_b['answers']).all()))
    geo = {G.cell_name(c, m): len(G.story_rows(grid[0], c, m))
           for c in G.FACT_CONDITIONS for m in G.FILLER_MULTIPLES}
    check('stories grow monotonically along both axes', all(
        geo[G.cell_name(c, a)] < geo[G.cell_name(c, b)]
        for c in G.FACT_CONDITIONS
        for a, b in zip(G.FILLER_MULTIPLES, G.FILLER_MULTIPLES[1:]))
        and all(geo[G.cell_name('F24', m)] < geo[G.cell_name('F64', m)]
                for m in G.FILLER_MULTIPLES), json.dumps(geo))


# ---------------------------------------------------------------------------- pairing

def group_pairing(grid):
    reference = None
    identical = True
    for condition in G.FACT_CONDITIONS:
        for multiple in G.FILLER_MULTIPLES:
            for w, world in enumerate(grid):
                cell = G.world_cell(world, condition, multiple)
                key = (cell['inputs'].questions.tolist(), cell['answers'].tolist(),
                       cell['two_inputs'].questions.tolist(),
                       cell['two_answers'].tolist(), cell['two_mid'].tolist())
                if reference is None:
                    reference = {}
                identical &= reference.setdefault(w, key) == key
    check('every cell asks the SAME questions with the SAME answers (paired grid)',
          identical, f'{len(G.CELLS)} cells x {len(grid)} worlds')
    check('768-question shape per world: 8 attribute + 4 LINK one-call, 4 two-hop',
          all(G.world_cell(w, 'F64', 0)['inputs'].questions.shape[0]
              == G.ATTR_PER_WORLD + G.LINK_PER_WORLD for w in grid))
    ok = True
    for condition in G.FACT_CONDITIONS:
        for multiple in G.FILLER_MULTIPLES:
            for world in grid:
                cell = G.world_cell(world, condition, multiple)
                for x in (cell['inputs'], cell['two_inputs']):
                    real = x.memory.ne(0).any(-1)[x.owner]
                    ok &= bool((x.eligible == real).all())
    check('every real story row is causally eligible for every question, as in the panels',
          ok)
    derived = True
    for condition in G.FACT_CONDITIONS:
        for world in grid:
            cell = G.world_cell(world, condition, 3)
            paths = A.truth_paths(cell['inputs'])
            derived &= [p[-1]['target'] for p in paths] == cell['answers'].tolist()
            two = A.truth_paths(cell['two_inputs'])
            derived &= [p[-1]['target'] for p in two] == cell['two_answers'].tolist()
            derived &= [p[0]['target'] for p in two] == cell['two_mid'].tolist()
    check('every answer and every two-hop intermediate is derivable from the VISIBLE rows',
          derived)
    unique = True
    for condition in G.FACT_CONDITIONS:
        for multiple in G.FILLER_MULTIPLES:
            for world in grid:
                cell = G.world_cell(world, condition, multiple)
                lines = FSF.supporting_lines(cell['inputs'])     # raises unless unique
                rows = cell['inputs'].memory[0].tolist()
                for q, line in zip(cell['inputs'].questions.tolist(), lines.tolist()):
                    row = rows[line]
                    unique &= row[0] == WORLD and row[1] == q[1] and row[2] == q[2]
    check('exactly one visible row supports each question in every cell', unique)


# ---------------------------------------------------------------------------- nesting

def group_nesting(grid):
    nested = facts_stable = True
    for condition in G.FACT_CONDITIONS:
        for small, big in zip(G.FILLER_MULTIPLES, G.FILLER_MULTIPLES[1:]):
            for world in grid:
                a = G.story_rows(world, condition, small)
                b = G.story_rows(world, condition, big)
                nested &= subsequence(a, b)
                facts_stable &= ([r for r in a if S._is_fact(r)]
                                 == [r for r in b if S._is_fact(r)])
    check("a smaller cell's rows are an in-order subset of every larger cell's", nested)
    check('the fact rows and their order are identical along the whole filler axis',
          facts_stable)
    superset = True
    for multiple in G.FILLER_MULTIPLES:
        for world in grid:
            small = [r for r in G.story_rows(world, 'F24', multiple) if S._is_fact(r)]
            big = [r for r in G.story_rows(world, 'F64', multiple) if S._is_fact(r)]
            superset &= all(any(x is y for y in big) for x in small) and len(big) == 64
    check('F64 keeps every F24 fact row and adds the other ten people', superset)
    blocks = True
    for world in grid:
        for small, big in zip(G.FILLER_MULTIPLES, G.FILLER_MULTIPLES[1:]):
            lo = world['filler'][:world['filler_offsets'][small]]
            hi = world['filler'][:world['filler_offsets'][big]]
            blocks &= hi[:len(lo)] == lo
    check('the filler blocks themselves are prefix-nested (fresh draws, never copies)',
          blocks and all(len({tuple(r) for r in w['filler']}) > 0.5*len(w['filler'])
                         for w in grid))


# ----------------------------------------------------------------------------- filler

def group_filler(grid):
    spec = G._spec()
    filler_tokens = {spec.filler(f) for f in range(spec.fillers)}
    from premonition.toy_ladder import NEWLINE
    clean = shape = True
    for world in grid:
        for row in world['filler']:
            clean &= not S._is_fact(row)
            clean &= not (ENTITY_MIN <= row[1] < ENTITY_MAX)
            shape &= row[0] == WORLD and row[-1] == NEWLINE
            shape &= all(t in filler_tokens for t in row[1:-1])
    check('no filler row can be read as a fact: never an entity token in the subject slot',
          clean)
    check('filler rows use only WORLD, filler tokens and NEWLINE -- no value, relation '
          'or LINK token ever appears in one', shape)
    answers = set()
    for world in grid:
        answers.update(a for _, _, a in world['attribute'] + world['link'])
    leak = any(t in answers for world in grid for row in world['filler'] for t in row)
    check('no filler token is ever a possible answer token', not leak)
    counts = [sum(1 for r in G.story_rows(world, 'F64', 1) if not S._is_fact(r))
              for world in grid]
    check('1x is the generator\'s own amount of filler/gap rows',
          all(c == len(world['filler'][:world['filler_offsets'][1]])
              for c, world in zip(counts, grid)), f'{counts}')


# -------------------------------------------------------------------------- exclusion

def group_exclusion(grid):
    forbidden = set(json.loads(G.EXCLUSION.read_text()))
    hits = checked = 0
    for condition in G.FACT_CONDITIONS:
        for world in grid:
            cell = G.world_cell(world, condition, 1)
            memory = cell['inputs'].memory.tolist()[0]
            for q in cell['inputs'].questions.tolist():
                checked += 1
                hits += int(A.visible_signature(memory, q) in forbidden)
    check('no new question collides with the registered development exclusion set',
          hits == 0, f'{checked} signatures against {len(forbidden)} forbidden')
    stable = True
    for world in grid[:2]:
        mem0 = G.world_cell(world, 'F64', 0)['inputs'].memory.tolist()[0]
        mem30 = G.world_cell(world, 'F64', 30)['inputs'].memory.tolist()[0]
        q = G.world_cell(world, 'F64', 0)['inputs'].questions.tolist()[0]
        stable &= A.visible_signature(mem0, q) == A.visible_signature(mem30, q)
    check('the semantic signature ignores filler, so the filler axis cannot change it',
          stable)


# ----------------------------------------------------------------------------- sanity

def group_sanity(grid):
    path = G.CHECKPOINTS['factorial-A-seed-0'][1]
    model, sha, meta = G.load_checkpoint(path)
    before = G.C.fingerprint(model)
    started = time.monotonic()
    row = G.score_cell(model, grid, 'F24', 1, two_hop=False)
    check('the checkpoint is unchanged by scoring (read-only)',
          G.C.fingerprint(model) == before, sha[:12])
    print(f'   SANITY (not asserted): arm-A seed-0, F24 / 1x filler -- '
          f"attribute accuracy {row['attribute']['accuracy']}, "
          f"LINK {row['link']['accuracy']}, "
          f"correct-row attention {row['attribute']['correct_line_mass']} "
          f"({row['attribute']['mass_over_uniform']}x uniform), "
          f"{row['geometry']['rows_per_story']} rows/story, "
          f'{time.monotonic()-started:.1f}s', flush=True)
    check('the sanity cell returns a full metric row',
          row['attribute']['n'] == SMALL*G.ATTR_PER_WORLD
          and row['link']['n'] == SMALL*G.LINK_PER_WORLD
          and all(row[f'relation{r}']['n'] > 0 for r in G.ATTRIBUTE_RELATIONS))


GROUPS = dict(build=group_build, pairing=group_pairing, nesting=group_nesting,
              filler=group_filler, exclusion=group_exclusion, sanity=group_sanity)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--worlds', type=int, default=SMALL)
    args = ap.parse_args()
    G.R.configure()
    SMALL = args.worlds
    grid = G.build_grid(SMALL)
    names = [n.strip() for n in args.only.split(',') if n.strip()] or list(GROUPS)
    for name in names:
        print(f'--- {name}', flush=True)
        GROUPS[name](grid)
    print(f'ALL {CHECKS} CHECKS PASSED', flush=True)
