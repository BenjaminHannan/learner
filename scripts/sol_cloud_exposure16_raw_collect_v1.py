#!/usr/bin/env python3
"""Read-only, watcher-bound byte recovery; diagnostic evidence is never training."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import select
import shutil
import subprocess
import sys
import time

W = Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q = Path('/Users/ben-hannan/premonition-watch/queue')
PC = 'C:/Users/benja/sol-cloud-exposure16-r5'
OWN = 'artifacts/sol-cloud-exposure16-raw-recovery-20260930'
EXPOSURE = 'artifacts/sol-cloud-exposure16-20260930/r5'
SEAL = 'd8a50948c5c5831928fd3d68e2ed87f8620bbf3af0b5dbfa8efe27afde08a018'
PART = 4 * 1024 ** 2
RAW_CAP, FRAME_CAP, FLOOR = 8 * 1024 ** 2, 16 * 1024 ** 2, 1024 ** 3
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=5',
       '-o', 'ServerAliveCountMax=2', 'benspc', r'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -B -']
NAMES = frozenset(['TRAIN-RAW.jsonl', 'DIAGNOSTIC-RAW.jsonl', 'INPUT-FRAMES.json'] +
                  ['frames-%06d.pt' % n for n in (0, 200, 400, 800)])


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 ** 2), b''):
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + '\n')


def relative_path(value):
    if not isinstance(value, str):
        raise ValueError('relative path required')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or ':' in value or '\\' in value:
        raise ValueError('safe relative path required')
    return p


def selected_records(manifest, seed, source_job):
    if (manifest.get('seed') != seed or manifest.get('job') != source_job
            or type(manifest.get('returncode')) is not int
            or manifest.get('actual_user_day') is not False or manifest.get('activated') is not False
            or not isinstance(manifest.get('records'), list)):
        raise ValueError('closed actual watcher manifest required')
    prefix = EXPOSURE + '/runs/s%d/' % seed
    seen, chosen = set(), []
    for record in manifest['records']:
        p = relative_path(record['relative'])
        if (not record['relative'].startswith(prefix) or record['relative'] in seen
                or type(record.get('bytes')) is not int or record['bytes'] < 0
                or not re.fullmatch('[0-9a-f]{64}', record.get('sha256', ''))):
            raise ValueError('manifest path/size/hash identity differs')
        seen.add(record['relative'])
        if p.parent.as_posix() == prefix.rstrip('/') and p.name in NAMES:
            chosen.append({k: record[k] for k in ('relative', 'bytes', 'sha256')})
    raw = sum(r['bytes'] for r in chosen if not r['relative'].endswith('.pt'))
    frames = sum(r['bytes'] for r in chosen if r['relative'].endswith('.pt'))
    if not chosen or raw > RAW_CAP or frames > FRAME_CAP:
        raise ValueError('fixed raw/frame recovery allowances exceeded or no saved evidence')
    return sorted(chosen, key=lambda r: r['relative'])


def remote_header(records):
    return '''import hashlib,json,pathlib,sys
assert sys.version_info[:3]==(3,10,9)
root=pathlib.Path(%r).resolve()
records=%r
def inspect(record):
 p=root/record['relative']
 assert not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(root)
 before=p.stat();assert before.st_size==record['bytes']
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 after=p.stat()
 assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
 assert h.hexdigest()==record['sha256']
 return dict(record,mtime_ns=after.st_mtime_ns)
''' % (PC, records)


def probe(records):
    source = remote_header(records) + 'print(json.dumps([inspect(r) for r in records]),flush=True)\n'
    result = subprocess.run(SSH, input=source.encode('utf-8'), capture_output=True, timeout=90)
    if result.returncode or len(result.stdout) > 32768:
        raise RuntimeError('bounded source hash probe failed; diagnostics suppressed')
    actual = json.loads(result.stdout.decode('utf-8'))
    if len(actual) != len(records) or any({k: a[k] for k in r} != r for a, r in zip(actual, records)):
        raise ValueError('source probe differs from pinned manifest')
    return actual


def stream_parts(command, source, record, out, timeout=120):
    """Strict binary stdout, exact extent,4MiB parts, no assembled second copy."""
    started, extent, parts = time.monotonic(), 0, []
    whole, piece, piece_hash, piece_size = hashlib.sha256(), None, None, 0
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        process.stdin.write(source.encode('utf-8')); process.stdin.close()
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                raise TimeoutError('binary read deadline; preserve partial parts')
            block = os.read(process.stdout.fileno(), 65536)
            if not block:
                break
            if extent + len(block) > record['bytes']:
                raise ValueError('remote binary stream exceeds pinned extent')
            whole.update(block); extent += len(block)
            while block:
                if piece is None:
                    name = PurePosixPath(record['relative']).name + '.part%03d' % len(parts)
                    piece = (out / name).open('xb'); piece_hash = hashlib.sha256(); piece_size = 0
                chunk, block = block[:PART-piece_size], block[PART-piece_size:]
                if shutil.disk_usage(out).free < FLOOR + len(chunk):
                    raise RuntimeError('Mac1GiB reserve; preserve partial parts')
                piece.write(chunk); piece_hash.update(chunk); piece_size += len(chunk)
                if piece_size == PART:
                    piece.close(); parts.append({'name':name,'bytes':piece_size,'sha256':piece_hash.hexdigest()}); piece = None
        if piece is not None:
            piece.close(); parts.append({'name':name,'bytes':piece_size,'sha256':piece_hash.hexdigest()}); piece = None
        if process.wait(timeout=max(0.1, timeout-(time.monotonic()-started))) != 0:
            raise RuntimeError('source binary stream failed; diagnostics suppressed')
        if extent != record['bytes'] or whole.hexdigest() != record['sha256']:
            raise ValueError('local recovered extent/hash differs')
        # Recount saved parts independently of hashes accumulated while writing.
        h = hashlib.sha256()
        for part in parts:
            p = out / part['name']
            if p.stat().st_size != part['bytes'] or sha(p) != part['sha256']:
                raise ValueError('saved part extent/hash differs')
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
        if h.hexdigest() != record['sha256']:
            raise ValueError('saved ordered-parts full hash differs')
        return dict(record, ordered_parts=parts, training_eligible=False, evidence_only=True)
    finally:
        if piece is not None:piece.close()
        if process.poll() is None:process.kill();process.wait(timeout=5)
        process.stdout.close()


def copy_record(record, out):
    source = remote_header([record]) + '''r=records[0];before=inspect(r)
h=hashlib.sha256()
with (root/r['relative']).open('rb') as f:
 for block in iter(lambda:f.read(65536),b''):
  h.update(block);sys.stdout.buffer.write(block)
sys.stdout.buffer.flush()
assert h.hexdigest()==r['sha256'] and inspect(r)==before
'''
    return stream_parts(SSH, source, record, out)


def pinned_json(record):
    p = relative_path(record['path'])
    # Only collector spec and fixed Mac execution receipts can be opened.
    if not (p.as_posix().startswith(OWN + '/') or p.as_posix().startswith(EXPOSURE + '/mac-launch-v1/')):
        raise ValueError('collector metadata namespace required before file access')
    path = W / p
    if sha(path) != record['sha256']:
        raise ValueError('immutable watcher receipt pin differs')
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    global PC
    parser=argparse.ArgumentParser()
    parser.add_argument('--spec',required=True);parser.add_argument('--spec-sha256',required=True)
    args=parser.parse_args();out=None;started=time.monotonic()
    try:
        if platform.system()!='Darwin' or sys.version_info[:3]!=(3,9,6) or Path.cwd().resolve()!=W.resolve():
            raise RuntimeError('actual native Mac3.9.6 watcher root required')
        spec=pinned_json({'path':args.spec,'sha256':args.spec_sha256})
        if (spec.get('schema')!='sol.cloud.exposure16.raw-collection-spec.v1'
                or spec.get('seed') not in (0,1) or type(spec['seed']) is not int
                or spec.get('exposure_seal_sha256')!=SEAL or spec.get('training_eligible') is not False):
            raise ValueError('exact r5 diagnostic recovery specification required')
        seed,job=spec['seed'],spec['job'];source_job=spec['source_job']
        if (not re.fullmatch('sol-cloud-exposure16-raw-[a-z0-9-]+',job)
                or not re.fullmatch('sol-cloud-exposure16-r5-s%d-r[0-9]+-benspc' % seed,source_job)):
            raise ValueError('fixed experiment watcher job names required')
        PC=spec['pc_root']
        if not re.fullmatch('C:/Users/benja/sol-cloud-exposure16-r5-r[0-9]+',PC):
            raise ValueError('fixed experiment PC root required')
        if not (Q/(job+'.running')).is_file() or (Q/(job+'.exit')).exists():
            raise ValueError('actual collector watcher running claim required')
        copied=(Q/(job+'.md')).read_bytes()
        tracked=subprocess.check_output(['git','show','origin/main:handoff/queue/'+job+'.md'],timeout=15)
        if copied!=tracked:raise ValueError('copied collector queue differs from origin/main')
        exit_path=Q/(source_job+'.exit');queue_path=Q/(source_job+'.md')
        if (Q/(source_job+'.running')).exists() or sha(exit_path)!=spec['source_watcher_exit_sha256']:
            raise ValueError('source watcher closure differs')
        exit_text=exit_path.read_text().strip()
        if not re.fullmatch('rc=-?[0-9]+',exit_text):raise ValueError('actual watcher rc protocol required')
        if sha(queue_path)!=spec['source_copied_queue_sha256']:
            raise ValueError('source copied queue differs from pinned immutable receipt')
        manifest_path=relative_path(spec['manifest']['path'])
        if manifest_path.name!='PC-FINAL-MANIFEST.json':
            raise ValueError('actual final manifest receipt required')
        manifest=pinned_json(spec['manifest'])
        watcher=pinned_json(spec['watcher_receipt'])
        if (relative_path(spec['watcher_receipt']['path']).parent!=manifest_path.parent
                or relative_path(spec['watcher_receipt']['path']).name!='PC-SSH-EXIT.json'
                or watcher.get('schema')!='sol.cloud.exposure16.ssh-exit.v2'
                or watcher.get('spawned') is not True or watcher.get('timed_out') is not False
                or type(watcher.get('returncode')) is not int or watcher['returncode']!=manifest.get('returncode')):
            raise ValueError('immutable actual watcher exit receipt differs')
        stdout=next((r for r in watcher.get('streams',[]) if r.get('name')=='PC-stdout.log'),None)
        if stdout is None or type(stdout.get('bytes')) is not int or not 0<stdout['bytes']<=256*1024:
            raise ValueError('bounded immutable watcher stdout receipt required')
        stdout_path=W/manifest_path.parent/'PC-stdout.log'
        if stdout_path.stat().st_size!=stdout['bytes'] or sha(stdout_path)!=stdout['sha256']:
            raise ValueError('saved watcher stdout bytes differ')
        if json.loads(stdout_path.read_text(encoding='utf-8').splitlines()[-1])!=manifest:
            raise ValueError('manifest differs from exact saved watcher output')
        records=selected_records(manifest,seed,source_job)
        if shutil.disk_usage(W).free<FLOOR+sum(r['bytes'] for r in records):
            raise RuntimeError('Mac reserve plus exact recovery bytes unavailable')
        out=W/OWN/('collected-'+job);out.mkdir(parents=True,exist_ok=False)
        write_new(out/'LAUNCH.json',{'seed':seed,'job':job,'source_job':source_job,'spec_sha256':args.spec_sha256,
                  'manifest_sha256':spec['manifest']['sha256'],'actual_user_day':False,'training_eligible':False,'model_calls':0,'optimizer_updates':0})
        before=probe(records);write_new(out/'SOURCE-BEFORE.json',before)
        local=[copy_record(r,out) for r in records]
        after=probe(records);write_new(out/'SOURCE-AFTER.json',after)
        if before!=after:raise ValueError('PC originals changed during recovery')
        receipt={'schema':'sol.cloud.exposure16.raw-collection-receipt.v1','seed':seed,'job':job,
                 'manifest_sha256':spec['manifest']['sha256'],'spec_sha256':args.spec_sha256,'records':local,
                 'source_before':before,'source_after':after,'PC_originals_preserved':True,'PC_writes':0,
                 'PC_archive_created':False,'source_deletions':0,'actual_user_day':False,'training_eligible':False,
                 'all_generated_diagnostics_never_training_material':True,'model_calls':0,'optimizer_updates':0,
                 'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-started}
        write_new(out/'COLLECTION-RECEIPT.json',receipt)
        print(json.dumps({'job':job,'files_copied':len(local),'bytes':sum(r['bytes'] for r in local),'training_eligible':False}),flush=True)
        return 0
    except Exception as error:
        failure={'status':'preserved recovery failure','exception_type':type(error).__name__,'raw_diagnostics_suppressed':True,
                 'PC_writes':0,'source_deletions':0,'model_calls':0,'optimizer_updates':0,'training_eligible':False}
        if out is not None:write_new(out/'FAILURE.json',failure)
        print(json.dumps(failure),flush=True);return 1


if __name__=='__main__':sys.exit(main())
