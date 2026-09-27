# C1 model availability

**Shown:** the saved grid LoRA tensors exist locally at
`/Users/ben-hannan/premonition-models/dl5-adapters/dl5-S-s8.pt` and `dl5-S-s9.pt`.
The exact original MiniCPM5-1B base revision required by PASSMARKS was not found
in the checked model roots: `premonition-models`, `premonition-weights`, the
standard Hugging Face cache and the current workspace runtime. Merged listener
models in those roots are different models and cannot substitute for that base.

**Untested:** real MiniCPM base/adapter prefill and cached generation parity.
Without the exact base, C1 is INCONCLUSIVE for real 1B serving. No model was
downloaded and neither the PC nor dl-9 was touched.

`test_retention_chat.py` instead exercises a tiny causal model constructed from
code, with actual attention caching over six generated tokens. This tests the
software mechanism only; it must never be reported as a 1B experiment or a
retention/learning success on general questions.

The earlier learned-gate draft was not run and was discarded when Ben clarified
that dl-9 already runs on the PC. No new router or training text was fitted.
