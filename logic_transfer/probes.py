"""Counterfactual probes for ladder rungs 0-2 (reported, never gated): does a passing checkpoint's answer move with the CONTENT?

  python -m logic_transfer.probes --ckpt CKPT --rows dev.jsonl --rung R [--device cpu|cuda] [--n 600] [--out probe.json]

Every probe edits the prompt TEXT of an eval row, re-derives the gold label of the edited text with the independent reader
(verify_rungs, which imports nothing from logicgen), and scores the checkpoint on the edited rows (new row ids: the loss/target cache is keyed
by id). Probes:
  rung 0  swap_answer   "The answer is W." -> "The answer is W'." (W' != W): gold = W'
          drop_answer   the answer sentence deleted: no gold exists; reported = how often the ORIGINAL word is still produced (chance ~ 1/3)
  rung 1,2 swap_entity  the queried entity replaced by one that appears nowhere in the prompt: gold = unknown
          flip_query    the query's "not" toggled: true <-> false, unknown stays
          drop_support  the fact about the queried (entity, predicate) deleted (true/false rows only): gold = unknown
Moving with content = accuracy on the edited rows near 100%; ignoring it = near the share a fixed answer would get.
"""
import argparse
import json
import random
import re

from logic_transfer import rows as R
from logic_transfer import verify_rungs as V

ENT_POOL = ['Zed', 'Quin', 'Rhea', 'Odin', 'Mira', 'Tove', 'Ugo', 'Wren', 'Xan', 'Yara']      # names outside the generator's lexicon is fine for a probe
WORDS = ('true', 'false', 'unknown')


def _suffix(prompt):
    body, opts = V.split_options(prompt)
    return body, (prompt[len(body):] if opts is not None else '')


def _new(r, tag, body, suffix, gold):
    r2 = {k: v for k, v in r.items() if k != 'meta'}
    r2.update(id=f"{r['id']}-cf-{tag}", prompt=body + suffix, answer=gold, accepted=[gold])
    return r2


def cf_rung0(rows, rng):
    swap, drop = [], []
    for r in rows:
        body, suf = _suffix(r['prompt'])
        w = r['answer']
        w2 = rng.choice([x for x in WORDS if x != w])
        swap.append(_new(r, 'swap', V.ANS.sub(f'The answer is {w2}.', body, count=1), suf, w2))
        d = re.sub(r'The answer is (?:true|false|unknown)\. ?', '', body, count=1).strip()
        drop.append(_new(r, 'drop', d, suf, w))                       # gold kept = the original word: accuracy here = "still says the old word"
    return {'swap_answer': swap, 'drop_answer': drop}


def cf_rung12(rows, rng):
    swap, flip, drop = [], [], []
    for r in rows:
        body, suf = _suffix(r['prompt'])
        ss = [s.strip() for s in V.sentences(body)]
        q = V.QUERY.match(ss[-1])
        if not q:
            continue
        qe, qn, qp = q.group(1), q.group(2), q.group(3)
        used = {m.group(1) for s in ss[:-1] for m in [V.FACT.match(s)] if m}
        e2 = rng.choice([e for e in ENT_POOL if e not in used and e != qe])
        sw = ss[:-1] + [f'Is {e2} {qn or ""}{qp}?']
        swap.append(_new(r, 'swap', ' '.join(sw), suf, 'unknown'))
        fl = ss[:-1] + [f'Is {qe} {"" if qn else "not "}{qp}?']
        flip.append(_new(r, 'flip', ' '.join(fl), suf, {'true': 'false', 'false': 'true', 'unknown': 'unknown'}[r['answer']]))
        if r['answer'] != 'unknown':
            keep = [s for s in ss[:-1] if not (V.FACT.match(s) and V.FACT.match(s).group(1) == qe and V.FACT.match(s).group(3) == qp)]
            drop.append(_new(r, 'drop', ' '.join(keep + [ss[-1]]), suf, 'unknown'))
    return {'swap_entity': swap, 'flip_query': flip, 'drop_support': drop}


def check_gold(cfs, rung):
    """Re-derive each edited row's gold with the independent reader (rungs 1-2 and swap_answer); returns the number of mismatches."""
    bad = 0
    for name, rs in cfs.items():
        if name == 'drop_answer':
            continue
        for r in rs:
            lab, err = V.check_r0(r) if rung == 0 else V.check_r12(r, 'any')       # 'any': an edit may leave 0-5 facts
            if err or lab != r['answer']:
                bad += 1
    return bad


def run(ckpt, rows, rung, device='cpu', seed=7):
    import torch
    from custom_io.evalx import evaluate
    from custom_io.models import load_model
    rng = random.Random(seed)
    cfs = (cf_rung0 if rung == 0 else cf_rung12)(rows, rng)
    bad = check_gold(cfs, rung)
    assert bad == 0, f'{bad} counterfactual rows whose independent label differs from the intended one'
    m = load_model(ckpt, device)
    out = {'n_rows': len(rows), 'probes': {}}
    base = evaluate(m, rows, 128, torch.device(device))
    out['original_dev'] = round(base['exact'], 2)
    for name, rs in cfs.items():
        r = evaluate(m, rs, 128, torch.device(device), return_preds=True)
        d = {'n': len(rs), 'acc': round(r['exact'], 2)}
        if name == 'swap_entity' or name == 'drop_support':
            d['says_unknown'] = d['acc']
        if name == 'drop_answer':
            d['still_old_word'] = d.pop('acc')
        out['probes'][name] = d
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--rows', required=True)
    ap.add_argument('--rung', type=int, required=True)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--n', type=int, default=600)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    from custom_io.data import load_rows
    rows = load_rows(a.rows, keep=None)[:a.n]
    res = run(a.ckpt, rows, a.rung, a.device)
    print(json.dumps(res))
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
