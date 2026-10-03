#!/usr/bin/env python3
"""Mac-side launcher for the approved capability256 arms on BensPC.

One pushed commit is the source of truth: every file (the sealed r4 package
plus this launcher) is read with `git show <commit>:path` and hash-checked, so a
missing or edited file stops the launch instead of silently running.

  python3 scripts/cap256_launch/mac_launch.py start  --commit SHA --arms s0-loop
  python3 scripts/cap256_launch/mac_launch.py start  --commit SHA --arms s0-plain,s1-loop,s1-plain --queue-behind
  python3 scripts/cap256_launch/mac_launch.py status
  python3 scripts/cap256_launch/mac_launch.py fetch  --dest artifacts/cap256-launch/pc-receipts

Status words: queued (request written, waiting for the lock), picked_up /
preflight_package_ok (checks running), runner_started (runner alive, no update
yet), training (FIRST-UPDATE.json saved), completed / failed (EXIT.json saved).
"""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
SPEC_PATH = ('artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v4/'
             'SPEC-sol-cloud-capability256-v1-s0-loop-train-r4.json')
SPEC_SHA = 'f011f7904f5a112c962c3046193ae0b9628d8de3d1fd04b7feb8796541492598'
LAUNCHER_FILES = ('scripts/cap256_launch/pc_guard.py', 'scripts/cap256_launch/pc_driver.py')
PCROOT = 'C:/Users/benja/sol-cloud-numeric-capability-v1'
PCPY = r'C:\Users\benja\lis300\venv\Scripts\python.exe'
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=10', 'benspc']
ARMS = {'s0-loop': (0, 'loop'), 's0-plain': (0, 'plain'), 's1-loop': (1, 'loop'), 's1-plain': (1, 'plain')}


def git(*args):
    return subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, check=True).stdout


def pc_python(source, timeout=600):
    done = subprocess.run([*SSH, PCPY + ' -X utf8 -B -'], input=source.encode('utf8'),
                          capture_output=True, timeout=timeout)
    return done.returncode, done.stdout.decode('utf8', 'replace'), done.stderr.decode('utf8', 'replace')


def header(**values):
    """Bind constants for a PC-side script as literal assignments."""
    return ''.join('%s=%r\n' % item for item in values.items())


STAGE = r'''
import base64,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(ROOT);state=root/'launch-cap256';req=REQUEST;files=FILES;queue_behind=QUEUE_BEHIND
def out(**k):print(json.dumps(k));sys.exit(0 if k.get('ok') else 3)
pkg=state/'pkg'/req['commit'][:12]
for f in files:
    data=base64.b64decode(f['b64']);assert hashlib.sha256(data).hexdigest()==f['sha256']
    rel=pathlib.PurePosixPath(f['path']);assert not rel.is_absolute() and '..' not in rel.parts
    dst=(pkg/rel.name) if f['launcher'] else root.joinpath(*rel.parts)
    if dst.exists():
        if hashlib.sha256(dst.read_bytes()).hexdigest()!=f['sha256']:out(ok=False,error='PC file differs; not overwriting',path=str(dst))
    else:
        dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as s:s.write(data)
lock=state/'LOCK.json'
if lock.exists() and not queue_behind:out(ok=False,error='a batch holds the lock; pass --queue-behind to queue',lock=lock.read_text())
ns=root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'/req['spec']['run_namespace']
for seed,arm in req['arms']:
    if (ns/('seed%d'%seed)/arm).exists() and not req.get('quarantine_zero_update_failures'):out(ok=False,error='arm output already exists',arm=[seed,arm])
    for b in (state/'batches').glob('*/BATCH.json'):
        rec=json.loads(b.read_text())
        if rec.get('status') in ('waiting_for_lock','running') and [seed,arm] in rec.get('arms',[]):
            out(ok=False,error='arm already queued/running in another batch',batch=rec['batch_id'])
bdir=state/'batches'/req['batch_id'];bdir.mkdir(parents=True,exist_ok=False)
rpath=bdir/'REQUEST.json';rpath.write_text(json.dumps(req,indent=2))
line='"%s" -X utf8 -B "%s" run --request "%s" --log "%s"'%(PCPY,pkg/'pc_driver.py',rpath,bdir/'driver.log')
ps="$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='%s';CurrentDirectory='%s'}; \"$($r.ReturnValue) $($r.ProcessId)\""%(line.replace("'","''"),str(root))
enc=base64.b64encode(ps.encode('utf-16-le')).decode()
p=subprocess.run(['powershell','-NoProfile','-NonInteractive','-EncodedCommand',enc],capture_output=True,text=True,timeout=60)
rv,_,pid=p.stdout.strip().partition(' ')
out(ok=p.returncode==0 and rv=='0',wmi_return=rv,driver_pid=pid,stderr=p.stderr[-2000:],request=str(rpath),command=line)
'''

STATUS = r'''
import json,pathlib
state=pathlib.Path(ROOT)/'launch-cap256';r={'lock':None,'batches':[],'jobs':[]}
if (state/'LOCK.json').exists():r['lock']=json.loads((state/'LOCK.json').read_text())
for b in sorted((state/'batches').glob('*/BATCH.json')):r['batches'].append(json.loads(b.read_text()))
for j in sorted((state/'jobs').glob('*')):
    rec={'job_id':j.name}
    for n in ('STATE.json','FIRST-UPDATE.json','PROGRESS.json'):
        if (j/n).exists():rec[n]=json.loads((j/n).read_text())
    r['jobs'].append(rec)
print(json.dumps(r))
'''


def start(args):
    commit = git('rev-parse', args.commit + '^{commit}').decode().strip()
    if not git('branch', '-r', '--contains', commit).strip():
        sys.exit('commit %s is not on any origin branch; push it first' % commit)
    spec_raw = git('show', commit + ':' + SPEC_PATH)
    if hashlib.sha256(spec_raw).hexdigest() != SPEC_SHA:
        sys.exit('sealed r4 spec differs at this commit')
    spec = json.loads(spec_raw)
    files = []
    for pin in spec['files']:
        data = git('show', commit + ':' + pin['path'])
        if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
            sys.exit('package file differs at commit: ' + pin['path'])
        files.append({'path': pin['path'], 'sha256': pin['sha256'], 'launcher': False,
                      'b64': base64.b64encode(data).decode()})
    for path in LAUNCHER_FILES:
        data = git('show', commit + ':' + path)
        files.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'launcher': True,
                      'b64': base64.b64encode(data).decode()})
    queued = datetime.datetime.now(datetime.timezone.utc)
    arms = [list(ARMS[name]) for name in args.arms.split(',')]
    batch_id = queued.strftime('%Y%m%dT%H%M%SZ')
    spec_for_pc = {k: v for k, v in spec.items()}
    request = {'batch_id': batch_id, 'commit': commit, 'queued_utc': queued.isoformat(), 'root': PCROOT,
               'arms': arms, 'spec': spec_for_pc, 'previous_exit_utc': args.previous_exit_utc,
               'quarantine_zero_update_failures': args.quarantine_zero_update_failures}
    source = header(ROOT=PCROOT, REQUEST=request, FILES=files, QUEUE_BEHIND=args.queue_behind, PCPY=PCPY) + STAGE
    rc, out, err = pc_python(source)
    receipt = {'batch_id': batch_id, 'commit': commit, 'queued_utc': request['queued_utc'], 'arms': arms,
               'ssh_returncode': rc, 'pc_stdout': out, 'pc_stderr': err,
               'launcher_file_sha256': {f['path']: f['sha256'] for f in files if f['launcher']}}
    dest = REPO / 'artifacts/cap256-launch' / batch_id
    dest.mkdir(parents=True, exist_ok=False)
    (dest / 'MAC-START.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('batch_id', 'commit', 'ssh_returncode', 'pc_stdout', 'pc_stderr')}, indent=2))
    return 0 if rc == 0 else 1


def status(_args):
    rc, out, err = pc_python(header(ROOT=PCROOT) + STATUS, timeout=60)
    if rc:
        sys.exit('status failed rc=%s %s' % (rc, err))
    report = json.loads(out)
    print('lock:', report['lock'])
    for batch in report['batches']:
        print('batch', batch['batch_id'], batch['status'], 'arms', batch['arms'], 'lock_wait_s', batch.get('lock_wait_seconds'))
    for job in report['jobs']:
        s = job.get('STATE.json', {})
        first = job.get('FIRST-UPDATE.json', {})
        prog = job.get('PROGRESS.json', {})
        print(job['job_id'], s.get('status'), 'updates', prog.get('optimizer_updates', s.get('optimizer_updates')),
              '/5120', 'first_update', first.get('first_update_detected_utc'),
              'queue->first_s', first.get('queue_to_first_update_seconds'),
              'idle_s', s.get('idle_seconds_since_previous_arm'), s.get('error', '')[:300] if s.get('error') else '')
    return 0


def fetch(args):
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run([*SSH, 'tar -cf - -C %s/launch-cap256 jobs batches' % PCROOT], capture_output=True, timeout=300)
    if tar.returncode:
        sys.exit('fetch failed: ' + tar.stderr.decode('utf8', 'replace'))
    subprocess.run(['tar', '-xf', '-', '-C', str(dest)], input=tar.stdout, check=True)
    print('fetched', len(tar.stdout), 'bytes into', dest)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('start')
    s.add_argument('--commit', required=True)
    s.add_argument('--arms', required=True, help='comma list of ' + ','.join(ARMS))
    s.add_argument('--queue-behind', action='store_true', help='wait for the running batch instead of refusing')
    s.add_argument('--quarantine-zero-update-failures', action='store_true',
                   help='move aside (never delete) a prior arm dir that failed with 0 optimizer updates')
    s.add_argument('--previous-exit-utc', help='for idle-time accounting when queueing behind a batch')
    sub.add_parser('status')
    f = sub.add_parser('fetch')
    f.add_argument('--dest', default=str(REPO / 'artifacts/cap256-launch/pc-receipts'))
    args = parser.parse_args()
    return {'start': start, 'status': status, 'fetch': fetch}[args.command](args)


if __name__ == '__main__':
    raise SystemExit(main())
