#!/usr/bin/env python3
"""Independent check of the six E edit-pair cells (attack b).

My own interpreter walks each side's visible memory and re-derives the answer from the
question alone.  The builder's expected answers, its chains and its edit classification
are all treated as claims to be checked, not as inputs.
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PANELS = HERE.parent / 'dev-panels'

LINK = 11            # the LINK relation token used in every chain step
OPEN, CLOSE = 4, 5   # question delimiters


def visible(side):
    return [tuple(r) for i, r in enumerate(side['memory']) if r and i < side['where']]


def interpret(side):
    """Answer the question from the visible memory, my own walk, no chain consulted."""
    q = list(side['question'])
    if q[0] != OPEN or q[-1] != CLOSE:
        return None, 'question is not delimited as expected'
    start, ops = q[1], q[2:-1]
    rows = visible(side)
    # only the relations the question actually asks about; other relations appear on
    # distractor rows and may legitimately repeat a (subject, relation) pair
    wanted = set(ops)
    index = {}
    for row in rows:
        if row[2] not in wanted:
            continue
        key = (row[1], row[2])
        if key in index:
            return None, f'ambiguous memory: two rows for {key}'
        index[key] = row[3]
    here, walked = start, []
    for op in ops:
        nxt = index.get((here, op))
        if nxt is None:
            return None, f'no row for ({here}, {op})'
        walked.append([here, op, nxt])
        here = nxt
    return (here, walked), None


out = {}
for cell in sorted(p.stem for p in PANELS.glob('E-*.json') if '.meta' not in p.name):
    doc = json.loads((PANELS / f'{cell}.json').read_text())
    edit = doc.get('edit')
    rows = dict(cell=cell, edit=edit, hops=doc['hops'], people=doc['people'],
                units=len(doc['units']), kind=doc['kind'])
    bad_rows, bad_answer, bad_chain, bad_question, edited_row_count = [], [], [], [], Counter()
    on_chain, answer_changed = Counter(), Counter()
    for unit in doc['units']:
        a, b = unit['a'], unit['b']
        if list(a['question']) != list(b['question']):
            bad_question.append(unit['index'])
        ra, rb = visible(a), visible(b)
        if len(ra) != len(rb):
            bad_rows.append((unit['index'], 'different row counts'))
            continue
        differ = [i for i in range(len(ra)) if ra[i] != rb[i]]
        edited_row_count[len(differ)] += 1
        # the edit must be a MEMORY edit only: same subjects and relations everywhere
        # except (for a value edit) the one edited row's object
        for i in differ:
            if ra[i][1] != rb[i][1]:
                bad_rows.append((unit['index'], f'row {i} changes its subject'))
        for side, letter in ((a, 'a'), (b, 'b')):
            got, problem = interpret(side)
            if problem:
                bad_answer.append((unit['index'], letter, problem))
                continue
            here, walked = got
            if here != int(side['answer']):
                bad_answer.append((unit['index'], letter,
                                   f'my walk gives {here}, the panel says {side["answer"]}'))
            if [list(s) for s in side['chain']] != walked:
                bad_chain.append((unit['index'], letter))
        touched = any(any(list(step)[:2] == [ra[i][1], ra[i][2]] for step in a['chain'])
                      for i in differ)
        on_chain[touched] += 1
        answer_changed[int(a['answer']) != int(b['answer'])] += 1
    rows.update(
        question_identical_on_both_sides=not bad_question,
        my_walk_reproduces_every_answer=not bad_answer,
        my_walk_reproduces_every_chain=not bad_chain,
        memory_edit_shape_ok=not bad_rows,
        edited_rows_per_unit=dict(edited_row_count),
        edit_touches_the_a_side_chain=dict(on_chain),
        answer_changed=dict(answer_changed),
        problems=dict(question=bad_question[:4], answer=bad_answer[:4],
                      chain=bad_chain[:4], rows=bad_rows[:4]))
    out[cell] = rows

expect = {}
for cell, row in out.items():
    kind = row['edit']
    if kind == 'irrelevant':
        expect[cell] = dict(want='answer UNCHANGED and the edit OFF the chain',
                            ok=bool(row['answer_changed'].get(True, 0) == 0
                                    and row['edit_touches_the_a_side_chain'].get(True, 0) == 0))
    else:
        expect[cell] = dict(want='answer CHANGED and the edit ON the chain',
                            ok=bool(row['answer_changed'].get(False, 0) == 0
                                    and row['edit_touches_the_a_side_chain'].get(False, 0) == 0))
result = dict(cells=out, expectations=expect,
              all_ok=bool(all(v['ok'] for v in expect.values())
                          and all(o['my_walk_reproduces_every_answer']
                                  and o['my_walk_reproduces_every_chain']
                                  and o['question_identical_on_both_sides']
                                  and o['memory_edit_shape_ok'] for o in out.values())))
print(json.dumps({k: (v if k != 'cells' else
                      {c: {kk: vv for kk, vv in r.items() if kk != 'problems'}
                       for c, r in v.items()}) for k, v in result.items()}, indent=1))
(HERE / 'checks-19b-epairs.json').write_text(json.dumps(result, indent=1, default=str))
