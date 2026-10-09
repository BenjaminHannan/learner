# code-map (Sonnet reader, 2026-10-05)

**Code map of the sandwich model (Premonition)**

Abbreviations:
- **UC** = origin/claude/ultracode-learning-blocker-gh011t, under scripts/cap256_launch/.
- **M** = scripts/ on main. It is byte-identical on UC and ajo58u. Six core files also match pipeline/scripts on origin/claude/real-pipeline-code by hash.
- **RP** = origin/claude/real-pipeline-code, under pipeline/scripts/cap256_launch/. This is the only branch holding train_contextual_input_compare_windows_v1.py, fresh_core_calculator_constructor.py and calculator_runtime*.py. The UC box clones pipeline/ from real-pipeline-checkpoints (ultracode_box.sh).
- **AJO** = origin/claude/project-thread-ajo58u, under reasoner_ptr/.

I built the core, reader, exit and tool on CPU with random weights (no training, no GPU) to confirm counts and shapes. The scripts are `count.py` and `tie.py` in the scratchpad.

## 1) Data flow (main2 path = skills_pretrain_v1.py `--copy-path --gen-fix`, N ≤ 64)

1. **Tokens.** ids = tokenizer(prompt) + EOS, shape [1,N], no BOS. Rows with N > 64 are skipped (UC/skills_pretrain_v1.py:90-97). BOS=1, EOS=7, PAD=0 (english_pilot_common_v1.py:16). The target is the answer tokens + EOS (:94-96), or "steps # answer" with `--steps`.
2. **Frozen LM features.** `lm.model(ids, mask, position_ids).last_hidden_state` gives [1,N,2048]. It is causal, has no BOS, and sits after the final norm (RP/train_contextual_input_compare_windows_v1.py:236-251). skills_pretrain recomputes it every row (:452). The English pilot caches it (english_feature_cache64_v1.py:110-161).
3. **Reader.** HumanInputProjection is LayerNorm(2048) → Linear(2048,32) → GELU → Linear(32,256), times the mask, then unsqueeze, giving [1,1,N,256] (M/sol_translator_grounding_v6.py:42-49; english_pilot_runtime_v1.py:142-150).
4. **Core input.** e = reader output + sinusoidal position code (128 frequencies, sin/cos) + role code. The h state starts at 0. Cap 64 is bound per instance (english_ordered_begin_cap64_v1.py:22-46, 59-76; M/sol_spatial_poc_ordered_v2.py:46-79).
5. **Core loop.** Four rounds of h ← ln_state(Block₂(Block₁(h+e))), same weights each round (M/sol_spatial_attention_core.py:98-100; claude_fewex_net.py:77-81; M/sol_spatial_poc_ordered_train_api_v2.py:9-19). The output is h [1,N,256]. read_latent also computes a halt logit, which is discarded (:102-105).
6. **Exit (StatePrefix).**
   - Each token is standardised over its 256 dims, then scaled and shifted.
   - Three features are appended: [0, pos/(N-1), 1].
   - Linear(259,32) → GELU → Linear(32,2048) gives [1,N,2048].
   - adaptive_avg_pool1d over positions gives [1,8,2048] (M/sol_translator_english_v6.py:15-46). With N < 8, positions are repeated.
7. **Copy-path glue** (skills_pretrain_v1.py:361-387). The LM input is [8 pooled][optional 8 pointer vectors][emb(prompt ids), N rows][optional K "back" vectors], then emb(BOS), then the teacher-forced answer embeddings.
   - The original English pilot fed only the 8 pooled vectors (english_pilot_runtime_v1.py:153-178). The prompt words were added by `--copy-path` (LIVE.md:122).
   - The pointer vectors are softmax(Linear(256,8)(h)) over positions, weighting the prompt embeddings (:349-360).
8. **Generation.**
   - FinalLatent(h, ones, mask, (1,N)) goes to the observer (english_observe_generation48_v1.py:13-73).
   - The decoder then calls `lm.generate(inputs_embeds=[prefix][emb BOS])`, greedy with KV cache, stopping at EOS=7. max_new is 12, or 48 with `--steps` (M/sol_translator_english_v6.py:83-96; skills_pretrain_v1.py:121).
   - AJO run_english.py is a different harness. It uses its own cache-free greedy loop, 12 new tokens (:189-202), and builds features with BOS prepended and sliced off (:134-135).

## 2) Modules, parameters, computation

| Part | Params | What it does |
|---|---|---|
| Frozen LM | about 1.2B | Reads the question once for features, then reads the prefix and prompt words and writes the answer. |
| Reader | 78,112 | Per-token 2048→32→256. This is a 32-dim bottleneck per token. |
| Core, stored | 9,007,790 | See breakdown below. |
| Exit StatePrefix | 76,416 | scale 256 + bias 256 + 259→32 (8,320) + 32→2048 (67,584). |
| Pointer (optional) | 2,056 | Linear(256,8). |
| CalculatorPath tool | 133,123 | Built as the 4th module but unused in this path (see section 6). |

Core breakdown:
- **Blocks:** 2 × 4,470,936 = 8,941,872. Each block has qkv 197,376, out 65,792, two LayerNorms 1,024 and relative bias 144. Its MoE has 8 experts (256→1024→256, 525,568 each) plus a router of 2,056.
- **Attention:** 8 heads, bidirectional, pre-LN. Heads 0-3 see only ±1 positions. Heads 4-7 are global, with relative bias clipped at ±4 (claude_fewex_net.py:28-48).
- **MoE:** top-2 of 8, equal-clone experts, zero-init router (sol_spatial_attention_core.py:19-43).
- **Other core parts:** ln_state 512, tok 32,000, slot 512, head 32,125, ln_out 512, halt 257. The last five come from the old puzzle net (vocab 125, claude_rsn358a_envs.py:39).
- **Halting:** there is no halting in the sandwich. The rounds are fixed at 4 and halt is frozen (english_pilot_runtime_v1.py:71; fresh_core_calculator_constructor.py:33). `reason_latent` (sol_spatial_attention_core.py:107-131) holds a halt rule that is never called.

There are 114 named trainable tensors (RT:25). That is 96 core, 6 reader, 6 exit and 6 tool.

## 3) Training

- **Loss.** `human_loss` (M/sol_translator_grounding_v6.py:84-93).
  - Input is [prefix][BOS][answer shifted].
  - Cross-entropy goes on answer + EOS, as a per-example mean over valid tokens.
  - There is no other term. The MoE balance loss is computed but excluded (train_english_paraphrase_pilot_windows_v1.py:110). `--aux-weight` can add it.
- **Optimiser.**
  - AdamW, lr 1e-3, weight decay 0, betas (0.9, 0.999), eps 1e-8.
  - Gradient clip 1.0, **batch 1**, constant lr (english_pilot_runtime_v1.py:27-28, 105-107; sol_cloud_capability256_v1.py:220-228).
  - Training continues from the parent checkpoint's Adam state.
- **Updates.**
  - Pilot: 2,304 per arm-seed from a 5,120-update parent (TR:36; RT:270).
  - main2: 50,000 skills updates, every 4th row of the 200k curriculum, copy path (LIVE.md:97, 122). The checkpoint counter reads 55,120 (STIFFNESS-TEST-v1.md:9).
  - v4 fit screens: 2,000 fixed rows × 3 passes = 6,000 updates, seeds 1-3 (SCREEN-v4.md:11).
  - Speed was about 500 updates/min (LIVE.md:97).
- **AJO run_english.py** (separate harness, fresh weights each run).
  - 2,000 steps of 16 rows.
  - AdamW lr 1e-3, weight decay 0.1, betas (0.9, 0.95), 200-step warmup then cosine, clip 1.0 (:357-360).
  - Loss is token-mean cross-entropy over the group (:186).
  - Training data is 96 bank rows, plus 8,000 generated rows in later rounds.

## 4) Eval and scoring

- **skills_pretrain `evaluate`** (:100-134):
  - Greedy generation as in section 1.
  - Strip at EOS and decode.
  - Score as hit = norm(text) ∈ {norm(a) for a in row['accepted']}, where norm is lowercase with collapsed whitespace (:39-40).
  - With `--steps`, only the text after the last "#" is scored.
  - Dev files: in_dist, answer, frame, vocab, variant, family. in_dist has 40 rows × 34 families = 1,360 rows. Family is the unseen-skill panel.
- **Diagnostics** (uc_diag_v4.py): `bare` (frozen LM alone), `chan` (optimise free vectors), `direct` (core + class head, no LM), `geom` (lesions), `exitcap`.
- **AJO scoring** (run_english.py:69-71, 260-263): NFC, lowercase, trailing punctuation stripped, exact match against accepted answers. A looser "contains" metric is reported alongside.
- **Lesions.** zero_pool zeroes the 8 pooled vectors. shuffle_pool swaps in the previous question's vectors. family-mean and global-mean replace them with averages (uc_diag_v4.py:244-260).

## 5) What can be reused with no LM

- **Core compute (pure torch).**
  - `Block` + `UpcycledMLP` + the `step` loop (claude_fewex_net.py:28-48, 77-81; sol_spatial_attention_core.py:19-43) have no LM dependency.
  - **Dependency trap:** claude_fewex_net imports claude_rsn358a_envs, which imports claude_blurt1 (puzzle solver). The import exists only for VOCAB=125. Copy the classes instead of importing.
  - OrderedAttentionReasoner also imports sol_spatial_poc_plain at top level (:10).
  - `position_codes` and `ordered_begin` (sol_spatial_poc_ordered_v2.py:46-79) are torch-only.
  - AJO/model_ptr.py:21-66 is a clean standalone copy of Block and UpcycledMLP. It lacks the absolute sinusoid and role codes and has a key mask. run_english.py does not import it. train_ptr.py does.
- **Reader and exit.**
  - HumanInputProjection and StatePrefix.project_training are tiny, torch-only MLPs. They are fixed to the 2048 LM width and to 8 pooled slots, so retarget them.
  - FinalLatent, validate_final and the decoder wrappers are LM-coupled.
- **Loss and data.**
  - `human_loss` needs an HF-style `lm(inputs_embeds=...)`, so rewrite it for a custom talker.
  - The skills curriculum (origin/claude/project-thread-y0sxwe:skills_curriculum) needs no LM. It has 38 families, checked answers, accepted lists, steps, meta and held-out shifts. The 200k seed-1 build is hash-pinned.
- **Hard LM couplings.** All of skills_pretrain_v1.py (global `CP['ids']` side channel, monkeypatched `ad.forward`/`project_training`, `lm.generate`), the English pilot's pinned-hash config machinery, and the feature cache.

## 6) Surprising findings

1. **70% of the core is idle (shown).**
   - Router is zero-init and the experts are equal clones, so every token ties.
   - Backward on a fresh core: the router gradient is exactly 0.0, only 2 experts per block get gradients, and those two get bit-identical gradients.
   - Experts 2-7 hold 6.3M of the 9.0M stored params and never train. The two live ones should stay clones (suggested). `--moe-revive` exists for this (skills_pretrain_v1.py:221-237).
   - Live core is about 2.63M, or about 1.58M distinct if the clones stay identical (suggested).
   - Dead legacy parts: tok/slot/head/ln_out/halt, 65,406 params. The tool's 133k params get no gradient when notebook=None (english_pilot_runtime_v1.py:181-186).
2. **The loop is nearly stateless (shown, main2, job 09).**
   - |e|/|h| = 44.4, and the relative change per round is about 0.6% from round 3 on.
   - 8 rounds give identical LM answers to 4 (160/320 both).
   - The 4-round loop acts like one 2-block pass over e.
3. **The talker sees the question words (shown).**
   - In copy-path, the frozen LM reads the raw prompt embeddings.
   - Without the question words it fails: ptr arm 18.9% vs allptr 82.9% (RESULTS-R7.md).
   - A same-family shuffle of the 8 core vectors leaves in_dist at 74.4% vs 74.6%.
   - The family-mean prefix matches intact (161 vs 160/320). The global mean drops to 124, nearly all of it cipher_map (0/35).
   - So the core output is a per-family mode vector.
4. **Doubled-prompt bug (shown, fixed by `--gen-fix`).**
   - The patched `ad.forward` called the patched `project_training`, so generation saw [pooled][prompt][prompt] while training saw [pooled][prompt].
   - Every pre-v4 copy-path eval ran on the wrong layout: main2 68.5% → 74.6% once fixed (SCREEN-v4.md:5-6).
   - The bug is visible in skills_pretrain_v1.py:380-387.
5. **The zero_pool lesion is confounded.**
   - Pooled prefix vectors have norm about 1,743 each (4,931 over the 8×2048 block). Mean token embedding norm is 0.736.
   - The "0 of 1,360 with the pool zeroed" result (fix-screen-v2) therefore shows an off-distribution input, not that the core carries content.
6. **Information bottlenecks (read from code, partly shown).**
   - Reader: 32 numbers per token. Exit: 32 hidden dims per token, averaged into 8 slots, so each slot lies in one 32-dim affine subspace (8×32 = 256 numbers per question).
   - Slot order inside a slot is lost.
   - Exit capacity (job 10): optimising the 32-wide exit hidden solves 64/64 rows. Optimising h through the frozen exit solves 53/64.
7. **Weak diagnostic arm.** `uc_diag --fresh-core` (:346-350) only calls `reset_parameters`. It leaves br/bc (relative bias, plain Parameters) at main2 values, and it makes the routers live and the experts independent. It is not a pure re-init.
8. **Harness differences.**
   - run_english.py feeds 8 constant notebook slots from tool.role and tool.status (:139-147). The pilot and skills path use notebook=None.
   - run_english.py uses answer tokens with a leading space (:97) and a query cap of 49. skills_pretrain_v1.py uses no leading space and cap 64.
   - run_english.py sets weight decay 0.1 where the pilot uses 0.
9. **Direct-head diagnostic (shown).** Reader + core + class head, no LM in the loss, 6,000 batch-1 updates: 46/320 train-fit, mostly group_induct. Computed-number families stay near 0 (job 03).

Not run: no GPU, no training, no GOLD-PRIVATE or blind panels, no repo edits.
