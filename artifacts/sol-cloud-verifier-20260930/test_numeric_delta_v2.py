"""Narrow independent stdlib tests: native decoder AST with numeric spies only."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path('/workspace/learner')
spec=importlib.util.spec_from_file_location('numeric_delta_under_test',ROOT/'scripts/sol_cloud_numeric_fit_v1.py')
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)

class Array:
    def __init__(self,shape,ids=None):self.shape=shape;self.ids=ids;self.dtype='float32';self.device='cpu'
    def __len__(self):return self.shape[0]
    def to(self,*args,**kwargs):return self
    def tolist(self):return self.ids
class Embedding:
    weight=SimpleNamespace(dtype='float32')
    def __call__(self,ids):return Array((1,1,1))
class SpyLM:
    def __init__(self,raw):self.raw=raw;self.calls=[]
    def get_input_embeddings(self):return Embedding()
    def generate(self,*args,**kwargs):
        self.calls.append((args,kwargs));return Array((1,len(self.raw)),[list(self.raw)])

# Execute the exact existing native generate definition; only tensor primitives
# and LM generation are numeric spies. No Torch/model/forward invocation.
native_source=(ROOT/'scripts/sol_translator_english_v6.py').read_text()
native_tree=ast.parse(native_source)
native_class=next(x for x in native_tree.body if isinstance(x,ast.ClassDef) and x.name=='FrozenEnglishDecoder')
native=copy.deepcopy(next(x for x in native_class.body if isinstance(x,ast.FunctionDef) and x.name=='generate'))
native.decorator_list=[]
fake_torch=SimpleNamespace(long='long',full=lambda shape,*a,**k:Array(shape),
    cat=lambda arrays,dim=0:Array((1,9,1)),ones=lambda shape,**kwargs:Array(shape))
namespace={'torch':fake_torch}
exec(compile(ast.fix_missing_locations(ast.Module(body=[native],type_ignores=[])),'exact_native_generate','exec'),namespace)
class NativeDecoder:
    generate=namespace['generate']
    eos_id=7;bos_id=1
    def __init__(self,raw):self.lm=SpyLM(raw);self.packet=None
    def eval(self):return self
    def adapter(self,packet):self.packet=packet;return Array((1,8,1))

class Delta(unittest.TestCase):
    def observe(self,raw,target=(42,7),limit=32):
        decoder=NativeDecoder(raw);packet=object()
        observed=D.observe_generation(decoder,packet,max_tokens=limit)
        self.assertEqual(len(decoder.lm.calls),1)
        self.assertIs(decoder.packet,packet)
        self.assertNotIn('generate',vars(decoder.lm))
        args,kwargs=decoder.lm.calls[0]
        self.assertEqual(args,())
        self.assertEqual(kwargs['max_new_tokens'],limit)
        self.assertEqual(kwargs['eos_token_id'],7)
        self.assertEqual(kwargs['bos_token_id'],1)
        self.assertFalse(kwargs['do_sample']);self.assertTrue(kwargs['use_cache'])
        self.assertEqual(set(kwargs),{'inputs_embeds','attention_mask','max_new_tokens','do_sample','use_cache','bos_token_id','eos_token_id','pad_token_id'})
        return observed,D.score_observed_generation(observed,list(target),7)

    def test_same_native_call_exact_target_actual_EOS(self):
        observed,scored=self.observe([42,7]);self.assertTrue(scored)
        self.assertEqual(observed['MODEL_native_decoder_return'],[[42]])
        self.assertEqual(observed['MODEL_raw_generate_ids'],[[42,7]])
        self.assertEqual(observed['termination_reason'],'observed_EOS')
    def test_correct_trimmed_target_without_EOS_fails(self):
        observed,scored=self.observe([42]);self.assertFalse(scored)
        self.assertEqual(observed['MODEL_native_decoder_return'],[[42]])
        self.assertEqual(observed['termination_reason'],'terminated_without_observed_EOS')
    def test_maximum_extent_without_EOS_fails(self):
        observed,scored=self.observe([42]*32);self.assertFalse(scored)
        self.assertEqual(observed['termination_reason'],'max_new_tokens_without_EOS')
    def test_multiple_EOS_and_postEOS_tokens_fail(self):
        for ids,reason in [([42,7,7],'invalid_multiple_EOS'),([42,7,99],'invalid_tokens_after_EOS')]:
            with self.subTest(ids=ids):
                observed,scored=self.observe(ids);self.assertFalse(scored);self.assertEqual(observed['termination_reason'],reason)
    def test_wrong_tokens_and_prose_containing_target_fail(self):
        for ids in ([99,7],[30,42,7],[42,30,7],[7],[42,6],[42]*33):
            with self.subTest(ids=ids):self.assertFalse(self.observe(ids)[1])
    def test_original_instance_method_restored_on_success(self):
        dec=NativeDecoder([42,7]);old=dec.lm.generate;dec.lm.generate=old
        self.assertTrue(D.score_observed_generation(D.observe_generation(dec,object()),[42,7],7))
        self.assertIs(vars(dec.lm)['generate'],old)
    def test_instance_and_class_arrangements_restored_on_native_error(self):
        for instance in (False,True):
            dec=NativeDecoder([42,7])
            def failing(*args,**kwargs):raise RuntimeError('numeric spy failure')
            if instance:dec.lm.generate=failing
            else:dec.lm.raw=None
            before=dict(vars(dec.lm));observed=D.observe_generation(dec,object())
            self.assertEqual('generate' in vars(dec.lm),'generate' in before)
            if instance:self.assertIs(vars(dec.lm)['generate'],before['generate'])
            self.assertFalse(D.score_observed_generation(observed,[42,7],7))
            self.assertIsNotNone(observed['generation_error'])
    def test_duplicate_native_generate_calls_fail_primary(self):
        dec=NativeDecoder([42,7]);native=dec.generate
        def twice(packet,max_tokens):native(packet,max_tokens=max_tokens);return native(packet,max_tokens=max_tokens)
        dec.generate=twice
        observed=D.observe_generation(dec,object())
        self.assertEqual(observed['native_generate_call_count'],2)
        self.assertFalse(D.score_observed_generation(observed,[42,7],7))
    def test_absent_atomic_destination_single_physical_file(self):
        with TemporaryDirectory() as root:
            base=Path(root);dest=base/'resume.pt';counts=[];inodes=[]
            def serialize(sink):
                counts.append(len(list(base.iterdir())))
                inodes.append((base/'resume.pt.tmp').stat().st_ino)
                sink.write(b'42'*512)
            D.save_new_atomic_file(dest,1024,serialize,lambda extent:counts.append(len(list(base.iterdir()))))
            self.assertEqual(dest.read_bytes(),b'42'*512)
            self.assertEqual(len(list(base.iterdir())),1)
            self.assertEqual(max(counts),1)
            self.assertEqual(dest.stat().st_ino,inodes[0])
    def test_prior_destination_temporary_or_output_never_overwritten(self):
        with TemporaryDirectory() as root:
            base=Path(root);dest=base/'resume.pt';calls=[]
            for old in (dest,base/'resume.pt.tmp'):
                old.write_bytes(b'preserved')
                with self.assertRaises(RuntimeError):D.save_new_atomic_file(dest,1024,lambda sink:calls.append('called'),lambda extent:None)
                self.assertEqual(old.read_bytes(),b'preserved');old.unlink()
            out=base/'arm';out.mkdir()
            with self.assertRaises(RuntimeError):D.require_new_output(out)
            self.assertEqual(calls,[])
    def test_retained_seed0_is_charged_to_fresh_seed1_free_space(self):
        peak=540*D.MIB;retained=524*D.MIB;shared=8*D.MIB
        good=D.resource_account(D.RESERVE+peak+shared,retained,0,peak,0)
        bad=D.resource_account(D.RESERVE+peak+shared-1,retained,0,peak,0)
        self.assertTrue(good['passed']);self.assertFalse(bad['passed'])
        self.assertEqual(good['other_seed_retained_allocated_bytes'],retained)
        self.assertEqual(good['additional_whole_matrix_peak_bytes'],peak+shared)
        same_pair=D.resource_account(D.RESERVE+peak-108*D.MIB+shared,retained+108*D.MIB,108*D.MIB,peak-108*D.MIB,0)
        self.assertTrue(same_pair['passed'])
        self.assertEqual(same_pair['other_seed_retained_allocated_bytes'],retained)
        first=D.resource_account(2214592512,0,0,2*peak,0)
        self.assertTrue(first['passed']);self.assertEqual(first['startup_free_floor_bytes'],2214592512)
        self.assertFalse(D.resource_account(2214592511,0,0,2*peak,0)['passed'])
        self.assertTrue(D.resource_account(2214592512-4*D.MIB,0,0,2*peak,4*D.MIB)['passed'])
        with self.assertRaises(RuntimeError):D.resource_account(10**12,0,0,0,shared+1)
    def test_full_matrix_future_writes_credit_only_closed_arms(self):
        plan={'seeds':[0,1],'arms':['loop','plain'],'budget':{'checkpoint_cap_bytes':{'loop':108*D.MIB,'plain':416*D.MIB},'raw_cap_bytes_per_pair':16*D.MIB}}
        with TemporaryDirectory(dir=ROOT/'artifacts/sol-cloud-verifier-20260930') as root:
            matrix=Path(root)
            with patch.object(D,'OWN',matrix):
                remaining,closed=D.remaining_matrix_peak(matrix,plan,4096,'0'*64)
                self.assertEqual(remaining,1080*D.MIB);self.assertEqual(closed,[])
                out=matrix/'seed0/loop';out.mkdir(parents=True)
                (out/'CLOSED.json').write_text(json.dumps({'closed':True,'optimizer_updates':800,'seed':0,'arm':'loop','plan_sha256':'0'*64}))
                remaining,closed=D.remaining_matrix_peak(matrix,plan,4096,'0'*64)
                self.assertEqual(remaining,972*D.MIB-4096);self.assertEqual(closed,[{'seed':0,'arm':'loop'}])
                with self.assertRaises(RuntimeError):D.remaining_matrix_peak(matrix,plan,4096,'1'*64)
                (out/'CLOSED.json').write_text(json.dumps({'closed':True,'optimizer_updates':799,'seed':0,'arm':'loop','plan_sha256':'0'*64}))
                with self.assertRaises(RuntimeError):D.remaining_matrix_peak(matrix,plan,4096,'0'*64)
    def test_exact_raw_writer_allocated_cap_and_append_credit(self):
        tree=ast.parse((ROOT/'scripts/sol_cloud_numeric_fit_v1.py').read_text())
        run=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='run')
        writer=copy.deepcopy(next(x for x in ast.walk(run) if isinstance(x,ast.FunctionDef) and x.name=='write_json'))
        with TemporaryDirectory() as root:
            pair=Path(root);out=pair/'loop';out.mkdir()
            ns={'json':json,'os':os,'pair':pair,'out':out,'plan':{'budget':{'raw_cap_bytes_per_pair':4096}},'allocated':lambda size:(size+4095)//4096*4096,'guard':lambda extra:None}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[writer],type_ignores=[])),'exact_raw_writer','exec'),ns)
            write=ns['write_json'];write('TRAIN.jsonl',{'x':42},True);before=(out/'TRAIN.jsonl').read_bytes()
            write('TRAIN.jsonl',{'x':42},True)
            self.assertEqual((out/'TRAIN.jsonl').read_bytes(),before+before)
            with self.assertRaises(RuntimeError):write('SECOND.json',{'x':42})
            self.assertFalse((out/'SECOND.json').exists())
            with self.assertRaisesRegex(RuntimeError,'64KiB'):write('CLOSED.json',{'x':'0'*65537})
            self.assertFalse((out/'CLOSED.json').exists())
    def test_training_graph_and_optimizer_loop_AST_unchanged(self):
        old=ast.parse((ROOT/'artifacts/sol-cloud-numeric-fit-20260930/RUNNER-SOURCE-v1.py').read_text())
        new=ast.parse((ROOT/'scripts/sol_cloud_numeric_fit_v1.py').read_text())
        def funcs(tree):return {x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
        old_run=funcs(old)['run'];new_run=funcs(new)['run']
        for name in ('latent','graph','state_identity','tensor_hash','timeout'):
            a=next(x for x in ast.walk(old_run) if isinstance(x,ast.FunctionDef) and x.name==name)
            b=next(x for x in ast.walk(new_run) if isinstance(x,ast.FunctionDef) and x.name==name)
            self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
        for name in ('numeric_optimizer_step','numeric_exact','supervise'):
            self.assertEqual(ast.dump(funcs(old)[name],include_attributes=False),ast.dump(funcs(new)[name],include_attributes=False))
        def loop(fn):return next(x for x in fn.body if isinstance(x,ast.Try)).body
        def update_loop(fn):return next(x for x in loop(fn) if isinstance(x,ast.For) and isinstance(x.target,ast.Tuple) and [a.id for a in x.target.elts]==['step','identity_id'])
        self.assertEqual(ast.dump(update_loop(old_run),include_attributes=False),ast.dump(update_loop(new_run),include_attributes=False))

if __name__=='__main__':unittest.main(verbosity=2)
