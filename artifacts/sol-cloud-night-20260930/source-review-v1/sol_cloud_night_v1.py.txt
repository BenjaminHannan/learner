#!/usr/bin/env python3
"""Queue-only human TRAIN fixture -> 25 actual core updates -> explicit rollback.

Reuses the ordered fixed-four-round graph. This is a new fixture mechanics run,
never a rerun of static25/V12, user-day learning, or semantic qualification.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import random
import shutil
import signal
import time

from sol_cloud_candidate_v1 import VERSION, sha, read, write, pin, verify_files, import_pinned, pointer_snapshot, fingerprint, exact_target, reject

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / 'artifacts/sol-cloud-night-20260930'


def require_watcher():
    if not os.environ.get('JOB') or Path(os.environ.get('TREE', '')).resolve() != ROOT.resolve():
        raise RuntimeError('watcher JOB and exact TREE required; no direct model/training run')


def check_plan(plan):
    expected = {'version': VERSION, 'updates': 25, 'batch': 2, 'fixed_rounds': 4,
                'context_cap': 512, 'lr': 1e-5, 'weight_decay': 0.01, 'actual_user_day': False,
                'activation_policy': 'explicit-rollback'}
    if any(plan.get(key) != value for key, value in expected.items()):
        raise ValueError('changed fixture contract requires a new released plan')
    if plan.get('question_cap', 48) != 48:
        raise ValueError('sealed question prefix cap48 required')
    if (not 1 <= plan['wall_cap_seconds'] <= 1800 or plan['disk_floor_bytes'] < 1024 ** 3
            or not 0 < plan['output_cap_bytes'] <= 256 * 1024 ** 2):
        raise ValueError('unsafe bounded time/disk budget')
    groups = [plan[name + '_ids'] for name in ('experience', 'replay', 'guard')]
    if any(not group or len(group) != len(set(group)) for group in groups):
        raise ValueError('nonempty distinct group identities required')
    if any(set(groups[i]) & set(groups[j]) for i in range(3) for j in range(i)):
        raise ValueError('fixture/replay/guard identity overlap')


def join_fixture(train, day_rows, plan):
    if [row['id'] for row in day_rows] != plan['experience_ids']:
        raise ValueError('fixture identities differ from presealed experience group')
    keys = ('question', 'context', 'answer_text', 'target_text', 'accepted_human_answers', 'source_sha256')
    for row in day_rows:
        original = train[row['id']]
        if row.get('actual_user_day') is not False or row.get('origin') != 'verified-human-TRAIN-fixture':
            raise ValueError('honest fixture provenance required')
        if any(row.get(key) != original.get(key) for key in keys):
            raise ValueError('fixture altered HUMAN TRAIN fields: ' + row['id'])
        if row['target_text'] != row['answer_text'] or row['target_text'] not in row['accepted_human_answers']:
            raise ValueError('target must be literal existing human answer')
    return day_rows


def run(args):
    require_watcher()  # gate before any torch import/model load
    if sha(args.binding) != args.binding_sha256:
        raise ValueError('binding hash changed')
    binding, plan = read(args.binding), read(args.plan)
    check_plan(plan)
    if binding['version'] != VERSION or sha(args.plan) != binding['plan_sha256'] or sha(__file__) != binding['driver_sha256']:
        raise ValueError('pinned driver/plan changed')
    if args.seed != binding['seed'] or args.seed not in plan['source_seeds']:
        raise ValueError('wrong source seed')
    verify_files(binding['dependency_pins'])
    import_pinned(reject.__module__, binding)
    source = binding['source']
    verify_files({record['path']: record['sha256'] for record in source.values()
                  if isinstance(record, dict) and set(record) == {'path', 'sha256'}})
    pointer_before = pointer_snapshot(source['pointer_db'])
    if pointer_before['exists'] and pointer_before['bundle'] != source['previous_bundle']:
        raise ValueError('source bundle is not the current active pointer')
    safety = read(source['awake_safety_receipt']['path'])
    if (safety['execution_policy'] != 'native-fixed4' or not safety['native_state_parity']
            or safety['parent_sha256'] != source['parent']['sha256']
            or safety['reader_sha256'] != source['reader']['sha256']
            or safety['prefix_sha256'] != source['prefix']['sha256']):
        raise ValueError('exact awake fixed4 safety tuple required')
    train_module = import_pinned(binding['modules']['trainonly'], binding)
    day_module = import_pinned(binding['modules']['day_adapter'], binding)
    rows, registry = train_module.human_rows(packet=binding['train']['packet']['path'],
        manifest=binding['train']['manifest']['path'],
        expected_packet_sha256=binding['train']['packet']['sha256'],
        expected_manifest_sha256=binding['train']['manifest']['sha256'])
    train_source_pins = read(binding['train']['manifest']['path'])['source_pins']
    if any(row['split'] != 'train' for row in rows):
        raise ValueError('TRAIN-only loader returned non-TRAIN records')
    train = {row['id']: row for row in rows}
    if len(train) != len(rows):
        raise ValueError('duplicate TRAIN identities')
    day_rows = day_module.load_rows(args.day_rows, args.day_sha256, source['previous_bundle']['sha256'])
    groups = {name: [train[value] for value in plan[name + '_ids']] for name in ('replay', 'guard')}
    groups['experience'] = join_fixture(train, day_rows, plan)
    output = Path(args.output).resolve()
    if not output.is_relative_to(OWN.resolve()) or output.exists():
        raise ValueError('NEW own output directory required; no silent resume/rerun')
    if shutil.disk_usage(OWN.parent).free < plan['disk_floor_bytes'] + plan['output_cap_bytes']:
        raise RuntimeError('reserve and complete output/atomic budget unavailable before run')
    output.mkdir(parents=True)
    write(output / 'pointer-before.json', pointer_before)
    input_pins = {args.binding: args.binding_sha256, args.plan: sha(args.plan), args.day_rows: args.day_sha256,
                  binding['train']['packet']['path']: binding['train']['packet']['sha256'],
                  binding['train']['manifest']['path']: binding['train']['manifest']['sha256']}
    verify_files(input_pins)
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(plan['torch_seed'] + args.seed)
    ordered = import_pinned(binding['modules']['ordered'], binding)
    graph = import_pinned(binding['modules']['graph'], binding)
    native = import_pinned(binding['modules']['native'], binding)
    from sol_translator_grounding_v6 import HumanInputProjection, question_notebook_tokens, target_tokens
    from sol_translator_english_v6 import FrozenEnglishDecoder, load_local_lm
    from scripts.sol_stop_adapter import FinalLatent
    lm, tokenizer, _ = load_local_lm(source['model_path'], source['provenance']['path'], args.device)
    core, metadata = ordered.load_ordered_bundle(source['parent']['path'], args.device)
    if core.constructor()['notebook_cap'] != 512:
        raise ValueError('ordered512 constructor required')
    reader_raw = torch.load(source['reader']['path'], map_location='cpu', weights_only=True)
    reader = HumanInputProjection(reader_raw['lm_width']).to(args.device)
    reader.load_state_dict(reader_raw['state_dict'])
    prefix_raw = torch.load(source['prefix']['path'], map_location='cpu', weights_only=True)
    if (prefix_raw['parent_sha256'] != source['parent']['sha256']
            or prefix_raw['reader_sha256'] != source['reader']['sha256']
            or prefix_raw['training_origin'] != 'verified-human-origin-verbatim'
            or prefix_raw['human_manifest_sha256'] != reader_raw['human_manifest_sha256']
            or prefix_raw['human_registry_sha256'] != train_source_pins['registry_sha256']
            or reader_raw['human_manifest_sha256'] != train_source_pins['pairs_sha256']):
        raise ValueError('awake reader/prefix HUMAN lineage mismatch')
    decoder = FrozenEnglishDecoder(lm, prefix_raw['state_width'], tokenizer.bos_token_id,
        tokenizer.eos_token_id, hidden=prefix_raw['hidden'], prefix_tokens=prefix_raw['prefix_tokens']).to(args.device)
    decoder.adapter.load_state_dict(prefix_raw['adapter_state'])
    reader.eval().requires_grad_(False)
    decoder.adapter.eval().requires_grad_(False)
    lm.eval().requires_grad_(False)
    for row in groups['experience'] + groups['replay'] + groups['guard']:
        target_tokens(tokenizer, [row], args.device)
        if len(tokenizer.encode(row['context'], add_special_tokens=False)) > 512:
            raise ValueError('sealed full notebook token cap exceeded; no truncation/drop')
    frozen = {name: fingerprint(module.state_dict()) for name, module in
              [('LM', lm), ('reader', reader), ('prefix', decoder.adapter)]}
    core_before = fingerprint(core.state_dict())
    initial_state = {name: value.detach().cpu().clone() for name, value in core.state_dict().items()}
    cancelled = [False]
    signal.signal(signal.SIGTERM, lambda *_: cancelled.__setitem__(0, True))
    signal.signal(signal.SIGINT, lambda *_: cancelled.__setitem__(0, True))
    start = time.monotonic()

    def row_loss(row):
        ids, valid, notebook_ids, notebook_valid = question_notebook_tokens(tokenizer, row, args.device,
            max_question=plan.get('question_cap', 48), max_context=plan['context_cap'])
        targets = target_tokens(tokenizer, [row], args.device)
        loss, raw = graph.row_graph(lm, core, reader, decoder, ids, valid, notebook_ids, notebook_valid, targets)
        account = {'input_ids': ids.cpu().tolist(), 'input_mask': valid.cpu().tolist(),
                   'notebook_ids': notebook_ids.cpu().tolist(), 'notebook_mask': notebook_valid.cpu().tolist()}
        import hashlib
        record = {**account, 'id': row['id'], 'split': 'open-HUMAN-TRAIN-fixture-engineering',
                  'actual_user_day': False, 'labels': targets.cpu().tolist(),
                  'label_mask': (targets != -100).cpu().tolist(), 'predictions': raw['predictions'],
                  'CE': raw['human_CE_per_example'][0], 'eos_token_id': tokenizer.eos_token_id,
                  'round': 4, 'binding_sha256': args.binding_sha256,
                  'source_sha256': row['source_sha256'], 'labels_origin': 'verified-human-TRAIN-answer',
                  'day_record_id': row.get('day_record_id'),
                  'source_row_id': row.get('source_row_id', row['id']),
                  'input_identity_sha256': hashlib.sha256(json.dumps(account, sort_keys=True).encode()).hexdigest()}
        return loss, record, (ids, valid, notebook_ids, notebook_valid)

    @torch.no_grad()
    def guards():
        core.eval()
        result = []
        for row in groups['guard']:
            _, record, (ids, valid, notebook_ids, notebook_valid) = row_loss(row)
            query = reader(lm.get_input_embeddings()(ids), valid)
            notebook = reader(lm.get_input_embeddings()(notebook_ids), notebook_valid).flatten(1, 2)
            with native.ordered_attention_math():
                state = core.begin_latent(query, notebook, query_mask=valid, notebook_mask=notebook_valid)
                for _ in range(4):
                    state = core.advance_latent(state)
                final, _ = core.read_latent(state)
            packet = FinalLatent(final, torch.ones_like(final, dtype=torch.bool), valid, (1, final.shape[1]))
            tokens = decoder.generate(packet, max_tokens=64)[0]
            record.update(generated_ids=tokens, generated_text_MODEL_LOG_ONLY=tokenizer.decode(tokens, skip_special_tokens=True),
                          human_target=row['target_text'])
            record['human_target_exact'] = exact_target(record)
            result.append(record)
        return result

    before, repeat = guards(), guards()
    repeat_noise = abs(sum(row['CE'] for row in repeat) / len(repeat) - sum(row['CE'] for row in before) / len(before))
    write(output / 'guard-before.json', before)
    write(output / 'guard-before-repeat.json', repeat)
    core.train().requires_grad_(True)
    for name, parameter in core.named_parameters():
        if 'halt' in name:
            parameter.requires_grad_(False)
    parameter_names = [name for name, value in core.named_parameters() if value.requires_grad]
    parameters = [value for value in core.parameters() if value.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=plan['lr'], weight_decay=plan['weight_decay'])
    if optimizer.state:
        raise ValueError('fixture must start with fresh Adam step0')
    sampling = random.Random(plan['sample_seed'] + args.seed)
    schedule = [[sampling.choice(groups['experience'])['id'], sampling.choice(groups['replay'])['id']] for _ in range(25)]
    if 'sample_schedule' in plan and plan['sample_schedule'][str(args.seed)] != schedule:
        raise ValueError('presealed sample schedule mismatch')
    sampling = random.Random(plan['sample_seed'] + args.seed)
    ledger = {'version': VERSION, 'seed': args.seed, 'updates': 0, 'closed': False,
              'actual_user_day': False, 'activated': False, 'fixture_rows': len(day_rows),
              'optimizer_scope': 'ordered core ONLY; halt frozen', 'core_before': core_before, 'core_after': core_before,
              'optimizer_parameter_names': parameter_names, 'core_Adam_initial_step': 0, 'core_optimizer_calls': 0,
              'optimizer_participation_counts': dict.fromkeys(parameter_names, 0),
              'optimizer_nonzero_gradient_counts': dict.fromkeys(parameter_names, 0),
              'model_authored_targets': 0, 'DEV_model_calls': 0, 'learned_stop_qualified': False,
              'target_scope': 'verbatim official human short answer + EOS; evidence_text retained as provenance only',
              'execution_policy': 'native-fixed4', 'experience_ids': [row['id'] for row in day_rows],
              'experience_record_ids': [row['day_record_id'] for row in day_rows], 'replay_ids': plan['replay_ids'],
              'day_rows_path': args.day_rows, 'day_rows_sha256': args.day_sha256,
              'raw_watermark_update': 0, 'binding_sha256': args.binding_sha256, 'plan_sha256': sha(args.plan),
              'orphan_policy': 'raw rows beyond the last durable watermark are retained as noncommitted; no silent truncation/restart',
              'persistence_policy': 'file fsync + atomic replace; POSIX directory fsync; no power-loss qualification',
              'input_pins': input_pins, 'job': os.environ['JOB'], 'repeat_CE_noise_measured': repeat_noise,
              'sample_schedule': schedule, 'frozen_component_fingerprints': frozen,
              'input_prefix_policy': {'question_cap': 48, 'context_cap': 512,
                  'question_truncated_rows': sum(len(tokenizer.encode(row['question'], add_special_tokens=False)) > 48
                      for group in groups.values() for row in group),
                  'context_truncated_rows': 0, 'target_truncated_rows': 0,
                  'selection': 'fixed question prefix; full notebook; no label-dependent crop/drop'},
              'frozen_components_unchanged': False, 'checkpoint_reload_exact': False, 'populated_Adam_reload_exact': False,
              'comparative_gain_proof': 'DEFERRED; fixture mechanics only'}
    write(output / 'STARTED.json', {'version': VERSION, 'actual_user_day': False,
          'job': os.environ['JOB'], 'optimizer_updates': 0, 'binding_sha256': args.binding_sha256,
          'plan_sha256': sha(args.plan), 'fixture_rows': len(day_rows), 'sample_schedule': schedule})

    def budget(estimated_temporary):
        existing = sum(path.stat().st_size for path in OWN.rglob('*') if path.is_file())
        if existing + estimated_temporary > plan['output_cap_bytes']:
            raise RuntimeError('aggregate output cap before atomic write; evidence preserved')
        if shutil.disk_usage(output).free < plan['disk_floor_bytes'] + estimated_temporary:
            raise RuntimeError('1GiB disk reserve before atomic write; evidence preserved')

    def save_tensor(value, filename, estimated):
        budget(estimated)
        temporary = output / (filename + '.tmp')
        with temporary.open('xb') as stream:
            torch.save(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if sum(path.stat().st_size for path in OWN.rglob('*') if path.is_file()) > plan['output_cap_bytes']:
            raise RuntimeError('actual serialized cap exceeded; preserve temporary and prior evidence')
        os.replace(temporary, output / filename)
        if os.name != 'nt':
            descriptor = os.open(output, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    def durable():
        if any(not bool(torch.isfinite(value).all()) for value in core.state_dict().values()):
            raise RuntimeError('nonfinite candidate; retain prior bundle')
        ledger['core_after'] = fingerprint(core.state_dict())
        ledger['raw_watermark_update'] = ledger['updates']
        ledger['wall_seconds'] = time.monotonic() - start
        core_bytes = sum(value.numel() * value.element_size() for value in core.state_dict().values())
        prefix_bytes = sum(value.numel() * value.element_size() for value in prefix_raw['adapter_state'].values())
        meta = dict(metadata, stage='cloud-fixture-night-candidate-unqualified', actual_user_day=False,
                    awake_parent_sha256=source['parent']['sha256'], overnight_updates=ledger['updates'])
        save_tensor(ordered.ordered_bundle_payload(core, meta), 'candidate-parent.pt', core_bytes + 2 * 1024 ** 2)
        rebound = dict(prefix_raw, parent_sha256=sha(output / 'candidate-parent.pt'),
                       training_stage='cloud-fixture-night-frozen-prefix-rebound-unqualified')
        save_tensor(rebound, 'candidate-English.pt', prefix_bytes + 2 * 1024 ** 2)
        resume = {'core': core.state_dict(), 'optimizer': optimizer.state_dict(),
                  'optimizer_parameter_names': parameter_names, 'sample_rng': sampling.getstate(),
                  'torch_rng': torch.get_rng_state(), 'cuda_rng': torch.cuda.get_rng_state_all(),
                  'ledger': dict(ledger), 'binding_sha256': args.binding_sha256,
                  'frozen_component_fingerprints': frozen}
        save_tensor(resume, 'night-resume.pt', 3 * core_bytes + 4 * 1024 ** 2)
        write(output / 'night-ledger.json', ledger)
        print(json.dumps({'status': 'FIXTURE-NIGHT-DURABLE', 'actual_user_day': False,
                          'updates': ledger['updates'], 'resume_sha256': sha(output / 'night-resume.pt')}), flush=True)

    try:
        with (output / 'night-raw.jsonl').open('x', encoding='utf8') as stream, (output / 'optimizer-updates.jsonl').open('x', encoding='utf8') as update_stream:
            for update in range(25):
                if cancelled[0] or time.monotonic() - start > plan['wall_cap_seconds']:
                    break
                batch = [sampling.choice(groups['experience']), sampling.choice(groups['replay'])]
                optimizer.zero_grad(set_to_none=True)
                losses, records = [], []
                for row in batch:
                    loss, record, _ = row_loss(row)
                    losses.append(loss)
                    records.append(dict(record, update=update + 1,
                        origin=row.get('origin', 'verified-human-origin-verbatim')))
                total = torch.stack(losses).mean()
                if not bool(torch.isfinite(total)):
                    raise RuntimeError('nonfinite fixture loss')
                total.backward()
                torch.nn.utils.clip_grad_norm_(parameters, 1, error_if_nonfinite=True)
                gradients = []
                for name, parameter in core.named_parameters():
                    if parameter.grad is not None:
                        norm = float(parameter.grad.detach().float().norm().cpu())
                        gradients.append({'name': name, 'l2_norm': norm, 'nonzero': norm > 0})
                        ledger['optimizer_participation_counts'][name] += 1
                        ledger['optimizer_nonzero_gradient_counts'][name] += int(norm > 0)
                if not gradients or not any(item['nonzero'] for item in gradients):
                    raise RuntimeError('no nonzero core gradient before optimizer update')
                step_before = fingerprint(core.state_dict())
                optimizer.step()
                step_after = fingerprint(core.state_dict())
                if step_before == step_after:
                    raise RuntimeError('optimizer call did not change actual core tensors')
                update_stream.write(json.dumps({'update': update + 1, 'actual_user_day': False,
                    'binding_sha256': args.binding_sha256, 'core_before': step_before,
                    'core_after': step_after, 'gradients': gradients}, allow_nan=False) + '\n')
                update_stream.flush()
                os.fsync(update_stream.fileno())
                for record in records:
                    stream.write(json.dumps(record, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
                ledger['updates'] = update + 1
                ledger['core_optimizer_calls'] = update + 1
                if update == 0 or (update + 1) % 5 == 0:
                    durable()
        ledger['closed'] = ledger['updates'] == 25 and not cancelled[0]
        durable()
        if not ledger['closed']:
            raise RuntimeError('fixture interrupted; durable partial candidate retained inactive')
        restored_core, _ = ordered.load_ordered_bundle(output / 'candidate-parent.pt', 'cpu')
        ledger['checkpoint_reload_exact'] = fingerprint(restored_core.state_dict()) == ledger['core_after']
        del restored_core
        restored = torch.load(output / 'night-resume.pt', map_location='cpu', weights_only=True)
        current, saved = optimizer.state_dict()['state'], restored['optimizer']['state']
        equal = bool(saved) and current.keys() == saved.keys()
        for key, values in current.items():
            equal = equal and values.keys() == saved[key].keys()
            for name, value in values.items():
                other = saved[key][name]
                equal = equal and (torch.equal(value.detach().cpu(), other) if isinstance(value, torch.Tensor) else value == other)
        ledger['populated_Adam_reload_exact'] = bool(equal)
        ledger['frozen_components_unchanged'] = all(fingerprint(module.state_dict()) == frozen[name]
            and all(parameter.grad is None for parameter in module.parameters())
            for name, module in [('LM', lm), ('reader', reader), ('prefix', decoder.adapter)])
        if any(not torch.equal(initial_state[name], value.detach().cpu()) for name, value in core.state_dict().items() if 'halt' in name):
            raise RuntimeError('halt changed despite freeze')
        if not ledger['checkpoint_reload_exact'] or not ledger['populated_Adam_reload_exact'] or not ledger['frozen_components_unchanged']:
            raise RuntimeError('candidate reload/frozen component verification failed')
        del restored
        durable()  # persist final validation flags into the actual resume checkpoint
        after = guards()
        write(output / 'guard-after.json', after)
        manifest = {'version': VERSION, 'seed': args.seed, 'actual_user_day': False,
                    'activated': False, 'activation_eligible': False, 'fixture_rows': len(day_rows),
                    'execution_policy': 'native-fixed4', 'learned_stop': 'UNQUALIFIED',
                    'parent': pin(output / 'candidate-parent.pt'), 'prefix': pin(output / 'candidate-English.pt'),
                    'reader': source['reader'], 'provenance': source['provenance'],
                    'previous_bundle': source['previous_bundle'], 'resume': pin(output / 'night-resume.pt'),
                    'ledger': pin(output / 'night-ledger.json'), 'scientific_gain': 'NOT SHOWN',
                    'target_scope': ledger['target_scope'],
                    'source_binding_sha256': args.binding_sha256, 'semantics': 'NOT SHOWN'}
        write(output / 'candidate-manifest.json', manifest)
        receipt = reject(args.binding, args.binding_sha256, args.plan, output, pointer_before)
        print(json.dumps({'status': 'FIXTURE-NIGHT-VALIDATED-EXPLICIT-ROLLBACK', 'updates': ledger['updates'],
                          'actual_user_day': False, 'activated': False,
                          'rollback': pin(output / 'rollback.json'), 'guard_passed': receipt['guard_passed']}), flush=True)
    except BaseException as error:
        write(output / 'FAILURE.json', {'version': VERSION, 'actual_user_day': False,
              'activated': False, 'updates': ledger['updates'], 'closed': ledger['closed'],
              'exception': type(error).__name__, 'error': str(error), 'binding_sha256': args.binding_sha256,
              'prior_pointer_unchanged': pointer_snapshot(source['pointer_db']) == pointer_before,
              'previous_bundle_unchanged': sha(source['previous_bundle']['path']) == source['previous_bundle']['sha256'],
              'reason': 'failure evidence preserved; candidate remains inactive'})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', required=True)
    parser.add_argument('--binding-sha256', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--seed', type=int, choices=(0, 1), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--day-rows', required=True)
    parser.add_argument('--day-sha256', required=True)
    parser.add_argument('--device', default='cuda')
    run(parser.parse_args())
