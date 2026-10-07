"""Fetch code and data from GitHub with the Python standard library only, for a rented box that cannot install git (Vast fallback; the home PC uses git).

Bootstrap (one line, no git; the repo is private, so a token is needed): curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github.raw" "https://api.github.com/repos/BenjaminHannan/learner/contents/custom_io/g8a/gh_fetch.py?ref=<SHA-or-branch>" -o gh_fetch.py

  python3 gh_fetch.py --ref <commit sha or branch> --dir custom_io --dest work/code/custom_io [--skip results]
      every file under custom_io/ at that ref (the directory tree is listed with the git trees API, one call; files come from the contents API with the raw media type, which also works for a private repo)
  python3 gh_fetch.py --ref claude/8a-own-data --files skills.jsonl.xz english.jsonl.xz teach.jsonl.xz --dest work/8a-inputs/own-data
  python3 gh_fetch.py --ref claude/data-pool-8b --files data_pool/web_slice.py data_pool/overlap13.py data_pool/panels/panel_hashes_all.npz \
        data_pool/built/own72_MANIFEST.json data_pool/built/web_slices_8a_MANIFEST.json --dest work/8a-inputs/data-pool

--files paths keep their directory structure under --dest. Resumes (skips a file whose size already matches the one GitHub reports for it when known) and retries 4 times with
backoff. The repo is private: set GITHUB_TOKEN (a fine-grained token with read access to contents). The contents API serves files up to 100 MB; none of ours is (the largest
own-text file is 48 MB).
"""
import argparse, json, os, sys, time, urllib.error, urllib.request

REPO = 'BenjaminHannan/learner'


def _req(url, accept=None):
    h = {'User-Agent': 'g8a-gh-fetch'}
    if accept:
        h['Accept'] = accept
    tok = os.environ.get('GITHUB_TOKEN')
    if tok:
        h['Authorization'] = 'Bearer ' + tok
    return urllib.request.Request(url, headers=h)


def _get(url, accept=None, tries=4):
    for k in range(tries):
        try:
            return urllib.request.urlopen(_req(url, accept), timeout=120)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404):
                raise
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))


def list_dir(repo, ref, d):
    """{path: size} of every blob under directory d at ref."""
    with _get(f'https://api.github.com/repos/{repo}/git/trees/{ref}:{d}?recursive=1', 'application/vnd.github+json') as r:
        t = json.load(r)
    if t.get('truncated'):
        sys.exit(f'the tree of {d} at {ref} is too big for one API call (truncated); use --files')
    return {f'{d}/{e["path"]}': e.get('size') for e in t['tree'] if e['type'] == 'blob'}


def fetch(repo, ref, path, dest_root, strip=None, size=None):
    rel = path if strip is None else path[len(strip):].lstrip('/')
    dst = os.path.join(dest_root, rel)
    if size is not None and os.path.exists(dst) and os.path.getsize(dst) == size:
        return 0
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    tmp = dst + '.part'
    with _get(f'https://api.github.com/repos/{repo}/contents/{path}?ref={ref}', 'application/vnd.github.raw') as r, open(tmp, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(tmp, dst)
    return os.path.getsize(dst)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=REPO)
    ap.add_argument('--ref', required=True, help='commit sha (preferred: reproducible) or branch name')
    ap.add_argument('--dir', help='fetch every file under this directory (its own name is dropped: --dest is the directory itself)')
    ap.add_argument('--files', nargs='*', default=[])
    ap.add_argument('--skip', nargs='*', default=['results', '__pycache__'], help='--dir: path components to leave out')
    ap.add_argument('--dest', required=True)
    a = ap.parse_args(argv)
    n = tot = 0
    if a.dir:
        for path, size in sorted(list_dir(a.repo, a.ref, a.dir.strip('/')).items()):
            if any(c in a.skip for c in path.split('/')[1:]):
                continue
            tot += fetch(a.repo, a.ref, path, a.dest, strip=a.dir.strip('/'), size=size)
            n += 1
    for path in a.files:
        tot += fetch(a.repo, a.ref, path, a.dest)
        n += 1
    print(json.dumps(dict(files=n, bytes=tot, ref=a.ref, dest=a.dest)))


if __name__ == '__main__':
    main()
