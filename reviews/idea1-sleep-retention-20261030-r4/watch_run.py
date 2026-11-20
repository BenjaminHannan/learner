import datetime, json, os, re, signal, subprocess, sys, time, shutil
from pathlib import Path
root=Path(sys.argv[1]).resolve()
def measure():
    vm=subprocess.check_output(['vm_stat'],text=True); page=int(re.search(r'page size of (\d+) bytes',vm).group(1)); counts={k:int(v) for k,v in re.findall(r'Pages (free|inactive|purgeable):\s+(\d+)',vm)}
    assert len(counts)==3
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'available_bytes':sum(counts.values())*page,'pressure_level':int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True)), 'disk_free_bytes':shutil.disk_usage('/System/Volumes/Data').free}
first=measure(); print('preload',first,flush=True)
if first['disk_free_bytes']<4*1024**3: raise SystemExit('preload disk requirement not met; no model loaded')
if first['available_bytes']<7*1024**3 or first['pressure_level']>=4: raise SystemExit('preload memory requirement not met; no model loaded')
cmd=[str(Path.home()/'learner-ops/speedbench/venv312/bin/python'),str(Path(__file__).resolve().parent/'run_hf.py'),'--root',str(root),'--model-dir',str(Path.home()/'learner-ops/lfm3/hf'),'--allow-model-load']
readings=[first];started=time.monotonic();reason=None
with (root/'stdout.log').open('w') as out,(root/'stderr.log').open('w') as err:
    child=subprocess.Popen(cmd,stdout=out,stderr=err)
    try:
        while child.poll() is None:
            m=measure(); readings.append(m); elapsed=time.monotonic()-started
            try: m['process_rss_bytes']=int(subprocess.check_output(['ps','-o','rss=','-p',str(child.pid)],text=True).strip() or 0)*1024
            except subprocess.CalledProcessError: pass
            if m['disk_free_bytes']<2*1024**3: reason='disk free below 2 GiB'
            elif m['available_bytes']<4*1024**3: reason='available memory below 4 GiB'
            elif m['pressure_level']>=4: reason='critical memory pressure'
            elif m.get('process_rss_bytes',0)>=8*1024**3: reason='process RSS 8 GiB cap'
            elif elapsed>=1800: reason='absolute 30-minute total cap'
            report_path=root/'HF-report.json'
            if report_path.exists():
                report=json.loads(report_path.read_text()); phases=report.get('phases',[])
                if phases:
                    phase=phases[-1]
                    if 'watchdog_s' in phase and 'training_wall_s' not in phase and report.get('elapsed_s',0)>=phase['phase_started_elapsed_s']+phase['watchdog_s']: reason='per-phase measured first-step watchdog'
                    # report elapsed is updated after each step; use wall clock to catch a stalled step.
                    if 'watchdog_s' in phase and 'training_wall_s' not in phase and elapsed>=phase['phase_started_elapsed_s']+phase['watchdog_s']+5: reason='per-phase measured first-step watchdog'
            if reason:
                os.kill(child.pid,signal.SIGTERM)
                try: child.wait(timeout=8)
                except subprocess.TimeoutExpired: os.kill(child.pid,signal.SIGKILL); child.wait()
                break
            time.sleep(2)
    finally:
        if child.poll() is None:
            os.kill(child.pid,signal.SIGTERM)
            try: child.wait(timeout=8)
            except subprocess.TimeoutExpired: os.kill(child.pid,signal.SIGKILL); child.wait()
        (root/'watch.json').write_text(json.dumps({'pid':child.pid,'exit_code':child.returncode,'stop_reason':reason,'wall_s':time.monotonic()-started,'readings':readings,'child_reaped':True},indent=2))
        print('finished',child.returncode,reason,flush=True)
