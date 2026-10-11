"""D0: can the model guess, before the tool checks it, whether its own answer will be right? (read-only check)

  python3 -m dopamine.d0_guess --run DIR --out OUT.json [--smoke] [--threads 4]

DIR is a domain-mode run folder (log.jsonl, night_K/checkpoint.pt). For day d the model as it was when it tried day d
(the parent for d=1, else night_{d-1}) answers the day's practice prompts greedily (domain.mode.greedy: calculator on, batch
64). In the same pass we keep what it "knew" about each prompt: (a) the reader's mean features (domain.route.features),
(b) the state the talker reads, pooled to one vector, (c) the talker's confidence in its own answer. The model is never
trained. A small logistic guesser V (L2, C=1, standardised on the training days) is fit on days < d and scored on day d.
Baselines: K = per-kind success rate over days < d; C = Platt-calibrated confidence (c).
"""
import argparse
import json
import os
import time
from collections import Counter, defaultdict

import numpy as np
import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from domain.mode import guard

BS = 64


# ---------- features, collected in the same pass as the greedy answers ----------

def talk_conf(m, state, X, xm, batch, modes):
    """(c) mean log-probability of the tokens the talker's greedy answer was read from, per mode (answers() in tool.py:416):
    GEN (mode 2): the 9-register pointer-generator's max prob, over the tokens before the first EOS (ledger.py:239);
    span (mode 0): log softmax of the answer pointer at its argmax (the stop head after the start char is ignored);
    WORD (mode 1): log softmax of the word pointer at its argmax. -> tensor [B]."""
    from custom_io.data import EOS
    R, Xt, idt, vis, lmode, lword = state[:6]
    Xc, mc, idc = torch.cat([X, Xt.to(X.dtype)], 1), torch.cat([xm, vis.bool()], 1), torch.cat([batch['prompt_ids'], idt.long()], 1)
    p, _ = m.gen_copy(R, Xc, mc, idc, False)
    top, ids = p.max(-1)
    lp = top.clamp(min=1e-9).log()
    out = torch.zeros(R.shape[0])
    wl = lword.log_softmax(-1).max(-1)[0]
    if m.span_copy:
        T, le = X.shape[1], Xt.shape[1] // 7
        lg = m.ptr(state[6], m.span_keys(Xc, T, le, mc), mc).masked_fill(~mc, -1e9)
        sp = lg.log_softmax(-1).max(-1)[0]
    for i, md in enumerate(modes):
        if md == 0:
            out[i] = sp[i]
        elif md == 1:
            out[i] = wl[i]
        else:
            row = ids[i].tolist()
            n = row.index(EOS) if EOS in row else len(row)
            out[i] = lp[i, :max(n, 1)].mean()
    return out


def pool_state(state):
    """(b) one vector per prompt: mean of the registers R over the register axis, mean of the tape features Xt over its
    visible positions, the mode logits lmode and word logits lword as they are, and the mean of qn over its axis if present."""
    R, Xt, idt, vis, lmode, lword = state[:6]
    w = vis.float()[..., None]
    parts = [R.mean(1), (Xt * w).sum(1) / w.sum(1).clamp(min=1), lmode, lword]
    if len(state) > 6:
        q = state[6]
        parts.append(q.mean(1) if q.dim() == 3 else q)
    return torch.cat([p.float() for p in parts], 1)


def day_features(m, prompts):
    """Greedy answers plus (a), (b), (c) for each prompt. -> (answers, A [N,da], S [N,ds], conf [N])."""
    m.eval()
    ans, A, S, C = [], [], [], []
    for s in range(0, len(prompts), BS):
        chunk = prompts[s:s + BS]
        ds = Dataset([{'id': f'g{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                      for i, p in enumerate(chunk)], m.vocab, strict=False)
        batch = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
        with torch.no_grad():
            o = m.run(batch)
            state = m.state_of(o)
            a, modes = m.talk(state, batch, return_modes=True)   # identical to greedy(): same run, same talk
            X, xm = m.read(batch, talker=True)                    # as route.features (route.py:34-38)
            w = xm.float()[..., None]
            A.append((X * w).sum(1) / w.sum(1).clamp(min=1))
            S.append(pool_state(state))
            C.append(talk_conf(m, state, X, xm, batch, modes))
        ans += a
    return ans, torch.cat(A).numpy(), torch.cat(S).numpy(), torch.cat(C).numpy()


# ---------- the guesser and the metrics (numpy/torch: sklearn is not installed) ----------

def fit_logistic(X, y, C=1.0):
    """Standardise by the training rows, then L2 logistic regression: min 0.5|w|^2 + C * sum(log loss), intercept free
    (sklearn LogisticRegression(C=1.0) objective), L-BFGS. -> predict(X) -> probabilities."""
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    if y.min() == y.max():
        const = float(y[0])
        return lambda Z: np.full(len(Z), const)
    Z, yt = torch.tensor((X - mu) / sd, dtype=torch.float64), torch.tensor(y, dtype=torch.float64)
    w = torch.zeros(Z.shape[1], dtype=torch.float64, requires_grad=True)
    b = torch.zeros(1, dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], lr=1.0, max_iter=2000, tolerance_grad=1e-7, tolerance_change=1e-10, line_search_fn='strong_wolfe')

    def closure():
        opt.zero_grad()
        loss = 0.5 * (w * w).sum() + C * torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b, yt, reduction='sum')
        loss.backward()
        return loss
    opt.step(closure)
    w, b = w.detach(), b.detach()
    return lambda Q: torch.sigmoid(torch.tensor((Q - mu) / sd, dtype=torch.float64) @ w + b).numpy()


def auc(y, v):
    """Area under the ROC curve by average ranks (ties count half). None when one outcome is missing."""
    y, v = np.asarray(y), np.asarray(v)
    n1, n0 = int(y.sum()), int(len(y) - y.sum())
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(v, kind='mergesort')
    r, sv = np.empty(len(v)), v[order]
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def within_kind_auc(y, v, kind, day, min_each=10):
    """Row-weighted mean over (day, kind) groups with >= min_each rows of each outcome. -> (value or None, groups used, rows used)."""
    tot, n, g = 0.0, 0, 0
    for key in set(zip(day, kind)):
        ix = np.array([i for i in range(len(y)) if (day[i], kind[i]) == key])
        yk = y[ix]
        if yk.sum() >= min_each and len(yk) - yk.sum() >= min_each:
            tot += auc(yk, v[ix]) * len(ix)
            n += len(ix)
            g += 1
    return (tot / n if n else None), g, n


def metrics(y, v, kind, day):
    a = auc(y, v)
    wk, groups, nrows = within_kind_auc(y, v, kind, day)
    return dict(n=len(y), auc=a, within_kind_auc=wk, within_kind_groups=groups, within_kind_rows=nrows,
                brier=float(np.mean((y - v) ** 2)))


def surprise(y, v, kind):
    """For G only: mean |r - V|, the four cells, mean V by outcome, per-kind mean V and success rate."""
    hi = v >= 0.5
    per = {k: dict(n=int((kind == k).sum()), mean_V=float(v[kind == k].mean()), success=float(y[kind == k].mean()))
           for k in sorted(set(kind))}
    return dict(mean_abs_r_minus_V=float(np.abs(y - v).mean()),
                r1_V_ge_half=int(((y == 1) & hi).sum()), r1_V_lt_half=int(((y == 1) & ~hi).sum()),
                r0_V_ge_half=int(((y == 0) & hi).sum()), r0_V_lt_half=int(((y == 0) & ~hi).sum()),
                mean_V_r1=float(v[y == 1].mean()) if (y == 1).any() else None,
                mean_V_r0=float(v[y == 0].mean()) if (y == 0).any() else None, per_kind=per)


# ---------- main ----------

def load_days(run):
    """-> (parent path, {day: [row events]} for practice rows (own/tool), N nights)."""
    ev = [json.loads(l) for l in open(guard(os.path.join(run, 'log.jsonl')))]
    parent = next(e for e in ev if e['event'] == 'start')['parent']
    n = sum(e['event'] == 'night' for e in ev)
    rows = defaultdict(list)
    for e in ev:
        if e['event'] == 'row' and e['source'] in ('own', 'tool'):
            rows[e['day']].append(e)
    return parent, rows, n


def main(argv=None):
    ap = argparse.ArgumentParser(description='D0: can the model guess whether its own answer will be right?')
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--smoke', action='store_true', help='first 128 rows of days 1-3 only')
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    t0 = time.time()
    parent, rows, N = load_days(a.run)
    if a.smoke:
        N = min(N, 3)
        rows = {d: rows[d][:128] for d in range(1, N + 1)}
    D = {}   # day -> dict(y, kind, A, S, c)
    own_wrong = 0
    for d in range(1, N + 1):
        ck = parent if d == 1 else os.path.join(a.run, f'night_{d - 1}', 'checkpoint.pt')
        m = load_model(guard(ck)).eval()
        rs = rows[d]
        ans, A, S, c = day_features(m, [r['prompt'] for r in rs])
        y = np.array([int(x == r['answer']) for x, r in zip(ans, rs)])
        own_wrong += sum(1 for r, yy in zip(rs, y) if r['source'] == 'own' and yy == 0)
        D[d] = dict(y=y, kind=np.array([r['kind'] for r in rs]), A=A, S=S, c=c)
        print(f'day {d}: {len(rs)} rows, greedy right {y.mean():.3f}, features a={A.shape[1]} b={S.shape[1]}', flush=True)

    cat = lambda ds, k: np.concatenate([D[x][k] for x in ds])
    P = {n: defaultdict(list) for n in ('G', 'G_reader', 'K', 'C')}   # name -> {'v','y','kind','day'} pooled over days 2..N
    per_day, surp_day = {}, {}
    for d in range(2, N + 1):
        tr = list(range(1, d))
        ytr, y, kind = cat(tr, 'y'), D[d]['y'], D[d]['kind']
        ktr = cat(tr, 'kind')
        preds = {'G': fit_logistic(np.hstack([cat(tr, 'A'), cat(tr, 'S')]), ytr)(np.hstack([D[d]['A'], D[d]['S']])),
                 'G_reader': fit_logistic(cat(tr, 'A'), ytr)(D[d]['A']),
                 'C': fit_logistic(cat(tr, 'c')[:, None], ytr)(D[d]['c'][:, None])}
        rate = {k: ytr[ktr == k].mean() for k in set(ktr)}
        preds['K'] = np.array([rate.get(k, ytr.mean()) for k in kind])
        per_day[d] = {n: metrics(y, v, kind, np.full(len(y), d)) for n, v in preds.items()}
        surp_day[d] = surprise(y, preds['G'], kind)
        for n, v in preds.items():
            P[n]['v'].append(v), P[n]['y'].append(y), P[n]['kind'].append(kind), P[n]['day'].append(np.full(len(y), d))
    pooled, cat2 = {}, lambda n, k: np.concatenate(P[n][k])
    for n in P:
        pooled[n] = metrics(cat2(n, 'y'), cat2(n, 'v'), cat2(n, 'kind'), cat2(n, 'day'))
    pooled_surprise = surprise(cat2('G', 'y'), cat2('G', 'v'), cat2('G', 'kind'))

    out = dict(run=a.run, smoke=a.smoke, parent=parent, days=N, rows_per_day={d: len(D[d]['y']) for d in D},
               success_per_day={d: float(D[d]['y'].mean()) for d in D}, own_rows_with_r0=own_wrong,
               feature_dims=dict(a_reader=D[1]['A'].shape[1], b_state=D[1]['S'].shape[1], c_confidence=1),
               pooling_b='mean of registers R + masked mean of tape Xt + lmode + lword (+ qn mean) (see pool_state)',
               per_day=per_day, pooled_days_2_to_N=pooled, surprise_G_per_day=surp_day, surprise_G_pooled=pooled_surprise,
               runtime_seconds=round(time.time() - t0, 1))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)

    f4 = lambda x: '  -  ' if x is None else f'{x:.3f}'
    print(f'\nown rows with r=0 (expect 0): {own_wrong}')
    print('pooled days 2..%d   AUC   within-kind AUC   Brier' % N)
    for n in P:
        r = pooled[n]
        print(f'  {n:9s}      {f4(r["auc"])}   {f4(r["within_kind_auc"])} ({r["within_kind_groups"]} groups)   {f4(r["brier"])}')
    s = pooled_surprise
    print(f'G surprise {s["mean_abs_r_minus_V"]:.3f}; cells r1&V>=.5 {s["r1_V_ge_half"]}, r1&V<.5 {s["r1_V_lt_half"]}, '
          f'r0&V>=.5 {s["r0_V_ge_half"]}, r0&V<.5 {s["r0_V_lt_half"]}; mean V r1 {f4(s["mean_V_r1"])} r0 {f4(s["mean_V_r0"])}')
    print('per day AUC (G / G_reader / K / C):')
    for d in per_day:
        print(f'  day {d}: ' + ' / '.join(f4(per_day[d][n]['auc']) for n in ('G', 'G_reader', 'K', 'C')))
    print(f'runtime {out["runtime_seconds"]}s  wrote {a.out}')


if __name__ == '__main__':
    main()
