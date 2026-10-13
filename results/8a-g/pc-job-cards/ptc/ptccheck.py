# CPU check for install_ptc.ps1, run from the new src-ptc folder (cwd = its root, which holds custom_io):
#   python ptccheck.py PATH_TO_ORIGINAL_ROOT        (C:\Users\benja\custom-io\src-b3g2, read only)
# No GPU and no EmbeddingGemma weights (eg_embed models are only counted). Prints PTC CPU CHECK OK at the end.
#  (i)   the six files PTC replaced: the originals (src-b3g2) are 74d6e92c75's by sha256, the new ones are the shipped overlay by sha256
#  (ii)  custom_io.tests.test_ptc, run with the original tree named by PTC_ORIG_TREE: calc_full cases; mask == generate (forced positions == masked
#        positions, text == gold); masked loss (no gradient on calculator characters, same width W); PTC count == PTS at 3M and 10M and LESIONS
#        ['nocalc']; job caps handling == PTS's; calc_train off == the original files (same weights at the same seed, loss, targets, trained decodes
#        intact / calc / loops:0, LESIONS ['calc'], cap counters, old arms' sizes and train_args)
#  (iii) both queue files parse; their g8a lines go through job.py's own argument parser (arms PTC, eg_embed, caps_b3s.json, accum), the PTC cfg and the
#        train.py command build, and each line equals the PTS control's line (src-b3g2's 8aG2C3S / 8aG2C10S) with only the arm and the names changed
import sys, os, re, json, hashlib, subprocess, argparse

ORIG = os.path.abspath(sys.argv[1])
NEW = os.getcwd()
PINS = {   # path under custom_io: (sha256 at 74d6e92c75, sha256 of the PTC file)
    'capcount.py': ('92E4CE46013CCC67CBAD583AC9EDB52E76F7504CB004FD236255A2EB89F22C3F', 'E3C43AC13DC76420BBE3DD442456489CB998402F07E4413E39EFE6A8EEA0C97F'),
    'models/plain_tf_steps.py': ('E3418B45FB339C38F90765CC7929C4B60E97453E28E375102EF15BFF64F76226', 'C39CDF1DC91EDDA7A0F11CF658FAF22148E533759227FC72153DAAFDEAAC4225'),
    'models/plain_lm.py': ('E90ACCF2E332D08A1E14CD2B5B537A9BE97BC93C44D48ED14DFE26FA8567AD10', 'F0E5FE42662EADC862E300DADE9470EB4AFA2898AF228A5F8061DA86C4CEF90B'),
    'g8a/configs.py': ('31287A25A6AD9CBF48973520F1174C788A3DB5CE61F607265AA5EC8FA99BD5DA', '48AA19CCB8B329FE11E45E42A17872D2581298CDBC03C2B11E3E034ADC887ECF'),
    'g8a/job.py': ('A590E3F176159F531571B1E5AE95BD48D2160238CB999ADD5EB6BE7734FE6A1A', 'EB0CF9DB191A75992F8ED24464D996B7EAABC86538843762B23E1A8C5F3C6888'),
    'tests/test_ptc.py': (None, '152D694A6B5798AA9CC0C352E5BA746E4D61F80F71BE0EB62E062C9BD1F6F972'),
}
CAPS_PY = '32862AE2D4E6E401FCAD5BB6C5E54B0B8845019202DEA73E2CB4C7EFE5EEA03E'
sys.path.insert(0, NEW)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest().upper() if os.path.exists(p) else 'missing'


# (i)
for rel, (o, n) in PINS.items():
    if o is not None:
        assert sha(os.path.join(ORIG, 'custom_io', rel)) == o.upper(), f'{rel} in {ORIG} is not 74d6e92c75\'s ({sha(os.path.join(ORIG, "custom_io", rel))})'
    assert sha(os.path.join(NEW, 'custom_io', rel)) == n.upper(), f'{rel} here is not the PTC file ({sha(os.path.join(NEW, "custom_io", rel))})'
for root in (ORIG, NEW):
    assert sha(os.path.join(root, 'custom_io', 'g8a', 'caps.py')) == CAPS_PY, f'caps.py in {root} changed'
print('(i) six replaced files: originals = 74d6e92c75 (sha256), new = the PTC overlay; caps.py unchanged in both')

# (ii)
env = dict(os.environ, PYTHONPATH=os.pathsep.join([NEW] + ([os.environ['PYTHONPATH']] if os.environ.get('PYTHONPATH') else [])), OMP_NUM_THREADS='1', PTC_ORIG_TREE=ORIG, PYTHONUTF8='1')
p = subprocess.run([sys.executable, '-m', 'custom_io.tests.test_ptc'], cwd=NEW, env=env, capture_output=True, text=True)
lines = (p.stdout + p.stderr).strip().splitlines()
for l in lines[-8:]:
    print('    ' + l[:230])
assert p.returncode == 0 and lines and lines[-1] == 'all test_ptc checks passed', 'test_ptc failed'
print('(ii) test_ptc: all checks passed')

# (iii)
from custom_io.local_runner import parse_queue, command
from custom_io.g8a import configs as C, job as J
from pathlib import Path


class Stop(Exception):
    pass


def parse_job(args):
    """The namespace job.main builds from a queue line (argparse only: nothing else of main runs)."""
    cmd = command('g8a', args, Path('W'), Path('O'), 'cuda')
    argv = cmd[cmd.index('custom_io.g8a.job') + 1:]
    real = argparse.ArgumentParser.parse_args

    def grab(self, a=None, ns=None):
        grab.ns = real(self, a, ns)
        raise Stop
    argparse.ArgumentParser.parse_args = grab
    try:
        J.main(argv)
    except Stop:
        pass
    finally:
        argparse.ArgumentParser.parse_args = real
    return grab.ns


for name, ctl, rung, accum in (('8aPTC3S', '8aG2C3S', '3M', 16), ('8aPTC10S', '8aG2C10S', '10M', 32)):
    q = os.path.join(NEW, 'custom_io', 'queue_local', name + '-pc.txt')
    r = parse_queue(q, work='W')
    assert [x[0] for x in r] == ['8a-data', f'{name}-{rung}-s400'] and r[1][1] == 'g8a' and r[1][3] == 9000, [x[:2] for x in r]
    ns = parse_job(r[1][2])
    b2x = json.loads(ns.b2_extra)
    assert ns.arms == ['PTC'] and ns.rung == rung and ns.seed == 400 and b2x == {'eg_embed': True} and ns.accum == f'PTC={accum}', vars(ns)
    assert ns.caps_file.endswith('caps_b3s.json') and ns.cloze_long and J.parse_accum(ns.accum, None, rung) == {'PTC': accum}
    cfg = C.ptc_cfg(rung, b2x)
    assert cfg == dict(C.pts_cfg(rung, b2x), calc_train=True) and cfg['all_steps'] and cfg['eg_embed'], cfg
    c = os.path.join(ORIG, 'custom_io', 'queue_local', ctl + '-pc.txt')
    if os.path.exists(c):
        want = [l for l in open(c, encoding='utf-8').read().splitlines() if l.startswith(('g8a', '# ENV', '# MEM'))]
        got = [l for l in open(q, encoding='utf-8').read().splitlines() if l.startswith(('g8a', '# ENV', '# MEM'))]
        fix = lambda l: l.replace("--arms PTS", "--arms PTC").replace("--accum PTS=", "--accum PTC=").replace(ctl, name)
        assert [fix(l) for l in want] == got, ('queue line differs from the PTS control beyond arm and names', want, got)
        same = f'equal to {ctl}\'s lines except arm and names'
    else:
        same = f'{ctl}-pc.txt not in src-b3g2 (not compared)'
    print(f'(iii) {name}-pc.txt: {len(r)} entries, {r[1][0]} --arms PTC --accum PTC={accum}, job.py parses it, cfg = PTS cfg + calc_train; {same}')
print('PTC CPU CHECK OK')
