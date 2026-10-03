"""CPU-only scoped saved-answer scoring. Gold opens after complete raw128 proof.

V2 preserves the v1 numeric/native/latency methods and admits only the specific
parent-reviewed available-metadata scope; missing history remains explicit.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

SCHEMA_SHA = 'd44d08e4798f27e09b4f17aecf30e02b4b4c0ddb8a40b67db72939c65acae322'
AUDIT_SHA = 'c07bef50d684376827cc3986c76b11a05ef55cb63dc8f0fa1456206d24e9393a'
ARITHMETIC_SHA = 'f477ca94abb5180c2438a590d4db18c64f06119e50a7590380954f2ae177846c'
NATIVE_SHA = 'c826c12983607a8d4897bbae9f961a1a109d507eeae65413da6f9eef3dbbed78'
ENDPOINTS_SHA = 'd65403c4ae27124f60448ae8696680922943cde8def506f648c474e075a5b2e3'
PROTOCOL_SHA = '1f86594390c56b9e028a3c24f4557f627a627516822df72cbdc03a631be1fb2a'
SCOPED_GENERATOR_SHA = 'c7b7dd85f31622582501c46789ef78722b08d9ab0295229a11019090828e9b95'
SCOPED_VALIDATOR_SHA = 'd19593b9763aa3d1dfac31fa1aade1ac011a5944d8cda3a233999e3651c91d29'
CLOSURE_EMITTER_SHA = '44b83687acc8c587db46da367046335c0f878986562ecdf3360268e2f6cea977'
INPUT_QUALIFICATION_SHA = '387c132ea2ce6e81a33fb7a5f4cdb93d4197ce05b5cc0a33ee3a89111e2682d4'
INPUT_SHA = 'e7c2de468c7530a97806012c995191718cec9089c4a7da680cfe6f68e98a45e0'
NUMERIC_PRODUCER_SHA = '0090b463807dd1e0cc307b598e4da0fc192638db8f35378a4a63e04cfc02514f'
FEATURE_IDENTITY_SHA = '860766764f41bc49bcf08e6e38605924379d79009ee80ae7a9f0b48c304edf8d'
TOKENIZER_ROOT = 'C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
TOKENIZER_ASSETS = {'special_tokens_map.json': '742aefe2b7dec496e8caffdba03a75d0c1a9925d53bd3f3e0d388c96b591b6f4',
    'tokenizer.json': 'df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd',
    'tokenizer_config.json': '2a52ec012d3df831ba434b081bef3726a6ee22501f062ad8353c557a0cfa0d01',
    'config.json': '15d6157fb6df3f8272e2fe90e18f57727ccf02a125c94469198b0f3281510185'}
IMAGE_PINS = {'original_worker': ('C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe',
    '53e910971cbb20c3223cc44c696254ccfba9595dc4be8e16f56f6c954fff831f'),
    'original_launcher': ('C:/Users/benja/lis300/venv/Scripts/python.exe',
    '0978726a27a8c5cc7b329e6d6f02c4c18bc1cdd448cc0ea29fdcdae4e2af7868')}
COUNTS = {'native_generate_calls': 128, 'four_loop_core_calls': 128, 'fixed_latent_advances': 512,
    'contextual_input_backbone_calls': 16, 'static_input_embedding_calls': 16,
    'teacherforced_calls': 0, 'optimizer_updates': 0, 'backward_calls': 0}
REQUEST_KEYS = {'schema', 'protocol', 'endpoints', 'inputs', 'gold', 'exposure_receipt', 'raw',
    'frozen', 'generated', 'operational_closure', 'numeric_token_receipt', 'numeric_token_producer', 'question_feature_cache', 'generation_config_sha256', 'generation_runner_sha256',
    'report_path', 'consumption_path', 'scoped_policy', 'operational_assembly_request'}


def support(root, relative, expected, name):
    path = Path(root) / relative
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('fixed independent support source differs: ' + relative)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def raw128_before_gold(raw, frozen, generated, operation, inputs, endpoints, request, schema):
    """No oracle/target argument exists in this pre-gold proof."""
    raw_bytes = Path(raw).read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    schema.require(raw_bytes.endswith(b'\n'), 'complete raw trailing record required')
    records = [json.loads(line) for line in raw_bytes.splitlines()]
    schema.require(len(records) == 128 and len(inputs) == 16 and len(endpoints) == 8, 'all eight complete16 native answers required')
    common = {'native_calls': 128, 'optimizer_updates': 0, 'teacherforced_examples': 0,
        'gold_accessed': False, 'gold_scoring_started': False, 'fit_gate_used': False,
        'all128_raw_frozen': True, 'generation_config_sha256': request['generation_config_sha256'],
        'generation_runner_sha256': request['generation_runner_sha256'], 'checkpoint_bindings': endpoints,
        'model_call_account': COUNTS, 'LM_unchanged': True, 'all_endpoint_weights_unchanged': True}
    for name, packet in (('freeze', frozen), ('generation closure', generated)):
        schema.require(all(schema.equal(packet.get(k), v) for k, v in common.items()), 'complete source-bound ' + name + ' differs')
    schema.require(frozen.get('schema') == 'cap256.fresh-terminal-raw128-frozen.v1'
        and frozen.get('sha256') == digest and frozen.get('all128_raw_frozen_before_any_gold_access') is True,
        'all128 physically frozen before any gold access required')
    schema.require(generated.get('schema') == 'cap256.fresh-terminal-generated-closed.v1'
        and generated.get('closed') is True and generated.get('status') == 'FROZEN-ALL128-NATIVE-OUTPUTS'
        and generated.get('raw_sha256') == digest and generated.get('frozen_sha256') == request['frozen']['sha256']
        and generated.get('checkpoint_bytes_unchanged') is True and schema.equal(generated.get('input_pin'), request['inputs']),
        'physical complete generation closure/freeze/input binding required')
    schema.require(operation.get('schema') == 'cap256.fresh-terminal-operational-closure.v1'
        and operation.get('worker_exit_code') == 0 and type(operation.get('worker_exit_code')) is int
        and operation.get('driver_exit_code') == 0 and type(operation.get('driver_exit_code')) is int
        and all(operation.get(k) is True for k in ('no_live_owned_processes', 'global_lock_absent', 'guard_absent'))
        and operation.get('queue_status') == 'completed' and schema.equal(operation.get('queue_completion_count'), 1)
        and operation.get('generated_closed_sha256') == request['generated']['sha256'],
        'actual terminated native owned worker/driver and no ownership guards required before gold')
    for key in ('original_worker', 'original_launcher'):
        owner = operation.get(key)
        image, image_sha = IMAGE_PINS[key]
        schema.require(type(owner) is dict and type(owner.get('pid')) is int and owner['pid'] > 0
            and type(owner.get('creation_filetime')) is int and owner['creation_filetime'] > 0
            and type(owner.get('image_path')) is str and owner['image_path'].replace('\\', '/').lower() == image.lower()
            and owner.get('executable_sha256') == image_sha
            and all(owner.get(k) is True for k in ('identity_verified', 'retained_original_handle', 'native_wait_confirmed'))
            and schema.equal(owner.get('native_wait_exit_code'), 0),
            'original retained native HANDLE identity and wait exit0 required: ' + key)
    sources = operation.get('source_receipts')
    schema.require(type(sources) is list and sources, 'physical original handle/queue/census source receipt pins required')
    for source in sources: schema.pin_shape(source)
    for i, row in enumerate(records):
        endpoint, frame = endpoints[i // 16], inputs[i % 16]
        required = {'call_index': i + 1, 'sequence_index': i, 'physical_row_index': i % 16,
            'phase': 'EVAL', 'id': frame['id'], 'input_frame_sha256': frame['frame_sha256'],
            'frame_sha256': frame['frame_sha256'], 'input_manifest_sha256': request['inputs']['sha256'],
            'checkpoint_sha256': endpoint['checkpoint']['sha256'],
            'config_sha256': request['generation_config_sha256'], 'runner_sha256': request['generation_runner_sha256'],
            'native_generate_call_count': 1, 'total_advances': 4, 'gold_accessed': False,
            **{k: endpoint[k] for k in ('seed', 'arm', 'condition', 'learning_rate')}}
        schema.require(all(schema.equal(row.get(k), value) for k, value in required.items()), 'raw128 physical endpoint/input/call sequence differs')
        performance = row.get('performance')
        schema.require(type(performance) is dict and type(performance.get('total_answer_seconds')) in (int, float)
            and math.isfinite(performance['total_answer_seconds']) and performance['total_answer_seconds'] >= 0,
            'all128 measured query latencies including failed answers required')
    return records, digest


def gold_after_raw(raw, frozen, generated, operation, inputs, endpoints, request, schema, load_gold):
    records, digest = raw128_before_gold(raw, frozen, generated, operation, inputs, endpoints, request, schema)
    gold = load_gold()
    schema.require(schema.digest(raw) == digest, 'raw128 changed while oracle was opened')
    return records, gold


def nonoracle_pin(root, record, gold, schema):
    """Reject physical aliases before hashing any purported metadata file."""
    schema.pin_shape(record)
    schema.require(schema.safe(root, record['path']) != schema.safe(root, gold['path']),
        'nonoracle metadata cannot alias the separately held gold payload')
    return schema.pin(root, record)


def numeric_token_map(packet, schema, producer):
    schema.require(type(packet) is dict and set(packet) == {'schema', 'status', 'tokenizer_files',
        'producer_source', 'eos_token_id', 'numeric_tokens', 'encoding_and_decoding_verified',
        'gold_accessed', 'question_panel_accessed', 'generic_numeric_map_independent_of_panel',
        'qualification', 'model_calls', 'Torch_imports'}, 'strict generic numeric tokenizer proof required')
    schema.require(packet['schema'] == 'cap256.generic-numeric-token-proof.v1' and packet['status'] == 'PASSED'
        and schema.equal(packet['eos_token_id'], 7) and packet['encoding_and_decoding_verified'] is True
        and packet['gold_accessed'] is False and packet['generic_numeric_map_independent_of_panel'] is True
        and schema.equal(packet['model_calls'], 0)
        and schema.equal(packet['Torch_imports'], 0), 'actual tokenizer-only single-number encode/decode proof required')
    schema.require(type(packet['tokenizer_files']) is list and len(packet['tokenizer_files']) == 4, 'actual pinned tokenizer file closure required')
    for item in packet['tokenizer_files']: schema.pin_shape(item)
    schema.require({item['path'].replace('\\', '/'): item['sha256'] for item in packet['tokenizer_files']}
        == {TOKENIZER_ROOT + '/' + name: value for name, value in TOKENIZER_ASSETS.items()},
        'numeric ID proof must use exact original four tokenizer asset bytes')
    schema.pin_shape(packet['producer_source'])
    schema.require(schema.equal(packet['producer_source'], producer) and producer['sha256'] == NUMERIC_PRODUCER_SHA,
        'numeric proof source must equal actual qualified pinned original-tokenizer producer')
    schema.require(packet['question_panel_accessed'] is True, 'numeric map qualifier question-only access must be reported honestly')
    schema.pin_shape(packet['qualification'])
    tokens = packet['numeric_tokens']
    schema.require(type(tokens) is dict and set(tokens) == {str(n) for n in range(10, 100)}
        and all(type(t) is int and 0 <= t < 65536 and t not in (0, 1, 7) for t in tokens.values())
        and len(set(tokens.values())) == 90, 'all90 canonical10..99 exact distinct single IDs required')
    return tokens


def qualify_gold(frames, inputs, audit, arithmetic, schema, tokens):
    schema.require(type(frames) is list and len(frames) == 16, 'complete separately pinned gold16 required')
    pairs = {}
    for frame, question in zip(frames, inputs):
        schema.require(schema.equal(audit.projected_input(frame), question)
            and frame.get('frame_sha256') == schema.canonical({k: v for k, v in frame.items() if k != 'frame_sha256'}),
            'gold exact original question/token/mask/EOS/span/registry binding differs')
        action, _, _ = arithmetic.target(frame, frame)
        labels = frame.get('labels')
        schema.require(type(labels) is list and len(labels) == 1 and type(labels[0]) is list
            and len(labels[0]) == 2 and all(type(v) is int and 0 <= v < 65536 for v in labels[0])
            and labels[0] == [tokens[frame['canonical_numeric_target']], 7],
            'canonical gold numeric ID must equal actual pinned tokenizer encode/decode proof plusEOS')
        a, b = frame['operands']
        registry = sorted(frame['numeric_registry'], key=lambda r: r['char_span'][0])
        schema.require(len(registry) == 2 and [entry['value'] for entry in registry] == [a, b]
            and all(entry['source'] == 'literal' and entry['status'] == 'OK' for entry in registry),
            'exactly two unchanged original numeric literals in operand order required')
        expected_case = ('carry' if a % 10 + b % 10 >= 10 else 'no_carry') if action == 'ADD' else ('borrow' if a % 10 < b % 10 else 'no_borrow')
        schema.require(frame.get('case') == expected_case, 'independent carry/borrow case differs')
        pairs.setdefault(frame['pair_id'], []).append((action, tuple(frame['operands'])))
    schema.require(len(pairs) == 8 and all(len(rows) == 2 and {a for a, _ in rows} == {'ADD', 'SUB'}
        and rows[0][1] == rows[1][1] for rows in pairs.values()), 'eight matched ADD/SUB original operand pairs required')
    schema.require(len({tuple(sorted(rows[0][1])) for rows in pairs.values()}) == 8, 'eight distinct unordered operand pairs required')
    return frames


def signal_identity_recount(result, answers, records, frames, audit):
    """A wrong verified numeric token remains a failed answer in every denominator."""
    for answer, record, frame in zip(answers, records, frames):
        if answer['equivalent_task_call_correct']:
            matching = [(i, call) for i, call in enumerate(record['predicted_trace'])
                if call.get('status') == 'OK' and call.get('result', {}).get('value') == int(frame['canonical_numeric_target'])]
            if not matching or any(call.get('numeric_token_id') != frame['labels'][0][0] for _, call in matching):
                answer['mechanical_errors'].append('verified-task-numeric-token-identity')
                answer['mechanically_valid'] = False
                answer['equivalent_task_call_correct'] = False
                answer['combined_correct'] = False
    for key in ('operation_correct', 'references_correct', 'result_correct', 'equivalent_task_call_correct',
            'strict_final_correct', 'combined_correct', 'mechanically_valid'):
        result[key] = sum(int(a[key]) for a in answers)
    groups = {}
    for frame, answer in zip(frames, answers): groups.setdefault(frame['pair_id'], []).append(answer)
    result['pair_results'] = [{'pair_id': key, 'member_ids': [a['id'] for a in members],
        'both_members_strict_final_correct': all(a['strict_final_correct'] for a in members),
        'both_members_combined_correct': all(a['combined_correct'] for a in members)} for key, members in sorted(groups.items())]
    result['pair_correct'] = sum(p['both_members_strict_final_correct'] for p in result['pair_results'])
    result['combined_pair_correct'] = sum(p['both_members_combined_correct'] for p in result['pair_results'])
    result['correct_call_conditioned_readout'] = audit.readout(answers)
    return result


def feature_cache_proof(cache, records, inputs, request, schema):
    schema.require(cache.get('schema') == 'cap256.contextual-input.final-EVAL-cache.v1'
        and cache.get('all_eight_terminal_closures_verified_before_extract') is True
        and cache.get('shared_across_seeds_and_LR') is True and schema.equal(cache.get('durable_tensor_copies'), 0)
        and cache.get('gold_accessed') is False and schema.equal(cache.get('optimizer_updates'), 0)
        and cache.get('generation_config_sha256') == request['generation_config_sha256']
        and cache.get('generation_runner_sha256') == request['generation_runner_sha256']
        and cache.get('input_manifest_sha256') == request['inputs']['sha256']
        and schema.equal(cache.get('model_call_account'), {'EVAL_input_static_embedding': 16, 'EVAL_input_contextual_backbone': 16})
        and type(cache.get('cache_seconds')) in (int, float) and math.isfinite(cache['cache_seconds']) and cache['cache_seconds'] >= 0,
        'frozen input-only cold cache must follow all eight closures and retain actual timing/counters')
    features = cache.get('features'); expected_bytes = 0
    schema.require(type(features) is dict and set(features) == {'static', 'contextual'}, 'both complete shared feature caches required')
    for arm, packet in features.items():
        schema.require(packet.get('schema') == 'cap256.question-feature-cache.v1' and packet.get('phase') == 'EVAL'
            and packet.get('arm') == arm and schema.equal(packet.get('rows'), 16)
            and all(packet.get(k) is True for k in ('pre_reader_only', 'input_only', 'shared_across_seeds'))
            and packet.get('gold_accessed') is False and schema.canonical(packet.get('feature_identity')) == FEATURE_IDENTITY_SHA
            and schema.equal(packet.get('backbone_forward_calls'), 16 if arm == 'contextual' else 0),
            'exact immutable pre-reader feature identity and16 rows per arm required')
        rows = packet.get('records'); extent = 0
        schema.require(type(rows) is list and len(rows) == 16, 'all sixteen cold encoding rows required')
        for row, frame in zip(rows, inputs):
            seconds = row.get('cold_original_question_encoding_seconds')
            size = len(frame['input_ids'][0]) * 2048 * 4
            schema.require(row.get('id') == frame['id'] and row.get('cache_hit') is False
                and row.get('stage') == 'final-EVAL-frozen-question-feature-cache-miss'
                and schema.equal(row.get('shape'), [1, len(frame['input_ids'][0]), 2048])
                and schema.equal(row.get('bytes'), size) and type(seconds) in (int, float)
                and math.isfinite(seconds) and seconds >= 0 and type(row.get('memory')) is dict,
                'complete exact-token cold feature extraction measurements required')
            for key in ('key_sha256', 'features_sha256'):
                schema.pin_shape({'path': 'hash-only.json', 'sha256': row.get(key)})
            extent += size
        schema.require(schema.equal(packet.get('cache_bytes'), extent), 'per-arm feature extent differs')
        expected_bytes += extent
    schema.require(schema.equal(cache.get('cache_bytes'), expected_bytes) and expected_bytes <= 12845056,
        'exact complete cache extent must fit structural bound')
    for row in records:
        feature = features[row['arm']]['records'][row['physical_row_index']]
        schema.require(row.get('feature_cache_receipt_sha256') == request['question_feature_cache']['sha256']
            and row.get('question_feature_key_sha256') == feature['key_sha256']
            and row.get('question_features_sha256') == feature['features_sha256'], 'every warm query must bind its actual frozen cold feature')
    return {'cache_seconds': cache['cache_seconds'], 'cache_bytes': expected_bytes, 'per_arm': features,
        'stage': 'cold-input-feature-extraction-before-native-answers', 'not_in_warm_query_latency': True}


def contrasts(results):
    lookup = {(r['seed'], r['arm'], r['condition']): r for r in results}
    comparisons = []
    for seed in (0, 1):
        for arm in ('static', 'contextual'):
            comparisons.append(('low-minus-control', seed, arm, lookup[(seed, arm, 'low_lr')], lookup[(seed, arm, 'control')]))
        for condition in ('control', 'low_lr'):
            comparisons.append(('contextual-minus-static', seed, condition, lookup[(seed, 'contextual', condition)], lookup[(seed, 'static', condition)]))
    return [{'comparison': name, 'seed': seed, 'level': level,
        'strict_item_delta': a['strict_final_correct'] - b['strict_final_correct'],
        'strict_pair_delta': a['pair_correct'] - b['pair_correct'],
        'task_call_delta': a['equivalent_task_call_correct'] - b['equivalent_task_call_correct'],
        'conditioned_final_numerator_delta': a['correct_call_conditioned_readout']['strict_final_correct_given_equivalent_task_call'] - b['correct_call_conditioned_readout']['strict_final_correct_given_equivalent_task_call']} for name, seed, level, a, b in comparisons]


def validate_scoped_protocol(protocol, schema):
    schema.require(protocol.get('schema') == 'cap256.fresh-terminal-eval-protocol.v2'
        and protocol.get('historical_question_metadata_incomplete') is True
        and protocol.get('global_operand_pair_novelty_verified') is False
        and protocol.get('parent_scoped_review_required') is True
        and protocol.get('GPU_dispatch_authorized') is False,
        'scoped preparation policy must retain explicit incomplete history and separate authority')
    # Reuse every unchanged v1 scientific requirement, changing only metadata schema.
    original_contract = dict(protocol, schema='cap256.fresh-terminal-eval-protocol.v1')
    schema.validate_protocol(original_contract)


def operation_replay(root, operation, request, schema):
    """Reconstruct closure from pinned original HANDLE/queue/census metadata."""
    emitter = support(root, 'scripts/cap256_launch/assemble_fresh_operational_closure_v1.py',
        CLOSURE_EMITTER_SHA, 'fresh_cpu_original_closure')
    source = nonoracle_pin(root, request['operational_assembly_request'], request['gold'], schema)
    assembly = json.loads(source.read_bytes())
    schema.require(set(assembly) == emitter.REQUEST_KEYS
        and assembly.get('schema') == 'cap256.fresh-terminal-closure-assembly-request.v2',
        'exact pinned physical original closure assembly request required')
    schema.require(schema.equal(operation.get('source_receipts'), [assembly[k] for k in emitter.PIN_FIELDS]),
        'operational source pins must equal the original closure assembly request')
    for key in ('raw', 'generated', 'frozen'):
        schema.require(schema.equal(assembly[key], request[key]), 'closure/scorer physical raw binding differs: ' + key)
    paths = {key: nonoracle_pin(root, assembly[key], request['gold'], schema) for key in emitter.PIN_FIELDS}
    packets = {key: json.loads(paths[key].read_bytes()) for key in ('ownership', 'worker_exit', 'completion',
        'terminal', 'queue_state', 'native_census', 'image_qualification', 'generated', 'frozen')}
    schema.require(packets['generated'].get('raw_sha256') == request['raw']['sha256']
        and packets['generated'].get('frozen_sha256') == request['frozen']['sha256']
        and packets['frozen'].get('sha256') == request['raw']['sha256'], 'original physical closure hash differs')
    replayed = emitter.derive(packets, assembly, schema)
    schema.require(schema.equal(operation, replayed),
        'operational closure must be reproducible from the actual retained HANDLE and physical queue sources')
    return replayed


def scoped_collision_proof(root, policy, exposure, inputs, request, schema):
    """Independently recount named available hashes; never infer absent history."""
    validator = support(root, 'scripts/cap256_launch/validate_fresh_scoped_exposure_v3.py',
        SCOPED_VALIDATOR_SHA, 'fresh_cpu_scoped_exposure')
    question_hashes = set(); counts = []
    for scope in policy['question_metadata_catalogues']:
        packet = json.loads(nonoracle_pin(root, scope['metadata'], request['gold'], schema).read_bytes())
        rows, unavailable = validator.catalogue_rows(scope, packet)
        question_hashes.update(row['question_sha256'] for row in rows)
        counts.append({'scope_id': scope['scope_id'], 'role': scope['role'], 'rows': len(rows),
            'numeric_pair_metadata_unavailable_rows': unavailable})
    pair_packet = json.loads(nonoracle_pin(root, policy['supplied_pair_exclusions_metadata'], request['gold'], schema).read_bytes())
    excluded = validator.known_pair_exclusions(pair_packet)
    for provenance in pair_packet['source_metadata_pins']:
        schema.pin_shape(provenance)
        schema.require(schema.safe(root, provenance['path']) != schema.safe(root, request['gold']['path']),
            'pair source metadata cannot alias separately held gold')
    nonoracle_pin(root, policy['input_producer_qualification'], request['gold'], schema)
    question_collisions = sum(frame['question_sha256'] in question_hashes for frame in inputs)
    pair_collisions = 0
    for frame in inputs:
        literals = sorted(frame['numeric_registry'], key=lambda row: row['char_span'][0])
        schema.require(len(literals) == 2, 'parent panel retains exactly two original quantities')
        pair_collisions += schema.canonical(sorted(row['value'] for row in literals)) in excluded
    schema.require(schema.equal(question_collisions, exposure['question_collisions'])
        and schema.equal(pair_collisions, exposure['supplied_pair_collisions'])
        and question_collisions == 0 and pair_collisions == 0,
        'named available question/pair collision facts must independently reproduce before gold')
    return {'available_question_metadata_scopes': counts, 'unique_available_question_hashes': len(question_hashes),
        'question_collisions': question_collisions, 'LOCAL_known40_pair_collisions': pair_collisions,
        'LOCAL_known40_pair_exclusions': 40, 'historical_question_metadata_incomplete': True,
        'global_operand_pair_novelty_verified': False, 'reserved_or_blind_payloads_opened': False,
        'missing_historical_scopes': policy['missing_historical_scopes'], 'claim_scope': policy['claim_scope']}


def run(root, request_path, request_sha):
    root = Path(root).resolve()
    schema = support(root, 'scripts/cap256_launch/fresh_terminal_eval_schema_v1.py', SCHEMA_SHA, 'fresh_cpu_schema')
    request_path = Path(request_path).resolve()
    schema.require(request_path.is_relative_to(root) and schema.digest(request_path) == request_sha, 'physical score request pin differs')
    request = json.loads(request_path.read_bytes())
    schema.require(set(request) == REQUEST_KEYS and request['schema'] == 'cap256.fresh-terminal-score-request.v2', 'positive CPU score request shape required')
    # Merely validate the gold pin shape here. Never hash/open its file yet.
    schema.pin_shape(request['gold'])
    for key in REQUEST_KEYS - {'schema', 'gold', 'generation_config_sha256', 'generation_runner_sha256', 'report_path', 'consumption_path'}:
        schema.pin_shape(request[key])
        schema.require(schema.safe(root, request[key]['path']) != schema.safe(root, request['gold']['path']),
            'nonoracle request metadata aliases separately held gold: ' + key)
    protocol = json.loads(schema.pin(root, request['protocol']).read_bytes())
    schema.require(request['protocol']['sha256'] == PROTOCOL_SHA and request['endpoints']['sha256'] == ENDPOINTS_SHA
        and schema.equal(protocol['endpoints'], request['endpoints']), 'fixed predeclared policy/eight checkpoint manifest required')
    validate_scoped_protocol(protocol, schema)
    endpoints = schema.validate_endpoints(json.loads(schema.pin(root, request['endpoints']).read_bytes()))
    inputs_packet = json.loads(schema.pin(root, request['inputs']).read_bytes())
    schema.require(inputs_packet.get('schema') == 'cap256.contextual-input.EVAL-inputs.v1', 'separate qualified input-only packet required')
    inputs = schema.validate_input_literal_fields(inputs_packet['rows'])
    native = support(root, 'scripts/cap256_launch/eval_contextual_input_compare_windows_v1.py', NATIVE_SHA, 'fresh_cpu_input_contract')
    native.validate_inputs(inputs)
    exposure = json.loads(schema.pin(root, request['exposure_receipt']).read_bytes())
    scoped = support(root, 'scripts/cap256_launch/eval_terminal_fresh_windows_v2.py', SCOPED_GENERATOR_SHA, 'fresh_cpu_scoped_contract')
    policy = json.loads(nonoracle_pin(root, request['scoped_policy'], request['gold'], schema).read_bytes())
    scoped.validate_scoped_policy(policy, request['inputs'], request['endpoints'])
    schema.require(request['generation_runner_sha256'] == SCOPED_GENERATOR_SHA, 'exact fixed scoped native generator source required')
    schema.require(request['inputs']['sha256'] == INPUT_SHA
        and policy['input_producer_qualification_sha256'] == INPUT_QUALIFICATION_SHA,
        'only the actual qualified parent-authored input16 is admitted')
    parent_review = json.loads(nonoracle_pin(root, policy['parent_scoped_review'], request['gold'], schema).read_bytes())
    scoped.validate_exposure_receipt(exposure, request['inputs'], inputs, policy, parent_review)
    raw = schema.pin(root, request['raw'])
    frozen = json.loads(schema.pin(root, request['frozen']).read_bytes())
    generated = json.loads(schema.pin(root, request['generated']).read_bytes())
    operation = json.loads(schema.pin(root, request['operational_closure']).read_bytes())
    pre_records, _ = raw128_before_gold(raw, frozen, generated, operation, inputs, endpoints, request, schema)
    # These are authority metadata, not model weights, tokenizers, or oracle files.
    operation_replay(root, operation, request, schema)
    exposure_facts = scoped_collision_proof(root, policy, exposure, inputs, request, schema)
    cache = json.loads(nonoracle_pin(root, request['question_feature_cache'], request['gold'], schema).read_bytes())
    cold = feature_cache_proof(cache, pre_records, inputs, request, schema)
    token_receipt = json.loads(nonoracle_pin(root, request['numeric_token_receipt'], request['gold'], schema).read_bytes())
    nonoracle_pin(root, request['numeric_token_producer'], request['gold'], schema)
    tokens = numeric_token_map(token_receipt, schema, request['numeric_token_producer'])
    nonoracle_pin(root, token_receipt['qualification'], request['gold'], schema)
    records, gold_packet = gold_after_raw(raw, frozen, generated, operation, inputs, endpoints, request, schema,
        lambda: json.loads(schema.pin(root, request['gold']).read_bytes()))
    schema.require(gold_packet.get('schema') == 'cap256.contextual-input.EVAL-gold.v1', 'separately qualified scorer-only oracle schema required')
    audit = support(root, 'scripts/cap256_launch/audit_contextual_input_compare_v1.py', AUDIT_SHA, 'fresh_cpu_saved_answer_contract')
    arithmetic = support(root, 'scripts/cap256_launch/audit_fresh_core_comparison.py', ARITHMETIC_SHA, 'fresh_cpu_independent_arithmetic')
    frames = qualify_gold(gold_packet['rows'], inputs, audit, arithmetic, schema, tokens)
    results = []
    for slot, endpoint in enumerate(endpoints):
        subset = records[slot * 16:(slot + 1) * 16]
        result, answers = audit.recount(subset, frames, endpoint, 'EVAL', arithmetic, tokenizer=None)
        signal_identity_recount(result, answers, subset, frames, audit)
        result.update({'condition': endpoint['condition'], 'learning_rate': endpoint['learning_rate'],
            'checkpoint': endpoint['checkpoint'], 'answers': answers, 'latency': audit.latency_summary(answers)})
        results.append(result)
    schema.require(schema.digest(raw) == request['raw']['sha256'], 'raw changed during full CPU recount')
    complete = [f'{arm}/{condition}' for arm in ('static', 'contextual') for condition in ('control', 'low_lr')
        if all(r['strict_final_correct'] == 16 and r['pair_correct'] == 8 for r in results if r['arm'] == arm and r['condition'] == condition)]
    matched = contrasts(results)
    comparison_decisions = []
    for name, levels in (('low-minus-control', ('static', 'contextual')), ('contextual-minus-static', ('control', 'low_lr'))):
        for level in levels:
            rows = [r for r in matched if r['comparison'] == name and r['level'] == level]
            comparison_decisions.append({'comparison': name, 'level': level,
                'both_seed_pair_improvement': len(rows) == 2 and all(r['strict_pair_delta'] > 0 for r in rows),
                'has_tie': any(r['strict_pair_delta'] == 0 for r in rows),
                'has_negative': any(r['strict_pair_delta'] < 0 for r in rows), 'checkpoint_selection_authorized': False})
    report = {'schema': 'cap256.fresh-terminal-score.v2', 'checked': True, 'source_sha256': schema.digest(Path(__file__)),
        'request_sha256': request_sha, 'protocol_sha256': PROTOCOL_SHA, 'raw_sha256': request['raw']['sha256'],
        'all128_raw_verified_before_first_gold_open': True, 'native_answers': 128, 'model_calls': 0,
        'optimizer_updates': 0, 'decoding_calls': 0, 'Torch_imports': 0, 'GPU_calls': 0, 'results': results,
        'matched_contrasts': matched, 'comparative_decisions': comparison_decisions, 'both_seed_complete_panel_arms': complete,
        'cold_feature_cache': cold, 'warm_query_latencies': 'all128 answers including failures; cold feature extraction is reported separately',
        'numeric_token_receipt': request['numeric_token_receipt'],
        'case_counts': {case: sum(f['case'] == case for f in frames) for case in ('carry', 'no_carry', 'borrow', 'no_borrow')},
        'claim_scope': protocol['claim_scope'], 'novelty_claim_limits': protocol['novelty_claim_limits'],
        'scoped_exposure': exposure_facts, 'parent_scoped_review': policy['parent_scoped_review'],
        'scoped_policy': request['scoped_policy'], 'operational_assembly_request': request['operational_assembly_request'],
        'prior_fitting_STOP_unchanged': True, 'additional_execution_authorized': False,
        'raw_unchanged_after_scoring': True}
    destination = schema.safe(root, request['report_path'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    consumption = {'schema': 'cap256.fresh-terminal-panel-consumption.v1', 'panel_status': 'CONSUMED_ONCE',
        'inputs': request['inputs'], 'gold': request['gold'], 'native_answers_frozen': 128,
        'raw_sha256': request['raw']['sha256'], 'score_sha256': schema.digest(destination),
        'model_rerun_allowed': False, 'training_or_tuning_or_fresh_evidence_reuse_allowed': False}
    with schema.safe(root, request['consumption_path']).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(consumption, stream, indent=2, sort_keys=True); stream.write('\n')
    return {'checked': True, 'report': str(destination), 'sha256': schema.digest(destination)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--request', required=True)
    parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.request, args.request_sha256)))
