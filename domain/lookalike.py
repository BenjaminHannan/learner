"""Look-alike test of the model's own add-on switch (domain/LOOKALIKE-MARKS-2026-10-10.md).

  python3 -m domain.lookalike screen --tool stats --parent P --diary-run RUN --old-panel LA.jsonl --dev DEV --panel PANEL --out OUT.json
  python3 -m domain.lookalike score --run RUN --parent P --old-panel LA.jsonl --dev DEV --panel PANEL [--gate v8|F1|F2]

screen (LA0, no model training): the switch exactly as mode.py trains it, from the practice prompts the mode's own maker
makes for --days days at even mix (seed --seed) against the diary prompts of --diary-run (an earlier run with the same
parent, data and seed has the identical diary). Reports its on-rates only.

score --gate all scores a run with no switch (a whole-model run): every question goes to the final checkpoint.

score (LA1-LA3, a finished per-tool add-on run): the switch is trained from RUN/log.jsonl as route.py does (v8), or with
one of the fixes fixed in the marks before any result (F1: risky diary questions, where the model's own answer with the
add-on on differs from its pre-mode answer, get half of the negative weight; F2: mean and max of the reader's features).
Every sealed-panel, DEV and lookalike-old question is then answered by the parent or by the final checkpoint (add-on on),
as the switch decides. Writes OUT_DIR/LOOKALIKE_<gate>.json (OUT_DIR defaults to RUN/analysis; its cache/ starts as a
copy of RUN/analysis/cache, so another thread's run folder is only read). Needs domain.analyze to have run (RESULT.json, cache).
No panel, DEV or lookalike-old row ever trains the switch.
"""
import argparse
import json
import os
import random
import shutil
from collections import Counter

import torch

from custom_io.models import load_model
from domain import analyze, audit, harm, mode, route, score

LA_FAMILY_DROP, LA_POOLED_DROP = 5.0, 1.5          # LA3 pass (marks sec. 4)
LA_PROVED_POOLED, LA_PROVED_VARIANT = 3.0, 10.0    # LA3 proved wrong
LOOKALIKE_FAMILIES = {'stats': ('compare_numbers', 'list_stats'), 'invoice': ('table_calc',)}


def features_mm(m, prompts, bs=128):
    """F2: mean and max of the reader's features over each prompt's letters. -> tensor [N, 2d]."""
    out = []
    for s in range(0, len(prompts), bs):
        chunk = prompts[s:s + bs]
        ds = mode.Dataset([{'id': f'r{i}', 'prompt': p, 'answer': '', 'accepted': [], 'family': '', 'level': 0}
                           for i, p in enumerate(chunk)], m.vocab, strict=False)
        b = mode.to_device(mode.collate([ds[i] for i in range(len(chunk))]), 'cpu')
        with torch.no_grad():
            X, xm = m.read(b, talker=True)
        w = xm.float()[..., None]
        mean = (X * w).sum(1) / w.sum(1).clamp(min=1)
        mx = X.masked_fill(w == 0, float('-inf')).max(1).values
        out.append(torch.cat([mean, mx], 1))
    return torch.cat(out)


def train_gate_w(pos, neg, neg_w):
    """route.train_gate with per-negative weights (they sum to 0.5; positives share 0.5, as in route.py). Same GATE
    settings. -> (gate, train_acc)."""
    G = route.GATE
    g = torch.Generator().manual_seed(G['seed'])
    X = torch.cat([pos, neg])
    y = torch.cat([torch.ones(len(pos)), torch.zeros(len(neg))])
    mu, sd = X.mean(0), X.std(0).clamp(min=1e-6)
    Z = (X - mu) / sd
    w = (torch.randn(Z.shape[1], generator=g) * 0.01).requires_grad_(True)
    b0 = torch.zeros(1, requires_grad=True)
    cw = torch.cat([torch.full((len(pos),), 0.5 / len(pos)), torch.as_tensor(neg_w, dtype=torch.float32)])
    opt = torch.optim.Adam([w, b0], lr=G['lr'])
    for _ in range(G['epochs']):
        loss = (torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b0, y, reduction='none') * cw).sum() \
            + G['l2'] * (w * w).sum()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        train_acc = (((Z @ w + b0) > 0).float() == y).float().mean().item()
    gate = lambda F: (torch.sigmoid(((F - mu) / sd) @ w.detach() + b0.detach()) > G['threshold'])
    return gate, train_acc


def on_rates(on, rows, key):
    c, n = Counter(), Counter()
    for o, r in zip(on, rows):
        n[r[key]] += 1
        c[r[key]] += int(o)
    return {k: dict(on=c[k], n=n[k], rate=round(c[k] / n[k], 4)) for k in sorted(n)}


def old_rows(path):
    """lookalike-old rows as harm_measure groups them: one group per variant."""
    rows = analyze.load_rows(path)
    return rows, [dict(r, family=r['variant']) for r in rows]


def la3_rule(hm):
    proved = hm['in_dist_drop'] > LA_PROVED_POOLED or any(
        f['drop'] > LA_PROVED_VARIANT and f['hi'] < 0 for f in hm['families'].values())
    return 'PASS' if hm['passes'] else ('PROVED WRONG' if proved else 'FAIL')


def harm_summary(hm, only=None):
    fams = {k: {x: round(v[x], 2) for x in ('a', 'b', 'drop', 'lo', 'hi')} | dict(fires=v['fires'])
            for k, v in hm['families'].items() if only is None or k in only or v['fires'] or abs(v['drop']) > 0}
    return dict(pooled_parent=round(hm['in_dist_a'], 2), pooled_after=round(hm['in_dist_b'], 2),
                drop=round(hm['in_dist_drop'], 2), fired=hm['fired'], passes=hm['passes'], groups=fams)


def screen(a):
    """LA0: the switch as mode.py trains it, from the maker's practice prompts (even mix) and the seed's diary."""
    tool = __import__(f'domain.tools.{a.tool}', fromlist=['x'])
    cons = json.load(open(mode.CONST_PATH))
    ck = torch.load(a.parent, map_location='cpu', weights_only=True)
    helps = tool.help()
    kinds = [h['kind'] for h in helps]
    ex = {h['kind']: h['prompt'] for h in helps}
    ctx = dict(vchars=set(ck['chars']), cons=cons, seen=set(), quiz_set=set(), lmax=mode.lmax_of(helps, cons['digit_len_extra']))
    quiet = lambda *x, **k: None
    mode.make_quiz(tool, kinds, ex, cons['quiz'], random.Random(f'{a.seed}-quiz'), ctx, quiet)
    share = {k: 1 / len(kinds) for k in kinds}
    pos, kept = [], Counter()
    for day in range(1, a.days + 1):
        items, _, _, _ = mode.make_practice(tool, kinds, ex, share, cons['day_problems'], random.Random(f'{a.seed}-day-{day}'), ctx)
        pos += [it['prompt'] for it in items]
        kept.update(it['kind'] for it in items)
    events = [json.loads(l) for l in open(os.path.join(a.diary_run, 'log.jsonl'))]
    neg = [e['prompt'] for e in events if e['event'] == 'row' and e['source'] == 'diary']
    m = load_model(a.parent).eval()
    gate, acc = route.train_gate(route.features(m, sorted(set(pos))), route.features(m, neg))
    lrows, _ = old_rows(a.old_panel)
    drows = analyze.load_rows(a.dev)
    prows = score.load_panel(a.panel)
    on_l = gate(route.features(m, [r['prompt'] for r in lrows])).tolist()
    on_d = gate(route.features(m, [r['prompt'] for r in drows])).tolist()
    on_p = gate(route.features(m, [r['prompt'] for r in prows])).tolist()
    dev_fam = on_rates(on_d, drows, 'family')
    out = dict(mark='LA0 screen (reported only)', tool=a.tool, seed=a.seed, days=a.days,
               train=dict(pos=len(set(pos)), neg=len(neg), acc=round(acc, 4), practice_kept=dict(kept)),
               old_panel_on={k: v for k, v in on_rates(on_l, lrows, 'variant').items()},
               dev_on_total=dict(on=int(sum(on_d)), n=len(on_d)),
               dev_on_families={k: v for k, v in dev_fam.items() if v['on']},
               panel_on=on_rates(on_p, prows, 'split'), panel_on_kind=on_rates(on_p, prows, 'kind'))
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ('train', 'old_panel_on', 'dev_on_total', 'dev_on_families', 'panel_on')}, indent=1))
    print('wrote', a.out)


def risky_weights(run, fin, diary, cache):
    """F1: the model's own answers to its diary with the add-on on (the merged final checkpoint), against its pre-mode
    answers (the diary rows). -> (negative weights, n risky). Cached in the run's analysis cache."""
    csha = analyze.sha256_file(fin)
    fp = dict(kind='diary_on', ckpt_sha256=csha, n=len(diary))
    path = os.path.join(cache, f'diary_on_{csha[:16]}.json')
    ans, _ = analyze.cached(path, fp, lambda: [x for _, x in mode.greedy(load_model(fin).eval(), [d['prompt'] for d in diary])])
    risky = [int(x != d['answer']) for x, d in zip(ans, diary)]   # diary answer = the pre-mode self's own answer
    k = sum(risky)
    if k == 0:
        return [0.5 / len(diary)] * len(diary), 0
    return [0.25 / k if r else 0.25 / (len(diary) - k) for r in risky], k


def score_run(a):
    summary = json.load(open(os.path.join(a.run, 'summary.json')))
    assert a.gate == 'all' or summary.get('addon') == 'per_tool', 'the switch needs a per-tool add-on run (else --gate all)'
    res = json.load(open(os.path.join(a.run, 'analysis', 'RESULT.json')))
    events = [json.loads(l) for l in open(os.path.join(a.run, 'log.jsonl'))]
    rows = [e for e in events if e['event'] == 'row']
    pos = sorted({e['prompt'] for e in rows if e['source'] in ('own', 'tool')})
    seen, diary = set(), []
    for e in rows:   # route.py's negatives (sorted unique prompts), each with its pre-mode answer
        if e['source'] == 'diary' and e['prompt'] not in seen:
            seen.add(e['prompt'])
            diary.append(e)
    diary.sort(key=lambda e: e['prompt'])
    out_dir = a.out_dir or os.path.join(a.run, 'analysis')
    cache = os.path.join(out_dir, 'cache')
    src = os.path.join(a.run, 'analysis', 'cache')
    os.makedirs(cache, exist_ok=True)
    for n in os.listdir(src):
        if n.endswith('.json') and not os.path.exists(os.path.join(cache, n)):
            shutil.copy(os.path.join(src, n), os.path.join(cache, n))
    fin = res['final_checkpoint']
    m = load_model(a.parent).eval()   # the parent's reader = the model's reader with the add-on off
    feat = features_mm if a.gate == 'F2' else route.features
    if a.gate == 'all':
        feat = lambda m, prompts: torch.zeros(len(prompts), 1)
    Fp, Fn = feat(m, pos), feat(m, [d['prompt'] for d in diary])
    n_risky = None
    if a.gate == 'all':   # no switch: every question goes to the final checkpoint (a whole-model run, or add-on left on)
        gate, acc = (lambda F: torch.ones(len(F), dtype=torch.bool)), None
    elif a.gate == 'F1':
        w, n_risky = risky_weights(a.run, fin, diary, cache)
        gate, acc = train_gate_w(Fp, Fn, w)
    else:
        gate, acc = route.train_gate(Fp, Fn)

    prows = score.load_panel(a.panel)
    psha = analyze.sha256_file(a.panel)
    drows, dsha = analyze.load_rows(a.dev), analyze.sha256_file(a.dev)
    lrows, lgroups = old_rows(a.old_panel)
    lsha = analyze.sha256_file(a.old_panel)
    p0, _ = analyze.score_one(a.parent, 'parent', prows, psha, cache)
    pN, _ = analyze.score_one(fin, 'final', prows, psha, cache)
    d0, _ = analyze.in_dist_one(a.parent, drows, dsha, cache)
    dN, _ = analyze.in_dist_one(fin, drows, dsha, cache)
    l0, _ = analyze.in_dist_one(a.parent, lrows, lsha, cache)
    lN, _ = analyze.in_dist_one(fin, lrows, lsha, cache)
    held = None
    if a.heldout_panel:   # addendum L1: the curriculum's held-out look-alike variants, reported only
        hrows, hgroups = old_rows(a.heldout_panel)
        hsha = analyze.sha256_file(a.heldout_panel)
        h0, _ = analyze.in_dist_one(a.parent, hrows, hsha, cache)
        hN, _ = analyze.in_dist_one(fin, hrows, hsha, cache)
        on_h = gate(feat(m, [r['prompt'] for r in hrows])).tolist()
        h_routed = [x1 if on else x0 for x0, x1, on in zip(h0['hits'], hN['hits'], on_h)]
        held = dict(on=on_rates(on_h, hrows, 'variant'),
                    routed=harm_summary(harm.harm_measure(h0['hits'], h_routed, hgroups, LA_FAMILY_DROP, LA_POOLED_DROP)),
                    addon_left_on=harm_summary(harm.harm_measure(h0['hits'], hN['hits'], hgroups, LA_FAMILY_DROP, LA_POOLED_DROP)))

    on_p = gate(feat(m, [r['prompt'] for r in prows])).tolist()
    on_d = gate(feat(m, [r['prompt'] for r in drows])).tolist()
    on_l = gate(feat(m, [r['prompt'] for r in lrows])).tolist()
    hit0 = {r['id']: r for r in p0['rows']}
    hitN = {r['id']: r for r in pN['rows']}
    routed = [dict(hitN[r['id']] if on else hit0[r['id']]) for r, on in zip(prows, on_p)]
    d_routed = [hN if on else h0 for h0, hN, on in zip(d0['hits'], dN['hits'], on_d)]
    l_routed = [hN if on else h0 for h0, hN, on in zip(l0['hits'], lN['hits'], on_l)]

    scored = res['kinds']['scored']
    dropped = set(audit.decontam(prows, {e['prompt'] for e in rows})['ids'])
    near0, nearR = analyze.pooled(p0['rows'], scored, 'near', dropped), analyze.pooled(routed, scored, 'near', dropped)
    nearN = analyze.pooled(pN['rows'], scored, 'near', dropped)
    gain = nearR - near0
    hm_d = harm.harm_measure(d0['hits'], d_routed, drows, family_drop=5.0, in_dist_drop=1.5)
    hm_l = harm.harm_measure(l0['hits'], l_routed, lgroups, family_drop=LA_FAMILY_DROP, in_dist_drop=LA_POOLED_DROP)
    look = LOOKALIKE_FAMILIES.get(summary['tool'], ())
    la2_proved = hm_d['in_dist_drop'] > 1.5 or any(f in hm_d['fired'] for f in look)
    left_d = harm.harm_measure(d0['hits'], dN['hits'], drows, family_drop=5.0, in_dist_drop=1.5)
    left_l = harm.harm_measure(l0['hits'], lN['hits'], lgroups, family_drop=LA_FAMILY_DROP, in_dist_drop=LA_POOLED_DROP)
    changed = Counter((r['variant'], 'lost' if h0 > hR else 'gained') for r, h0, hR in zip(lrows, l0['hits'], l_routed) if h0 != hR)
    dev_fam = on_rates(on_d, drows, 'family')
    out = dict(run=a.run, tool=summary['tool'], seed=summary['seed'], gate=a.gate, gate_settings=route.GATE,
               train=dict(pos=len(pos), neg=len(diary), acc=None if acc is None else round(acc, 4), risky_diary=n_risky),
               on=dict(panel=on_rates(on_p, prows, 'split'), panel_kind=on_rates(on_p, prows, 'kind'),
                       old_panel=on_rates(on_l, lrows, 'variant'), dev_total=dict(on=int(sum(on_d)), n=len(on_d)),
                       dev_families={k: v for k, v in dev_fam.items() if v['on']}),
               LA1=dict(near_parent=near0, near_addon_always_on=nearN, near_routed=nearR, gain=round(gain, 4),
                        hair_miss_met=round(gain + 100.0 / max(1, sum(1 for r in prows if r['split'] == 'near'
                                                                      and r['kind'] in scored and r['id'] not in dropped)), 6) >= 30,
                        verdict='PASS' if gain >= 30 else ('PROVED WRONG' if gain < 10 else 'FAIL')),
               LA2=dict(harm_summary(hm_d, look), verdict='PASS' if hm_d['passes'] else ('PROVED WRONG' if la2_proved else 'FAIL')),
               LA3=dict(harm_summary(hm_l), verdict=la3_rule(hm_l)),
               old_answers_changed={f'{v} {d}': n for (v, d), n in sorted(changed.items())},
               addon_left_on=dict(dev=harm_summary(left_d, look), old_panel=harm_summary(left_l)),
               heldout_variants_reported=held, decontam_dropped=len(dropped))
    path = os.path.join(out_dir, f'LOOKALIKE_{a.gate}.json')
    with open(path, 'w') as f:
        json.dump(out, f, indent=1)
    short = dict(train=out['train'], on_panel=out['on']['panel'], on_old=out['on']['old_panel'], on_dev=out['on']['dev_total'],
                 LA1={k: out['LA1'][k] for k in ('near_parent', 'near_routed', 'gain', 'verdict')},
                 LA2={k: out['LA2'][k] for k in ('drop', 'fired', 'verdict')},
                 LA3={k: out['LA3'][k] for k in ('drop', 'fired', 'verdict')},
                 left_on_old={k: out['addon_left_on']['old_panel'][k] for k in ('drop', 'fired')})
    print(json.dumps(short, indent=1))
    print('wrote', path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('screen')
    s.add_argument('--tool', required=True)
    s.add_argument('--seed', type=int, default=200)
    s.add_argument('--days', type=int, default=7)
    s.add_argument('--diary-run', required=True)
    s.add_argument('--out', required=True)
    r = sub.add_parser('score')
    r.add_argument('--run', required=True)
    r.add_argument('--gate', default='v8', choices=['v8', 'F1', 'F2', 'all'],
                   help="all = no switch, every question to the final checkpoint (whole-model runs)")
    r.add_argument('--out-dir', default=None)
    r.add_argument('--heldout-panel', default=None, help='lookalike-old-heldout.v1.jsonl (addendum L1, reported only)')
    for p in (s, r):
        p.add_argument('--parent', required=True)
        p.add_argument('--old-panel', required=True)
        p.add_argument('--dev', required=True)
        p.add_argument('--panel', required=True)
        p.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    random.seed(0)
    (screen if a.cmd == 'screen' else score_run)(a)


if __name__ == '__main__':
    main()
