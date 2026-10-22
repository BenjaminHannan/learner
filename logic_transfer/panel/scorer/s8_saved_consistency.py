"""Internal-consistency audit of EVERY saved score.json that contains logic/placebo splits (stdlib only):
n vs the eval file's row count, file sha256 vs the file on disk, sum(by_label) / sum(by_level) / answer_words diagonal == correct,
answer_words gold-row totals == label counts, exact == 100*correct/n, noop_round1.n == n.

  python s8_saved_consistency.py -> s8_saved_consistency.json
"""
import collections
import glob
import hashlib
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
EVAL = SP + '/lt2/rows/eval'


def sha(p):
    h = hashlib.sha256()
    h.update(open(p, 'rb').read())
    return h.hexdigest()


def main():
    files = sorted(set(glob.glob(SP + '/lt2/**/score*.json', recursive=True) + glob.glob(SP + '/wt/lt/logic_transfer/results/**/score*.json', recursive=True)
                       + glob.glob(SP + '/wt/lt/logic_transfer/results/*score*.json')))
    gold = {}
    disk_sha = {}
    for p in glob.glob(EVAL + '/*.jsonl'):
        name = os.path.basename(p)[:-6]
        rs = [json.loads(l) for l in open(p)]
        gold[name] = (len(rs), collections.Counter(r['answer'] for r in rs))
        disk_sha[name] = sha(p)
    R = {'n_files': 0, 'n_splits': 0, 'problems': [], 'sha_mismatch_files': [], 'rows': []}
    for f in files:
        d = json.load(open(f))
        if 'splits' not in d:
            continue
        R['n_files'] += 1
        for name, v in d['splits'].items():
            if name not in gold:
                continue
            R['n_splits'] += 1
            n_expect, lab = gold[name]
            tag = f'{os.path.relpath(f, SP)}::{name}'
            def bad(msg):
                R['problems'].append(f'{tag}: {msg}')
            if v['n'] != n_expect: bad(f'n {v["n"]} != file rows {n_expect}')
            if round(100 * v['correct'] / v['n'], 4) != v['exact']: bad('exact != 100*correct/n')
            if sum(c['correct'] for c in v['by_label'].values()) != v['correct']: bad('sum by_label correct')
            if sum(c['n'] for c in v['by_label'].values()) != v['n']: bad('sum by_label n')
            if {k: c['n'] for k, c in v['by_label'].items()} != dict(lab): bad('by_label n != label counts')
            if sum(c['correct'] for c in v['by_level'].values()) != v['correct']: bad('sum by_level correct')
            if sum(c['n'] for c in v['by_level'].values()) != v['n']: bad('sum by_level n')
            aw = next(iter(v['answer_words'].values()))
            if {g: sum(h.values()) for g, h in aw.items()} != dict(lab): bad('answer_words gold totals != label counts (orientation)')
            if sum(h.get(g, 0) for g, h in aw.items()) != v['correct']: bad('answer_words diagonal != correct')
            if v['noop_round1']['n'] != v['n']: bad('noop n')
            sh = d.get('logic_files_sha256', {}).get(name)
            if sh is None:
                R['sha_mismatch_files'].append(f'{tag}: no sha recorded')
            elif sh != disk_sha[name]:
                R['sha_mismatch_files'].append(f'{tag}: sha differs from file on disk')
            if name == 'logic_gate':
                R['rows'].append((os.path.relpath(f, SP).replace('wt/lt/logic_transfer/results/', 'R/'), v['correct'], v['n'], round(v['exact'], 2)))
    R['gate_accuracy_range'] = [min(r[3] for r in R['rows']), max(r[3] for r in R['rows'])] if R['rows'] else None
    R['n_problems'] = len(R['problems'])
    json.dump(R, open(f'{OUT}/s8_saved_consistency.json', 'w'), indent=1)
    print({k: R[k] for k in ('n_files', 'n_splits', 'n_problems', 'gate_accuracy_range')})
    print('sha issues:', len(R['sha_mismatch_files']), R['sha_mismatch_files'][:5])
    print(R['problems'][:10])


if __name__ == '__main__':
    main()
