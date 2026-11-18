"""Build + cache a 'pairs' split: DEV passages that carry >=2 short-answer questions with different gold spans (2 rows per passage)."""
import sys, collections, os
sys.path.insert(0, '.'); sys.path.insert(0, 'diag')
import common as C, prep_states as P
sp = C.build_splits()
by = collections.defaultdict(list)
for r in sp['dev']:
    if r['type'] == 'short_answer':
        m = C.make_row(r)
        if m['gold_words'] is not None:
            by[m['passage']].append(m)
rows = []
for p in sorted(by, key=lambda p: C._sha('pairs' + p)):
    ms = by[p]
    pick = None
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            if ms[i]['gold_words'] != ms[j]['gold_words'] and ms[i]['question'] != ms[j]['question']:
                pick = (ms[i], ms[j]); break
        if pick: break
    if pick: rows += list(pick)
    if len(rows) >= 800: break
print('passages with pairs', len(rows) // 2, 'of', len(by))
out = '/Users/ben-hannan/talker_gap_cache/pairs'; os.makedirs(out, exist_ok=True)
eg = P.load_eg()
P.write_split(eg, 'pairs', rows, out)
print('cached', len(rows))
