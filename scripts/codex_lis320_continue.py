#!/usr/bin/env python3
"""Counts-only continuation of ADDENDA 11/12. Shell invokes every 600 seconds.
No model calls, auth reads, test reads, rentals, or edits to existing files.
Exit 0: wait; 10: data ready; 20: stop. Main commits add only the next queue file.
"""
import argparse, gzip, json, re, subprocess, sys
from pathlib import Path
A='artifacts/claude-lis320-20260926'
F=A+'/full-luna'
SHA='9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2'
def run(*args,check=True):
    return subprocess.run(args,capture_output=True,check=check)
def blob(ref,path,optional=False):
    p=run('git','show',ref+':'+path,check=False)
    if p.returncode:
        if optional:return None
        raise ValueError('missing '+path)
    return p.stdout
def event(state,name,**counts):
    r=dict(utc=run('date','-u','+%FT%TZ').stdout.decode().strip(),event=name,**counts)
    with (state/'events.jsonl').open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n')
    print(json.dumps(r,sort_keys=True),flush=True)
    return r
def summary(report,k):
    lines=[s for s in report.splitlines() if s.startswith('CHUNK-SUMMARY ')]
    if len(lines)!=1:raise ValueError(f'chunk {k}: expected exactly one summary')
    d=dict(re.findall(r'(\w+)=([^ ]+)',lines[0]))
    if int(d['K'])!=k or d.get('stop')!='ok':raise ValueError(f'chunk {k}: '+lines[0])
    if any(s.startswith('STOP:') for s in report.splitlines()):raise ValueError(f'chunk {k}: STOP in report')
    if int(d['rawcheck2_rc'])!=0 or int(d['of'])!=6000:raise ValueError(f'chunk {k}: rawcheck/target mismatch')
    calls,parsed=int(d['calls']),int(d['parsed'])
    if calls<=0 or parsed/calls<.85:raise ValueError(f'chunk {k}: parsed {parsed}/{calls}; below 85% or zero calls')
    return d
def queue_text(s,k,lw):
    s=s.replace('chunk 10 (seed',f'chunk {k} (seed').replace('K=10; LW=6; N=6000',f'K={k}; LW={lw}; N=6000')
    s=s.replace('claude-lis320-luna-c10b-mac (re-run: c10 stopped at its git fetch)',f'claude-lis320-luna-c{k}-mac')
    s=s.replace('full-luna/chunk10',f'full-luna/chunk{k}')
    if 'c10b' in s or f'K={k}; LW={lw}; N=6000' not in s:raise ValueError('queue template mismatch')
    code=s.split('```bash\n',1)[1].split('\n```',1)[0]
    subprocess.run(['bash','-n'],input=code.encode(),check=True,capture_output=True)
    return s
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',required=True);a=ap.parse_args()
    state=Path(a.state);state.mkdir(parents=True,exist_ok=True)
    if (state/'STOP.json').exists():return 20
    if (state/'DATA-READY.json').exists():return 10
    if run('git','fetch','-q','origin','main','builder-outbox',check=False).returncode:return 0
    ref=run('git','rev-parse','origin/builder-outbox').stdout.decode().strip();completed=[]
    try:
        for k in range(1,101):
            report=blob(ref,f'{F}/chunk{k}/RESULTS.md',True)
            if report is None:break
            d=summary(report.decode(),k)
            seed=blob(ref,f'{F}/chunk{k}/SEEDS.sha256.txt').decode().strip()
            if seed!=SHA:raise ValueError(f'chunk {k}: changed seeds hash {seed}')
            rc=json.loads(blob(ref,f'{F}/chunk{k}/rawcheck.json'))
            if rc['rawcheck2']!='OK' or rc['models']!='gpt-6-luna':raise ValueError(f'chunk {k}: rawcheck2 failed')
            completed.append(d)
        if not completed:raise ValueError('chunk 1 missing')
        k=len(completed);last=completed[-1];seenpath=state/'last-verified.json'
        seen=json.loads(seenpath.read_text()) if seenpath.exists() else {}
        if seen.get('chunk')!=k:
            sys.path.insert(0,str(Path(__file__).resolve().parent))
            from claude_lis320_resume_clean import clean
            from claude_lis320_rawcheck2 import check
            joined=[]
            for j in range(1,k+1):
                data=gzip.decompress(blob(ref,f'{F}/chunk{j}/raw.new.jsonl.gz'))
                rows=[json.loads(x) for x in data.splitlines() if x.strip()]
                if len(rows)!=int(completed[j-1]['new']):raise ValueError(f'chunk {j}: new-row count mismatch')
                joined.extend(rows)
            raw,cc=clean(joined)
            ids={f's320cr-324-{i:05d}' for i in range(6000)}
            ok,rc=check(raw,{'gpt-6-luna'},ids)
            parsed=sum(r.get('parsed') is not None for r in raw)
            if not ok or parsed!=int(last['worded_ok']):raise ValueError('rawcheck/count mismatch '+json.dumps(rc))
            seals=[Path(A)/'PASSMARKS.sha256.txt']+sorted(Path(A).glob('SEAL-ADDENDA*.sha256.txt'))
            for seal in seals:
                if run('shasum','-a','256','-c',str(seal),check=False).returncode:raise ValueError('seal failed: '+str(seal))
            for s in ('luna3','seed_cr','check_we3','rawcheck2','resume_clean'):
                if run(sys.executable,'-B',f'scripts/claude_lis320_{s}.py','--selftest',check=False).returncode:raise ValueError('selftest failed: '+s)
            seen=event(state,'CHUNK-LANDED',chunk=k,parsed=parsed,of=6000,outbox=ref,rawcheck2='OK',clean=cc)
            seenpath.write_text(json.dumps(seen)+'\n')
            if parsed==6000 and {r['dialog_id'] for r in raw}==ids:
                (state/'DATA-READY.json').write_text(json.dumps(seen)+'\n');event(state,'DATA-READY',parsed=6000,of=6000,outbox=ref);return 10
            if len(raw)==6000 and parsed<6000:raise ValueError(f'resume cannot retry nonempty unparsed rows: {parsed}/6000 parsed; addendum needed')
        lw=min(int(last.get('lw',6)),6)
        if int(last.get('ratelimit',0))>0 or int(last.get('tries_failed',0))>.05*int(last['calls']):lw=3
        nk=k+1;target=f'handoff/queue/claude-lis320-luna-c{nk}-mac.md'
        if blob('origin/main',target,True) is not None:return 0
        if run('git','status','--porcelain','--untracked-files=no').stdout.strip():raise ValueError('tracked checkout edits: automatic commit refused')
        template=blob('origin/main','handoff/queue/claude-lis320-luna-c10b-mac.md').decode()
        text=queue_text(template,nk,lw);p=Path(target)
        if p.exists():
            if p.read_text()!=text:raise ValueError('unpublished queue file differs: '+target)
        else:
            with p.open('x') as f:f.write(text)
        run('git','add','--',target)
        if run('git','diff','--cached','--name-status').stdout.decode().strip()!='A\t'+target:raise ValueError('unexpected staged paths; commit refused')
        run('git','commit','-m',f'lis-320: queue Luna chunk {nk} after verified chunk {k}')
        for attempt in range(3):
            run('git','pull','--rebase','origin','main')
            if run('git','push','origin','HEAD:main',check=False).returncode==0:
                event(state,'CHUNK-QUEUED',chunk=nk,workers=lw,commit=run('git','rev-parse','HEAD').stdout.decode().strip());return 0
        raise ValueError('push failed after three rebased attempts')
    except Exception as e:
        reason='command failed: '+' '.join(e.cmd) if isinstance(e,subprocess.CalledProcessError) else str(e)
        r=event(state,'STOP',reason=reason,completed_chunks=len(completed))
        (state/'STOP.json').write_text(json.dumps(r)+'\n');return 20
if __name__=='__main__':raise SystemExit(main())
