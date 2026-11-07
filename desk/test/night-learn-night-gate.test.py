import datetime,importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'src/night-learn/night_gate.py'
s=importlib.util.spec_from_file_location('night_gate',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class GateTest(unittest.TestCase):
 def test_refuses_user_activity_and_daytime(self):
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,1,0),1199)
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,8,0),1200)
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,1,0),float('nan'))
if __name__=='__main__':unittest.main()
