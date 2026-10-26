"""D0 (PASS-MARKS addendum 16): can B2's reader output be read back as exact digits? No training of B2, CPU, read only.
python3 -m custom_io.diag_d0 --ckpt CK/B2_s200/checkpoint.pt [--copies 8] [--ctl27] [--out custom_io/results/d0/B2_s200.json]
Prompts: the five pooled dev splits, deduplicated, plus `--copies` copies of each prompt with every number replaced by a random 1-9 digit
number (length uniform 1-9, no leading zero, fixed seed; copies over MAX_PROMPT dropped). Split 75/25 by prompt, all copies on one side.
  reading (official): X at the 9 chars ending at a number's last digit, concatenated -> linear probe per place p = 1..9 (digit or none)
           and one for the digit count; scored on held-out prompts, per place only on numbers that have that place.
  read only: the same probes on the real dev numbers of held-out prompts; the digit from its own char's X; from the mean of X over the span.
  --ctl27: eval_all + chain-5 intact and under lesion ctl27 (controls 2-7 zeroed after every controller iteration)."""
import argparse, collections, json, os, random, time
import numpy as np
import torch
from custom_io.analyze import POOL
from custom_io.data import DEFAULT_DATA, MAX_PROMPT, collate, Dataset, load_rows
from custom_io.diag_eg import probe
from custom_io.models import load_model
from custom_io.models.progparse import NUM_RE

W = 9           # places read (units .. 9th)


def prompts(data, copies, seed=0):
    """-> [(prompt, group, kind)]; group = index of the original dev prompt (the split unit), kind 'real' or 'sub'."""
    seen, base = set(), []
    for s in POOL:
        for r in load_rows(os.path.join(data, 'dev', f'{s}.jsonl'), keep=('prompt',)):
            if r['prompt'] not in seen:
                seen.add(r['prompt']); base.append(r['prompt'])
    rng = random.Random(seed)
    rnd = lambda: str(rng.randrange(10 ** (L - 1) if (L := rng.randint(1, W)) > 1 else 0, 10 ** L))
    out = []
    for g, p in enumerate(base):
        out.append((p, g, 'real'))
        for _ in range(copies):
            q = NUM_RE.sub(lambda m: rnd(), p)
            if len(q) <= MAX_PROMPT and q != p:
                out.append((q, g, 'sub'))
    return out, len(base)


@torch.no_grad()
def reader_states(m, ps, bs=128):
    out = []
    for s in range(0, len(ps), bs):
        rs = [{'prompt': p, 'answer': ''} for p in ps[s:s + bs]]
        b = collate([Dataset(rs, m.vocab, strict=False)[i] for i in range(len(rs))])
        X = m.read(b)[0]
        out += [X[k, :len(r['prompt'])].float().numpy() for k, r in enumerate(rs)]
    return out


def features(m, ps, bs=128):
    """Per number of 1..W digits -> dict(win [n, W*d], pool [n, d], digits [n, W] (10 = none), count [n], prompt [n]).
    Reader states are made one chunk of prompts at a time and dropped once the chunk's features are taken."""
    F = collections.defaultdict(list)
    for c in range(0, len(ps), 2048):
        _features(ps[c:c + 2048], reader_states(m, ps[c:c + 2048], bs), c, F)
    F = {k: np.stack(v) for k, v in F.items()}
    F['own'] = F['win'].reshape(len(F['win']), W, -1)
    return F


def _features(ps, X, off, F):
    d = X[0].shape[1]
    for i, p in enumerate(ps, off):
        x = X[i - off]
        for mt in NUM_RE.finditer(p):
            s, e = mt.span()
            if e - s > W:
                continue
            win = np.zeros((W, d), np.float32)        # win[p-1] = X at the char of place p (p = 1 units); zeros before the prompt
            lo = max(0, e - W)
            win[:e - lo] = x[lo:e][::-1]
            dg = np.full(W, 10, np.int64)
            dg[:e - s] = [int(c) for c in mt.group()[::-1]]
            F['win'].append(win.reshape(-1)); F['pool'].append(x[s:e].mean(0))
            F['digits'].append(dg); F['count'].append(e - s - 1); F['prompt'].append(i)


def pc(h):
    return round(100 * float(np.mean(h)), 3) if len(h) else None


def reading(F, groups, kinds, n_groups, steps, seed=0):
    rng = np.random.RandomState(seed)
    test_g = set(rng.permutation(n_groups)[: n_groups // 4].tolist())
    g = np.array([groups[i] for i in F['prompt']])
    kd = np.array([kinds[i] for i in F['prompt']])
    tr = ~np.isin(g, list(test_g))
    te_sub, te_real = ~tr & (kd == 'sub'), ~tr & (kd == 'real')
    res = {'n_numbers': {'train': int(tr.sum()), 'test_sub': int(te_sub.sum()), 'test_real': int(te_real.sum())},
           'n_prompts': {'train': int(sum(x not in test_g for x in groups)), 'test': int(sum(x in test_g for x in groups))}}
    for name, key in (('window', 'win'), ('pool', 'pool')):
        Xf = F[key]
        r = {}
        for p in range(W):
            y = F['digits'][:, p]
            hit = probe(Xf[tr], y[tr], Xf[~tr], y[~tr], 11, steps=steps)
            has = y[~tr] < 10
            r[f'place{p + 1}'] = {'test_sub': pc(hit[(has & te_sub[~tr])]), 'test_real': pc(hit[(has & te_real[~tr])]),
                                  'none_rows_test': pc(hit[~has]), 'n_test_sub': int((has & te_sub[~tr]).sum()),
                                  'n_test_real': int((has & te_real[~tr]).sum())}
            if key == 'win':
                ftr = probe(Xf[tr], y[tr], Xf[tr], y[tr], 11, steps=steps)
                r[f'place{p + 1}']['train_fit'] = pc(ftr[y[tr] < 10])
        hit = probe(Xf[tr], F['count'][tr], Xf[~tr], F['count'][~tr], W, steps=steps)
        r['count'] = {'test_sub': pc(hit[te_sub[~tr]]), 'test_real': pc(hit[te_real[~tr]])}
        res[name] = r
    # own char: one shared 10-way probe over (number, place) pairs that exist
    o = []
    for p in range(W):
        y = F['digits'][:, p]
        k = y < 10
        o.append((F['own'][:, p][k], y[k], tr[k], te_sub[k], te_real[k], p))
    Xo, yo, tro, tso, tre = (np.concatenate([x[i] for x in o]) for i in range(5))
    po = np.concatenate([np.full(len(x[1]), x[5]) for x in o])
    hit = probe(Xo[tro], yo[tro], Xo[~tro], yo[~tro], 10, steps=steps)
    pt, ts, tr_ = po[~tro], tso[~tro], tre[~tro]
    res['own_char'] = {f'place{p + 1}': {'test_sub': pc(hit[(pt == p) & ts]), 'test_real': pc(hit[(pt == p) & tr_])} for p in range(W)}
    vals = [res['window'][f'place{p + 1}']['test_sub'] for p in range(W)] + [res['window']['count']['test_sub']]
    res['mark'] = {'min_place_or_count': min(vals), 'pass': all(v is not None and v >= 99.0 for v in vals)}
    return res


def ctl27(m, data, big, bs):
    from custom_io.evalx import chain_panel, eval_all
    out = {}
    for les in (None, 'ctl27'):
        ev = eval_all(m, data, None, les, bs, torch.device('cpu'))
        c5 = chain_panel(m, big, les, bs, torch.device('cpu'))
        out[les or 'intact'] = {'pooled5': 100 * sum(ev[s]['correct'] for s in POOL) / sum(ev[s]['n'] for s in POOL),
                                'chain5': c5['exact'], **{s: ev[s]['exact'] for s in ev}}
    out['change'] = {k: out['ctl27'][k] - out['intact'][k] for k in out['intact']}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--data', default=DEFAULT_DATA)
    ap.add_argument('--big-data', default=DEFAULT_DATA + '_big')
    ap.add_argument('--copies', type=int, default=8)
    ap.add_argument('--steps', type=int, default=1500)
    ap.add_argument('--ctl27', action='store_true')
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    torch.set_num_threads(os.cpu_count() or 1)
    t0 = time.time()
    m = load_model(a.ckpt)
    rows, n_groups = prompts(a.data, a.copies)
    ps, groups, kinds = zip(*rows)
    F = features(m, list(ps), a.batch)
    res = {'ckpt': a.ckpt, 'copies': a.copies, 'steps': a.steps, 'n_dev_prompts': n_groups, 'n_prompts': len(ps),
           'reading': reading(F, groups, kinds, n_groups, a.steps)}
    del F
    if a.ctl27:
        res['ctl27'] = ctl27(m, a.data, a.big_data, a.batch)
    res['seconds'] = round(time.time() - t0, 1)
    js = json.dumps(res, indent=1)
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        open(a.out, 'w').write(js)
    print(js)


if __name__ == '__main__':
    main()
