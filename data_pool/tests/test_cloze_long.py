import os, sys, tempfile, unittest, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import cloze_long as CL


class _Z:      # minimal stand-in so the test does not need the 8a build branch
    @staticmethod
    def norm_text(t): return ' '.join(t.split())


class T(unittest.TestCase):
    def test_probs_sum_to_one(self):
        self.assertAlmostEqual(sum(CL.bucket_probs(CL.MIX)), 1.0)

    def test_ceiling_deterministic_and_chunks_fit(self):
        p = CL.bucket_probs(CL.MIX)
        self.assertEqual(CL.pick_ceiling(400, 'd', 3, CL.MIX, p), CL.pick_ceiling(400, 'd', 3, CL.MIX, p))
        text = ' '.join(['word%d' % (i % 50) for i in range(3000)])
        ch = CL.chunks_mixed(text, 400, 'doc', CL.MIX, p)
        self.assertTrue(all(len(c) <= m - 1 for c, m in ch))
        self.assertTrue(len({m for _, m in ch}) > 1)
        self.assertEqual(ch, CL.chunks_mixed(text, 400, 'doc', CL.MIX, p))


if __name__ == '__main__':
    unittest.main()
