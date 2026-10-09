"""ST1 inputs for B3 group 2 (PLAN.md big-run, "G2 step 2b", sealed 12:55 PM ET 10-09).

Rule (fixed, no hand picking): the kinds of the variant split (a kind = family id + held-out variant), in alphabetical order of family id, keeping the first
three that (a) have a generator that makes fresh question-and-answer rows, (b) appear in no training pool (own72 skills, the 200k skills train file, the
bigger 1M build): a held-out variant is never trained on, with or without steps, and (c) the calculator tool can check (progparse builds a calculator program
whose result is the gold answer, on every dev row of the kind).
For each kind: 2,000 fresh question-and-answer pairs (no steps, no meta, no slots) and a separate 500-row evaluation file (dev-row format). Namespaces ST1T /
ST1E and seeds disjoint from the curriculum (1), the long file (424242) and the 8a seeds (400-405); prompts disjoint from every dev split, every training pool,
the long file and each other.

  python3 -m custom_io.g8a.st1_data --curriculum DIR --out OUT --pools train.jsonl ... --dev DEVDIR ...
"""
import argparse, glob, hashlib, json, os, sys

SEED_T, SEED_E = 5311, 5312
N_TRAIN, N_EVAL = 2000, 500


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def prompts(paths):
    s = set()
    for p in paths:
        for f in (glob.glob(p) or [p]):
            with open(f, encoding='utf-8') as fh:
                for line in fh:
                    if line.strip():
                        s.add(json.loads(line)['prompt'])
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--curriculum', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pools', nargs='*', default=[], help='training pools (jsonl) the held-out variant must not appear in')
    ap.add_argument('--dev', nargs='*', default=[], help='dev splits: the variant split names the kinds, every split\'s prompts are avoided')
    ap.add_argument('--avoid', nargs='*', default=[], help='more jsonl files whose prompts are avoided (the long file)')
    a = ap.parse_args(argv)
    sys.path.insert(0, a.curriculum)
    from skills_curriculum import skills, build as B  # noqa: F401
    from skills_curriculum.core import FAMILIES, make_item
    from custom_io.models import progparse as pp
    dev_rows = []
    for d in a.dev:
        for f in sorted(glob.glob(os.path.join(d, '*.jsonl'))):
            dev_rows += [(os.path.basename(f), json.loads(l)) for l in open(f, encoding='utf-8') if l.strip()]
    var = [r for n, r in dev_rows if n == 'variant.jsonl']
    in_train = set()
    for p in a.pools:
        for f in (glob.glob(p) or [p]):
            for line in open(f, encoding='utf-8'):
                r = json.loads(line)
                in_train.add((r.get('family'), r.get('variant')))
    kinds = {}
    for r in var:
        kinds.setdefault((r['family'], r['variant']), []).append(r)
    chosen, log = [], []
    for (fam, v), rs in sorted(kinds.items()):
        why = []
        if fam not in FAMILIES or v not in FAMILIES[fam]['variants']:
            why.append('no generator')
        if (fam, v) in in_train:
            why.append('in a training pool')
        if not all(pp.program_for(r)[0] is not None for r in rs):
            why.append('calculator cannot check every dev row')
        log.append(dict(family=fam, variant=v, dev_rows=len(rs), rejected=why))
        if not why and len(chosen) < 3:
            chosen.append((fam, v))
    print('kinds considered (alphabetical):', json.dumps(log[:8]))
    assert len(chosen) == 3, chosen
    avoid = set(r['prompt'] for _, r in dev_rows) | prompts(a.pools) | prompts(a.avoid)
    os.makedirs(a.out, exist_ok=True)
    man = dict(rule=__doc__.split('\n\n')[1].strip(), kinds=[], seeds=dict(train=SEED_T, eval=SEED_E), namespaces=dict(train='ST1T', eval='ST1E'),
               kinds_considered_before_the_third=log[:log.index(next(x for x in log if (x['family'], x['variant']) == chosen[-1])) + 1])
    for fam, v in chosen:
        kind = f'{fam}__{v}'
        out = {}
        for tag, ns, seed, n in (('train', 'ST1T', SEED_T, N_TRAIN), ('eval', 'ST1E', SEED_E, N_EVAL)):
            rows, i = [], 0
            import random
            rng = random.Random(f'{ns}|{seed}|{kind}')
            while len(rows) < n:
                i += 1
                assert i < 200000, (kind, tag, len(rows))
                it = make_item(fam, f'{ns}{seed}', i, rng.choices((0, 1, 2), B.DIFF_WEIGHTS)[0], force_variant=v)
                f = it['flags']
                if f['variant'] or f['answer'] or f['frame'] or f['vocab'] or f['family'] or it['est_tokens'] > B.MAX_TOKENS_EST:
                    continue
                if it['prompt'] in avoid:
                    continue
                avoid.add(it['prompt'])
                it['id'] = f'st1-{tag}-{kind}-{len(rows):04d}'
                if tag == 'train':
                    it = dict(id=it['id'], family=fam, variant=v, prompt=it['prompt'], answer=it['answer'], accepted=it['accepted'], steps=[])
                rows.append(it)
            fn = os.path.join(a.out, f'st1_{tag}_{kind}.jsonl')
            with open(fn, 'w', encoding='utf-8') as fh:
                for r in rows:
                    fh.write(json.dumps(r, sort_keys=True) + '\n')
            out[tag] = dict(file=os.path.basename(fn), rows=len(rows), sha256=sha(fn), draws=i)
        man['kinds'].append(dict(family=fam, variant=v, id=kind, **out))
    man['generator_files_sha256'] = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(a.curriculum, 'skills_curriculum', '*.py')))}
    json.dump(man, open(os.path.join(a.out, 'st1_MANIFEST.json'), 'w'), indent=1)
    print(json.dumps(man['kinds'], indent=1))


if __name__ == '__main__':
    main()
