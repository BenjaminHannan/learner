"""Stdlib-only freeze/bind for a NEW exact ordered safety-receipt run."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'sol-stop-ordered-checkpoint-receipt-v1'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def bind(package_path, tuple_path, output):
    package=json.loads(Path(package_path).read_text())
    candidate=json.loads(Path(tuple_path).read_text())
    if package['version']!=VERSION:raise ValueError('wrong receipt package')
    if set(candidate)!={'parent','reader','prefix','provenance'}:raise ValueError('exact four component roles required')
    pins={str(ROOT/p):digest for p,digest in package['source_pins'].items()}
    for path,digest in pins.items():
        if sha(path)!=digest:raise ValueError('source changed '+path)
    for role,item in candidate.items():
        if set(item)!={'path','sha256'} or sha(item['path'])!=item['sha256']:
            raise ValueError('owner-declared actual checkpoint pin mismatch '+role)
        item['path']=str(Path(item['path']).resolve())
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'artifacts/sol-stop-20260929') or output.exists():
        raise ValueError('NEW owned binding path required')
    spec=dict(version=VERSION,probe_seeds=[0,1],dependency_pins=pins,**candidate,
        package_sha256=sha(package_path),tuple_manifest_sha256=sha(tuple_path),
        scope='numeric native-fixed4 checkpoint safety only; no learned-stop acceptance')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:stream.write(json.dumps(spec,indent=2)+'\n')
    return dict(spec_path=str(output),spec_sha256=sha(output))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--tuple',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(bind(a.package,a.tuple,a.out)))
