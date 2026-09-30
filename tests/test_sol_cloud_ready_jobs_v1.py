"""Bounded stdlib fixtures only; no model imports, SSH, GPU or live queues."""
import concurrent.futures
import datetime
import json
from pathlib import Path
import tempfile
import unittest

from scripts.sol_cloud_queue_recovery_v1 import RecoveryError, reconcile
from scripts.sol_cloud_ready_jobs_v1 import (
    ReadyJobs, clean_tree_smoke, failure_receipt, latency_ledger,
    retain_return, runtime_manifest, sha_bytes, stage_package,
)


class ReliabilityFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = {'scripts/launch.py': b'import sys\n', 'review.json': b'{"review":"ok"}\n'}
        self.pins = [{'path': p, 'bytes': len(b), 'sha256': sha_bytes(b)} for p, b in self.data.items()]
        self.provider = lambda commit, path: self.data[path]
        self.manifest = self.make('first')
        self.idle = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'pc_probe_ok': True, 'pc_owned_pids': [],
                     'watcher_running_jobs': [], 'gpu_busy_claim': None, 'ownership_closed': True}

    def make(self, job):
        return runtime_manifest(job, '1'*40, self.pins, 'artifacts/relay-v3', required=self.pins)

    def stage(self, manifest=None):
        return stage_package(manifest or self.manifest, self.root/'cache', self.provider)

    def store(self):
        return ReadyJobs(self.root/'receipts')

    def ready(self, store, job, position):
        manifest = self.make(job)
        store.register(manifest, 'Derek explicit fixture approval', position, 1)
        store.mark_ready(job, self.stage(manifest))

    def test_missing_review_refuses_before_staging(self):
        with self.assertRaisesRegex(RecoveryError, 'required runtime dependency'):
            runtime_manifest('job', '1'*40, self.pins[:1], 'artifacts/v3', required=self.pins)

    def test_duplicate_and_wrong_pin(self):
        with self.assertRaises(RecoveryError):
            runtime_manifest('job', '1'*40, self.pins+self.pins[:1], 'artifacts/v3')
        with self.assertRaisesRegex(RecoveryError, 'different'):
            stage_package(self.manifest, self.root/'cache', lambda c, p: b'stale')

    def test_registration_rejects_manifest_bypass(self):
        store = self.store()
        for invalid in (dict(self.manifest, commit='main'),
                        dict(self.manifest, paths={'execution_path':'artifacts/v3/execution-first',
                                                   'publication_path':'artifacts/stale'})):
            with self.assertRaises(RecoveryError):
                store.register(invalid, 'owner approval', 0, 1)

    def test_clean_tree_missing_launcher_then_physical_smoke(self):
        self.assertFalse((self.root/'cache'/'scripts/launch.py').exists())
        staged = self.stage()
        smoke = clean_tree_smoke(self.manifest, staged)
        self.assertEqual(smoke['physical_files_read'], 2)
        self.assertEqual(smoke['source_syntax']['executed_bootstraps'], 0)
        self.assertEqual(smoke['optimizer_updates'], 0)

    def test_stale_tree_is_not_used_or_overwritten(self):
        stale = self.root/'working-tree/scripts/launch.py'
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b'stale')
        staged = self.stage()
        self.assertEqual((Path(staged['root'])/'scripts/launch.py').read_bytes(), self.data['scripts/launch.py'])
        self.assertEqual(stale.read_bytes(), b'stale')

    def test_interrupted_staging_repeated_recovery(self):
        calls = []
        def interrupted(commit, path):
            calls.append(path)
            if path == 'review.json':
                raise ConnectionError('fixture transport interrupted')
            return self.data[path]
        with self.assertRaises(ConnectionError):
            stage_package(self.manifest, self.root/'cache', interrupted)
        staged = self.stage()
        again = stage_package(self.manifest, self.root/'cache', lambda c, p: self.fail('must reuse staged exact bytes'))
        self.assertEqual(staged, again)
        (Path(staged['root'])/'review.json').write_bytes(b'corrupt')
        with self.assertRaises(RecoveryError):
            self.stage()

    def test_layout_has_single_execution_publication_value(self):
        self.assertEqual(self.manifest['paths']['execution_path'], self.manifest['paths']['publication_path'])
        self.assertIn('relay-v3/execution-first', self.manifest['paths']['execution_path'])

    def test_ready_handoff_and_restart_never_repeats_completed_job(self):
        store = self.store()
        self.ready(store, 'first', 0)
        self.ready(store, 'second', 1)  # safe prestaging while prior work runs
        first = store.claim_next('sole-integrator', self.idle)
        self.assertEqual(first['job'], 'first')
        self.assertEqual(self.store().claim_next('sole-integrator', self.idle)['action'], 'blocked')
        store.record('first', 'started', {'kind':'running', 'optimizer_updates': None})
        store.record('first', 'closed', {'kind':'terminal', 'outcome':'completed', 'optimizer_updates':1})
        next_job = self.store().claim_next('sole-integrator', self.idle)
        self.assertEqual(next_job['job'], 'second')
        self.assertFalse(next_job['dispatched'])
        store.record('first', 'closed', {'kind':'terminal', 'outcome':'completed', 'optimizer_updates':1})
        self.assertEqual(len(store.receipts('first')), 3)

    def test_uncertain_ownership_never_starts_next(self):
        store = self.store()
        self.ready(store, 'first', 0)
        for changed in ({'pc_owned_pids':[1]}, {'pc_probe_ok':False}, {'gpu_busy_claim':'old'},
                        {'watcher_running_jobs':['old']}, {'ownership_closed':False}):
            observation = dict(self.idle, **changed)
            self.assertEqual(store.claim_next('owner', observation)['action'], 'blocked')
        for stamp in (None, '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z'):
            self.assertEqual(store.claim_next('owner', dict(self.idle, checked_utc=stamp))['action'], 'blocked')

    def test_concurrent_claim_has_single_winner(self):
        store = self.store()
        self.ready(store, 'first', 0)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda owner: self.store().claim_next(owner, self.idle), ('a','b')))
        self.assertEqual(sum(r['action']=='reserved' for r in results), 1)

    def test_failed_predecessor_blocks_even_zero_updates(self):
        store = self.store()
        self.ready(store, 'first', 0)
        self.ready(store, 'second', 1)
        store.record('first', 'failure', {'kind':'terminal', 'outcome':'failed', 'optimizer_updates':0,
                     'failure':{'before_optimizer':True, 'error':'missing dependency'}})
        self.assertIn('failed predecessor', store.claim_next('owner', self.idle)['error'])

    def test_interrupted_return_retained_once_without_encoded_payload(self):
        expected = {'bytes':10, 'sha256':sha_bytes(b'0123456789')}
        result = retain_return(self.root/'return', 'stdout.log', b'012', expected)
        self.assertFalse(result['complete'])
        self.assertEqual(retain_return(self.root/'return', 'stdout.log', b'012', expected), result)
        self.assertNotIn('data_b64', json.dumps(result))
        with self.assertRaisesRegex(RecoveryError, 'preserve'):
            retain_return(self.root/'return', 'stdout.log', b'0123456789', expected)
        self.assertEqual((self.root/'return/stdout.log').read_bytes(), b'012')

    def test_return_cap_preserves_prefix_and_path_escape_fails(self):
        body = b'abcdef'
        result = retain_return(self.root/'return', 'stderr.log', body,
                               {'bytes':len(body), 'sha256':sha_bytes(body)}, cap=3)
        self.assertFalse(result['complete'])
        self.assertEqual((self.root/'return/stderr.log').read_bytes(), b'abc')
        with self.assertRaises(RecoveryError):
            retain_return(self.root, '../escape', body, {}, cap=3)

    def test_failure_bodies_phase_and_unknown_updates_survive_restart(self):
        stderr = b'NameError: bootstrap missing\napi_key=secret-value\n'
        receipt = failure_receipt(self.root/'failure', 'PC-bootstrap', b'', stderr,
                                  dispatched=True, export_preview=True)
        self.assertIsNone(receipt['optimizer_updates'])
        self.assertIn('NameError', receipt['redacted_excerpts']['stderr'])
        self.assertNotIn('secret-value', receipt['redacted_excerpts']['stderr'])
        self.assertEqual((self.root/'failure/stderr.log').read_bytes(), stderr)
        self.assertEqual(json.loads((self.root/'failure/failure.json').read_text()), receipt)
        with self.assertRaisesRegex(RecoveryError, 'metadata differs'):
            failure_receipt(self.root/'failure', 'different-phase', b'', stderr,
                            dispatched=True, export_preview=True)
        self.assertEqual(failure_receipt(self.root/'failure', 'PC-bootstrap', b'', stderr,
                         dispatched=True, export_preview=True), receipt)

    def test_unknown_transport_and_stale_heartbeat_do_not_allow_retry(self):
        store = self.store()
        self.ready(store, 'first', 0)
        store.claim_next('owner', self.idle)
        state = store.record('first', 'started', {'kind':'running', 'optimizer_updates':None})
        decision = reconcile(state, {'heartbeat_stale':True, 'coordinator_connected':False})
        self.assertFalse(decision['retry_eligible'])
        self.assertIsNone(decision['optimizer_updates'])

    def test_ledger_separates_handoff_load_and_missing_values(self):
        ledger = latency_ledger('job', {'published':'2026-09-30T00:00:00Z',
            'watcher_pickup':'2026-09-30T00:00:02Z', 'pc_start':'2026-09-30T00:00:03Z',
            'first_update':'2026-09-30T00:00:23Z'})
        self.assertEqual(ledger['seconds']['publication_to_pickup'], 2)
        self.assertEqual(ledger['seconds']['PC_start_to_first_update_including_load'], 20)
        self.assertIsNone(ledger['seconds']['completion_to_next_first_update'])
        self.assertEqual(ledger['sample_count'], 0)


if __name__ == '__main__':
    unittest.main()
