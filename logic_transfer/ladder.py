"""LT-2 learnability ladder: row files, count baseline, independent label check (marks: MARKS-LT2-2026-10-14.md).

  python -m logic_transfer.ladder build --rung 0..6 --out DIR [--n-train 130000] [--n-eval 1200] [--n-new 600]
  python -m logic_transfer.ladder baseline --train TRAIN.jsonl EVAL.jsonl [...]

build writes DIR/rung<r>/{train,dev[,wording],newwords}.jsonl (converted rows, options suffix, <= 208 chars) and DIR/rung<r>/summary.json:
per file n, sha256, label counts, max prompt chars, train-fitted count baseline, overlap with the train prompts (must be 0), the
rows.verify() result and the independent label check (verify_rungs, must agree on 100%).
Seeds: train 100+10r, dev +1, wording +2, newwords +3 (rungs 4-5: dev +1, gate +2, deeper +3; rung 3 = the LT-1 placebo files, seeds 12/25/26).
Eval files never repeat a train prompt (generation excludes them). Rungs 4-5 are F2-matched (logicgen.matched).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

from logicgen import rungs
from logic_transfer import rows as R
from logic_transfer import verify_rungs as V

NEG_WORDS = {'not', 'never', "isn't", "wasn't", 'no', 'none', 'nothing'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def read(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def count_key(prompt):
    """(negation-word count, sentence count) of the prompt body (options suffix removed)."""
    body, _ = V.split_options(prompt)
    toks = re.findall(r"[a-z']+(?:-[a-z]+)?", body.lower())
    neg = sum(1 for t in toks if t in NEG_WORDS or t.startswith('non-'))
    return neg, len(re.findall(r'[.?!]', body))


def count_baseline(train_rows, eval_rows):
    """Train-fitted lookup on count_key (majority label per key; unseen keys -> the global majority). -> dict(acc, n, table_size)."""
    tab = defaultdict(Counter)
    glob = Counter()
    for r in train_rows:
        tab[count_key(r['prompt'])][r['answer']] += 1
        glob[r['answer']] += 1
    gmaj = sorted(glob.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    pred = {k: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, c in tab.items()}
    hit = sum(pred.get(count_key(r['prompt']), gmaj) == r['answer'] for r in eval_rows)
    out = dict(acc=round(100.0 * hit / max(len(eval_rows), 1), 2), hit=hit, n=len(eval_rows), table_size=len(pred))
    lv = defaultdict(lambda: [0, 0])
    for r in eval_rows:
        lv[str(r['level'])][0] += pred.get(count_key(r['prompt']), gmaj) == r['answer']
        lv[str(r['level'])][1] += 1
    out['by_level'] = {k: round(100.0 * v[0] / v[1], 2) for k, v in sorted(lv.items())}
    return out


def write_rows(path, rows):
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def convert_rows(raw, dst):
    """Write raw generator rows to a temp file and convert with the options suffix (format v2). -> raw question texts."""
    with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False) as t:
        for r in raw:
            t.write(json.dumps(r) + '\n')
        tmp = t.name
    try:
        R.convert(tmp, dst, options=True)
    finally:
        os.unlink(tmp)
    return {r['question'] for r in raw}


def gen_convert(kind, split, n, seed, dst, exclude):
    """Rungs 0-2: generate raw rows, convert, write dst. -> (raw question texts, stats)."""
    raw = rungs.make_rows(kind, split, n, seed, 208 - R.OPTIONS_CHARS, exclude=exclude)
    stats = dict(rungs.make_rows.last_stats)
    return convert_rows(raw, dst), stats


# rung -> [(file name, generator split, n, seed offset from the rung base, depths or None)]; the first entry is the train file
LOGIC_SPECS = {
    4: [('train', 'train', 130000, 0, [1]), ('dev', 'dev', 1200, 1, [1]), ('gate', 'gate', 1200, 2, [1])],
    5: [('train', 'train', 130000, 0, None), ('dev', 'dev', 1200, 1, None), ('gate', 'gate', 1608, 2, None), ('deeper', 'test_deeper', 800, 3, None)],
}
TRAIN_N = {1: 36000}     # rung 1: the common-word true/false prompt space is only ~22k per label; a bigger train file would exhaust it and tie word type to the label
RUNG_SEED_BASE = {0: 100, 3: None, 1: 1110, 2: 1120, 4: 1140, 5: 1150, 6: None}     # v2 (Addendum 2): rungs 1, 2, 4, 5 were rebuilt, so their ids / seeds differ from v1 (110/120/140/150)


def train_n(rung):
    return TRAIN_N.get(rung, 130000)


def seed_base(rung):
    return RUNG_SEED_BASE[rung]


ATTACK_MAX = 37.0        # F2 check (marks): the panel's (distinct, singleton, sentences) lookup must score <= 37% on every eval file


def build_logic(rung, d, n_train, summary):
    """Rungs 4-5: logic rows with F2 rejection matching. Returns nothing; fills summary['files'][name]['gen'] and ['f2_attack']."""
    from logicgen import matched
    base = seed_base(rung)
    raw_train, train_q = None, None
    for name, split, n, off, depths in LOGIC_SPECS[rung]:
        n = n_train if name == 'train' else n
        raw = matched.make_rows('logic', split, n, base + off, 208 - R.OPTIONS_CHARS, depths=depths, exclude=train_q)
        info = dict(gen=dict(matched.make_rows.last_stats), seed=base + off, split=split, depths=depths)
        q = convert_rows(raw, os.path.join(d, name + '.jsonl'))
        if name == 'train':
            raw_train, train_q = raw, q
        else:
            info['f2_attack'] = matched.lookup_attack(raw_train, raw)
            assert info['f2_attack']['acc'] <= ATTACK_MAX, f'F2 lookup attack {info["f2_attack"]} on {name} exceeds {ATTACK_MAX}'
        summary['files'][name] = info
    del raw_train


def build_placebo(d, n_train, summary):
    """Rung 3: the LT-1 depth-0 placebo files (same seeds, so byte-identical to the sealed ones): train 12, dev 25, wording 26."""
    from logic_transfer import run_lt1
    spec = [('placebo', 'train', n_train, 12, 'train.jsonl'), ('placebo', 'dev', 1200, 25, 'dev.jsonl'), ('placebo', 'test_wording', 1200, 26, 'wording.jsonl')]
    gen = os.path.join(d, '_gen')
    run_lt1.make_rows(gen, spec=spec)
    for _, _, _, seed, rel in spec:
        os.replace(os.path.join(gen, rel), os.path.join(d, rel))
        summary['files'][rel[:-6]] = dict(seed=seed)
    import shutil
    shutil.rmtree(gen)


TWO_FACT_FILES = ('train', 'dev', 'newwords')       # rung 6 (Addendum 7): the rung-2 files restricted to rows with exactly ONE distractor (two facts); wording is not evaluated there


def build_two_fact(d, out, summary):
    """Rung 6 = rung 2 with exactly one distractor. The rows are the sealed rung-2 rows with meta.n_distractors == 1, in file order, ids unchanged (rung 6 runs
    never see the rung-2 files, so the id-keyed loss cache cannot collide); rung 2 is built first when missing (byte-deterministic, hashes checked later).
    A subset of a train-disjoint eval file is train-disjoint; the count baseline is refitted on the filtered train file."""
    src = os.path.join(out, 'rung2')
    if not os.path.exists(os.path.join(src, 'summary.json')):
        build(2, out)
    for name in TWO_FACT_FILES:
        rows = [r for r in read(os.path.join(src, name + '.jsonl')) if r['meta']['n_distractors'] == 1]
        write_rows(os.path.join(d, name + '.jsonl'), rows)
        summary['files'][name] = dict(filter='rung2 rows with meta.n_distractors == 1', source=f'rung2/{name}')


def build(rung, out, n_train=None, n_eval=1200, n_new=600):
    kind = f'rung{rung}'
    assert 0 <= rung <= 6
    n_train = n_train or train_n(rung)
    d = os.path.join(out, kind)
    os.makedirs(d, exist_ok=True)
    base = seed_base(rung)
    summary = dict(rung=rung, kind=kind, files={})
    if rung <= 2:
        summary['seeds'] = dict(train=base, dev=base + 1, wording=base + 2, newwords=base + 3)
        train_q, st = gen_convert(kind, 'train', n_train, base, os.path.join(d, 'train.jsonl'), None)
        summary['files']['train'] = dict(gen=st)
        for i, (name, split, n) in enumerate((('dev', 'dev', n_eval), ('wording', 'wording', n_eval), ('newwords', 'newwords', n_new)), 1):
            _, st = gen_convert(kind, split, n, base + i, os.path.join(d, name + '.jsonl'), train_q)
            summary['files'][name] = dict(gen=st)
    elif rung == 3:
        build_placebo(d, n_train, summary)
    elif rung == 6:
        build_two_fact(d, out, summary)
    else:
        build_logic(rung, d, n_train, summary)
    train_rows = read(os.path.join(d, 'train.jsonl'))
    train_prompts = {r['prompt'] for r in train_rows}
    for name, info in summary['files'].items():
        p = os.path.join(d, name + '.jsonl')
        rows = read(p)
        info.update(path=os.path.relpath(p, out), n=len(rows), sha256=sha256(p), labels=dict(Counter(r['answer'] for r in rows)),
                    distinct_prompts=len({r['prompt'] for r in rows}), verify=R.verify(p))
        if name != 'train':
            info['overlap_with_train_prompts'] = sum(r['prompt'] in train_prompts for r in rows)
            info['count_baseline'] = count_baseline(train_rows, rows)
        info['independent_label_check'] = V.check_file(p)
        assert info['independent_label_check']['agree'] == info['n'], f'independent solver disagrees on {name}: {info["independent_label_check"]}'
    json.dump(summary, open(os.path.join(d, 'summary.json'), 'w'), indent=1)
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--rung', type=int, required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--n-train', type=int, default=None, help='default: ladder.train_n(rung) (130000; 36000 for rung 1)')
    b.add_argument('--n-eval', type=int, default=1200)
    b.add_argument('--n-new', type=int, default=600)
    c = sub.add_parser('baseline')
    c.add_argument('--train', required=True)
    c.add_argument('files', nargs='+')
    a = ap.parse_args(argv)
    if a.cmd == 'build':
        s = build(a.rung, a.out, a.n_train, a.n_eval, a.n_new)
        for name, info in s['files'].items():
            print(name, info['n'], info['sha256'][:12], info['labels'], 'baseline', info.get('count_baseline', {}).get('acc'),
                  'overlap', info.get('overlap_with_train_prompts'), 'indep', info['independent_label_check']['agreement'])
    else:
        tr = read(a.train)
        for p in a.files:
            print(p, json.dumps(count_baseline(tr, read(p))))


if __name__ == '__main__':
    main()
