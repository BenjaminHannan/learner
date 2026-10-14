"""Show two defects of the kit's own vast.py (unpatched), offline: urllib.request.urlopen is replaced, no network call is possible.
usage: python3 kit_bug_test.py KIT_VAST_PY DRY_RUN_LOG
 1  `collect` on a log that contains checkpoint parts (7-field RBEGIN lines)
 2  `collectck` writes a normal result block to the module's OUT (custom_io/results of the kit's repo), not to --out
"""
import io
import json
import sys
import urllib.request
import importlib.util
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

kit, logf = sys.argv[1:3]
spec = importlib.util.spec_from_file_location('vast', kit)
vast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vast)
LOG = Path(logf).read_text(errors='replace').splitlines()
first = next(i for i, ln in enumerate(LOG) if 'PTC3S RESULT PRINTED' in ln)
st = {'cursor': len(LOG), 'tail': 20000}


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake(req, timeout=None):
    url = req if isinstance(req, str) else req.full_url
    if 'request_logs' in url:
        st['tail'] = int(json.loads(req.data.decode())['tail'])
        return Resp(json.dumps({'result_url': 'http://fake.invalid/log'}).encode())
    return Resp('\n'.join(LOG[:st['cursor']][-st['tail']:]).encode())


out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('/tmp/kit_bug_out')
print('kit OUT (module default for collectck result blocks):', vast.OUT)
with mock.patch.object(urllib.request, 'urlopen', fake), mock.patch('time.sleep', lambda s: None):
    st['cursor'] = len(LOG)
    sys.argv = [kit, 'collect', '--id', '1', '--out', str(out / 'c1')]
    try:
        with redirect_stdout(io.StringIO()) as b:
            vast.main()
        print('1 collect printed:', b.getvalue().strip())
    except Exception as e:
        print('1 collect on a log with checkpoint parts raised: %s: %s' % (type(e).__name__, e))
    st['cursor'] = first + 5
    vast.OUT = out / 'kit_default_OUT'                      # stand-in for custom_io/results, so nothing is written into any repo
    sys.argv = [kit, 'collectck', '--id', '1', '--out', str(out / 'c2'), '--max-min', '1', '--want', '8aPTC3S-3M-s400']
    with redirect_stdout(io.StringIO()):
        vast.main()
print('2 --out given as', out / 'c2', '; result block landed in:', sorted(str(p.relative_to(out)) for p in out.glob('*/8aPTC3S-3M-s400/RESULT.json')))
