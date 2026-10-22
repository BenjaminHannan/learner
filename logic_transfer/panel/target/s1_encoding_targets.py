"""Panel/target step 1+2: character encoding and pointer-target audit of logic / placebo rows.
Run: PYTHONPATH=<wt/lt> python s1_encoding_targets.py   (pure python + torch.load of the checkpoint's 'chars' only; no model)
Streams the six eval files in full and a stride sample (<=20000 rows, every 6th line) of each 130k train file.
Writes s1_result.json next to this script.
"""
import json, os, re, sys, collections
import torch
from custom_io.data import CharVocab, word_spans, MAX_PROMPT, UNK, load_rows
from custom_io.models import progparse as pp

OUT = os.path.dirname(os.path.abspath(__file__))
CK = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
ROWS = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
chars = torch.load(CK, map_location='cpu', weights_only=True)['chars']
vocab = CharVocab(chars)
SUF = re.compile(r' \((true|false|unknown)/(true|false|unknown)/(true|false|unknown)\)$')
WORDS = ('true', 'false', 'unknown')

files = {f'eval/{n}': f'{ROWS}/eval/{n}.jsonl' for n in
         ['logic_gate', 'logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_dev', 'placebo_test_wording']}
files['train/logic(every6th,<=20k)'] = f'{ROWS}/logic_train.jsonl'
files['train/placebo(every6th,<=20k)'] = f'{ROWS}/placebo_train.jsonl'


def stream(path, stride=1, cap=None):
    n = 0
    with open(path) as f:
        for i, line in enumerate(f):
            if i % stride:
                continue
            yield json.loads(line)
            n += 1
            if cap and n >= cap:
                return


def audit(rows):
    c = collections.Counter()
    nw_hist = collections.Counter()
    len_hist = collections.Counter()
    nacc_hist = collections.Counter()
    early_by_label = collections.Counter()
    pat = collections.Counter()
    for r in rows:
        p, a = r['prompt'], r['answer']
        c['n'] += 1
        enc = vocab.encode(p)
        c['unk_prompt_chars'] += enc.count(UNK)
        c['rows_with_unk'] += UNK in enc or UNK in vocab.encode(a)
        c['len_gt_208'] += len(p) > MAX_PROMPT
        c['len_eq_208'] += len(p) == MAX_PROMPT
        c['len_ge_200'] += len(p) >= 200
        len_hist[len(p) // 10 * 10] += 1
        m = SUF.search(p)
        c['has_suffix'] += bool(m)
        sp = word_spans(p)
        nw = len(sp)
        nw_hist[nw] += 1
        c['nwords_gt_64'] += nw > pp.W_MAX
        words = [p[s:e].lower() for s, e in sp]
        # position of the three suffix option words among the word list
        if m:
            tail = [i for i, w in enumerate(words) if w in WORDS][-3:]
            c['suffix_words_all_in_first64'] += all(i < pp.W_MAX for i in tail)
            c['suffix_words_separate_tokens'] += (words[-7:] == ['(', words[-6], '/', words[-4], '/', words[-2], ')'])
            sufpos = [len(words) - 6, len(words) - 4, len(words) - 2]
            gold_suffix_pos = [q for q in sufpos if words[q] == a]
            c['gold_in_suffix_exactly_once'] += len(gold_suffix_pos) == 1
        t = pp._targets(r)                      # fresh, not cached
        c[f'mode_{t["mode"]}'] += 1
        wt = t['word']
        nacc_hist[len(wt)] += 1
        # positions of gold word before the suffix
        pre = [i for i in wt if i < len(words) - 7]
        c['gold_also_before_suffix'] += bool(pre)
        early_by_label[(a, bool(pre))] += 1
        # any of the 3 words anywhere before suffix
        before = [w for w in words[:len(words) - 7] if w in WORDS]
        c['any_option_word_before_suffix'] += bool(before)
        c['all_three_before_suffix'] += len(set(before)) == 3
        # distinct patterns of where a prior option word appears (context immediately before it)
        for i, w in enumerate(words[:len(words) - 7]):
            if w in WORDS:
                ctx = ' '.join(words[max(0, i - 2):i]) + ' _ ' + ' '.join(words[i + 1:i + 3])
                pat[ctx] += 1
        c['gold_positions_total'] += len(wt)
        c['word_set_not_just_one_suffix_pos'] += len(wt) != 1
        # gold word text vs. word set
        c['accepted_is_single_answer'] += r['accepted'] == [a]
        # steps / stage / family
        c['steps_none'] += r['steps'] == ['none']
    return c, nw_hist, len_hist, nacc_hist, early_by_label, pat


res = {}
for name, path in files.items():
    stride, cap = (6, 20000) if name.startswith('train/') else (1, None)
    c, nwh, lh, nah, ebl, pat = audit(stream(path, stride, cap))
    n = c['n']
    d = dict(c)
    d['max_words'] = max(nwh)
    d['mean_words'] = round(sum(k * v for k, v in nwh.items()) / n, 2)
    d['nacc_hist'] = {str(k): v for k, v in sorted(nah.items())}
    d['gold_also_before_suffix_by_label'] = {f'{k[0]}|{k[1]}': v for k, v in sorted(ebl.items())}
    d['top_prior_option_word_contexts'] = pat.most_common(12)
    d['len_hist_10'] = {str(k): v for k, v in sorted(lh.items())}
    res[name] = d
    print(f'{name:34s} n={n:6d} unkrows={c["rows_with_unk"]} len>208={c["len_gt_208"]} len==208={c["len_eq_208"]} '
          f'words>64={c["nwords_gt_64"]} maxw={d["max_words"]} suffix={c["has_suffix"]} sep_tokens={c["suffix_words_separate_tokens"]} '
          f'in64={c["suffix_words_all_in_first64"]} modes(0/1/2)={c["mode_0"]}/{c["mode_1"]}/{c["mode_2"]} '
          f'gold_before_suffix={c["gold_also_before_suffix"]} ({100*c["gold_also_before_suffix"]/n:.1f}%) '
          f'anyopt_before={100*c["any_option_word_before_suffix"]/n:.1f}% nacc={d["nacc_hist"]}')
json.dump(res, open(os.path.join(OUT, 's1_result.json'), 'w'), indent=1)
