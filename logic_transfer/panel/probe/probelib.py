"""Shared helpers for the probe dimension (inference only).

Decode = the scorer's decode: model.run(batch) -> model.state_of -> model.talk(..., return_modes=True), which is exactly
Tool.generate() (= evalx.evaluate's predictor).  Run python with PYTHONPATH=<worktree lt>.
"""
import json, math, os, pickle, random, re, sys
import numpy as np
import torch

torch.set_num_threads(1)
from custom_io import data as D

D.set_max_ans(8)
from custom_io.data import Dataset, collate, load_rows, to_device, word_spans
from custom_io.models import load_model

SP = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
ROWS = f'{SP}/lt2/rows'
OUT = f'{SP}/panel/probe'
OPT = ('true', 'false', 'unknown')
SUF = re.compile(r' \((\w+)/(\w+)/(\w+)\)$')
W_MAX = 64


def suffix_of(prompt):
    m = SUF.search(prompt)
    return list(m.groups()) if m else None


def tokens(prompt):
    return [prompt[a:b].lower() for a, b in word_spans(prompt)][:W_MAX]


def slot_of_index(prompt, idx):
    """Which suffix slot (0,1,2) the pointer index idx is: 'q' = another option word in the question text, 'o' = anything else."""
    sp = word_spans(prompt)
    n = len(sp)
    if idx >= n:
        return 'o'
    # suffix tokens are the last 7: ( w / w / w )
    for s, k in enumerate((n - 6, n - 4, n - 2)):
        if idx == k:
            return s
    w = prompt[sp[idx][0]:sp[idx][1]].lower()
    return 'q' if w in OPT else 'o'


@torch.no_grad()
def forward(model, rows, bs=64):
    """-> dict of aligned arrays: pred (list[str] raw decode), mode, lword [N,64] (fp32, masked -1e9), lmode [N,3], ncalls (rows with any op>0)."""
    n = len(rows)
    order = sorted(range(n), key=lambda i: len(rows[i]['prompt']))
    ds = Dataset(rows, model.vocab, strict=False)
    pred = [None] * n
    mode = np.zeros(n, np.int64)
    lw = np.zeros((n, W_MAX), np.float32)
    lm = np.zeros((n, 3), np.float32)
    nc = np.zeros(n, np.int64)
    for s in range(0, n, bs):
        ids = order[s:s + bs]
        b = to_device(collate([ds[i] for i in ids]), torch.device('cpu'))
        o = model.run(b)
        st = model.state_of(o)
        ans, modes = model.talk(st, b, return_modes=True)
        calls = sum((x[0].argmax(-1) > 0).long() for x in o['steps'])
        for k, i in enumerate(ids):
            pred[i], mode[i] = ans[k], modes[k]
        lw[ids] = st[5].float().numpy()
        lm[ids] = st[4].float().numpy()
        nc[ids] = calls.numpy()
    return dict(pred=pred, mode=mode, lword=lw, lmode=lm, ncalls=nc)


def norm(s):
    return ' '.join(s.strip().lower().split())


def lse(x, axis=-1):
    m = np.max(x, axis=axis, keepdims=True)
    return (m + np.log(np.exp(x - m).sum(axis=axis, keepdims=True))).squeeze(axis)


def option_logmass(lword, prompts):
    """-> [N,3] log pointer mass on each option word type (sum over every occurrence among the first 64 tokens, order OPT),
    and [N] log mass on all non-option tokens.  Same marginal as Tool.loss's `lword` term."""
    N = len(prompts)
    out = np.full((N, 3), -np.inf)
    oth = np.full(N, -np.inf)
    for i, p in enumerate(prompts):
        t = tokens(p)
        lz = lse(lword[i].astype(np.float64))
        ar = np.arange(len(t))
        for k, w in enumerate(OPT):
            idx = [j for j, x in enumerate(t) if x == w]
            if idx:
                out[i, k] = lse(lword[i, idx].astype(np.float64)) - lz
        idx = [j for j, x in enumerate(t) if x not in OPT]
        if idx:
            oth[i] = lse(lword[i, idx].astype(np.float64)) - lz
    return out, oth


# ---------------------------------------------------------------------- information measures
def mi_bits(a, b):
    """Plug-in mutual information (bits) of two integer-coded 1-D arrays."""
    a, b = np.asarray(a), np.asarray(b)
    ua, ia = np.unique(a, return_inverse=True)
    ub, ib = np.unique(b, return_inverse=True)
    j = np.zeros((len(ua), len(ub)))
    np.add.at(j, (ia, ib), 1)
    j /= j.sum()
    pa, pb = j.sum(1, keepdims=True), j.sum(0, keepdims=True)
    nz = j > 0
    return float((j[nz] * np.log2(j[nz] / (pa @ pb)[nz])).sum())


def mi_report(a, b, nboot=1000, nperm=1000, seed=0):
    """plug-in MI, bootstrap 95% CI over rows, permutation-null mean and 95th percentile (shuffle b), excess = MI - null mean."""
    rng = np.random.RandomState(seed)
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    obs = mi_bits(a, b)
    bs = [mi_bits(a[i], b[i]) for i in (rng.randint(0, n, n) for _ in range(nboot))]
    nl = [mi_bits(a, b[rng.permutation(n)]) for _ in range(nperm)]
    return dict(mi=round(obs, 5), ci95=[round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)],
                null_mean=round(float(np.mean(nl)), 5), null_p95=round(float(np.percentile(nl, 95)), 5),
                excess=round(obs - float(np.mean(nl)), 5), p_perm=round(float((np.sum(np.array(nl) >= obs) + 1) / (nperm + 1)), 4), n=n)


def boot_ci(x, nboot=2000, seed=0, fn=np.mean):
    rng = np.random.RandomState(seed)
    x = np.asarray(x, float)
    n = len(x)
    v = [fn(x[rng.randint(0, n, n)]) for _ in range(nboot)]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
