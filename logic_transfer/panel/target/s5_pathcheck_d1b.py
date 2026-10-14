"""Panel/target steps 3,4,5 on the D1b ckpt-3500 (94% logic, 5000 updates in all): (1) free-run == teacher-forced pointer; (2) train-style batch (mixed with sk200k rows, strict Dataset,
KEEP keys) vs score-style batch (length-sorted, keep=None, strict=False) give the same pointer logits; (3) reproduce the logged loss_mix and its terms; (4) label-dependent gradient;
(5) teacher-forced gold-vs-wrong-label gap by depth. Forward/backward only, no optimizer, nothing saved.
Run: PYTHONPATH=<wt/lt> python s5_pathcheck_d1b.py   -> s5_result.json"""
from common import *
from custom_io.evalx import is_hit
import math, collections
CK = f'{D1B}/checkpoint-3500.pt'
res = {}
model = load_model(CK)
model.eval()

# ---------- (1) free-run vs teacher-forced ----------
rows = stride_rows(f'{ROWS}/eval/logic_dev.jsonl', 128, keep=None)
ds = Dataset(rows, model.vocab, strict=False)
batch = to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')
with torch.no_grad():
    g = model.gold(rows, 'cpu')
    tf = model.run(batch, gold=g)
    fr = model.run(batch)
    valid = tf['wvalid']
    dl = (tf['lword'] - fr['lword']).abs().masked_fill(~valid, 0).max().item()
    dm = (tf['lmode'] - fr['lmode']).abs().max().item()
    n_calls = sum(len(c) for c in fr['calls'])
    noop_all = bool(all((st[0].argmax(-1) == 0).all() for st in fr['steps']))
    gen = model.generate(batch)
    sp = [word_spans(r['prompt'])[:64] for r in rows]
    am = fr['lword'].argmax(-1).tolist()
    dec = [r['prompt'][sp[i][am[i]][0]:sp[i][am[i]][1]] for i, r in enumerate(rows)]
print(f'(1) free-run vs teacher-forced on 128 logic_dev rows: max|d lword|={dl:.2e}  max|d lmode|={dm:.2e}  calculator calls made in free run={n_calls}  all 7 rounds NOOP={noop_all}  generate()==argmax-word decode in {sum(a == b for a, b in zip(gen, dec))}/128')
res['freerun_vs_tf'] = dict(max_abs_dlword=dl, max_abs_dlmode=dm, calls=n_calls, all_noop=noop_all, generate_equals_argmax=sum(a == b for a, b in zip(gen, dec)))

# ---------- (2) train-style vs score-style batch ----------
sk = load_rows(f'{SK200K}/train.jsonl', limit=3000)
logic64 = stride_rows(f'{ROWS}/logic_train.jsonl', 64, total=130000)                # KEEP keys, as course.py
ids_sk = [r['id'] for r in sk]
assert not ({r['id'] for r in logic64} & set(ids_sk))
mix_items = [Dataset(sk, model.vocab, strict=True)[i] for i in range(0, 3000, 750)] + [Dataset(logic64, model.vocab, strict=True)[i] for i in range(60)]   # 4 sk + 60 logic: D1b's mix
tb = to_device(collate(mix_items), 'cpu')
print(f'(2) train-style mixed batch: shape {tuple(tb["prompt_ids"].shape)} (4 sk200k rows + 60 logic rows, padded to the longest), sk prompt lens {[len(r["prompt"]) for r in [sk[0], sk[750], sk[1500], sk[2250]]]}')
with torch.no_grad():
    g1 = model.gold(tb['rows'], 'cpu')
    o_tr = model.run(tb, gold=g1)                         # training path (teacher forced, K = longest gold program)
    logic_rows_full = stride_rows(f'{ROWS}/logic_train.jsonl', 64, keep=None, total=130000)
    order = sorted(range(64), key=lambda i: len(logic_rows_full[i]['prompt']))
    ds2 = Dataset(logic_rows_full, model.vocab, strict=False)
    sb = to_device(collate([ds2[i] for i in order]), 'cpu')   # score.py / evalx.evaluate: length-sorted, keep=None, strict=False
    o_sc = model.run(sb)                                      # free run, as generate()
# compare logic rows 4..63 of the training batch with the same rows in the score batch
pos_sc = {logic_rows_full[i]['id']: k for k, i in enumerate(order)}
diffs, same_ids = [], 0
for j in range(4, 64):
    rid = tb['rows'][j]['id']
    k = pos_sc[rid]
    a = o_tr['lword'][j]; b = o_sc['lword'][k]
    m = o_tr['wvalid'][j] & o_sc['wvalid'][k]
    n_ = int(o_tr['wvalid'][j].sum()); assert n_ == int(o_sc['wvalid'][k].sum())
    diffs.append(float((a - b).abs().masked_fill(~m, 0).max()))
    # the char ids of the same row are identical up to padding
    L = len(tb['rows'][j]['prompt'])
    same_ids += int(torch.equal(tb['prompt_ids'][j, :L], sb['prompt_ids'][k, :L]))
print(f'    same 60 logic rows: char ids identical in {same_ids}/60; max over rows of max|lword_train_path - lword_score_path| = {max(diffs):.2e} (mean {np.mean(diffs):.2e}); padded widths {tb["prompt_ids"].shape[1]} vs {sb["prompt_ids"].shape[1]}')
res['train_vs_score_path'] = dict(char_ids_identical=same_ids, max_abs_dlword=max(diffs), mean_abs_dlword=float(np.mean(diffs)), width_train=int(tb['prompt_ids'].shape[1]), width_score=int(sb['prompt_ids'].shape[1]))

# ---------- (3) reproduce loss_mix (course.py slices: no_grad model.loss on the mix rows, train mode) ----------
model.train()
mixes = stride_rows(f'{ROWS}/logic_train.jsonl', 512, total=130000)[::2]            # 256 train rows
acc = collections.defaultdict(list)
for k in range(0, 256, 64):
    b = batch_of(model, mixes[k:k + 64])
    model._drill_rng = random.Random(f'slice|2|{k}|mix')
    with torch.no_grad():
        tot, aux = model.loss(b)
    acc['total'].append(float(tot)); [acc[kk].append(float(v)) for kk, v in aux.items()]
print('(3) D1b-3500, train mode, 256 train logic rows (4x64), model.loss exactly as course.py slice: total=%.4f  mode=%.4f word=%.4f prog(NOOP terms)=%.4f gen=%.4f span_ans=%.4f stop=%.4f   [logged loss_mix, update 3400-3500 window: 1.0554 / 1.0354]' % (
    np.mean(acc['total']), np.mean(acc['mode']), np.mean(acc['word']), np.mean(acc['prog']), np.mean(acc['gen']), np.mean(acc['span_ans']), np.mean(acc['stop'])))
res['loss_mix_repro'] = {k: float(np.mean(v)) for k, v in acc.items() if k in ('total', 'mode', 'word', 'prog', 'gen', 'span_ans', 'stop', 'span_call')}
dev256 = stride_rows(f'{ROWS}/eval/logic_dev.jsonl', 256, keep=D.KEEP)
accd = collections.defaultdict(list)
for k in range(0, 256, 64):
    b = batch_of(model, dev256[k:k + 64], strict=False)
    with torch.no_grad():
        tot, aux = model.loss(b)
    accd['total'].append(float(tot)); accd['word'].append(float(aux['word'])); accd['mode'].append(float(aux['mode']))
print('    same model on 256 HELD-OUT logic_dev rows: total=%.4f word=%.4f mode=%.4f   (ln 3 = %.4f)' % (np.mean(accd['total']), np.mean(accd['word']), np.mean(accd['mode']), math.log(3)))
res['loss_dev256'] = {k: float(np.mean(v)) for k, v in accd.items()}

# ---------- (4) label-dependent gradient: consistency of the gold-label direction across independent batches ----------
big = stride_rows(f'{ROWS}/logic_train.jsonl', 6 * 64 * 3, total=130000)
big = big[1::3][:6 * 64]                                                          # 384 rows, distinct from (3)
rng = np.random.RandomState(3)
gg, gs = [], []
for k in range(6):
    chunk = big[k * 64:(k + 1) * 64]
    for lab, store in (('gold', gg), ('shuf', gs)):
        rr = chunk if lab == 'gold' else with_labels(chunk, [OPTS[i] for i in rng.randint(0, 3, size=64)], f'shuf{k}')
        model.zero_grad(set_to_none=True)
        T = terms(model, batch_of(model, rr))
        T['lword'].backward()
        store.append(flat_grad(model).clone())
cos = lambda a, b: float(F.cosine_similarity(a, b, dim=0))
gold_gold = [cos(gg[i], gg[j]) for i in range(6) for j in range(i + 1, 6)]
gold_shuf = [cos(gg[i], gs[j]) for i in range(6) for j in range(6) if i != j]
shuf_shuf = [cos(gs[i], gs[j]) for i in range(6) for j in range(i + 1, 6)]
norms = lambda L: float(np.mean([x.norm() for x in L]))
print('(4) D1b-3500 lword gradient over 6 independent 64-row batches: mean|g| gold=%.3f shuf=%.3f | mean cos(gold_i,gold_j)=%+.4f  cos(gold_i,shuf_j)=%+.4f  cos(shuf_i,shuf_j)=%+.4f' % (
    norms(gg), norms(gs), np.mean(gold_gold), np.mean(gold_shuf), np.mean(shuf_shuf)))
gm = groups(model)
model.zero_grad(set_to_none=True)
T = terms(model, batch_of(model, big[:64])); T['lword'].backward()
print('    lword grad norms by group on one gold batch (value %.4f):' % float(T['lword'].detach()), {k: v for k, v in grad_report(model).items() if v > 0})
res['grad_consistency'] = dict(cos_gold_gold=float(np.mean(gold_gold)), cos_gold_shuf=float(np.mean(gold_shuf)), cos_shuf_shuf=float(np.mean(shuf_shuf)), mean_norm_gold=norms(gg), mean_norm_shuf=norms(gs),
                               grad_norm_groups=grad_report(model))
model.zero_grad(set_to_none=True)
model.eval()

# ---------- (5) by-depth teacher-forced gap ----------
@torch.no_grad()
def tf_stats(rows):
    out = []
    ds_ = Dataset(rows, model.vocab, strict=False)
    for s in range(0, len(rows), 64):
        ch = rows[s:s + 64]
        b = to_device(collate([ds_[s + i] for i in range(len(ch))]), 'cpu')
        o = model.run(b, gold=model.gold(ch, 'cpu'))
        p = F.softmax(o['lword'].float(), -1)
        for i, r in enumerate(ch):
            words = [r['prompt'][a:e].lower() for a, e in word_spans(r['prompt'])[:64]]
            pl = np.array([float(sum(p[i, j] for j, w in enumerate(words) if w == L)) for L in OPTS])
            gi = OPTS.index(r['answer'])
            nll = -np.log(pl + 1e-30)
            out.append((str(r['meta'].get('depth')), r['meta'].get('label'), gi, int(np.argmax(pl)), nll[gi], np.delete(nll, gi).mean()))
    return out
by = {}
for fname in ('logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'logic_gate'):
    rows_all = load_rows(f'{ROWS}/eval/{fname}.jsonl', keep=None)
    st = tf_stats(rows_all)
    for dep in sorted({s[0] for s in st}):
        sub = [s for s in st if s[0] == dep]
        n = len(sub); acc3 = np.mean([s[2] == s[3] for s in sub]); d = np.array([s[5] - s[4] for s in sub])
        se = d.std(ddof=1) / math.sqrt(n)
        by[f'{fname}|depth{dep}'] = dict(n=n, acc=float(acc3), gap_wrong_minus_gold=float(d.mean()), se=float(se))
        print(f'(5) {fname:20s} depth {dep}: n={n:4d} acc(argmax over 3 options)={acc3:.3f}  mean[nll(wrong label) - nll(gold)]={d.mean():+.4f} +- {se:.4f}')
    d = np.array([s[5] - s[4] for s in st]); n = len(st)
    by[f'{fname}|ALL'] = dict(n=n, acc=float(np.mean([s[2] == s[3] for s in st])), gap_wrong_minus_gold=float(d.mean()), se=float(d.std(ddof=1) / math.sqrt(n)))
    print(f'    {fname} ALL: n={n} acc={by[fname + "|ALL"]["acc"]:.3f} gap={d.mean():+.4f} +- {by[fname + "|ALL"]["se"]:.4f}')
res['by_depth'] = by
json.dump(res, open(os.path.join(OUT, 's5_result.json'), 'w'), indent=1)
