#!/usr/bin/env python3
"""Transport-only relay for the pinned CPU weights_only checkpoint audits."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

WATCHER_ROOT = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
PC_ROOT = 'C:/Users/benja/sol-cloud-numeric-capability-v1'
PC_PYTHON = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
OWN_REL = Path('artifacts/sol-cloud-verifier-20260930/numeric16-checkpoint-audit-r2')
TIMEOUT_SECONDS = 540
STRICT_SSH = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
              '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=10',
              '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2']
SOURCES = [
    {'path': 'artifacts/sol-cloud-verifier-20260930/recount_numeric_checkpoint_v2.py',
     'sha256': '4d1d81e73bf5a6eab3cc605e3cbeee661cc41478d343159a80dc8377ce97968d',
     'bytes': 13568},
    {'path': 'artifacts/sol-cloud-verifier-20260930/recount_saved_numeric16_v2.py',
     'sha256': '4dff4349b458d8b462ff712e6789c9ce68fc58f54341abc6726acded1e7eddca'},
]
ARMS = [(0, 'loop'), (0, 'plain'), (1, 'loop'), (1, 'plain')]
EXPECTED = {
    (0, 'loop'): {'bytes': 109627251, 'checkpoint': '6b63344aeeafaa2d51a6255c282b20822cca3872a47f0fe44f8fc35b74908584', 'closed': 'e2e9e296d23f25ecd063ee8a7fd2c8aade496385c2a8d500d735d3a199604ca2'},
    (0, 'plain'): {'bytes': 432016889, 'checkpoint': '619115ebc7ae140e2e7699e65270216af90d44a93e9d1fdcbc87b20c089b68', 'closed': '4a44f2022a9b4868f272551fa6a2bda4f7cbc77b8d890fb6e9c1eb7ee970e660'},
    (1, 'loop'): {'bytes': 109627315, 'checkpoint': '4f0b2614cff2e6e10ea2e52b8765f6102d81099aad89538e99b5fd4c8b42b51e', 'closed': 'fc69dc95dbddc814333099afe33fe56636f6bbc163212fc2d5feb4fba1b64a43'},
    (1, 'plain'): {'bytes': 415180585, 'checkpoint': '5c49e22f0d5a4471542bc5c17aec6eb0b035b8229a93b5ea6850fc29108451fd', 'closed': '01a0e01930d08f6e58dfe74b71f052394e0f4f15bd7ee1e0cc5cc523341a10e8'},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def fetch_main_source(pin):
    result = subprocess.run(['git', '-C', str(WATCHER_ROOT), 'show',
                             'origin/main:' + pin['path']], capture_output=True,
                            timeout=15)
    if result.returncode or len(result.stdout) > 65536 or sha(result.stdout) != pin['sha256']:
        raise RuntimeError('pinned audit source unavailable or changed: ' + pin['path'])
    if 'bytes' in pin and len(result.stdout) != pin['bytes']:
        raise RuntimeError('pinned audit source size changed: ' + pin['path'])
    return result.stdout


def remote_program(payload):
    source = r'''import base64,datetime,hashlib,json,os,pathlib,shutil,subprocess,sys
PAYLOAD=__PAYLOAD__
EXPECTED=__EXPECTED__
ROOT=pathlib.Path(r'C:/Users/benja/sol-cloud-numeric-capability-v1').resolve()
OWN=(ROOT/'artifacts/sol-cloud-verifier-20260930').resolve()
assert ROOT.is_absolute() and ROOT.as_posix().casefold()=='c:/users/benja/sol-cloud-numeric-capability-v1'
def sha(b):return hashlib.sha256(b).hexdigest()
def contained(path,parent):
 p=path.resolve();q=parent.resolve()
 assert p==q or q in p.parents, 'path escaped approved root'
 return p
for relative,item in PAYLOAD.items():
 path=contained(ROOT/relative,ROOT)
 data=base64.b64decode(item['data'],validate=True)
 assert len(data)==item['bytes'] and sha(data)==item['sha256'], 'Mac source payload pin mismatch'
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  assert path.is_file() and not path.is_symlink() and sha(path.read_bytes())==item['sha256'], 'existing PC audit source differs; preserved'
 else:
  with path.open('xb') as stream:stream.write(data)
def hash_file(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def original_manifest():
 rows=[]
 for (seed,arm),pin in EXPECTED.items():
  run=ROOT/'artifacts/sol-cloud-numeric-fit-20260930/run-v1/seed%d/%s'%(seed,arm)
  checkpoint=run/'final-resume.pt';closed=run/'CLOSED.json'
  for path in (checkpoint,closed):
   assert path.is_file() and not path.is_symlink(), 'exact original missing or not regular: '+path.name
  cs=checkpoint.stat();ds=closed.stat()
  assert cs.st_size==pin['bytes'] and hash_file(checkpoint)==pin['checkpoint'], 'checkpoint original before audit differs'
  assert hash_file(closed)==pin['closed'], 'CLOSED before audit differs'
  rows.append({'seed':seed,'arm':arm,'checkpoint_bytes':cs.st_size,'checkpoint_sha256':pin['checkpoint'],
               'checkpoint_mtime_ns':cs.st_mtime_ns,'closed_bytes':ds.st_size,'closed_sha256':pin['closed'],
               'closed_mtime_ns':ds.st_mtime_ns})
 return rows
def process_inventory():
 cmd=("$items = Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%.exe' OR Name='py.exe'\" | "
      "Select-Object -First 129 ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine; "
      "ConvertTo-Json -Compress -InputObject @($items)")
 p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',cmd],capture_output=True,text=True,timeout=20)
 if p.returncode or len(p.stdout)>262144:raise RuntimeError('bounded sanitized Python process query failed')
 parsed=json.loads(p.stdout) if p.stdout.strip() else []
 if isinstance(parsed,dict):parsed=[parsed]
 if not isinstance(parsed,list) or len(parsed)>128:raise RuntimeError('process result exceeds bounded record count')
 rows=[]
 root_text=ROOT.as_posix().casefold().rstrip('/')
 for row in parsed:
  cmdline=str(row.get('CommandLine') or '').replace('\\','/').casefold()
  name=str(row.get('Name') or '').lower()
  rows.append({'pid':int(row['ProcessId']) if str(row.get('ProcessId','')).isdigit() else None,
               'ppid':int(row['ParentProcessId']) if str(row.get('ParentProcessId','')).isdigit() else None,
               'name':name if len(name)<=80 else '',
               'project_root_match':root_text in cmdline,
               'audit_process':str(row.get('ProcessId'))==str(os.getpid())})
 return rows
def snapshot():
 disk=shutil.disk_usage('C:/')
 gpu=subprocess.run(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used,memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=20)
 apps=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=20)
 if gpu.returncode or apps.returncode:raise RuntimeError('read-only GPU inventory failed')
 gpu_apps=[]
 for line in apps.stdout.splitlines():
  values=[x.strip() for x in line.split(',')]
  if len(values)==3:
   base=pathlib.PureWindowsPath(values[1]).name
   gpu_apps.append({'pid':int(values[0]) if values[0].isdigit() else None,
                    'basename':base if base.replace('_','').replace('-','').replace('.','').isalnum() and len(base)<=80 else '',
                    'used_gpu_memory_MiB':int(values[2]) if values[2].isdigit() else None})
 return {'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'C_total_bytes':disk.total,'C_free_bytes':disk.free,'C_used_bytes':disk.used,
         'python_processes_sanitized':process_inventory(),
         'gpu_rows':gpu.stdout.splitlines()[:8],'gpu_compute_apps':gpu_apps[:128]}
before=snapshot()
if any(p['project_root_match'] for p in before['python_processes_sanitized']):
 raise RuntimeError('numeric project process still active; audit refused')
originals_before=original_manifest()
auditor=OWN/'recount_numeric_checkpoint_v2.py'
reports=[];failures=[]
for seed,arm in ((0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')):
 name='NUMERIC16-R3-S%d-%s-ACTUAL-CHECKPOINT-RECOUNT-v1.json'%(seed,arm.upper())
 run=ROOT/'artifacts/sol-cloud-numeric-fit-20260930/run-v1/seed%d/%s'%(seed,arm)
 output=OWN/name
 checkpoint=run/'final-resume.pt'
 argv=[sys.executable,'-X','utf8','-B',str(auditor),'--repo-root',str(ROOT),
       '--checkpoint',str(checkpoint),'--run',str(run),'--seed',str(seed),
       '--arm',arm,'--output',str(output)]
 try:
  p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',timeout=180)
  if len(p.stdout.encode('utf-8'))>262144 or len(p.stderr.encode('utf-8'))>262144:
   failures.append({'seed':seed,'arm':arm,'returncode':p.returncode,'bounded_output_exceeded':True})
   break
  if p.returncode:
   failures.append({'seed':seed,'arm':arm,'returncode':p.returncode,
                    'stdout_tail':p.stdout[-4000:],'stderr_tail':p.stderr[-8000:]})
   break
  assert output.is_file() and not output.is_symlink(), 'audit proof not saved'
  data=output.read_bytes();assert len(data)<=1048576, 'audit proof exceeds small-return bound'
  report=json.loads(data)
  assert report['seed']==seed and report['arm']==arm and report['global_update']==800
  assert report['safe_load']=={'map_location':'cpu','weights_only':True,'unsafe_fallback':False,
                               'torch_version':report['safe_load']['torch_version']}
  assert report['model_calls']==report['tokenizer_calls']==report['optimizer_calls']==report['GPU_calls']==0
  reports.append({'name':name,'bytes':len(data),'sha256':sha(data),
                  'data':base64.b64encode(data).decode('ascii'),
                  'safe_load':report['safe_load'],'actual_tensor_checks_passed':report['actual_tensor_checks_passed'],
                  'checkpoint':report['checkpoint']})
 except Exception as e:
  failures.append({'seed':seed,'arm':arm,'exception_type':type(e).__name__,'error':str(e)[:4000]})
after=snapshot()
originals_after=original_manifest()
if originals_before!=originals_after:
 failures.append({'stage':'original_checkpoint_after_audit','error':'original stat/hash manifest changed'})
result={'schema':'sol.cloud.numeric16.checkpoint-audit-transport.v1',
        'before':before,'after':after,'originals_before':originals_before,
        'originals_after':originals_after,'reports':reports,'failures':failures,
        'model_calls':0,'tokenizer_calls':0,'optimizer_calls':0,'GPU_compute_calls':0,
        'CUDA_used':False,'training_or_checkpoint_write':False,'original_checkpoints_preserved':True}
print(json.dumps(result,sort_keys=True,allow_nan=False),flush=True)
if failures:raise SystemExit(1)
'''
    return source.replace('__PAYLOAD__', repr(payload)).replace('__EXPECTED__', repr(EXPECTED))


def main():
    if platform.system() != 'Darwin' or sys.version_info[:3] != (3, 9, 6):
        raise RuntimeError('verified native Mac3.9.6 required')
    if Path.cwd().resolve() != WATCHER_ROOT.resolve():
        raise RuntimeError('actual watcher source worktree required')
    started = time.monotonic()
    out = WATCHER_ROOT / OWN_REL
    out.mkdir(parents=True, exist_ok=False)
    payload = {}
    for pin in SOURCES:
        data = fetch_main_source(pin)
        payload[pin['path']] = {'sha256': pin['sha256'], 'bytes': len(data),
                                'data': base64.b64encode(data).decode('ascii')}
    remote = remote_program(payload)
    if time.monotonic() - started > 20:
        raise TimeoutError('audit source staging budget exceeded before PC call')
    command = ['ssh', '-T', *STRICT_SSH, 'benspc',
               PC_PYTHON + ' -X utf8 -B -']
    exit_record = {'spawned': False, 'returncode': None, 'timed_out': False,
                   'audit_kind': 'CPU weights_only checkpoint/Adam audit',
                   'original_checkpoints_preserved': True}
    try:
        exit_record['spawned'] = True
        result = subprocess.run(command, input=remote.encode('utf-8'),
                                capture_output=True, timeout=TIMEOUT_SECONDS)
        exit_record['returncode'] = result.returncode
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        exit_record['timed_out'] = True
        stdout = error.stdout or b''
        stderr = error.stderr or b''
        exit_record['returncode'] = None
    exit_record['stdout_bytes'] = len(stdout)
    exit_record['stderr_bytes'] = len(stderr)
    exit_record['stdout_sha256'] = sha(stdout)
    exit_record['stderr_sha256'] = sha(stderr)
    write_new(out / 'PC-SSH-EXIT.json',
              (json.dumps(exit_record, sort_keys=True, indent=2) + '\n').encode())
    write_new(out / 'PC-stdout.log', stdout)
    write_new(out / 'PC-stderr.log', stderr)
    if exit_record['timed_out'] or exit_record['returncode'] != 0:
        raise RuntimeError('PC audit failed or timed out; exact SSH stdout/stderr retained')
    packet = json.loads(stdout)
    assert packet['schema'] == 'sol.cloud.numeric16.checkpoint-audit-transport.v1'
    assert not packet['failures'] and len(packet['reports']) == 4
    for report in packet['reports']:
        data = base64.b64decode(report.pop('data'), validate=True)
        assert len(data) == report['bytes'] and sha(data) == report['sha256']
        parsed = json.loads(data)
        assert parsed['seed'] in (0, 1) and parsed['arm'] in ('loop', 'plain')
        assert parsed['safe_load']['weights_only'] is True
        assert parsed['safe_load']['map_location'] == 'cpu'
        assert parsed['model_calls'] == parsed['tokenizer_calls'] == parsed['optimizer_calls'] == parsed['GPU_calls'] == 0
        write_new(out / report['name'], data)
    packet['reports'] = [{k: v for k, v in row.items() if k != 'data'}
                         for row in packet['reports']]
    write_new(out / 'AUDIT-RETURN.json',
              (json.dumps(packet, sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps({'audit_receipt_path': str(out), 'checkpoint_reports': len(packet['reports']),
                      'all_weights_only_cpu': True, 'all_originals_preserved': True,
                      'failures': packet['failures']}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
