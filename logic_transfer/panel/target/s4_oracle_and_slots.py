"""Panel/target step 2c + 5: (a) the positions the LOSS rewards == the positions the DECODER/SCORER counts as a hit (oracle pointer test, real Tool.answers + evalx.is_hit),
(b) option-slot order vs label independence in the options suffix (chi2), (c) answer-case / tokenisation edge cases.
Run: PYTHONPATH=<wt/lt> python s4_oracle_and_slots.py    -> s4_result.json"""
from common import *
from custom_io.evalx import is_hit, norm
import collections, math

model = load_model(PARENT)
files = {n: (f'{ROWS}/eval/{n}.jsonl', 1, None) for n in ['logic_gate', 'logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_dev', 'placebo_test_wording']}
files['train_logic(every6th)'] = (f'{ROWS}/logic_train.jsonl', 6, 20000)
files['train_placebo(every6th)'] = (f'{ROWS}/placebo_train.jsonl', 6, 20000)
SUF = re.compile(r' \((true|false|unknown)/(true|false|unknown)/(true|false|unknown)\)$')
res = {}
for name, (path, stride, cap) in files.items():
    rows = []
    for i, l in enumerate(open(path)):
        if i % stride:
            continue
        r = json.loads(l)
        rows.append({k: r[k] for k in D.KEEP if k in r})
        if cap and len(rows) >= cap:
            break
    n = len(rows)
    agree = disagree = 0
    hits_at_gold = tot_gold = 0
    hits_at_other_opt = tot_other_opt = 0
    max_hit_positions = 0
    pad_hits = 0
    # slot x label
    ct = np.zeros((3, 3), int)       # rows: gold label (true,false,unknown); cols: slot (0,1,2) of the gold word inside the suffix
    for r in rows:
        sp = word_spans(r['prompt'])[:pp.W_MAX]
        t = pp._targets(r)
        gold_set = set(t['word'])
        # decode every candidate position with the real answers()
        texts, _ = model.answers([[]] * (len(sp) + 2), [1] * (len(sp) + 2), list(range(len(sp) + 2)), [r] * (len(sp) + 2))
        hit_pos = {j for j, tx in enumerate(texts[:len(sp)]) if is_hit(tx, r)}
        pad_hits += sum(is_hit(tx, r) for tx in texts[len(sp):])           # positions >= n_words fall back to GEN text of [] -> '' (must be a miss)
        if hit_pos == gold_set:
            agree += 1
        else:
            disagree += 1
        tot_gold += len(gold_set); hits_at_gold += len(hit_pos & gold_set)
        max_hit_positions = max(max_hit_positions, len(hit_pos))
        # the wrong option words in the suffix are decoded as misses
        words = [r['prompt'][a:b].lower() for a, b in sp]
        suf = [j for j, w in enumerate(words) if w in OPTS][-3:]
        for j in suf:
            if words[j] != r['answer']:
                tot_other_opt += 1; hits_at_other_opt += j in hit_pos
        ct[OPTS.index(r['answer']), [words[j] for j in suf].index(r['answer'])] += 1
    exp = ct.sum(1, keepdims=True) * ct.sum(0, keepdims=True) / ct.sum()
    chi2 = float(((ct - exp) ** 2 / exp).sum())
    res[name] = dict(n=n, loss_positions_equal_scorer_hit_positions=agree, mismatch=disagree, gold_positions=tot_gold, wrong_option_words_scored_as_hit=hits_at_other_opt,
                     wrong_option_words_total=tot_other_opt, positions_past_end_scored_as_hit=pad_hits, slot_by_label_counts=ct.tolist(), slot_label_chi2_df4=chi2)
    print(f'{name:26s} n={n:6d} loss-target positions == scorer-hit positions in {agree}/{n} rows (mismatch {disagree}); wrong suffix option words scored as hit: {hits_at_other_opt}/{tot_other_opt}; '
          f'past-end hits {pad_hits}; slot x label chi2(df4)={chi2:.2f}  table(rows=true/false/unknown, cols=slot0/1/2)={ct.tolist()}')
json.dump(res, open(os.path.join(OUT, 's4_result.json'), 'w'), indent=1)
