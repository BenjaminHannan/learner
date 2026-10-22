# Outside opinion wanted: a fair, cheap test of "logic practice helps other skills" in a 3M-parameter model

You are reviewing an experiment design for a small research project. Please be blunt. Label every claim you make as SHOWN (follows from the numbers below), SUGGESTED (likely, from literature or reasoning) or UNTESTED (a guess). Ask for one change at a time, each with pass marks fixed in advance and the result that would prove it wrong. End with a plain-language summary for the project owner (a high-school senior), under 120 words.

## The project and the model (facts, from code and result files)

- Goal: a small model that learns skills and critical thinking from few examples. The owner just proposed: "the model should learn logic. It should be incredible at being a logician. I think that would help it with stuff." Our coordinator's verdict was "change it": logic is not a headline goal; run ONE cheap test of whether logic practice helps OTHER skills.
- Test model ("T1SDR"): 3,314,132 trained parameters. Character-level reader (raw printable ASCII, 2 conv blocks), a looped "thinker" (8 control + 9 register tokens, 8 loops), and a "talker" whose answer comes out by one of 3 modes: copy a span of the prompt, emit a word, or generate up to 8 characters. Prompt limit 208 characters.
- Outside calculator tool: in each of up to 7 rounds the thinker picks an op (NOOP, ADD, SUB, MUL, DIV, MOD, MIN, MAX, CMP) and writes two numbers (digit cells or a copied span); the tool returns "op a b = r", which the reader reads back next round. Training rows whose worked steps parse into calculator ops are taught those calls; rows without a program are taught NOOP calls (loss weight 0.1) and the answer only. The call writer can only write an op plus two numbers.
- Project rules that bind the design: everything inside the model is learned (no hand-written logic inside); hand-written code may exist only as an outside tool the model itself chooses to call while deployed; no new teacher model (procedurally generated, program-checked data is allowed); pass marks written before training; at least 6 paired seeds for any "confirmed" claim.
- Training data: a procedurally generated "skills curriculum", 200,000 training rows over 34 trained families (arithmetic, word stories, lists, sequences, tables, ciphers, passages, and some logic-flavoured families: syllogism with nonsense words, e.g. "All yarps are draxs. All tarns are yarps. Vira is a tarn. Is Vira a drax?" -> yes; prop_eval "P is false. R is true. Is this true or false: if P then R?" -> true; rule_apply; kin_chain; order_chain). Original training: 24,000 updates x 256 rows (about 31 passes), AdamW lr 1e-3 cosine to 1e-4.
- Held-out dev splits (200 rows per family x split cell): in_dist, answer (new answer mix), frame (held-out openers/closers), vocab (unseen names/words), variant (sub-task variants and layouts never trained, e.g. a "Question: ... Facts:" layout), family (4 families never trained).
- SHOWN, parent seed 200 exact-match: in_dist 90.3, answer 75.3, frame 88.8, vocab 87.6, variant 36.7, family 1.3. Three trained parents exist (seeds 200, 201, 204).
- SHOWN, on a bigger sibling model (same curriculum, 3M -> 10M growth test): 268 of 270 errors on calculator families were in the variant split (unpractised variants); this is the project's main generalisation weakness.
- Far-transfer "learn test" (a separate harness): start from parent s200, fine-tune 4,000 updates (batch 64, lr 1e-4, all weights) on 12,000 spreadsheet-formula practice rows. Probe F4 = 420 two-piece formulas joined by + or * on 2-4 row grids, e.g. "A: 49 20 65 | B: 78 59 92 ; =SUM(B2:B3)+MAX(B2:B3)" -> 243; probe F5 "far" = 420 joins on 5-6 row grids. SHOWN: parent F4 0.7%, F5 0.0%; after the practice F4 = 15.7% at 2,000 updates and 28.1% at 4,000; F5 = 1.4%. Item-sampling SE on F4 at 28% is about 2.2 points; one identical-config rerun differed by 2.6 points at 4,000 updates (CPU nondeterminism). About 2.7 s per update on a 4-core CPU.
- Compute: CPU only for this test (a 4-core cloud container; maybe an M1 Pro later). Budget: roughly one night, about 15-25 CPU-hours.

## What the literature says (our helpers' summary; numbers from abstracts, not re-checked)

- Logic-to-other transfer exists but is small and only shown at 7B-70B: ALT/FLDx2 (LLaMA-3.1 8B/70B) +4 points on a math/code average; SynLogic matched ablation (32B, math+code with vs without logic) +1 to +2; Enigmata: +0.4 to +1.9 on one base and "no such generalization" on another. No paper tests it below 100M parameters.
- Controls shrink it: Wu, Li & Liang 2022 (T5-small 60M): a non-logic "Set" synthetic task recovers 65% of pretraining benefit vs 67% for the logic-flavoured LIME task. Hu et al. 2025 (Pythia-160M): natural text recovers about two-thirds of a formal-language pre-pretraining gain.
- Shortcut risk: Zhang et al. 2022 (BERT, SimpleLogic): near 100% in-distribution, 57% when the problem generator changes; depth-only splits miss it. ProofWriter: single-shot answers collapse with depth (93/70/27 at depths 3/4/5) while step-by-step proving holds (90/89/88).
- Humans: abstract logic training alone barely moved selection-task reasoning (Cheng, Holyoak, Nisbett & Oliver 1986); transfer tracks shared elements (Thorndike & Woodworth 1901).
- Solver-as-tool (Logic-LM, LINC, SatLM): large gains on logic benchmarks; the translation step (text to formal) is the weak link.

## Draft design "LT-1" (please critique)

Logic practice rows (built, tested): first-order forward chaining over named entities; rule kinds "every P is Q", "no P is Q", "anything P and Q is R", "anything not P is Q", entity-specific "if e is P then e is Q"; facts with negation; query "is e Q?" -> true / false / unknown (open world; no contrapositive). Fresh predicate words per problem (half nonsense, half common adjectives). Label-first sampler with exact label balance per depth, depths 0-3, 1-3 distractors incl. near-miss rules and broken chains for "unknown"; >= 12 templates per rule kind, two-thirds used in training, one-third held out; sentences shuffled; <= 208 chars; a forward-chaining checker verifies every label. A surface-feature classifier (11 features) scores 38% vs a 33% majority on 5,000 training rows. Example: "Neil isn't flokra. Those white are pifmub. If Neil is pifmub, Neil is not happy too. No flokra is stone. Every smart thing is niddax. If it is not flokra, it is white. Claim: Neil is not happy." -> true (3 steps). Rows are trained answer-only (NOOP calls), like the existing syllogism family, because the model cannot write text steps.

Placebo rows: identical contexts, templates and lengths, but a surface lookup question with no chaining: "Is it stated that James is safe?" -> yes/no; "no" atoms are a mix of derivable-but-unstated atoms, same predicate with another entity, and opposite polarity.

Stage 1 "logic course": continue training each parent (s200, s201, s204) for 4,000 updates, batch 64, AdamW lr 1e-4 constant after 100 warmup, same loss. Arms: C = 100% curriculum replay; L = 75% curriculum + 25% logic rows (about 64,000 logic rows seen once); P = 75% curriculum + 25% placebo rows. The 75% curriculum rows are identical across arms (same seed). Plus one A/A run (C with another course seed) on s200.
Stage 2: score every dev split and the logic splits (dev, held-out wording, depths 4-5, a different "rule-first" generator).
Stage 3: run the far learn test (2,000 updates) from each stage-1 checkpoint; read F4 and F5.

Draft marks (screen = 3 pairs; confirm = 6 pairs by adding course seed 2 per parent):
- M0 manipulation check: L's logic dev accuracy >= C's + 20 points, else "the model never learned the logic, test can't tell".
- V (primary): variant-split accuracy over NON-logic families (excluding syllogism, prop_eval, rule_apply, kin_chain, order_chain). PASS: L - C >= +2.0 points AND L - P >= +1.0, both with paired 95% CI above 0 over 6 pairs. PROVED WRONG: L - C <= +0.5, or L - P <= 0. Screen -> confirm only if L - C >= +1.0 mean with 2 of 3 pairs positive.
- J (secondary): F4 at 2,000 learn updates. PASS: L - C >= +4 and L - P >= +2. PROVED WRONG: L - C <= 0.
- H (harm): in_dist non-logic accuracy L - C >= -1.0.
- Reported only: logic held-out wording / deeper / other-generator accuracy; near families; never-trained families.
- Outside logic tool: deferred, because the call writer can only write an op plus two numbers; a tool would need the model to spell out facts and rules (translation), which needs a text writer this model lacks.

## Questions

1. Is this the right single cheap test of the owner's idea at this size? If you would change one thing first, what, and why?
2. Arms: is the placebo fair (too easy? too hard? it also adds new wording variety)? Is C needed if P exists? Should the logic rows instead REPLACE the existing syllogism/prop_eval rows, or be a larger share?
3. Dose and recipe: is 4,000 x 64 at lr 1e-4 with 25% logic enough for a 3M model to learn depth-1-3 chaining? What M0 bar is sensible? Would you train from scratch instead (about 1-3 CPU-days per run, so not 6 seeds)?
4. Bars: given the noise above, are the V and J pass/fail marks sensible? Suggest exact numbers and the statistical rule (paired t over parents? bootstrap over items?).
5. Which non-logic measure is most likely to show real transfer, and which is most likely to show a fake one? Should we add or drop a measure?
6. Is an outside logic tool worth testing now in this model, and if so what is the cheapest design that obeys "the model must call it itself and write its input"?
7. Your prediction: probability that V passes, that J passes, and that L beats C but not P.
8. Plain-language summary for the owner.
