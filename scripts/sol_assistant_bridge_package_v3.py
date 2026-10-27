#!/usr/bin/env python3
"""Seal a concrete bounded watcher bridge job from integrator-owned exact pipeline.
No network, execution, training, implicit source selection or fake weight bindings.
"""
import argparse,ast,hashlib,json,subprocess,tarfile
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,sha,save_new,Unavailable
from sol_assistant_watcher_bridge_v3 import checked_spec

def build(spec_path,sources_path,out):
    out=owned(out);out.mkdir(parents=True,exist_ok=False)
    spec=json.loads(Path(spec_path).read_text(encoding='utf-8'));digest=sha(spec_path)
    checked_spec(spec_path,digest)
    sources=json.loads(Path(sources_path).read_text(encoding='utf-8'))
    # Explicit local source inventory only; no checkpoint or LM bytes in this transport.
    files={}
    for relative,expected in sources.items():
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT) or path.suffix not in ('.py','.json') or sha(path)!=expected:raise Unavailable('source inventory mismatch')
        if path.stat().st_size>4*1024**2:raise Unavailable('small code/plan transport only')
        if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
        files[path.relative_to(ROOT).as_posix()]=expected
    remote_root=spec['pc_root'].rstrip('/')
    bridge='scripts/sol_assistant_watcher_bridge_v3.py'
    if files.get(bridge)!=spec['remote_source']['sha256'] or spec['remote_source']['path']!=remote_root+'/'+bridge:raise Unavailable('exact bridge source missing')
    for phase in spec['pipeline']:
        argv=phase['argv']
        if not argv or argv[0]!='{python}':raise Unavailable('explicit Python pipeline required')
        scripts=[x for x in argv[1:] if x.endswith('.py')]
        if len(scripts)!=1:raise Unavailable('one explicit pinned Python entrypoint per phase')
        source=scripts[0].removeprefix(remote_root+'/')
        if source not in files:raise Unavailable('pipeline source absent from transport inventory')
        if not any(p['path']==remote_root+'/'+source and p['sha256']==files[source] for p in spec['dependency_pins']):raise Unavailable('pipeline entrypoint not pinned in bridge spec')
    expected_spec=remote_root+'/'+out.relative_to(ROOT).as_posix()+'/bridge-spec.json'
    if spec['remote_spec_path']!=expected_spec:raise Unavailable('remote spec must match exact new output path')
    (out/'bridge-spec.json').write_bytes(Path(spec_path).read_bytes())
    files[(out/'bridge-spec.json').relative_to(ROOT).as_posix()]=digest
    archive=out/'payload.tar.gz'
    with tarfile.open(archive,'x:gz') as tar:
        for relative in sorted(files):tar.add(ROOT/relative,arcname=relative,recursive=False)
    save_new(out/'package.json',{'files':files,'sha256':sha(archive),'spec_sha256':digest})
    # The bootstrap executes only in the existing Mac watcher job.
    local=out.relative_to(ROOT).as_posix();remote_spec=spec['remote_spec_path']
    # Validate interpolated path/name characters to keep the shell template literal.
    allowed=set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.:')
    if any(set(x)-allowed for x in (local,remote_root,remote_spec)):raise Unavailable('unsupported path characters in watcher transport')
    script=f'''set -euo pipefail
perl -e 'alarm shift; exec @ARGV' 4400 bash -s <<'SOL_JOB'
set -euo pipefail
cd /Users/ben-hannan/Desktop/projects/beautiful-model
scp {local}/payload.tar.gz benspc:{remote_root}/assistant-day-bridge-payload.tar.gz
scp {local}/package.json benspc:{remote_root}/assistant-day-bridge-package.json
ssh -T -o BatchMode=yes -o ConnectTimeout=15 benspc 'C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -' <<'PYREMOTE'
import hashlib,json,tarfile
from pathlib import Path
r=Path('{remote_root}');m=json.loads((r/'assistant-day-bridge-package.json').read_text(encoding='utf-8'))
assert hashlib.sha256((r/'assistant-day-bridge-payload.tar.gz').read_bytes()).hexdigest()==m['sha256']=='{sha(archive)}'
with tarfile.open(r/'assistant-day-bridge-payload.tar.gz') as t:
 for x in t.getmembers():
  assert x.isfile() and x.name in m['files'] and '..' not in Path(x.name).parts and not x.name.startswith('/')
  p=r/x.name
  if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][x.name]
 t.extractall(r)
for name,h in m['files'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h
PYREMOTE
JOB=sol-assistant-day-bridge TREE=/Users/ben-hannan/Desktop/projects/beautiful-model python3 -B scripts/sol_assistant_watcher_bridge_v3.py --spec {local}/bridge-spec.json --sha256 {digest} 2>&1 | tee {local}/watcher-raw.log
SOL_JOB'''
    check=subprocess.run(['bash','-n'],input=script,text=True,capture_output=True)
    if check.returncode:raise Unavailable(check.stderr)
    text='BASH-ONLY: yes\nLOAD-LIGHT: yes\nGPU: yes\nDISK: 1\nLOWDISK-OK: yes\nTIME CAP: 74 minutes\nLABEL: sol-assistant-day-bridge\n\nBounded idle capture→actual day batch→pinned night/candidate/activation; no cron.\nNo silent static replay fallback. Fixed4 unqualified learned stop.\n\n```bash\n'+script+'\n```\n'
    (out/'queue-sol-assistant-day-bridge.md').write_text(text,encoding='utf-8')
    return {'queue':str(out/'queue-sol-assistant-day-bridge.md'),'archive_sha256':sha(archive),'spec_sha256':digest,'launched':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--sources',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(build(a.spec,a.sources,a.out)))
