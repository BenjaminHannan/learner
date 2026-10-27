"""Package ONLY awake seal files. No network, training, caches or source weights."""
import hashlib
import json
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/sol-compose-20260929'
if __name__=='__main__':
    seal=ART/'SEAL-AWAKE.json';data=json.loads(seal.read_text())
    paths=list(data['sha256'])+[str(seal.relative_to(ROOT))]
    out=ART/'sol_compose_awake_payload.tar.gz'
    if out.exists():raise FileExistsError(out)
    for name,sha in data['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:raise ValueError('SEAL MISMATCH '+name)
    with tarfile.open(out,'x:gz') as archive:
        for name in paths:archive.add(ROOT/name,arcname=name,recursive=False)
    manifest=dict(path=str(out.relative_to(ROOT)),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                  bytes=out.stat().st_size,uncompressed_bytes=sum((ROOT/x).stat().st_size for x in paths),
                  entries=paths,contains_weights=False)
    (ART/'sol_compose_awake_PACKAGE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
