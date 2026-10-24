# Tricks for more brains per size: ranked for our setup (2026-10-24)

Setup: M1 Pro 32 GB. Boss Qwen3.6-35B-A3B (3B active) + Qwen3.5-4B workers. Goal: small + tricks beats big plain.
Sources: two research sweeps (16 families, ~70 tricks, 105 claims fact-checked: 68 confirmed, 31 overstated, 5 wrong,
1 unverifiable; raw JSON in `/mnt/project-files/research/tricks/sweep{1,2}.json`) plus our own Tricks-1 run
(`RESULTS-tricks1.md`). Labels: **shown** = measured on comparable models; **suggested** = indirect or one source;
**untested** = guess. "Ours" = measured by us.

## Step 0: one fact changes the plan (shown, and ours)
On an M1 Pro the boss is about as fast as a worker at short context: 35B-A3B ~45-50 tok/s vs Qwen3.5-4B ~50-55 tok/s (oMLX
community runs). The project's own mlx-lm test on Ben's Mac (backbone thread, `~/learner-ops/speedbench/RESULTS.md`) gave the
boss 45.4 tok/s alone, 29.9 each at 2 streams, 17.4 at 4 and 9.7 at 8. Its speed comes from reading only ~3B weights per token.
Caveat: the boss is reported to slow far more at long context (~21 tok/s at 32k, unverified). Newer oMLX (v0.7) reports ~2x total
throughput at batch 4 for the 4B (~28 tok/s each); older versions only 1.2x. So:
- "4B + trick" competes with the boss **at equal seconds**, not at equal FLOPs. Vote-of-8 on the 4B costs ~8x the time of one boss answer.
  Kinetics (NeurIPS 2025, dense models on GPUs) suggests that below ~14B (7B for DeepSeek distills) extra test-time tokens buy less than a bigger model (suggested for us).
  Early stopping and batching cut the cost: on our saved votes, stopping at 3 agreeing answers kept the MATH score with ~3.8 samples.
- Workers are worth having for **parallel work and memory headroom**, not for speed. At most ~2 streams hold 30 tok/s each at the same time.
- On tool use the 4B is close to the boss's class on paper: TAU2 79.9 vs 81.2 for Qwen3.5-35B-A3B (vendor numbers, bf16, thinking on,
  32-81k token budgets). At 4-bit one harness saw the 4B drop 75.1 → 61.7, so measure the worker as we will actually run it.

## Tier 1: do now (cheap, evidence strong)
| # | Trick | Evidence | Expected gain for us | Cost |
|---|---|---|---|---|
| 1 | **Always look it up** on fact questions, enforced by the harness (search or local RAG over notes and docs) | Ours on the Mac (RESULTS-mac.md): 4B 12% closed-book → 40% with forced lookup; with the same evidence the 4B beat the LFM2.5 boss on rare facts (48 vs 42, n=100). Ours on GPU: 4B+Wikipedia 36.5% vs plain 35B 27.25% (rare facts 33.5 vs 19.5, whole-word scoring). Qwen3.5-4B PopQA 18% → 51% with search (2607.05752). Whoever decides tends to under-search: ours, the 35B searched only 13% of the time; where it did search it beat the 4B (34.0 vs 22.6, n=53). Caveat: forced search lowered Qwen3.5-4B on false-premise and ambiguous questions (0.644 → 0.538) | +10-30 pts on facts; the biggest "punch above weight" lever, for whichever model uses it | ~50 generated tokens + ~600 tokens of retrieved text to read per search |
| 2 | **Prefix/KV-cache reuse + cache-friendly prompts** (fixed system and tool block first, dynamic content last; fork one prefill for retries and votes) | shown (oMLX, mlx-lm 0.31+, llama.cpp). Hybrid DeltaNet layers make caches fragile: an edit earlier in the context re-prefills from the last saved checkpoint | Time to first token for each agent step drops from ~10-14 s to ~1 s at 3-4k context (figures from older oMLX versions) | Engineering only |
| 3 | **Capped thinking** (~2k tokens, then force `</think>` + answer), only for maths and multi-step steps; off for facts and tool calls | shown: uncapped Qwen3-4B thinking beats non-thinking Qwen3-30B-A3B (MATH-500 97.0 vs 89.8). A hard cap at half the length keeps ~47% of the MATH-500 gain (25% on AIME); a soft budget keeps ~72%. Thinking adds no facts and raises tool hallucination | +5-10 pts on maths/multi-step | ~40 s per question at 50 tok/s |
| 4 | **Optimized skill documents / prompts** (SkillOpt, GEPA) with Claude as the optimizer | suggested (one unreplicated preprint on our exact pair, SkillOpt 2605.23904): 4B+skill beat plain 35B-A3B on ALFWorld 81.3 vs 59.7, LiveMath 52.0 vs 31.2, DocVQA 89.0 vs 87.6; lost on 3 others. GEPA +9.6 avg on Qwen3-8B (self-reflecting). What fails is OPRO/TextGrad-style self-proposal; a model reflecting on its own runs kept 56-74% of the gain | +5-15 pts on procedures and multi-step tool tasks | API credit; zero runtime cost |
| 5 | **Calibrated quants, and check the worker's bit width** (DWQ/AWQ, imatrix); no 3-bit for the 4B; fp16 not bf16 on M1 | shown for the boss: DWQ ~2.8x lower KL than plain 4-bit at the same size. Suggested for the worker: one harness saw Tau2 drop ~13 pts at Q4 vs bf16, so test Q4 vs Q6 (Q6 ~22% slower). fp16 prefill 30-60% faster on M1 (one model card) | Free for the boss; up to ~10 pts on tool tasks for the worker if Q6 is needed | Download + one eval |
| 6 | **Don't build**: self-critique without an outside check, multi-agent debate, mixtures of small models, LIMO/s1 SFT at 4B, naive looping, latent reasoning, small/big token-level collaboration | shown: self-correction without feedback loses (Llama-2 GSM8K 62→36.5); debate loses to a plain vote at 7-8B; LIMO-style SFT costs 3-4B models 14-25 MATH pts; small/big collaboration has no point when the boss is as fast as the worker | Saves weeks | none |

## Tier 2: worth building next (some training or plumbing)
| # | Trick | Evidence | Expected gain | Cost |
|---|---|---|---|---|
| 7 | **Narrow skill LoRA / RL on our own tools** (one adapter per request, never mixed) | shown in-domain (TinyAgent, APIGen-MT). Qwen3.5-4B is already strong on generic tool use (TAU2 79.9) | +5-20 pts on our tool flows | Hours on one GPU |
| 8 | **On-policy distillation from the boss** (same 248k vocab, token-level) | shown generally; gap to close: BFCL-V4 50.3→67.3, IFBench 59.2→70.2 | Some of that gap | One GPU-day |
| 9 | **Know when unsure from logits or probes, not from what the model says** | shown: stated confidence is ~chance at ≤4B (AUROC 0.47-0.55 on a MacBook test); P(Yes) and mid-layer probes reach ~0.75-0.85 | Better search/escalate/abstain gates | Small |
| 10 | **Vote-of-k with early stop; use disagreement as the "unsure" flag** | Ours: 4B vote-of-8 87.7 vs 35B 86.7 on MATH (8x tokens); 4B pass@8 95%. On the Mac, 8 answers in one batch took 6.4x one answer (mlx-lm, no shared prefill): over our 6x bar, so plain voting is out for interactive use | +2-6 pts maths; feeds escalation | k× time; prefer the boss at equal seconds |
| 11 | **Short, fresh worker contexts**; mask old tool outputs (in batches, since each edit breaks the hybrid model's cache, #2); memory as retrieval | shown (ACON, LongMemEval, context rot). Long memory is tested by the "untouched areas" thread | +5-20 pts on long sessions, 40-50% fewer prompt tokens | Engineering |
| 12 | **Tool-call hygiene**: native Qwen XML format, lazy grammar only after `<tool_call>`, "ask the user" instead of guessing a missing argument | suggested: grammar from the first token cost 10-40 pts on Qwen2.5-1.5B/3B (one paper), while Qwen3-4B was ~100% valid either way; "ask the user" bypass +3-13 pts on turns with missing info (one paper) | Reliability over 10-step chains | Small |
| 13 | **Speculative decoding** (DFlash drafter, native MTP heads) | suggested on M1 Pro: 1.3-1.8x for the 4B. The M1 Pro is compute-poor, so gains are smaller than on M4/M5 | Faster workers, which pays for thinking time | Library support |
| 14 | **Free RAM on the boss**: REAP 20-25% expert pruning or tensor-aware 3-4 bit (~3-4.5 GB saved) | shown: RAM only, speed unchanged. Boss peaks at 19.3-20 GB on MLX 4-bit; the Q4_K_M GGUF file is 22.1 GB | Room for one more resident worker | Calibrate on our traffic |
| 15 | **Sleep-time compute + plan caching**: think ahead while the Mac is idle; the boss writes plan templates that workers reuse | suggested | Faster repeat tasks; ~half the boss calls avoided | Overlaps the sleep thread |
| 16 | **Worker bake-off**: MiniCPM5-2B (1.75x fewer bytes per token) vs Qwen3.5-4B on our tasks | suggested, vendor numbers | ~1.75x faster worker if quality holds | One eval |
| 17 | **Serve all workers as one batched model** (one weight read per step for all streams) | suggested: decides what voting and parallel work cost; oMLX v0.7 ~2x total at batch 4 | Several workers for ~the price of one | Server choice |
| 18 | **Run independent tool calls in parallel** (LLMCompiler-style) | shown: 20-50% less wall-clock on multi-tool tasks | Faster multi-tool tasks | Engineering |
| 19 | **Cache-reusing checker/router heads** (activated LoRA) | suggested | Makes #9 and #10 checks take under a second | Small training |
| 20 | **RL-trained 4B search agents for overnight research jobs** | shown: LiteResearcher-4B 71.3 on GAIA vs Tongyi-DeepResearch-30B 70.9 | Long background research | Minutes per question; not interactive |

## Tier 3: skip for now
Test-time training per query (TTRL, qTTT, SEAL: ~0 at 4B, blocks the GPU), hypernetwork LoRAs (none exist for Qwen3.5),
Engram / MoE upcycling (needs pretraining), retrofitted recurrence (0-1.5 pts and slower decode), KV eviction (hurts
multi-turn), swapping to a function-calling fine-tune (could cost 30-40 pts on tau2 retail, though xLAM-2-8b wins on airline), a code tool for maths (ours: +1 pt).
Exception worth a later test: TTT on the user's worked examples for repeated batch jobs (+7 pts at 8B on BBH).

## Next cheap tests (free hardware first; revised after review)
0. **DONE (4B): Mac timing**: n=1 vs batched n=8 for both models at 1k and 8k context. Voting is out if batched n=8 takes > 6x n=1. Without this, "equal seconds" is a guess.
1. **PARTLY DONE (LFM2.5 boss, 100/400 rows): boss worse by 6 pts, keep lookups on the 4B. Boss with forced lookup** vs 4B with lookup on PopQA (fixed scorer; final round forces an answer). If boss+lookup ≥ 4B+lookup + 5 (paired CI > 0): send fact questions to the boss with lookup. If ≤ +1: the 4B with lookup is an equal and frees the boss.
2. **Capped thinking (s_think2k)** with Qwen3.5 thinking sampling (presence penalty checked on a 50-item slice first). Pass: ≥ s_plain + 5 on MATH and ≥ b_plain + 2 within 2.5x b_plain's Mac seconds. Out if < +2 over s_plain.
3. **Claude-optimized skill sheet** for the 4B + Python on 100 held-out GSM-Hard rows, then our own tool tasks; same sheet on the boss. Pass: ≥ +5, paired CI > 0; out if < +2.
4. **Checker over the 8 saved tries** (vote 87.7, pass@8 95). Pass: ≥ max(vote, b_plain) + 3, CI > 0; out if ≤ vote + 1.
5. **Search only when unsure**, on a mixed set (PopQA leaves only +2 room). Worth building only if ≥ 30% of solvable questions succeed without search and forced search turns ≥ 5% of right answers wrong.
