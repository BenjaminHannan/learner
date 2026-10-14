"""Panel/target step 4b/4c/5: teacher-forced answer loss, gold vs wrong labels, on trained checkpoints; free-run == teacher-forced; padding/batch invariance;
loss_mix reproduction. NO optimizer, nothing saved.
Run: PYTHONPATH=<wt/lt> python s3_teacher_forced.py [ckpt_tag ...]   (default tags: D1b-3500 first; extras via argv)   -> s3_result.json (merged)"""
from common import *
import math, collections

CKPTS = {
    'parent': PARENT,
    'D1b-500': f'{D1B}/checkpoint-500.pt', 'D1b-1500': f'{D1B}/checkpoint-1500.pt', 'D1b-2500': f'{D1B}/checkpoint-2500.pt', 'D1b-3500': f'{D1B}/checkpoint-3500.pt',
    'L-s1-1000': f'{SCR}/lt2/jobs/course-s200-L-s1/out/checkpoint-1000.pt', 'P-s1-1000': f'{SCR}/lt2/jobs/course-s200-P-s1/out/checkpoint-1000.pt',
}
tags = sys.argv[1:] or ['D1b-3500']
resf = os.path.join(OUT, 's3_result.json')
RES = json.load(open(resf)) if os.path.exists(resf) else {}


@torch.no_grad()
def label_probs(model, rows, bs=50):
    """Teacher-forced forward (the training path model.run(batch, gold=g)); returns per-row dict. Labels never enter the forward."""
    model.eval()
    ds = Dataset(rows, model.vocab, strict=False)
    out = []
    for s in range(0, len(rows), bs):
        chunk = rows[s:s + bs]
        batch = to_device(collate([ds[s + i] for i in range(len(chunk))]), 'cpu')
        g = model.gold(chunk, 'cpu')
        o = model.run(batch, gold=g)
        lp = F.log_softmax(o['lword'].float(), -1)
        pm = F.softmax(o['lmode'].float(), -1)
        for i, r in enumerate(chunk):
            sp = word_spans(r['prompt'])[:64]
            words = [r['prompt'][a:b].lower() for a, b in sp]
            p = lp[i].exp()
            pl = {L: float(sum(p[j] for j, w in enumerate(words) if w == L)) for L in OPTS}
            suf = [j for j, w in enumerate(words) if w in OPTS][-3:]               # the 3 suffix option slots, in text order
            slot_words = [words[j] for j in suf]
            slot_p = [float(p[j]) for j in suf]
            am = int(p.argmax())
            out.append(dict(id=r['id'], gold=r['answer'], pl=pl, slot_words=slot_words, slot_p=slot_p, argmax_word=words[am] if am < len(words) else None,
                            argmax_in_suffix=am in suf, mode_probs=pm[i].tolist(), mode_arg=int(pm[i].argmax()), lword_gold=float(-torch.log(torch.tensor(pl[r['answer']] + 1e-30)))))
    return out


def summarize(out, name):
    n = len(out)
    gold = np.array([OPTS.index(o['gold']) for o in out])
    P = np.array([[o['pl'][L] for L in OPTS] for o in out])               # mass on each label's words (all positions)
    mass = P.sum(1)
    Q = P / np.maximum(mass[:, None], 1e-30)                                # renormalised over the 3 labels
    nll_gold = -np.log(P[np.arange(n), gold] + 1e-30)
    wrong = np.stack([-np.log(P[np.arange(n), (gold + k) % 3] + 1e-30) for k in (1, 2)], 1)   # the two wrong labels
    nll_wrong = wrong.mean(1)                                               # expected NLL under a uniformly-random wrong label
    d = nll_wrong - nll_gold                                                # >0 means gold label is better supported
    rng = np.random.RandomState(0)
    boots = [d[rng.randint(0, n, n)].mean() for _ in range(2000)]
    # normalised 3-way cross-entropy (removes the 'how much mass is on option words' part)
    ce3 = -np.log(Q[np.arange(n), gold] + 1e-30)
    acc3 = float((Q.argmax(1) == gold).mean())
    acc_decode = float(np.mean([(o['argmax_word'] == o['gold']) for o in out]))
    conf = np.zeros((3, 3), int)
    for g_, q in zip(gold, Q.argmax(1)):
        conf[g_, q] += 1
    # slot bias: which suffix slot (0,1,2) holds the argmax among the 3 suffix words
    slot = collections.Counter(int(np.argmax(o['slot_p'])) for o in out)
    # chi2 independence of predicted vs gold
    exp = conf.sum(1, keepdims=True) * conf.sum(0, keepdims=True) / conf.sum()
    chi2 = float(((conf - exp) ** 2 / np.maximum(exp, 1e-9)).sum())
    # sign test on d
    k = int((d > 0).sum()); m = int((d != 0).sum())
    from math import comb
    pval = sum(comb(m, i) for i in range(k, m + 1)) / 2 ** m if k > m / 2 else 1.0
    r = dict(n=n, mass_on_option_words=float(mass.mean()), mass_min=float(mass.min()), lword_gold=float(nll_gold.mean()), lword_wrong_label=float(nll_wrong.mean()),
             gold_minus_wrong=float(-d.mean()), boot95=[float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], rows_gold_better=k, rows_nonzero=m,
             sign_test_p_one_sided=float(pval), ce3_gold=float(ce3.mean()), ln3=math.log(3), acc3_argmax_over_options=acc3,
             acc_decode_argmax_word=acc_decode, confusion_gold_by_pred_true_false_unknown=conf.tolist(), chi2_pred_vs_gold_df4=chi2,
             pred_label_share=Q.argmax(1).tolist().count(0) / n, argmax_slot_counts=dict(slot), mode_argmax=dict(collections.Counter(o['mode_arg'] for o in out)),
             mean_p_gold_over_options=float(Q[np.arange(n), gold].mean()), argmax_in_suffix=float(np.mean([o['argmax_in_suffix'] for o in out])))
    print(f'  [{name}] n={n} mass_on_option_words={r["mass_on_option_words"]:.3f} lword gold={r["lword_gold"]:.4f} wrong-label={r["lword_wrong_label"]:.4f} '
          f'(gold-wrong={r["gold_minus_wrong"]:+.4f}, 95%CI of wrong-gold [{r["boot95"][0]:+.4f},{r["boot95"][1]:+.4f}], gold better in {k}/{m} rows, sign p={pval:.3f}) '
          f'3-way CE={r["ce3_gold"]:.4f} (ln3={math.log(3):.4f}) acc3={acc3:.3f} decode-acc={acc_decode:.3f} chi2={chi2:.1f} slots={dict(slot)} modes={r["mode_argmax"]}')
    print('     confusion (rows=gold true/false/unknown, cols=pred):', conf.tolist())
    return r


for tag in tags:
    print(f'\n===== {tag} =====')
    model = load_model(CKPTS[tag])
    res = {}
    for fname, key in (('logic_dev', 'logic_dev500'), ('placebo_dev', 'placebo_dev500'), ('logic_test_sampler', 'logic_test_sampler500')):
        rows = stride_rows(f'{ROWS}/eval/{fname}.jsonl', 500 if fname != 'logic_dev' else 500, keep=None)
        out = label_probs(model, rows)
        res[key] = summarize(out, key)
        if key == 'logic_dev500' and tag.startswith('D1b-3500'):
            json.dump(out, open(os.path.join(OUT, 's3_perrow_D1b3500_logic_dev500.json'), 'w'))
    RES[tag] = res
    del model
    json.dump(RES, open(resf, 'w'), indent=1)
