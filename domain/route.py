"""Addendum A22: the model switches its own add-on (Level 2 routing), measured on a finished per-tool add-on run.

  python3 -m domain.route --run RUN_DIR --parent PARENT_CKPT --panel PANEL.jsonl --dev DEV_IN_DIST.jsonl [--threads N]

The switch is a small gate on the model's own reader: the mean of the parent's reader features over the prompt
(the add-on off, so the switch never depends on the add-on), then a logistic unit. The model trains it from its own
records in RUN_DIR/log.jsonl: positives = the prompts it practised with the tool (row events with source own or tool),
negatives = its old questions (row events with source diary). Fixed settings, the same for every domain; no panel or
DEV row is ever used to train it. Then every sealed-panel question and every old-skills question goes to the parent
or to the final checkpoint (add-on on) by the gate's own decision, and DM1 and DM3 are scored on those answers.
Per-row hits come from domain/analyze.py's cache in RUN_DIR/analysis/cache (run domain.analyze first).
Writes RUN_DIR/analysis/ROUTE.json. Never writes elsewhere in RUN_DIR.
"""
import argparse
import json
import os
import random

import torch

from domain import analyze, audit, harm, score
from domain.mode import Dataset, collate, load_model, to_device

GATE = dict(epochs=400, lr=0.01, l2=1e-4, seed=0, threshold=0.5)   # fixed before any routed result


def features(m, prompts, bs=128):
    """Mean of the reader's features over each prompt's letters. -> tensor [N, d]."""
    out = []
    for s in range(0, len(prompts), bs):
        chunk = prompts[s:s + bs]
        ds = Dataset([{'id': f'r{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                      for i, p in enumerate(chunk)], m.vocab, strict=False)
        b = to_device(collate([ds[i] for i in range(len(chunk))]), 'cpu')
        with torch.no_grad():
            X, xm = m.read(b, talker=True)
        w = xm.float()[..., None]
        out.append((X * w).sum(1) / w.sum(1).clamp(min=1))
    return torch.cat(out)


def train_gate(pos, neg):
    """Logistic unit on standardised features, classes weighted to balance. -> function(features) -> bool tensor."""
    g = torch.Generator().manual_seed(GATE['seed'])
    X = torch.cat([pos, neg])
    y = torch.cat([torch.ones(len(pos)), torch.zeros(len(neg))])
    mu, sd = X.mean(0), X.std(0).clamp(min=1e-6)
    Z = (X - mu) / sd
    w = (torch.randn(Z.shape[1], generator=g) * 0.01).requires_grad_(True)
    b0 = torch.zeros(1, requires_grad=True)
    cw = torch.where(y > 0, 0.5 / len(pos), 0.5 / len(neg))
    opt = torch.optim.Adam([w, b0], lr=GATE['lr'])
    for _ in range(GATE['epochs']):
        loss = (torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b0, y, reduction='none') * cw).sum() \
            + GATE['l2'] * (w * w).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        train_acc = (((Z @ w + b0) > 0).float() == y).float().mean().item()
    gate = lambda F: (torch.sigmoid(((F - mu) / sd) @ w.detach() + b0.detach()) > GATE['threshold'])
    gate.state = dict(mu=mu, sd=sd, w=w.detach(), b=b0.detach(), threshold=GATE['threshold'])
    return gate, train_acc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--parent', required=True)
    ap.add_argument('--panel', required=True)
    ap.add_argument('--dev', required=True)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    random.seed(0)
    summary = json.load(open(os.path.join(a.run, 'summary.json')))
    assert summary.get('addon') == 'per_tool', 'routing needs a per-tool add-on run'
    res = json.load(open(os.path.join(a.run, 'analysis', 'RESULT.json')))
    events = [json.loads(l) for l in open(os.path.join(a.run, 'log.jsonl'))]
    rows = [e for e in events if e['event'] == 'row']
    pos = sorted({e['prompt'] for e in rows if e['source'] in ('own', 'tool')})
    neg = sorted({e['prompt'] for e in rows if e['source'] == 'diary'})

    m = load_model(a.parent).eval()   # the parent's reader = the model's reader with the add-on off
    gate, train_acc = train_gate(features(m, pos), features(m, neg))

    cache = os.path.join(a.run, 'analysis', 'cache')
    panel_rows = score.load_panel(a.panel)
    panel_sha = analyze.sha256_file(a.panel)
    dev_rows = analyze.load_rows(a.dev)
    dev_sha = analyze.sha256_file(a.dev)
    fin = res['final_checkpoint']
    p0, _ = analyze.score_one(a.parent, 'parent', panel_rows, panel_sha, cache)
    pN, _ = analyze.score_one(fin, 'final', panel_rows, panel_sha, cache)
    d0, _ = analyze.in_dist_one(a.parent, dev_rows, dev_sha, cache)
    dN, _ = analyze.in_dist_one(fin, dev_rows, dev_sha, cache)

    on_panel = gate(features(m, [r['prompt'] for r in panel_rows])).tolist()
    on_dev = gate(features(m, [r['prompt'] for r in dev_rows])).tolist()
    hit0 = {r['id']: r for r in p0['rows']}
    hitN = {r['id']: r for r in pN['rows']}
    routed = [dict(hitN[r['id']] if on else hit0[r['id']]) for r, on in zip(panel_rows, on_panel)]
    dev_routed = [hN if on else h0 for h0, hN, on in zip(d0['hits'], dN['hits'], on_dev)]

    scored = res['kinds']['scored']
    dropped = set(audit.decontam(panel_rows, {e['prompt'] for e in rows})['ids'])
    near0 = analyze.pooled(p0['rows'], scored, 'near', dropped)
    nearR = analyze.pooled(routed, scored, 'near', dropped)
    far0 = analyze.pooled(p0['rows'], scored, 'far', dropped)
    farR = analyze.pooled(routed, scored, 'far', dropped)
    hm = harm.harm_measure(d0['hits'], dev_routed, dev_rows, family_drop=5.0, in_dist_drop=1.5)
    out = dict(run=a.run, gate=GATE, train=dict(pos=len(pos), neg=len(neg), acc=round(train_acc, 4)),
               routed_on=dict(panel_near=round(sum(o for o, r in zip(on_panel, panel_rows) if r['split'] == 'near')
                                               / max(1, sum(r['split'] == 'near' for r in panel_rows)), 4),
                              panel_far=round(sum(o for o, r in zip(on_panel, panel_rows) if r['split'] == 'far')
                                              / max(1, sum(r['split'] == 'far' for r in panel_rows)), 4),
                              dev=round(sum(on_dev) / len(on_dev), 4), dev_n_on=int(sum(on_dev))),
               DM1=dict(near_parent=near0, near_routed=nearR, gain=round(nearR - near0, 4),
                        verdict='PASS' if nearR - near0 >= 30 else ('PROVED WRONG' if nearR - near0 < 10 else 'FAIL')),
               far=dict(parent=far0, routed=farR),
               DM3=dict(in_dist_parent=round(hm['in_dist_a'], 4), in_dist_routed=round(hm['in_dist_b'], 4),
                        drop=round(hm['in_dist_drop'], 4), fired=hm['fired'], verdict='PASS' if hm['passes'] else
                        ('PROVED WRONG' if hm['in_dist_drop'] > analyze.DM3_PROVED else 'FAIL')))
    path = os.path.join(a.run, 'analysis', 'ROUTE.json')
    with open(path, 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ('train', 'routed_on', 'DM1', 'DM3')}, indent=1))
    print('wrote', path)


if __name__ == '__main__':
    main()
