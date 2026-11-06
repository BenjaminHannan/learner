"""One explicitly authorized, bounded desktop capture; regular recording stays OFF."""
import datetime, json, subprocess, time
from pathlib import Path
base = Path.home() / 'learner-ops/hands-recorder'
ctl = base / 'recorderctl'
def call(*args):
    return json.loads(subprocess.check_output([str(ctl), *args], text=True))
def table():
    rows = {}
    text = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,rss=,%cpu=,time=,command='], text=True)
    for line in text.splitlines():
        p = line.strip().split(None, 5)
        if len(p) != 6: continue
        parts = p[4].replace('-', ':').split(':')
        seconds = sum(float(v) * 60**n for n, v in enumerate(reversed(parts)))
        rows[int(p[0])] = dict(pid=int(p[0]), ppid=int(p[1]), rssKiB=int(p[2]), psCpu=float(p[3]), cpuSeconds=seconds, command=p[5])
    return rows
def tree(rows, roots):
    ids = set(roots)
    while True:
        more = {p for p, row in rows.items() if row['ppid'] in ids}
        if more <= ids: return ids & rows.keys()
        ids |= more
assert call('status')['enabled'] is False
assert not (base/'LEAD-RELEASE.json').exists()
preflight = call('preflight')
assert preflight['screen'] and preflight['input'] and preflight['accessibility']
result_path = base/'DESKTOP-BENCHMARK.json'
if result_path.exists(): result_path.unlink()
started = call('scratch-benchmark', '--ben-confirmed-away')
host = started['hostPid']
samples = []; began = time.monotonic(); all_owned = set()
try:
    for i in range(123):
        time.sleep(max(0, began + i + 1 - time.monotonic()))
        rows = table(); own = tree(rows, [host]); all_owned |= own
        samples.append({'atSeconds':time.monotonic()-began, 'processes':[rows[p] for p in sorted(own)]})
        if (base/'DESKTOP-BENCHMARK.json').exists(): break
finally:
    stopped = call('stop')
result = json.loads((base/'DESKTOP-BENCHMARK.json').read_text())
cpu = 0
previous = {}
for sample in samples:
    current = {r['pid']:r['cpuSeconds'] for r in sample['processes']}
    cpu += sum(max(0, value-previous.get(pid,0)) for pid,value in current.items())
    previous = current
seconds = samples[-1]['atSeconds']
result.update({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'preflight':preflight,'peakRssMiB':max(sum(r['rssKiB'] for r in s['processes']) for s in samples)/1024,
 'cpuPercentOneCore':100*cpu/seconds,'cpuWindowSeconds':seconds,
 'scope':'All recorder-role Premonition descendants (host, native worker and ffmpeg); existing chat/brain excluded; process CPU time deltas sampled every second',
 'regularRecordingEnabled':call('status')['enabled'],'releaseFileAbsent':not (base/'LEAD-RELEASE.json').exists(),'samples':samples})
for i in range(40):
    live = table()
    if not all_owned & live.keys(): break
    time.sleep(.1)
result['allRecorderProcessesStopped'] = not bool(all_owned & live.keys())
assert result['scratchDeleted'] and not Path(result['root']).exists()
assert not result['regularRecordingEnabled'] and result['releaseFileAbsent']
assert not result.get('error'), result
assert result['elapsedSeconds'] >= 119 and result['frames'] > 0, result
out = Path.home()/'learner-ops/aon-notes/hands-20261106/T9-live-desktop-resources.json'
out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
