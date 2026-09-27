# Retention through immutable serving paths

The observed failures have two distinct causes. Training shared parameters
changes old computations. Even with every old tensor frozen, adding router logits
changes which expert runs and the softmax multiplier on that expert. The latter
was measured in the existing `rsn358e` diagnostic: the original router group and
its original normalization restore the old grids score.

The engineering fix tested here is to keep a complete released computation
unchanged while training a candidate elsewhere. This follows the broad principle
of [Progressive Neural Networks](https://arxiv.org/abs/1606.04671); it is not a
claim to have invented a new continual-learning algorithm.

## Small reasoner

Save an entire mastered model and its stop rule. Train a full clone for the next
skill, allowing the new learner to change attention, embeddings and output heads
as well as its MLP. Select the released snapshot once, using the existing typed
task input. A skill registry must reject unknown IDs rather than silently send
them to the most recently trained model.

This permits old-task output identity, conditional on the same preprocessing,
task identity and execution settings. Storage grows by one small model per
skill. It does not establish a benefit at equal total parameters, automatic task
recognition, or transfer between skills.

Run the experiment with `reasoner/codex_retention_reasoner.py`; its protocol and
measurements are in `artifacts/codex-retention-20260927/reasoner/`.

## Chat model

Keep the base frozen and keep each published skill adapter immutable. A learned
switch may select the adapter from frozen-base prompt features. Compute that
decision before generation, and retain it for the entire answer and its KV
cache. An inactive adapter must bypass its update entirely. The default branch
is the base model; confidence thresholds require separate calibration data.

`implementation/retention.py`'s `RequestScopedAdapter` works with the repository's
`claude_blurt2.add_lora` layers, preserving their checkpoint keys:

```python
# Add this artifact's implementation/ directory to sys.path.
from retention import RequestScopedAdapter

# Load the frozen base, add LoRA, load its saved A/B tensors, then:
model.eval()
serving = RequestScopedAdapter(model)

# Extract router features through the default, base-only path.
# Choose once; never reuse a KV cache from a different route.
use_skill = bool(router_decision)
answer = serving.generate(enabled=use_skill, **tokenized_prompt)

# For an existing synchronous generation helper:
with serving.scope(use_skill):
    answer = existing_generation_helper(model)
```

Do not train this published model concurrently. Train an independently loaded
candidate and validate it before replacing a version. Do not return a lazy
stream from the scope: the scope must remain open until decoding finishes.

Scopes use per-context state, rather than global mutable LoRA scales. They
restore the previous route on nesting and exceptions, and bypass even a poisoned
adapter. `base_digest()` checks all base weights and buffers while excluding
the adapter's A/B parameters. It does not fingerprint tokenizer, prompt code,
model configuration or dependencies; those must also be pinned in deployment.

The project already runs dl-9 for learned routing. We do not duplicate it. The
artifact's `chat/retention_chat.py` is an untested live parity runner using an
explicit caller domain ID and locally supplied weights; `chat/STATUS.md` records
that the exact 1B base was not found locally. No model is downloaded. Its saved
dl-5 adapters are finding-only software fixtures, not clean training evidence.
`chat/test_retention_chat.py` checks real cached attention and token generation
in a tiny code-generated model; it does not measure MiniCPM capability.

## Release criteria

Measure lost previously-correct answers separately from gained answers. Gains
cannot compensate for losses in a retention guarantee. Check every prior skill
after every later training phase, and include save/reload, alternating requests,
stopping behavior and false routing. New-skill learning is an independent
requirement: keeping an untrained learner unchanged is not success.

Tests with known task identities and identical old paths establish scoped
functional retention. A learned switch supplies only measured reliability.
Finite clean panels never establish universal no-forgetting: for example, zero
failures on 200 independent trials still has a one-sided 95% binomial upper
failure-rate bound of about 1.49%. Paraphrases, mixed tasks and unknown inputs
need separate evaluation. Do not use a final panel to tune the router or decide
which checkpoint to publish.

This is a candidate implementation and experiment package, not a deployment to
the existing chat service or a replacement of registered earlier FAIL results.
