"""Swap-pair binding probe rows (PREREG-SWAP-PROBE-2026-10-16.md). Rung-6 (R2a) format: two facts, a query, ' (a/b/c)' options.

  python -m logic_transfer.swap_probe build --train TRAIN.jsonl [--out DIR] [--seed 20261016]

A PAIR is   bound: "A is [pA]X. B is [pB]Y. Is A [q]X? (a/b/c)"      gold true / false (the query is derivable from ONE fact)
            split: "A is [pA]Y. B is [pB]X. Is A [q]X? (a/b/c)"      gold unknown   (X and Y exchanged between the facts)
Same fact order, same option order (hash of the PAIR id, shared by both members), len(X) == len(Y), X != Y, A != B, X and Y of the same word type
(nonsense / common), so the two prompts have the same characters, the same words and the same character positions except where X and Y trade places.
Strata, balanced by construction: not_rel (pA == pB 'equal' / pA != pB 'differ') x query polarity x A-fact first or second (x pA x word type).
Words come from the generator's own pools: 'dev' = the main words (what rung-6 dev uses), 'newwords' = the held-out 20% (logicgen.rungs.ENTS / COMMON /
Pool / pred_cls / ent_len). Text comes from rungs.plain_fact / plain_query, the row from rows.convert_row, the option suffix from rows.options_suffix.
WORD-MISSING controls: a bound member whose query name (sub=ent) or query property (sub=pred) is replaced by a word that is in neither fact, same length
(same type for a property); gold unknown.

Writes DIR/{dev_pairs,nw_pairs,wm}.jsonl and DIR/BUILD.json. Every gold label is the logicgen checker's (checker.run_program on the stored program) and is
compared with the label by construction and with verify_rungs' text-only re-derivation; any disagreement, any prompt of the rung-6 train file (ignoring
the option suffix), any duplicate prompt, any is_hard slip (hard.is_hard must hold on every split row and on no bound row), or any rows.verify failure
raises AssertionError and BUILD.json is not written.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter

from logicgen import checker as ck
from logicgen import rungs
from logicgen import templates as T
from logic_transfer import hard
from logic_transfer import rows as R
from logic_transfer import verify_rungs as V

SEED = 20261016
N_DEV, N_NW, N_WM = 1600, 600, 400          # pairs (dev vocabulary), pairs (newwords vocabulary), rows per word-missing kind
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replicas', 'r2a', 'swap_probe', 'rows')
WSET = {'dev': 'main', 'newwords': 'new'}                      # vocabulary -> logicgen.rungs word set
FILES = {'dev_pairs': 'dev', 'nw_pairs': 'newwords'}
MAX_TRIES = 400


def plan(n, seed, vocab):
    """n pair slots: n/2 equal-not, n/2 differ-not; inside each, the four (query polarity, A-fact first) cells are equal; pA and the word type alternate
    inside a cell (every 4 consecutive pairs of a cell hold all four combinations; the offset alternates between cells, so totals stay balanced when a cell
    is not a multiple of 4). Shuffled by a string seed."""
    assert n % 2 == 0 and (n // 2) % 4 == 0, n
    per = n // 8
    out = []
    for rel in ('equal', 'differ'):
        for c, (q_neg, a_first) in enumerate(((False, False), (False, True), (True, False), (True, True))):
            for k in range(per):
                out.append(dict(not_rel=rel, q_neg=q_neg, a_first=a_first, pA=bool((k + c) % 2), cls='nc'[(k // 2 + c // 2) % 2]))
    random.Random(f'{seed}|{vocab}|plan').shuffle(out)
    return out


def lit_text(facts, qlit):
    return ' '.join(rungs.plain_fact(f) for f in facts) + ' ' + rungs.plain_query(qlit)


def make_row(rid, pair_id, facts, qlit, split, sub, meta):
    """facts / qlit are (negated, predicate, entity) literals. The label is the checker's; the option suffix is that of the PAIR id."""
    ctx = '; '.join(f'F {ck.fmt_lit(f)}' for f in facts)
    program = f'{ctx}; Q {ck.fmt_lit(qlit)}'
    label = ck.run_program(program)
    assert label in R.OPTIONS, (rid, label)
    text = lit_text(facts, qlit)
    g = dict(id=rid, question=text, answer=label, steps=['Not enough information.'] if label == 'unknown' else [T.atom_sentence(next(f for f in facts if f[2] == qlit[2]))], program=program, label=label,
             kind='rung2', split=split, depth=0, n_rules=0, n_facts=len(facts), n_distractors=1, sampler='swap-probe', query=ck.fmt_lit(qlit), ctx=ctx,
             template_ids=['FN:0' if f[0] else 'FP:0' for f in facts] + ['Q:0'], template_set='plain', sub=sub, chars=len(text))
    r = R.convert_row(g)
    r['prompt'] += R.options_suffix(pair_id)
    r['meta'].update(meta, pair_id=pair_id)
    return r


def body(prompt):
    return V.split_options(prompt)[0]


def build_pair(i, slot, vocab, seed, banned):
    """-> (bound row, split row) of pair i. banned = bodies (prompts without the option suffix) that no row may take: the train file's and the rows so far."""
    pair_id = f'swap-{vocab}-{i:05d}'
    for t in range(MAX_TRIES):
        rng = random.Random(f'{seed}|{vocab}|{i}|{t}')
        pool = rungs.Pool(rng, WSET[vocab])
        A = pool.ent()
        B = pool.ent(avoid={A})
        X = rungs.pred_cls(pool, slot['cls'])
        Y = rungs.pred_cls(pool, slot['cls'], avoid={X}, length=len(X))
        pA = slot['pA']
        pB = pA if slot['not_rel'] == 'equal' else not pA
        qlit = (slot['q_neg'], X, A)

        def order(fa, fb):
            return [fa, fb] if slot['a_first'] else [fb, fa]
        facts = dict(bound=order((pA, X, A), (pB, Y, B)), split=order((pA, Y, A), (pB, X, B)))
        if any(body(lit_text(f, qlit)) in banned for f in facts.values()):
            continue
        meta = dict(vocab=vocab, not_rel=slot['not_rel'], q_neg=slot['q_neg'], a_first=slot['a_first'], pA=pA, pB=pB, ent_A=A, ent_B=B, prop_X=X, prop_Y=Y,
                    word_type=slot['cls'])
        split_meta = dict(name_fact='first' if slot['a_first'] else 'second', prop_fact='second' if slot['a_first'] else 'first',
                          name_fact_neg=pA, prop_fact_neg=pB)
        bound = make_row(f'{pair_id}-bound', pair_id, facts['bound'], qlit, vocab, None, dict(meta, member='bound'))
        split = make_row(f'{pair_id}-split', pair_id, facts['split'], qlit, vocab, 'split', dict(meta, member='split', **split_meta))
        return bound, split
    raise RuntimeError(f'could not build {pair_id} ({slot})')


def build_wm(src, kind, banned, seed):
    """The word-missing control of a dev BOUND row: sub=ent -> 'Is C [q]X?' (C: same-length name in neither fact); sub=pred -> 'Is A [q]Z?' (Z: same-length
    word of the type of X in neither fact). The facts are the bound member's, in its order. Gold unknown (the checker decides)."""
    m = src['meta']
    pair_id, A, B, X, Y = m['pair_id'], m['ent_A'], m['ent_B'], m['prop_X'], m['prop_Y']
    facts = [(neg, p, e.lower()) for e, neg, p in parse(src['prompt'])[0]]
    for t in range(MAX_TRIES):
        rng = random.Random(f'{seed}|wm|{kind}|{pair_id}|{t}')
        pool = rungs.Pool(rng, WSET[m['vocab']])
        if kind == 'ent':
            W = rungs.ent_len(pool, len(A), avoid={A, B})
            qlit = (m['q_neg'], X, W)
        else:
            W = rungs.pred_cls(pool, m['word_type'], avoid={X, Y}, length=len(X))
            qlit = (m['q_neg'], W, A)
        if body(lit_text(facts, qlit)) in banned:
            continue
        meta = {k: m[k] for k in ('vocab', 'not_rel', 'q_neg', 'a_first', 'pA', 'pB', 'ent_A', 'ent_B', 'prop_X', 'prop_Y', 'word_type')}
        return make_row(f'{pair_id}-wm_{kind}', pair_id, facts, qlit, m['vocab'], kind, dict(meta, member=f'wm_{kind}', absent=W, source_row=src['id']))
    raise RuntimeError(f'no absent word for {pair_id} ({kind})')


def cell(r):
    m = r['meta']
    return (m['not_rel'], m['q_neg'], m['a_first'], m['pA'])


def pick_wm(bound_rows, n):
    """n bound rows for each word-missing kind: n/16 per (not_rel, q_neg, a_first, pA) cell, split between the two word types (the type that gets the odd
    one alternates between cells), taken in pair order; the two kinds never share a pair. -> {'ent': [...], 'pred': [...]}"""
    assert n % 16 == 0, n
    k = n // 16
    cells = {}
    for r in bound_rows:
        cells.setdefault(cell(r), {'n': [], 'c': []})[r['meta']['word_type']].append(r)
    assert len(cells) == 16, len(cells)
    out = {'ent': [], 'pred': []}
    for j, c in enumerate(sorted(cells)):
        for kind, t0 in (('ent', 'nc'[j % 2]), ('pred', 'cn'[j % 2])):
            t1 = 'c' if t0 == 'n' else 'n'
            for t, m in ((t0, (k + 1) // 2), (t1, k // 2)):
                assert len(cells[c][t]) >= m, (c, t, len(cells[c][t]), m)
                out[kind] += cells[c][t][:m]
                del cells[c][t][:m]
    return out


# ---------------------------------------------------------------------------------------------------------------------------- checks


def parse(prompt):
    """Text-only parse of a probe prompt: (facts [(entity, negated, predicate)], (entity, negated, predicate) of the query, option words)."""
    b, opts = V.split_options(prompt)
    ss = [s.strip() for s in V.sentences(b)]
    q = V.QUERY.match(ss[-1])
    facts = [V.FACT.match(s) for s in ss[:-1]]
    assert q and facts and all(facts) and opts, prompt
    return [(f.group(1), bool(f.group(2)), f.group(3)) for f in facts], (q.group(1), bool(q.group(2)), q.group(3)), opts


def swap_facts(prompt, x, y):
    """The prompt with x and y exchanged in the FACTS only (the query keeps its word)."""
    k = prompt.rindex(' Is ') + 1
    return re.sub(r'\b(?:%s|%s)\b' % (x, y), lambda mm: y if mm.group(0) == x else x, prompt[:k]) + prompt[k:]


def check_labels(all_rows):
    """Gold = checker = label by construction = verify_rungs' text-only label, on every row. -> number of rows."""
    for r in all_rows:
        m = r['meta']
        assert ck.run_program(m['program']) == r['answer'] == r['accepted'][0], (r['id'], 'checker', r['answer'])
        mine, err = V.label_of(r)
        assert err is None and mine == r['answer'], (r['id'], 'verify_rungs', mine, err, r['answer'])
        if m['member'] == 'bound':
            want = 'true' if m['q_neg'] == m['pA'] else 'false'
        else:
            want = 'unknown'
        assert r['answer'] == want, (r['id'], 'by construction', r['answer'], want)
    return len(all_rows)


def check_pairs(by_pair):
    """Every pair: same characters, same words, same length, same options, same fact order, differing only by the X / Y exchange; len(X) == len(Y), X != Y,
    A != B; is_hard on the split member and not on the bound one."""
    for pid, (b, s) in by_pair.items():
        m = b['meta']
        A, B, X, Y = m['ent_A'], m['ent_B'], m['prop_X'], m['prop_Y']
        assert len(X) == len(Y) and X != Y and A != B, pid
        assert (rungs.word_class(X) == rungs.word_class(Y) == m['word_type']), pid
        assert len(b['prompt']) == len(s['prompt']) and b['prompt'] != s['prompt'], pid
        assert sorted(b['prompt']) == sorted(s['prompt']), (pid, 'characters')
        assert sorted(re.findall(r'[A-Za-z]+', b['prompt'])) == sorted(re.findall(r'[A-Za-z]+', s['prompt'])), (pid, 'words')
        assert swap_facts(b['prompt'], X, Y) == s['prompt'], (pid, 'not a pure X/Y exchange')
        diff = [k for k in range(len(b['prompt'])) if b['prompt'][k] != s['prompt'][k]]
        spans = {k for mm in re.finditer(r'\b(?:%s|%s)\b' % (X, Y), b['prompt']) for k in range(*mm.span())}
        assert set(diff) <= spans, (pid, 'characters differ outside the exchanged words')
        assert V.split_options(b['prompt'])[1] == V.split_options(s['prompt'])[1], pid
        assert b['prompt'].endswith(R.options_suffix(pid)) and s['prompt'].endswith(R.options_suffix(pid)), pid
        A, B = A.capitalize(), B.capitalize()                                     # the text capitalises names (templates.cap)
        fb, qb, _ = parse(b['prompt'])
        fs, qs, _ = parse(s['prompt'])
        assert qb == qs == (A, m['q_neg'], X), pid
        assert [(e, n) for e, n, _ in fb] == [(e, n) for e, n, _ in fs], (pid, 'fact order / polarity')
        assert [e for e, _, _ in fb][0 if m['a_first'] else 1] == A, pid
        assert dict((e, p) for e, _, p in fb) == {A: X, B: Y} and dict((e, p) for e, _, p in fs) == {A: Y, B: X}, pid
        assert not hard.is_hard(b) and hard.is_hard(s), (pid, 'is_hard', hard.is_hard(b), hard.is_hard(s))
        nf = s['meta']
        assert (nf['name_fact_neg'], nf['prop_fact_neg']) == (m['pA'], m['pB']), pid
    return len(by_pair)


def check_wm(wm_rows, bound_by_id):
    for r in wm_rows:
        m = r['meta']
        b = bound_by_id[m['source_row']]
        fb, qb, ob = parse(b['prompt'])
        fw, qw, ow = parse(r['prompt'])
        assert fb == fw and ob == ow and r['answer'] == 'unknown', r['id']
        used = {e for e, _, _ in fw} | {p for _, _, p in fw}
        if m['member'] == 'wm_ent':
            assert qw[0] not in used and len(qw[0]) == len(qb[0]) and qw[1:] == qb[1:] and qw[0] == m['absent'].capitalize(), r['id']
        else:
            assert qw[2] not in used and len(qw[2]) == len(qb[2]) and qw[:2] == qb[:2] and qw[2] == m['absent'], r['id']
            assert rungs.word_class(qw[2]) == rungs.word_class(qb[2]), r['id']
        assert not hard.is_hard(r), r['id']
        assert len(r['prompt']) == len(b['prompt']), r['id']
    return len(wm_rows)


def read(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def write_rows(path, rows):
    with open(path, 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


def counts(rows, keys):
    return {k: dict(sorted(Counter(r['meta'][k] if k in r['meta'] else r[k] for r in rows).items(), key=str)) for k in keys}


def strata(rows):
    return dict(sorted(Counter('|'.join(str(r['meta'][k]) for k in ('not_rel', 'q_neg', 'a_first', 'pA')) for r in rows).items()))


def build(train, out=OUT, seed=SEED, n_dev=N_DEV, n_nw=N_NW, n_wm=N_WM, log=print):
    """Build and check; -> the BUILD.json dict (also written). Raises AssertionError (nothing but the row files is written) when any check fails."""
    banned = {body(r['prompt']) for r in read(train)}
    n_train = len(banned)
    pairs = {}
    for vocab, n in (('dev', n_dev), ('newwords', n_nw)):
        pairs[vocab] = []
        for i, slot in enumerate(plan(n, seed, vocab)):
            b, s = build_pair(i, slot, vocab, seed, banned)
            banned.update((body(b['prompt']), body(s['prompt'])))
            pairs[vocab] += [b, s]
        log(f'{vocab}: {len(pairs[vocab]) // 2} pairs')
    dev_bound = [r for r in pairs['dev'] if r['meta']['member'] == 'bound']
    wm_rows = []
    for kind, srcs in pick_wm(dev_bound, n_wm).items():
        for src in srcs:
            r = build_wm(src, kind, banned, seed)
            banned.add(body(r['prompt']))
            wm_rows.append(r)
    log(f'wm: {len(wm_rows)} rows')
    files = {'dev_pairs': pairs['dev'], 'nw_pairs': pairs['newwords'], 'wm': wm_rows}
    every = [r for v in files.values() for r in v]

    checks = {}
    checks['labels_checked'] = check_labels(every)                              # checker, construction and verify_rungs on every row, 100%
    by_pair = {}
    for r in pairs['dev'] + pairs['newwords']:
        by_pair.setdefault(r['meta']['pair_id'], {})[r['meta']['member']] = r
    checks['pairs_checked'] = check_pairs({k: (v['bound'], v['split']) for k, v in by_pair.items()})
    checks['wm_checked'] = check_wm(wm_rows, {r['id']: r for r in dev_bound})
    ids = [r['id'] for r in every]
    assert len(set(ids)) == len(ids), 'duplicate ids'
    prompts = [r['prompt'] for r in every]
    assert len(set(prompts)) == len(prompts), 'duplicate prompts'
    bodies = [body(p) for p in prompts]
    assert len(set(bodies)) == len(bodies), 'duplicate prompts ignoring the option suffix'
    train_bodies = {body(r['prompt']) for r in read(train)}
    checks['overlap_with_train_ignoring_options'] = sum(b in train_bodies for b in bodies)
    assert checks['overlap_with_train_ignoring_options'] == 0
    checks['duplicate_prompts'] = 0
    checks['max_prompt_chars'] = max(len(p) for p in prompts)
    checks['is_hard'] = dict(split_rows=sum(hard.is_hard(r) for r in every if r['meta']['member'] == 'split'),
                             bound_rows=sum(hard.is_hard(r) for r in every if r['meta']['member'] == 'bound'), wm_rows=sum(hard.is_hard(r) for r in wm_rows))
    for name, rows_ in files.items():                                           # balance by construction: equal cells, equal pA, equal word types
        for member in {r['meta']['member'] for r in rows_}:
            sub = [r for r in rows_ if r['meta']['member'] == member]
            for rel in {r['meta']['not_rel'] for r in sub}:
                s2 = [r for r in sub if r['meta']['not_rel'] == rel]
                for key in ('q_neg', 'a_first', 'pA', 'word_type'):
                    c = Counter(r['meta'][key] for r in s2)
                    assert max(c.values()) - min(c.values()) <= 1 and len(c) == 2, (name, member, rel, key, c)
    os.makedirs(out, exist_ok=True)
    info = {}
    for name, rows_ in files.items():
        p = os.path.join(out, name + '.jsonl')
        write_rows(p, rows_)
        v = R.verify(p)                                                         # raises on any violation (length, characters, program parse, ids)
        info[name] = dict(n=len(rows_), sha256=sha256(p), verify=v, labels=dict(Counter(r['answer'] for r in rows_)),
                          members=dict(Counter(r['meta']['member'] for r in rows_)), strata_not_rel_qneg_afirst_pA={mb: strata([r for r in rows_ if r['meta']['member'] == mb]) for mb in sorted({r['meta']['member'] for r in rows_})},
                          counts=counts(rows_, ('not_rel', 'q_neg', 'a_first', 'pA', 'pB', 'word_type', 'vocab', 'sub')),
                          unknown_option_position=dict(sorted(Counter(V.split_options(r['prompt'])[1].index('unknown') for r in rows_).items())))
    checks['rows_verify'] = 'ok'
    summary = dict(probe='swap-pair binding probe', prereg='logic_transfer/PREREG-SWAP-PROBE-2026-10-16.md', seed=seed, n_pairs=dict(dev=n_dev, newwords=n_nw),
                   n_wm_per_kind=n_wm, train=dict(path=train, sha256=sha256(train), distinct_bodies=n_train), files=info, checks=checks,
                   meta_note='pA / pB / q_neg / name_fact_neg / prop_fact_neg are True when the sentence is negated ("not"); a_first = the fact about A comes first; '
                             'ent_A / ent_B / prop_X / prop_Y: bound member = "A is pA X. B is pB Y." and the query "Is A q X?"')
    with open(os.path.join(out, 'BUILD.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    return summary


# ---------------------------------------------------------------------------------------------------------------------------- score / analyze
# Behavioural readouts of the prereg (answer-word scorer; no training, CPU only). The linear probe is NOT here (it needs the controller state).

PROBE = os.path.dirname(OUT)
SCORES = os.path.join(PROBE, 'scores')
BEHAVIOUR = os.path.join(PROBE, 'BEHAVIOUR.json')
R2A = os.path.dirname(PROBE)
FEAS = '/tmp/claude-0/-home-user/25d50c87-f133-5117-867c-2334706963ac/scratchpad/feas'
HARD = os.path.join(FEAS, 'rows', 'rung6', 'hard.jsonl')
LINEAGES = ('s200', 's201', 's204')
REPLICAS = [f'{s}-s{k}' for s in LINEAGES for k in (1, 2)]
PARENTS = [f'parent-{s}' for s in LINEAGES]
CKPTS = dict([(f'parent-{s}', os.path.join(FEAS, f'T1SDR_{s}.pt')) for s in LINEAGES] + [(n, os.path.join(R2A, n, 'checkpoint.pt')) for n in REPLICAS])
SETS = ('dev_pairs', 'nw_pairs', 'wm')
BOOT_N, BOOT_SEED = 2000, 20261016
OPTS = ('true', 'false', 'unknown')
BASES = ('greedy', 'argmax')          # greedy = Tool.talk's own answer ('pred'); argmax = the best-scoring option word by logP (defined even when the greedy answer is not an option)
B_ABSENT, B_PARTLY, PTR_LOW = 0.25, 0.5, 0.65


def score(names, threads=2, rows_dir=OUT, out=SCORES, batch=64, force=False, log=print):
    """Score the probe rows with every named checkpoint -> out/<name>.jsonl (one answer_words record per row plus `set`). An existing file is kept unless force."""
    import time
    import torch
    from custom_io.data import load_rows
    from logic_transfer import answer_words as AW
    torch.set_num_threads(threads)
    os.makedirs(out, exist_ok=True)
    rows = {k: load_rows(os.path.join(rows_dir, k + '.jsonl'), keep=None) for k in SETS}
    for n in names:
        path = os.path.join(out, n + '.jsonl')
        if os.path.exists(path) and not force:
            log(f'{n}: kept {path}')
            continue
        t0 = time.time()
        m, _ = AW.load(CKPTS[n])
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:
            for k in SETS:
                for r in AW.score_rows(m, rows[k], batch):
                    f.write(json.dumps(dict(r, set=k)) + '\n')
        os.replace(tmp, path)
        log(f'{n}: {sum(len(v) for v in rows.values())} rows in {time.time() - t0:.0f}s')


def norm(s):
    return ' '.join(str(s).strip().lower().split())


def auc(pos, neg):
    """P(pos > neg) + P(tie) / 2 over all (pos, neg) pairs (Mann-Whitney), by average ranks."""
    import numpy as np
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    v, inv, cnt = np.unique(np.concatenate([pos, neg]), return_inverse=True, return_counts=True)
    rank = np.cumsum(cnt) - (cnt - 1) / 2
    r = rank[inv][:len(pos)].sum()
    return float((r - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def boot(d, n=BOOT_N, seed=BOOT_SEED):
    """mean of d and its pair-bootstrap 95% percentile CI."""
    import numpy as np
    d = np.asarray(d, float)
    idx = np.random.default_rng(seed).integers(0, len(d), (n, len(d)))
    lo, hi = np.percentile(d[idx].mean(1), [2.5, 97.5])
    return dict(mean=float(d.mean()), lo=float(lo), hi=float(hi), n=len(d))


def implied(fact, q):
    """The answer a reader gets by taking `fact` (entity, negated, predicate) to be about the query (entity, negated, predicate): true when the polarities agree."""
    return 'true' if fact[1] == q[1] else 'false'


def which_fact(items, basis):
    """items: [(prompt, record)]. Among rows where the committed answer (basis) is true / false: the fraction that equals the answer implied by (a) the fact holding the
    query NAME, (b) the fact holding the query PROPERTY, (c) the first fact, (d) the last fact. -> dict."""
    c = dict(n=len(items), n_commit=0, name=0, prop=0, first=0, last=0)
    for prompt, rec in items:
        ans = norm(rec['pred'] if basis == 'greedy' else rec['argmax'])
        if ans not in ('true', 'false'):
            continue
        facts, q, _ = parse(prompt)
        pick = dict(name=next(f for f in facts if f[0] == q[0]), prop=next(f for f in facts if f[2] == q[2]), first=facts[0], last=facts[-1])
        c['n_commit'] += 1
        for k, f in pick.items():
            c[k] += ans == implied(f, q)
    out = dict(n=c['n'], n_commit=c['n_commit'], commit_rate=c['n_commit'] / max(c['n'], 1))
    for k in ('name', 'prop', 'first', 'last'):
        out['frac_' + k] = c[k] / c['n_commit'] if c['n_commit'] else None
    return out


def readouts(rows, recs, hard_items=None):
    """All behavioural readouts of ONE checkpoint. rows: {set: [row]}; recs: {set: {id: record}}; hard_items: [(prompt, record)] of the sealed hard rows or None."""
    import numpy as np
    lp = lambda set_, rid: recs[set_][rid]['logp']['unknown']
    out = dict(p_mode={}, vocab={})
    allr = [r for k in SETS for r in recs[k].values()]
    out['p_mode'] = dict(n=len(allr), mean_word=float(np.mean([r['p_mode'][1] for r in allr])), min_word=float(min(r['p_mode'][1] for r in allr)),
                         mean_span=float(np.mean([r['p_mode'][0] for r in allr])), mean_gen=float(np.mean([r['p_mode'][2] for r in allr])),
                         greedy_mode_word=sum(r['mode'] == 1 for r in allr) / len(allr), rows_p_word_ge_099=sum(r['p_mode'][1] >= 0.99 for r in allr) / len(allr),
                         greedy_in_options=sum(norm(r['pred']) in OPTS for r in allr) / len(allr))
    for vocab, set_ in (('dev', 'dev_pairs'), ('newwords', 'nw_pairs')):
        by = {}
        for r in rows[set_]:
            by.setdefault(r['meta']['pair_id'], {})[r['meta']['member']] = r
        v = {}
        for rel in ('equal', 'differ'):
            ps = [(b, s) for b, s in ((x['bound'], x['split']) for x in by.values()) if b['meta']['not_rel'] == rel]
            d = [lp(set_, s['id']) - lp(set_, b['id']) for b, s in ps]
            v[f'B_{rel}'] = boot(d)
            v[f'B_{rel}']['frac_pairs_positive'] = float(np.mean(np.array(d) > 0))
            v[f'pointer_auc_{rel}'] = auc([lp(set_, s['id']) for b, s in ps], [lp(set_, b['id']) for b, s in ps])
            v[f'mean_lp_unknown_bound_{rel}'] = float(np.mean([lp(set_, b['id']) for b, s in ps]))
            v[f'mean_lp_unknown_split_{rel}'] = float(np.mean([lp(set_, s['id']) for b, s in ps]))
            for basis in BASES:
                key = 'pred' if basis == 'greedy' else 'argmax'
                g = lambda rid: norm(recs[set_][rid][key])
                sfx = '' if basis == 'greedy' else '_argmax'
                v[f'acc_split_{rel}{sfx}'] = float(np.mean([g(s['id']) == 'unknown' for b, s in ps]))
                v[f'u_bound_{rel}{sfx}'] = float(np.mean([g(b['id']) == 'unknown' for b, s in ps]))
                v[f'acc_bound_{rel}{sfx}'] = float(np.mean([g(b['id']) == b['answer'] for b, s in ps]))
        for basis in BASES:
            sfx = '' if basis == 'greedy' else '_argmax'
            v['u_bound' + sfx] = (v['u_bound_equal' + sfx] + v['u_bound_differ' + sfx]) / 2
            v['acc_bound' + sfx] = (v['acc_bound_equal' + sfx] + v['acc_bound_differ' + sfx]) / 2
            v['which_fact_differ_split' + sfx] = which_fact([(s['prompt'], recs[set_][s['id']]) for x in by.values() for b, s in [(x['bound'], x['split'])] if b['meta']['not_rel'] == 'differ'], basis)
        out['vocab'][vocab] = v
    # word-missing controls vs their own source bound row
    src = {r['id']: r for r in rows['dev_pairs']}
    wm = {}
    for kind in ('ent', 'pred'):
        rs = [r for r in rows['wm'] if r['meta']['member'] == 'wm_' + kind]
        d = [lp('wm', r['id']) - lp('dev_pairs', r['meta']['source_row']) for r in rs]
        wm[kind] = dict(n=len(rs), B_wm=boot(d), pointer_auc=auc([lp('wm', r['id']) for r in rs], [lp('dev_pairs', r['meta']['source_row']) for r in rs]),
                        unknown_recall=float(np.mean([norm(recs['wm'][r['id']]['pred']) == 'unknown' for r in rs])),
                        unknown_recall_argmax=float(np.mean([norm(recs['wm'][r['id']]['argmax']) == 'unknown' for r in rs])))
    out['word_missing'] = wm
    if hard_items is not None:
        h = {}
        for basis in BASES:
            sfx = '' if basis == 'greedy' else '_argmax'
            diff = [(p, r) for p, r in hard_items if len({f[1] for f in parse(p)[0]}) > 1]
            h['differ' + sfx] = which_fact(diff, basis)
            h['all' + sfx] = which_fact(hard_items, basis)
        h['greedy_unknown_acc'] = float(np.mean([norm(r['pred']) == 'unknown' for p, r in hard_items]))
        out['hard32'] = h
    return out


def read_scores(name, out=SCORES):
    recs = {k: {} for k in SETS}
    for r in read(os.path.join(out, name + '.jsonl')):
        recs[r['set']][r['id']] = r
    return recs


def hard_items(name, hard_path=HARD):
    """[(prompt, record)] of the sealed hard rows for a replica, from its answer_words/<run>.jsonl (records of set 'hard')."""
    rows = {r['id']: r for r in read(hard_path)}
    recs = {r['id']: r for r in read(os.path.join(R2A, 'answer_words', name + '.jsonl')) if r['set'] == 'hard'}
    assert set(rows) == set(recs) and len(rows) == 32, (name, len(rows), len(recs))
    return [(rows[i]['prompt'], recs[i]) for i in rows]


def calls(res):
    """The prereg's fixed calls, behavioural halves only, from the six replicas' point estimates (dev vocabulary)."""
    B = {n: res[n]['vocab']['dev']['B_equal']['mean'] for n in REPLICAS}
    P = {n: res[n]['vocab']['dev']['pointer_auc_equal'] for n in REPLICAS}
    lt, ge, pl = [n for n in REPLICAS if B[n] < B_ABSENT], [n for n in REPLICAS if B[n] >= B_PARTLY], [n for n in REPLICAS if P[n] < PTR_LOW]
    return dict(
        binding_absent=dict(rule=f'B_eq < {B_ABSENT} nats in >= 5 of 6 replicas AND probe AUC < 0.65', behavioural_half_holds=len(lt) >= 5, n_B_eq_below=len(lt), replicas=lt,
                            probe_half='pending'),
        present_not_read_out=dict(rule=f'probe AUC >= 0.75 in >= 4 of 6 replicas while pointer AUC < {PTR_LOW}',
                                  behavioural_half_holds=len(pl) >= 4, n_pointer_auc_below=len(pl), replicas_pointer_auc_below=pl, probe_half='pending (needs probe AUC >= 0.75 in >= 4 of 6, on replicas that are in this list)'),
        partly_expressed=dict(rule=f'B_eq >= {B_PARTLY} nats in >= 4 of 6 replicas', holds=len(ge) >= 4, n_B_eq_at_least=len(ge), replicas=ge, probe_half='none (fully behavioural)'),
        note='the two hold-calls need the probe AUC; instrument-broken (behavioural parts): label disagreement 0 and train overlap 0 from BUILD.json; shuffled-label and word-missing probe AUC pending',
        B_eq_dev=B, pointer_auc_eq_dev=P)


def analyze(names=None, out=SCORES, rows_dir=OUT, path=BEHAVIOUR, log=print):
    names = names or PARENTS + REPLICAS
    rows = {k: read(os.path.join(rows_dir, k + '.jsonl')) for k in SETS}
    res = {}
    for n in names:
        res[n] = readouts(rows, read_scores(n, out), hard_items(n) if n in REPLICAS else None)
    lineage = {}
    for s in LINEAGES:
        p = res[f'parent-{s}']['vocab']
        for k in (1, 2):
            r = res[f'{s}-s{k}']['vocab']
            lineage[f'{s}-s{k}'] = dict(parent=f'parent-{s}', **{f'{vo}_{m}': r[vo][m]['mean'] - p[vo][m]['mean'] if isinstance(r[vo][m], dict) else r[vo][m] - p[vo][m]
                                                                 for vo in ('dev', 'newwords') for m in ('B_equal', 'B_differ', 'acc_split_equal', 'acc_split_differ', 'pointer_auc_equal')})
    for s in LINEAGES:
        ks = [lineage[f'{s}-s{k}'] for k in (1, 2)]
        lineage[f'{s}-mean'] = {m: sum(x[m] for x in ks) / 2 for m in ks[0] if m != 'parent'}
    final = dict(prereg='logic_transfer/PREREG-SWAP-PROBE-2026-10-16.md', bootstrap=dict(resamples=BOOT_N, seed=BOOT_SEED, unit='pair', ci='percentile 95%'),
                 definitions=dict(B='mean over pairs of logP(unknown|split) - logP(unknown|bound), nats', acc_split='greedy (Tool.talk) answer == unknown on split members',
                                  u_bound='greedy answer == unknown on bound members', pointer_auc='pooled Mann-Whitney AUC of logP(unknown), split vs bound members',
                                  word_missing='B_wm / pointer_auc: word-missing row vs its own source bound row; unknown_recall: greedy answer == unknown',
                                  suffix_argmax='same with the answer = best-scoring option word by logP instead of the greedy answer',
                                  which_fact='of rows where the committed answer is true / false: fraction equal to the answer implied by the fact holding the query name / property / the first / the last fact'),
                 checkpoints=res, lineage_delta=lineage)
    if all(n in res for n in REPLICAS):
        final['calls'] = calls(res)
    with open(path, 'w') as f:
        json.dump(final, f, indent=1)
    return final


def table(final):
    """One line per checkpoint (dev vocabulary unless said): the compact readout."""
    c = ['ckpt', 'p_word', 'B_eq [95% CI]', 'B_diff', 'B_eq_nw', 'accS_eq', 'accS_diff', 'u_bound', 'acc_bound', 'wm_ent', 'wm_pred', 'AUC_eq', 'AUC_diff', 'AUC_wm_ent', 'AUC_wm_pred',
         'wf_name', 'wf_prop', 'wf_first', 'wf_last', 'n_commit', 'hard_name', 'hard_prop', 'hard_first', 'hard_last', 'hard_n']
    f = lambda x: '-' if x is None else f'{x:.2f}'
    lines = ['\t'.join(c)]
    for n, r in final['checkpoints'].items():
        v = r['vocab']['dev']
        w, h = v['which_fact_differ_split'], r.get('hard32', {}).get('differ')
        b = v['B_equal']
        lines.append('\t'.join([n, f(r['p_mode']['mean_word']), f"{b['mean']:.2f} [{b['lo']:.2f},{b['hi']:.2f}]", f(v['B_differ']['mean']), f(r['vocab']['newwords']['B_equal']['mean']),
                                f(v['acc_split_equal']), f(v['acc_split_differ']), f(v['u_bound']), f(v['acc_bound']), f(r['word_missing']['ent']['unknown_recall']),
                                f(r['word_missing']['pred']['unknown_recall']), f(v['pointer_auc_equal']), f(v['pointer_auc_differ']), f(r['word_missing']['ent']['pointer_auc']),
                                f(r['word_missing']['pred']['pointer_auc']), f(w['frac_name']), f(w['frac_prop']), f(w['frac_first']), f(w['frac_last']), str(w['n_commit']),
                                *([f(h['frac_name']), f(h['frac_prop']), f(h['frac_first']), f(h['frac_last']), str(h['n_commit'])] if h else ['-'] * 5)]))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--train', required=True, help='the rung-6 train.jsonl (no probe prompt may occur in it, ignoring the option suffix)')
    b.add_argument('--out', default=OUT)
    b.add_argument('--seed', type=int, default=SEED)
    s = sub.add_parser('score', help='score the probe rows with every checkpoint -> scores/<name>.jsonl')
    s.add_argument('--ckpt', action='append', help='checkpoint NAME (parent-s200 ... s204-s2); default all nine')
    s.add_argument('--threads', type=int, default=2)
    s.add_argument('--force', action='store_true')
    an = sub.add_parser('analyze', help='scores/*.jsonl + sealed hard answer words -> BEHAVIOUR.json and a table')
    a = ap.parse_args(argv)
    if a.cmd == 'build':
        s = build(a.train, a.out, a.seed)
        for name, info in s['files'].items():
            print(name, info['n'], info['sha256'][:12], info['labels'], info['members'])
        print(json.dumps(s['checks']))
    elif a.cmd == 'score':
        score(a.ckpt or PARENTS + REPLICAS, a.threads, force=a.force)
    else:
        final = analyze()
        print(table(final))
        print(json.dumps(final.get('calls'), indent=1))


if __name__ == '__main__':
    sys.exit(main())
