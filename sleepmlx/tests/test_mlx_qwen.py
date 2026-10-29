"""Optional actual MLX/Qwen architecture tests; tiny random weights only."""
from dataclasses import replace
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

try:
    import mlx.core as mx
    from mlx.utils import tree_flatten
    from mlx_lm.models.qwen3_5_moe import Model, ModelArgs
    from mlx_lm.tuner.utils import load_adapters
    from mlx_lm.utils import quantize_model
except ImportError:
    mx = None

from sleepmlx.model import MLXBackend
from sleepmlx.profile import load_profile


def tiny_model(quantized=False):
    args = {"model_type": "qwen3_5_moe", "text_config": {
        "model_type": "qwen3_5_moe_text", "hidden_size": 64, "num_hidden_layers": 2,
        "num_attention_heads": 4, "num_key_value_heads": 2, "head_dim": 16, "vocab_size": 128,
        "linear_num_value_heads": 4, "linear_num_key_heads": 2, "linear_key_head_dim": 16,
        "linear_value_head_dim": 16, "full_attention_interval": 2, "num_experts": 4,
        "num_experts_per_tok": 2, "moe_intermediate_size": 64, "shared_expert_intermediate_size": 64,
        "rope_parameters": {"partial_rotary_factor": 1.0, "rope_theta": 10000, "type": "default",
                            "mrope_section": [2, 3, 3]}, "tie_word_embeddings": False,
    }}
    mx.random.seed(1)
    model = Model(ModelArgs.from_dict(args))
    if quantized:
        model, _ = quantize_model(model, args, group_size=32, bits=3)
    return model


@unittest.skipIf(mx is None, "optional MLX and current mlx-lm dependencies are not installed")
class QwenArchitectureTests(unittest.TestCase):
    def test_selected_logits_match_native_untied_output_head(self):
        model = tiny_model()
        backend = MLXBackend.__new__(MLXBackend)
        ids = mx.array([[1, 2, 3, 4]])
        bi, ti = mx.array([0, 0]), mx.array([1, 2])
        expected = model(ids[:, :-1])[bi, ti].astype(mx.float32)
        actual = backend._logits(model, ids, bi, ti)
        old_tied = model.model.embed_tokens.as_linear(model.model(ids[:, :-1])[bi, ti])
        mx.eval(expected, actual, old_tied)
        self.assertTrue(bool(mx.allclose(actual, expected, atol=1e-5)))
        self.assertGreater(float(mx.max(mx.abs(old_tied - expected))), 0.01)

    def test_quantized_moe_updates_reload_and_native_daytime_adapter_load(self):
        model = tiny_model(quantized=True)
        profile = load_profile("apex35b_mlx", {})
        profile = replace(profile, lora=dict(profile.lora, rank=2))
        tokenizer = SimpleNamespace(convert_tokens_to_ids=lambda token: 2, eos_token_ids={2},
                                    encode=lambda text, **kwargs: [1, 4, 5],
                                    decode=lambda ids, **kwargs: " ".join(str(token) for token in ids))
        backend = MLXBackend(model, tokenizer, profile, "tiny-random-qwen", tok_budget=32,
                             grad_ckpt=True, gen_batch=1, mem_limit=2e9, cache_limit=0.1e9)
        initial = dict(tree_flatten(model.trainable_parameters()))
        mx.eval(initial)
        backend.train_begin(3, 0.001)
        for step in range(2):
            metrics = backend.train_step([([1, 4, 5, 6, 2], 3)], [([1, 7, 8, 2], 2)], step)
            self.assertTrue(all(math.isfinite(value) for value in metrics.values()), metrics)
        changed = dict(tree_flatten(model.trainable_parameters()))
        self.assertTrue(any(not bool(mx.array_equal(initial[key], value)) for key, value in changed.items()))
        self.assertTrue(all(bool(mx.all(mx.isfinite(value))) for value in changed.values()))
        generated = backend.generate(["synthetic prompt"], 2)
        self.assertEqual(len(generated), 1)
        self.assertIsInstance(generated[0], str)
        ids = mx.array([[1, 4, 5]])
        expected = model(ids)
        mx.eval(expected)
        with tempfile.TemporaryDirectory(prefix="tiny-qwen-adapter-") as tmp:
            path = Path(tmp) / "adapter"
            backend.save_adapter(path)
            backend.load_adapter(None)
            backend.load_adapter(path)
            restored = model(ids)
            mx.eval(restored)
            self.assertTrue(bool(mx.allclose(expected, restored, atol=1e-5)))
            # This is the same native loader used by mlx_lm.server --adapter-path.
            daytime = load_adapters(tiny_model(quantized=True), str(path))
            daytime.eval()
            actual = daytime(ids)
            mx.eval(actual)
            self.assertTrue(bool(mx.allclose(expected, actual, atol=1e-5)))
        backend.close()


if __name__ == "__main__":
    unittest.main()
