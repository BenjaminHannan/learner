# LFM3 training and served-weight identity

Ben's active chat uses `LFM3-1.7B-QAD-Q4_0.gguf`; sleep trains the cached `LiquidAI/LFM3-1.7B` HF checkpoint with the `lfm3_mps` profile. Both are LFM3, but exact underlying weight equivalence has not been established. The [official GGUF model card](https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF) explicitly identifies Q4_0 as a checkpoint trained through quantization-aware distillation. The [HF model card](https://huggingface.co/LiquidAI/LFM3-1.7B) describes the BF16 checkpoint.

Consequently an HF held-out improvement is not proof that its exported adapter delivers the same improvement through the active quantized server. Current real native and Windows all-zero-adapter smokes establish export loading, protocol, process cleanup and retention checks only. They do not establish learned-fact transfer. The current served policy permits a zero/zero held-out tie; that is a retention result, not evidence of learning.

No model switch, inference interruption, production adapter promotion or acceptance-policy change was made for this finding. There is no accepted production adapter. The existing failed control and interrupted replay results remain unchanged.

Next learning-quality experiment: preserve a trained nonzero adapter from a fixed synthetic control, export it, and measure the same unseen paraphrases through HF and an isolated native QAD server, with a recorded base/incumbent comparison. If a plain quantization of the HF checkpoint is compared, keep its bytes, tokenizer, prompts and generation settings recorded and separate. Do not infer equivalence from architecture names, artifact paths or an on/off tie. Run only when resources permit without disturbing active user work.
