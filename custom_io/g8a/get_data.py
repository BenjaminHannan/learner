"""Get the 8a data onto a machine that cannot read the project files (BensPC): rebuild what is rebuildable, verify every file against the data-pool thread's
manifests (PR #47, branch claude/data-pool-8b: data_pool/built/own72_MANIFEST.json and web_slices_8a_MANIFEST.json), refuse to continue on any mismatch.

  python -m custom_io.g8a.get_data --work WORK --data-pool DIR --own-xz DIR [--rungs rung3 rung10 rung30]

  --data-pool DIR   a checkout of branch claude/data-pool-8b (data_pool/web_slice.py, overlap13.py, panels/panel_hashes_all.npz, built/*_MANIFEST.json).
  --own-xz DIR      the three own-text files compressed: skills.jsonl.xz english.jsonl.xz teach.jsonl.xz (branch claude/8a-own-data: they are generator output
                    that cannot be re-made on the PC, TEACH being 171,940 rows the 1.2B wrote on the PC GPU, so they travel in git, 83 MB in all).
  WEB (rebuilt)     FineWeb-Edu sample-10BT shard 0 (2.15 GB, downloaded from the Hugging Face hub, resumable), then data_pool/web_slice.py with the manifest's own
                    arguments (fk-max 12, budgets rung3 / rung10 / rung30, the panel hash index in the checkout). The slices must hash to the manifest's sha256: the
                    rebuild was checked once in the cloud (rung3 and rung10 hashes equal), so a mismatch means a different shard revision or index, and nothing is used.
Outputs WORK/data8a/{own72/*.jsonl, web/slice_rung*.jsonl, READY.json}. Re-running skips every file whose sha256 already matches. A lock file (WORK/data8a/LOCK)
makes concurrent callers wait for the first one.
"""
import argparse, hashlib, json, lzma, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

SHARD_REPO, SHARD_FILE = 'HuggingFaceFW/fineweb-edu', 'sample/10BT/000_00000.parquet'


def sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def say(*a):
    print('[get_data %s]' % time.strftime('%H:%M:%S'), *a, flush=True)


class Lock:
    def __init__(self, path):
        self.path = Path(path)

    def __enter__(self):
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                if time.time() - self.path.stat().st_mtime > 6 * 3600:     # a crashed holder
                    self.path.unlink(missing_ok=True)
                    continue
                say('another process is preparing the data; waiting')
                time.sleep(30)

    def __exit__(self, *e):
        self.path.unlink(missing_ok=True)


def own_text(work, xz_dir, manifest):
    out = work / 'own72'
    out.mkdir(parents=True, exist_ok=True)
    for name, want in manifest['sha256'].items():
        dst = out / name
        if dst.exists() and sha256(dst) == want:
            say(name, 'ok (already there)')
            continue
        src = Path(xz_dir) / (name + '.xz')
        say('decompressing', src)
        with lzma.open(src, 'rb') as f, open(dst, 'wb') as g:
            shutil.copyfileobj(f, g, 1 << 22)
        got = sha256(dst)
        if got != want:
            dst.unlink()
            sys.exit(f'HASH MISMATCH {name}: got {got}, manifest {want}')
        say(name, 'verified', want[:12])
    return {n: w for n, w in manifest['sha256'].items()}


def download_shard(dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(SHARD_REPO, SHARD_FILE, repo_type='dataset', local_dir=str(dst.parent / 'hub'))
        return Path(p)
    except ImportError:
        pass
    url = f'https://huggingface.co/datasets/{SHARD_REPO}/resolve/main/{SHARD_FILE}'
    have = dst.stat().st_size if dst.exists() else 0
    req = urllib.request.Request(url, headers={'Range': f'bytes={have}-'} if have else {})
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, 'ab' if have and r.status == 206 else 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 22)
    return dst


def web_slices(work, data_pool, manifest, rungs):
    out = work / 'web'
    out.mkdir(parents=True, exist_ok=True)
    want = {f'slice_{r}.jsonl': manifest['sha256'][f'slice_{r}.jsonl'] for r in rungs}
    if all((out / n).exists() and sha256(out / n) == h for n, h in want.items()):
        say('web slices ok (already there)', sorted(want))
        return want
    shard = work / 'shard' / '000_00000.parquet'
    if not shard.exists():
        say('downloading FineWeb-Edu shard 0 (2.15 GB)')
        got = download_shard(shard)
        if Path(got) != shard:
            shutil.copy2(got, shard)
    # the data-pool code needs numpy and pyarrow
    for mod in ('numpy', 'pyarrow'):
        try:
            __import__(mod)
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', mod])
    tmp = work / 'web_build'
    shutil.rmtree(tmp, ignore_errors=True)
    budgets = ','.join(f'{k}={v:g}' for k, v in manifest['budgets'].items())
    say('building web slices:', budgets)
    subprocess.check_call([sys.executable, str(Path(data_pool) / 'data_pool' / 'web_slice.py'), '--shards', str(shard), '--index',
                           str(Path(data_pool) / 'data_pool' / 'panels' / 'panel_hashes_all.npz'), '--out', str(tmp), '--fk-max', str(manifest['fk_max']),
                           '--plain-fk', str(manifest['plain_fk']), '--budgets', budgets])
    bad = []
    for name, h in manifest['sha256'].items():
        got = sha256(tmp / name)
        if name in want and got != h:
            bad.append((name, got, h))
    if bad:
        sys.exit('HASH MISMATCH after the web rebuild (different shard revision or panel index?): ' + json.dumps(bad))
    for n in want:
        shutil.move(str(tmp / n), str(out / n))
    say('web slices verified', {n: h[:12] for n, h in want.items()})
    return want


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--data-pool', required=True)
    ap.add_argument('--own-xz')
    ap.add_argument('--expect-manifest-sha', help='sha256 of data_pool/built/own72_MANIFEST.json that this run must see; anything else (or PENDING) refuses to run, so stale own text cannot be used')
    ap.add_argument('--out', help='dir for RESULT.json (local_runner counts the line as done when it exists)')
    ap.add_argument('--rungs', nargs='+', default=['rung3', 'rung10', 'rung30'])
    a = ap.parse_args(argv)
    work = Path(a.work) / 'data8a'
    work.mkdir(parents=True, exist_ok=True)
    built = Path(a.data_pool) / 'data_pool' / 'built'
    if a.expect_manifest_sha is not None:
        got = sha256(built / 'own72_MANIFEST.json')
        if got != a.expect_manifest_sha:
            msg = f'own72_MANIFEST.json sha256 is {got}, expected {a.expect_manifest_sha}: the own text is not the approved build; refusing to run'
            (work / 'REFUSED.txt').write_text(msg + '\n')
            (work / 'READY.json').unlink(missing_ok=True)
            sys.exit(msg)
    (work / 'REFUSED.txt').unlink(missing_ok=True)
    with Lock(work / 'LOCK'):
        own = json.load(open(built / 'own72_MANIFEST.json'))
        web = json.load(open(built / 'web_slices_8a_MANIFEST.json'))
        o = own_text(work, a.own_xz or '.', own)
        w = web_slices(work, a.data_pool, web, a.rungs)
        json.dump(dict(own72=o, web=w, shard=SHARD_FILE, made=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())), open(work / 'READY.json', 'w'), indent=1)
    say('READY', work)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(dict(status='ok', ready=str(work / 'READY.json')), open(os.path.join(a.out, 'RESULT.json'), 'w'))


if __name__ == '__main__':
    main()
