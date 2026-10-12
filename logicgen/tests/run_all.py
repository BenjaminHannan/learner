"""Run every test_* function without pytest: python tests/run_all.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_logicgen as m  # noqa: E402

fails = 0
for name in sorted(dir(m)):
    if name.startswith("test_"):
        t = time.time()
        try:
            getattr(m, name)()
            print(f"PASS {name} ({time.time() - t:.1f}s)")
        except Exception:
            import traceback
            fails += 1
            print(f"FAIL {name}")
            traceback.print_exc()
print("FAILED" if fails else "ALL PASSED")
sys.exit(1 if fails else 0)
