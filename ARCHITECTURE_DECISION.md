# Architecture decision

Date: 2026-09-18

## Selected model

The primary implementation is a from-scratch **depth-recurrent transformer** with a token-structured temporary workspace and a separate four-head delta-rule persistent memory.

- Reader width: 256
- Prelude: one pre-norm transformer layer
- Recurrent core: two shared pre-norm transformer layers, iterated six times
- Persistent memory: four independent 128 × 128 float32 matrices (262,144 bytes total)
- Writer: one transformer layer; receives only the accepted teaching sentence and emits four unit keys and four values
- Write: `W_h' = W_h + (v_h - W_h k_h) k_h^T`, exactly once per head per accepted sentence
- Read: every recurrent step computes fresh queries from the current token workspace, then reads all four matrices without mutating them
- Workspace: reset before every query and never serialized
- Output: bounded cross-attention answer slots over the final workspace
- Trainable parameters in the implemented model: 4,843,361

The existing 700K GRU learner remains a measured ablation baseline. It is not the selected final backbone: its single-vector workspace is a likely bottleneck for multi-hop facts and procedure execution.

## Why this architecture

It is the smallest reviewed design that combines all three required properties:

1. accepted teachings make closed-form, inspectable persistent changes without fine-tuning the main network;
2. later retrievals can depend on earlier retrieved results;
3. temporary state has token-level structure for names, lists, and intermediate values.

Broad English is deliberately deferred. The pilot learns a controlled grammar from scratch. A frozen pretrained language front end is the fallback if the separately trained in-context interpreter control fails at both tested widths.

## Decision-changing evidence

- Switch the front end to a frozen small language model if the in-context interpreter control fails at both widths.
- Treat writer/reader co-adaptation as the blocker if oracle-written memory passes chaining while the learned writer plateaus.
- Switch the persistent substrate to a byte-matched slot store if it beats the delta store by at least ten points on corrected two-hop queries with a small soft-to-hard gap.

## Implementation status

`memorylab/transformer_model.py` implements the selected reader, writer, recurrent memory reads, four-bank delta writes, bounded decoder, and fresh-workspace inference. The token workspace is the query tokens plus one slot token per memory head; each step's fresh read is added into its slot, the slots persist across steps, and the decoder attends over tokens and slots. `pc-memory --backbone transformer` and `smoke`/`pilot`/`evaluate --backbone transformer` run end to end with bit-exact (logit-level) checkpoint/restart identity.

2026-09-18 fixes, each found by measurement:

- Checkpoint theta views used only `named_children()`, so the transformer's root-level `positions` and `memory_head_embedding` were never saved; every transformer restart/resume reinitialized them. Fixed; restart identity now also requires identical logits, because token-only comparison passed vacuously for a degenerate model.
- Reader v1 discarded each step's memory tokens after the core layers. Measured on PC-E: step-0 retrieval was correct but later queries drifted to an item-independent fixed point and the decoder ignored W (logit change 0.005; accuracy equal with and without W). Reader v2 kept transformed memory slots recurrently accumulated across steps and scaled token embeddings to std d^-1/2. PC-C then exposed a second defect: with both oracle memory reads exact (cosine 1.0) and the matched one-hop path at 100%, the two-hop decoder still collapsed to 6.25%. Reader v3 resets the read slots every recurrent step, lets the token workspace carry prior-step information, and exposes only the latest transformed read slots to the decoder. Tensor shapes and parameter count are unchanged; `reader_version: 3` rejects v1/v2 checkpoints. The transformer needs lr 3e-4 (1e-3 failed in ablation).

Measured PC-memory controls, RTX 5070 Ti, identical protocol for both backbones (fresh start, 2,500 PC-E + 2,500 PC-W steps, orthogonality weight 50, 16 items, 256 held-out validation queries):

| Backbone | Seed | PC-E | PC-W | W=0 | Wall time |
|---|---|---|---|---|---|
| GRU 0.70M | 0 | 85.5% | 83.2% | 14.1% | 269 s |
| GRU 0.70M | 1 | 92.2% | 89.8% | 16.0% | 268 s |
| Transformer 4.84M (reader v2) | 0 | 84.8% | 81.3% | 12.9% | 425 s |
| Transformer 4.84M (reader v2) | 1 | 88.7% | 87.9% | 14.5% | 424 s |

Neither backbone passes the preset gates (PC-E >= 95%, PC-W >= 90%). On these single-hop controls the transformer does not beat the GRU (mean about 2 points lower, within seed noise) while costing about 1.6x wall time. Its expected advantage, multi-hop chaining and structured intermediate values, is not yet tested. GPU utilization is low (about 205 MiB peak; steps are bound by kernel launches and synchronization), so larger item batches are nearly free. Raw results: `artifacts/benspc/`.

First tier-2 learned-memory probe (transformer reader v2, seed 0, 600 tier-2 optimizer steps, lr 3e-4) is a negative but not yet a chaining verdict. The scored checkpoint was evaluated separately after training: overall exact match 10.94% on 64 held-out queries; corrected two-hop 6.25%, its paraphrase 6.25%, single-hop control 6.25%, and distractor control 25.0%. Zero-W exact match was 0%, and all 64 queries changed both logits and generated tokens when W was restored, so W is causal but the answer path is still output-collapsed at this training point. Because the required single-hop control also failed, this result cannot distinguish "cannot re-key" from "reader/decoder not trained yet." The contract's PC-C oracle-written, teacher-forced chain control is therefore the next required discriminator before making any claim about recurrent chaining.

PC-C is now implemented as an evaluator-only positive control: oracle W stores a first-hop key to a second-hop key and that second-hop key to the corrected tag code; the evaluator injects only the second-hop key at reasoning step 2. The injected key is derived from the canonical `relation_value_key_probe()` text with placeholder target `unknown`, so the scored target cannot influence either key. The writer is frozen, held-out validation is separate, W=0 is measured, and restart verification reconstructs the injected cue after loading rather than serializing temporary evaluator state.

Measured PC-C on BensPC RTX 5070 Ti, transformer seed 0, 2,000 steps, lr 3e-4, 16 held-out worlds / 32 two-hop queries:

| Reader | Two-hop | Matched one-hop | W=0 two-hop | W=0 one-hop | Restart | Wall time |
|---|---:|---:|---:|---:|---|---:|
| v2 accumulated slots | 6.25% | 100% | 6.25% | 6.25% | token-identical, logits differed by 1.9e-6 | 132 s |
| v3 fresh-per-step slots | **100%** | **100%** | **0%** | **0%** | bit-exact logits/tokens, workspace absent | 132 s |

This passes the preset PC-C >=90% gate and localizes the old failure to the recurrent slot-carry/read-decode path rather than an inability of the transformer to use two sequential memory reads. It does **not** yet show that the learned workspace can infer the second-hop key on its own: PC-C deliberately teacher-forces that key. The next research discriminator remains learned re-keying/adaptive retrieval, after the prerequisite learned-key/writer controls are brought through their gates. Raw v3 result and checkpoint are under `artifacts/benspc/pc-chain-transformer-reader3-seed0-final-20260918.*`.

The same run exposed a wall-clock accounting defect: a nominal 300 s pilot took 346.7 s because the selected transformer's ~58 MiB AdamW recovery checkpoint was serialized after the training deadline inside the evaluation reserve. `run_experiment` now reserves an additional measured 120 s checkpoint window for full-size transformer pilots; tiny transformer fixtures and GRU runs keep the previous budget. After PC-C and reader v3, the local regression suite is 98/98 and the BensPC platform-applicable suite is 86/86.

These are controls, not research claims. Multi-hop reasoning, transferable method learning, learned stopping, broad English, an RL write policy, and long-term forgetting resistance are not demonstrated.

## Provenance

This decision incorporates the teaching-to-test contract, the five-reviewer adversarial report, the measured failures of the GRU baseline, and Claude/Fable's 2026-09-18 architecture review. The architecture review's broader literature and resource estimates remain hypotheses until reproduced locally; the parameter count, state sizes, update equations, tests, and restart behavior above are measured in this repository.
