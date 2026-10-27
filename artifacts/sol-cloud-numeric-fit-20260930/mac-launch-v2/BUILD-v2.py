#!/usr/bin/env python3
"""Freeze exact transport specs/held queues from integrator's final byte pins."""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[2]
ORDER=[(0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')]
PCROOT='C:/Users/benja/sol-cloud-numeric-capability-v1'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_new(path,value):
    with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True)+'\n')


def render_queue(seed,arm,files,spec_pin):
    job='sol-cloud-numeric-v1-s%d-%s-r2-benspc'%(seed,arm)
    bootstrap="""import hashlib,os,pathlib,subprocess,time
started=time.monotonic()
files=__FILES__
for pin in files:
 result=subprocess.run(['git','show','origin/main:'+pin['path']],capture_output=True,timeout=min(10,600-(time.monotonic()-started)),check=True)
 assert hashlib.sha256(result.stdout).hexdigest()==pin['sha256'],'sealed source unavailable/different'
 path=pathlib.Path(pin['path']);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256'],'existingsource differs; preserve it'
 else:
  with path.open('xb') as stream:stream.write(result.stdout)
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',__WRAPPER__,'--seed',__SEED__,'--arm',__ARM__,'--spec',__SPEC__,'--spec-sha256',__SPEC_SHA__,'--started-monotonic',str(started)])
""".replace('__WRAPPER__',repr(str((OWN/'MAC-LAUNCH-v2.py').relative_to(ROOT)))).replace('__SEED__',repr(str(seed))).replace('__ARM__',repr(arm)).replace('__SPEC_SHA__',repr(spec_pin['sha256'])).replace('__SPEC__',repr(spec_pin['path'])).replace('__FILES__',repr(files))
    shell="set -euo pipefail\ncd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27\nperl -e 'alarm shift; exec @ARGV' 600 /usr/bin/python3 -B - <<'NUMERIC_MAC_BOOTSTRAP'\n"+bootstrap+"NUMERIC_MAC_BOOTSTRAP\n"
    header='''BASH-ONLY: yes
GPU: yes
DISK: 0
TIME CAP: 10 minutes
LABEL: __JOB__
PUSH: __OUT__

HELD serial template; sole integrator owns actual main/queue publication. Fixed order s0-loop, s0-plain, s1-loop, s1-plain; only first job live initially. Previous physical watcher exits and exact PC transport dispositions must already be closed. No retries or altered sealed model/objective/scoring. Complete canonical numeric target plus EOS is scored without number extraction.
NativeMac3.9.6 /usr/bin/python3 and verifiedPC3.10.9; actual copied-main running claim/shared GPUclaim required. Same600second deadline covers source staging, bounded driver and small return. No archive extraction, weight copies or deletion. Exact PCstdout/stderr/SSHrc preserved even absent manifest; optional PID metadata cannot abort. Large states/raw evidence stay onPC if outside bounded small return.

```bash
'''.replace('__JOB__',job).replace('__OUT__',str(OWN.relative_to(ROOT))+'/execution-r2-s%d-%s'%(seed,arm))
    return header+shell+'```\n',bootstrap,shell


def main():
    p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--package-sha256',required=True)
    p.add_argument('--bootstrap',required=True);p.add_argument('--bootstrap-sha256',required=True);args=p.parse_args()
    for path,expected in [(args.package,args.package_sha256),(args.bootstrap,args.bootstrap_sha256)]:
        if sha(ROOT/path)!=expected:raise ValueError('supplied final external source SHA differs')
    wrapper={'path':str((OWN/'MAC-LAUNCH-v2.py').relative_to(ROOT)),'sha256':sha(OWN/'MAC-LAUNCH-v2.py')}
    pins=[]
    for seed,arm in ORDER:
        spec={'schema':'sol.cloud.numeric-mac-launch-spec.v1','job':'sol-cloud-numeric-v1-s%d-%s-r2-benspc'%(seed,arm),
              'seed':seed,'arm':arm,'pc_root':PCROOT,'actual_user_day':False,'activated':False,
              'package':{'path':args.package,'sha256':args.package_sha256},'bootstrap':{'path':args.bootstrap,'sha256':args.bootstrap_sha256}}
        specpath=OWN/('SPEC-s%d-%s.json'%(seed,arm));dump_new(specpath,spec)
        specpin={'path':str(specpath.relative_to(ROOT)),'sha256':sha(specpath)}
        text,bootstrap,shell=render_queue(seed,arm,[wrapper,specpin],specpin)
        ast.parse(bootstrap,feature_version=(3,9))
        with tempfile.NamedTemporaryFile(mode='w',suffix='.sh',dir='/tmp',delete=False) as f:f.write(shell);temp=f.name
        try:subprocess.run(['bash','-n',temp],check=True,capture_output=True)
        finally:Path(temp).unlink()
        queue=OWN/('HELD-queue-'+spec['job']+'.md')
        with queue.open('x',encoding='utf8') as stream:stream.write(text)
        for path in (specpath,queue):pins.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path)})
    for path in (OWN/'MAC-LAUNCH-v2.py',OWN/'BUILD-v2.py',OWN/'CHECK-v2.py',OWN/'CHECKS-v2.json'):
        pins.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path)})
    freeze={'schema':'sol.cloud.numeric-mac-launch-freeze.v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'pins':pins,'external_package':args.package_sha256,'external_PC_bootstrap':args.bootstrap_sha256,
            'CPU_checks':26,'Mac39_bootstrap_AST_and_rendered_Bash_syntax':True,'model_calls':0,'GPU_calls':0,'optimizer_updates':0,
            'SSH_calls':0,'live_queue_entries':0,'integrator_is_sole_publisher':True,'four_jobs_serial':ORDER}
    dump_new(OWN/'FREEZE-v1.json',freeze)
    print(json.dumps({'pins':pins,'freeze_sha256':sha(OWN/'FREEZE-v1.json')},indent=2))


if __name__=='__main__':main()
