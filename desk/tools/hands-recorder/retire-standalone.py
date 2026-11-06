"""Remove only the two old recorder app bundles after the Premonition move."""
from pathlib import Path
import json, plistlib, shutil, subprocess, os
base = Path.home()/'learner-ops/hands-recorder'
status = json.loads(subprocess.check_output([str(base/'recorderctl'),'status'],text=True))
if status['enabled']: raise RuntimeError('Stop recording before removing legacy apps')
legacy_job = 'gui/'+str(os.getuid())+'/local.glim.hands-recorder'
if subprocess.run(['launchctl','print',legacy_job],capture_output=True).returncode == 0:
    raise RuntimeError('Legacy launchd job is loaded; stop its exact job first')
removed = []
for name in ['Hands Recorder.app','Hands Recorder Canary.app']:
    p = base/name
    if not p.exists(): continue
    if p.is_symlink() or p.resolve().parent != base.resolve(): raise RuntimeError('Unexpected app path')
    info = plistlib.loads((p/'Contents/Info.plist').read_bytes())
    if not str(info['CFBundleIdentifier']).startswith('local.glim.hands-recorder'): raise RuntimeError('Unexpected bundle identity')
    shutil.rmtree(p)
    removed.append(str(p))
# Exact obsolete files, never recording folders or user data.
for p in [base/'local.glim.hands-recorder.plist',base/'daemon.js',
          Path('/Applications/Premonition.app/Contents/Resources/glim-recorder/capture'),
          Path('/Applications/Premonition.app/Contents/Resources/glim-recorder/canary')]:
    if p.is_symlink(): raise RuntimeError('Unexpected symlink')
    if p.exists(): p.unlink(); removed.append(str(p))
print(json.dumps({'removed':removed,'tccReset':False,'recording':'OFF'}))
