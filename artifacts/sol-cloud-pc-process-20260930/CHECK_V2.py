"""New metadata/protocol checks only; no network, model or PC execution."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pc_metadata_v2', ROOT / 'COLLECTOR-v2.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = []


def check(name, result):
    checks.append({'name': name, 'pass': bool(result)})
    assert result, name


ast.parse((ROOT / 'COLLECTOR-v2.py').read_text(), feature_version=(3, 9))
ast.parse(module.remote_script(), feature_version=(3, 9))
check('local and remote v2 source parse under native Python3.9 grammar', True)
check('frozen v1 collector remains identical', hashlib.sha256((ROOT / 'COLLECTOR.py').read_bytes()).hexdigest() == '60d8ff63f55884a245e319ca93d27e975a9a8bb44c2f09c8964c8083aeb9b483')
expected = ['C:/Users/benja/sol-translator-tiny-v12/artifacts/sol-translator-20260929/tiny-v12-s0/connected-resume.pt', 'C:/Users/benja/sol-translator-tiny-v12/artifacts/sol-translator-20260929/tiny-v12-s1/connected-resume.pt']
check('only two exact authorized checkpoint paths', module.RESUME_PATHS == expected)
with patch.object(module.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFREG, st_size=33554432, st_mtime_ns=1790751234567890000)) as calls, patch('builtins.open', side_effect=AssertionError('checkpoint content read prohibited')):
    rows = module.stat_exact_resumes()
    check('stat visits exactly two paths with symlink following disabled', calls.call_args_list == [((path,), {'follow_symlinks': False}) for path in expected])
    check('successful metadata contains only exact path bytes and mtime', rows == [{'path': path, 'bytes': 33554432, 'mtime_ns': 1790751234567890000} for path in expected])
with patch.object(module.os, 'stat', side_effect=FileNotFoundError('SENTINEL_SECRET')):
    check('missing metadata hides raw exception details', module.stat_exact_resumes() == [{'path': path, 'error_type': 'FileNotFoundError'} for path in expected])
with patch.object(module.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFLNK, st_size=10, st_mtime_ns=2)):
    check('symlink metadata is rejected without following target', module.stat_exact_resumes() == [{'path': path, 'error_type': 'ValueError'} for path in expected])
with tempfile.TemporaryDirectory() as folder:
    done, running = Path(folder) / 'job.exit', Path(folder) / 'job.running'
    done.write_text('rc=0\n')
    check('actual watcher rc=0 protocol is admitted', module.collection_ready(done, running))
    done.write_text('0\n')
    check('old incompatible receipt text is rejected', not module.collection_ready(done, running))
    done.write_text('rc=0\n')
    running.touch()
    check('collection running marker prevents inventory', not module.collection_ready(done, running))
queue = (ROOT / 'queue-template-sol-cloud-pc-process-reconcile-v2.md').read_text()
sha = hashlib.sha256((ROOT / 'COLLECTOR-v2.py').read_bytes()).hexdigest()
check('bootstrap pins collector bytes from origin/main', sha in queue and "['git', 'show', 'origin/main:' + str(source)]" in queue and "source.open('xb')" in queue and 'existing collector differs; preserved without overwrite' in queue)
bash = queue.split('```bash\n', 1)[1].split('```', 1)[0]
result = subprocess.run(['bash', '-n'], input=bash, text=True, capture_output=True)
check('queue Bash syntax passes', result.returncode == 0)
check('remote runtime reports exact version without imports of model', "'version_info':list(sys.version_info[:3])" in module.remote_script() and 'import torch' not in module.remote_script())
check('read-only collector requires known cwd without unsupported JOB environment', "pathlib.Path.cwd().resolve() != WATCHER_ROOT.resolve()" in (ROOT / 'COLLECTOR-v2.py').read_text() and "os.environ.get('JOB')" not in (ROOT / 'COLLECTOR-v2.py').read_text() and "os.environ['JOB']" not in queue)
check('remote runtime inspects tar filter capability without extraction', "'filter' in inspect.signature(tarfile.TarFile.extractall).parameters" in module.remote_script() and "hasattr(tarfile,'data_filter')" in module.remote_script() and '.extractall(' not in module.remote_script())
owned = module.ownership_metadata('python.exe C:/Users/benja/sol-translator-tiny-v12/scripts/sol_translator_tiny_v12.py --token=SENTINEL_SECRET')
check('shared V12 project ownership is categorical and redacted', owned['project_root_matches'] == ['tiny-v12'] and 'SENTINEL_SECRET' not in json.dumps(owned))
print(json.dumps({'checks': checks, 'passed': len(checks), 'total': len(checks), 'network_calls': 0, 'model_calls': 0, 'optimizer_updates': 0, 'pc_writes': 0, 'process_stops': 0}, indent=2))
