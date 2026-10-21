"""python3 -m custom_io.tests.test_english   (CPU, under a minute; no skills data needed)
Test B1 english.py: scorer norm, rows, taught string, atype, clean-up drops, overlap guard, held-out grouping, parity cut, judged donor pairs,
eval_english on a fake span model (state / talk contract) and on PlainTF, plus the span-mode Ledger checks when models/ledger.py has `span`."""
import shutil, collections, contextlib, hashlib, json, os, tempfile, time
import torch
import torch.nn as nn
from custom_io import english as E
from custom_io.data import ASCII, CharVocab, word_spans
from custom_io.evalx import donor_pairs, evaluate

EVAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'english_eval')
# fingerprints of the eval rows (id, prompt, taught answer, atype) and the numbers the spec expects, taken with this file's first version
GOLD = {'fresh': ('01dab9bc3155517f2be4ab369b8a46b6225bf48c', dict(span1=54, spanN=114, yes_no=22, nonspan=2)),
        'new_r5': ('657857321baf6e28c4646ef9611c12e4859ea764', dict(span1=58, spanN=110, yes_no=24)),
        'new_r6': ('0748d8eb288a140b3b1edba77d32a78904c0f49b', dict(span1=58, spanN=114, yes_no=20)),
        'gen_heldout': ('266c7387df2bf407914a9f6fff3d7016eef4d91f', dict(span1=34, spanN=140, yes_no=16, nonspan=2))}
GOLD_SKIPPED = {'new_pooled': 8, 'fresh': 2}


def test_en_norm():
    cases = {'  Hello  World.!  ': 'hello world', 'It’s': "it's", '‘Hi’': "'hi'", 'A B': 'a b', 'Yes.': 'yes', 'x ; :': 'x ;',
             'Café': 'café', 'a.b': 'a.b', '...': '', 'to  Hale?': 'to hale', 'Dax,': 'dax'}
    for a, b in cases.items():
        assert E.en_norm(a) == b, (a, E.en_norm(a), b)
    assert E.clean('“a” – b — c d ‘e’') == '"a" - b - c d \'e\''
    assert E.clean('Café') == 'café'.replace('caf', 'Caf')
    print('ok en_norm')


def test_word_runs_and_taught():
    p = 'The light doll is bigger than the long doll. Which doll is smaller?'
    assert E.word_runs(p, 'doll') == [(2, 2), (8, 8), (8, 9), (11, 11)]      # 'doll' + '.' is a run too: its norm drops the full stop
    ws = word_spans(p)
    for s, e in E.word_runs(p, 'light doll'):
        assert E.en_norm(p[ws[s][0]:ws[e][1]]) == 'light doll'
    assert E.word_runs(p, 'light doll') == [(1, 2)]
    assert E.word_runs(p, 'nothing here') == [] and E.word_runs(p, '') == []
    assert E.word_runs(p, 'the light doll', span_max=2) == [] and E.word_runs(p, 'the light doll', span_max=3) == [(0, 2)]
    assert E.word_runs(p, 'the light doll', w_max=2) == []
    # trailing punctuation token: 'doll' + '.' normalises to 'doll', so both runs are listed
    assert E.word_runs('See Dax.', 'dax') == [(1, 1), (1, 2)]
    # taught string: yes/no -> canonical; first candidate that is a run; else canonical
    assert E.taught_answer(p, 'No', ['No']) == 'No'
    assert E.taught_answer('Dax tossed it to Hale. To whom?', 'Hale', ['Hale', 'to Hale']) == 'Hale'
    assert E.taught_answer('Dax tossed it to Hale. To whom?', 'hale!', ['to Hale']) == 'hale!'
    assert E.taught_answer('Dax gave it to Hale. To whom?', 'Remo', ['to Hale', 'Hale']) == 'to Hale'          # accepted-only form
    assert E.taught_answer('Dax gave it. Who?', 'two', ['2']) == 'two'                                        # absent: canonical
    assert E.taught_answer('Tev packed 2 plums. How many?', 'two', ['2', 'two']) == '2'
    assert E.taught_answer('Is it yes or no? yes', 'No', ['No']) == 'No'                                      # never a span
    print('ok word_runs / taught_answer')


def test_atype_and_rows():
    ex = [dict(id='e1', family='f', source_text='Dax tossed a plum to Hale.', paraphrase='A plum was tossed to Hale by Dax.',
               questions=[dict(question='To whom did Dax toss the plum?', type='short_answer', canonical_answer='Hale', accepted_answers=['Hale', 'to Hale']),
                          dict(question='Did Dax toss a plum?', type='yes_no', canonical_answer='Yes', accepted_answers=['Yes']),
                          dict(question='Which fruit, in two words?', type='short_answer', canonical_answer='a plum', accepted_answers=['plum']),
                          dict(question='How many?', type='short_answer', canonical_answer='one', accepted_answers=['1'])])]
    rows = E.qa_rows(ex)
    assert [r['id'] for r in rows] == [f'e1-{p}-q{q}' for p in ('source_text', 'paraphrase') for q in range(4)]
    r = rows[0]
    assert r['prompt'] == 'Dax tossed a plum to Hale. To whom did Dax toss the plum?' and r['accepted'] == ['Hale', 'to Hale'] and r['answer'] == 'Hale'
    assert [x['atype'] for x in rows[:4]] == ['span1', 'yes_no', 'spanN', 'nonspan'] and rows[1]['answer'] == 'Yes'
    assert rows[2]['answer'] == 'a plum' and rows[2]['canonical'] == 'a plum' and rows[2]['level'] == 0 and rows[2]['panel'] == 'source_text'
    assert rows[4]['prompt'].startswith('A plum was tossed') and rows[4]['panel'] == 'paraphrase'
    S = E.eval_sets(EVAL)
    for k, (h, ac) in GOLD.items():
        R = S[k]
        assert len(R) == 192 and len({r['id'] for r in R}) == 192
        assert hashlib.sha1(json.dumps([(r['id'], r['prompt'], r['answer'], r['atype']) for r in R]).encode()).hexdigest() == h, k
        assert dict(collections.Counter(r['atype'] for r in R)) == ac, (k, collections.Counter(r['atype'] for r in R))
        assert [r['id'].rsplit('-q', 1)[0] for r in R[:4]] == [R[0]['ex'] + '-source_text'] * 2 + [R[0]['ex'] + '-paraphrase'] * 2
    assert S['new_pooled'] == S['new_r5'] + S['new_r6'] and len(S['new_pooled']) == 384
    print('ok rows / atype (matches round 6 on all 768 eval rows)')


def test_judged_donor_pairs():
    S = E.eval_sets(EVAL)
    for k, skip in GOLD_SKIPPED.items():
        R = S[k]
        P, sk = E.judged_pairs(R)
        assert sk == skip and len(P) + sk == len(R), (k, sk)
        assert E.judged_pairs(R) == (P, sk)                                                  # seeded
        assert [i for i, _ in P] == sorted({i for i, _ in P})                                # rows in rows_of order
        for i, j in P:
            ri, rj = R[i], R[j]
            acc = {E.en_norm(a) for a in ri['accepted']}
            assert (ri['family'], ri['type']) == (rj['family'], rj['type'])                    # never crosses kind or question type
            assert E.en_norm(rj['canonical']) not in acc
            ws = word_spans(ri['prompt'])
            for s, e in E._taught_runs(rj):                                                  # never coincide by position
                assert e >= len(ws) or E.en_norm(ri['prompt'][ws[s][0]:ws[e][1]]) not in acc, (ri['id'], rj['id'])
        plain, _ = donor_pairs(R, 0, E.en_norm)                                              # the read-only pairing may cross question types
        assert len(plain) >= len(P)
    print('ok judged donor pairs')


def _example(i, names=('Dax', 'Hale', 'Tev', 'Remo', 'Zani', 'Tira', 'Dani', 'Mika', 'Pell', 'Orin'), **kw):
    a, b = names[i % 10], names[(i * 3 + 1) % 10]
    if a == b:
        b = names[(i + 5) % 10]
    tag = ''.join('abcdefghij'[int(c)] for c in str(i)) + 'x'
    obj = f'{tag} bottle'
    ex = dict(id=f'ex{i}', family=kw.get('family', 'giver_recipient_roles'),
              source_text=f'At the beach, {a} gave the {obj} to {b}.', paraphrase=f'At the beach, {b} got the {obj} from {a}.',
              questions=[dict(question=f'Who gave the {obj}?', type='short_answer', canonical_answer=a, accepted_answers=[a, f'{a} did']),
                         dict(question=f'Did {a} give the {obj}?', type='yes_no', canonical_answer='Yes', accepted_answers=['Yes'])])
    return ex


def _write(path, examples, jsonl=False):
    with open(path, 'w') as f:
        if jsonl:
            f.writelines(json.dumps(e) + '\n' for e in examples)
        else:
            json.dump({'examples': examples}, f)


def test_load_and_cleanup():
    with tempfile.TemporaryDirectory() as d:
        ex = [_example(i) for i in range(3)]
        for name, jl in (('a.json', False), ('b.jsonl', True)):
            _write(os.path.join(d, name), ex, jl)
            assert E.load_examples(os.path.join(d, name)) == ex
        json.dump(ex, open(os.path.join(d, 'c.json'), 'w'))
        assert E.load_examples(os.path.join(d, 'c.json')) == ex
        bad = [_example(0), _example(1), _example(2), _example(3), _example(4), _example(5)]
        bad[0]['questions'][0]['question'] = 'Who gave the “bottle” – really?'                  # fixed by clean-up, kept
        bad[0]['questions'][0]['canonical_answer'] = bad[0]['questions'][0]['accepted_answers'][0] = 'Dax'
        bad[1]['source_text'] = 'At the café, Hale gave a thing to Dax.'                         # non-ASCII: both rows of that panel dropped
        bad[2]['questions'][0]['question'] = 'Who gave it? ' + 'x' * 210                         # prompt over 208
        bad[3]['questions'][0]['canonical_answer'] = ' '                                         # empty taught answer
        bad[3]['questions'][0]['accepted_answers'] = []
        bad[4]['questions'][0]['canonical_answer'] = 'q' * 33                                    # taught answer over 32
        bad[4]['questions'][0]['accepted_answers'] = ['q' * 33]
        bad[5]['questions'][1]['accepted_answers'] = ['Yes', 'Ye s']                        # nbsp -> space, kept
        p = os.path.join(d, 'x.json')
        _write(p, bad)
        a = E.prepare_arm(p)
        kept = {r['id'] for e in a['examples'] for r in e['rows']}
        assert 'ex0-source_text-q0' in kept and all('“' not in r['prompt'] and '–' not in r['prompt'] for e in a['examples'] for r in e['rows'])
        assert 'ex1-source_text-q0' not in kept and 'ex1-paraphrase-q0' in kept and 'ex1-source_text-q1' not in kept
        assert not {'ex2-source_text-q0', 'ex2-paraphrase-q0', 'ex3-source_text-q0', 'ex4-source_text-q0'} & kept and 'ex2-source_text-q1' in kept
        assert all(r['accepted'] == list(dict.fromkeys(r['accepted'])) and all(set(c) <= ASCII for c in r['accepted']) for e in a['examples'] for r in e['rows'])
        assert a['drops']['prompt_over_208'] == 2 and a['drops']['answer_empty'] == 2 and a['drops']['answer_over_32'] == 2 and a['drops']['not_printable_ascii'] == 2
        assert a['steps'][0]['rows'] == 6 * 4 and a['steps'][1]['rows'] == 6 * 4 - sum(a['drops'].values())
        assert a['drops_by_kind'] == {'giver_recipient_roles': sum(a['drops'].values())}
    print('ok load / clean-up drops')


def _build(d, teach, gen, **kw):
    _write(os.path.join(d, 't.jsonl'), teach, True)
    _write(os.path.join(d, 'g.jsonl'), gen, True)
    return E.build_pair(os.path.join(d, 't.jsonl'), os.path.join(d, 'g.jsonl'), os.path.join(d, 'out'), EVAL, **kw)


def _read(path):
    return [json.loads(l) for l in open(path)]


def test_build_guard_split_parity():
    with tempfile.TemporaryDirectory() as d:
        teach = [_example(i) for i in range(300)]
        gen = [_example(1000 + i, family='other') for i in range(450)]
        # a stock question equal to an eval question is counted, not dropped
        fresh = E.load_examples(os.path.join(EVAL, 'FRESH-EN-R3.json'))
        stock = fresh[0]['questions'][0]['question']
        teach[5]['questions'][0]['question'] = stock
        # two examples that share a passage must land on the same side of the held-out split
        for k in (11, 12):
            teach[k]['paraphrase'] = teach[10]['paraphrase']
        man = _build(d, teach, gen)
        t, g = (os.path.join(d, 'out', n) for n in ('teach', 'gen'))
        rt, rg = _read(os.path.join(t, 'train.jsonl')), _read(os.path.join(g, 'train.jsonl'))
        assert len(rt) == len(rg) and man['teach']['steps'][-1]['rows'] == len(rt) == man['gen']['steps'][-1]['rows']
        assert [s['step'] for s in man['teach']['steps']] == ['source', 'clean_up', 'overlap_guard', 'heldout_split', 'parity_cut']
        assert man['teach']['steps'][-2]['rows'] != man['gen']['steps'][-2]['rows'] and man['gen']['steps'][-1]['target'] == len(rt)
        for a, rows in (('teach', rt), ('gen', rg)):
            ho = _read(os.path.join(d, 'out', a, 'dev', 'in_dist.jsonl'))
            ids = [r['id'] for r in rows] + [r['id'] for r in ho]
            assert len(ids) == len(set(ids)) and len(ho) >= 1 and len(ho) <= 2000
            ps = {E.en_norm(r['prompt'].rsplit('?', 1)[0]) for r in rows}
            tp = {E.en_norm(e) for r in rows for e in [r['prompt'][:r['prompt'].index('.') + 1]]}
            hp = {E.en_norm(r['prompt'][:r['prompt'].index('.') + 1]) for r in ho}
            assert not tp & hp
            v = CharVocab.load(os.path.join(d, 'out', a, 'charvocab.json'))
            assert len(v) == 108 and json.load(open(os.path.join(d, 'out', a, 'charvocab.json')))['train_bytes'] == os.path.getsize(os.path.join(d, 'out', a, 'train.jsonl'))
            m = json.load(open(os.path.join(d, 'out', a, 'MANIFEST.json')))
            assert m['files']['train.jsonl'] == E._sha(os.path.join(d, 'out', a, 'train.jsonl')) and m['atype'] and m['max_prompt'] <= 208
            assert set(m['overlap']) == {'fresh', 'new_r5', 'new_r6', 'gen_heldout'} and 'train_passages_with_gen_heldout_name' in m
        # the shared-passage group is whole on one side
        ho_t = {r['id'] for r in _read(os.path.join(t, 'dev', 'in_dist.jsonl'))}
        side = {k: any(r.startswith(f'ex{k}-') for r in ho_t) for k in (10, 11, 12)}
        assert len(set(side.values())) == 1
        # Windows text mode (newline '\r\n') must not change any output byte, so the manifest sha is the same on every machine
        import builtins
        real_open = builtins.open
        def win_open(f, mode='r', *a, **kw):
            if 'w' in mode and 'b' not in mode:
                kw['newline'] = '\r\n' if kw.get('newline') is None else kw['newline']
            return real_open(f, mode, *a, **kw)
        builtins.open = win_open
        try:
            E.build_pair(os.path.join(d, 't.jsonl'), os.path.join(d, 'g.jsonl'), os.path.join(d, 'outw'), EVAL)
        finally:
            builtins.open = real_open
        for n in ('teach', 'gen'):
            for f in ('MANIFEST.json', 'train.jsonl', 'charvocab.json', 'dev/in_dist.jsonl'):
                assert E._sha(os.path.join(d, 'outw', n, f)) == E._sha(os.path.join(d, 'out', n, f)), (n, f)
        assert b'\r' not in real_open(os.path.join(d, 'out', 'teach', 'MANIFEST.json'), 'rb').read()
        # determinism: same sources -> same bytes
        m1 = E._sha(os.path.join(t, 'MANIFEST.json'))
        man2 = E.build_pair(os.path.join(d, 't.jsonl'), os.path.join(d, 'g.jsonl'), os.path.join(d, 'out2'), EVAL)
        assert E._sha(os.path.join(d, 'out2', 'teach', 'MANIFEST.json')) == m1
        # the eval question is counted per kind and per eval set
        eq = man['teach']['overlap']['fresh']['train_questions_equal_eval_question']
        assert eq.get('giver_recipient_roles', 0) >= 1 and man['teach']['overlap']['fresh']['n_train_questions_equal'] >= 1
    print('ok build / split / parity / manifest')


def test_split_grouping():
    ex = [dict(_example(i), rows=[{'id': f'{i}-{k}'} for k in range(4)]) for i in range(40)]
    for k in (7, 8, 9):                                                                      # a chain: 7~8 by paraphrase, 8~9 by source
        ex[k]['paraphrase'] = ex[7]['paraphrase']
    ex[9]['source_text'] = ex[8]['source_text']
    for seed in range(8):
        tr, ho = E.split_heldout(ex, seed, frac=0.1)
        assert not E._passages(tr) & E._passages(ho)
        assert (len(ho) >= 1) and len(tr) + len(ho) == 40
    tr, ho = E.split_heldout(ex[:3], 0)
    assert len(ho) == 1                                                                      # at least 1
    tr, ho = E.split_heldout(ex, 0, frac=1.0, max_rows=20)
    assert sum(len(e['rows']) for e in ho) <= 20                                             # at most max_rows
    print('ok held-out grouping')


def test_parity_cut():
    ex = [dict(id=i, rows=[0] * (1 + i % 4)) for i in range(200)]
    n = sum(len(e['rows']) for e in ex)
    for target in (n, n - 1, n - 37, n // 2):
        out, trim = E.parity_cut(ex, target, 0)
        assert sum(len(e['rows']) for e in out) == target and 0 <= trim < 4
        assert sum(e in ex for e in out) >= len(out) - 1                                     # whole examples dropped; at most one trimmed
        assert (out, trim) == E.parity_cut(ex, target, 0) and (target == n or out != E.parity_cut(ex, target, 1)[0])
    four = [dict(id=i, rows=[0] * 4) for i in range(50)]
    out, trim = E.parity_cut(four, 150, 0)
    assert trim == 2 and len(out) == 38 and sum(len(e['rows']) for e in out) == 150
    print('ok parity cut')


def test_overlap_guard_refuses():
    fresh = E.load_examples(os.path.join(EVAL, 'FRESH-EN-R3.json'))
    with tempfile.TemporaryDirectory() as d:
        for key in ('source_text', 'paraphrase'):
            bad = [_example(i) for i in range(30)]
            bad[3][key] = '  ' + fresh[7][key].upper().replace('’', "'") + ' '              # equal under en_norm
            try:
                _build(d, bad, [_example(500 + i) for i in range(30)])
                raise AssertionError('guard did not refuse')
            except SystemExit as e:
                assert e.code not in (0, None) and 'refusing' in str(e.code), e.code
            assert not os.path.exists(os.path.join(d, 'out')), 'nothing may be written on refusal'
    print('ok overlap guard')


class FakeLedger(nn.Module):
    """The span-Ledger contract eval_english relies on: vocab, generate, state(batch, loops), talk(state, batch, lesion, return_modes), LESIONS,
    supports_donor, n_loops. The 'reasoner' state is (mode, s, e) read from the gold; the talker emits prompt[s..e] of the CURRENT row, or yes / no."""
    LESIONS = ['zero_state', 'shuffle_state']
    n_loops = 8

    def __init__(self):
        super().__init__()
        self.vocab, self.w = CharVocab(ASCII), nn.Parameter(torch.zeros(1))

    def supports_donor(self):
        return True

    def state(self, batch, loops=None):
        out = torch.zeros(len(batch['rows']), 3)
        if loops == 0:
            return out
        for i, r in enumerate(batch['rows']):
            ans = E.en_norm(r['answer'])
            if ans in ('yes', 'no'):
                out[i] = torch.tensor([2., ans == 'no', 0])
            else:
                runs = E.word_runs(r['prompt'], ans)
                out[i] = torch.tensor([1., *runs[0]]) if runs else torch.tensor([3., 0, 0])
        return out

    def talk(self, state, batch, lesion=None, return_modes=False):
        out, modes = [], []
        for st, r in zip(state.tolist(), batch['rows']):
            m, s, e = int(st[0]), int(st[1]), int(st[2])
            ws = word_spans(r['prompt'])
            if m == 1 and e < len(ws) and e < s + 12:
                out.append(r['prompt'][ws[s][0]:ws[e][1]])
            elif m == 1:
                out.append('')
            else:
                out.append(('yes', 'no')[int(st[1])] if m == 2 else '?')
            modes.append(m if m < 2 else 2)
        return (out, modes) if return_modes else out

    def generate(self, batch, lesion=None):
        name, _, arg = (lesion or '').partition(':')
        st = self.state(batch, int(arg) if name == 'loops' else None)
        if name == 'zero_state':
            st = torch.zeros_like(st)
        if name == 'shuffle_state':
            st = st.roll(1, 0)
        return self.talk(st, batch)

    def parameters(self, recurse=True):
        return iter([self.w])


FakeLedger.__name__ = 'Ledger'


def test_eval_english_fake_span_model():
    m = FakeLedger()
    S = E.eval_sets(EVAL)
    held = [dict(r, id='h' + r['id']) for r in S['fresh'][:10]]
    events = []
    res = E.eval_english(m, EVAL, held, 'cpu', 64, contextlib.nullcontext, log=events.append)
    json.dumps(res)
    assert set(res['intact']) == {'fresh', 'new_r5', 'new_r6', 'new_pooled', 'gen_heldout', 'in_dist_heldout'}
    nonspan = lambda k: sum(r['atype'] == 'nonspan' for r in S[k])
    for k in ('fresh', 'gen_heldout'):
        assert res['intact'][k]['correct'] == 192 - nonspan(k) and res['intact'][k]['n'] == 192, k
    assert res['intact']['new_pooled']['exact'] == 100.0 and res['intact']['new_pooled']['n'] == 384 and res['intact']['new_r5']['n'] == 192
    assert res['intact']['new_r5']['correct'] + res['intact']['new_r6']['correct'] == 384
    assert res['intact']['gen_heldout']['label'].startswith('generator kinds') and res['intact']['in_dist_heldout']['n'] == 10
    for k in ('by_family', 'by_type', 'by_atype', 'by_panel'):
        assert sum(c['n'] for c in res['intact']['fresh'][k].values()) == 192
    assert res['intact']['fresh']['by_atype']['nonspan'] == dict(correct=0, n=2, exact=0.0)
    assert res['intact']['new_pooled']['reachable']['n'] == 384
    assert res['intact']['fresh']['reachable']['n'] == 192 - sum(not any(len(a) <= 8 for a in r['accepted']) and r['atype'] == 'nonspan' for r in S['fresh'])
    d = res['lesions']['new_pooled']['donor']
    assert d['n'] == 376 and d['skipped'] == 8 and res['lesions']['fresh']['donor']['n'] == 190 and res['lesions']['fresh']['donor']['skipped'] == 2
    assert d['exact'] == 0.0 and d['donor_match'] > 0 and 'plain' in d and d['plain']['pos_coincide'] > 0 and d['pos_coincide'] == 0.0
    assert d['plain']['exact'] > 0 and d['exact_given_intact_right']['n'] == 376 and d['exact_given_intact_right']['exact'] == 0.0
    assert d['donor_position_match'] > 0 and d['donor_position_n'] > 0
    assert set(res['donor_preds']['new_pooled']) == {r['id'] for r in S['new_pooled']} - {S['new_pooled'][i]['id'] for i in range(384) if S['new_pooled'][i]['id'] not in res['donor_preds']['new_pooled']}
    assert len(res['donor_preds']['new_pooled']) == 376 and len(res['preds']['new_pooled']) == 384 and len(res['preds']['fresh']) == 192
    jid, jp = next(iter(res['donor_preds']['fresh'].values()))
    assert isinstance(jid, str) and isinstance(jp, str)
    l0 = res['lesions']['new_pooled']['loops:0']
    assert l0['label'] == 'question-blind talker' and sum(l0['modes'].values()) == 384 and set(l0['modes']) == {'NUM', 'span', 'GEN'} and l0['exact'] < 20
    assert l0['modes']['NUM'] == 384
    assert 'zero_state' in res['lesions']['fresh'] and res['lesions']['fresh']['zero_state']['exact'] < 20
    assert any(e.get('lesion') == 'donor' for e in events) and any(e.get('set') == 'in_dist_heldout' for e in events)
    # rescoring from the stored predictions needs no model
    sc = E.score(S['new_pooled'], res['preds']['new_pooled'])
    assert sc['exact'] == res['intact']['new_pooled']['exact']
    # an empty held-out slice is {n: 0} and never evaluated
    res0 = E.eval_english(m, EVAL, [], 'cpu', 64)
    assert res0['intact']['in_dist_heldout'] == {'n': 0} and E.score([], {}) == {'n': 0}
    print('ok eval_english (fake span model)')


def test_eval_english_plain_tf():
    from custom_io.models.plain_tf import PlainTF
    torch.manual_seed(0)
    m = PlainTF(CharVocab(ASCII), d_model=32, n_layers=1, n_heads=2, max_ans=32).eval()
    held = E.eval_sets(EVAL)['fresh'][:6]
    res = E.eval_english(m, EVAL, held, 'cpu', 96)
    json.dumps(res)
    assert res['lesions'] == {'new_pooled': {}, 'fresh': {}} and res['donor_preds'] == {} and set(res['preds']) == {'new_pooled', 'fresh'}
    assert res['intact']['new_pooled']['n'] == 384 and res['intact']['in_dist_heldout']['n'] == 6
    assert res['intact']['new_pooled']['reachable']['n'] == 384                      # every accepted answer fits 32 chars
    m8 = PlainTF(CharVocab(ASCII), d_model=32, n_layers=1, n_heads=2).eval()
    assert E._reach(m8)({'accepted': ['x' * 9]}) is False and E._reach(m)({'accepted': ['x' * 9]}) is True
    mm = PlainTF(CharVocab(ASCII), d_model=32, n_layers=1, n_heads=2, n_loops=2).eval()
    r2 = E.eval_english(mm, EVAL, [], 'cpu', 96)
    assert 'loops:0' in r2['lesions']['fresh'] and 'modes' not in r2['lesions']['fresh']['loops:0'] and 'donor' not in r2['lesions']['fresh']
    print('ok eval_english (PlainTF)')


def test_evalx_defaults_unchanged():
    """The optional arguments leave the skills numbers alone: evalx.norm / is_hit / donor_pairs behave as before when not given."""
    from custom_io import evalx
    rows = [dict(id=str(i), family='f' if i < 4 else 'g', answer=a, accepted=[a]) for i, a in enumerate(['A b', 'a  B', 'c', 'd', 'e', 'f'])]
    P, sk = evalx.donor_pairs(rows, 0)
    assert all(evalx.norm(rows[i]['answer']) != evalx.norm(rows[j]['answer']) for i, j in P) and sk == 0
    assert evalx.is_hit('A  B', rows[0]) and not evalx.is_hit('a b.', rows[0]) and evalx.is_hit('a b.', rows[0], E.en_norm)
    assert evalx.donor_pairs(rows, 0) == evalx.donor_pairs(rows, 0, evalx.norm)
    print('ok evalx defaults')


def _fake_result(arm, seed, pooled, donor, data, steps=16000, status='ok', short=None):
    model = 'plain_tf' if arm == 'tft' else 'ledger'
    cfg = dict(d=384, n_heads=6, reader_layers=2, blocks=3, n_loops=8, mlp=6.0, copy=True, span=True) if model == 'ledger' else dict(d_model=384, n_layers=6, n_heads=6, max_ans=32)
    blk = lambda x, n=384, sh=None: dict(exact=x, correct=0, n=n, by_atype={'span1': dict(exact=x, n=10, correct=0)}, reachable=dict(n=n, share=100.0),
                                         by_type={'short_answer': dict(exact=x if sh is None else sh, n=340, correct=0), 'yes_no': dict(exact=x, n=44, correct=0)},
                                         by_family={'winner': dict(exact=x, n=n // 2, correct=0), 'fear': dict(exact=x, n=n // 2, correct=0)})
    en = dict(intact={'fresh': blk(70, 192), 'new_r5': blk(pooled, 192), 'new_r6': blk(pooled, 192), 'new_pooled': blk(pooled, sh=short), 'gen_heldout': blk(50, 192), 'in_dist_heldout': blk(90, 10)},
              lesions={'new_pooled': {'donor': dict(exact=donor, n=376, skipped=8, plain=dict(exact=1.0))} if model == 'ledger' else {}, 'fresh': {}})
    return dict(config=dict(model=model, cfg=cfg, data=data, seed=seed, batch=256, lr=7e-4, warmup=500, bf16=True, max_ans=32, steps=16000, minutes=None, final_eval=True, grad_clip=1.0, order='shuffled'),
                n_params=10782336 if model == 'plain_tf' else 10914681, steps=steps, status=status, english=en)


def test_analyze_b1():
    from custom_io import analyze_b1 as A
    with tempfile.TemporaryDirectory() as d:
        shas = {}
        for w in ('teach', 'gen'):
            os.makedirs(os.path.join(d, 'data', w))
            open(os.path.join(d, 'data', w, 'MANIFEST.json'), 'w').write(w)
            shas[w] = E._sha(os.path.join(d, 'data', w, 'MANIFEST.json'))
        def put(arm, seed, *a, **kw):
            os.makedirs(os.path.join(d, 'res', f'{arm}_s{seed}'))
            json.dump(_fake_result(arm, seed, *a, os.path.join(d, 'data', 'gen' if arm == 'b2g' else 'teach'), **kw), open(os.path.join(d, 'res', f'{arm}_s{seed}', 'RESULT.json'), 'w'))
        for sd, (t, g_, f) in {300: (60, 40, 50), 301: (58, 41, 52)}.items():
            put('b2t', sd, t, 5.0); put('b2g', sd, g_, 5.0); put('tft', sd, f, 0.0)
        run = lambda: A.analyze([os.path.join(d, 'res')], [300, 301], EVAL, '/nonexistent', dict(teach=shas['teach'], gen=shas['gen']))
        out = run()
        m = out['marks']
        assert m['B1-a']['verdict'] == 'PASS' and abs(m['B1-a']['mean'] - 18.5) < 1e-9 and m['B1-a']['ahead_all']
        assert m['B1-b']['verdict'] == 'PASS' and m['B1-b']['mean'] == 5.0 and m['B1-c']['verdict'] == 'PASS' and abs(m['B1-c']['mean'] - 8.0) < 1e-9
        assert 'B1-a (b2t - b2g)' in out['read_only']['atype_diffs'] and out['read_only']['always']['new_pooled']['n_yes_no'] == 44
        assert 'PASS' in A.markdown(out) and json.dumps(out)
        assert abs(m['B1-a']['short_answer_only']['mean'] - 18.5) < 1e-9 and 'B1-a guard' in A.markdown(out)
        assert out['read_only']['by_type']['new_pooled']['b2t']['short_answer']['n'] == 340 and set(out['read_only']['by_kind']['fresh']) == {'b2t', 'b2g', 'tft'}
        # the extra guard (thinker-first B1 addendum): passes overall, but on short answers alone TEACH is only +8 over GEN -> NOT SHOWN
        for sd, (t, g_, st, sg) in {300: (60, 40, 48, 40), 301: (58, 41, 49, 41)}.items():
            for arm, v, sh in (('b2t', t, st), ('b2g', g_, sg), ('tft', 50, None)):
                os.makedirs(os.path.join(d, 'res_yn', f'{arm}_s{sd}'))
                json.dump(_fake_result(arm, sd, v, 5.0, os.path.join(d, 'data', 'gen' if arm == 'b2g' else 'teach'), short=sh),
                          open(os.path.join(d, 'res_yn', f'{arm}_s{sd}', 'RESULT.json'), 'w'))
        yn = A.analyze([os.path.join(d, 'res_yn')], [300, 301], EVAL, '/nonexistent', dict(teach=shas['teach'], gen=shas['gen']))['marks']['B1-a']
        assert yn['verdict'].startswith('NOT SHOWN') and abs(yn['short_answer_only']['mean'] - 8.0) < 1e-9 and abs(yn['mean'] - 18.5) < 1e-9, yn['verdict']
        wrong = A.analyze([os.path.join(d, 'res')], [300, 301, 302], EVAL, '/nonexistent', dict(teach=shas['teach'], gen=shas['gen']))     # seed 302 missing
        assert all(x['verdict'] == 'NOT JUDGED' for x in wrong['marks'].values())
        assert A.analyze([os.path.join(d, 'res')], [300, 301], EVAL, '/nonexistent', dict(teach='0' * 64, gen=shas['gen']))['marks']['B1-a']['verdict'] == 'NOT JUDGED'
        assert A.analyze([os.path.join(d, 'res')], [300, 301], EVAL, '/nonexistent', {})['marks']['B1-a']['verdict'] == 'NOT JUDGED'                  # nothing recorded
        pm = os.path.join(d, 'PASS-MARKS.md')     # the committed addendum-3 line format is read
        open(pm, 'w').write(f"## Addendum 3: x\n- teach MANIFEST.json sha256 {shas['teach']}\n- gen MANIFEST.json sha256 {shas['gen']}\n")
        assert A.recorded_shas(pm) == shas
        assert A.analyze([os.path.join(d, 'res')], [300, 301], EVAL, pm, {})['marks']['B1-a']['verdict'] == 'PASS'
        assert A.recorded_shas('/nonexistent') == {}
        assert A.analyze([os.path.join(d, 'res')], [300, 301], EVAL, '/nonexistent', {}, data_check=False)['marks']['B1-a']['verdict'] == 'PASS'
        # an invalid run (steps), a close call, one seed behind, an uninformative donor
        os.makedirs(os.path.join(d, 'res2'))
        for sd, (t, g_, f) in {300: (30, 20, 29), 301: (8, 19, 12)}.items():
            for arm, v in (('b2t', t), ('b2g', g_), ('tft', f)):
                os.makedirs(os.path.join(d, 'res2', f'{arm}_s{sd}'))
                json.dump(_fake_result(arm, sd, v, 3.0, os.path.join(d, 'data', 'gen' if arm == 'b2g' else 'teach')), open(os.path.join(d, 'res2', f'{arm}_s{sd}', 'RESULT.json'), 'w'))
        m = A.analyze([os.path.join(d, 'res2')], [300, 301], EVAL, '/nonexistent', dict(teach=shas['teach'], gen=shas['gen']))['marks']
        assert m['B1-a']['verdict'] == 'PROVED WRONG' and m['B1-a']['mean'] == -0.5 and not m['B1-a']['ahead_all'] and m['B1-c']['verdict'] == 'FAIL'
        assert m['B1-b']['verdict'].startswith('UNINFORMATIVE')
        r = json.load(open(os.path.join(d, 'res', 'b2g_s301', 'RESULT.json')))
        r['steps'] = 15999
        json.dump(r, open(os.path.join(d, 'res', 'b2g_s301', 'RESULT.json'), 'w'))
        out = run()
        assert out['marks']['B1-a']['verdict'] == 'NOT JUDGED' and out['marks']['B1-c']['verdict'] == 'PASS' and 'steps 15999' in out['marks']['B1-a']['why_not'][0]
        # a changed grad clip / batch order, a b2t run with no donor result, and one run name in two folders are NOT JUDGED with a reason
        for k, v in (('grad_clip', 0.1), ('order', 'curriculum')):
            r = json.load(open(os.path.join(d, 'res', 'tft_s300', 'RESULT.json'))); r['config'][k] = v
            os.makedirs(os.path.join(d, f'bad_{k}', 'tft_s300')); json.dump(r, open(os.path.join(d, f'bad_{k}', 'tft_s300', 'RESULT.json'), 'w'))
            assert any(k in w for w in A.validate('tft', 300, r, dict(teach=shas['teach'])))
        r = json.load(open(os.path.join(d, 'res', 'b2t_s300', 'RESULT.json'))); r['english']['lesions']['new_pooled'] = {}
        assert any('donor' in w for w in A.validate('b2t', 300, r, dict(teach=shas['teach'])))
        os.makedirs(os.path.join(d, 'dup', 'b2t_s300')); shutil.copy(os.path.join(d, 'res', 'b2t_s300', 'RESULT.json'), os.path.join(d, 'dup', 'b2t_s300', 'RESULT.json'))
        o = A.analyze([os.path.join(d, 'res', 'b2t_s300', '..'), os.path.join(d, 'dup')], [300, 301], EVAL, '/nonexistent', dict(teach=shas['teach'], gen=shas['gen']))
        assert o['duplicates'] == ['b2t_s300'] and o['marks']['B1-b']['verdict'] == 'NOT JUDGED' and 'more than one folder' in o['marks']['B1-b']['why_not'][0]
    print('ok analyze_b1')


def test_ledger_span_if_present():
    """When models/ledger.py has the span talker: decode never leaves span_max or the CURRENT row's word count; state carries lwend."""
    from custom_io.models.ledger import Ledger
    try:
        torch.manual_seed(0)
        m = Ledger(CharVocab(ASCII), d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0, copy=True, span=True).eval()
    except TypeError:
        print('skip ledger span checks (models/ledger.py has no span yet)')
        return
    from custom_io.data import Dataset, collate
    rows = E.eval_sets(EVAL)['fresh']
    short, long_ = sorted(rows, key=lambda r: len(r['prompt']))[:8], sorted(rows, key=lambda r: -len(r['prompt']))[:8]
    ds = lambda rs: collate([Dataset(rs, m.vocab, strict=False)[i] for i in range(len(rs))])
    T = max(len(r['prompt']) for r in long_)
    cur, don = ds(short), ds(long_)
    pad = lambda b: dict(b, prompt_ids=nn.functional.pad(b['prompt_ids'], (0, T - b['prompt_ids'].shape[1])), prompt_mask=nn.functional.pad(b['prompt_mask'], (0, T - b['prompt_mask'].shape[1])))
    with torch.no_grad():
        st = m.state(pad(don))
        assert len(st) == 7
        out, modes = m.talk(st, pad(cur), return_modes=True)
        assert out == m.talk(st, pad(cur)) and len(modes) == 8 and set(modes) <= {0, 1, 2}
    for o, r, md in zip(out, short, modes):
        if md == 1:
            ws = word_spans(r['prompt'])
            assert any(o == r['prompt'][ws[s][0]:ws[e][1]] for s in range(len(ws)) for e in range(s, min(len(ws), s + 12))), (o, r['prompt'])
    print('ok ledger span decode')


if __name__ == '__main__':
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    t0 = time.time()
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            t = time.time()
            fn()
            print(f'  [{name} {time.time() - t:.0f}s]')
    print(f'all ok ({time.time() - t0:.0f}s)')
