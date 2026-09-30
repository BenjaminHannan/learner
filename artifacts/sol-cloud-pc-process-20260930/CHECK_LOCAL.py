"""Pure sanitizer/syntax checks; no subprocess/network/model execution."""
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pc_metadata_collector', ROOT / 'COLLECTOR.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = []

def check(name, value):
    checks.append({'name': name, 'pass': bool(value)})
    assert value, name

source = (ROOT / 'COLLECTOR.py').read_text()
ast.parse(source, feature_version=(3, 9))
ast.parse(module.remote_script(), feature_version=(3, 9))
check('Mac and remote source parse under Python3.9 grammar', True)
unknown = module.ownership_metadata('python.exe "C:/private/SENTINEL_SECRET.py" --password=SENTINEL_SECRET')
check('unknown arguments/paths emit no values', 'SENTINEL_SECRET' not in json.dumps(unknown) and not unknown['project_root_matches'] and not unknown['known_script_paths'])
known = module.ownership_metadata('python.exe "C:\\Users\\benja\\sol-translator-ordered-v10r2\\scripts\\sol_translator_tiny_v12.py" --password=SENTINEL_SECRET')
check('known exact project script retained without arguments', known['known_script_paths'] == ['C:/Users/benja/sol-translator-ordered-v10r2/scripts/sol_translator_tiny_v12.py'] and 'SENTINEL_SECRET' not in json.dumps(known))
reference = module.ownership_metadata('python.exe C:/Users/benja/sol-compose-night-v2-s0/unknown/SENTINEL_SECRET.py')
check('unknown path inside project root emits categorical root only', reference['project_root_matches'] == ['static-night-v2-s0'] and not reference['known_script_paths'] and 'SENTINEL_SECRET' not in json.dumps(reference))
check('lookalike project root not accepted', not module.ownership_metadata('python.exe C:/Users/benja/sol-translator-ordered-v10r2-SENTINEL_SECRET/scripts/sol_translator_tiny_v12.py')['project_root_matches'])
check('traversal path not accepted', not module.ownership_metadata('python.exe C:/Users/benja/sol-compose-night-v2-s0/../SENTINEL_SECRET.py')['project_root_matches'])
row = module.sanitized_process({'Name':'pythonw.exe','ProcessId':3716,'ParentProcessId':10,'created_utc':'2026-09-29T18:00:00.000Z','ExecutablePath':'C:/private/SENTINEL_SECRET.exe','CommandLine':'pythonw.exe --token=SENTINEL_SECRET'},7352)
check('process PID/parent/start/image retained', (row['pid'],row['ppid'],row['created_utc'],row['image']) == (3716,10,'2026-09-29T18:00:00.000Z','pythonw.exe'))
check('unknown executable path and command line absent', not row['executable_path'] and 'SENTINEL_SECRET' not in json.dumps(row) and 'CommandLine' not in row)
check('collector PID distinguished', module.sanitized_process({'Name':'python.exe','ProcessId':7352},7352)['inventory_process'])
check('non-Python processes excluded', module.sanitized_process({'Name':'private.exe','ProcessId':1},7352) is None)
gpu = module.gpu_compute_records('17336, C:\\private\\python.exe, 1740\n')
check('GPU name is basename only with numeric PID/memory', gpu == [{'pid':17336,'process_name':'python.exe','used_gpu_memory_MiB':1740}])
check('strict SSH flags retained', all(flag in module.SSH for flag in ['BatchMode=yes','StrictHostKeyChecking=yes','UpdateHostKeys=no','ConnectTimeout=15']))
check('only verified known project script basenames', all((ROOT.parents[1] / 'scripts' / name).is_file() for name in module.KNOWN_SCRIPTS))
check('local queue exit gate distinct from published outbox', str(module.COLLECTION_EXIT) == '/Users/ben-hannan/premonition-watch/queue/sol-cloud-static-night-raw-collect-v4.exit')
print(json.dumps({'checks':checks,'passed':len(checks),'total':len(checks),'network_calls':0,'model_calls':0,'optimizer_updates':0,'pc_writes':0,'process_stops':0},indent=2))
