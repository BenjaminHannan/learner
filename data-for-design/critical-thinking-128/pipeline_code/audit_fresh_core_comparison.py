"""Read-only independent receipt/math recount; zero inference or optimizer work.

Run only after owned model processes have stopped. The oracle frame file is not
opened until the complete saved fresh64 sequence and frozen hash are verified.
Optional CPU checkpoint loading inspects tensor shapes, never invokes a model.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ORDER = [(0, 'shallow'), (0, 'deep'), (1, 'shallow'), (1, 'deep')]
CORE_COUNTS = {'shallow': 9007790, 'deep': 8563454}
COMMON_COUNTS = {'reader': 78112, 'prefix': 76416, 'tool': 133123}
PIN_FIELDS = {'runner_sha256': 'runner', 'runtime_sha256': 'runtime_module',
    'constructor_sha256': 'constructor_module', 'architecture_contract_sha256': 'architecture_contract',
    'training_contract_sha256': 'training_contract', 'calculator_tools_sha256': 'calculator_tools',
    'resume_helpers_sha256': 'resume_helpers', 'source_plan_sha256': 'source_plan',
    'source_seal_sha256': 'source_seal', 'frames_sha256': 'frames', 'schedule_sha256': 'schedules'}


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 ** 2), b''): result.update(block)
    return result.hexdigest()


def read(path): return json.loads(Path(path).read_bytes())


def equal(a, b):
    if type(a) is not type(b): return False
    if type(a) is dict: return set(a) == set(b) and all(equal(a[k], b[k]) for k in a)
    if type(a) is list: return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def safe(root, relative):
    path = Path(str(relative).replace('\\', '/'))
    require(not path.is_absolute() and '..' not in path.parts, 'root-relative evidence path required')
    result = (root / path).resolve()
    require(result.is_relative_to(root), 'evidence escapes root')
    return result


def pin(root, record):
    require(type(record) is dict and set(record) == {'path', 'sha256'}
        and type(record['path']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'exact evidence pin required')
    path = safe(root, record['path']); require(sha(path) == record['sha256'], 'evidence hash differs: ' + record['path'])
    return path


def lines(path):
    data = Path(path).read_bytes()
    require(not data or data.endswith(b'\n'), 'incomplete trailing raw record: ' + str(path))
    return [json.loads(line) for line in data.splitlines()]


def raw64_before_oracle(raw, frozen):
    records = lines(raw)
    require(len(records) == 64 and frozen.get('sha256') == sha(raw)
        and frozen.get('gold_scoring_started') is False and frozen.get('fit_gate_used') is False
        and type(frozen.get('native_calls')) is int and frozen['native_calls'] == 64,
        'all64 complete frozen fresh answers required before oracle metadata access')
    for index, record in enumerate(records):
        seed, arm = ORDER[index // 16]
        require(type(record.get('call_index')) is int and record['call_index'] == index + 1
            and type(record.get('seed')) is int and record['seed'] == seed
            and record.get('arm') == arm and record.get('phase') == 'FRESH'
            and type(record.get('native_generate_call_count')) is int
            and record['native_generate_call_count'] == 1 and record.get('total_advances') == 4,
            'saved fresh sequence differs from fixed64 calls')
    require(all([r.get('id') for r in records[n * 16:(n + 1) * 16]] ==
        [r.get('id') for r in records[:16]] for n in range(4)), 'fresh16 order must match all endpoints')
    return records


def target(row, frame):
    op = row.get('operation'); values = row.get('operands')
    require(op in ('add', 'sub', 'subtract') and type(values) is list and len(values) == 2
        and all(type(n) is int and 10 <= n <= 99 for n in values) and values[0] != values[1]
        and row.get('independently_verified') is True, 'independently qualified arithmetic metadata required')
    wanted = values[0] + values[1] if op == 'add' else values[0] - values[1]
    require(10 <= wanted <= 99 and row.get('canonical_numeric_target') == str(wanted)
        and frame.get('canonical_numeric_target') == str(wanted), 'independent arithmetic target differs')
    question = row.get('question')
    require(type(question) is str and frame.get('question') == question
        and row.get('question_sha256') == hashlib.sha256(question.encode()).hexdigest()
        and frame.get('question_sha256') == row['question_sha256'], 'exact qualified English question binding differs')
    refs = []; registry = frame['numeric_registry']
    for value in values:
        matches = [r for r in registry if r.get('source') == 'literal' and r.get('status') == 'OK'
            and type(r.get('value')) is int and r['value'] == value]
        require(len(matches) == 1, 'operand must map to one original literal')
        literal = matches[0]; start, end = literal['char_span']
        require(type(start) is int and type(end) is int and int(question[start:end]) == value,
            'literal source text differs from independent operand')
        refs.append(literal['id'])
    return 'ADD' if op == 'add' else 'SUB', refs, wanted


def strict_answer(record, frame, tokenizer=None):
    """Reconstruct full-sequence/EOS rules without the producer's scorer."""
    gold = frame['labels'][0]; options = record.get('native_generation_options')
    require(type(gold) is list and len(gold) >= 2 and all(type(n) is int and n >= 0 for n in gold),
        'typed target token sequence required')
    eos = gold[-1]; raw = record.get('MODEL_raw_generate_ids'); full = record.get('MODEL_generated_ids_with_observed_EOS')
    typed = type(raw) is list and len(raw) == 1 and type(raw[0]) is list and all(type(n) is int and n >= 0 for n in raw[0])
    ids = raw[0] if typed else []
    eos_positions = [i for i, n in enumerate(ids) if n == eos]
    valid = (typed and equal(full, ids) and 1 <= len(ids) <= 32 and eos_positions == [len(ids) - 1]
        and equal(record.get('MODEL_native_decoder_return'), [ids[:-1]])
        and equal(record.get('EOS_positions'), eos_positions) and record.get('observed_EOS') is True
        and record.get('native_stripped_output_equal') is True and record.get('generation_error') is None
        and record.get('termination_reason') == 'observed_EOS'
        and record.get('native_call_contract_valid') is True and record.get('raw_output_single_typed_sequence') is True
        and type(record.get('native_generate_call_count')) is int and record['native_generate_call_count'] == 1
        and type(options) is dict and set(options) == {'max_new_tokens', 'do_sample', 'use_cache',
            'bos_token_id', 'eos_token_id', 'pad_token_id'}
        and type(options.get('max_new_tokens')) is int and options['max_new_tokens'] == 32
        and options.get('do_sample') is False and options.get('use_cache') is True
        and type(options.get('bos_token_id')) is int and options['bos_token_id'] >= 0
        and type(options.get('eos_token_id')) is int and options['eos_token_id'] == eos
        and type(options.get('pad_token_id')) is int and options['pad_token_id'] == eos)
    text, full_text = None, None
    if tokenizer is not None:
        require(tokenizer.eos_token_id == eos, 'actual offline tokenizer EOS differs')
        require(equal(tokenizer.encode(frame['canonical_numeric_target'], add_special_tokens=False) + [eos], gold),
            'actual offline tokenizer target differs from frozen target tokens')
        if typed:
            full_text = tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
            text = tokenizer.decode(ids[:-1] if eos_positions == [len(ids) - 1] else ids,
                skip_special_tokens=False, clean_up_tokenization_spaces=False)
    correct = valid and equal(ids, gold) and (tokenizer is None or text == frame['canonical_numeric_target'])
    return {'strict_final_correct': bool(correct), 'full_token_sequence': ids,
        'decoded_full_answer_with_special_tokens': full_text, 'decoded_answer_before_EOS': text,
        'EOS_at_end_once': eos_positions == [len(ids) - 1], 'output_token_count': len(ids),
        'native_contract_reconstructed': bool(valid)}


def mechanical_calls(record, frame):
    """Replay original literal/results and integer calculations independently."""
    traces = record.get('predicted_trace'); require(type(traces) is list and len(traces) == 4, 'four loop traces required')
    registry = [dict(r) for r in frame['numeric_registry']]; errors = []
    query_n = len(frame['input_ids'][0])
    for loop, call in enumerate(traces):
        require(type(call) is dict, 'typed tool trace required')
        expected_geometry = {'loop_index': loop, 'call_index': loop + 1,
            'candidate_ids': [r['id'] for r in registry], 'value_slot': query_n + 2 * loop,
            'status_slot': query_n + 2 * loop + 1, 'original_query_unchanged_on_insert': True, 'policy_features': 'h+e'}
        if any(not equal(call.get(k), v) for k, v in expected_geometry.items()): errors.append('geometry:%d' % loop)
        action, refs, status = call.get('action'), call.get('refs'), call.get('status')
        byid = {r['id']: r for r in registry}
        if action == 'NONE':
            if status != 'NONE' or refs != [] or call.get('result') is not None: errors.append('NONE:%d' % loop)
            continue
        if (action not in ('ADD', 'SUB') or type(refs) is not list or len(refs) != 2
                or any(type(r) is not str or r not in byid for r in refs) or refs[0] == refs[1]):
            if status != 'ERROR' or call.get('result') is not None: errors.append('invalid-call:%d' % loop)
            continue
        chosen = [byid[r] for r in refs]; values = [r['value'] for r in chosen]
        if any(type(n) is not int for n in values): errors.append('operand-type:%d' % loop); continue
        integer = values[0] + values[1] if action == 'ADD' else values[0] - values[1]
        for key, ref in zip(('left_index', 'right_index'), refs):
            index = call.get(key)
            if type(index) is not int or not 0 <= index < len(registry) or registry[index]['id'] != ref:
                errors.append('pointer:%d' % loop)
        if not equal(call.get('operand_values'), values): errors.append('operand-values:%d' % loop)
        if status == 'ERROR' and call.get('error_code') == 'UNSUPPORTED_NUMERIC_TOKEN' and call.get('result') is None:
            continue  # No qualified result is inserted; all future refs still replay.
        result = call.get('result'); origins = []
        for r in chosen:
            for span in ([r['char_span']] if r['source'] == 'literal' else r['origin_char_spans']):
                if span not in origins: origins.append(span)
        expected = {'id': 'result:%d' % (loop + 1), 'index': len(registry), 'value': integer,
            'source': 'result', 'status': 'OK', 'source_call_index': loop + 1,
            'origin_char_spans': origins, 'operand_references': refs}
        if (status != 'OK' or not equal(result, expected) or abs(integer) > 1000000
                or call.get('value_content_zero') is not False
                or type(call.get('numeric_token_id')) is not int or call['numeric_token_id'] < 0):
            errors.append('host-result:%d' % loop)
        if type(result) is dict and status == 'OK':
            registry.append({**result, 'slot_index': query_n + 2 * loop, 'token_indices': [query_n + 2 * loop]})
    return errors


def task_calls(record, row, frame):
    action, wanted_refs, wanted = target(row, frame)
    values_byid = {r['id']: r['value'] for r in frame['numeric_registry']}
    operation = references = result = False
    for call in record['predicted_trace']:
        refs = call.get('refs'); op = call.get('status') == 'OK' and call.get('action') == action
        bound = type(refs) is list and len(refs) == 2 and all(type(r) is str for r in refs)
        ref_ok = op and bound and (set(refs) == set(wanted_refs) if action == 'ADD' else refs == wanted_refs)
        value = call.get('result'); operands = [values_byid[r] for r in refs] if bound and all(r in values_byid for r in refs) else None
        number_ok = (ref_ok and operands is not None and equal(call.get('operand_values'), operands)
            and type(value) is dict and type(value.get('value')) is int and value['value'] == wanted
            and value.get('source') == 'result' and value.get('status') == 'OK')
        operation |= bool(op); references |= bool(ref_ok); result |= bool(number_ok)
    errors = mechanical_calls(record, frame)
    return {'operation_correct': operation, 'references_correct': references, 'result_correct': result,
        'equivalent_task_call_correct': bool(result and not errors), 'mechanical_errors': errors,
        'mechanically_valid': not errors}


def recount(records, frames, metadata, seed, arm, phase, tokenizer=None):
    require(len(records) == len(frames) and len(frames) == (8 if phase == 'TRAIN' else 16), 'complete phase panel required')
    answers, pairs = [], {}
    for record, frame in zip(records, frames):
        row = metadata[frame['id']]
        require(record.get('id') == frame['id'] and record.get('seed') == seed and record.get('arm') == arm,
            'record/endpoint/id order differs')
        checked = target(row, frame)
        answer = {'id': frame['id'], 'seed': seed, 'arm': arm, 'phase': phase, 'independent_target': checked[2],
            **strict_answer(record, frame, tokenizer), **task_calls(record, row, frame)}
        answer['combined_correct'] = answer['strict_final_correct'] and answer['equivalent_task_call_correct']
        answers.append(answer)
        pair = pairs.setdefault(tuple(sorted(row['operands'])), [])
        pair.append((frame['id'], row['operation'], [r['value'] for r in sorted(frame['numeric_registry'], key=lambda r:r['char_span'][0])]))
    pair_records = []
    byid = {a['id']: a for a in answers}
    for quantities, group in sorted(pairs.items()):
        require(len(group) == 2 and sorted('add' if op == 'add' else 'sub' for _, op, _ in group) == ['add', 'sub']
            and group[0][2] == group[1][2], 'matched ADD/SUB pair and literal order required')
        ids = sorted(i for i, _, _ in group)
        pair_records.append({'quantities': list(quantities), 'member_ids': ids,
            'both_members_strict_final_correct': all(byid[i]['strict_final_correct'] for i in ids),
            'both_members_combined_correct': all(byid[i]['combined_correct'] for i in ids)})
    fields = ['strict_final_correct', 'equivalent_task_call_correct', 'combined_correct',
        'operation_correct', 'references_correct', 'result_correct', 'mechanically_valid']
    summary = {'seed': seed, 'arm': arm, 'rows': len(frames), 'pairs': len(pair_records),
        **{field: sum(bool(a[field]) for a in answers) for field in fields},
        'pair_correct': sum(p['both_members_strict_final_correct'] for p in pair_records),
        'combined_pair_correct': sum(p['both_members_combined_correct'] for p in pair_records), 'pair_results': pair_records}
    return summary, answers


def selection(train, fresh):
    deltas = []
    for seed in (0, 1):
        ts, td = [r for r in train if r['seed'] == seed]; fs, fd = [r for r in fresh if r['seed'] == seed]
        deltas.append({'seed': seed, 'TRAIN_final_item_gain': td['strict_final_correct'] - ts['strict_final_correct'],
            'TRAIN_final_pair_gain': td['pair_correct'] - ts['pair_correct'],
            'fresh_final_item_gain': fd['strict_final_correct'] - fs['strict_final_correct'],
            'fresh_final_pair_gain': fd['pair_correct'] - fs['pair_correct']})
    if any(min(d['TRAIN_final_item_gain'], d['TRAIN_final_pair_gain'], d['fresh_final_pair_gain']) < 0 for d in deltas): chosen = 'shallow'
    elif all(d['fresh_final_pair_gain'] > 0 for d in deltas): chosen = 'deep'
    else: chosen = 'inconclusive'
    return {'selected': chosen, 'seed_deltas': deltas}


def endpoint_identity(cfg, cfg_hash, seed, arm):
    source = next(s for s in cfg['sources'] if s['seed'] == seed)
    return {'seed': seed, 'arm': arm, 'config_sha256': cfg_hash,
        **{field: cfg[key]['sha256'] for field, key in PIN_FIELDS.items()},
        'source_parent_sha256': source['checkpoint']['sha256'], 'fresh_core': True,
        'optimizer_reset': True, 'disposable_probe': False, 'TRAIN_only': True,
        'fresh_accessed': False, 'total_latent_advances': 4, 'selected_common_updates': cfg['additional_updates'],
        'target_updates': 2048, 'common_tier_selection': cfg['common_tier_selection'],
        'external_fresh_evaluation_policy': 'all4-endpoints-new-paired16-once-regardless-TRAIN'}


def parameter_context(root, cfg, endpoints, frames, load_checkpoints):
    counts, verified = [], False
    if load_checkpoints:
        import torch
        verified = True
        for endpoint in endpoints:
            cp = torch.load(pin(root, endpoint['checkpoint']), map_location='cpu', weights_only=True)
            groups = Counter()
            for name in cp['optimizer_parameter_names']:
                group, key = name.split('.', 1); tensor = cp[group][key]
                require(tensor.device.type == 'cpu' and tensor.dtype == torch.float32, 'CPU FP32 parameter shape inspection required')
                groups[group] += tensor.numel()
            halt = sum(t.numel() for name, t in cp['core'].items() if name.startswith('halt.'))
            require(halt == 257, 'exact frozen halt parameter count differs')
            require(groups['core'] + halt == CORE_COUNTS[endpoint['arm']]
                and all(groups[k] == v for k, v in COMMON_COUNTS.items()), 'actual checkpoint parameter count differs')
            counts.append({'seed': endpoint['seed'], 'arm': endpoint['arm'], 'components_trainable': dict(groups),
                'stored_adapted': sum(groups.values()) + halt, 'trainable_adapted': sum(groups.values()), 'frozen_halt': halt})
            del cp
    else:
        for seed, arm in ORDER:
            stored = CORE_COUNTS[arm] + sum(COMMON_COUNTS.values())
            counts.append({'seed': seed, 'arm': arm, 'stored_adapted': stored, 'trainable_adapted': stored - 257,
                'count_basis': 'frozen architecture contract; tensor-shape verification pending'})
    context = {}
    for phase, panel in frames.items():
        lengths = [len(f['input_ids'][0]) for f in panel]
        context[phase] = {'rows': len(lengths), 'mean_question_tokens_with_EOS': sum(lengths) / len(lengths),
            'min_question_tokens_with_EOS': min(lengths), 'max_question_tokens_with_EOS': max(lengths),
            'mean_core_context_tokens_including8tool_slots': sum(lengths) / len(lengths) + 8}
    return {'counts': counts, 'mean_stored_adapted_parameters': sum(c['stored_adapted'] for c in counts) / 4,
        'mean_trainable_adapted_parameters': sum(c['trainable_adapted'] for c in counts) / 4,
        'checkpoint_tensor_shapes_CPU_verified': verified,
        'frozen_English_LM_parameters_included': False,
        'frozen_English_interface': 'same pinned LiquidAI/LFM2.5-1.2B-Instruct for both arms; parameter counts above cover trainable core/reader/prefix/tool plus frozen core halt',
        'context': context, 'max_question_tokens_with_EOS': 49, 'max_core_context_tokens': 57,
        'native_output_token_limit': 32, 'fixed_outer_loops': 4,
        'physical_block_visits': {'shallow': 8, 'deep': 64}, 'runtime_or_FLOPs_matched': False}


def optimizer_raw_observation(path, cfg, cfg_hash, endpoint, schedule):
    """Host-side streaming validation avoids copying large teacher-forced raw."""
    identity = endpoint_identity(cfg, cfg_hash, endpoint['seed'], endpoint['arm'])
    checksum = hashlib.sha256(); count = 0
    with path.open('rb') as stream:
        for line in stream:
            checksum.update(line)
            require(line.endswith(b'\n'), 'incomplete optimizer raw line')
            record = json.loads(line); count += 1
            require(count <= len(schedule) and type(record.get('additional_update')) is int
                and record['additional_update'] == count and record.get('id') == schedule[count - 1]
                and all(equal(record.get(k), v) for k, v in identity.items()), 'optimizer order/schedule/identity differs')
            require(all(type(record.get(k)) in (int,float) and math.isfinite(record[k]) for k in
                ('numeric_CE','action_CE','pointer_CE','total_loss','preclip_norm')), 'nonfinite optimizer signal')
            require(record.get('auxiliary_terms') == 4 * (2 if endpoint['arm']=='shallow' else 16)
                and equal(record.get('auxiliary_weight'),0), 'four physical loops/zero sparse loss weight differs')
            require(math.isclose(record['total_loss'], record['numeric_CE']+record['action_CE']+record['pointer_CE'],
                rel_tol=2e-6,abs_tol=2e-6), 'independent loss signal sum differs')
    require(count == cfg['additional_updates'], 'full common-tier optimizer count required')
    stat = path.stat()
    return {'sha256': checksum.hexdigest(), 'size_bytes':stat.st_size, 'mtime_ns':stat.st_mtime_ns,
        'complete_records':count, 'updates_sequence_verified':True, 'schedule_verified':True,
        'identity_verified':True, 'finite_loss_fields_verified':True}


def collect_host(args):
    """After execution stops: filesystem/tensor inspection only, no model calls."""
    root=Path(args.root).resolve(); cfg_pin={'path':args.train_config,'sha256':args.train_config_sha256}
    cfg=read(pin(root,cfg_pin)); packet_pin={'path':args.endpoints,'sha256':args.endpoints_sha256}
    packet=read(pin(root,packet_pin)); endpoints=packet['endpoints']
    require(packet['train_config_sha256']==cfg_pin['sha256'] and [(e['seed'],e['arm']) for e in endpoints]==ORDER,
        'fixed host endpoint packet required')
    schedules=read(pin(root,cfg['schedules']))['schedules']; files={}
    for endpoint in endpoints:
        cp=pin(root,endpoint['checkpoint']); cpstat=cp.stat()
        files[endpoint['checkpoint']['path'].replace('\\','/')]={'sha256':endpoint['checkpoint']['sha256'],
            'size_bytes':cpstat.st_size,'mtime_ns':cpstat.st_mtime_ns,'actual_checkpoint_bytes_hashed':True}
        closed=read(pin(root,endpoint['closed'])); directory=safe(root,endpoint['closed']['path']).parent
        raw=directory/'TRAIN-RAW.jsonl'; schedule=schedules[str(endpoint['seed'])]['fresh_core_compare'][str(cfg['additional_updates'])]
        observation=optimizer_raw_observation(raw,cfg,cfg_pin['sha256'],endpoint,schedule)
        require(observation['sha256']==closed['TRAIN_raw_sha256'],'host raw closure hash differs')
        files[str(raw.relative_to(root)).replace('\\','/')]=observation
        for name in ('CLOSED.json','INITIALIZATION.json','LAUNCH.json','TRAIN-OBSERVATIONS.jsonl','TRAIN-OBSERVATIONS-FROZEN.json'):
            file=directory/name;stat=file.stat()
            files[str(file.relative_to(root)).replace('\\','/')]={'sha256':sha(file),'size_bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}
    evaluation=read(pin(root,{'path':args.evaluation_config,'sha256':args.evaluation_config_sha256}))
    for file in safe(root,evaluation['output_namespace']).iterdir():
        if file.is_file():
            stat=file.stat();files[str(file.relative_to(root)).replace('\\','/')]={'sha256':sha(file),
                'size_bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}
    probe=read(pin(root,cfg['deep_gradient_probe_receipt']))
    require(probe.get('closed') is True and equal(probe.get('optimizer_updates'),8)
        and equal(probe.get('model_call_account'),{'TRAIN_optimizer_teacherforcing':8})
        and equal(probe.get('native_calls'),0) and equal(probe.get('fresh_calls'),0)
        and probe.get('checkpoint_written') is False,'actual separately charged disposable probe differs')
    result={'schema':'cap256.fresh-core.host-observations.v1','train_config':cfg_pin,'endpoints':packet_pin,
        'collector_sha256':sha(__file__),'files':files,'actual_model_calls':0,'actual_optimizer_updates':0,
        'disposable_probe':{'closed':cfg['deep_gradient_probe_receipt'],'optimizer_updates':8,'model_calls':8,
            'native_calls':0,'fresh_calls':0,'checkpoint_written':False},
        'existing_evidence_preserved':True,'collection_scope':'completed checkpoint bytes, native receipt metadata, and complete optimizer raw streams'}
    if args.load_checkpoint_shapes:
        result['parameter_observations']=parameter_context(root,cfg,endpoints,{},True)
    return result


def owner_terminal(root, terminal_pin, cfg_pin, eval_pin, U):
    """Bind measured owner accounting; no invented free-space or wall counters."""
    path = pin(root, terminal_pin); terminal = read(path)
    require(terminal.get('terminal') is True and terminal.get('status') == 'completed'
        and terminal.get('accounting_complete') is True and terminal.get('optimizer_updates_exact') is True
        and terminal.get('config_sha256') == cfg_pin['sha256']
        and terminal.get('evaluation_config_sha256') == eval_pin['sha256']
        and equal(terminal.get('optimizer_updates'), 4 * U)
        and equal(terminal.get('model_calls'), 4 * U + 96)
        and equal(terminal.get('native_calls'), 96) and equal(terminal.get('fresh_native_calls'), 64)
        and equal(terminal.get('teacherforced_examples'), 4 * U)
        and terminal.get('output_includes_terminal_receipt') is True, 'owner terminal provenance/exact counters differ')
    pins = [e for e in terminal.get('evidence', []) if e.get('kind') == 'accounting']
    require(len(pins) == 1, 'one measured owner-accounting receipt required')
    value = pins[0]; origin = 'C:/Users/benja/sol-cloud-numeric-capability-v1/'
    relative = str(value['path']).replace('\\', '/')
    if relative.startswith(origin): relative = relative[len(origin):]
    elif Path(relative).is_absolute():
        relative = str(Path(relative).resolve().relative_to(root))
    census = read(pin(root, {'path': relative, 'sha256': value['sha256']}))
    unit = census.get('allocation_unit_bytes'); base = census.get('new_output_allocated_bytes')
    require(type(unit) is int and unit > 0 and type(base) is int and base >= 0
        and terminal['output_bytes'] == base + math.ceil(path.stat().st_size / unit) * unit,
        'owner terminal allocation differs from hashed measured accounting')
    require(type(census.get('project_allocated_bytes')) is int and type(census.get('free_bytes')) is int,
        'actual project allocation/free observation required')
    return {'pin': terminal_pin, 'job_id':terminal['job_id'], 'attempt_id':terminal['attempt_id'],
        'wall_seconds':terminal['wall_seconds'], 'allocated_output_bytes_including_terminal':terminal['output_bytes'],
        'allocation_unit_bytes':unit, 'project_allocated_bytes_at_closure':census['project_allocated_bytes'],
        'free_bytes_at_closure':census['free_bytes']}


def audit(args):
    root = Path(args.root).resolve()
    cfg_pin = {'path': args.train_config, 'sha256': args.train_config_sha256}
    cfg = read(pin(root, cfg_pin)); eval_pin = {'path': args.evaluation_config, 'sha256': args.evaluation_config_sha256}
    ev = read(pin(root, eval_pin)); protocol = read(pin(root, ev['evaluation_protocol']))
    require(ev['train_config'] == cfg_pin and cfg['schema'] == 'cap256.fresh-core-calculator-compare.v2'
        and cfg['additional_updates'] in (512, 1024, 2048) and cfg['execution_order'] == [list(p) for p in ORDER], 'frozen common-tier config differs')
    for name in PIN_FIELDS.values(): pin(root,cfg[name])
    for name in ('training_runner','evaluation_runner','scoring_module'): pin(root,ev[name])
    packet_pin = {'path': args.endpoints, 'sha256': args.endpoints_sha256}; packet = read(pin(root, packet_pin))
    require(packet['train_config_sha256'] == cfg_pin['sha256'] and packet['evaluation_config_sha256'] == eval_pin['sha256']
        and packet['protocol_sha256'] == ev['evaluation_protocol']['sha256'], 'endpoint packet provenance differs')
    endpoints = packet['endpoints']; require([(e['seed'], e['arm']) for e in endpoints] == ORDER, 'four fixed endpoint identities required')
    host = None
    if args.host_observations:
        require(args.host_observations_sha256 is not None, 'trusted host-observation SHA required')
        host=read(pin(root,{'path':args.host_observations,'sha256':args.host_observations_sha256}))
        require(host.get('schema')=='cap256.fresh-core.host-observations.v1'
            and equal(host.get('train_config'),cfg_pin) and equal(host.get('endpoints'),packet_pin)
            and host.get('actual_model_calls')==0 and host.get('actual_optimizer_updates')==0,
            'host observation config/endpoint pins differ')
    out = safe(root, ev['output_namespace']); raw = out / 'FRESH-OBSERVATIONS.jsonl'
    frozen = read(out / 'FRESH-OBSERVATIONS-FROZEN.json')
    fresh_records = raw64_before_oracle(raw, frozen)
    # No fresh frames/targets/semantics were accessed above this line.
    fresh_frames = read(pin(root, protocol['fresh_frames']))['rows']
    train_frames = read(pin(root, cfg['frames']))['rows']
    require(len(fresh_frames) == 16 and len(train_frames) == 8, 'new TRAIN8/FRESH16 panels required')
    train_metadata = {r['id']: r for r in cfg['selected_rows']}; fresh_metadata = {r['id']: r for r in fresh_frames}
    require(len(train_metadata)==8 and len(fresh_metadata)==16
        and all(r.get('split_role')=='FRESH' for r in fresh_frames), 'unique TRAIN8 and qualified FRESH16 IDs required')
    require(not set(fresh_metadata) & (set(train_metadata) | set(cfg['original_ids'])), 'fresh IDs overlap TRAIN/original256')
    require(not {r['source_group'] for r in fresh_frames} & {r['source_group'] for r in cfg['selected_rows']}, 'TRAIN/fresh source groups overlap')
    tokenizer = None
    if args.tokenizer_path:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer_path, local_files_only=True, trust_remote_code=False)
    train_summary, fresh_summary, answers, CP_verified = [], [], [], True
    for slot, endpoint in enumerate(endpoints):
        closed_path = pin(root, endpoint['closed']); closed = read(closed_path); identity = endpoint_identity(cfg, cfg_pin['sha256'], *ORDER[slot])
        require(all(equal(closed.get(k), v) for k, v in identity.items()), 'endpoint immutable identity differs')
        U = cfg['additional_updates']
        require(closed.get('closed') is True and closed.get('checkpoint') == endpoint['checkpoint']
            and type(closed.get('optimizer_updates')) is int and closed['optimizer_updates'] == U
            and closed.get('additional_optimizer_updates') == U
            and equal(closed.get('model_call_account'), {'TRAIN_optimizer_teacherforcing': U, 'TRAIN_native_generation': 8})
            and closed.get('model_calls_exact') is True and closed.get('optimizer_updates_exact') is True
            and closed.get('durable_model_and_Adam_reload_equal') is True
            and closed.get('raw_frozen_before_scoring') is True and closed.get('native_weight_unchanged') is True
            and closed.get('LM_unchanged') is True and closed.get('halt_unchanged') is True
            and closed.get('fresh_calls') == 0, 'endpoint counters/weights/TRAIN-only closure differs')
        cp_path = safe(root, endpoint['checkpoint']['path'])
        if cp_path.is_file(): pin(root, endpoint['checkpoint'])
        else:
            observed=(host or {}).get('files',{}).get(endpoint['checkpoint']['path'].replace('\\','/'),{})
            CP_verified &= (observed.get('sha256')==endpoint['checkpoint']['sha256']
                and observed.get('actual_checkpoint_bytes_hashed') is True
                and type(observed.get('size_bytes')) is int and observed['size_bytes']>0)
        native_path = closed_path.parent / 'TRAIN-OBSERVATIONS.jsonl'
        require(sha(native_path) == closed['TRAIN_observations_sha256'], 'TRAIN native raw hash differs')
        train_native = lines(native_path)
        require(all(all(equal(r.get(k), v) for k, v in identity.items())
            and r.get('checkpoint_sha256') == endpoint['checkpoint']['sha256'] for r in train_native), 'TRAIN native provenance differs')
        training_raw = closed_path.parent / 'TRAIN-RAW.jsonl'
        schedule = read(pin(root, cfg['schedules']))['schedules'][str(endpoint['seed'])]['fresh_core_compare'][str(U)]
        require(len(schedule) == U, 'fixed common-tier schedule length differs')
        if training_raw.is_file(): observed=optimizer_raw_observation(training_raw,cfg,cfg_pin['sha256'],endpoint,schedule)
        else: observed=(host or {}).get('files',{}).get(str(training_raw.relative_to(root)).replace('\\','/'),{})
        require(observed.get('sha256')==closed['TRAIN_raw_sha256'] and equal(observed.get('complete_records'),U)
            and all(observed.get(k) is True for k in ('updates_sequence_verified','schedule_verified',
                'identity_verified','finite_loss_fields_verified')), 'complete pinned host/local optimizer observation required')
        seed, arm = ORDER[slot]
        group = fresh_records[slot * 16:(slot + 1) * 16]
        require(all(r.get('checkpoint_sha256') == endpoint['checkpoint']['sha256']
            and r.get('config_sha256') == eval_pin['sha256'] and r.get('train_config_sha256') == cfg_pin['sha256']
            and r.get('endpoints_sha256') == packet_pin['sha256'] for r in group), 'fresh raw endpoint/config provenance differs')
        summary, items = recount(train_native, train_frames, train_metadata, seed, arm, 'TRAIN', tokenizer)
        train_summary.append(summary); answers += items
        summary, items = recount(group, fresh_frames, fresh_metadata, seed, arm, 'FRESH', tokenizer)
        fresh_summary.append(summary); answers += items
    closed = read(out / 'CLOSED.json')
    require(closed.get('closed') is True and closed.get('config_sha256') == eval_pin['sha256']
        and closed.get('train_config_sha256') == cfg_pin['sha256'] and closed.get('endpoints_sha256') == packet_pin['sha256']
        and equal(closed.get('model_call_account'), {'FRESH_native_generation':64})
        and closed.get('native_calls') == 64 and closed.get('fresh_native_calls') == 64
        and equal(closed.get('optimizer_updates'),0) and equal(closed.get('teacherforced_examples'),0)
        and closed.get('all64_raw_frozen_before_any_gold_scoring') is True
        and closed.get('endpoint_weights_and_checkpoint_bytes_unchanged') is True and closed.get('LM_unchanged') is True,
        'fresh immutable closure differs')
    for name, expected in closed['file_sha256'].items():
        require(Path(name).name == name and sha(out / name) == expected, 'closed fresh file hash differs')
    fields = ('seed','arm','rows','pairs','strict_final_correct','pair_correct','combined_correct','combined_pair_correct',
        'equivalent_task_call_correct','operation_correct','references_correct','result_correct','mechanically_valid','pair_results')
    for computed, declared in zip(train_summary + fresh_summary, closed['TRAIN_results'] + closed['fresh_results']):
        require(all(equal(computed[k], declared.get(k)) for k in fields), 'independent result recount disagrees with producer')
    require(len(closed['TRAIN_results'])==4 and len(closed['fresh_results'])==4, 'all four producer result summaries required')
    selected = selection(train_summary, fresh_summary)
    require(closed['selection']['selected'] == selected['selected'] and equal(closed['selection']['seed_deltas'], selected['seed_deltas']),
        'independent selection differs')
    terminal = None
    if args.terminal:
        require(args.terminal_sha256 is not None, 'trusted terminal SHA must accompany owner receipt')
        terminal = owner_terminal(root, {'path':args.terminal, 'sha256':args.terminal_sha256},cfg_pin,eval_pin,U)
    if host:
        require(equal(host.get('disposable_probe'),{'closed':cfg['deep_gradient_probe_receipt'],'optimizer_updates':8,
            'model_calls':8,'native_calls':0,'fresh_calls':0,'checkpoint_written':False}), 'host probe charge/provenance differs')
    else:
        probe=read(pin(root,cfg['deep_gradient_probe_receipt']))
        require(probe.get('closed') is True and equal(probe.get('optimizer_updates'),8)
            and equal(probe.get('model_call_account'),{'TRAIN_optimizer_teacherforcing':8}), 'actual probe charge differs')
    param_context=parameter_context(root,cfg,endpoints,{'TRAIN':train_frames,'FRESH':fresh_frames},args.load_checkpoint_shapes)
    if host and host.get('parameter_observations'):
        params=host['parameter_observations']
        require(params.get('checkpoint_tensor_shapes_CPU_verified') is True
            and [(r.get('seed'),r.get('arm')) for r in params.get('counts',[])]==ORDER,
            'host parameter shape observations differ')
        for field in ('counts','mean_stored_adapted_parameters','mean_trainable_adapted_parameters','checkpoint_tensor_shapes_CPU_verified'):
            param_context[field]=params[field]
        param_context['count_basis']='actual completed checkpoint CPU tensor inspection in pinned host observation'
    result = {'schema':'cap256.fresh-core.independent-audit.v1', 'status':'PASS',
        'train_config':cfg_pin, 'evaluation_config':eval_pin, 'endpoints':packet_pin,
        'auditor_sha256':sha(__file__), 'producer_scoring_code_imported':False,
        'actual_model_calls':0, 'actual_optimizer_updates':0,
        'protocol_calls':{'matrix_optimizer_updates':4*U, 'matrix_teacherforced_calls':4*U,
            'TRAIN_native_calls':32,'fresh_native_calls':64,'matrix_model_calls':4*U+96,
            'disposable_probe_updates_separately_charged':8},
        'TRAIN_results':train_summary,'fresh_results':fresh_summary,'selection':selected,'answers':answers,
        'checkpoint_bytes_verified':CP_verified, 'offline_decoded_full_answers_verified':tokenizer is not None,
        'owner_terminal':terminal, 'live_process_exit_observed_by_this_auditor':False,
        'raw_before_gold_evidence':'matching complete frozen raw receipts and pinned producer control flow; no independent signed event clock',
        'parameter_context':param_context,
        'limitations':['Tiny source-disjoint paired-case test; no population-wide generalization claim.',
            'Frozen external pretrained English LM remains part of the interface; adapted parameter counts exclude it.'],
        'fresh_retuning_allowed':False}
    if not CP_verified or tokenizer is None or terminal is None:
        result['status']='RECOUNT-PASS-OWNER-BYTE-OR-DECODE-VERIFICATION-PENDING'
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    for name in ('train-config','evaluation-config','endpoints'):
        parser.add_argument('--'+name,required=True); parser.add_argument('--'+name+'-sha256',required=True)
    parser.add_argument('--tokenizer-path'); parser.add_argument('--load-checkpoint-shapes',action='store_true')
    parser.add_argument('--terminal'); parser.add_argument('--terminal-sha256')
    parser.add_argument('--host-observations'); parser.add_argument('--host-observations-sha256')
    parser.add_argument('--collect-host-observations',action='store_true')
    args=parser.parse_args()
    try: output=collect_host(args) if args.collect_host_observations else audit(args)
    except Exception as error:
        print(json.dumps({'status':'AUDIT-BLOCKED','error_type':type(error).__name__,'error':str(error),
            'actual_model_calls':0,'actual_optimizer_updates':0,'existing_evidence_preserved':True})); raise SystemExit(1)
    print(json.dumps(output,sort_keys=True,allow_nan=False));
