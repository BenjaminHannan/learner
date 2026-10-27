"""One initialization-only hypothesis; inherited runtime, no task imports.

SpatialInitVariant(source.tok, top_k=1, raw_sum=True) adds +1 only to
recurrent.bias_ih[width:2*width], once after the unchanged base constructor.
retention_init=False is the exact base-initialization control. Supply the same
starting RNG state for paired constructors. Checkpoint loads replace these
values normally; never reapply this initialization to a trained checkpoint.
"""
from __future__ import annotations

import torch

from spatial_relation import SpatialRelation, SOURCE_WIDTH, VOCAB


RECIPE = "gru_update_bias_ih_add_1_v1"
BASE_SHA256 = "b6715f7cb5cfc35371f2c4e1eb374d17fbb9354f90a1e68d53ab8187cd7d0ef6"


class SpatialInitVariant(SpatialRelation):
    """Same parameters and methods; only the named initial bias slice changes."""

    def __init__(self, source_embedding, *, retention_init=True, **kwargs):
        if type(retention_init) is not bool:
            raise TypeError("retention_init must be bool")
        super().__init__(source_embedding, **kwargs)
        self.init_recipe = RECIPE if retention_init else "base"
        if retention_init:
            with torch.no_grad():
                self.recurrent.bias_ih[self.width:2 * self.width].add_(1.0)


def selftest():
    """CPU1 synthetic mechanics, <1s excluding interpreter/torch import.

    No checkpoints, task generators, targets, CE, optimizer, fit, or scoring.
    The scalar squared-logit probe exists only to test autograd connectivity.
    """
    import hashlib
    import math
    from pathlib import Path
    import platform
    import time

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    started = time.perf_counter()
    here = Path(__file__).resolve().parent
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(here / "spatial_relation.py") == BASE_SHA256
    torch.manual_seed(90729)
    source = torch.nn.Embedding(VOCAB, SOURCE_WIDTH)
    source_before = source.weight.detach().clone()
    tokens = torch.randint(VOCAB, (2, 2, 3))
    slots = torch.randint(2, tokens.shape)
    tokens_before, slots_before = tokens.clone(), slots.clone()
    checks = []
    for seed in (0, 1):
        init_seed = 74120929 + 100000 * seed
        torch.manual_seed(init_seed)
        base = SpatialRelation(source, top_k=1, raw_sum=True)
        base_rng = torch.get_rng_state().clone()
        torch.manual_seed(init_seed)
        disabled = SpatialInitVariant(source, top_k=1, raw_sum=True,
                                      retention_init=False)
        assert torch.equal(torch.get_rng_state(), base_rng)
        torch.manual_seed(init_seed)
        variant = SpatialInitVariant(source, top_k=1, raw_sum=True)
        assert torch.equal(torch.get_rng_state(), base_rng)
        original, control, changed = base.state_dict(), disabled.state_dict(), variant.state_dict()
        assert original.keys() == control.keys() == changed.keys()
        differences = []
        for name, tensor in original.items():
            assert torch.equal(tensor, control[name]), name
            assert tensor.shape == changed[name].shape and tensor.dtype == changed[name].dtype
            expected = tensor.clone()
            if name == "recurrent.bias_ih":
                expected[base.width:2 * base.width].add_(1.0)
            assert torch.equal(expected, changed[name]), name
            if not torch.equal(tensor, changed[name]):
                differences.append(name)
        assert differences == ["recurrent.bias_ih"]
        differing_scalars = int((original[differences[0]] != changed[differences[0]]).sum())
        assert differing_scalars == base.width == 48
        assert base.counts() == variant.counts() == disabled.counts()
        assert all(getattr(SpatialInitVariant, name) is getattr(SpatialRelation, name)
                   for name in ("embed", "initial_state", "step", "route", "communicate",
                                "read", "forward", "counts"))
        state_before = {k: v.clone() for k, v in changed.items()}
        with torch.no_grad():
            e, offsets = variant.embed(tokens, slots)
            assert not bool(e[..., variant.dynamic_channels].any())
            saved = e.clone()
            h = variant.step(e)
            torch.testing.assert_close(variant.step(torch.zeros_like(e), e, *offsets), h,
                                       rtol=0, atol=0)
            assert torch.equal(e, saved)
            assert torch.equal(h[..., variant.anchor_channels], e[..., variant.anchor_channels])
            assert torch.equal(variant.rounds(h), torch.ones(2, dtype=torch.long))
            assert torch.equal(variant.answer_mask(h), slots.reshape(2, 6).bool())
            torch.testing.assert_close(variant.step(h.flip(0)), variant.step(h).flip(0),
                                       rtol=1e-5, atol=3e-6)
            torch.testing.assert_close(variant.step(h[:1]), variant.step(h)[:1],
                                       rtol=1e-5, atol=3e-6)
            # Direct GRU oracle: reset/update/new order and +1 on update only.
            x = torch.randn(3, base.recurrent.input_size)
            old = torch.randn(3, base.width)
            gi = torch.nn.functional.linear(x, base.recurrent.weight_ih, base.recurrent.bias_ih)
            gh = torch.nn.functional.linear(old, base.recurrent.weight_hh, base.recurrent.bias_hh)
            ir, iz, inn = gi.chunk(3, -1)
            hr, hz, hn = gh.chunk(3, -1)
            z_before, z_after = (iz + hz).sigmoid(), (iz + hz + 1).sigmoid()
            assert bool((z_after > z_before).all())
            candidate = (inn + (ir + hr).sigmoid() * hn).tanh()
            oracle = z_after * old + (1 - z_after) * candidate
            oracle_error = float((variant.recurrent(x, old) - oracle).abs().max())
            assert oracle_error < 5e-7
            # Loading into the original class reproduces the variant runtime.
            base.load_state_dict(variant.state_dict(), strict=True)
            torch.testing.assert_close(base(tokens, slots, rounds=3),
                                       variant(tokens, slots, rounds=3), rtol=0, atol=0)
            disabled.load_state_dict(variant.state_dict(), strict=True)
            assert all(torch.equal(v, disabled.state_dict()[k]) for k, v in changed.items())
        hidden_outputs, public_outputs = [], []
        def capture(destination):
            def hook(_module, _args, output):
                output.retain_grad()
                destination.append(output)
            return hook
        hooks = [variant.recurrent.register_forward_hook(capture(hidden_outputs)),
                 variant.public_proposal.register_forward_hook(capture(public_outputs))]
        try:
            logits = variant(tokens, slots, rounds=24, grad_rounds=None,
                             output_rounds=(23, 24))
            assert logits.shape == (2, 2, 2, 3, VOCAB)
            assert bool(torch.isfinite(logits).all())
            logits.square().mean().backward()
        finally:
            for hook in hooks:
                hook.remove()
        assert len(hidden_outputs) == len(public_outputs) == 24
        first_round_gradients = {
            "hidden_l1": float(hidden_outputs[0].grad.abs().sum()),
            "public_proposal_l1": float(public_outputs[0].grad.abs().sum()),
        }
        assert all(math.isfinite(x) and x > 0 for x in first_round_gradients.values())
        grads = {n: float(p.grad.abs().sum()) for n, p in variant.named_parameters()
                 if p.grad is not None}
        assert all(math.isfinite(v) for v in grads.values())
        for name in ("endpoint.weight", "router.weight", "recurrent.bias_ih",
                     "source_projection.weight", "public_proposal.weight"):
            assert grads[name] > 0, name
        assert any(v > 0 for n, v in grads.items() if n.startswith("experts."))
        assert variant.source.weight.grad is None and not variant.source.weight.requires_grad
        assert torch.equal(source.weight, source_before)
        assert all(torch.equal(v, variant.state_dict()[k]) for k, v in state_before.items())
        checks.append({"seed_label": seed, "initialization_seed": init_seed,
                       "source_kind": "synthetic random embedding, not qualified source",
                       "only_changed_parameter": differences[0], "changed_scalars": differing_scalars,
                       "identical_shapes_and_disabled_weights": True,
                       "identical_constructor_rng_consumption": True,
                       "inherited_runtime_methods": True, "state_and_source_immutable": True,
                       "zero_dynamic_start": True, "strict_checkpoint_and_runtime_parity": True,
                       "batch_permutation_removal_and_zero_start_parity": True,
                       "update_gate_oracle_max_abs_error": oracle_error,
                       "first_round_gradients": first_round_gradients,
                       "finite_nonzero_endpoint_router_expert_gradients": True})
    assert torch.equal(tokens, tokens_before) and torch.equal(slots, slots_before)
    seconds = time.perf_counter() - started
    assert seconds < 1., seconds
    return {"passed": True, "recipe": RECIPE, "only_intervention":
            "add 1.0 to recurrent.bias_ih[width:2*width] after complete base construction",
            "device": "cpu", "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "seconds_excluding_interpreter_and_torch_import": seconds,
            "torch_version": torch.__version__, "platform": platform.platform(),
            "task_items_generated_or_evaluated": 0, "query_labels_used": 0,
            "checkpoint_tensors_loaded": 0, "optimizer_steps": 0,
            "trained_or_scored": False, "qualified_source_seeds_tested": False,
            "checks": checks, "counts": variant.counts(),
            "code_sha256": {"spatial_relation.py": sha(here / "spatial_relation.py"),
                            "spatial_init_variant.py": sha(Path(__file__).resolve())}}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(selftest(), indent=2))
