"""Fill the pin blocks of ptc3s_box.template.sh from the PTC package README (the pinned copy fetched from c2bf1a71c7), install_ptc.ps1 and the PC's own scripts.
Every value is read from a source file, none is typed here; the box script re-checks them against README.md / install_ptc.ps1 at run time as well."""
import os, re, subprocess, sys
S = '/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox'
OV = S + '/ovl/results/8a-g/pc-job-cards/ptc'
readme = open(OV + '/README.md').read()
ps1 = open(OV + '/install_ptc.ps1').read()
rows = re.findall(r'\| `([^`]+)` \| `([^`]+)` \| `([0-9A-F]{64}|\(new file\))` \| `([0-9A-F]{64})` \|', readme)
assert len(rows) == 6, rows
ORDER = ['capcount.py', 'plain_tf_steps.py', 'plain_lm.py', 'configs.py', 'job.py', 'test_ptc.py']      # install_ptc.ps1's $FILES order (the README lists them in another order)
assert sorted(r[0] for r in rows) == sorted(ORDER), rows
rows.sort(key=lambda r: ORDER.index(r[0]))
overlay = []
for f, dest, old, new in rows:
    o = '-' if old.startswith('(') else old.lower()
    # the ps1 must carry the same triple (rel path with backslashes there)
    m = re.search(r"f = '%s';\s+rel = '%s';\s+o = (\$null|'%s');\s+n = '%s'" % (re.escape(f), re.escape(dest.replace('/', '\\')), old, new), ps1)
    assert m, ('install_ptc.ps1 does not carry the README row', f)
    overlay.append('%s %s %s %s' % (f, dest, o, new.lower()))
oth = dict(re.findall(r'\| `([^`]+)` \| `([0-9A-F]{64})` \|', readme.split('Other files:')[1]))
pkg = ['%s %s' % (f, oth[f].lower()) for f in ('ptccheck.py', 'install_ptc.ps1', '8aPTC3S-pc.txt', '8aPTC10S-pc.txt', 'ptc3s.template.md', 'ptc10s.template.md')]
caps_py = re.search(r"\$CAPS\s+= '([0-9A-F]{64})'", ps1).group(1).lower()
up = open(S + '/docs/upgrade_post_g1_v3.ps1').read()
caps_b3s = re.search(r"'caps_b3s.json' = '([0-9A-F]{64})'", up).group(1).lower()
post = open(S + '/docs/install_post_g1.ps1').read()
cloze = re.search(r"\$LONG\s+= '([0-9A-F]{64})'", post).group(1).lower()
import os
t = open(os.environ.get('TEMPLATE', S + '/ptc3s_box.template.sh')).read()       # TEMPLATE=...frozen.sh regenerates the frozen script (a check that the pipeline is unchanged)
WT = os.environ.get('GEN_WT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))       # the work tree the git reads and code_identity.py come from: the checkout this file is in (GEN_WT overrides; the work tree the first versions named has been removed)
ci = open(WT + '/results/8a-g/vast-ptc3s/code_identity.py', newline='').read()
assert 'PYID' not in ci and '\r' not in ci and ci.endswith('\n')
t = t.replace('@@CODE_IDENTITY_PY@@\n', ci)
t = t.replace('@@PKG_PINS@@', '\n'.join(pkg)).replace('@@OVERLAY_PINS@@', '\n'.join(overlay))
t = t.replace('@@CLOZE_SHA@@', cloze).replace('@@CAPS_PY_SHA@@', caps_py).replace('@@CAPS_B3S_SHA@@', caps_b3s)
# PROFILE mode (added 2026-10-14): the profiling harness commit as the coordinator named it, and the sha256 of prof_train.py read from that commit with git (not typed)
# re-pinned 2026-10-14 from 6a870a767c6231fe6c2489b84752ffdafd7824fa to the newest harness commit (E2 scale diagnostics, relative E2 rule, E1-floor text, CPU/bf16 label)
# re-pinned 2026-10-14 (PROF_PLAN=b3sweep) to the commit that adds the accumsweep and accumcmp sections; PROF_SHA in the environment overrides (a check, never used for the committed script)
# re-pinned 2026-10-14 (PROF_PLAN=b3ab) to the commit that adds the unfused, pad64 and nosync variants and the abequiv and abbench sections
# re-pinned 2026-10-14 (PROF_PLAN=b3ab, final) to the commit with the review fixes (arm order, pad64p, mark 6 label, error isolation, half-done setup undo)
PROF_SHA = os.environ.get('PROF_SHA', '75cd5fcc01875bfefccbb8ebde09fde53ebd0490')
assert subprocess.run(['git', '-C', WT, 'cat-file', '-t', PROF_SHA], capture_output=True, text=True).stdout.strip() == 'commit', 'harness commit not in the repo'
blob = subprocess.run(['git', '-C', WT, 'show', PROF_SHA + ':results/8a-g/speedup/prof/prof_train.py'], capture_output=True, check=True).stdout
import hashlib
prof_py = hashlib.sha256(blob).hexdigest()
t = t.replace('@@PROF_SHA@@', PROF_SHA).replace('@@PROF_PY_SHA@@', prof_py)
# PROF_PLAN=b3sweep: the AT-1 code pins. Two sources must agree: the AT10M kit's pin list (at10m_box.sh) and the files of the commit as git has them; the queue file's pin comes from git only
AT_SHA = '6e72a5fae514a343c217c4d95cde37bc3b587c8e'
at10 = open(WT + '/results/8a-g/pc-job-cards/at10m/vast/at10m_box.sh').read()
assert re.search(r'^SRC_SHA=%s ' % AT_SHA, at10, re.M), 'AT10M kit does not pin this commit'
a_caps_py = re.search(r'^CAPS_PY_SHA=([0-9a-f]{64})', at10, re.M).group(1)
a_caps_json = re.search(r'^CAPS_JSON_SHA=([0-9a-f]{64})', at10, re.M).group(1)
a_train0 = re.search(r'^TRAIN0_SHA=([0-9a-f]{64})', at10, re.M).group(1)
blockpins = at10.split('done <<PINS\n')[1].split('\nPINS\n')[0]
at_pins = []
for ln in blockpins.splitlines():
    f, h = ln.split()
    h = {'$CAPS_PY_SHA': a_caps_py, '$CAPS_JSON_SHA': a_caps_json, '$TRAIN0_SHA': a_train0}.get(h, h)
    assert re.fullmatch(r'[0-9a-f]{64}', h), ln
    g = subprocess.run(['git', '-C', WT, 'show', AT_SHA + ':custom_io/' + f], capture_output=True, check=True).stdout
    assert hashlib.sha256(g).hexdigest() == h, ('AT10M kit pin differs from git', f)
    at_pins.append('%s %s' % (f, h))
assert len(at_pins) == 10 and any(x.startswith('g8a/caps_b3g2.json ') for x in at_pins), at_pins
qf = 'queue_local/8aAT-3M-s400-pc.txt'
qb = subprocess.run(['git', '-C', WT, 'show', AT_SHA + ':custom_io/' + qf], capture_output=True, check=True).stdout
at_pins.append('%s %s' % (qf, hashlib.sha256(qb).hexdigest()))
t = t.replace('@@AT_PINS@@', '\n'.join(at_pins)).replace('@@AT_SHA@@', AT_SHA).replace('@@AT_CAPS_SHA@@', a_caps_json)
print('AT pins:', len(at_pins), 'files at', AT_SHA[:10])
# PROF_PLAN=b3ab, stage i4_b3g2_pair: the PC's src-b3g2 = custom_io at B3G2_SHA (74d6e92c75, the code of the G2f runs). Three sources must agree: PINS0 of install_g2fa4.py (the pack's pin list), the files of the
# commit as git has them, and the queue files of the pack (read with git at Q_SHA, the commit that last changed the pack's queue/ and install_g2fa4.py); none of the hashes is typed here
B3G2_SHA = '74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6'
Q_SHA = '758cfcad5bd08befa1a2fa179c8e88a66f2b9f39'
assert subprocess.run(['git', '-C', WT, 'cat-file', '-t', B3G2_SHA], capture_output=True, text=True).stdout.strip() == 'commit', 'B3G2 commit not in the repo'
assert subprocess.run(['git', '-C', WT, 'cat-file', '-t', Q_SHA], capture_output=True, text=True).stdout.strip() == 'commit', 'pack commit not in the repo'
PK = 'results/8a-g/pc-job-cards/g2fa4/'
def gshow(rev, path):
    return subprocess.run(['git', '-C', WT, 'show', rev + ':' + path], capture_output=True, check=True).stdout
inst = gshow(Q_SHA, PK + 'install_g2fa4.py').decode()
pins0 = re.search(r'^PINS0 = \{\n(.*?)^\}', inst, re.M | re.S).group(1)
b3_pins = []
for ln in pins0.splitlines():
    m = re.match(r"\s+'([^']+)': '([0-9a-f]{64})',", ln)
    assert m, ln
    g = gshow(B3G2_SHA, 'custom_io/' + m.group(1))
    assert hashlib.sha256(g).hexdigest() == m.group(2), ('install_g2fa4.py PINS0 differs from git', m.group(1))
    b3_pins.append('%s %s' % (m.group(1), m.group(2)))
assert len(b3_pins) == 8 and any(x.startswith('g8a/caps_b3g2.json ') for x in b3_pins), b3_pins
b3_caps = [x.split()[1] for x in b3_pins if x.startswith('g8a/caps_b3g2.json ')][0]
assert b3_caps == a_caps_json      # the same caps file as the AT-1 code's
def qextract(name):      # the box needs the queue lines only: the MEM line and the g8a line (the comments and the Windows ENV lines are not used on Linux); the full file's hash is recorded
    full = gshow(Q_SHA, PK + 'queue/' + name)
    keep = [l for l in full.decode().splitlines() if re.match(r'# MEM \d+$', l) or l.startswith('g8a: ')]
    assert len([l for l in keep if l.startswith('g8a: ')]) == 1, keep
    return hashlib.sha256(full).hexdigest(), '\n'.join(keep) + '\n'
q4_full, q4_txt = qextract('8aB3G2A4-pc.txt')
q32_full, q32_txt = qextract('8aB3G2A4b32-pc.txt')
assert '--accum B3G2=4 ' in q4_txt and '--accum B3G2=32 ' in q32_txt
b3_qpins = ['8aB3G2A4-pc.txt %s' % hashlib.sha256(q4_txt.encode()).hexdigest(), '8aB3G2A4b32-pc.txt %s' % hashlib.sha256(q32_txt.encode()).hexdigest()]
t = t.replace('@@B3G2_PINS@@', '\n'.join(b3_pins)).replace('@@B3G2_SHA@@', B3G2_SHA).replace('@@B3G2_QPINS@@', '\n'.join(b3_qpins))
t = t.replace('@@B3G2_Q4@@\n', q4_txt).replace('@@B3G2_Q32@@\n', q32_txt)
t = t.replace('@@B3G2_Q4_FULL@@', q4_full).replace('@@B3G2_Q32_FULL@@', q32_full).replace('@@B3G2_Q_SHA@@', Q_SHA)
print('B3G2 pins:', len(b3_pins), 'files at', B3G2_SHA[:10], '; queue extracts', b3_qpins)
assert '@@' not in t
print('PROF_SHA', PROF_SHA, 'prof_train.py sha256', prof_py, len(blob), 'bytes')
out = sys.argv[1]
open(out, 'w', newline='\n').write(t)
print('wrote', out, len(t), 'bytes; caps_py', caps_py, 'caps_b3s', caps_b3s, 'cloze', cloze)
