"""Panel/target step 4c (rigorous version): is the gold-vs-wrong label gap of D1b-3500 real? Label-permutation null over each slice (robust to unbalanced slices and to any
global label/slot preference of the pointer). Teacher-forced forward only; labels never enter the forward.
Run: PYTHONPATH=<wt/lt> python s6_permutation.py [ckpt_tag]  -> s6_result_<tag>.json"""
from common import *
import math, collections
tag = sys.argv[1] if len(sys.argv) > 1 else 'D1b-3500'
CK = PARENT if tag == 'parent' else (f'{D1B}/checkpoint-{tag.split("-")[1]}.pt' if tag.startswith('D1b') else tag)
model = load_model(CK); model.eval()
PL = {}
@torch.no_grad()
def pl_matrix(rows):
    out = []
    ds = Dataset(rows, model.vocab, strict=False)
    for s in range(0, len(rows), 64):
        ch = rows[s:s + 64]
        b = to_device(collate([ds[s + i] for i in range(len(ch))]), 'cpu')
        o = model.run(b, gold=model.gold(ch, 'cpu'))
        p = F.softmax(o['lword'].float(), -1)
        for i, r in enumerate(ch):
            words = [r['prompt'][a:e].lower() for a, e in word_spans(r['prompt'])[:64]]
            out.append([float(sum(p[i, j] for j, w in enumerate(words) if w == L)) for L in OPTS])
    return np.array(out)
rng = np.random.RandomState(0)
def perm_test(P, gold, nperm=5000):
    n = len(gold)
    nll = -np.log(P + 1e-30)
    obs = nll[np.arange(n), gold].mean()
    obs_acc = (P.argmax(1) == gold).mean()
    nulls, nacc = [], []
    for _ in range(nperm):
        g2 = gold[rng.permutation(n)]
        nulls.append(nll[np.arange(n), g2].mean()); nacc.append((P.argmax(1) == g2).mean())
    nulls, nacc = np.array(nulls), np.array(nacc)
    return dict(n=n, label_share=[float((gold == k).mean()) for k in range(3)], nll_gold=float(obs), nll_null_mean=float(nulls.mean()), nll_gap_null_minus_obs=float(nulls.mean() - obs),
                p_nll=float((nulls <= obs).mean()), acc=float(obs_acc), acc_null_mean=float(nacc.mean()), p_acc=float((nacc >= obs_acc).mean()))
res = {}
for fname in ['logic_gate', 'logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_dev', 'placebo_test_wording']:
    rows = load_rows(f'{ROWS}/eval/{fname}.jsonl', keep=None)
    P = pl_matrix(rows)
    gold = np.array([OPTS.index(r['answer']) for r in rows])
    np.save(os.path.join(OUT, f's6_P_{tag}_{fname}.npy'), P)
    res[fname] = {'ALL': perm_test(P, gold)}
    dep = np.array([str(r['meta'].get('depth')) for r in rows])
    for d in sorted(set(dep)):
        m = dep == d
        if m.sum() >= 100:
            res[fname][f'depth{d}'] = perm_test(P[m], gold[m])
    sm = np.array([str(r['meta'].get('sampler')) for r in rows])
    for d in sorted(set(sm)):
        m = sm == d
        if m.sum() >= 100 and len(set(sm)) > 1:
            res[fname][f'sampler={d}'] = perm_test(P[m], gold[m])
    for k, v in res[fname].items():
        print(f'{tag} {fname:20s} {k:22s} n={v["n"]:5d} labels={[round(x,3) for x in v["label_share"]]} nll_gold={v["nll_gold"]:.4f} null={v["nll_null_mean"]:.4f} (null-obs={v["nll_gap_null_minus_obs"]:+.4f}, perm p={v["p_nll"]:.4f}) acc={v["acc"]:.3f} (null {v["acc_null_mean"]:.3f}, p={v["p_acc"]:.4f})')
json.dump(res, open(os.path.join(OUT, f's6_result_{tag}.json'), 'w'), indent=1)
