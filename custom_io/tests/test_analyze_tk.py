"""python3 -m custom_io.tests.test_analyze_tk   (CPU, seconds). Synthetic RESULT.json trees for custom_io/g8a/analyze_tk.py, built in a temp dir by copying a real G1 control
RESULT.json (8aG1d-3M-s400 B2; the path comes from env TK_CTL_RESULT, else it is read with git show from origin/claude/8a-g-pc-results) and editing numbers."""
import copy, io, json, os, subprocess, sys, tempfile, contextlib
from custom_io.g8a import analyze_tk as T

REF = 'results/8a-g/pc/8aG1d-pc/8aG1d-3M-s400/B2/RESULT.json'


def base_result():
    p = os.environ.get('TK_CTL_RESULT')
    if p:
        return json.load(open(p))
    return json.loads(subprocess.check_output(['git', 'show', f'origin/claude/8a-g-pc-results:{REF}']))


def setx(r, split, exact):
    d = r['final_eval'][split]
    d['correct'] = round(d['n'] * exact / 100.0); d['exact'] = 100.0 * d['correct'] / d['n']


def edit(r, seed, kind, p5=0, frame=None, vocab=None, cipher=None, chain5=None, loops0=None, ind=None):
    """p5: shift pooled-5 by about this many points (via 'variant' rows); cipher: (in_dist, answer, frame) correct out of 40 each."""
    r = copy.deepcopy(r)
    r['config']['seed'] = seed
    if kind in ('TK', 'TKN'):
        r['config']['cfg']['tok_think'] = True
    if kind == 'TKN':
        r['config']['cfg'].update(reader_layers=0, mlp=7.29883)
    if p5:
        v = r['final_eval']['variant']
        v['correct'] = v['correct'] + round(p5 * 6040 / 100); v['exact'] = 100.0 * v['correct'] / v['n']
    if frame is not None: setx(r, 'frame', frame)
    if vocab is not None: setx(r, 'vocab', vocab)
    if ind is not None: setx(r, 'in_dist', ind)
    if cipher:
        for sp, c in zip(T.CIPHER_SPLITS, cipher):
            r['final_eval'][sp]['by_family']['cipher_map'] = dict(correct=c, n=40)
    if chain5 is not None: r['chain5']['intact']['exact'] = chain5
    if loops0 is not None: r['lesions']['loops:0']['in_dist']['exact'] = loops0
    if kind in ('TK', 'TKN'):
        r['tok_think'] = dict(letters=1000, spots=320, ratio=3.125)
    return r


def put(root, queue, seed, r):
    d = os.path.join(root, f'{queue}-3M-s{seed}', 'B2')
    os.makedirs(d, exist_ok=True)
    json.dump(r, open(os.path.join(d, 'RESULT.json'), 'w'))


def tree(base, spec):
    """spec: list of (queue, seed, kind, edits) -> temp dir"""
    root = tempfile.mkdtemp(prefix='tk_test_')
    for q, s, k, e in spec:
        put(root, q, s, edit(base, s, k, **e))
    return root


def run(root, *extra):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = T.main(['--results', root, *extra])
    return out, buf.getvalue()


def controls(**e1):
    return [('8aG1d', 400, 'GB2', {}), ('8aG1e', 401, 'GB2', e1)]


def main():
    base = base_result()
    ok_tk = dict(p5=0, chain5=99.9)
    c_ind = base['final_eval']['in_dist']['exact']
    print('control s400: cipher_map', T.cipher(base), 'pooled-5 %.2f' % T.A.P5(base), 'in_dist', c_ind, 'loops0', base['lesions']['loops:0']['in_dist']['exact'])
    assert T.cipher(base) == (79, 120)

    # 1. pass: TK equal to the control on both seeds
    root = tree(base, controls() + [('8aTK', 400, 'TK', ok_tk), ('8aTK', 401, 'TK', ok_tk)])
    res, txt = run(root)
    assert res['TK']['readout'] == 'PASS' and res['M3_gate']['judged'] is True, (res['TK']['readout'], res['TK']['notes'])
    assert res['TK']['marks']['cipher_counts']['arm'] == [(79, 120), (79, 120)]
    assert res['reported']['tok_think_letters_per_spot']['TK'][400]['ratio'] == 3.125
    print('pass ok')

    # 2. M1 fail: pooled-5 down 1.5 on both seeds (mean -1.5: fails M1, not proved wrong)
    root = tree(base, controls() + [('8aTK', s, 'TK', dict(ok_tk, p5=-1.5)) for s in (400, 401)])
    res, _ = run(root)
    assert res['TK']['readout'] == 'NOT SHOWN' and res['TK']['marks']['M1']['ok'] is False, res['TK']
    print('M1 fail ok')

    # 3. hair pass: chain-5 98.7 on one seed (short by 0.3), all else passing
    root = tree(base, controls() + [('8aTK', 400, 'TK', dict(ok_tk, chain5=98.7)), ('8aTK', 401, 'TK', ok_tk)])
    res, _ = run(root)
    assert res['TK']['readout'] == 'PASS (hair rule)' and len(res['TK']['hair']) == 1, res['TK']
    # a miss of 0.6 is not hair; M1 in the same shape gets no tolerance
    root = tree(base, controls() + [('8aTK', 400, 'TK', dict(ok_tk, chain5=98.4)), ('8aTK', 401, 'TK', ok_tk)])
    assert run(root)[0]['TK']['readout'] == 'NOT SHOWN'
    root = tree(base, controls() + [('8aTK', s, 'TK', dict(ok_tk, p5=-1.05)) for s in (400, 401)])
    assert run(root)[0]['TK']['readout'] == 'NOT SHOWN'
    print('hair ok')

    # 4. proved wrong: pooled-5 -2.5 on both seeds; and by cipher_map 24+ rows... (79 -> 40 of 120 = -32.5 points) with M3 judged
    root = tree(base, controls() + [('8aTK', s, 'TK', dict(ok_tk, p5=-2.5)) for s in (400, 401)])
    assert run(root)[0]['TK']['readout'] == 'PROVED WRONG'
    root = tree(base, controls() + [('8aTK', s, 'TK', dict(ok_tk, cipher=(13, 13, 14))) for s in (400, 401)])
    res, _ = run(root)
    assert res['TK']['readout'] == 'PROVED WRONG' and res['M3_gate']['judged'] is True, res['TK']
    print('proved wrong ok')

    # 5. M3 not judged: G-B2 seeds differ by 12.5 points on cipher_map (79 vs 64 of 120); the same TK cipher collapse is then not proved wrong
    ctl = controls(cipher=(21, 21, 22))
    root = tree(base, ctl + [('8aTK', s, 'TK', dict(ok_tk, cipher=(13, 13, 14))) for s in (400, 401)])
    res, _ = run(root)
    assert res['M3_gate']['judged'] is False and res['TK']['marks']['M3']['ok'] == 'not judged' and res['TK']['readout'] == 'PASS', (res['M3_gate'], res['TK'])
    print('M3 not judged ok')

    # 6. stop-check TK: STOP (pooled-5 -2.0 on seed 400 exactly), STOP (cipher > 20 below, M3 judged), CONTINUE; exit 0 either way
    s_stop = tree(base, controls() + [('8aTK', 400, 'TK', dict(ok_tk, p5=-2.0))])
    line = run(s_stop, '--stop-check', 'TK')[1]
    assert line.startswith('STOP:'), line
    s_c = tree(base, controls() + [('8aTK', 400, 'TK', dict(ok_tk, cipher=(13, 13, 14)))])
    assert run(s_c, '--stop-check', 'TK')[1].startswith('STOP:')
    s_c2 = tree(base, controls(cipher=(21, 21, 22)) + [('8aTK', 400, 'TK', dict(ok_tk, cipher=(13, 13, 14)))])      # M3 not judged -> no cipher stop
    assert run(s_c2, '--stop-check', 'TK')[1].startswith('CONTINUE:'), run(s_c2, '--stop-check', 'TK')[1]
    s_ok = tree(base, controls() + [('8aTK', 400, 'TK', dict(ok_tk, p5=-1.0))])
    line = run(s_ok, '--stop-check', 'TK')[1]
    assert line.startswith('CONTINUE:') and 'diff -0.99' in line, line
    s_only = tree(base, [('8aG1d', 400, 'GB2', {}), ('8aTK', 400, 'TK', dict(ok_tk, cipher=(13, 13, 14)))])         # G-B2 s401 absent: M3 not judgeable yet, so CONTINUE with a note
    line = run(s_only, '--stop-check', 'TK')[1]
    assert line.startswith('CONTINUE:') and 'not yet judgeable' in line, line
    print('stop-check TK ok')

    # 7. stop-check TKN against TK s400
    tkn = lambda **e: [('8aG1d', 400, 'GB2', {}), ('8aTK', 400, 'TK', ok_tk), ('8aTKN', 400, 'TKN', dict(ok_tk, **e))]
    assert run(tree(base, tkn(p5=-2.0)), '--stop-check', 'TKN')[1].startswith('STOP:')
    assert run(tree(base, tkn(cipher=(13, 13, 14))), '--stop-check', 'TKN')[1].startswith('STOP:')
    line = run(tree(base, tkn(p5=-1.9, cipher=(17, 17, 18))), '--stop-check', 'TKN')[1]       # 52/120 vs 79/120 = -22.5 -> STOP; use -19 below instead
    assert line.startswith('STOP:'), line
    line = run(tree(base, tkn(p5=-1.9, cipher=(20, 20, 20))), '--stop-check', 'TKN')[1]       # 60/120: 19 rows = -15.8 points -> not > 20
    assert line.startswith('CONTINUE:'), line
    print('stop-check TKN ok')

    # 8. TKN vs TK window lines
    full = controls() + [('8aTK', s, 'TK', ok_tk) for s in (400, 401)]
    res, _ = run(tree(base, full + [('8aTKN', s, 'TKN', ok_tk) for s in (400, 401)]))
    assert res['TKN_vs_TK']['window'] == 'window can go', res['TKN_vs_TK']
    res, _ = run(tree(base, full + [('8aTKN', s, 'TKN', dict(ok_tk, p5=-2.2)) for s in (400, 401)]))
    assert res['TKN_vs_TK']['window'] == 'window needed'
    res, _ = run(tree(base, full + [('8aTKN', s, 'TKN', dict(ok_tk, p5=-1.5)) for s in (400, 401)]))
    assert res['TKN_vs_TK']['window'].startswith('not shown')
    print('window ok')

    # 9. missing runs give n/a, never a crash; wrong names / failed status are skipped with a reason
    res, txt = run(tree(base, controls()))
    assert res['TK']['readout'] == 'n/a' and res['TKN_vs_TK']['window'] == 'n/a'
    root = tree(base, controls())
    put(root, '8aTK', 400, edit(base, 400, 'GB2'))                 # 8aTK name, no tok_think in cfg
    put(root, '8aTKN', 400, edit(base, 400, 'TK'))                 # 8aTKN name, reader_layers not 0
    bad = edit(base, 400, 'TK'); bad['status'] = 'failed'; put(root, '8aTK', 401, bad)
    res, txt = run(root)
    assert len(res['skipped']) == 3 and res['TK']['readout'] == 'n/a', res['skipped']
    empty = tempfile.mkdtemp(prefix='tk_empty_')
    res, _ = run(empty)
    assert res['TK']['readout'] == 'n/a'
    assert run(empty, '--stop-check', 'TK')[1].startswith('NO DECISION')
    out = os.path.join(empty, 'o.json'); run(root, '--out', out); json.load(open(out))
    print('missing / skipped ok')
    print('ALL OK')


if __name__ == '__main__':
    main()
