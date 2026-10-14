"""Shortcut audits for the ladder row files (LT-2 marks, Addendum 2). A cue is a feature a model could use to name the label WITHOUT doing the
task. Each audit fits a train-only lookup table on a handful of surface features and scores it on an eval file; a file is clean when every
lookup stays near the count baseline. Features are read from the converted rows (prompt text, plus the generator's stored program for logic rows).

  python -m logic_transfer.cues --rows DIR [--rungs 1 2 4 5]       (DIR as written by ladder build: DIR/rung<r>/{train,dev,...}.jsonl)

Rungs 1-2: word-TYPE cues (nonsense vs common predicate words, their sequence and match with the query predicate), length, and the label share of
the fact predicate's type. Rungs 4-5: counts of sentences, negations, rules, entities, predicates, singletons and query-word occurrences.
Word IDENTITY comparisons (does the query entity / predicate equal the fact's) are the task itself and are not cues.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict

from logic_transfer import verify_rungs as V

ATTACK12_GAIN = 3.0      # R1/R2: adding the word-type keys to a lookup may raise its accuracy by at most this many points over the same lookup without them
HOLDOUT_GAIN = 1.5       # ... and by at most this many on 20% of the train file held out of the fit (large n, so little noise)
ATTACK45_MAX = 50.0      # R4/R5 count lookups (all of K45) must stay at or under this on every eval file (a fixed answer scores 33.3; every bar is >= 55)
CLASS_SHARE_GAP = 4.0    # R1/R2: P(fact predicate is a common word | label) may differ by at most this many points between labels


def _common():
    from logicgen.lexicon import COMMON_WORDS
    return frozenset(COMMON_WORDS)


def feats12(prompt, common):
    body, _ = V.split_options(prompt)
    ss = [s.strip() for s in V.sentences(body)]
    q = V.QUERY.match(ss[-1])
    qe, qn, qp = q.group(1), bool(q.group(2)), q.group(3)
    F = []
    for s in ss[:-1]:
        m = V.FACT.match(s)
        F.append((m.group(1), bool(m.group(2)), m.group(3)))
    cls = lambda w: 'C' if w in common else 'N'
    d = dict(n=len(F), qn=qn, nneg=sum(f[1] for f in F), qcls=cls(qp), len=len(body) // 4,
             pcls_seq=''.join(cls(f[2]) for f in F) + cls(qp), pcls_match=sum(cls(f[2]) == cls(qp) for f in F),
             clsmatch_same=tuple(sorted(cls(f[2]) == cls(qp) for f in F)),
             f0cls=cls(F[0][2]))
    d['f0_cls_match'] = cls(F[0][2]) == cls(qp)
    return d


# (word-type keys, other keys): the audit compares lookup(type + other keys) with lookup(other keys alone); polarity keys (qn, nneg) and the fact count n
# carry the real count baseline of rungs 1-2, so only the GAIN from the type keys is a cue
K12 = [(('qcls',), ()), (('pcls_seq',), ()), (('pcls_seq',), ('qn', 'nneg')), (('pcls_match',), ('n',)), (('clsmatch_same',), ('n', 'qn', 'nneg')),
       (('f0_cls_match',), ('qn', 'nneg')), (('len',), ('n', 'qn', 'nneg'))]   # text length carries the negation count by itself, so it is judged beyond polarity


def feats45(r):
    from logicgen import checker as ck
    m = r['meta']
    facts, rules, q = ck.parse_program(m['program'])
    body, _ = V.split_options(r['prompt'])
    neg = len(re.findall(r"\b(?:not|never|isn't|no|none|nothing|non-\w+)\b", body, re.I))
    ents = Counter([f[2] for f in facts] + [ru.ent for ru in rules if ru.ent] + [q[2]])
    preds = Counter()
    for f in facts:
        preds[f[1]] += 1
    for ru in rules:
        for _, p in ru.lhs + (ru.rhs,):
            preds[p] += 1
    preds[q[1]] += 1
    return dict(nsent=len(m['template_ids']), neg=neg, nrules=len(rules), nent=len(ents), nsing_e=sum(v == 1 for v in ents.values()),
                npred=len(preds), nsing_p=sum(v == 1 for v in preds.values()),
                q_ent_cnt=sum(f[2] == q[2] for f in facts) + sum(ru.ent == q[2] for ru in rules), q_pred_cnt=preds[q[1]],
                q_neg=q[0], nfacts=len(facts), chars=len(body) // 8, depth=r['level'])


K45 = [('nsent',), ('neg',), ('nrules',), ('nent',), ('nsing_e',), ('npred',), ('nsing_p',), ('q_ent_cnt',), ('q_pred_cnt',), ('chars',),
       ('nsent', 'neg', 'nrules', 'nent', 'npred'), ('nsent', 'neg', 'nrules', 'nent', 'npred', 'nsing_e', 'nsing_p'),
       ('nent', 'nsing_e', 'q_ent_cnt'), ('nent', 'nsing_e', 'q_ent_cnt', 'neg', 'nrules'), ('neg', 'nrules', 'q_neg', 'q_ent_cnt', 'q_pred_cnt'),
       ('nent', 'nsing_e', 'npred', 'nsing_p', 'nsent', 'q_ent_cnt', 'q_pred_cnt')]


def lookup(train, ev, keys, by_depth=False):
    """train/ev = [(feature dict, label)]; majority label per key; unseen key -> the global majority. -> percent correct
    (by_depth=True: {depth: percent} for feature dicts that carry 'depth')."""
    tab, g = defaultdict(Counter), Counter()
    for d, l in train:
        tab[tuple(d[k] for k in keys)][l] += 1
        g[l] += 1
    gm = g.most_common(1)[0][0]
    pred = {k: c.most_common(1)[0][0] for k, c in tab.items()}
    if by_depth:
        h, n = Counter(), Counter()
        for d, l in ev:
            h[d['depth']] += pred.get(tuple(d[k] for k in keys), gm) == l
            n[d['depth']] += 1
        return {str(k): round(100.0 * h[k] / n[k], 1) for k in sorted(n)}
    return round(100.0 * sum(pred.get(tuple(d[k] for k in keys), gm) == l for d, l in ev) / max(len(ev), 1), 1)


def class_share(rows, common):
    """P(fact predicate is a common word | label) in percent (the first fact; rungs 1-2)."""
    c = defaultdict(lambda: [0, 0])
    for r in rows:
        f = feats12(r['prompt'], common)
        c[r['answer']][0] += f['f0cls'] == 'C'
        c[r['answer']][1] += 1
    return {k: round(100.0 * a / b, 1) for k, (a, b) in sorted(c.items())}


def audit(rung, d, names, train_rows=None, nmax=70000):
    """d = directory holding rung<r> files. -> dict(file -> dict(lookups..., worst, ok))."""
    def rd(name, n=None):
        out = []
        with open(f'{d}/{name}.jsonl') as fh:
            for l in fh:
                out.append(json.loads(l))
                if n and len(out) >= n:
                    break
        return out
    tr = train_rows if train_rows is not None else rd('train', nmax)
    res = {}
    if rung in (1, 2, 6):
        common = _common()
        ftr = [(feats12(r['prompt'], common), r['answer']) for r in tr]
        cut = len(ftr) - min(20000, len(ftr) // 5)
        ho = {}
        for ck_, ok_ in K12:
            key = '+'.join(ck_ + ok_)
            ho[key] = round(lookup(ftr[:cut], ftr[cut:], ck_ + ok_) - lookup(ftr[:cut], ftr[cut:], ok_), 1)
        res['train_holdout'] = dict(n=len(ftr) - cut, gain=ho, worst_gain=max(ho.values()), ok=max(ho.values()) <= HOLDOUT_GAIN)
        for name in names:
            ev = rd(name)
            fev = [(feats12(r['prompt'], common), r['answer']) for r in ev]
            lk, gain = {}, {}
            for ck_, ok_ in K12:
                key = '+'.join(ck_ + ok_)
                lk[key] = lookup(ftr, fev, ck_ + ok_)
                gain[key] = round(lk[key] - lookup(ftr, fev, ok_), 1)
            sh = class_share(ev, common)
            gap = round(max(sh.values()) - min(sh.values()), 1)
            se = 100.0 * (0.25 / max(len(fev), 1)) ** 0.5
            res[name] = dict(lookups=lk, gain=gain, worst=max(lk.values()), worst_gain=max(gain.values()), class_share=sh, class_share_gap=gap,
                             ok=max(gain.values()) <= ATTACK12_GAIN + 2 * se and gap <= CLASS_SHARE_GAP)   # + 2 standard errors of a file of this size
        res['train'] = dict(class_share=class_share(tr, common))
    else:
        ftr = [(feats45(r), r['answer']) for r in tr]
        for name in names:
            ev = rd(name)
            fev = [(feats45(r), r['answer']) for r in ev]
            lk = {','.join(k): lookup(ftr, fev, k) for k in K45}
            bd = {','.join(k): lookup(ftr, fev, k, by_depth=True) for k in K45}
            worst_depth = {dp: max(v[dp] for v in bd.values()) for dp in sorted({dp for v in bd.values() for dp in v})}
            res[name] = dict(lookups=lk, worst=max(lk.values()), worst_by_depth=worst_depth, ok=max(lk.values()) <= ATTACK45_MAX)
    return res


EVAL_FILES = {1: ['dev', 'wording', 'newwords'], 2: ['dev', 'wording', 'newwords'], 6: ['dev', 'newwords'], 4: ['dev', 'gate'], 5: ['dev', 'gate', 'deeper']}


def feats_shallow(r):
    """Rungs 4-5 (REPORT-ONLY, marks Addendum 3): the local structure around the query that needs no derivation chain. For every rule whose head is the query
    predicate (and whose entity is the query entity or universal): the head's polarity relative to the query plus a status per premise literal (G given for the
    query entity, X its complement given, D some rule concludes it, A absent); plus the polarity of every given fact about the query entity and predicate."""
    import collections
    from logicgen import checker as ck
    facts, rules, q = ck.parse_program(r['meta']['program'])
    qneg, qp, qe = q
    given = collections.defaultdict(set)
    for f in facts:
        given[f[2]].add((f[0], f[1]))

    def status(lit, ent):
        if (lit[0], lit[1]) in given[ent]:
            return 'G'
        if (not lit[0], lit[1]) in given[ent]:
            return 'X'
        if any(ru.rhs == (lit[0], lit[1]) and ru.ent in (None, ent) for ru in rules):
            return 'D'
        return 'A'
    sig = []
    for ru in rules:
        if ru.rhs[1] == qp and ru.ent in (None, qe):
            sig.append(('s' if ru.rhs[0] == qneg else 'o') + ''.join(sorted(status(l, qe) for l in ru.lhs)))
    qfact = ''.join(sorted(('s' if f[0] == qneg else 'o') for f in facts if f[1] == qp and f[2] == qe))
    return dict(depth=r['level'], sig=tuple(sorted(sig)), qfact=qfact)


def shallow_ceiling(d, names, nmax=70000):
    """What a lookup on feats_shallow (train-fitted, never following a chain) scores on each eval file, whole and by depth: the 'shallow ceiling' printed next to
    the R5 bars. A depth-2/3 accuracy above it is the only kind of number that can be read as chaining (Addendum 3)."""
    def load(n):
        out = []
        for l in open(f'{d}/{n}.jsonl'):
            if l.strip():
                r = json.loads(l)
                out.append((feats_shallow(r), r['answer']))
        return out
    tr = load('train')[:nmax]
    res = {}
    for n in names:
        ev = load(n)
        res[n] = dict(acc=lookup(tr, ev, ('sig', 'qfact')), by_depth=lookup(tr, ev, ('sig', 'qfact'), by_depth=True))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--rungs', type=int, nargs='+', default=[1, 2, 4, 5])
    ap.add_argument('--out')
    ap.add_argument('--shallow', action='store_true', help='also print the report-only shallow-reader ceiling of rungs 4-5')
    a = ap.parse_args(argv)
    allres, bad = {}, 0
    for r in a.rungs:
        res = audit(r, f'{a.rows}/rung{r}', EVAL_FILES[r])
        allres[f'rung{r}'] = res
        for name, v in res.items():
            if name == 'train':
                print(f'rung{r} train class share', v['class_share'])
                continue
            if name == 'train_holdout':
                print(f'rung{r} train hold-out ({v["n"]} rows): worst type-gain {v["worst_gain"]}  ok={v["ok"]}', flush=True)
                bad += not v['ok']
                continue
            print(f'rung{r} {name}: worst lookup {v["worst"]}' + (f'  worst type-gain {v["worst_gain"]}  class share {v["class_share"]}' if 'class_share' in v else '')
                  + (f'  worst by depth {v["worst_by_depth"]}' if 'worst_by_depth' in v else '') + f'  ok={v["ok"]}', flush=True)
            bad += not v['ok']
    if a.shallow:
        for r in a.rungs:
            if r in (4, 5):
                allres[f'rung{r}_shallow_ceiling'] = shallow_ceiling(f'{a.rows}/rung{r}', EVAL_FILES[r])
                print(f'rung{r} shallow-reader ceiling (report only):', json.dumps(allres[f'rung{r}_shallow_ceiling']), flush=True)
    if a.out:
        json.dump(allres, open(a.out, 'w'), indent=1)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
