#!/usr/bin/env python3
"""Vast control for the ultracode queue box (scripts/cap256_launch/ultracode_box.sh), run from the cloud container.

The proxy adds the Vast key to console.vast.ai requests; this script never reads or prints a key.
  search [--gpu "RTX 5090"] [--n 8]       cheapest verified offers (reliability >= 0.98, CUDA >= 12.8)
  create --offer ID [--label L] [--maxpar 5]
  status --id ID
  tail --id ID [--n 60]                   last log lines (result lines hidden)
  collect --id ID [--out DIR]             decode every finished job's RBEGIN/R|/REND block, check sha256, extract
  destroy --id ID                         and confirm it is gone
  credit
"""
import argparse
import base64
import hashlib
import io
import json
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API = 'https://console.vast.ai/api/v0'
IMAGE = 'pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime'
BOX = REPO / 'scripts/cap256_launch/ultracode_box.sh'
OUT = REPO / 'artifacts/ultracode-v4/results'


def call(method, path, body=None, timeout=60):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read().decode() or '{}')
        except Exception:
            d = {}
        return {'success': False, 'http': e.code, 'error': d.get('error'), 'msg': d.get('msg')}


def get(url, timeout=120):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def search(a):
    q = {'verified': {'eq': True}, 'rentable': {'eq': True}, 'rented': {'eq': False}, 'type': 'on-demand',
         'num_gpus': {'eq': 1}, 'gpu_ram': {'gte': 23000}, 'reliability': {'gte': 0.98},
         'cuda_max_good': {'gte': 12.8}, 'disk_space': {'gte': 60}, 'inet_down': {'gte': 300},
         'cpu_cores_effective': {'gte': 8}, 'order': [['dph_total', 'asc']], 'limit': 300}
    offers = call('POST', '/bundles/', q).get('offers') or []
    keep = [o for o in offers if o.get('gpu_name') == a.gpu]
    for o in keep[: a.n]:
        print(json.dumps({k: o.get(k) for k in ('id', 'gpu_name', 'gpu_ram', 'dph_total', 'reliability', 'inet_down',
                                                 'cpu_cores_effective', 'cpu_ram', 'disk_space', 'cuda_max_good',
                                                 'geolocation')}))


def create(a):
    script = BOX.read_text()
    args = ['bash', '-c', 'export MAXPAR=%d\n' % a.maxpar + script, 'uc']
    body = {'client_id': 'me', 'image': IMAGE, 'disk': 80, 'label': a.label, 'runtype': 'args', 'args': args,
            'target_state': 'running'}
    r = call('PUT', '/asks/%s/' % a.offer, body, timeout=120)
    print(json.dumps({'success': r.get('success'), 'new_contract': r.get('new_contract'), 'error': r.get('error'),
                      'msg': r.get('msg'), 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}))


def inst(i):
    r = call('GET', '/instances/%s/' % i)
    x = r.get('instances') or {}
    return (x[0] if x else {}) if isinstance(x, list) else x


def status(a):
    x = inst(a.id)
    print(json.dumps({k: x.get(k) for k in ('id', 'label', 'actual_status', 'intended_status', 'cur_state',
                                             'status_msg', 'gpu_name', 'dph_total', 'start_date', 'duration')}))


def log_text(i, tail=200000):
    r = call('PUT', '/instances/request_logs/%s/' % i, {'tail': str(tail)})
    url = r.get('result_url')
    if not url:
        return ''
    for _ in range(24):
        time.sleep(5)
        try:
            return get(url, 120).decode('utf-8', 'replace')
        except Exception:
            continue
    return ''


def tail(a):
    text = log_text(a.id)
    lines = [ln for ln in text.splitlines() if not ln.startswith('R|')]
    print('\n'.join(lines[-a.n:]))


def collect(a):
    text = log_text(a.id)
    out = Path(a.out)
    blocks, cur = {}, None
    for ln in text.splitlines():
        if ln.startswith('RBEGIN|'):
            _, name, h, size = ln.split('|')
            cur = name
            blocks[name] = {'sha': h, 'size': int(size), 'parts': []}
        elif ln.startswith('R|') and cur:
            _, name, data = ln.split('|', 2)
            if name in blocks:
                blocks[name]['parts'].append(data)
        elif ln.startswith('REND|'):
            cur = None
    got = {}
    for name, b in blocks.items():
        try:
            raw = base64.b64decode(''.join(b['parts']))
        except Exception as e:
            got[name] = 'b64-error %s' % e
            continue
        if hashlib.sha256(raw).hexdigest() != b['sha'] or len(raw) != b['size']:
            got[name] = 'sha-mismatch'
            continue
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / 'result.tgz.sha256').write_text(b['sha'] + '\n')
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as t:
            t.extractall(out, filter='data')
        got[name] = 'ok'
    print(json.dumps(got))


def waitfor(a):
    """poll every 2 min; return when a job not in --seen has finished (REND), on UC-FAIL, or after --max-min"""
    seen = set(filter(None, (a.seen or '').split(',')))
    t0 = time.time()
    while time.time() - t0 < a.max_min * 60:
        text = log_text(a.id)
        done = {ln.split('|')[1] for ln in text.splitlines() if ln.startswith('REND|')}
        fail = [ln for ln in text.splitlines() if 'UC-FAIL' in ln or 'Traceback' in ln]
        if done - seen or fail:
            print(json.dumps({'finished': sorted(done), 'new': sorted(done - seen), 'fail': fail[-3:],
                              'waited_min': round((time.time() - t0) / 60, 1)}))
            return
        time.sleep(120)
    print(json.dumps({'timeout': True, 'waited_min': round((time.time() - t0) / 60, 1)}))


def destroy(a):
    r = call('DELETE', '/instances/%s/' % a.id)
    print(json.dumps({'destroy': r.get('success'), 'msg': r.get('msg')}))
    time.sleep(5)
    ids = [i.get('id') for i in (call('GET', '/instances/').get('instances') or [])]
    print(json.dumps({'still_listed': int(a.id) in ids}))


def credit(a):
    d = call('GET', '/users/current/')
    print(json.dumps({'credit': d.get('credit')}))
    for i in call('GET', '/instances/').get('instances') or []:
        print(json.dumps({k: i.get(k) for k in ('id', 'label', 'actual_status', 'gpu_name', 'dph_total')}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['search', 'create', 'status', 'tail', 'collect', 'destroy', 'credit', 'waitfor'])
    ap.add_argument('--gpu', default='RTX 5090')
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--offer')
    ap.add_argument('--label', default='claude-ultracode-v4')
    ap.add_argument('--maxpar', type=int, default=5)
    ap.add_argument('--id')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--seen', default='')
    ap.add_argument('--max-min', type=float, default=120)
    a = ap.parse_args()
    {'search': search, 'create': create, 'status': status, 'tail': tail, 'collect': collect, 'destroy': destroy,
     'credit': credit, 'waitfor': waitfor}[a.cmd](a)


if __name__ == '__main__':
    main()
