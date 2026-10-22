"""Tests for fable_join.py on synthetic g1diag outputs (real key names: rows.jsonl chosen3M raw_mode3M hit3M ...; g1diag.json meta / oracle / train_loss.groups).
  python3 -m unittest -q          (from this folder)      or      python3 -I test_fable_join.py
The numbers asserted for the tiny case are worked out by hand in the comments. The large case is checked against a second, set-based implementation."""
import contextlib, io, json, math, os, random, re, subprocess, sys, tempfile, unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fable_join as fj

POOL5 = fj.POOL5
TERM_KEYS = ['total', 'prog', 'mode', 'ans', 'word', 'gen']


# ---------------------------------------------------------------- builders
def rjson(path):
    with open(path) as fh:
        return json.load(fh)


def wjson(path, obj):
    with open(path, 'w') as fh:
        json.dump(obj, fh)


def rtext(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def terms(total, gen=0.0):
    """One model's per-term loss dict, in g1diag's shape (the six terms plus the two approximate extras)."""
    return dict(total=total, prog=total / 2, mode=total / 10, ans=total / 10, word=total / 10, gen=gen, op_acc=0.9, copy_share=0.5)


def loss_set(skill_total, web_gen):
    return dict(skill=terms(skill_total, 0.01), web=terms(web_gen + 0.2, web_gen))


def write_run(d, rows, vec, blocks, params, losses, device=('cpu', 'fp32'), sample='sample-v1', k=2000, seen=None, group_n=2000, oracle=True):
    """rows: list of dict(split, id, family, gold). vec: {'3M': dict(hit, chosen, raw), '10M': ...}. losses: {'3M': loss_set, '10M': loss_set} or None."""
    os.makedirs(d)
    with open(os.path.join(d, 'rows.jsonl'), 'w') as fh:
        for i, r in enumerate(rows):
            rec = dict(id=r['id'], split=r['split'], family=r['family'], gold_mode=r['gold'])
            for tag in ('3M', '10M'):
                v = vec[tag]
                rec.update({'chosen' + tag: v['chosen'][i], 'raw_mode' + tag: v['raw'][i], 'hit' + tag: v['hit'][i], 'cand_hits' + tag: [v['hit'][i], 0, 0],
                            'cand_avail' + tag: [1, 1, 1], 'ws_gold' + tag: 0, 'ws_gold_result_slots' + tag: 0})
            fh.write(json.dumps(rec) + '\n')
    gd = dict(meta=dict(device=device[0], amp=device[1], n_reg=36, blocks=blocks, trained_params=params, max_rows=None, caps=dict(n_reg=36)))
    if oracle:
        orc = {}
        for blk, test in (('pooled5', lambda r: True), ('block13', lambda r: r['family'] in fj.B13), ('block21', lambda r: r['family'] not in fj.B13)):
            idx = [i for i, r in enumerate(rows) if r['split'] in POOL5 and test(r)]
            orc[blk] = {t: dict(n=len(idx), correct=sum(vec[t]['hit'][i] for i in idx)) for t in ('3M', '10M')}
        gd['oracle'] = orc
    if losses is not None:
        gd['train_loss'] = dict(source='/some/train.jsonl', seen=seen or dict(web=group_n, skill=group_n), k=k,
                                groups={g: dict(n=group_n, **{t: losses[t][g] for t in ('3M', '10M')}) for g in ('web', 'skill')}, note='x')
    wjson(os.path.join(d, 'g1diag.json'), gd)
    if sample is not None:
        with open(os.path.join(d, 'train_sample.jsonl'), 'w') as fh:
            fh.write(sample)


def make_case(root, rows, models, losses, **kw):
    """models: {'s400': vec, 'deep': vec, 's401': vec, 'wide': vec}; losses: {'s400': loss_set, ...}. -> (dirA, dirB)."""
    a, b = os.path.join(root, 'A'), os.path.join(root, 'B')
    write_run(a, rows, {'3M': models['s400'], '10M': models['deep']}, dict(kw.get('blocksA', {'3M': 2, '10M': 8})), {'3M': 3544913, '10M': 10496537},
              None if losses is None else {'3M': losses['s400'], '10M': losses['deep']}, **kw.get('A', {}))
    write_run(b, rows, {'3M': models['s401'], '10M': models['wide']}, {'3M': 2, '10M': 2}, {'3M': 3544913, '10M': 10173509},
              None if losses is None else {'3M': losses['s401'], '10M': losses['wide']}, **kw.get('B', {}))
    return a, b


def run_main(a, b, out, extra=()):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fj.main(['--runA', a, '--runB', b, '--out', out] + list(extra))


# ---------------------------------------------------------------- the tiny case, worked by hand
# 20 rows. Rows 0-9 arith_bare (calculator family), 10-14 seq_next (zero-coverage, non-calc), 15-19 passage_qa (non-calc). Row i is in split POOL5[i % 5].
# Misses (hit == 0):
#   s400 {8,9,10,11,12,16,17}   s401 {0,3,9,10,11,16,17}   deep {8,9,13,17}   wide {2,8,9,11,12,16,17}
TINY_MISS = {'s400': {8, 9, 10, 11, 12, 16, 17}, 's401': {0, 3, 9, 10, 11, 16, 17}, 'deep': {8, 9, 13, 17}, 'wide': {2, 8, 9, 11, 12, 16, 17}}
TINY_FAM = ['arith_bare'] * 10 + ['seq_next'] * 5 + ['passage_qa'] * 5
TINY_GOLD = [0] * 10 + [2, 2, 2, 0, 0] + [1] * 5
# rows 10-14 (seq_next): chosen / raw mode per model
TINY_CHOSEN = {'s400': [2, 2, 0, 2, 2], 's401': [2, 2, 2, 2, 2], 'deep': [2, 0, 0, 2, 2], 'wide': [2, 2, 2, 2, 0]}
TINY_RAW = {'s400': [2, 2, 0, 0, 2], 's401': [2, 2, 2, 2, 2], 'deep': [2, 0, 0, 0, 2], 'wide': [2, 2, 2, 2, 0]}


def tiny_rows():
    return [dict(split=POOL5[i % 5], id=f'{TINY_FAM[i]}-{i}', family=TINY_FAM[i], gold=TINY_GOLD[i]) for i in range(20)]


def tiny_models(miss=None):
    miss = miss or TINY_MISS
    out = {}
    for m in fj.MODELS:
        ch, raw = [2] * 20, [2] * 20
        ch[10:15], raw[10:15] = TINY_CHOSEN[m], TINY_RAW[m]
        out[m] = dict(hit=[0 if i in miss[m] else 1 for i in range(20)], chosen=ch, raw=raw)
    return out


GOOD_LOSS = {'s400': loss_set(0.08, 0.85), 'deep': loss_set(0.07, 0.86), 's401': loss_set(0.085, 0.851), 'wide': loss_set(0.09, 0.84)}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def sub(self, name):
        return os.path.join(self.root, name)

    def tiny(self, name='t', losses=GOOD_LOSS, miss=None, **kw):
        a, b = make_case(self.sub(name), tiny_rows(), tiny_models(miss), losses, **kw)
        return a, b

    def report(self, name='t', **kw):
        a, b = self.tiny(name, **kw)
        return run_main(a, b, self.sub(name + '-out'))


# ---------------------------------------------------------------- unit tests of the statistic
class TestMcNemar(unittest.TestCase):
    def test_hand_values(self):
        self.assertEqual(fj.mcnemar_exact(0, 0), 1.0)
        self.assertEqual(fj.mcnemar_exact(5, 5), 1.0)                 # b == c: the doubled tail passes 1, capped
        self.assertEqual(fj.mcnemar_exact(1, 3), 0.625)               # 2 * (1 + 4) / 16
        self.assertEqual(fj.mcnemar_exact(3, 1), 0.625)
        self.assertEqual(fj.mcnemar_exact(0, 5), 0.0625)              # 2 * 1 / 32
        self.assertEqual(fj.mcnemar_exact(2, 10), 158 / 4096)         # 2 * (1 + 12 + 66) / 4096
        self.assertEqual(fj.mcnemar_exact(1, 4), 0.375)               # 2 * (1 + 5) / 32

    def test_large_counts_do_not_overflow(self):
        self.assertEqual(fj.mcnemar_exact(0, 6000), 0.0)              # underflows to 0.0 instead of raising
        self.assertEqual(fj.mcnemar_exact(3000, 3000), 1.0)
        p = fj.mcnemar_exact(60, 100)
        self.assertTrue(0.0 < p < 0.01)


# ---------------------------------------------------------------- tiny case: exact numbers, flags
class TestTiny(Base):
    def setUp(self):
        super().setUp()
        self.rep = self.report()

    def pair(self, blk, x, b):
        return self.rep['part1'][blk][f'{x}|{b}']

    def test_pooled_pairs_by_hand(self):
        w = self.pair('pooled5', 'wide', 's400')       # both {8,9,11,12,16,17}=6 of 7; b = {2}; c = {10}
        self.assertEqual((w['misses_x'], w['misses_base'], w['both'], w['b_x_wrong_base_right'], w['c_x_right_base_wrong']), (7, 7, 6, 1, 1))
        self.assertAlmostEqual(w['overlap_pct'], 600 / 7)
        self.assertAlmostEqual(w['jaccard_pct'], 75.0)
        self.assertEqual(w['mcnemar_p'], 1.0)
        s = self.pair('pooled5', 's401', 's400')       # both {9,10,11,16,17}=5 of 7; b = {0,3}; c = {8,12}
        self.assertEqual((s['both'], s['b_x_wrong_base_right'], s['c_x_right_base_wrong']), (5, 2, 2))
        self.assertAlmostEqual(s['overlap_pct'], 500 / 7)
        self.assertAlmostEqual(s['jaccard_pct'], 500 / 9)
        d = self.pair('pooled5', 'deep', 's400')       # deep misses 4; both {8,9,17}=3; b = {13}; c = {10,11,12,16}; p = 2*(1+5)/32
        self.assertEqual((d['misses_x'], d['misses_base'], d['both'], d['b_x_wrong_base_right'], d['c_x_right_base_wrong']), (4, 7, 3, 1, 4))
        self.assertAlmostEqual(d['overlap_pct'], 75.0)
        self.assertAlmostEqual(d['jaccard_pct'], 37.5)
        self.assertEqual(d['mcnemar_p'], 0.375)
        r = self.pair('pooled5', 's400', 'deep')       # ordered pair reversed: overlap uses the other denominator, b and c swap
        self.assertAlmostEqual(r['overlap_pct'], 300 / 7)
        self.assertEqual((r['b_x_wrong_base_right'], r['c_x_right_base_wrong']), (4, 1))
        self.assertEqual(r['mcnemar_p'], 0.375)
        dd = self.pair('pooled5', 'deep', 's401')      # both {9,17}; b = {8,13}; c = {0,3,10,11,16}; n=7, p = 2*(1+7+21)/128
        self.assertEqual((dd['both'], dd['b_x_wrong_base_right'], dd['c_x_right_base_wrong']), (2, 2, 5))
        self.assertEqual(dd['mcnemar_p'], 58 / 128)

    def test_blocks_by_hand(self):
        c = self.pair('calc13', 'wide', 's400')        # calculator rows 0-9: wide misses {2,8,9}, s400 {8,9}
        self.assertEqual((c['n'], c['misses_x'], c['misses_base'], c['both']), (10, 3, 2, 2))
        self.assertAlmostEqual(c['overlap_pct'], 200 / 3)
        n = self.pair('noncalc21', 'deep', 's400')     # non-calculator rows 10-19: deep misses {13,17}, s400 {10,11,12,16,17}
        self.assertEqual((n['n'], n['misses_x'], n['misses_base'], n['both']), (10, 2, 5, 1))
        self.assertAlmostEqual(n['overlap_pct'], 50.0)
        self.assertEqual((n['b_x_wrong_base_right'], n['c_x_right_base_wrong']), (1, 4))
        self.assertAlmostEqual(self.pair('noncalc21', 's401', 's400')['overlap_pct'], 100.0)
        self.assertAlmostEqual(self.pair('noncalc21', 'wide', 's400')['overlap_pct'], 100.0)

    def test_accuracy_table(self):
        a = self.rep['part4']
        self.assertEqual((a['s400']['pooled5']['correct'], a['s400']['pooled5']['n']), (13, 20))
        self.assertAlmostEqual(a['deep']['pooled5']['pooled_pct'], 80.0)
        self.assertAlmostEqual(a['s400']['noncalc21']['pooled_pct'], 50.0)
        self.assertEqual(a['s400']['noncalc21']['n_families'], 2)
        self.assertAlmostEqual(a['s400']['noncalc21']['unweighted_family_pct'], 50.0)      # seq_next 40, passage_qa 60
        self.assertAlmostEqual(a['deep']['noncalc21']['unweighted_family_pct'], 80.0)      # 80, 80
        self.assertAlmostEqual(a['s401']['calc13']['pooled_pct'], 70.0)
        self.assertEqual(a['s400']['original']['pooled5'], 73.01)

    def test_marks_and_flags(self):
        st = {m['id']: m['status'] for m in self.rep['marks']}
        self.assertEqual(st, {'P1a': 'PASS', 'P1b': 'FAIL', 'P1c': 'PASS', 'P1c-alt': 'PASS', 'P2a': 'PASS', 'P2b': 'PASS', 'P2c': 'PASS', 'P3a': 'FAIL', 'P3a-raw': 'FAIL', 'P3b': 'FAIL'})
        by = {m['id']: m for m in self.rep['marks']}
        self.assertAlmostEqual(by['P1b']['value'], 100 / 7)                      # 85.714 - 71.429
        self.assertAlmostEqual(by['P1c']['value'], 50.0)                         # 100 - 50 (seed baseline reading)
        self.assertAlmostEqual(by['P1c-alt']['value'], 50.0)                     # 100 - 50 (WIDE reading)
        self.assertFalse(by['P1c-alt']['counted'])
        v = self.rep['verdict']
        self.assertEqual((v['e1'], v['counted'], v['passed'], v['failed']), ('NOT SUPPORTED', 8, 5, ['P1b', 'P3a', 'P3b']))
        self.assertEqual(v['wrong_rules_that_apply'], [])

    def test_part2_numbers(self):
        t = self.rep['part2']['train_loss']
        self.assertEqual(t['s400']['skill']['total'], 0.08)
        self.assertEqual(t['wide']['web']['gen'], 0.84)
        self.assertEqual(t['s400']['skill']['n'], 2000)
        d = self.rep['part2']['diff_vs_s400']
        self.assertAlmostEqual(d['deep']['skill']['total'], -0.01)
        self.assertAlmostEqual(d['wide']['web']['gen'], -0.01)
        self.assertEqual(self.rep['part2']['dev_gold_loss_pooled5']['s400'], None)      # not in the synthetic json

    def test_part3_by_hand(self):
        z = self.rep['part3']['seq_next']             # rows 10-14: gold [2,2,2,0,0]
        self.assertEqual(z['n'], 5)
        self.assertAlmostEqual(z['gold_num_pct'], 40.0)
        s4 = z['models']['s400']
        self.assertAlmostEqual(s4['call_pct'], 20.0)                  # chosen [2,2,0,2,2]
        self.assertAlmostEqual(s4['raw_num_pct'], 40.0)               # raw [2,2,0,0,2]
        self.assertAlmostEqual(s4['acc_pct'], 40.0)                   # right on rows 13, 14
        self.assertAlmostEqual(s4['false_call_pct'], 100 / 3)         # NUM chosen on row 12, where gold is not NUM
        self.assertAlmostEqual(s4['missed_call_pct'], 100.0)          # gold NUM on rows 13, 14, never chosen
        self.assertAlmostEqual(z['models']['deep']['call_pct'], 40.0)
        self.assertAlmostEqual(z['models']['s401']['call_pct'], 0.0)
        self.assertAlmostEqual(z['models']['deep']['acc_pct'], 80.0)
        self.assertEqual(self.rep['part3']['table_lookup']['n'], 0)                    # families absent from the data are n/a, not zero
        self.assertIsNone(self.rep['part3']['table_lookup']['models']['s400']['call_pct'])
        self.assertEqual(self.rep['part3']['pooled']['n'], 5)
        by = {m['id']: m for m in self.rep['marks']}
        self.assertAlmostEqual(by['P3a']['value'], 40.0)
        self.assertIn('raw_mode==0 differs', by['P3a']['note'])           # s400 raw 40 vs chosen 20: a 20 point gap is flagged
        self.assertAlmostEqual(by['P3b']['value'], 40.0)                                # deep 80 vs s400 40

    def test_wide_cross_check_default(self):
        cc = self.rep['cross_checks']['wide_pooled5']
        self.assertEqual(cc['recomputed']['correct'], 13)
        self.assertEqual(cc['diff_rows_vs_expected'], 13 - 4429)
        self.assertIsNone(cc['result_json'])

    def test_warnings_for_tiny_family_counts(self):
        w = ' '.join(self.rep['alignment']['warnings'])
        self.assertIn('found 1 families in the calc13 block', w)
        self.assertIn('found 2 families in the noncalc21 block', w)

    def test_alignment_facts(self):
        al = self.rep['alignment']
        self.assertEqual(al['n_rows'], 20)
        self.assertIn('identical', al['train_sample']['status'])
        self.assertEqual(al['oracle_check']['A']['3M/pooled5'], 'ok (13/20)')


# ---------------------------------------------------------------- flags: E3, memorisation, seed-noise-limited
class TestWrongRules(Base):
    def test_e3_schedule_limited(self):
        losses = dict(GOOD_LOSS, s400=loss_set(0.30, 0.85), deep=loss_set(0.30, 0.86), wide=loss_set(0.31, 0.84))
        rep = self.report(losses=losses)
        w = {x['id']: x for x in rep['wrong_rules']}
        self.assertTrue(w['W2']['applies'])
        st = {m['id']: m['status'] for m in rep['marks']}
        self.assertEqual((st['P2a'], st['P2b']), ('FAIL', 'PASS'))
        self.assertIn('W2', rep['verdict']['wrong_rules_that_apply'])

    def test_e3_not_when_sizes_differ(self):
        losses = dict(GOOD_LOSS, s400=loss_set(0.30, 0.85), deep=loss_set(0.30, 0.86), wide=loss_set(0.40, 0.84))
        self.assertFalse({x['id']: x for x in self.report(losses=losses)['wrong_rules']}['W2']['applies'])

    def test_memorisation_needs_both_conditions(self):
        # wide: task loss 0.10 below s400's 0.20, and wide has the same number of misses as s400 (7), so dev is unchanged. deep: loss almost the same.
        losses = dict(GOOD_LOSS, s400=loss_set(0.20, 0.85), deep=loss_set(0.19, 0.86), wide=loss_set(0.10, 0.84))
        rep = self.report(losses=losses)
        w = {x['id']: x for x in rep['wrong_rules']}['W3']
        self.assertTrue(w['applies'])
        self.assertTrue(w['detail']['wide']['both'])
        self.assertAlmostEqual(w['detail']['wide']['pooled5_gain_points'], 0.0)
        self.assertFalse(w['detail']['deep']['both'])
        self.assertFalse(w['detail']['deep']['below_by_at_least_0_05'])

    def test_memorisation_not_when_dev_moved(self):
        # deep: task loss 0.10 lower, but deep gains 15 points on dev, so dev misses are NOT unchanged
        losses = dict(GOOD_LOSS, s400=loss_set(0.20, 0.85), deep=loss_set(0.10, 0.86), wide=loss_set(0.19, 0.84))
        d = {x['id']: x for x in self.report(losses=losses)['wrong_rules']}['W3']
        self.assertFalse(d['applies'])
        self.assertTrue(d['detail']['deep']['below_by_at_least_0_05'])
        self.assertFalse(d['detail']['deep']['dev_misses_unchanged'])
        self.assertAlmostEqual(d['detail']['deep']['pooled5_gain_points'], 15.0)

    def test_memorisation_not_when_dev_got_worse(self):
        # wide: task loss 0.10 lower, but 5 more dev misses than s400 (a 25 point loss), so dev misses are not unchanged either
        losses = dict(GOOD_LOSS, s400=loss_set(0.20, 0.85), deep=loss_set(0.19, 0.86), wide=loss_set(0.10, 0.84))
        miss = dict(TINY_MISS, wide=TINY_MISS['s400'] | {0, 1, 2, 3, 4})
        w = {x['id']: x for x in self.report(losses=losses, miss=miss)['wrong_rules']}['W3']
        self.assertFalse(w['applies'])
        self.assertTrue(w['detail']['wide']['below_by_at_least_0_05'])
        self.assertFalse(w['detail']['wide']['dev_misses_unchanged'])
        self.assertAlmostEqual(w['detail']['wide']['pooled5_gain_points'], -25.0)

    def test_seed_noise_limited_overlap_below_60(self):
        miss = dict(TINY_MISS, wide={0, 1, 2, 3, 4, 5, 8})      # shares only row 8 with s400: 1/7 = 14%
        rep = self.report(miss=miss)
        w = {x['id']: x for x in rep['wrong_rules']}['W1']
        self.assertTrue(w['applies'])
        st = {m['id']: m['status'] for m in rep['marks']}
        self.assertEqual(st['P1a'], 'FAIL')
        self.assertIn('W1', rep['verdict']['wrong_rules_that_apply'])

    def test_overlap_exactly_on_a_mark(self):
        # P1a is >= 80: 4 of 5 misses shared is exactly 80.0 and must pass; W1 is < 60: 3 of 5 is exactly 60.0 and must not fire
        miss = dict(TINY_MISS, s400={8, 9, 10, 11, 12}, wide={8, 9, 10, 11, 0})
        self.assertEqual(self.report('edge80', miss=miss)['marks'][0]['status'], 'PASS')
        miss = dict(TINY_MISS, s400={8, 9, 10, 11, 12}, wide={8, 9, 10, 0, 1})
        rep = self.report('edge60', miss=miss)
        self.assertAlmostEqual(rep['part1']['pooled5']['wide|s400']['overlap_pct'], 60.0)
        self.assertFalse({x['id']: x for x in rep['wrong_rules']}['W1']['applies'])


# ---------------------------------------------------------------- the large synthetic case with real family names and counts
FAMS = [('arith_bare', 160), ('backward_solve', 160), ('chain_ops', 200), ('chain_story2', 200), ('cipher_map', 120), ('compare_numbers', 160), ('copy_word', 200),
        ('digits_parity', 160), ('distance_units', 200), ('div_exact', 200), ('fewshot_number_rule', 160), ('group_induct', 120), ('kin_chain', 200), ('letter_ops', 200),
        ('list_index', 200), ('list_stats', 160), ('object_track', 200), ('odd_one_out', 160), ('order_chain', 200), ('passage_qa', 200), ('percent_rate', 200),
        ('prop_eval', 120), ('rule_apply', 200), ('seq_cycle', 160), ('seq_next', 160), ('state_update', 200), ('story_addsub', 200), ('story_chain3', 200),
        ('syllogism', 160), ('table_calc', 200), ('table_lookup', 200), ('var_chain', 160), ('verify_claim', 120), ('word_filter', 200)]
ACC = dict(arith_bare=.89, backward_solve=.81, chain_ops=1.0, chain_story2=.93, cipher_map=.63, compare_numbers=.78, copy_word=.82, digits_parity=.46, distance_units=.85,
           div_exact=.80, fewshot_number_rule=.17, group_induct=.79, kin_chain=.89, letter_ops=.76, list_index=.60, list_stats=.56, object_track=.57, odd_one_out=.83,
           order_chain=.72, passage_qa=.67, percent_rate=.88, prop_eval=.83, rule_apply=.50, seq_cycle=.63, seq_next=.34, state_update=1.0, story_addsub=.92,
           story_chain3=1.0, syllogism=.87, table_calc=.79, table_lookup=.29, var_chain=.83, verify_claim=.79, word_filter=.63)
HELD = ['clock_date', 'op_define', 'string_transform', 'unit_convert']


def big_rows():
    rows = []
    for fam, n in FAMS:
        for si, split in enumerate(POOL5):
            for j in range(n // 5):
                gold = 0 if fam in fj.B13 else (0 if fam in fj.ZERO4 and j % 10 == 0 else 1 + j % 2)
                rows.append(dict(split=split, id=f'{fam}-{j}', family=fam, gold=gold))        # ids repeat across the five splits on purpose
    for fam in HELD:
        rows += [dict(split='family', id=f'{fam}-{j}', family=fam, gold=2) for j in range(40)]
    return rows


def flip(hit, idx, frac, rng):
    """Flip exactly round(frac * len(idx)) of the rows in idx (random, but fixed by rng)."""
    out = list(hit)
    for i in sorted(idx, key=lambda _: rng.random())[:round(frac * len(idx))]:
        out[i] ^= 1
    return out


def big_models(seed=7):
    rng = random.Random(seed)
    rows = big_rows()
    n = len(rows)
    s400 = [int(rng.random() < (ACC[r['family']] if r['split'] in POOL5 else 0.02)) for r in rows]
    pool = [i for i, r in enumerate(rows) if r['split'] in POOL5]
    z4 = [i for i in pool if rows[i]['family'] in fj.ZERO4]
    rest = [i for i in pool if rows[i]['family'] not in fj.ZERO4]
    noncalc_rest = [i for i in rest if rows[i]['family'] not in fj.B13]
    hits = dict(s400=s400,
                s401=flip(s400, pool, 0.03, rng),              # another seed: 3% of rows flip
                wide=flip(s400, rest, 0.04, rng),              # 4% flip, the four zero-coverage families untouched
                deep=flip(s400, noncalc_rest, 0.15, rng))      # depth: flips mostly in the non-calculator rows
    models = {}
    for m, h in hits.items():
        ch, raw = [2] * n, [2] * n
        for i in z4:
            if rng.random() < 0.05:
                ch[i] = 0
            raw[i] = 0 if ch[i] == 0 or rng.random() < 0.01 else 2
        models[m] = dict(hit=h, chosen=ch, raw=raw)
    return rows, models


def ref_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    t = sum(Fraction(math.factorial(n), math.factorial(i) * math.factorial(n - i)) for i in range(min(b, c) + 1))
    return float(min(Fraction(1), 2 * t / Fraction(2 ** n)))


class TestBig(Base):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.models = big_models()
        cls.tmp = tempfile.TemporaryDirectory()
        a, b = make_case(cls.tmp.name, cls.rows, cls.models, GOOD_LOSS)
        cls.rep = run_main(a, b, os.path.join(cls.tmp.name, 'out'))
        cls.out = os.path.join(cls.tmp.name, 'out')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        pass

    def test_sizes(self):
        self.assertEqual(self.rep['alignment']['n_rows'], 6200)
        self.assertEqual(len(self.rep['part1']['pooled5']), 12)
        self.assertEqual(self.rep['part1']['pooled5']['wide|s400']['n'], 6040)
        self.assertEqual(self.rep['part1']['calc13']['wide|s400']['n'], 2440)
        self.assertEqual(self.rep['part1']['noncalc21']['wide|s400']['n'], 3600)
        self.assertEqual(self.rep['alignment']['warnings'], [])           # 13 and 21 families found, model mapping fine

    def test_every_pair_matches_a_set_based_reference(self):
        rows = self.rows
        idxs = {'pooled5': [i for i, r in enumerate(rows) if r['split'] in POOL5],
                'calc13': [i for i, r in enumerate(rows) if r['split'] in POOL5 and r['family'] in fj.B13],
                'noncalc21': [i for i, r in enumerate(rows) if r['split'] in POOL5 and r['family'] not in fj.B13]}
        for blk, idx in idxs.items():
            ms = {m: {i for i in idx if self.models[m]['hit'][i] == 0} for m in fj.MODELS}
            for x in fj.MODELS:
                for b in fj.MODELS:
                    if x == b:
                        continue
                    got = self.rep['part1'][blk][f'{x}|{b}']
                    both = ms[x] & ms[b]
                    bb, cc = len(ms[x] - ms[b]), len(ms[b] - ms[x])           # x wrong & base right, x right & base wrong
                    self.assertEqual((got['misses_x'], got['misses_base'], got['both']), (len(ms[x]), len(ms[b]), len(both)), (blk, x, b))
                    self.assertEqual((got['b_x_wrong_base_right'], got['c_x_right_base_wrong']), (bb, cc), (blk, x, b))
                    self.assertAlmostEqual(got['overlap_pct'], 100 * len(both) / len(ms[x]), places=9)
                    self.assertAlmostEqual(got['jaccard_pct'], 100 * len(both) / len(ms[x] | ms[b]), places=9)
                    self.assertAlmostEqual(got['mcnemar_p'], ref_p(bb, cc), places=12)

    def test_designed_pattern_passes_every_mark(self):
        st = {m['id']: m['status'] for m in self.rep['marks']}
        self.assertEqual({k: v for k, v in st.items() if k != 'P3a-raw'}, {k: 'PASS' for k in ('P1a', 'P1b', 'P1c', 'P1c-alt', 'P2a', 'P2b', 'P2c', 'P3a', 'P3b')})
        v = self.rep['verdict']
        self.assertEqual((v['e1'], v['counted'], v['passed'], v['failed'], v['wrong_rules_that_apply']), ('SUPPORTED', 8, 8, [], []))
        p = self.rep['part1']
        self.assertGreaterEqual(p['pooled5']['wide|s400']['overlap_pct'], 80.0)
        self.assertLessEqual(abs(p['pooled5']['wide|s400']['overlap_pct'] - p['pooled5']['s401|s400']['overlap_pct']), 5.0)
        self.assertGreaterEqual(p['noncalc21']['s401|s400']['overlap_pct'] - p['noncalc21']['deep|s400']['overlap_pct'], 8.0)
        self.assertGreaterEqual(p['noncalc21']['wide|s400']['overlap_pct'] - p['noncalc21']['deep|s400']['overlap_pct'], 8.0)

    def test_seed_baseline_and_zero4_untouched(self):
        a = self.rep['part3']['pooled']
        self.assertEqual(a['n'], 720)
        for m in ('deep', 'wide'):
            self.assertEqual(a['models'][m]['acc_pct'], a['models']['s400']['acc_pct'])      # flips skipped these families for deep and wide
        self.assertLessEqual(max(a['models'][m]['call_pct'] for m in fj.MODELS), 10.0)

    def test_files_and_markdown(self):
        js = rjson(os.path.join(self.out, 'FABLE-TEST.json'))
        self.assertEqual(js['verdict']['e1'], 'SUPPORTED')
        self.assertEqual(set(js['models']), set(fj.MODELS))
        self.assertEqual(js['thresholds']['overlap_min'], 80.0)
        check_markdown(self, rtext(os.path.join(self.out, 'FABLE-TEST.md')))


def check_markdown(tc, md):
    tc.assertTrue(md.startswith('# '))
    tc.assertTrue(all(ord(c) < 128 for c in md), 'markdown must be plain ASCII (no em or en dashes)')
    tc.assertNotIn(chr(0x2014), md)
    h = [md.index(t) for t in ('## Verdict by mark', '## Claims', '## Plain-language summary for Ben (a high-school senior)', '## Limits', '## Detail tables')]
    tc.assertEqual(h, sorted(h))
    tc.assertIn('small card experiments only', md.split('## Verdict by mark')[0])        # the scope line is at the top
    claims = [ln for ln in md.split('## Claims')[1].split('## Plain-language')[0].splitlines() if ln.startswith('- ')]
    tc.assertTrue(all(re.match(r'- \*\*(shown|suggested|untested)\*\*: ', ln) for ln in claims))
    tc.assertEqual({re.match(r'- \*\*(\w+)', ln).group(1) for ln in claims}, {'shown', 'suggested', 'untested'})
    para = md.split('## Plain-language summary for Ben (a high-school senior)')[1].split('## Limits')[0].strip()
    sentences = re.split(r'(?<=[.!?])\s+', para)
    tc.assertLessEqual(len(sentences), 8, sentences)
    tc.assertGreaterEqual(len(sentences), 6)
    table = md.split('## Verdict by mark')[1].split('\n\n')[1]
    tc.assertTrue(all(row.count('|') == table.splitlines()[0].count('|') for row in table.splitlines()), 'verdict table rows must have equal column counts')
    tc.assertTrue(re.search(r'\*\*(PASS|FAIL|n-a)\*\*', table))


# ---------------------------------------------------------------- alignment errors and input checks
class TestAlignment(Base):
    def expect_error(self, a, b, text):
        out = self.sub('err-out')
        with self.assertRaises(SystemExit) as cm:
            run_main(a, b, out)
        msg = str(cm.exception)
        self.assertIn(text, msg)
        self.assertFalse(os.path.exists(out), 'nothing may be written when the inputs do not align')
        return msg

    def edit_rows(self, d, fn):
        path = os.path.join(d, 'rows.jsonl')
        recs = [json.loads(line) for line in rtext(path).splitlines()]
        recs = fn(recs)
        with open(path, 'w') as fh:
            fh.write(''.join(json.dumps(r) + '\n' for r in recs))

    def edit_json(self, d, fn):
        path = os.path.join(d, 'g1diag.json')
        gd = rjson(path)
        fn(gd)
        wjson(path, gd)

    def test_missing_row(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: recs[:-1])
        msg = self.expect_error(a, b, 'ALIGNMENT ERROR')
        self.assertIn('run A 20 rows, run B 19 rows', msg)

    def test_other_id_same_count(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: [dict(recs[0], id='zzz')] + recs[1:])
        self.expect_error(a, b, 'not hold the same (id, split, family) rows')

    def test_other_family(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: recs[:-1] + [dict(recs[-1], family='seq_next')])
        self.expect_error(a, b, 'ALIGNMENT ERROR')

    def test_other_split(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: [dict(recs[0], split='family')] + recs[1:])
        self.expect_error(a, b, 'ALIGNMENT ERROR')

    def test_other_gold_mode(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: [dict(recs[0], gold_mode=2)] + recs[1:])
        self.expect_error(a, b, 'different gold_mode')

    def test_row_order_may_differ(self):
        a, b = self.tiny()
        self.edit_rows(b, lambda recs: list(reversed(recs)))
        rep = run_main(a, b, self.sub('ok-out'))                                 # the join is by (split, id), not by position
        self.assertEqual(rep['part1']['pooled5']['wide|s400']['both'], 6)

    def test_train_sample_hash_differs(self):
        a, b = self.tiny(B=dict(sample='sample-v2'))
        self.expect_error(a, b, 'train_sample.jsonl differs')

    def test_train_sample_size_differs(self):
        a, b = self.tiny(B=dict(group_n=1500))
        self.expect_error(a, b, 'train-loss samples differ')

    def test_train_sample_unverifiable(self):
        a, b = self.tiny(A=dict(sample=None), B=dict(sample=None), )
        rep = run_main(a, b, self.sub('ok-out'))                                  # seen and k agree: allowed, but said to be unverified
        self.assertIn('not verified', rep['alignment']['train_sample']['status'])
        a, b = self.tiny('t2', A=dict(sample=None), B=dict(sample=None, seen=dict(web=99, skill=99)))
        self.expect_error(a, b, 'cannot show that the train-loss samples are the same')

    def test_sample_file_same_but_seen_differs_is_fine(self):
        a, b = self.tiny(A=dict(seen=dict(web=1400000, skill=900000)), B=dict())     # A sampled the full file, B reused the sample: same sha256
        rep = run_main(a, b, self.sub('ok-out'))
        self.assertIn('identical', rep['alignment']['train_sample']['status'])

    def test_nothing_recorded_about_the_sample(self):
        a, b = self.tiny(losses=None)
        rep = run_main(a, b, self.sub('ok-out'))
        self.assertIn('nothing recorded', rep['alignment']['train_sample']['status'])
        st = {m['id']: m['status'] for m in rep['marks']}
        self.assertEqual((st['P2a'], st['P2b'], st['P2c']), ('n-a', 'n-a', 'n-a'))
        self.assertEqual(rep['verdict']['e1'], 'NOT SUPPORTED')                  # P1b, P3a, P3b still fail: one failure is enough
        self.assertEqual(rep['verdict']['not_available'], ['P2a', 'P2b', 'P2c'])

    def test_undecided_when_nothing_fails_but_marks_are_missing(self):
        # a case that passes every mark that can be computed, without a train_loss block: UNDECIDED, not SUPPORTED
        rows, models = big_models()
        a, b = make_case(self.sub('big'), rows, models, None)
        rep = run_main(a, b, self.sub('big-out'))
        self.assertEqual(rep['verdict']['e1'], 'UNDECIDED')
        self.assertEqual(rep['verdict']['failed'], [])

    def test_rows_and_json_from_different_runs(self):
        a, b = self.tiny()
        self.edit_json(a, lambda gd: gd['oracle']['pooled5']['3M'].update(correct=14))
        self.expect_error(a, b, 'rows.jsonl and g1diag.json disagree')

    def test_missing_file(self):
        a, b = self.tiny()
        os.remove(os.path.join(b, 'g1diag.json'))
        self.expect_error(a, b, 'INPUT ERROR')

    def test_missing_pool5_split(self):
        a, b = self.tiny()
        for d in (a, b):
            self.edit_rows(d, lambda recs: [r for r in recs if r['split'] != 'vocab'])
            self.edit_json(d, lambda gd: gd.pop('oracle'))
        self.expect_error(a, b, "dev splits missing from rows.jsonl: ['vocab']")

    def test_swapped_directory_is_warned(self):
        a, b = self.tiny(blocksA={'3M': 2, '10M': 2})                              # deep checkpoint with 2 blocks: mapping looks wrong
        rep = run_main(a, b, self.sub('ok-out'))
        self.assertTrue(any('MODEL MAPPING?' in w and 'deep' in w and '2 blocks' in w for w in rep['alignment']['warnings']))

    def test_device_difference_is_warned(self):
        a, b = self.tiny(B=dict(device=('cuda', 'bf16')))
        rep = run_main(a, b, self.sub('ok-out'))
        self.assertTrue(any('differ in device/precision' in w for w in rep['alignment']['warnings']))


# ---------------------------------------------------------------- the --result-wide cross-check and the command line
class TestCli(Base):
    def test_result_wide_cross_check(self):
        a, b = self.tiny()
        res = os.path.join(self.root, 'RESULT.json')
        fe = {s: dict(correct=0, n=0) for s in POOL5}
        fe['in_dist'] = dict(correct=10, n=14)
        fe['answer'] = dict(correct=5, n=6)
        wjson(res, dict(final_eval=fe))
        rep = run_main(a, b, self.sub('o'), ['--result-wide', res])
        r = rep['cross_checks']['wide_pooled5']['result_json']
        self.assertEqual((r['correct'], r['n'], r['diff_rows']), (15, 20, 13 - 15))
        self.assertAlmostEqual(r['diff_points'], 100 * 13 / 20 - 75.0)
        self.assertIn('difference -2 rows', rtext(os.path.join(self.sub('o'), 'FABLE-TEST.md')))

    def test_unreadable_result_is_reported_not_fatal(self):
        a, b = self.tiny()
        rep = run_main(a, b, self.sub('o'), ['--result-wide', os.path.join(self.root, 'nope.json')])
        self.assertIn('error', rep['cross_checks']['wide_pooled5']['result_json'])

    def test_command_line_hygiene(self):
        a, b = self.tiny()
        out = self.sub('cli-out')
        p = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'fable_join.py'), '--runA', a, '--runB', b, '--out', out], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('NOT SUPPORTED', p.stdout)
        check_markdown(self, rtext(os.path.join(out, 'FABLE-TEST.md')))
        bad = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'fable_join.py'), '--runA', a, '--runB', self.sub('nonexistent'), '--out', self.sub('x')],
                             capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('INPUT ERROR', bad.stderr)


class TestPlainWords(Base):
    def test_no_em_dashes_anywhere_in_the_script(self):
        src = rtext(os.path.join(HERE, 'fable_join.py'))
        self.assertNotIn(chr(0x2014), src)
        self.assertNotIn(chr(0x2013), src)
        self.assertTrue(all(ord(c) < 128 for c in src))


if __name__ == '__main__':
    unittest.main(verbosity=1)
