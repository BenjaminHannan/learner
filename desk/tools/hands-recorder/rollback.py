"""Undo only our package entry change; no app/brain restart, no data deletion."""
from pathlib import Path
import json, os, subprocess
base = Path.home()/'learner-ops/hands-recorder'
status = json.loads(subprocess.check_output([str(base/'recorderctl'),'status'],text=True))
if status['enabled']: raise RuntimeError('Run recorderctl stop first')
p = Path('/Applications/Premonition.app/Contents/Resources/app/package.json')
metadata = json.loads(p.read_text())
if metadata['main'] != 'recorder-entry.js': raise RuntimeError('Entry changed elsewhere; nothing overwritten')
metadata['main'] = 'main.js'
tmp = p.with_name('package.recorder-rollback.json')
tmp.write_text(json.dumps(metadata,indent=2)+'\n');os.replace(tmp,p)
print('Recorder entry removed. Chat was not restarted. Recordings remain local.')
