import sys, numpy as np
from collections import defaultdict
d = sys.argv[1]
Z = dict(np.load(d + '/cache.npz'))
ptr, cpid, ckind, cw = Z['cand_ptr'], Z['cand_pid'], Z['cand_kind'], Z['cand_wanted']
right = Z['correct'][cpid] == 1
R = len(Z['round_sess']); ridx = Z['round_idx']
split = Z['sess_split'][Z['round_sess']]
L = Z['sess_L']
curk = np.full(R, -1)
for r in range(R):
    for c in range(ptr[r], ptr[r+1]):
        if cpid[c] == Z['round_cur'][r]: curk[r] = ckind[c]
# fit counts on training rounds
nw = defaultdict(lambda: [0, 0]); nr = defaultdict(lambda: [0, 0])
for r in np.where(split == 0)[0]:
    for c in range(ptr[r], ptr[r+1]):
        key = (curk[r], ckind[c], ridx[r]); nw[key][0] += cw[c]; nw[key][1] += 1
        nr[ckind[c]][0] += right[c]; nr[ckind[c]][1] += 1
save = defaultdict(float); acts = 0
for r in np.where(split == 1)[0]:
    best, bc = 0.0, None
    for c in range(ptr[r], ptr[r+1]):
        a, b = nw[(curk[r], ckind[c], ridx[r])]; pw = a / b if b else 0
        a2, b2 = nr[ckind[c]]; pr = a2 / b2 if b2 else 0
        ev = pw * (2 * pr - 1) - (1 - pw) * 0.25
        if ev > best: best, bc = ev, c
    if bc is not None:
        acts += 1
        save[Z['round_sess'][r]] += (1.0 if right[bc] else -1.0) if cw[bc] else -0.25
S = (Z['sess_split'] == 1).sum()
print(d, 'kind-level calibrated helper: saving per session %.3f, extras per session %.3f' % (sum(save.values()) / S, acts / S))
