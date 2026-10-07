"""Run one research-loop eval on the rented GPU box (LOCKED). Syncs the editable learner files, checks that the box's locked files match this
checkout byte for byte, runs creative.rl.eval_c2 there and streams its output. The box URL and token live outside the repo (~/rl/vast/url, token).

  python3 creative/rl/remote.py dev|holdout SEED [extra eval args]
"""
import glob, hashlib, io, json, os, subprocess, sys, tarfile, time, urllib.request

VAST = os.path.expanduser(os.environ.get('RL_VAST_DIR', '~/rl/vast'))
EDITABLE = ['creative/rl/method.py', 'creative/rl/m']
LOCKED = ['creative/rl/eval_c2.py', 'creative/rl/refs.py', 'creative/rl/make_holdout.py', 'creative/fastsleep.py', 'creative/fewshot.py',
          'creative/programs.py', 'creative/sleep.py', 'creative/c2_pilot.py', 'creative/c2_stones.py', 'creative/rules_real.py', 'creative/legal.py',
          'creative/nightchain.py', 'creative/data/c2/dev.jsonl', 'creative/data/c2/pool.jsonl', 'creative/data/c2/warm.jsonl',
          'creative/data/c2/labelled.jsonl', 'creative/data/c2rl/holdout.jsonl'] + sorted(glob.glob('custom_io/**/*.py', recursive=True))
ENV = 'RL_DEVICE=cuda RL_PARENTS=/workspace/rl/parents RL_SKILLS_TRAIN=/workspace/work/data/train.jsonl RL_SKILLS_DATA=/workspace/work/data_big'


def call(path, data=None, timeout=60, tries=6):
    url, tok = open(os.path.join(VAST, 'url')).read().strip(), open(os.path.join(VAST, 'token')).read().strip()
    for k in range(tries):
        try:
            req = urllib.request.Request(url + path, data=data, headers={'X-Token': tok}, method='POST' if data is not None else 'GET')
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 * 2 ** k)


def main():
    split, seed, extra = sys.argv[1], sys.argv[2], sys.argv[3:]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for p in EDITABLE:
            if os.path.exists(p):
                tf.add(p, filter=lambda ti: None if '__pycache__' in ti.name else ti)
    call('/put?path=learner/_sync.tgz', buf.getvalue())
    local = {p: hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in LOCKED}
    cmd = ('cd learner && rm -rf creative/rl/m && tar xzf _sync.tgz && python3 -c "import hashlib,json,sys;'
           'print(\'LOCKHASH\',json.dumps({p:hashlib.sha256(open(p,\'rb\').read()).hexdigest() for p in sys.argv[1:]}))" ' + ' '.join(LOCKED) +
           f' && {ENV} PYTHONPATH=. python3 -m creative.rl.eval_c2 --split {split} --seed {seed} --threads 4 ' + ' '.join(extra))
    jid = call('/start', json.dumps({'cmd': cmd, 'timeout': 3600}).encode())['id']
    n, ok_hash = 0, False
    while True:
        time.sleep(4)
        j = call(f'/job?id={jid}&from={n}')
        for line in j['out'].splitlines():
            if line.startswith('LOCKHASH '):
                remote = json.loads(line[9:])
                bad = [p for p in LOCKED if remote.get(p) != local[p]]
                if bad:
                    call(f'/kill?id={jid}', b'')
                    print('locked files differ on the box: ' + ', '.join(bad), flush=True)
                    sys.exit(3)
                ok_hash = True
                continue
            print(line, flush=True)
        n = j['n']
        if j['done']:
            if not ok_hash:
                print('no lock hash from the box', flush=True)
                sys.exit(3)
            sys.exit(j['code'] or 0)


if __name__ == '__main__':
    main()
