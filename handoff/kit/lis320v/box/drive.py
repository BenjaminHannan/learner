#!/usr/bin/env python3
"""One sealed lis-320 training/read chain. Counts/logs only; never retry a panel read."""
import ast, gzip, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
ROOT=Path('/root/lis320');os.chdir(ROOT)
A=Path('artifacts/claude-lis320-20260926');P=Path('artifacts/claude-readpanel320-20260926')
W=Path('W');R=W/'results';R.mkdir(parents=True,exist_ok=True)
BASE_REV='87179e5c1f455ef22e6223592d2d61351b525bfc'
OLD_SHA='970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b'
PY=sys.executable

def utc():return subprocess.check_output(['date','-u','+%FT%TZ'],text=True).strip()
def state(phase,**kw):
    d=dict(utc=utc(),phase=phase,**kw)
    p=W/'state.tmp';p.write_text(json.dumps(d)+'\n');p.replace(W/'state.json')
    with (W/'steps.jsonl').open('a') as f:f.write(json.dumps(d)+'\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def call(name,args,train=False):
    state(name)
    log=W/(name+'.log')
    with log.open('xb') as f:
        p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
    (W/'child.pid').write_text(str(p.pid)+'\n')
    t=time.monotonic();grad=False
    while p.poll() is None:
        if train:
            # Only this process's PID can be terminated, and no training text is logged.
            for line in log.read_text(errors='replace').splitlines():
                if line.startswith("{'grad_none_after_first_backward':"):
                    n=ast.literal_eval(line)['grad_none_after_first_backward']
                    if n!=0:
                        p.terminate();p.wait(timeout=30);raise RuntimeError(f'GRAD-NONE {n}')
                    grad=True
            if not grad and time.monotonic()-t>120:
                p.terminate();p.wait(timeout=30);raise RuntimeError('GRAD-PROBE absent after 120 seconds')
        time.sleep(2)
    (W/'child.pid').unlink(missing_ok=True)
    if p.returncode:raise RuntimeError(f'{name} exited {p.returncode}; see private log')
    state(name+'-DONE',seconds=round(time.monotonic()-t,2))
    return log

def script(name,*args,**kw):return call(name,[PY,'-B','scripts/'+name+'.py',*map(str,args)],**kw)
def seal_files(paths,out):
    with Path(out).open('x') as f:
        for p in paths:f.write(sha(p)+'  '+str(p)+'\n')

def main():
    with (W/'CHAIN-STARTED').open('x') as f:f.write(utc()+'\n')
    (W/'drive.pid').write_text(str(os.getpid())+'\n')
    state('START')
    call('pip-torch',[PY,'-m','pip','install','--no-cache-dir','torch==2.11.0','--index-url','https://download.pytorch.org/whl/cu128'])
    call('pip-remove',[PY,'-m','pip','uninstall','-y','torchvision','torchaudio'])
    call('pip-reader',[PY,'-m','pip','install','--no-cache-dir','transformers==5.17.0','peft==0.21.0','safetensors','huggingface_hub','accelerate','numpy'])
    import torch,transformers,peft
    if not torch.__version__.startswith('2.11.0') or not torch.cuda.is_available():raise RuntimeError('TORCH-CUDA check failed')
    env=dict(torch=torch.__version__,cuda=torch.version.cuda,transformers=transformers.__version__,peft=peft.__version__,gpu=torch.cuda.get_device_name(0))
    (R/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    for s in [A/'PASSMARKS.sha256.txt',*sorted(A.glob('SEAL-ADDENDA*.sha256.txt')),A/'SEAL-DATA.sha256.txt',A/'SEAL-EXECUTION.sha256.txt']:
        call('seal-'+s.stem,['sha256sum','-c',str(s)])
    call('seal-panel',['bash','-c',f'cd {P} && sha256sum -c SEAL.sha256.txt'])
    for script_name,cmd in [('claude_lis320_score','selftest'),('claude_lis319k_score','selftest'),('claude_lis320_rawcheck2','--selftest'),('claude_lis320_resume_clean','--selftest')]:
        call('selftest-'+script_name,[PY,'-B','scripts/'+script_name+'.py',cmd])
    from huggingface_hub import snapshot_download
    state('BASE-DOWNLOAD')
    base=snapshot_download('openbmb/MiniCPM5-1B',revision=BASE_REV)
    if Path(base).name!=BASE_REV:raise RuntimeError('BASE-MISMATCH')
    os.environ.update(HF_HUB_OFFLINE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONUTF8='1')
    old=Path('old/lis319f-merged')
    if sha(old/'model.safetensors')!=OLD_SHA:raise RuntimeError('OLD-READER-MISMATCH')
    (R/'base-and-old.json').write_text(json.dumps(dict(base_revision=BASE_REV,old_merged_sha256=OLD_SHA,base_weights={p.name:sha(p) for p in Path(base).glob('*.safetensors')}),indent=2)+'\n')
    D=W/'data-work';D.mkdir()
    script('claude_lis320_seed_cr','--seed',324,'--n',6000,'--ask-back','--avoid-names',A/'avoid_names_dev.txt','--avoid-hashes',A/'avoid_test.sha256','--out',D/'seeds.jsonl')
    counts=json.loads((A/'full-luna/final/COUNTS.json').read_text())
    with (D/'joined.jsonl').open('wb') as f:
        for c in counts['chunks']:
            p=A/f'full-luna/chunk{c["chunk"]}/raw.new.jsonl.gz'
            if sha(p)!=c['sha256']:raise RuntimeError('RAW-CHUNK-MISMATCH')
            f.write(gzip.decompress(p.read_bytes()))
    script('claude_lis320_resume_clean','--raw',D/'joined.jsonl','--out',D/'raw.jsonl')
    raw=rows(D/'raw.jsonl');seeds=rows(D/'seeds.jsonl')
    if len(raw)!=6000 or any(r.get('parsed') is None for r in raw) or {r['dialog_id'] for r in raw}!={r['dialog_id'] for r in seeds}:raise RuntimeError('DATA-INCOMPLETE')
    script('claude_lis320_rawcheck2','--raw',D/'raw.jsonl','--seeds',D/'seeds.jsonl','--models','gpt-6-luna')
    script('claude_lis320_check_we3','--raw',D/'raw.jsonl','--seeds',D/'seeds.jsonl','--out',D/'kept.jsonl','--drops',D/'drops.jsonl')
    script('claude_lis320_build','--kept',D/'kept.jsonl','--out',D/'data','--dev-pct',3)
    expected=json.loads((A/'full-luna/final/DATA-HASHES.json').read_text())
    if any(sha(D/p)!=h for p,h in expected.items()):raise RuntimeError('DATA-HASH-MISMATCH')
    (R/'DATA-VERIFIED.json').write_text(json.dumps(expected,indent=2)+'\n')
    lengths=script('claude_lis319_lencheck','--model',base,'--data',D/'data','--max-len',512)
    (R/'LENGTHS.json').write_bytes(lengths.read_bytes())
    script('claude_lis300_train','--model',base,'--data',D/'data','--out',W/'model','--epochs',2,'--lr','2e-4','--rank',32,'--batch',16,'--max-len',512,'--seed',300,'--max-minutes',150,'--merge',train=True)
    summary=json.loads((W/'model/summary.json').read_text())
    (R/'train_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if summary['stopped'] is not None or summary['steps']!=summary['planned_steps'] or summary['grad_none_after_first_backward']!=0:raise RuntimeError('TRAIN-INCOMPLETE')
    seal_files([*sorted((W/'model/adapter').iterdir()),*sorted((W/'model/merged').iterdir())],R/'SEAL-run.sha256.txt')
    # Complete panel, with exclusive started markers. No sample, preview, tuning or retry.
    panel=rows(P/'panel.jsonl')
    if len(panel)!=336 or len({r['id'] for r in panel})!=336:raise RuntimeError('PANEL-COUNT-MISMATCH')
    script('claude_lis319_rows','--rows',P/'panel.jsonl','--out',W/'h320.jsonl')
    for arm,model in [('old',old),('new',W/'model/merged')]:
        with (R/f'panel-{arm}.started').open('x') as f:f.write(utc()+'\n')
        call('read-panel-'+arm,[PY,'-B','scripts/claude_lis319_read.py','--model',str(model),'--rows',str(W/'h320.jsonl'),'--out',str(R/f'reads_panel_{arm}.jsonl')])
        read=rows(R/f'reads_panel_{arm}.jsonl')
        if len(read)!=336 or {r['id'] for r in read}!={r['id'] for r in panel}:raise RuntimeError('READ-COUNT-MISMATCH '+arm)
        call('pairs-'+arm,[PY,'-B','scripts/claude_lis319k_score.py','pairs','--panel',str(P/'panel.jsonl'),'--reads',str(R/f'reads_panel_{arm}.jsonl'),'--out',str(R/f'pairs_panel_{arm}.jsonl')])
        call('extra-'+arm,[PY,'-B','scripts/claude_lis320_score.py','extra','--panel',str(P/'panel.jsonl'),'--reads',str(R/f'reads_panel_{arm}.jsonl'),'--out',str(R/f'extra_{arm}.json')])
        (R/f'panel-{arm}.completed').write_text(utc()+'\n')
    call('read-dev',[PY,'-B','scripts/claude_lis319_read.py','--model',str(W/'model/merged'),'--rows',str(D/'data/dev.jsonl'),'--out',str(R/'dev_pred_new.jsonl')])
    log=call('score-dev',[PY,'-B','scripts/claude_lis300_score.py','--gold',str(D/'data/dev.jsonl'),'--pred',str(R/'dev_pred_new.jsonl'),'--threshold','0.995'])
    (R/'dev_score_new.txt').write_bytes(log.read_bytes())
    # Any separately sealed report-only panel is transferred explicitly before launch.
    report=Path('artifacts/codex-lis320-glm-report-test/kept.jsonl')
    if report.exists():
        for arm,model in [('old',old),('new',W/'model/merged')]:
            call('read-report-'+arm,[PY,'-B','scripts/claude_lis319_read.py','--model',str(model),'--rows',str(report),'--out',str(R/f'report_pred_{arm}.jsonl')])
            log=call('score-report-'+arm,[PY,'-B','scripts/claude_lis300_score.py','--gold',str(report),'--pred',str(R/f'report_pred_{arm}.jsonl'),'--threshold','0.995'])
            (R/f'report_score_{arm}.txt').write_bytes(log.read_bytes())
    seal_files(sorted(p for p in R.iterdir() if p.is_file()),W/'RESULTS.sha256.txt')
    state('DONE',panel_rows=336,train_steps=summary['steps'],base_revision=BASE_REV)

if __name__=='__main__':
    try:main()
    except Exception as e:
        # Exception classes and static reasons only; source rows never appear in progress output.
        state('FAILED',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__)
        raise SystemExit(1)
