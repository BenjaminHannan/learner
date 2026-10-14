"""Offline analysis of res/*.pkl (no model).  python analyze.py [TAG ...]  -> analysis/<item>.json (+ prints)."""
import collections, json, os, pickle, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
import numpy as np
from probelib import *
import cf as CF

LN3 = math.log(3)
AD = f'{OUT}/analysis'
os.makedirs(AD, exist_ok=True)
C = pickle.load(open(f'{OUT}/conds.pkl', 'rb'))
for _f in ('conds_extra.pkl', 'conds_extra2.pkl'):
    if os.path.exists(f'{OUT}/{_f}'):
        C.update(pickle.load(open(f'{OUT}/{_f}', 'rb')))
ROWBY = {}
for k, v in C.items():
    for r in v:
        ROWBY.setdefault(r['id'], r)
_RES = {}


def res(tag):
    if tag not in _RES:
        R = pickle.load(open(f'{OUT}/res/{tag}.pkl', 'rb'))
        for name, full in (('gate600', 'full_logic_gate'), ('dev600', 'full_logic_dev'), ('plac600', 'full_placebo_dev')):
            if name not in R and full in R:           # the 600-row balanced subsets are subsets of the full files: select by id
                pos = {r['id']: i for i, r in enumerate(C[full])}
                ix = [pos[r['id']] for r in C[name]]
                R[name] = {k: ([v[i] for i in ix] if isinstance(v, list) else v[ix]) for k, v in R[full].items()}
                R[name]['ids'] = [r['id'] for r in C[name]]
        for pre in ('extra_', 'extra2_'):
            p = f'{OUT}/res/{pre}{tag}.pkl'
            if os.path.exists(p):
                R.update(pickle.load(open(p, 'rb')))
        _RES[tag] = R
    return _RES[tag]


def lab_of(r):
    return r['meta']['label'] if 'meta' in r else r['answer']


def pw(pred):
    p = norm(pred)
    return p if p in OPT else 'other'


class Frame:
    """Per-row view of one condition at one checkpoint."""

    def __init__(self, tag, cond):
        R = res(tag)[cond]
        self.rows = C[cond]
        self.ids = [r['id'] for r in self.rows]
        assert R['ids'] == self.ids
        self.n = len(self.rows)
        self.word = np.array([pw(p) for p in R['pred']])
        self.y = np.array([lab_of(r) for r in self.rows])
        self.depth = np.array([r['meta']['depth'] if r['meta'].get('depth') is not None else -1 for r in self.rows]) if 'meta' in self.rows[0] else np.zeros(self.n, int)
        self.lword, self.lmode = R['lword'], R['lmode']
        self.logm, self.oth = option_logmass(self.lword, [r['prompt'] for r in self.rows])
        self.ncalls = R['ncalls']
        self.mode = R['mode']
        self.idx = self.lword.argmax(1)
        self.slot = np.array([slot_of_index(r['prompt'], i) for r, i in zip(self.rows, self.idx)], dtype=object)
        self.suf = [suffix_of(r['prompt']) for r in self.rows]
        self.hit = (self.word == self.y).astype(float)
        self.id2i = {i: k for k, i in enumerate(self.ids)}

    def word_slot(self):
        """position (0,1,2) of the decoded word inside the option suffix (first occurrence), -1 if not an option."""
        return np.array([s.index(w) if w in s else -1 for s, w in zip(self.suf, self.word)])

    def gold_slot(self):
        return np.array([s.index(y) for s, y in zip(self.suf, self.y)])


# ============================================================ item 1: teacher-forced loss, gold vs shuffled labels
def item1(tag, cond, strata_by_depth=True):
    F = Frame(tag, cond)
    lab_ix = np.array([OPT.index(y) for y in F.y])
    nll = -F.logm                                      # [N,3] pointer NLL if the answer were option k (raw, training-equivalent)
    lse3 = lse(F.logm, axis=1)
    nll3 = -(F.logm - lse3[:, None])                   # renormalised over the three options
    mode_ce = -(F.lmode[:, 1] - lse(F.lmode.astype(np.float64), axis=1))
    strata = F.depth if strata_by_depth else np.zeros(F.n, int)
    out = {}

    def block(mask, name):
        if mask.sum() == 0:
            return
        sel = np.where(mask)[0]
        res_ = {'n': int(len(sel))}
        for nm, M in (('raw', nll), ('norm3', nll3)):
            gold = M[sel, lab_ix[sel]]
            # expected loss when row i is given a label drawn from its depth-stratum's label marginal (= a within-stratum label shuffle)
            exp_shuf = np.zeros(len(sel))
            for j, i in enumerate(sel):
                s = strata == strata[i]
                q = np.bincount(lab_ix[s], minlength=3) / s.sum()
                exp_shuf[j] = (q * M[i]).sum()
            d = exp_shuf - gold
            res_[nm] = dict(gold=round(float(gold.mean()), 5), gold_ci=[round(x, 5) for x in boot_ci(gold)], shuffled=round(float(exp_shuf.mean()), 5),
                            adv=round(float(d.mean()), 5), adv_ci=[round(x, 5) for x in boot_ci(d)])
        res_['acc'] = round(float(F.hit[sel].mean()), 4)
        res_['mass_on_options'] = round(float(np.exp(lse3[sel]).mean()), 5)
        res_['mode_ce'] = round(float(mode_ce[sel].mean()), 6)
        res_['mean_pmax3'] = round(float(np.exp(F.logm[sel] - lse3[sel, None]).max(1).mean()), 4)
        out[name] = res_

    block(np.ones(F.n, bool), 'all')
    for l in OPT:
        block(F.y == l, f'label={l}')
    for d in sorted(set(F.depth.tolist())):
        block(F.depth == d, f'depth={d}')
    # permutation test of the whole-set advantage (global gold-vs-shuffled-within-depth)
    rng = np.random.RandomState(0)
    gold = nll[np.arange(F.n), lab_ix].mean()
    null = []
    for _ in range(500):
        p = lab_ix.copy()
        for s in np.unique(strata):
            ix = np.where(strata == s)[0]
            p[ix] = lab_ix[rng.permutation(ix)]
        null.append(nll[np.arange(F.n), p].mean())
    out['all']['perm_p_one_sided'] = round(float((np.sum(np.array(null) <= gold) + 1) / 501), 4)
    out['ncalls_nonzero'] = int((F.ncalls > 0).sum())
    return out


# ============================================================ item 2: prediction anatomy
def item2(tag, cond, nboot=500):
    F = Frame(tag, cond)
    ws = F.word_slot()
    gs = F.gold_slot()
    sig = np.array(['/'.join(s) for s in F.suf])
    sl = np.array([str(x) for x in F.slot])
    out = dict(n=F.n, acc=round(float(F.hit.mean()), 4),
               pred_word={w: round(float((F.word == w).mean()), 4) for w in list(OPT) + ['other']},
               gold_word={w: round(float((F.y == w).mean()), 4) for w in OPT},
               pointer_target={s: round(float((sl == s).mean()), 4) for s in ['0', '1', '2', 'q', 'o']},
               pred_slot_of_decoded_word={str(k): round(float((ws == k).mean()), 4) for k in (0, 1, 2, -1)},
               gold_slot={str(k): round(float((gs == k).mean()), 4) for k in (0, 1, 2)},
               acc_by_gold_slot={str(k): round(float(F.hit[gs == k].mean()), 4) for k in (0, 1, 2)},
               acc_by_gold_word={w: round(float(F.hit[F.y == w].mean()), 4) for w in OPT})
    H = lambda a: float(-sum(p * np.log2(p) for p in np.unique(a, return_counts=True)[1] / len(a)))
    out['entropy_bits'] = dict(pred_word=round(H(F.word), 4), pred_slot=round(H(ws), 4), max=round(math.log2(3), 4))
    out['MI'] = {
        'pred_word ; gold_label': mi_report(F.word, F.y, nboot, 500),
        'pred_slot ; gold_slot': mi_report(ws, gs, nboot, 500),
        'pred_word ; suffix_order(6)': mi_report(F.word, sig, nboot, 500),
        'pred_slot ; suffix_order(6)': mi_report(ws, sig, nboot, 500),
        'pred_slot ; gold_label': mi_report(ws, F.y, nboot, 500),
        'pred_word ; gold_slot': mi_report(F.word, gs, nboot, 500),
    }
    out['hit_rate'] = dict(est=round(float(F.hit.mean()), 4), ci95=[round(x, 4) for x in boot_ci(F.hit)])
    return out


# ============================================================ item 3: counterfactuals
def cf_tables(tag, base):
    """base = 'gate' or 'plac'.  Orig predictions come from the 600-row set that holds the base rows."""
    big = 'gate600' if base == 'gate' else 'plac600'
    B = Frame(tag, big)
    base_ids = [r['id'] for r in C[f'cf_{base}_base']]
    bi = {i: B.id2i[i] for i in base_ids}
    orig_word = {i: B.word[bi[i]] for i in base_ids}
    orig_y = {i: B.y[bi[i]] for i in base_ids}
    orig_logm = {i: B.logm[bi[i]] for i in base_ids}
    orig_suf = {i: B.suf[bi[i]] for i in base_ids}
    out = {'n_base': len(base_ids), 'orig_acc': round(float(np.mean([orig_word[i] == orig_y[i] for i in base_ids])), 4),
           'orig_pred_dist': {w: round(float(np.mean([orig_word[i] == w for i in base_ids])), 4) for w in OPT}}
    rng = np.random.RandomState(1)

    def frame(cond):
        name = f'cf_{base}_{cond}'
        if name not in res(tag):
            return None
        return Frame_cf(tag, name)

    def agree_baseline(a, b, reps=200):
        """P(a[i] == b[pi(i)]) over random pairings: agreement expected if the two predictions shared nothing but their marginals."""
        a, b = np.array(a), np.array(b)
        return float(np.mean([(a == b[rng.permutation(len(b))]).mean() for _ in range(reps)]))

    def norm3(lm):
        return np.exp(lm - lse(lm))

    # (a) permutations
    P = frame('perm')
    if P:
        w0 = np.array([orig_word[b] for b in P.base])
        w1 = P.word
        s0 = np.array([orig_suf[b].index(w) if w in orig_suf[b] else -1 for b, w in zip(P.base, w0)])
        s1 = np.array([sf.index(w) if w in sf else -1 for sf, w in zip(P.suf, w1)])
        same_w, same_s = (w0 == w1).astype(float), (s0 == s1).astype(float)
        acc1 = (w1 == P.y).astype(float)
        out['perm'] = dict(n=int(P.n), word_same=round(float(same_w.mean()), 4), word_same_ci=[round(x, 4) for x in boot_ci(same_w)],
                           slot_same=round(float(same_s.mean()), 4), slot_same_ci=[round(x, 4) for x in boot_ci(same_s)],
                           word_same_row_shuffled_baseline=round(agree_baseline(w0, w1), 4),
                           slot_same_row_shuffled_baseline=round(agree_baseline(s0, s1), 4),
                           acc_orig=round(float(np.mean([orig_word[b] == orig_y[b] for b in P.base])), 4), acc_perm=round(float(acc1.mean()), 4),
                           expect_content_or_word_driven=dict(word_same=1.0, slot_same=0.2), expect_position_driven=dict(word_same=0.2, slot_same=1.0),
                           expect_noise_both='~1/3')
    # (b) entity swap
    E = frame('ent')
    if E:
        w0 = np.array([orig_word[b] for b in E.base])
        y0 = np.array([orig_y[b] for b in E.base])
        u0, u1 = (w0 == 'unknown').astype(float), (E.word == 'unknown').astype(float)
        d = u1 - u0
        soft0 = np.array([norm3(orig_logm[b])[2] for b in E.base])
        soft1 = np.array([norm3(lm)[2] for lm in E.logm])
        mv = (w0 != 'unknown')
        out['ent'] = dict(n=int(E.n), p_unknown_orig=round(float(u0.mean()), 4), p_unknown_new=round(float(u1.mean()), 4), diff=round(float(d.mean()), 4),
                          diff_ci=[round(x, 4) for x in boot_ci(d)], moved_to_unknown_of_nonunknown_orig=round(float(u1[mv].mean()), 4),
                          soft_p_unknown_orig=round(float(soft0.mean()), 4), soft_p_unknown_new=round(float(soft1.mean()), 4),
                          soft_diff_ci=[round(x, 4) for x in boot_ci(soft1 - soft0)], pred_unchanged=round(float((w0 == E.word).mean()), 4),
                          unchanged_row_shuffled_baseline=round(agree_baseline(w0, E.word), 4),
                          new_pred_dist={w: round(float((E.word == w).mean()), 4) for w in OPT},
                          expect_content_using='p_unknown_new ~ 1.0', expect_content_blind='p_unknown_new ~ p_unknown_orig')
    # (c) deletions, paired on rows having both
    S, Dd = frame('del_support'), frame('del_distractor')
    if S and Dd:
        w0s = np.array([orig_word[b] for b in S.base])
        ch_s = (S.word != w0s).astype(float)
        us = (S.word == 'unknown').astype(float)
        u0s = (w0s == 'unknown').astype(float)
        w0d = np.array([orig_word[b] for b in Dd.base])
        ch_d = (Dd.word != w0d).astype(float)
        common = [b for b in S.base if b in set(Dd.base)]
        ps = {b: ch_s[k] for k, b in enumerate(S.base)}
        pd_ = {b: ch_d[k] for k, b in enumerate(Dd.base)}
        diff = np.array([ps[b] - pd_[b] for b in common])
        soft0 = np.array([norm3(orig_logm[b])[2] for b in S.base])
        soft1 = np.array([norm3(lm)[2] for lm in S.logm])
        out['del'] = dict(n_support=int(S.n), n_distractor=int(Dd.n), n_paired=len(common),
                          change_rate_after_support_deleted=round(float(ch_s.mean()), 4), change_rate_after_distractor_deleted=round(float(ch_d.mean()), 4),
                          paired_diff=round(float(diff.mean()), 4), paired_diff_ci=[round(x, 4) for x in boot_ci(diff)],
                          p_unknown_orig_support_rows=round(float(u0s.mean()), 4), p_unknown_after_support_deleted=round(float(us.mean()), 4),
                          p_unknown_diff_ci=[round(x, 4) for x in boot_ci(us - u0s)],
                          soft_unknown_orig=round(float(soft0.mean()), 4), soft_unknown_after=round(float(soft1.mean()), 4),
                          soft_diff_ci=[round(x, 4) for x in boot_ci(soft1 - soft0)],
                          chance_change_rate_if_new_pred_independent=round(1 - agree_baseline(w0s, S.word), 4),
                          expect_content_using='change_support high (~0.7+), change_distractor ~0, p_unknown_after ~1',
                          expect_content_blind='change_support ~ change_distractor')
    # (d) negation
    N = frame('neg')
    if N:
        w0 = np.array([orig_word[b] for b in N.base])
        y0 = np.array([orig_y[b] for b in N.base])
        flip = collections.defaultdict(lambda: 'other', {'true': 'false', 'false': 'true', 'unknown': 'unknown'})
        w1 = N.word
        tf = np.isin(w0, ['true', 'false'])
        isflip = np.array([flip[a] == b for a, b in zip(w0, w1)])
        same = (w0 == w1)
        both_tf = tf & np.isin(w1, ['true', 'false'])
        yy = np.array([flip[a] for a in y0])
        tfrows = np.isin(y0, ['true', 'false'])
        out['neg'] = dict(n=int(N.n), n_orig_pred_true_false=int(tf.sum()),
                          flip_rate_given_orig_pred_TF=round(float(isflip[tf].mean()), 4), flip_ci=[round(x, 4) for x in boot_ci(isflip[tf].astype(float))],
                          unchanged_rate_given_orig_pred_TF=round(float(same[tf].mean()), 4),
                          acc_new_vs_checker=round(float((w1 == N.y).mean()), 4),
                          acc_new_on_TF_label_rows=round(float((w1 == N.y)[tfrows].mean()), 4),
                          acc_orig_same_rows=round(float(np.mean([orig_word[b] == orig_y[b] for b in N.base])), 4),
                          flip_baseline_if_new_pred_independent=round(float(np.mean([((np.array([flip[a] for a in w0]) == w1[rng.permutation(len(w1))])[tf]).mean() for _ in range(200)])), 4),
                          expect_content_using='flip ~ 1.0, unchanged ~ 0', expect_content_blind_to_negation='flip ~ 0, unchanged ~ 1')
    # (e) body swap
    Bs = frame('body_swap')
    if Bs:
        w0 = np.array([orig_word[b] for b in Bs.base])
        ag = (w0 == Bs.word).astype(float)
        dl = np.array([C_lab(Bs.rows[k]) for k in range(Bs.n)])
        s0 = np.array([orig_suf[b].index(w) if w in orig_suf[b] else -1 for b, w in zip(Bs.base, w0)])
        s1 = np.array([sf.index(w) if w in sf else -1 for sf, w in zip(Bs.suf, Bs.word)])
        out['body_swap'] = dict(n=int(Bs.n), pred_same_as_orig=round(float(ag.mean()), 4), pred_same_ci=[round(x, 4) for x in boot_ci(ag)],
                                row_shuffled_baseline=round(agree_baseline(w0, Bs.word), 4), slot_same=round(float((s0 == s1).mean()), 4),
                                acc_vs_donor_label=round(float((Bs.word == dl).mean()), 4),
                                expect_body_ignored='pred_same ~ 1.0', expect_body_used_arbitrarily='pred_same ~ baseline')
    # (f) context removed
    X = frame('ctx_removed')
    if X:
        w0 = np.array([orig_word[b] for b in X.base])
        u1 = (X.word == 'unknown').astype(float)
        u0 = (w0 == 'unknown').astype(float)
        soft0 = np.array([norm3(orig_logm[b])[2] for b in X.base])
        soft1 = np.array([norm3(lm)[2] for lm in X.logm])
        out['ctx_removed'] = dict(n=int(X.n), p_unknown_orig=round(float(u0.mean()), 4), p_unknown_new=round(float(u1.mean()), 4), diff_ci=[round(x, 4) for x in boot_ci(u1 - u0)],
                                  soft_unknown_orig=round(float(soft0.mean()), 4), soft_unknown_new=round(float(soft1.mean()), 4), soft_diff_ci=[round(x, 4) for x in boot_ci(soft1 - soft0)],
                                  new_pred_dist={w: round(float((X.word == w).mean()), 4) for w in OPT}, expect_content_using='p_unknown_new ~ 1.0')
    # (g) content-free whitespace padding, (j) sentence reorder: same words, same label -> a content reader should not change its answer
    for cond in ('pad2', 'pad6', 'reorder'):
        Q = frame(cond)
        if Q:
            w0 = np.array([orig_word[b] for b in Q.base])
            ag = (w0 == Q.word).astype(float)
            soft0 = np.array([norm3(orig_logm[b]) for b in Q.base])
            soft1 = np.array([norm3(lm) for lm in Q.logm])
            out[cond] = dict(n=int(Q.n), pred_unchanged=round(float(ag.mean()), 4), ci=[round(x, 4) for x in boot_ci(ag)],
                             row_shuffled_baseline=round(agree_baseline(w0, Q.word), 4), acc_orig=round(float(np.mean([orig_word[b] == orig_y[b] for b in Q.base])), 4),
                             acc_new=round(float((Q.word == Q.y).mean()), 4), mean_abs_change_in_option_probs=round(float(np.abs(soft1 - soft0).mean()), 4),
                             expect_content_reader='pred_unchanged ~ 1.0')
    # (h) fresh query predicate (answer unknown), (i) stated fact flipped (answer true<->false)
    Pq = frame('predswap')
    if Pq:
        w0 = np.array([orig_word[b] for b in Pq.base])
        u0, u1 = (w0 == 'unknown').astype(float), (Pq.word == 'unknown').astype(float)
        out['predswap'] = dict(n=int(Pq.n), p_unknown_orig=round(float(u0.mean()), 4), p_unknown_new=round(float(u1.mean()), 4), diff_ci=[round(x, 4) for x in boot_ci(u1 - u0)],
                               pred_unchanged=round(float((w0 == Pq.word).mean()), 4), unchanged_row_shuffled_baseline=round(agree_baseline(w0, Pq.word), 4),
                               expect_content_using='p_unknown_new ~ 1.0')
    Ff = frame('factflip')
    if Ff:
        w0 = np.array([orig_word[b] for b in Ff.base])
        y0 = np.array([orig_y[b] for b in Ff.base])
        flip = collections.defaultdict(lambda: 'other', {'true': 'false', 'false': 'true', 'unknown': 'unknown'})
        fl = np.array([flip[a] == b for a, b in zip(w0, Ff.word)])
        tf = np.isin(w0, ['true', 'false'])
        out['factflip'] = dict(n=int(Ff.n), acc_orig=round(float((w0 == y0).mean()), 4), acc_new=round(float((Ff.word == Ff.y).mean()), 4),
                               acc_new_ci=[round(x, 4) for x in boot_ci((Ff.word == Ff.y).astype(float))], pred_unchanged=round(float((w0 == Ff.word).mean()), 4),
                               flip_rate_given_orig_pred_TF=round(float(fl[tf].mean()), 4) if tf.any() else None,
                               expect_content_using='acc_new ~ 1.0, flip ~ 1.0')
    # (d2) signed effect of toggling 'not': shift of the (renormalised) option probabilities toward false minus toward true
    if N:
        qn0 = np.array([ROWBY[b]['meta']['query'].startswith('~') for b in N.base])
        p0 = np.array([norm3(orig_logm[b]) for b in N.base])
        p1 = np.array([norm3(lm) for lm in N.logm])
        shift = (p1[:, 1] - p0[:, 1]) - (p1[:, 0] - p0[:, 0])        # (P(false)-P(true)) change after the edit
        out['neg_signed'] = dict(shift_toward_false_when_not_added=round(float(shift[~qn0].mean()), 4), ci_added=[round(x, 4) for x in boot_ci(shift[~qn0])],
                                 shift_toward_false_when_not_removed=round(float(shift[qn0].mean()), 4), ci_removed=[round(x, 4) for x in boot_ci(shift[qn0])],
                                 note='a polarity-lexicon reader: positive when "not" is added, negative when removed; a content reader of the puzzle: sign depends on the row')
    return out


def C_lab(r):
    return r['answer']


class Frame_cf(Frame):
    def __init__(self, tag, cond):
        super().__init__(tag, cond)
        self.base = [r['base_id'] for r in self.rows]
        self.y = np.array([r['exp'] for r in self.rows])
        self.hit = (self.word == self.y).astype(float)


# ============================================================ item 4: is the edge real?
def feats(r):
    m = r['meta']
    facts, rules, q = CF.ck.parse_program(m['program'])
    neg, pred, ent = q
    return dict(qneg=int(neg), depth=m.get('depth'), label=m['label'], qtemplate=m['template_ids'][-1], n_dis=m.get('n_distractors'),
                n_facts=m.get('n_facts'), n_rules=m.get('n_rules'),
                ent_facts=sum(f[2] == ent for f in facts), pair_stated=int(any(f[1] == pred and f[2] == ent for f in facts)),
                pred_stated_any=int(any(f[1] == pred for f in facts)), ent_in_fact=int(any(f[2] == ent for f in facts)),
                tset=m.get('template_set'), sampler=m.get('sampler'),
                has_R5=int(any(t.startswith('R5') for t in m['template_ids'])), n_FN=sum(t.startswith('FN') for t in m['template_ids']),
                n_FP=sum(t.startswith('FP') for t in m['template_ids']), rule_kinds=''.join(sorted(t[:2] for t in m['template_ids'] if t.startswith('R'))))


def item4(tag, conds, nboot=1000):
    out = {}
    allF = []
    for cond in conds:
        F = Frame(tag, cond)
        rows = F.rows
        ft = [feats(r) for r in rows]
        Ls = np.array([len(r['prompt']) for r in rows])
        q5 = np.searchsorted(np.quantile(Ls, [.2, .4, .6, .8]), Ls, side='right')
        for f, q in zip(ft, q5):
            f['len5'] = int(q)
        gs = F.gold_slot()
        k = {'n': F.n, 'acc': round(float(F.hit.mean()), 4), 'ci95': [round(x, 4) for x in boot_ci(F.hit, nboot)]}
        # exact independence expectation from the label and prediction marginals
        py = np.array([(F.y == l).mean() for l in OPT]); pp_ = np.array([(F.word == l).mean() for l in OPT])
        k['expected_acc_if_independent'] = round(float((py * pp_).sum()), 4)
        k['edge'] = round(k['acc'] - k['expected_acc_if_independent'], 4)
        k['binom_se'] = round(float(math.sqrt(k['expected_acc_if_independent'] * (1 - k['expected_acc_if_independent']) / F.n)), 4)
        k['z'] = round(k['edge'] / k['binom_se'], 2)
        bins = {}
        for key in ('qneg', 'depth', 'qtemplate', 'n_dis', 'ent_facts', 'pair_stated', 'pred_stated_any', 'ent_in_fact', 'n_rules', 'has_R5', 'n_FN', 'n_FP'):
            vals = np.array([str(f[key]) for f in ft])
            for v in sorted(set(vals)):
                sel = vals == v
                if sel.sum() < 30 or len(set(F.y[sel])) < 2:       # a bin that fixes the label has no 'edge' to measure (reported under by_feature_value)
                    continue
                py = np.array([(F.y[sel] == l).mean() for l in OPT]); pq = np.array([(F.word[sel] == l).mean() for l in OPT])
                e = float(F.hit[sel].mean() - (py * pq).sum())
                eb = [float((lambda ix: F.hit[sel][ix].mean() - (np.array([(F.y[sel][ix] == l).mean() for l in OPT]) * np.array([(F.word[sel][ix] == l).mean() for l in OPT])).sum())(np.random.RandomState(s).randint(0, sel.sum(), sel.sum()))) for s in range(200)]
                bins[f'{key}={v}'] = dict(n=int(sel.sum()), acc=round(float(F.hit[sel].mean()), 4), edge=round(e, 4), edge_ci=[round(float(np.percentile(eb, 2.5)), 4), round(float(np.percentile(eb, 97.5)), 4)],
                                          share_of_total_edge=round(float(sel.mean() * e / max(k['edge'], 1e-9)), 3))
        k['bins'] = bins
        qn = np.array([f['qneg'] for f in ft])
        k['polarity_heuristic_acc'] = round(float(np.mean(np.where(qn == 0, F.y == 'true', F.y == 'false'))), 4)       # 'is X' -> true, 'is not X' -> false
        k['edge_within_qneg_strata'] = round(float(sum((qn == v).mean() * bins[f'qneg={v}']['edge'] for v in (0, 1) if f'qneg={v}' in bins)), 4)
        byfv = {}
        for key in ('qneg', 'pair_stated', 'ent_in_fact'):
            vals = np.array([str(f[key]) for f in ft])
            for v in sorted(set(vals)):
                sel = vals == v
                byfv[f'{key}={v}'] = dict(n=int(sel.sum()), acc=round(float(F.hit[sel].mean()), 4), gold={l: round(float((F.y[sel] == l).mean()), 3) for l in OPT},
                                         pred={l: round(float((F.word[sel] == l).mean()), 3) for l in OPT})
        k['by_feature_value'] = byfv
        k['by_label'] = {l: dict(n=int((F.y == l).sum()), recall=round(float(F.hit[F.y == l].mean()), 4)) for l in OPT}
        # which simple feature does the PREDICTION track (MI with permutation null), and does the LABEL carry it too
        mi = {}
        for key in ('len5', 'qneg', 'depth', 'qtemplate', 'ent_facts', 'pair_stated', 'pred_stated_any', 'ent_in_fact', 'n_dis', 'has_R5', 'n_FN', 'n_FP', 'rule_kinds'):
            vals = np.array([str(f[key]) for f in ft])
            r1 = mi_report(F.word, vals, 200, 200)
            r2 = mi_report(F.y, vals, 200, 200)
            mi[key] = dict(pred=dict(mi=r1['mi'], excess=r1['excess'], p=r1['p_perm']), label=dict(mi=r2['mi'], excess=r2['excess'], p=r2['p_perm']))
        k['MI_with_feature'] = mi
        k['pred_dist'] = {w: round(float((F.word == w).mean()), 4) for w in OPT}
        k['pred_dist_by_length_quintile'] = {str(q): {w: round(float((F.word[q5 == q] == w).mean()), 3) for w in OPT} for q in range(5)}
        k['acc_by_gold_slot'] = {str(s): round(float(F.hit[gs == s].mean()), 4) for s in (0, 1, 2)}
        out[cond] = k
        allF.append(F)
    # pooled over the files that carry a logic label (not placebo)
    hits = np.concatenate([F.hit for F in allF])
    out['pooled_all_files'] = dict(n=int(len(hits)), acc=round(float(hits.mean()), 4), ci95=[round(x, 4) for x in boot_ci(hits, nboot)])
    return out


def jdump(obj, name):
    json.dump(obj, open(f'{AD}/{name}.json', 'w'), indent=1, default=str)


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'item1':
        out = {}
        for tag in sys.argv[2:]:
            R = res(tag)
            out[tag] = {}
            for cond in R:
                if cond.startswith('cf_') or cond.startswith('full_logic_test') or cond.startswith('full_placebo_test'):
                    continue
                out[tag][cond] = item1(tag, cond)
        jdump(out, 'item1')
    elif what == 'item2':
        out = {}
        for tag in sys.argv[2:]:
            R = res(tag)
            out[tag] = {c: item2(tag, c) for c in R if c.startswith('full_') or c in ('gate600', 'dev600', 'plac600')}
        jdump(out, 'item2')
    elif what == 'item3':
        out = {}
        for tag in sys.argv[2:]:
            out[tag] = {b: cf_tables(tag, b) for b in ('gate', 'plac')}
        jdump(out, 'item3')
    elif what == 'item4':
        tag = sys.argv[2]
        out = {tag: item4(tag, [c for c in res(tag) if c.startswith('full_')])}
        jdump(out, 'item4_' + tag)


# ============================================================ item 2b: what explains the model's preference between the three options
def decompose(tag, cond):
    """Centre the 3 option log-masses of each row; regress them on (word identity, suffix slot, is-gold) indicators.
    R2 of each predictor alone and together; the rest is 'something else' (row-specific content the labels do not explain)."""
    F = Frame(tag, cond)
    Z = F.logm - F.logm.mean(1, keepdims=True)                 # [N,3] centred
    N = F.n
    word = np.tile(np.eye(3), (N, 1, 1))                      # [N,3,3] one-hot of option word
    slot = np.zeros((N, 3, 3))
    gold = np.zeros((N, 3, 1))
    for i in range(N):
        for k, w in enumerate(OPT):
            slot[i, k, F.suf[i].index(w)] = 1
        gold[i, OPT.index(F.y[i]), 0] = 1
    z = Z.reshape(-1)

    def r2(*blocks):
        X = np.concatenate([b.reshape(N * 3, -1) for b in blocks], 1)
        X = X - X.reshape(N, 3, -1).mean(1, keepdims=True).repeat(3, 1).reshape(N * 3, -1)      # centre within row, as z is
        beta, *_ = np.linalg.lstsq(X, z, rcond=None)
        return float(1 - ((z - X @ beta) ** 2).sum() / (z ** 2).sum())

    out = dict(n=N, sd_of_centred_logit=round(float(z.std()), 4), r2_word=round(r2(word), 4), r2_slot=round(r2(slot), 4), r2_gold=round(r2(gold), 4),
               r2_word_slot=round(r2(word, slot), 4), r2_word_slot_gold=round(r2(word, slot, gold), 4))
    out['r2_unexplained'] = round(1 - out['r2_word_slot_gold'], 4)
    # bootstrap CI of the gold-only R2 and of the gain from adding gold
    rng = np.random.RandomState(0)
    gain, g_only = [], []
    for _ in range(200):
        ix = rng.randint(0, N, N)
        zz = Z[ix].reshape(-1)
        def r2b(*blocks):
            X = np.concatenate([b[ix].reshape(N * 3, -1) for b in blocks], 1)
            X = X - X.reshape(N, 3, -1).mean(1, keepdims=True).repeat(3, 1).reshape(N * 3, -1)
            beta, *_ = np.linalg.lstsq(X, zz, rcond=None)
            return float(1 - ((zz - X @ beta) ** 2).sum() / (zz ** 2).sum())
        g_only.append(r2b(gold)); gain.append(r2b(word, slot, gold) - r2b(word, slot))
    out['r2_gold_ci'] = [round(float(np.percentile(g_only, 2.5)), 4), round(float(np.percentile(g_only, 97.5)), 4)]
    out['gain_from_gold_given_word_slot'] = round(r2(word, slot, gold) - r2(word, slot), 4)
    out['gain_ci'] = [round(float(np.percentile(gain, 2.5)), 4), round(float(np.percentile(gain, 97.5)), 4)]
    # calibrated information in the predictions: 2-fold cross-fitted temperature on the 3-way logits, nll improvement over ln 3
    lm = F.logm - lse(F.logm, axis=1)[:, None]
    y = np.array([OPT.index(v) for v in F.y])
    def nll_T(T, ix):
        l = lm[ix] / T
        l = l - lse(l, axis=1)[:, None]
        return -l[np.arange(len(ix)), y[ix]].mean()
    perm = np.random.RandomState(1).permutation(N)
    halves = [perm[:N // 2], perm[N // 2:]]
    Ts = np.exp(np.linspace(np.log(0.2), np.log(50), 120))
    imp = []
    for a, b in ((0, 1), (1, 0)):
        T = Ts[int(np.argmin([nll_T(t, halves[a]) for t in Ts]))]
        imp.append(math.log(3) - nll_T(T, halves[b]))
    out['calibrated_gain_over_ln3_nats_crossfit'] = round(float(np.mean(imp)), 5)
    out['raw_gain_over_ln3_nats'] = round(float(math.log(3) - nll_T(1.0, np.arange(N))), 5)
    return out


def calib_gain_ci(tag, cond, nboot=150, seed=0):
    """Bootstrap CI (rows resampled) of the cross-fitted, temperature-calibrated gain over ln 3 (nats/row): how much the model's three-way
    probabilities tell about the label once over-confidence is removed."""
    F = Frame(tag, cond)
    lm = F.logm - lse(F.logm, axis=1)[:, None]
    y = np.array([OPT.index(v) for v in F.y])
    Ts = np.exp(np.linspace(np.log(0.2), np.log(50), 40))

    def nll(T, ix):
        l = lm[ix] / T
        l = l - lse(l, axis=1)[:, None]
        return -l[np.arange(len(ix)), y[ix]].mean()

    def gain(ix, rng):
        p = ix[rng.permutation(len(ix))]
        h = [p[:len(p) // 2], p[len(p) // 2:]]
        g = []
        for a, b in ((0, 1), (1, 0)):
            T = Ts[int(np.argmin([nll(t, h[a]) for t in Ts]))]
            g.append(math.log(3) - nll(T, h[b]))
        return float(np.mean(g))
    rng = np.random.RandomState(seed)
    pt = np.mean([gain(np.arange(F.n), rng) for _ in range(5)])
    bs = [gain(rng.randint(0, F.n, F.n), rng) for _ in range(nboot)]
    return dict(gain=round(float(pt), 5), ci95=[round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)])


def gold_nll(tag, cond):
    F = Frame(tag, cond)
    return -F.logm[np.arange(F.n), [OPT.index(y) for y in F.y]]


def gap_ci(tag, conds_a, cond_b, nboot=2000, seed=0):
    """mean gold NLL of pooled conds_a minus cond_b, bootstrap CI (independent resampling of the two row sets).  Negative = a is lower (better fit)."""
    a = np.concatenate([gold_nll(tag, c) for c in conds_a])
    b = gold_nll(tag, cond_b)
    rng = np.random.RandomState(seed)
    d = [a[rng.randint(0, len(a), len(a))].mean() - b[rng.randint(0, len(b), len(b))].mean() for _ in range(nboot)]
    return dict(a_mean=round(float(a.mean()), 4), b_mean=round(float(b.mean()), 4), diff=round(float(a.mean() - b.mean()), 4), ci95=[round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)],
                n_a=len(a), n_b=len(b))
