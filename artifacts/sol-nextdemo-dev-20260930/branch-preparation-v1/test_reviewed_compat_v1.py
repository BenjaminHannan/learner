"""Actual-packet CPU tests. Mutations are in-memory rejection probes only."""
import copy,hashlib,json,os,sys,unittest,zipfile
from pathlib import Path
import reviewed_compat_v1 as adapter
import branch_source_v1 as loader

ARCHIVE=Path(os.environ.get('PREMONITION_REVIEWED_ZIP',str(Path(__file__).resolve().parent/'actual-reviewed-source.zip')))

class ActualPacketTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.packet=adapter.project(ARCHIVE)
  cls.n,cls.t,cls.r,cls.p,cls.q,cls.raw=cls.packet

 def valid(self,n=None,t=None,r=None):
  return adapter.check_projection(n or self.n,t or self.t,r or self.r)

 def test_actual_packet_success_162_ineligible_cases(self):
  inputs,labels=self.valid()
  self.assertEqual(len(inputs),162);self.assertEqual(len(labels),162)
  self.assertEqual(sum(c['numeric_target'] is not None for c in labels),108)
  self.assertTrue(all(r['execution_eligible'] is False and r['training_eligible'] is False for r in inputs))
  self.assertTrue(all(c['training_eligible'] is False for c in labels))
  self.assertEqual({a:sum(r['assignment']==a for r in inputs) for a in ('TRAIN','EXPERIENCE','TEST')},
    {'TRAIN':96,'EXPERIENCE':42,'TEST':24})

 def test_all_108_values_unchanged_and_no_advisory_labels(self):
  original=json.loads(self.raw['independent_targets.json'])
  lookup={(c['episode_id'],adapter.STAGES[c['stage']]):c for c in original['cases']}
  for c in self.t['cases']:
   self.assertEqual(c['numeric_target'],lookup[(c['episode_id'],c['stage'])]['numeric_target'])
   self.assertEqual(c['verification_pin'],self.r['review_pin'])
  self.assertEqual(self.q['supported_numeric_values_preserved'],108)

 def test_literal_history_roundtrip_and_documented_lineage(self):
  source=json.loads(self.raw['notes.json'])
  for old,new in zip(source['episodes'],self.n['episodes']):
   self.assertEqual(new['notes'],'\n'.join(old['notes']))
   self.assertEqual(new['missing_notes'],'\n'.join(old['missing_notes']))
   self.assertEqual(new['question'],old['question']);self.assertEqual(new['correction'],old['correction'])
   self.assertEqual(new['givens'],old['givens']);self.assertEqual(new['corrected_givens'],old['corrected_givens'])
   self.assertEqual(new['lineage']['writer_model'],old['lineage'])
   self.assertEqual(self.p['episodes'][old['id']]['original_episode'],old)
   self.assertIsNone(self.p['episodes'][old['id']]['writer_reference']['model_version'])

 def test_rejected_worlds_never_export_or_schedule(self):
  inputs,labels=self.valid();ids={r['episode_id'] for r in inputs}
  self.assertFalse(set(adapter.REJECTED)&ids)
  self.assertEqual(loader.candidate_schedule(inputs,labels,'EXPERIENCE'),
     [w+':'+s for w in loader.replay_world_ids() for s in ('initial','corrected')])
  self.assertEqual(len(loader.candidate_schedule(inputs,labels,'TRAIN')),128)
  with self.assertRaises(ValueError):loader.candidate_schedule(inputs,labels,'TEST')

 def test_review_evidence_source_hashes_and_no_model_import(self):
  hashes=json.loads(self.raw['verification_hashes.json'])
  for name,h in hashes['files'].items():self.assertEqual(adapter.byte_sha(self.raw[name]),h)
  self.assertEqual(adapter.byte_sha(ARCHIVE.read_bytes()),adapter.ARCHIVE_SHA)
  self.assertNotIn('torch',sys.modules)

 def test_recorded_witnesses_reproduce_but_do_not_relax_train_ranges(self):
  self.valid()
  with self.assertRaises(ValueError):loader.numeric_value('I',{'boxes':2,'items_per_box':1,'removed_items':1})
  self.assertEqual(loader.numeric_witness_value('I',{'boxes':2,'items_per_box':1,'removed_items':1}),1)
  with self.assertRaises(ValueError):loader.numeric_witness_value('I',{'boxes':2,'items_per_box':1,'removed_items':3})
  with self.assertRaises(ValueError):loader.numeric_witness_value('P',{'first_batch_items':1,'second_batch_items':4,'number_of_packs':2})

 def test_wrong_numeric_value_rejects_even_rehashed_copy(self):
  t=copy.deepcopy(self.t);r=copy.deepcopy(self.r)
  t['cases'][0]['numeric_target']=str(int(t['cases'][0]['numeric_target'])+1)
  r['targets_sha256']=adapter.byte_sha(adapter.json_bytes(t))
  with self.assertRaises(ValueError):self.valid(t=t,r=r)

 def test_rejected_id_in_approved_receipt_rejects(self):
  r=copy.deepcopy(self.r);r['approved_ids'].append('NX-P04')
  with self.assertRaises(ValueError):self.valid(r=r)

 def test_test_or_missing_training_eligibility_rejects(self):
  for index in (2,next(i for i,c in enumerate(self.t['cases']) if c['episode_id'].startswith('NE-'))):
   t=copy.deepcopy(self.t);r=copy.deepcopy(self.r);t['cases'][index]['training_eligible']=True
   r['targets_sha256']=adapter.byte_sha(adapter.json_bytes(t))
   with self.assertRaises(ValueError):self.valid(t=t,r=r)

 def test_missing_numeric_target_rejects(self):
  t=copy.deepcopy(self.t);r=copy.deepcopy(self.r)
  t['cases'][2]['numeric_target']='1';r['targets_sha256']=adapter.byte_sha(adapter.json_bytes(t))
  with self.assertRaises(ValueError):self.valid(t=t,r=r)

 def test_stage_or_assignment_mutation_rejects(self):
  t=copy.deepcopy(self.t);t['cases'][0]['stage']='missing';r=copy.deepcopy(self.r)
  r['targets_sha256']=adapter.byte_sha(adapter.json_bytes(t))
  with self.assertRaises(ValueError):self.valid(t=t,r=r)
  n=copy.deepcopy(self.n);n['episodes'][0]['assignment']='EXPERIENCE';r=copy.deepcopy(self.r)
  r['notes_sha256']=adapter.byte_sha(adapter.json_bytes(n))
  with self.assertRaises(ValueError):self.valid(n=n,r=r)

 def test_missing_semantic_check_rejects(self):
  r=copy.deepcopy(self.r);r['literal_wording_checked']=False
  with self.assertRaises(ValueError):self.valid(r=r)

 def test_correction_edit_breaks_original_field_pin(self):
  n=copy.deepcopy(self.n);r=copy.deepcopy(self.r);n['episodes'][0]['correction']+=' Changed.'
  r['notes_sha256']=adapter.byte_sha(adapter.json_bytes(n))
  with self.assertRaises(ValueError):self.valid(n=n,r=r)

 def test_no_unperformed_checks_promoted(self):
  self.assertFalse(self.q['actual_frozen_tokenizer_checked'])
  self.assertFalse(self.q['external_global_exclusions_checked'])
  self.assertFalse(self.q['execution_eligible']);self.assertFalse(self.q['training_eligible'])
  self.assertIn('NOT RECORDED',self.p['writer_model_version'])
  inputs,labels=self.valid()
  class TooLong:
   def encode(self,text,add_special_tokens=False):return [1]*48
  with self.assertRaises(ValueError):loader.token_check(inputs,labels,TooLong(),'0'*64,actual_frozen_tokenizer=False)

 def test_initial_only_exact_selection(self):
  inputs,labels=adapter.initial_only_selection(*self.valid())
  self.assertEqual(len(inputs),40);self.assertEqual(len(labels),40)
  self.assertEqual(sum(r['assignment']=='TRAIN' for r in inputs),32)
  self.assertEqual(sum(r['assignment']=='TEST' for r in inputs),8)
  self.assertTrue(all(r['stage']=='initial' for r in inputs))
  self.assertTrue(all(c['training_eligible'] is False for c in labels))
  self.assertTrue(all(r['episode_id'] not in adapter.REJECTED for r in inputs))

 def test_initial_only_export_four_pass_unreleased(self):
  import tempfile
  tmp=tempfile.mkdtemp(prefix='premonition-compat-test-',dir='/tmp')
  if True:
   q,m=adapter.export(ARCHIVE,Path(tmp)/'new',stage_selection='initial-only-v2')
   self.assertEqual(m['counts'],{'TRAIN':32,'EXPERIENCE':0,'TEST':8})
   self.assertEqual(len(m['candidate_TRAIN_schedule']),128)
   self.assertEqual(m['candidate_EXPERIENCE_ids'],[])
   self.assertFalse(m['execution_eligible']);self.assertFalse(m['training_eligible'])
   self.assertFalse(m['correction_claim'])
   self.assertEqual(m['candidate_fit_spec']['evaluation_calls'],64)
   self.assertEqual(len(json.loads((Path(tmp)/'new'/'NORMALIZED-TARGETS.json').read_text())['cases']),162)

if __name__=='__main__':unittest.main(verbosity=2)
