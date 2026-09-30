#!/usr/bin/env python3
"""Exact bounded read-only PC artifact copies to the existing Mac publisher.

No model/tensor imports, remote writes, directory collection, cleanup, credentials
or environment/argument dumps. All four source files are statted and budgeted
before any contents are hashed or copied. Oversize originals stay untouched.
"""
import datetime
import hashlib
import json
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time

SPEC = {'schema': 'sol.cloud.bridge-weights-recovery.spec.v1', 'created_utc': '2026-09-30T09:43:15.942487+00:00', 'status': 'held until fit process conflict is safe; not queued', 'source_metadata': {'inventory_path': 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/recovered-v3-small/cloud-recovery/SOURCE-MANIFEST-AFTER.json', 'inventory_sha256': '909fec15bbd3d5a5ee94eb07c6dbcfdf569d8caf8c9f08ac7a9fc00d20c8cef7', 'binding_path': 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/BINDING-v3.json', 'binding_sha256': 'e1c2e410d5e71e1b605706f9cf872b9f0b1005b8d15c06f2bc7049cb60b448a7', 'candidate_manifest_path': 'artifacts/sol-cloud-coordinator-20260930/integration/fixture-night-v1/recovered-v3-small/cloud-recovery/copied/artifacts/sol-cloud-night-20260930/run-v3/candidate-manifest.json', 'candidate_manifest_sha256': 'd494990bc8526750ac65733354e1fccb79ef0443ec586e788e306e93f05657a9'}, 'expected_originals': [{'role': 'candidate-parent', 'path': 'C:/Users/benja/sol-cloud-fixture-night-v3/artifacts/sol-cloud-night-20260930/run-v3/candidate-parent.pt', 'metadata_path': 'C:\\Users\\benja\\sol-cloud-fixture-night-v3\\artifacts\\sol-cloud-night-20260930\\run-v3\\candidate-parent.pt', 'sha256': '5cddc77e9068f0e8336a8f65bc079c3747c23d3137596c77317508d04d80a485', 'bytes': 36087479, 'local_name': 'candidate-parent.pt'}, {'role': 'candidate-English', 'path': 'C:/Users/benja/sol-cloud-fixture-night-v3/artifacts/sol-cloud-night-20260930/run-v3/candidate-English.pt', 'metadata_path': 'C:\\Users\\benja\\sol-cloud-fixture-night-v3\\artifacts\\sol-cloud-night-20260930\\run-v3\\candidate-English.pt', 'sha256': '0dca989339b758e51a773548300dada8c00f128901427d71fef671d570143967', 'bytes': 309269, 'local_name': 'candidate-English.pt'}, {'role': 'night-resume', 'path': 'C:/Users/benja/sol-cloud-fixture-night-v3/artifacts/sol-cloud-night-20260930/run-v3/night-resume.pt', 'metadata_path': 'C:\\Users\\benja\\sol-cloud-fixture-night-v3\\artifacts\\sol-cloud-night-20260930\\run-v3\\night-resume.pt', 'sha256': '6be188a0cab8dc17a08936849123d7aa77cd80aaf7edb44830a283e75d5bab5e', 'bytes': 107705303, 'local_name': 'night-resume.pt'}, {'role': 'source-parent', 'path': 'C:/Users/benja/sol-translator-ordered-v10r2/artifacts/sol-translator-20260929/ground-ordered-v10-s0-loop/parent-s0.pt', 'metadata_path': 'C:\\Users\\benja\\sol-translator-ordered-v10r2\\artifacts\\sol-translator-20260929\\ground-ordered-v10-s0-loop\\parent-s0.pt', 'sha256': 'e7aef267c0ba32aec41f01054d019317b6025e3d29b47de88c31e136a598d925', 'bytes': None, 'local_name': 'source-parent.pt', 'size_status': 'Unknown; read-only all-file stat before any content hash/copy'}], 'per_file_cap_bytes': 134217728, 'total_cap_bytes': 268435456, 'part_bytes': 4194304, 'known_candidate_bytes': 144102051, 'source_parent_size_guessed': False, 'mac_python': '/usr/bin/python3', 'mac_version': [3, 9, 6], 'pc_python': 'C:/Users/benja/lis300/venv/Scripts/python.exe', 'pc_version': [3, 10, 9], 'watcher_publisher_root': '/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27', 'output_relative': 'artifacts/sol-cloud-bridge-weights-recovery-20260930/collected-v1', 'pc_writes': 0, 'source_deletions': 0, 'model_calls': 0, 'optimizer_updates': 0, 'hold_policy': 'Integrator routes only after fit process conflict safe; copies only through existing authorized watcher', 'scope': 'Exactly3new bridge weights plus original source parent, regular files only, no PC archives/model/corpus/directory collections'}

PER_FILE_CAP = 128 * 1024**2
TOTAL_CAP = 256 * 1024**2
PART_BYTES = 4 * 1024**2
MAC_RETAINED_FLOOR = 1024**3
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=15',
       '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2', 'benspc',
       r'C:\Users\benja\lis300\venv\Scripts\python.exe -B -X utf8 -']
PROTECTED = ('/uncle-questions/', 'readpanel320', 'dev100', 'stop88',
             '/blind/', '/sealed-panels/', '/sealedquestions/')


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_hash(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def write_new(path, payload):
    with pathlib.Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def validate_pins(pins):
    if not isinstance(pins, list) or len(pins) != 4:
        raise ValueError('Exactly four frozen bridge originals required')
    expected = [(pin['path'], pin['local_name']) for pin in SPEC['expected_originals']]
    roles = ['candidate-parent', 'candidate-English', 'night-resume', 'source-parent']
    if [pin.get('role') for pin in pins] != roles:
        raise ValueError('Exact candidate/English/resume/source-parent roles required')
    for pin, (path, name) in zip(pins, expected):
        if pin['path'] != path or pin['local_name'] != name or pin['sha256'] != SPEC['expected_originals'][roles.index(pin['role'])]['sha256']:
            raise ValueError('Frozen original path or local filename changed')
        if not isinstance(pin['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
            raise ValueError('Expected original SHA256 required')
        unknown_source_size = pin['role'] == 'source-parent' and pin.get('bytes') is None
        if not unknown_source_size and (type(pin.get('bytes')) is not int or not 0 < pin['bytes'] <= PER_FILE_CAP):
            raise ValueError('Pinned byte count within128MiB required')
        if sum(p['bytes'] or 0 for p in pins) > TOTAL_CAP:
            raise ValueError('Pinned aggregate above256MiB refused')
        if any(word in pin['path'].lower() for word in PROTECTED):
            raise ValueError('Protected path refused before any source action')


def validate_records(records, hashes_required):
    pins = SPEC['expected_originals']
    if not isinstance(records, list) or len(records) != len(pins):
        raise ValueError('Exact complete source record set required')
    total = 0
    for pin, actual in zip(pins, records):
        if actual.get('path') != pin['path']:
            raise ValueError('Source record path changed')
        if (type(actual.get('bytes')) is not int or not 0 < actual['bytes'] <= PER_FILE_CAP
                or (pin['bytes'] is not None and actual['bytes'] != pin['bytes'])):
            raise ValueError('Original missing/empty/above128MiB cap')
        if type(actual.get('mtime_ns')) is not int:
            raise ValueError('Original mtime required')
        if hashes_required and actual.get('sha256') != pin['sha256']:
            raise ValueError('Original source hash mismatch')
        total += actual['bytes']
    if total > TOTAL_CAP:
        raise ValueError('Original aggregate above256MiB cap')
    return total


def remote_probe_script():
    # This program creates nothing and opens only frozen regular source files.
    return '''import hashlib,json,pathlib,platform,shutil,sys
pins = ''' + repr(SPEC['expected_originals']) + '''
record = dict(runtime=dict(platform=platform.system(),python=list(sys.version_info[:3]),executable=sys.executable),records=[],read_only=True)
def emit(status):
    record['status']=status
    print(json.dumps(record),flush=True)
def main():
    if sys.platform!='win32' or sys.version_info[:3]!=(3,10,9) or sys.flags.optimize:
        emit('runtime-refused');return
    executable=str(pathlib.Path(sys.executable).resolve()).replace('\\\\','/').lower()
    if executable!='c:/users/benja/lis300/venv/scripts/python.exe':
        emit('executable-refused');return
    record['disk_free_bytes']=shutil.disk_usage('C:/').free
    if record['disk_free_bytes']<1073741824:
        emit('disk-reserve-refused');return
    paths=[]
    for pin in pins:
        p=pathlib.Path(pin['path'])
        if str(p.resolve()).replace('\\\\','/').lower()!=pin['path'].lower():
            record['records'].append(dict(path=pin['path'],error_type='ResolvedPathChanged'));continue
        try:
            if p.is_symlink() or not p.is_file():
                record['records'].append(dict(path=pin['path'],error_type='NotRegularFile'));continue
            stat=p.stat()
            paths.append((p,pin,stat))
            record['records'].append(dict(path=pin['path'],bytes=stat.st_size,mtime_ns=stat.st_mtime_ns))
        except Exception as error:
            record['records'].append(dict(path=pin['path'],error_type=type(error).__name__))
    # No file content reads before this all-file stat/budget decision.
    if len(paths)!=len(pins):emit('stat-refused');return
    if any(not 0<r['bytes']<=134217728 or (pin['bytes'] is not None and r['bytes']!=pin['bytes']) for pin,r in zip(pins,record['records'])) or sum(r['bytes'] for r in record['records'])>268435456:
        emit('budget-refused');return
    for (p,pin,before),r in zip(paths,record['records']):
        h=hashlib.sha256()
        try:
            with p.open('rb') as f:
                for block in iter(lambda:f.read(1048576),b''):h.update(block)
            after=p.stat()
        except Exception as error:
            r['error_type']=type(error).__name__;emit('hash-read-refused');return
        r['sha256']=h.hexdigest()
        if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns:
            emit('source-changed-during-hash');return
        if r['sha256']!=pin['sha256']:emit('hash-refused');return
    emit('verified')
main()
'''


def bounded_timeout(deadline, cap):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Declared collection wall budget exhausted')
    return min(cap, remaining)


def probe_originals(deadline):
    result = subprocess.run(SSH, input=remote_probe_script(), text=True,
                            encoding='utf-8', capture_output=True,
                            timeout=bounded_timeout(deadline, 90), check=True)
    if len(result.stdout) > 32 * 1024:
        raise ValueError('Bounded probe metadata exceeded')
    return json.loads(result.stdout)


def remote_copy_script(pin, original):
    # Binary stdout only, bounded by the already verified exact source size.
    # Even a concurrently growing source cannot exceed its admitted byte count.
    return '''import hashlib,pathlib,sys
pin = ''' + repr(pin) + '''
original = ''' + repr(original) + '''
if sys.flags.optimize:raise RuntimeError('Unoptimized verified runtime required')
assert sys.platform=='win32' and sys.version_info[:3]==(3,10,9)
assert str(pathlib.Path(sys.executable).resolve()).replace('\\\\','/').lower()=='c:/users/benja/lis300/venv/scripts/python.exe'
p=pathlib.Path(pin['path'])
assert str(p.resolve()).replace('\\\\','/').lower()==pin['path'].lower()
assert p.is_file() and not p.is_symlink()
before=p.stat()
assert before.st_size==original['bytes'] and before.st_mtime_ns==original['mtime_ns']
assert 0<before.st_size<=134217728
remaining=before.st_size
h=hashlib.sha256()
with p.open('rb') as f:
    while remaining:
        block=f.read(min(1048576,remaining))
        assert block,'Source shortened during bounded copy'
        remaining-=len(block)
        h.update(block)
        sys.stdout.buffer.write(block)
sys.stdout.buffer.flush()
after=p.stat()
assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
assert h.hexdigest()==pin['sha256']
'''


def copy_original(pin, original, target, deadline):
    with pathlib.Path(target).open('xb') as stream:
        result = subprocess.run(SSH, input=remote_copy_script(pin, original).encode('utf-8'),
            stdout=stream, stderr=subprocess.PIPE,
            timeout=bounded_timeout(deadline, 60), check=False)
        stream.flush()
    if result.returncode != 0:
        # Failure keeps the local partial bytes; neither stderr nor argv prints.
        raise subprocess.CalledProcessError(result.returncode, 'bounded-read-only-copy')
    size = pathlib.Path(target).stat().st_size
    if size != original['bytes'] or size > PER_FILE_CAP:
        raise ValueError('Copied original size mismatch')
    digest = file_hash(target)
    if digest != pin['sha256']:
        raise ValueError('Copied original hash mismatch')
    return dict(source_path=pin['path'], local_name=pin['local_name'],
                bytes=size, sha256=digest)


def publication_parts(source, target_dir):
    parts = []
    digest = hashlib.sha256()
    total = 0
    with pathlib.Path(source).open('rb') as stream:
        index = 0
        for block in iter(lambda: stream.read(PART_BYTES), b''):
            digest.update(block)
            total += len(block)
            if total > PER_FILE_CAP:
                raise ValueError('Local file exceeded sealed publication cap')
            name = pathlib.Path(source).name + '.part%03d' % index
            with (pathlib.Path(target_dir) / name).open('xb') as target:
                target.write(block)
                target.flush()
            parts.append(dict(name=name, bytes=len(block),
                              sha256=hashlib.sha256(block).hexdigest()))
            index += 1
    return dict(bytes=total, sha256=digest.hexdigest(), ordered_parts=parts)


def main():
    started = time.monotonic()
    deadline = started + 600
    out = None
    probe_status = None
    stage = 'native Mac runtime and frozen pin preflight'
    try:
        if platform.system() != 'Darwin' or sys.version_info[:3] != (3, 9, 6):
            raise RuntimeError('Verified native Mac3.9.6 required')
        root = pathlib.Path.cwd().resolve()
        if root != pathlib.Path(SPEC['watcher_publisher_root']).resolve():
            raise ValueError('Verified watcher publisher cwd required')
        validate_pins(SPEC['expected_originals'])
        if shutil.disk_usage(root).free < MAC_RETAINED_FLOOR + 2 * TOTAL_CAP + 1024**2:
            raise RuntimeError('Mac reserve plus copied originals/publication parts required')
        fresh_out = root / SPEC['output_relative']
        if fresh_out.exists():
            raise FileExistsError('Preserve prior collection; fresh queue/output identity required')
        fresh_out.mkdir(parents=True, exist_ok=False)
        out = fresh_out
        raw_dir, publication = out / 'raw', out / 'publication'
        raw_dir.mkdir()
        publication.mkdir()
        write_new(publication / 'LAUNCH.json', dict(started_utc=utc_now(),
            native_runtime=dict(invoked='/usr/bin/python3', reported_executable=sys.executable,
                                resolved_executable=str(pathlib.Path(sys.executable).resolve()),
                                platform=platform.system(), python=list(sys.version_info[:3])),
            metadata_pin=SPEC['source_metadata'], publisher_root=str(root),
            collection_only=True, model_imports=0, optimizer_updates=0, pc_writes=0,
            source_deletions=0, full_arguments_or_environment_logged=False))

        stage = 'stat all exact originals and before-copy SHA verification'
        before_probe = probe_originals(deadline)
        write_new(publication / 'SOURCE-BEFORE.json', before_probe)
        probe_status = before_probe.get('status')
        if before_probe.get('status') != 'verified':
            raise RuntimeError('Original probe refused; measured metadata preserved')
        before = before_probe['records']
        total = validate_records(before, hashes_required=True)
        if shutil.disk_usage(root).free < MAC_RETAINED_FLOOR + 2 * total + 1024**2:
            raise RuntimeError('Fresh Mac reserve for actual bounded sizes required')

        stage = 'exact named copies and local SHA verification'
        local = []
        for pin, original in zip(SPEC['expected_originals'], before):
            target = raw_dir / pin['local_name']
            local.append(copy_original(pin, original, target, deadline))
        write_new(publication / 'LOCAL-COPIES.json', local)

        stage = 'after-copy original SHA and metadata preservation'
        after_probe = probe_originals(deadline)
        write_new(publication / 'SOURCE-AFTER.json', after_probe)
        if after_probe.get('status') != 'verified' or after_probe['records'] != before:
            raise ValueError('PC originals changed; retain evidence and refuse completion')

        stage = 'bounded Mac-only publication parts'
        published = []
        for pin, copied in zip(SPEC['expected_originals'], local):
            bounded_timeout(deadline, 60)
            parts = publication_parts(raw_dir / pin['local_name'], publication)
            if parts['bytes'] != copied['bytes'] or parts['sha256'] != copied['sha256']:
                raise ValueError('Publication part source mismatch')
            published.append(dict(original_path=pin['path'], local_name=pin['local_name'], **parts))
        manifest = dict(schema='sol.cloud.bridge-weights-recovery.parts.v1',
            completed_utc=utc_now(), originals=published, total_original_bytes=total,
            per_file_cap_bytes=PER_FILE_CAP, total_cap_bytes=TOTAL_CAP,
            part_bytes=PART_BYTES, before_local_after_sha_checks=12,
            pc_originals_retained=True, pc_writes=0, source_deletions=0,
            model_imports=0, model_calls=0, optimizer_updates=0,
            training_material=False,
            reassembly='For each original concatenate ordered parts; verify each part and full bytes/SHA before parsing')
        write_new(publication / 'PARTS-MANIFEST.json', manifest)
        summary = dict(completed_utc=utc_now(), wall_seconds=time.monotonic()-started,
            status='verified', files_copied=len(local), total_original_bytes=total,
            original_pins=SPEC['expected_originals'], local_records=local,
            publication_manifest_sha256=file_hash(publication / 'PARTS-MANIFEST.json'),
            pc_originals_retained=True, pc_writes=0, source_deletions=0,
            model_calls=0, optimizer_updates=0, stage_proof_status='NOT SHOWN')
        write_new(publication / 'COLLECTION.json', summary)
        print(json.dumps(summary, sort_keys=True), flush=True)
        return 0
    except Exception as error:
        # subprocess exceptions contain full arguments; never print their text,
        # stdout/stderr or environment. Only exact stage and error class escape.
        failure = dict(failed_utc=utc_now(), stage=stage,
            error_type=type(error).__name__, wall_seconds=time.monotonic()-started,
            pc_writes=0, source_deletions=0, model_calls=0, optimizer_updates=0,
            retry_policy='Preserve partial output and failure; additive queue required')
        if probe_status in ('runtime-refused', 'executable-refused', 'disk-reserve-refused', 'stat-refused',
                            'budget-refused', 'hash-read-refused',
                            'source-changed-during-hash', 'hash-refused', 'verified'):
            failure['original_probe_status'] = probe_status
        if isinstance(error, subprocess.CalledProcessError):
            failure['subprocess_returncode'] = error.returncode
        if out is not None and out.is_dir() and (out / 'publication').is_dir():
            write_new(out / 'publication' / 'FAILURE.json', failure)
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
