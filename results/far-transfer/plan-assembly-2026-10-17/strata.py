"""Dead-zone strata on the HO cell of a dump_items file: hit rate by (n_steps, cells), and where the first wrong call falls by role.
python3 out/strata.py out/items-X.jsonl"""
import collections
import json
import re
import sys

sys.path.insert(0, '.')
from domain.far import join_gap as JG
from domain.tools import sheet as sheet_tool


def ncells(prompt):
    f = prompt.split('=', 1)[1]
    n = 0
    for m in re.finditer(r'([AB])(\d)(?::([AB])(\d))?', f):
        n += (int(m.group(4)) - int(m.group(2)) + 1) if m.group(3) else 1
    return n


def kj(prompt):
    f = prompt.split(';', 1)[1].strip()[1:]
    sp = JG.split_formula(f)
    op, K, J, _ = sp
    nK = len(sheet_tool.evaluate(JG.piece_prompt(prompt, K))['steps'])
    nJ = len(sheet_tool.evaluate(JG.piece_prompt(prompt, J))['steps'])
    return K, J, nK, nJ


def role(r, nK, nJ, n):
    if r is None:
        return 'all calls right'
    if r == 0:
        return 'R0 (K first call)'
    if r < nK:
        return 'K later call'
    if r == nK:
        return 'TRANSITION (J first call)'
    if r < nK + nJ:
        return 'J later call'
    if r == n - 1:
        return 'join call'
    return 'stop/extra'


def main(path, cell='HO'):
    items = [json.loads(l) for l in open(path) if json.loads(l)['cell'] == cell]
    by = collections.defaultdict(lambda: [0, 0])
    roles = collections.defaultdict(collections.Counter)
    shapes = collections.defaultdict(collections.Counter)
    for it in items:
        n, c = len(it['tool_steps']), ncells(it['prompt'])
        K, J, nK, nJ = kj(it['prompt'])
        assert nK + nJ + 1 == n, (it['prompt'], nK, nJ, n)
        key = 'DZ (4 steps, 4 cells)' if (n, c) == (4, 4) else f'{n} steps' + (' (5 cells)' if n == 4 else '')
        by[key][0] += it['hit']
        by[key][1] += 1
        r = it['first_diff_round']
        if r is not None and r >= n:
            r = n
        roles[key][role(r, nK, nJ, n) if not it['calls_match'] or r is not None else 'all calls right'] += 1
        shapes[key][(nK, nJ)] += 1
    print(path)
    for k in sorted(by):
        h, t = by[k]
        print(f'  {k:24s} hits {h}/{t}  shapes(nK,nJ) {dict(shapes[k])}')
        tot = sum(roles[k].values())
        for rl, v in roles[k].most_common():
            print(f'      {rl:28s} {v:4d}  {100 * v / tot:5.1f}%')


if __name__ == '__main__':
    main(sys.argv[1], *(sys.argv[2:3]))
