# Haiku digest: does logic training transfer? (verify numbers before quoting)
1 FLD 2023 (2308.07336): T5-base; only logic evals; EntailmentBank T1 36.8->39.3; no placebo.
2 ALT/FLDx2 2024 (2411.12498): LLaMA-3.1 8B/70B, 100k samples; 70B HumanEval +10.3, MathQA +7.6, MATH +5.2, GSM8K +2.4; avg 8B +4.1, 70B +4.4; w/o Recall Adam ALT < base. Other logic corpora on 8B avg: FLD +4.0, RuleTaker +2.2, PARARULE-Plus +0.2. No non-logic placebo.
3 Logic-RL 2025 (2502.14768): Qwen2.5-7B, <5k K&K, relative AIME +125% AMC +38%; no math control.
4 SynLogic 2025 (2505.19641): Qwen 7B/32B; 32B Math+Code with vs without logic: AIME24 +1.3, LCB +1.2, GPQA-D +2.3; logic+math ~= math-only on average. 7B MATH500 below instruct.
5 Enigmata 2025 (2505.19914): matched ablation +0.4..+1.9 on Seed1.5; "no such generalization for Qwen2.5-32B"; excess puzzle data -> forgetting.
6 Reasoning Gym (2505.24760): 3B, math tasks, no compute-matched arm.
7 LIME 2021 (2101.06223): synthetic deduction/induction/abduction -> formal math LeanStep +14, IsarStep +6.5; no non-logic synthetic arm.
8 Wu/Li/Liang 2022 NeurIPS (Insights via simpler synthetic tasks): T5-small 60M; share of natural pretraining benefit: LIME 67%, Set 65%, Dyck 49%, Identity 46%, param-stats 39%. -> non-logic Set task gets almost all of LIME's benefit.
9 Papadimitriou&Jurafsky 2023 (2304.13060): GPT2-small formal-language pretraining -> LM perplexity only; random-token control.
10 Hu et al 2025 ACL (2502.19249): Pythia-160M Dyck pre-pretraining: LM loss 3.780->3.741; BLiMP +0.009; C4 control gets ~2/3 of gain; random strings worse than none.
ReSyn 2026 (2602.20117): Qwen7B puzzles GSM8K 82.3->91.4, no control.
VERDICT: transfer exists but small (+1..+4 broad, at 7B-70B); best controls shrink it (Set 65% of LIME; C4 2/3 of Dyck; SynLogic matched +1..+2); NO paper tests logic->other transfer below 100M. Need placebo matched on format/length/vocab, matched steps, fixed benchmarks, 3+ seeds.
