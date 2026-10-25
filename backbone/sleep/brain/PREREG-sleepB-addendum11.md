# Sleep-B addendum 11: the sleep recipe on K2-Horizon, small tier (3.7B) bf16 vs q4, and a MoVA-36B q4 speed bench (written 2026-10-25 ~12:50Z, before any addendum-11 code or run)

Labels: shown / suggested / untested. Week-2 world (sha256 70db7146...), tests and scoring as addendum 9. Not the village model, not the
card experiments.

## Why
Ben (2026-10-25 12:36Z and 12:40Z): run sleep on K2-Horizon in two tiers. The small tier, K2-Horizon-3.7B, is for small computers. The big
tier, K2-Horizon-MoVA-36B-A4B, is for powerful ones. For each, have sleep run on a q4 version and compare it with the full-precision one.
For MoVA only the q4 version matters ("we'll never be able to do full precision for MOVA"). The recipe is addendum 9's adopted
ab_ob_b4_nb, which on Qwen3.5-2B gave recall 91.5 / 91.0 and two-hop 38.5 / 35.9 on two seeds.

## Models
- IFM/K2-Horizon-3.7B, revision 9d280ff742235796925c9fe3cf243dc1beea5c08. It is dense: 36 layers, hidden 2560, a vocab of 250,624, and
  about 5.1B parameters with embeddings (about 10 GB in bf16). It is a reasoning model, Apache 2.0, and its code loads with
  trust_remote_code.
- IFM/K2-Horizon-MoVA-36B-A4B (bench only here): 48 layers, 100 routed experts (top 8) plus 1 shared expert, MoVA attention, 37.4B
  parameters (75 GB in bf16).

## Port (no behaviour change for Qwen runs; checked by the selftest and a CPU smoke)
- **Loading:** `--model` takes a K2 repo id with trust_remote_code and a pinned revision.
- **Thinking off:** K2 always opens a thinking block. Every prompt ends with an empty one, `<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>`,
  as the backbone thread's no-think template does. Training targets follow the same prefix.
- **End of turn:** chat turns end with `<|ifm|im_end|>` (id 250019). It is the stop token for generation and the last training target.
- **LoRA:** the same rank, alpha and target names as for Qwen (self_attn q/k/v/o and mlp gate/up/down). On the 3.7B those are all of its
  attention and MLP linears.
- **Recipe:** everything else as ab_ob_b4_nb: hyperparameters, work scale 4, names pass, bridge prompt, open-book rehearsal, gate. No
  tuning for K2. This is a transfer test, not a tuned run.
- **q4 base for the 3.7B:** the M2 thread's `--q4-base`. Before LoRA, every Linear and Embedding weight of the frozen base is replaced by
  an MLX-style affine 4-bit fake-quantized copy (group 64), so the base is numerically what an MLX q4 model on the Mac would be. It is
  computed in bf16 memory on the GPU.

## Arms (Week-2, work scale 4, seed 1)
- **k2s_bf16:** ab_ob_b4_nb on K2-Horizon-3.7B, bf16 base.
- **k2s_q4:** the same with `--q4-base`.

## Pass marks (fixed now)
- **No harm (each arm):** ARC-Easy >= that arm's pre-sleep ARC-Easy - 5 (the same 500 questions, measured by the port on the base before
  night 1), and diary pooled >= the same model's diary score before sleep (`base_diary`) - 5.
- **T1 (the recipe transfers to K2-3.7B):** k2s_bf16 recall on C2+C4 >= 75 (Qwen3.5-2B: 91.5; Week-2 control on Qwen: 53).
  **Wrong if** the tagger's mention recall is >= 0.5 but recall is < 60: then the note-taking works and the night's learning does not transfer.
- **Q1 (sleeping on q4 keeps most of the memory):** k2s_q4 - k2s_bf16 >= -5 on C2+C4 recall, paired. A loss beyond -5 with p < 0.05 is
  **shown** harm from q4.
- **Reported, not marked:** two-hop, reverse, changed-new, routine; tagger recall and precision; names-pass counts; chain yield; reverts;
  k2s_bf16 vs Qwen ab_ob_b4_nb seed 1 (paired on the same questions); wall time and dollars.
- **Expectation (not a mark):** k2s_bf16 recall 80-92; q4 loses 3-10 points (the M2 thread saw a 16-point q4 loss on Qwen at 1x work on
  Week-1).

## MoVA-36B q4: speed bench only (no sleep arm in this addendum)
- **Base:** a real 4-bit base (bitsandbytes NF4 on every Linear, so about 20 GB) on one RTX 5090, with LoRA on top. This is a different
  4-bit scheme from MLX's, and the report says so.
- **Bench, at most one hour:** load time, peak memory, seconds per training step at the Week-2 token budget, and generation tokens per
  second for the tagger and dream prompts. It runs with the released expert loop, and with a faster expert path if one is ready.
- **Output:** a cost estimate for one Week-2 4x-work MoVA q4 sleep arm, sent to the coordinator before any full run.

## Compute
- Two RTX 5090 boxes for the 3.7B arms, about 2-2.5 h each (cap $3, approved 12:39Z), on proven hosts. One RTX 5090 hour for the MoVA
  bench (cap $1.50, approved 12:39Z).
- A box that is not running within 10 minutes is dropped. Each JSON is pulled after the self-stop, and only then is the box destroyed.
