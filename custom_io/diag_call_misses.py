"""Amendment 8's 'miss breakdown first' for an R4 call-accuracy miss, read only, CPU fp32: the call-accuracy rows of Tool.extra_evals
(subsample of the big dev set's program rows, 400), teacher-forced and free run, every wrong call listed with the gold and written strings,
which side was wrong, the gate's path (span or cells) and where the gold operand comes from (prompt number, constant, earlier result).
python3 -m custom_io.diag_call_misses --ck CK [--ck CK2 ...] --big-data DIR --out OUT.json"""
import argparse, collections, json, os
import torch
from custom_io.data import collate, Dataset, load_rows, to_device
from custom_io.evalx import subsample
from custom_io.models import load_model, progparse as pp
from custom_io.models.tool import COMM, R0


@torch.no_grad()
def misses(m, rows, bs=100):
    out, n = dict(teacher_forced=[], free_run=[]), dict(teacher_forced=0, free_run=0)
    for s0 in range(0, len(rows), bs):
        part = rows[s0:s0 + bs]
        b = to_device(collate([Dataset(part, m.vocab, strict=False)[i] for i in range(len(part))]), torch.device('cpu'))
        g = m.gold(b['rows'], 'cpu')
        for mode, gd in (('teacher_forced', g), ('free_run', None)):
            o = m.run(b, gold=gd)
            for s, st in enumerate(o['steps']):
                op, wr = st[0].argmax(-1), m.written(st)
                for i, r in enumerate(b['rows']):
                    ops, opd = m.row_gold(r)[:2]
                    if s >= len(ops):
                        continue
                    n[mode] += 1
                    sa, sb = opd[s]
                    good_op = int(op[i]) == ops[s]
                    good = good_op and (wr[i] == (sa, sb) or (ops[s] in COMM and wr[i] == (sb, sa)))
                    if good:
                        continue
                    prog = pp.row_targets(r)['prog'][s]
                    src = ['result' if c[0] >= R0 else 'const' if c[0] >= pp.N_NUM else 'prompt' for c in (prog[1], prog[2])]
                    sp = st[2] if len(st) > 2 else None
                    out[mode].append(dict(id=r['id'], family=r['family'], step=s, n_steps=len(ops), op_ok=good_op, gold=(sa, sb), got=list(wr[i]),
                                          sides_wrong=[k for k, (x, y) in enumerate(zip((sa, sb), wr[i])) if x != y], gold_src=src,
                                          span=None if sp is None else [bool(sp['ga'][i] >= 0), bool(sp['gb'][i] >= 0)]))
    return out, n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ck', nargs='+', required=True)
    ap.add_argument('--big-data', required=True)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    rows = load_rows(os.path.join(a.big_data, 'dev', 'in_dist.jsonl'))
    sl = subsample([r for r in rows if pp.row_targets(r)['prog']], 400)
    res = {}
    for ck in a.ck:
        m = load_model(ck, 'cpu')
        ms, n = misses(m, sl)
        summ = {}
        for mode, xs in ms.items():
            kinds = collections.Counter(('op' if not x['op_ok'] else 'operand ' + '+'.join('ab'[k] for k in x['sides_wrong']) or 'order')
                                        + ' / gold from ' + ','.join(x['gold_src'][k] for k in (x['sides_wrong'] or [0, 1])) for x in xs)
            summ[mode] = dict(n_calls=n[mode], wrong=len(xs), call_acc=round(100 * (1 - len(xs) / max(n[mode], 1)), 2), kinds=dict(kinds.most_common()),
                              families=dict(collections.Counter(x['family'] for x in xs).most_common()))
        res[os.path.basename(os.path.dirname(ck))] = dict(checkpoint=ck, summary=summ, misses=ms)
        print(json.dumps({os.path.basename(os.path.dirname(ck)): summ}), flush=True)
    json.dump(dict(n_rows=len(sl), device='cpu fp32', results=res), open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
