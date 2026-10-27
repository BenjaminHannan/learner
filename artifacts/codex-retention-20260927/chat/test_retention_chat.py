"""Cached autoregressive computation on a tiny code-generated test model.

Software parity checks, NOT measurements of the absent MiniCPM base.
No pretrained model, prompt text, learned gate, or external service is used.
"""
import copy
import hashlib
import inspect
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "implementation"))
from claude_blurt2 import add_lora
from retention import RequestScopedAdapter
import retention_chat as c1
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

    def forward(self, input_ids, past_key_values=None, **kwargs):
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

    def generate(self, input_ids, max_new_tokens=6, past_key_values=None,
                 output_scores=False, return_dict_in_generate=False, **kwargs):
        sequence, current, cache = input_ids, input_ids, past_key_values
        generation_scores = []
        for _ in range(max_new_tokens):
            output = self(current, past_key_values=cache)
            if output_scores:
                generation_scores.append(output.logits[:, -1, :])
            current = output.logits[:, -1:].argmax(-1)
            sequence = torch.cat((sequence, current), 1)
            cache = output.past_key_values
        if return_dict_in_generate:
            return SimpleNamespace(sequences=sequence, scores=tuple(generation_scores), past_key_values=cache)
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

    def test_production_probe_compares_unwrapped_base_and_b2_references(self):
        ids = {"input_ids": self.inputs}
        base_ref = c1.probe_model(torch, self.base, ids, eos_token_id=0)
        original_b2 = add_lora(copy.deepcopy(self.base), r=4, dropout=.05).eval()
        adapter_state = {k: v for k, v in self.model.state_dict().items() if k.endswith((".A", ".B"))}
        original_b2.load_state_dict(adapter_state, strict=False)
        adapter_ref = c1.probe_model(torch, original_b2, ids, eos_token_id=0)
        actual_off = c1.probe_model(torch, self.model, ids, eos_token_id=0,
                                    controller=self.controller, enabled=False)
        actual_on = c1.probe_model(torch, self.model, ids, eos_token_id=0,
                                   controller=self.controller, enabled=True)
        self.assertEqual(actual_off, base_ref)
        self.assertEqual(actual_on, adapter_ref)
        self.assertEqual(actual_on["prefill_logits_sha256"], c1.tensor_hash(self.original_on_logits))
        self.assertNotEqual(actual_on["prefill_logits_sha256"],
                            c1.tensor_hash(self.original_on_logits[:, -1, :]))
        self.assertEqual(len(actual_on["decode_score_sha256"]), 6)
        self.assertEqual(c1.probe_model(torch, self.model, ids, 0, self.controller, False), base_ref)

    def test_strict_adapter_keys_reject_base_tensor_even_with_matching_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = add_lora(copy.deepcopy(self.base), r=16).eval()
            state = {k: v.detach().cpu() for k, v in model.state_dict().items()
                     if k.endswith((".A", ".B"))}
            def save(weights):
                path = root / "dl5-S-s8.pt"
                torch.save(weights, path)
                (root / "dl5-S-s8.json").write_text(json.dumps({
                    "sha256": c1.sha_file(path), "tensors": len(weights)}))
            with patch.object(c1, "ADAPTERS", root), patch.object(c1, "SIDECARS", root):
                save(state)
                self.assertEqual(len(c1.load_adapter(torch, model, 8)), 64)
                bad = dict(state)
                bad.pop(next(iter(bad)))
                bad["q_proj.base.weight"] = model.q_proj.base.weight.detach().cpu()
                save(bad)
                with self.assertRaisesRegex(SystemExit, "A/B tensors"):
                    c1.load_adapter(torch, model, 8)

    def test_snapshot_hashes_cover_files_and_reject_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / c1.PIN
            snapshot.mkdir()
            files = {"config.json": b"{}", "model.safetensors": b"weights",
                     "tokenizer.json": b"tokens", "modeling_demo.py": b"class Model: pass\n"}
            for name, raw in files.items():
                (snapshot / name).write_bytes(raw)
            code = root / "runtime_model.py"
            code.write_text("class RuntimeModel: pass\n")
            manifest = {"revision": c1.PIN,
                        "snapshot_files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
                        "model_code_files": {str(code): c1.sha_file(code)}}
            c1.check_snapshot(snapshot, manifest)
            (snapshot / "tokenizer.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "tokenizer.json"):
                c1.check_snapshot(snapshot, manifest)
            (snapshot / "tokenizer.json").write_bytes(files["tokenizer.json"])
            (snapshot / "extra.txt").write_bytes(b"not committed")
            with self.assertRaisesRegex(ValueError, "file list differs"):
                c1.check_snapshot(snapshot, manifest)

    def test_hash_manifest_must_equal_committed_head_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / "hashes.json"
            committed = b'{"revision":"pinned"}\n'
            path.write_bytes(committed)
            fake_show = SimpleNamespace(stdout=committed)
            fake_head = SimpleNamespace(stdout="commit-id\n")
            with patch.object(c1, "ROOT", root), patch.object(c1.subprocess, "run",
                                                              side_effect=[fake_show, fake_head]), \
                    patch.object(c1, "check_snapshot") as check:
                data, digest, head = c1.committed_manifest(path, root)
                self.assertEqual((data, digest, head),
                                 (json.loads(committed), hashlib.sha256(committed).hexdigest(), "commit-id"))
                check.assert_called_once()
            path.write_bytes(b'{"revision":"changed"}\n')
            with patch.object(c1, "ROOT", root), patch.object(c1.subprocess, "run",
                                                              side_effect=[fake_show, fake_head]):
                with self.assertRaisesRegex(ValueError, "differs from committed"):
                    c1.committed_manifest(path, root)

    def test_loaded_runtime_code_must_match_manifest(self):
        import claude_blurt2 as blurt
        from retention import RequestScopedAdapter

        class FakeTok:
            def apply_chat_template(self):
                return ""

        model, tok = TinyCausal(), FakeTok()
        sources = (model.__class__, model.forward, model.generate, tok.__class__,
                   tok.apply_chat_template, blurt.add_lora, RequestScopedAdapter)
        files = {str(Path(inspect.getfile(item)).resolve()) for item in sources}
        manifest = {"model_code_files": {name: c1.sha_file(Path(name)) for name in files}}
        c1.check_runtime_code(manifest, model, tok)
        manifest["model_code_files"].pop(next(iter(files)))
        with self.assertRaisesRegex(ValueError, "unhashed loaded"):
            c1.check_runtime_code(manifest, model, tok)

    def test_reply_sidecar_writer_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replies.json"
            c1.write_exclusive(path, {"first": True})
            with self.assertRaises(FileExistsError):
                c1.write_exclusive(path, {"first": False})
            self.assertEqual(json.loads(path.read_text()), {"first": True})


if __name__ == "__main__":
    unittest.main()
