"""Offline test of vastptc.py + the kit's vast.py: urllib.request.urlopen is replaced, so NO network call can happen.
usage: python3 fake_vast_test.py KIT_VAST_PY VASTPTC_PY LOGFILE OUTDIR
 A  create: the PUT body the kit would send (args = bash -c "<exports>\\n<script>" cio), the script inside it, size, no key in it
 B  search: the filter and the printed rows
 C  collect on the finished dry-run log
 D  collectck on a log that grows while polling (virtual time): started at RESULT PRINTED, and started late (round 2)
"""
import base64
import hashlib
import io
import json
import os
import runpy
import sys
import tarfile
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

kit, wrapper, logf, outdir = sys.argv[1:5]
outdir = Path(outdir)
outdir.mkdir(parents=True, exist_ok=True)
LOG = Path(logf).read_text(errors='replace').splitlines()
state = {'calls': [], 'cursor': len(LOG), 'tail': 20000, 'lines': LOG}


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(req, timeout=None):
    url = req if isinstance(req, str) else req.full_url
    method = getattr(req, 'method', 'GET')
    body = None if isinstance(req, str) or req.data is None else json.loads(req.data.decode())
    state['calls'].append((method, url, body))
    if 'request_logs' in url:
        state['tail'] = int(body['tail'])
        return Resp(json.dumps({'result_url': 'http://fake.invalid/log.txt'}).encode())
    if url == 'http://fake.invalid/log.txt':
        vis = state['lines'][:state['cursor']]
        return Resp('\n'.join(vis[-state['tail']:]).encode())
    if url.endswith('/bundles/'):
        offers = [{'id': 111, 'gpu_name': 'RTX 4090', 'gpu_ram': 24564, 'dph_total': 0.38, 'reliability': 0.99, 'inet_down': 900.0, 'cpu_cores_effective': 16.0,
                   'cpu_ram': 64000, 'disk_space': 200, 'cuda_max_good': 12.9, 'geolocation': 'XX'},
                  {'id': 112, 'gpu_name': 'RTX 5090', 'gpu_ram': 32000, 'dph_total': 0.47}]
        return Resp(json.dumps({'offers': offers}).encode())
    if '/asks/' in url:
        return Resp(json.dumps({'success': True, 'new_contract': 4242}).encode())
    if url.endswith('/instances/') or '/instances/4242' in url:
        inst = {'id': 4242, 'label': 'ptc3s', 'actual_status': 'running', 'dph_total': 0.38}
        return Resp(json.dumps({'instances': [inst] if method == 'GET' else []}).encode())
    return Resp(b'{}')


def run(argv):
    sys.argv = [wrapper, kit] + argv
    buf = io.StringIO()
    with mock.patch.object(urllib.request, 'urlopen', fake_urlopen), mock.patch('time.sleep', lambda s: None), redirect_stdout(buf):
        try:
            runpy.run_path(wrapper, run_name='__main__')
        except SystemExit as e:
            if e.code not in (None, 0):
                raise
    return buf.getvalue()


# ---- A create
out = run(['create', '--offer', '111', '--label', 'ptc3s', '--env', 'MAXH=6 DPH=0.38 PROJ_CAP_USD=4 END_SLEEP=600 FAIL_SLEEP=900'])
print('A create printed:', out.strip())
m, url, body = [c for c in state['calls'] if c[0] == 'PUT'][-1]
print('A PUT', url, '| keys', sorted(body), '| image', body['image'], '| disk', body['disk'], '| runtype', body['runtype'])
args = body['args']
box = (Path(wrapper).parent / 'ptc3s_box.sh').read_text()
print('A args[0:2]', args[:2], '| args[3]', args[3], '| len(args[2])', len(args[2]), 'bytes', len(args[2].encode()))
head, _, rest = args[2].partition('\n')
print('A exports line:', head)
print('A script after the exports line is ptc3s_box.sh byte for byte:', rest == box)
(outdir / 'create_script.sh').write_text(args[2])
joined = json.dumps(body)
print('A body mentions a key/token/bearer word:', any(w in joined.lower() for w in ('bearer', 'api_key', 'apikey', 'authorization')))

# ---- B search
state['calls'].clear()
out = run(['search', '--gpu', 'RTX 4090', '--n', '8'])
print('B search printed:', out.strip())
print('B filter:', json.dumps(state['calls'][0][2]))

# ---- C collect on the finished log
state['calls'].clear()
state['cursor'] = len(LOG)
cdir = outdir / 'collect'
out = run(['collect', '--id', '4242', '--out', str(cdir)])
print('C collect printed:', out.strip())
print('C extracted:', sorted(str(p.relative_to(cdir)) for p in cdir.rglob('*') if p.is_file())[:12], '...')

# ---- D collectck, live-log emulation: each poll sees 3,334 more lines (= one 3 MB part per 100 s at a poll every 40 s)
first = next(i for i, ln in enumerate(LOG) if 'PTC3S RESULT PRINTED' in ln)
rd2 = [i for i, ln in enumerate(LOG) if ln.startswith('CKFULL|')]
print('D log lines', len(LOG), '| RESULT PRINTED at line', first, '| CKFULL lines at', rd2)


PARTS_END = [i + 1 for i, ln in enumerate(LOG) if ln.startswith('part ck')]       # log position after each printed part (the box prints a part in one burst, then sleeps PACE = 100 s)


def pos_at(t, first):
    """cursor of the live log t virtual seconds after 'PTC3S RESULT PRINTED': part i (1-based) is printed at 100*(i-1)+1 s; the closing lines come after the last sleep"""
    n = sum(1 for i in range(len(PARTS_END)) if t >= 100 * i + 1)
    if n == 0:
        return first + 5
    if n == len(PARTS_END) and t >= 100 * len(PARTS_END) + 1:
        return len(LOG)
    return PARTS_END[n - 1]


def live(start_t, label, first):
    d = outdir / label
    orig = state['lines']
    clock = [1000.0]                         # virtual clock: the kit's max-min loop must end without really waiting
    origin = clock[0] - start_t
    state['cursor'] = pos_at(start_t, first)

    def adv(s):
        clock[0] += s
        state['cursor'] = pos_at(clock[0] - origin, first)
    with mock.patch.object(urllib.request, 'urlopen', fake_urlopen), mock.patch('time.sleep', adv), mock.patch('time.time', lambda: clock[0]), redirect_stdout(io.StringIO()) as buf:
        sys.argv = [wrapper, kit, 'collectck', '--id', '4242', '--out', str(d), '--max-min', '60', '--want', '8aPTC3S-3M-s400/PTC 8aPTC3S-3M-s400']
        os.environ['PTC_OUT'] = str(d)
        try:
            runpy.run_path(wrapper, run_name='__main__')
        except SystemExit:
            pass
    lines = buf.getvalue().strip().splitlines()
    print('D %s: %d polls, %.1f virtual minutes; first: %s' % (label, len(lines), (clock[0] - 1000.0) / 60, lines[0] if lines else None))
    print('D %s: last: %s' % (label, lines[-1] if lines else None))
    ck = d / '8aPTC3S-3M-s400' / 'PTC' / 'checkpoint.pt'
    print('D %s: checkpoint.pt %s' % (label, ('%d bytes sha256 %s' % (ck.stat().st_size, hashlib.sha256(ck.read_bytes()).hexdigest()[:16])) if ck.exists() else 'MISSING'))
    print('D %s: RESULT.json %s' % (label, (d / '8aPTC3S-3M-s400' / 'RESULT.json').exists()))


live(0, 'ck_started_at_result_printed', first)
live(100 * 5 + 6, 'ck_started_at_round2', first)
live(100 * 7 + 6, 'ck_started_mid_round2', first)
