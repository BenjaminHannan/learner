"""Fill the pin blocks of ptc3s_box.template.sh from the PTC package README (the pinned copy fetched from c2bf1a71c7), install_ptc.ps1 and the PC's own scripts.
Every value is read from a source file, none is typed here; the box script re-checks them against README.md / install_ptc.ps1 at run time as well."""
import re, subprocess, sys
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
ci = open('/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/code_identity.py', newline='').read()
assert 'PYID' not in ci and '\r' not in ci and ci.endswith('\n')
t = t.replace('@@CODE_IDENTITY_PY@@\n', ci)
t = t.replace('@@PKG_PINS@@', '\n'.join(pkg)).replace('@@OVERLAY_PINS@@', '\n'.join(overlay))
t = t.replace('@@CLOZE_SHA@@', cloze).replace('@@CAPS_PY_SHA@@', caps_py).replace('@@CAPS_B3S_SHA@@', caps_b3s)
# PROFILE mode (added 2026-10-14): the profiling harness commit as the coordinator named it, and the sha256 of prof_train.py read from that commit with git (not typed)
# re-pinned 2026-10-14 from 6a870a767c6231fe6c2489b84752ffdafd7824fa to the newest harness commit (E2 scale diagnostics, relative E2 rule, E1-floor text, CPU/bf16 label)
# re-pinned 2026-10-14 (PROF_PLAN=b3sweep) to the commit that adds the accumsweep and accumcmp sections; PROF_SHA in the environment overrides (a check, never used for the committed script)
PROF_SHA = os.environ.get('PROF_SHA', '1d728b99ef7180c567b285b07ede9aac7a46427a')
WT = '/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1'
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
assert '@@' not in t
print('PROF_SHA', PROF_SHA, 'prof_train.py sha256', prof_py, len(blob), 'bytes')
out = sys.argv[1]
open(out, 'w', newline='\n').write(t)
print('wrote', out, len(t), 'bytes; caps_py', caps_py, 'caps_b3s', caps_b3s, 'cloze', cloze)
