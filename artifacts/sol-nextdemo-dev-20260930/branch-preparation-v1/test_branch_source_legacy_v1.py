"""Synthetic CPU rejection fixtures only; never an admitted training corpus."""
import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

import branch_source_v1 as S


def fixture():
    assignments = S.expected_ids(); episodes = []; cases = []; used = set()
    options = {}
    options['I'] = []
    for b, p, r, newp in itertools.product(range(4, 10), range(6, 16), range(1, 5), range(6, 16)):
        if p == newp: continue
        old = dict(boxes=b, items_per_box=p, removed_items=r)
        new = {**old, 'items_per_box':newp}
        if min(S.numeric_value('I', old), S.numeric_value('I', new)) > 15:
            options['I'].append((old, new))
    options['P'] = []
    for a, b, n in itertools.product(range(30, 61), range(30, 61), range(2, 7)):
        if (a+b) % n or a+n > 60: continue
        options['P'].append((dict(first_batch_items=a,second_batch_items=b,number_of_packs=n),
                             dict(first_batch_items=a+n,second_batch_items=b,number_of_packs=n)))
    for split, (prefix, count) in S.SPLITS.items():
        for family in ('I', 'P'):
            for pair_index in range(count//2):
                pair = None
                for first in options[family]:
                    if any(S.digest({'family':family,'givens':g}) in used for g in first): continue
                    for second in options[family]:
                        fingerprints = [S.digest({'family':family,'givens':g}) for g in (*first,*second)]
                        if len(set(fingerprints)) != 4 or any(v in used for v in fingerprints): continue
                        answers = [S.numeric_value(family,g) for g in (*first,*second)]
                        literals = {v for g in (*first,*second) for v in g.values()}
                        if len(set(answers))==4 and not set(answers)&literals:
                            pair=(first,second);used.update(fingerprints);break
                    if pair:break
                if not pair: raise RuntimeError('Synthetic fixture construction failed')
                question='Synthetic unit fixture query '+family+' '+prefix+' '+chr(65+pair_index)
                for offset,(old,new) in enumerate(pair):
                    identity=f'{prefix}-{family}{pair_index*2+offset:02d}'
                    changed='items_per_box' if family=='I' else 'first_batch_items'
                    e=dict(id=identity,assignment=split,family=family,question=question,
                        notes=' '.join(str(v) for v in old.values()),correction=str(new[changed]),
                        missing_notes=' '.join(str(v) for k,v in old.items() if k!=changed),
                        givens=old,corrected_givens=new,lineage={'writer_model':'unit-test-double','source_instance_id':identity+'-unit-test'})
                    episodes.append(e)
                    if identity not in S.REJECTED_IDS:
                        for stage in S.STAGES:
                            numeric=stage!='missing_fact'
                            cases.append(dict(episode_id=identity,stage=stage,answerability=numeric,
                                numeric_target=str(S.numeric_value(family,old if stage=='initial' else new)) if numeric else None,
                                verification_pin={'path':'unit-test-only','sha256':'c'*64},training_eligible=numeric and split!='TEST'))
    notes=dict(schema='sol.nextdemo.branch-numeric-notes.v1',origin=S.ORIGIN,source_pool=S.POOL,assignments=assignments,episodes=episodes)
    targets=dict(schema='sol.nextdemo.branch-numeric-targets.v1',source_pool=S.POOL,cases=cases)
    all_ids=[i for values in assignments.values() for i in values]
    receipt=dict(schema='sol.nextdemo.branch-numeric-check.v1',source_pool=S.POOL,notes_sha256='a'*64,targets_sha256='b'*64,
        approved_ids=[i for i in all_ids if i not in S.REJECTED_IDS],rejected_ids=S.REJECTED_IDS,
        rejection_review_pin={'path':'unit-test-rejection','sha256':'d'*64},independent_verifier_identity='unit-test-verifier-double',
        review_pin={'path':'unit-test-review','sha256':'c'*64},source_exclusion_metadata_pins=[{'path':'unit-test-exclusions','sha256':'e'*64}],
        literal_wording_checked=True,numeric_labels_checked=True,no_answer_or_intermediate_checked=True,assignments_checked=True,
        per_field_sha256={},missing_fact_witnesses={})
    for e in episodes:
        if e['id'] in S.REJECTED_IDS:continue
        receipt['per_field_sha256'][e['id']]={k:S.digest(e[k]) for k in S.FIELDS-{'id','assignment','family'}}
        changed='items_per_box' if e['family']=='I' else 'first_batch_items'
        receipt['missing_fact_witnesses'][e['id']]={'first':e['givens'][changed],'second':e['corrected_givens'][changed]}
    return notes,targets,receipt,{'notes':'a'*64,'targets':'b'*64}


class WordTokenizerDouble:
    def encode(self,text,**kwargs): return list(range(len(text.split())))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.source=fixture()
    def fresh(self):return copy.deepcopy(self.source)
    def load(self,source=None):return S.load_source(*(source or self.source))

    def test_partial_acceptance_and_exact_placement_parity(self):
        inputs,labels=self.load()
        self.assertEqual(len(inputs),162)
        self.assertEqual({k:sum(r['assignment']==k for r in inputs) for k in S.SPLITS},dict(TRAIN=96,EXPERIENCE=42,TEST=24))
        self.assertFalse(any(r['episode_id'] in S.REJECTED_IDS for r in inputs))
        for row in inputs:
            note=S.model_inputs(row,'notebook');inline=S.model_inputs(row,'inline')
            self.assertEqual(inline,{'question':note['context']+'\n'+note['question'],'context':''})
            self.assertEqual(set(note),{'question','context'})
            self.assertNotIn('numeric_target',note);self.assertFalse(row['training_eligible'])
        missing=next(r for r in inputs if r['stage']=='missing_fact')
        self.assertNotIn('\n',missing['history'])

    def test_schedules_exclude_test_missing_and_rejected(self):
        inputs,labels=self.load()
        train=S.candidate_schedule(inputs,labels,'TRAIN');experience=S.candidate_schedule(inputs,labels,'EXPERIENCE')
        self.assertEqual(len(train),128);self.assertEqual(len(experience),16)
        self.assertEqual({i.split(':')[0] for i in experience},set(S.replay_world_ids()))
        self.assertFalse(any('missing_fact' in i or 'NE-' in i for i in train+experience))
        with self.assertRaises(ValueError):S.candidate_schedule(inputs,labels,'TEST')
        with self.assertRaises(ValueError):S.model_inputs(inputs[0],'empty_notes')

    def test_labels_and_eligibility_tampering_rejected(self):
        for mutation in ('numeric','TEST','missing'):
            n,t,r,p=self.fresh()
            target=next(c for c in t['cases'] if c['stage']=='initial' and c['episode_id'].startswith('NE-')) if mutation=='TEST' else next(c for c in t['cases'] if c['stage']==('missing_fact' if mutation=='missing' else 'initial'))
            if mutation=='numeric':target['numeric_target']='999'
            else:target['training_eligible']=True
            with self.assertRaises(ValueError):self.load((n,t,r,p))

    def test_rejected_pair_cannot_be_readmitted_or_repaired(self):
        n,t,r,p=self.fresh();r['rejected_ids']=[]
        with self.assertRaises(ValueError):self.load((n,t,r,p))
        n,t,r,p=self.fresh();r['approved_ids'].append('NX-P04')
        with self.assertRaises(ValueError):self.load((n,t,r,p))

    def test_pair_uniqueness_only_not_global_answer_uniqueness(self):
        inputs,labels=self.load();answers=[c['numeric_target'] for c in labels if c['answerability']]
        self.assertLess(len(set(answers)),len(answers))
        n,t,r,p=self.fresh();n['episodes'][1]['question']+='changed'
        r['per_field_sha256'][n['episodes'][1]['id']]['question']=S.digest(n['episodes'][1]['question'])
        with self.assertRaises(ValueError):self.load((n,t,r,p))

    def test_source_hash_origin_and_missing_witness_rejections(self):
        for mutation in ('hash','origin','witness','lineage'):
            n,t,r,p=self.fresh()
            if mutation=='hash':r['notes_sha256']='f'*64
            elif mutation=='origin':n['origin']='human-authored-development'
            elif mutation=='witness':r['missing_fact_witnesses']['NT-I00']['second']=r['missing_fact_witnesses']['NT-I00']['first']
            else:
                n['episodes'][1]['lineage']=n['episodes'][0]['lineage']
                r['per_field_sha256']['NT-I01']['lineage']=S.digest(n['episodes'][1]['lineage'])
            with self.assertRaises(ValueError):self.load((n,t,r,p))

    def test_inline_overlength_rejection_and_test_double_not_qualified(self):
        inputs,labels=self.load();audit=S.token_check(inputs,labels,WordTokenizerDouble(),'e'*64)
        self.assertFalse(audit['actual_frozen_tokenizer']);self.assertFalse(audit['execution_eligible'])
        bad=copy.deepcopy(inputs);bad[0]['history']='word '*48
        with self.assertRaises(ValueError):S.token_check(bad,labels,WordTokenizerDouble(),'e'*64)

    def test_pinned_export_and_no_overwrite(self):
        inputs,labels=self.load()
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'export';manifest=S.export_new(target,inputs,labels,{'notes':'a'*64,'targets':'b'*64})
            self.assertEqual(manifest['accepted_world_counts'],dict(TRAIN=32,EXPERIENCE=14,TEST=8))
            self.assertFalse(manifest['execution_eligible']);self.assertEqual(len(manifest['candidate_TRAIN_schedule']),128)
            self.assertTrue(all('numeric_target' not in json.loads(line) for line in (target/'TRAIN-inputs.jsonl').read_text().splitlines()))
            with self.assertRaises(ValueError):S.export_new(target,inputs,labels,{})
            path=Path(directory)/'pin.json';path.write_text('{}')
            with self.assertRaises(ValueError):S.read_pin(path,'0'*64)
            with self.assertRaises(ValueError):S.safe('/tmp/readpanel320/data')


if __name__=='__main__':unittest.main()
