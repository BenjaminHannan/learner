"""CPU test of the Message Batches path and its direct-call fallback in fix.py, with a fake anthropic client. Usage: python3 skillsleep/tests/test_fix.py"""
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).parent.parent))
import fix

fix.POLL_S = 0.01


class Batches:
    def __init__(self, ends_after, fail_create=False, drop=()):
        self.n = 0; self.ends_after = ends_after; self.cancelled = False; self.fail_create = fail_create; self.drop = drop

    def create(self, requests):
        if self.fail_create:
            raise RuntimeError("boom")
        self.reqs = requests; assert all(r["params"]["model"] == "claude-sonnet-5-5" for r in requests)
        return N(id="b1", processing_status="in_progress")

    def retrieve(self, i):
        self.n += 1
        return N(id=i, processing_status="ended" if self.n >= self.ends_after else "in_progress")

    def cancel(self, i):
        self.cancelled = True

    def results(self, i):
        return [N(custom_id=r["custom_id"], result=N(type="succeeded", message=N(content=[N(text=" batch " + r["custom_id"] + " ")])))
                for r in self.reqs if r["custom_id"] not in self.drop]


def client(**kw):
    c = N(messages=N(batches=Batches(**kw), create=lambda **k: N(content=[N(text=" direct ")])))
    return c


P = {"3": "p3", "5": "p5"}
c = client(ends_after=2); assert fix.critiques(c, P) == {"3": "batch t3", "5": "batch t5"} and not c.messages.batches.cancelled
c = client(ends_after=2, drop=("t5",)); assert fix.critiques(c, P) == {"3": "batch t3", "5": "direct"}  # one request errored in the batch
fix.BATCH_WAIT_S = 0.05; c = client(ends_after=10 ** 9)
assert fix.critiques(c, P) == {"3": "batch t3", "5": "batch t5"} and c.messages.batches.cancelled  # timed out: cancelled, partial results kept
c = client(ends_after=1, fail_create=True); assert fix.critiques(c, P) == {"3": "direct", "5": "direct"}
print("FIX BATCH TESTS OK")
