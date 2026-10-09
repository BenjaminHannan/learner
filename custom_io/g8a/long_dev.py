"""Held-out long-row test file for B3 mark B3-5 ("reads long input"; PLAN.md, big-run, addendum 12:40 PM ET 10-09).

Our own generators only (the skills_curriculum families; no TEACH rows, no Claude-written text, nothing from the protected panels).
Four length buckets of the PROMPT in letters: le280 (the reference), 280-700, 700-1300, 1300-2000. Every bucket holds the SAME base items: the same
34 trained families x K generator items (hold-out clean, "in_dist" kind, seeds disjoint from every training / dev seed), so the buckets differ only in length.
le280 is the base prompt itself. The longer buckets pad the base with distractor sentences from FineWeb-Edu documents of a shard that no training pool
reads (sample/10BT shard 013; the 8a pools read shard 0). The base prompt (the facts and the question) sits in the first, middle or last third of the
input, equally often per bucket. Gold answers are the generator's. A pad sentence is dropped if it has a digit or contains any slot / answer string of the
row, so the gold answer stays unambiguous. Rows keep the dev-row format (+ a 'long' field).

  python3 -m custom_io.g8a.long_dev --curriculum DIR --shard 013_00000.parquet --out OUT --check-prompts train.jsonl ... [--k 10]
"""
import argparse, glob, hashlib, json, os, random, re, sys

BUCKETS = [('le280', 0, 280), ('b280_700', 281, 700), ('b700_1300', 701, 1300), ('b1300_2000', 1301, 2000)]
SEED, NS = 424242, 'LD'        # training seeds are 1 (curriculum) and 400-405; dev built with seed 1
POS = ['first', 'middle', 'last']


def sentences(shard, need, say=print):
    """Clean distractor sentences, in document order, from the parquet shard: [(sentence, doc_id)]."""
    import pyarrow.parquet as pq
    from custom_io.g8a import cloze as Z
    pf = pq.ParquetFile(shard)
    out, seen, docs = [], set(), 0
    split = re.compile(r'(?<=[.!?]) +(?=[A-Z])')
    for g in range(pf.num_row_groups):
        t = pf.read_row_group(g, columns=['id', 'text']).to_pydict()
        for did, text in zip(t['id'], t['text']):
            docs += 1
            for s in split.split(Z.norm_text(text)):
                if 40 <= len(s) <= 180 and s.isascii() and s[0].isupper() and not re.search(r'\d|____', s) and s not in seen:
                    seen.add(s)
                    out.append((s, did))
        if len(out) >= need:
            break
    say('distractor sentences', len(out), 'from', docs, 'documents')
    return out


def file_sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def clash(s, row):
    low = s.lower()
    keys = [str(x).lower() for x in list(row.get('slots') or []) + [row['answer']] if len(str(x)) >= 2]
    return any(re.search(r'(?<![a-z0-9])' + re.escape(k) + r'(?![a-z0-9])', low) for k in keys)


def pad(row, bucket_i, g, pool, rng):
    """-> (prompt, position, n_sentences) with len(prompt) inside the bucket."""
    _, lo, hi = BUCKETS[bucket_i]
    base = row['prompt']
    pos = POS[(g + bucket_i) % 3]      # g = running index over all base items: thirds come out equal per bucket
    for _ in range(200):
        target = rng.randint(lo + 20, hi - 5)
        chosen, n = [], len(base)
        while n < target:
            s, _ = pool[rng.randrange(len(pool))]
            if clash(s, row) or s in chosen:
                continue
            if n + 1 + len(s) > hi:
                break
            chosen.append(s)
            n += 1 + len(s)
        if len(chosen) < 2:
            continue
        a = {'first': 0, 'middle': len(chosen) // 2, 'last': len(chosen)}[pos]
        text = ' '.join(chosen[:a] + [base] + chosen[a:])
        if lo <= len(text) <= hi:
            return text, pos, len(chosen)
    raise RuntimeError('could not pad %s into %s' % (row['id'], BUCKETS[bucket_i][0]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--curriculum', required=True, help='directory holding skills_curriculum/')
    ap.add_argument('--shard', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--k', type=int, default=10, help='base items per family')
    ap.add_argument('--check-prompts', nargs='*', default=[], help='jsonl files whose prompts a base item must not equal (every training / dev / panel-free pool)')
    a = ap.parse_args(argv)
    sys.path.insert(0, a.curriculum)
    from skills_curriculum import skills, build as B  # noqa: F401
    from skills_curriculum.core import FAMILIES
    from custom_io.data import ASCII
    seen = set()
    for p in a.check_prompts:
        for pat in (glob.glob(p) or [p]):
            with open(pat, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        seen.add(json.loads(line)['prompt'])
    print('prompts to avoid', len(seen))
    pool = sentences(a.shard, 40000)
    fams = B.train_families()
    rows, bases = [], []
    for fid in fams:
        m = B.Maker(fid, NS, SEED)
        for j in range(a.k):
            it = m.next('in_dist', seen)
            assert it is not None, fid
            assert len(it['prompt']) <= 280, (fid, len(it['prompt']))
            seen.add(it['prompt'])
            bases.append((fid, j, it))
    for bi, (name, lo, hi) in enumerate(BUCKETS):
        for g, (fid, j, it) in enumerate(bases):
            r = json.loads(json.dumps(it))
            r['base_id'] = it['id']
            if bi == 0:
                pos, ns_ = 'none', 0
            else:
                rng = random.Random('%s|%d|%s' % (it['id'], SEED, name))
                r['prompt'], pos, ns_ = pad(it, bi, g, pool, rng)
            r['id'] = 'long-%s-%s' % (name, it['id'])
            r['long'] = dict(bucket=name, position=pos, base_id=it['id'], base_len=len(it['prompt']), pad_sentences=ns_)
            assert all(c in ASCII for c in r['prompt']), r['id']
            assert lo <= len(r['prompt']) <= hi, (r['id'], len(r['prompt']))
            rows.append(r)
    os.makedirs(a.out, exist_ok=True)
    f = os.path.join(a.out, 'long_dev.jsonl')
    with open(f, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + '\n')
    cnt = {}
    for r in rows:
        c = cnt.setdefault(r['long']['bucket'], dict(rows=0, pos={}, min_len=10 ** 9, max_len=0, families=set()))
        c['rows'] += 1
        c['pos'][r['long']['position']] = c['pos'].get(r['long']['position'], 0) + 1
        c['min_len'], c['max_len'] = min(c['min_len'], len(r['prompt'])), max(c['max_len'], len(r['prompt']))
        c['families'].add(r['family'])
    for c in cnt.values():
        c['families'] = len(c['families'])
    man = dict(file='long_dev.jsonl', sha256=file_sha(f), rows=len(rows), families=len(fams), k_per_family=a.k, buckets=cnt, seed=SEED, namespace=NS,
               generator=dict(package='skills_curriculum', files_sha256={os.path.basename(p): file_sha(p) for p in sorted(glob.glob(os.path.join(a.curriculum, 'skills_curriculum', '*.py')))}),
               shard=os.path.basename(a.shard), shard_sha256=file_sha(a.shard), distractor_sentences=len(pool), avoided_prompts=len(seen) - len(bases),
               rules='in_dist-clean generator items; pad sentences: ASCII, 40-180 chars, no digits, no row slot/answer string; positions cycled first/middle/last; no TEACH, no protected panels')
    json.dump(man, open(os.path.join(a.out, 'long_dev_MANIFEST.json'), 'w'), indent=1)
    print(json.dumps({k: man[k] for k in ('sha256', 'rows', 'families', 'buckets')}, indent=1, default=str))


if __name__ == '__main__':
    main()
