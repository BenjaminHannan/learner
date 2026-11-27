"""python3 -m custom_io.tests.test_plain_tf_steps   (CPU, about a minute)"""
import time
import torch
from custom_io.data import DEFAULT_DATA, CharVocab, Dataset, collate, load_rows
from custom_io.models.plain_tf_steps import (PlainTFSteps, STEP_FAMILIES, calc_fill, final_answer, target_text)
import custom_io.models.plain_tf_steps as M


def batch_of(rows, v):
    ds = Dataset(rows, v, strict=False)
    return collate([ds[i] for i in range(len(rows))])


def real_rows(n_per=2):
    rows, seen = load_rows(f'{DEFAULT_DATA}/train.jsonl'), {}
    for r in rows:
        if seen.setdefault(r['family'], []) is not None and len(seen[r['family']]) < n_per:
            seen[r['family']].append(r)
    return rows, seen


def test_targets():
    rows, seen = real_rows()
    assert STEP_FAMILIES <= set(seen), STEP_FAMILIES - set(seen)
    assert target_text(dict(family='var_chain', steps=['z = 21 * 2 = 42', 'm = 42 * 7 = 294'], answer='294')) == \
        'z = 21 * 2 = 42; m = 42 * 7 = 294 # 294'
    assert target_text(dict(family='copy_word', steps=['copy sune'], answer='sune')) == 'sune'
    assert target_text(dict(family='chain_ops', steps=['1 + 1 = 2'] * 12, answer='2')) == '2'      # over the cap
    for r in (x for v in seen.values() for x in v):
        t = target_text(r)
        assert len(t) <= 64 or t == r['answer']
        assert (' # ' in t) == (r['family'] in STEP_FAMILIES and t != r['answer'])
        assert final_answer(t) == r['answer']
    print('targets ok', sum(target_text(r) != r['answer'] for r in rows) / len(rows), 'of rows carry steps')


def test_memorise():
    rows, seen = real_rows(1)
    sel = [seen[f][0] for f in sorted(STEP_FAMILIES)[:8]] + [seen[f][0] for f in ['copy_word', 'list_index', 'compare_numbers', 'odd_one_out', 'table_lookup', 'syllogism', 'cipher_map', 'kin_chain'] if f in seen]
    sel = sel[:16]
    v = CharVocab.build(rows)
    torch.manual_seed(0)
    m = PlainTFSteps(v, d_model=128, n_layers=2)
    b = batch_of(sel, v)
    opt = torch.optim.AdamW(m.parameters(), 2e-3)
    t0 = time.time()
    for i in range(400):
        l = m.loss(b); opt.zero_grad(); l.backward(); opt.step()
        if i % 50 == 0:
            print(i, round(float(l), 4))
        if float(l) < 0.003:
            break
    m.eval()
    out = m.generate(b)
    acc = sum(o == r['answer'] for o, r in zip(out, sel)) / len(sel)
    print('memorise', round(acc, 3), round(time.time() - t0, 1), 's', 'steps in', sum(target_text(r) != r['answer'] for r in sel))
    assert acc == 1.0, [(o, r['answer']) for o, r in zip(out, sel)]
    solo = [m.generate(batch_of([r], v))[0] for r in sel]
    assert solo == out, (solo, out)       # batched == single-row
    print('batched == single ok; params', m.n_params())


def test_calc():
    assert calc_fill('x = 21 * 2 =') == ' 42' and calc_fill('a; 115 / 5 =') == ' 23' and calc_fill('7 / 2 =') is None
    assert calc_fill('3 x 4 =') == ' 12' and calc_fill('-3 - 5 =') == ' -8' and calc_fill('86+5=') == '91'
    assert calc_fill('64+14-15=') == '63' and calc_fill('23+17-8=') == '32' and calc_fill('x; 76+3=') == '79' and calc_fill('2+3*4=') is None
    assert calc_fill('') is None and calc_fill('= =') is None and calc_fill('9 / 0 =') is None and calc_fill('12 =') is None
    assert calc_fill('x' * 500 + '; 1 + 1 =') == ' 2'
    # scripted model: always writes the plan, with a wrong '0' after every '='; calc must overrule it
    plan = '34 + 29 = 0; 62 * 2 = 0 # 63 - 1 = 0'
    v = CharVocab.build([dict(prompt='x', answer='y')])
    m = PlainTFSteps(v, d_model=32, n_layers=1, n_heads=2).eval()
    seen = []

    def hidden(ids, loops=None):
        m._ids = ids
        return torch.zeros(ids.shape[0], ids.shape[1], 32)

    def logits(h):
        import re
        out = torch.full((h.shape[0], len(v)), -1.0)
        for b in range(h.shape[0]):
            t = ''.join(v.itos[i] for i in m._ids[b, 3:].tolist() if i >= 13)
            if b == 0:
                seen.append(t)
            k = len(re.sub(r'= -?\d+', '= 0', t))
            out[b, v.stoi[plan[k]] if k < len(plan) else 2] = 1.0
        return out
    m.hidden, m.logits = hidden, logits
    b = batch_of([dict(prompt='x', answer='y')], v)
    assert m.generate(b) == ['63 - 1 = 0'], (m.generate(b), seen[-2:])
    seen.clear()
    assert m.generate(b, 'calc') == ['63 - 1 = 62'], seen[-1]
    assert any('34 + 29 = 63; 62 * 2 = 124 # 63 - 1 = 6' in t for t in seen), seen[-3:]
    print('calc decode ok')


if __name__ == '__main__':
    t0 = time.time()
    test_targets(); test_calc(); test_memorise()
    print('all ok', round(time.time() - t0, 1), 's')
