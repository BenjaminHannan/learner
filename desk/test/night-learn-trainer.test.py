import importlib.util
import sys
import tempfile
from PIL import Image
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'src' / 'night-learn'
sys.path.insert(0,str(root))
spec = importlib.util.spec_from_file_location('night_trainer',root/'trainer.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class TrainerTests(unittest.TestCase):
    def test_time_split_and_identity(self):
        rows=[{'id':'a','timeMs':79},{'id':'b','timeMs':80}]
        train,held,cutoff=m.partition(rows,0,100)
        self.assertEqual(cutoff,80); self.assertEqual(train[0]['id'],'a'); self.assertEqual(held[0]['id'],'b')
        with self.assertRaises(ValueError): m.partition(rows+[rows[0]],0,100)
    def test_production_gate_refuses_active_user(self):
        old=m.idle_seconds
        try:
            m.idle_seconds=lambda:0
            with self.assertRaises(RuntimeError): m.production_gate()
        finally: m.idle_seconds=old
    def test_unverified_example_is_refused(self):
        with self.assertRaises(ValueError): m.load_example({'verified':False})

    def test_sparse_first_night_and_incompatible_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); frame=d/'f.png'; Image.new('RGB',(80,80),'white').save(frame)
            row=dict(id='one',timeMs=1,verified=True,frame=str(frame),intent='save',action=dict(kind='click',x=10,y=10))
            bad=d/'bad.pt'; bad.write_bytes(b'not a checkpoint')
            r=m.train(dict(startMs=0,endMs=2,examples=[row],allowSparse=True),d/'out',gate=lambda:None,steps=1,previous=bad)
            self.assertFalse(r['hasPreviousModel']); self.assertTrue(r['baselineWarning'])
            self.assertEqual(r['held'],[]); self.assertTrue((d/'out/candidate.pt').exists())

    def test_empty_night_does_not_claim_supervised_training(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.train(dict(startMs=0,endMs=1,examples=[],allowSparse=True),Path(d),gate=lambda:None,steps=10)
            self.assertEqual(r['trainingStepsPerArm'],0)
            self.assertEqual(r['train'],[]); self.assertEqual(r['held'],[])
            self.assertTrue((Path(d)/'candidate.pt').exists())

if __name__ == '__main__': unittest.main()
