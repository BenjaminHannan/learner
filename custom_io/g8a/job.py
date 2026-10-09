"""One 8a job: build the pool of one rung for one seed, then train B2, PT and LLM (and, at 30M, the public model) in sequence on it.

PC / local queue mode (the default way to run 8a; custom_io/queue_local/4x-pc-8a-*.txt, via local_runner `g8a:` lines):
  python -m custom_io.g8a.job --rung 10M --seed 400 --work WORK --local --out WORK/results/Q/NAME --skills WORK/data --big-data WORK/data_big \
      --data8a WORK/data8a [--arms B2 PT LLM] [--speed-json SPEED.json] [--lr-scale 0.5] [--public pythia31m]
  Outputs OUT/<arm>/ (train.py's RESULT.json, stdout.txt, ...), OUT/pool_MANIFEST.json, OUT/box.json and OUT/RESULT.json (the job summary; local_runner reads it as "done").
  The pool (WORK/pools/<own rung>-<web slice>-s<seed>-a<max ans>/, large) is shared by the 3M and 10M rungs of a seed (addendum B1) and built once: callers wait on a lock.
Vast mode (fallback; no --local): outputs under WORK/w/ and every folder is printed as RBEGIN|name|sha|size / R|name|base64 / REND|name lines (vast.py collect).
  python -m custom_io.g8a.job --rung 3M --seed 400 --work /job --skills /job/data --own72 /job/own72 --web /job/web/slice_rung10.jsonl --big-data /job/data_big [--maxh 5]

Never decides spend: the caps are --maxh (whole job) and --minutes per arm. A run whose size is outside its band is refused before anything is built.
Gradient accumulation: --accum B2=2,PT=1 or --speed-json from g8a.speed (arms whose peak memory passed its limit); always 256 rows per update.
"""
import argparse, base64, hashlib, io, json, math, os, re, shutil, subprocess, sys, tarfile, time
from custom_io.g8a import caps as CP
from custom_io.g8a import configs as C
from custom_io.g8a import pool as P

EVENT = re.compile(r'"event"|Traceback|Error|error|RESULT')


def emit(work_w, name):
    """Print the finished folder `name` (without *.pt, stdout.txt) as base64 lines, after writing its events file."""
    d = os.path.join(work_w, name)
    so = os.path.join(d, 'stdout.txt')
    if os.path.exists(so):
        with open(so, errors='replace') as f, open(os.path.join(d, 'stdout.events.txt'), 'w') as g:
            for ln in f:
                if EVENT.search(ln):
                    g.write(ln[:4000].rstrip('\n') + '\n')
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as t:
        t.add(d, arcname=name, filter=lambda ti: None if ti.name.endswith('.pt') or ti.name.endswith('stdout.txt') else ti)
    raw = buf.getvalue()
    print('RBEGIN|%s|%s|%d' % (name, hashlib.sha256(raw).hexdigest(), len(raw)))
    b = base64.b64encode(raw).decode()
    for i in range(0, len(b), 300):
        print('R|%s|%s' % (name, b[i:i + 300]))
    print('REND|' + name, flush=True)


def _locked(path, wait=30, stale=6 * 3600):
    """O_EXCL lock file; returns when we hold it (the caller removes it)."""
    while True:
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return
        except FileExistsError:
            if time.time() - os.path.getmtime(path) > stale:
                os.remove(path)
                continue
            time.sleep(wait)


def get_caps(a, pdir):
    """The caps of the whole ladder (addendum F d: set once from the largest pool, the same at every rung), written to the pool dir beside a report of the rows
    of THIS pool and the dev splits that any cap touches (target 0; a run with a touched row stops instead of cutting it)."""
    f = os.path.join(pdir, 'caps.json')
    if os.path.exists(f):
        return json.load(open(f))
    dev = [os.path.join(pdir, 'dev')] + ([a.big_data] if a.big_data and os.path.isdir(a.big_data) else [])
    own72 = a.own72 or (os.path.join(a.data8a, 'own72') if a.data8a else None)
    web30 = a.web30 or (os.path.join(a.data8a, 'web', 'slice_rung30.jsonl') if a.data8a else None)
    pinned = a.caps_file or (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'caps_g.json') if not a.recompute_caps else None)
    if pinned and a.scale == 1.0:       # addendum G: one set of caps for every rung and every box; a pool row that does not fit stops the job (checked below), nothing is cut
        caps = json.load(open(pinned))
    elif own72 and web30 and os.path.exists(web30) and a.scale == 1.0:
        gf = os.path.join(a.work, 'caps-global.json')
        _locked(gf + '.lock')
        try:
            if not os.path.exists(gf):
                t = time.time()
                caps = CP.compute_global(own72, web30, dev, a.max_ans)
                caps['compute_s'] = round(time.time() - t)
                json.dump(caps, open(gf, 'w'), indent=1)
                print('global caps', json.dumps(caps), flush=True)
            caps = json.load(open(gf))
        finally:
            os.remove(gf + '.lock')
    else:       # dry run: the pool's own longest cases
        caps = CP.compute([os.path.join(pdir, 'train.jsonl')] + dev)
    paths = [os.path.join(pdir, 'train.jsonl')] + dev
    rep = CP.report(caps, paths, progs=True)        # program steps too: a few minutes per pool, against hours of training
    rep_dev = CP.report(caps, dev, progs=True)
    rep['rows_over_caps_dev_with_programs'] = rep_dev['rows_over_caps']
    json.dump(caps, open(f, 'w'))
    json.dump(rep, open(os.path.join(pdir, 'caps_report.json'), 'w'), indent=1)
    bad = {k: max(rep['rows_over_caps'][k], rep_dev['rows_over_caps'][k]) for k in rep['rows_over_caps'] if rep['rows_over_caps'][k] or rep_dev['rows_over_caps'][k]}
    if bad:
        os.remove(f)
        sys.exit('rows touch the global caps (a cap would cut them): ' + json.dumps(bad) + ' -> recompute caps-global.json from the larger pool')
    return caps


def parse_accum(s, speed_json, rung):
    acc = {}
    if speed_json and os.path.exists(speed_json):
        sp = json.load(open(speed_json))
        for arm, r in (sp.get('rungs', {}).get(rung) or {}).items():
            if isinstance(r, dict) and r.get('accum') and not arm.startswith('_'):
                acc[arm] = int(r['accum'])
    for kv in filter(None, (s or '').split(',')):
        k, v = kv.split('=')
        acc[k.strip()] = int(v)
    return acc


def get_pool(a, man_out_dir):
    """Build (or reuse) the pool dir of this rung and seed. Returns (dir, manifest)."""
    R = C.RUNGS[a.rung]
    assert R['own_rung'] is not None, f'the {a.rung} pool is not built (the 600M pool is the data thread\'s and waits for a GO)'
    key = 'p%d-%s-s%d-a%d' % (R['own_rung'], R['web'], a.seed, a.max_ans)
    pdir = os.path.join(a.work, 'pools', key)
    os.makedirs(os.path.dirname(pdir), exist_ok=True)
    lock = pdir + '.lock'
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(lock) > 4 * 3600:
                os.remove(lock)
                continue
            print('waiting for another job to finish building', key, flush=True)
            time.sleep(30)
    try:
        mf = os.path.join(pdir, 'MANIFEST.json')
        if os.path.exists(mf) and not a.scale != 1.0:
            man = json.load(open(mf))
            if os.path.getsize(os.path.join(pdir, 'train.jsonl')) == man['train_bytes'] and P.sha256_file(os.path.join(pdir, 'train.jsonl')) == man['train_sha256']:
                print('pool reused', key, flush=True)
                return pdir, man
        if a.own72:
            own72 = a.own72
        else:
            own72 = os.path.join(a.data8a, 'own72') if a.data8a else None
        web = a.web or os.path.join(a.data8a, 'web', 'slice_%s.jsonl' % R['web'])
        ns = argparse.Namespace(rung=a.rung, seed=a.seed, out=pdir, own72=own72, own=None if own72 else [os.path.join(a.skills, 'train.jsonl')] + list(a.own_extra), web=web,
                                dev=os.path.join(a.skills, 'dev'), max_ans=a.max_ans, allow_short=a.allow_short, keep_mix=not a.no_keep_mix, scale=a.scale,
                                overlap_index=a.overlap_index, data_pool=a.data_pool)
        return pdir, P.build(ns)
    finally:
        os.remove(lock)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rung', choices=list(C.RUNGS), required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--local', action='store_true', help='PC mode: arms go to OUT/<arm>/, nothing is printed for collection')
    ap.add_argument('--out', help='--local: the output folder')
    ap.add_argument('--skills', required=True, help='skills build dir: dev/ (the pooled-5 dev splits) and train.jsonl')
    ap.add_argument('--data8a', help='get_data.py output dir (own72/ and web/); gives --own72 and --web')
    ap.add_argument('--own72', help='data_pool own72 dir (overrides --data8a)')
    ap.add_argument('--own-extra', nargs='*', default=[], help='without own72: more own-row files PATH:WEIGHT')
    ap.add_argument('--caps-file', help='pinned caps json (default: g8a/caps_g.json, the addendum G caps)')
    ap.add_argument('--recompute-caps', action='store_true', help='size the caps from own72 + the rung30 slice instead of using the pinned file (needs a dated addendum first)')
    ap.add_argument('--web30', help='web slice of the 30M rung (default DATA8A/web/slice_rung30.jsonl): the global caps are sized from it')
    ap.add_argument('--web', help='web slice jsonl (default: DATA8A/web/slice_<rung slice>.jsonl)')
    ap.add_argument('--big-data')
    ap.add_argument('--arms', nargs='+', default=list(C.ARMS), choices=list(C.ALL_ARMS), help='B3 (B3-GROUP1-BUILD): the b3 model at the rung, config from configs.b3_cfg; --b2-extra adds switches to it')
    ap.add_argument('--max-ans', type=int, default=P.HYGIENE_ANS, help='data hygiene limit on answer chars for the pool builder (NOT a model cap: model caps come from caps.json)')
    ap.add_argument('--b2-extra', default='{}', help='JSON reader switches for B2 (stage 2b pick), e.g. {"eg_embed": true}')
    ap.add_argument('--lr-scale', type=float, default=1.0)
    ap.add_argument('--public', choices=['none'] + list(C.PUBLIC), default='none', help='30M rung only: add the public-model arm of mark 5 (pinned revision)')
    ap.add_argument('--maxh', type=float, default=0, help='stop starting arms after this many hours of the job (0 = no cap)')
    ap.add_argument('--minutes', nargs='*', type=float, default=[], help='per-arm wall caps in minutes, in arm order (a capped run is flagged time_cap)')
    ap.add_argument('--dph', type=float, default=0, help='dollars per hour of the box, for the cost line only')
    ap.add_argument('--accum', default='', help='ARM=K,... gradient-accumulation micro-batches (256 rows per update either way)')
    ap.add_argument('--speed-json', help='speed.json from g8a.speed: its per-arm accum values are used')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--scale', type=float, default=1.0, help='DRY RUNS ONLY: shrink the pool and seen budgets')
    ap.add_argument('--train-extra', default='', help='extra train.py flags appended last (DRY RUNS: --batch 16 --eval-max 16)')
    ap.add_argument('--steps', type=int, help='DRY RUNS ONLY: override the scheduled steps')
    ap.add_argument('--overlap-index')
    ap.add_argument('--data-pool', default='data_pool')
    ap.add_argument('--no-emit', action='store_true')
    ap.add_argument('--allow-short', action='store_true')
    ap.add_argument('--no-keep-mix', action='store_true')
    a = ap.parse_args(argv)
    t0 = time.time()
    b2_extra = json.loads(a.b2_extra)
    if b2_extra.get('eg_embed'):        # test 8a-G: every arm that runs has the same frozen-Gemma front; the LLM arm and the public model have none
        assert set(a.arms) <= {C.B2_ARM, C.PT_ARM, C.B3_ARM} and a.public == 'none', 'with eg_embed only the B2, PT and B3 arms run (plain_lm and the public model have no Gemma front)'
    assert a.public == 'none' or a.rung == '30M', 'the public-model arm belongs to the 30M rung (mark 5)'
    arms = list(a.arms) + ([C.PUB_ARM] if a.public != 'none' else [])
    tag = '8a-%s-s%d' % (a.rung, a.seed)
    if a.local:
        assert a.out, '--local needs --out'
        base = a.out
        arm_dir = lambda arm: os.path.join(base, arm)
        emit_on = False
    else:
        base = os.path.join(a.work, 'w')
        arm_dir = lambda arm: os.path.join(base, '%s-%s' % (tag, arm))
        emit_on = not a.no_emit
    os.makedirs(base, exist_ok=True)
    if a.data8a and not a.own72 and os.path.exists(os.path.join(a.data8a, 'REFUSED.txt')):
        sys.exit('the 8a data step refused to run: ' + open(os.path.join(a.data8a, 'REFUSED.txt')).read().strip())
    if a.data8a and not a.own72 and not os.path.exists(os.path.join(a.data8a, 'READY.json')):      # the queue's first line (g8a-data:) is still building it
        print('waiting for', os.path.join(a.data8a, 'READY.json'), flush=True)
        t_wait = time.time()
        while not os.path.exists(os.path.join(a.data8a, 'READY.json')):
            assert time.time() - t_wait < 8 * 3600, 'the 8a data was never ready'
            if os.path.exists(os.path.join(a.data8a, 'REFUSED.txt')):
                sys.exit('the 8a data step refused to run: ' + open(os.path.join(a.data8a, 'REFUSED.txt')).read().strip())
            time.sleep(30)
    pdir, man = get_pool(a, base)
    caps = get_caps(a, pdir)
    CP.apply(caps)                                  # in this process too, so the parameter counts below include the sized position / place tables
    b2_extra = dict(b2_extra, n_loops=CP.n_loops_needed(caps)) if CP.n_loops_needed(caps) > 8 else b2_extra
    old = [x for x in a.arms if x != C.B3_ARM]
    cfgs, counts = C.sizes(a.rung, b2_extra) if old else ({}, {})
    if old:
        C.check_bands(a.rung, cfgs, counts, exact_3m=all(caps[k] == CP.TODAY[k] for k in CP.TODAY))   # a run outside its band does not count: refuse before training
    if C.B3_ARM in a.arms:          # B3: n_loops (and any extra switch) come in through --b2-extra; its trained count is checked against its rung band
        cfgs[C.B3_ARM] = C.b3_cfg(a.rung, b2_extra)
        counts[C.B3_ARM] = C.check_b3(a.rung, cfgs[C.B3_ARM])
        sz = C.b3_sizes(cfgs[C.B3_ARM])
        print('B3 size', json.dumps(sz), flush=True)
    steps = a.steps or man['schedule']['steps']
    pm_dir = base if a.local else os.path.join(base, tag + '-pool')
    os.makedirs(pm_dir, exist_ok=True)
    json.dump(man, open(os.path.join(pm_dir, 'pool_MANIFEST.json' if a.local else 'MANIFEST.json'), 'w'), indent=1)
    for f in ('caps.json', 'caps_report.json'):         # E3: the caps used and the rows any cap touches (target 0), beside the results
        shutil.copy2(os.path.join(pdir, f), os.path.join(pm_dir, f))
    if emit_on:
        emit(base, tag + '-pool')
    accum = parse_accum(a.accum, a.speed_json, a.rung)
    box = dict(rung=a.rung, seed=a.seed, steps=steps, cfgs=cfgs, trained_params=counts, lr=C.RUNGS[a.rung]['lr'] * a.lr_scale, lr_scale=a.lr_scale, caps=caps,
               maxh=a.maxh, dph=a.dph, accum=accum, arms={}, started_unix=t0, pool_build_s=round(time.time() - t0, 1), pool_train_sha256=man['train_sha256'],
               pool_schedule=man['schedule'], b2_extra=b2_extra)
    qdir = None
    if a.public != 'none':       # the same question rows, no web fill-in rows (the public model was pretrained on web text); same passes over them
        qdir = P.question_only(pdir, os.path.join(a.work, 'poolq-%s-s%d' % (a.rung, a.seed)))
        box['public'] = dict(C.PUBLIC[a.public], key=a.public, question_rows=man['own']['rows'])
    dev_flag = [] if a.device == 'auto' else ['--device', a.device]
    for k, arm in enumerate(arms):
        if a.maxh and (time.time() - t0) / 3600 >= a.maxh:
            box['arms'][arm] = dict(status='skipped_maxh')
            continue
        out = arm_dir(arm)
        os.makedirs(out, exist_ok=True)
        mins = a.minutes[k] if k < len(a.minutes) else None
        if arm == C.PUB_ARM:
            pb = C.PUBLIC[a.public]
            psteps = a.steps or int(math.ceil(man['schedule']['passes'] * man['own']['rows'] / pb['batch']))
            cmd = [sys.executable, '-m', 'custom_io.hf_baseline', '--hf-id', pb['hf_id'], '--revision', pb['revision'], '--mode', 'finetune', '--target', 'steps', '--calc',
                   '--data', qdir, '--steps', str(psteps), '--batch', str(pb['batch']), '--lr', repr(pb['lr'] * a.lr_scale if a.lr_scale != 1 else pb['lr']), '--seed', str(a.seed),
                   '--bf16', '--log-every', '500', '--final-eval', '--out', out] + (['--minutes', repr(mins)] if mins else []) + dev_flag
            box['public']['steps'] = psteps
        else:
            args = C.train_args(a.rung, arm, a.seed, steps, pdir, out=out, minutes=mins, lr=C.RUNGS[a.rung]['lr'] * a.lr_scale,
                                b2_extra=b2_extra, big_data=a.big_data, caps=os.path.join(pdir, 'caps.json'))
            if accum.get(arm, 1) > 1:
                args += ['--accum', str(accum[arm])]
            cmd = [sys.executable, '-m', 'custom_io.train'] + args + dev_flag
        cmd += a.train_extra.split()
        ta = time.time()
        with open(os.path.join(out, 'stdout.txt'), 'w') as so:
            rc = subprocess.call(cmd, stdout=so, stderr=subprocess.STDOUT)
        res = {}
        if os.path.exists(os.path.join(out, 'RESULT.json')):
            res = json.load(open(os.path.join(out, 'RESULT.json')))
        box['arms'][arm] = dict(rc=rc, status=res.get('status', 'no_result'), wall_s=round(time.time() - ta, 1), steps=res.get('steps'), steps_per_s=res.get('steps_per_s'),
                                n_params=res.get('n_params'), cmd=' '.join(cmd), accum=accum.get(arm, 1), peak_mem_mib=res.get('peak_mem_mib'))
        if emit_on:
            emit(base, '%s-%s' % (tag, arm))
    box['wall_s'] = round(time.time() - t0, 1)
    box['cost_usd'] = round(box['wall_s'] / 3600 * a.dph, 3)
    if a.local:
        json.dump(box, open(os.path.join(base, 'box.json'), 'w'), indent=1)
        json.dump(dict(status='ok' if all(v.get('rc') == 0 for v in box['arms'].values()) else 'arm_failed', job=box), open(os.path.join(base, 'RESULT.json'), 'w'), indent=1)
    else:
        os.makedirs(os.path.join(base, tag + '-box'), exist_ok=True)
        json.dump(box, open(os.path.join(base, tag + '-box', 'box.json'), 'w'), indent=1)
        if emit_on:
            emit(base, tag + '-box')
    print(json.dumps({k: box[k] for k in ('rung', 'seed', 'steps', 'wall_s', 'cost_usd')}), flush=True)
    return box


if __name__ == '__main__':
    main()
