"""Pool assembler: the fixed-mix, nested training pool of one 8a rung (8A spec sections 2, 4, 5 and addenda A, B).

  python3 -m custom_io.g8a.pool build --rung 10M --seed 400 --out /job/pool10M --dev /job/data/dev \
      --own72 /job/own72 --web /job/web/slice_rung10.jsonl [--max-ans 64] [--overlap-index panels.npz --data-pool DIR]
  python3 -m custom_io.g8a.pool build --rung 3M --seed 400 --out OUT --dev DEV --own PATH[:WEIGHT] [PATH[:WEIGHT] ...] --web SLICE   # plain row files
  python3 -m custom_io.g8a.pool nested SMALL_DIR BIG_DIR          # every row of the smaller pool is in the bigger one (same line)

Writes OUT/train.jsonl (own rows, then cloze rows), OUT/dev/ (copied from --dev: the pooled-5 dev splits, never trained on) and OUT/MANIFEST.json
(sha256 of the train file, rows and word pieces per source, the cloze statistics, the schedule, the deviations from the spec text). train.py picks
MANIFEST.json up and stores its sha256 in every RESULT.json.

Own text, --own72 DIR (data_pool/gen_own_text.py output: skills.jsonl, english.jsonl, teach.jsonl, each row with `rung` and `pos`): the rows with
rung <= the rung's own_rung (3M and 10M read the 22.8M-token prefix, 30M all 72M), in `pos` order, so a bigger rung's own text starts with the smaller
one's. A skills row is used as is. An english / teach record (one passage, one question) becomes ONE row: prompt = panel + ' ' + question, the panel alternating
source_text / paraphrase by record position, answer = english.taught_answer (the yes/no word, else the answer as it sits in the prompt, else the canonical answer),
the way english.qa_rows builds them. Rows with an answer over --max-ans chars, a prompt over 400 chars or a non-ASCII char are dropped and counted.
Own text, --own PATH[:WEIGHT]: plain standard-format row files, each taken from the top until its share (OWN_SHARE x pool x weight / sum of weights).

Web: cloze rows (g8a.cloze) from the slice, in document order, until the web budget. By default the mix is KEPT (--keep-mix): the web budget is
min(WEB_SHARE x pool, own pieces x WEB_SHARE / OWN_SHARE), so if answer-length drops leave less own text than the data plan counted, the pool shrinks with
it and stays 38% own / 62% web. Without --keep-mix a shortfall refuses to build unless --allow-short.

Schedule (addendum B1): steps = max(24,000, ceil(seen word pieces / (256 x mean row pieces))), seen = 20 pieces per trained parameter. If the 20-per-parameter
count rules and a row would be drawn more than MAX_REUSE times, build refuses; if the 24,000-update floor rules, the passes are reported, not refused.
Word pieces: web rows use the document's own GPT-2 token_count; own rows are estimated as chars / ratio per source (skills 3.12, english 3.90, teach 3.76 chars
per LFM2.5 token, measured on data_pool's own72 against its manifest), disclosed in the manifest.
"""
import argparse, hashlib, heapq, json, math, os, shutil, sys
from custom_io import english as EN
from custom_io.data import ASCII
from custom_io.g8a import cloze as Z
from custom_io.g8a.configs import BATCH, OWN_SHARE, RUNGS, UPDATE_FLOOR, WEB_SHARE

OWN_CHARS_PER_PIECE = {'skills': 3.12, 'english': 3.90, 'teach': 3.76, 'rows': 3.13}
MAX_REUSE = 4
MAX_WEB_SHORT = 0.06       # the rung slices yield 95.5% of their token budget as cloze pieces (measured on the rung30 slice: 112.45M of 117.8M)
HYGIENE_PROMPT, HYGIENE_ANS = 400, 64       # data hygiene only (a prompt or answer this long is a broken row); the model caps are sized from the data (g8a/caps.py)
DEVIATIONS = [
    'cloze prompt <= %d chars incl. the blank, blanked word %d..%d letters (the spec sizes, addendum E); model caps sized from the data (caps.json)' % (Z.CHUNK_MAX + 1, Z.WORD_MIN, Z.WORD_MAX),
    'own-row word pieces estimated as chars / ratio per source (web rows use the exact GPT-2 token_count)',
    'english / teach records become ONE row each (panel alternating source_text / paraphrase), not two',
]


def own_pieces(row, src='rows'):
    return (len(row['prompt']) + 1 + len(row['answer'])) / OWN_CHARS_PER_PIECE[src]


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def _bad(row, max_ans, stat):
    s = [row['prompt'], row['answer']]
    if not all(c in ASCII for x in s for c in x):
        stat['dropped_non_ascii'] += 1
    elif len(row['prompt']) > HYGIENE_PROMPT:
        stat['dropped_prompt'] += 1
    elif not row['answer'].strip():
        stat['dropped_empty'] += 1
    elif len(row['answer']) > max_ans:
        stat['dropped_answer'] += 1
    else:
        return False
    return True


def _newstat(**kw):
    return dict(read=0, taken=0, pieces=0.0, dropped_non_ascii=0, dropped_prompt=0, dropped_empty=0, dropped_answer=0, dropped_dup=0, **kw)


def qa_row(rec, src):
    """An own72 english / teach record -> one standard row (see module doc). Panel by record position parity."""
    rec = EN.clean_example(dict(rec, questions=[dict(question=rec['question'], canonical_answer=rec['canonical_answer'],
                                                     accepted_answers=rec.get('accepted_answers', []), type=rec.get('type', ''))]))
    q = rec['questions'][0]
    panel = 'source_text' if rec['pos'] % 2 == 0 else 'paraphrase'
    prompt, can = rec[panel] + ' ' + q['question'], q['canonical_answer']
    acc = list(dict.fromkeys([can] + list(q.get('accepted_answers', []))))
    return dict(id=rec['id'] + '-' + ('s' if panel == 'source_text' else 'p'), prompt=prompt, answer=EN.taught_answer(prompt, can, acc), accepted=acc,
                family=rec.get('kind', src), level=0, stage=0, variant=q.get('type', ''), steps=[])


def own72_iter(dirpath, own_rung, max_ans, ids, stats, cap_pieces=None):
    """Yield (json line, pieces, src) for the rung's own72 rows in pos order; `stats` = {src: stat dict} is filled in as it runs."""
    def one(src):
        with open(os.path.join(dirpath, src + '.jsonl')) as f:
            for line in f:
                r = json.loads(line)
                if r['rung'] <= own_rung:
                    yield r['pos'], src, r
    for pos, src, r in heapq.merge(*(one(s) for s in ('skills', 'english', 'teach')), key=lambda t: t[0]):
        st = stats[src]
        st['read'] += 1
        row = dict(r, id=r['id']) if src == 'skills' else qa_row(r, src)
        if src == 'skills':
            row = {k: row[k] for k in ('id', 'prompt', 'answer', 'accepted', 'family', 'level', 'stage', 'variant', 'steps')}
        if _bad(row, max_ans, st):
            continue
        if row['id'] in ids:
            st['dropped_dup'] += 1
            continue
        p = own_pieces(row, src)
        if cap_pieces is not None and sum(s_['pieces'] for s_ in stats.values()) + p > cap_pieces:
            return
        ids.add(row['id'])
        st['taken'] += 1
        st['pieces'] += p
        yield json.dumps(row) + '\n', p, src


def own_files_iter(specs, own_total, max_ans, ids, stats):
    """--own PATH[:WEIGHT]: standard-format files, each from the top until its share of own_total pieces."""
    srcs = []
    for s in specs:
        path, _, w = s.rpartition(':') if ':' in s and s.rpartition(':')[2].replace('.', '', 1).isdigit() else (s, '', '1')
        srcs.append((path, float(w)))
    wsum = sum(w for _, w in srcs)
    for path, w in srcs:
        key = os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path)
        st = stats.setdefault(key, _newstat(weight=w, budget_pieces=own_total * w / wsum))
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                st['read'] += 1
                if _bad(r, max_ans, st):
                    continue
                if r['id'] in ids:
                    st['dropped_dup'] += 1
                    continue
                p = own_pieces(r)
                if st['pieces'] + p > st['budget_pieces']:
                    break
                ids.add(r['id'])
                st['taken'] += 1
                st['pieces'] += p
                yield line if line.endswith('\n') else line + '\n', p, key


def schedule(rung, mean_row_pieces, n_rows, scale=1.0):
    """steps = max(UPDATE_FLOOR, ceil(seen / (BATCH x mean row pieces))). reuse refused only when the 20-per-parameter count (not the floor) rules."""
    seen = RUNGS[rung]['seen'] * scale
    by_seen = int(math.ceil(seen / (BATCH * mean_row_pieces)))
    floor = UPDATE_FLOOR if scale == 1.0 else 0
    steps = max(floor, by_seen)
    draws = steps * BATCH
    reuse = math.ceil(draws / max(n_rows, 1))
    floor_rules = floor > by_seen
    return dict(seen_pieces_target=seen, steps_by_seen=by_seen, update_floor=floor, steps=steps, floor_rules=floor_rules, row_draws=draws, passes=round(draws / max(n_rows, 1), 3),
                max_row_draws=reuse, ok_reuse=floor_rules or reuse <= MAX_REUSE,
                seen_pieces_actual=round(steps * BATCH * mean_row_pieces))


def load_long(path):
    """data_pool/cloze_long.py (the data thread's long-chunk builder, big-run REPLAN 10-09) by path: `path` is that file or the directory holding it."""
    import importlib.util
    f = os.path.join(path, 'cloze_long.py') if os.path.isdir(path) else path
    spec = importlib.util.spec_from_file_location('cloze_long', f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.PATH, m.SHA256 = f, sha256_file(f)
    return m


def web_rows(slice_path, seed, budget, stats, cloze_long=None):
    """The web fill-in rows of a slice, in document order, until `budget` word pieces. cloze_long = path of cloze_long.py (or its folder): chunks get their own
    ceilings (280 / 700 / 1300 / 2000 letters, 80 / 7 / 7 / 6% of pieces); otherwise the 8a rows (<= 280 letters). Rows carry '_np'."""
    if cloze_long:
        return load_long(cloze_long).cloze_rows_mixed(Z, Z.read_slice(slice_path), seed, budget, stats)
    return Z.cloze_rows(Z.read_slice(slice_path), seed, budget, stats)


def build(a):
    global HYGIENE_PROMPT
    HYGIENE_PROMPT = 2000 if getattr(a, 'cloze_long', None) else 400       # B3 trains on inputs up to 2,000 letters: an own row of 401-2,000 letters is not a broken row
    R = RUNGS[a.rung]
    pool = R['pool'] * a.scale
    own_total, web_total = pool * OWN_SHARE, pool * WEB_SHARE
    os.makedirs(a.out, exist_ok=True)
    ids, stats = set(), {}
    if a.own72:
        stats.update({s: _newstat() for s in ('skills', 'english', 'teach')})
        it = own72_iter(a.own72, R['own_rung'], a.max_ans, ids, stats, cap_pieces=own_total if a.scale != 1.0 else None)   # the cap is for dry runs only: at scale 1 the rung tag defines the prefix
    else:
        it = own_files_iter(a.own, own_total, a.max_ans, ids, stats)
    tr = os.path.join(a.out, 'train.jsonl')
    n_rows, own_p, by_src = 0, 0.0, {}
    with open(tr, 'w') as f:
        for line, p, src in it:
            f.write(line)
            n_rows += 1
            own_p += p
        own_rows = n_rows
        web_budget = min(web_total, own_p * WEB_SHARE / OWN_SHARE) if a.keep_mix else web_total
        zs = Z.Stats()
        for r in web_rows(a.web, a.seed, web_budget, zs, getattr(a, 'cloze_long', None)):
            assert r['id'] not in ids, r['id']
            ids.add(r['id'])
            r.pop('_np')
            f.write(json.dumps(r) + '\n')
    web = zs.report()
    long_ = getattr(a, 'cloze_long', None)
    if long_:
        CL = load_long(long_)
        web['cloze_long'] = dict(file=os.path.basename(CL.PATH), sha256=CL.SHA256, mix=CL.MIX, buckets=getattr(zs, 'extra', {}))
        DEVIATIONS[0] = 'cloze prompts up to %d chars incl. the blank (long-chunk mix %s, data_pool/cloze_long.py), blanked word %d..%d letters; model caps sized from the data (caps.json)' % (
            max(c for c, _ in CL.MIX), json.dumps(CL.MIX), Z.WORD_MIN, Z.WORD_MAX)
    n_rows += web['rows']
    pieces = own_p + web['pieces']
    web_short = max(0.0, web_budget - web['pieces'])
    short = {}
    if own_p < 0.995 * own_total:
        short['own'] = own_total - own_p
    if web_short > 0.005 * web_budget:
        short['web'] = web_short
    if short and not (a.allow_short or a.keep_mix):
        sys.exit('SHORTFALL (pieces): %s. The mix would not be the spec\'s; fix the sources or pass --keep-mix / --allow-short.' % json.dumps({k: round(v) for k, v in short.items()}))
    if web_short > MAX_WEB_SHORT * web_budget:
        sys.exit('the web slice ran out %d pieces short of the %d the mix needs (more than %.0f%%): cut a bigger slice (data_pool/web_slice.py)' % (web_short, web_budget, 100 * MAX_WEB_SHORT))
    if web_short > 0.005 * web_budget:      # a few percent short is accepted and disclosed: the slice budgets count tokens, the cloze rows use 95.5% of them (chunks under 60 letters etc. are not used)
        DEVIATIONS.append('web fill-in rows %.1f%% short of the budget (%d of %d pieces): web share %.1f%% instead of %d%%' % (100 * web_short / web_budget, web_short, web_budget, 100 * web['pieces'] / max(pieces, 1), 100 * WEB_SHARE))
    sched = schedule(a.rung, pieces / max(n_rows, 1), n_rows, a.scale)
    if not sched['ok_reuse']:
        sys.exit('a row would be drawn %d times (> %d): %s' % (sched['max_row_draws'], MAX_REUSE, json.dumps(sched)))
    if a.dev:
        dd = os.path.join(a.out, 'dev')
        if os.path.exists(dd):
            shutil.rmtree(dd)
        shutil.copytree(a.dev, dd)
    man = dict(rung=a.rung, seed=a.seed, scale=a.scale, trained_params_target=R['target'], pool_pieces_spec=pool, seen_pieces_target=R['seen'] * a.scale,
               own_share_spec=OWN_SHARE, web_share_spec=WEB_SHARE, keep_mix=bool(a.keep_mix), rows=n_rows, pieces=pieces,
               own=dict(rows=own_rows, pieces=own_p, share=own_p / max(pieces, 1), spec_pieces=own_total, sources=stats, own72=bool(a.own72), own_rung=R['own_rung']),
               web=dict(web, share=web['pieces'] / max(pieces, 1), budget_pieces=web_budget, spec_pieces=web_total, slice=os.path.basename(a.web)),
               shortfalls=short, max_ans=a.max_ans, schedule=sched, train_sha256=sha256_file(tr), train_bytes=os.path.getsize(tr), deviations=DEVIATIONS,
               piece_method='web: GPT-2 token_count of the document; own: chars / per-source ratio (%s)' % json.dumps(OWN_CHARS_PER_PIECE))
    if a.overlap_index:
        man['own_overlap'] = own_overlap(tr, a.overlap_index, a.data_pool, n_own=own_rows)
    json.dump(man, open(os.path.join(a.out, 'MANIFEST.json'), 'w'), indent=1)
    print(json.dumps(dict(rows=n_rows, pieces=round(pieces), own_share=round(own_p / max(pieces, 1), 3), steps=sched['steps'], passes=sched['passes'], floor_rules=sched['floor_rules'],
                          copyable_share=round(web['copyable_share'], 4), shortfalls={k: round(v) for k, v in short.items()})))
    return man


def own_overlap(train, index, data_pool, n_own, sample=100_000):
    """REPORT ONLY (spec section 4: generator rows rely on their hold-out splits): share of own rows whose prompt shares a 13-gram window with any
    panel in the overlap index (data_pool/overlap13.py). First `sample` own rows, file order."""
    sys.path.insert(0, data_pool)
    import overlap13 as O
    by_len, _ = O.load_index(index)
    hit = tot = 0
    with open(train) as f:
        for i, line in enumerate(f):
            if i >= min(n_own, sample):
                break
            tot += 1
            hit += bool(O.doc_hits(json.loads(line)['prompt'], by_len))
    return dict(checked=tot, hits=hit, share=hit / max(tot, 1), gated=False)


def question_only(pdir, out):
    """OUT = a data dir with only the question rows of pdir (every row that is not a cloze row), in file order, and pdir's dev splits. Mark 5's public model
    trains on these (it was pretrained on web text, so the fill-in rows are left out). Returns OUT."""
    os.makedirs(out, exist_ok=True)
    n = 0
    with open(os.path.join(pdir, 'train.jsonl')) as f, open(os.path.join(out, 'train.jsonl'), 'w') as g:
        for line in f:
            if not Z.is_cloze(json.loads(line)):
                g.write(line)
                n += 1
    dd = os.path.join(out, 'dev')
    if os.path.exists(dd):
        shutil.rmtree(dd)
    shutil.copytree(os.path.join(pdir, 'dev'), dd)
    json.dump(dict(question_rows=n, from_train_sha256=json.load(open(os.path.join(pdir, 'MANIFEST.json')))['train_sha256']), open(os.path.join(out, 'QUESTIONS.json'), 'w'))
    return out


def nested(small, big):
    """True iff every line of small/train.jsonl occurs in big/train.jsonl (own rows are pos-order prefixes, cloze rows are keyed by document)."""
    seen = set()
    with open(os.path.join(big, 'train.jsonl')) as f:
        for line in f:
            seen.add(hashlib.blake2b(line.encode(), digest_size=12).digest())
    miss = tot = 0
    with open(os.path.join(small, 'train.jsonl')) as f:
        for line in f:
            tot += 1
            miss += hashlib.blake2b(line.encode(), digest_size=12).digest() not in seen
    return dict(rows=tot, missing=miss, nested=miss == 0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--rung', choices=list(RUNGS), required=True)
    b.add_argument('--seed', type=int, required=True)
    b.add_argument('--out', required=True)
    g = b.add_mutually_exclusive_group(required=True)
    g.add_argument('--own72', help='data_pool own72 dir (skills.jsonl english.jsonl teach.jsonl with rung and pos)')
    g.add_argument('--own', nargs='+', help='PATH[:WEIGHT] standard-format row files, file order')
    b.add_argument('--web', required=True, help='web slice jsonl from data_pool/web_slice.py (slice_rung10.jsonl for 3M / 10M, slice_rung30.jsonl for 30M)')
    b.add_argument('--dev', help='dir with the dev splits (pooled-5), copied to OUT/dev')
    b.add_argument('--max-ans', type=int, default=HYGIENE_ANS, help='data hygiene limit on answer chars (rows over it are dropped and counted); NOT a model cap')
    b.add_argument('--keep-mix', action='store_true', default=True)
    b.add_argument('--no-keep-mix', dest='keep_mix', action='store_false')
    b.add_argument('--allow-short', action='store_true')
    b.add_argument('--scale', type=float, default=1.0, help='DRY RUNS ONLY: multiply the pool and seen budgets (recorded in the manifest)')
    b.add_argument('--overlap-index')
    b.add_argument('--cloze-long', help='data_pool/cloze_long.py (or its folder): web rows with chunks up to 2,000 letters (B3); default the 8a rows (<= 280)')
    b.add_argument('--data-pool', default='data_pool')
    n = sub.add_parser('nested')
    n.add_argument('small')
    n.add_argument('big')
    a = ap.parse_args(argv)
    if a.cmd == 'build':
        build(a)
    else:
        r = nested(a.small, a.big)
        print(json.dumps(r))
        sys.exit(0 if r['nested'] else 1)


if __name__ == '__main__':
    main()
