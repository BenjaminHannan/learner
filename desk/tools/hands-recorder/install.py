"""Install the recorder-only role in Premonition. Never restart chat or start capture."""
from pathlib import Path
import datetime, json, shutil, subprocess, os
repo = Path(__file__).resolve().parents[2]
base = Path.home() / 'learner-ops/hands-recorder'
app = Path('/Applications/Premonition.app/Contents/Resources/app')
resources = app.parent
base.mkdir(parents=True, exist_ok=True)
os.chmod(base, 0o700)
# Preserve the installed app's exact package manifest; never copy a working main.js.
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
rollback = base / 'rollback' / stamp
rollback.mkdir(parents=True)
package = app / 'package.json'
shutil.copy2(package, rollback / 'package.json')
metadata = json.loads(package.read_text())
if metadata['main'] not in ('main.js', 'recorder-entry.js'):
    raise RuntimeError('Unexpected app entry; stop rather than replace it')
helper = resources / 'glim-recorder'
helper.mkdir(exist_ok=True)
for name, source in [('capture', 'recorder.swift'), ('canary', 'secure-canary.swift')]:
    target = helper / (name + '.dylib')
    temporary = helper / (name + '.new.dylib')
    subprocess.run(['swiftc', '-O', '-target', 'arm64-apple-macos13.0', '-emit-library', '-module-name', 'Glim_' + name, str(repo / 'helper/hands-toy' / source), '-o', str(temporary)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(temporary)], check=True)
    os.replace(temporary, target)
subprocess.run(['clang++', '-arch', 'arm64', '-std=c++17', '-bundle', '-undefined', 'dynamic_lookup', '-I/opt/homebrew/include/node', str(repo / 'helper/hands-toy/native-bridge.cc'), '-o', str(helper / 'native-bridge.node')], check=True)
for rel in ['recorder-entry.js', 'src/hands-toy/premonition-host.js', 'src/hands-toy/scratch-benchmark.js', 'src/hands-toy/recorder.js', 'src/hands-toy/retention.js']:
    destination = app / rel
    if destination.exists():
        old = rollback / rel
        old.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, old)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / rel, destination)
metadata['main'] = 'recorder-entry.js'
temporary = app / 'package.recorder-new.json'
temporary.write_text(json.dumps(metadata, indent=2) + '\n')
os.replace(temporary, package)
for name in ['control.js', 'recorderctl', 'verify-canary.js', 'README.md', 'rollback.py']:
    shutil.copy2(Path(__file__).parent / name, base / name)
(base / 'recorderctl').chmod(0o700)
(base / 'state.json').write_text('{"enabled":false}\n')
(base / 'INSTALL.json').write_text(json.dumps({'host':'Premonition','bundleId':'com.electron.premonition-desk','rollback':str(rollback),'recordingEnabled':False}, indent=2))
print(json.dumps({'installed':str(app),'rollback':str(rollback),'recording':'OFF','chatRestarted':False}))
