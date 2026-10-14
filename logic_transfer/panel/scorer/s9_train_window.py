"""Train files (first 50,000 rows each, streamed): word-token count vs the 64-token WORD window, and the talker-mode label (NUM/WORD/GEN) the loader's
row_targets assigns. A row whose suffix words fall outside the first 64 word tokens gets mode GEN and can never be answered by the WORD pointer.
  PYTHONPATH=<worktree> python s9_train_window.py -> s9_train_window.json"""
import collections, json
from common import *   # noqa
from custom_io.data import word_spans
from custom_io.models import progparse as pp

R = {}
for name in ('logic_train', 'placebo_train'):
    nt = collections.Counter(); modes = collections.Counter(); nprog = 0; n = 0; mx = 0
    with open(f'{ROWS}/{name}.jsonl') as f:
        for line in f:
            r = json.loads(line)
            n += 1
            k = len(word_spans(r['prompt'])); mx = max(mx, k)
            nt[k > 64] += 1
            t = pp.row_targets({kk: r[kk] for kk in ('id', 'prompt', 'answer', 'accepted', 'family', 'steps')})
            modes[t['mode']] += 1; nprog += bool(t['prog'])
            if n >= 50000: break
    R[name] = dict(n=n, max_word_tokens=mx, rows_over_64=nt[True], mode_counts_NUM0_WORD1_GEN2=[modes[0], modes[1], modes[2]], rows_with_program=nprog)
    pp._CACHE.clear()
wjson('s9_train_window.json', R)
print(json.dumps(R))
