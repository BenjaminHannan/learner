"""CPU contracts/numeric initial-function parity; never an optimizer/model fit."""
import ast
from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'scripts/sol_cloud_numeric_fit_v1.py'
spec=importlib.util.spec_from_file_location('numeric_fit_under_test',SOURCE)
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
PLAN=json.loads((Path(__file__).parent/'PLAN-v3.json').read_text())


class Contracts(unittest.TestCase):
    def test_cpu_import_and_pc310_syntax(self):
        ast.parse(SOURCE.read_text(),feature_version=(3,10))
        self.assertNotIn('torch',driver.__dict__)

    def test_exact_protocol_rejects_loss_architecture_budget_drift(self):
        driver.validate_plan(PLAN)
        for key,value in [('objective','CE-plus-aux'),('rounds',5),('primary_metric','numeric_constant_exact'),
                          ('checkpoint_updates',[200,800]),('input_scope','question-and-audit')]:
            changed=copy.deepcopy(PLAN);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):driver.validate_plan(changed)
        changed=copy.deepcopy(PLAN);changed['optimizer']['reset']=False
        with self.assertRaises(ValueError):driver.validate_plan(changed)

    def test_exact_schedule_and_token_selection(self):
        self.assertEqual(driver.token_gate(PLAN)['checks_passed'],2412)
        seal=driver.read_pin(ROOT/PLAN['selection']['path'],PLAN['selection']['sha256'],ROOT)
        self.assertEqual(seal['selected_ids'],PLAN['selected_ids'])
        self.assertEqual(len(set(PLAN['selected_ids'])),16)
        for seed in (0,1):
            pin=PLAN['schedules'][str(seed)];schedule=driver.read_pin(ROOT/pin['path'],pin['sha256'],ROOT)
            self.assertEqual(Counter(schedule),Counter({identity:50 for identity in PLAN['selected_ids']}))
        for row in seal['selected_rows']:
            self.assertLessEqual(len(row['question_token_ids_before_EOS']),48)
            self.assertEqual(row['question_token_ids_with_EOS'],row['question_token_ids_before_EOS']+[7])
            self.assertEqual(row['target_token_ids_with_EOS'],row['target_token_ids_before_EOS']+[7])
            self.assertEqual(row['model_input_keys'],['question']);self.assertEqual(row['notebook_tokens'],0)
        self.assertEqual(PLAN['diagnostic_updates'],[0,200,400,800])

    def test_watcher_refusal_before_any_read_or_import(self):
        with patch.dict(os.environ,{},clear=True),patch.object(driver,'read_pin') as read:
            with self.assertRaisesRegex(RuntimeError,'watcher'):driver.gates(SimpleNamespace())
            read.assert_not_called()

    def test_protected_literal_and_symlink_refused_before_read(self):
        with patch.object(Path,'open') as opened:
            for name in ('handoff/uncle-questions/a.json','readpanel320.json','STOP88.json','x/blind/y'):
                with self.subTest(name=name),self.assertRaises(ValueError):driver.sha(ROOT/name)
            opened.assert_not_called()
        with patch.object(Path,'resolve',return_value=ROOT/'x/sealed-panels/z'),patch.object(Path,'open') as opened:
            with self.assertRaises(ValueError):driver.sha(ROOT/'artifacts/benign.json')
            opened.assert_not_called()

    def test_bounded_sink_rejects_before_write_and_restores_seek(self):
        stream=io.BytesIO();events=[];sink=driver.BoundedFileSink(stream,4,events.append)
        sink.write(b'12');self.assertEqual(stream.getvalue(),b'12')
        with self.assertRaises(RuntimeError):sink.write(b'345')
        self.assertEqual(stream.getvalue(),b'12')
        with self.assertRaises(RuntimeError):sink.seek(5)
        self.assertEqual(stream.tell(),2)
        sink.seek(0);sink.write(b'3');sink.flush()
        self.assertEqual(stream.getvalue(),b'32');self.assertEqual(events,[2,2,2])

    def test_numeric_secondary_cannot_accept_expression_or_prose(self):
        self.assertTrue(driver.numeric_exact(' 2.0 ','2'))
        self.assertTrue(driver.numeric_exact('1/2','1/2'))
        for text in ('1+1','The answer is 2','2.','1/0','__import__("os")','02','nan'):
            with self.subTest(text=text):self.assertFalse(driver.numeric_exact(text,'2'))
        self.assertEqual(PLAN['primary_metric'],'target_ids_plus_observed_EOS_exact')

    def test_mocked_optimizer_exact_single_ce_backward_no_aux(self):
        events=[]
        ce=SimpleNamespace(backward=lambda:events.append('CE.backward'))
        opt=SimpleNamespace(step=lambda:events.append('AdamW.step'))
        torch=SimpleNamespace(isfinite=lambda _:True,nn=SimpleNamespace(utils=SimpleNamespace(
            clip_grad_norm_=lambda ps,cap,**kw:events.append(('clip',cap,kw)) or 2.5)))
        result=driver.numeric_optimizer_step(ce,opt,['numeric parameter'],torch,lambda:events.append('participation'))
        self.assertEqual(result,2.5)
        self.assertEqual(events,['CE.backward','participation',('clip',1,{'error_if_nonfinite':True}),'AdamW.step'])
        for _ in range(799):driver.numeric_optimizer_step(ce,opt,[],torch)
        self.assertEqual(events.count('AdamW.step'),800)
        self.assertEqual(events.count('CE.backward'),800)

    def test_mocked_nonfinite_or_clip_failure_never_steps(self):
        events=[];ce=SimpleNamespace(backward=lambda:events.append('backward'))
        opt=SimpleNamespace(step=lambda:events.append('step'))
        api=SimpleNamespace(isfinite=lambda _:False)
        with self.assertRaisesRegex(RuntimeError,'nonfinite'):driver.numeric_optimizer_step(ce,opt,[],api)
        self.assertEqual(events,[])
        def clip(*args,**kwargs):raise RuntimeError('numeric clip failure')
        api=SimpleNamespace(isfinite=lambda _:True,nn=SimpleNamespace(utils=SimpleNamespace(clip_grad_norm_=clip)))
        with self.assertRaisesRegex(RuntimeError,'clip'):driver.numeric_optimizer_step(ce,opt,[],api)
        self.assertEqual(events,['backward'])

    def test_connected_source_seed_lineage_and_table_rejection(self):
        b=PLAN['warmstart']['tuples']['0']
        raw={'arm':'connected','seed':0,'update':200,'binding':dict(b),'core':{},'reader':{},'prefix':{},'optimizer':{}}
        self.assertIs(driver.validate_connected(raw,0,b),raw)
        for key,value in [('seed',1),('arm','TABLE'),('update',800),('table',{})]:
            bad=dict(raw);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):driver.validate_connected(bad,0,b)

    def test_supervisor_direct_base_pid_metadata_no_interposed_guard(self):
        worker=SimpleNamespace(pid=4321,wait=lambda timeout:0)
        with patch.object(driver.sys,'_base_executable','native-base-python'),patch.object(driver.subprocess,'Popen',return_value=worker) as spawn:
            self.assertEqual(driver.supervise(SimpleNamespace()),0)
            argv=spawn.call_args.args[0];self.assertEqual(argv[0],'native-base-python');self.assertEqual(argv[-1],'--worker')
            self.assertIn('SOL_NUMERIC_FIT_SUPERVISOR_PID',spawn.call_args.kwargs['env'])


class StorageAndEOS(unittest.TestCase):
    class RawIDs:
        def __init__(self,rows):self.rows=rows
        def tolist(self):return copy.deepcopy(self.rows)
    class SpyLM:
        def __init__(self,rows):self.rows=rows;self.calls=[]
        def generate(self,**kwargs):
            self.calls.append(kwargs)
            return StorageAndEOS.RawIDs(self.rows)
    class NativeStripDecoder:
        eos_id=7;bos_id=1
        def __init__(self,rows):
            self.lm=StorageAndEOS.SpyLM(rows);self.prefix_and_BOS=object();self.mask=object()
        def generate(self,packet,max_tokens=32):
            # Spy equivalent of the exact existing native call and EOS strip.
            ids=self.lm.generate(inputs_embeds=self.prefix_and_BOS,attention_mask=self.mask,
                max_new_tokens=max_tokens,do_sample=False,use_cache=True,bos_token_id=1,eos_token_id=7,pad_token_id=7)
            return [row[:row.index(7)] if 7 in row else row for row in ids.tolist()]

    def observed(self,raw):
        decoder=self.NativeStripDecoder(raw)
        result=driver.observe_generation(decoder,object(),32)
        return decoder,result

    def test_same_native_call_observed_EOS_parity_and_class_method_restore(self):
        decoder,result=self.observed([[42,7]])
        self.assertEqual(result['MODEL_raw_generate_ids'],[[42,7]])
        self.assertEqual(result['MODEL_native_decoder_return'],[[42]])
        self.assertEqual(result['termination_reason'],'observed_EOS')
        self.assertTrue(driver.score_observed_generation(result,[42,7],7))
        self.assertEqual(len(decoder.lm.calls),1)
        self.assertIs(decoder.lm.calls[0]['inputs_embeds'],decoder.prefix_and_BOS)
        self.assertIs(decoder.lm.calls[0]['attention_mask'],decoder.mask)
        self.assertNotIn('generate',vars(decoder.lm))
        self.assertEqual(decoder.lm.generate.__func__,self.SpyLM.generate)

    def test_no_EOS_max_tokens_multiple_EOS_multiple_sequences_and_prose_ids_fail(self):
        cases=[([[42]],'terminated_without_observed_EOS'),([[42]*32],'max_new_tokens_without_EOS'),
               ([[42,7,7]],'invalid_multiple_EOS'),([[42,7,99]],'invalid_tokens_after_EOS'),
               ([[42,7],[42,7]],'invalid_or_multiple_output_sequences'),
               ([[101,42,7]],'observed_EOS'),([[-1,7]],'invalid_or_multiple_output_sequences')]
        for raw,reason in cases:
            with self.subTest(raw=raw):
                _,result=self.observed(raw)
                self.assertEqual(result['termination_reason'],reason)
                self.assertFalse(driver.score_observed_generation(result,[42,7],7))

    def test_instance_override_and_exception_restore_no_extra_call(self):
        decoder=self.NativeStripDecoder([[42,7]])
        original=decoder.lm.generate
        def override(**kwargs):return original(**kwargs)
        decoder.lm.generate=override
        result=driver.observe_generation(decoder,object(),32)
        self.assertIs(decoder.lm.generate,override);self.assertTrue(result['observed_EOS'])
        def failure(**kwargs):raise RuntimeError('native generation failure')
        decoder.lm.generate=failure
        result=driver.observe_generation(decoder,object(),32)
        self.assertIs(decoder.lm.generate,failure)
        self.assertEqual(result['native_generate_call_count'],1)
        self.assertEqual(result['generation_error']['error_type'],'RuntimeError')
        self.assertFalse(driver.score_observed_generation(result,[42,7],7))

    def test_duplicate_or_preexisting_output_refused_before_serializer(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            arm=Path(temporary)/'loop';driver.require_new_output(arm);arm.mkdir()
            with self.assertRaises(RuntimeError):driver.require_new_output(arm)
            target=arm/'final-resume.pt';target.write_bytes(b'prior numeric evidence')
            with self.assertRaises(RuntimeError):driver.save_new_atomic_file(target,1024,lambda _:self.fail('serializer called'),lambda _:None)
            self.assertEqual(target.read_bytes(),b'prior numeric evidence')
            target.unlink();target.with_suffix('.pt.tmp').write_bytes(b'failed numeric extent')
            with self.assertRaises(RuntimeError):driver.save_new_atomic_file(target,1024,lambda _:self.fail('serializer called'),lambda _:None)

    def test_actual_first_write_highwater_one_file_then_rename(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root=Path(temporary);target=root/'final-resume.pt';highwater=[]
            def before(extent):
                files=list(root.iterdir())
                self.assertFalse(target.exists());self.assertEqual(len(files),1)
                self.assertEqual(files[0].name,'final-resume.pt.tmp')
                highwater.append(max(files[0].stat().st_size,extent))
            def serialize(sink):sink.write(bytes(range(32)));sink.write(bytes(range(32)))
            driver.save_new_atomic_file(target,64,serialize,before)
            self.assertEqual(target.stat().st_size,64)
            self.assertEqual([p.name for p in root.iterdir()],['final-resume.pt'])
            self.assertEqual(max(highwater),64)
            self.assertEqual(driver.allocated_bytes(root,16),64)

    def test_atomic_extent_failure_preserves_partial_bytes_without_destination(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            root=Path(temporary);target=root/'final-resume.pt'
            def serialize(sink):sink.write(b'12');sink.write(b'345')
            with self.assertRaises(RuntimeError):driver.save_new_atomic_file(target,4,serialize,lambda _:None)
            self.assertFalse(target.exists());self.assertEqual((root/'final-resume.pt.tmp').read_bytes(),b'12')

    def test_retained_seed0_is_charged_by_fresh_seed1_free_not_double_subtracted(self):
        peak=540*driver.MIB;shared=8*driver.MIB;base=driver.RESERVE+2*peak+shared
        first=driver.resource_account(base,0,0,2*peak,0)
        self.assertTrue(first['passed'])
        retained=520*driver.MIB
        # A completed prior pair contributes only retained bytes, no future writes.
        second=driver.resource_account(base-retained-shared,retained,0,peak,shared)
        self.assertTrue(second['passed']);self.assertEqual(second['other_seed_retained_allocated_bytes'],retained)
        self.assertEqual(second['startup_free_floor_bytes'],driver.RESERVE+peak)
        blocked=driver.resource_account(driver.RESERVE+peak-1,retained,0,peak,shared)
        self.assertFalse(blocked['passed'])
        within_same_pair=driver.resource_account(driver.RESERVE+peak-108*driver.MIB,retained,108*driver.MIB,peak-108*driver.MIB,shared)
        self.assertTrue(within_same_pair['passed'])
        self.assertEqual(PLAN['budget']['planned_pair_peak_bytes'],540*driver.MIB)
        self.assertEqual(PLAN['budget']['pair_cap_bytes'],1280*driver.MIB)
        self.assertEqual(PLAN['budget']['planned_matrix_peak_bytes'],1088*driver.MIB)
        self.assertEqual(first['startup_free_floor_bytes'],2214592512)
        with self.assertRaises(RuntimeError):driver.resource_account(base,0,0,2*peak,shared+1)
        oversized_prior=544*driver.MIB
        self.assertFalse(driver.resource_account(base-oversized_prior-shared,oversized_prior,0,peak,shared)['passed'])

    def test_full_matrix_future_bounds_credit_only_exact_closed_plan(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            matrix=Path(temporary)/'matrix';digest='a'*64;unit=16
            remaining,closed=driver.remaining_matrix_peak(matrix,PLAN,unit,digest)
            self.assertEqual(remaining,1080*driver.MIB);self.assertEqual(closed,[])
            pair=matrix/'seed0'
            for arm in ('loop','plain'):
                out=pair/arm;out.mkdir(parents=True)
                (out/'CLOSED.json').write_text(json.dumps({'closed':True,'optimizer_updates':800,'seed':0,'arm':arm,'plan_sha256':digest}))
                (out/'final-resume.pt').write_bytes(b'numeric fixture')
            with patch.object(driver,'OWN',Path(temporary)):
                remaining,closed=driver.remaining_matrix_peak(matrix,PLAN,unit,digest)
                self.assertEqual(remaining,540*driver.MIB);self.assertEqual(len(closed),2)
                with self.assertRaises(RuntimeError):driver.remaining_matrix_peak(matrix,PLAN,unit,'b'*64)

    def test_raw_physical_append_extent_counts_existing_cluster_once(self):
        # The runner charges allocated extents rather than only JSON byte lengths.
        allocated=lambda size:((size+4095)//4096)*4096
        existing=4096;old=100;addition=50
        self.assertEqual(existing-allocated(old)+allocated(old+addition),4096)
        self.assertEqual(existing-allocated(old)+allocated(old+4100),8192)
        source=SOURCE.read_text()
        self.assertIn('prospective_raw=raw_bytes-allocated(old_size)+allocated',source)
        self.assertIn('if prospective_raw>',source)


class NumericInitialFunction(unittest.TestCase):
    def test_real_existing_core_numeric_initial_parity_no_lm_no_optimizer(self):
        sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
        import torch
        from sol_spatial_attention_core import N
        from sol_spatial_poc_ordered_v2 import OrderedAttentionReasoner,OrderedPlainAttentionReasoner
        from sol_spatial_poc_ordered_train_api_v2 import fixed4_training
        from scripts.sol_stop_ordered_api2 import ordered_attention_math
        torch.set_num_threads(1);torch.manual_seed(0)
        loop=OrderedAttentionReasoner(N.Net('loop'),experts=8,active=2).eval()
        plain=OrderedPlainAttentionReasoner(loop).eval()
        self.assertEqual(len(loop.blocks),2);self.assertEqual(len(plain.blocks),8)
        self.assertNotEqual(id(plain.blocks[0]),id(plain.blocks[2]))
        self.assertEqual(plain.experts_count,8);self.assertEqual(plain.active_count,2)
        # Numeric tensor fixture only: no tokenizer, English model, or text data.
        with torch.no_grad(),ordered_attention_math():
            for length in (1,7,49):
                query=torch.arange(length*256,dtype=torch.float32).reshape(1,1,length,256)/1024
                mask=torch.ones(1,length,dtype=torch.bool)
                a,_,_=fixed4_training(loop,query,None,query_mask=mask)
                b,_,_=fixed4_training(plain,query,None,query_mask=mask)
                self.assertTrue(torch.equal(a,b),length)
        del loop,plain


if __name__=='__main__':unittest.main()
