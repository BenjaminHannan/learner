"""python3 -m mainbrain.test_kfnorm : check kf.kfac_stats(norm=...) (one thread, 128 diary rows)."""
import torch

from custom_io.models import load_model
from mainbrain import common, kf

torch.set_num_threads(1)
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUN = '/mnt/project-files/main-brain/runs/sheet-s200-kf97'
BASE = '/tmp/claude-0/-home-user-learner/f940b6ca-364b-5210-9e75-665a78bcdc5c/scratchpad/base_stats.pt'   # A, G from kf.py before the edit


def main():
    m = load_model(PARENT)
    rows = common.run_rows(RUN)[0][:128]
    s0 = kf.kfac_stats(m, rows)
    s1 = kf.kfac_stats(m, rows, bs=1, norm='example')
    base = torch.load(BASE)
    for n, (A, G) in base.items():   # (a) norm=None is today's code
        assert torch.equal(A, s0[n][0]) and torch.equal(G, s0[n][1]), ('(a) differs', n)
    print('(a) norm=None identical to pre-edit A and G on', len(base), 'modules')
    # (b) expected = number of (example, call) output-gradient blocks that are nonzero. A module the model calls several times
    # per example (a shared loop body) contributes one unit block per call, so for those the count exceeds the example count.
    cnt, calls, hs = {}, {}, []
    for n, mod in kf.gp.projected_modules(m):
        def fh(mod, inp, out, n=n):
            if out.requires_grad:
                calls[n] = calls.get(n, 0) + 1
                out.register_hook(lambda g, n=n: cnt.__setitem__(n, cnt.get(n, 0) + int((g.flatten(1).abs().sum(1) > 0).sum())))
        hs.append(mod.register_forward_hook(fh))
    kf.kfac_stats(m, rows, bs=1, norm='example')
    for h in hs:
        h.remove()
    worst = 0.0
    for n, (A, G) in s1.items():
        t, e = float(G.trace()), cnt[n]
        worst = max(worst, abs(t - e) / e)
        assert abs(t - e) <= 1e-3 * e, ('(b)', n, t, e)
    multi = sum(1 for n in calls if calls[n] > len(rows))
    print('(b) trace(G) == nonzero-block count on all %d modules, max rel dev %.2e; %d modules are called more than once per example'
          % (len(s1), worst, multi))
    # (c) same batching for both (bs=1): A must be identical. (bs=64 vs bs=1 differ already for norm=None, since the model's
    # padded positions are not all zero after the first layers, so the batch composition changes A. Not caused by norm.)
    s0b = kf.kfac_stats(m, rows, bs=1)
    assert all(torch.equal(A, s0b[n][0]) for n, (A, _) in s1.items()), '(c) A differs'
    print('(c) A identical between norm=None and norm=example at bs=1; bs=64 vs bs=1 max rel dev of A (pre-existing): %.1e' % max(
        float((A - s0[n][0]).abs().max() / s0[n][0].abs().max()) for n, (A, _) in s1.items()))
    for tag, s in (('empirical', s0), ('example', s1)):   # (d)
        F, info = kf.factors(s, 0.97)
        fs = [v['free_share'] for v in info.values()]
        print('(d) %s: %d layers, mean free_share %.4f' % (tag, len(fs), sum(fs) / len(fs)))


if __name__ == '__main__':
    main()
