"""Offline test of vastptc.py + the kit's vast.py on a PROFILE=1 dry-run log: urllib.request.urlopen is replaced, so NO network call can happen.
usage: python3 fake_vast_prof_test.py KIT_VAST_PY VASTPTC_PY LOGFILE OUTDIR [SCRIPT]
 A  create with the PROFILE env words: the PUT body, the script inside it (byte for byte), the exports line, sizes
 B  tail: the kit's tail hides R| lines; the markers a person looks for are in the last lines
 C  collect on the finished log: both blocks (profjob, profrun) decode, the sha256 checks pass, the files that come out
"""
import io
import json
import runpy
import sys
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

kit, wrapper, logf, outdir = sys.argv[1:5]
box_path = Path(sys.argv[5]) if len(sys.argv) > 5 else Path(wrapper).parent / 'ptc3s_box.sh'
outdir = Path(outdir)
outdir.mkdir(parents=True, exist_ok=True)
LOG = Path(logf).read_text(errors='replace').splitlines()
state = {'calls': [], 'tail': 20000}


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
        return Resp('\n'.join(LOG[-state['tail']:]).encode())
    if '/asks/' in url:
        return Resp(json.dumps({'success': True, 'new_contract': 4242}).encode())
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


out = run(['create', '--offer', '111', '--label', 'ptcprof', '--env', 'PROFILE=1 MAXH=2 DPH=0.40 END_SLEEP=300 FAIL_SLEEP=300'])
print('A create printed:', out.strip())
m, url, body = [c for c in state['calls'] if c[0] == 'PUT'][-1]
args = body['args']
head, _, rest = args[2].partition('\n')
print('A exports line:', head)
print('A script after the exports line is the box script byte for byte:', rest == box_path.read_text(), '| script bytes', len(rest.encode()), '| whole args[2] bytes', len(args[2].encode()), '| body json bytes', len(json.dumps(body)))
print('A args[0:2]', args[:2], '| args[3]', args[3])

state['calls'].clear()
out = run(['tail', '--id', '4242', '--n', '14'])
print('B tail printed %d lines, any R| line: %s; last lines:' % (len(out.splitlines()), any(ln.startswith('R|') for ln in out.splitlines())))
for ln in out.splitlines()[-14:]:
    print('B   ', ln[:200])

cdir = outdir / 'collect'
out = run(['collect', '--id', '4242', '--out', str(cdir)])
print('C collect printed:', out.strip())
files = sorted(p.relative_to(cdir) for p in cdir.rglob('*') if p.is_file())
print('C %d files extracted:' % len(files))
for f in files:
    print('C   ', f, (cdir / f).stat().st_size)
