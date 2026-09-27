"""Cached autoregressive computation on a tiny code-generated test model.

Software parity checks, NOT measurements of the absent MiniCPM base.
No pretrained model, prompt text, learned gate, or external service is used.
"""
import copy
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))
from claude_blurt2 import add_lora
from retention import RequestScopedAdapter
from retention_chat import install_controller, route


class TinyCausal(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(32, 16)
        self.q_proj = nn.Linear(16, 16)
        self.k_proj = nn.Linear(16, 16)
        self.v_proj = nn.Linear(16, 16)
        self.o_proj = nn.Linear(16, 16)
        self.norm = nn.LayerNorm(16)
        self.head = nn.Linear(16, 32)

    def forward(self, input_ids, past_key_values=None):
        x = self.embedding(input_ids)
        q, k, v = self.q_proj(x), self.k_proj(x), self.v_proj(x)
        prefix = 0
        if past_key_values is not None:
            pk, pv = past_key_values
            prefix = pk.shape[1]
            k, v = torch.cat((pk, k), 1), torch.cat((pv, v), 1)
        query_pos = torch.arange(q.shape[1], device=q.device) + prefix
        key_pos = torch.arange(k.shape[1], device=q.device)
        allowed = query_pos[:, None] >= key_pos[None, :]
        scores = (q @ k.transpose(-1, -2)) / math.sqrt(q.shape[-1])
        attn = scores.masked_fill(~allowed, float("-inf")).softmax(-1)
        logits = self.head(self.norm(x + self.o_proj(attn @ v)))
        return SimpleNamespace(logits=logits, past_key_values=(k, v))

    def generate(self, input_ids, max_new_tokens=6, past_key_values=None):
        sequence, current, cache = input_ids, input_ids, past_key_values
        for _ in range(max_new_tokens):
            output = self(current, past_key_values=cache)
            current = output.logits[:, -1:].argmax(-1)
            sequence = torch.cat((sequence, current), 1)
            cache = output.past_key_values
        return sequence


class CachedGenerationTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(2729)
        self.model = TinyCausal().eval()
        self.base = copy.deepcopy(self.model)
        add_lora(self.model, r=4, dropout=.05)
        with torch.no_grad():
            for layer in self.model.modules():
                if hasattr(layer, "B"):
                    layer.B.normal_(std=.2)
        self.model.eval()
        self.inputs = torch.randint(0, 32, (2, 5))
        with torch.inference_mode():
            self.original_on_logits = self.model(self.inputs).logits.clone()
            self.original_on_reply = self.model.generate(self.inputs)
            self.base_logits = self.base(self.inputs).logits.clone()
            self.base_reply = self.base.generate(self.inputs)
        self.controller = RequestScopedAdapter(self.model)

    def test_prefill_logits_and_six_cached_decode_steps_match(self):
        with torch.inference_mode(), self.controller.scope(False):
            self.assertTrue(torch.equal(self.model(self.inputs).logits, self.base_logits))
        with torch.inference_mode(), self.controller.scope(True):
            self.assertTrue(torch.equal(self.model(self.inputs).logits, self.original_on_logits))
        self.assertFalse(torch.equal(self.original_on_logits, self.base_logits))
        for on in (True, False, False, True, False):
            got = self.controller.generate(enabled=on, input_ids=self.inputs)
            self.assertTrue(torch.equal(got, self.original_on_reply if on else self.base_reply))

    def test_adapter_write_leaves_base_prefill_and_cache_decode_identical(self):
        before = self.controller.base_digest()
        with torch.no_grad():
            for layer in self.model.modules():
                if hasattr(layer, "B"):
                    layer.B.mul_(10)
        self.assertEqual(before, self.controller.base_digest())
        self.assertTrue(torch.equal(self.controller.generate(input_ids=self.inputs), self.base_reply))
        with torch.inference_mode(), self.controller.scope(False):
            self.assertTrue(torch.equal(self.model(self.inputs).logits, self.base_logits))

    def test_foreign_kv_cache_refused_at_serving_entrypoint(self):
        with torch.inference_mode(), self.controller.scope(True):
            cache = self.model(self.inputs).past_key_values
        with self.assertRaisesRegex(ValueError, "reuse attention caches"):
            self.controller.generate(enabled=False, input_ids=self.inputs[:, -1:], past_key_values=cache)

    def test_live_runner_import_and_explicit_route(self):
        self.assertFalse(route("general"))
        self.assertTrue(route("grid"))
        with self.assertRaises(ValueError):
            route("unknown")
        model = copy.deepcopy(self.base)
        serving = install_controller(model)
        self.assertTrue(torch.equal(serving.generate(input_ids=self.inputs), self.base_reply))


if __name__ == "__main__":
    unittest.main()
