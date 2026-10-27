"""Collect three immutable numeric artifacts; never load a model or tensor."""

import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
import time

WATCHER_ROOT = pathlib.Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
OUTPUT_RELATIVE = pathlib.Path('artifacts/sol-cloud-coordinator-20260930/integration/static-night-raw-collection-v2/collected-v2')
OLD_SPEC = 'artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/STATIC-NIGHT-RAW-COLLECTION-SPEC-v1.json'
OLD_SPEC_SHA256 = 'c9a5e0e3f48200943fa2af4f312c0c560f0fe0ac8ad90e64a140093632557e5d'
SOURCE_PREFIX = 'C:/Users/benja/sol-compose-night-v2-s0/artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1/night-static-v2-s0/actual/'
EXPECTED_PINS = [
    {'path': SOURCE_PREFIX + 'receipt.json', 'sha256': 'd154ce22538b53dc0df7304529640712e4aac23e1e1a32134685f63c5c8dbb3f'},
    {'path': SOURCE_PREFIX + 'raw-probe-0.pt', 'sha256': 'e2e4c9105285604057b8bcb7a30e910706deee551550723f52d67d6746bcc060'},
    {'path': SOURCE_PREFIX + 'raw-probe-1.pt', 'sha256': 'f6e85a2aa52bd232b426d46bccee7037c152f3c43b1c49c176a917d578af73aa'},
]
SOURCE_CAP = 64 * 1024**2
LOCAL_FREE_FLOOR = 384 * 1024**2
PART_BYTES = 4 * 1024**2
SSH = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
       '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2', 'benspc',
       r'C:\Users\benja\lis300\venv\Scripts\python.exe -X utf8 -']


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


def check_source_manifest(records):
    assert isinstance(records, list) and len(records) == 3, 'Exactly three original source files required'
    total = 0
    for expected, actual in zip(EXPECTED_PINS, records):
        assert actual['path'] == expected['path'], 'Source path changed'
        assert actual['sha256'] == expected['sha256'], 'Original source hash mismatch'
        assert isinstance(actual['bytes'], int) and actual['bytes'] > 0, 'Invalid source size'
        assert isinstance(actual['mtime_ns'], int), 'Missing original modification time'
        total += actual['bytes']
    assert total <= SOURCE_CAP, '64 MiB original-source collection cap'
    return total


def remote_probe_script():
    # This script reads only the three exact pinned paths; it creates nothing.
    return '''import hashlib,json,pathlib
pins = ''' + repr(EXPECTED_PINS) + '''
records = []
for pin in pins:
    p = pathlib.Path(pin['path'])
    assert p.is_file() and not p.is_symlink(), 'Original regular file required: ' + str(p)
    before = p.stat()
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    after = p.stat()
    assert before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns, 'Source changed during hashing'
    assert h.hexdigest() == pin['sha256'], 'Original source hash mismatch: ' + str(p)
    records.append(dict(path=pin['path'],sha256=h.hexdigest(),bytes=after.st_size,mtime_ns=after.st_mtime_ns))
assert sum(r['bytes'] for r in records) <= 67108864, '64 MiB original-source collection cap'
print(json.dumps(records), flush=True)
'''


def probe_originals():
    result = subprocess.run(SSH, input=remote_probe_script(), text=True,
                            encoding='utf-8', capture_output=True, timeout=75, check=True)
    records = json.loads(result.stdout)
    check_source_manifest(records)
    return records


def remote_inventory_script():
    # Process image names/PIDs only; no command lines, users, tokens, or auth files.
    return '''import csv,datetime,hashlib,io,json,os,pathlib,shutil,subprocess
record = dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    inventory_pid=os.getpid(),read_only=True,model_imports=0,optimizer_updates=0,
    disk=dict(zip(['total','used','free'],shutil.disk_usage('C:/'))))
commands = {}
for role, args in [
    ('processes',['tasklist','/FO','CSV','/NH']),
    ('gpu',['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'])]:
    try:
        r = subprocess.run(args,capture_output=True,timeout=15)
        commands[role] = dict(returncode=r.returncode,stdout=r.stdout.decode('utf-8',errors='replace'))
    except Exception as e:
        commands[role] = dict(error_type=type(e).__name__,error=str(e))
processes = []
if commands.get('processes',{}).get('returncode') == 0:
    for row in csv.reader(io.StringIO(commands['processes']['stdout'])):
        if len(row)>=2 and row[0].lower() in ['python.exe','pythonw.exe','bash.exe','ssh.exe']:
            processes.append(dict(image=row[0],pid=int(row[1]),inventory_process=int(row[1])==os.getpid()))
record['relevant_processes'] = processes[:256]
record['relevant_process_count'] = len(processes)
record['process_inventory_complete'] = commands.get('processes',{}).get('returncode') == 0 and len(processes)<=256
record['gpu'] = commands.get('gpu',{})
claims = pathlib.Path('C:/Users/benja/claims')
record['claim_directory_exists'] = claims.is_dir()
if claims.is_dir():
    names = sorted(p.name for p in claims.iterdir())
    record['claim_count'] = len(names)
    record['claim_names'] = names[:4096]
    record['claim_inventory_complete'] = len(names)<=4096
else:
    record['claim_count'] = 0
    record['claim_names'] = []
    record['claim_inventory_complete'] = False
busy = pathlib.Path('C:/Users/benja/GPU-BUSY.txt')
record['gpu_busy_marker_exists'] = busy.is_file()
if busy.is_file():
    assert busy.stat().st_size<=4096,'Bounded GPU busy marker only'
    raw = busy.read_bytes()
    text = raw.decode('utf-8',errors='replace').strip()
    record['gpu_busy_marker_sha256'] = hashlib.sha256(raw).hexdigest()
    if text.startswith('BUSY: queue job '):
        record['gpu_busy_marker'] = text[:512]
    else:
        record['gpu_busy_marker_format'] = 'Unrecognized; content withheld'
print(json.dumps(record),flush=True)
'''


def inventory_pc():
    result = subprocess.run(SSH, input=remote_inventory_script(), text=True,
                            encoding='utf-8', capture_output=True, timeout=60, check=True)
    return json.loads(result.stdout)


def main():
    started = time.monotonic()
    out = None
    stage = 'local preflight'
    try:
        assert sys.executable == '/usr/bin/python3', 'Verified Mac /usr/bin/python3 required'
        assert sys.version_info[:3] == (3, 9, 6), 'Verified Mac Python 3.9.6 required'
        root = pathlib.Path.cwd().resolve()
        assert root == WATCHER_ROOT.resolve(), 'Watcher publisher worktree required'
        assert pathlib.Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()).resolve() == root, 'Git publisher root mismatch'
        old_bytes = subprocess.check_output(['git', 'show', 'origin/main:' + OLD_SPEC])
        assert hashlib.sha256(old_bytes).hexdigest() == OLD_SPEC_SHA256, 'Preserved original specification changed'
        old_spec = json.loads(old_bytes)
        assert [old_spec['receipt']] + old_spec['raw_probes'] == EXPECTED_PINS, 'Preserved original pin list changed'
        assert old_spec['collection_only'] and old_spec['no_inference'] and old_spec['no_optimizer'], 'Original collection policy changed'
        assert shutil.disk_usage(root).free >= LOCAL_FREE_FLOOR, '384 MiB Mac collection floor'
        fresh_out = root / OUTPUT_RELATIVE
        assert not fresh_out.exists(), 'Fresh collection output required; preserve earlier runs'
        fresh_out.mkdir(parents=True, exist_ok=False)
        out = fresh_out
        write_new(out / 'LAUNCH.json', dict(started_utc=utc_now(), executable=sys.executable,
            python=sys.version, publisher_root=str(root), old_spec_sha256=OLD_SPEC_SHA256,
            collection_only=True, inference_calls=0, optimizer_updates=0, source_deletions=0))

        stage = 'read-only PC process/claim/GPU/disk inventory'
        inventory = inventory_pc()
        local_queue = pathlib.Path('/Users/ben-hannan/premonition-watch/queue')
        inventory['mac_running_job_names'] = sorted(p.stem for p in local_queue.glob('*.running'))
        inventory['mac_queue_directory_exists'] = local_queue.is_dir()
        write_new(out / 'PC-INVENTORY.json', inventory)
        print(json.dumps(dict(read_only_pc_inventory=inventory), sort_keys=True), flush=True)

        stage = 'original PC manifest before copy'
        originals_before = probe_originals()
        write_new(out / 'SOURCE-MANIFEST.json', dict(checked_utc=utc_now(), before_copy=True,
            old_spec_sha256=OLD_SPEC_SHA256, records=originals_before))

        stage = 'exact-byte copy'
        for pin in EXPECTED_PINS:
            name = pathlib.PurePosixPath(pin['path']).name
            subprocess.run(['scp', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
                            'benspc:' + pin['path'], str(out / name)],
                           check=True, timeout=60, capture_output=True, text=True, encoding='utf-8')
        local_records = []
        for pin, original in zip(EXPECTED_PINS, originals_before):
            local = out / pathlib.PurePosixPath(pin['path']).name
            digest = file_hash(local)
            assert digest == pin['sha256'], 'Copied original hash mismatch'
            assert local.stat().st_size == original['bytes'], 'Copied original size mismatch'
            local_records.append(dict(source_path=pin['path'], local_name=local.name,
                                      sha256=digest, bytes=local.stat().st_size))

        stage = 'original PC preservation after copy'
        originals_after = probe_originals()
        assert originals_after == originals_before, 'Original source bytes or metadata changed'
        write_new(out / 'POST-COPY-VERIFY.json', dict(checked_utc=utc_now(),
            source_before=originals_before, source_after=originals_after, local_records=local_records,
            original_preservation_checks=3, local_hash_checks=3, inference_calls=0, optimizer_updates=0))

        stage = 'bounded publication archive'
        archive = out / 'original-numeric-raw-v2.tar.gz'
        assert not archive.exists(), 'New publication archive required'
        with tarfile.open(str(archive), 'x:gz') as stream:
            for name in ['receipt.json', 'raw-probe-0.pt', 'raw-probe-1.pt',
                         'SOURCE-MANIFEST.json', 'POST-COPY-VERIFY.json', 'PC-INVENTORY.json']:
                stream.add(str(out / name), arcname=name, recursive=False)
        assert archive.stat().st_size <= SOURCE_CAP + 1024**2, 'Bounded publication archive cap'
        parts = []
        with archive.open('rb') as stream:
            index = 0
            for block in iter(lambda: stream.read(PART_BYTES), b''):
                part = out / ('original-numeric-raw-v2.tar.gz.part%03d' % index)
                with part.open('xb') as target:
                    target.write(block)
                parts.append(dict(name=part.name, bytes=len(block), sha256=file_hash(part)))
                index += 1
        archive_record = dict(name=archive.name, bytes=archive.stat().st_size,
                              sha256=file_hash(archive), ordered_parts=parts)
        write_new(out / 'ARCHIVE-MANIFEST.json', archive_record)
        report = dict(completed_utc=utc_now(), wall_seconds=time.monotonic() - started,
            scope='Exact-byte original numeric artifact recovery only', publisher_root=str(root),
            source_records=originals_before, local_records=local_records, archive=archive_record,
            pc_inventory=inventory,
            source_hash_checks_before_copy=3, source_preservation_checks_after_copy=3,
            local_hash_checks=3, files_copied=3, model_imports=0, inference_calls=0,
            optimizer_updates=0, sleep_repeated=False, receipt_writer_repeated=False,
            original_deletions=0, old_collection_failure_preserved=True,
            stage_proof_status='NOT SHOWN')
        write_new(out / 'COLLECTION.json', report)
        print(json.dumps(report, sort_keys=True), flush=True)
        return 0
    except Exception as error:
        failure = dict(failed_utc=utc_now(), stage=stage, error_type=type(error).__name__,
                       error=str(error), wall_seconds=time.monotonic() - started,
                       inference_calls=0, optimizer_updates=0, source_deletions=0,
                       retry_policy='Preserve failure; new queue identity required')
        if out is not None and out.is_dir() and not (out / 'FAILURE.json').exists():
            write_new(out / 'FAILURE.json', failure)
        print(json.dumps(failure, sort_keys=True), flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
