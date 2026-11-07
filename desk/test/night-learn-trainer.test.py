import importlib.util
import sys
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

if __name__ == '__main__': unittest.main()
