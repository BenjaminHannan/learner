#!/usr/bin/env python3
"""Stdlib queue receipts and read-only recovery; never dispatches or retries work.

Callers supply already bounded watcher/PC observations. An absent return, stale
heartbeat or disconnected coordinator cannot establish that an optimizer stopped.
This module has no model, checkpoint loader, scoring, network or process-kill API.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import ntpath
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sqlite3
import subprocess


SCHEMA = 'sol.cloud.queue-state.v1'
STATES = ('planned', 'claimed', 'running', 'terminal', 'evidence-recovered')


class RecoveryError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def relative_path(value):
    """Use POSIX seal/queue keys even for Windows Path.relative_to results."""
    text = str(value).replace('\\', '/')
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ':' in text or '..' in path.parts:
        raise RecoveryError('contained relative path required')
    return path.as_posix()


def relative_key(path, root):
    windows = isinstance(path, PureWindowsPath) or '\\' in str(path) or bool(PureWindowsPath(str(path)).drive)
    try:
        if windows:
            base = PureWindowsPath(ntpath.normpath(str(root)))
            candidate = PureWindowsPath(path)
            if not candidate.is_absolute():
                candidate = base / candidate
            candidate = PureWindowsPath(ntpath.normpath(str(candidate)))
        else:
            base = Path(root).resolve()
            candidate = Path(path)
            candidate = (candidate if candidate.is_absolute() else base / candidate).resolve()
        return relative_path(candidate.relative_to(base).as_posix())
    except ValueError as error:
        raise RecoveryError('path is outside its declared root') from error


def output_layout(execution_root, job, *, run_root=None, run_namespace=None, seed=None, arm=None):
    """One value supplies the execution destination and queue PUSH destination."""
    if not isinstance(job, str) or not job or relative_path(job) != job or '/' in job:
        raise RecoveryError('single job path component required')
    execution = relative_path(PurePosixPath(relative_path(execution_root)) / ('execution-' + job))
    result = {'execution_path': execution, 'publication_path': execution}
    if run_root is not None:
        if type(seed) is not int or seed < 0 or not isinstance(arm, str) or '/' in arm or '\\' in arm:
            raise RecoveryError('runtime seed/arm path components required')
        result['runtime_output_path'] = relative_path(PurePosixPath(relative_path(run_root)) /
            relative_path(run_namespace) / ('seed%d' % seed) / relative_path(arm))
    return result


def _pin(pin):
    if type(pin) is not dict or not isinstance(pin.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
        raise RecoveryError('exact lowercase SHA256 pin required')
    result = {'path': relative_path(pin['path']), 'sha256': pin['sha256']}
    if 'bytes' in pin:
        if type(pin['bytes']) is not int or pin['bytes'] < 0:
            raise RecoveryError('nonnegative pinned byte count required')
        result['bytes'] = pin['bytes']
    return result


def packaged_runtime_pins(spec, plan, seal, release):
    """Collect small package files the capability runner actually reads.

    Existing PC checkpoints/tokenizer files stay outside this package closure;
    their native PC closure probe remains the launcher's responsibility.
    """
    pins = [spec[key] for key in ('runner', 'plan', 'seal', 'release')]
    pins.extend({'path': path, 'sha256': digest} for path, digest in seal['files'].items())
    pins.append(release['independent_review'])
    pins.extend(plan[key] for key in ('selection', 'protocol', 'token_gate', 'token_audit'))
    pins.extend(plan['schedules'].values())
    if 'comparators' in plan:
        pins.append(plan['comparators'])
    result = {}
    for raw in pins:
        pin = _pin(raw)
        previous = result.get(pin['path'])
        if previous is not None and previous['sha256'] != pin['sha256']:
            raise RecoveryError('runtime aliases disagree on exact file pin')
        result[pin['path']] = pin
    return list(result.values())


def package_smoke(root, files, *, required_pins=(), max_bytes=8 * 1024 ** 2):
    """Read/hash every deployed package and required runtime alias before launch.

    Reading does not import sources or invoke a runner. Return all observed file
    hashes so a receipt proves actual deployed reads rather than in-memory import.
    """
    root = Path(root).resolve()
    pins = {}
    for raw in files:
        pin = _pin(raw)
        if 'bytes' not in pin:
            raise RecoveryError('packaged file requires its exact byte count')
        if pin['path'] in pins:
            raise RecoveryError('duplicate packaged file path')
        pins[pin['path']] = pin
    for raw in required_pins:
        pin = _pin(raw)
        if pin['path'] not in pins:
            raise RecoveryError('required runtime file absent from package: ' + pin['path'])
        existing = pins[pin['path']]
        if existing['sha256'] != pin['sha256'] or ('bytes' in pin and existing.get('bytes') != pin['bytes']):
            raise RecoveryError('required runtime pin differs from package: ' + pin['path'])
    observed = []
    total = 0
    for pin in pins.values():
        path = root.joinpath(*PurePosixPath(pin['path']).parts)
        if not path.resolve().is_relative_to(root):
            raise RecoveryError('packaged file is outside root')
        try:
            size = path.stat().st_size
            if size > max_bytes - total:
                raise RecoveryError('package byte cap exceeded before read')
            data = path.read_bytes()
        except OSError as error:
            raise RecoveryError('deployed runtime file unavailable: ' + pin['path']) from error
        total += len(data)
        if len(data) != size or total > max_bytes or ('bytes' in pin and len(data) != pin['bytes']) or sha_bytes(data) != pin['sha256']:
            raise RecoveryError('deployed runtime bytes differ: ' + pin['path'])
        observed.append({'path': pin['path'], 'sha256': sha_bytes(data), 'bytes': len(data)})
    return {'schema': 'sol.cloud.packaged-launch-smoke.v1', 'files': observed,
            'total_bytes': total, 'physical_files_read': len(observed),
            'model_calls': 0, 'optimizer_updates': 0, 'dispatched': False}


def source_smoke(*, python_sources=(), queue_texts=()):
    """Parse Python and bash -n queue fences, including quoted Python heredocs."""
    python_count = shell_count = heredoc_count = 0
    for source in python_sources:
        ast.parse(source)
        python_count += 1
    for text in queue_texts:
        blocks = re.findall(r'```bash\s*\n(.*?)\n```', text, re.S)
        if not blocks:
            raise RecoveryError('queue bash fence missing')
        for block in blocks:
            probe = subprocess.run(['bash', '-n'], input=block, text=True,
                                   capture_output=True, timeout=5, check=False)
            if probe.returncode:
                raise RecoveryError('queue shell parse failed: ' + probe.stderr.strip())
            lines = block.splitlines()
            for index, line in enumerate(lines):
                if 'python' not in line or '<<' not in line:
                    continue
                match = re.search(r"<<\s*'([A-Za-z_][A-Za-z_0-9]*)'\s*$", line)
                if match is None:
                    raise RecoveryError('Python bootstrap heredoc must use a quoted delimiter')
                marker = match.group(1)
                try:
                    end = lines.index(marker, index + 1)
                except ValueError as error:
                    raise RecoveryError('Python bootstrap heredoc terminator missing') from error
                ast.parse('\n'.join(lines[index + 1:end]) + '\n')
                heredoc_count += 1
            shell_count += 1
    return {'python_sources_parsed': python_count, 'shell_blocks_parsed': shell_count,
            'python_heredocs_parsed': heredoc_count, 'executed_bootstraps': 0}


def _updates(value, maximum):
    if value is not None and (type(value) is not int or not 0 <= value <= maximum):
        raise RecoveryError('update count must be unknown or within planned range')
    return value


def reconcile(state, observation):
    """Pure, read-only decision. Retry eligibility never invokes a retry.

    observation fields: watcher_claim (running/closed/unknown), watcher_exit,
    pc_probe_ok, pc_owned_pids, pc_exit, coordinator_connected, heartbeat_stale,
    return_present, and optional terminal {outcome, optimizer_updates, failure}.
    Unknown process inventory is distinct from a known empty inventory.
    """
    maximum = state['planned_updates']
    if state.get('state') not in STATES or type(maximum) is not int or maximum <= 0:
        raise RecoveryError('valid durable job state and positive planned updates required')
    known = _updates(state.get('optimizer_updates'), maximum)
    lower = state.get('updates_lower_bound', 0)
    if type(lower) is not int or not 0 <= lower <= maximum or known is not None and known < lower:
        raise RecoveryError('durable update lower bound conflicts with latest count')
    terminal = observation.get('terminal')
    reasons = []
    outcome = state.get('outcome')
    failure = state.get('failure')
    if terminal is not None:
        outcome = terminal.get('outcome')
        count = _updates(terminal.get('optimizer_updates'), maximum)
        if outcome not in ('completed', 'failed') or count is not None and count < lower:
            raise RecoveryError('terminal receipt conflicts with durable update state')
        if outcome == 'completed' and count != maximum:
            raise RecoveryError('completed receipt must contain exact planned update count')
        if state.get('outcome') is not None and state['outcome'] != outcome:
            raise RecoveryError('terminal outcomes conflict')
        if known is not None and state['state'] in ('terminal', 'evidence-recovered') and count != known:
            raise RecoveryError('terminal update counts conflict')
        if state.get('failure') is not None and terminal.get('failure') != state['failure']:
            raise RecoveryError('terminal failure evidence conflicts')
        known = count
        failure = terminal.get('failure') if outcome == 'failed' else None
        reasons.append('terminal_receipt_recovered')
    running = (observation.get('pc_probe_ok') is True and
               bool(observation.get('pc_owned_pids')))
    closed = (observation.get('pc_probe_ok') is True and
              observation.get('pc_owned_pids') == [] and
              type(observation.get('pc_exit')) is int and
              observation.get('watcher_claim') == 'closed' and
              type(observation.get('watcher_exit')) is int)
    missing = [name for name, present in (
        ('return_file', observation.get('return_present') is True),
        ('pc_inventory', observation.get('pc_probe_ok') is True),
        ('pc_exit', type(observation.get('pc_exit')) is int),
        ('watcher_exit', type(observation.get('watcher_exit')) is int)) if not present]
    preupdate = (outcome == 'failed' and known == 0 and lower == 0 and
                 isinstance(failure, dict) and failure.get('before_optimizer') is True)
    retry = preupdate and closed and not running
    if running:
        disposition = 'running'
        reasons.append('PC_owned_process_still_running')
    elif outcome == 'completed':
        disposition = 'evidence-recovered' if terminal is not None else 'completed'
    elif retry:
        disposition = 'known_preupdate_failure_ownership_closed'
    elif outcome == 'failed':
        disposition = 'failed_preserve_evidence'
    else:
        disposition = 'uncertain_preserve_evidence'
    if observation.get('coordinator_connected') is False:
        reasons.append('coordinator_disconnected_does_not_close_PC_ownership')
    if observation.get('heartbeat_stale') is True:
        reasons.append('stale_heartbeat_does_not_close_PC_ownership')
    return {'schema': 'sol.cloud.queue-recovery-decision.v1', 'job': state['job'],
            'disposition': disposition, 'outcome': outcome, 'failure': failure,
            'optimizer_updates': known, 'missing_metadata': missing,
            'ownership_closed': closed, 'retry_eligible': bool(retry),
            'reasons': reasons, 'read_only': True, 'dispatched': False,
            'optimizer_updates_performed': 0, 'scoring_calls': 0}


class ReceiptStore:
    """Transactional job state plus immutable, idempotent receipt records."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / 'queue-receipts.sqlite3'
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs(job TEXT PRIMARY KEY, record TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS receipts(job TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, snapshot TEXT NOT NULL, PRIMARY KEY(job,id))')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            with db:
                yield db
        finally:
            db.close()

    def plan(self, job, planned_updates, paths):
        if not isinstance(job, str) or not job or type(planned_updates) is not int or planned_updates <= 0:
            raise RecoveryError('job and positive planned update count required')
        paths = dict(paths)
        if paths.get('execution_path') != paths.get('publication_path'):
            raise RecoveryError('execution and publication paths must use the same value')
        record = {'schema': SCHEMA, 'job': job, 'state': 'planned', 'planned_updates': planned_updates,
                  'optimizer_updates': 0, 'updates_lower_bound': 0, 'paths': paths,
                  'outcome': None, 'failure': None, 'missing_metadata': [], 'claim': None}
        with self.transaction() as db:
            row = db.execute('SELECT record FROM jobs WHERE job=?', (job,)).fetchone()
            if row:
                old = json.loads(row[0])
                if old['planned_updates'] != planned_updates or old['paths'] != paths:
                    raise RecoveryError('existing job plan differs')
                return old
            db.execute('INSERT INTO jobs VALUES(?,?)', (job, encoded(record)))
        return record

    def get(self, job):
        with self.transaction() as db:
            row = db.execute('SELECT record FROM jobs WHERE job=?', (job,)).fetchone()
            if row is None:
                raise RecoveryError('job is not planned')
            return json.loads(row[0])

    def record(self, job, receipt_id, event):
        if not isinstance(receipt_id, str) or not receipt_id:
            raise RecoveryError('nonempty receipt ID required')
        payload = encoded(event)
        with self.transaction() as db:
            row = db.execute('SELECT record FROM jobs WHERE job=?', (job,)).fetchone()
            if row is None:
                raise RecoveryError('job is not planned')
            state = json.loads(row[0])
            old = db.execute('SELECT payload FROM receipts WHERE job=? AND id=?', (job, receipt_id)).fetchone()
            if old:
                if old[0] != payload:
                    raise RecoveryError('duplicate receipt ID has different evidence')
                return state
            kind = event.get('kind')
            if kind not in ('claimed', 'running', 'progress', 'terminal', 'evidence-recovered'):
                raise RecoveryError('unsupported job event')
            if state['state'] in ('terminal', 'evidence-recovered') and kind not in ('terminal', 'evidence-recovered'):
                raise RecoveryError('terminal job cannot be reopened or implicitly retried')
            if kind == 'claimed':
                claim = event.get('claim')
                if not isinstance(claim, str) or not claim or state['claim'] not in (None, claim):
                    raise RecoveryError('another claim already owns this job')
                if state['state'] not in ('planned', 'claimed'):
                    raise RecoveryError('claim cannot move a running job backwards')
                state.update(state='claimed', claim=claim)
            elif kind in ('running', 'progress'):
                if state['state'] not in ('claimed', 'running'):
                    raise RecoveryError('running evidence requires an existing claim')
                count = _updates(event.get('optimizer_updates'), state['planned_updates'])
                if count is not None and count < state['updates_lower_bound']:
                    raise RecoveryError('optimizer update count moved backwards')
                state.update(state='running', optimizer_updates=count)
                if count is not None:
                    state['updates_lower_bound'] = count
            else:
                decision = reconcile(state, {'terminal': event, 'return_present': True})
                state.update(state=kind, outcome=decision['outcome'], failure=decision['failure'],
                             optimizer_updates=decision['optimizer_updates'],
                             missing_metadata=event.get('missing_metadata', []))
                if state['optimizer_updates'] is not None:
                    state['updates_lower_bound'] = state['optimizer_updates']
            snapshot = encoded(state)
            db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (job, receipt_id, payload, snapshot))
            db.execute('UPDATE jobs SET record=? WHERE job=?', (snapshot, job))
            return state

    def receipts(self, job):
        with self.transaction() as db:
            return [{'id': row[0], 'event': json.loads(row[1]), 'snapshot': json.loads(row[2])}
                    for row in db.execute('SELECT id,payload,snapshot FROM receipts WHERE job=? ORDER BY rowid', (job,))]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, help='bounded job-state JSON')
    parser.add_argument('--observation', required=True, help='bounded read-only watcher/PC evidence JSON')
    args = parser.parse_args(argv)
    print(encoded(reconcile(json.loads(Path(args.state).read_text()),
                            json.loads(Path(args.observation).read_text()))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
