"""One-wave CPU supervisor, outcome-blind timing, fixed-final-checkpoint scoring."""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time
import traceback

import astra_canonical_operator as A
import astra_canonical_operator_panels as P
import premonition_memnn_compare as C

torch, OUT, ROOT = A.torch, P.OUT, P.ROOT
PYTHON = '/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12'


def configure():
    A.data.bootstrap()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1


def check_manifest():
    path = OUT/'astra_canonical_operator_launch.json'
    manifest = json.loads(path.read_text())
    for name, expected in manifest['files'].items():
        if C.sha(ROOT/name) != expected:
            raise RuntimeError(f'registered file changed: {name}')
    return manifest


def deadline(start, cap):
    if time.monotonic()-start >= cap:
        raise TimeoutError(f'wave work deadline {cap}s')


@torch.no_grad()
def score_cell(model, panel, wave_start, work_cap):
    units, records = [], []
    cost = {k: dict(seconds=0., flops=0, calls=0, batches=0) for k in ('R','M','oracle')}
    for sides in P.chunks(panel):
        per_side = {}
        for side, (x, targets) in sides.items():
            deadline(wave_start, work_cap)
            # Native model methods receive only four visible tensors, never paths.
            started = time.monotonic()
            m = model(x).argmax(-1).tolist()
            cost['M']['seconds'] += time.monotonic()-started
            cost['M']['flops'] += A.inference_flops(x, model)
            cost['M']['calls'] += len(targets)
            cost['M']['batches'] += 1
            started = time.monotonic()
            r = A.execute(model, x)
            cost['R']['seconds'] += time.monotonic()-started
            paths = A.truth_paths(x)
            assert [p[-1]['target'] for p in paths] == list(targets)
            started = time.monotonic()
            oracle = A.oracle_inputs(model, x, paths)
            cost['oracle']['seconds'] += time.monotonic()-started
            for policy, info in (('R', r),('oracle',oracle)):
                for key in ('flops','calls','batches'):
                    cost[policy][key] += info[key]
            per_side[side] = []
            for i, (target, path) in enumerate(zip(targets,paths)):
                truth = [s['target'] for s in path]
                emitted = r['emitted'][i]
                pred_oracle = oracle['predictions'][i]
                links = [j for j,s in enumerate(path) if s['operation'] == A.LINK]
                native_links = [int(j < len(emitted) and emitted[j] == truth[j]) for j in links]
                row = dict(target=int(target), M=m[i], R=r['predictions'][i], emitted=emitted,
                           truth_path=truth, oracle=pred_oracle,
                           native_links=native_links,
                           oracle_links=[int(pred_oracle[j] == truth[j]) for j in links],
                           terminal_oracle=int(pred_oracle[-1] == truth[-1]),
                           native_joint=int(emitted == truth),
                           asker_cycle=bool(len(path)==3 and truth[1] == path[0]['entity']))
                per_side[side].append(row)
        for i in range(len(per_side['a'])):
            rows = {s:vals[i] for s,vals in per_side.items()}
            correct = {policy: all(row[policy] == row['target'] for row in rows.values()) for policy in ('R','M')}
            if panel.get('invariant',False):
                for policy in correct:
                    correct[policy] &= len({row[policy] for row in rows.values()}) == 1
            units.append({k:int(v) for k,v in correct.items()})
            records.append(dict(index=len(records), sides=rows, correct=units[-1]))
    assert len(units) == panel['n']
    diagnostics = {}
    for side in records[0]['sides']:
        rows = [r['sides'][side] for r in records]
        diagnostics[side] = dict(n=len(rows),
            native_links=[sum(r['native_links'][j] for r in rows) for j in range(len(rows[0]['native_links']))],
            oracle_links=[sum(r['oracle_links'][j] for r in rows) for j in range(len(rows[0]['oracle_links']))],
            terminal_oracle=sum(r['terminal_oracle'] for r in rows),
            native_joint=sum(r['native_joint'] for r in rows))
    split = {}
    if len(records[0]['sides']['a']['truth_path']) == 3:
        for is_cycle in (False,True):
            selected = [r for r in records if r['sides']['a']['asker_cycle'] == is_cycle]
            split['asker_cycle' if is_cycle else 'distinct_chain'] = dict(n=len(selected),
                R=sum(r['correct']['R'] for r in selected), M=sum(r['correct']['M'] for r in selected),
                native_joint=sum(r['sides']['a']['native_joint'] for r in selected))
    return dict(n=len(units), R=sum(u['R'] for u in units), M=sum(u['M'] for u in units),
                gain=sum(u['R'] and not u['M'] for u in units), loss=sum(u['M'] and not u['R'] for u in units),
                diagnostics=diagnostics, cycle_split=split, costs=cost, records=records)


def timing_worker(index, folder):
    # Nonregistered initialization/data seeds. No model, loss, accuracy, prediction,
    # optimizer state or random state is serialized or printed from this function.
    m = A.new_model(993100+index)
    optimizer = A.T.optimizer_for(m)
    rng = random.Random(993200+index)
    (folder/f'ready-{index}').touch(exist_ok=False)
    while not (folder/'start').exists():
        time.sleep(.02)
    start, intervals, flops = time.monotonic(), [], 0
    for step in range(50):
        t = time.monotonic()
        b = A.training_batch(rng,16,forbidden={'timing-overhead-placeholder'})
        flops += A.training_flops(b,m)
        A.training_step(m,optimizer,b,step)
        intervals.append(time.monotonic()-t)
    elapsed = time.monotonic()-start
    del optimizer, b
    gc.collect()
    from premonition.toy_ladder import LadderSpec
    panel = P.generate('c3_own_heldout_two_hop',n=512,
                       namespace='astra-canonical-operator-timing-panel',
                       spec=LadderSpec(entities=12),extra_link=True)
    m.eval()
    timing = {p:dict(seconds=0.,flops=0) for p in ('R','M','full_path_oracle')}
    with torch.no_grad():
        for sides in P.chunks(panel):
            x,_ = sides['a']
            paths = A.truth_paths(x)
            t = time.monotonic()
            m(x)
            timing['M']['seconds'] += time.monotonic()-t
            timing['M']['flops'] += A.inference_flops(x,m)
            t = time.monotonic()
            r = A.execute(m,x)
            timing['R']['seconds'] += time.monotonic()-t
            timing['R']['flops'] += r['flops']
            del r
            t = time.monotonic()
            oracle = A.oracle_inputs(m,x,paths)
            timing['full_path_oracle']['seconds'] += time.monotonic()-t
            timing['full_path_oracle']['flops'] += oracle['flops']
            del oracle
    result = dict(updates=50, updates_per_second=50/elapsed,
                  tail40_updates_per_second=40/sum(intervals[-40:]),
                  training_flops=flops, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  evaluation_512_twelve_person_three_hop=timing)
    C.write_new(folder/f'timing-{index}.json',result)


def worker(seed, wave_start):
    started = time.monotonic()
    folder = OUT/f'astra_canonical_operator_seed-{seed}'
    folder.mkdir(exist_ok=False)
    updates = 0
    try:
        manifest = check_manifest()
        params = manifest['schedule']
        forbidden = set(json.loads(Path(manifest['exclusion_path']).read_text()))
        m = A.new_model(seed)
        assert m.parameters_count() == 79316
        initial = C.fingerprint(m)
        optimizer = A.T.optimizer_for(m)
        rng = random.Random(1101)
        training_start = time.monotonic()
        flops = 0
        for step in range(params['updates']):
            deadline(wave_start,params['work_seconds'])
            if time.monotonic()-training_start >= params['training_seconds']:
                raise TimeoutError('registered training time cap')
            b = A.training_batch(rng,16,forbidden)
            flops += A.training_flops(b,m)
            A.training_step(m,optimizer,b,step)
            updates += 1
            if updates % 500 == 0:
                print(json.dumps(dict(seed=seed,updates=updates,training_seconds=time.monotonic()-training_start)),flush=True)
        train_seconds = time.monotonic()-training_start
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=m.state_dict(),seed=seed,updates=updates,
                        architecture=dict(vocab=68,width=48,heads=4,steps=3),
                        launch_sha256=C.sha(OUT/'astra_canonical_operator_launch.json')),checkpoint)
        final_fingerprint = C.fingerprint(m)
        training = dict(seed=seed,updates=updates,seconds=train_seconds,flops=flops,
                        initial_fingerprint=initial,final_fingerprint=final_fingerprint,
                        checkpoint_sha256=C.sha(checkpoint),canonical_records=updates*16*6,
                        monolithic_records=updates*16*2,overlap_checks=updates*16*8,
                        heldout_compositions=0,three_hop=0,twelve_person=0)
        C.write_new(folder/'training.json',training)
        del m, optimizer, b
        gc.collect()
        # Evaluation uses only the saved final checkpoint, loaded once.
        saved = P.load(checkpoint)
        model = A.CanonicalOperator(**saved['architecture'])
        model.load_state_dict(saved['state_dict'],strict=True)
        model.eval()
        assert C.fingerprint(model) == final_fingerprint
        results = {}
        for name,row in manifest['panels'].items():
            deadline(wave_start,params['work_seconds'])
            assert C.sha(row['path']) == row['sha256']
            panel = P.load(row['path'])
            result = score_cell(model,panel,wave_start,params['work_seconds'])
            C.write_new(folder/f'{name}.json',result)
            results[name] = {k:v for k,v in result.items() if k != 'records'}
            print(json.dumps(dict(seed=seed,cell=name,R=result['R'],M=result['M'])),flush=True)
        assert C.fingerprint(model) == final_fingerprint
        assert C.sha(checkpoint) == training['checkpoint_sha256']
        check_manifest()
        deadline(wave_start,params['work_seconds'])
        C.write_new(folder/'completion.json',dict(seed=seed,complete=True,updates=updates,
                    seconds=time.monotonic()-started,wave_elapsed=time.monotonic()-wave_start,
                    peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    final_checkpoint_only=True,weights_unchanged=True,registered_files_unchanged=True,results=results))
    except BaseException as exc:
        C.write_new(folder/'failure.json',dict(seed=seed,complete=False,updates=updates,
                    seconds=time.monotonic()-started,error=repr(exc),traceback=traceback.format_exc()))
        raise


def supervise(timing=False):
    if timing:
        folder = OUT/'astra_canonical_operator_rehearsal'
        folder.mkdir(exist_ok=False)
        cap = 300
    else:
        manifest = check_manifest()
        folder = OUT/'astra_canonical_operator_wave'
        folder.mkdir(exist_ok=False)
        cap = manifest['schedule']['terminate_seconds']
    start = time.monotonic()
    C.write_new(folder/'started.json',dict(unix=time.time(),monotonic=start,cap_seconds=cap))
    procs, logs = [], []
    env = dict(os.environ, OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    for seed in (0,1,2):
        handle = (folder/f'seed-{seed}.log').open('x')
        logs.append(handle)
        args = [PYTHON,'-B',str(Path(__file__).resolve()),'timing-worker' if timing else 'worker',
                '--seed',str(seed),'--wave-start',str(start)]
        procs.append(subprocess.Popen(args,stdout=handle,stderr=subprocess.STDOUT,env=env,start_new_session=True))
    if timing:
        while not all((folder/f'ready-{i}').exists() for i in range(3)):
            if any(p.poll() is not None for p in procs) or time.monotonic()-start > 60:
                for p in procs:
                    if p.poll() is None: p.terminate()
                raise RuntimeError('rehearsal synchronization failed')
            time.sleep(.05)
        (folder/'start').touch(exist_ok=False)
    while any(p.poll() is None for p in procs):
        if time.monotonic()-start >= cap-2:
            for p in procs:
                if p.poll() is None: p.terminate()
            time.sleep(.2)
            for p in procs:
                if p.poll() is None: p.kill()
            break
        time.sleep(.2)
    exits = [p.wait() for p in procs]
    for f in logs: f.close()
    complete = all(c == 0 for c in exits)
    if not timing:
        complete &= all((OUT/f'astra_canonical_operator_seed-{s}/completion.json').exists() for s in (0,1,2))
    C.write_new(folder/'completion.json',dict(seconds=time.monotonic()-start,exit_codes=exits,
                complete=complete,parallel_processes=3,cap_seconds=cap))
    print(json.dumps(dict(seconds=time.monotonic()-start,exit_codes=exits,complete=complete)),flush=True)
    if not complete: sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['rehearse','timing-worker','launch','worker'])
    parser.add_argument('--seed',type=int)
    parser.add_argument('--wave-start',type=float)
    args = parser.parse_args()
    configure()
    if args.command == 'rehearse': supervise(True)
    elif args.command == 'timing-worker': timing_worker(args.seed,OUT/'astra_canonical_operator_rehearsal')
    elif args.command == 'launch': supervise(False)
    else: worker(args.seed,args.wave_start)
