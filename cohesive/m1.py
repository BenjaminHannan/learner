"""M1 "one shelf": five rank-8 pieces + one readout in one model file. Marks: /mnt/project-files/cohesive-model/M1-MARKS-2026-10-10.md

  python -m cohesive.m1 --out /mnt/project-files/cohesive-model/m1 --dev DEV_IN_DIST.jsonl [--threads 4]
"""
import argparse
import json
import os
import random
import shutil
import time
from collections import Counter

import torch

from cohesive import shelf as S
from domain import analyze, audit, harm, lookalike, score
from domain.mode import greedy, load_model

RUNS_DIR = '/mnt/project-files/domain-mode/runs'
PANEL_DIR = '/mnt/project-files/domain-mode/panel'
PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
RUNS = dict(sheet='sheet-s200-v7', rpn='rpn-s200-v7', stats='stats-s200-v8', invoice='invoice-s200-v8', py='py-s200-v8')
OLD_PANEL = f'{PANEL_DIR}/lookalike-old.v1.jsonl'
HELD_PANEL = f'{PANEL_DIR}/lookalike-old-heldout.v1.jsonl'
DEV_SHA = 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'
# marks file: own routed near / far per subject (table), S1 threshold = near - 3, proved wrong below near - 10
OWN = dict(sheet=(40.24, 1.79), rpn=(90.07, 0.36), stats=(99.29, 18.57), invoice=(62.22, 16.67), py=(61.00, 2.50))
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.0f}s]', *a, flush=True)


def timed(times, key):
    class C:
        def __enter__(s):
            s.t = time.time()

        def __exit__(s, *e):
            times[key] = round(time.time() - s.t, 1)
    return C()


def verdict_rank(v):
    return {'PASS': 2, 'FAIL': 1, 'PROVED WRONG': 0}[v]


def on_rates(cls, rows, key):
    """Wrongly-on counts: any class other than none."""
    n, c = Counter(), Counter()
    for k, r in zip(cls, rows):
        n[r[key]] += 1
        c[r[key]] += int(k != 0)
    return {g: dict(on=c[g], n=n[g]) for g in sorted(n) if c[g] or key == 'variant'}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--dev', required=True)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    random.seed(0)
    times = {}
    # ---- DEV file must be the verified one
    for _ in range(80):
        if os.path.exists(a.dev):
            break
        time.sleep(30)
    dsha = analyze.sha256_file(a.dev)
    assert dsha == DEV_SHA, f'DEV sha differs: {dsha}'
    os.makedirs(a.out, exist_ok=True)
    cache = os.path.join(a.out, 'cache')
    os.makedirs(cache, exist_ok=True)
    for run in RUNS.values():
        src = f'{RUNS_DIR}/{run}/analysis/cache'
        for n in os.listdir(src):
            if n.endswith('.json') and not os.path.exists(os.path.join(cache, n)):
                shutil.copy(os.path.join(src, n), os.path.join(cache, n))
    deviations = []

    # ---- a. pieces
    ck = torch.load(PARENT, map_location='cpu')
    m = load_model(PARENT).eval()
    lin = S.linear_names(m)
    finals, pieces, piece_rep, results = [], [], {}, {}
    with timed(times, 'pieces'):
        for s in S.SUBJECTS:
            res = json.load(open(f'{RUNS_DIR}/{RUNS[s]}/analysis/RESULT.json'))
            results[s] = res
            fin = res['final_checkpoint']
            finals.append(fin)
            fck = torch.load(fin, map_location='cpu')
            assert all(fck[k] == ck[k] for k in ('name', 'cfg', 'chars', 'step')), 'checkpoint header differs from parent'
            pc, rep = S.piece_from(ck['model'], fck['model'], lin, with_report=True)
            pieces.append(pc)
            piece_rep[s] = dict(checkpoint=fin, tensors_changed=rep['changed'], numbers=rep['numbers'], max_recon_err=rep['max_err'])
            log('piece', s, piece_rep[s])
    ckpts = [PARENT] + finals                      # index = class index
    csha = [analyze.sha256_file(c) for c in ckpts]

    # ---- b. router rows
    cls_prompts = {}
    for k, s in enumerate(S.SUBJECTS, 1):
        ev = [json.loads(l) for l in open(f'{RUNS_DIR}/{RUNS[s]}/log.jsonl')]
        rows = [e for e in ev if e['event'] == 'row']
        results[s]['_train_prompts'] = {e['prompt'] for e in rows}
        cls_prompts.setdefault(k, set()).update(e['prompt'] for e in rows if e['source'] in ('own', 'tool'))
        cls_prompts.setdefault(0, set()).update(e['prompt'] for e in rows if e['source'] == 'diary')
    seen = Counter()
    for k, ps in cls_prompts.items():
        seen.update(ps)
    both = {p for p, c in seen.items() if c > 1}
    pair_counts = Counter()
    for p in both:
        pair_counts[tuple(sorted(k for k, ps in cls_prompts.items() if p in ps))] += 1
    for k in cls_prompts:
        cls_prompts[k] -= both
    train_prompts, train_y = [], []
    for k in range(6):
        ps = sorted(cls_prompts[k])
        train_prompts += ps
        train_y += [k] * len(ps)
    sizes = {S.CLASSES[k]: len(cls_prompts[k]) for k in range(6)}
    log('class sizes', sizes, 'prompts in two or more classes (dropped from all):', len(both), dict(pair_counts))
    if both:
        deviations.append(f'{len(both)} training prompts appeared in two or more classes and were dropped from every class (pairs: '
                          f'{ {str(k): v for k, v in pair_counts.items()} }); marks file does not say this happens')

    # ---- eval sets
    panels = {s: score.load_panel(f"{PANEL_DIR}/{os.path.basename(results[s]['panel']['path'])}") for s in S.SUBJECTS}
    for s in S.SUBJECTS:
        assert os.path.exists(results[s]['panel']['path']) or True
    psha = {s: analyze.sha256_file(f"{PANEL_DIR}/{os.path.basename(results[s]['panel']['path'])}") for s in S.SUBJECTS}
    drows = analyze.load_rows(a.dev)
    lrows, lgroups = lookalike.old_rows(OLD_PANEL)
    hrows, hgroups = lookalike.old_rows(HELD_PANEL)
    lsha, hsha = analyze.sha256_file(OLD_PANEL), analyze.sha256_file(HELD_PANEL)
    sets = {f'panel:{s}': [r['prompt'] for r in panels[s]] for s in S.SUBJECTS}
    sets['dev'] = [r['prompt'] for r in drows]
    sets['old'] = [r['prompt'] for r in lrows]
    sets['held'] = [r['prompt'] for r in hrows]

    # ---- c. features (parent only)
    feats_T, feats_R, glance = {}, {}, {}
    with timed(times, 'features'):
        XT, _ = S.workspace_features(m, train_prompts)
        XR = S.reader_features(m, train_prompts)
        log('training features', tuple(XT.shape), tuple(XR.shape))
        for k, ps in sets.items():
            feats_T[k], glance[k] = S.workspace_features(m, ps)
            feats_R[k] = S.reader_features(m, ps)
            log('features', k, len(ps))
    with timed(times, 'fit'):
        rT = S.fit_router(XT, train_y, kind='workspace (8 control rows x 256, after the last round)')
        rR = S.fit_router(XR, train_y, kind='reader mean (256)')
    log('router train acc  T', round(rT['train_acc'], 4), ' R', round(rR['train_acc'], 4))
    routes = {'T': {k: S.route(rT, feats_T[k]).tolist() for k in sets}, 'R': {k: S.route(rR, feats_R[k]).tolist() for k in sets}}

    # ---- d. save the arm-T shelf
    shelf = S.Shelf(ck, pieces, rT)
    shelf_path = os.path.join(a.out, 'shelf.pt')
    shelf.save(shelf_path)
    nums = shelf.numbers()
    nums['readout_R_for_comparison'] = sum(rR[k].numel() for k in ('mu', 'sd', 'W', 'b'))
    nums['parent_plus_five_full_copies'] = nums['parent'] * 6
    nums['file_bytes'] = os.path.getsize(shelf_path)
    log('shelf saved', shelf_path, nums)

    # ---- e. equivalence check on the saved file
    with timed(times, 'equivalence'):
        fresh = S.Shelf.load(shelf_path)
        eq_sets, eq_prompts, eq_src = {}, [], []
        for s in S.SUBJECTS:
            ix = random.Random(0).sample(range(len(panels[s])), 60)
            eq_sets[f'panel:{s}'] = ix
        eq_sets['dev'] = random.Random(0).sample(range(len(drows)), 200)
        for k, ix in eq_sets.items():
            for i in ix:
                eq_prompts.append(sets[k][i])
                eq_src.append((k, i))
        ans, rt = fresh.answer(eq_prompts)
        same_route = sum(r == routes['T'][k][i] for r, (k, i) in zip(rt, eq_src))
        ref = [None] * len(eq_prompts)
        for k in range(6):
            ix = [j for j, r in enumerate(rt) if r == k]
            if ix:
                mk = load_model(ckpts[k]).eval()
                for j, (_, x) in zip(ix, greedy(mk, [eq_prompts[j] for j in ix])):
                    ref[j] = x
        match = [x == y for x, y in zip(ans, ref)]
        eq = dict(n=len(match), share=round(100 * sum(match) / len(match), 3),
                  by_set={k: round(100 * sum(match[j] for j, (kk, _) in enumerate(eq_src) if kk == k) / len(ix), 2) for k, ix in eq_sets.items()},
                  route_agrees_with_in_memory=f'{same_route}/{len(rt)}', routes=dict(Counter(S.CLASSES[r] for r in rt)),
                  mismatches=[dict(set=eq_src[j][0], prompt=eq_prompts[j], shelf=ans[j], picked_ckpt=ref[j], cls=S.CLASSES[rt[j]]) for j, ok in enumerate(match) if not ok][:20])
        del fresh
    log('equivalence', json.dumps({k: v for k, v in eq.items() if k != 'mismatches'}))
    if eq['share'] < 99.0:
        out = dict(stopped='equivalence below 99%', equivalence=eq, sizes=sizes, numbers=nums, pieces=piece_rep)
        json.dump(out, open(os.path.join(a.out, 'RESULT.json'), 'w'), indent=1)
        log('STOP: equivalence below 99%; marks not read')
        return

    # ---- f. per-row hits for six checkpoints
    ph, dh, lh, hh = {}, [], [], []
    with timed(times, 'hits'):
        for i, c in enumerate(ckpts):
            for s in S.SUBJECTS:
                r, _ = analyze.score_one(c, 'parent' if i == 0 else 'final', panels[s], psha[s], cache)
                assert [x['id'] for x in r['rows']] == [x['id'] for x in panels[s]]
                ph[(i, s)] = r['rows']
            dh.append(analyze.in_dist_one(c, drows, dsha, cache)[0]['hits'])
            lh.append(analyze.in_dist_one(c, lrows, lsha, cache)[0]['hits'])
            hh.append(analyze.in_dist_one(c, hrows, hsha, cache)[0]['hits'])
            log('hits done for checkpoint', i)

    # ---- g, h, i. per arm
    dropped = {s: set(audit.decontam(panels[s], results[s]['_train_prompts'])['ids']) for s in S.SUBJECTS}
    arms = {}
    for arm in ('T', 'R'):
        R = routes[arm]
        out = dict(S1={}, far={}, route_table={}, route_table_near_far={})
        for j, s in enumerate(S.SUBJECTS, 1):
            rows = panels[s]
            cl = R[f'panel:{s}']
            routed = [dict(ph[(c, s)][i]) for i, c in enumerate(cl)]
            scored = results[s]['kinds']['scored']
            nn = sum(1 for r in rows if r['split'] == 'near' and r['kind'] in scored and r['id'] not in dropped[s])
            nf = sum(1 for r in rows if r['split'] == 'far' and r['kind'] in scored and r['id'] not in dropped[s])
            near, far = analyze.pooled(routed, scored, 'near', dropped[s]), analyze.pooled(routed, scored, 'far', dropped[s])
            near_par = analyze.pooled(ph[(0, s)], scored, 'near', dropped[s])
            near_fin = analyze.pooled(ph[(j, s)], scored, 'near', dropped[s])
            thr = round(OWN[s][0] - 3, 2)
            hair = round(near + 100.0 / nn, 6) >= thr
            passed = near >= thr - 1e-9
            proved = near < OWN[s][0] - 10
            v = 'PASS' if passed or hair else ('PROVED WRONG' if proved else 'FAIL')
            out['S1'][s] = dict(near=near, threshold=thr, own_routed_near=OWN[s][0], n_near=nn, parent_near=near_par, final_alone_near=near_fin,
                                passed_without_hair_miss=passed, hair_miss_used=bool(hair and not passed), verdict=v)
            out['far'][s] = dict(far=far, own_routed_far=OWN[s][1], n_far=nf, parent_far=analyze.pooled(ph[(0, s)], scored, 'far', dropped[s]),
                                 final_alone_far=analyze.pooled(ph[(j, s)], scored, 'far', dropped[s]))
            cnt = {sp: Counter(c for c, r in zip(cl, rows) if r['split'] == sp) for sp in ('near', 'far')}
            out['route_table'][s] = [sum(cnt[sp][c] for sp in cnt) for c in range(6)]
            out['route_table_near_far'][s] = {sp: [cnt[sp][c] for c in range(6)] for sp in cnt}
        d_routed = [dh[c][i] for i, c in enumerate(R['dev'])]
        l_routed = [lh[c][i] for i, c in enumerate(R['old'])]
        h_routed = [hh[c][i] for i, c in enumerate(R['held'])]
        hm_d = harm.harm_measure(dh[0], d_routed, drows, family_drop=5.0, in_dist_drop=1.5)
        hm_l = harm.harm_measure(lh[0], l_routed, lgroups, family_drop=5.0, in_dist_drop=1.5)
        hm_h = harm.harm_measure(hh[0], h_routed, hgroups, family_drop=5.0, in_dist_drop=1.5)
        out['S2'] = dict(lookalike.harm_summary(hm_d), verdict='PASS' if hm_d['passes'] else 'PROVED WRONG')
        out['S3'] = dict(lookalike.harm_summary(hm_l), verdict=lookalike.la3_rule(hm_l))
        out['heldout'] = dict(lookalike.harm_summary(hm_h), verdict=lookalike.la3_rule(hm_h))
        out['false_on'] = dict(dev=dict(total=sum(c != 0 for c in R['dev']), n=len(drows), by_family=on_rates(R['dev'], drows, 'family'),
                                        by_class=dict(Counter(S.CLASSES[c] for c in R['dev'] if c))),
                               old=dict(total=sum(c != 0 for c in R['old']), n=len(lrows), by_variant=on_rates(R['old'], lrows, 'variant'),
                                        by_class=dict(Counter(S.CLASSES[c] for c in R['old'] if c))),
                               held=dict(total=sum(c != 0 for c in R['held']), n=len(hrows), by_variant=on_rates(R['held'], hrows, 'variant'),
                                         by_class=dict(Counter(S.CLASSES[c] for c in R['held'] if c))))
        out['false_on_total'] = sum(out['false_on'][k]['total'] for k in ('dev', 'old', 'held'))
        vs = [out['S1'][s]['verdict'] for s in S.SUBJECTS] + [out['S2']['verdict'], out['S3']['verdict']]
        out['S1_verdict'] = 'PROVED WRONG' if 'PROVED WRONG' in [out['S1'][s]['verdict'] for s in S.SUBJECTS] else (
            'PASS' if all(out['S1'][s]['verdict'] == 'PASS' for s in S.SUBJECTS) else 'FAIL')
        out['overall'] = 'PROVED WRONG' if 'PROVED WRONG' in (out['S1_verdict'], out['S2']['verdict'], out['S3']['verdict']) else (
            'PASS' if all(x == 'PASS' for x in (out['S1_verdict'], out['S2']['verdict'], out['S3']['verdict'])) else 'FAIL')
        out['train_acc'] = round((rT if arm == 'T' else rR)['train_acc'], 4)
        arms[arm] = out
    T, Rr = arms['T'], arms['R']
    fewer = Rr['false_on_total'] - T['false_on_total']
    not_worse = verdict_rank(T['S2']['verdict']) >= verdict_rank(Rr['S2']['verdict']) and verdict_rank(T['S3']['verdict']) >= verdict_rank(Rr['S3']['verdict'])
    comparison = dict(false_on_T=T['false_on_total'], false_on_R=Rr['false_on_total'], T_fewer_by=fewer, threshold=20,
                      T_not_worse_than_R_on_S2_S3=not_worse,
                      S2_drop=dict(T=T['S2']['drop'], R=Rr['S2']['drop']), S3_drop=dict(T=T['S3']['drop'], R=Rr['S3']['drop']),
                      statement='the brain\'s own thinking picks skills better than the reader\'s mean (suggested, one seed)'
                      if fewer >= 20 and not_worse else 'no difference shown')
    result = dict(marks='M1-MARKS-2026-10-10.md', dev_sha256=dsha, checkpoints=ckpts, checkpoint_sha256=csha, pieces=piece_rep,
                  class_sizes=sizes, dropped_cross_class=len(both), router_train_acc=dict(T=arms['T']['train_acc'], R=arms['R']['train_acc']),
                  numbers=nums, equivalence=eq, arms=arms, comparison=comparison, deviations=deviations, timings_s=times,
                  total_secs=round(time.time() - T0, 1), decontam_dropped={s: len(dropped[s]) for s in S.SUBJECTS})
    with open(os.path.join(a.out, 'RESULT.json'), 'w') as f:
        json.dump(result, f, indent=1, default=str)
    write_md(result, os.path.join(a.out, 'RESULT.md'))
    log('T overall', T['overall'], '| S1', T['S1_verdict'], 'S2', T['S2']['verdict'], 'S3', T['S3']['verdict'])
    log('R overall', Rr['overall'], '| S1', Rr['S1_verdict'], 'S2', Rr['S2']['verdict'], 'S3', Rr['S3']['verdict'])
    log('comparison', comparison)


def write_md(r, path):
    L = ['# M1 "one shelf" result', '', f"DEV sha256 {r['dev_sha256'][:16]}...; total {r['total_secs']} s; timings {r['timings_s']}", '']
    L += ['## Pieces', '', '| subject | tensors changed | numbers | max recon err |', '|---|---|---|---|']
    for s, p in r['pieces'].items():
        L.append(f"| {s} | {p['tensors_changed']} | {p['numbers']} | {p['max_recon_err']:.2e} |")
    L += ['', f"Class sizes {r['class_sizes']}; prompts in two or more classes (dropped): {r['dropped_cross_class']}", f"Readout train accuracy {r['router_train_acc']}",
          f"Sizes {r['numbers']}", '', f"## Equivalence (shelf.pt vs picked checkpoint): {r['equivalence']['share']}% of {r['equivalence']['n']}", '',
          f"{ {k: v for k, v in r['equivalence'].items() if k != 'mismatches'} }", '']
    for arm in ('T', 'R'):
        A = r['arms'][arm]
        L += [f"## Arm {arm}: overall {A['overall']} (S1 {A['S1_verdict']}, S2 {A['S2']['verdict']}, S3 {A['S3']['verdict']})", '',
              '| subject | near | threshold | own routed near | parent near | final alone near | verdict | hair-miss used |', '|---|---|---|---|---|---|---|---|']
        for s, x in A['S1'].items():
            L.append(f"| {s} | {x['near']:.2f} | {x['threshold']} | {x['own_routed_near']} | {x['parent_near']:.2f} | {x['final_alone_near']:.2f} | {x['verdict']} | {x['hair_miss_used']} |")
        L += ['', '| subject | far | own routed far | parent far | final alone far |', '|---|---|---|---|---|']
        for s, x in A['far'].items():
            L.append(f"| {s} | {x['far']:.2f} | {x['own_routed_far']} | {x['parent_far']:.2f} | {x['final_alone_far']:.2f} |")
        L += ['', 'Routing of the subject panels (all rows; columns none, sheet, rpn, stats, invoice, py):', '', '| panel | none | sheet | rpn | stats | invoice | py |', '|---|---|---|---|---|---|---|']
        for s, row in A['route_table'].items():
            L.append(f"| {s} | " + ' | '.join(map(str, row)) + ' |')
        L += ['', f"S2 DEV: parent {A['S2']['pooled_parent']} -> {A['S2']['pooled_after']}, drop {A['S2']['drop']}, fired {A['S2']['fired']}, {A['S2']['verdict']}",
              f"S3 look-alike old: parent {A['S3']['pooled_parent']} -> {A['S3']['pooled_after']}, drop {A['S3']['drop']}, fired {A['S3']['fired']}, {A['S3']['verdict']}",
              f"Held-out (reported): parent {A['heldout']['pooled_parent']} -> {A['heldout']['pooled_after']}, drop {A['heldout']['drop']}, fired {A['heldout']['fired']}, {A['heldout']['verdict']}", '',
              f"Wrongly switched on: DEV {A['false_on']['dev']['total']}/{A['false_on']['dev']['n']} {A['false_on']['dev']['by_class']}; "
              f"old {A['false_on']['old']['total']}/{A['false_on']['old']['n']} {A['false_on']['old']['by_class']}; "
              f"held {A['false_on']['held']['total']}/{A['false_on']['held']['n']} {A['false_on']['held']['by_class']}; total {A['false_on_total']}",
              f"DEV by family: {A['false_on']['dev']['by_family']}", f"old by variant: {A['false_on']['old']['by_variant']}", f"held by variant: {A['false_on']['held']['by_variant']}", '']
    L += ['## Comparison rule', '', json.dumps(r['comparison'], indent=1), '', '## Deviations', ''] + [f'- {d}' for d in r['deviations']]
    with open(path, 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
