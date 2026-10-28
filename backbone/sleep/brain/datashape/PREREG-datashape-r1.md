# Data-shape round 1: wider cards (W) and linked two-hop cards (L) on race-mini (written 2026-10-28 ~03:00Z, before any W or L run)

Thread "Shape training data for better sleep" (Ben 2026-10-28 02:20Z: "figure out how to manipulate data so that training gives better results").
Labels: shown / suggested / untested. Small card experiment only (race-mini harness, Week-2 world); not the village model.

## Harness (nothing here changes)
Race-mini (backbone/sleep/brain/race/PROTOCOL-mini.md + ADDENDUM-1 + ADDENDUM-2): frozen code `race_mini.py` at f5d5bc5f81, LFM3-1.7B rev 40ebe0aa66 on the
served QAD-Q4_0 GGUF (`--base q4_0`), add-on storage (LoRA r16 a32, lr 2e-4, SHY), **75 steps a night**, bsz 16, half sentences / half Q&A, KL guard,
no morning gate, Week-2, seeds 1 and 2. Controls: `c75_s1`, `c75_s2` (same code, same flags, shared tape `tape_week2.json` sha 8c242e48...), rerun in the same job on the
same machine, so every arm shares one GPU (race-mini v2's own c75 runs on BensPC are reported only).
Headline tag as race-mini addendum 1: if the pooled control's final C2+C4 >= 90, every number below uses the night-4 score instead (decided by analyze.py from the control alone).
Only the `--tape` file differs from the control. Run script `run_datashape.sh`; analysis `analyze.py` (exact two-sided McNemar on the 400 pooled paired C2+C4 forward items).

## Arm W: more distinct cards at equal steps (one change: the tape)
Every value keeps its cards and gets up to 8 more paraphrases and 8 more Q&A from Claude Haiku (Batches), asked to differ in structure from the existing
ones; near copies (token Jaccard >= 0.8 to a kept line), leaks (sleepb's leak rule) and answers that are not one of the value's names are dropped (`make_tapes.py --arm W`).
Steps are unchanged, so each card is drawn about half as often. Same idea as sleep addendum 15's D8 (32 + 32 cards per item), but at equal steps on the 4-bit add-on.
- Why (suggested): Allen-Zhu & Li 2023 (Physics of LMs 3.1, arXiv 2309.14316) and Mecklenburg et al. 2024 (arXiv 2404.00213) report that more varied
  restatements per fact make facts extractable by new questions; our own test questions are worded differently from every card. Against: on Qwen3.5-2B,
  twisted dreams = plain paraphrases at equal count (addendum 6: 69.0 vs 68.5), so variety alone may add nothing.
- **PASS:** pooled C2+C4 recall >= control + 4 points, p < 0.05, and no harm (ARC-Easy 500 >= base - 5 on both seeds).
- **WRONG (the idea is refuted):** recall <= control - 4 with p < 0.05 (fewer repeats per card cost more than the variety gains).
- Anything else: FAIL (no effect shown). A lead with 0.05 <= p < 0.2 gets seed 3 for control and W before it is called (race-mini rule 9).
- Reported, not judged: per-seed recall, reverse, changed-new/stale, C1 (should stay low), KL, wall time.

## Arm L: linked two-hop cards (one change: the tape)
For 41 of the 78 Week-2 two-hop test pairs (within each chain kind, tests k with (k // 2) % 2 == 0, `make_tapes.carded`; balanced over the two test question templates), the first fact's tape value gets
1 linked sentence naming both facts and the middle person (e.g. "Raiflibas's mentor, Rabrituth, lives in Gigadrith.") and 2 two-hop Q&A in wordings that are
not the test's (template-built from ground truth, no model writer; leak-checked). The other 37 pairs get nothing. The number of linked cards per carded pair is fixed (3).
- Why: sleep thread addendum 14: a dreamed chain is answered right 87-96% (Qwen3.5-2B), 0-4% when not dreamed (shown, other model and storage).
  Balesni et al. (two-hop curse, arXiv 2411.16353): training on some two-hop pairs did not generalize to held-out pairs (shown in their synthetic setting).
  New here: gold cards with no writer in the way, on LFM3 4-bit + LoRA, and the carded-vs-uncarded split.
- **L1 (carded pairs are learned):** two-hop on carded pairs >= 50% and >= uncarded + 30 points (pooled seeds). WRONG-if: carded < control's carded + 10.
- **L2 (generalization to uncarded pairs):** uncarded two-hop >= control's uncarded + 10 points with p < 0.05. Expected to FAIL (Balesni), which would
  mean every two-hop fact needs its own card (coverage is everything).
- **No harm:** C2+C4 recall > control - 3 points and ARC-Easy 500 >= base - 5.
- Known caveat: a linked card can teach the second fact before its own night (both facts are C2/C4, so they are studied later anyway).

## Compute
6 arm-seeds in this order: c75_s1, W_s1, L_s1, c75_s2, W_s2, L_s2 (est. 20-40 min each, ~3 h; unmeasured), on the Radeon PC (brikto, RX 7700 XT 12 GB,
WSL ~/rvenv, cap 11 GiB) after lfm3q4 arm G (coordinator 02:31Z Oct 28). Free compute only; tapes cost about $1 of Haiku Batches.

## Tape facts (built before sealing)
- W: Haiku batch msgbatch_014BNQNZzkByRo5ajSG7yMh9, est. $1.29; 344 values, 8 replies unparseable (those values keep only the shared cards), +2686 paraphrases and +2672 Q&A kept (dropped: 7 near copies, 2 leaks, 9 bad answers); mean 15.8 paraphrases and 15.2 Q&A per value (shared tape: ~8 + 8).
- L: 41 carded / 37 uncarded pairs.

## Seals
Tapes: `tapes/tape_week2_W.json`, `tapes/tape_week2_L.json` (sha256 in SEALS-datashape-r1.sha256 together with this file).

## Amendment 1 (2026-10-28 ~02:40Z, before any W, L or control run finished; the first launch died in 8 s on every arm)
- Review found the first L split (every other pair, k % 2) put all carded pairs on test template 0 and all uncarded on template 1 (week.make_tests picks the
  template with k % 2), mixing L1 with question wording. Split changed to (k // 2) % 2 (41 / 37, both templates on both sides); L tape rebuilt and resealed.
- analyze.py: two-hop uses the same headline tag (final or night-4) as recall; L1 WRONG-if is now computed; an ARC error counts as harm; rule-9 "lead" flagged.
- sleepb.mem_cap: indexed device (ROCm torch rejects torch.device("cuda") in set_per_process_memory_fraction). Changes no number.
