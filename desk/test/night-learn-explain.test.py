import base64
import json
import importlib.util
import unittest
import urllib.error
from unittest.mock import patch
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'src' / 'night-learn' / 'explain.py'
s = importlib.util.spec_from_file_location('night_explain', p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class ExplainTests(unittest.TestCase):
    def test_uses_eyes_and_rejects_unbound_step(self):
        calls = []
        def fake(url, payload, timeout=300):
            calls.append((url, payload))
            if url == 'eyes':
                return {'ok':True, 'shape':[64,768], 'f16':base64.b64encode(bytes(64*768*2)).decode(), 'eye':'eye'}
            return {'choices':[{'message':{'content':'{"task":"t","why":"unknown","steps":[{"actionIndex":0,"intent":"open"}],"success":null,"confidence":0.5,"facts":[],"guesses":[]}'}}]}
        m.post = fake
        result = m.explain({'frames':[{'path':'/tmp/example.png','timeMs':1}], 'actions':[{'type':'click'}]}, 'eyes','brain')
        self.assertEqual(result['steps'][0]['intent'], 'open')
        self.assertEqual(calls[1][1]['messages'][0]['content'][1]['type'], 'image_features')
        with self.assertRaises(ValueError):
            m.explain({'frames':[{'path':'/tmp/example.png','timeMs':1}], 'actions':[]}, 'eyes','brain')

    def test_host_owns_complete_references_even_when_glim_invents_steps(self):
        def fake(url, payload, timeout=300):
            if url == 'eyes':
                return {'ok':True, 'shape':[64,768], 'f16':base64.b64encode(bytes(64*768*2)).decode(), 'eye':'eye'}
            return {'choices':[{'message':{'content':'{"task":"save","why":"keep changes","steps":[{"actionIndex":999,"intent":"invented"}],"success":true,"confidence":0.5,"facts":[],"guesses":[]}'}}]}
        m.post=fake
        r=m.explain({'frames':[{'path':'/tmp/f.png','timeMs':0}], 'actions':[{'kind':'click'},{'kind':'key'}]},'eyes','brain')
        self.assertEqual([s['actionIndex'] for s in r['steps']],[0,1])
        self.assertTrue(all(s['binding']=='episode-context' for s in r['steps']))
        self.assertEqual(r['unboundSteps'][0]['actionIndex'],999)
        self.assertIsNone(r['success'])

    def test_explicit_idle_scene_has_no_invented_actions(self):
        def fake(url, payload, timeout=300):
            if url == 'eyes':
                return {'ok':True, 'shape':[64,768], 'f16':base64.b64encode(bytes(64*768*2)).decode(), 'eye':'eye'}
            return {'choices':[{'message':{'content':'{"task":"idle screen","why":"unknown","intent":"observe","success":null,"confidence":0.2,"facts":[],"guesses":[]}'}}]}
        m.post=fake
        result=m.explain({'frames':[{'path':'/tmp/idle.png','timeMs':0}], 'actions':[], 'idle':True},'eyes','brain')
        self.assertEqual(result['steps'],[]); self.assertTrue(result['idle'])
        self.assertIsNone(result['success'])

    def test_background_preemption_and_partial_json_retry_within_the_owned_turn(self):
        replies=[urllib.error.HTTPError('brain',503,'busy',None,None),
                 {'choices':[{'message':{'content':'{"task":'},'finish_reason':'stop'}]},
                 {'choices':[{'message':{'content':'{"task":"saved"}'},'finish_reason':'stop'}]}]
        def fake(*args, **kwargs):
            reply=replies.pop(0)
            if isinstance(reply,Exception): raise reply
            return reply
        m.post=fake; guards=[]
        with patch.object(m.time,'sleep') as sleep:
            result=m.completion_json('brain',{},lambda:guards.append(True))
        self.assertEqual(result,{'task':'saved'}); self.assertEqual(len(guards),2); self.assertEqual(sleep.call_count,2)

    def test_desktop_frames_keep_separate_image_features_and_timestamps(self):
        calls=[]
        def fake(url,payload,timeout=300):
            calls.append((url,payload))
            if url=='eyes':
                return {'ok':True,'shape':[64,768],'f16':base64.b64encode(bytes(64*768*2)).decode(),'eye':'eye'}
            return {'choices':[{'message':{'content':'{"task":"edit","why":"save changes","intent":"save","success":null,"confidence":0.5,"facts":[],"guesses":[]}'}}]}
        m.post=fake
        result=m.explain({'frames':[{'path':'/tmp/first.png','timeMs':1000},{'path':'/tmp/last.png','timeMs':2500}],'actions':[{'kind':'key'}]},'eyes','brain')
        content=calls[-1][1]['messages'][0]['content']
        images=[x['image_features'] for x in content if x['type']=='image_features']
        self.assertEqual(len(images),2)
        self.assertTrue(all(x['shape']==[64,768] and 'clip' not in x for x in images))
        self.assertTrue(any('1.5 seconds' in x.get('text','') for x in content))
        self.assertEqual(result['steps'][0]['actionIndex'],0)

    def test_empty_multi_frame_response_retries_one_actual_frame_with_disclosed_limit(self):
        content=[{'type':'text','text':'Recorded actions: key 0'}, {'type':'image_features','image_features':{'frame':'first'}}, {'type':'image_features','image_features':{'frame':'last'}}]
        calls=[]
        def fake(url,payload,timeout=300):
            calls.append(json.loads(json.dumps(payload)))
            return {'choices':[{'message':{'content':None if len(calls)==1 else '{"task":"edit"}'},'finish_reason':'stop'}]}
        m.post=fake
        with patch.object(m.time,'sleep'), patch.object(m.time,'monotonic',side_effect=[0,121]):
            result=m.completion_json('brain',{'messages':[{'role':'user','content':content}]})
        images=[x for x in calls[1]['messages'][0]['content'] if x['type']=='image_features']
        self.assertEqual(images,[content[-1]])
        self.assertEqual(len(content),3)
        self.assertIn('last sampled recorded frame',result['visualContext'])
        self.assertIn('do not claim earlier',calls[1]['messages'][0]['content'][1]['text'])

    def test_failure_explanation_requires_failure(self):
        m.post = lambda *a, **kw: {'choices':[{'message':{'content':'{"shouldHaveDone":"a","actuallyDid":"b","whatWentWrong":"unknown","facts":[],"guesses":[],"confidence":0.2}'}}]}
        with self.assertRaises(ValueError): m.explain_failure({'judgedOutcome':'unknown','steps':[]})
        self.assertEqual(m.explain_failure({'judgedOutcome':'fail','steps':[]})['actuallyDid'],'b')

if __name__ == '__main__': unittest.main()
