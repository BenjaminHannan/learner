"""Exact-match evaluation. A model only needs .vocab and .generate(batch, lesion=None) -> list[str]."""
import argparse, json, os
import numpy as np
import torch
from custom_io.data import DEFAULT_DATA, DEV_SPLITS, Dataset, collate, load_rows, to_device

MULTISTEP = {'chain_ops', 'chain_story2', 'story_chain3', 'var_chain', 'state_update', 'backward_solve',
             'kin_chain', 'object_track', 'order_chain', 'table_calc', 'distance_units', 'percent_rate'}


def norm(s):
    return ' '.join(s.strip().lower().split())


def is_hit(pred, row):
    return norm(pred) in {norm(a) for a in row['accepted']}


def subsample(rows, k):
    """k rows spread evenly over the file (dev files are grouped by family, so a prefix would be one family)."""
    if k is None or k >= len(rows):
        return rows
    return [rows[i] for i in np.linspace(0, len(rows) - 1, k).astype(int)]


def _tally(d, key, hit):
    c = d.setdefault(key, {'correct': 0, 'n': 0})
    c['correct'] += hit
    c['n'] += 1


@torch.no_grad()
def evaluate(model, rows, batch_size=128, device=None, lesion=None, return_preds=False):
    """-> {'exact' (%), 'correct', 'n', 'by_family', 'by_level' (str keys), 'multistep'} (+ 'preds' {id: pred})."""
    device = device or next(model.parameters()).device
    was_training = model.training
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))     # length-sorted: less padding
    preds = [None] * len(rows)
    for s in range(0, len(order), batch_size):
        ids = order[s:s + batch_size]
        out = model.generate(to_device(collate([ds[i] for i in ids]), device), lesion=lesion)
        assert len(out) == len(ids)
        for i, p in zip(ids, out):
            preds[i] = p
    model.train(was_training)
    res = {'by_family': {}, 'by_level': {}, 'multistep': {'correct': 0, 'n': 0}}
    for r, p in zip(rows, preds):
        hit = int(is_hit(p, r))
        _tally(res['by_family'], r['family'], hit)
        _tally(res['by_level'], str(r['level']), hit)
        if r['family'] in MULTISTEP:
            res['multistep']['correct'] += hit
            res['multistep']['n'] += 1
    c = sum(v['correct'] for v in res['by_family'].values())
    res.update(correct=c, n=len(rows), exact=100 * c / max(len(rows), 1))
    res['multistep']['exact'] = 100 * res['multistep']['correct'] / max(res['multistep']['n'], 1)
    if return_preds:
        res['preds'] = {r['id']: p for r, p in zip(rows, preds)}
    return res


def eval_all(model, dev_dir=DEFAULT_DATA, max_per_split=None, lesion=None, batch_size=128, device=None):
    """Evaluate the six dev splits -> {split: evaluate(...)}. dev_dir is the data root or its dev/ folder."""
    if os.path.isdir(os.path.join(dev_dir, 'dev')):
        dev_dir = os.path.join(dev_dir, 'dev')
    return {s: evaluate(model, subsample(load_rows(os.path.join(dev_dir, f'{s}.jsonl')), max_per_split),
                        batch_size, device, lesion) for s in DEV_SPLITS}


def short(res):
    """One-line view of an eval_all result: {split: exact %} plus the multistep exact on in_dist."""
    return {**{s: round(v['exact'], 2) for s, v in res.items()}, 'multistep_in_dist': round(res['in_dist']['multistep']['exact'], 2)}


if __name__ == '__main__':      # python -m custom_io.evalx --run RUN_DIR [--data DIR] [--lesion L] [--max N]
    from custom_io.models import load_model
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True, help='dir containing checkpoint.pt')
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--lesion')
    ap.add_argument('--max', type=int)
    ap.add_argument('--device', default='cpu')
    a = ap.parse_args()
    m = load_model(os.path.join(a.run, 'checkpoint.pt'), a.device)
    print(json.dumps(short(eval_all(m, a.data, a.max, a.lesion, device=a.device))))
