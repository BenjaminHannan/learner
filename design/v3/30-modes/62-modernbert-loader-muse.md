# 62 — ModernBERT plain-PyTorch loader (fable_modernbert58, 2026-09-21)

## Goal

Give the ears a second borrowed encoder, ModernBERT-base
(`answerdotai/ModernBERT-base`, Apache-2.0,
https://huggingface.co/answerdotai/ModernBERT-base), with every line around the
weights our own: `scripts/fable_modernbert58_loader.py` reuses only
`read_safetensors` and `SENTENCES` from `scripts/fable_bert_loader.py` (never edited).
Doc 47c ranked it best for extraction but hardest to load; this doc records how each
hard part maps to plain PyTorch. Companions: `artifacts/fable-modernbert58-20260921/`
(PASSMARKS sealed pre-run, RESULTS with the registered FAIL).

## Architecture mapping (transformers 5.x eager path, fp32)

Config: 22 layers, hidden 768, 12 heads (head dim 64), FF 1152, vocab 50,368,
eps 1e-5, all biases off (`attention_bias`, `mlp_bias`, `norm_bias` false).

- **Embeddings.** Token embedding only (pad id 50283), then LayerNorm, no bias, no
  dropout at eval. No absolute positions and no token-type table; positions come from RoPE.
- **Layer i.** Global (full) attention iff `i % 3 == 0` (layers 0, 3, …, 21; eight
  global, fourteen sliding). Pre-LN residuals: `x += attn(norm(x))`, then
  `x += mlp(mlp_norm(x))`. Exception: layer 0's attention norm is the identity, so
  the first attention reads raw embeddings. Final LayerNorm after layer 21.
- **Attention.** One fused `Wqkv` (768→2304, no bias), reshaped to
  (batch, 12, seq, 64) per q/k/v; NeoX-style RoPE (`rotate_half`) on q and k;
  scale 1/√64; softmax in fp32; fused `Wo` (no bias). Global layers mask padding
  only; sliding layers additionally require |query − key| ≤ 64 (half of
  `local_attention` 128), ANDed with the padding mask — replicated from
  `sliding_window_bidirectional_overlay` in transformers' `masking_utils.py`.
- **RoPE.** Per layer type: inv_freq = 1/θ^(arange(0,64,2)/64), θ = 160,000 global /
  10,000 local; positions 0..T−1 over the padded batch (padded queries still get
  positions, their outputs are ignored downstream). cos/sin cached per (type, T),
  applied in float then cast back — matches `apply_rotary_pos_emb`.
- **MLP (GeGLU).** `Wi`: 768→2304, chunk into (input, gate), `Wo2(gelu(input)·gate)`
  with exact erf GELU (`F.gelu` default = `ACT2FN["gelu"]`). No biases, no dropout.
- **Weight rename.** `model.embeddings.tok_embeddings/norm.weight`,
  `model.layers.i.{attn.Wqkv, attn.Wo, attn_norm, mlp_norm, mlp.Wi, mlp.Wo}`,
  `model.final_norm.weight`. Layer 0 has no `attn_norm` key; masked-LM head keys
  (`decoder.bias`, `head.dense/norm.weight`; `decoder.weight` is tied/absent) are
  skipped. 149,014,272 encoder params.

## Tokenizer (plain Python from `tokenizer.json`)

NFC normalizer; GPT-2-style pre-split
(`'s|'t|'re|'ve|'m|'ll|'d| ?L+| ?N+| ?[^LN\s]+| trailing-space|space`) hand-rolled
with `unicodedata` categories plus char offsets; each piece UTF-8 encoded through
the standard GPT-2 byte map, then canonical BPE (always merge the lowest-rank
present pair; 50,009 merges) with vocab lookup. Non-special added tokens
(multi-space runs, `|||IP_ADDRESS|||`) are pre-split and emitted whole. Framing:
`[CLS]` 50281 … `[SEP]` 50282, pad 50283, unk 50280, truncation to 128. Every BPE
piece inherits its pre-split piece's char span, so `encode` returns
`len(spans) == len(ids)` — the span-pointer input (M3).

## Verification and the registered FAIL

Sealed marks M1–M4; registered `--check` on the 20 reused sentences: M1 20/20 exact
token match, M3 20/20, M4 1.7 s load, pad-vs-single 2.10e-05 — but M2 measured
3.07e-04 against the < 1e-4 bar, so the registered verdict is FAIL and stands.
Post-hoc probe showed ours-vs-eager is bit-exact (0.00) while the reference's own
`sdpa`-vs-`eager` gap is exactly 3.07e-04 (worst on the 83-token sentence): the
implementation is right; the sealed bar met the noisier backend. A re-seal should
pin `attn_implementation="eager"` or use the 1e-3 bar of the BERT loader.

## Limits

`str.isspace()`/`unicodedata` stand in for the `regex`-crate tables; literal
special-token strings in user text are not split; `rope_parameters`-style configs
are not parsed (this snapshot uses `global/local_rope_theta`); pair-input
framing not implemented. None affected the check.

## What it means / What it does not mean

It means the ears now have a loadable, exactly-verified (eager-path) ModernBERT
encoder with span-ready tokenization, built additively with no new dependencies.
It does not mean ModernBERT is selected over SciBERT, nor that span/relation heads
exist — that is later ears work on top of this loader.
