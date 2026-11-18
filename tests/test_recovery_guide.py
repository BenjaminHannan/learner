import hashlib
import json
import random
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from scripts.cap256_launch import recovery_guide as guide


class GuideTests(unittest.TestCase):
    def fixture(self,root):
        folder=root/'docs/premonition-recovery';folder.mkdir(parents=True)
        text='Fixture only: preflight. Preserve evidence. Atomic receipts. Atomic storage.\n'
        path=folder/'fixture-v1.md';path.write_text(text)
        rules=dict(zip((guide.START_RULE,guide.FAILURE_RULE,guide.RECEIPT_RULE,guide.STORAGE_RULE),('preflight.','Preserve evidence.','Atomic receipts.','Atomic storage.')))
        current={'version':'fixture-v1','path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rules':rules}
        (folder/'CURRENT.json').write_text(json.dumps(current))
        loaded=guide.load_current(root)
        request={'batch_id':'test-only','guide_acknowledgment':{k:loaded[k] for k in ('version','sha256','current_manifest_sha256')}}
        request['guide_acknowledgment'].update(phase='task_start',batch_id='test-only',loaded=True,actor='test-owner',applicable_rules=[guide.START_RULE],action='Validate scope and resources before any launch.')
        return request,path

    def test_absent_current_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):guide.require_start(folder,{'batch_id':'x'})

    def test_absent_ack_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder))
            with self.assertRaises(ValueError):guide.require_start(folder,{'batch_id':'x'})

    def test_current_ack_loads_bytes_without_rng_change(self):
        with tempfile.TemporaryDirectory() as folder:
            request,path=self.fixture(Path(folder));before=random.getstate();receipt=guide.require_start(folder,request)
            self.assertEqual(receipt['loaded_bytes'],len(path.read_bytes()));self.assertEqual(random.getstate(),before)
            self.assertFalse(receipt['comprehension_verified'])

    def test_every_stale_or_wrong_binding_is_blocked(self):
        for key,value in [('version','old'),('sha256','0'*64),('current_manifest_sha256','0'*64),('batch_id','another'),('phase','failure'),('loaded',False),('applicable_rules',[]),('action','')]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as folder:
                request,_=self.fixture(Path(folder));request['guide_acknowledgment'][key]=value
                with self.assertRaises(ValueError):guide.require_start(folder,request)

    def test_changed_guide_cannot_use_old_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            request,path=self.fixture(Path(folder));path.write_text('changed')
            with self.assertRaises(ValueError):guide.require_start(folder,request)

    def test_real_driver_blocks_absent_stale_ack_before_any_process_or_lock(self):
        from scripts.cap256_launch import mixture_receipt_pc_driver as driver
        pkg=Path(driver.__file__).parent
        for kind in ('missing','stale'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);request,_=self.fixture(root)
                if kind=='missing':request.pop('guide_acknowledgment')
                else:request['guide_acknowledgment']['sha256']='0'*64
                request.update(root=str(root),pkg=str(pkg),launcher_sha256={name:hashlib.sha256((pkg/name).read_bytes()).hexdigest() for name in ('receipt_io.py','recovery_guide.py')})
                packet=root/'request.json';packet.write_text(json.dumps(request))
                with patch.object(driver.subprocess,'Popen') as popen:
                    with self.assertRaises(ValueError):driver.execute(packet)
                popen.assert_not_called()
                self.assertFalse((root/'launch-cap256').exists())

    def test_driver_failure_emits_rule_action_evidence_without_model_calls(self):
        import importlib,os
        from types import SimpleNamespace
        from scripts.cap256_launch import mixture_receipt_pc_driver as driver
        pkg=Path(driver.__file__).parent
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);request,_=self.fixture(root)
            for name in ('runner.py','eval.py'): (root/name).write_text('# fixture only\n')
            cfg={'continuation_runner':{'path':'runner.py','sha256':hashlib.sha256((root/'runner.py').read_bytes()).hexdigest()},'evaluation_runner':{'path':'eval.py','sha256':hashlib.sha256((root/'eval.py').read_bytes()).hexdigest()},'dispatch_allowed':True,'budget':{'worker_seconds':2400,'total_fit_seconds':9600,'remaining_fit_seconds':8067.229115,'failed_attempt_charged_seconds':1532.770885},'output_namespace':'new-output','sources':[],'execution_order':[[0,'repeat256']]}
            cfgpath=root/'config.json';cfgpath.write_text(json.dumps(cfg))
            request.update(root=str(root),pkg=str(pkg),config={'path':'config.json','sha256':hashlib.sha256(cfgpath.read_bytes()).hexdigest()},commit='fixture',queued_utc='fixture',launcher_sha256={name:hashlib.sha256((pkg/name).read_bytes()).hexdigest() for name in ('receipt_io.py','recovery_guide.py')})
            state=root/'launch-cap256';state.mkdir();lock=state/'LOCK.json'
            def acquire():lock.write_text(json.dumps({'pid':os.getpid()}))
            error=PermissionError('fixture blocked receipt replacement');error.winerror=5
            fake=SimpleNamespace(root=root,state=state,batch_id=request['batch_id'],lock=lock,acquire_lock=acquire,guard=lambda _:(_ for _ in ()).throw(error))
            # Import the actual stdlib-only launcher package; replace only its
            # CPU test guard/driver, never invoke PC probes or owned processes.
            import sys
            sys.path.insert(0,str(pkg));dmod=importlib.import_module('pc_driver')
            packet=root/'request.json';packet.write_text(json.dumps(request))
            with patch.object(dmod,'Driver',return_value=fake),patch.object(driver.subprocess,'Popen') as popen:
                self.assertEqual(driver.execute(packet),1)
            popen.assert_not_called()
            batch=json.loads((state/'mixtures/test-only/BATCH.json').read_bytes())
            receipt=batch['guide_failure_consultation']
            self.assertIn(guide.RECEIPT_RULE,receipt['applicable_rules']);self.assertTrue(receipt['action'])
            self.assertEqual(receipt['sha256'],request['guide_acknowledgment']['sha256'])
            self.assertTrue((state/'mixtures/test-only/GUIDE-START.json').exists())

    def test_both_receipt_incidents_route_and_record_action(self):
        with tempfile.TemporaryDirectory() as folder:
            self.fixture(Path(folder));error=PermissionError('BATCH.json.tmp -> BATCH.json');error.winerror=5
            cases=[(FileNotFoundError('PROGRESS.json.tmp'),guide.STORAGE_RULE),(error,guide.RECEIPT_RULE)]
            for error,rule in cases:
                receipt=guide.consult_failure(folder,'test-only',error,'Preserve failed artifacts; no retry dispatch.')
                self.assertIn(rule,receipt['applicable_rules']);self.assertIn('sha256',receipt);self.assertTrue(receipt['action'])


if __name__=='__main__':unittest.main()
