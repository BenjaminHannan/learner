"""Information access, gradient, causal-isolation and persistence checks."""
from dataclasses import replace
import io
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_token_memory as T
T.data.bootstrap()
torch, F = T.torch, T.F


class TokenMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.x, cls.y = T.data.training_batch(random.Random(773821), visits=2)

    def model(self):
        torch.manual_seed(773822)
        return T.TokenMemoryReasoner()

    def test_size(self):
        self.assertEqual(self.model().parameters_count(), 79316)

    def test_counted_flops(self):
        from premonition.flops import count_flops
        m = self.model()
        counted = count_flops(lambda: F.cross_entropy(m(self.x), self.y))
        self.assertEqual(counted,T.training_flops(self.x,m))

    def test_answer_loss_trains_every_read_query_and_key(self):
        m = self.model()
        logits, weights = m(self.x, trace=True)
        weights.retain_grad()
        F.cross_entropy(logits, self.y).backward()
        for name in ("line_encoder.attention.query.weight", "line_encoder.attention.key.weight",
                     "question_encoder.attention.query.weight", "read.cross_attention.query.weight",
                     "read.cross_attention.key.weight", "read.cross_attention.value.weight",
                     "read.self_attention.query.weight"):
            grad = dict(m.named_parameters())[name].grad
            self.assertTrue(torch.isfinite(grad).all(), name)
            self.assertGreater(float(grad.abs().sum()), 0, name)

    def test_every_real_token_is_available_to_every_head(self):
        m = self.model()
        _, attention = m(self.x, trace=True)
        counts = self.x.memory.ne(0).sum((1, 2))[self.x.owner]
        self.assertEqual(attention.shape[:3], (len(self.y), 3, 4))
        for q, count in enumerate(counts):
            self.assertTrue((attention[q, :, :, :, :count] > 0).all())
            self.assertTrue((attention[q, :, :, :, count:-1] == 0).all())
        self.assertTrue(torch.allclose(attention.sum(-1), torch.ones_like(attention.sum(-1))))

    def test_future_lines_cannot_change_answer(self):
        x = T.data.pack([[[3,52,8,12,7], [], [3,53,9,13,7]]], [[4,52,8,5]], [0], [1])
        m = self.model()
        z = replace(x, memory=x.memory.clone())
        z.memory[0,2] = torch.tensor([3,60,10,23,7])
        self.assertTrue(torch.equal(m(x), m(z)))
        _, a = m(x, trace=True)
        self.assertTrue((a[...,5:10] == 0).all())

    def test_empty_memory_is_finite_and_uses_only_null(self):
        x = replace(self.x, eligible=torch.zeros_like(self.x.eligible))
        logits, a = self.model()(x, trace=True)
        self.assertTrue(torch.isfinite(logits).all())
        self.assertTrue((a[...,-1] == 1).all())
        self.assertTrue((a[...,:-1] == 0).all())

    def test_padding_does_not_change_predictions(self):
        x = replace(self.x, memory=F.pad(self.x.memory, (0,3,0,2)),
                    questions=F.pad(self.x.questions,(0,3)), eligible=F.pad(self.x.eligible,(0,2)))
        m = self.model()
        self.assertTrue(torch.allclose(m(self.x),m(x),atol=2e-6,rtol=1e-5))

    def test_line_order_invariance_preserves_tokens(self):
        order = torch.randperm(self.x.memory.shape[1])
        x = replace(self.x, memory=self.x.memory[:,order], eligible=self.x.eligible[:,order])
        m = self.model()
        self.assertTrue(torch.allclose(m(self.x),m(x),atol=2e-6,rtol=1e-5))

    def test_world_and_question_isolation(self):
        m = self.model().eval()
        full = m(self.x)
        for q, owner in enumerate(self.x.owner):
            x = T.data.Inputs(self.x.memory[owner:owner+1], self.x.questions[q:q+1],
                             torch.zeros(1,dtype=torch.long), self.x.eligible[q:q+1])
            single = m(x)
            self.assertTrue(torch.allclose(full[q:q+1],single,atol=2e-6,rtol=1e-5))
            self.assertEqual(int(full[q].argmax()),int(single.argmax()))

    def test_train_eval_and_reload_use_identical_policy(self):
        m = self.model()
        before = {k:v.clone() for k,v in m.state_dict().items()}
        train = m(self.x)
        m.eval()
        self.assertTrue(torch.equal(train,m(self.x)))
        buffer = io.BytesIO()
        torch.save(m.state_dict(),buffer)
        buffer.seek(0)
        other = self.model()
        other.load_state_dict(torch.load(buffer,weights_only=True))
        self.assertTrue(torch.equal(train,other(self.x)))
        self.assertTrue(all(torch.equal(v,m.state_dict()[k]) for k,v in before.items()))

    def test_question_anchor_is_unchanged_across_iterations(self):
        m, anchors = self.model(), []
        handle = m.read.register_forward_pre_hook(lambda _, args: anchors.append(args[1].detach().clone()))
        m(self.x)
        handle.remove()
        self.assertEqual(len(anchors),3)
        self.assertTrue(all(torch.equal(anchors[0],x) for x in anchors[1:]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
