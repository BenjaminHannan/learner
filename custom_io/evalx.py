"""Exact-match evaluation. A model only needs .vocab and .generate(batch, lesion=None) -> list[str]
(donor_eval also needs .state / .talk, see models/base.py)."""
import argparse, json, os
import numpy as np
import torch
import torch.nn.functional as F
from custom_io.data import DEFAULT_DATA, DEV_SPLITS, Dataset, collate, load_rows, to_device

MULTISTEP = {'chain_ops', 'chain_story2', 'story_chain3', 'var_chain', 'state_update', 'backward_solve',
             'kin_chain', 'object_track', 'order_chain', 'table_calc', 'distance_units', 'percent_rate'}
CHAIN5 = ['chain_ops', 'chain_story2', 'story_chain3', 'state_update', 'var_chain']
ONE_STEP = ['arith_bare', 'div_exact', 'story_addsub']


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


def _pad_prompt(batch, T):
    """Right-pad a collated batch's prompt tensors to length T (the model sees the same rows, just more PAD)."""
    k = T - batch['prompt_ids'].shape[1]
    return dict(batch, prompt_ids=F.pad(batch['prompt_ids'], (0, k)), prompt_mask=F.pad(batch['prompt_mask'], (0, k))) if k else batch


def donor_pairs(rows, seed=0):
    """-> ([(i, j)], n_skipped): row i gets donor row j of the SAME family whose normalised answer is not
    one of i's accepted answers (so a donor-answer hit can never also be an exact hit). Row i is skipped
    (and counted) if its family has no such row. Deterministic given seed and the order of `rows`."""
    rng, fam, pairs = np.random.RandomState(seed), {}, []
    for i, r in enumerate(rows):
        fam.setdefault(r['family'], []).append(i)
    ans = [norm(r['answer']) for r in rows]
    for i, r in enumerate(rows):
        bad = {norm(a) for a in r['accepted']} | {ans[i]}
        cand = [j for j in fam[r['family']] if ans[j] not in bad]
        if cand:
            pairs.append((i, cand[rng.randint(len(cand))]))
    return pairs, len(rows) - len(pairs)


@torch.no_grad()
def donor_eval(model, rows, batch_size=128, device=None, seed=0):
    """Donor-swap lesion. Every row i gets a donor row j (donor_pairs: same family, different answer); the reasoner
    runs on the donor, the talker answers row i: preds = model.talk(model.state(donor_batch), current_batch).
    So talk() receives the DONOR's state and the CURRENT rows' batch (lengths and copy sources come from the
    current batch). Both batches are collated separately, then padded to a common prompt length so a time dim
    in the state still matches the current batch's shape. Pairing is by index and independent of batch order.
    -> {'exact' (% equal to the current row's accepted answers), 'donor_match' (% equal to the donor row's answer),
        'n' (rows scored), 'skipped' (no donor available), 'by_family': {fam: {exact, donor_match, n}}}."""
    device = device or next(model.parameters()).device
    was_training = model.training
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    pairs, skipped = donor_pairs(rows, seed)
    pairs.sort(key=lambda p: max(len(rows[p[0]]['prompt']), len(rows[p[1]]['prompt'])))     # length-sorted: less padding
    preds = {}
    for s in range(0, len(pairs), batch_size):
        chunk = pairs[s:s + batch_size]
        cur, don = collate([ds[i] for i, _ in chunk]), collate([ds[j] for _, j in chunk])
        T = max(cur['prompt_ids'].shape[1], don['prompt_ids'].shape[1])
        cur, don = (to_device(_pad_prompt(b, T), device) for b in (cur, don))
        out = model.talk(model.state(don), cur)
        assert len(out) == len(chunk)
        for (i, _), p in zip(chunk, out):
            preds[i] = p
    model.train(was_training)
    fam = {}
    for i, j in pairs:
        c = fam.setdefault(rows[i]['family'], {'exact': 0, 'donor_match': 0, 'n': 0})
        c['exact'] += is_hit(preds[i], rows[i])
        c['donor_match'] += norm(preds[i]) == norm(rows[j]['answer'])
        c['n'] += 1
    def pct(c):
        return {k: 100 * c[k] / max(c['n'], 1) for k in ('exact', 'donor_match')} | {'n': c['n']}
    tot = {k: sum(c[k] for c in fam.values()) for k in ('exact', 'donor_match', 'n')}
    return {**pct(tot), 'skipped': skipped, 'by_family': {f: pct(c) for f, c in fam.items()}}


def _dev_rows(dev_dir, split, max_per_split):
    d = os.path.join(dev_dir, 'dev')
    return subsample(load_rows(os.path.join(d if os.path.isdir(d) else dev_dir, f'{split}.jsonl')), max_per_split)


def chain_panel(model, big_root, lesion=None, batch_size=128, device=None, return_preds=False):
    """chain-5: evaluate() on the CHAIN5 families of the big build's dev/in_dist.jsonl (200 rows per cell).
    -> {'exact', 'n', 'by_family': {fam: {correct, n}}} (+ 'preds' with return_preds)."""
    rows = [r for r in _dev_rows(big_root, 'in_dist', None) if r['family'] in CHAIN5]
    r = evaluate(model, rows, batch_size, device, lesion, return_preds)
    return {k: r[k] for k in ('exact', 'n', 'by_family') + (('preds',) if return_preds else ())}


def can_donor(model):
    return getattr(model, 'supports_donor', lambda: False)()


def eval_all(model, dev_dir=DEFAULT_DATA, max_per_split=None, lesion=None, batch_size=128, device=None, donor=False):
    """Evaluate the six dev splits -> {split: evaluate(...)}. dev_dir is the data root or its dev/ folder.
    donor=True and a model with state/talk: each split's result also gets 'donor': donor_eval(...) (no lesion applies)."""
    res = {}
    for s in DEV_SPLITS:
        rows = _dev_rows(dev_dir, s, max_per_split)
        res[s] = evaluate(model, rows, batch_size, device, lesion)
        if donor and can_donor(model):
            res[s]['donor'] = donor_eval(model, rows, batch_size, device)
    return res


def donor_all(model, dev_dir=DEFAULT_DATA, max_per_split=None, batch_size=128, device=None):
    """donor_eval on the six dev splits -> {split: donor_eval(...)} (what train.py stores as lesions['donor'])."""
    return {s: donor_eval(model, _dev_rows(dev_dir, s, max_per_split), batch_size, device) for s in DEV_SPLITS}


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
