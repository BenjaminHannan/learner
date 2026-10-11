"""M3-0 "can the skill pieces live inside the loop?" screen, no training. Marks: /mnt/project-files/cohesive-model/M3-MARKS-2026-10-11.md

  python -m cohesive.m3_0 --out /mnt/project-files/cohesive-model/m3-0 --dev DEV_IN_DIST.jsonl [--threads 4]

Trace which nn.Linear layers run before the first call to core.0.qkv (the first thinker block), put the parent's weights back in those
layers of each M1 subject's final checkpoint, and score the trimmed checkpoint alone as M1 scored "final alone".
"""
import argparse
import json
import os
import shutil
import time

import torch

from cohesive import m1 as M
from cohesive import shelf as S
from domain import analyze, audit, score
from domain.mode import load_model

FIRST = 'core.0.qkv'
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.0f}s]', *a, flush=True)


def trace(m, prompts):
    """Names of nn.Linear modules in call order for one m.run(batch) (eval, no grad)."""
    order, hooks = [], []
    for n, x in m.named_modules():
        if isinstance(x, torch.nn.Linear):
            hooks.append(x.register_forward_hook(lambda mod, i, o, n=n: order.append(n)))
    try:
        with torch.no_grad():
            m.run(S._batch(m, prompts))
    finally:
        for h in hooks:
            h.remove()
    return order


def split_trace(order):
    assert FIRST in order, f'{FIRST} was not called'
    f = order.index(FIRST)
    before = {n for n in order[:f]}
    later = {n for n in order[f:]}
    return before, later


def trim_state(parent_sd, final_sd, before_weights):
    out = {k: v.clone() for k, v in final_sd.items()}
    for k in before_weights:
        out[k] = parent_sd[k].clone()
    return out


def self_check(parent_sd, final_sd, trimmed, before_weights):
    diff = {k for k in final_sd if not torch.equal(final_sd[k], trimmed[k])}
    changed = {k for k in final_sd if not torch.equal(final_sd[k], parent_sd[k])}
    assert diff == (set(before_weights) & changed), 'trimmed state differs from final outside the listed layers'
    assert all(torch.equal(trimmed[k], parent_sd[k]) for k in before_weights)
    assert all(torch.equal(trimmed[k], final_sd[k]) for k in final_sd if k not in set(before_weights))
    return sorted(diff)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--dev', required=True)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--layers', default=None, help='comma list of Linear names to trim (default: the traced before-the-loop set, M3-0)')
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    times = {}
    t = time.time()
    assert analyze.sha256_file(a.dev) == M.DEV_SHA, 'DEV sha differs'
    SUBJ, run_map = tuple(M.RUNS), dict(M.RUNS)
    os.makedirs(os.path.join(a.out, 'trimmed'), exist_ok=True)
    cache = os.path.join(a.out, 'cache')
    os.makedirs(cache, exist_ok=True)
    for src in [M.M1_CACHE] + [f'{M.RUNS_DIR}/{r}/analysis/cache' for r in run_map.values()]:
        for n in os.listdir(src):
            if n.endswith('.json') and not os.path.exists(os.path.join(cache, n)):
                shutil.copy(os.path.join(src, n), os.path.join(cache, n))
    m1res = json.load(open('/mnt/project-files/cohesive-model/m1/RESULT.json'))
    ck = torch.load(M.PARENT, map_location='cpu')
    m = load_model(M.PARENT).eval()
    lin = S.linear_names(m)
    results, panels, psha = {}, {}, {}
    for s in SUBJ:
        results[s] = json.load(open(f'{M.RUNS_DIR}/{run_map[s]}/analysis/RESULT.json'))
        assert results[s]['parent'] == M.PARENT
        pp = f"{M.PANEL_DIR}/{os.path.basename(results[s]['panel']['path'])}"
        panels[s], psha[s] = score.load_panel(pp), analyze.sha256_file(pp)
        ev = [json.loads(l) for l in open(f'{M.RUNS_DIR}/{run_map[s]}/log.jsonl')]
        results[s]['_train_prompts'] = {e['prompt'] for e in ev if e['event'] == 'row'}
    drows = analyze.load_rows(a.dev)
    dsha = analyze.sha256_file(a.dev)

    # ---- a. trace
    batches = {'dev': [r['prompt'] for r in drows[:64]]}
    for s in SUBJ:
        batches[f'panel:{s}'] = [r['prompt'] for r in panels[s][:64]]
    sets = {}
    for k, ps in batches.items():
        sets[k] = split_trace(trace(m, ps))
        log('trace', k, len(sets[k][0]), 'before-loop layers')
    union = set().union(*[b for b, _ in sets.values()])
    inter = set.intersection(*[b for b, _ in sets.values()])
    later_any = set().union(*[l for _, l in sets.values()])
    same = union == inter
    first_order = trace(m, batches['dev'])
    before = [n for n in dict.fromkeys(first_order) if n in union and n != FIRST]
    before = [n for n in dict.fromkeys(first_order[:first_order.index(FIRST)]) if n in union]
    before += sorted(union - set(before))
    trace_rep = dict(same_set_in_all_six_batches=same, union=before, differences={k: sorted(b ^ union) for k, (b, _) in sets.items() if b != union},
                     also_called_in_loop={n: n in later_any for n in before}, batches={k: len(v) for k, v in batches.items()})
    traced = list(before)
    if a.layers:
        before = [x for x in a.layers.split(',') if x]
        assert set(before) <= set(traced), f'--layers not all in the traced set {traced}'
    trace_rep['traced_set'] = traced
    trace_rep['trimmed_layers'] = before
    trace_rep['also_called_in_loop'] = {n: n in later_any for n in before}
    before_w = [n + '.weight' for n in before]
    assert all(w in lin for w in before_w)
    log('before-the-loop layers', trace_rep['also_called_in_loop'])
    times['trace'] = round(time.time() - t, 1)

    # ---- b, c. trimmed states and scores
    t = time.time()
    dropped = {s: set(audit.decontam(panels[s], results[s]['_train_prompts'])['ids']) for s in SUBJ}
    par_dev = analyze.in_dist_one(M.PARENT, drows, dsha, cache)[0]['hits']
    pooled_dev = lambda h: round(100.0 * sum(h) / len(h), 2)
    out, devrows = {}, {}
    for s in SUBJ:
        fin = results[s]['final_checkpoint']
        fck = torch.load(fin, map_location='cpu')
        assert all(fck[k] == ck[k] for k in ('name', 'cfg', 'chars', 'step'))
        tr = trim_state(ck['model'], fck['model'], before_w)
        diffs = self_check(ck['model'], fck['model'], tr, before_w)
        tot = trimmed_n = 0
        per_layer = {}
        for k in ck['model']:
            if torch.equal(ck['model'][k], fck['model'][k]):
                continue
            o, i = fck['model'][k].shape
            n = min(8, o, i) * (o + i)
            tot += n
            if k in before_w:
                trimmed_n += n
                per_layer[k[:-7]] = n
        path = os.path.join(a.out, 'trimmed', f'{s}.pt')
        torch.save(dict(model=tr, name=ck['name'], cfg=ck['cfg'], chars=ck['chars'], step=ck['step']), path)
        log('trimmed saved', s, path)
        scored = results[s]['kinds']['scored']
        res = {}
        for lab, c in (('untrimmed', fin), ('trimmed', path)):
            r, _ = analyze.score_one(c, 'final', panels[s], psha[s], cache)
            res[lab] = dict(near=analyze.pooled(r['rows'], scored, 'near', dropped[s]), far=analyze.pooled(r['rows'], scored, 'far', dropped[s]))
            dh = analyze.in_dist_one(c, drows, dsha, cache)[0]['hits']
            res[lab]['dev'] = pooled_dev(dh)
            log(s, lab, res[lab])
        nn = sum(1 for r in panels[s] if r['split'] == 'near' and r['kind'] in scored and r['id'] not in dropped[s])
        nf = sum(1 for r in panels[s] if r['split'] == 'far' and r['kind'] in scored and r['id'] not in dropped[s])
        m1n = m1res['arms']['T']['S1'][s]['final_alone_near']
        m1f = m1res['arms']['T']['far'][s]['final_alone_far']
        sane = abs(res['untrimmed']['near'] - m1n) < 1e-4 and abs(res['untrimmed']['far'] - m1f) < 1e-4
        ref = res['untrimmed']['near']
        near = res['trimmed']['near']
        thr = round(ref - 3, 2)
        passed = near >= thr - 1e-9
        hair = round(near + 100.0 / nn, 6) >= thr
        proved = near < ref - 10
        v = 'PASS' if passed or hair else ('PROVED WRONG' if proved else 'FAIL')
        out[s] = dict(final_checkpoint=fin, trimmed_checkpoint=path, tensors_changed_in_final=sum(1 for k in ck['model'] if not torch.equal(ck['model'][k], fck['model'][k])),
                      tensors_reset=diffs, piece_numbers=tot, numbers_in_trimmed_layers=trimmed_n, share_trimmed_pct=round(100.0 * trimmed_n / tot, 2),
                      numbers_per_trimmed_layer=per_layer, untrimmed=res['untrimmed'], trimmed=res['trimmed'], n_near=nn, n_far=nf,
                      m1_final_alone_near=m1n, m1_final_alone_far=m1f, sanity_matches_m1=sane,
                      threshold=thr, passed_without_hair_miss=passed, hair_miss_used=bool(hair and not passed), proved_wrong_below=round(ref - 10, 2), verdict=v)
    times['trim_and_score'] = round(time.time() - t, 1)
    vs = {s: out[s]['verdict'] for s in SUBJ}
    bad = [s for s in SUBJ if vs[s] != 'PASS']
    wrong = [s for s in SUBJ if vs[s] == 'PROVED WRONG']
    overall = 'PASS' if not bad else (f'PROVED WRONG ({", ".join(wrong)})' if wrong else f'FAIL ({", ".join(bad)})')
    result = dict(marks='M3-MARKS-2026-10-11.md' + (' (Addendum M3-0b)' if a.layers else ''), parent=M.PARENT, dev_sha256=dsha, parent_dev_pooled=pooled_dev(par_dev), trace=trace_rep,
                  subjects=out, sanity_all_match_m1=all(out[s]['sanity_matches_m1'] for s in SUBJ), overall=overall, timings_s=times,
                  total_secs=round(time.time() - T0, 1), decontam_dropped={s: len(dropped[s]) for s in SUBJ})
    json.dump(result, open(os.path.join(a.out, 'RESULT.json'), 'w'), indent=1, default=str)
    write_md(result, os.path.join(a.out, 'RESULT.md'))
    log('overall', overall, 'sanity', result['sanity_all_match_m1'])
    assert result['sanity_all_match_m1'], 'untrimmed numbers differ from M1: stop'


def write_md(r, path):
    L = ['# M3-0 result: skill pieces with their before-the-loop parts removed', '',
         f"Overall: **{r['overall']}**. Sanity (untrimmed = M1 final alone near/far): {r['sanity_all_match_m1']}. Total {r['total_secs']} s; {r['timings_s']}", '',
         '## Before-the-loop layers (called before the first call to core.0.qkv)', '',
         f"Same set in all six traced batches: {r['trace']['same_set_in_all_six_batches']}; differences {r['trace']['differences']}", '',
         '| layer | also called inside the loop |', '|---|---|']
    L += [f'| {n} | {v} |' for n, v in r['trace']['also_called_in_loop'].items()]
    L += ['', '## Share of each piece in those layers', '', '| subject | rank-8 numbers | in trimmed layers | share % |', '|---|---|---|---|']
    L += [f"| {s} | {x['piece_numbers']} | {x['numbers_in_trimmed_layers']} | {x['share_trimmed_pct']} |" for s, x in r['subjects'].items()]
    L += ['', '## Panel scores alone (decontaminated)', '',
          '| subject | untrimmed near | trimmed near | threshold | proved wrong below | verdict | hair-miss | untrimmed far | trimmed far | n near | M1 match |', '|---|---|---|---|---|---|---|---|---|---|---|']
    L += [f"| {s} | {x['untrimmed']['near']:.2f} | {x['trimmed']['near']:.2f} | {x['threshold']} | {x['proved_wrong_below']} | {x['verdict']} | {x['hair_miss_used']} | "
          f"{x['untrimmed']['far']:.2f} | {x['trimmed']['far']:.2f} | {x['n_near']} | {x['sanity_matches_m1']} |" for s, x in r['subjects'].items()]
    L += ['', f"## DEV in_dist pooled (parent {r['parent_dev_pooled']})", '', '| subject | untrimmed | trimmed |', '|---|---|---|']
    L += [f"| {s} | {x['untrimmed']['dev']} | {x['trimmed']['dev']} |" for s, x in r['subjects'].items()]
    open(path, 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
