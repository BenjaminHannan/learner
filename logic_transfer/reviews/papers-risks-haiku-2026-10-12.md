# Haiku digest: risks/limits (numbers from ar5iv/abstracts; verify before quoting)
1 Zhang 2022 SimpleLogic BERT: RP-trained depth0-6: 99.9->95.5 on RP, 99.8->57.3 on LP; LP-trained on RP 97.3->69.2; shortcut = number of rules. Break came from changing generator (not depth).
2 RuleTaker D<=3: 99.3 in-dist, 97.6 depth 5; D<=2 model 71.1 at depth 3. ProofWriter T5-11B single-shot trained d3: 93.4/69.9/27.4 at d3/4/5; iterative 90.4/88.9/87.8.
3 PrOntoQA: 5-hop steps 93.2% valid; failure = wrong branch choice. OOD: longer proofs hard; distractors mostly harmless; no disjunction-elim / contradiction w/o demos.
4 Faith and Fate: fine-tuned high in-domain, sharp OOD decline; linearised subgraph matching.
5 Humans: Thorndike&Woodworth 1901 small transfer except identical elements; Cheng/Holyoak/Nisbett/Oliver 1986: abstract logic rules alone little effect on Wason; gains with worked problems; Lehman/Lempert/Nisbett 1988: psych/med training improved statistical reasoning; chemistry nothing.
6 Tools: Logic-LM GPT-4 ProofWriter 52.7->79.7, FOLIO 69.1->78.9, LogicalDeduction 71.3->87.6; PrOntoQA CoT 98.8 > Logic-LM 83.2. LINC: FOLIO GPT-4 CoT 75.3 vs 72.5 n.s.; translation syntax errors 38%/24%/13%. SatLM: LSAT 35.0 vs 23.5. Translation = weak link; score formalisation separately.
Design rules: hold out depth + proof shape; hold out wording + generator stats; placebo + no-training control; surface-feature shortcut baseline; marks + falsifier before training (near/mid/far); score formalisation separately.
