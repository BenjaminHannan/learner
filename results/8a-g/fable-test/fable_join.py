"""Fable's pre-registered test for the WIDE 10M question, scored from two g1diag runs. Small card experiments only: no claim about a larger final model.
Reads rows.jsonl + g1diag.json from each run directory (train_sample.jsonl too if present). Pure stdlib, no torch, no GPU, no network.
  python3 -I fable_join.py --runA DIR_A --runB DIR_B --out OUTDIR [--result-wide RESULT.json]
Run A: tag 3M = G1 3M seed 400 ("s400"), tag 10M = G1 deep 10M seed 400 ("deep").
Run B: tag 3M = G1 3M seed 401 ("s401"), tag 10M = WIDE 10M seed 400 ("wide").
Marks are copied from api-opinions/answers/fable-wide.md section 2 (M below). Writes OUTDIR/FABLE-TEST.json and OUTDIR/FABLE-TEST.md."""
import argparse, collections, hashlib, json, math, os, sys

POOL5 = ['in_dist', 'answer', 'frame', 'vocab', 'variant']      # the 6th dev split, 'family', is held-out families: not in pooled-5
B13 = ['arith_bare', 'backward_solve', 'chain_ops', 'story_addsub', 'story_chain3', 'chain_story2', 'var_chain', 'div_exact', 'table_calc',
       'distance_units', 'compare_numbers', 'state_update', 'percent_rate']          # the 13 calculator families (same list as g1diag.py)
ZERO4 = ['table_lookup', 'seq_next', 'rule_apply', 'fewshot_number_rule']            # 0% program coverage in training
TERMS = ['total', 'prog', 'mode', 'ans', 'word', 'gen']
MODELS = ['s400', 'deep', 's401', 'wide']
SOURCE = {'s400': ('A', '3M'), 'deep': ('A', '10M'), 's401': ('B', '3M'), 'wide': ('B', '10M')}      # model -> (run, g1diag tag)
NAMES = {'s400': '3M s400', 'deep': 'deep 10M', 's401': '3M s401', 'wide': 'WIDE 10M'}
PAIRS = [('wide', 's400'), ('deep', 's400'), ('s401', 's400'), ('wide', 's401'), ('deep', 's401'), ('wide', 'deep')]      # (X, base)
MODE_NUM = 0            # g1diag modes: 0 NUM (a number slot is printed), 1 WORD, 2 GEN
EPS = 1e-9              # float slack so a value sitting exactly on a mark is not flipped by rounding

# Pre-registered marks, verbatim from fable-wide.md section 2 (nothing here is tuned).
M = dict(
    overlap_min=80.0,           # P1a  WIDE and 3M-s400 miss overlap >= 80%
    overlap_within=5.0,         # P1b  ... and within 5 points of the s401 vs s400 overlap
    deep_lower=8.0,             # P1c  deep and 3M overlap lower by >= 8 points on the 21 non-calc families
    task_loss_max=0.10,         # P2a  task-row total loss <= 0.10 for s400, deep, wide
    task_diff_max=0.02,         # P2b  cross-size differences <= 0.02
    web_gen_diff_max=0.03,      # P2c  web-fill GEN loss cross-size differences <= 0.03
    call_rate_max=10.0,         # P3a  tool-call rate in the four zero-coverage families <= 10% for every checkpoint
    acc_within=2.0,             # P3b  family accuracy within 2 points across sizes
    wrong_overlap=60.0,         # W1   overlap < 60%: seed-noise-limited
    wrong_task_loss=0.25,       # W2   task-row loss >= 0.25 for all sizes and still equal: schedule-limited (E3)
    wrong_mem_drop=0.05,        # W3   10M task-row loss >= 0.05 below 3M while dev misses are unchanged: memorisation
    dev_unchanged=0.7,          # W3   "dev misses unchanged" = |pooled-5 gain| <= 0.7 points (the 3M seed gap is 0.67); set by the roadmap thread (not by Fable)
    raw_flag=5.0)               # P3a  flag when the raw_mode==0 rate differs from the chosen==0 rate by more than 5 points (set by the roadmap thread, not by Fable)

# Figures quoted in prompts/wide-10m-scaling.md and the WIDE readout (shown there from the result files). u21 / u13 are UNWEIGHTED family means.
ORIG = {'s400': dict(pooled5=73.01, misses=1630, u21=62.64, u13=88.54, calc_misses=270, noncalc_misses=1360, zero4_misses=501),
        'deep': dict(pooled5=74.65, misses=1531, u21=65.38, u13=88.64),
        's401': dict(pooled5=73.68),
        'wide': dict(pooled5=73.33, misses=1611, u21=63.48, u13=88.14, calc_misses=280, noncalc_misses=1331)}
WIDE_EXPECT = dict(correct=4429, n=6040, pct=73.328)
EXPECT_BLOCKS = {'s400': 2, 'deep': 8, 's401': 2, 'wide': 2}
EXPECT_PARAMS = {'s400': 3544913, 'deep': 10496537, 's401': 3544913, 'wide': 10173509}      # n_params in the RESULT.json files


class AlignmentError(Exception):
    pass


# ---------------------------------------------------------------- small helpers
def dig(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def pct(a, b):
    return 100.0 * a / b if b else None


def sub(a, b):
    return None if a is None or b is None else a - b


def ge(a, b):
    return None if a is None else a >= b - EPS


def le(a, b):
    return None if a is None else a <= b + EPS


def lt(a, b):
    return None if a is None else a < b - EPS


def all_ok(oks):
    """None if any input is missing, else the AND."""
    return None if any(o is None for o in oks) else all(oks)


def status(ok):
    return 'n-a' if ok is None else 'PASS' if ok else 'FAIL'


def f(x, d=1):
    if x is None:
        return 'n/a'
    return f'{x:.{d}f}' if isinstance(x, float) else str(x)


def mcnemar_exact(b, c):
    """Exact two-sided binomial p for b vs c discordant rows (H0: each is equally likely): twice the smaller tail, capped at 1."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1))
    return min(1.0, 2 * tail / 2 ** n)


# ---------------------------------------------------------------- loading and the alignment check
def load_run(d, name):
    rp, gp = os.path.join(d, 'rows.jsonl'), os.path.join(d, 'g1diag.json')
    for p in (rp, gp):
        if not os.path.isfile(p):
            raise AlignmentError(f'INPUT ERROR: run {name}: {p} not found')
    with open(rp, encoding='utf-8') as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    with open(gp, encoding='utf-8') as fh:
        gd = json.load(fh)
    sp = os.path.join(d, 'train_sample.jsonl')
    sha = None
    if os.path.isfile(sp):
        with open(sp, 'rb') as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
    seen, keys = collections.Counter(), []
    for r in rows:
        k = (r['split'], r['id'])
        keys.append(k + (seen[k],))         # ids may repeat across splits (and in principle inside one): the occurrence number keeps the join exact
        seen[k] += 1
    for tag in ('3M', '10M'):
        for fld in ('hit', 'chosen', 'raw_mode'):
            if rows and (fld + tag) not in rows[0]:
                raise AlignmentError(f'INPUT ERROR: run {name}: rows.jsonl has no field {fld + tag}')
    return dict(name=name, dir=d, rows=rows, keys=keys, gd=gd, sample_sha=sha)


def check_oracle(run):
    """rows.jsonl and g1diag.json of one run must be the same run: g1diag's oracle table counts the same hits."""
    out = {}
    for tag in ('3M', '10M'):
        for blk, test in (('pooled5', lambda r: True), ('block13', lambda r: r['family'] in B13), ('block21', lambda r: r['family'] not in B13)):
            want = dig(run['gd'], 'oracle', blk, tag)
            if want is None:
                out[f'{tag}/{blk}'] = 'not checked (no oracle table in g1diag.json)'
                continue
            rs = [r for r in run['rows'] if r['split'] in POOL5 and test(r)]
            got = (len(rs), sum(int(r['hit' + tag]) for r in rs))
            if got != (want['n'], want['correct']):
                raise AlignmentError(f"ALIGNMENT ERROR: run {run['name']}: rows.jsonl and g1diag.json disagree on {tag} {blk}: rows.jsonl has {got[1]}/{got[0]} "
                                     f"correct, g1diag.json oracle table has {want['correct']}/{want['n']}. They are not from the same run.")
            out[f'{tag}/{blk}'] = f'ok ({got[1]}/{got[0]})'
    return out


def sample_info(run):
    tl = run['gd'].get('train_loss')
    if not isinstance(tl, dict):
        return dict(recorded=False)
    return dict(recorded=True, source=tl.get('source'), k=tl.get('k'), seen=tl.get('seen'), sha=run['sample_sha'],
                n={g: dig(tl, 'groups', g, 'n') for g in ('web', 'skill')})


def check_alignment(A, B):
    """Stop (AlignmentError) unless both runs scored the same dev rows and the same train-loss sample. Returns the facts and warnings."""
    ca = collections.Counter((r['split'], r['id'], r['family']) for r in A['rows'])
    cb = collections.Counter((r['split'], r['id'], r['family']) for r in B['rows'])
    if ca != cb:
        oa, ob = ca - cb, cb - ca
        raise AlignmentError(f"ALIGNMENT ERROR: the two rows.jsonl files do not hold the same (id, split, family) rows: run A {len(A['rows'])} rows, run B "
                             f"{len(B['rows'])} rows; {sum(oa.values())} only in A (e.g. {list(oa)[:3]}), {sum(ob.values())} only in B (e.g. {list(ob)[:3]}). "
                             'The miss overlap would be meaningless. Nothing was written.')
    gb = dict(zip(B['keys'], (r['gold_mode'] for r in B['rows'])))
    bad = sum(1 for k, r in zip(A['keys'], A['rows']) if gb[k] != r['gold_mode'])
    if bad:
        raise AlignmentError(f'ALIGNMENT ERROR: {bad} rows have the same (id, split, family) but a different gold_mode in the two runs. Nothing was written.')
    splits = collections.Counter(r['split'] for r in A['rows'])
    miss = [s for s in POOL5 if not splits[s]]
    if miss:
        raise AlignmentError(f'ALIGNMENT ERROR: dev splits missing from rows.jsonl: {miss}. Nothing was written.')
    sa, sb = sample_info(A), sample_info(B)
    if not (sa['recorded'] and sb['recorded']):
        smp = dict(status='nothing recorded: g1diag.json has no train_loss block in ' + ' and '.join(n for n, s in (('run A', sa), ('run B', sb)) if not s['recorded']))
    else:
        if sa['k'] != sb['k'] or sa['n'] != sb['n']:
            raise AlignmentError(f"ALIGNMENT ERROR: the train-loss samples differ: k {sa['k']} vs {sb['k']}, rows per group {sa['n']} vs {sb['n']}. Nothing was written.")
        if sa['sha'] and sb['sha']:
            if sa['sha'] != sb['sha']:
                raise AlignmentError('ALIGNMENT ERROR: train_sample.jsonl differs between the two runs (sha256 differs), so the per-term losses are not on the same rows. '
                                     'Rerun both g1diag runs with the same --train file. Nothing was written.')
            smp = dict(status='identical: train_sample.jsonl has the same sha256 in both runs', sha256=sa['sha'])
        elif sa['seen'] == sb['seen']:
            smp = dict(status='consistent but not verified: k, rows per group and rows seen are equal, but train_sample.jsonl is missing in at least one run folder')
        else:
            raise AlignmentError(f"ALIGNMENT ERROR: cannot show that the train-loss samples are the same: rows seen {sa['seen']} vs {sb['seen']} and no train_sample.jsonl "
                                 'in both run folders to compare. Copy train_sample.jsonl next to g1diag.json in both. Nothing was written.')
        smp.update(k=sa['k'], rows_per_group=sa['n'], seen_A=sa['seen'], seen_B=sb['seen'], source_A=sa['source'], source_B=sb['source'])
    warns = []
    for r in (A, B):
        mr = dig(r['gd'], 'meta', 'max_rows')
        if mr:
            warns.append(f"run {r['name']} was made with --max-rows {mr} (debug run)")
    dev_a, dev_b = ((dig(r['gd'], 'meta', 'device'), dig(r['gd'], 'meta', 'amp')) for r in (A, B))
    if dev_a != dev_b:
        warns.append(f'the runs differ in device/precision: A {dev_a[0]}/{dev_a[1]}, B {dev_b[0]}/{dev_b[1]}')
    if dig(A['gd'], 'meta', 'caps') != dig(B['gd'], 'meta', 'caps'):
        warns.append('meta.caps differs between the two runs')
    for m in MODELS:
        run, tag = (A, B)[SOURCE[m][0] == 'B'], SOURCE[m][1]
        nb, npar = dig(run['gd'], 'meta', 'blocks', tag), dig(run['gd'], 'meta', 'trained_params', tag)
        if nb is not None and nb != EXPECT_BLOCKS[m]:
            warns.append(f'MODEL MAPPING? {NAMES[m]} (run {run["name"]} tag {tag}) has {nb} blocks, expected {EXPECT_BLOCKS[m]}')
        if npar is not None and npar != EXPECT_PARAMS[m]:
            warns.append(f'MODEL MAPPING? {NAMES[m]} (run {run["name"]} tag {tag}) has {npar:,} trained params, RESULT.json says {EXPECT_PARAMS[m]:,}')
    return dict(n_rows=len(A['rows']), rows_per_split=dict(splits), same_rows='yes: identical (id, split, family) rows and gold_mode', train_sample=smp,
                oracle_check={n: check_oracle(r) for n, r in (('A', A), ('B', B))}, warnings=warns,
                devices={n: [dig(r['gd'], 'meta', 'device'), dig(r['gd'], 'meta', 'amp')] for n, r in (('A', A), ('B', B))})


# ---------------------------------------------------------------- the data per model
def model_vectors(A, B):
    """Per model: hit / chosen / raw_mode lists in run A's row order. Returns (vectors, meta rows, subsets)."""
    by = {'A': A['rows'], 'B': dict(zip(B['keys'], B['rows']))}
    order = {'A': A['rows'], 'B': [by['B'][k] for k in A['keys']]}
    V = {}
    for m, (run, tag) in SOURCE.items():
        rs = order[run]
        V[m] = dict(hit=[int(r['hit' + tag]) for r in rs], chosen=[int(r['chosen' + tag]) for r in rs], raw=[int(r['raw_mode' + tag]) for r in rs])
        if any(h not in (0, 1) for h in V[m]['hit']):
            raise AlignmentError(f'INPUT ERROR: {m}: hit values other than 0/1')
    meta = [dict(split=r['split'], family=r['family'], gold=int(r['gold_mode'])) for r in A['rows']]
    pool = [i for i, r in enumerate(meta) if r['split'] in POOL5]
    sub_ = dict(pooled5=pool, calc13=[i for i in pool if meta[i]['family'] in B13], noncalc21=[i for i in pool if meta[i]['family'] not in B13])
    return V, meta, sub_


def by_family(hit, meta, idx):
    d = {}
    for i in idx:
        c, n = d.get(meta[i]['family'], (0, 0))
        d[meta[i]['family']] = (c + hit[i], n + 1)
    return d


def block_acc(hit, meta, idx):
    fam = by_family(hit, meta, idx)
    c = sum(hit[i] for i in idx)
    um = sum(100.0 * a / b for a, b in fam.values()) / len(fam) if fam else None
    return dict(n=len(idx), correct=c, misses=len(idx) - c, pooled_pct=pct(c, len(idx)), unweighted_family_pct=um, n_families=len(fam))


# ---------------------------------------------------------------- part 1: miss overlap
def pair_stats(hx, hb, idx):
    mx = sum(1 for i in idx if not hx[i])
    mb = sum(1 for i in idx if not hb[i])
    both = sum(1 for i in idx if not hx[i] and not hb[i])
    b = sum(1 for i in idx if not hx[i] and hb[i])         # X wrong, base right
    c = sum(1 for i in idx if hx[i] and not hb[i])         # X right, base wrong
    return dict(n=len(idx), misses_x=mx, misses_base=mb, both=both, overlap_pct=pct(both, mx), jaccard_pct=pct(both, mx + mb - both), b_x_wrong_base_right=b,
                c_x_right_base_wrong=c, mcnemar_p=mcnemar_exact(b, c))


def part1(V, sub_):
    out = {}
    for name, idx in sub_.items():
        out[name] = {f'{x}|{b}': pair_stats(V[x]['hit'], V[b]['hit'], idx) for x in MODELS for b in MODELS if x != b}
    return out


# ---------------------------------------------------------------- part 2: per-term train loss
def part2(runs):
    tab, diff = {}, {}
    for m, (run, tag) in SOURCE.items():
        tab[m] = {}
        for g in ('web', 'skill'):
            d = dig(runs[run]['gd'], 'train_loss', 'groups', g, tag)
            tab[m][g] = None if d is None else dict(n=dig(runs[run]['gd'], 'train_loss', 'groups', g, 'n'), **{t: d.get(t) for t in TERMS})
    for m in ('deep', 'wide', 's401'):
        diff[m] = {g: {t: (sub(tab[m][g][t], tab['s400'][g][t]) if tab[m][g] and tab['s400'][g] else None) for t in TERMS} for g in ('web', 'skill')}
    dev = {m: dig(runs[SOURCE[m][0]]['gd'], 'dev_loss', 'pooled5', SOURCE[m][1]) for m in MODELS}
    fam = {}
    for m, (run, tag) in SOURCE.items():
        for fm, d in (dig(runs[run]['gd'], 'dev_loss', 'by_family') or {}).items():
            fam.setdefault(fm, {})[m] = dig(d, tag, 'total')
    return dict(train_loss=tab, diff_vs_s400=diff, dev_gold_loss_pooled5=dev, dev_gold_loss_total_by_family=fam,
                note='row-weighted means of per-batch means (g1diag, batches of 64): approximate; teacher-forced, eval mode, on the shared train sample')


# ---------------------------------------------------------------- part 3: calls in the four zero-program families
def part3(V, meta, splits):
    out = {}
    for fam in ZERO4 + ['pooled']:
        idx = [i for i, r in enumerate(meta) if r['split'] in splits and (fam == 'pooled' or r['family'] == fam) and (fam != 'pooled' or r['family'] in ZERO4)]
        n = len(idx)
        gold = [i for i in idx if meta[i]['gold'] == MODE_NUM]
        rec = dict(n=n, gold_num_pct=pct(len(gold), n), models={})
        for m in MODELS:
            v = V[m]
            notgold = [i for i in idx if meta[i]['gold'] != MODE_NUM]
            rec['models'][m] = dict(call_pct=pct(sum(1 for i in idx if v['chosen'][i] == MODE_NUM), n), raw_num_pct=pct(sum(1 for i in idx if v['raw'][i] == MODE_NUM), n),
                                    correct=sum(v['hit'][i] for i in idx), acc_pct=pct(sum(v['hit'][i] for i in idx), n),
                                    false_call_pct=pct(sum(1 for i in notgold if v['chosen'][i] == MODE_NUM), len(notgold)),
                                    missed_call_pct=pct(sum(1 for i in gold if v['chosen'][i] != MODE_NUM), len(gold)))
        out[fam] = rec
    return out


# ---------------------------------------------------------------- the marks
def mark(mid, text, value, vtext, thr, ok, counted=True, note=''):
    return dict(id=mid, mark=text, value=value, value_text=vtext, threshold=thr, status=status(ok), counted=counted, note=note)


def build_marks(P1, P2, P3):
    ms = []
    pw, pd, ps = (P1['pooled5'][k] for k in ('wide|s400', 'deep|s400', 's401|s400'))
    nw, nd, ns = (P1['noncalc21'][k] for k in ('wide|s400', 'deep|s400', 's401|s400'))
    ov_w, ov_s = pw['overlap_pct'], ps['overlap_pct']
    ms.append(mark('P1a', 'WIDE miss overlap with 3M s400 (share of WIDE misses that s400 also misses), pooled-5', ov_w,
                   f"{f(ov_w)}% ({pw['both']}/{pw['misses_x']})", f"at least {M['overlap_min']:g}%", ge(ov_w, M['overlap_min'])))
    d = None if ov_w is None or ov_s is None else abs(ov_w - ov_s)
    ms.append(mark('P1b', 'WIDE overlap within 5 points of the seed baseline (s401 vs s400 overlap), pooled-5', d,
                   f"abs({f(ov_w)} - {f(ov_s)}) = {f(d)} points", f"at most {M['overlap_within']:g} points", le(d, M['overlap_within'])))
    low = sub(ns['overlap_pct'], nd['overlap_pct'])
    ms.append(mark('P1c', 'deep overlap with s400 LOWER than the seed baseline (s401 vs s400) by 8 points, 21 non-calc families (primary reading)', low,
                   f"{f(ns['overlap_pct'])} - {f(nd['overlap_pct'])} = {f(low)} points", f"at least {M['deep_lower']:g} points lower", ge(low, M['deep_lower'])))
    lw = sub(nw['overlap_pct'], nd['overlap_pct'])
    ms.append(mark('P1c-alt', 'same, but lower than WIDE overlap with s400 on the 21 non-calc families (alternative reading)', lw,
                   f"{f(nw['overlap_pct'])} - {f(nd['overlap_pct'])} = {f(lw)} points", f"at least {M['deep_lower']:g} points lower", ge(lw, M['deep_lower']),
                   counted=False, note='shown for completeness; the verdict uses P1c'))
    tl = P2['train_loss']
    task = {m: dig(tl, m, 'skill', 'total') for m in ('s400', 'deep', 'wide')}
    vals = list(task.values())
    ms.append(mark('P2a', 'task-row (non-web) total train loss, s400 / deep / wide', None if None in vals else max(vals),
                   ' / '.join(f(task[m], 4) for m in task), f"at most {M['task_loss_max']:.2f} for each", None if None in vals else all(le(v, M['task_loss_max']) for v in vals)))
    td = [sub(task[m], task['s400']) for m in ('deep', 'wide')]
    tdm = None if None in td else max(abs(x) for x in td)
    ms.append(mark('P2b', 'task-row total loss cross-size differences (deep minus s400, wide minus s400)', tdm, ' / '.join(f(x, 4) for x in td),
                   f"absolute value at most {M['task_diff_max']:.2f}", le(tdm, M['task_diff_max'])))
    wg = {m: dig(tl, m, 'web', 'gen') for m in ('s400', 'deep', 'wide')}
    wd = [sub(wg[m], wg['s400']) for m in ('deep', 'wide')]
    wdm = None if None in wd else max(abs(x) for x in wd)
    ms.append(mark('P2c', 'web-fill GEN loss cross-size differences (deep minus s400, wide minus s400)', wdm, ' / '.join(f(x, 4) for x in wd),
                   f"absolute value at most {M['web_gen_diff_max']:.2f}", le(wdm, M['web_gen_diff_max'])))
    pz = P3['pooled']
    calls = {m: pz['models'][m]['call_pct'] for m in MODELS}
    cm = None if pz['n'] == 0 else max(calls.values())
    raw = {m: pz['models'][m]['raw_num_pct'] for m in MODELS}
    flag = [m for m in MODELS if pz['n'] and abs(raw[m] - calls[m]) > M['raw_flag'] + EPS]
    ms.append(mark('P3a', 'call rate (chosen mode == NUM) pooled over the 4 zero-coverage families, every checkpoint (s400 / deep / s401 / wide)', cm,
                   ' / '.join(f(calls[m]) + '%' for m in MODELS), f"at most {M['call_rate_max']:g}% for each", le(cm, M['call_rate_max']),
                   note=('raw_mode==0 differs from chosen==0 by more than 5 points for: ' + ', '.join(NAMES[m] for m in flag)) if flag else 'raw_mode==0 agrees within 5 points'))
    rm = None if pz['n'] == 0 else max(raw.values())
    ms.append(mark('P3a-raw', 'same with the raw mode head (raw_mode == NUM)', rm, ' / '.join(f(raw[m]) + '%' for m in MODELS), f"at most {M['call_rate_max']:g}% for each",
                   le(rm, M['call_rate_max']), counted=False, note='shown for completeness; the verdict uses chosen'))
    diffs = {}
    for m in ('deep', 'wide'):
        for fam in ZERO4 + ['pooled']:
            r = P3[fam]
            if r['n']:
                diffs[f'{m}|{fam}'] = abs(r['models'][m]['acc_pct'] - r['models']['s400']['acc_pct'])
    worst = max(diffs, key=diffs.get) if diffs else None
    ms.append(mark('P3b', 'family accuracy difference to s400, deep and wide, each of the 4 families and pooled (largest shown)', diffs[worst] if worst else None,
                   (f"{f(diffs[worst])} points ({worst.replace('|', ' on ')})" if worst else 'n/a'), f"at most {M['acc_within']:g} points", le(diffs[worst], M['acc_within']) if worst else None,
                   note='all differences must pass; s401 minus s400 is in the Part 3 table as a noise reference'))
    return ms


def wrong_rules(P1, P2, P4):
    out = []
    ovs = {k: P1['pooled5'][k]['overlap_pct'] for k in ('wide|s400', 'deep|s400', 's401|s400')}
    out.append(dict(id='W1', rule='miss overlap < 60%: the models fail on different rows, seed-noise-limited, the only honest spend is seeds',
                    value=f"WIDE vs s400 {f(ovs['wide|s400'])}%; deep vs s400 {f(ovs['deep|s400'])}%; s401 vs s400 {f(ovs['s401|s400'])}%",
                    applies=lt(ovs['wide|s400'], M['wrong_overlap']), note='tested on WIDE vs s400 (pooled-5); the other two are shown'))
    tl = P2['train_loss']
    task = {m: dig(tl, m, 'skill', 'total') for m in ('s400', 'deep', 'wide')}
    vals = list(task.values())
    ok = None if None in vals else all(ge(v, M['wrong_task_loss']) for v in vals) and max(vals) - min(vals) <= M['task_diff_max'] + EPS
    out.append(dict(id='W2', rule='task-row loss >= 0.25 for all sizes and still equal: schedule-limited (E3), a longer or hotter 3M run is next',
                    value=' / '.join(f'{m} {f(task[m], 4)}' for m in task), applies=ok, note='"equal" = largest minus smallest <= 0.02, the tolerance of mark P2b'))
    mem = {}
    for m in ('deep', 'wide'):
        drop = sub(task['s400'], task[m])
        gain = sub(P4[m]['pooled5']['pooled_pct'], P4['s400']['pooled5']['pooled_pct'])
        below = ge(drop, M['wrong_mem_drop'])
        flat = None if gain is None else abs(gain) <= M['dev_unchanged'] + EPS
        mem[m] = dict(task_loss_below_s400_by=drop, below_by_at_least_0_05=below, pooled5_gain_points=gain, dev_misses_unchanged=flat, both=all_ok([below, flat]))
    both = [mem[m]['both'] for m in mem]
    out.append(dict(id='W3', rule='10M task-row loss >= 0.05 below 3M while dev misses are unchanged: capacity is used for memorisation only',
                    value='; '.join(f"{m}: loss lower by {f(mem[m]['task_loss_below_s400_by'], 4)}, dev gain {f(mem[m]['pooled5_gain_points'], 2)} points" for m in mem),
                    applies=(True if any(b is True for b in both) else None if any(b is None for b in both) else False), detail=mem,
                    note='"dev misses unchanged" = pooled-5 gain within +-0.7 points of s400'))
    return out


def verdict(marks, wrongs):
    counted = [m for m in marks if m['counted']]
    fails = [m['id'] for m in counted if m['status'] == 'FAIL']
    nas = [m['id'] for m in counted if m['status'] == 'n-a']
    npass = sum(1 for m in counted if m['status'] == 'PASS')
    if fails:
        word = 'NOT SUPPORTED'          # E1 wins only if ALL marks hold, so one failure is enough
    elif nas:
        word = 'UNDECIDED'
    else:
        word = 'SUPPORTED'
    return dict(e1=word, counted=len(counted), passed=npass, failed=fails, not_available=nas, wrong_rules_that_apply=[w['id'] for w in wrongs if w['applies'] is True],
                text=f'E1 (capacity is not the binding limit on this card) is {word} by the pre-registered marks: {npass} of {len(counted)} counted marks pass'
                     + (f', fail: {", ".join(fails)}' if fails else '') + (f', cannot compute: {", ".join(nas)}' if nas else '') + '.')


# ---------------------------------------------------------------- part 4: accuracy table and cross-checks
def part4(V, meta, sub_, runs):
    acc = {}
    for m in MODELS:
        acc[m] = {name: block_acc(V[m]['hit'], meta, idx) for name, idx in sub_.items()}
        acc[m]['original'] = ORIG[m]
        g1 = dig(runs[SOURCE[m][0]]['gd'], 'compare_g1', SOURCE[m][1])
        acc[m]['g1_result_json'] = None if g1 is None else dict(correct=g1.get('g1_correct'), n=g1.get('g1_n'), pct=g1.get('g1_pooled5'))
    return acc


def cross_checks(acc, P3, wide_result):
    w = acc['wide']['pooled5']
    cc = dict(expected=WIDE_EXPECT, recomputed=dict(correct=w['correct'], n=w['n'], pct=w['pooled_pct']), diff_rows_vs_expected=w['correct'] - WIDE_EXPECT['correct'],
              diff_points_vs_expected=w['pooled_pct'] - WIDE_EXPECT['pct'], result_json=None)
    if wide_result:
        try:
            with open(wide_result, encoding='utf-8') as fh:
                d = json.load(fh)
            fe = d.get('final_eval', d)
            c, n = sum(fe[s]['correct'] for s in POOL5), sum(fe[s]['n'] for s in POOL5)
            cc['result_json'] = dict(path=wide_result, correct=c, n=n, pct=pct(c, n), diff_rows=w['correct'] - c, diff_points=w['pooled_pct'] - pct(c, n))
        except (OSError, ValueError, KeyError, TypeError) as e:
            cc['result_json'] = dict(path=wide_result, error=f'could not read pooled-5 from it: {e!r}')
    q = []

    def add(name, quoted, got):
        q.append(dict(name=name, quoted=quoted, recomputed=got, diff=got - quoted))
    for m in ('s400', 'deep', 'wide'):
        add(f'{NAMES[m]} misses, pooled-5', ORIG[m]['misses'], acc[m]['pooled5']['misses'])
    for m in ('s400', 'wide'):
        add(f'{NAMES[m]} misses, 13 calculator families', ORIG[m]['calc_misses'], acc[m]['calc13']['misses'])
        add(f'{NAMES[m]} misses, 21 non-calculator families', ORIG[m]['noncalc_misses'], acc[m]['noncalc21']['misses'])
    z = P3['pooled']
    if z['n']:
        add('3M s400 misses in the 4 zero-coverage families', ORIG['s400']['zero4_misses'], z['n'] - z['models']['s400']['correct'])
    return cc, q


# ---------------------------------------------------------------- the words
def claims(rep):
    P1, P2, P3, A = rep['part1'], rep['part2'], rep['part3'], rep['part4']
    pw, pd, ps = (P1['pooled5'][k] for k in ('wide|s400', 'deep|s400', 's401|s400'))
    nw, nd, ns = (P1['noncalc21'][k] for k in ('wide|s400', 'deep|s400', 's401|s400'))
    st = {m['id']: m['status'] for m in rep['marks']}
    tl = P2['train_loss']
    pz = P3['pooled']
    shown, sugg, untested = [], [], []
    shown.append(f"Pooled-5, {pw['n']} rows. WIDE misses {pw['misses_x']}; {pw['both']} of them ({f(pw['overlap_pct'])}%) are also misses of 3M s400. The seed baseline (s401 vs s400) is "
                 f"{f(ps['overlap_pct'])}% ({ps['both']}/{ps['misses_x']}). Deep vs s400 is {f(pd['overlap_pct'])}% ({pd['both']}/{pd['misses_x']}).")
    shown.append(f"Discordant rows (X wrong, base right / X right, base wrong) with exact two-sided binomial p: WIDE vs s400 {pw['b_x_wrong_base_right']}/{pw['c_x_right_base_wrong']} "
                 f"(p {f(pw['mcnemar_p'], 3)}); deep vs s400 {pd['b_x_wrong_base_right']}/{pd['c_x_right_base_wrong']} (p {f(pd['mcnemar_p'], 3)}); "
                 f"s401 vs s400 {ps['b_x_wrong_base_right']}/{ps['c_x_right_base_wrong']} (p {f(ps['mcnemar_p'], 3)}).")
    shown.append(f"21 non-calculator families ({nd['n']} rows): overlap with s400 is deep {f(nd['overlap_pct'])}%, WIDE {f(nw['overlap_pct'])}%, s401 {f(ns['overlap_pct'])}%. "
                 f"Deep is lower than the seed baseline by {f(sub(ns['overlap_pct'], nd['overlap_pct']))} points and lower than WIDE by {f(sub(nw['overlap_pct'], nd['overlap_pct']))} points.")
    shown.append('Task-row (non-web) total train loss: ' + ', '.join(f"{NAMES[m]} {f(dig(tl, m, 'skill', 'total'), 4)}" for m in MODELS)
                 + '. Web-fill GEN loss: ' + ', '.join(f"{NAMES[m]} {f(dig(tl, m, 'web', 'gen'), 4)}" for m in MODELS) + '.')
    if pz['n']:
        shown.append(f"Four zero-coverage families ({pz['n']} pooled-5 rows, gold mode NUM in {f(pz['gold_num_pct'])}% of them). Rate of chosen mode == NUM: "
                     + ', '.join(f"{NAMES[m]} {f(pz['models'][m]['call_pct'])}%" for m in MODELS) + '. Accuracy: '
                     + ', '.join(f"{NAMES[m]} {f(pz['models'][m]['acc_pct'])}%" for m in MODELS) + '.')
    cc = rep['cross_checks']['wide_pooled5']
    shown.append(f"WIDE pooled-5 recomputed here: {cc['recomputed']['correct']}/{cc['recomputed']['n']} = {f(cc['recomputed']['pct'], 3)}% against the readout's 4429/6040 = 73.328% "
                 f"(difference {cc['diff_rows_vs_expected']:+d} rows).")
    if st['P1a'] == 'PASS' and st['P1b'] == 'PASS':
        sugg.append('WIDE misses nearly the same rows as 3M s400, about as many as a second 3M seed does, so on this card it looks like one more seed of the small model.')
    elif st['P1a'] == 'FAIL' or st['P1b'] == 'FAIL':
        sugg.append('WIDE does not behave like a second seed of the 3M model by the overlap marks (see P1a, P1b): its misses are shared with s400 less than the marks allow, or differ from the seed baseline.')
    if st['P1c'] == 'PASS':
        sugg.append('Depth changed which non-calculator rows are missed by more than a new seed does (P1c passes). That fits "depth did something specific", but it is one deep run.')
    elif st['P1c'] == 'FAIL':
        sugg.append('On the 21 non-calculator families deep shows no clear extra change in which rows are missed compared with a new seed (P1c fails at the pre-registered 8 points).')
    if st['P2a'] == 'PASS' and st['P2b'] == 'PASS':
        sugg.append('The task rows are close to solved at every size and size does not change that, so extra size has little left to fit on them.')
    elif st['P2a'] == 'FAIL':
        sugg.append('The task-row loss is above 0.10 for at least one size, so "the training rows are solved" does not hold in this teacher-forced measurement.')
    if st['P3a'] == 'FAIL':
        sugg.append('The models print a number slot (chosen mode NUM) more than 10% of the time in the zero-coverage families, so the "do not call" label ceiling is not as clean as assumed; read it together with the gold-NUM share.')
    sugg.append('A row-level McNemar p-value compares two fixed checkpoints; it is not a measure of training-seed noise. With one training run per condition the s401 vs s400 pair is the better yardstick.')
    untested += ['Whether the data manifests differ in content. Recorded hashes: 3M s400 and deep 133e463e, 3M s401 4ad1440e, WIDE 8ee0b3ee (copied from the RESULT.json files, not recomputed here). The seed baseline therefore differs in seed and manifest, and WIDE differs from deep in manifest.',
                 'Whether the runs are schedule-limited (E3): no learning-curve slope is measured here.',
                 'Whether the "do not call" weighting of rows without a program causes the low zero-coverage scores: only call rates and accuracies are measured, no change is made.',
                 'Anything about a larger final model.']
    return dict(shown=shown, suggested=sugg, untested=untested)


def summary(rep):
    """At most 8 plain sentences for Ben; every sentence follows from the computed marks."""
    P1, P3 = rep['part1'], rep['part3']
    st = {m['id']: m['status'] for m in rep['marks']}
    n0 = lambda x: 'n/a' if x is None else str(round(x))
    ov = lambda blk, k: n0(P1[blk][k]['overlap_pct'])
    tl = rep['part2']['train_loss']
    pz = P3['pooled']
    v = rep['verdict']
    s = ['We took four saved small models and checked, question by question, which ones get the same questions wrong.']
    s.append(f"Two of them differ only in their random start, and of the questions one of them gets wrong, about {ov('pooled5', 's401|s400')} out of every 100 are also wrong for the other, "
             'so that is the overlap plain luck gives.')
    s.append(f"The wide model shares {ov('pooled5', 'wide|s400')} out of 100 of its wrong answers with the first small model, which is "
             + ('close to that luck level, so it acts like one more random start.' if st['P1a'] == 'PASS' and st['P1b'] == 'PASS' else 'not close enough to that luck level for the test we set.'))
    s.append(f"The deep model shares only {ov('noncalc21', 'deep|s400')} out of 100 on the 21 question types that need no calculator, against {ov('noncalc21', 's401|s400')} for the luck level, so "
             + ('depth did change which questions it misses.' if st['P1c'] == 'PASS' else 'depth did not clearly change which questions it misses.'))
    task = [dig(tl, m, 'skill', 'total') for m in ('s400', 'deep', 'wide')]
    s.append('On the practice questions that need a skill, the three models make mistakes scoring ' + ', '.join(f(x, 2) for x in task) + ' (0 would be perfect), and '
             + ('the bigger models are not any better.' if st['P2b'] == 'PASS' else 'the sizes differ by more than we allowed.'))
    if pz['n']:
        s.append('On the four question types that never use the calculator in training, the models print a calculator-style number in at most '
                 f"{n0(max(pz['models'][m]['call_pct'] for m in MODELS))} out of every 100 rows, and their scores "
                 + ('stay within 2 points of each other across sizes.' if st['P3b'] == 'PASS' else 'move by more than 2 points across sizes.'))
    word = {'SUPPORTED': 'supported', 'NOT SUPPORTED': 'not supported', 'UNDECIDED': 'not settled'}[v['e1']]
    s.append(f"Of the {v['counted']} checks we fixed before looking, {v['passed']} passed, so the idea that making the model bigger is not what limits it on this card is {word}.")
    s.append('This covers only the small card experiments with one training run each, so it says nothing about a bigger final model.')
    return s


def limits(rep):
    dev = rep['alignment']['devices']
    return ['One training run per condition (s400, deep, s401, wide). The seed baseline is a single pair (s401 vs s400), and s401 also has a different data manifest from s400.',
            f"g1diag recomputed every row (run A on {dev['A'][0]}/{dev['A'][1]}, run B on {dev['B'][0]}/{dev['B'][1]}) while the original numbers come from GPU runs in bf16, so a few rows can differ; "
            'the WIDE cross-check in the detail tables shows the size of that difference.',
            'Per-term losses are g1diag numbers, which it describes as batch means weighted by rows (approximate; batches of 64), teacher forced in eval mode on a sample of 2,000 web + 2,000 task rows. '
            'They are not the logged training loss. On my reading of loss() in ledger.py at 612f5c5b01, each of the six terms used here is a sum over rows divided by the batch size, so the row weighting '
            'gives their exact row mean; only op_acc and copy_share (not used here) are truly approximate.',
            '"Overlap(X|base)" = rows both miss / rows X misses: the share of X\'s misses that the base also misses. It depends on how many misses X has and is not symmetric. Jaccard is also given.',
            '"Call rate" is the share of rows whose chosen output mode is NUM (the value of the number slot the answer pointer picks is printed). That includes pointing at a number that was in the prompt, '
            'so it is not a literal count of calculator calls. The raw mode head (raw_mode == NUM) is shown next to it.',
            'Part 3 uses the 5 pooled-5 splits (720 rows in the 4 families in the real dev set), so a 2-point accuracy mark is a few rows per family and is tight compared with seed noise.',
            'The 13 calculator and 21 non-calculator blocks are the pooled-5 rows whose family is (or is not) in the g1diag list of 13; the held-out families of the sixth dev split are in neither block.',
            'P1c has two readings; the verdict flag uses the seed baseline, the other is printed as P1c-alt and does not count.']


# ---------------------------------------------------------------- the markdown
def table(head, rows):
    cell = lambda c: str(c).replace('|', '/')            # a pipe would break the markdown table
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(cell(c) for c in r) + ' |' for r in rows]


def write_md(rep, path):
    P1, P2, P3, A = rep['part1'], rep['part2'], rep['part3'], rep['part4']
    o = []
    A_ = o.append
    A_('# Fable test on the WIDE 10M question: error overlap, per-term loss, call rate\n')
    A_('Scope: small card experiments only (34 question families, pooled-5 dev rows). It says nothing about a larger final model.\n')
    al = rep['alignment']
    A_(f"Inputs: {al['n_rows']} dev rows in both runs ({al['same_rows']}). Train sample: {al['train_sample']['status']}. Models: s400 = run A tag 3M, deep = run A tag 10M, s401 = run B tag 3M, wide = run B tag 10M.\n")
    for w in al['warnings']:
        A_(f'- WARNING: {w}')
    if al['warnings']:
        A_('')
    A_('## Verdict by mark\n')
    A_('\n'.join(table(['Mark', 'What is measured', 'Value', 'Threshold (pre-registered)', 'Result', 'Counts'],
                       [(m['id'], m['mark'], m['value_text'], m['threshold'], '**' + m['status'] + '**', 'yes' if m['counted'] else 'no') for m in rep['marks']])))
    A_(f"\n**{rep['verdict']['text']}**\n")
    for m in rep['marks']:
        if m['note']:
            A_(f"- {m['id']}: {m['note']}")
    A_('\nResults that Fable said would prove E1 wrong:\n')
    A_('\n'.join(table(['Rule', 'Condition', 'Value', 'Applies?'],
                       [(w['id'], w['rule'], w['value'], 'n-a' if w['applies'] is None else 'YES' if w['applies'] else 'no') for w in rep['wrong_rules']])))
    A_('\nFailing a mark does not prove E1 wrong; only the rows above do. Overall flag: wrong rules that apply = '
       + (', '.join(rep['verdict']['wrong_rules_that_apply']) or 'none') + '.\n')
    c = rep['claims']
    A_('## Claims\n')
    for lab, key in (('shown', 'shown'), ('suggested', 'suggested'), ('untested', 'untested')):
        for t in c[key]:
            A_(f'- **{lab}**: {t}')
    A_('\n## Plain-language summary for Ben (a high-school senior)\n')
    A_(' '.join(rep['summary']) + '\n')
    A_('## Limits\n')
    for t in limits(rep):
        A_(f'- {t}')
    # details
    A_('\n## Detail tables\n')
    A_('### Part 1: miss overlap and McNemar (rows are pooled-5)\n')
    A_('Overlap(X|base) = rows both miss / rows X misses. b = X wrong and base right, c = X right and base wrong; p is the exact two-sided binomial test on b vs c.\n')
    head = ['X', 'base', 'misses X', 'misses base', 'both', 'overlap %', 'Jaccard %', 'b', 'c', 'p']
    first = [f'{x}|{b}' for x, b in PAIRS]
    allk = first + [f'{x}|{b}' for x in MODELS for b in MODELS if x != b and f'{x}|{b}' not in first]
    for blk, lab, keys in (('pooled5', 'pooled-5 (all 12 ordered pairs; the six that matter first)', allk),
                           ('calc13', '13 calculator families (pairs that matter)', first),
                           ('noncalc21', '21 non-calculator families (pairs that matter)', first)):
        A_(f"**{lab}**, {P1[blk][keys[0]]['n']} rows\n")
        rows = []
        for k in keys:
            x, b = k.split('|')
            s = P1[blk][k]
            rows.append((NAMES[x], NAMES[b], s['misses_x'], s['misses_base'], s['both'], f(s['overlap_pct']), f(s['jaccard_pct']), s['b_x_wrong_base_right'],
                         s['c_x_right_base_wrong'], f(s['mcnemar_p'], 4)))
        A_('\n'.join(table(head, rows)) + '\n')
    A_('### Part 2: teacher-forced train loss per term (means over the shared sample)\n')
    rows = []
    for g, lab in (('skill', 'task rows'), ('web', 'web fill-in rows')):
        for m in MODELS:
            d = P2['train_loss'][m][g]
            rows.append((lab, NAMES[m], 'n/a' if d is None else d['n']) + tuple('n/a' if d is None else f(d[t], 4) for t in TERMS))
    A_('\n'.join(table(['rows', 'model', 'n'] + TERMS, rows)) + '\n')
    rows = []
    for g, lab in (('skill', 'task rows'), ('web', 'web fill-in rows')):
        for m in ('deep', 'wide', 's401'):
            rows.append((lab, NAMES[m] + ' minus 3M s400') + tuple(f(P2['diff_vs_s400'][m][g][t], 4) for t in TERMS))
    A_('Differences to 3M s400:\n\n' + '\n'.join(table(['rows', 'comparison'] + TERMS, rows)) + '\n')
    rows = [(NAMES[m],) + tuple('n/a' if P2['dev_gold_loss_pooled5'][m] is None else f(P2['dev_gold_loss_pooled5'][m].get(t), 3) for t in TERMS) for m in MODELS]
    A_('Gold log-likelihood on the dev rows (teacher-forced loss, pooled-5; per family in the JSON):\n\n' + '\n'.join(table(['model'] + TERMS, rows)) + '\n')
    A_('### Part 3: the four zero-coverage families (pooled-5 rows)\n')
    A_('gold NUM % is the share of rows whose label says the answer is a number slot. call % = chosen mode NUM; raw % = mode head says NUM; acc % = family accuracy. '
       'false call % = chosen NUM where the label is not NUM.\n')
    rows = []
    for fam in ZERO4 + ['pooled']:
        r = P3[fam]
        for m in MODELS:
            q = r['models'][m]
            rows.append((fam, r['n'], f(r['gold_num_pct']), NAMES[m], f(q['call_pct']), f(q['raw_num_pct']), f(q['acc_pct']), f(q['false_call_pct'])))
    A_('\n'.join(table(['family', 'n', 'gold NUM %', 'model', 'call %', 'raw %', 'acc %', 'false call %'], rows)) + '\n')
    rows = []
    for fam in ZERO4 + ['pooled']:
        r = P3[fam]
        if r['n']:
            rows.append((fam,) + tuple(f(sub(r['models'][m]['acc_pct'], r['models']['s400']['acc_pct'])) for m in ('deep', 'wide', 's401')))
    A_('Accuracy minus 3M s400 (points):\n\n' + '\n'.join(table(['family', 'deep', 'wide', 's401 (noise reference)'], rows)) + '\n')
    s6 = rep['part3_all_splits']['pooled']
    if s6['n']:
        A_(f"With all six dev splits ({s6['n']} rows in the 4 families) the pooled call rate (chosen NUM) is " + ', '.join(f"{NAMES[m]} {f(s6['models'][m]['call_pct'])}%" for m in MODELS) + '.\n')
    A_('### Part 4: accuracy, recomputed here next to the original figures\n')
    rows = []
    for m in MODELS:
        a, o_ = A[m], A[m]['original']
        g1 = a['g1_result_json']
        rows.append((NAMES[m], f"{a['pooled5']['correct']}/{a['pooled5']['n']}", f(a['pooled5']['pooled_pct'], 2), f(o_['pooled5'], 2), a['pooled5']['misses'], f(o_.get('misses')),
                     f(a['calc13']['pooled_pct'], 2), f(a['calc13']['unweighted_family_pct'], 2), f(o_.get('u13'), 2),
                     f(a['noncalc21']['pooled_pct'], 2), f(a['noncalc21']['unweighted_family_pct'], 2), f(o_.get('u21'), 2),
                     'n/a' if not g1 else f"{g1['correct']}/{g1['n']}"))
    A_('\n'.join(table(['model', 'pooled-5 correct', 'pooled-5 %', 'original %', 'misses', 'original misses', '13 calc % (rows)', '13 calc % (family mean)', 'original 13',
                        '21 non-calc % (rows)', '21 non-calc % (family mean)', 'original 21', 'RESULT.json via g1diag'], rows)))
    A_(f"\nThe original 13 and 21 figures are unweighted family means, so compare them with the family-mean columns. Families found in pooled-5: {A['s400']['calc13']['n_families']} calculator, "
       f"{A['s400']['noncalc21']['n_families']} other (expected 13 and 21).\n")
    cc = rep['cross_checks']['wide_pooled5']
    A_(f"WIDE cross-check: recomputed {cc['recomputed']['correct']}/{cc['recomputed']['n']} ({f(cc['recomputed']['pct'], 3)}%); readout 4429/6040 (73.328%); difference {cc['diff_rows_vs_expected']:+d} rows ({cc['diff_points_vs_expected']:+.3f} points).")
    if cc['result_json']:
        r = cc['result_json']
        A_('Against the given RESULT.json: ' + (r['error'] if 'error' in r else f"{r['correct']}/{r['n']} ({f(r['pct'], 3)}%); difference {r['diff_rows']:+d} rows ({r['diff_points']:+.3f} points)."))
    A_('\nNumbers quoted in the WIDE prompt, recomputed:\n')
    A_('\n'.join(table(['quantity', 'quoted', 'recomputed', 'difference'], [(q['name'], q['quoted'], q['recomputed'], f"{q['diff']:+d}") for q in rep['cross_checks']['quoted']])) + '\n')
    A_('### Alignment checks\n')
    A_(f"- rows per split: {al['rows_per_split']}")
    A_(f"- train sample: {json.dumps(al['train_sample'])}")
    A_(f"- rows.jsonl vs g1diag.json oracle table: {json.dumps(al['oracle_check'])}")
    A_(f"- device / precision: {al['devices']}")
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(o) + '\n')


# ---------------------------------------------------------------- main
def analyse(A, B, wide_result=None):
    info = check_alignment(A, B)
    V, meta, sub_ = model_vectors(A, B)
    runs = {'A': A, 'B': B}
    P1, P2 = part1(V, sub_), part2(runs)
    P3, P3all = part3(V, meta, POOL5), part3(V, meta, POOL5 + ['family'])
    P4 = part4(V, meta, sub_, runs)
    cc, quoted = cross_checks(P4, P3, wide_result)
    marks = build_marks(P1, P2, P3)
    wrongs = wrong_rules(P1, P2, P4)
    for name, want in (('calc13', 13), ('noncalc21', 21)):
        got = P4['s400'][name]['n_families']
        if got != want:
            info['warnings'].append(f'found {got} families in the {name} block of pooled-5, expected {want}')
    rep = dict(title='Fable test on the WIDE 10M question', scope='small card experiments only; no claim about a larger final model', marks_source='api-opinions/answers/fable-wide.md section 2',
               thresholds=M, models={m: dict(run=SOURCE[m][0], tag=SOURCE[m][1], name=NAMES[m]) for m in MODELS}, alignment=info, part1=P1, part2=P2, part3=P3, part3_all_splits=P3all,
               part4=P4, cross_checks=dict(wide_pooled5=cc, quoted=quoted), marks=marks, wrong_rules=wrongs, verdict=verdict(marks, wrongs))
    rep['claims'] = claims(rep)
    rep['summary'] = summary(rep)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--runA', required=True, help='g1diag folder: tag 3M = s400, tag 10M = deep')
    ap.add_argument('--runB', required=True, help='g1diag folder: tag 3M = s401, tag 10M = wide')
    ap.add_argument('--out', required=True)
    ap.add_argument('--result-wide', help="WIDE's RESULT.json, to cross-check its pooled-5 (4429/6040)")
    a = ap.parse_args(argv)
    try:
        rep = analyse(load_run(a.runA, 'A'), load_run(a.runB, 'B'), a.result_wide)
    except AlignmentError as e:
        sys.exit(str(e))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'FABLE-TEST.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rep, fh, indent=1)
    write_md(rep, os.path.join(a.out, 'FABLE-TEST.md'))
    print(rep['verdict']['text'], flush=True)
    for w in rep['wrong_rules']:
        print(f"  {w['id']}: {'n/a' if w['applies'] is None else 'APPLIES' if w['applies'] else 'does not apply'} | {w['value']}", flush=True)
    print('wrote FABLE-TEST.json and FABLE-TEST.md into', a.out, flush=True)
    return rep


if __name__ == '__main__':
    main()
