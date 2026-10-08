"""Roadmap 8e924aaa2f: a 2x2 drift check on W1. CPU. Reads the skills TRAIN file (held slice, replay rows), C2 DEV and skills DEV (MEASURE only); C2 test / labelled / holdout never opened.
  python3 -m creative.drift7d run --model ~/c7d/s3/s100/W1.pt --out DIR --skills-train ~/work/data/train.jsonl --skills-data ~/work/data_big --threads 1
  python3 -m creative.drift7d report --out DIR --parents s100 s101
Test R found replay-only updates on a model's own skills TRAINING rows make its skills worse. Two suspects: (1) optimiser drift (a fresh AdamW at lr 1e-3 on rows the model already fits turns gradient noise into
full-size steps); (2) overfitting a small reused row set. All four cells start from the same M0 = W1 and run 256 replay-only updates: lr {1e-3, 1e-4} x {1,024 reused rows (4 visits each), 16,384 fresh rows (1 visit each)}."""
import argparse, json, os, random, time, copy
import torch
from creative import c2_pilot, c2_stones, rules_real as R, sleep
from creative.sleep7d import DATA, _cached, _h, _limit, _log, _sha_file, greedy_rows
from creative.repair7d import held_split, held_hits, _draw, _replay_only, _stage, skills_dev
from creative.harm_look import harm_measure
from custom_io.data import load_rows
from custom_io.evalx import subsample

CELLS = {'lr1e-3_reused': (1e-3, 'reused'), 'lr1e-3_fresh': (1e-3, 'fresh'), 'lr1e-4_reused': (1e-4, 'reused'), 'lr1e-4_fresh': (1e-4, 'fresh')}
RULES = dict(drift_confirmed='BOTH lr 1e-4 cells drop <= 1.0 AND lr1e-3_fresh drops >= 3.0 (held in_dist drop vs M0, points)',
             overfit_confirmed='lr1e-3_fresh drops <= 1.0 AND lr1e-3_reused drops >= 3.0 (held in_dist drop vs M0, points)',
             proved_wrong='all four cells\' held in_dist drops within 1.0 point of each other (max - min <= 1.0)')


def marks(drops):
    """Pure function of the four held in_dist drops (points, vs M0) {cell: drop} -> the three marks."""
    d = drops
    return dict(drift_confirmed=bool(d['lr1e-4_reused'] <= 1.0 and d['lr1e-4_fresh'] <= 1.0 and d['lr1e-3_fresh'] >= 3.0),
                overfit_confirmed=bool(d['lr1e-3_fresh'] <= 1.0 and d['lr1e-3_reused'] >= 3.0),
                proved_wrong=bool(max(d.values()) - min(d.values()) <= 1.0), rules=RULES)


def _train_cell(M0, rpool, vocab, device, seed, lr, kind, updates, n_reused):
    fams = list(rpool)
    n, sd = (n_reused, seed + 200) if kind == 'reused' else (updates * 64, seed + 300)
    recs, _ = _draw(rpool, fams, n, random.Random(sd))
    m = copy.deepcopy(M0)
    m.eval()
    t0 = time.time()
    out = _replay_only(m, recs, vocab, updates, lr, sd, device)
    mv = max(out['visits'].values()) if out.get('visits') else 0
    return m, dict(updates=updates, rows=len(recs), max_visits=mv, lr=lr, kind=kind, train_seconds=time.time() - t0, requested_rows=n)


def drift_parent(model_path, out, skills_train, skills_data, seed=0, updates=256, n_reused=1024, lrs=(1e-3, 1e-4), held_per_family=100, dev_limit=None, skills_limit=None,
                 device='cpu', name=None, resume=True, log=_log, r_dir=None):
    """One parent's 2x2. DIR/<name>/drift.json is written after every stage; each cell is cached (<cell>.pt + .pkl) and each measure is cached."""
    model_path = os.path.expanduser(model_path)
    name = name or os.path.basename(os.path.dirname(os.path.abspath(model_path)))
    pdir = os.path.join(out, name)
    os.makedirs(pdir, exist_ok=True)
    t00, secs = time.time(), {}
    res = dict(name=name, model=model_path, spec=__doc__.split('\n')[0], rules=RULES, secs=secs,
               args=dict(seed=seed, updates=updates, n_reused=n_reused, lrs=list(lrs), held_per_family=held_per_family, dev_limit=dev_limit, skills_limit=skills_limit, skills_train=skills_train, skills_data=skills_data),
               note='skills TRAIN (held slice, replay rows); C2 DEV and skills DEV MEASURE only; test / labelled / holdout never opened')
    save = lambda: json.dump(res, open(os.path.join(pdir, 'drift.json'), 'w'), indent=1)
    dev = c2_stones._with_nums(_limit(R.load_split(DATA, 'dev'), dev_limit))
    held, rpool = held_split(load_rows(skills_train), held_per_family, seed)
    res['held'] = dict(rows=len(held), per_family=held_per_family, families=len(rpool), repair_rows=sum(len(v) for v in rpool.values()), ids_sha256=_h([r['id'] for r in held]))
    rj = os.path.join(r_dir or os.path.expanduser('~/c7d/r'), name, 'r.json')
    if os.path.exists(rj):
        rsha = json.load(open(rj))['held']['ids_sha256']
        assert rsha == res['held']['ids_sha256'], f'held ids differ from R ({rsha} vs {res["held"]["ids_sha256"]})'
        res['held']['matches_r'] = True
    held_m = subsample(held, skills_limit) if skills_limit else held
    M0, vocab, meta = sleep.load_parent(model_path, device)
    M0.eval()
    sha = dict(M0=_sha_file(model_path))
    hk = (res['held']['ids_sha256'], held_per_family, skills_limit)
    kw = dict(pdir=pdir, meta=meta, vocab=vocab, device=device, resume=resume, log=log)
    models, cinfo = dict(M0=M0), {}
    for cell, (lr, kind) in CELLS.items():
        if lr not in lrs:
            continue
        t0 = time.time()
        m, cinfo[cell], sha[cell] = _stage(name=cell, key=_h('drift', sha['M0'], lr, kind, updates, n_reused, seed, held_per_family), fn=lambda lr=lr, kind=kind: _train_cell(M0, rpool, vocab, device, seed, lr, kind, updates, n_reused), **kw)
        models[cell] = m
        secs[cell] = time.time() - t0
        res.setdefault('cells', {})[cell] = dict(cinfo[cell])
        log(cell, cinfo[cell])
        save()
    # reproduction of R's W1e (same seed + 200 draw, lr 1e-3, reused)
    w1e = os.path.join(r_dir or os.path.expanduser('~/c7d/r'), name, 'W1e.pt')
    # measures
    hh, dh, c2, rows = {}, {}, {}, None
    for a, m in models.items():
        t0 = time.time()
        hh[a] = _cached(os.path.join(pdir, f'held_{a}.pkl'), ('held', sha[a], hk), lambda m=m: held_hits(m, held_m, device), resume, log, f'held {a}')
        rows, dh[a], p5, ia = _cached(os.path.join(pdir, f'skills_{a}.pkl'), ('skills', sha[a], skills_data, skills_limit), lambda m=m: skills_dev(m, skills_data, device, skills_limit), resume, log, f'skills {a}')[:4]
        dh[a] = (dh[a], p5, ia)
        c2[a] = _cached(os.path.join(pdir, f'c2_{a}.pkl'), ('c2', sha[a], dev_limit), lambda m=m: greedy_rows(m, dev, vocab, device), resume, log, f'c2 dev {a}')
        secs[f'measure_{a}'] = time.time() - t0
        log('measure', a, 'held %.2f' % (100 * sum(hh[a]) / len(hh[a])), 'dev %.2f' % ia)
    right = lambda a: [float(d['right']) for d in c2[a]]
    table = {}
    for a in models:
        row = dict(held_in_dist=100 * sum(hh[a]) / len(hh[a]), dev_in_dist=dh[a][2], dev_pooled5=dh[a][1], c2_first_try=100 * sum(right(a)) / len(dev), stuck_rate=1 - sum(d['fit'] for d in c2[a]) / len(dev))
        if a != 'M0':
            hm_h, hm_d = harm_measure(hh['M0'], hh[a], held_m), harm_measure(dh['M0'][0], dh[a][0], rows)
            bt = dict(zip(('points', 'lo', 'hi'), c2_pilot.boot(right(a), right('M0'))))
            row.update(held_drop=hm_h['in_dist_drop'], held_fired=len(hm_h['fired']), held_fired_families=hm_h['fired'], dev_drop=hm_d['in_dist_drop'], dev_fired=len(hm_d['fired']), dev_fired_families=hm_d['fired'],
                       dev_passes=hm_d['passes'], c2_first_try_boot_vs_M0=bt, updates=cinfo[a]['updates'], rows=cinfo[a]['rows'], max_visits=cinfo[a]['max_visits'], seconds=cinfo[a]['train_seconds'])
        table[a] = row
    res['table'] = table
    if 'lr1e-3_reused' in models and os.path.exists(w1e):
        W1e, _, _ = sleep.load_parent(w1e, device)
        W1e.eval()
        he = held_hits(W1e, held_m, device)
        _, de, _, ie = skills_dev(W1e, skills_data, device, skills_limit)
        res['reproduces_W1e'] = dict(equal=bool(he == hh['lr1e-3_reused'] and de == dh['lr1e-3_reused'][0]), held_in_dist_W1e=100 * sum(he) / len(he), held_in_dist_cell=table['lr1e-3_reused']['held_in_dist'],
                                    dev_in_dist_W1e=ie, dev_in_dist_cell=table['lr1e-3_reused']['dev_in_dist'])
    fresh = [c for c in cinfo if c.endswith('fresh')]
    res['fresh_check'] = {c: dict(rows=cinfo[c]['rows'], requested=cinfo[c]['requested_rows'], max_visits=cinfo[c]['max_visits'], all_distinct_once=cinfo[c]['max_visits'] == 1 and cinfo[c]['rows'] == cinfo[c]['requested_rows']) for c in fresh}
    if all(c in table for c in CELLS):
        res['marks'] = marks({c: table[c]['held_drop'] for c in CELLS})
    secs['total'] = time.time() - t00
    save()
    log('MARKS', res.get('marks', {}).get('drift_confirmed'), res.get('marks', {}).get('overfit_confirmed'), res.get('marks', {}).get('proved_wrong'))
    return res


def drift(models, out, **kw):
    os.makedirs(out, exist_ok=True)
    return {p: drift_parent(p, out, **kw) for p in models}


def driftreport(out, parents):
    """-> DIR/drift-report.json: per-parent marks and tables; a mark is true for the pair only when it holds on every parent; lists where the parents disagree."""
    res = {p: json.load(open(os.path.join(out, p, 'drift.json'))) for p in parents}
    mk = {p: x.get('marks') or {} for p, x in res.items()}
    names = list(RULES)
    rep = dict(parents=list(parents), per_parent={p: {k: mk[p].get(k) for k in names} for p in parents}, tables={p: x.get('table') for p, x in res.items()}, rules=RULES,
               disagree=[k for k in names if len({mk[p].get(k) for p in parents}) > 1])
    rep.update({k: all(mk[p].get(k) is True for p in parents) for k in names})
    json.dump(rep, open(os.path.join(out, 'drift-report.json'), 'w'), indent=1)
    return rep


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    sub = a.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('run'); q.add_argument('--model', nargs='+', required=True); q.add_argument('--out', required=True); q.add_argument('--skills-train', required=True); q.add_argument('--skills-data', required=True)
    q.add_argument('--updates', type=int, default=256); q.add_argument('--dev-limit', type=int); q.add_argument('--skills-limit', type=int); q.add_argument('--device', default='cpu'); q.add_argument('--threads', type=int)
    q.add_argument('--no-resume', action='store_true')
    q = sub.add_parser('report'); q.add_argument('--out', required=True); q.add_argument('--parents', nargs='+', default=['s100', 's101'])
    a = a.parse_args()
    if getattr(a, 'threads', None):
        torch.set_num_threads(a.threads)
    if a.cmd == 'report':
        print(json.dumps(driftreport(a.out, tuple(a.parents)), indent=1))
    else:
        ex = os.path.expanduser
        drift(a.model, a.out, skills_train=ex(a.skills_train), skills_data=ex(a.skills_data), updates=a.updates, dev_limit=a.dev_limit, skills_limit=a.skills_limit, device=a.device, resume=not a.no_resume)
