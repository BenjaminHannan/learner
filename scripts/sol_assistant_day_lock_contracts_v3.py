"""Actual subprocess validation under activation writer lock; no model fixtures."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from sol_assistant_day_v3 import DayStore
from sol_assistant_bundle import ROOT,sha
out=ROOT/'artifacts/sol-assistant-20260930/day-bridge-v3';plan=json.loads((out/'PRE-RUN.json').read_text())
for p,h in plan['source_pins'].items():assert sha(ROOT/p)==h
results=[]
child="import sys,json;from sol_assistant_day_v3 import DayStore; s=DayStore(sys.argv[1],read_only=True); c=s.connect();print(json.dumps({'events':c.execute('SELECT count(*) FROM events').fetchone()[0]}));c.close()"
env=dict(os.environ,PYTHONPATH=str(ROOT/'scripts'),PYTHONDONTWRITEBYTECODE='1')
for seed in plan['seeds']:
    state=out/f'lock-fixture-s{seed}';store=DayStore(state);store.activity();marks=[];values=[]
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for repeat in (0,1):
            r=subprocess.run([sys.executable,'-B','-c',child,str(state)],env=env,capture_output=True,text=True,timeout=3)
            assert r.returncode==0,r.stderr
            values.append(json.loads(r.stdout)['events'])
        marks.append({'name':'read under writer lock','pass':values[0]==0})
        marks.append({'name':'repeat count','noise':abs(values[0]-values[1]),'pass':values==[0,0]})
    missing=out/f'missing-s{seed}'
    r=subprocess.run([sys.executable,'-B','-c',child,str(missing)],env=env,capture_output=True,text=True,timeout=3)
    marks.append({'name':'missing read-only store refuses','pass':r.returncode!=0 and not missing.exists()})
    results.append({'seed':seed,'marks':marks,'passed':sum(m['pass'] for m in marks),'total':3})
report={'plan_sha256':sha(out/'PRE-RUN.json'),'results':results,'actual_day_rows':0,'optimizer_steps':0,'model_calls':0,'network_calls':0,'scope':plan['scope']}
with (out/'RAW.json').open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert all(x['passed']==3 for x in results)
