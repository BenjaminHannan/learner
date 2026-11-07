import base64
import importlib.util
import unittest
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

    def test_failure_explanation_requires_failure(self):
        m.post = lambda *a, **kw: {'choices':[{'message':{'content':'{"shouldHaveDone":"a","actuallyDid":"b","whatWentWrong":"unknown","facts":[],"guesses":[],"confidence":0.2}'}}]}
        with self.assertRaises(ValueError): m.explain_failure({'judgedOutcome':'unknown','steps':[]})
        self.assertEqual(m.explain_failure({'judgedOutcome':'fail','steps':[]})['actuallyDid'],'b')

if __name__ == '__main__': unittest.main()
