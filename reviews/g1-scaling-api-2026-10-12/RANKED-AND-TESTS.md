# Why G1 didn't scale, besides width: ranked causes and proposed tests (12 Oct 2026, ~11:15 AM ET)

Thread "Why G1 didn't scale: Fable and Opus". Ben asked (9:30 AM ET 10-12) for Fable 5.1 and Opus 5.5 ideas on why G1 didn't
scale other than width. Brief: `g1-other-causes-brief-2026-10-12.md`; answers: `g1-other-causes-fable-answer-2026-10-12.md`,
`g1-other-causes-opus-answer-2026-10-12.md` (this folder; also branch claude/project-thread-s3y3gg, PR #71). Normal API, effort
xhigh, $3.38. Every claim below was checked against the G1 code (612f5c5b01 + caps overlay) or the 3M s400/s401 RESULT/stdout
files on branch claude/8a-g-pc-results (d17716d8ea), by Haiku checkers; nothing here has been trained.

## 1. What changes how G1 reads (SHOWN, checked)

- **86% of the -3.71 gap is plain learning arithmetic that ours already has.** Family sizes (120/160/200) sum to 6,040. In the 13
  families whose gold answers are >= 99% calculator-reachable (2,440 rows), ours had 270 errors at 3M and fixed **-1** at 10M; plain
  had 572 and fixed **+191**. Other 21 families: ours fixed 100 of 1,360 errors (7.4%), plain 132 of 1,414 (9.3%). Recomputed here
  from RESULT.json by_family (Opus's table holds exactly).
- **Ours' 13-family errors at 3M are 268 of 270 in the variant file** (new templates). In in_dist/answer/frame/vocab ours makes
  0-2 errors there; plain makes 278. So plain's +191 is mostly catch-up outside variant. Variant holds ~51% of ours' misses
  (836/1,630); ours fixes ~2.6% of its variant errors per rung, plain ~6.5% (Opus).
- Error ratio err(10M)/err(3M): ours 0.939, plain 0.837. WIDE's pass bar (76.31) equals ratio 0.878.
- One seed: ours' +1.64 is ~1.2-1.4 sd from zero; the gap has the same sign as the old ladder (6 seeds), so probably real.

## 2. Ranked causes (other than width and the parallel GEN writer)

| # | cause | label | source |
|---|---|---|---|
| 1 | **Yardstick**: "difference of gains" mostly counts plain catching up on arithmetic (section 1). Not a model fault; changes what to track. | shown | both |
| 2 | **Template generalisation, not capacity**: ours' training rows are ~solved (op/operand loss 0; 3M skills-only run fit train 3x better at 10M with dev flat), so extra blocks get almost no gradient from where dev errors are (new templates). | shown (pattern) / suggested (mechanism) | both |
| 3 | **Calculator only by imitation**: rows with no hand-parsed program are trained to NOOP every round (weight 0.1; ledger.py:322, 495). table_lookup, seq_next, fewshot_number_rule and rule_apply have **0% program coverage but mostly numeric answers** (e.g. "desert plus anchor?" = 81; "39, 46, 53, 60 -> ?" = 67; skills.jsonl). Ours must spell those numbers with the parallel GEN writer and is taught to leave the calculator idle. These four families = 501 of ours' 1,630 misses at 3M (30.4% right, both seeds); ours scores about the WORD share of table_lookup (27.5 vs 31%). Size can't help a path the model is trained not to use. | shown (labels, coverage, answers) / suggested (effect) | Opus #7, checked here |
| 4 | **Web fill-in rows own the gradient**: 42.8% of rows (62% of pieces) are one-word blanks; for ours they are GEN (72%) or WORD (28% "copyable") rows; GEN ~70% of ours' loss and flat after 12k updates. Spare capacity goes to an unscored task at a floor. Weakened: the old skills-only look (no web rows) also gained little, but that model had the 9-register bug. | suggested | Fable C1, Opus #5 |
| 5 | **Shallow fixed keys**: slot keys are a linear map of mean reader output over the digits; word keys pool the same 2-conv reader. Depth improves queries only. Partly weakened: the frozen encoder's contextual per-character state is added before the conv blocks (eg.py:62,95; reader.py:74), so context is present, but only through a fixed linear map. | suggested | Opus #1 |
| 6 | **Mode routing / one-word pointer**: mode CE ~0.21 (late block mean). Labels are a fixed priority NUM > WORD > GEN from the answer string (progparse.py:196-209), not arbitrary; on web rows the WORD/GEN label depends on whether the blank's word appears elsewhere, a guess. WORD copies one token; no multi-word answers in the weak families. | suggested | Fable C3, Opus #6 |
| 7 | **Optimiser for 288 residual additions** (lr 1e-3 at both sizes, 300 warmup). Untested; no grad norms logged. | untested | both |
| - | Ruled out or weak: accumulation/clipping (micro-batch losses are **averaged**, train.py:191, so Opus's "clip fires 4x more" premise is false); 12 rounds/halting/teacher forcing (loops:24 = loops:12; free-run = forced); frozen encoder (old ladder flat without it); update budget (both sizes saw ~260M pieces; 3M loss flat at lr floor). | shown | checks |

Flags: (a) the repo's caps.py at 612f5c5b01 still has the 9-register bug; the spec says the PC printed "36 35" with the overlay hash
before G1, but nothing in-run logs it. Worth one line in the 10M box/stdout check. (b) "62% web" is pieces; by rows it is 42.8%.

## 3. Proposed next steps for the roadmap thread (marks written before any run; one change each)

**D (free, CPU, saved final weights of 3M s400 and 10M s400 B2):** error ledger by file x family x chosen mode vs reachable modes;
oracle-mode rescoring (gain under best reachable mode); per-term teacher-forced loss on ~4k train rows split web/skill; 10M block
knockout (skip each block, and blocks 3-8 together, all rounds); gold log-likelihood per family. Decision rules written now:
- oracle-mode 10M gain >= +3.0 (vs +1.64) -> routing masks the thinker (cause 6) -> marginal mode loss test next;
- skipping blocks 3-8 at 10M costs < 1.0 point in_dist -> idle depth (cause 7 or 2) -> short lr test (5e-4 vs 1e-3);
- skill-term train loss at 10M <= half of 3M while dev flat -> memorisation (cause 2) confirmed.

**T-C, continuation mix (cause 4; Opus T2).** From the saved final 3M s400 and 10M s400 B2 weights: 2,000 more updates, batch 256,
100-step warmup then constant lr 1e-4, same accumulation, seed 400 order. Two arms per size: (a) same pool mix, (b) own rows only
(skills + english + teach, no web cloze). E(size) = pooled-5(b) - pooled-5(a).
- Pass: E(10M) >= +1.5 AND E(10M) - E(3M) >= +1.0.
- Proved wrong: E(10M) <= +0.5 OR E(10M) - E(3M) <= 0.
- Between: unclear; no more spend on cause 4 until G2f reads.
- Report: per file, the 13-family and 21-family blocks, error ratio, per-term train loss.
- Cost: ~7 h (10M, 2 arms x 2,000 x ~6.2 s) + ~1 h (3M) on the PC. Needs the 10M final weights; skip if they were not kept.

**T-P, self-found programs (cause 3).** 3M s400, otherwise exactly G1's 3M B2. One change: on training rows with no parsed program
and an integer gold answer, drop the NOOP op target (weight 0 instead of 0.1) and each update sample K = 8 programs per such row
from the model's own op/operand heads (temperature 1), run them on the calculator, and train op/operand/mode (NUM -> that result slot)
teacher-forced on the shortest sampled program whose result equals the gold answer; rows with no hit keep their GEN target.
Deployable: the model proposes, the calculator (an outside tool) checks; no hand rule.
- Pass: the four families (table_lookup, seq_next, fewshot_number_rule, rule_apply; 720 dev rows; G1 3M s400 = 219/720 = 30.4%,
  s401 30.3%) >= 38.4% (+8 points), AND pooled-5 >= 72.5, AND chain-5 >= 99.
- Proved wrong: four-family score <= 32.4% (+2).
- Between: run s401.
- Size follow-up only on a pass: the same change at 10M s400, scaling mark = own gain >= +3.3 (WIDE's bar).
- Cost: code (Sonnet medium) + ~8-10 h PC at 3M (sampling adds cost); fits Modal if the PC is busy.

**Reporting change (no run):** for WIDE, G2f and every later size test, also report the error ratio and the 13/21-family blocks
(Opus's yardstick; own error ratio <= 0.85 at two seeds = "scales well").

Not proposed: Fable's T1 (web weight 0.1 from scratch at 3M) is a recipe change that doesn't test size; T-C answers the same question
from saved weights at both sizes. Opus's T1 (attention reader, ~10.6M) is a good cause-5 test but competes with WIDE for the same
10M slot; hold it until the D ledger says misses are operand/pointer errors on variant rows.
