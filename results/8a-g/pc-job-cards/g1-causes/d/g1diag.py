"""D: free read-only measurements on G1's saved final B2 weights (3M s400 and 10M s400; same cfg except blocks 2 vs 8). Never trains, never writes
outside --out (and --sample-only's OUTFILE). Roadmap file reviews/G1-OTHER-CAUSES-RANKED-2026-10-12.md section 3 "D"; its three decision rules are
sealed and printed with their numbers at the end.
  1 error ledger (3 candidate outputs per row, chosen mode, hits) on the 6 dev splits   2 oracle-mode rescoring (a row counts if ANY candidate hits)
  3 10M block knockout on in_dist   4 per-term teacher-forced train loss (web vs skill rows)   5 gold log-likelihood per family on the 5 dev splits
  python g1diag.py --src SRC --data POOL --ckpt3 C3 --ckpt10 C10 --out OUT [--train FILE] [--result3 R3 --result10 R10] [--device auto]
  python g1diag.py --train POOL/train.jsonl --sample-only SAMPLE.jsonl        (4,000-row train sample, pure python)
  python g1diag.py --src SRC --selftest                                         (CPU, no checkpoints, no EmbeddingGemma)
EmbeddingGemma is frozen and the same for both models: ONE FrozenEG instance is shared, its encode() is wrapped with a one-batch cache."""
import argparse, collections, contextlib, json, os, random, sys, tempfile, time

B13 = ['arith_bare', 'backward_solve', 'chain_ops', 'story_addsub', 'story_chain3', 'chain_story2', 'var_chain', 'div_exact', 'table_calc',
       'distance_units', 'compare_numbers', 'state_update', 'percent_rate']
POOL5 = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
SPLITS = POOL5 + ['family']
MODE_NAMES = ['NUM', 'WORD', 'GEN']
TERMS = ['total', 'prog', 'mode', 'ans', 'word', 'gen']
EXTRA_TERMS = ['op_acc', 'copy_share']          # batch means, row-weighted: approximate
ACTIONS = {'R1': 'routing masks the thinker (cause 6) -> marginal mode loss test next',
           'R2': 'idle depth (cause 7 or 2) -> short lr test (5e-4 vs 1e-3)',
           'R3': 'memorisation (cause 2) confirmed'}
DEV_FLAT_GAIN = 3.0     # R3 gives no cutoff for "dev flat": D reads it as D's own recomputed normal pooled-5 gain < 3.0 (the R1 bar); numbers are printed


def say(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- the train sample (pure python)
def reservoir(path, k=2000, seed=0, keep=('id', 'prompt', 'answer', 'accepted', 'family', 'level', 'stage', 'variant', 'steps')):
    """One streamed pass, reservoir sampling (algorithm R) of k web rows (family 'cloze') and k other rows, random.Random(seed). -> (web, skill, seen)."""
    rng = random.Random(seed)
    res, seen = {'web': [], 'skill': []}, {'web': 0, 'skill': 0}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            g = 'web' if r.get('family') == 'cloze' else 'skill'
            r = {x: r[x] for x in keep if x in r}
            n = seen[g]
            seen[g] += 1
            if n < k:
                res[g].append(r)
            else:
                j = rng.randint(0, n)
                if j < k:
                    res[g][j] = r
    return res['web'], res['skill'], seen


def write_sample(train, outfile, k, seed=0):
    web, skill, seen = reservoir(train, k, seed)
    d = os.path.dirname(os.path.abspath(outfile))
    os.makedirs(d, exist_ok=True)
    with open(outfile, 'w', encoding='utf-8', newline='\n') as f:
        for r in web + skill:
            f.write(json.dumps(r) + '\n')
    say(f'sample: {len(web)} web (of {seen["web"]}) + {len(skill)} skill (of {seen["skill"]}) rows -> {outfile}')
    return web, skill, seen


# ---------------------------------------------------------------- helpers (need torch / custom_io)
def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


def pct(c, n):
    return 100.0 * c / n if n else float('nan')


def setup(args):
    """sys.path, torch, caps (BEFORE any model code), N_REG check. -> namespace of the modules."""
    sys.path.insert(0, os.path.abspath(args.src))
    import torch
    from custom_io.g8a import caps as C
    caps = C.apply(json.load(open(os.path.join(args.data, 'caps.json'), encoding='utf-8')))
    from custom_io.models import ledger as L, progparse as pp
    assert L.N_REG == 36, f'N_REG {L.N_REG}: the caps overlay (36-register fix) is not in {args.src}'
    say('N_REG 36')
    ns = argparse.Namespace(torch=torch, caps=caps, L=L, pp=pp)
    return ns


def install_eg_cache(models):
    """ONE FrozenEG for every model; its encode() keeps only the current batch (key = (tuple(prompts), T, device))."""
    ms = list(models.values())
    egs = [m._eg for m in ms if getattr(m, '_eg', None)]
    if not egs:
        return 0
    for m in ms:
        if getattr(m, '_eg', None):
            m._eg = egs[0]
    eg = egs[0][0]
    orig, box = eg.encode, {}

    def encode(prompts, T, device, chars=True):
        key = (tuple(prompts), T, str(device))
        hit = box.get('last')
        if hit is not None and hit[0] == key and (hit[1][0] is not None or not chars):
            return hit[1]
        out = orig(prompts, T, device, chars)
        box['last'] = (key, out)
        return out
    eg.encode = encode
    return 1


def main_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', default='.', help='folder containing custom_io (inserted first on sys.path)')
    ap.add_argument('--data', help='pool dir with dev/, charvocab.json, caps.json')
    ap.add_argument('--ckpt3')
    ap.add_argument('--ckpt10')
    ap.add_argument('--train', help='jsonl for the train-row sample (default DATA/train.jsonl; may be a small pre-made sample file)')
    ap.add_argument('--result3')
    ap.add_argument('--result10')
    ap.add_argument('--out')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--eval-batch', type=int, default=128)
    ap.add_argument('--loss-batch', type=int, default=64)
    ap.add_argument('--max-rows', type=int, help='debug: rows per dev split and per train group')
    ap.add_argument('--sample-k', type=int, default=2000, help='train rows per group (web / skill)')
    ap.add_argument('--sample-only', metavar='OUTFILE')
    ap.add_argument('--eg', help='EmbeddingGemma folder (sets $CUSTOM_IO_EG2)')
    ap.add_argument('--selftest', action='store_true')
    return ap.parse_args(argv)


# ---------------------------------------------------------------- the pipeline
def pipeline(args, ns=None):
    t00 = time.time()
    ns = ns or setup(args)
    torch, L, pp = ns.torch, ns.L, ns.pp
    import torch.nn as nn
    from custom_io.data import CharVocab, Dataset, collate, to_device, word_spans
    from custom_io.evalx import _dev_rows, is_hit
    from custom_io.models import build
    if args.eg:
        os.environ['CUSTOM_IO_EG2'] = args.eg
    out = args.out
    os.makedirs(out, exist_ok=True)
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else 'cpu' if args.device == 'auto' else args.device)
    amp = (lambda: torch.autocast(device.type, dtype=torch.bfloat16)) if device.type == 'cuda' else contextlib.nullcontext
    say(f'device {device}; autocast {"bf16" if device.type == "cuda" else "off (fp32)"}')
    vocab = CharVocab.load(os.path.join(args.data, 'charvocab.json'))
    models, ckpts = {}, {'3M': args.ckpt3, '10M': args.ckpt10}
    for tag, path in ckpts.items():
        try:
            ck = torch.load(path, map_location='cpu', weights_only=False)
        except TypeError:
            ck = torch.load(path, map_location='cpu')
        assert ck['name'] == 'ledger', ck['name']
        assert ck['chars'] == vocab.chars, f'{tag}: checkpoint chars differ from charvocab.json'
        m = build('ledger', vocab, **ck['cfg'])
        m.load_state_dict(ck['model'])                  # strict
        models[tag] = m.to(device).eval()
        say(f'{tag}: cfg {ck["cfg"]} step {ck.get("step")} trained params {m.n_params():,}')
    install_eg_cache(models)
    tags = list(models)
    m10 = models['10M']
    nb = len(m10.core)
    # in-run check that G1's 36-slot caps fix is in force: the register tokens of a run() output
    b0 = to_device(collate([Dataset(_dev_rows(args.data, 'in_dist', 4), vocab, strict=False)[i] for i in range(4)]), device)
    with torch.no_grad(), amp():
        o0 = m10.run(b0)
    shape = list(o0['R'].shape)
    assert shape[1] == 36 and shape[2] == m10.d, f'register tokens {shape}, expected [B, 36, {m10.d}]'
    say(f'register tokens in a run() output: [B, {shape[1]}, {shape[2]}] (B={shape[0]})')
    pp._CACHE.clear()
    report = dict(meta=dict(device=str(device), amp='bf16' if device.type == 'cuda' else 'fp32', n_reg=L.N_REG, register_shape=['B', shape[1], shape[2]],
                            blocks={t: len(m.core) for t, m in models.items()}, max_rows=args.max_rows, eval_batch=args.eval_batch,
                            trained_params={t: m.n_params() for t, m in models.items()}, caps=ns.caps))

    # ---- 1 + 3: per-row ledger on the 6 dev splits (evalx.eval_all batching), candidates, self-check, 10M knockout on in_dist
    @torch.no_grad()
    def candidates(m, b):
        """The three outputs talk() could print and the one it does, mirrored line for line. -> dict of lists per row."""
        st = m.state(b)
        R, vals, valid, lmode, lans, lword = st
        if m.copy:
            X, xm = m.read(b, talker=True)
            ids = m.gen_copy(R, X, xm, b['prompt_ids'], False)[0].argmax(-1)
        else:
            ids = m.readout(R).argmax(-1)
        gen = [m.vocab.decode(r)[::-1] for r in ids.tolist()]
        mode, k, w = lmode.argmax(-1).tolist(), lans.argmax(-1).tolist(), lword.argmax(-1).tolist()
        sps = [word_spans(r['prompt'])[:L.W_MAX] for r in b['rows']]
        vals, valid = vals.tolist(), valid.tolist()
        res = dict(num=[], word=[], gen=gen, chosen=[], cmode=[], raw=mode, ws=[], wsres=[])
        res['talk'] = m.talk(st, b, return_modes=True)      # the model's own talk() on the same state: the mirror below must equal it
        for i, row in enumerate(b['rows']):
            num = str(vals[i][k[i]]) if valid[i][k[i]] else None
            word = row['prompt'][sps[i][w[i]][0]:sps[i][w[i]][1]] if w[i] < len(sps[i]) else None
            if mode[i] == 0 and num is not None:
                ch, cm = num, 0
            elif mode[i] == 1 and word is not None:
                ch, cm = word, 1
            else:
                ch, cm = gen[i], 2
            a = row['answer']
            isint = a.lstrip('-').isdigit() and str(int(a)) == a
            res['ws'].append(bool(isint and any(v_ and x == int(a) for x, v_ in zip(vals[i], valid[i]))))
            res['wsres'].append(bool(isint and any(v_ and x == int(a) for x, v_ in zip(vals[i][L.R0:], valid[i][L.R0:]))))
            res['num'].append(num)
            res['word'].append(word)
            res['chosen'].append(ch)
            res['cmode'].append(cm)
        return res

    @contextlib.contextmanager
    def without_blocks(m, drop):
        """Run with the controller blocks in `drop` removed in EVERY round. run() builds each block's K/V and zips self.core per call, so this is safe."""
        full = m.core
        m.core = nn.ModuleList([b for i, b in enumerate(full) if i not in drop])
        try:
            yield
        finally:
            m.core = full

    kos = [(f'skip_{i}', {i}) for i in range(nb)]
    if nb > 2:
        kos.append((f'skip_2-{nb - 1}', set(range(2, nb))))     # blocks 3-8 together (1-based) = indices 2..7
    ko_hits = collections.Counter()
    recs, mism, mism_mode, nrows = [], collections.Counter(), collections.Counter(), collections.Counter()
    t1 = time.time()
    for split in SPLITS:
        pp._CACHE.clear()
        rows = _dev_rows(args.data, split, args.max_rows)
        ds = Dataset(rows, vocab, strict=False)
        order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
        per = [None] * len(rows)
        for s in range(0, len(order), args.eval_batch):
            ids = order[s:s + args.eval_batch]
            b = to_device(collate([ds[i] for i in ids]), device)
            res = {}
            for tag, m in models.items():
                with amp():
                    c = candidates(m, b)
                    gen = m.generate(b)
                mism[tag] += sum(x != y for x, y in zip(gen, c['chosen']))
                mism_mode[tag] += sum(x != y for x, y in zip(c['talk'][1], c['cmode'])) + sum(x != y for x, y in zip(c['talk'][0], c['chosen']))
                res[tag] = c
            if split == 'in_dist':
                with torch.no_grad():
                    for name, drop in kos:
                        with without_blocks(m10, drop), amp():
                            outs = m10.generate(b)
                        ko_hits[name] += sum(is_hit(p, r) for p, r in zip(outs, b['rows']))
            for j, i in enumerate(ids):
                r = rows[i]
                t = pp.row_targets(r)
                rec = dict(id=r['id'], split=split, family=r['family'], gold_mode=t['mode'])
                for tag in tags:
                    c = res[tag]
                    hits = [int(p is not None and is_hit(p, r)) for p in (c['num'][j], c['word'][j], c['gen'][j])]
                    rec['chosen' + tag] = c['cmode'][j]
                    rec['raw_mode' + tag] = c['raw'][j]
                    rec['hit' + tag] = int(is_hit(c['chosen'][j], r))
                    rec['cand_hits' + tag] = hits
                    rec['cand_avail' + tag] = [int(c['num'][j] is not None), int(c['word'][j] is not None), 1]
                    rec['ws_gold' + tag] = int(c['ws'][j])
                    rec['ws_gold_result_slots' + tag] = int(c['wsres'][j])
                per[i] = rec
        recs += per
        nrows[split] = len(rows)
        say(f'  dev {split}: {len(rows)} rows, {time.time() - t1:.0f}s; mismatches vs generate: ' + ', '.join(f'{t} {mism[t]}' for t in tags))
    # NB the per-row records use short tag keys; JSONL rows use the exact names asked for
    with open(os.path.join(out, 'rows.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
        for r in recs:
            f.write(json.dumps(r) + '\n')
    report['selfcheck'] = dict(rows=sum(nrows.values()), mismatches_chosen_vs_generate={t: mism[t] for t in tags},
                               mismatches_mirror_vs_talk_output_and_mode={t: mism_mode[t] for t in tags}, total_mismatches=sum(mism.values()))
    say('self-check: chosen output vs model.generate(batch):', report['selfcheck'])

    # tables
    def sel(split=None, fams=None, pool=None):
        for r in recs:
            if split is not None and r['split'] != split:
                continue
            if pool is not None and r['split'] not in pool:
                continue
            if fams is not None and r['family'] not in fams:
                continue
            yield r

    fam_all = sorted({r['family'] for r in recs})
    B13s = [f for f in B13 if f in fam_all]
    B21s = [f for f in fam_all if f not in B13]
    blocks = {'pooled5': None, 'block13': set(B13), 'block21': set(B13)}

    def score(rs, tag):
        rs = list(rs)
        n = len(rs)
        normal = sum(r['hit' + tag] for r in rs)
        oracle = sum(any(r['cand_hits' + tag]) for r in rs)
        return dict(n=n, correct=normal, exact=pct(normal, n), oracle_correct=oracle, oracle_exact=pct(oracle, n))

    def block_rows(name, pool):
        rs = list(sel(pool=pool))
        if name == 'block13':
            return [r for r in rs if r['family'] in B13]
        if name == 'block21':
            return [r for r in rs if r['family'] not in B13]
        return rs
    orc = {}
    for name in ('pooled5', 'block13', 'block21'):
        orc[name] = {t: score(block_rows(name, POOL5), t) for t in tags}
        a, b_ = orc[name]['3M'], orc[name]['10M']
        orc[name]['gain'] = dict(normal=b_['exact'] - a['exact'], oracle=b_['oracle_exact'] - a['oracle_exact'],
                                 error_ratio_normal=(b_['n'] - b_['correct']) / max(a['n'] - a['correct'], 1),
                                 error_ratio_oracle=(b_['n'] - b_['oracle_correct']) / max(a['n'] - a['oracle_correct'], 1))
    orc['by_split'] = {s: {t: score(sel(split=s), t) for t in tags} for s in SPLITS}
    orc['block_families'] = dict(block13=B13s, block21=B21s, block13_missing=[f for f in B13 if f not in fam_all])
    orc['by_split_blocks'] = {s: {nm: {t: score([r for r in block_rows(nm, [s])], t) for t in tags} for nm in ('block13', 'block21')} for s in POOL5}
    report['oracle'] = orc

    # comparison with G1's RESULT.json (D's normal pooled-5 vs G1's)
    cmp_ = {}
    for tag, path in (('3M', args.result3), ('10M', args.result10)):
        if not path:
            continue
        fe = json.load(open(path, encoding='utf-8'))['final_eval']
        g_c, g_n = sum(fe[s]['correct'] for s in POOL5), sum(fe[s]['n'] for s in POOL5)
        d = orc['pooled5'][tag]
        cmp_[tag] = dict(g1_pooled5=pct(g_c, g_n), g1_correct=g_c, g1_n=g_n, d_pooled5=d['exact'], d_correct=d['correct'], d_n=d['n'],
                         diff_points=d['exact'] - pct(g_c, g_n), diff_rows=d['correct'] - g_c,
                         by_split={s: dict(g1=fe[s]['correct'], d=orc['by_split'][s][tag]['correct'], n=fe[s]['n']) for s in SPLITS if s in fe},
                         g1_in_dist=fe['in_dist']['exact'])
    if len(cmp_) == 2:
        cmp_['g1_gain'] = cmp_['10M']['g1_pooled5'] - cmp_['3M']['g1_pooled5']
    report['compare_g1'] = cmp_
    say('pooled-5 normal / oracle:', {t: (round(orc['pooled5'][t]['exact'], 2), round(orc['pooled5'][t]['oracle_exact'], 2)) for t in tags}, 'gain', orc['pooled5']['gain'])

    # error ledger tables
    led = {}
    for tag in tags:
        wrong = collections.Counter()
        for r in recs:
            if not r['hit' + tag]:
                wrong[f"{r['split']}|{r['family']}|{MODE_NAMES[r['chosen' + tag]]}|gold {MODE_NAMES[r['gold_mode']]}"] += 1
        reach = collections.Counter()
        for r in recs:
            if r['split'] in POOL5 and not r['hit' + tag]:
                reach[f"gold {MODE_NAMES[r['gold_mode']]}|chosen {MODE_NAMES[r['chosen' + tag]]}|workspace holds gold {bool(r['ws_gold' + tag])}"] += 1
        led[tag] = dict(wrong_by_split_family_chosen_gold=dict(sorted(wrong.items())), wrong_pooled5_gold_chosen_workspace=dict(sorted(reach.items())),
                        wrong_per_split={s: sum(1 for r in sel(split=s) if not r['hit' + tag]) for s in SPLITS})
    fb = collections.defaultdict(lambda: dict(fixed=0, broken=0, both_right=0, both_wrong=0))
    trans = collections.Counter()
    for r in recs:
        k = f"{r['split']}|{r['family']}"
        f_, br = (not r['hit3M']) and r['hit10M'], r['hit3M'] and (not r['hit10M'])
        fb[k]['fixed'] += int(f_)
        fb[k]['broken'] += int(br)
        fb[k]['both_right'] += int(r['hit3M'] and r['hit10M'])
        fb[k]['both_wrong'] += int(not r['hit3M'] and not r['hit10M'])
        if f_ or br:
            trans[f"{'fixed' if f_ else 'broken'}|{r['split']}|{MODE_NAMES[r['chosen3M']]}->{MODE_NAMES[r['chosen10M']]}"] += 1
    led['fixed_broken_3M_to_10M'] = dict(by_split_family=dict(sorted(fb.items())),
                                         by_split={s: {k: sum(v[k] for kk, v in fb.items() if kk.startswith(s + '|')) for k in ('fixed', 'broken')} for s in SPLITS},
                                         pooled5={k: sum(v[k] for kk, v in fb.items() if kk.split('|')[0] in POOL5) for k in ('fixed', 'broken', 'both_wrong')},
                                         mode_transitions=dict(sorted(trans.items())))
    report['ledger'] = led

    # 3: knockout
    intact = pct(sum(r['hit10M'] for r in sel(split='in_dist')), nrows['in_dist'])
    ko = dict(intact_in_dist=intact, n=nrows['in_dist'], blocks=nb, note='every round; model.core replaced by a ModuleList without the blocks (run() builds K/V and zips core per call), restored after',
              runs={name: dict(blocks_removed=sorted(drop), exact=pct(ko_hits[name], nrows['in_dist']), cost=intact - pct(ko_hits[name], nrows['in_dist'])) for name, drop in kos})
    report['knockout'] = ko
    say('knockout (in_dist exact, cost vs intact %.2f):' % intact, {k: (round(v['exact'], 2), round(v['cost'], 2)) for k, v in ko['runs'].items()})

    # ---- 4 + 5: teacher-forced loss
    def tf_losses(groups):
        """groups: {name: [rows lists, each from one cache scope]} -> {name: {tag: {term: row-weighted mean}, n}}."""
        acc = {g: {t: collections.Counter() for t in tags} for g in groups}
        cnt = collections.Counter()
        for g, chunks in groups.items():
            for rows in chunks:
                order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
                ds = Dataset(rows, vocab, strict=False)
                for s in range(0, len(order), args.loss_batch):
                    ids = order[s:s + args.loss_batch]
                    b = to_device(collate([ds[i] for i in ids]), device)
                    for tag, m in models.items():
                        with torch.no_grad(), amp():
                            tot, aux = m.loss(b)
                        n = len(ids)
                        acc[g][tag]['total'] += float(tot) * n
                        for k, v in aux.items():
                            acc[g][tag][k] += float(v) * n
                    cnt[g] += len(ids)
        return {g: dict(n=cnt[g], **{t: {k: v / max(cnt[g], 1) for k, v in acc[g][t].items()} for t in tags}) for g in groups}
    t2 = time.time()
    tp = args.train or os.path.join(args.data, 'train.jsonl')
    web, skill, seen = reservoir(tp, args.sample_k, 0)
    if args.max_rows:
        web, skill = web[:args.max_rows], skill[:args.max_rows]
    with open(os.path.join(out, 'train_sample.jsonl'), 'w', encoding='utf-8', newline='\n') as f:
        for r in web + skill:
            f.write(json.dumps(r) + '\n')
    say(f'train sample from {tp}: {len(web)} web (of {seen["web"]}), {len(skill)} skill (of {seen["skill"]})')
    pp._CACHE.clear()
    trl = tf_losses({'web': [web], 'skill': [skill]})
    pp._CACHE.clear()
    report['train_loss'] = dict(source=tp, seen=seen, k=args.sample_k, groups=trl,
                                note='row-weighted mean of model.loss() terms on group-only batches of %d, teacher forced, no_grad; op_acc / copy_share are batch means' % args.loss_batch)
    say('train loss (total) web/skill:', {g: {t: round(trl[g][t]['total'], 4) for t in tags} for g in trl}, f'{time.time() - t2:.0f}s')
    dev_groups = collections.defaultdict(list)
    for split in POOL5:
        rows = _dev_rows(args.data, split, args.max_rows)
        by = collections.defaultdict(list)
        for r in rows:
            by[r['family']].append(r)
        for f_, rs in by.items():
            dev_groups[f_].append((split, rs))
    dev_loss = {}
    for split in POOL5:             # id caches are per split (dev ids may repeat across splits)
        pp._CACHE.clear()
        part = tf_losses({f_: [rs for sp, rs in lst if sp == split] for f_, lst in dev_groups.items()})
        for f_, v in part.items():
            if not v['n']:
                continue
            d = dev_loss.setdefault(f_, dict(n=0, **{t: collections.Counter() for t in tags}))
            for t in tags:
                for k, x in v[t].items():
                    d[t][k] += x * v['n']
            d['n'] += v['n']
    for f_, d in dev_loss.items():
        for t in tags:
            d[t] = {k: x / d['n'] for k, x in d[t].items()}
    pooled = {t: {k: sum(d[t][k] * d['n'] for d in dev_loss.values() if k in d[t]) / sum(d['n'] for d in dev_loss.values() if k in d[t]) for k in TERMS} for t in tags}
    report['dev_loss'] = dict(by_family=dict(sorted(dev_loss.items())), pooled5=dict(n=sum(d['n'] for d in dev_loss.values()), **pooled),
                              note='gold log-likelihood = the teacher-forced loss on the 5 dev splits (pooled-5), batches of %d grouped by split x family' % args.loss_batch)
    say(f'dev loss done {time.time() - t2:.0f}s total phase')

    # ---- 6: sealed decision rules
    R = {}
    g = orc['pooled5']['gain']
    R['R1'] = dict(rule='oracle-mode 10M gain >= +3.0 (vs +1.64) -> ' + ACTIONS['R1'], oracle_gain_10M_minus_3M=g['oracle'], normal_gain_D=g['normal'],
                   normal_gain_G1=cmp_.get('g1_gain'), oracle_pooled5={t: orc['pooled5'][t]['oracle_exact'] for t in tags}, threshold=3.0, fires=bool(g['oracle'] >= 3.0))
    c36 = ko['runs'].get(f'skip_2-{nb - 1}')
    R['R2'] = dict(rule='skipping blocks 3-8 at 10M costs < 1.0 point in_dist -> ' + ACTIONS['R2'], blocks=nb, intact_in_dist=intact,
                   skip_3_to_8_in_dist=None if c36 is None else c36['exact'], cost_points=None if c36 is None else c36['cost'], threshold=1.0,
                   fires=bool(c36 is not None and c36['cost'] < 1.0), note=None if c36 is not None else 'model has %d blocks: no blocks 3-8' % nb)
    sk = trl['skill']
    ratio = sk['10M']['total'] / sk['3M']['total'] if sk['3M']['total'] else float('nan')
    R['R3'] = dict(rule='skill-term (non-cloze) teacher-forced train loss at 10M <= half of 3M, with dev flat (G1 gain +1.64) -> ' + ACTIONS['R3'],
                   skill_total_3M=sk['3M']['total'], skill_total_10M=sk['10M']['total'], ratio_10M_over_3M=ratio, half_condition=bool(ratio <= 0.5),
                   skill_terms={t: {k: sk[t][k] for k in TERMS} for t in tags}, dev_gain_G1=1.64, dev_gain_D_recomputed=g['normal'],
                   dev_flat_cutoff=DEV_FLAT_GAIN, dev_flat=bool(g['normal'] < DEV_FLAT_GAIN),
                   dev_flat_note='the sealed rule gives no cutoff for "dev flat"; D reads it as D\'s recomputed normal pooled-5 gain < %.1f; judge from the numbers' % DEV_FLAT_GAIN,
                   fires=bool(ratio <= 0.5 and g['normal'] < DEV_FLAT_GAIN))
    report['rules'] = R
    report['wall_s'] = time.time() - t00
    json.dump(report, open(os.path.join(out, 'g1diag.json'), 'w', encoding='utf-8', newline='\n'), indent=1)
    md = write_md(report, os.path.join(out, 'G1DIAG.md'))
    for k, v in R.items():
        say(f"{k}: {'FIRES' if v['fires'] else 'does not fire'} | {v['rule']} | " + json.dumps({a: b_ for a, b_ in v.items() if a not in ('rule', 'skill_terms')}))
    say(f'wrote g1diag.json, G1DIAG.md, rows.jsonl, train_sample.jsonl into {out} in {report["wall_s"]:.0f}s')
    return report


# ---------------------------------------------------------------- the markdown
def write_md(rep, path):
    f = lambda x, d=2: 'n/a' if x is None else (f'{x:.{d}f}' if isinstance(x, float) else str(x))
    o = []
    A = o.append
    R = rep['rules']
    A('# G1 diagnostic D: free measurements on the saved 3M and 10M B2 weights\n')
    A(f"device {rep['meta']['device']}, {rep['meta']['amp']}, N_REG {rep['meta']['n_reg']}, register tokens {rep['meta']['register_shape']}, blocks {rep['meta']['blocks']}"
      f"{', --max-rows ' + str(rep['meta']['max_rows']) if rep['meta']['max_rows'] else ''}. generate() self-check mismatches: {rep['selfcheck']['total_mismatches']} "
      f"of {rep['selfcheck']['rows']} rows x 2 models.\n")
    A('## Decision rules (sealed before the run)\n')
    r1, r2, r3 = R['R1'], R['R2'], R['R3']
    A(f"- **R1 {'FIRES' if r1['fires'] else 'does not fire'}**: oracle-mode 10M gain {f(r1['oracle_gain_10M_minus_3M'])} (bar >= +3.0; D's normal gain {f(r1['normal_gain_D'])}, G1's {f(r1['normal_gain_G1'])}). "
      f"{'-> ' + ACTIONS['R1'] if r1['fires'] else ''}")
    A(f"- **R2 {'FIRES' if r2['fires'] else 'does not fire'}**: skipping blocks 3-8 at 10M: in_dist {f(r2['skip_3_to_8_in_dist'])} vs intact {f(r2['intact_in_dist'])}, cost {f(r2['cost_points'])} points (bar < 1.0). "
      f"{'-> ' + ACTIONS['R2'] if r2['fires'] else ''}")
    A(f"- **R3 {'FIRES' if r3['fires'] else 'does not fire'}**: skill train loss total 3M {f(r3['skill_total_3M'], 4)}, 10M {f(r3['skill_total_10M'], 4)}, ratio {f(r3['ratio_10M_over_3M'], 3)} "
      f"(bar <= 0.5: {r3['half_condition']}); dev gain G1 +1.64, D recomputed {f(r3['dev_gain_D_recomputed'])} (flat = below {r3['dev_flat_cutoff']}: {r3['dev_flat']}; the sealed rule names no cutoff). "
      f"{'-> ' + ACTIONS['R3'] if r3['fires'] else ''}\n")
    A('## Oracle-mode rescoring (a row counts if ANY of NUM / WORD / GEN hits)\n')
    A('| rows | n | 3M normal | 3M oracle | 10M normal | 10M oracle | gain normal | gain oracle | err ratio normal | err ratio oracle |\n|---|---|---|---|---|---|---|---|---|---|')
    for nm, lab in (('pooled5', 'pooled-5'), ('block13', '13-family block'), ('block21', '21-family block')):
        d = rep['oracle'][nm]
        A(f"| {lab} | {d['3M']['n']} | {f(d['3M']['exact'])} | {f(d['3M']['oracle_exact'])} | {f(d['10M']['exact'])} | {f(d['10M']['oracle_exact'])} | "
          f"{f(d['gain']['normal'])} | {f(d['gain']['oracle'])} | {f(d['gain']['error_ratio_normal'], 3)} | {f(d['gain']['error_ratio_oracle'], 3)} |")
    A('\nPer split:\n\n| split | n | 3M normal | 3M oracle | 10M normal | 10M oracle |\n|---|---|---|---|---|---|')
    for s, d in rep['oracle']['by_split'].items():
        A(f"| {s} | {d['3M']['n']} | {f(d['3M']['exact'])} | {f(d['3M']['oracle_exact'])} | {f(d['10M']['exact'])} | {f(d['10M']['oracle_exact'])} |")
    A(f"\n13-family block present: {len(rep['oracle']['block_families']['block13'])} of 13 ({rep['oracle']['block_families']['block13_missing'] or 'none missing'}); "
      f"21-family block = the {len(rep['oracle']['block_families']['block21'])} other families in the dev files.\n")
    if rep['compare_g1']:
        A('## D vs G1 RESULT.json (normal pooled-5; on CPU fp32 small differences are expected)\n')
        A('| model | G1 | D | diff (points) | diff (rows) |\n|---|---|---|---|---|')
        for t in ('3M', '10M'):
            if t in rep['compare_g1']:
                c = rep['compare_g1'][t]
                A(f"| {t} | {f(c['g1_pooled5'], 3)} ({c['g1_correct']}/{c['g1_n']}) | {f(c['d_pooled5'], 3)} ({c['d_correct']}/{c['d_n']}) | {f(c['diff_points'], 3)} | {c['diff_rows']} |")
        A('')
    A('## 10M block knockout on in_dist (every round)\n')
    ko = rep['knockout']
    A(f"intact {f(ko['intact_in_dist'])} on {ko['n']} rows\n\n| removed (0-based) | in_dist exact | cost vs intact |\n|---|---|---|")
    for k, v in ko['runs'].items():
        A(f"| {k} | {f(v['exact'])} | {f(v['cost'])} |")
    A('\n## Teacher-forced loss, train sample (row means)\n')
    A('| group | n | model | ' + ' | '.join(TERMS) + ' |\n|---|---|---|' + '---|' * len(TERMS))
    for g_, v in rep['train_loss']['groups'].items():
        for t in ('3M', '10M'):
            A(f"| {g_} | {v['n']} | {t} | " + ' | '.join(f(v[t].get(k), 4) for k in TERMS) + ' |')
    A('\n## Gold log-likelihood (teacher-forced loss) per family, dev pooled-5\n')
    A('| family | n | 3M total | 10M total | 3M prog | 10M prog | 3M mode | 10M mode | 3M ans | 10M ans | 3M word | 10M word | 3M gen | 10M gen |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for fam, d in rep['dev_loss']['by_family'].items():
        A(f'| {fam} | {d["n"]} | ' + ' | '.join(f(d[t][k], 3) for k in TERMS for t in ('3M', '10M')) + ' |')
    p = rep['dev_loss']['pooled5']
    A(f'| pooled-5 | {p["n"]} | ' + ' | '.join(f(p[t][k], 3) for k in TERMS for t in ('3M', '10M')) + ' |')
    A('\n## Error ledger\n')
    A('Wrong rows, pooled-5, by gold mode (what the labels say) x chosen mode (what the model printed), with whether its own workspace held the gold number:\n')
    for t in ('3M', '10M'):
        A(f'**{t}** (wrong per split: {rep["ledger"][t]["wrong_per_split"]})\n\n| gold | chosen | workspace holds gold | wrong rows |\n|---|---|---|---|')
        for k, v in sorted(rep['ledger'][t]['wrong_pooled5_gold_chosen_workspace'].items(), key=lambda kv: -kv[1]):
            g_, c_, w_ = k.split('|')
            A(f'| {g_} | {c_} | {w_.split()[-1]} | {v} |')
        A('')
    A('Largest cells (split | family | chosen | gold), wrong rows:\n')
    for t in ('3M', '10M'):
        top = sorted(rep['ledger'][t]['wrong_by_split_family_chosen_gold'].items(), key=lambda kv: -kv[1])[:12]
        A(f'- {t}: ' + '; '.join(f'{k} = {v}' for k, v in top))
    fb = rep['ledger']['fixed_broken_3M_to_10M']
    A(f"\nFixed / broken 3M -> 10M: pooled-5 {fb['pooled5']}; by split {fb['by_split']}\n")
    top = sorted(fb['by_split_family'].items(), key=lambda kv: -(kv[1]['fixed'] + kv[1]['broken']))[:12]
    A('Most changed (split | family): ' + '; '.join(f"{k} +{v['fixed']}/-{v['broken']}" for k, v in top))
    A('\nFull tables: g1diag.json (ledger, wrong_by_split_family_chosen_gold, fixed_broken_3M_to_10M.by_split_family) and rows.jsonl.')
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(o) + '\n')
    return path


# ---------------------------------------------------------------- selftest
def selftest(args):
    t0 = time.time()
    root = tempfile.mkdtemp(prefix='g1diag-selftest-')
    data, outd = os.path.join(root, 'data'), args.out or os.path.join(root, 'out')
    os.makedirs(os.path.join(data, 'dev'))
    caps_json = os.path.join(os.path.abspath(args.src), 'custom_io', 'g8a', 'caps_g.json')
    assert os.path.exists(caps_json), caps_json
    open(os.path.join(data, 'caps.json'), 'w').write(open(caps_json).read())
    args.data = data
    ns = setup(args)
    torch = ns.torch
    from custom_io.data import CharVocab
    from custom_io.evalx import eval_all
    rng = random.Random(1)
    words = ['red', 'blue', 'green', 'plum', 'gold']

    def mk(fam, i):
        a, b, c = rng.randint(2, 40), rng.randint(2, 40), rng.randint(2, 9)
        if fam == 'arith_bare':
            return f'What is {a} + {b}?', str(a + b), [f'{a} + {b} = {a + b}']
        if fam == 'chain_ops':
            return f'Compute ({a} + {b}) * {c}.', str((a + b) * c), [f'({a} + {b}) * {c} = {(a + b) * c}']
        if fam == 'story_addsub':
            return f'Tom has {a} apples and gets {b} more. How many now?', str(a + b), [f'{a} + {b} = {a + b}']
        if fam == 'table_lookup':
            w = rng.sample(words, 3)
            return f'Pick the word: {w[0]} {w[1]} {w[2]}. Which is second?', w[1], []
        if fam == 'seq_next':
            return f'Is {a} bigger than {b}? Reply.', 'yes' if a > b else 'no', []
        if fam == 'cloze':
            w = rng.choice(words)
            return f'The cat saw the {w} bird and the ___ one.', rng.choice([w, 'zebra', 'qq']), []
    fams = ['arith_bare', 'chain_ops', 'story_addsub', 'table_lookup', 'seq_next']

    def rows_for(n, fl, tag=''):
        out = []
        for i in range(n):
            fam = fl[i % len(fl)]
            p, a, st = mk(fam, i)
            out.append(dict(id=f'{fam}-{i // len(fl)}', prompt=p, answer=a, accepted=[a], family=fam, level=1, stage=1, variant=0, steps=st))
        return out
    allrows = []
    for s in SPLITS:         # ids repeat across the splits and the train file on purpose (the target cache must be cleared between them)
        rs = rows_for(40 if s != 'family' else 10, fams)
        allrows += rs
        open(os.path.join(data, 'dev', f'{s}.jsonl'), 'w').write('\n'.join(json.dumps(r) for r in rs) + '\n')
    tr = rows_for(60, fams[:3] + ['cloze'] * 3 + fams[3:])
    open(os.path.join(data, 'train.jsonl'), 'w').write('\n'.join(json.dumps(r) for r in tr) + '\n')
    vocab = CharVocab.build(allrows + tr)
    vocab.save(os.path.join(data, 'charvocab.json'))
    cov = ns.pp.coverage(allrows)
    say('selftest data: dev rows', len(allrows), 'coverage', {k: v for k, v in cov['all'].items()})
    assert cov['all']['NUM'] > 0 and cov['all']['WORD'] > 0 and cov['all']['GEN'] > 0 and cov['all']['prog'] > 0, cov
    from custom_io.models import build
    cfg = dict(d=32, n_heads=2, reader_layers=1, blocks=1, n_loops=12, mlp=2.0, copy=True, eg_embed=False)
    ck = {}
    for tag, nb in (('3', 1), ('10', 3)):
        torch.manual_seed(7 + nb)
        c = dict(cfg, blocks=nb)
        m = build('ledger', vocab, **c).eval()
        for p in m.parameters():            # random init gives near-constant outputs: spread the weights so the modes and pointers vary
            if p.ndim >= 2:
                p.data.normal_(0, 0.3)
        p_ = os.path.join(root, f'fake{tag}.pt')
        torch.save(dict(model=m.state_dict(), name='ledger', cfg=c, chars=vocab.chars, step=0), p_)
        ck[tag] = (p_, m)
        res = eval_all(m, data, None, None, args.eval_batch, torch.device('cpu'))       # an independent evalx number to compare with
        json.dump(dict(final_eval=res), open(os.path.join(root, f'result{tag}.json'), 'w'))
    args.ckpt3, args.ckpt10 = ck['3'][0], ck['10'][0]
    args.result3, args.result10 = os.path.join(root, 'result3.json'), os.path.join(root, 'result10.json')
    args.out, args.device, args.train, args.sample_k, args.eg = outd, 'cpu', os.path.join(data, 'train.jsonl'), 20, None
    args.loss_batch = 16
    ns.pp._CACHE.clear()
    rep = pipeline(args, ns)
    sc = rep['selfcheck']
    assert sc['total_mismatches'] == 0 and sum(sc['mismatches_mirror_vs_talk_output_and_mode'].values()) == 0, sc
    for t in ('3M', '10M'):
        c = rep['compare_g1'][t]
        assert c['diff_rows'] == 0 and all(v['g1'] == v['d'] for v in c['by_split'].values()), c      # same code path -> identical on CPU
    assert set(rep['rules']) == {'R1', 'R2', 'R3'} and rep['knockout']['runs'].keys() >= {'skip_0', 'skip_1', 'skip_2', 'skip_2-2'}
    tc = rep['train_loss']['groups']
    assert tc['web']['n'] == 20 and tc['skill']['n'] == 20, tc['web']['n']      # the reservoir took 20 of the 30 / 90 rows
    for fn in ('rows.jsonl', 'g1diag.json', 'G1DIAG.md', 'train_sample.jsonl'):
        assert os.path.getsize(os.path.join(outd, fn)) > 0, fn
    n_rows = sum(1 for _ in open(os.path.join(outd, 'rows.jsonl')))
    assert n_rows == len(allrows), (n_rows, len(allrows))
    # reproducible sample: the same file twice
    a1, b1, _ = reservoir(args.train, 20, 0)
    a2, b2, _ = reservoir(args.train, 20, 0)
    assert a1 == a2 and b1 == b2
    import shutil
    shutil.rmtree(root, ignore_errors=True)         # only the folder this selftest made (data, fake checkpoints and, unless --out was given, its output)
    say(f'selftest: {time.time() - t0:.1f}s')
    say('D SELFTEST OK')


def main(argv=None):
    a = main_args(argv)
    if a.sample_only:
        tr = a.train or (os.path.join(a.data, 'train.jsonl') if a.data else None)
        assert tr, '--sample-only needs --train FILE (or --data POOL)'
        write_sample(tr, a.sample_only, a.sample_k)
        return
    if a.selftest:
        return selftest(a)
    for k in ('data', 'ckpt3', 'ckpt10', 'out'):
        if not getattr(a, k):
            sys.exit(f'--{k} is required')
    pipeline(a)


if __name__ == '__main__':
    main()
