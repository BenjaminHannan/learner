"""Fake pictures only. Includes the recorder role, chat app tree and existing brain."""
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
before = table()
chat = [p for p,r in before.items() if r['command'] == '/Applications/Premonition.app/Contents/MacOS/Premonition']
brain = [p for p,r in before.items() if '/bin/Glim ' in r['command'] and 'glim_main.py' in r['command']]
assert len(chat) == 1 and len(brain) == 1, (chat, brain)
preflight = call('preflight')
assert preflight['responsibleBundleId'] == 'com.electron.premonition-desk'
assert preflight['screen'] and preflight['input'] and preflight['accessibility']
assert call('status')['enabled'] is False
started = call('start', '--fake')
host = started['hostPid']
samples = []; began = time.monotonic(); all_owned = set()
try:
    for i in range(35):
        time.sleep(max(0, began + i + 1 - time.monotonic()))
        rows = table(); own = tree(rows, [host]); all_owned |= own
        groups = {'recorder': own, 'chat': tree(rows, chat), 'brain': tree(rows, brain)}
        samples.append({'atSeconds':time.monotonic()-began, 'groups':{k:[rows[p] for p in sorted(ids)] for k,ids in groups.items()}})
finally:
    stopped = call('stop')
elapsed = time.monotonic()-began
for i in range(40):
    live = table()
    if not all_owned & live.keys(): break
    time.sleep(.1)
assert not all_owned & live.keys(), 'recorder processes survived stop'
assert set(chat + brain) <= live.keys(), 'chat or brain stopped'
assert call('status')['enabled'] is False
assert json.loads((base/'state.json').read_text())['enabled'] is False
saved = json.loads((base/'status.json').read_text())
assert saved['enabled'] is False and saved['stopped'] is True
assert not saved.get('reason'), saved
stats = {}
for name in ['recorder','chat','brain']:
    warm = [s for s in samples if s['atSeconds'] > 5]
    cpu = 0
    previous = {r['pid']:r['cpuSeconds'] for r in warm[0]['groups'][name]}
    for s in warm[1:]:
        current = {r['pid']:r['cpuSeconds'] for r in s['groups'][name]}
        cpu += sum(max(0, value-previous.get(pid,0)) for pid,value in current.items())
        previous = current
    seconds = warm[-1]['atSeconds']-warm[0]['atSeconds']
    stats[name] = {'peakRssMiB':max(sum(r['rssKiB'] for r in s['groups'][name]) for s in samples)/1024,
                   'cpuPercentOneCore':100*cpu/seconds, 'cpuWindowSeconds':seconds}
stats['combined'] = {'peakRssMiB':max(sum(r['rssKiB'] for group in s['groups'].values() for r in group) for s in samples)/1024,
                     'cpuPercentOneCore':sum(v['cpuPercentOneCore'] for v in stats.values())}
new_bytes = saved['totalBytes'] - started['totalBytes']
result = {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope':'fake 1280x720 20fps + 192px crop; H264 VideoToolbox; all recorder descendants; existing chat/brain shown separately',
          'seconds':elapsed, 'bytes':new_bytes, 'bytesPerMinute':new_bytes*60/elapsed,
          'preflight':preflight, 'stats':stats, 'stopPassed':True, 'settingsEnabled':False,
          'chatPidsUnchanged':chat,'brainPidsUnchanged':brain,'samples':samples}
out = Path.home()/'learner-ops/aon-notes/hands-20261106/T9-premonition-resources.json'
out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
