from types import SimpleNamespace
import unittest

import torch

from memorylab.controls import (
    MATRIX_BYTES,
    ByteMatchedSlotMemory,
    OracleMatrixMemory,
    compare_interventions,
    rollback_memory,
    snapshot_memory,
    swap_memory,
    zero_memory,
)


class ImmutableControlTests(unittest.TestCase):
    def test_zero_swap_and_rollback_are_independent_and_strict(self):
        own = torch.arange(2 * 128 * 128, dtype=torch.float32).reshape(2, 128, 128)
        donor = own.neg()
        own_before = own.clone()
        donor_before = donor.clone()

        zeroed = zero_memory(own)
        swapped = swap_memory(own, donor)
        snapshot = snapshot_memory(own)
        changed = own + 7.0
        restored = rollback_memory(snapshot)

        torch.testing.assert_close(zeroed, torch.zeros_like(own), rtol=0, atol=0)
        torch.testing.assert_close(swapped, donor, rtol=0, atol=0)
        torch.testing.assert_close(restored, own_before, rtol=0, atol=0)
        torch.testing.assert_close(own, own_before, rtol=0, atol=0)
        torch.testing.assert_close(donor, donor_before, rtol=0, atol=0)
        self.assertNotEqual(zeroed.data_ptr(), own.data_ptr())
        self.assertNotEqual(swapped.data_ptr(), donor.data_ptr())
        self.assertNotEqual(snapshot.data_ptr(), own.data_ptr())
        self.assertNotEqual(restored.data_ptr(), snapshot.data_ptr())
        self.assertFalse(torch.equal(changed, restored))

        invalid = (
            torch.zeros(128, 128, dtype=torch.float32),
            torch.zeros(1, 127, 128, dtype=torch.float32),
            torch.zeros(1, 128, 128, dtype=torch.float64),
            torch.full((1, 128, 128), float("nan"), dtype=torch.float32),
        )
        for memory in invalid:
            with self.subTest(shape=tuple(memory.shape), dtype=memory.dtype):
                with self.assertRaises((TypeError, ValueError)):
                    zero_memory(memory)


class OracleMatrixMemoryTests(unittest.TestCase):
    def test_pc_k_one_hot_exact_recall_through_128_associations(self):
        rig = OracleMatrixMemory()
        initial = rig.empty(batch=1)
        keys = rig.one_hot_keys(128, batch=1)
        values = (
            torch.arange(128 * 128, dtype=torch.float32).reshape(1, 128, 128) / 256.0
        )

        written = rig.install_many(initial, keys, values)
        recalled = rig.recall_many(written, keys)

        self.assertTrue(torch.equal(recalled, values))
        self.assertTrue(torch.equal(initial, torch.zeros_like(initial)))
        self.assertEqual(written.dtype, torch.float32)


class ByteMatchedSlotMemoryTests(unittest.TestCase):
    def test_accounting_is_exact_and_raw_tensors_match_it(self):
        memory = ByteMatchedSlotMemory()
        accounting = memory.byte_accounting
        state = memory.empty(batch=1)

        self.assertEqual(accounting.slots, 63)
        self.assertEqual(accounting.payload_bytes, 64_512)
        self.assertEqual(accounting.slot_metadata_bytes, 1_008)
        self.assertEqual(accounting.header_bytes, 16)
        self.assertEqual(accounting.metadata_bytes, 1_024)
        self.assertEqual(accounting.total_bytes, 65_536)
        self.assertEqual(accounting.target_bytes, MATRIX_BYTES)
        self.assertTrue(accounting.exact_match)
        self.assertEqual(memory.tensor_bytes(state), 65_536)

    def test_write_is_immutable_and_same_key_overwrites_nearest_slot(self):
        memory = ByteMatchedSlotMemory(overwrite_similarity_threshold=0.95)
        empty = memory.empty(batch=1)
        key = torch.zeros(1, 128, dtype=torch.float32)
        key[0, 7] = 1.0
        first_value = torch.zeros(1, 128, dtype=torch.float32)
        first_value[0, 11] = 2.0
        corrected_value = torch.zeros(1, 128, dtype=torch.float32)
        corrected_value[0, 13] = -3.0

        first = memory.write(empty, key, first_value)
        corrected = memory.write(first, key, corrected_value)

        self.assertEqual(int(memory.occupied_mask(empty).sum().item()), 0)
        self.assertEqual(int(memory.occupied_mask(first).sum().item()), 1)
        self.assertEqual(int(memory.occupied_mask(corrected).sum().item()), 1)
        torch.testing.assert_close(memory.read(first, key), first_value, rtol=0, atol=0)
        torch.testing.assert_close(memory.read(corrected, key), corrected_value, rtol=0, atol=0)
        torch.testing.assert_close(empty.keys, torch.zeros_like(empty.keys), rtol=0, atol=0)
        torch.testing.assert_close(empty.values, torch.zeros_like(empty.values), rtol=0, atol=0)
        self.assertEqual(memory.last_written(first)[0, 0].item(), 1)
        self.assertEqual(memory.last_written(corrected)[0, 0].item(), 2)


class _MemoryMarkerModel:
    def generate(
        self,
        query_tokens,
        memory,
        *,
        lengths=None,
        max_new_tokens=None,
        steps=None,
    ):
        del query_tokens, lengths, max_new_tokens, steps
        tokens = memory[:, 0, 0].round().to(torch.long).unsqueeze(1)
        return SimpleNamespace(decoding=SimpleNamespace(tokens=tokens))


class InterventionTests(unittest.TestCase):
    def test_compare_interventions_reports_only_generated_token_differences(self):
        own = torch.zeros(1, 128, 128, dtype=torch.float32)
        swapped = torch.zeros_like(own)
        rollback = torch.zeros_like(own)
        own[0, 0, 0] = 1.0
        swapped[0, 0, 0] = 2.0
        rollback[0, 0, 0] = 3.0
        own_before = own.clone()
        swapped_before = swapped.clone()
        rollback_before = rollback.clone()

        result = compare_interventions(
            _MemoryMarkerModel(),
            torch.tensor([[5]], dtype=torch.long),
            own,
            swapped,
            rollback,
        )

        self.assertEqual(result.own_tokens.tolist(), [[1]])
        self.assertEqual(result.zero_tokens.tolist(), [[0]])
        self.assertEqual(result.swapped_tokens.tolist(), [[2]])
        self.assertEqual(result.rollback_tokens.tolist(), [[3]])
        self.assertEqual(
            result.equality_to_own(),
            {"zero": False, "swapped": False, "rollback": False},
        )
        torch.testing.assert_close(own, own_before, rtol=0, atol=0)
        torch.testing.assert_close(swapped, swapped_before, rtol=0, atol=0)
        torch.testing.assert_close(rollback, rollback_before, rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
