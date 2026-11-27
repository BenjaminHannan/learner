"""No-training loop probe of saved B2 checkpoints (design/LOOPS-probe.md; gates fixed before it ran).
python3 -m custom_io.probe_loops --ckpt DIR/B2_s100/checkpoint.pt DIR/B2_s101/checkpoint.pt --data BIG_DATA_ROOT --out custom_io/results/40-loops-probe
Per checkpoint: in_dist exact at loops K = 1..16 (M1), settle rounds (M2), late gain (M3), overthinking (M4), controller-token RMS per
iteration (M5); then gates G1-G3, each open only if it opens on every checkpoint. CPU is fine (no training, no GPU)."""
import argparse, collections, json, os
import torch
from custom_io.analyze import NUMBER_FAMS, STRING_FAMS
from custom_io.data import collate, Dataset, load_rows, to_device
from custom_io.evalx import evaluate, is_hit
from custom_io.models import load_model
from custom_io.models import progparse as pp
from custom_io.models.ledger import N_CTRL

KS = list(range(1, 17))


def probe(ck, rows, bs, dev):
    m = load_model(ck, dev)
    assert type(m).__name__ == 'Ledger' and m.n_loops == 8, 'the probe is written for B2 (n_loops 8)'
    L = {r['id']: len(pp.row_targets(r)['prog']) for r in rows}
    hits = {}
    for K in KS:
        p = evaluate(m, rows, bs, dev, None if K == m.n_loops else f'loops:{K}', return_preds=True)['preds']
        hits[K] = {r['id']: is_hit(p[r['id']], r) for r in rows}
    fam = {r['id']: r['family'] for r in rows}
    pct = lambda ids, K: 100 * sum(hits[K][i] for i in ids) / max(len(ids), 1)
    allids = [r['id'] for r in rows]
    by_fam = collections.defaultdict(list)
    for i in allids:
        by_fam[fam[i]].append(i)
    by_len = collections.defaultdict(list)
    for i in allids:
        by_len[L[i]].append(i)
    out = dict(ckpt=ck, n=len(rows))
    out['M1'] = dict(all={K: pct(allids, K) for K in KS}, by_len={l: {K: pct(ids, K) for K in KS} for l, ids in sorted(by_len.items())},
                     n_by_len={l: len(ids) for l, ids in sorted(by_len.items())},
                     by_family={f: {K: pct(ids, K) for K in KS} for f, ids in sorted(by_fam.items())})
    right8 = [i for i in allids if hits[8][i]]
    settle = {}
    for i in right8:
        k = 8
        while k > 1 and hits[k - 1][i]:
            k -= 1
        settle[i] = k
    def settle_stats(ids):
        ids = [i for i in ids if i in settle]
        if not ids:
            return None
        rel = collections.Counter(settle[i] - (L[i] + 1) for i in ids)
        return dict(n=len(ids), mean_settle=sum(settle[i] for i in ids) / len(ids), mean_len_plus1=sum(L[i] + 1 for i in ids) / len(ids),
                    settle_minus_len_plus1=dict(sorted(rel.items())), late_by_more_than_2=100 * sum(settle[i] > L[i] + 3 for i in ids) / len(ids))
    out['M2'] = dict(all=settle_stats(allids), number_fams=settle_stats([i for i in allids if fam[i] in NUMBER_FAMS]),
                     string_fams=settle_stats([i for i in allids if fam[i] in STRING_FAMS]),
                     by_len={l: settle_stats(ids) for l, ids in sorted(by_len.items())})
    wrong8 = [i for i in allids if not hits[8][i]]
    late = [i for i in wrong8 if any(hits[K][i] for K in KS if K > 8)]
    out['M3'] = dict(gain16_by_family={f: pct(ids, 16) - pct(ids, 8) for f, ids in sorted(by_fam.items())}, n_by_family={f: len(ids) for f, ids in sorted(by_fam.items())},
                     wrong_at_8=len(wrong8), right_later=len(late), right_later_pct_of_wrong=100 * len(late) / max(len(wrong8), 1))
    over = [i for i in wrong8 if any(hits[K][i] for K in KS if K < 8)]
    out['M4'] = dict(overthinking=len(over), pct_of_in_dist=100 * len(over) / len(allids),
                     by_family=dict(collections.Counter(fam[i] for i in over).most_common()))
    # M5: RMS of the controller tokens after each iteration (output of the last controller block), loops = 16, 512 rows
    rec = []
    h = m.core[-1].register_forward_hook(lambda mod, inp, o: rec.append((o[:, :N_CTRL].float().pow(2).mean(-1).sqrt().mean().item(),
                                                                         o[:, N_CTRL:].float().pow(2).mean(-1).sqrt().mean().item(), o.shape[0])))
    sub = rows[:: max(1, len(rows) // 512)][:512]
    with torch.no_grad():
        for s in range(0, len(sub), bs):
            rs = sub[s:s + bs]
            b = to_device(collate([Dataset(rs, m.vocab, strict=False)[i] for i in range(len(rs))]), dev)
            m.run(b, loops=16)
    h.remove()
    it = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for j, (c, r_, n) in enumerate(rec):
        t = j % 16
        it[t][0] += c * n; it[t][1] += r_ * n; it[t][2] += n
    out['M5'] = dict(ctrl_rms={t + 1: v[0] / v[2] for t, v in sorted(it.items())}, reg_rms={t + 1: v[1] / v[2] for t, v in sorted(it.items())}, n_rows=len(sub))
    c = out['M5']['ctrl_rms']
    out['M5']['ctrl_growth_8_over_1'] = c[8] / c[1]
    return out


def gates(res):
    def g1(r):
        fam = [f for f, n in r['M3']['n_by_family'].items() if n >= 50 and r['M3']['gain16_by_family'][f] >= 3.0]
        return dict(families=fam, right_later_pct_of_wrong=r['M3']['right_later_pct_of_wrong'], open=bool(fam) or r['M3']['right_later_pct_of_wrong'] >= 5.0)
    def g2(r):
        return dict(overthinking_pct=r['M4']['pct_of_in_dist'], open=r['M4']['pct_of_in_dist'] >= 2.0)
    def g3(r):
        return dict(ctrl_growth_8_over_1=r['M5']['ctrl_growth_8_over_1'], open=r['M5']['ctrl_growth_8_over_1'] >= 10.0)
    G = {}
    for name, fn in (('G1 more loops', g1), ('G2 halting', g2), ('G3 hidden-state growth', g3)):
        per = {os.path.basename(os.path.dirname(r['ckpt'])): fn(r) for r in res}
        G[name] = dict(per_ckpt=per, open=all(v['open'] for v in per.values()))
    return G


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', nargs='+', required=True)
    ap.add_argument('--data', required=True, help='data root whose dev/in_dist.jsonl is probed (the big build: 200 rows per cell)')
    ap.add_argument('--out', default='custom_io/results/40-loops-probe')
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--max-rows', type=int)
    a = ap.parse_args(argv)
    torch.manual_seed(0)
    rows = load_rows(os.path.join(a.data, 'dev', 'in_dist.jsonl'))
    if a.max_rows:
        rows = rows[:: max(1, len(rows) // a.max_rows)][:a.max_rows]
    dev = torch.device('cpu')
    res = [probe(c, rows, a.batch, dev) for c in a.ckpt]
    G = gates(res)
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(results=res, gates=G), open(os.path.join(a.out, 'PROBE.json'), 'w'), indent=1)
    for r in res:
        nm = os.path.basename(os.path.dirname(r['ckpt']))
        print(nm, 'in_dist by K:', {K: round(v, 1) for K, v in r['M1']['all'].items()})
        print('  settle:', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in (r['M2']['all'] or {}).items()})
        print('  numbers vs strings mean settle:', round((r['M2']['number_fams'] or {}).get('mean_settle', 0), 2), round((r['M2']['string_fams'] or {}).get('mean_settle', 0), 2))
        print('  late:', r['M3']['right_later'], 'of', r['M3']['wrong_at_8'], 'overthinking:', r['M4']['overthinking'], 'ctrl rms by iter:', {t: round(v, 1) for t, v in r['M5']['ctrl_rms'].items()})
    print(json.dumps({k: v['open'] for k, v in G.items()}))
    return res, G


if __name__ == '__main__':
    main()
