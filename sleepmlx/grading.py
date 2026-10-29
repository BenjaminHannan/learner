"""One byte-identical Python/Node grading contract; no model imports."""
import hashlib
import json
import re
from pathlib import Path

_BYTES = Path(__file__).with_name('grading-contract.json').read_bytes()
CONTRACT = json.loads(_BYTES)
if (type(CONTRACT.get('version')) is not int or CONTRACT['version'] != 1
        or (not isinstance(CONTRACT.get('grader'), str) or not re.fullmatch(r'strict-[1-9][0-9]*', CONTRACT['grader'])) or CONTRACT.get('head_words') != 12
        or not isinstance(CONTRACT.get('served'), dict)
        or set(CONTRACT['served']) != {'general_n', 'max_general_loss', 'held_max'}
        or any(type(CONTRACT['served'][key]) is not int or CONTRACT['served'][key] != value for key, value in {'general_n': 8, 'max_general_loss': 1, 'held_max': 12}.items())):
    raise ValueError('Unsupported grading contract.')
GRADER = CONTRACT['grader']
CONTRACT_SHA256 = hashlib.sha256(_BYTES).hexdigest()


def binding():
    return {'grader': GRADER, 'grading_contract_sha256': CONTRACT_SHA256}


def current(verdict):
    return isinstance(verdict, dict) and all(verdict.get(k) == v for k, v in binding().items())


def valid_metrics(verdict, held_count):
    policy = CONTRACT['served']
    if (not isinstance(verdict, dict) or type(held_count) is not int or not 1 <= held_count <= policy['held_max']
            or type(verdict.get('general_n')) is not int or verdict['general_n'] != policy['general_n']
            or type(verdict.get('held_n')) is not int or verdict['held_n'] != held_count):
        return False
    return all(type(verdict.get(key)) is int and 0 <= verdict[key] <= count
               for key, count in [('general_on', policy['general_n']), ('general_off', policy['general_n']),
                                  ('held_on', held_count), ('held_off', held_count)])


def served_pass(verdict):
    return (verdict['general_on'] >= verdict['general_off'] - CONTRACT['served']['max_general_loss']
            and verdict['general_on'] * 2 >= verdict['general_off'] and verdict['held_on'] >= verdict['held_off'])


def valid_decision(verdict, held_count):
    return (current(verdict) and valid_metrics(verdict, held_count) and type(verdict.get('ok')) is bool
            and 'failure_kind' not in verdict and ('pending' not in verdict or verdict['pending'] is False) and verdict['ok'] == served_pass(verdict))


def mechanical_rejection(verdict, expected_adapter_sha256):
    return (current(verdict) and verdict.get('ok') is False and ('pending' not in verdict or verdict['pending'] is False)
            and verdict.get('failure_kind') == 'adapter_load' and type(verdict.get('adapter_exit_code')) is int
            and verdict.get('plain_load_verified') is True and isinstance(expected_adapter_sha256, str)
            and re.fullmatch(r'[0-9a-f]{64}', expected_adapter_sha256) and verdict.get('checked_adapter_sha256') == expected_adapter_sha256
            and not any(key in verdict for key in ('general_n', 'general_on', 'general_off', 'held_n', 'held_on', 'held_off')))
