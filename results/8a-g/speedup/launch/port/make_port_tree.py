"""make_port_tree.py OUT_DIR  (DRAFT, like everything in this pack until the coordinator has code-reviewed it)

Builds OUT_DIR/custom_io = `git archive 74d6e92c75 custom_io` + the g2fa4 checkpoint/resume train.py + every file under port/overlay/custom_io/ (b3g2.py edited, b3g2_defer.py new, train.py with
--speed-arms, tests/test_b3g2_defer.py). Prints the sha256 of every overlay file and of the base file it replaced. Refuses: an OUT_DIR that exists and is not empty (so an existing src-b3g2 /
src-b3g2ck tree is never written into), those two names as OUT_DIR, a base whose b3g2.py / train.py sha256 is not the g2fa4 pin, a missing commit. Writes nothing outside OUT_DIR.
"""
import hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMIT_FULL = '74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6'
PINS = {'custom_io/models/b3g2.py': 'a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce',
        'custom_io/train.py': 'e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d'}
G2FA4_TRAIN = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'pc-job-cards', 'g2fa4', 'overlay', 'train.py'))
OVERLAY = os.path.join(HERE, 'overlay', 'custom_io')
FORBIDDEN_NAMES = ('src-b3g2', 'src-b3g2ck')


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def die(msg):
    sys.exit(f'make_port_tree: REFUSED: {msg}')


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    out = os.path.abspath(argv[0])
    if os.path.basename(out.rstrip(os.sep)) in FORBIDDEN_NAMES:
        die(f'{out}: never builds into a tree named {FORBIDDEN_NAMES}')
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        die(f'{out} exists and is not an empty folder')
    top = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True).stdout.strip()
    full = subprocess.run(['git', '-C', top, 'rev-parse', '--verify', '74d6e92c75^{commit}'], capture_output=True, text=True)
    if full.returncode or full.stdout.strip() != COMMIT_FULL:
        die(f'commit 74d6e92c75 is not {COMMIT_FULL} in {top} ({full.stdout.strip()!r} {full.stderr.strip()})')
    for p in (G2FA4_TRAIN, OVERLAY):
        if not os.path.exists(p):
            die(f'missing {p}')
    os.makedirs(out, exist_ok=True)
    arc = subprocess.run(['git', '-C', top, 'archive', COMMIT_FULL, 'custom_io'], check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', out], input=arc, check=True)
    base = {}
    for rel, pin in PINS.items():
        h = sha(os.path.join(out, rel))
        if h != pin:
            import shutil
            shutil.rmtree(out)
            die(f'base {rel} sha256 {h} != pin {pin}')
        base[rel] = h
    print(f'base: git archive {COMMIT_FULL} custom_io -> {out}/custom_io')
    for rel, h in base.items():
        print(f'  base  {h}  {rel}  (matches the g2fa4 pin)')
    # 1. the g2fa4 train.py (checkpoint / resume) replaces the base train.py
    dst = os.path.join(out, 'custom_io', 'train.py')
    open(dst, 'wb').write(open(G2FA4_TRAIN, 'rb').read())
    print(f'  g2fa4 {sha(G2FA4_TRAIN)}  custom_io/train.py  (g2fa4 overlay/train.py; replaces base {base["custom_io/train.py"][:12]})')
    # 2. this pack's overlay files (train.py here is g2fa4's + --speed-arms; it replaces the g2fa4 one)
    for dp, dn, fn in os.walk(OVERLAY):
        dn[:] = sorted(d for d in dn if d != '__pycache__')
        for f in sorted(fn):
            if f.endswith('.pyc'):
                continue
            src = os.path.join(dp, f)
            rel = 'custom_io/' + os.path.relpath(src, OVERLAY).replace(os.sep, '/')
            dst = os.path.join(out, rel)
            prev = sha(dst) if os.path.exists(dst) else None
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(open(src, 'rb').read())
            was = 'NEW' if prev is None else f'replaces {prev[:12]}' + (' (base)' if prev == base.get(rel) else ' (g2fa4 train.py)' if rel == 'custom_io/train.py' else ' (BASE FILE NOT IN THE PIN LIST)')
            print(f'  port  {sha(src)}  {rel}  ({was})')
    print(f'port tree ready: {out} (put {out} on PYTHONPATH / PROF_PKG_ROOT; no .pyc written)')


if __name__ == '__main__':
    main(sys.argv[1:])
