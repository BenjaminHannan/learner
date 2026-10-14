"""Shared helpers for the panel/target scripts. No optimizer, no saving, 1 thread."""
import json, os, random, re, sys
import numpy as np
import torch
import torch.nn.functional as F
torch.set_num_threads(1)
from custom_io import data as D
from custom_io.data import Dataset, collate, load_rows, to_device, word_spans
from custom_io.models import load_model, build, progparse as pp
from custom_io.data import CharVocab

D.set_max_ans(8)                      # as logic_transfer/course.py does
SCR = '/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
ROWS = f'{SCR}/lt2/rows'
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
D1B = f'{SCR}/lt2/diag/D1b'
SK200K = f'{SCR}/data/sk200k'
OUT = os.path.dirname(os.path.abspath(__file__))
OPTS = ('true', 'false', 'unknown')


def stride_rows(path, n, keep=D.KEEP, total=None):
    """n rows spread evenly over the file (streams the file once; <= n rows held)."""
    if total is None:
        total = sum(1 for _ in open(path))
    want = set(np.linspace(0, total - 1, n).astype(int).tolist())
    out = []
    with open(path) as f:
        for i, line in enumerate(f):
            if i in want:
                r = json.loads(line)
                out.append(r if keep is None else {k: r[k] for k in keep if k in r})
    return out


def batch_of(model, rows, strict=True):
    ds = Dataset(rows, model.vocab, strict=strict)
    return to_device(collate([ds[i] for i in range(len(rows))]), 'cpu')


def terms(model, batch, golds=None):
    """Re-derivation of Tool.loss's terms (same formulas) -> dict of tensors that keep the graph. Used to isolate each term's gradient."""
    B = len(batch['rows'])
    dev = batch['prompt_ids'].device
    if golds is None and model.ans_drill and model.training:
        golds = model.train_golds(batch['rows'])
    g = model.gold(batch['rows'], dev, golds)
    o = model.run(batch, gold=g)
    lop, lcall, hits, tot = model.call_loss(o['steps'], g, B)
    marg = lambda lg, m, sel: torch.where(sel, -(torch.logsumexp(lg.masked_fill(~m, -1e9), -1) - torch.logsumexp(lg, -1)),
                                          torch.zeros_like(lg[:, 0])).sum() / B
    lmode = F.cross_entropy(o['lmode'].float(), g['mode'])
    lword = marg(o['lword'], g['word'], g['mode'] == 1)
    ls = model.span_loss(o, g, batch, B) if model.span_copy else {}
    total = lop + lcall + lmode + lword + (ls['span_call'] + ls['span_ans'] + ls['stop'] if ls else 0.0)
    return dict(lop=lop, lcall=lcall, lmode=lmode, lword=lword, span=ls, total=total, g=g, o=o)


def groups(model):
    """param-name prefix -> group used in the gradient report"""
    def grp(n):
        if n.startswith('reader.'):
            return 'reader(char table,pos,place,2 conv blocks,LN)'
        if n.startswith('core.') or n in ('ctrl.weight', 'step_emb.weight', 'src.weight', 'stype.weight', 'ordinal.weight') or n.startswith('ln_z'):
            return 'thinker(8+9 tokens, core blocks, step/ctrl emb, ln_z)'
        if n.startswith(('q_word', 'k_word', 'len_emb', 'k_wc', 'ln_wc')):
            return 'word-pointer head(q_word,k_word,len_emb,k_wc,ln_wc)'
        if n.startswith('mode_head'):
            return 'mode head'
        if n.startswith('op_head'):
            return 'op head'
        return 'other(' + n.split('.')[0] + ')'
    return {n: grp(n) for n, _ in model.named_parameters()}


def grad_report(model):
    gm = groups(model)
    acc = {}
    for n, p in model.named_parameters():
        g = 0.0 if p.grad is None else float(p.grad.float().pow(2).sum())
        acc[gm[n]] = acc.get(gm[n], 0.0) + g
    return {k: round(v ** 0.5, 6) for k, v in sorted(acc.items())}


def flat_grad(model):
    return torch.cat([(p.grad if p.grad is not None else torch.zeros_like(p)).flatten() for p in model.parameters()])


def with_labels(rows, labels, tag):
    """Copy of rows with the answer replaced; ids get a tag so progparse/Tool target caches (keyed by id) cannot serve the old labels."""
    out = []
    for r, a in zip(rows, labels):
        r2 = dict(r)
        r2['id'] = f'{tag}|{r["id"]}'
        r2['answer'] = a
        r2['accepted'] = [a]
        out.append(r2)
    return out
