#!/usr/bin/env python3
"""Local approved-job staging and receipt recovery. Never publishes or dispatches.

The sole integrator supplies approvals and fresh PC/watcher observations, then
uses claim_next before its existing dispatcher. Native launch gates still apply.
"""
import datetime
import json
import os
from pathlib import Path
import re
import subprocess

from scripts.sol_cloud_queue_recovery_v1 import (
    ReceiptStore, RecoveryError, encoded, output_layout, package_smoke,
    relative_path, sha_bytes, source_smoke,
)

CAP = 8 * 1024**2


def runtime_manifest(job, commit, files, execution_root, *, required=(), runtime_output=None):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise RecoveryError('immutable Git commit required')
    # Structural validation also detects duplicate/contradictory runtime aliases.
    seen = set()
    for pin in files:
        path = relative_path(pin['path'])
        if path != pin['path'] or path in seen:
            raise RecoveryError('unique canonical runtime file paths required')
        if type(pin.get('bytes')) is not int or not 0 <= pin['bytes'] <= CAP:
            raise RecoveryError('bounded exact runtime size required')
        if not re.fullmatch('[0-9a-f]{64}', pin.get('sha256', '')):
            raise RecoveryError('exact runtime hash required')
        seen.add(path)
    if sum(p['bytes'] for p in files) > CAP:
        raise RecoveryError('runtime package exceeds staging cap')
    for pin in required:
        if not any(p['path'] == pin['path'] and p['sha256'] == pin['sha256']
                   and ('bytes' not in pin or p['bytes'] == pin['bytes']) for p in files):
            raise RecoveryError('required runtime dependency absent/different: ' + pin['path'])
    paths = output_layout(execution_root, job)
    if runtime_output is not None:
        paths['runtime_output_path'] = relative_path(runtime_output)
    return {'schema': 'sol.cloud.ready-manifest.v1', 'job': job, 'commit': commit,
            'files': files, 'required': list(required),
            'paths': paths}


def validate_manifest(manifest):
    checked = runtime_manifest(manifest['job'], manifest['commit'], manifest['files'],
                               manifest['paths']['execution_path'].rsplit('/execution-', 1)[0],
                               required=manifest['required'],
                               runtime_output=manifest['paths'].get('runtime_output_path'))
    if checked != manifest:
        raise RecoveryError('runtime manifest contains conflicting layout/fields')
    return checked


def _contained(root, path):
    root = Path(root).resolve()
    target = root / relative_path(path)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise RecoveryError('source/receipt path escapes its declared root')
    return target


def stage_package(manifest, cache, provider):
    """Pre-stage source bytes only; interrupted/repeated calls preserve originals.

    provider(commit, path) must return already bounded immutable Git bytes. This
    helper does not read models, claims, queue directories or training outcomes.
    """
    validate_manifest(manifest)
    root = Path(cache) / sha_bytes(encoded(manifest).encode())
    root.mkdir(parents=True, exist_ok=True)
    for pin in manifest['files']:
        target = _contained(root, pin['path'])
        if not target.exists():
            data = provider(manifest['commit'], pin['path'])
            if len(data) != pin['bytes'] or sha_bytes(data) != pin['sha256']:
                raise RecoveryError('pinned Git source unavailable/different: ' + pin['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            # One immutable write per source. A partial write is preserved and
            # fails subsequent smoke; never overwrite suspect bytes to recover.
            try:
                with target.open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                pass  # A concurrent stager's bytes must pass the same smoke.
    smoke = package_smoke(root, manifest['files'], required_pins=manifest['required'])
    return {'root': str(root), 'manifest_sha256': sha_bytes(encoded(manifest).encode()),
            'smoke': smoke, 'dispatched': False}


def git_provider(repository):
    def read(commit, path):
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise RecoveryError('immutable Git commit required')
        path = relative_path(path)
        size = subprocess.run(['git', '-C', str(repository), 'cat-file', '-s', commit + ':' + path],
                              check=True, capture_output=True, timeout=10)
        if int(size.stdout) > CAP:
            raise RecoveryError('Git blob exceeds source cap')
        return subprocess.run(['git', '-C', str(repository), 'show', commit + ':' + path],
                              check=True, capture_output=True, timeout=10).stdout
    return read


def clean_tree_smoke(manifest, staged):
    """Physical closure and Python syntax only: no entrypoint/model execution."""
    validate_manifest(manifest)
    root = Path(staged['root'])
    observed = package_smoke(root, manifest['files'], required_pins=manifest['required'])
    sources = [(root / pin['path']).read_bytes() for pin in manifest['files']
               if pin['path'].endswith('.py')]
    return dict(observed, source_syntax=source_smoke(python_sources=sources),
                manifest_sha256=sha_bytes(encoded(manifest).encode()))


class ReadyJobs(ReceiptStore):
    """Ordered approvals + immutable readiness; atomic single-owner selection."""
    def __init__(self, directory):
        super().__init__(directory)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS ready(job TEXT PRIMARY KEY, position INTEGER UNIQUE, approval TEXT, manifest TEXT, root TEXT)')

    def register(self, manifest, approved_by, position, planned_updates):
        validate_manifest(manifest)
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise RecoveryError('explicit job approval required')
        if type(position) is not int or position < 0:
            raise RecoveryError('nonnegative serial order required')
        self.plan(manifest['job'], planned_updates, manifest['paths'])
        values = (manifest['job'], position, approved_by, encoded(manifest))
        with self.transaction() as db:
            row = db.execute('SELECT job,position,approval,manifest FROM ready WHERE job=?', (manifest['job'],)).fetchone()
            if row and row != values:
                raise RecoveryError('approved job definition is immutable')
            if not row:
                db.execute('INSERT INTO ready VALUES(?,?,?,?,NULL)', values)

    def mark_ready(self, job, staged):
        with self.transaction() as db:
            row = db.execute('SELECT manifest,root FROM ready WHERE job=?', (job,)).fetchone()
            if row is None:
                raise RecoveryError('job has no approved manifest')
            manifest = json.loads(row[0])
            smoke = clean_tree_smoke(manifest, staged)
            if staged['manifest_sha256'] != smoke['manifest_sha256']:
                raise RecoveryError('staged manifest differs from approval')
            if row[1] is not None and row[1] != staged['root']:
                raise RecoveryError('readiness root changed')
            db.execute('UPDATE ready SET root=? WHERE job=?', (staged['root'], job))
        return smoke

    def claim_next(self, claim, observation):
        """Reserve exactly one local ready job; caller alone publishes/dispatches.

        Requires fresh native ownership proof even if previous receipts say
        complete. A dead coordinator or stale heartbeat never closes a claim.
        """
        if not isinstance(claim, str) or not claim:
            raise RecoveryError('sole-integrator claim identity required')
        stamp = observation.get('checked_utc')
        try:
            checked = datetime.datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            age = (datetime.datetime.now(datetime.timezone.utc) - checked).total_seconds()
        except (AttributeError, TypeError, ValueError):
            age = float('inf')
        if not -5 <= age <= 30:
            return {'action': 'blocked', 'error': 'fresh timestamped ownership observation required', 'dispatched': False}
        if not (observation.get('pc_probe_ok') is True and
                observation.get('pc_owned_pids') == [] and
                observation.get('watcher_running_jobs') == [] and
                observation.get('gpu_busy_claim') is None and
                observation.get('ownership_closed') is True):
            return {'action': 'blocked', 'error': 'fresh closed PC/watcher ownership required', 'dispatched': False}
        with self.transaction() as db:
            jobs = [json.loads(r[0]) for r in db.execute('SELECT record FROM jobs')]
            if any(s['state'] in ('claimed', 'running') for s in jobs):
                return {'action': 'blocked', 'error': 'existing durable owner/outcome unresolved', 'dispatched': False}
            states = {s['job']: s for s in jobs}
            for job, _, _, raw, root in db.execute('SELECT * FROM ready ORDER BY position'):
                state = states[job]
                if state['state'] in ('terminal', 'evidence-recovered'):
                    if state['outcome'] != 'completed':
                        return {'action': 'blocked', 'error': 'failed predecessor requires explicit disposition: ' + job, 'dispatched': False}
                    continue
                if root is None:
                    return {'action': 'blocked', 'error': 'next approved package is not staged: ' + job, 'dispatched': False}
                manifest = json.loads(raw)
                clean_tree_smoke(manifest, {'root': root})
                state.update(state='claimed', claim=claim)
                event = {'kind': 'claimed', 'claim': claim, 'manifest_sha256': sha_bytes(raw.encode())}
                db.execute('INSERT INTO receipts VALUES(?,?,?,?)',
                           (job, 'ready-claim', encoded(event), encoded(state)))
                db.execute('UPDATE jobs SET record=? WHERE job=?', (encoded(state), job))
                return {'action': 'reserved', 'job': job, 'manifest': manifest,
                        'root': root, 'claim': claim, 'dispatched': False}
        return {'action': 'empty', 'dispatched': False}


def retain_return(root, path, data, expected, *, cap=CAP):
    """Single raw evidence copy plus hash metadata, never base64 in manifests."""
    if type(cap) is not int or cap < 0:
        raise RecoveryError('nonnegative return cap required')
    target = _contained(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    accepted = data[:cap]
    if target.exists():
        if target.read_bytes() != accepted:
            raise RecoveryError('existing return differs; preserve and collect under a new identity')
    else:
        with target.open('xb') as stream:
            stream.write(accepted)
            stream.flush()
            os.fsync(stream.fileno())
    complete = len(data) <= cap and len(data) == expected['bytes'] and sha_bytes(data) == expected['sha256']
    return {'path': relative_path(path), 'bytes': len(accepted), 'sha256': sha_bytes(accepted),
            'complete': complete, 'error': None if complete else 'interrupted/overbound/hash-mismatched return; original retained',
            'PC_originals_preserved': True}


def failure_receipt(root, phase, stdout, stderr, *, dispatched, updates=None,
                    known_secrets=(), export_preview=False):
    """Keep original failure bodies locally; exported excerpts are optional.

    Redaction covers supplied secrets and common credential labels/PEM blocks.
    Unknown secret forms still require human review before external export.
    Post-dispatch failure never implies zero updates without an actual receipt.
    """
    if not isinstance(phase, str) or not phase or type(dispatched) is not bool:
        raise RecoveryError('explicit failure phase and dispatch state required')
    if updates is not None and (type(updates) is not int or updates < 0):
        raise RecoveryError('update state must be unknown or nonnegative integer')
    if not dispatched and updates not in (None, 0):
        raise RecoveryError('pre-dispatch failure cannot contain optimizer updates')
    streams = {}
    previews = {}
    for name, data in (('stdout', stdout), ('stderr', stderr)):
        expected = {'bytes': len(data), 'sha256': sha_bytes(data)}
        streams[name] = retain_return(root, name + '.log', data, expected)
        if export_preview:
            text = data[:16384].decode('utf8', errors='replace')
            for secret in sorted(known_secrets, key=len, reverse=True):
                if secret:
                    text = text.replace(secret, '[REDACTED]')
            text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|$)',
                          '[REDACTED PRIVATE KEY]', text, flags=re.S)
            text = re.sub(r'(?im)((?:authorization|api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*)[^\r\n]+',
                          r'\1[REDACTED]', text)
            previews[name] = text
    receipt = {'schema': 'sol.cloud.retained-failure.v1', 'phase': phase,
            'dispatched': dispatched, 'optimizer_updates': updates if dispatched else 0,
            'optimizer_status': 'unknown; reconcile original PC receipt/process state' if dispatched and updates is None else 'known',
            'streams': streams, 'redacted_excerpts': previews,
            'external_export_requires_review': bool(export_preview),
            'retry_performed': False}
    raw = encoded(receipt).encode('utf8')
    target = _contained(root, 'failure.json')
    if target.exists():
        if target.read_bytes() != raw:
            raise RecoveryError('existing failure metadata differs; preserve original receipt')
    else:
        with target.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return receipt


def latency_ledger(job, timestamps):
    """UTC event intervals; missing timestamps stay unknown, never estimated."""
    names = ('package_ready', 'published', 'watcher_pickup', 'pc_start',
             'first_update', 'completed', 'next_first_update')
    parsed = {}
    for name in names:
        value = timestamps.get(name)
        if value is not None:
            stamp = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            if stamp.utcoffset() is None:
                raise RecoveryError('timezone-aware latency timestamps required')
            parsed[name] = stamp
    present = [parsed[n] for n in names if n in parsed]
    if any(b < a for a, b in zip(present, present[1:])):
        raise RecoveryError('latency timestamps are not chronological')
    intervals = {}
    for label, a, b in (
        ('publication_to_pickup', 'published', 'watcher_pickup'),
        ('handoff_to_PC_start', 'watcher_pickup', 'pc_start'),
        ('PC_start_to_first_update_including_load', 'pc_start', 'first_update'),
        ('completion_to_next_first_update', 'completed', 'next_first_update')):
        intervals[label] = (parsed[b] - parsed[a]).total_seconds() if a in parsed and b in parsed else None
    return {'job': job, 'timestamps': {n: timestamps.get(n) for n in names},
            'seconds': intervals, 'sample_count': int(intervals['completion_to_next_first_update'] is not None),
            'load_only_seconds': None, 'load_only_note': 'requires explicit load-completion evidence'}
