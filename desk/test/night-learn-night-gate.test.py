import datetime,importlib.util,unittest
from unittest.mock import patch
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'src/night-learn/night_gate.py'
s=importlib.util.spec_from_file_location('night_gate',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class GateTest(unittest.TestCase):
 def test_refuses_user_activity_and_daytime(self):
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,1,0),1199)
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,8,0),1200)
  with self.assertRaises(RuntimeError):m.check(datetime.datetime(2026,11,7,1,0),float('nan'))
 def test_dry_context_is_explicit_and_cleared_for_production(self):
  for dry in (True,False):
   argv=['night_gate.py']+(['--dry-run'] if dry else [])+['/usr/bin/true']
   captured=[]
   with patch.object(m.sys,'argv',argv), patch.object(m.os,'getppid',return_value=123), patch.object(m.Path,'read_text',return_value='NIGHT-LEARN 123 now'), patch.object(m,'check'), patch.object(m,'idle_seconds',return_value=1200), patch.dict(m.os.environ,{'NIGHT_LEARN_DRY_RUN':'stale'}), patch.object(m.os,'execv',side_effect=lambda *args:captured.append(m.os.environ.get('NIGHT_LEARN_DRY_RUN'))):
    m.main()
   self.assertEqual(captured,['1' if dry else None])
if __name__=='__main__':unittest.main()
