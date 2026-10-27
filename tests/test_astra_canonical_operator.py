"""Pre-launch mechanism/privilege tests on throwaway, untrained fixtures."""
from dataclasses import fields, replace
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import astra_canonical_operator as A
import astra_canonical_operator_panels as P
A.data.bootstrap()
torch = A.torch


class CanonicalOperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def batch(self):
        return A.training_batch(random.Random(992811), 2)

    def test_parameter_schema_and_native_parity(self):
        m = A.new_model(992812)
        original = A.T.TokenMemoryReasoner()
        original.load_state_dict(m.state_dict(), strict=True)
        self.assertEqual(m.parameters_count(), 79316)
        self.assertEqual([(k, v.shape) for k, v in m.state_dict().items()],
                         [(k, v.shape) for k, v in original.state_dict().items()])
        x = self.batch().monolithic
        self.assertTrue(torch.equal(m(x), original(x)))
        self.assertEqual([f.name for f in fields(A.data.Inputs)], ['memory','questions','owner','eligible'])

    def test_eight_records_stream_evidence_and_exclusions(self):
        r1, r2 = random.Random(1101), random.Random(1101)
        for _ in range(3):
            batch = A.training_batch(r1, 2)
            old, targets = A.E.training_batch(r2, 2)
            self.assertEqual(r1.getstate(), r2.getstate())
            self.assertEqual(batch.accounting['records'], 16)
            self.assertEqual(batch.accounting['kinds'], dict.fromkeys(['one_hop','link','terminal','monolithic'],4))
            self.assertTrue(torch.equal(batch.monolithic.questions, old.questions[[2,3,6,7]]))
            self.assertTrue(torch.equal(batch.monolithic_targets.answer, targets.answer[[2,3,6,7]]))
            self.assertTrue(torch.equal(batch.canonical.memory, old.memory))
            self.assertEqual(batch.canonical.questions.shape[1], 4)
            self.assertTrue(A.E.evidence_mask(batch.canonical, batch.canonical_targets).any(-1).all())
            self.assertTrue(A.E.evidence_mask(batch.monolithic, batch.monolithic_targets).any(-1).all())
            for x, y in [(batch.canonical,batch.canonical_targets),(batch.monolithic,batch.monolithic_targets)]:
                self.assertEqual([p[-1]['target'] for p in A.truth_paths(x)], y.answer.tolist())
        b = self.batch()
        sig = A.visible_signature(b.canonical.memory[0].tolist(), b.canonical.questions[0].tolist())
        with self.assertRaisesRegex(RuntimeError, 'overlap'):
            A.training_batch(random.Random(992811), 2, {sig})

    def test_first_link_identity_and_fresh_call_equivalence(self):
        b = self.batch()
        base = A.select(b.monolithic, [0])
        subject = int(base.questions[0,1])
        m = A.new_model(992813).eval()
        # Force a known entity so all three calls execute, without oracle fallback.
        with torch.no_grad():
            m.output_bias[52] = 100
        captures = []
        anchors, first_states = [], []
        def hook(module, args):
            state, anchor = args[:2]
            if not anchors or anchor.data_ptr() != anchors[-1].data_ptr():
                anchors.append(anchor)
                first_states.append(state)
        h = m.read.register_forward_pre_hook(hook)
        for q in ([4,subject,11,8,5], [4,subject,11,10,5], [4,subject,11,11,10,5]):
            traced = []
            x = replace(base, questions=torch.tensor([q]))
            out = A.execute(m, x, lambda a,l: traced.append((a,l.clone())))
            self.assertEqual(out['calls'], len(q)-3)
            captures.append(traced)
        h.remove()
        for traced in captures[1:]:
            for name in ('memory','questions','owner','eligible'):
                self.assertTrue(torch.equal(getattr(captures[0][0][0],name),getattr(traced[0][0],name)))
            self.assertTrue(torch.equal(captures[0][0][1],traced[0][1]))
        self.assertEqual(len(anchors), 7)
        self.assertEqual(len({a.data_ptr() for a in anchors}), 7)
        self.assertTrue(all(torch.equal(s,a) for s,a in zip(first_states,anchors)))
        for traced in captures:
            for x, logits in traced:
                self.assertEqual(x.questions.shape[1],4)
                self.assertTrue(torch.equal(logits,m(x)))
                self.assertTrue(torch.equal(x.memory,base.memory))
                self.assertTrue(torch.equal(x.eligible,base.eligible))

    def test_nonentity_aborts_without_fallback_and_final_full_vocab(self):
        class Invalid(A.CanonicalOperator):
            def forward(self, x):
                out = torch.zeros(len(x.questions),68)
                out[:,30] = 1
                return out
        x = self.batch().monolithic
        out = A.execute(Invalid(),x)
        self.assertEqual(out['predictions'],[-1]*len(x.questions))
        self.assertEqual(out['emitted'],[[30]]*len(x.questions))
        self.assertEqual(out['calls'],len(x.questions))
        one = self.batch().canonical
        out = A.execute(Invalid(),one)
        self.assertEqual(out['predictions'],[30]*len(one.questions))

    def test_counts_match_instrumented_matmuls_and_gradients(self):
        from torch.utils.flop_counter import FlopCounterMode
        from premonition.flops import count_flops
        b, m = self.batch(), A.new_model(992814)
        count = count_flops(lambda: .75*A.E.loss_for(m,b.canonical,b.canonical_targets)[0]
                            + .25*A.E.loss_for(m,b.monolithic,b.monolithic_targets)[0])
        self.assertEqual(count,A.training_flops(b,m))
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None))
        for x in (b.canonical,b.monolithic):
            with torch.no_grad(), FlopCounterMode(display=False) as counter:
                m(x)
            self.assertEqual(int(counter.get_total_flops()), A.inference_flops(x,m))

    def test_panel_truth_edits_and_semantic_order_invariance(self):
        for name in ('c1_own_one_hop','c3_own_heldout_two_hop','c4_changed_link',
                     'c5_changed_endpoint_value','c6_irrelevant_edit'):
            panel = P.generate(name,n=2,namespace='astra-canonical-operator-fixture')
            sem, raw = P.signatures(panel)
            self.assertEqual(len(set(sem)),len(sem))
        b = self.batch().canonical
        mem, q = b.memory[0].tolist(), b.questions[0].tolist()
        self.assertEqual(A.visible_signature(mem,q),A.visible_signature(list(reversed(mem)),q))

    def test_evaluation_pair_denominators_paths_and_cycle_split(self):
        import time
        from astra_canonical_operator_run import score_cell
        class FixtureOracle(A.CanonicalOperator):
            def forward(self, x):
                out = torch.zeros(len(x.questions),68)
                for i,path in enumerate(A.truth_paths(x)):
                    # Canonical fixture is perfect; monolithic fixture always wrong.
                    value = path[-1]['target'] if x.questions.shape[1] == 4 else 30
                    out[i,value] = 1
                return out
        model = FixtureOracle()
        panel = P.generate('c4_changed_link',n=2,namespace='astra-canonical-operator-score-fixture')
        r = score_cell(model,panel,time.monotonic(),60)
        self.assertEqual((r['R'],r['M'],r['gain'],r['loss']),(2,0,2,0))
        for side in ('a','b'):
            self.assertEqual(r['diagnostics'][side]['native_links'],[2])
            self.assertEqual(r['diagnostics'][side]['oracle_links'],[2])
            self.assertEqual(r['diagnostics'][side]['terminal_oracle'],2)
        x = A.data.pack([[[3,52,11,53,7],[3,53,11,52,7],[3,52,10,12,7],[]]],
                        [[4,52,11,11,10,5]],[0],[3])
        panel = dict(n=1,chunks=[dict(sides={'a':(x,[12])})])
        r = score_cell(model,panel,time.monotonic(),60)
        self.assertEqual(r['cycle_split']['asker_cycle'],dict(n=1,R=1,M=0,native_joint=1))
        self.assertEqual(r['diagnostics']['a']['native_links'],[1,1])
        self.assertEqual(r['costs']['R']['calls'],3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
