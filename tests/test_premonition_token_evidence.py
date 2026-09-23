from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import premonition_token_evidence as E
E.data.bootstrap()


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        E.torch.set_num_threads(1)

    def test_identical_visible_training_stream_and_answers(self):
        a,b=random.Random(1101),random.Random(1101)
        for _ in range(2):
            x,y=E.training_batch(a,2)
            old,answer=E.data.training_batch(b,2)
            for name in ("memory","questions","owner","eligible"):
                self.assertTrue(E.torch.equal(getattr(x,name),getattr(old,name)))
            self.assertTrue(E.torch.equal(y.answer,answer))
            self.assertTrue(E.evidence_mask(x,y).any(-1).all())
            self.assertFalse(E.evidence_mask(x,y)[...,-1].any())

    def test_evidence_loss_count_and_finite_gradients(self):
        from premonition.flops import count_flops
        x,y=E.training_batch(random.Random(774113),2)
        m=E.T.TokenMemoryReasoner()
        count=count_flops(lambda:E.loss_for(m,x,y)[0])
        self.assertEqual(count,E.T.training_flops(x,m))
        self.assertTrue(all(E.torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None))


if __name__=="__main__":
    unittest.main(verbosity=2)
