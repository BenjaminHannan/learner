# Code map: Premonition reader (hearer) and talker (exit), for replacing the frozen LFM2.5-1.2B

Read-only investigation. Abbreviations: AJO = origin/claude/project-thread-ajo58u (PR #30, allptr, English task);
U9U = origin/claude/project-thread-u9uvmq (PR #33 "real model" arithmetic recipe, pipeline/recipe_test/);
6QS = origin/claude/project-thread-6qsyg1 (scaling_test/); LR = origin/claude/premonition-launch-recovery-96c708.
Nothing here touched GOLD-PRIVATE or blind panels. Items marked (mem) are from my memory of LFM2, not stated in the repo.

IMPORTANT TWO-RECIPE NOTE. There are two "real pipeline" runners, same reader/core/exit modules, different tasks:
 (A) AJO reasoner_ptr/real/english/run_english.py: English passage QA, multi-token answers, exit = allptr (pool + pointer + all words).
 (B) U9U pipeline/recipe_test/run_arm.py (PR #33): two-number add/subtract word problems (one- and two-step), 4 calculator-call loops, answer = ONE token from a mechanical calculator copied into the prefix. This has the contextual reader (--ctx), input cap 160 (--long), two-step chains, distractor practice (--dist).
Newest English recipe = AJO round 6 (run_english.py, --gen 8000 --kinds 12 --block-r6). Newest arithmetic recipe = U9U round 8 (--task two --frames rlv --ctx --copy --long --dist). 6QS scaling_test/run_english.py is a fork of (A) with --layers/--experts.

## 1. Data flow (recipe A, allptr)
Tokenizer: the LFM2.5 tokenizer itself, `AutoTokenizer.from_pretrained("LiquidAI/LFM2.5-1.2B-Instruct", revision 0f604ada...)` (AJO run_english.py:33-34,53-54). Prompt = passage + " " + question, no special tokens, + EOS; hard assert <=49 tokens incl EOS (run_english.py:83-88). Answer = tok.encode(" "+answer) + EOS (:91-92). Prompt lengths are bucketed so each batch is equal-length (:151-155).
LM load: fp32, `.eval().requires_grad_(False)`, TF32 on (run_english.py:55-57). Fully frozen; no LoRA.

make_prefix (run_english.py:123-148), per question:
 1. LM forward #1, no grad: `lm(input_ids=[BOS]+ids, output_hidden_states=True).hidden_states[-1][:,1:]` = the LM's LAST-layer states, one 2048-d vector per prompt token (e0). This is the "contextual reader" input (:128). All LM layers are run; no truncation, no cache. (hidden size = lm.config.hidden_size, :58; 2048 (mem).)
 2. Reader = HumanInputProjection(LMW) (AJO scripts/sol_translator_grounding.py:42-49): per-token LayerNorm(2048) -> Linear(2048,32) -> GELU -> Linear(32,256). No attention, no mixing across tokens; the context comes entirely from the LM. Output query [B,1,n,256].
 3. Core = OrderedAttentionReasoner(base.Net("loop"), experts=8, active=2) (:103-109): 256-wide, 2 distinct shared blocks (ARMS["loop"] d=256, layers=2, heads=8, scripts/claude_fewex_net.py:22), run as 4 loops; 8-expert top-2 MoE MLP; 9,007,790 params (asserted :108). Call: begin_latent(query, memo[8 notebook slots = role / PENDING+role], query_mask) then 4x advance_latent (:136-139). Output h = state["h"][:, :n], [B,n,256]. No tool/calculator calls in recipe A; CalculatorPath only supplies role/status vectors for the 8 notebook slots.
 4. Exit adapter StatePrefix(256, 2048, hidden=32, 8) (AJO scripts/sol_translator_english_v6.py:15-46): LayerNorm-ish normalise h, concat 2 geometry dims + slot flag, Linear(259,32)-GELU-Linear(32,2048), then adaptive_avg_pool1d over the n token positions -> 8 prefix vectors [B,8,2048].
 5. allptr extras (:145-147): ptr = Linear(256,8) on h, softmax over prompt positions -> 8 weights; 8 pointer vectors = weighted sum of the LM's INPUT embeddings (layer 0, `emb(ids)`) of the prompt tokens; plus ALL n prompt-token input embeddings. Final prefix = [8 pooled ‖ 8 pointer ‖ n word embeddings] = up to 8+8+49 = 65 vectors, placed BEFORE BOS (:148, :167).
 Talker: the SAME frozen LM, forward #2 (with grad flowing through the frozen layers to the prefix): input = [prefix ‖ emb(BOS) ‖ emb(answer tokens shifted)], logits = the LM's own tied LM head over the full ~65k vocab; teacher-forced CE on answer tokens + EOS (loss_on :158-169). So the talker = frozen full LM decoding from a soft prefix; "copying" is done by the frozen LM attending to the raw word embeddings in the prefix, not by an explicit pointer/copy head over a small vocab.
 Test decode (:172-185): greedy, up to --max-new 12 steps, NO KV cache (re-runs the whole prefix+BOS+generated each step), stop at EOS. Answers ~4.2 tokens incl EOS (LIVE.md in AJO-lineage branches, line "answers ~4.2 tokens incl. EOS").
 Why the LM runs twice: pass 1 = frozen reader features (no grad, input_ids only, last hidden layer); pass 2 = frozen talker (inputs_embeds from the learned prefix, needs grad through layers). Different inputs, cannot be shared. Per training item: 2 LM forwards + 1 LM backward (backward only for pass 2); per eval answer: 1 + (<=12) LM forwards.

Recipe B (PR #33) differences (U9U pipeline/recipe_test/run_arm.py):
 - Reader identical but input is `emb(ids)` (context-free) unless --ctx, which switches to hidden_states[-1] (:133-137). --ctx is the round-2 "contextual reader".
 - Core is run by `calc_forward` (:127-208): begin_latent once, then 4 loops, each loop: tool.action head on mean of token features (or --ordered per-loop learned query) picks ADD/SUB/NONE, left/right pointer heads pick two number literals (registry from build_registry, calculator_tools), the mechanical calculator computes, result token embedded via the reader and written into notebook slot n+2L; then advance_latent.
 - Exit: StatePrefix -> 8 prefix vectors, plus (--copy) a 9th vector = LM input embedding of the latest OK calculator result (:219-224). Answer = ONE token (two-digit numbers are single tokens in this tokenizer, asserted :72) + EOS; logits = frozen LM head at position after BOS (:226-229). Loss = final CE + action CE + pointer CE (:233-274, 406).
 - Input cap: core refuses >49 tokens (ordered_begin QUERY_CAP; round-3 note in RESULTS-3.md). --long sets `sol_spatial_poc_ordered_v2.QUERY_CAP = 160` (run_arm.py:366-368), a guard only (RESULTS-7.md).

## 2. Trainable parameters vs frozen LM
Frozen LM: 1,170,340,608 params (6QS scaling_test/PASS-MARKS-SCALE.md, "frozen LM 1,170,340,608"). Embedding table (tied head) ~65536x2048 = 134M (mem); 16 layers (mem).
Trainable (my arithmetic from the code; measured total in the result json):
 - allptr total `params` = 9,297,240 (AJO results/box54092912/out/allptr-seed0.json; same in gen runs).
 - core 9,007,790 (halt frozen: 257 -> 9,007,533 trainable; but "64 of 114 tensors get no gradient", incl. tok/slot/head/ln_out and MoE experts 2-7, per LIVE.md 17:50Z entry; so effective <9.0M)
 - reader 78,112 (4,096 LN + 65,568 + 8,448)
 - StatePrefix 76,480 (512 scale/bias + 8,320 + 67,584)
 - ptr head 2,056 (allptr only)
 - CalculatorPath remainder ~133k (by subtraction; unused heads get no gradient in recipe A)
 => ~0.8% of the LM. Reader+exit adapters together are only ~157k; the core is ~97% of trainable params.
LFM layers actually consumed: ALL of them. Reader uses the last layer's output (hidden_states[-1]); talker runs the entire LM (all layers + head) over the prefix. Input embeddings (layer 0 table) are used for pointer values, word-copy block, answer/BOS tokens. No intermediate layer is tapped anywhere in these runners.

## 3. Tasks
Recipe A (English QA, AJO). Six families (giver/recipient, negation, comparison, two relations, which-one/descriptive reference, event order), made-up names, 1-2 short facts per passage + question; answers are a yes/no or a short phrase copied (sometimes with a preposition tweak) from the passage. Generated examples from AJO gen_english.py (run offline, seed 1000):
  - "On Wednesday, Vak gave Nolo the blue card." Q "Did Nolo give the blue card to Vak?" -> "No"; Q "To whom did Vak give the blue card?" -> "Nolo"
  - "For the trip, Ras bought the metal camera, not the old ball." Q "What did Ras buy?" -> "metal camera"; Q "Did Ras buy the old ball?" -> "No"
  - "Two pink binders sat on the dresser: the handled one was left of the handleless one. Livi moved the left one to the cart." Q "Which binder did Livi move?" -> "handled binder"; Q "Where did Livi move the binder?" -> "to the cart"
  Answers: 1-4 word tokens + EOS (avg ~4.2 incl EOS). Prompt <=48 tokens + EOS. Each example is asked of source_text and a paraphrase. Round 5-6 add unseen kinds (time, cause, counting, tool, attribute, location, speech, weather, price, direction, duration, origin) in NEW-KINDS-R5/NEW-KINDS2-R6 (test files, not read).
Recipe B (arithmetic, U9U gen.py/gen_two_r3.py; sampled by me from `gen.stream_b` and `g3.stream`):
  - "Hana had 29 shells. Hana gave away 13 of them. How many shells does Hana have now?" -> 16
  - "Pablo placed 58 balloons on the top shelf and 33 balloons on the lower shelf. How many balloons did Pablo place altogether?" -> 91
  - two-step: "Dev had 96 toy cars to begin with. 64 were lost by Dev. Following that, Dev earned 11 more. Give the total of toy cars Dev has at the end." -> 43
  Answer = a two-digit number = ONE LM token (+EOS); the held-out split reserves 30 of 90 answer values never seen in training (the "unseen answer" test, gen.py:1-8). Layout families: narrative, question-first, table, distance, chat, receipt, ledger etc.

## 4. Measured results
Exit ablation (arithmetic/story task, 6 paired seeds, AJO reasoner_ptr/real/RESULTS-R2.md; this is run_story.py, one-word answers):
  unseen answers: pool (8 pooled vectors only, "today's exit") 0.0% | ptr (pool + 8 pointer vectors) 56.7% | emb (pool + all prompt word embeddings) 87.2%. Seen answers 16.8 / 57.9 / 89.6. All 1152/1152 wrong answers of pool were training answers (closed-set signature). Zeroing the 8 pooled vectors at test: ptr 2.4%, emb 0.0%. (So 0/57/87 = pool/ptr/all-words; "core-state-only" = pool.)
Recipe A English (AJO english/RESULTS-R3..R6.md, fresh set 192 Qs, exact match):
  R3 bank only (96 rows): pool 4.3% | allptr 34.7% (seeds 21-68%) | bare LM alone zero-shot 29.7% exact / 76.0% contains.
  R4 allptr + 8000 generated: 92.6% (seeds 89-96); bare LM 8-shot 75.0% (CI of gain +14.7..+20.6). Zero pool lesion: 0%.
  R5 new kinds: 79.9% vs bare 8-shot 67.7%; leave-one-family-out 80.2 vs 76.6 (not shown better).
  R6 12 kinds: 83.0% vs 67.7% on R5 set but only 78.2% vs 77.6% on second unseen set (a tie with bare LM); speech 40.6%. 
Reader variants (arithmetic, U9U): 
  RESULTS-2.md contextual reader (--ctx) vs lexical: new-wording right-call 59.2 -> 91.0 (+31.8); all-question final 72.5 -> 95.5 (single-step; these are the "72.5 -> 95.5" numbers); train fit 96->100.
  RESULTS-3.md ordered read (--ordered, per-loop learned query) HURTS on two-step: chain 54.9 -> 43.1 (-11.8); helps only "distance" layout (+17).
  RESULTS-4: composed wording training: chain 54.9 -> 81.4. RESULTS-5/6: blind layouts by another Claude worker 73.4% / 62.5%.
  RESULTS-7: cap lifted to 160, long (55-150 tok) chain 66.6%, no drop on short sets.
  RESULTS-8: irrelevant numbers inside long text drop chain 62.4 -> 16.3; distractor practice restores 50.2 (partial).
  RESULTS.md copy path (calculator result as prefix vector): unseen answers 0.3 -> 68.1.
Skills-pretraining line (LR/aya9pk docs/premonition-status/LIVE.md): with the 8-vector exit alone copying a made-up word 0/40; with prompt token embeddings in prefix 40/40; full curriculum with copy path plateaus at 72% in-dist.
Scaling test of the CORE (6QS scaling_test/PASS-MARKS-SCALE.md): layers 2/4/8 (9.0M/17.9M/35.8M), 6 boxes rented at 1229f8ef3; no result file found on the branch yet (ledger says run in progress).

## 5. Smaller/no LM, from-scratch, truncation, caching
 - Smaller or absent LM in these runners: NONE. `--lm` is a path/name arg (run_english.py:33,53) so a swap needs the width (LMW) to match; reader/exit hard-code the LM width through LMW only, so another HF causal LM with tied/embedding table would load, but pointer/word-copy depends on the LM's input embedding space.
 - Layer truncation: none (nothing slices lm.model.layers; hidden_states[-1] only).
 - Caching: LR/AJO scripts/cap256_launch/english_feature_cache64_v1.py = a cache of the frozen last-layer features (final-layer LFM2 last_hidden_state, detached FP32, <=64 tokens incl EOS, keyed by token ids) for the PC English pilot. Not used by run_english.py/run_arm.py, which recompute pass 1 each step (no grad). Pass 2 cannot be cached (needs the learned prefix).
 - From-scratch talker: DESIGN ONLY: AJO design/v3/24-talker-from-scratch-fable-design.md (+24b Ben "choose your recommendations"): 6-layer w384 encoder + decoder, ~33M params, 416-d typed thought, ~1.2B tokens SimpleStories/TinyStories reading list, BensPC ~9-10 GPU-h. Related prep docs design/v3/30-modes/101/120*, design/v3/40-talker/41-talker-recipe-gpt-xhigh.md. I found no results from it. Also design/05-village-v0.md and design/v3/02-track-b-mini-village.md (not read).
 - Tiny LMs (hidden 16-32, 1-2 layers) exist only as side classifiers in scripts/claude_bm397t_train.py etc. (LlamaConfig vocab 64), not as the reader/talker.
 - Speed probe (LR docs/premonition-status/LIVE.md 18:43Z, bench_tps): M1 Pro MPS system (reader+core+exit, 1 answer token) 5.6 q/s at batch 1, ~20 q/s at batch 16-32 on short prompts; bare LFM decode 25 tok/s fp32 batch 1.

## 6. Cost of a run
Recipe A: 2000 updates x batch 16 = 32,000 row presentations (bank 96 rows + 8000 gen examples x 2 panels x 2 Qs ~ 32k rows, about 1 epoch). One run measured: 2643 s (bank only, RTX 3090, AJO allptr-seed0.json), 2292 s (with --gen 8000, RTX 3090, 4% fewer buckets). Whole 6-seed round on rented RTX 3090s: ~$0.9-1.1 (about 45-90 min wall per box incl. setup, LEDGER.md in AJO english/), ~$0.10-0.28 per box. Round 4 ran allptr + lm_fewshot on the seed-0 box.
Recipe B: 3000 updates x 16 = 48,000 rows (stream sized steps*batch*1.25, non-repeating). ~23 min per run on a 3090, ~6.5 min on an RTX 5090 ("2 runs in ~13 min", RESULTS-4.md); rounds cost ~$0.6-1.35 per 12-24 runs (U9U LEDGER.md). Some 5090 boxes were ~20x slow (rounds 7-8), replaced.
Scaling test smoke: 4 sizes x 30 updates in 93 s on a 5090; forecast 1.5-2 h per box for 3 sizes at 2000 updates.
Cheap-test implications (suggested, untested): the frozen LM is run on every step, twice, with ~65-token prefix; anything that removes pass 1 (reader) or shortens pass 2 saves most of the per-step cost; the core is tiny. Eval decode has no KV cache, so swapping a smaller talker also speeds eval.

## Caveats
Branch names in the brief map: PR #30 = AJO; "PR #33 real model fixes" = pipeline/recipe_test on U9U/upbeil lineage (commit 34608a1 is round 3 of it). I did not run any code except offline data generators (stubbed tokenizer) in the scratchpad. Param counts for reader/adapter are my arithmetic. LFM layer count/hidden size are from memory.
