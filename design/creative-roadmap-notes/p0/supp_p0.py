"""Supplementary (post hoc, added AFTER seeing the B2_s100 tables; not part of the pre-registered meaning):
1. effective program = the non-NOOP (op, a, b) steps only (the raw 'program' also counts operand pointers on NOOP steps,
   which do nothing). P(answer differs from greedy | effective program differs), by greedy mode.
2. where sampled hits come from: the candidate's talker mode (NUM output equal to a prompt number / other NUM / WORD / GEN).
3. a chance floor: pick a prompt token (data.word_spans) uniformly 32 times; floor pass@32 = 1 - (1 - k/W)^32, k = tokens
   equal to the answer (normalised). Answers not in the prompt get 0.
python supp_p0.py DATA_DIR p0_B2_s100.json [p0_B2_s101.json]   (run from the B2 worktree root)
"""
import json, re, sys
from collections import Counter, defaultdict
import numpy as np
from custom_io.data import load_rows, word_spans
from custom_io.evalx import norm
from custom_io.models import progparse as pp

data = sys.argv[1]
prompts = {}
for f in ('family', 'frame', 'vocab'):
    for r in load_rows(f'{data}/dev/{f}.jsonl'):
        prompts[r['id']] = r['prompt']


def eff(prog):
    st = [tuple(prog[i:i + 3]) for i in range(0, len(prog), 3)]
    return tuple(s for s in st if s[0] != 0)


for path in sys.argv[2:]:
    R = json.load(open(path))
    name = re.search(r'(B2_s\d+)', path).group(1)
    print(f'\n## {name} (supplementary, post hoc)\n')
    print('| split/variant | T | eff. programs distinct (mean) | eff. program != greedy % | P(answer != greedy given eff. program != greedy) %, greedy NUM rows | same, other rows | hits by candidate path (NUM=prompt number / NUM other / WORD / GEN) | uniform prompt-token floor pass@32 | sampled pass@32 |')
    print('|---|---|---|---|---|---|---|---|---|')
    for key, recs in R['records'].items():
        for T in R['temps']:
            k = str(T)
            dist, effdiff, cond = [], [], {True: [0, 0], False: [0, 0]}
            path = Counter()
            floors, p32 = [], []
            for r in recs:
                s = r['samples'][k]
                ge = eff(r['greedy_prog'])
                es = [eff(p) for p in s['prog']]
                dist.append(len(set(es)))
                effdiff.append(np.mean([e != ge for e in es]))
                isnum = r['greedy_mode'] == 0
                for e, o in zip(es, s['outs']):
                    if e != ge:
                        cond[isnum][0] += 1
                        cond[isnum][1] += norm(o) != norm(r['greedy'])
                nums = set(map(str, pp.prompt_numbers(prompts[r['id']])))
                if not r['greedy_hit']:
                    for o, h, md in zip(s['outs'], s['hits'], s['mode']):
                        if h:
                            path['NUM=prompt#' if md == 0 and o in nums else ('NUM other' if md == 0 else ('WORD' if md == 1 else 'GEN'))] += 1
                toks = [norm(prompts[r['id']][a:b]) for a, b in word_spans(prompts[r['id']])[:pp.W_MAX]]
                kk = sum(t == norm(r['answer']) for t in toks)
                floors.append(1 - (1 - kk / max(len(toks), 1)) ** 32)
                p32.append(int(any(s['hits'])))
            pc = lambda c: f'{100 * c[1] / c[0]:.1f} (n={c[0]})' if c[0] else 'n/a'
            print(f'| {key} | {T} | {np.mean(dist):.1f} | {100 * np.mean(effdiff):.1f} | {pc(cond[True])} | {pc(cond[False])} | '
                  f'{path["NUM=prompt#"]} / {path["NUM other"]} / {path["WORD"]} / {path["GEN"]} | {100 * np.mean(floors):.1f} | {100 * np.mean(p32):.1f} |')
