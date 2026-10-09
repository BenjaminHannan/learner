# Amazon AGI research on looped LLMs (found 10-06, ET morning)

Method note: summaries below come from the arXiv HTML page and the GitHub README/docs (fetched and read). Numbers are as the authors report them. I did NOT read the last ~38k characters of the paper HTML, and I did not run any code. Nothing here is tested on B2.

## Bottom line
Only ONE Amazon AGI looped-LM paper turned up: **ALoDLM** (Adaptively Looped Diffusion Language Models). Authors are from UIC, Amazon AGI and Korea University. I found no Amazon blog post on it (amazon.science searches returned nothing on looped models) and no other Amazon looped paper. If Ben meant a different one, send the title and I will chase it.

- Paper: arXiv 2610.04198, "ALoDLM: Adaptively Looped Diffusion Language Models" (Liancheng Fang, Zhuowei Li, Youngeun Kim, Tianchen Zhao, Rajat Koner, Jiaye Wu, Linghan Xu, Xuanbai Chen, Xiang Xu, Zheng Zhang, Jakub Zablocki, Nishant Sankaran, Yifan Xing)
- Code: https://github.com/amazon-science/ALoDLM (portable PyTorch decoder, CUDA-graph inference engine, training + eval code; CC BY-NC 4.0)
- Weights: huggingface.co/amazon/ALoDLM-1.7B and ALoDLM-8B

## What ALoDLM is
A diffusion LM (predicts many tokens in parallel). Claim: diffusion LMs lose to same-size autoregressive (AR) models because they spend the same depth on every unknown token, though some are easy and some hard ("computation-difficulty mismatch").
Fix: token-adaptive latent recurrence.
- Qwen3 backbone split into prelude (first layers), shared recurrent core (middle layers), coda (last layers). 8B: 36 layers, prelude [0,10), core [10,26) = 16 layers, coda [26,36).
- Each pass reads out predictions for unresolved tokens. Confident tokens are committed and fed back as ordinary token embeddings. Unresolved tokens keep their latent state and go round the core again.
- Learned halting gate per token: a shared linear gate on detached readout features, with a learned bias per depth. Max recurrent depth K = 4.
- Gate trained with a latent-variable objective (conditional NELBO) and sequence-level outcome credit, plus a geometric depth prior (c=0.4), KL regularizers (beta_mi=0.1, beta_marg=1.0), weighted supervision at every depth up to the sampled exit, and a next-token auxiliary loss averaged over depths.
- Training: SFT-style on a 5B-token corpus, initialized from Qwen3 1.7B / 8B (not from scratch, no continued pretraining).

## Key numbers (their Table 1, mean of 11 benchmarks)
| Scale | Qwen3 AR | Best other diffusion LM | ALoDLM |
|---|---|---|---|
| 1.7B | 63.8 | 61.0 (SDAR) | 65.5 |
| 8B | 78.5 | 75.1 (WeDLM) | 80.3 |
- Speed: ~2.7x throughput of vLLM Qwen3-8B on GSM8K at similar or better accuracy (one B200, single stream).
- Compute: at 93.25% accuracy, 133.5 GFLOPs/token vs 154.6 for WeDLM (-13.6%).
- Test-time scaling: raising the halt threshold q took average loops/token from 1.6 to 2.34 and average score from 77.9% to 79.1% (+1.2).
- Token adaptivity: number tokens halt later (first-pass halt prob 0.369) than the cross-dataset mean (0.417); word tokens halt earliest (0.428). Model learned "numbers need more thinking" with no difficulty labels.

## Ablations (from the paper)
- Max depth: K=2 plateaus lower; K=4 matches K=8 and trains faster. Fits our own finding that 8 loops did not beat 4.
- Loop placement: looping middle layers [10,26) beats looping the last 16 layers [20,36) at equal core size.
- Intermediate (per-depth) supervision cuts gradient variance of the gate objective 1.76x (step 1k), 1.49x (6.5k), 1.42x (17k).
- Limitation they state: slower time-to-first-token (depth-specific KV caches built at prefill); speed depends on input and is worse on domains thin in training data.

## Closest non-Amazon looped-LM papers seen (affiliation checked or not Amazon; abstract-level only)
- Ouro / "Scaling Latent Reasoning via Looped Language Models" (2510.25741): 1.4B and 2.6B looped models, 7.7T tokens, match dense 4B / 8B.
- A Mechanistic Analysis of Looped Reasoning LMs (2604.11791): each layer in the cycle converges to its own fixed point; the block follows a cyclic trajectory; attention patterns stabilize.
- Dense Supervision Is Not Enough (2606.24898, Sharma and Vu, 44M and 129M models): per-loop CE sees only what the readout exposes; hidden-state norm is hidden by RMSNorm/LayerNorm yet keeps growing through the loop (norms reached the thousands without a fix). Fix: make scale visible to the loss or remove it from the loop. Small-model relevant.
- Improving Test-Time Scaling with Adaptive Looped Transformers / TaH2 (2609.35748): extra loops only on tokens that benefit; accuracy gain per doubling of compute 2.74 vs 1.79 on AIME; kept improving from 2 to 8 loops.
- Allocating Recurrent Compute in Looped LMs (2608.18230, MixerLoop): loop the mixer layers, run the dense FFN once; at 15M params beat full-block looping, at 110M kept 41.5% of the gain at 45.9% less recurrent compute.
- LoopCD (2609.24196): training-free contrast of early-loop vs last-loop logits to fix loop instability.
- Looped Diffusion LMs / LoopMDM (2605.26106): looping early-middle layers, up to 3.3x fewer training FLOPs, up to +8.5 on GSM8K.
- Looped LMs Improve Compositional Tool Calling (2608.18171): accuracy rises with recurrent depth on API-Bank, BFCL, NESTful.

## What looks testable on B2 (facts, not recommendations; Opus decides)
Our thinker is already a 4-loop looped core, so ALoDLM's structure (prelude, shared core, coda, K=4) is what we have. Differences that could be tested cheaply:
1. Per-token (or per-row) halting gate instead of fixed 4 loops. Untested here. Our 8-loop result suggests the gain would come from spending loops unevenly, not from more loops.
2. Per-loop supervision (readout loss at every round, weighted). ALoDLM reports lower gate-gradient variance from it; we have not tried it on B2 as far as the repo notes show.
3. Loop placement: loop only the middle block with a separate prelude/coda, vs looping the whole core.
4. Watch hidden-norm growth across loops (Dense Supervision paper): a cheap diagnostic on existing checkpoints, no training needed.
5. Numbers-need-more-loops: check whether B2 already needs more rounds on arithmetic-planning rows than on others (per-round answer probe).
Caveats: ALoDLM is diffusion, 1.7B+ and initialized from a pretrained Qwen3; B2 is 3.3M from scratch with an exact calculator, so transfer is unproven. Any B2 test must follow the repo rule of 6+ paired seeds with pass marks written first.
