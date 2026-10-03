"""Pure CPU policy for a single new panel; no payload discovery or model imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ORDER = ((1, 'contextual', 'control'), (1, 'contextual', 'low_lr'),
    (0, 'static', 'control'), (0, 'static', 'low_lr'),
    (0, 'contextual', 'control'), (0, 'contextual', 'low_lr'),
    (1, 'static', 'control'), (1, 'static', 'low_lr'))
LRS = {'control': 0.001, 'low_lr': 0.0001}
INSPECTION_SHA = '39a1d6f0eec5c309f07dd0f019297b81d8e7f6348ee27d917b55ee5530322233'
TERMINAL_SHA = 'b704f654874dd23ed01a17aa8eea9dbf55d1a341c147a511d38930281cb2c369'
INPUT_FIELDS = frozenset(('id', 'question', 'question_sha256', 'input_ids',
    'input_mask', 'notebook_ids', 'notebook_mask', 'numeric_registry',
    'split_role', 'source_group', 'pair_id', 'frame_sha256'))
LITERAL_FIELDS = frozenset(('id', 'index', 'source', 'status', 'value', 'char_span', 'token_indices'))
PROTOCOL_REQUIRED = {
    'schema': 'cap256.fresh-terminal-eval-protocol.v1', 'seeds': [0, 1],
    'arms': ['static', 'contextual'],
    'conditions': [{'condition': 'control', 'learning_rate': 0.001}, {'condition': 'low_lr', 'learning_rate': 0.0001}],
    'terminal_updates': 5120, 'new_EVAL_rows': 16, 'new_EVAL_pairs': 8,
    'native_EVAL_call_limit': 128, 'EVAL_optimizer_updates': 0, 'EVAL_teacherforced_examples': 0,
    'EVAL_max_new_tokens': 32, 'max_question_tokens_including_EOS': 49,
    'four_fixed_latent_loops': True, 'EVAL_fit_gate': 'none',
    'all128_raw_frozen_before_any_EVAL_gold_access': True,
    'EVAL_input_cache_after_all_eight_final_closures': True,
    'EVAL_contextual_backbone_calls': 16, 'EVAL_static_embedding_calls': 16,
    'EVAL_features_shared_across_all_matching_cells': True,
    'one_panel_once': True, 'no_checkpoint_selection': True, 'no_consumed_panel_reuse': True,
    'claim_scope': 'narrow arithmetic transfer on one newly admitted panel; no broad English reasoning or own-core independence claim',
    'execution_order': [list(item) for item in ORDER],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal(a, b):
    if type(a) is not type(b): return False
    if type(a) is dict: return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if type(a) in (list, tuple): return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin_shape(record):
    require(type(record) is dict and set(record) == {'path', 'sha256'}
        and type(record['path']) is str and type(record['sha256']) is str
        and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'exact path/SHA256 pin required')
    return record


def safe(root, relative):
    require(type(relative) is str and '\\' not in relative, 'root-relative POSIX path required')
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'escaping input refused')
    result = (Path(root).resolve() / path).resolve()
    require(result.is_relative_to(Path(root).resolve()), 'input escaped through symlink')
    text = '/' + result.as_posix().lower().strip('/') + '/'
    require(not any(s in text for s in ('/blind/', 'sealed-panels', 'sealed-user', 'sealed-blind',
        'dev100', 'stop88', 'reserved-pool', '/confirmation/')), 'reserved content path refused')
    require(result.suffix.lower() in ('.json', '.jsonl', '.py', '.txt', '.md'), 'weight/binary reads refused')
    return result


def pin(root, record):
    pin_shape(record)
    path = safe(root, record['path'])
    require(digest(path) == record['sha256'], 'physical metadata/source pin differs: ' + record['path'])
    return path


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def validate_protocol(protocol):
    for key, value in PROTOCOL_REQUIRED.items():
        require(equal(protocol.get(key), value), 'prospective policy differs: ' + key)
    pin_shape(protocol['endpoints'])
    require(not any('gold' in key.lower() for key in protocol if key not in PROTOCOL_REQUIRED), 'generation protocol cannot carry gold paths')


def validate_endpoints(packet):
    require(packet.get('schema') == 'cap256.fresh-terminal-endpoints.v1', 'endpoint schema differs')
    require(packet.get('terminal_inspection', {}).get('sha256') == INSPECTION_SHA
        and packet.get('terminal_closure', {}).get('sha256') == TERMINAL_SHA, 'fixed terminal evidence differs')
    for name in ('terminal_inspection', 'terminal_closure'): pin_shape(packet[name])
    endpoints = packet.get('endpoints')
    require(type(endpoints) is list and len(endpoints) == 8, 'all eight endpoints required')
    for endpoint, (seed, arm, condition) in zip(endpoints, ORDER):
        require(type(endpoint) is dict and set(endpoint) == {'seed', 'arm', 'condition', 'learning_rate', 'checkpoint'}
            and equal(endpoint['seed'], seed) and endpoint['arm'] == arm and endpoint['condition'] == condition
            and equal(endpoint['learning_rate'], LRS[condition]), 'all eight fixed cells/order required')
        pin_shape(endpoint['checkpoint'])
        require(endpoint['checkpoint']['path'] == f'artifacts/train-contextual-lr-stability-v1/{condition}/seed{seed}/{arm}/final-resume.pt', 'terminal-only checkpoint path required')
    require(len({e['checkpoint']['sha256'] for e in endpoints}) == 8, 'eight unique checkpoint pins required')
    return endpoints


def validate_input_literal_fields(inputs):
    require(type(inputs) is list and len(inputs) == 16, 'exact input16 required')
    for frame in inputs:
        require(type(frame) is dict and set(frame) == INPUT_FIELDS, 'strict input-only question frame required')
        require(all(type(r) is dict and set(r) == LITERAL_FIELDS for r in frame['numeric_registry']),
            'literal registry admits no target/operation/hidden supervision')
    return inputs
