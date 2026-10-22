"""Item 5: recompute the training-slice loss at D1b-3500 through the real batch path (Dataset -> collate -> model.loss), compare with log.jsonl.
python item5.py TAG   (TAG = D1b3500 only needs the slice rows; other sets are measured too)."""
import pickle, sys, time, json
sys.path.insert(0, '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe')
from probelib import *
from run_probe import CK

def batch_losses(m, rows, bs):
    ds = Dataset(rows, m.vocab)            # strict, as in training
    outs = []
    for s in range(0, len(rows) - bs + 1, bs):
        b = to_device(collate([ds[i] for i in range(s, s + bs)]), torch.device('cpu'))
        with torch.no_grad():
            L, aux = m.loss(b)
        outs.append((float(L), float(aux['word']), float(aux['mode']), float(aux['prog'])))
    a = np.array(outs)
    return dict(n_batches=len(outs), n_rows=len(outs) * bs, loss=float(a[:, 0].mean()), loss_sd_over_batches=float(a[:, 0].std(ddof=1)) if len(a) > 1 else None,
                word=float(a[:, 1].mean()), mode=float(a[:, 2].mean()), prog=float(a[:, 3].mean()), per_batch=[round(x, 4) for x in a[:, 0]])

def main(tag):
    C = pickle.load(open(f'{OUT}/conds.pkl', 'rb'))
    m = load_model(CK[tag], 'cpu')
    m.eval()
    res = {'ln3': math.log(3)}
    sl = C['slice_D1b3500']
    # (a) exactly the logged slices: 20 slices (updates 3405..3500 step 5) of 60 mix rows, one model.loss call per slice (what course.py logged)
    per = [batch_losses(m, sl[i * 60:(i + 1) * 60], 60) for i in range(20)]
    res['logged_slices_20x60'] = dict(mean_loss=float(np.mean([p['loss'] for p in per])), mean_word=float(np.mean([p['word'] for p in per])),
                                      per_slice=[round(p['loss'], 4) for p in per])
    # (b) 640 rows of those slice rows in batches of 64
    res['slice_rows_640_bs64'] = batch_losses(m, sl[:640], 64)
    # (c) other sets, batches of 60 (the mix-slice size), 600 rows
    for name in ('tr_D1b3500_k1', 'tr_D1b3500_k2', 'tr_D1b3500_k3', 'dev600', 'gate600', 'plac600'):
        res[name] = batch_losses(m, C[name], 60)
    logs = [json.loads(l) for l in open(f'{SP}/lt2/diag/D1b/log.jsonl')]
    res['log_loss_mix'] = {r['update']: r['loss_mix'] for r in logs if r['update'] >= 3000}
    json.dump(res, open(f'{OUT}/res/item5_{tag}.json', 'w'), indent=1)
    print(json.dumps({k: (v['loss'] if 'loss' in v else v.get('mean_loss')) for k, v in res.items() if isinstance(v, dict) and ('loss' in v or 'mean_loss' in v)}))

if __name__ == '__main__':
    main(sys.argv[1])
