"""Synthetic native-observation checks only; no actual examples or models."""
import unittest
from scripts.cap256_launch.recount_noteadapt import score


def observation(ids):
    eos=7;positions=[i for i,t in enumerate(ids) if t==eos];stripped=ids[:positions[0]] if positions else ids
    return dict(MODEL_raw_generate_ids=[ids],MODEL_generated_ids_with_observed_EOS=ids,
                MODEL_native_decoder_return=[stripped],native_generate_call_count=1,
                native_call_contract_valid=True,generation_error=None,EOS_positions=positions,
                observed_EOS=bool(positions),native_stripped_output_equal=True,
                termination_reason='observed_EOS' if positions else 'terminated_without_observed_EOS')


class TestNativeRecount(unittest.TestCase):
    def test_exact_target_with_actual_EOS(self):
        self.assertEqual(score(observation([2,7]),[2,7],7),(True,True,False))

    def test_target_without_EOS_fails(self):
        self.assertEqual(score(observation([2]),[2,7],7),(False,False,False))

    def test_empty_EOS_is_no_numeric_answer(self):
        self.assertEqual(score(observation([7]),[2,7],7),(False,True,True))

    def test_wrong_answer_and_invalid_extra_output_fail(self):
        self.assertEqual(score(observation([3,7]),[2,7],7),(False,True,False))
        self.assertEqual(score(observation([2,7,3]),[2,7],7),(False,False,False))
        record=observation([2,7]);record['native_generate_call_count']=2
        self.assertEqual(score(record,[2,7],7),(False,False,False))

    def test_metadata_parity_corruption_is_rejected(self):
        record=observation([2,7]);record['MODEL_native_decoder_return']=[[3]]
        with self.assertRaises(AssertionError):score(record,[2,7],7)


if __name__=='__main__':unittest.main()
