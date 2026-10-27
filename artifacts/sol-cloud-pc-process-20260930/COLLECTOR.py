"""Read-only PC process ownership metadata through the existing Mac watcher.

Command lines are parsed only inside PC memory; arguments, unknown paths and
subprocess diagnostics are never emitted. No PC file/process mutation occurs.
"""
import argparse
import csv
import datetime
import hashlib
import inspect
import io
import json
import ntpath
import os
import pathlib
import platform
import re
import subprocess
import sys

WATCHER_ROOT = pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
COLLECTION_EXIT = pathlib.Path('/Users/ben-hannan/premonition-watch/queue/sol-cloud-static-night-raw-collect-v4.exit')
COLLECTION_RUNNING = COLLECTION_EXIT.with_suffix('.running')
OUTPUT = pathlib.Path('artifacts/sol-cloud-pc-process-20260930/collected-v1')
KNOWN_PIDS = [17336, 3716, 25576]
PREVIOUS_COLLECTOR_PID = 7352
PROJECT_ROOTS = {
    'ordered-v10r2': 'C:/Users/benja/sol-translator-ordered-v10r2',
    'static-night-v2-s0': 'C:/Users/benja/sol-compose-night-v2-s0',
    'ordered-safety-s0': 'C:/Users/benja/sol-stop-ordered-receipt-v1-s0',
    'answer-v11-s0': 'C:/Users/benja/sol-translator-answer-v11-s0',
    'answer-v11-s1': 'C:/Users/benja/sol-translator-answer-v11-s1',
    'tiny-v12-s0': 'C:/Users/benja/sol-translator-tiny-v12-s0',
    'tiny-v12-s1': 'C:/Users/benja/sol-translator-tiny-v12-s1',
    'pc-watcher': 'C:/Users/benja/pcwatch',
}
KNOWN_SCRIPTS = [
    'sol_translator_ground_answer_v11.py', 'sol_translator_tiny_v12.py',
    'sol_translator_ground_ordered_v10.py', 'sol_sleep_ordered_v2.py',
    'sol_stop_ordered_checkpoint_receipt_v1.py', 'sol_cloud_night_v1.py',
]
KNOWN_EXECUTABLES = [
    'C:/Users/benja/lis300/venv/Scripts/python.exe',
    'C:/Users/benja/lis300/venv/Scripts/pythonw.exe',
    'C:/Users/benja/AppData/Local/Programs/Python/Python310/python.exe',
    'C:/Users/benja/AppData/Local/Programs/Python/Python310/pythonw.exe',
]
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15',
       '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2', 'benspc',
       r'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -B -']


def normalized_path(value):
    return str(value or '').replace('\\', '/').lower()


def safe_integer(value):
    text = str(value)
    return int(text) if text.isdigit() else None


def ownership_metadata(commandline):
    """Emit fixed whitelist values, never arbitrary argument/path substrings."""
    commandline = str(commandline or '')[:8192]
    tokens = [quoted or unquoted for quoted, unquoted in
              re.findall(r'"([^"\r\n]*)"|([^\s"]+)', commandline)]
    roots, script_paths, basenames = set(), set(), set()
    for token in tokens:
        normalized = normalized_path(token)
        if '..' in normalized.split('/'):
            continue
        for label, root in PROJECT_ROOTS.items():
            canonical_root = normalized_path(root)
            if normalized == canonical_root or normalized.startswith(canonical_root + '/'):
                roots.add(label)
            for name in KNOWN_SCRIPTS:
                for relative in ('/' + name, '/scripts/' + name):
                    if normalized == canonical_root + relative:
                        script_paths.add(root + relative)
        if normalized in KNOWN_SCRIPTS or normalized in ['scripts/' + name for name in KNOWN_SCRIPTS]:
            basenames.add(ntpath.basename(normalized))
    return {'project_root_matches': sorted(roots), 'known_script_paths': sorted(script_paths),
            'known_script_basenames': sorted(basenames),
            'ownership_scope': 'whitelist references only; not a process-stop authorization'}


def sanitized_process(row, collector_pid):
    image = str(row.get('Name') or '').lower()
    if not re.fullmatch(r'(?:python[0-9.w-]*|py)\.exe', image):
        return None
    executable = normalized_path(row.get('ExecutablePath'))
    approved = next((path for path in KNOWN_EXECUTABLES if normalized_path(path) == executable), '')
    created = str(row.get('created_utc') or '')
    if not re.fullmatch(r'[0-9T:Z.+-]{10,40}', created):
        created = ''
    result = {'pid': safe_integer(row.get('ProcessId')), 'ppid': safe_integer(row.get('ParentProcessId')),
              'created_utc': created, 'image': image, 'executable_path': approved,
              'executable_path_known': bool(approved),
              'inventory_process': safe_integer(row.get('ProcessId')) == collector_pid}
    result.update(ownership_metadata(row.get('CommandLine')))
    return result


def gpu_compute_records(text):
    rows = []
    for values in csv.reader(io.StringIO(text)):
        if len(values) != 3 or safe_integer(values[0].strip()) is None:
            continue
        name = ntpath.basename(values[1].strip().replace('/', '\\'))
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', name):
            name = ''
        rows.append({'pid': safe_integer(values[0].strip()), 'process_name': name,
                     'used_gpu_memory_MiB': safe_integer(values[2].strip())})
    return rows[:128]


def remote_script():
    # Shared pure sanitizers run on PC before anything crosses SSH stdout.
    header = 'import csv,datetime,io,json,ntpath,os,re,shutil,subprocess\n'
    constants = '\n'.join(name + ' = ' + repr(globals()[name]) for name in
                          ('PROJECT_ROOTS', 'KNOWN_SCRIPTS', 'KNOWN_EXECUTABLES', 'KNOWN_PIDS', 'PREVIOUS_COLLECTOR_PID'))
    helpers = '\n'.join(inspect.getsource(function) for function in
                        (normalized_path, safe_integer, ownership_metadata, sanitized_process, gpu_compute_records))
    query = "$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%.exe' OR Name='py.exe'\" | Select-Object -First 129 | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,@{Name='created_utc';Expression={if($_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{''}}}) | ConvertTo-Json -Compress"
    tail = '''
record = {'schema':'sol.cloud.pc-process-inventory.v1','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_pid':os.getpid(),'read_only':True,'model_calls':0,'optimizer_updates':0,'pc_writes':0,'process_stops':0}
try:
    result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',QUERY],capture_output=True,encoding='utf-8',errors='replace',timeout=20)
    if result.returncode or len(result.stdout)>2097152:
        raise ValueError('bounded metadata query failed')
    raw = json.loads(result.stdout or '[]')
    if isinstance(raw,dict):raw=[raw]
    if not isinstance(raw,list):raise ValueError('invalid metadata type')
    record['process_inventory_complete']=len(raw)<=128
    processes=[sanitized_process(row,os.getpid()) for row in raw[:128] if isinstance(row,dict)]
    record['python_processes']=sorted([row for row in processes if row is not None],key=lambda row:row['pid'] or 0)
    pids={row['pid'] for row in record['python_processes']}
    record['known_pid_presence']={str(pid):pid in pids for pid in KNOWN_PIDS}
    record['previous_collector_pid_present']=PREVIOUS_COLLECTOR_PID in pids
except Exception as error:
    record['process_inventory_complete']=False
    record['process_query_error_type']=type(error).__name__
try:
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,encoding='utf-8',errors='replace',timeout=15)
    record['gpu_compute_query_returncode']=result.returncode
    record['gpu_compute_apps']=gpu_compute_records(result.stdout) if result.returncode==0 else []
    result=subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,encoding='utf-8',errors='replace',timeout=15)
    record['gpu_query_returncode']=result.returncode
    record['gpus']=[dict(zip(['index','memory_used_MiB','memory_total_MiB','utilization_percent'],[safe_integer(item.strip()) for item in row])) for row in csv.reader(io.StringIO(result.stdout)) if len(row)==4] if result.returncode==0 else []
except Exception as error:
    record['gpu_query_error_type']=type(error).__name__
record['disk_C']=dict(zip(['total_bytes','used_bytes','free_bytes'],shutil.disk_usage('C:/')))
print(json.dumps(record,sort_keys=True),flush=True)
'''
    return header + constants + '\n' + helpers + '\nQUERY = ' + repr(query) + '\n' + tail


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def write_new(path, payload):
    with pathlib.Path(path).open('x', encoding='utf-8') as stream:
        json.dump(payload, stream, sort_keys=True, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    if file_sha(__file__) != args.source_sha256:
        raise RuntimeError('collector source pin differs')
    if platform.system() != 'Darwin' or sys.version_info[:3] != (3, 9, 6):
        raise RuntimeError('verified native Mac Python 3.9.6 required')
    if not os.environ.get('JOB') or pathlib.Path.cwd().resolve() != WATCHER_ROOT.resolve():
        raise RuntimeError('existing Mac watcher job and publisher worktree required')
    if COLLECTION_RUNNING.exists() or not COLLECTION_EXIT.is_file() or COLLECTION_EXIT.stat().st_size > 32 or COLLECTION_EXIT.read_text().strip() != '0':
        raise RuntimeError('successful collection exit required before process reconciliation')
    output = WATCHER_ROOT / OUTPUT
    output.mkdir(parents=True, exist_ok=False)
    runtime = {'invoked_interpreter':'/usr/bin/python3','reported_executable':sys.executable,
               'resolved_executable':str(pathlib.Path(sys.executable).resolve()),
               'python':platform.python_version(),'machine':platform.machine(),
               'collector_sha256':args.source_sha256,'read_only_pc':True}
    write_new(output / 'LAUNCH.json', runtime)
    result = subprocess.run(SSH, input=remote_script(), text=True, encoding='utf-8',capture_output=True,timeout=90)
    if result.returncode or len(result.stdout) > 65536:
        write_new(output / 'FAILURE.json', {'ssh_returncode':result.returncode,'raw_diagnostics_suppressed':True})
        raise RuntimeError('bounded read-only metadata query failed; diagnostics suppressed')
    inventory = json.loads(result.stdout)
    if inventory.get('schema') != 'sol.cloud.pc-process-inventory.v1':
        raise RuntimeError('unexpected inventory schema')
    write_new(output / 'PC-INVENTORY.json', inventory)
    print(json.dumps(inventory,sort_keys=True),flush=True)
    if inventory.get('process_inventory_complete') is not True:
        raise RuntimeError('process inventory incomplete; ownership remains unresolved')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'collector_error_type':type(error).__name__,'raw_diagnostics_suppressed':True}),flush=True)
        raise SystemExit(1)
