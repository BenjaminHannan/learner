import datetime,json,os,re,signal,subprocess,sys,time
from pathlib import Path
root=Path('/private/tmp/idea1-sleep-retention-r2')
plan=json.loads((root/'preregistration.json').read_text()); deadline=datetime.datetime.fromisoformat(plan['absolute_stop_utc']).timestamp()
def measure():
    vm=subprocess.check_output(['vm_stat'],text=True);page=int(re.search(r'page size of (\d+) bytes',vm).group(1)); counts={k:int(v) for k,v in re.findall(r'Pages (free|inactive|purgeable):\s+(\d+)',vm)}
    assert len(counts)==3
    pressure=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'available_bytes':sum(counts.values())*page,'pages':counts,'page_size':page,'pressure_level':pressure}
first=measure(); readings=[first];print('initial memory',first,flush=True)
assert first['available_bytes']>=7*1024**3 and first['pressure_level']<4 and time.time()<deadline-900
cmd=[str(Path.home()/'learner-ops/speedbench/venv312/bin/python'),str(Path(__file__).resolve().parent/'run_hf.py'),'--root',str(root),'--model-dir',str(Path.home()/'learner-ops/lfm3/hf'),'--allow-model-load']
with (root/'HF-stdout.log').open('w') as out,(root/'HF-stderr.log').open('w') as err:
    child=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True); reason=None; started=time.monotonic()
    try:
        while child.poll() is None:
            m=measure();readings.append(m)
            if m['available_bytes']<5.5*1024**3:reason='available memory below 5.5 GiB'
            elif m['pressure_level']>=4:reason='critical pressure'
            elif time.monotonic()-started>=1050:reason='HF outer watchdog 1050 seconds'
            elif time.time()>=deadline:reason='absolute deadline'
            rss=int(subprocess.check_output(['ps','-o','rss=','-p',str(child.pid)],text=True).strip() or 0)*1024
            m['process_rss_bytes']=rss
            if rss>=8*1024**3:reason='process RSS 8 GiB cap'
            if reason:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                break
            time.sleep(2)
    finally:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        (root/'watch.json').write_text(json.dumps({'pid':child.pid,'exit_code':child.returncode,'stop_reason':reason,'readings':readings,'child_reaped':True},indent=2))
        print('finished',child.returncode,reason,flush=True)
