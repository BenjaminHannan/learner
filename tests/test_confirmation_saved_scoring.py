import unittest

from scripts.cap256_launch.eval_mixture_confirmation import score_saved


class ConfirmationSavedScoringTests(unittest.TestCase):
    def fixture(self):
        order = [(0, 'repeat256'), (0, 'diverse512'),
                 (1, 'diverse512'), (1, 'repeat256')]
        frames = [{'id': str(i), 'group': str(i % 12), 'labels': [[i + 10, 7]]}
                  for i in range(32)]
        saved = []
        for seed, arm in order:
            for frame in frames:
                saved.append({'call_index': len(saved) + 1, 'seed': seed, 'arm': arm,
                              'id': frame['id'], 'raw': frame['labels'][0][:]})
        return saved, frames, order

    def test_incomplete_stream_never_scores(self):
        saved, frames, order = self.fixture()
        called = []
        with self.assertRaises(AssertionError):
            score_saved(saved[:-1], frames, order,
                        lambda *args: called.append(args), 7)
        self.assertEqual(called, [])

    def test_call_identity_mismatch_is_rejected(self):
        saved, frames, order = self.fixture()
        saved[0]['seed'] = 1
        called = []
        with self.assertRaises(AssertionError):
            score_saved(saved, frames, order, lambda *args: called.append(args), 7)
        self.assertEqual(called, [])

    def test_complete_stream_preserves_raw_and_reports_all_slots(self):
        saved, frames, order = self.fixture()
        saved[32]['raw'] = [999, 7]
        before = repr(saved)
        results, answers = score_saved(saved, frames, order,
                                       lambda r, target, eos: r['raw'] == target, 7)
        self.assertEqual(repr(saved), before)
        self.assertEqual([(r['seed'], r['arm']) for r in results], order)
        self.assertEqual([r['strict_correct'] for r in results], [32, 31, 32, 32])
        self.assertEqual(len(answers), 128)
        self.assertFalse(answers[32]['strict_exact'])


if __name__ == '__main__':
    unittest.main()
