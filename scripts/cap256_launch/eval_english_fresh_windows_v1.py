"""G9: input-only sealed generation for the English pilot (6 states).

States: 2 parents + 4 endpoints. Every state answers every fresh model input
(fresh comprehension, meaning transfer and paraphrase prompts, exactly as the
fresh file's learner_text) plus the TRAIN panel (48 QA + the arm's 24 auxiliary
frames; parents get both auxiliary sets). Generation is the unchanged native
greedy decoder seen through the 48-token observer; inputs over 64 tokens
(incl. EOS) are a hard stop before any generation.

Seal before gold: this runner never opens the gold-bearing eval file. A
separate stdlib step (extract_fresh_inputs) copies only model_inputs into an
inputs-only file; the runner reads that file, writes RAW-<state>.jsonl for every
state, then SEALED.json with all raw hashes. Scoring (G10) refuses to read gold
until it has verified SEALED.json.

Import is stdlib-only.
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

SCHEMA = 'premonition.English-pilot-fresh-eval.v1'
INPUTS_SCHEMA = 'premonition.English-fresh-inputs.v1'
SEAL_SCHEMA = 'premonition.English-pilot-sealed-outputs.v1'
GO_LINE = 'BEGIN ENGLISH FRESH EVAL\n'
INPUT_KEYS = {'item_id', 'learner_text', 'task'}
STATE_ORDER = (('seed0-parent', 0, None), ('seed1-parent', 1, None), ('seed0-control', 0, 'control'),
               ('seed0-treatment', 0, 'treatment'), ('seed1-control', 1, 'control'),
               ('seed1-treatment', 1, 'treatment'))
ENDPOINT_UPDATE = 2304


def validate_model_inputs(items):
    if type(items) is not list or not items:
        raise ValueError('nonempty model_inputs list required')
    seen = set()
    for item in items:
        if type(item) is not dict or set(item) != INPUT_KEYS:
            raise ValueError('model input keys must be exactly item_id/learner_text/task')
        if any(type(item[k]) is not str or not item[k] for k in INPUT_KEYS):
            raise ValueError('nonempty string model input fields required')
        if item['item_id'] in seen:
            raise ValueError('duplicate fresh item_id')
        seen.add(item['item_id'])
    return items


def extract_fresh_inputs(eval_items_path, out_path):
    """Copy ONLY model_inputs out of the gold-bearing file; returns the new file sha."""
    source = Path(eval_items_path)
    document = json.loads(source.read_bytes())
    items = validate_model_inputs(document.get('model_inputs'))
    record = {'schema': INPUTS_SCHEMA, 'source_sha256': common.digest(source),
              'model_inputs': items, 'model_inputs_sha256': common.canonical(items)}
    del document
    return common.write_new_json(out_path, record)


def load_fresh_inputs(path):
    record = common.read_json(path)
    if (type(record) is not dict or set(record) != {'schema', 'source_sha256', 'model_inputs', 'model_inputs_sha256'}
            or record['schema'] != INPUTS_SCHEMA
            or record['model_inputs_sha256'] != common.canonical(record['model_inputs'])):
        raise ValueError('inputs-only fresh file required (no gold fields)')
    return validate_model_inputs(record['model_inputs']), record['source_sha256']


def tokenize_fresh(tokenizer, items):
    """All fresh inputs to <=64 IDs incl. EOS; any violation is a hard stop listing all."""
    records, violations = [], []
    for item in items:
        ids = [int(v) for v in tokenizer.encode(item['learner_text'], add_special_tokens=False)]
        problem = None
        if not 1 <= len(ids) <= common.INPUT_CAP_WITH_EOS - 1:
            problem = '%d ordinary tokens' % len(ids)
        elif any(v in (common.PAD_ID, common.BOS_ID, common.EOS_ID) or not 0 <= v < 65536 for v in ids):
            problem = 'special/out-of-range ID inside the input'
        if problem:
            violations.append('%s: %s' % (item['item_id'], problem))
            continue
        full = ids + [common.EOS_ID]
        records.append({'input_id': 'FRESH-' + item['item_id'], 'item_id': item['item_id'], 'task': item['task'],
                        'learner_text': item['learner_text'], 'input_ids': [full], 'input_mask': [[True] * len(full)]})
    if violations:
        raise ValueError('%d fresh input(s) exceed the 64-token contract; no generation:\n%s'
                         % (len(violations), '\n'.join(violations)))
    return records


def train_panel(arm):
    if arm is None:
        return [4 * p + s for p in range(24) for s in range(4)]
    aux = 2 if arm == 'control' else 3
    return [4 * p + s for p in range(24) for s in (0, 1, aux)]


def validate_state(saved, seed, arm, parent_sha):
    if arm is None:
        if saved.get('update') != runtime.PARENT_UPDATE:
            raise ValueError('parent state update count differs')
    elif (saved.get('update') != ENDPOINT_UPDATE or saved.get('seed') != seed or saved.get('arm') != arm
          or saved.get('parent_checkpoint_sha256') != parent_sha):
        raise ValueError('endpoint state must be the closed 2304-update run of this seed/arm/parent')


def generate_state(rt, ctx, state_id, saved, seed, arm, fresh_records, raw_path):
    """Restore one state, generate every fresh input + its TRAIN panel, append raw lines."""
    torch = rt.torch
    modules = runtime.build_modules(rt, ctx.dec, seed, ctx.device)
    runtime.restore_parent_modules(rt, saved, modules, ctx.lm)
    parts = runtime.module_dict(modules)
    jobs = [('fresh', r) for r in fresh_records]
    jobs += [('TRAIN', ctx.frames_by_index[i]) for i in train_panel(arm)]

    def inference():
        rows = []
        for panel, record in jobs:
            ctx.guard()
            ctx.gpu_guard()
            if panel == 'fresh':
                features, ids = ctx.fresh_features[record['input_id']], record['input_ids']
            else:
                features, ids = ctx.features[record['frame_index']], record['input_ids']
            mask = torch.ones((1, len(ids[0])), dtype=torch.bool, device=ctx.device)
            observed = runtime.generate_observed(rt, ctx.dec, parts['core'], parts['reader'], features, mask, 48)
            stripped = observed['MODEL_native_decoder_return'][0] if observed['MODEL_native_decoder_return'] else []
            row = {'state_id': state_id, 'panel': panel, 'input_ids_sha256': common.canonical(ids),
                   'output_ids': stripped, 'output_text': ctx.tokenizer.decode(stripped, skip_special_tokens=True),
                   'observation_valid': rt.observer.observation_valid(observed), **observed}
            if panel == 'fresh':
                row.update(item_id=record['item_id'], task=record['task'])
            else:
                row.update(frame_index=record['frame_index'], frame_task=record['task'])
            common.append_jsonl(raw_path, row)
            rows.append(row)
        return rows
    rows, preservation = runtime.preserved_measurement(inference, [('decoder', ctx.dec)] + list(modules), None, torch)
    return {'state_id': state_id, 'generations': len(rows), 'invalid_observations': sum(not r['observation_valid'] for r in rows),
            'raw_sha256': common.digest(raw_path), 'preservation': {k: v for k, v in preservation.items() if k != 'before'}}


def seal(out, states, fresh_inputs_sha256, frames_sha256, extra):
    record = {'schema': SEAL_SCHEMA, 'states': states, 'fresh_inputs_sha256': fresh_inputs_sha256,
              'frames_sha256': frames_sha256, 'gold_accessed': False, 'grading_metadata_opened': False,
              'raw_files': {s['state_id']: {'path': 'RAW-%s.jsonl' % s['state_id'], 'sha256': s['raw_sha256']}
                            for s in states}, **extra}
    sha = common.write_new_json(Path(out) / 'SEALED.json', record)
    return sha


def validate_eval_states(cfg):
    states = cfg['states']
    parents = {p['seed']: p['checkpoint'] for p in cfg['parents']}
    if type(states) is not list or [(s.get('state_id'), s.get('seed'), s.get('arm')) for s in states] != list(STATE_ORDER):
        raise ValueError('exact six states in fixed order required')
    for s in states:
        if set(s) != {'state_id', 'seed', 'arm', 'checkpoint'}:
            raise ValueError('state pin fields required')
        if s['arm'] is None and s['checkpoint'] != parents[s['seed']]:
            raise ValueError('parent states must use the pinned parent checkpoints')
    return states


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
    admitted = runtime.validate_native_config(root, cfg, 'eval', Path(__file__))
    states = validate_eval_states(cfg)
    items, source_sha = load_fresh_inputs(common.pinned(root, cfg['fresh_inputs']))
    if args.check:
        print(json.dumps({'schema': SCHEMA, 'checked': True, 'fresh_inputs': len(items), 'states': len(states),
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
        'code': runtime.code_digests(), 'gold_accessed': False, 'fresh_source_sha256': source_sha})
    try:
        dec, tokenizer, lm = runtime.load_native_stack(rt, root, cfg)
        frames = admitted['frames']
        runtime.check_tokenizer_frames(tokenizer, frames)
        fresh = tokenize_fresh(tokenizer, items)
        records = [rt.cache.frame_input_record(f) for f in frames] + [
            {k: r[k] for k in ('input_id', 'learner_text', 'input_ids', 'input_mask')} for r in fresh]
        features, cache_receipt = rt.cache.prepare_english_feature_cache(
            lm, records, cfg['feature_identity'], torch, device=cfg['device'],
            directory=root / cfg['cache_namespace'], guard=guard, gpu_guard=gpu_guard,
            max_seconds=900, max_bytes=512 * common.MIB)
        ctx = type('Ctx', (), {})()
        ctx.lm, ctx.dec, ctx.tokenizer, ctx.device = lm, dec, tokenizer, cfg['device']
        ctx.frames_by_index = {f['frame_index']: f for f in frames}
        ctx.features = {f['frame_index']: x for f, x in zip(frames, features[:len(frames)])}
        ctx.fresh_features = {r['input_id']: x for r, x in zip(fresh, features[len(frames):])}
        ctx.guard, ctx.gpu_guard = guard, gpu_guard
        parent_shas = {p['seed']: p['checkpoint']['sha256'] for p in cfg['parents']}
        closed = []
        for state in states:
            saved = torch.load(common.pinned(root, state['checkpoint']), map_location='cpu', weights_only=True)
            validate_state(saved, state['seed'], state['arm'], parent_shas[state['seed']])
            result = generate_state(rt, ctx, state['state_id'], saved, state['seed'], state['arm'], fresh,
                                    out / ('RAW-%s.jsonl' % state['state_id']))
            closed.append({**result, 'checkpoint': state['checkpoint']})
            del saved
        sha = seal(out, closed, common.digest(common.pinned(root, cfg['fresh_inputs'])),
                   cfg['frames']['sha256'], {'config_sha256': args.config_sha256, 'cache': cache_receipt,
                                             'fresh_source_sha256': source_sha,
                                             'wall_seconds': time.monotonic() - started, 'gpu': gpu_guard()})
        print(json.dumps({'event': 'english-fresh-eval-sealed', 'sealed_sha256': sha}), flush=True)
        return 0
    except Exception as exc:
        common.write_new_json(out / 'FAILED.json', {'schema': SCHEMA, 'error': type(exc).__name__ + ': ' + str(exc),
                                                    'gold_accessed': False})
        raise


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command')
    gen = sub.add_parser('generate')
    gen.add_argument('--root', required=True)
    gen.add_argument('--config', required=True)
    gen.add_argument('--config-sha256', required=True)
    gen.add_argument('--require-owned-stdin', action='store_true')
    gen.add_argument('--check', action='store_true')
    ext = sub.add_parser('extract-inputs')
    ext.add_argument('--eval-items', required=True)
    ext.add_argument('--out', required=True)
    argv = sys.argv[1:]
    if argv and argv[0].startswith('--'):
        argv = ['generate'] + argv  # driver calls the worker without a subcommand
    args = p.parse_args(argv)
    if args.command == 'extract-inputs':
        print(json.dumps({'inputs_only_sha256': extract_fresh_inputs(args.eval_items, args.out)}))
        return 0
    return run(args)


if __name__ == '__main__':
    sys.exit(main())
