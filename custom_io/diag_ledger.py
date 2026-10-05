"""Where design B (ledger) loses rows: per split and family, the gold talker mode (from progparse), the predicted mode,
accuracy, and what each talker path (NUM pointer, WORD copy, GEN registers) would have said. CPU is fine.

  python -m custom_io.diag_ledger --ckpt RUN/checkpoint.pt --data DATA_DIR --out OUT.json [--rows-out ROWS.jsonl]"""
import argparse
import collections
import json
import torch
from custom_io.data import DEV_SPLITS, Dataset, collate, to_device, word_spans
from custom_io.evalx import _dev_rows, is_hit
from custom_io.models import load_model
from custom_io.models import progparse as pp

MODES = ['NUM', 'WORD', 'GEN']


@torch.no_grad()
def paths(model, batch):
    o = model.run(batch)
    R, vals, valid = o['R'], o['vals'].tolist(), o['valid'].tolist()
    gen = [model.vocab.decode(r)[::-1] for r in model.readout(R).argmax(-1).tolist()]
    mode, k, w = o['lmode'].argmax(-1).tolist(), o['lans'].argmax(-1).tolist(), o['lword'].argmax(-1).tolist()
    out = []
    for i, row in enumerate(batch['rows']):
        sp = word_spans(row['prompt'])[:pp.W_MAX]
        num = str(vals[i][k[i]]) if valid[i][k[i]] else None
        word = row['prompt'][sp[w[i]][0]:sp[w[i]][1]] if w[i] < len(sp) else None
        chosen = num if mode[i] == 0 and num is not None else word if mode[i] == 1 and word is not None else gen[i]
        out.append(dict(mode=MODES[mode[i]], num=num, word=word, gen=gen[i], pred=chosen))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rows-out')
    ap.add_argument('--batch', type=int, default=128)
    ap.add_argument('--splits', default=','.join(s for s in DEV_SPLITS if s != 'family'))
    a = ap.parse_args(argv)
    model = load_model(a.ckpt, 'cpu')
    torch.set_grad_enabled(False)
    res, rows_out = {}, []
    for split in a.splits.split(','):
        rows = _dev_rows(a.data, split, None)
        ds = Dataset(rows, model.vocab, strict=False)
        fam = collections.defaultdict(lambda: collections.Counter())
        for s in range(0, len(rows), a.batch):
            idx = list(range(s, min(s + a.batch, len(rows))))
            batch = to_device(collate([ds[i] for i in idx]), 'cpu')
            for i, p in zip(idx, paths(model, batch)):
                r = rows[i]
                g = MODES[pp.row_targets(r)['mode']]
                c = fam[r['family']]
                c['n'] += 1
                c['hit'] += is_hit(p['pred'], r)
                c[f'gold_{g}'] += 1
                c[f'pred_{p["mode"]}'] += 1
                c['mode_ok'] += p['mode'] == g
                for k in ('num', 'word', 'gen'):
                    c[f'{k}_would_hit'] += p[k] is not None and is_hit(p[k], r)
                c['any_path_hits'] += any(p[k] is not None and is_hit(p[k], r) for k in ('num', 'word', 'gen'))
                if a.rows_out and not is_hit(p['pred'], r):
                    rows_out.append(dict(split=split, family=r['family'], prompt=r['prompt'], answer=r['answer'], gold_mode=g, **p))
        res[split] = {f: dict(c) for f, c in sorted(fam.items())}
        tot = sum(c['hit'] for c in fam.values()), sum(c['n'] for c in fam.values())
        print(split, 'exact', round(100 * tot[0] / tot[1], 2), flush=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    if a.rows_out:
        with open(a.rows_out, 'w') as f:
            for r in rows_out:
                f.write(json.dumps(r) + '\n')


if __name__ == '__main__':
    main()
