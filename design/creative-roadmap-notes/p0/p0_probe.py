"""P0: sampled candidates from B2 (ledger copy=True), scored with the answer key. CPU only, no training.

Run from the B2 worktree root (the dir that holds custom_io/):
  python p0_probe.py --ckpt .../B2_s100/checkpoint.pt --data .../sk200k --out p0_B2_s100.json
Spec: PROBE-SPEC.md (written before any sampled run).
The sampled forward pass is a copy of Ledger.run / Ledger.talk (custom_io/models/ledger.py:186-279) with argmax replaced
by sampling at the marked lines; nothing else changes.
"""
import argparse, json, math, os, sys, time
from collections import Counter
import numpy as np
import torch
import torch.nn.functional as F

from custom_io.data import collate, Dataset, to_device, word_spans
from custom_io.evalx import evaluate, is_hit, norm, _dev_rows
from custom_io.models import load_model
from custom_io.models import ledger as L
from custom_io.models import progparse as pp

N_CTRL, N_REG, N_RES, R0, ADD, SUB = L.N_CTRL, L.N_REG, L.N_RES, L.R0, L.ADD, L.SUB
SPLIT_OFF = {'heldout': 0, 'frame_wrong': 1, 'vocab_wrong': 2}


def samp(logits, T, g):
    """sample one index per row from softmax(logits / T); masked entries (-1e9) keep probability 0."""
    p = (logits.float() / T).softmax(-1)
    return torch.multinomial(p, 1, generator=g)[:, 0]


@torch.no_grad()
def run_sampled(m, batch, T, g, sample_mode=False, sample_gen=False):
    """Ledger.run (ledger.py:186-250) with op / a / b sampled (was argmax, ledger.py:227), then Ledger.talk (260-279) with the
    answer and word pointers sampled (were argmax, 269); mode (all-heads only) and GEN chars (all-heads only) sampled too.
    -> (outputs list[str], info dict of per-row tensors/lists)."""
    X, xm = m.reader(batch)
    ns, ne, nv, ws, we = m.tokenize(batch)
    B, Tn, dev = X.shape[0], X.shape[1], X.device
    t_ix = torch.arange(Tn, device=dev)
    inn = (t_ix >= ns[..., None]) & (t_ix < ne[..., None])
    cnt = inn.sum(-1)
    pool = torch.bmm(inn.to(X.dtype), X) / cnt.clamp(min=1)[..., None]
    consts = torch.tensor(pp.CONSTS, device=dev).expand(B, -1)
    vals = torch.cat([nv, consts, torch.zeros(B, N_RES, dtype=torch.long, device=dev)], 1)
    valid = torch.cat([cnt > 0, torch.ones_like(consts, dtype=torch.bool), torch.zeros(B, N_RES, dtype=torch.bool, device=dev)], 1)
    S0 = m.vcode(L.value_code(vals[:, :R0], valid[:, :R0])) * valid[:, :R0, None]
    S0 = torch.cat([S0[:, :L.N_NUM] + pool + m.ordinal.weight + m.stype.weight[0], S0[:, L.N_NUM:] + m.stype.weight[1]], 1)
    S0 = S0 * valid[:, :R0, None]
    Rs = torch.zeros(B, N_RES, m.d, device=dev, dtype=S0.dtype)
    Kw, wvalid = m.word_keys(ws, we), we > ws
    if m.copy:
        Kw = Kw + m.word_content(X, ws, we)
    kvx = [b.kv_of(X + m.src.weight[1]) for b in m.core]
    P = m.reader.place.weight[:N_REG]
    Z = torch.cat([m.ctrl.weight, P]).expand(B, -1, -1)
    ops, As, Bs, oks = [], [], [], []
    for t in range(m.n_loops):
        ts = min(t, m.n_loops - 1)
        S = torch.cat([S0, Rs], 1)
        kvs = [b.kv_of(S + m.src.weight[0]) for b in m.core]
        mask = torch.cat([valid, xm], 1)
        Z = Z + m.step_emb.weight[ts]
        for b, kx, ks in zip(m.core, kvx, kvs):
            Z = b(Z, ks, kx, mask)
        if not 1 <= t <= N_RES:
            continue
        z = m.ln_z(Z[:, 0])
        ks_ = m.k_slot(m.ln_k(torch.cat([S0, Rs], 1)))
        lop, la, lb = m.op_head(z), m.ptr(m.q_a(z), ks_, valid), m.ptr(m.q_b(z), ks_, valid)
        op, a, b = samp(lop, T, g), samp(la, T, g), samp(lb, T, g)          # SAMPLED (was argmax, ledger.py:227)
        v, ok = L.execute(op, vals.gather(1, a[:, None])[:, 0], vals.gather(1, b[:, None])[:, 0])
        vals, valid = vals.clone(), valid.clone()
        vals[:, R0 + t - 1], valid[:, R0 + t - 1] = v, ok
        new = (m.vcode(L.value_code(v, ok)) + m.stype.weight[2] + m.op_emb(op) + m.step_emb.weight[ts] + m.res_from_z(z)) * ok[:, None]
        Rs = torch.cat([Rs[:, :t - 1], new[:, None].to(Rs.dtype), Rs[:, t:]], 1)
        ops.append(op); As.append(a); Bs.append(b); oks.append(ok)
    zf = m.ln_z(Z[:, 1])
    ks_ = m.k_slot(m.ln_k(torch.cat([S0, Rs], 1)))
    R, lmode = Z[:, N_CTRL:], m.mode_head(zf)
    lans, lword = m.ptr(m.q_ans(zf), ks_, valid), m.ptr(m.q_word(zf), Kw, wvalid)
    # ---- talker (ledger.py:260-279) ----
    p, _ = m.gen_copy(R, X, xm, batch['prompt_ids'])
    if sample_gen:                                                           # all-heads: GEN chars sampled from p^(1/T)
        q = (p.clamp_min(1e-12).log() / T).softmax(-1)
        ids = torch.multinomial(q.flatten(0, 1), 1, generator=g)[:, 0].view(B, -1)
    else:
        ids = p.argmax(-1)
    gen = [m.vocab.decode(r)[::-1] for r in ids.tolist()]
    mode = (samp(lmode, T, g) if sample_mode else lmode.argmax(-1)).tolist()
    k, w = samp(lans, T, g).tolist(), samp(lword, T, g).tolist()          # SAMPLED (were argmax, ledger.py:269)
    vl, vd, out, path_ok = vals.tolist(), valid.tolist(), [], []
    for i, row in enumerate(batch['rows']):
        sp = word_spans(row['prompt'])[:L.W_MAX]
        if mode[i] == 0 and vd[i][k[i]]:
            out.append(str(vl[i][k[i]])); path_ok.append(True)
        elif mode[i] == 1 and w[i] < len(sp):
            out.append(row['prompt'][sp[w[i]][0]:sp[w[i]][1]]); path_ok.append(True)
        else:
            out.append(gen[i]); path_ok.append(mode[i] == 2)
    op_t, ok_t = torch.stack(ops, 1), torch.stack(oks, 1)
    steps_ok = ((op_t == 0) | ok_t).all(1).tolist()
    any_op = (op_t != 0).any(1).tolist()
    prog = [tuple(x) for x in torch.stack([op_t, torch.stack(As, 1), torch.stack(Bs, 1)], 2).flatten(1).tolist()]
    return out, dict(mode=mode, path_ok=path_ok, steps_ok=steps_ok, any_op=any_op, prog=prog)


@torch.no_grad()
def greedy_info(m, batch):
    """greedy outputs (= m.generate) plus the greedy program and mode, from Ledger.run."""
    o = m.run(batch)
    outs = m.generate(batch)
    ops, a, b = o['prog']
    prog = [tuple(x) for x in torch.stack([ops, a, b], 2)[:, :N_RES].flatten(1).tolist()]
    return outs, dict(mode=o['lmode'].argmax(-1).tolist(), prog=prog)


def pass_at_k(n, c, k):
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def batches_of(m, rows, size):
    for s in range(0, len(rows), size):
        rs = rows[s:s + size]
        yield rs, collate([Dataset(rs, m.vocab, strict=False)[i] for i in range(len(rs))])


def probe(m, rows, N, temps, seed, variant, rows_per_batch=8):
    """-> per-row records: greedy output/hit/mode, and per temperature the 32 outputs, hits, programs, flags."""
    recs = {r['id']: dict(id=r['id'], family=r['family'], answer=r['answer'], samples={}) for r in rows}
    for rs, b in batches_of(m, rows, 64):
        outs, gi = greedy_info(m, b)
        for i, r in enumerate(rs):
            recs[r['id']].update(greedy=outs[i], greedy_hit=int(is_hit(outs[i], r)), greedy_mode=gi['mode'][i], greedy_prog=gi['prog'][i])
    for ti, T in enumerate(temps):
        g = torch.Generator().manual_seed(seed + 1000 * ti)
        for rs, _ in batches_of(m, rows, rows_per_batch):
            rep = [r for r in rs for _ in range(N)]                 # each row N times in one batch
            b = collate([Dataset(rep, m.vocab, strict=False)[i] for i in range(len(rep))])
            outs, info = run_sampled(m, b, T, g, sample_mode=(variant == 'all'), sample_gen=(variant == 'all'))
            for j, r in enumerate(rs):
                sl = slice(j * N, (j + 1) * N)
                recs[r['id']]['samples'][str(T)] = dict(
                    outs=outs[sl], hits=[int(is_hit(x, r)) for x in outs[sl]], mode=info['mode'][sl],
                    wellformed=[int(a and c) for a, c in zip(info['steps_ok'][sl], info['path_ok'][sl])],
                    any_op=[int(x) for x in info['any_op'][sl]], prog=info['prog'][sl])
    return list(recs.values())


def summarise(recs, temps, N):
    out = {}
    fams = sorted({r['family'] for r in recs})
    for scope in ['ALL'] + fams:
        rs = [r for r in recs if scope == 'ALL' or r['family'] == scope]
        n = len(rs)
        s = dict(n=n, greedy_pass1=100 * sum(r['greedy_hit'] for r in rs) / n,
                 greedy_mode=dict(Counter(['NUM', 'WORD', 'GEN'][r['greedy_mode']] for r in rs)))
        for T in temps:
            k = str(T)
            cs = [sum(r['samples'][k]['hits']) for r in rs]
            dist_ans = [len({norm(x) for x in r['samples'][k]['outs']}) for r in rs]
            dist_prog = [len(set(map(tuple, r['samples'][k]['prog']))) for r in rs]
            diff_greedy = [np.mean([norm(x) != norm(r['greedy']) for x in r['samples'][k]['outs']]) for r in rs]
            prog_diff = [np.mean([tuple(p) != tuple(r['greedy_prog']) for p in r['samples'][k]['prog']]) for r in rs]
            s[k] = dict(
                pass1=100 * np.mean([pass_at_k(N, c, 1) for c in cs]),
                pass8=100 * np.mean([pass_at_k(N, c, 8) for c in cs]),
                pass32=100 * np.mean([pass_at_k(N, c, 32) for c in cs]),
                greedy_or_any=100 * np.mean([max(r['greedy_hit'], int(c > 0)) for r, c in zip(rs, cs)]),
                rows_with_hit=int(sum(c > 0 for c in cs)), mean_hits_per_row_with_hit=float(np.mean([c for c in cs if c > 0])) if any(cs) else 0.0,
                distinct_answers=dict(mean=float(np.mean(dist_ans)), median=float(np.median(dist_ans)), max=int(max(dist_ans))),
                distinct_programs=dict(mean=float(np.mean(dist_prog)), median=float(np.median(dist_prog))),
                answer_differs_from_greedy=100 * float(np.mean(diff_greedy)),
                program_differs_from_greedy=100 * float(np.mean(prog_diff)),
                wellformed=100 * float(np.mean([np.mean(r['samples'][k]['wellformed']) for r in rs])),
                any_op=100 * float(np.mean([np.mean(r['samples'][k]['any_op']) for r in rs])),
                mode_share={nm: 100 * float(np.mean([np.mean([md == i for md in r['samples'][k]['mode']]) for r in rs])) for i, nm in enumerate(['NUM', 'WORD', 'GEN'])})
        out[scope] = s
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--N', type=int, default=32)
    ap.add_argument('--temps', default='0.7,1.0,1.5')
    ap.add_argument('--seed', type=int, default=20261006)
    ap.add_argument('--variants', default='prog')
    ap.add_argument('--splits', default='heldout,frame_wrong,vocab_wrong')
    a = ap.parse_args()
    torch.set_num_threads(4)
    temps = [float(x) for x in a.temps.split(',')]
    m = load_model(a.ckpt)
    assert m.copy, 'expects B2 (copy=True)'
    res = dict(ckpt=a.ckpt, N=a.N, temps=temps, seed=a.seed, torch=torch.__version__, splits={})
    for split in a.splits.split(','):
        t0 = time.time()
        if split == 'heldout':
            rows = _dev_rows(a.data, 'family', None)
        else:
            src = split.split('_')[0]
            allr = _dev_rows(a.data, src, None)
            ev = evaluate(m, allr, 128, 'cpu', return_preds=True)
            rows = [r for r in allr if not is_hit(ev['preds'][r['id']], r)]
            res.setdefault('greedy_full', {})[src] = dict(exact=ev['exact'], n=ev['n'], n_wrong=len(rows))
        for vi, variant in enumerate(a.variants.split(',')):
            recs = probe(m, rows, a.N, temps, a.seed + 100 * vi + 10 * SPLIT_OFF[split], variant)
            key = f'{split}/{variant}'
            res['splits'][key] = dict(summary=summarise(recs, temps, a.N), secs=time.time() - t0)
            res.setdefault('records', {})[key] = recs
            print(json.dumps(dict(split=key, n=len(rows), secs=round(time.time() - t0, 1),
                                  ALL={k: (v if not isinstance(v, dict) else {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()})
                                       for k, v in res['splits'][key]['summary']['ALL'].items()})), flush=True)
    json.dump(res, open(a.out, 'w'))


if __name__ == '__main__':
    main()
