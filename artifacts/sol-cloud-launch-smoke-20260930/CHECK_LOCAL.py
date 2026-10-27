"""Bounded local source/adversarial checks; no model/optimizer/remote execution."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OWN = ROOT / 'artifacts/sol-cloud-launch-smoke-20260930'
spec = importlib.util.spec_from_file_location('offline_launch_smoke', ROOT / 'scripts/sol_cloud_offline_launch_smoke_v1.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
package = json.loads((OWN / 'r5-v1/SOURCE-PACKAGE.json').read_bytes())
checks = []


def check(name, value):
    checks.append({'name': name, 'pass': bool(value)})
    assert value, name


def rejected(function):
    try:
        function()
    except ValueError:
        return True
    return False


source = (ROOT / 'scripts/sol_cloud_offline_launch_smoke_v1.py').read_text()
ast.parse(source, feature_version=(3, 9))
stdin_probe = smoke.probe_source(package, str(ROOT), None, None)
ast.parse(stdin_probe, feature_version=(3, 9))
compile(stdin_probe, '<generated-stdin-probe>', 'exec')
check('driver and standalone stdin probe parse under native Python3.9 syntax', True)
template = (OWN / 'queue-template-sol-cloud-offline-launch-smoke-r5-v2.md').read_text()
bootstrap = template.split("<<'SMOKE_BOOTSTRAP'\n", 1)[1].split('\nSMOKE_BOOTSTRAP', 1)[0]
ast.parse(bootstrap, feature_version=(3, 9))
compile(bootstrap, '<queue-Python-heredoc>', 'exec')
check('queue Python heredoc compiles under Python3.9 syntax', True)
bash = template.split('```bash\n', 1)[1].split('```', 1)[0]
check('queue Bash syntax passes', subprocess.run(['bash', '-n'], input=bash, text=True, capture_output=True).returncode == 0)
actual_stdin = subprocess.run([__import__('sys').executable, '-B', '-'], input=stdin_probe,
                             text=True, capture_output=True, timeout=10)
check('generated stdin probe actually imports selected sources on current local interpreter', actual_stdin.returncode == 0 and json.loads(actual_stdin.stdout)['pass'])
check('exact three explicit modules decoded', set(smoke.verify_package(package)) == set(smoke.SELECTED.values()))
damaged = copy.deepcopy(package)
damaged['modules'][0]['source_b64'] = 'eA=='
check('source hash drift rejected before imports', rejected(lambda: smoke.verify_package(damaged)))
unknown = copy.deepcopy(package)
unknown['modules'][0]['path'] = 'scripts/unknown.py'
check('unknown module and source path rejected before imports', rejected(lambda: smoke.verify_package(unknown)))
for name in ('../outside.py', '/absolute.py', 'C:/outside.py', 'scripts/../outside.py',
             'scripts\\outside.py', './scripts/file.py', 'scripts//file.py'):
    check('unsafe relative path rejected: ' + name, rejected(lambda name=name: smoke.safe_relative(name)))
regular = tarfile.TarInfo('scripts/safe.py')
regular.size = 1
smoke.regular_members_only([regular], {'scripts/safe.py'})
check('exact regular manual member check succeeds without extraction', True)
for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE):
    member = tarfile.TarInfo('scripts/safe.py')
    member.type = kind
    check('link or special member rejected: ' + str(kind), rejected(lambda member=member: smoke.regular_members_only([member], {'scripts/safe.py'})))
check('duplicate manual members rejected', rejected(lambda: smoke.regular_members_only([regular, regular], {'scripts/safe.py'})))
with tempfile.TemporaryDirectory(prefix='sol-launch-smoke-path-') as folder:
    root = Path(folder)
    destination = root / 'destination'
    destination.mkdir()
    outside = root / 'outside'
    outside.mkdir()
    (destination / 'scripts').symlink_to(outside, target_is_directory=True)
    check('existing parent symlink cannot escape virtual layout containment', rejected(lambda: smoke.contained_target(destination, 'scripts/safe.py')))
receipt = smoke.run_probe(package, str(ROOT))
check('current local interpreter imports all three exact sources with no side effects', receipt['pass'] and len(receipt['modules']) == 3 and not receipt['denied_side_effects'])
check('tar API capability invokes empty archive method and records actual behavior', receipt['tar_capabilities']['empty_archive_filter_data_call'] in ('supported', 'unavailable') and receipt['tar_capabilities']['filesystem_extractions'] == 0)
check('local allocation-unit query is bounded metadata only', receipt['allocation_capabilities'].get('r5_allocation_unit_bound_ok') is True and receipt['allocation_capabilities']['filesystem_writes'] == 0)
for label, statement in (
        ('data open', "open('/forbidden-human-packet.json', 'rb')"),
        ('model import', "__import__('torch')"),
        ('subprocess launch', "__import__('subprocess').run(['forbidden-child-command'])")):
    adversarial = copy.deepcopy(package)
    first = adversarial['modules'][0]
    data = __import__('base64').b64decode(first['source_b64']) + ('\n' + statement + '\n').encode()
    first['source_b64'] = __import__('base64').b64encode(data).decode()
    first['sha256'] = hashlib.sha256(data).hexdigest()
    rejected_receipt = smoke.run_probe(adversarial, str(ROOT))
    check('audit denies adversarial ' + label + ' before side effect', not rejected_receipt['pass'] and bool(rejected_receipt['denied_side_effects']))
report = {'checks': checks, 'passed': len(checks), 'total': len(checks),
          'model_calls': 0, 'optimizer_updates': 0, 'remote_calls': 0,
          'claim_scope': 'current Linux interpreter and source guards only; actual Mac/PC receipts pending'}
print(json.dumps(report, indent=2))
