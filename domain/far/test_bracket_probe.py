"""Tests of domain/far/bracket_probe.py (pytest; CPU, no training, a couple of minutes at most):

  python3 -m pytest domain/far/test_bracket_probe.py -q

Real-data tests (strata 106 / 60 / 46 / 126, the rewrites on all 106, the layout parse against sheet.evaluate on the eval + train rows) use the session
fixture `l5`: the extracted L5 rows from $BRACKET_PROBE_DATA (a directory holding stratum/eval-rows-l5.jsonl, stratum/train-rows-l5.jsonl and
stratum/sheet-probe.jsonl) when it is set and complete, else extracted with `git show` from origin/claude/far-transfer-inputs (inputs/far-transfer/learn/
eval-rows-l5.jsonl, .../train-rows-l5.jsonl, .../diag/sheet-probe.jsonl) into a temp dir; they skip, with the reason printed by `pytest -rs`, only when neither
is available. Model tests use a
random-init T1SD span model (Tool(vocab, span_copy=True, span_idx=True, span_end=True, ans_drill=0), built as test_learn_probe_r1.py builds its
span model) on a handful of real-form prompts (HAND), so they never need a checkpoint. The run()-path identity is tested without a trained model by
teacher-forcing the model's OWN free-run calls as the gold: every round must then be TF-exact and the answers equal, bit for bit.
"""
import json
import os
import random

import pytest
import torch

from domain.far import bracket_probe as B
from domain.far import join_gap as JG
from domain.far import learn_probe as LP
from domain.tools import sheet

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GIT_REF = 'origin/claude/far-transfer-inputs'
GIT_DIRS = ('learn', 'diag')                                     # where inputs/far-transfer/<dir>/<file> may live on that ref
L5_FILES = ('eval-rows-l5.jsonl', 'train-rows-l5.jsonl', 'sheet-probe.jsonl')
L5_REQUIRED = ('eval-rows-l5.jsonl', 'train-rows-l5.jsonl')
SMALL = dict(d=48, n_heads=2, reader_layers=1, blocks=1, n_loops=8, mlp=2.0)
SPAN = dict(span_copy=True, span_idx=True, span_end=True, ans_drill=0.0)


# Thin test-only wrappers over the production functions (collect / main do not use them; they used to live in bracket_probe.py).
def gold_path_check(m, preps_, bs=64):
    """The premise of the identity per item: the pass collect_items runs (tf_with_premise) -> PremiseCheck.result."""
    return B.tf_with_premise(m, preps_, bs)[1]


def premise_of(m, items, bs):
    """gold_path_check plus the per-cell counts (premise_cells)."""
    return B.premise_cells(items, gold_path_check(m, items, bs))


def margins(m, rows, bs=64):
    """tf_pass(margins=True) reduced to per row dict(lp, lp_flat) (None for a dropped row)."""
    return [({k: r[k] for k in ('lp', 'lp_flat')} if r['made'] else None) for r in B.tf_pass(m, rows, bs, margins=True)]


def validate_repair(m, rows, recs, sample=None, bs=64, seed=0):
    """validate_all with all items pooled into ONE stratum and no repair sets -> dict(n, agree, mismatches)."""
    v = B.validate_all(m, rows, [dict(r, strata=['all']) for r in recs], sample, bs, seed, sets=())
    a = v['strata'].get('all', dict(n=0, agree=0, mismatches=[]))
    return {k: a[k] for k in ('n', 'agree', 'mismatches')}


def report(by_label, meta=None, expect=None, no_gate=False, accept_allowed=False):
    """make_report's text only (no exit status; the gate failures are in the text)."""
    return B.make_report(by_label, meta, expect, no_gate, accept_allowed)[0]


def extract_l5_from_git(dest, ref=GIT_REF, repo=REPO):
    """`git show <ref>:inputs/far-transfer/<learn|diag>/<file>` for each of L5_FILES into dest/stratum/ (read-only on the repo). -> ({file: path} of
    those found, a reason string for those missing)."""
    import subprocess
    out, why = {}, []
    os.makedirs(os.path.join(dest, 'stratum'), exist_ok=True)
    for name in L5_FILES:
        for d in GIT_DIRS:
            r = subprocess.run(['git', '-C', repo, 'show', f'{ref}:inputs/far-transfer/{d}/{name}'], capture_output=True)
            if r.returncode == 0 and r.stdout:
                path = os.path.join(dest, 'stratum', name)
                with open(path, 'wb') as f:
                    f.write(r.stdout)
                out[name] = path
                break
        else:
            why.append(f'{name} not on {ref}')
    return out, '; '.join(why)


@pytest.fixture(scope='session')
def l5(tmp_path_factory):
    """-> dict(eval, train, probe) paths of the real L5 rows: $BRACKET_PROBE_DATA/stratum/* when that is set and holds the required files, else
    extracted from git (extract_l5_from_git) under tmp_path_factory; skips with the reason when neither works."""
    env = os.environ.get('BRACKET_PROBE_DATA')
    if env and all(os.path.exists(os.path.join(env, 'stratum', f)) for f in L5_REQUIRED):
        pr = os.path.join(env, 'stratum', 'sheet-probe.jsonl')
        return dict(eval=os.path.join(env, 'stratum', L5_FILES[0]), train=os.path.join(env, 'stratum', L5_FILES[1]), probe=pr if os.path.exists(pr) else None,
                    source=f'BRACKET_PROBE_DATA={env}')
    found, why = extract_l5_from_git(str(tmp_path_factory.mktemp('l5')))
    if not all(f in found for f in L5_REQUIRED):
        pytest.skip(f'real L5 rows not found: BRACKET_PROBE_DATA is {"unset" if not env else "set (" + env + ") but lacks stratum/eval-rows-l5.jsonl or train-rows-l5.jsonl"}'
                    f' and the git extraction failed ({why}); set BRACKET_PROBE_DATA to a directory holding stratum/eval-rows-l5.jsonl and stratum/train-rows-l5.jsonl')
    return dict(eval=found[L5_FILES[0]], train=found[L5_FILES[1]], probe=found.get(L5_FILES[2]), source=f'git {GIT_REF}')


# (split, prompt): real-form rows of the L5 eval file (D_K, D_J, non-CA HO, 6-call HO, HPO with a CA piece, S5 twins and flat layouts, S, HP, F4-two)
HAND = [
    ('HO', 'A: 71 53 35 31 | B: 3 24 77 45 ; =(B1+B4*2)*(MAX(A3:A4))'),
    ('HO', 'A: 14 39 7 | B: 7 42 70 ; =(B3+A1*2)*(B2/B1)'),
    ('HO', 'A: 80 51 2 | B: 69 79 9 ; =(MAX(B1:B2))*(B2+B3*2)'),
    ('HO', 'A: 54 72 | B: 6 98 ; =(MAX(A1:A2))*(B2+A2*2)'),
    ('HO', 'A: 46 77 58 | B: 86 87 68 ; =(SUM(B1:B3))*(MAX(B2:B3))'),
    ('HO', 'A: 22 50 87 | B: 15 43 2 ; =(SUM(B1:B3))*(MIN(A1:A2))'),
    ('HO', 'A: 69 60 74 13 | B: 37 67 19 79 ; =(SUM(B1:B3))*(ABS(B2-A4))'),
    ('HPO', 'A: 67 86 83 43 | B: 70 35 42 3 ; =(SUM(B1:B3))*(A1+B3*2)'),
    ('S5', 'A: 46 32 | B: 13 71 ; =(MAX(A1:A2))+(B2+A2*2)'),
    ('S5', 'A: 49 60 72 12 | B: 95 45 61 23 ; =(MAX(B3:B4))+(A4+B3*2)'),
    ('S5', 'A: 27 89 | B: 80 63 ; =SUM(A1:A2)-MIN(A1:A2)'),
    ('S', 'A: 95 73 31 | B: 44 72 19 ; =SUM(A2:A3)+ABS(B3-B2)'),
    ('HP', 'A: 37 63 51 | B: 5 85 10 ; =SUM(A1:A3)+B2/B1'),
    ('F4-two', 'A: 5 53 60 13 | B: 49 16 80 90 ; =(SUM(B2:B4))*(MAX(A3:A4))'),
]


def hand_rows():
    return [dict(id=f'h{i}', kind='SUM', partner='MAX', split=sp, prompt=p, answer=sheet.evaluate(p)['value']) for i, (sp, p) in enumerate(HAND)]


def hand_preps():
    return B.prepare(hand_rows())


def build_model(seed=3, vocab_rows=None, boost=True):
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    vocab = CharVocab.build(vocab_rows or hand_rows())
    torch.manual_seed(seed)
    m = Tool(vocab, **SPAN, **SMALL)
    if boost:       # a random head is near-uniform: sharpen it so the ops (and so the tape texts) vary across rounds and rows
        with torch.no_grad():
            m.op_head.weight.mul_(30)
            m.op_head.bias.normal_(0, 3)
    return m.eval()


@pytest.fixture(scope='module')
def model():
    return build_model()


@pytest.fixture(scope='module')
def preps():
    return hand_preps()


# ---------- pure helpers ----------

def test_sha256_check(tmp_path):
    p = tmp_path / 'f.bin'
    p.write_bytes(b'abc')
    want = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    assert LP.sha256_file(str(p)) == want
    for empty in ('', '   '):                      # an empty digest used to mean "no check" silently
        with pytest.raises(ValueError, match='empty sha256'):
            B.check_sha(str(p), empty)
    assert B.check_sha(str(p), want.upper()) == want and B.check_sha(str(p), None) == want
    with pytest.raises(ValueError, match='mismatch'):
        B.check_sha(str(p), '0' * 64)
    with pytest.raises(B.ChecksumRefused):
        B.check_sha(str(p), '0' * 64)


def test_main_reports_only_the_checksum_refusal(monkeypatch, tmp_path):
    """Only check_sha's refusal is 'REFUSED'; any other exception (even a ValueError) propagates unchanged."""
    ev = tmp_path / 'e.jsonl'
    ev.write_text('')
    argv = ['collect', '--ckpt', 'x', '--sha256', '0' * 64, '--label', 'x', '--eval-rows', str(ev), '--out', str(tmp_path / 'o')]
    monkeypatch.setattr(B, 'collect', lambda *a, **k: (_ for _ in ()).throw(B.ChecksumRefused('bad sha')))
    with pytest.raises(SystemExit, match='REFUSED: bad sha'):
        B.main(argv)
    for exc in (ValueError('other value error'), RuntimeError('boom'), AssertionError('premise')):
        monkeypatch.setattr(B, 'collect', lambda *a, _e=exc, **k: (_ for _ in ()).throw(_e))
        with pytest.raises(type(exc)) as ei:
            B.main(argv)
        assert 'REFUSED' not in str(ei.value)


def test_wilson_and_frac():
    lo, hi = B.wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3
    lo, hi = B.wilson(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3
    assert B.wilson(0, 0) is None and B.frac(0, 0) == '0/0'
    assert B.frac(53, 106).startswith('53/106 = 50.0% [')


def test_parse_layout():
    f = B.parse_layout
    assert f('(MAX(B1:B2))*(B2+B3*2)') == ('(K)*(J)', '*', 'MAX(B1:B2)', 'B2+B3*2')
    assert f('(SUM(A1:A2))-(MIN(A1:A2))') == ('(K)-(J)', '-', 'SUM(A1:A2)', 'MIN(A1:A2)')
    assert f('(SUM(A1:A2))   *   (MIN(A1:A2))') == ('(K)*(J)', '*', 'SUM(A1:A2)', 'MIN(A1:A2)')      # the spaced rewrite
    assert f('SUM(A1:A2)+ABS(B3-B2)') == ('K+J', '+', 'SUM(A1:A2)', 'ABS(B3-B2)')
    assert f('SUM(A1:A2)-MIN(A1:A2)')[:2] == ('K-J', '-')
    assert f('SUM(A1:A2)*MIN(A1:A2)')[:2] == ('K*J', '*')
    assert f('B1+B2*2+SUM(A1:A2)') == ('K+J', '+', 'B1+B2*2', 'SUM(A1:A2)')           # left to right: (B1+B2*2) + SUM
    assert f('SUM(A1:A2)') is None and f('B1+B2*2') is None and f('A2/A3') is None    # one piece, not a join


def test_parse_layout_operator_precedence_and_left_associativity():
    """The split is the root of the tree sheet evaluates: * and / bind tighter than + and -, equal levels group to the left. The old parse took the
    first atom of the form X+Y*2 it found, which changed the program for each of these."""
    f = B.parse_layout
    assert f('C1*A1+B1*2') == ('K+J', '+', 'C1*A1', 'B1*2')                           # (C1*A1) + (B1*2), not C1 * (A1+B1*2)
    assert f('C1-A1+B1*2') == ('K+J', '+', 'C1-A1', 'B1*2')                           # (C1-A1) + (B1*2)
    assert f('SUM(A1:A2)*B1/B2') == ('K/J', '/', 'SUM(A1:A2)*B1', 'B2')              # (SUM*B1) / B2
    assert f('SUM(A1:A2)+B1+B2*2') == ('K+J', '+', 'SUM(A1:A2)+B1', 'B2*2')           # (SUM+B1) + (B2*2), not SUM + (B1+B2*2)
    assert f('A1+B1*2*MIN(A1:A2)') == ('K+J', '+', 'A1', 'B1*2*MIN(A1:A2)')
    assert f('C1-A1-B1') == ('K-J', '-', 'C1-A1', 'B1')                                # left-associative
    assert f('A1/B1*SUM(A1:A2)') == ('K*J', '*', 'A1/B1', 'SUM(A1:A2)')
    assert f('(A1+B2*2)*(A1/B1)') == ('(K)*(J)', '*', 'A1+B2*2', 'A1/B1')              # brackets hide their operators
    for formula in ('C1*A1+B1*2', 'C1-A1+B1*2', 'SUM(A1:A2)*B1/B2', 'SUM(A1:A2)+B1+B2*2', 'C1-A1-B1'):
        prompt = 'A: 3 2 1 | B: 6 5 4 | C: 90 80 70 ; =' + formula
        p = B.prep_row(dict(id='x', split='S', prompt=prompt, answer=sheet.evaluate(prompt)['value']))
        assert p['layout'] and p['order_ok'], (formula, p['layout'], p['K'], p['J'])   # K steps, J steps, then the root call: sheet's own order


def test_parse_layout_agrees_with_join_gap_split_where_that_is_right():
    for f in ('SUM(A1:A3)+MAX(B1:B2)', '(SUM(A1:A3))*(ABS(A1-B1))', '(A1+B2*2)*(A1/B1)', 'A1/B1+MIN(A1:A2)', 'A1+B2*2+SUM(A1:A2)'):
        _, op, K, J = B.parse_layout(f)
        assert (op, K, J) == JG.split_formula(f)[:3], f
    # join_gap.split_formula masks the first X+Y*2 it sees and so splits 'SUM(..)+A1+B2*2' as SUM + (A1+B2*2); the sheet evaluates (SUM+A1) + B2*2
    assert JG.split_formula('SUM(A1:A2)+A1+B2*2')[1:3] == ('SUM(A1:A2)', 'A1+B2*2')
    assert B.parse_layout('SUM(A1:A2)+A1+B2*2')[2:] == ('SUM(A1:A2)+A1', 'B2*2')


def test_provenance_is_the_sheet_tools_own_run():
    for sp, p in HAND:
        prov = B.provenance(p)
        steps = sheet.evaluate(p)['steps']
        assert prov is not None and len(prov) == len(steps), p
    prov = B.provenance('A: 80 51 2 | B: 69 79 9 ; =(MAX(B1:B2))*(B2+B3*2)')
    assert prov == [(('cell', 'B1'), ('cell', 'B2')), (('cell', 'B3'), ('const',)), (('cell', 'B2'), ('res', 1)), (('res', 0), ('res', 2))]
    assert B.provenance('A: 1 ; =A1+Z9') is None


def test_prep_row_fields():
    p = B.prep_row(dict(id='x', split='HO', prompt='A: 80 51 2 | B: 69 79 9 ; =(MAX(B1:B2))*(B2+B3*2)', answer='7663'))
    assert p['layout'] == '(K)*(J)' and (p['K'], p['J']) == ('MAX(B1:B2)', 'B2+B3*2') and (p['nK'], p['nJ'], p['n']) == (1, 2, 4)
    assert p['ca_pos'] == 'J' and p['order_ok'] and p['answer_ok'] and p['paren_sensitive']
    assert p['types'] == ['lookup', 'ca_mul', 'ca_add', 'join'] and p['ca'] == dict(start=1, x='B2', y='B3', xv=79, yv=9, shape_ok=True)
    assert p['flat_steps'][0] == p['steps'][0] and p['d'] == 1 and p['flat_steps'][1][0] == 'mul' and p['flat_steps'][1] != p['steps'][1]
    assert 'D' in p['strata'] and 'D_J' in p['strata'] and 'HO_CA_all' in p['strata'] and 'HO4' in p['strata']
    q = B.prep_row(dict(id='y', split='HO', prompt='A: 46 77 58 | B: 86 87 68 ; =(SUM(B1:B3))*(MAX(B2:B3))', answer='20967'))
    assert q['ca_pos'] is None and not q['paren_sensitive'] and q['d'] is None and q['flat_steps'] == q['steps'] and 'HO4_nonD' in B.strata_of(q)
    f = B.prep_row(dict(id='z', split='S5', prompt='A: 27 89 | B: 80 63 ; =SUM(A1:A2)-MIN(A1:A2)', answer='89'))
    assert f['layout'] == 'K-J' and not f['paren_sensitive']
    assert f['types'] == ['lookup', 'lookup', 'join']                 # was `a and b and c or d`, which only checked the last type; the right list is this
    assert B.prep_row(dict(id='w', split='S', prompt='A: 1 2 ; =SUM(A1:A2)', answer='3'))['layout'] is None


def test_position_role_join_when_j_is_a_bare_cell():
    """SUM(A1:A2)+B1: K = SUM (1 step), J = B1 (0 steps), so nK == n - 1 == 1: that round is the JOIN (the old order labelled it J_first)."""
    p = B.prep_row(dict(id='j', split='S', prompt='A: 3 4 | B: 5 6 ; =SUM(A1:A2)+B1', answer='12'))
    assert (p['n'], p['nK'], p['nJ'], p['order_ok']) == (2, 1, 0, True)
    assert [B.position_role(p, k) for k in range(4)] == ['r0', 'join', 'post', 'post']
    assert B.round_labels(p, 1) == {'join'}


# ---------- real rows: strata ----------

def test_real_strata(l5):
    rows = LP.load_jsonl(l5["eval"])
    preps = B.prepare(rows)
    c = B.check_real_strata(preps)
    assert c['D'] == 106 and c['D_K'] == 60 and c['D_J'] == 46 and c['HO_CA_all'] == 126 and c['HO4'] == 139 and c['HO4_nonD'] == 33
    assert c['HO_nonCA'] == 294 and c['HO'] == 420 and c['HPO_CA'] == 146 and c['twins'] == 41
    assert all(p['answer_ok'] for p in preps)
    D = [p for p in preps if 'D' in p['strata']]
    assert all(p['layout'] == '(K)*(J)' and p['order_ok'] and p['paren_sensitive'] and p['d'] == 1 and p['ca']['shape_ok'] for p in D)
    assert {tuple(p['types']) for p in D} == {('ca_mul', 'ca_add', 'lookup', 'join'), ('lookup', 'ca_mul', 'ca_add', 'join')}
    for p in preps:     # the provenance run is the tool's own run
        assert len(B.provenance(p['prompt'])) == p['n']
    differs = []
    for p, r in zip(preps, rows):     # layout parse = the file's own layout column, except where the generator wrote 'K op X+Y*2' without brackets
        if p['layout'] is not None and p['layout'] != r['layout']:
            differs.append((p, r))
    # there the SHEET evaluates (K op X) + Y*2 (left to right, * first), not K op (X+Y*2) as the layout column says: the parse follows the sheet
    assert all(r['layout'] in ('K+J', 'K*J') and B.CA_PARTS.search(r['prompt'].split(';')[1]) for _, r in differs)
    assert len(differs) == 14 and {r['split'] for _, r in differs} == {'S5'}, len(differs)       # K*J written for MIN(..)*B1+A4*2: really (MIN*B1) + A4*2
    assert all(p['order_ok'] and p['layout'] == 'K+J' for p, _ in differs)


def test_real_rows_layout_parse_is_the_sheets_own_program(l5):
    """On every real row (eval + train file), a parsed layout's K, J and op reproduce sheet.evaluate's program: the steps of K, then those of J, then
    the root call (op of the layout) on the values of K and J. The old parse failed this on the unparenthesised K+Y+Z*2 / K*Y+Z*2 rows."""
    rows = LP.load_jsonl(l5["eval"]) + LP.load_jsonl(l5["train"])
    n_split = 0
    for r in rows:
        formula = r['prompt'].split(';', 1)[1].strip()[1:]
        lay = B.parse_layout(formula)
        if lay is None:
            continue
        n_split += 1
        _, op, K, J = lay
        steps = [tuple(s) for s in sheet.evaluate(r['prompt'])['steps']]
        ks, js = B.piece_steps(r['prompt'], K), B.piece_steps(r['prompt'], J)
        kv, jv = (sheet.evaluate(JG.piece_prompt(r['prompt'], x))['value'] for x in (K, J))
        assert steps[:len(ks)] == ks and steps[len(ks):len(ks) + len(js)] == js, r['prompt']
        assert len(steps) == len(ks) + len(js) + 1 and steps[-1][:3] == (sheet.BIN_OP[op], kv, jv), r['prompt']
        assert B.prep_row(r)['order_ok'], r['prompt']
    assert n_split == 8100


def test_real_strata_counts_unchanged_by_the_new_parse(l5):
    preps = B.prepare(LP.load_jsonl(l5["eval"]))
    c = B.strata_counts(preps)
    assert (c['D'], c['HO_CA_all'], c['HPO_CA'], c['twins']) == (106, 126, 146, 41)


# ---------- rewrites ----------

def test_spaced_tokenizer_skips_spaces():
    assert B.spaced_ok()


def test_rewrites_on_all_106(l5):
    preps = B.prepare(LP.load_jsonl(l5["eval"]))
    D = [p for p in preps if 'D' in p['strata']]
    assert len(D) == 106
    made = {}
    for name in B.REWRITES:
        vs, skipped = B.make_versions(D, name, strata=('D',))
        made[name] = len(vs)
        assert len(vs) + sum(skipped.values()) == 106, (name, skipped)
        by = {v['base_id']: v for v in vs}
        for p in D:
            v = by.get(p['id'])
            if v is None:
                assert name in ('minus', 'strip'), (name, p['prompt'])       # a negative K - J, a '?' flat value
                continue
            n = p['n']
            assert v['version'] == name and v['strata'] == p['strata'] and v['value'] != '?'
            if name in ('plus', 'minus'):
                assert v['steps'][:n - 1] == p['steps'][:n - 1]                                # K and J calls identical to the gold
                assert v['steps'][n - 1][0] == ('add' if name == 'plus' else 'sub') and v['steps'][n - 1][1:3] == p['steps'][n - 1][1:3]
            elif name == 'swap':
                assert v['value'] == p['value'] and v['n'] == n and v['layout'] == '(K)*(J)' and (v['K'], v['J']) == (p['J'], p['K'])
                assert v['steps'][-1] == ('mul', p['steps'][-1][2], p['steps'][-1][1], p['steps'][-1][3])
                assert [t for t in v['types']] == (['lookup', 'ca_mul', 'ca_add', 'join'] if p['ca_pos'] == 'K' else ['ca_mul', 'ca_add', 'lookup', 'join'])
            elif name == 'strip':
                assert v['steps'] == p['flat_steps'] and v['layout'] == 'K+J' and v['order_ok'] and not v['paren_sensitive']   # K*X+Y*2 is (K*X) + Y*2
            else:
                assert v['steps'] == p['steps'] and v['value'] == p['value'] and '   *   ' in v['prompt']
    assert made['plus'] == made['swap'] == made['spaced'] == 106
    assert 0 < made['minus'] < 106 and made['strip'] > 0


def test_rewrites_synthetic_relations():
    p = B.prepare([dict(id='a', split='HO', prompt='A: 80 51 2 | B: 69 79 9 ; =(MAX(B1:B2))*(B2+B3*2)', answer='7663')])[0]
    v, why = B.make_version(p, 'plus')
    assert why is None and v['prompt'].endswith('=(MAX(B1:B2))+(B2+B3*2)') and v['value'] == str(79 + 97)
    v, why = B.make_version(p, 'minus')
    assert v is None and why == 'value ?'                                                        # 79 - 97 would be negative
    v, why = B.make_version(p, 'swap')
    assert v['prompt'].endswith('=(B2+B3*2)*(MAX(B1:B2))') and v['value'] == '7663'
    assert [s[0] for s in v['steps']] == ['mul', 'add', 'max', 'mul']
    v, why = B.make_version(p, 'strip')
    assert v['prompt'].endswith('=MAX(B1:B2)*B2+B3*2') and v['steps'] == p['flat_steps'] and v['value'] != p['value']
    q = B.prepare([dict(id='b', split='S5', prompt='A: 1 2 ; =SUM(A1:A2)+MAX(A1:A2)', answer='5')])[0]
    assert B.make_version(q, 'plus') == (None, 'not (K)*(J)')


# ---------- the model: TF pass, free pass, identity ----------

def test_free_pass_equals_greedy(model, preps):
    from domain.mode import greedy
    rows = preps * 5                  # 70 rows: two chunks
    fp = B.free_pass(model, rows, 64)
    gr = greedy(model, [r['prompt'] for r in rows])
    assert len(fp) == len(gr) == 70
    for f, (calls, pred) in zip(fp, gr):
        assert [tuple(c[1:]) for c in f['calls']] == [tuple(c) for c in calls] and f['pred'] == pred
    assert [f['hit'] for f in fp] == [B.hit_of(f['pred'], r['accepted']) for f, r in zip(fp, rows)]


def test_free_pass_batch_independence(model, preps):
    one = [B.free_pass(model, [p], 64)[0] for p in preps]
    allr = B.free_pass(model, preps, 64)
    assert [(f['calls'], f['pred']) for f in one] == [(f['calls'], f['pred']) for f in allr], 'a row\'s free run changed with its batch mates'


def test_tf_pass_basic_and_restores_full_tape(model, preps):
    assert model._full_tape is False and not model.training
    snap = B.drill_state(model)
    out = B.tf_pass(model, preps, 64, margins=True)
    assert model._full_tape is False and not model.training and B.drill_state(model) == snap
    assert all(o['made'] for o in out) and len(out) == len(preps)
    for p, o in zip(preps, out):
        assert len(o['tf']) == 7 and set(o['tf'][0]) >= {'op', 'a', 'b', 'ga', 'gb', 'sa', 'sb', 'ex', 'ei'}
        for k, r in enumerate(o['tf']):
            gold = tuple(p['steps'][k][:3]) if k < p['n'] else None
            assert (r['ex'], r['ei']) == B.judge((r['op'], r['a'], r['b']), gold)
            assert r['sa'] == (r['ga'] >= 0) and r['sb'] == (r['gb'] >= 0)
            assert r['ex'] <= r['ei']                      # exact implies either-order
        assert isinstance(o['ans_tf'], bool) and len(o['lp']) == 7
    assert out[0]['lp_flat'] is not None                                           # hand row 0 is a D row: it has a bracket-stripped call
    assert out[4]['lp_flat'] is None                                                # a non-CA row has no divergence


def test_tf_run_restores_full_tape_on_error(model, preps, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError('boom')
    monkeypatch.setattr(model, 'talk', boom)
    with pytest.raises(RuntimeError):
        B.tf_pass(model, preps[:3], 64)
    assert model._full_tape is False


def test_tf_pass_reports_drops(model):
    bad = B.prepare([dict(id='bad', split='S', prompt='A: 1 2 ; =A1-A2', answer='?'), hand_rows()[2]])
    out = B.tf_pass(model, bad, 64)
    assert out[0] == dict(made=False, drop='zero_steps', caller_training=False) and out[1]['made']


def test_tf_pass_matches_the_free_run_on_the_gold_path(model, preps):
    """Where the free run's calls equal the gold calls so far, the free and TF calls agree (here: at round 0 the tape is empty in both)."""
    fp = B.free_pass(model, preps, 64)
    tf = B.tf_pass(model, preps, 64)
    for f, t in zip(fp, tf):
        c = f['calls'][0] if f['calls'] else None
        r = t['tf'][0]
        assert (c is None and r['op'] == B.NOOP) or (c is not None and (c[1], c[2], c[3]) == (r['op'], r['a'], r['b']))


def own_call_records(m, rows):
    """Records for identity_check built from the model's OWN free calls taken as gold, one chunk."""
    from custom_io.models.tool import NAMES, entry
    o, ans, batch = B.free_chunk(m, [r['prompt'] for r in rows])
    op = torch.zeros(len(rows), B.N_RES, dtype=torch.long)
    tape = [[''] * B.N_RES for _ in rows]
    gold = [[None] * B.N_RES for _ in rows]
    for i in range(len(rows)):
        for t, opn, a, b, r in o['calls'][i]:
            op[i, t - 1] = NAMES.index(opn)
            tape[i][t - 1] = entry(opn, a, b, r)
            gold[i][t - 1] = (opn, a, b)
    o2, ans2 = B.tf_run(m, batch, dict(op=op, tape=tape))
    rounds = B.tf_rounds(m, o2)
    recs = []
    for i, r in enumerate(rows):
        recs.append(dict(id=r['id'], version='orig', tf=B.judge_rounds(rounds[i], gold[i]), ans_tf=B.hit_of(ans2[i], [ans[i]]),
                         gold=[list(c[1:]) for c in o['calls'][i]], free=dict(calls=[list(c) for c in o['calls'][i]], pred=ans[i],
                                                                              hit=B.hit_of(ans[i], [ans[i]]))))
    return recs, o, o2


def test_identity_own_calls(model, preps):
    """Teacher-force the model's own free calls as the gold: every round TF-exact, answers equal, op / gate / pointer logits identical."""
    rows = preps * 6
    recs, o, o2 = own_call_records(model, rows[:64])
    ncalls = sum(len(r['free']['calls']) for r in recs)
    assert ncalls > 64, 'the random model must write calls for the test to mean anything'
    assert len({c[1] for r in recs for c in r['free']['calls']}) >= 2, 'ops must vary'
    assert all(B.predicted_hit(r) for r in recs)
    idc = B.identity_check(recs)
    assert idc['table'] == {(True, True): 64} and idc['agree'] == 64 and not idc['mismatches']
    res = B.own_call_identity(model, rows, 64)
    assert res['n'] == len(rows) and res['bad'] == [] and res['ans_bad'] == [] and res['max_diff'] <= 1e-6, res['max_diff']
    for st, st2 in zip(o['steps'], o2['steps']):
        assert torch.equal(st[0], st2[0])


def test_identity_is_sensitive_to_the_tape_text(model, preps):
    """Control: the same prompt with a different tape entry text gives different logits at later rounds, so the identity test above could fail."""
    from custom_io.models.tool import NAMES, entry
    rows = preps[:4]
    o, ans, batch = B.free_chunk(model, [r['prompt'] for r in rows])
    op = torch.zeros(4, B.N_RES, dtype=torch.long)
    op[:, :3] = NAMES.index('add')
    tape_a = [['add 1 2 = 3', 'add 3 4 = 7', 'add 7 8 = 15'] + [''] * 4 for _ in rows]
    tape_b = [['add 5 2 = 7', 'add 3 4 = 7', 'add 7 8 = 15'] + [''] * 4 for _ in rows]
    oa, _ = B.tf_run(model, batch, dict(op=op, tape=tape_a))
    ob, _ = B.tf_run(model, batch, dict(op=op, tape=tape_b))
    assert torch.equal(oa['steps'][0][0], ob['steps'][0][0])                  # round 0 sees no tape
    assert not torch.equal(oa['steps'][1][0], ob['steps'][1][0])              # round 1 sees entry 0


def rec_of(p, wrong=(), ans_tf=True, free_hit=None, calls=None):
    """A record for the pure analysis functions: item p of the prepared rows with TF-wrong rounds `wrong` (a dict round -> (op, a, b)). calls = the free
    run's calls; by default those the identity predicts (the gold calls before the first TF-wrong round, the TF call at it), so the record satisfies the
    round-level identity."""
    tf = []
    for k in range(7):
        gold = tuple(p['steps'][k][:3]) if k < p['n'] else None
        call = wrong[k] if isinstance(wrong, dict) and k in wrong else gold or (B.NOOP, '', '')
        ex, ei = B.judge(call, gold)
        tf.append(dict(op=call[0], a=call[1], b=call[2], ga=1.0, gb=1.0, sa=True, sb=True, ex=ex, ei=ei))
    if calls is None:
        kw = next((k for k, r in enumerate(tf) if not r['ex']), None)
        calls = [[k + 1, *p['steps'][k]] for k in range(p['n'] if kw is None else min(kw, p['n']))]
        if kw is not None and tf[kw]['op'] != B.NOOP:
            calls.append([kw + 1, tf[kw]['op'], tf[kw]['a'], tf[kw]['b'], '0'])
    rec = {k: p[k] for k in B.KEEP}
    rec.update(gold=[list(s) for s in p['steps']], flat=[list(s) for s in p['flat_steps']], tf=tf, ans_tf=ans_tf, label='t',
               free=dict(calls=calls, pred='x', hit=int(bool(free_hit))), dropped=None, lp=None, lp_flat=None)
    rec['wrong'] = B.annotate_wrong(rec)
    return rec


def test_identity_check_reason_classes(preps):
    D_J = preps[2]                      # (MAX(B1:B2))*(B2+B3*2): max 69 79 | mul 9 2 | add 79 18 | mul 79 97
    g = [tuple(s[:3]) for s in D_J['steps']]
    free_ok = [[k + 1, *D_J['steps'][k]] for k in range(4)]

    def mism(wrong, **kw):
        r = rec_of(D_J, wrong, **kw)
        idc = B.identity_check([r])
        return idc['mismatches'][0]['reason'] if idc['mismatches'] else None

    assert mism({}, free_hit=True) is None and mism({}, free_hit=False) == 'other'     # predicted hit but missed: not explained by a call
    assert mism({0: ('max', '79', '69')}, free_hit=True) == 'either-order-only'
    assert mism({0: ('max', '069', '79')}, free_hit=True) == 'normalised-number-only'
    assert mism({4: ('add', '1', '2')}, free_hit=True) == 'extra call'
    assert mism({2: (B.NOOP, '', '')}, free_hit=True) == 'missing call/NOOP'
    assert mism({1: ('mul', '9', '3')}, free_hit=True) == 'alternative program'
    assert mism({1: ('mul', '9', '3')}, free_hit=False) is None                        # predicted miss, observed miss: no mismatch
    r = rec_of(D_J, {0: ('max', '79', '69')}, free_hit=True, calls=free_ok)
    assert B.mismatch_reason(r)[1:] == (0, 'either-order-only') and r['wrong'][0]['kind'] == 'format only'


def test_roles_and_repair_sets(preps):
    DK, DJ, HOnon = preps[0], preps[2], preps[4]
    assert [B.position_role(DK, k) for k in range(7)] == ['r0', 'K_cont', 'J_first', 'join', 'post', 'post', 'post']
    assert [B.position_role(DJ, k) for k in range(7)] == ['r0', 'J_first', 'J_cont', 'join', 'post', 'post', 'post']
    assert B.round_labels(DJ, 1) == {'J_first', 'ca_mul', 'd'} and B.round_labels(DK, 1) == {'K_cont', 'ca_add', 'd'}
    assert B.round_labels(DK, 5) == {'post'} and B.round_labels(HOnon, 2) == {'J_first', 'lookup'}

    def C(p, wrong, ans_tf=True):
        r = rec_of(p, wrong, ans_tf)
        return {name: B.repair_ok(r, S) for name, S in B.REPAIR_SETS.items()}
    bad = lambda p, k: ('add', '1', '1') if k < p['n'] else ('add', '1', '1')
    c = C(DJ, {1: bad(DJ, 1)})                      # only the boundary round (the ca_mul of a D_J item) wrong
    assert c['J_first'] and c['ca_mul'] and c['d'] and c['r0+J_first'] and not c['r0'] and not c['join'] and not c['none'] and not c['ca_add']
    c = C(DJ, {0: bad(DJ, 0), 1: bad(DJ, 1)})
    assert c['r0+J_first'] and not c['r0'] and not c['J_first'] and not c['ca_mul']
    c = C(DK, {0: bad(DK, 0)})                      # the ca_mul of a D_K item at round 0
    assert c['r0'] and c['ca_mul'] and not c['d'] and not c['J_first']
    c = C(DJ, {}, ans_tf=False)
    assert c['answer'] and not c['none'] and not c['r0']
    c = C(DJ, {3: bad(DJ, 3)}, ans_tf=False)
    assert not c['join'] and not c['answer']        # the readout is wrong too and 'answer' is not in the set {join}
    t = B.repair_table([rec_of(DJ, {1: bad(DJ, 1)}), rec_of(DJ, {}), rec_of(DJ, {3: bad(DJ, 3)})])
    assert t['none'] == (1, 3) and t['J_first'] == (2, 3) and t['join'] == (2, 3) and t['d'] == (2, 3)


def test_position_roles_of_items_that_are_not_order_ok(preps):
    DJ = dict(preps[2])
    assert DJ['order_ok'] and DJ['nK'] is not None
    assert [B.position_role(DJ, k) for k in range(7)] == ['r0', 'J_first', 'J_cont', 'join', 'post', 'post', 'post']
    DJ['order_ok'] = False                                 # nK is still set, but is no boundary of an item whose program is not K, J, join
    assert [B.position_role(DJ, k) for k in range(7)] == ['r0', 'unordered', 'unordered', 'unordered', 'post', 'post', 'post']
    assert B.round_labels(DJ, 1) == {'unordered', 'ca_mul', 'd'}
    assert B.position_role(dict(DJ, nK=None), 2) == 'unordered'


def test_self_check_indices(preps):
    ps = []
    for rep in range(40):                                  # 40 copies of the hand rows: 4 D rows each (the HO rows with 4 calls and a CA piece)
        for p in preps:
            ps.append(dict(p, id=f'{p["id"]}-{rep}'))
    ndr = sum(1 for p in ps if 'D' in p['strata'])
    assert ndr == 160
    idx = B.self_check_indices(ps, 256)
    assert idx == sorted(set(idx)) and len(idx) == 256
    assert {i for i, p in enumerate(ps) if 'D' in p['strata']} <= set(idx)           # every D row
    cells = {c: sum(1 for i in idx if ps[i]['split'] == c) for c in {p['split'] for p in ps}}
    assert all(v >= 1 for v in cells.values()), cells                                  # every cell is sampled
    assert B.self_check_indices(ps, 256) == idx                                        # fixed seed
    assert B.self_check_indices(ps, 256, seed=1) != idx
    small = B.self_check_indices(ps, 200)
    assert len(small) == 200 and {i for i, p in enumerate(ps) if 'D' in p['strata']} <= set(small)
    assert len(B.self_check_indices(ps, 10)) == ndr                                    # D rows always, even over budget
    assert len(B.self_check_indices(ps, 10 ** 6)) == len(ps)


def test_classifiers(preps):
    DJ = preps[2]                        # a=80 51 2 | B: 69 79 9: x = B2 = 79, y = B3 = 9; flat program's round 1 is mul 79 79 ... checked below
    r = rec_of(DJ, {1: ('mul', '79', '2')})
    assert B.ca_took_x(r, 1) and r['wrong'][0]['ca_took_x'] and r['wrong'][0]['kind'] == 'wrong_named_cell'
    r = rec_of(DJ, {1: ('mul', '2', '79')})
    assert B.ca_took_x(r, 1)                                                      # either order
    r = rec_of(DJ, {1: ('mul', '9', '3')})
    assert not B.ca_took_x(r, 1) and r['wrong'][0]['kind'] == 'other_number'                  # 3 is neither a grid number nor a literal here
    r = rec_of(DJ, {0: ('min', '69', '79')})
    assert r['wrong'][0]['kind'] == 'wrong op'
    r = rec_of(DJ, {0: ('max', '69', '51')})                                       # 51 is a grid cell the formula does not name
    assert r['wrong'][0]['kind'] == 'unnamed_cell'
    r = rec_of(DJ, {3: ('mul', '79', '18')})                                       # 18 is the round-1 result, not a grid number
    assert r['wrong'][0]['kind'] == 'intermediate'
    r = rec_of(DJ, {1: ('add', '79', '18')})
    assert r['wrong'][0]['kind'] == 'later step done first'
    r = rec_of(DJ, {5: ('add', '1', '2'), 2: (B.NOOP, '', '')})
    assert sorted((w['k'], w['kind']) for w in r['wrong']) == [(2, 'missing call (NOOP)'), (5, 'extra call')]
    # matches_flat: the stripped program MAX(B1:B2)*B2+B3*2 does round 1 = mul 79 79 (max result * B2), not mul 9 2
    fl = DJ['flat_steps']
    r = rec_of(DJ, {1: tuple(fl[1][:3])})
    assert DJ['d'] == 1 and B.matches_flat(r, 1) and r['wrong'][0]['matches_flat']
    r = rec_of(DJ, {1: (fl[1][0], fl[1][2], fl[1][1])}) if fl[1][0] in B.SYM else r
    assert B.matches_flat(r, 1)
    assert not B.matches_flat(rec_of(preps[4], {0: ('add', '1', '2')}), 0)


def test_matches_flat_is_not_commutative_for_sub_and_div_and_only_at_round_d():
    """join_gap.same_call swaps operands only for add / mul / min / max: a flat program's SUB call written with its operands swapped is another call.
    And only the divergence round d is evidence; a wrong call later that equals the flat program's call there is coincidental (flat_coincides)."""
    p = B.prep_row(dict(id='n', split='HO', prompt='A: 3 2 1 | B: 99 40 5 ; =(MAX(B1:B2))-(B3+A1*2)', answer='88'))
    assert p['layout'] == '(K)-(J)' and p['paren_sensitive'] and p['d'] == 1
    assert p['steps'] == [('max', '99', '40', '99'), ('mul', '3', '2', '6'), ('add', '5', '6', '11'), ('sub', '99', '11', '88')]
    assert p['flat_steps'] == [('max', '99', '40', '99'), ('sub', '99', '5', '94'), ('mul', '3', '2', '6'), ('add', '94', '6', '100')]
    assert B.matches_flat(rec_of(p, {1: ('sub', '99', '5')}), 1)                          # the flat call at d, as written
    assert not B.matches_flat(rec_of(p, {1: ('sub', '5', '99')}), 1)                      # sub is not commutative: swapped operands are another call
    assert not rec_of(p, {1: ('sub', '5', '99')})['wrong'][0]['matches_flat']
    assert not B.matches_flat(rec_of(p, {1: ('add', '99', '5')}), 1)                      # another op
    assert B.JG.same_call(('mul', '2', '3'), ('mul', '3', '2'))                           # control: a commutative op does match swapped
    # after d: the flat call of round 2 (mul 3 2), written at round 2 where the gold wants add: equal to the flat call but NOT matches_flat
    r = rec_of(p, {1: ('sub', '99', '5'), 2: ('mul', '3', '2')})
    assert B.matches_flat(r, 1) and not B.matches_flat(r, 2) and B.flat_coincides(r, 2) and not B.flat_coincides(r, 1)
    w = {x['k']: x for x in r['wrong']}
    assert w[1]['matches_flat'] and not w[1]['flat_coincides'] and w[2]['flat_coincides'] and not w[2]['matches_flat']


def gold_forced_vs_tf(m, preps_, bs=64):
    """Free run with the GOLD call forced at every round (NOOP past the program) against the TF run of the same rows (same chunks): -> (rows whose free
    tape text differs from the gold tape, largest gate / span-pointer logit difference, rows seen). Along the gold path the two runs are the same run."""
    r = gold_path_check(m, preps_, bs)
    return r['n'] - r['ok'], r['max_diff'], r['n'] + r['dropped']


def test_gold_calls_forced_into_a_free_run_reproduce_the_tf_run(model, preps):
    bad, worst, n = gold_forced_vs_tf(model, preps)
    assert n == len(preps) and bad == 0 and worst <= 1e-6, (bad, worst)


def test_gold_forced_free_run_equals_tf_run_on_all_real_rows(l5):
    """The premise of the identity on the real rows: with the gold calls on the tape the free run writes exactly the gold tape text (the calculator's
    reply equals progparse's value text for every entry of all 2,100 eval rows) and the controller sees exactly what it sees under teacher forcing."""
    rows = LP.load_jsonl(l5["eval"])
    m = build_model(3, vocab_rows=rows)
    ps = B.prepare(rows)
    bad, worst, n = gold_forced_vs_tf(m, ps)
    assert n == 2100 and bad == 0 and worst <= 1e-6, (bad, worst)
    assert all(o['made'] for o in B.tf_pass(m, ps, 64)), 'make_row dropped a real eval row'


# ---------- forced runs ----------

def free_logits(m, rows):
    o, ans, _ = B.free_chunk(m, [r['prompt'] for r in rows])
    return o, ans


def test_forced_run_forces_exactly_the_call(model, preps):
    from custom_io.models.tool import calc, entry
    rows = preps[:6]
    base = B.forced_run(model, rows, {})
    base2 = B.free_pass(model, rows, 64, with_tape=True)
    assert [b['calls'] for b in base] == [b['calls'] for b in base2] and [b['tape'] for b in base] == [b['tape'] for b in base2]
    k = 2
    force = {(1, k): ('add', '12', '5'), (3, k): ('mul', '7', '8'), (4, 0): ('max', '3', '9'), (5, k): (B.NOOP, '', '')}
    res = B.forced_run(model, rows, force)
    assert res[1]['tape'][k] == entry('add', '12', '5', calc('add', '12', '5')) == 'add 12 5 = 17'
    assert res[3]['tape'][k] == 'mul 7 8 = 56'
    assert res[4]['tape'][0] == 'max 3 9 = 9'
    assert res[5]['tape'][k] == '' and all(c[0] != k + 1 for c in res[5]['calls'])
    for i, kk in ((1, k), (3, k), (5, k)):                       # rounds before the forced one are untouched
        assert res[i]['tape'][:kk] == base[i]['tape'][:kk] and [c for c in res[i]['calls'] if c[0] <= kk] == [c for c in base[i]['calls'] if c[0] <= kk]
    for i in (0, 2):                                              # rows with nothing forced are identical
        assert res[i] == base[i]
    assert [c[:4] for c in res[1]['calls'] if c[0] == k + 1] == [[k + 1, 'add', '12', '5']]


def test_forced_run_restores_everything(model, preps):
    rows = preps[:8]
    o0, a0 = free_logits(model, rows)
    free0 = B.free_pass(model, rows, 64)
    B.forced_run(model, rows, {(0, 1): ('add', '1', '2'), (2, 0): ('sub', '9', '3')})
    o1, a1 = free_logits(model, rows)
    assert a0 == a1 and all(torch.equal(x[0], y[0]) and torch.equal(x[1], y[1]) for x, y in zip(o0['steps'], o1['steps']))
    assert B.free_pass(model, rows, 64) == free0
    assert 'written' not in model.__dict__ and len(model.op_head._forward_hooks) == 0
    with pytest.raises(RuntimeError):                            # and restored when the run raises
        with B.forcing(model, {0: {0: ('add', '1', '1')}}):
            assert 'written' in model.__dict__ and len(model.op_head._forward_hooks) == 1
            raise RuntimeError('x')
    assert 'written' not in model.__dict__ and len(model.op_head._forward_hooks) == 0
    o2, a2 = free_logits(model, rows)
    assert a2 == a0 and all(torch.equal(x[0], y[0]) for x, y in zip(o0['steps'], o2['steps']))


def test_forcing_counts_rounds_per_run(model, preps):
    with B.forcing(model, {}) as cnt:
        free_logits(model, preps[:3])
        assert (cnt['op'], cnt['written'], len(cnt['raw'])) == (7, 7, 7)


# ---------- validate_repair on a scripted model ----------

def scripted_model(rows, wrong_round, bad=('add', '1', '1')):
    """A model whose calls are the gold calls except the call at wrong_round[i] (None, a round, or a tuple of rounds) of row i (the call `bad`), written
    through the same two patches forced_run uses (op_head hook at +1e3, below LARGE_LOGIT, so a forced call wins; m.written), and whose answer readout
    DEPENDS ON THE TAPE: the result of the last tape entry if every written entry is the gold entry text, else '?'. Rows are recognised by their
    prompt (the prompts of `rows` are distinct), not by their batch index, so any sub-batch of them behaves the same. Returns (model, undo)."""
    from custom_io.models.tool import NAMES, entry
    m = build_model()
    assert len({p['prompt'] for p in rows}) == len(rows)
    gold_tape = {p['prompt']: [entry(*s_) for s_ in p['steps']] for p in rows}
    wr = {}
    for i, p in enumerate(rows):
        w = wrong_round[i]
        wr[p['prompt']] = (p, () if w is None else (w,) if isinstance(w, int) else tuple(w))
    cnt, cur = dict(op=0, written=0), []
    orig_written, orig_run = m.written, m.run

    def call_of(i, k):
        if i >= len(cur) or cur[i] not in wr:
            return None
        p, ws = wr[cur[i]]
        return bad if k in ws else (tuple(p['steps'][k][:3]) if k < p['n'] else None)

    def run(batch, *a, **kw):
        cur[:] = [r['prompt'] for r in batch['rows']]
        return orig_run(batch, *a, **kw)

    def hook(mod, inp, out):
        k, cnt['op'] = cnt['op'] % 7, cnt['op'] + 1
        out = out.clone()
        for i in range(out.shape[0]):
            c = call_of(i, k)
            out[i, NAMES.index(c[0]) if c else 0] += 1e3
        return out

    def written(st):
        k, cnt['written'] = cnt['written'] % 7, cnt['written'] + 1
        res = list(orig_written(st))
        for i in range(len(res)):
            c = call_of(i, k)
            if c:
                res[i] = c[1:3]
        return res

    def talk(state, batch):
        out = []
        for i, r in enumerate(batch['rows']):
            tape = [t for t in B.tape_texts(m, state)[i] if t]
            out.append(tape[-1].split('= ')[-1] if tape and tape == gold_tape.get(r['prompt'], [])[:len(tape)] else '?')
        return out
    h = m.op_head.register_forward_hook(hook)
    m.written, m.talk, m.state_of, m.run = written, talk, lambda o: o, run

    def undo():
        h.remove()
        for a_ in ('written', 'talk', 'state_of', 'run'):
            del m.__dict__[a_]
    return m, undo


def test_validate_repair_on_a_scripted_model(preps):
    """A model scripted through the same patches: its calls are the gold calls except one wrong round per item, and its readout is a function of the
    tape (the last entry's result when the whole tape is the gold tape, else '?'). So forcing a WRONG call misses and forcing the GOLD call hits, which
    validate_repair must find, in both directions."""
    rows = preps[:6]
    wrong_round = {i: (i % 2) + 1 for i in range(len(rows))}
    BAD = ('add', '1', '1')
    assert all(tuple(p['steps'][wrong_round[i]][:3]) != BAD for i, p in enumerate(rows))
    m, undo = scripted_model(rows, wrong_round, BAD)
    try:
        tf = B.tf_pass(m, rows, 64)
        free = B.free_pass(m, rows, 64)
        recs = [B.make_record('s', p, f, t) for p, f, t in zip(rows, free, tf)]
        assert [B.wrong_rounds(r) for r in recs] == [[wrong_round[i]] for i in range(len(rows))]
        assert all(r['ans_tf'] for r in recs)                                   # the readout under the gold tape is right
        assert [f['hit'] for f in free] == [0] * len(rows)                      # the unforced scripted run keeps its wrong call: a miss
        wrong = B.forced_run(m, rows, {(i, wrong_round[i]): BAD for i in range(len(rows))})
        gold = B.forced_run(m, rows, {(i, wrong_round[i]): tuple(rows[i]['steps'][wrong_round[i]][:3]) for i in range(len(rows))})
        assert [f['hit'] for f in wrong] == [0] * len(rows) and [f['pred'] for f in wrong] == ['?'] * len(rows)     # forcing a WRONG call: a miss
        assert [f['hit'] for f in gold] == [1] * len(rows)                                                          # forcing the GOLD call: a hit
        out = validate_repair(m, rows, recs, sample=None)
        assert out['n'] == len(rows) and out['agree'] == len(rows) and not out['mismatches']
        assert B.repair_table(recs)['none'][0] == 0
        for r in recs:                                                          # the opposite claim (the TF readout is wrong) disagrees with the forced hit
            r['ans_tf'] = False
        out = validate_repair(m, rows, recs, sample=None)
        assert out['agree'] == 0 and len(out['mismatches']) == len(rows)
    finally:
        undo()
    assert 'written' not in m.__dict__ and len(m.op_head._forward_hooks) == 0


def test_forced_call_not_written_exactly_raises(model, preps):
    """A competing op_head hook (+1e5, beating the forcing patch's +1e4) used to leave the call unforced and silently scored it: now an error."""
    rows = preps[:4]
    from custom_io.models.tool import NAMES
    force = {(1, 2): ('add', '12', '5'), (2, 0): ('mul', '7', '8')}
    B.forced_run(model, rows, force)                                          # fine without the competitor

    def compete(mod, inp, out):
        out = out.clone()
        out[:, NAMES.index('sub')] += 1e5
        return out
    h = model.op_head.register_forward_hook(compete)
    try:
        with pytest.raises(B.ForcedCallError, match='not written exactly'):
            B.forced_run(model, rows, force)
        with pytest.raises(B.ForcedCallError):                                # also a forced NOOP that the competitor overrode with a call
            B.forced_run(model, rows, {(0, 1): (B.NOOP, '', '')})
        B.free_pass(model, rows, 64)                                          # an unforced run is not checked
    finally:
        h.remove()
    assert 'written' not in model.__dict__ and len(model.op_head._forward_hooks) == 0


def test_validate_repair_detects_a_broken_counterfactual(preps):
    """Same scripted model, but its readout is right only while the tape is the gold tape: with the forced call the tape equals the gold one at the
    wrong round but the run's later rounds are still scripted wrong ones, so the free hit and the prediction disagree and validate_repair says so."""
    m = build_model()
    rows = preps[:4]
    recs = []
    for p in rows:
        r = rec_of(p, {1: ('add', '1', '1')}, ans_tf=True)
        recs.append(r)
    out = validate_repair(m, rows, recs, sample=None)         # the unscripted random model cannot reach the answer after the repair
    assert out['n'] == 4 and out['agree'] < 4 and len(out['mismatches']) == 4 - out['agree']


# ---------- margins ----------

def test_margins_finite_and_deterministic(model, preps):
    a = margins(model, preps, 64)
    b = margins(model, preps, 64)
    assert a == b
    for r, p in zip(a, preps):
        assert len(r['lp']) == 7 and all(torch.isfinite(torch.tensor(x)) for x in r['lp'])
        assert (r['lp_flat'] is None) == (p['d'] is None)
        if p['d'] is not None:
            assert torch.isfinite(torch.tensor(r['lp_flat']))
    # a row's margins do not depend on its batch mates
    one = margins(model, preps[2:3], 64)[0]
    assert all(abs(x - y) < 1e-4 for x, y in zip(one['lp'], a[2]['lp'])) and abs(one['lp_flat'] - a[2]['lp_flat']) < 1e-4


def test_margins_equal_the_training_terms(preps):
    """The proxy is the model's own training log-likelihood terms for rows whose every operand is a number token of the visible context: the op
    log-probs plus the span terms (gate + pointer, either order) equal -(op CE) - span_call of Tool.span_terms for a one-row batch. Used for
    checking only; margins never call m.loss()."""
    import torch.nn.functional as F
    from custom_io.models.tool import NAMES, Tool
    m = build_model(boost=False)
    checked = 0
    for p in preps:
        from domain import mode
        cons = json.load(open(mode.CONST_PATH))
        g_row, why = mode.make_row(m, 'domain_sheet', p['prompt'], p['value'], p['steps'], cons, 'tool')
        batch = B.make_batch(m, [g_row])
        g = m.gold(batch['rows'], 'cpu')
        o, _ = B.tf_run(m, batch, g)
        Ma, Mb, _, _ = m.span_gold(batch['rows'], batch['prompt_ids'].shape[1], o['le'], o['K'], g['rowg'])
        if not all(Ma[0, k].any() and Mb[0, k].any() for k in range(p['n'])):
            continue
        checked += 1
        mg = B.margins_batch(m, o, batch)[0]['lp']
        ops = g['rowg'][0][0]
        lop = [float(F.log_softmax(st[0][0].float(), -1)[ops[k] if k < len(ops) else 0]) for k, st in enumerate(o['steps'])]
        terms, _ = Tool.span_terms(m, o, g, batch, 1)
        assert abs(sum(mg) - (sum(lop) - float(terms['span_call']))) < 1e-3, (p['prompt'], sum(mg), sum(lop), float(terms['span_call']))
    assert checked >= 6


def test_margins_equal_the_training_terms_cells_only():
    """A model without span copy: the proxy is the op CE plus the cells' NLL, both orders for commutative ops (Tool.call_loss), exactly."""
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    from domain import mode
    rows = hand_rows()
    torch.manual_seed(7)
    m = Tool(CharVocab.build(rows), **SMALL).eval()
    cons = json.load(open(mode.CONST_PATH))
    for p in B.prepare(rows)[:6]:
        g_row, _ = mode.make_row(m, 'domain_sheet', p['prompt'], p['value'], p['steps'], cons, 'tool')
        batch = B.make_batch(m, [g_row])
        g = m.gold(batch['rows'], 'cpu')
        o, _ = B.tf_run(m, batch, g)
        mg = B.margins_batch(m, o, batch)[0]['lp']
        lop, lcall, _, _ = m.call_loss(o['steps'], g, 1)
        assert abs(sum(mg) - (-float(lop) - float(lcall))) < 1e-3, (sum(mg), float(lop), float(lcall))


# ---------- identity at round level, scripted model with hits ----------

def scripted_records(rows, wrong_round, bad=('add', '1', '1')):
    m, undo = scripted_model(rows, wrong_round, bad)
    try:
        tf = B.tf_pass(m, rows, 64)
        free = B.free_pass(m, rows, 64)
        recs = [B.make_record('s', p, f, t) for p, f, t in zip(rows, free, tf)]
        return m, undo, recs, free
    except Exception:
        undo()
        raise


def test_identity_on_a_scripted_model_with_hits():
    """Items with no wrong round HIT (free hit 1, predicted 1), items with one wrong round miss: the 2x2 table has all-diagonal mass in both cells, so the
    agreement is not the trivial 'nothing ever hits' one, and the round-level identity (free calls = gold calls up to the first wrong round, free call
    there = TF call) holds on every item."""
    rows = hand_preps()[:8]
    wrong_round = {0: None, 1: 1, 2: None, 3: 2, 4: None, 5: 0, 6: (1, 3), 7: None}
    m, undo, recs, free = scripted_records(rows, wrong_round)
    try:
        idc = B.identity_check(recs)
        assert [f['hit'] for f in free] == [1, 0, 1, 0, 1, 0, 0, 1]
        assert idc['table'] == {(True, True): 4, (False, False): 4} and idc['n'] == 8 and idc['agree'] == 8
        assert idc['round_agree'] == 8 and idc['round_mismatches'] == []
        assert [B.wrong_rounds(r) for r in recs] == [[], [1], [], [2], [], [0], [1, 3], []]
        # the check can fail: a free run whose call before the first wrong round is not the gold call, or whose call at the wrong round is not the TF call
        r = json.loads(json.dumps(recs[3]))
        r['free']['calls'][0][2] = '99'                                                  # round 0 call differs from the gold, before the wrong round 2
        assert B.round_identity(r)[:2] == (False, 0)
        r = json.loads(json.dumps(recs[3]))
        r['free']['calls'][2][1] = 'sub'                                                 # the wrong round's free call differs from the TF call
        assert B.round_identity(r)[:2] == (False, 2)
        r = json.loads(json.dumps(recs[0]))
        r['free']['calls'].append([6, 'add', '1', '2', '3'])                             # an extra free call where gold and TF both stop
        assert B.round_identity(r)[:2] == (False, 5)
        bad = B.identity_check([r, recs[1]])
        assert bad['round_agree'] == 1 and bad['round_mismatches'][0]['id'] == r['id']
    finally:
        undo()


def test_validate_all_on_a_scripted_model():
    """validate_all: every D item with one wrong round, a seeded sample of the other strata, the repair sets r0 / J_first / d / r0+J_first, each forced
    with real free runs; the scripted model makes the forced gold call hit, as the prediction says."""
    rows = hand_preps()
    wrong_round = {0: 0, 1: 1, 2: 1, 3: (0, 1), 4: 2, 5: None, 6: 0, 7: 1, 8: 0, 9: 1, 10: 2, 11: None, 12: 1, 13: 2}
    m, undo, recs, free = scripted_records(rows, wrong_round)
    try:
        assert [i for i, r in enumerate(recs) if 'D' in r['strata']] == [0, 1, 2, 3]
        v = B.validate_all(m, rows, recs, sample=None)
        D = v['strata']['D']
        assert D['n'] == 3 and D['agree'] == 3 and D['mismatches'] == [] and D['rate'] == 0.0        # items 0, 1, 2 (item 3 has two wrong rounds)
        assert v['strata']['D_K']['n'] == 2 and v['strata']['D_J']['n'] == 1
        assert v['sets']['r0']['n'] == 1                                                              # item 0 (wrong at round 0 only)
        assert v['sets']['d']['n'] == 2                                                               # items 1, 2 (round 1 is d)
        assert v['sets']['J_first']['n'] == 1                                                         # item 2 (D_J: round 1 is J_first)
        assert v['sets']['r0+J_first']['n'] == 3                                                      # items 0 (r0), 2 (J_first) and 3 ({0, 1}: r0 and J_first of a D_J item)
        assert all(a['agree'] == a['n'] for kind in ('strata', 'sets') for a in v[kind].values())
        assert v['strata']['HO']['n'] == 5 and v['strata']['S5']['n'] == 3
        w = B.validate_all(m, rows, recs, sample=2)                                                   # a sample of 2 per non-D stratum, seeded
        assert w['strata']['HO']['n'] == 2 and w['strata']['S5']['n'] == 2 and w['strata']['D']['n'] == 3
        assert B.validate_all(m, rows, recs, sample=2) == w                                           # deterministic
        assert B.validate_all(m, rows, recs, sample=0)['strata']['HO']['n'] == 0
        for r in recs[:3]:                                                                            # a wrong prediction is found, with a rate
            r['ans_tf'] = False
        x = B.validate_all(m, rows, recs, sample=None)
        assert x['strata']['D']['agree'] == 0 and x['strata']['D']['rate'] == 1.0 and len(x['strata']['D']['mismatches']) == 3
        assert x['strata']['D']['mismatches'][0] == dict(id='h0', rounds=[0], predicted=False, observed=True)
    finally:
        undo()
    assert 'written' not in m.__dict__ and 'run' not in m.__dict__ and len(m.op_head._forward_hooks) == 0


# ---------- premise check with drops, shared TF run ----------

def test_gold_path_check_compares_logits_in_chunks_with_drops(model):
    """A chunk with a make_row-dropped row used to skip the logit comparison and report max_diff 0.0; now its other rows are compared (the free run is
    of the made rows only, so both runs hold the same rows), the dropped row is listed as not checked, and the counts of chunks / rows are recorded."""
    bad = B.prepare([dict(id='bad', split='S', prompt='A: 1 2 ; =A1-A2', answer='?')] + hand_rows()[:5])
    pc = gold_path_check(model, bad, 64)
    assert (pc['n'], pc['ok'], pc['dropped'], pc['dropped_idx'], pc['bad_ids']) == (5, 5, 1, [0], [])
    assert pc['logit_chunks'] == [1, 1] and pc['logit_rows'] == 5 and pc['max_diff'] is not None and pc['max_diff'] <= 1e-6
    two = gold_path_check(model, bad * 20, 64)                               # 120 rows: 2 chunks, both with drops
    assert two['logit_chunks'] == [2, 2] and two['dropped'] == 20 and two['n'] == 100
    alldrop = gold_path_check(model, bad[:1] * 3, 64)                        # nothing made: nothing compared, and it says so (not 0.0)
    assert alldrop['n'] == 0 and alldrop['max_diff'] is None and alldrop['logit_chunks'] == [0, 1]


def test_premise_of_does_not_count_dropped_rows_as_passes(model):
    items = B.prepare([dict(id='bad', split='S', prompt='A: 1 2 ; =A1-A2', answer='?')] + hand_rows()[:5])
    pc = premise_of(model, items, 64)
    assert pc['cells']['S'] == dict(ok=0, n=0, not_checked=1)                   # the dropped S row: not checked, NOT ok
    assert pc['cells']['HO'] == dict(ok=5, n=5, not_checked=0)
    assert sum(c['ok'] for c in pc['cells'].values()) == pc['ok'] == 5 and sum(c['not_checked'] for c in pc['cells'].values()) == pc['dropped'] == 1


def test_collect_items_runs_one_tf_pass_for_records_and_premise(model, preps, monkeypatch):
    calls = []
    orig = B.tf_run
    monkeypatch.setattr(B, 'tf_run', lambda *a, **k: (calls.append(1), orig(*a, **k))[1])
    recs, pc = B.collect_items(model, preps, 'x', 64, with_margins=False)
    assert len(calls) == 1 and len(recs) == len(preps)                         # one TF run per chunk, not one for the records and one for the premise
    assert pc['n'] == pc['ok'] == len(preps) and pc['max_diff'] <= 1e-6 and pc['logit_chunks'] == [1, 1]
    again = premise_of(model, preps, 64)
    assert {k: pc[k] for k in ('n', 'ok', 'dropped', 'bad_ids')} == {k: again[k] for k in ('n', 'ok', 'dropped', 'bad_ids')}


# ---------- margins when the flat program is longer than the gold ----------

def test_margins_flat_call_beyond_the_gold_program_uses_the_marks_of_its_operands(model, preps, monkeypatch):
    """d == n: the flat program has a call the gold program does not. Its operands' marks come from the visible tokens (here: '68' and '86' of the
    prompt); they used to be the empty base marks, which scores the span operands as if they were cells."""
    p = dict(preps[4])                                         # (SUM(B1:B3))*(MAX(B2:B3)): n = 4
    p['flat_steps'], p['d'], p['paren_sensitive'] = list(p['steps']) + [('max', '68', '86', '86')], p['n'], True
    seen = []
    orig = B.call_logprob

    def spy(m, st, i, op, sa, sb, ma, mb):
        seen.append((op, sa, sb, ma, mb))
        return orig(m, st, i, op, sa, sb, ma, mb)
    monkeypatch.setattr(B, 'call_logprob', spy)
    out = margins(model, [p], 64)[0]
    flat = [x for x in seen if x[:3] == ('max', '68', '86')]
    assert len(flat) == 1 and flat[0][3].any() and flat[0][4].any(), 'the flat call at d == n was scored with empty operand marks'
    assert out['lp_flat'] is not None and torch.isfinite(torch.tensor(out['lp_flat']))
    assert len(out['lp']) == 7                                  # the gold rounds are unchanged by the flat call


# ---------- command line: collect ----------

def _jsonl(path, rows):
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))


@pytest.fixture(scope='module')
def tiny(tmp_path_factory):
    """A random-init T1SD checkpoint (tmp dir, never the shared scratchpad), an eval file that is NOT eval-rows-l5-shaped (no HP cell), the same with an HP
    cell (l5-shaped) and a probe file, all made of the hand rows. -> dict(ck, digest, eval, eval_l5, probe, order)."""
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    from domain.mode import save_ckpt
    root = tmp_path_factory.mktemp('tiny')
    rows = hand_rows()
    vocab = CharVocab.build(rows)
    cfg = dict(SMALL, **SPAN)
    torch.manual_seed(4242)
    m = Tool(vocab, **cfg)
    with torch.no_grad():
        m.op_head.weight.mul_(30)
        m.op_head.bias.normal_(0, 3)
    ck = str(root / 'checkpoint.pt')
    save_ckpt(dict(name='tool', chars=vocab.chars, cfg=cfg), m, ck)                  # the format mode.save_ckpt / load_model expect

    def eval_rows(skip):
        erows = [dict(r, layout=None) for r in rows if r['split'] not in skip] * 3
        return [dict(r, id=f'{r["id"]}-{i}') for i, r in enumerate(erows)]
    ep, ep5, pp = root / 'eval.jsonl', root / 'eval5.jsonl', root / 'probe.jsonl'
    _jsonl(ep, eval_rows(('F4-two', 'HP')))
    _jsonl(ep5, eval_rows(('F4-two',)))
    prow = [dict(r, kind='SUM', split=s) for r in rows if r['split'] == 'F4-two' for s in ('F4-two', 'F0-near')]
    _jsonl(pp, [dict(r, id=f'{r["id"]}-{r["split"]}') for r in prow])
    return dict(ck=ck, digest=LP.sha256_file(ck), eval=str(ep), eval_l5=str(ep5), probe=str(pp),
                order=B.prepare(B.ordered_rows(LP.load_jsonl(str(ep)), LP.load_jsonl(str(pp)))))


def collect_argv(t, out, label='tiny', eval_key='eval', *extra):
    return ['collect', '--ckpt', t['ck'], '--label', label, '--eval-rows', t[eval_key], '--probe', t['probe'], '--threads', '2', '--out', str(out), *extra]


def test_cli_collect_and_report(tiny, tmp_path, capsys):
    t, out = tiny, tmp_path / 'out'
    with pytest.raises(SystemExit, match='REFUSED'):
        B.main(collect_argv(t, out, 'x', 'eval', '--sha256', '0' * 64))
    assert not (out / 'bracket-x.jsonl').exists()
    B.main(collect_argv(t, out, 'tiny', 'eval', '--sha256', t['digest'], '--rewrites', 'plus,minus,swap,strip,spaced', '--rewrite-strata', 'HO,HPO',
                        '--self-check', '16'))
    recs = [json.loads(l) for l in open(out / 'bracket-tiny.jsonl')]
    from domain.score import score
    from custom_io.models import load_model
    order = t['order']
    assert [r['split'] for r in order][:3] == ['S5', 'S5', 'S5'] and order[-1]['split'] == 'F4-two' and order[-2]['split'] == 'F0-near'
    run = score(t['ck'], [dict(r, kind='SUM') for r in order], 'x')                      # domain/score.py's own path on the ordered row list
    assert [r['pred'] for r in run['rows']] == [f['pred'] for f in B.free_pass(load_model(t['ck']), order, 64)]
    assert [(r['id'], r['free']['pred']) for r in recs if r['version'] == 'orig'] == [(r['id'], r['pred']) for r in run['rows']]
    meta = json.load(open(out / 'bracket-tiny.meta.json'))
    assert meta['sha256'] == t['digest'] and meta['sha_check'] == 'ok' and meta['allowed_failures'] == []
    assert meta['self_check']['bad'] == 0 and meta['self_check']['max_diff'] <= 1e-6
    assert meta['real_strata_checked'].startswith('not checked')                          # no HP cell: not an eval-rows-l5 file
    sc = meta['self_check']
    nD = sum(1 for r in order if 'D' in r['strata'])
    assert nD > 0 and sc['D'] == nD and sc['n'] == 16 and sum(sc['cells'].values()) == 16 and sc['cells']['HO'] >= nD   # every D row, per-cell counts
    assert set(meta['premise']) == {'orig'} | {v for v in meta['rewrites'] if meta['rewrites'][v]['made']}
    assert set(meta['self_check_versions']) == set(meta['premise']) - {'orig'}            # the rewritten versions are self-checked too
    for v, sc in meta['self_check_versions'].items():
        assert sc['n'] > 0 and sc['bad'] == 0 and sc['ans_bad'] == 0 and sc['max_diff'] <= 1e-6, (v, sc)
    for v, pc in meta['premise'].items():                                   # the gold-path premise holds on every version
        assert pc['n'] > 0 and pc['ok'] == pc['n'] and not pc['bad_ids'] and pc['max_diff'] <= 1e-6 and pc['dropped'] == 0, (v, pc)
        assert pc['logit_chunks'][0] == pc['logit_chunks'][1] >= 1
        assert sum(c['n'] + c['not_checked'] for c in pc['cells'].values()) == pc['n'] + pc['dropped']
    assert meta['premise']['orig']['n'] == len(order) and set(meta['premise']['orig']['cells']) >= {'F0-near', 'F4-two'}   # probe rows too
    vers = {r['version'] for r in recs}
    assert vers == {'orig', 'plus', 'minus', 'swap', 'strip', 'spaced'} or vers == {'orig', 'plus', 'swap', 'strip', 'spaced'}
    for r in recs:
        assert r['label'] == 'tiny' and len(r['tf']) == 7 and set(r['free']) >= {'calls', 'pred', 'hit'} and r['dropped'] is None
        assert len(r['lp']) == 7 and (r['version'] == 'orig' or r['base_id'] != r['id'])
    idc = B.identity_check([r for r in recs if r['version'] == 'orig'])
    assert idc['agree'] == idc['n'] and idc['round_agree'] == idc['n']
    assert set(meta['identity']) == vers and all(v['agree'] == v['n'] and v['round_agree'] == v['n'] for v in meta['identity'].values())
    # collect ran validate_repair: every D item with exactly one TF-wrong round, the sample of the other strata, the key repair sets
    v = meta['validate']
    orig = [r for r in recs if r['version'] == 'orig']
    single = [r for r in orig if len(B.wrong_rounds(r)) == 1]
    assert v['sample'] == 64 and v['seed'] == 0
    for name, a in v['strata'].items():
        have = sum(1 for r in single if name in r['strata'])
        assert a['n'] == (have if name in B.FULL_VALIDATE else min(have, 64)), name
    assert set(v['sets']) == set(B.VALIDATE_SETS) and all(set(a) >= {'n', 'agree', 'mismatches', 'rate'} for a in list(v['strata'].values()) + list(v['sets'].values()))
    assert all(a['agree'] == a['n'] for a in v['strata'].values()), 'the repair prediction must equal the forced free hit on a real model'
    assert set(v['strata']) == {s for r in single for s in r['strata']}
    capsys.readouterr()
    rep = tmp_path / 'report.md'
    nho = sum(1 for r in orig if 'HO' in r['strata'])
    # a random model never hits, so no D item has exactly ONE TF-wrong round: the D validation group is empty, which is a gate FAILURE (not a note) and
    # the only one here; --accept-allowed-failures does not cover it (it is not an allowed failure)
    assert v['strata'].get('D', {}).get('n', 0) == 0
    expect = [f'HO=0/{nho}', 'tiny:D=0']
    by, metas = B.load_records([str(out)])
    text, fails = B.make_report(by, metas, expect)
    assert len(fails) == 1 and 'D validation group' in fails[0] and 'unvalidated' in fails[0], fails
    with pytest.raises(SystemExit) as e:
        B.main(['report', str(out), '--expect', *expect, '--out', str(rep)])
    assert e.value.code == 1
    with pytest.raises(SystemExit) as e:
        B.main(['report', str(out), '--expect', *expect, '--accept-allowed-failures', '--out', str(rep)])
    assert e.value.code == 1
    assert B.main(['report', str(out), '--no-gate', '--out', str(rep)]) is None
    text = rep.read_text()
    for head in ('## 0. Reproduction gate', '## 1. The identity', '## 2. Teacher-forced accuracy', '## 3. Inside D', '## 4. First TF-wrong round',
                 '## 5. Repair counterfactuals', '## 6. What the wrong calls are', '## 7. B2 and B1', '## 8. Rewrites', '## 9. Log-prob margin',
                 '### validate_repair', 'round-level agreement', 'logits on'):
        assert head in text, head
    text, _ = B.make_report(by, metas, expect)
    assert 'all given expectations met' in text and '95%' in text and 'Gate: FAILED' not in text and '| FAIL |' not in text
    assert text.count('**FAIL') == 1 and 'the D validation group' in text.split('**FAIL')[1]
    with pytest.raises(SystemExit) as e:                                      # a wrong expectation: the process fails, the report is still written
        B.main(['report', str(out), '--expect', 'HO=99', '--out', str(tmp_path / 'bad.md')])
    assert e.value.code == 1 and 'FAIL' in (tmp_path / 'bad.md').read_text()


def test_collect_validates_repairs_on_a_scripted_model_end_to_end(tiny, tmp_path, monkeypatch):
    """collect() on a scripted model that HITS on some items and has exactly one wrong round on others: validate_repair runs on every D item with one
    wrong round, the key repair sets and a sample of the other strata, the identity is non-trivial (hits), and the report's gate passes with the
    scripted hit counts and fails on a validate disagreement."""
    import custom_io.models as CM
    rows = [r for r in hand_rows() if r['split'] not in ('F4-two', 'HP')]
    preps_ = B.prepare(B.ordered_rows(rows))
    d_script, other = iter([0, 1, 1, None]), iter([None, 0, 1, 2] * 4)
    wrong_round = {i: next(d_script) if 'D' in p['strata'] else next(other) for i, p in enumerate(preps_)}
    m, undo = scripted_model(preps_, wrong_round)
    monkeypatch.setattr(CM, 'load_model', lambda ck: m)
    try:
        recs, meta = B.collect(tiny['ck'], 's', rows, None, rewrites=(), sha=tiny['digest'], self_check=8, validate_sample=64)
    finally:
        undo()
    hits = sum(r['free']['hit'] for r in recs)
    assert 0 < hits < len(recs) and meta['sha_check'] == 'ok' and meta['allowed_failures'] == []
    singles = [r for r in recs if len(B.wrong_rounds(r)) == 1]
    v = meta['validate']
    assert v['strata']['D']['n'] == sum(1 for r in singles if 'D' in r['strata']) == 3 and v['strata']['D']['agree'] == 3
    assert v['sets']['r0']['n'] >= 1 and v['sets']['d']['n'] >= 2 and all(a['agree'] == a['n'] for k in ('strata', 'sets') for a in v[k].values())
    assert meta['identity']['orig']['agree'] == meta['identity']['orig']['n'] == len(recs) and meta['identity']['orig']['round_agree'] == len(recs)
    assert {(B.predicted_hit(r), bool(r['free']['hit'])) for r in recs} == {(True, True), (False, False)}       # both diagonal cells are populated
    by = {'s': recs}
    n_ho = sum(1 for r in recs if 'HO' in r['strata'])
    h_ho = sum(r['free']['hit'] for r in recs if 'HO' in r['strata'])
    text, fails = B.make_report(by, {'s': meta}, [f'HO={h_ho}/{n_ho}'])
    assert fails == [] and 'validate_repair' in text and 'stratum D' in text
    meta['validate']['strata']['D'].update(rate=0.34, agree=2, mismatches=[dict(id='h1', rounds=[1], predicted=True, observed=False)])
    text, fails = B.make_report(by, {'s': meta}, [f'HO={h_ho}/{n_ho}'])
    assert len(fails) == 1 and 'validate_repair mismatch rate 34.0%' in fails[0] and 'FAIL: s stratum D' in text


def test_collect_requires_a_checksum_or_no_sha(tiny, tmp_path):
    for extra in ([], ['--sha256', ''], ['--sha256', '   '], ['--sha256', tiny['digest'], '--no-sha']):
        with pytest.raises(SystemExit) as e:
            B.main(collect_argv(tiny, tmp_path / 'o', 'x', 'eval', *extra))
        assert e.value.code == 2, extra                                       # argparse error: nothing ran
    assert not (tmp_path / 'o').exists()
    B.main(collect_argv(tiny, tmp_path / 'o', 'x', 'eval', '--no-sha', '--rewrites', '', '--self-check', '0', '--limit', '6'))
    meta = json.load(open(tmp_path / 'o' / 'bracket-x.meta.json'))
    assert meta['sha_check'] == 'sha unchecked'
    B.main(['report', str(tmp_path / 'o'), '--no-gate', '--out', str(tmp_path / 'r.md')])
    assert 'sha unchecked' in (tmp_path / 'r.md').read_text()


def test_collect_strata_check_runs_on_l5_shaped_files_and_is_fatal(tiny, tmp_path):
    """The eval file has the five cells of eval-rows-l5 but not 2,100 rows: the real-strata counts (106 / 60 / ...) are checked and do not hold."""
    with pytest.raises(SystemExit) as e:
        B.main(collect_argv(tiny, tmp_path / 'o', 'x', 'eval_l5', '--no-sha', '--rewrites', '', '--self-check', '0'))
    assert 'FATAL' in str(e.value) and 'real strata' in str(e.value) and not (tmp_path / 'o').exists()
    out = tmp_path / 'allowed'
    B.main(collect_argv(tiny, out, 'x', 'eval_l5', '--no-sha', '--rewrites', '', '--self-check', '0', '--allow-premise-fail'))
    meta = json.load(open(out / 'bracket-x.meta.json'))
    assert meta['real_strata_checked'].startswith('FAILED') and len(meta['allowed_failures']) == 1 and 'real strata' in meta['allowed_failures'][0]
    B.main(['report', str(out), '--no-gate', '--out', str(out / 'r.md')])
    assert 'failure ALLOWED at collect' in (out / 'r.md').read_text()
    lim = tmp_path / 'lim'
    B.main(collect_argv(tiny, lim, 'x', 'eval_l5', '--no-sha', '--rewrites', '', '--self-check', '0', '--limit', '5'))
    assert json.load(open(lim / 'bracket-x.meta.json'))['real_strata_checked'] == 'strata unchecked (limit)'


def test_collect_premise_and_self_check_failures_are_fatal_unless_allowed(tiny, tmp_path, monkeypatch):
    orig_result = B.PremiseCheck.result

    def broken(self, tf_out):
        r = orig_result(self, tf_out)
        r['ok'] -= 1
        r['bad_ids'] = ['h0-0']
        return r
    monkeypatch.setattr(B.PremiseCheck, 'result', broken)
    argv = collect_argv(tiny, tmp_path / 'p', 'x', 'eval', '--no-sha', '--rewrites', '', '--self-check', '0')
    with pytest.raises(SystemExit) as e:
        B.main(argv)
    assert 'FATAL' in str(e.value) and 'premise check FAILED' in str(e.value) and not (tmp_path / 'p').exists()
    B.main(argv + ['--allow-premise-fail'])
    meta = json.load(open(tmp_path / 'p' / 'bracket-x.meta.json'))
    assert len(meta['allowed_failures']) == 1 and 'premise check FAILED' in meta['allowed_failures'][0]
    monkeypatch.undo()
    monkeypatch.setattr(B, 'own_call_identity', lambda *a, **k: dict(n=3, bad=[(0, 1, None, ('add', '1', '2'))], ans_bad=[], max_diff=0.0))
    argv = collect_argv(tiny, tmp_path / 's', 'x', 'eval', '--no-sha', '--rewrites', '', '--self-check', '8', '--limit', '6')
    with pytest.raises(SystemExit) as e:
        B.main(argv)
    assert 'FATAL' in str(e.value) and 'self-check failed' in str(e.value) and not (tmp_path / 's').exists()
    B.main(argv + ['--allow-premise-fail'])
    assert 'self-check failed' in json.load(open(tmp_path / 's' / 'bracket-x.meta.json'))['allowed_failures'][0]


def test_premise_failed_fails_a_check_that_compared_nothing():
    ok = dict(n=5, ok=5, bad_ids=[], dropped=0, max_diff=0.0, logit_chunks=[1, 1])
    assert not B.premise_failed(ok) and not B.premise_unchecked(ok)
    for empty in (dict(ok, n=0, ok=0), dict(ok, max_diff=None), dict(ok, logit_chunks=[0, 1], max_diff=None), dict(ok, logit_chunks=[0, 2])):
        assert B.premise_unchecked(empty) and B.premise_failed(empty), empty
    assert B.premise_failed(dict(ok, ok=4)) and not B.premise_unchecked(dict(ok, ok=4))


def test_collect_premise_unchecked_is_fatal_unless_allowed_and_the_report_gate_follows(tiny, tmp_path, monkeypatch):
    orig_result = B.PremiseCheck.result

    def nothing_compared(self, tf_out):
        r = orig_result(self, tf_out)
        r.update(max_diff=None, logit_chunks=[0, r['logit_chunks'][1]])
        return r
    monkeypatch.setattr(B.PremiseCheck, 'result', nothing_compared)
    for extra in ([], ['--limit', '6']):                                  # a --limit smoke run is no exception
        argv = collect_argv(tiny, tmp_path / ('p' + ''.join(extra)), 'x', 'eval', '--no-sha', '--rewrites', '', '--self-check', '0') + extra
        with pytest.raises(SystemExit) as e:
            B.main(argv)
        assert 'FATAL' in str(e.value) and 'premise unchecked for orig' in str(e.value) and not (tmp_path / ('p' + ''.join(extra))).exists()
    out = tmp_path / 'allowed'
    B.main(collect_argv(tiny, out, 'x', 'eval', '--no-sha', '--rewrites', '', '--self-check', '0', '--limit', '6', '--allow-premise-fail'))
    meta = json.load(open(out / 'bracket-x.meta.json'))
    assert len(meta['allowed_failures']) == 1 and 'premise unchecked for orig' in meta['allowed_failures'][0], meta['allowed_failures']
    # the report: a gate failure by default, accepted only with --accept-allowed-failures and only because collect recorded it
    def gate(accept):
        by_label, meta_ = B.load_records([str(out)])
        text, fails = B.make_report(by_label, meta_, None, False, accept)
        return text, [f for f in fails if 'no --expect given' not in f]     # this smoke run has no expectations
    text, fails = gate(False)
    assert any('premise unchecked for orig' in f for f in fails) and 'premise unchecked for orig' in text, fails
    assert gate(True)[1] == []
    meta['allowed_failures'] = []
    (out / 'bracket-x.meta.json').write_text(json.dumps(meta))
    assert any('premise unchecked for orig' in f and 'NOT recorded' in f for f in gate(True)[1])       # unrecorded: not accepted


def test_report_gate_fails_a_version_whose_premise_compared_nothing():
    recs = synthetic_recs()
    pc = dict(n=0, ok=0, bad_ids=[], dropped=5, max_diff=None, logit_chunks=[0, 1])
    meta = dict(good_meta(), premise={'orig': pc})
    text, fails = full_report(recs, meta)
    assert any('premise unchecked for orig' in f for f in fails), fails
    meta = dict(meta, allowed_failures=['t/orig: premise unchecked for orig (n 0)'])
    assert full_report(recs, meta, accept=True)[1] == []


# ---------- command line: report, the gate, labels ----------

def synthetic_recs(label='t', reps=4, seed=3):
    rng = random.Random(seed)
    recs = []
    for rep in range(reps):
        for p in hand_preps():
            wrong = {k: ('add', '0', '0') for k in range(p['n']) if rng.random() < 0.3}
            r = rec_of(p, wrong, ans_tf=rng.random() < 0.8, free_hit=rng.random() < 0.3)
            r['id'] = f'{p["id"]}-{rep}'
            r['base_id'] = r['id']
            r['label'] = label
            recs.append(r)
    return recs


def good_meta(label='t', rate=0.0):
    a = dict(n=20, agree=int(20 * (1 - rate)), mismatches=[dict(id='h0-0', rounds=[1], predicted=True, observed=False)] * int(20 * rate), rate=rate)
    return dict(label=label, validate=dict(sample=64, seed=0, strata={'D': a}, sets={'r0': dict(a)}), premise={}, allowed_failures=[], sha_check='ok')


def write_run(d, label, recs, meta=True, fname=None):
    d.mkdir(parents=True, exist_ok=True)
    base = d / f'bracket-{fname or label}'
    _jsonl(base.with_suffix('.jsonl'), recs)
    if meta:
        (d / f'bracket-{fname or label}.meta.json').write_text(json.dumps(good_meta(label) if meta is True else meta))
    return str(d)


def ho_counts(recs):
    ho = [r for r in recs if r['version'] == 'orig' and 'HO' in r['strata']]
    return sum(r['free']['hit'] for r in ho), len(ho)


def run_report(argv, capsys=None):
    """-> exit code (0 = returned normally) of B.main(['report', ...])."""
    try:
        B.main(['report'] + argv)
    except SystemExit as e:
        return e.code
    return 0


def test_report_gate_failure_exits_nonzero(tmp_path, capsys):
    recs = synthetic_recs()
    d = write_run(tmp_path / 'r', 't', recs)
    hits, n = ho_counts(recs)
    assert 0 < hits < n
    assert run_report([d, '--expect', f'HO={hits}', '--out', str(tmp_path / 'a.md')]) == 0                         # hits only
    assert run_report([d, '--expect', f'HO={hits}/{n}', 't:HO=%d/%d' % (hits, n), '--out', str(tmp_path / 'a.md')]) == 0
    assert 'all given expectations met' in (tmp_path / 'a.md').read_text()
    assert run_report([d, '--expect', f'HO={hits + 1}', '--out', str(tmp_path / 'b.md')]) == 1                      # wrong hits
    assert 'FAIL' in (tmp_path / 'b.md').read_text()
    assert run_report([d, '--expect', f'HO={hits}/{n + 1}', '--out', str(tmp_path / 'b.md')]) == 1                  # right hits, wrong n
    assert run_report([d, '--expect', f'HO={hits}/{n - 1}', '--out', str(tmp_path / 'b.md')]) == 1
    assert run_report([d, '--expect', f'nolabel:HO={hits}', '--out', str(tmp_path / 'b.md')]) == 1                  # a label that matches no run: not dropped
    assert 'no such run' in (tmp_path / 'b.md').read_text()
    assert run_report([d, '--expect', f'HO={hits}', 'NOSUCH=0', '--out', str(tmp_path / 'b.md')]) == 1               # a key that matches no cell: not dropped
    assert 'no such cell' in (tmp_path / 'b.md').read_text()
    assert run_report([d, '--expect', f't:NOSUCH=0', '--out', str(tmp_path / 'b.md')]) == 1
    assert run_report([d, '--out', str(tmp_path / 'c.md')]) == 1                                                    # no --expect and no --no-gate
    assert 'no --expect given' in (tmp_path / 'c.md').read_text()
    assert run_report([d, '--expect', 'HO', '--out', str(tmp_path / 'c.md')]) == 2                                   # malformed --expect: argparse error
    assert run_report([d, '--no-gate', '--out', str(tmp_path / 'd.md')]) == 0
    assert 'GATE NOT RUN' in (tmp_path / 'd.md').read_text()
    assert run_report([d, '--no-gate', '--expect', f'HO={hits}']) == 2                                              # contradictory
    capsys.readouterr()


def test_report_gate_fails_on_validate_repair_mismatch_rate(tmp_path):
    recs = synthetic_recs()
    hits, n = ho_counts(recs)
    ok = write_run(tmp_path / 'ok', 't', recs, meta=good_meta('t', rate=0.05))             # exactly 5%: not above the limit
    assert run_report([ok, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'ok.md')]) == 0
    bad = write_run(tmp_path / 'bad', 't', recs, meta=good_meta('t', rate=0.1))
    assert run_report([bad, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'bad.md')]) == 1
    text = (tmp_path / 'bad.md').read_text()
    assert 'FAIL: t stratum D: validate_repair disagrees' in text and '10.0%' in text
    nov = write_run(tmp_path / 'nov', 't', recs, meta=dict(good_meta('t'), validate=None))       # validate_repair never ran
    assert run_report([nov, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'nov.md')]) == 1
    assert 'validate_repair was NOT run' in (tmp_path / 'nov.md').read_text()
    nometa = write_run(tmp_path / 'nometa', 't', recs, meta=False)
    assert run_report([nometa, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'nm.md')]) == 1
    assert run_report([nov, '--no-gate', '--out', str(tmp_path / 'ng.md')]) == 0               # --no-gate: shown, not enforced


def test_load_records_refuses_duplicate_labels_and_keys_meta_by_label(tmp_path):
    recs = synthetic_recs('t')
    a = write_run(tmp_path / 'a', 't', recs)
    b = write_run(tmp_path / 'b', 't', recs)
    with pytest.raises(ValueError, match="duplicate label 't'"):
        B.load_records([a, b])
    with pytest.raises(ValueError, match='duplicate label'):                     # the same directory twice
        B.load_records([a, a])
    c = write_run(tmp_path / 'c', 't', recs, fname='other')                      # a second file of the same label inside one directory
    write_run(tmp_path / 'c', 't', recs, fname='first')
    with pytest.raises(ValueError, match='duplicate label'):
        B.load_records([c])
    with pytest.raises(SystemExit, match='duplicate label'):
        B.main(['report', a, b, '--no-gate'])
    # the label is the one inside the records, not the file name: meta follows it
    d = write_run(tmp_path / 'd', 'real', synthetic_recs('real'), fname='misnamed')
    by, meta = B.load_records([d])
    assert list(by) == ['real'] and list(meta) == ['real'] and meta['real']['label'] == 'real'
    both, metas = B.load_records([a, d])
    assert set(both) == {'t', 'real'} and set(metas) == {'t', 'real'}
    with pytest.raises(ValueError, match='exactly one label'):                  # a file that mixes labels
        B.load_records([write_run(tmp_path / 'e', 't', synthetic_recs('t')[:3] + synthetic_recs('u')[:3], meta=False)])
    wrong = write_run(tmp_path / 'f', 'v', synthetic_recs('v'), meta=good_meta('someone else'))   # meta of another run beside these records
    with pytest.raises(ValueError, match='meta label'):
        B.load_records([wrong])


def test_report_kind_tables_split_d_into_d_k_and_d_j():
    """'kind of every wrong round, by position' had one pooled D table that mixes ca_mul and lookup rounds."""
    recs = synthetic_recs()
    text = report({'t': recs}, None, None, no_gate=True)
    for title in ('D_K (the CA piece is K): ', 'D_J (the CA piece is J): ', 'D pooled (mixes call types): ', 'HO_nonCA: '):
        assert title in text, title
    n_k = sum(len(r['wrong']) for r in B.of(recs, 'D_K'))
    n_j = sum(len(r['wrong']) for r in B.of(recs, 'D_J'))
    n_d = sum(len(r['wrong']) for r in B.of(recs, 'D'))
    assert n_k > 0 and n_j > 0 and n_k + n_j == n_d
    assert f'D_K (the CA piece is K): {n_k} wrong rounds' in text and f'D_J (the CA piece is J): {n_j} wrong rounds' in text
    assert 'coincidental, not evidence' in text and 'all wrong rounds: call == flat call' not in text


def test_report_on_synthetic_records():
    """The report runs on records with a mix of right and wrong rounds and its numbers are the hand counts."""
    recs = synthetic_recs('t')
    text = report({'t': recs}, None, ['HO=1'])
    assert '## 5. Repair counterfactuals' in text
    sub = B.of(recs, 'HO_CA_all')
    t = B.repair_table(sub)
    assert t['none'] == (sum(1 for r in sub if B.predicted_hit(r)), len(sub))
    assert all(t['none'][0] <= t[k][0] <= t[k][1] for k in t)
    assert B.frac(*t['none']) in text
    assert B.frac(*B.role_acc(sub, 'r0', 'pos')) in text
    idc = B.identity_check(B.of(recs))
    assert B.frac(idc['agree'], idc['n']) in text and B.frac(idc['round_agree'], idc['n']) in text


# =====================================================================================================================================================
# Second review round: gate, identity, validation, logit comparison, explicit raises, roles, inclusion rules, wrappers, data location
# =====================================================================================================================================================

def full_report(recs, meta, accept=False, label='t'):
    hits, n = ho_counts(recs)
    return B.make_report({label: recs}, {label: meta}, [f'HO={hits}/{n}'], accept_allowed=accept)


# ---------- 1. report gate: failures allowed at collect ----------

def test_report_fails_on_failures_allowed_at_collect_unless_accepted(tmp_path, capsys):
    recs = synthetic_recs()
    hits, n = ho_counts(recs)
    assert full_report(recs, good_meta())[1] == []                                          # control: the same run with nothing allowed passes
    meta = dict(good_meta(), allowed_failures=['real strata check failed: stratum D: 3 rows, expected 106'])
    text, fails = full_report(recs, meta)
    assert len(fails) == 1 and 'real strata check failed' in fails[0] and 'accept-allowed-failures' in fails[0]
    text, fails = full_report(recs, meta, accept=True)
    assert fails == [] and 'ACCEPTED ALLOWED FAILURES' in text and 'real strata check failed' in text
    d = write_run(tmp_path / 'a', 't', recs, meta=meta)
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'a.md')]) == 1       # the report CLI: fails by default
    capsys.readouterr()
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--accept-allowed-failures', '--out', str(tmp_path / 'b.md')]) == 0
    assert 'ACCEPTED ALLOWED FAILURES' in capsys.readouterr().err and 'ACCEPTED ALLOWED FAILURES' in (tmp_path / 'b.md').read_text()
    assert run_report([d, '--no-gate', '--out', str(tmp_path / 'c.md')]) == 0 and 'failure ALLOWED at collect' in (tmp_path / 'c.md').read_text()


def test_report_fails_on_recorded_self_check_and_premise_failures_unless_accepted():
    recs = synthetic_recs()
    sc = dict(n=3, bad=1, ans_bad=0, max_diff=0.0)
    pc = dict(n=5, ok=4, bad_ids=['x'], dropped=0, max_diff=0.0)
    entry_for = {'self_check': 't/orig: the own-calls self-check failed (1 calls)', 'self_check_versions': 't/plus: the own-calls self-check failed (1 calls)',
                 'premise': 't/orig: gold-path premise check FAILED for 1/5 rows'}
    for key, val, word in (('self_check', sc, 'self-check FAILED'), ('self_check_versions', {'plus': sc}, 'self-check FAILED for plus'),
                           ('premise', {'orig': pc}, 'premise check FAILED for version orig')):
        meta = dict(good_meta(), allowed_failures=[entry_for[key]], **{key: val})
        _, fails = full_report(recs, meta)
        assert any(word in f for f in fails) and any(entry_for[key] in f for f in fails), (key, fails)     # the flag AND the allowed entry
        _, fails = full_report(recs, meta, accept=True)
        assert fails == [], (key, fails)
        meta = dict(good_meta(), **{key: val})                                           # failed, but collect recorded nothing: not an allowed failure
        _, fails = full_report(recs, meta, accept=True)
        assert any(word in f and 'NOT recorded' in f for f in fails), (key, fails)


def test_accepting_allowed_failures_does_not_accept_an_empty_d_validation():
    recs = synthetic_recs()
    v = good_meta()['validate']
    v['strata'], v['sets'] = {}, {}
    meta = dict(good_meta(), validate=v, allowed_failures=['premise check failed: x'])
    _, fails = full_report(recs, meta, accept=True)
    assert len(fails) == 1 and 'D validation group' in fails[0]


# ---------- 2. round-level identity is a gate ----------

def copies(p, count, **kw):
    out = []
    for i in range(count):
        r = rec_of(p, **kw)
        r['id'], r['base_id'], r['label'] = f'{p["id"]}-{i}', f'{p["id"]}-{i}', 't'
        out.append(r)
    return out


def identity_fails(recs):
    fails = []
    B.identity_gate({'t': recs}, False, fails)
    return fails


def test_round_identity_mismatch_in_d_fails_the_gate(preps):
    recs = copies(preps[2], 40) + copies(preps[0], 40) + copies(preps[4], 250)
    assert identity_fails(recs) == []
    recs[3]['free']['calls'][0][2] = '99'                                      # ONE round-level mismatch in a D_J item
    fails = identity_fails(recs)
    assert any('D_J' in f and 'any mismatch fails' in f for f in fails) and any(f.startswith('t: round-level identity broken in 1/') and ' of D ' in f for f in fails)
    recs = copies(preps[2], 40) + copies(preps[0], 40)
    recs[50]['free']['calls'][1][3] = '98'                                     # in a D_K item
    assert any(' of D_K ' in f for f in identity_fails(recs))


def test_round_identity_rate_above_half_a_percent_fails_elsewhere(preps):
    recs = copies(preps[4], 250)                                               # HO non-CA items: HO, HO4, HO4_nonD, HO_nonCA (250 each)
    recs[0]['free']['calls'][0][2] = '99'
    assert identity_fails(recs) == []                                          # 1 / 250 = 0.4%: not above 0.5%
    recs[1]['free']['calls'][1][2] = '98'
    fails = identity_fails(recs)                                               # 2 / 250 = 0.8%
    assert any(' of HO ' in f and '0.8%' in f for f in fails) and any(' of HO4_nonD ' in f for f in fails) and not any(' of D ' in f for f in fails)
    text = '\n'.join(B.identity_gate({'t': recs}, True, []))                   # --no-gate: shown, not enforced
    assert 'FAIL' in text


def test_report_cli_exits_1_on_a_round_level_identity_break(tmp_path):
    recs = synthetic_recs(reps=4)
    hits, n = ho_counts(recs)
    d = write_run(tmp_path / 'ok', 't', recs)
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'ok.md')]) == 0
    assert '### Round-level identity (orig version): a gate' in (tmp_path / 'ok.md').read_text()
    j = next(i for i, r in enumerate(recs) if 'D' in r['strata'])
    recs[j]['free']['calls'].append([6, 'add', '1', '2', '3'])                 # an extra free call where gold and TF both stop (or a changed one)
    recs[j]['free']['calls'][0][2] = '12345'
    d = write_run(tmp_path / 'bad', 't', recs)
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'bad.md')]) == 1
    assert 'the round-level identity breaks' in (tmp_path / 'bad.md').read_text()


# ---------- 3. an empty D validation group fails ----------

def test_empty_d_validation_group_fails_the_gate(tmp_path):
    recs = synthetic_recs()
    hits, n = ho_counts(recs)
    for strata in ({}, {'D_K': dict(n=3, agree=3, mismatches=[], rate=0.0)}, {'D': dict(n=0, agree=0, mismatches=[], rate=0.0)}):
        v = dict(good_meta()['validate'], strata=strata, sets={})
        text, fails = full_report(recs, dict(good_meta(), validate=v))
        assert len(fails) == 1 and 'D validation group' in fails[0] and 'unvalidated' in fails[0] and 'n == 0' in fails[0], (strata, fails)
        assert '**FAIL: t: the D validation group' in text
    d = write_run(tmp_path / 'e', 't', recs, meta=dict(good_meta(), validate=dict(good_meta()['validate'], strata={}, sets={})))
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--out', str(tmp_path / 'e.md')]) == 1
    assert run_report([d, '--no-gate', '--out', str(tmp_path / 'e2.md')]) == 0
    assert run_report([d, '--expect', f'HO={hits}/{n}', '--accept-allowed-failures', '--out', str(tmp_path / 'e3.md')]) == 1


def test_other_empty_validation_groups_stay_notes():
    recs = synthetic_recs()
    v = good_meta()['validate']
    v['strata']['D_K'] = dict(n=0, agree=0, mismatches=[], rate=0.0)
    v['sets']['J_first'] = dict(n=0, agree=0, mismatches=[], rate=0.0)
    text, fails = full_report(recs, dict(good_meta(), validate=v))
    assert fails == [] and 'Note: t: validation groups with no item' in text and 'stratum D_K' in text and 'set J_first' in text


def d_solved_recs(label='t'):
    """Records in which no D item has a TF-wrong round (D fully solved under TF); the other strata keep their random wrong rounds."""
    out = []
    for r in synthetic_recs(label):
        if 'D' in r['strata']:
            r = rec_of(next(p for p in hand_preps() if r['id'].startswith(p['id'] + '-')), {}, ans_tf=True, free_hit=True) | dict(id=r['id'], base_id=r['base_id'], label=label)
        out.append(r)
    return out


def test_d_validated_only_by_repair_sets_does_not_fail():
    """P1: D items with several wrong rounds are never in the single-wrong-round D group, but a repair set forced them: that validates D."""
    recs = synthetic_recs()
    assert any('D' in r['strata'] and B.wrong_rounds(r) for r in recs)
    v = good_meta()['validate']
    v['strata'] = {}                                                  # no single-wrong-round D group ...
    v['sets'] = {'r0': dict(n=2, agree=2, mismatches=[], rate=0.0)}  # ... but a repair set forced two D items
    text, fails = full_report(recs, dict(good_meta(), validate=v))
    assert fails == [] and 'D validation group' not in text
    v['sets'] = {'r0': dict(n=0, agree=0, mismatches=[], rate=0.0)}  # nothing forced at all: fails
    _, fails = full_report(recs, dict(good_meta(), validate=v))
    assert len(fails) == 1 and 'D validation group' in fails[0]
    v['sets'] = {'r0': dict(n=4, agree=2, mismatches=[dict(id='x', rounds=[0], predicted=True, observed=False)] * 2, rate=0.5)}   # forced, but the >5% mismatch FAIL stays
    _, fails = full_report(recs, dict(good_meta(), validate=v))
    assert len(fails) == 1 and 'mismatch rate 50.0%' in fails[0]


def test_d_with_no_tf_wrong_round_is_a_note_not_a_failure():
    """P1: D fully solved under TF has nothing to validate; empty validation groups then are fine."""
    recs = d_solved_recs()
    assert any('D' in r['strata'] for r in recs) and not any('D' in r['strata'] and B.wrong_rounds(r) for r in recs)
    v = dict(good_meta()['validate'], strata={}, sets={})
    text, fails = full_report(recs, dict(good_meta(), validate=v))
    assert fails == [] and 'D has no TF-wrong rounds: nothing to validate' in text and '**FAIL: t: the D validation group' not in text
    recs[next(i for i, r in enumerate(recs) if 'D' in r['strata'])] = synthetic_recs()[next(i for i, r in enumerate(synthetic_recs()) if 'D' in r['strata'] and B.wrong_rounds(r))]
    _, fails = full_report(recs, dict(good_meta(), validate=v))      # one D item with a wrong round, nothing forced: fails again
    assert len(fails) == 1 and 'D validation group' in fails[0]


def test_accept_allowed_failures_matches_one_by_one():
    """P2: each self-check / premise / strata failure is accepted only against its own entry in meta['allowed_failures']."""
    recs = synthetic_recs()
    sc = dict(n=3, bad=1, ans_bad=0, max_diff=0.0)
    pc = dict(n=5, ok=4, bad_ids=['x'], dropped=0, max_diff=0.0)
    e_sc, e_pc, e_st = ('t/orig: the own-calls self-check failed (1 calls)', 't/orig: gold-path premise check FAILED for 1/5 rows',
                        'real strata check failed: stratum D: 3 rows, expected 106')
    base = dict(good_meta(), self_check=sc, premise={'orig': pc}, real_strata_checked='FAILED: stratum D: 3 rows, expected 106')
    _, fails = full_report(recs, dict(base, allowed_failures=[e_sc, e_pc, e_st]), accept=True)
    assert fails == []                                              # all three recorded: accepted
    for entries, still in (([e_pc, e_st], 'self-check FAILED'), ([e_sc, e_st], 'premise check FAILED'), ([e_sc, e_pc], 'real strata check FAILED')):
        _, fails = full_report(recs, dict(base, allowed_failures=entries), accept=True)
        assert len(fails) == 1 and still in fails[0] and 'NOT recorded' in fails[0], (entries, fails)
    _, fails = full_report(recs, dict(base, allowed_failures=[e_sc.replace('orig', 'plus'), e_pc, e_st]), accept=True)   # self-check entry of ANOTHER version
    assert len(fails) == 1 and 'self-check FAILED' in fails[0]
    _, fails = full_report(recs, dict(base, allowed_failures=[e_sc, e_pc.replace('orig', 'plus'), e_st]), accept=True)    # premise entry for another version
    assert len(fails) == 1 and 'premise check FAILED' in fails[0]
    _, fails = full_report(recs, dict(base, allowed_failures=[]), accept=True)
    assert len(fails) == 3 and all('NOT recorded' in f for f in fails)


# ---------- 4. forced-run agreement includes the tape ----------

def test_agreement_requires_the_forced_tape_to_equal_the_gold_tape(preps):
    from custom_io.models.tool import entry
    DJ = preps[2]
    r = rec_of(DJ, {1: ('add', '1', '1')})
    good = [entry(*s) for s in DJ['steps']] + [''] * (B.N_RES - DJ['n'])
    assert B.gold_tape(r) == good
    a = B._agreement([r], [0], [dict(hit=1, tape=good)])
    assert (a['n'], a['agree'], a['mismatches']) == (1, 1, [])
    for k, text in ((2, 'add 1 2 = 3'), (3, ''), (5, 'add 1 2 = 3')):           # a changed entry, a missing one, an extra one: the hit bit alone agrees
        bad = list(good)
        bad[k] = text
        a = B._agreement([r], [0], [dict(hit=1, tape=bad)])
        assert a['agree'] == 0 and a['mismatches'][0]['tape_round'] == k and a['mismatches'][0]['predicted'] == a['mismatches'][0]['observed'] is True
    assert B._agreement([r], [0], [dict(hit=1)])['agree'] == 0                  # no tape at all is not a pass


def test_validate_all_counts_a_forced_tape_mismatch(preps, monkeypatch):
    rows = hand_preps()[:4]
    wrong_round = {0: 0, 1: 1, 2: 1, 3: None}
    m, undo, recs, free = scripted_records(rows, wrong_round)
    try:
        v = B.validate_all(m, rows, recs, sample=None)
        assert v['strata']['D']['n'] == 3 and v['strata']['D']['agree'] == 3 and v['sets']['d']['agree'] == v['sets']['d']['n'] >= 1
        orig = B.forced_run

        def tampered(*a, **k):
            out = orig(*a, **k)
            for o in out:
                o['tape'] = list(o['tape'])
                o['tape'][3] = o['tape'][3] + ' '                      # hits and calls unchanged, one tape text differs
            return out
        monkeypatch.setattr(B, 'forced_run', tampered)
        w = B.validate_all(m, rows, recs, sample=None)
    finally:
        undo()
    assert w['strata']['D']['agree'] == 0 and w['strata']['D']['rate'] == 1.0
    assert all(x['tape_round'] == 3 for x in w['strata']['D']['mismatches']) and all(a['rate'] == 1.0 for a in w['sets'].values() if a['n'])
    text, fails = B.make_report({'t': [dict(r, label='t') for r in recs]}, {'t': dict(good_meta(), validate=w)}, None, no_gate=False)
    assert any('validate_repair mismatch rate 100.0%' in f for f in fails) and 'tape@3' in text


# ---------- 5. ONE logit comparison ----------

def fake_steps(rounds=3, rows=2, span=True, seed=0):
    g = torch.Generator().manual_seed(seed)
    steps = []
    for _ in range(rounds):
        st = (torch.randn(rows, 5, generator=g), torch.rand(rows, 4, 6, generator=g))
        if span:
            st += (dict(la=torch.randn(rows, 9, generator=g), lb=torch.randn(rows, 9, generator=g), ga=torch.randn(rows, generator=g),
                        gb=torch.randn(rows, generator=g), m=torch.rand(rows, 9, generator=g) > 0.3),)
        steps.append(st)
    return steps


def bumped(steps, rnd, which, by):
    """A copy of steps with `by` added to one tensor kind of round rnd."""
    out = []
    for r, st in enumerate(steps):
        st = list(st)
        if len(st) > 2:
            st[2] = dict(st[2])
        if r == rnd:
            if which == 'op':
                st[0] = st[0] + by
            elif which == 'cells':
                st[1] = st[1] + by
            elif which in ('ga', 'gb'):
                st[2][which] = st[2][which] + by
            else:                                                    # a pointer logit, at a position visible in both runs (and one that is not)
                vis = st[2]['m']
                st[2][which] = st[2][which] + by * vis
        out.append(tuple(st))
    return out


def test_logit_diff_compares_op_cells_gate_and_pointer():
    a = fake_steps()
    z = B.logit_diff(a, bumped(a, 0, 'op', 0.0))
    assert z == dict(op=0.0, cells=0.0, gate=0.0, pointer=0.0)
    for which, kind in (('op', 'op'), ('cells', 'cells'), ('ga', 'gate'), ('gb', 'gate'), ('la', 'pointer'), ('lb', 'pointer')):
        d = B.logit_diff(a, bumped(a, 1, which, 0.25))
        assert abs(d[kind] - 0.25) < 1e-6 and all(d[k] == 0.0 for k in d if k != kind), (which, d)
    assert B.logit_diff(a, bumped(a, 1, 'op', 0.25), compare_op=False)['op'] is None      # skipped
    assert B.logit_diff(a, bumped(a, 1, 'op', 0.25), compare_op=False)['cells'] == 0.0
    b = [(st[0], st[1], dict(st[2], la=st[2]['la'] + 5 * (~st[2]['m']))) for st in a]       # pointer logits at positions invisible to both runs do not count
    assert B.logit_diff(a, b)['pointer'] == 0.0
    plain = fake_steps(span=False)                                                          # no span copy: op and cells compared, gate / pointer not
    d = B.logit_diff(plain, bumped(plain, 2, 'cells', 0.5))
    assert d['op'] == 0.0 and abs(d['cells'] - 0.5) < 1e-6 and d['gate'] is None and d['pointer'] is None
    nan = bumped(a, 0, 'op', float('nan'))
    assert B.logit_diff(a, nan)['op'] == float('inf') and B.diff_bad(B.diff_overall(B.logit_diff(a, nan)))      # NaN is never a pass
    with pytest.raises(B.ProbeError):
        B.logit_diff(a, a[:2])
    with pytest.raises(B.ProbeError):
        B.logit_diff(a, fake_steps(span=False))


def perturb_tf_run(monkeypatch, which, by):
    orig = B.tf_run

    def run(m, batch, g):
        o, ans = orig(m, batch, g)
        o['steps'] = bumped(o['steps'], 2, which, by)
        return o, ans
    monkeypatch.setattr(B, 'tf_run', run)


def test_own_call_identity_compares_cells_and_reports_each_kind(model, preps, monkeypatch):
    res = B.own_call_identity(model, preps, 64)
    assert res['bad'] == [] and set(res['max_diff_by']) == set(B.DIFF_KINDS) and all(v is not None and v <= 1e-6 for v in res['max_diff_by'].values())
    perturb_tf_run(monkeypatch, 'cells', 0.01)                                            # the cell probabilities used not to be compared at all
    res = B.own_call_identity(model, preps, 64)
    assert abs(res['max_diff_by']['cells'] - 0.01) < 1e-6 and res['max_diff_by']['op'] <= 1e-6 and res['max_diff'] >= 0.0099
    assert B.self_check_failed(dict(bad=0, ans_bad=0, max_diff=res['max_diff']))


def test_own_call_identity_without_span_copy_still_compares_op_and_cells(monkeypatch):
    m = build_plain_model()
    res = B.own_call_identity(m, hand_preps(), 64)
    by = res['max_diff_by']
    assert res['bad'] == [] and by['gate'] is None and by['pointer'] is None and by['op'] <= 1e-6 and by['cells'] <= 1e-6 and by['op'] is not None
    perturb_tf_run(monkeypatch, 'op', 0.5)
    assert abs(B.own_call_identity(m, hand_preps(), 64)['max_diff_by']['op'] - 0.5) < 1e-5


def build_plain_model(seed=5):
    from custom_io.data import CharVocab
    from custom_io.models.tool import Tool
    torch.manual_seed(seed)
    m = Tool(CharVocab.build(hand_rows()), **SMALL).eval()
    with torch.no_grad():
        m.op_head.weight.mul_(30)
        m.op_head.bias.normal_(0, 3)
    return m


def test_premise_check_compares_op_cells_gate_and_pointer(model, preps, monkeypatch):
    pc = gold_path_check(model, preps, 64)
    assert pc['n'] == pc['ok'] == len(preps) and set(pc['max_diff_by']) == set(B.DIFF_KINDS)
    assert all(v is not None and v <= 1e-6 for v in pc['max_diff_by'].values()), pc['max_diff_by']      # op included, though every round is forced
    for which, kind in (('op', 'op'), ('cells', 'cells'), ('ga', 'gate'), ('la', 'pointer')):
        perturb_tf_run(monkeypatch, which, 0.3)
        pc = gold_path_check(model, preps, 64)
        assert abs(pc['max_diff_by'][kind] - 0.3) < 1e-4, (which, pc['max_diff_by'])
        assert B.premise_failed(pc)
        monkeypatch.undo()


def test_premise_check_without_span_copy_compares_op_and_cells(monkeypatch):
    m = build_plain_model()
    pc = gold_path_check(m, hand_preps(), 64)
    by = pc['max_diff_by']
    assert pc['ok'] == pc['n'] and by['gate'] is None and by['pointer'] is None and by['op'] is not None and by['op'] <= 1e-6 and by['cells'] <= 1e-6
    perturb_tf_run(monkeypatch, 'cells', 0.2)
    assert B.premise_failed(gold_path_check(m, hand_preps(), 64))


def test_forced_free_run_keeps_the_op_logits_it_computed_before_the_boost(model, preps):
    o, _, _ = B.free_chunk(model, [p['prompt'] for p in preps[:3]], {0: {0: ('add', '1', '2')}})
    free, _, _ = B.free_chunk(model, [p['prompt'] for p in preps[:3]])
    assert len(o['op_raw']) == 7 and torch.equal(o['op_raw'][0], free['steps'][0][0])      # round 0 is before any tape: the raw logits are the free run's
    assert float(o['steps'][0][0][0].max()) > 1e3 and float(o['op_raw'][0][0].max()) < 1e3


def test_collect_records_the_max_logit_difference_per_kind(tiny, tmp_path):
    out = tmp_path / 'o'
    B.main(collect_argv(tiny, out, 'k', 'eval', '--no-sha', '--rewrites', 'plus', '--rewrite-strata', 'HO', '--self-check', '8'))
    meta = json.load(open(out / 'bracket-k.meta.json'))
    for d in [meta['self_check'], meta['premise']['orig']] + list(meta['self_check_versions'].values()):
        assert set(d['max_diff_by']) == set(B.DIFF_KINDS) and all(v is not None and v <= 1e-6 for v in d['max_diff_by'].values())
    text = report(*[x for x in (B.load_records([str(out)]))], None, no_gate=True)
    assert 'by kind (op / cells / gate / pointer' in text


# ---------- 6. explicit raises ----------

def test_gating_checks_are_raises_not_asserts_even_under_python_O():
    import subprocess
    import sys
    code = '''
import sys
from domain.far import bracket_probe as B
try:
    B.check_real_strata(B.prepare([dict(id="a", split="HO", prompt="A: 1 2 | B: 3 4 ; =(SUM(A1:A2))*(MAX(B1:B2))", answer="9")]))
except B.StrataError as e:
    print("raised", type(e).__mro__[1].__name__)
else:
    print("NOT RAISED")
try:
    B.main(["collect", "--ckpt", "x", "--no-sha", "--label", "x", "--eval-rows", "x", "--rewrites", "plus,bogus", "--out", "x"])
except SystemExit as e:
    print("exit", e.code)
'''
    r = subprocess.run([sys.executable, '-O', '-c', code], capture_output=True, text=True, cwd=REPO, env=dict(os.environ, PYTHONPATH=REPO))
    assert 'raised ProbeError' in r.stdout and 'exit 2' in r.stdout and 'unknown rewrite' in r.stderr, (r.stdout, r.stderr[-500:])


def test_check_real_strata_raises_strata_error():
    p = B.prepare(hand_rows())
    with pytest.raises(B.StrataError, match='stratum D: 4 rows, expected 106') as ei:
        B.check_real_strata(p)
    assert isinstance(ei.value, RuntimeError) and not isinstance(ei.value, AssertionError)
    assert B.check_real_strata(p, dict(D=4, HO=7))['D'] == 4


def test_tf_run_always_runs_in_eval_mode_and_records_what_the_caller_handed(preps):
    m = build_model()
    batch = B.make_batch(m, [dict(id='a', prompt=preps[0]['prompt'], answer='', accepted=[], family='', level=0)])
    g = dict(op=torch.zeros(1, B.N_RES, dtype=torch.long), tape=[[''] * B.N_RES])
    seen = []
    orig_run = m.run
    m.run = lambda *a, **k: (seen.append(m.training), orig_run(*a, **k))[1]
    m.train()                                   # a caller that hands over a training-mode model: no raise, the run is in eval mode
    o, _ = B.tf_run(m, batch, g)
    assert o['caller_training'] is True and seen == [False] and not m.training
    m.eval()
    o, _ = B.tf_run(m, batch, g)
    assert o['caller_training'] is False and seen == [False, False]
    m.run = orig_run


def test_tf_pass_records_a_training_mode_caller(model, preps):
    m = build_model()
    m.train()
    out = B.tf_pass(m, preps[:2], 64)
    assert out and all(r['caller_training'] is True for r in out) and not m.training
    assert all(r['caller_training'] is False for r in B.tf_pass(m, preps[:2], 64))


def test_tf_run_raises_when_a_drill_draw_happens(preps):
    m = build_model()
    batch = B.make_batch(m, [dict(id='a', prompt=preps[0]['prompt'], answer='', accepted=[], family='', level=0)])
    g = dict(op=torch.zeros(1, B.N_RES, dtype=torch.long), tape=[[''] * B.N_RES])
    m.eval()
    orig = m.run

    def drawing(*a, **k):
        m._drill_rng.random()
        return orig(*a, **k)
    m.run = drawing
    with pytest.raises(B.TFRunError, match='ans_drill'):
        B.tf_run(m, batch, g)
    assert m._full_tape is False


def test_rewrites_are_validated_by_argparse(tiny, tmp_path, capsys):
    for bad in ('bogus', 'plus,bogus', 'PLUS'):
        with pytest.raises(SystemExit) as e:
            B.main(collect_argv(tiny, tmp_path / 'o', 'x', 'eval', '--no-sha', '--rewrites', bad))
        assert e.value.code == 2 and 'unknown rewrite' in capsys.readouterr().err
    assert not (tmp_path / 'o').exists()
    assert B.rewrite_list('') == () and B.rewrite_list('plus, swap') == ('plus', 'swap')


# ---------- 7. position_role with nK == 0 ----------

NK0 = 'A: 69 20 96 | B: 30 55 69 ; =B3+A2*2*B3/A1'


def test_position_role_round_0_is_j_first_when_k_is_a_bare_cell():
    p = B.prep_row(dict(id='z', split='S5', prompt=NK0, answer=sheet.evaluate(NK0)['value']))
    assert (p['n'], p['nK'], p['nJ'], p['order_ok']) == (4, 0, 3, True)
    assert [B.position_role(p, k) for k in range(6)] == ['J_first', 'J_cont', 'J_cont', 'join', 'post', 'post']
    assert B.round_labels(p, 0) == {'J_first', 'r0', 'other'}                 # r0 and J_first coincide: both labels
    assert 'r0' not in [B.position_role(p, k) for k in range(7)]
    wrong0 = rec_of(p, {0: ('add', '1', '1')})
    c = {name: B.repair_ok(wrong0, S) for name, S in B.REPAIR_SETS.items()}
    assert c['r0'] and c['J_first'] and c['r0+J_first'] and not c['none'] and not c['join']       # the r0 repair set still contains round 0
    assert B.role_acc([wrong0], 'r0', 'pos') == (0, 0) and B.role_acc([wrong0], 'J_first', 'pos') == (0, 1)
    ok = [B.position_role(B.prep_row(dict(id='y', split='S', prompt='A: 3 4 | B: 5 6 ; =SUM(A1:A2)+B1', answer='12')), k) for k in range(3)]
    assert ok == ['r0', 'join', 'post']                                       # nK > 0 is unchanged


def test_position_role_round_0_is_j_first_on_the_real_nk0_rows(l5):
    ps = [p for p in B.prepare(LP.load_jsonl(l5['eval'])) if p['nK'] == 0 and p['order_ok']]
    assert len(ps) == 12 and any(p['prompt'].endswith('=B3+A2*2*B3/A1') for p in ps)
    for p in ps:
        assert [B.position_role(p, k) for k in (0, p['n'] - 1, p['n'])] == ['J_first', 'join', 'post'], p['prompt']
        assert B.round_labels(p, 0) >= {'J_first', 'r0'}


# ---------- 8. inclusion rules ----------

def test_call_type_tables_include_items_that_are_not_order_ok_and_position_tables_do_not(preps):
    DJ = preps[2]
    a, b = rec_of(DJ, {1: ('mul', '9', '3')}), rec_of(DJ, {1: ('mul', '9', '3')})
    b['order_ok'] = False
    assert B.role_acc([a, b], 'ca_mul', 'type') == (0, 2)                      # call types are defined for every item
    assert B.role_acc([a, b], 'J_first', 'pos') == (0, 1)                      # nK is a boundary only for an order_ok item
    c = rec_of(DJ)
    c['order_ok'] = False
    assert B.role_acc([c], 'ca_mul', 'type') == (1, 1) and B.role_acc([c], 'J_first', 'pos') == (0, 0)


def test_report_states_the_inclusion_rule_of_each_table(preps):
    DJ = preps[2]
    recs = copies(DJ, 3, wrong={1: ('mul', '9', '3')})
    recs[0]['order_ok'] = False
    text = B.sec_roles({'t': recs}, strata=('D',))
    assert text.count('Inclusion: order_ok items only') == 2 and text.count('Inclusion: all items with a TF record, order_ok or not') == 2
    row = next(l for l in text.splitlines() if l.startswith('| D (n=3, order_ok 2)'))
    assert '0/2' in row                                                          # position: 2 order_ok items
    type_rows = [l for l in text.split('by call type, exact')[1].splitlines() if l.startswith('| D')]
    assert any('0/3' in l for l in type_rows)                                    # call type ca_mul: all 3 items
    rw = {**{r['id']: r for r in recs}}
    sub = B.sec_rewrites({'t': recs + [dict(r, id=r['id'] + '~strip', base_id=r['id'], version='strip') for r in recs]}, strata=('D',))
    assert 'By call type (inclusion: every paired item with a round of the type, order_ok or not)' in sub and rw
    assert 'Inclusion: D items' in B.sec_2x2({'t': recs}) and 'Inclusion: order_ok items with a TF record' in B.sec_margins({'t': recs})


def test_b1b2_requires_order_ok_and_reports_the_excluded_items(preps):
    DJ = preps[2]
    ok = copies(DJ, 2)
    unordered = copies(DJ, 1)
    unordered[0]['order_ok'] = False
    one_piece = B.prep_row(dict(id='w', split='HO', prompt='A: 1 2 | B: 3 4 ; =A1/A2', answer=sheet.evaluate('A: 1 2 | B: 3 4 ; =A1/A2')['value']))
    assert one_piece['layout'] is None
    nolay = [rec_of(one_piece)]
    nolay[0]['label'] = 't'
    text = B.sec_b1b2({'t': ok + unordered + nolay}, strata=('HO',))
    row = next(l for l in text.splitlines() if l.startswith('| HO '))
    assert '| 2 | 2 (1 no layout, 1 layout but not order_ok) |' in row, row
    assert 'AND are order_ok' in text and 'excluded counts' in text


# ---------- 9. wilson ----------

def test_wilson_is_the_library_interval():
    import math
    from learnlab.metrics import wilson_interval

    def local(k, n, z=1.96):                      # the former local formula
        p, den = k / n, 1 + z * z / n
        c = (p + z * z / (2 * n)) / den
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return max(0.0, c - h), min(1.0, c + h)
    for n in (1, 2, 3, 10, 59, 106, 420, 2940):
        for k in sorted({0, 1, n // 3, n // 2, n - 1, n}):
            lo, hi = B.wilson(k, n)
            assert (lo, hi) == wilson_interval(k, n)
            assert abs(lo - local(k, n)[0]) < 2e-5 and abs(hi - local(k, n)[1]) < 2e-5, (k, n)       # the numbers match the former ones to far below frac's 0.1 point
    assert B.wilson(0, 7)[0] == 0.0 and B.wilson(7, 7)[1] == 1.0 and B.wilson(0, 0) is None
    assert B.frac(0, 7).startswith('0/7 = 0.0% [0.0,') and B.frac(7, 7).endswith('100.0]') and B.frac(3, 0) == '3/0'


def test_wilson_delegates_to_the_library(monkeypatch):
    monkeypatch.setattr(B, 'wilson_interval', lambda k, n: (0.25, 0.75))
    assert B.wilson(3, 10) == (0.25, 0.75) and B.frac(3, 10).endswith('[25.0, 75.0]')


# ---------- 10. small clean-ups ----------

def test_tf_pass_closes_the_constants_file(model, preps, monkeypatch):
    import builtins
    from domain import mode
    opened = []
    real_open = builtins.open

    def spy(f, *a, **k):
        fh = real_open(f, *a, **k)
        if str(f) == str(mode.CONST_PATH):
            opened.append(fh)
        return fh
    monkeypatch.setattr(builtins, 'open', spy)
    B.tf_pass(model, preps[:2], 64)
    assert opened and all(fh.closed for fh in opened)


def test_spaced_tokenizer_is_checked_once_per_make_versions_call(preps, monkeypatch):
    n = []
    orig = B.spaced_ok
    monkeypatch.setattr(B, 'spaced_ok', lambda: (n.append(1), orig())[1])
    ho = [p for p in preps if p['layout'] == '(K)*(J)' and 'HO' in p['strata']]
    assert len(ho) >= 6
    vs, skipped = B.make_versions(ho, 'spaced')
    assert len(vs) == len(ho) and skipped == {} and len(n) == 1                  # was one tokenizer check per prompt
    assert B.make_version(ho[0], 'spaced')[1] is None and len(n) == 2            # standalone: still checked
    assert B.make_version(ho[0], 'spaced', spaced=False) == (None, 'tokenizer does not skip spaces') and len(n) == 2
    B.make_versions(ho, 'plus')
    assert len(n) == 2                                                           # other rewrites never ask


# ---------- 11. one production path ----------

def test_gold_path_check_and_collect_items_share_the_production_pass(model, preps, monkeypatch):
    seen = []
    orig = B.tf_with_premise
    monkeypatch.setattr(B, 'tf_with_premise', lambda *a, **k: (seen.append(k.get('margins')), orig(*a, **k))[1])
    gold_path_check(model, preps, 64)
    B.collect_items(model, preps, 'x', 64, with_margins=True)
    assert seen == [None, True]                                                  # both went through tf_with_premise (collect_items with margins)


def test_pooled_validate_wrapper_goes_through_validate_all(monkeypatch):
    rows = hand_preps()[:4]
    m, undo, recs, free = scripted_records(rows, {0: 0, 1: 1, 2: 1, 3: None})
    try:
        calls = []
        orig = B.validate_all
        monkeypatch.setattr(B, 'validate_all', lambda *a, **k: (calls.append((a, k)), orig(*a, **k))[1])
        out = validate_repair(m, rows, recs, sample=None)
        assert len(calls) == 1 and calls[0][1].get('sets') == () and (out['n'], out['agree'], out['mismatches']) == (3, 3, [])
        none = validate_repair(m, rows, [dict(r, tf=[]) for r in recs], sample=None)                  # no item with a TF record: nothing forced
        assert (none['n'], none['agree'], none['mismatches']) == (0, 0, [])
        orig_forced = B.forced_run
        monkeypatch.setattr(B, 'forced_run', lambda *a, **k: [dict(o, tape=['x'] * B.N_RES) for o in orig_forced(*a, **k)])
        bad = validate_repair(m, rows, recs, sample=None)                                              # the production tape check applies here too
        assert bad['agree'] == 0 and bad['mismatches'][0]['tape_round'] == 0
    finally:
        undo()


# ---------- 12. test data location ----------

def test_l5_rows_are_extracted_from_git_when_the_env_dir_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv('BRACKET_PROBE_DATA', str(tmp_path / 'nowhere'))
    found, why = extract_l5_from_git(str(tmp_path / 'x'), ref='refs/heads/no-such-ref-for-sure')
    assert found == {} and 'eval-rows-l5.jsonl not on refs/heads/no-such-ref-for-sure' in why
    found, why = extract_l5_from_git(str(tmp_path / 'g'))
    if not all(f in found for f in L5_REQUIRED):
        pytest.skip(f'{GIT_REF} is not available here ({why})')
    rows = LP.load_jsonl(found['eval-rows-l5.jsonl'])
    assert len(rows) == 2100 and len(LP.load_jsonl(found['train-rows-l5.jsonl'])) > 8000 and os.path.dirname(found['eval-rows-l5.jsonl']).endswith('stratum')
    assert B.check_real_strata(B.prepare(rows))['D'] == 106


def test_the_l5_fixture_names_its_source(l5):
    assert os.path.exists(l5['eval']) and os.path.exists(l5['train']) and (l5['source'].startswith('git ') or l5['source'].startswith('BRACKET_PROBE_DATA='))
