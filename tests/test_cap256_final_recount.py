"""Synthetic raw-token checks for the independent final evaluator recount."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('cap256_recount', Path(__file__).resolve().parents[1] / 'scripts/cap256_launch/recount_final.py')
recount = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recount)


class RawScoreTests(unittest.TestCase):
    def record(self, full, target, reason='observed_EOS', valid=True):
        eos = target[-1]
        positions = [i for i, token in enumerate(full) if token == eos]
        stripped = full[:positions[0]] if positions else full
        return {'MODEL_raw_generate_ids': [full], 'MODEL_generated_ids_with_observed_EOS': full,
                'MODEL_native_decoder_return': [stripped], 'EOS_positions': positions,
                'observed_EOS': bool(positions), 'native_stripped_output_equal': True,
                'native_generate_call_count': 1, 'native_call_contract_valid': valid,
                'generation_error': None, 'native_generation_options': {'max_new_tokens': 32,
                'do_sample': False, 'use_cache': True, 'eos_token_id': eos, 'pad_token_id': eos},
                'termination_reason': reason, 'target_ids_plus_observed_EOS_exact': full == target and valid}

    def test_exact_target_and_observed_eos(self):
        self.assertTrue(recount.score(self.record([10, 2], [10, 2]), [10, 2]))

    def test_numeric_tokens_without_eos_fail(self):
        self.assertFalse(recount.score(self.record([10], [10, 2], 'terminated_without_observed_EOS'), [10, 2]))

    def test_wrong_numeric_token_fails(self):
        self.assertFalse(recount.score(self.record([11, 2], [10, 2]), [10, 2]))

    def test_repeated_or_nonterminal_eos_fails(self):
        for full in ([10, 2, 2], [10, 2, 11]):
            self.assertFalse(recount.score(self.record(full, [10, 2], 'invalid_multiple_EOS'), [10, 2]))

    def test_invalid_generation_contract_fails(self):
        self.assertFalse(recount.score(self.record([10, 2], [10, 2], 'invalid_native_generation_call', False), [10, 2]))

    def test_saved_score_disagreement_is_rejected(self):
        record = self.record([10, 2], [10, 2]); record['target_ids_plus_observed_EOS_exact'] = False
        with self.assertRaises(AssertionError):
            recount.score(record, [10, 2])


if __name__ == '__main__':
    unittest.main()
