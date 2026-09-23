"""Independent synthetic invariants for the eval-only routing instrumentation."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import astra_transfer_diagnostic as D
D.data.bootstrap()
from premonition.toy_ladder import LadderSpec, WORLD, QUESTION, ANSWER, NEWLINE

torch = D.torch


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.spec = LadderSpec()

    def fixture(self):
        s = self.spec
        ents = [s.vocab_size + e for e in range(3)]
        lines = []
        for e in range(3):
            lines.append([WORLD, ents[e], s.link, ents[(e+1) % 3], NEWLINE])
            for r in range(3):
                lines.append([WORLD, ents[e], s.relation(r), s.value(e*3+r), NEWLINE])
        lines.append([WORLD, s.filler(0), s.filler(1), NEWLINE])
        lines.append([])
        # Future fact must remain unavailable to native and oracle reads.
        lines.append([WORLD, ents[0], s.relation(2), s.value(15), NEWLINE])
        x = D.data.pack([lines], [[QUESTION, ents[0], s.link, s.relation(2), ANSWER]], [0], [13])
        return x, [D.parse_facts(x, 0, s)]

    def model(self):
        torch.manual_seed(20260920901)
        return D.T.TokenMemoryReasoner().eval()

    @torch.no_grad()
    def test_passive_exact_and_forced_mass(self):
        x, facts = self.fixture()
        m = self.model()
        before = D.C.fingerprint(m)
        native = m(x)
        self.assertTrue(torch.equal(native, D.routed(m, x, facts, 'N')))
        self.assertTrue(torch.equal(native, m(x, trace=True)[0]))
        for mode in ['L', 'E', 'LE']:
            _, attn = D.routed(m, x, facts, mode, return_trace=True)
            ids = D.token_line_ids(x)
            for step in range(3):
                if (step == 0 and 'L' in mode) or (step > 0 and 'E' in mode):
                    target = facts[0]['link_line' if step == 0 else 'endpoint_line']
                    outside = ids[0] != target
                    self.assertTrue((attn[0, step, :, :, outside] == 0).all())
                    self.assertTrue(torch.allclose(attn[0, step].sum(-1), torch.ones(4, 5)))
            self.assertTrue(torch.equal(native, m(x)), 'hook leaked into next episode')
        self.assertEqual(before, D.C.fingerprint(m))

    @torch.no_grad()
    def test_line_mass_matches_manual_compaction(self):
        x, facts = self.fixture()
        _, attention = self.model()(x, trace=True)
        masses = D.line_attention(x, attention)
        for line in range(x.memory.shape[1]):
            start = int(x.memory[0, :line].ne(0).sum())
            n = int(x.memory[0, line].ne(0).sum())
            expected = attention[0, :, :, -1, start:start+n].sum(-1)
            self.assertTrue(torch.allclose(masses[0, :, :, line], expected))
        self.assertTrue((masses[0, :, :, 14] == 0).all())
        self.assertEqual(facts[0]['answer'], self.spec.value(5))

    def test_requery_is_ordinary_visible_question(self):
        x, facts = self.fixture()
        y = D.requery(x, facts)
        self.assertEqual(y.questions.tolist(), [[QUESTION, self.spec.vocab_size + 1, self.spec.relation(2), ANSWER]])
        self.assertIs(y.memory, x.memory)
        self.assertIs(y.eligible, x.eligible)

    def test_error_overlap_and_missing_category(self):
        x, facts = self.fixture()
        f = facts[0]
        f['decoy'] = self.spec.value(3)
        f['other_person_same_relation_values'] = [self.spec.value(3)]
        primary, flags, collision = D.error_class(self.spec.value(3), f, self.spec)
        self.assertEqual(primary, 'b_decoy')
        self.assertEqual(len(flags), 3)
        self.assertTrue(collision)
        self.assertEqual(D.error_class(f['endpoint'], f, self.spec)[0], 'c_link_entity')
        self.assertEqual(D.error_class(self.spec.value(15), f, self.spec)[0], 'f_other_value')
        self.assertEqual(D.error_class(f['answer'], f, self.spec)[0], 'correct')

    def test_pair_statistics_do_not_count_one_correct_twin(self):
        # Registered pair scorer must count BOTH answers, and invariant same-answer condition.
        pa = [[12, 2], [12, 2]]
        pb = [[13, 2], [12, 2]]
        self.assertEqual(D.C.score_predictions(pa, [[12, 2], [12, 2]], pb, [[13, 2], [13, 2]], False), [True, False])


if __name__ == '__main__':
    unittest.main(verbosity=2)
