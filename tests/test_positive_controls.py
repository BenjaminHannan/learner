import tempfile
import unittest

import torch

from memorylab.model import MainNetwork
from memorylab.positive_controls import (
    _pc_c_oracle_memory,
    _key_orthogonality_loss,
    InContextReader,
    build_in_context_query,
    evaluate_memory_control,
    evaluate_pc_c,
    memory_control_examples,
    pc_c_examples,
    run_memory_positive_controls,
    run_pc_c_control,
    evaluate_pc_r,
    run_pc_r_control,
    train_memory_control_step,
    train_pc_c_step,
    train_pc_r_episode,
)
from memorylab.storage import Budget
from memorylab.tasks import Query, TOKENIZER, batch_queries, batch_teachings, generate_episode
from memorylab.transformer_model import RecurrentTransformerLearner


def make_fast_reader():
    torch.manual_seed(321)
    network = MainNetwork(
        embed_width=8,
        hidden_width=128,
        reasoning_steps=1,
        max_reasoning_steps=1,
        max_decode_len=3,
    )
    return InContextReader(network)


def make_fast_memory_model():
    torch.manual_seed(322)
    return MainNetwork(
        embed_width=8,
        hidden_width=128,
        reasoning_steps=1,
        max_reasoning_steps=1,
        max_decode_len=2,
    )


def make_fast_chain_transformer():
    torch.manual_seed(323)
    return RecurrentTransformerLearner(
        model_width=32,
        memory_width=128,
        memory_heads=4,
        attention_heads=4,
        ffn_width=64,
        reasoning_steps=2,
        max_reasoning_steps=2,
        max_decode_len=2,
    )


def make_fast_chain_gru():
    torch.manual_seed(324)
    return MainNetwork(
        embed_width=8,
        hidden_width=128,
        reasoning_steps=2,
        max_reasoning_steps=2,
        max_decode_len=2,
    )


class PcReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_context_contains_only_teachings_and_query_text(self):
        episode = generate_episode("train", 5, tier=3)
        original = episode.queries[0]
        example = build_in_context_query(episode, original)
        expected_text = " ".join(
            [*(teaching.text for teaching in episode.teachings), original.text]
        )
        self.assertEqual(example.text, expected_text)
        self.assertIsNone(example.program)
        batch = batch_queries([example])
        self.assertEqual(
            batch.token_ids[0, : batch.lengths[0]].tolist(),
            TOKENIZER.encode(expected_text),
        )
        self.assertEqual(tuple(vars(batch)), ("token_ids", "lengths", "attention_mask"))

    def test_training_has_encoder_gradients_frozen_writer_and_exact_zero_w(self):
        reader = make_fast_reader()
        writer_before = {
            name: value.detach().clone()
            for name, value in reader.network.writer.state_dict().items()
        }
        optimizer = torch.optim.AdamW(
            [parameter for parameter in reader.parameters() if parameter.requires_grad],
            lr=1e-3,
        )
        result = train_pc_r_episode(
            reader,
            generate_episode("train", 7, tier=2),
            optimizer,
            device="cpu",
        )
        self.assertGreater(result["encoder_grad_norm"], 0.0)
        self.assertEqual(result["writer_grad_norm"], 0.0)
        self.assertEqual(result["zero_memory_max_abs"], 0.0)
        for name, value in reader.network.writer.state_dict().items():
            torch.testing.assert_close(value, writer_before[name], rtol=0, atol=0)

    def test_update_and_evaluation_split_guards(self):
        reader = make_fast_reader()
        optimizer = torch.optim.AdamW(
            [parameter for parameter in reader.parameters() if parameter.requires_grad]
        )
        with self.assertRaisesRegex(ValueError, "split=train"):
            train_pc_r_episode(
                reader,
                generate_episode("validation", 1, tier=2),
                optimizer,
            )
        with self.assertRaisesRegex(ValueError, "validation/test"):
            evaluate_pc_r(reader, split="train", worlds_per_tier=1)

    def test_evaluation_is_deterministic_and_quality_is_separate(self):
        reader = make_fast_reader()
        first = evaluate_pc_r(
            reader,
            tiers=(2,),
            worlds_per_tier=1,
            seed=11,
        )
        second = evaluate_pc_r(
            reader,
            tiers=(2,),
            worlds_per_tier=1,
            seed=11,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "completed")
        self.assertTrue(first["zero_memory_control"])
        self.assertIsInstance(first["threshold_passed"], bool)

    def test_bounded_run_reports_completion_separately_from_threshold(self):
        report = run_pc_r_control(
            reader=make_fast_reader(),
            tiers=(2,),
            steps=1,
            seconds=20,
            eval_worlds=1,
            seed=13,
        )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["training"]["steps_completed"], 1)
        self.assertTrue(report["controls"]["persistent_memory_disabled"])
        self.assertIsInstance(report["threshold_passed"], bool)
        self.assertEqual(
            report["threshold_passed"],
            report["evaluation"]["threshold_passed"],
        )


class PcMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_examples_are_disjoint_text_batches_with_evaluator_targets_separate(self):
        examples = memory_control_examples("train", 17, item_count=16)
        self.assertEqual(len(examples), 16)
        teachings = tuple(teaching for teaching, _ in examples)
        queries = tuple(query for _, query in examples)
        self.assertEqual(len({query.text for query in queries}), 16)
        self.assertTrue(all(not teaching.correction for teaching in teachings))
        teaching_batch = batch_teachings(teachings)
        query_batch = batch_queries(queries)
        self.assertEqual(
            tuple(vars(teaching_batch)),
            ("token_ids", "lengths", "attention_mask"),
        )
        self.assertEqual(
            tuple(vars(query_batch)),
            ("token_ids", "lengths", "attention_mask"),
        )

    def test_key_orthogonality_penalizes_collapse_per_memory_head(self):
        collapsed = torch.ones(4, 2, 3)
        separated = torch.zeros(3, 2, 3)
        for index in range(3):
            separated[index, :, index] = 1.0
        collapsed_loss, collapsed_max = _key_orthogonality_loss(collapsed)
        separated_loss, separated_max = _key_orthogonality_loss(separated)
        self.assertGreater(float(collapsed_loss), 0.9)
        self.assertAlmostEqual(float(collapsed_max), 1.0, places=6)
        self.assertEqual(float(separated_loss), 0.0)
        self.assertEqual(float(separated_max), 0.0)

    def test_pc_e_uses_oracle_value_without_training_writer_value_path(self):
        model = make_fast_memory_model()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        examples = memory_control_examples("train", 19, item_count=4)
        result = train_memory_control_step(
            model,
            examples,
            optimizer,
            mode="encoder",
        )
        self.assertEqual(result["mode"], "PC-E")
        self.assertGreater(result["writer_key_grad_norm"], 0.0)
        self.assertEqual(result["writer_value_grad_norm"], 0.0)
        self.assertGreater(result["encoder_grad_norm"], 0.0)
        self.assertEqual(result["value_loss"], 0.0)

    def test_pc_w_trains_writer_value_and_evaluation_reports_w_zero(self):
        model = make_fast_memory_model()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        examples = memory_control_examples("train", 23, item_count=4)
        result = train_memory_control_step(
            model,
            examples,
            optimizer,
            mode="writer",
        )
        self.assertEqual(result["mode"], "PC-W")
        self.assertGreater(result["writer_value_grad_norm"], 0.0)
        report = evaluate_memory_control(
            model,
            mode="writer",
            worlds=1,
            item_count=4,
            seed=29,
        )
        self.assertEqual(report["queries"], 4)
        self.assertIn("no_w_exact_match_rate", report)
        self.assertIsNotNone(report["_restart_fixture"])

    def test_transformer_memory_evaluation_can_override_reasoning_depth(self):
        model = make_fast_chain_transformer()
        report = evaluate_memory_control(
            model,
            mode="encoder",
            worlds=1,
            item_count=2,
            seed=31,
            reasoning_steps=1,
        )
        self.assertEqual(report["reasoning_steps"], 1)
        self.assertEqual(model.reasoning_steps, 2)

    def test_bounded_pc_memory_run_serializes_and_restarts(self):
        with tempfile.TemporaryDirectory() as root:
            budget = Budget(
                root,
                hard=100_000_000,
                steady=80_000_000,
                free_floor=0,
            )
            report = run_memory_positive_controls(
                budget=budget,
                model=make_fast_memory_model(),
                encoder_steps=1,
                writer_steps=1,
                seconds=20,
                eval_worlds=1,
                item_count=2,
                learning_rate=1e-3,
            )
            self.assertIn(report["status"], {"completed", "failed_controls"})
            self.assertEqual(report["training"]["pc_e_steps_completed"], 1)
            self.assertEqual(report["training"]["pc_w_steps_completed"], 1)
            self.assertTrue(report["restart_identity"]["workspace_is_none"])
            self.assertTrue(report["restart_identity"]["identical_tokens"])
            checkpoint = budget.root / report["restart_identity"]["checkpoint"]
            self.assertTrue(checkpoint.is_file())


class PcChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_second_hop_key_uses_query_text_not_target(self):
        model = make_fast_chain_transformer().eval()
        original = pc_c_examples("train", 31, worlds=1)[0]
        first, second = original
        self.assertEqual(second.expected, "unknown")
        replacement = next(symbol for symbol in "abcdefgh" if symbol != first.expected)
        changed_first = Query(
            first.text,
            replacement,
            tier=first.tier,
            purpose=first.purpose,
        )
        baseline = _pc_c_oracle_memory(model, (original,), device=torch.device("cpu"))
        changed = _pc_c_oracle_memory(
            model,
            ((changed_first, second),),
            device=torch.device("cpu"),
        )
        torch.testing.assert_close(
            baseline["first_key"],
            changed["first_key"],
            rtol=0,
            atol=0,
        )
        torch.testing.assert_close(
            baseline["second_key"],
            changed["second_key"],
            rtol=0,
            atol=0,
        )
        self.assertFalse(torch.equal(baseline["tag_value"], changed["tag_value"]))

    def test_oracle_chain_reads_exact_links_and_injects_only_second_hop(self):
        model = make_fast_chain_transformer().eval()
        examples = pc_c_examples("train", 37, worlds=1)
        oracle = _pc_c_oracle_memory(model, examples, device=torch.device("cpu"))
        encoded = model.encode(
            oracle["first_batch"].token_ids,
            lengths=oracle["first_batch"].lengths,
        )
        trace = model.reason(
            encoded,
            oracle["weights"],
            steps=2,
            query_overrides={1: oracle["second_key"]},
        )
        torch.testing.assert_close(
            trace.steps[0].query,
            oracle["first_key"],
            rtol=1e-5,
            atol=1e-6,
        )
        torch.testing.assert_close(
            trace.steps[0].memory_read,
            oracle["second_key"],
            rtol=1e-5,
            atol=1e-5,
        )
        torch.testing.assert_close(
            trace.steps[1].query,
            oracle["second_key"],
            rtol=1e-5,
            atol=1e-6,
        )
        torch.testing.assert_close(
            trace.steps[1].memory_read,
            oracle["tag_value"],
            rtol=1e-5,
            atol=1e-5,
        )

    def test_transformer_pc_c_training_keeps_writer_out_of_graph(self):
        model = make_fast_chain_transformer()
        before = {
            name: value.detach().clone()
            for name, value in model.writer.state_dict().items()
        }
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
        result = train_pc_c_step(
            model,
            pc_c_examples("train", 41, worlds=1),
            optimizer,
            device="cpu",
        )
        self.assertGreater(result["reader_grad_norm"], 0.0)
        self.assertEqual(result["writer_grad_norm"], 0.0)
        self.assertGreater(result["first_hop_read_cosine"], 0.999)
        self.assertGreater(result["second_hop_read_cosine"], 0.999)
        self.assertGreater(result["single_hop_read_cosine"], 0.999)
        for name, value in model.writer.state_dict().items():
            torch.testing.assert_close(value, before[name], rtol=0, atol=0)

    def test_evaluation_is_held_out_and_reports_w_zero(self):
        report = evaluate_pc_c(
            make_fast_chain_transformer(),
            worlds=1,
            seed=43,
            device="cpu",
        )
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["queries"], 2)
        self.assertTrue(report["teacher_forced_second_hop"])
        self.assertFalse(report["first_hop_teacher_forced"])
        self.assertFalse(report["target_used_for_key"])
        self.assertIn("zero_w_exact_match_rate", report)
        self.assertIn("single_hop_exact_match_rate", report)
        self.assertIn("single_hop_zero_w_exact_match_rate", report)

    def test_bounded_pc_c_run_serializes_and_restarts(self):
        with tempfile.TemporaryDirectory() as root:
            budget = Budget(
                root,
                hard=100_000_000,
                steady=80_000_000,
                free_floor=0,
            )
            report = run_pc_c_control(
                budget=budget,
                model=make_fast_chain_gru(),
                backbone="gru",
                steps=1,
                seconds=20,
                eval_worlds=1,
                learning_rate=1e-3,
            )
            self.assertIn(report["status"], {"completed", "failed_controls"})
            self.assertEqual(report["training"]["steps_completed"], 1)
            self.assertTrue(report["controls"]["only_second_hop_key_injected"])
            self.assertTrue(report["restart_identity"]["workspace_is_none"])
            self.assertEqual(report["restart_identity"]["verification_device"], "cpu")
            self.assertTrue(report["restart_identity"]["identical_tokens"])
            self.assertTrue(report["restart_identity"]["identical_logits"])
            checkpoint = budget.root / report["restart_identity"]["checkpoint"]
            self.assertTrue(checkpoint.is_file())


if __name__ == "__main__":
    unittest.main()
