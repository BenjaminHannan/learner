"""make_port_tree.py OUT_DIR  (DRAFT, like everything in this pack until the coordinator has code-reviewed it)

Builds OUT_DIR/custom_io = `git archive 74d6e92c75 custom_io` + every file under port/overlay/custom_io/ (b3g2.py edited, b3g2_defer.py new, train.py = the g2fa4 checkpoint/resume train.py + --speed-arms,
tests/test_b3g2_defer.py). The g2fa4 overlay/train.py is only checked against its sha256 pin. Prints the sha256 of every overlay file and of the base file it replaced. Refuses: an OUT_DIR that exists and is not empty (so an existing src-b3g2 /
src-b3g2ck tree is never written into), an OUT_DIR that is or lies inside (resolved path, any ancestor) a folder named src-b3g2 or src-b3g2ck, a g2fa4 train.py off its pin, a base whose b3g2.py / train.py sha256 is not the g2fa4 pin, a missing commit. Writes nothing outside OUT_DIR.
"""
import hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMIT_FULL = '74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6'
PINS = {'custom_io/models/b3g2.py': 'a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce',
        'custom_io/train.py': 'e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d'}
G2FA4_PIN = 'e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015'      # sha256 of the g2fa4 overlay/train.py this pack's train.py was derived from
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
    real = os.path.realpath(out)
    if any(part.lower() in {n.lower() for n in FORBIDDEN_NAMES} for part in real.split(os.sep)):      # case-insensitive (the PC's NTFS is not case sensitive)
        die(f'{out} (resolved: {real}) is, or is inside, a folder named {FORBIDDEN_NAMES} (any case): never builds into those trees')
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        die(f'{out} exists and is not an empty folder')
    top = subprocess.run(['git', '-C', HERE, 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True).stdout.strip()
    full = subprocess.run(['git', '-C', top, 'rev-parse', '--verify', '74d6e92c75^{commit}'], capture_output=True, text=True)
    if full.returncode or full.stdout.strip() != COMMIT_FULL:
        die(f'commit 74d6e92c75 is not {COMMIT_FULL} in {top} ({full.stdout.strip()!r} {full.stderr.strip()})')
    for p in (G2FA4_TRAIN, OVERLAY):
        if not os.path.exists(p):
            die(f'missing {p}')
    if sha(G2FA4_TRAIN) != G2FA4_PIN:
        die(f'g2fa4 overlay/train.py sha256 {sha(G2FA4_TRAIN)} != pin {G2FA4_PIN}')
    base = {}
    for rel, pin in PINS.items():       # checked on the committed blobs, before anything is written
        h = hashlib.sha256(subprocess.run(['git', '-C', top, 'show', f'{COMMIT_FULL}:{rel}'], check=True, capture_output=True).stdout).hexdigest()
        if h != pin:
            die(f'base {rel} sha256 {h} != pin {pin}')
        base[rel] = h
    os.makedirs(out, exist_ok=True)
    arc = subprocess.run(['git', '-C', top, 'archive', COMMIT_FULL, 'custom_io'], check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', out], input=arc, check=True)
    for rel, pin in PINS.items():       # and again on the extracted files
        if sha(os.path.join(out, rel)) != pin:
            die(f'extracted {rel} differs from the pin; {out} is left for inspection')
    print(f'base: git archive {COMMIT_FULL} custom_io -> {out}/custom_io')
    for rel, h in base.items():
        print(f'  base  {h}  {rel}  (matches the g2fa4 pin)')
    print(f'  g2fa4 {G2FA4_PIN}  train.py the overlay train.py derives from (pinned, matches; not copied: the overlay file below replaces the base train.py)')
    # this pack's overlay files (train.py here is g2fa4's + --speed-arms)
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
            was = 'NEW' if prev is None else f'replaces {prev[:12]}' + (' (base)' if prev == base.get(rel) else ' (BASE FILE NOT IN THE PIN LIST)')
            print(f'  port  {sha(src)}  {rel}  ({was})')
    print(f'port tree ready: {out} (put {out} on PYTHONPATH / PROF_PKG_ROOT; no .pyc written)')


if __name__ == '__main__':
    main(sys.argv[1:])
