"""G7: English paraphrase pilot training worker (query-only, notebook=None).

Four runs in fixed order: seed0 control, seed0 treatment, seed1 control, seed1
treatment; 2304 updates each from the same parent per seed, continuing the
parent's Adam state. The only arm difference is the auxiliary frame (control:
source reconstruction; treatment: supervised paraphrase); QA frames and order
are shared. Loss = unchanged human_loss only (no action/pointer/extra terms).

Conventions follow train_contextual_lr_stability_windows_v1.py: positive config
allowlist, stdlib --check, owned-stdin GO handshake, budget guards (wall, output,
free disk, CUDA reservation), per-update TRAIN-RAW.jsonl, FIRST-UPDATE.json,
durable reload-verified checkpoints, CLOSED/FAILED receipts. Additionally:
resume checkpoints every resume_every_updates (resume-equivalence is tested
bit-exactly on CPU), matched-asserts across arms before update 1, and an
optional segment limit so Stage B (first 72 updates) can run as its own segment.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402
import english_full_pilot_schedule_v1 as schedule_module  # noqa: E402

SCHEMA = 'premonition.English-paraphrase-pilot-train.v1'
RUN_ORDER = ((0, 'control'), (0, 'treatment'), (1, 'control'), (1, 'treatment'))
TOTAL = schedule_module.UPDATES
GO_LINE = 'BEGIN ENGLISH PARAPHRASE PILOT\n'
MATCHED_FIELDS = ('parent_checkpoint_sha256', 'QA_frames_in_order_sha256', 'schedule_sha256',
                  'optimizer_sha256', 'RNG_sha256', 'code_sha256', 'initial_model_sha256')


class SegmentPaused(Exception):
    """Clean stop after the configured segment limit; resume continues exactly."""


def run_folder(out, seed, arm):
    return Path(out) / ('seed%d' % seed) / arm


def matched_record(ctx, seed, arm, parent_sha, records, modules, opt, rng, torch):
    qa = [ctx.frames_by_index[r[arm + '_frame_index']]['frame_sha256'] for r in records if r['task_role'] == 'QA']
    return {'seed': seed, 'arm': arm, 'parent_checkpoint_sha256': parent_sha,
            'QA_frames_in_order_sha256': common.canonical(qa),
            'schedule_sha256': common.canonical(records),
            'optimizer_sha256': common.tree_digest(opt.state_dict(), torch),
            'RNG_sha256': common.tree_digest(rng, torch),
            'code_sha256': common.canonical(ctx.code),
            'initial_model_sha256': common.tree_digest({n: m.state_dict() for n, m in modules}, torch)}


def check_matched(out, seed, arm, record):
    other = 'treatment' if arm == 'control' else 'control'
    path = run_folder(out, seed, other) / 'MATCHED.json'
    if path.is_file():
        theirs = common.read_json(path)
        diff = [k for k in MATCHED_FIELDS if theirs.get(k) != record[k]]
        if diff:
            raise ValueError('matched-arm asserts differ: ' + ','.join(diff))
        return True
    return False


def latest_resume(folder):
    best = None
    for receipt in sorted(Path(folder).glob('resume-*.json')):
        value = common.read_json(receipt)
        cp = Path(folder) / value['checkpoint']
        if cp.is_file() and common.digest(cp) == value['checkpoint_sha256']:
            if best is None or value['update'] > best['update']:
                best = value
    return best


def train_step(rt, ctx, modules, named, opt, frame_index, participation, nonzero):
    torch = rt.torch
    parts = runtime.module_dict(modules)
    opt.zero_grad(set_to_none=True)
    ids, mask, labels = ctx.tokens[frame_index]
    h, aux = runtime.english_graph(rt, parts['core'], parts['reader'], ctx.features[frame_index], mask)
    per, prediction, stats = runtime.english_loss(rt, ctx.lm, ctx.dec, h, mask, labels)
    loss = per.mean()
    contract = {}

    def before_step():
        contract.update(runtime.gradient_contract(rt, modules, ctx.lm))
        if any(not r['finite'] for r in contract['component_gradients'].values()):
            raise RuntimeError('nonfinite gradient')
        if contract['unexpected_gradient_count']:
            raise RuntimeError('frozen LM/halt/tool/unused core parameter received a gradient')
        for name, p in named:
            if p.grad is not None:
                participation[name] += 1
                if bool(torch.count_nonzero(p.grad)):
                    nonzero[name] += 1
    preclip = rt.sealed.numeric_optimizer_step(loss, opt, [p for _, p in named], torch, before_step)
    if not bool(torch.stack([torch.isfinite(p.detach()).all() for _, p in named]).all()):
        raise ValueError('nonfinite trainable parameter after update')
    return {'frame_index': frame_index, 'input_tokens_with_EOS': int(ids.shape[1]), **stats,
            'preclip_norm': float(preclip), 'sparse_auxiliary_observed_excluded': float(aux.detach()),
            'teacherforced_argmax': prediction.detach().cpu().tolist(), **contract}


def save_verified(rt, ctx, path, payload):
    torch = rt.torch
    ctx.save_checkpoint(path, payload)
    restored = torch.load(path, map_location='cpu', weights_only=True)
    if not common.state_equal(payload, restored, torch):
        raise ValueError('durable checkpoint reload differs')
    return {'path': path.name, 'sha256': common.digest(path)}


def train_run(rt, ctx, seed, arm, records, saved, parent_sha):
    """One arm-seed run, resumable. Returns the CLOSED record."""
    torch = rt.torch
    folder = run_folder(ctx.out, seed, arm)
    if (folder / 'CLOSED.json').is_file():
        closed = common.read_json(folder / 'CLOSED.json')
        cp = folder / closed['checkpoint']['path']
        if common.digest(cp) != closed['checkpoint']['sha256']:
            raise ValueError('closed run checkpoint changed')
        return closed
    folder.mkdir(parents=True, exist_ok=True)
    total = ctx.total_updates
    if len(records) != total:
        raise ValueError('schedule length differs from the run update total')
    frames = [r[arm + '_frame_index'] for r in records]
    modules = runtime.build_modules(rt, ctx.dec, seed, ctx.device)
    named = runtime.restore_parent_modules(rt, saved, modules, ctx.lm)
    names = [n for n, _ in named]
    runtime.validate_parent_metadata(saved, names, ctx.parent_update)
    opt = runtime.make_optimizer(torch, [p for _, p in named])
    runtime.restore_adam(torch, opt, saved, named)
    parts = runtime.module_dict(modules)
    parent_rng = {k: saved[k] for k in ('torch_rng', 'cuda_rng', 'python_rng')}
    tool_before = common.module_fingerprint(parts['tool'], torch)
    halt_before = common.module_fingerprint(parts['core'].halt, torch)
    buffers_before = common.tree_digest(dict(parts['core'].named_buffers()), torch)
    lm_before = common.module_fingerprint(ctx.lm, torch)
    parent_steps = runtime.adam_steps(opt, named)
    matched = matched_record(ctx, seed, arm, parent_sha, records, modules, opt, parent_rng, torch)
    if not (folder / 'MATCHED.json').is_file():
        check_matched(ctx.out, seed, arm, matched)
        common.write_new_json(folder / 'MATCHED.json', matched)
    elif common.read_json(folder / 'MATCHED.json') != matched:
        raise ValueError('matched record differs from an earlier segment of this run')
    participation = Counter(saved['participation'])
    nonzero = Counter()
    cursor, rng = 0, parent_rng
    raw = folder / 'TRAIN-RAW.jsonl'
    resume = latest_resume(folder)
    if resume is not None:
        state = torch.load(folder / resume['checkpoint'], map_location='cpu', weights_only=True)
        if (state['schedule_sha256'] != matched['schedule_sha256'] or state['update'] != resume['update']
                or state['config_sha256'] != ctx.config_sha256 or state['optimizer_parameter_names'] != names):
            raise ValueError('resume checkpoint identity differs')
        for name, module in modules:
            module.load_state_dict(state[name], strict=True)
        opt.load_state_dict(copy.deepcopy(state['optimizer']))
        if not common.state_equal(opt.state_dict(), state['optimizer'], torch):
            raise ValueError('resumed Adam state differs')
        participation, nonzero = Counter(state['participation']), Counter(state['nonzero_gradient_updates'])
        cursor, rng = state['update'], {k: state[k] for k in ('torch_rng', 'cuda_rng', 'python_rng')}
        size = raw.stat().st_size if raw.exists() else 0
        if size < resume['raw_bytes']:
            raise ValueError('raw log shorter than resume watermark')
        with raw.open('rb') as handle:
            head = handle.read(resume['raw_bytes'])
            tail = handle.read()
        if hashlib.sha256(head).hexdigest() != resume['raw_sha256']:
            raise ValueError('raw log prefix differs from resume watermark')
        if tail:
            kept = folder / ('TRAIN-RAW-after-%d-interrupted-%d.jsonl' % (cursor, int(time.time())))
            with kept.open('xb') as handle:
                handle.write(tail)
            with raw.open('r+b') as handle:
                handle.truncate(resume['raw_bytes'])
        del state
    else:
        stamp = int(time.time())
        for name in ('TRAIN-RAW.jsonl', 'FIRST-UPDATE.json'):
            if (folder / name).exists():  # interrupted before the first resume checkpoint: keep, restart
                (folder / name).rename(folder / ('%s-interrupted-%d' % (name, stamp)))
        start = {**ctx.identity, 'seed': seed, 'arm': arm, 'parameter_names': names,
                 'parent_Adam_steps': parent_steps, 'optimizer_reset': False,
                 'parent_RNG_restored_before_first_update': True, 'matched': matched}
        if not (folder / 'RESUME.json').is_file():
            common.write_new_json(folder / 'RESUME.json', start)
        elif common.read_json(folder / 'RESUME.json') != start:
            raise ValueError('run start record differs from an earlier segment')
    common.restore_rng(rng, torch)  # last RNG-affecting preparation
    run_identity = {**ctx.identity, 'seed': seed, 'arm': arm}
    segment_done = 0
    previous = resume
    for update in range(cursor + 1, total + 1):
        ctx.guard()
        ctx.gpu_guard()
        frame_index = frames[update - 1]
        started = time.perf_counter()
        row = train_step(rt, ctx, modules, named, opt, frame_index, participation, nonzero)
        common.synchronize(torch)
        row.update({'update': update, 'task_role': records[update - 1]['task_role'],
                    'frame_sha256': ctx.frames_by_index[frame_index]['frame_sha256'],
                    'update_seconds': time.perf_counter() - started, 'gpu': ctx.gpu_guard()})
        common.append_jsonl(raw, {**run_identity, **row})
        if update == 1:
            if not row['passed']:
                raise RuntimeError('first-update gradient contract failed: ' + json.dumps(row['trainable_violations']))
            common.write_new_json(folder / 'FIRST-UPDATE.json', {**run_identity, **row,
                'parent_Adam_loaded': True, 'parent_RNG_restored': True})
        segment_done += 1
        pause = ctx.segment_update_limit is not None and segment_done >= ctx.segment_update_limit and update < total
        if update < total and (update % ctx.resume_every == 0 or pause):
            payload = runtime.checkpoint_payload(modules, opt, names, participation, {
                **run_identity, 'update': update, 'schedule_sha256': matched['schedule_sha256'],
                'config_sha256': ctx.config_sha256, 'nonzero_gradient_updates': dict(nonzero)},
                common.rng_snapshot(torch))
            pin = save_verified(rt, ctx, folder / ('resume-%04d.pt' % update), payload)
            receipt = {'update': update, 'checkpoint': pin['path'], 'checkpoint_sha256': pin['sha256'],
                       'raw_bytes': raw.stat().st_size, 'raw_sha256': common.digest(raw)}
            path = folder / ('resume-%04d.json' % update)
            if path.exists():
                path.unlink()  # stale receipt of an interrupted segment at this same update
            common.write_new_json(path, receipt)
            if previous is not None and previous['checkpoint'] != pin['path']:
                stale = folder / previous['checkpoint']
                if stale.is_file():
                    stale.unlink()  # bounded disk: keep only the latest verified resume state
            previous = receipt
        if pause:
            raise SegmentPaused('segment limit reached at update %d' % update)
    expected = Counter(frames)
    visits = Counter(json.loads(line)['frame_index'] for line in raw.read_text().splitlines())
    if visits != expected or len(raw.read_text().splitlines()) != total:
        raise ValueError('raw log does not cover the exact run schedule')
    if (common.module_fingerprint(parts['tool'], torch) != tool_before
            or common.module_fingerprint(parts['core'].halt, torch) != halt_before
            or common.tree_digest(dict(parts['core'].named_buffers()), torch) != buffers_before
            or common.module_fingerprint(ctx.lm, torch) != lm_before):
        raise ValueError('tool/halt/buffers/LM must stay bit-identical')
    steps = runtime.adam_steps(opt, named)
    audit = [{'name': n, 'Adam_step': steps[n], 'parent_Adam_step': parent_steps[n],
              'participation': participation[n], 'nonzero_gradient_updates': nonzero[n]} for n in names]
    if any(r['Adam_step'] != r['participation'] for r in audit):
        raise ValueError('final Adam steps differ from participation')
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    payload = runtime.checkpoint_payload(modules, opt, names, participation, {
        **run_identity, 'update': total, 'parent_update': ctx.parent_update,
        'parent_checkpoint_sha256': parent_sha, 'schedule_sha256': matched['schedule_sha256'],
        'config_sha256': ctx.config_sha256, 'nonzero_gradient_updates': dict(nonzero),
        'optimizer_audit': audit}, common.rng_snapshot(torch))
    pin = save_verified(rt, ctx, folder / 'final-checkpoint.pt', payload)
    if previous is not None and (folder / previous['checkpoint']).is_file():
        (folder / previous['checkpoint']).unlink()
    closed = {**run_identity, 'closed': True, 'optimizer_updates': total, 'checkpoint': pin,
              'checkpoint_reload_verified': True, 'matched': matched,
              'QA_updates': sum(r['task_role'] == 'QA' for r in rows),
              'auxiliary_updates': sum(r['task_role'] == 'auxiliary' for r in rows),
              'supervised_target_tokens': sum(r['valid_target_tokens'] for r in rows),
              'auxiliary_target_tokens': sum(r['valid_target_tokens'] for r in rows if r['task_role'] == 'auxiliary'),
              'finite_loss_all_updates': True, 'cap_violations': 0,
              'gradient_contract_failures': sum(not r['passed'] for r in rows),
              'final_CE_last_pass_mean': sum(r['CE'] for r in rows[-min(72, total):]) / min(72, total),
              'tool_bit_identical': True, 'halt_bit_identical': True, 'buffers_bit_identical': True,
              'LM_unchanged': True, 'optimizer_reset': False, 'optimizer_audit': audit,
              'TRAIN_raw_sha256': common.digest(raw)}
    common.write_new_json(folder / 'CLOSED.json', closed)
    return closed


def execute_runs(rt, ctx, schedules, parents):
    """parents: {seed: (saved_checkpoint_dict, sha256)}"""
    results = []
    for seed, arm in ctx.run_order:
        saved, sha = parents[seed]
        results.append(train_run(rt, ctx, seed, arm, schedules[seed], saved, sha))
        print(json.dumps({'event': 'english-pilot-run-closed', 'seed': seed, 'arm': arm,
                          'checkpoint': results[-1]['checkpoint']}), flush=True)
    return results


def cpu_preflight(root, cfg, workerpath):
    admitted = runtime.validate_native_config(root, cfg, 'train', workerpath)
    return {'schema': SCHEMA, 'checked': True, 'frames': len(admitted['frames']),
            'updates_per_run': TOTAL, 'runs': [list(r) for r in RUN_ORDER],
            'Torch_imported': 'torch' in sys.modules, 'admitted': admitted}


def run(args):
    root = Path(args.root).resolve()
    cfgpath = Path(args.config).resolve()
    if not cfgpath.is_relative_to(root) or common.digest(cfgpath) != args.config_sha256:
        raise ValueError('owned config physical pin differs')
    cfg = common.read_json(cfgpath)
    if args.require_owned_stdin:
        print(json.dumps({'event': 'actual-worker-ready', 'pid': os.getpid(), 'ppid': os.getppid(),
                          'sys_executable': sys.executable, 'config_sha256': args.config_sha256}), flush=True)
        if sys.stdin.readline() != GO_LINE:
            raise ValueError('owned process release required')
    admission = cpu_preflight(root, cfg, Path(__file__))
    admitted = admission.pop('admitted')
    if args.check:
        print(json.dumps(admission, sort_keys=True), flush=True)
        return 0
    if not args.require_owned_stdin or cfg['dispatch_allowed'] is not True:
        raise ValueError('authorized sole-driver owned dispatch required')
    out = root / cfg['output_namespace']
    launches = sorted(out.glob('LAUNCH-*.json')) if out.exists() else []
    if out.exists() and not args.resume:
        raise ValueError('unique output required; pass --resume to continue a preserved run')
    if args.resume and (not launches or common.read_json(launches[0])['config_sha256'] != args.config_sha256):
        raise ValueError('resume requires the same config as the first launch')
    out.mkdir(parents=True, exist_ok=bool(args.resume))
    wall = common.WallBudget(cfg['budget']['worker_seconds'])
    rt = runtime.import_runtime()
    torch = rt.torch
    if cfg['device'] == 'cuda':
        rt.compare.install_cuda_memory_budget(torch, cfg['budget']['cuda_peak_reserved_cap_bytes'])
        torch.cuda.reset_peak_memory_stats()
    guard, gpu_guard = runtime.make_guards(rt, out, cfg['budget'], root, wall)
    identity = {'schema': SCHEMA, 'config_sha256': args.config_sha256, 'TRAIN_only': True,
                'EVAL_accessed': False, 'notebook': None, 'four_fixed_latent_loops': True,
                'prefix_vectors': 8, 'loss': 'human_loss only'}
    common.write_new_json(out / ('LAUNCH-%03d.json' % len(launches)), {**identity,
        'code': runtime.code_digests(), 'segment_update_limit': args.segment_updates})
    phase = 'setup'
    try:
        torch.set_num_threads(2)
        dec, tokenizer, lm = runtime.load_native_stack(rt, root, cfg)
        frames = admitted['frames']
        runtime.check_tokenizer_frames(tokenizer, frames)
        features, cache_receipt = rt.cache.prepare_english_feature_cache(
            lm, [rt.cache.frame_input_record(f) for f in frames], cfg['feature_identity'], torch,
            device=cfg['device'], directory=root / cfg['cache_namespace'], guard=guard,
            gpu_guard=gpu_guard, max_seconds=600, max_bytes=256 * common.MIB)
        ctx = type('Ctx', (), {})()
        ctx.lm, ctx.dec, ctx.device, ctx.out = lm, dec, cfg['device'], out
        ctx.frames_by_index = {f['frame_index']: f for f in frames}
        ctx.features = {f['frame_index']: x for f, x in zip(frames, features)}
        ctx.tokens = runtime.frame_tensors(torch, frames, cfg['device'])
        ctx.guard, ctx.gpu_guard = guard, gpu_guard
        ctx.code, ctx.identity, ctx.config_sha256 = runtime.code_digests(), identity, args.config_sha256
        ctx.parent_update, ctx.resume_every = runtime.PARENT_UPDATE, cfg['resume_every_updates']
        ctx.segment_update_limit, ctx.run_order = args.segment_updates, RUN_ORDER
        ctx.total_updates = TOTAL
        allowance = 114687936 + 64 * common.MIB  # 3x FP32 params (weights + 2 Adam moments) + metadata

        def save_checkpoint(path, payload):
            import checkpoint_io
            checkpoint_io.save_reserved(path, allowance, lambda sink: torch.save(payload, sink),
                rt.sealed.save_new_atomic_file, guard, lambda: shutil.disk_usage(root).free,
                cfg['budget']['retained_free_bytes'], 4096)
        ctx.save_checkpoint = save_checkpoint
        parents = {}
        for parent in cfg['parents']:
            path = common.pinned(root, parent['checkpoint'])
            parents[parent['seed']] = (torch.load(path, map_location='cpu', weights_only=True),
                                       parent['checkpoint']['sha256'])
        phase = 'training'
        results = execute_runs(rt, ctx, admitted['schedules'], parents)
        common.write_new_json(out / 'CLOSED.json', {**identity, 'closed': True, 'runs': [
            {k: r[k] for k in ('seed', 'arm', 'checkpoint', 'supervised_target_tokens',
                               'auxiliary_target_tokens', 'final_CE_last_pass_mean')} for r in results],
            'cache': cache_receipt, 'gpu': gpu_guard(), 'wall_seconds': wall.elapsed()})
        print(json.dumps({'event': 'english-pilot-training-closed', 'runs': len(results)}), flush=True)
        return 0
    except SegmentPaused as paused:
        common.write_new_json(out / ('PAUSED-%03d.json' % len(launches)), {**identity, 'paused': str(paused)})
        print(json.dumps({'event': 'english-pilot-segment-paused', 'detail': str(paused)}), flush=True)
        return 0
    except Exception as exc:
        common.write_new_json(out / ('FAILED-%03d.json' % len(launches)), {**identity, 'phase': phase,
            'error': type(exc).__name__ + ': ' + str(exc), 'evidence_preserved': True})
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--require-owned-stdin', action='store_true')
    p.add_argument('--check', action='store_true')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--segment-updates', type=int, default=None)
    return run(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
