"""Panel/target steps 3+4a: end-to-end trace of one real course.py-style logic batch on the PARENT checkpoint (forward + backward, NO optimizer step).
Run: PYTHONPATH=<wt/lt> python s2_parent_trace.py     Writes s2_result.json"""
from common import *
import copy

res = {}
model = load_model(PARENT)
model.train()                       # course.py trains in train mode (ans_drill active; no dropout exists)
print('model', type(model).__name__, 'params', model.n_params(), 'ans_drill', model.ans_drill, 'span_copy', model.span_copy, 'w_noop', model.w_noop)
res['cfg'] = dict(n_params=model.n_params(), ans_drill=model.ans_drill, w_noop=model.w_noop, n_loops=model.n_loops, d=model.d)

rows = stride_rows(f'{ROWS}/logic_train.jsonl', 32, total=130000)          # 32 real train rows spread over the file, KEEP keys like course.py
print('rows', len(rows), 'keys', sorted(rows[0]))
random.seed(0)
model._drill_rng = random.Random('ans_drill|1|1')
batch = batch_of(model, rows, strict=True)                               # Dataset(strict) + collate: the real path
ids = batch['prompt_ids']
print('prompt_ids', tuple(ids.shape), 'ans_ids', tuple(batch['ans_ids'].shape), 'UNK count', int((ids == D.UNK).sum()), 'PAD inside mask', int(((ids == D.PAD) & batch['prompt_mask']).sum()))
r0 = rows[0]
print('ROW0 prompt :', r0['prompt'])
print('ROW0 answer :', r0['answer'], '| steps', r0['steps'], '| family', r0['family'], '| stage', r0['stage'])
t0 = pp._targets(r0)
words = [r0['prompt'][s:e] for s, e in word_spans(r0['prompt'])]
print('ROW0 words  :', list(enumerate(words)))
print('ROW0 targets: mode', t0['mode'], 'word positions', t0['word'], '->', [words[i] for i in t0['word']], 'prog', t0['prog'], 'ans', t0['ans'])
print('ROW0 ids head:', ids[0, :12].tolist(), '... decode ->', model.vocab.decode(ids[0].tolist())[:60])
print('ROW0 ans_ids :', batch['ans_ids'][0].tolist(), 'ans_mask', batch['ans_mask'][0].tolist(), '(answer chars are NOT used by the logic loss: mode=WORD -> gen target empty)')
res['row0'] = dict(prompt=r0['prompt'], answer=r0['answer'], words=words, word_targets=list(t0['word']), mode=t0['mode'])

# real loss exactly as logic_transfer/course.py: out = model.loss(batch); loss = out[0]
model.zero_grad(set_to_none=True)
model._drill_rng = random.Random('ans_drill|1|1')
out = model.loss(batch)
total, aux = out
print('\nREAL model.loss total = %.5f' % float(total))
print('aux:', {k: round(float(v), 5) for k, v in aux.items()})
model._drill_rng = random.Random('ans_drill|1|1')
T = terms(model, batch)
print('re-derived terms: lop=%.5f lcall=%.5f lmode=%.5f lword=%.5f span=%s total=%.5f  (matches real total: %s)' % (
    float(T['lop']), float(T['lcall']), float(T['lmode']), float(T['lword']), {k: round(float(v), 5) for k, v in T['span'].items() if k != 'span_share'}, float(T['total']), abs(float(T['total']) - float(total)) < 1e-4))
g = T['g']
print('targets in batch: mode counts', torch.bincount(g['mode'], minlength=3).tolist(), '| rows with op>0 (has program):', int(g['has'].sum()),
      '| gen target slots >=0:', int((g['gen'] >= 0).sum()), '| gold word positions per row (mean): %.2f' % float(g['word'].sum(1).float().mean()),
      '| w_noop weight on these rows:', model.w_noop)
res['real_loss'] = dict(total=float(total), aux={k: float(v) for k, v in aux.items()}, rederived=dict(lop=float(T['lop']), lmode=float(T['lmode']), lword=float(T['lword'])),
                        mode_counts=torch.bincount(g['mode'], minlength=3).tolist(), has_program=int(g['has'].sum()), gen_targets=int((g['gen'] >= 0).sum()))

# gradient reachability: real loss -> backward; per-term too
def grads_of(fn):
    model.zero_grad(set_to_none=True)
    fn().backward()
    return grad_report(model), flat_grad(model).clone()

model._drill_rng = random.Random('ans_drill|1|1')
Tt = terms(model, batch)
gr_total, f_total = grads_of(lambda: Tt['total'])
print('\nGRAD NORMS of the real total loss (gold labels):')
for k, v in gr_total.items():
    print('   %-62s %.5f' % (k, v))
gn = float(f_total.norm())
print('   global grad norm = %.5f  (course.py clips at 1.0)' % gn)
parts = {}
for name in ('lword', 'lmode', 'lop'):
    Tp = terms(model, batch)
    gr, f = grads_of(lambda: Tp[name])
    parts[name] = (gr, f)
    print('\nGRAD NORMS of term %s alone (value %.5f):' % (name, float(Tp[name])))
    for k, v in gr.items():
        print('   %-62s %.5f' % (k, v))
res['grad_norms_total'] = gr_total
res['grad_norms_lword'] = parts['lword'][0]
res['grad_norms_lmode'] = parts['lmode'][0]
res['grad_norms_lop'] = parts['lop'][0]
res['global_grad_norm_total'] = gn

# shuffled labels (uniform random label per row; new ids so the target caches cannot serve old labels)
rng = np.random.RandomState(7)
shuf = [OPTS[i] for i in rng.randint(0, 3, size=len(rows))]
same = sum(a == b for a, b in zip(shuf, [r['answer'] for r in rows]))
rows_s = with_labels(rows, shuf, 'shuf')
batch_s = batch_of(model, rows_s)
model._drill_rng = random.Random('ans_drill|1|1')
Ts = terms(model, batch_s)
print('\nSHUFFLED labels (random label per row, %d/%d coincide with gold): lword=%.5f lmode=%.5f lop=%.5f total=%.5f   | gold: lword=%.5f lmode=%.5f lop=%.5f total=%.5f' % (
    same, len(rows), float(Ts['lword']), float(Ts['lmode']), float(Ts['lop']), float(Ts['total']), float(T['lword']), float(T['lmode']), float(T['lop']), float(T['total'])))
gr_s, f_s = grads_of(lambda: Ts['lword'])
f_g = parts['lword'][1]
cos = float(F.cosine_similarity(f_g, f_s, dim=0))
diff = float((f_g - f_s).norm())
print('lword gradient: |g_gold|=%.4f |g_shuf|=%.4f cos(g_gold,g_shuf)=%.4f |g_gold-g_shuf|=%.4f' % (float(f_g.norm()), float(f_s.norm()), cos, diff))
print('lword grad norms with SHUFFLED labels:', gr_s)
print('label-dependent part of the lword gradient (|g_gold - g_shuf|) by group:')
gm = groups(model)
tmp = {}
off = 0
for n, p in model.named_parameters():
    k = p.numel(); d = (f_g[off:off + k] - f_s[off:off + k]).pow(2).sum().item(); off += k
    tmp[gm[n]] = tmp.get(gm[n], 0.0) + d
res['label_dependent_grad_by_group'] = {k: round(v ** 0.5, 6) for k, v in sorted(tmp.items())}
for k, v in res['label_dependent_grad_by_group'].items():
    print('   %-62s %.5f' % (k, v))
res['shuffled'] = dict(n_same_as_gold=same, lword=float(Ts['lword']), lmode=float(Ts['lmode']), total=float(Ts['total']), cos_lword_grad=cos, grad_diff_norm=diff)

# what does the parent do on these rows? pointer mass and a "uniform over all words" reference
with torch.no_grad():
    o = T['o']
    lp = F.log_softmax(o['lword'].float(), -1)
    sp = [word_spans(r['prompt'])[:64] for r in rows]
    nw = torch.tensor([len(s) for s in sp])
    wl = [[r['prompt'][a:b].lower() for a, b in s] for r, s in zip(rows, sp)]
    mass_opt = []
    for i, w in enumerate(wl):
        suf = [j for j, x in enumerate(w) if x in OPTS][-3:]
        mass_opt.append(float(lp[i, suf].exp().sum()))
    unif = float(torch.tensor([np.log(len(w) / max(1, len(T['g']['word'][i].nonzero()))) for i, w in enumerate(wl)]).mean())
    print('\nPARENT on these 32 logic rows: pointer mass on the 3 suffix option words: mean %.3f (uniform over all words would be %.3f); mean ln(n_words/n_gold) = %.3f; lword = %.3f' % (
        np.mean(mass_opt), float(np.mean([3 / len(w) for w in wl])), unif, float(T['lword'])))
    print('  mode head argmax counts (0 NUM/span,1 WORD,2 GEN):', torch.bincount(o['lmode'].argmax(-1), minlength=3).tolist(), ' op argmax at round1 NOOP frac: %.2f' % float((o['steps'][0][0].argmax(-1) == 0).float().mean()))
res['parent_pointer'] = dict(mass_on_3_option_words_mean=float(np.mean(mass_opt)), uniform_ref=float(np.mean([3 / len(w) for w in wl])), mean_ln_nwords_over_ngold=unif)

# a FRESH random-init model (same cfg, seed 0, never trained): what is the pointer loss at init?
torch.manual_seed(0)
ck = torch.load(PARENT, map_location='cpu', weights_only=True)
fresh = build(ck['name'], CharVocab(ck['chars']), **ck['cfg'])
fresh.train()
fresh._drill_rng = random.Random('x')
Tf = terms(fresh, batch)
print('\nFRESH random-init model on the same 32 rows: lword=%.4f lmode=%.4f lop=%.4f total=%.4f  (ln 3 = %.4f; mean ln(n_words/n_gold)=%.4f; ln 3 NOOP-free)' % (
    float(Tf['lword']), float(Tf['lmode']), float(Tf['lop']), float(Tf['total']), np.log(3), unif))
res['fresh_init'] = dict(lword=float(Tf['lword']), lmode=float(Tf['lmode']), lop=float(Tf['lop']), total=float(Tf['total']))

# parent on 32 SHUFFLED (done above) + a larger parent sample (4 batches of 64) for the "same scale" statement
vals_g, vals_s = [], []
big = stride_rows(f'{ROWS}/logic_train.jsonl', 256, total=130000)
sh = [OPTS[i] for i in np.random.RandomState(8).randint(0, 3, size=256)]
big_s = with_labels(big, sh, 'shufbig')
for k in range(0, 256, 64):
    bg = batch_of(model, big[k:k + 64]); bs_ = batch_of(model, big_s[k:k + 64])
    with torch.no_grad():
        vals_g.append(float(terms(model, bg)['lword'])); vals_s.append(float(terms(model, bs_)['lword']))
print('\nPARENT lword over 256 train rows: gold %.4f (per-64 %s) | shuffled %.4f (per-64 %s)' % (np.mean(vals_g), np.round(vals_g, 3).tolist(), np.mean(vals_s), np.round(vals_s, 3).tolist()))
res['parent_lword_256'] = dict(gold=float(np.mean(vals_g)), shuffled=float(np.mean(vals_s)), gold_batches=vals_g, shuf_batches=vals_s)
json.dump(res, open(os.path.join(OUT, 's2_result.json'), 'w'), indent=1)
