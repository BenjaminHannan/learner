"""Panel/target step 1 (full): scan ALL 260,000 train rows + all 7,608 eval rows (streamed, one row in memory at a time): UNK, >208 chars, >64 words, suffix inside the first 64 words,
target mode, id uniqueness and id clash with sk200k, family/stage/steps fields.  Run: PYTHONPATH=<wt/lt> python s1c_full_scan.py -> s1c_result.json"""
import json, os, re, collections, torch
from custom_io.data import CharVocab, word_spans, MAX_PROMPT, UNK
from custom_io.models import progparse as pp
OUT = os.path.dirname(os.path.abspath(__file__))
ck = torch.load('/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt', map_location='cpu', weights_only=True)
vocab = CharVocab(ck['chars'])
ROWS = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
SK = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/data/sk200k/train.jsonl'
files = [f'{ROWS}/eval/{n}.jsonl' for n in ['logic_gate', 'logic_dev', 'logic_test_sampler', 'logic_test_deeper', 'placebo_dev', 'placebo_test_wording']] + [f'{ROWS}/logic_train.jsonl', f'{ROWS}/placebo_train.jsonl']
SUF = re.compile(r' \((true|false|unknown)/(true|false|unknown)/(true|false|unknown)\)$')
sk_ids = {json.loads(l)['id'] for l in open(SK)}
ids = set(); res = {}
tot = collections.Counter()
for p in files:
    c = collections.Counter(); mx_w = 0; mx_len = 0
    for l in open(p):
        r = json.loads(l)
        pr = r['prompt']
        c['n'] += 1
        c['unk'] += UNK in vocab.encode(pr) or UNK in vocab.encode(r['answer'])
        c['len>208'] += len(pr) > MAX_PROMPT; mx_len = max(mx_len, len(pr))
        sp = word_spans(pr); mx_w = max(mx_w, len(sp)); c['words>64'] += len(sp) > 64
        m = SUF.search(pr); c['suffix'] += bool(m)
        c['digits_in_prompt'] += any(ch.isdigit() for ch in pr)
        t = pp._targets(r)
        c[f'mode{t["mode"]}'] += 1; c['prog'] += bool(t['prog'])
        c['dup_id'] += r['id'] in ids; ids.add(r['id'])
        c['clash_sk200k'] += r['id'] in sk_ids
        c['bad_fields'] += not (r['steps'] == ['none'] and r['stage'] == 9 and r['family'] in ('logic_fc', 'logic_placebo') and r['accepted'] == [r['answer']])
        c['answer_not_option'] += r['answer'] not in ('true', 'false', 'unknown')
    res[os.path.basename(p)] = dict(c, max_words=mx_w, max_len=mx_len)
    print(os.path.basename(p), dict(c), 'max_words', mx_w, 'max_len', mx_len)
json.dump(res, open(os.path.join(OUT, 's1c_result.json'), 'w'), indent=1)
