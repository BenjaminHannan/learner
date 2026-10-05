"""G5: Stage A zero-update probe for the English pilot (no optimizer step).

Per parent seed: verify the parent (sha pin, strict load of all four modules,
114 names, constructors, FP32, exact Adam continuation, RNG restored last).
Per run (seed x arm): 72 backward-only gradient checks (48 QA + the arm's 24
auxiliary frames) against the contract: reader/core/prefix gradients finite with
positive norm; LM, core.halt, tool, core.tok/slot/head/ln_out gradients None.
Each probe restores gradients and RNG and proves model/Adam/buffers unchanged.
Per parent: native greedy answers (48-token observer) for all 96 frames.

Import is stdlib-only. The CLI (--config) is the native GPU step; tests call
probe_parent() with tiny CPU fixtures.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import english_pilot_common_v1 as common  # noqa: E402
import english_pilot_runtime_v1 as runtime  # noqa: E402

SCHEMA = 'premonition.English-pilot-zero-update-probe.v1'
ARMS = ('control', 'treatment')
GO_LINE = 'BEGIN ENGLISH ZERO UPDATE PROBE\n'


def arm_frame_indices(arm):
    aux = 2 if arm == 'control' else 3
    return [4 * p + s for p in range(24) for s in (0, 1, aux)]


def backward_probe(rt, ctx, modules, frame_index):
    """One backward with no optimizer step; returns the contract receipt."""
    torch = rt.torch
    parts = runtime.module_dict(modules)
    for _, module in modules:
        module.zero_grad(set_to_none=True)
    ids, mask, labels = ctx.tokens[frame_index]
    h, aux = runtime.english_graph(rt, parts['core'], parts['reader'], ctx.features[frame_index], mask)
    per, _prediction, stats = runtime.english_loss(rt, ctx.lm, ctx.dec, h, mask, labels)
    if not bool(torch.isfinite(per).all()):
        raise RuntimeError('nonfinite probe CE at frame %d' % frame_index)
    per.mean().backward()
    contract = runtime.gradient_contract(rt, modules, ctx.lm)
    for _, module in modules:
        module.zero_grad(set_to_none=True)
    return {'frame_index': frame_index, 'CE': stats['CE'], 'valid_target_tokens': stats['valid_target_tokens'],
            'input_tokens_with_EOS': int(ids.shape[1]), 'sparse_auxiliary_observed': float(aux.detach()),
            **contract}


def probe_parent(rt, ctx, seed, saved, expected_update, generate=True):
    """Full Stage A for one parent; never steps the optimizer."""
    torch = rt.torch
    modules = runtime.build_modules(rt, ctx.dec, seed, ctx.device)
    named = runtime.restore_parent_modules(rt, saved, modules, ctx.lm)
    names = [n for n, _ in named]
    runtime.validate_parent_metadata(saved, names, expected_update)
    opt = runtime.make_optimizer(torch, [p for _, p in named])
    adam_states = runtime.restore_adam(torch, opt, saved, named)
    parent_rng = {k: saved[k] for k in ('torch_rng', 'cuda_rng', 'python_rng')}
    model_before = common.tree_digest({n: m.state_dict() for n, m in modules}, torch)
    optimizer_before = common.tree_digest(opt.state_dict(), torch)
    buffers_before = common.tree_digest({n: b for n, b in runtime.module_dict(modules)['core'].named_buffers()}, torch)
    lm_before = common.module_fingerprint(ctx.lm, torch)
    common.restore_rng(parent_rng, torch)  # last RNG-affecting preparation
    rng_digest = common.tree_digest(parent_rng, torch)
    runs = {}
    for arm in ARMS:
        rows = []
        for frame_index in arm_frame_indices(arm):
            ctx.guard()
            ctx.gpu_guard()
            rows.append(backward_probe(rt, ctx, modules, frame_index))
            common.restore_rng(parent_rng, torch)
        runs[arm] = {'probes': len(rows), 'passed': all(r['passed'] for r in rows),
                     'failed_frames': [r['frame_index'] for r in rows if not r['passed']], 'rows': rows}
    answers = []
    if generate:
        parts = runtime.module_dict(modules)

        def inference():
            out = []
            for frame in ctx.frames:
                ctx.guard()
                _, mask, _ = ctx.tokens[frame['frame_index']]
                observed = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'],
                                                     ctx.features[frame['frame_index']], mask, 48)
                out.append({'frame_index': frame['frame_index'], 'frame_sha256': frame['frame_sha256'], **observed})
            return out
        answers, _preservation = runtime.preserved_measurement(
            inference, [('decoder', ctx.dec)] + list(modules), opt, torch)
    after = {'model': common.tree_digest({n: m.state_dict() for n, m in modules}, torch),
             'optimizer': common.tree_digest(opt.state_dict(), torch),
             'buffers': common.tree_digest({n: b for n, b in runtime.module_dict(modules)['core'].named_buffers()}, torch),
             'lm': common.module_fingerprint(ctx.lm, torch),
             'RNG': common.tree_digest(common.rng_snapshot(torch), torch)}
    unchanged = (after['model'] == model_before and after['optimizer'] == optimizer_before
                 and after['buffers'] == buffers_before and after['lm'] == lm_before and after['RNG'] == rng_digest)
    if not unchanged:
        raise ValueError('zero-update probe changed model/Adam/buffers/LM/RNG state')
    return {'schema': SCHEMA, 'seed': seed, 'parameter_names': len(names), 'Adam_states': adam_states,
            'optimizer_updates': 0, 'state_unchanged': True, 'parent_RNG_sha256': rng_digest,
            'model_sha256': model_before, 'optimizer_sha256': optimizer_before,
            'runs': runs, 'gradient_contract_passed': all(r['passed'] for r in runs.values()),
            'native_answers': answers, 'native_answer_count': len(answers)}


def run(args):
    started = time.monotonic()
    root = Path(args.root).resolve()
    cfgpath = Path(args.config).resolve()
    if not cfgpath.is_relative_to(root) or common.digest(cfgpath) != args.config_sha256:
        raise ValueError('owned config physical pin differs')
    cfg = common.read_json(cfgpath)
    if args.require_owned_stdin:
        print(json.dumps({'event': 'actual-worker-ready', 'pid': os.getpid(), 'ppid': os.getppid(),
                          'config_sha256': args.config_sha256}), flush=True)
        if sys.stdin.readline() != GO_LINE:
            raise ValueError('owned process release required')
    admitted = runtime.validate_native_config(root, cfg, 'probe', Path(__file__))
    if args.check:
        print(json.dumps({'schema': SCHEMA, 'checked': True, 'frames': len(admitted['frames']),
                          'Torch_imported': 'torch' in sys.modules}, sort_keys=True), flush=True)
        return 0
    if cfg['dispatch_allowed'] is not True or not args.require_owned_stdin:
        raise ValueError('authorized owned dispatch required')
    out = root / cfg['output_namespace']
    out.mkdir(parents=True, exist_ok=False)
    wall = common.WallBudget(cfg['budget']['worker_seconds'])
    rt = runtime.import_runtime()
    torch = rt.torch
    if cfg['device'] == 'cuda':
        rt.compare.install_cuda_memory_budget(torch, cfg['budget']['cuda_peak_reserved_cap_bytes'])
        torch.cuda.reset_peak_memory_stats()
    guard, gpu_guard = runtime.make_guards(rt, out, cfg['budget'], root, wall)
    common.write_new_json(out / 'LAUNCH.json', {'schema': SCHEMA, 'config_sha256': args.config_sha256,
                                                'code': runtime.code_digests(), 'optimizer_updates': 0})
    try:
        dec, tokenizer, lm = runtime.load_native_stack(rt, root, cfg)
        frames = admitted['frames']
        runtime.check_tokenizer_frames(tokenizer, frames)
        records = [rt.cache.frame_input_record(f) for f in frames]
        features, cache_receipt = rt.cache.prepare_english_feature_cache(
            lm, records, cfg['feature_identity'], torch, device=cfg['device'],
            directory=root / cfg['cache_namespace'], guard=guard, gpu_guard=gpu_guard,
            max_seconds=600, max_bytes=256 * common.MIB)
        ctx = type('Ctx', (), {})()
        ctx.lm, ctx.dec, ctx.frames, ctx.device = lm, dec, frames, cfg['device']
        ctx.features = {f['frame_index']: x for f, x in zip(frames, features)}
        ctx.tokens = runtime.frame_tensors(torch, frames, cfg['device'])
        ctx.guard, ctx.gpu_guard = guard, gpu_guard
        results = []
        for parent in cfg['parents']:
            saved = torch.load(common.pinned(root, parent['checkpoint']), map_location='cpu', weights_only=True)
            result = probe_parent(rt, ctx, parent['seed'], saved, runtime.PARENT_UPDATE)
            result['parent_checkpoint'] = parent['checkpoint']
            common.write_new_json(out / ('PROBE-seed%d.json' % parent['seed']), result)
            results.append({k: v for k, v in result.items() if k != 'native_answers' and k != 'runs'}
                           | {'runs': {a: {k: v for k, v in r.items() if k != 'rows'} for a, r in result['runs'].items()}})
        passed = all(r['gradient_contract_passed'] for r in results)
        common.write_new_json(out / 'CLOSED.json', {'schema': SCHEMA, 'closed': True, 'passed': passed,
            'parents': results, 'cache': cache_receipt, 'gpu': gpu_guard(),
            'wall_seconds': time.monotonic() - started})
        print(json.dumps({'event': 'english-zero-update-probe-closed', 'passed': passed}), flush=True)
        return 0 if passed else 2
    except Exception as exc:
        common.write_new_json(out / 'FAILED.json', {'schema': SCHEMA, 'error': type(exc).__name__ + ': ' + str(exc)})
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--config-sha256', required=True)
    p.add_argument('--require-owned-stdin', action='store_true')
    p.add_argument('--check', action='store_true')
    return run(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
