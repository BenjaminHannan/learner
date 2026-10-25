# Sleep-B addendum 15: long nights with varied cards vs repeated cards (written 2026-10-25 ~21:50Z, before the code, the new-wording questions and any run)

Labels: shown / suggested / untested. Model K2-Horizon-3.7B (bf16 base), Week-2 world, seed 1. Not the village model, not the card experiments.

## Why
- Ben (2026-10-25 20:36Z): the assistant is often idle for up to about 12 hours while he sleeps, so sleep could use all of that time.
- Ben (2026-10-25 ~21:15Z), on long nights: "it's really important that it's also diverse flashcards, because if you just have like 12
  hours, you know you're going to have the issue of over-memorization. So that's why you want like the weird dreams thing."

What we know:
- **Shown (Qwen3.5-2B, Week-2):** more night work helps: 1x -> 2x +14.5 recall (p = 0.0005), 2x -> 4x +9 (p = 0.001).
- **Shown (Qwen3.5-2B, Week-2, 2x work, addendum 6):** twisted dream scenes are no better than the same number of plain paraphrases
  (69.0 vs 68.5, p = 1.0). Changed-new fell 73.3 -> 60.0 with the twisted scenes (p = 0.22, not significant).
- **Untested:** whether cramming (learning the exact card wordings rather than the fact) appears on long nights, and whether varied
  cards prevent it. Today's sleep writes each item's cards once, from one prompt, and rehearses them every night until the item is
  mentioned again. At work scale s, one prompt asks for 4s paraphrases and 4s question cards (64 in one reply at 8x).
- **Suggested (literature, language-model pretraining):** repeating the same data up to about 4 times is almost as good as new data.
  8x may be too short for cramming to show. This is a risk for V1/V2 below.

## The base recipe (fixed now, from addendum 14's outcome)
- If addendum-14 arm B (k2c_r2) passes its no-harm marks and its two-hop is >= arm A's, the base is B's flags.
- Otherwise, if A (k2c) passes its no-harm marks, the base is A's flags.
- Otherwise, the base is the adopted recipe with defaults (ab_ob_b4_nb, k2s_bf16's flags).
- `--think-eval` (report-only) is left out.
- The **4x reference** is that addendum-14 arm, or k2s_bf16 when the defaults are the base.
- Every arm below uses the same `--gen-bs` (16, so it fits a 16 GB GPU), whichever GPU runs it.

## Arms (Week-2, seed 1, K2 bf16, base flags plus)
- **R8, repeats:** `--budget-scale 8 --text-scale 4`. Twice the 4x training steps. Every generation knob stays at 4x: cards per
  item, item cap, REM chain and gist caps, and dream token budget. So the same cards as a 4x night are practised about twice as often.
- **V8, varied cards with weird dreams:** `--budget-scale 8 --dream-vary mix`. The question cards are as at 8x (32 per item). The 32
  paraphrase-like texts come from four styles, 8 each:
  - plain paraphrases (nrem_prompt asking for 8);
  - a tiny everyday story;
  - a note in Sam's own voice;
  - a weird, surreal dream scene in which the fact stays true (twist_prompt style).
  Every style text must pass the same checks as a twisted scene: it names both entities; it is not a test leak; it names no older value
  of the fact (stale_hit); and the base model, shown only the text, answers one of the item's question cards. Style texts are sampled
  under their own fixed seed, so the main sampling stream is unchanged.
- **D8, today's long night:** `--budget-scale 8`. The same counts as V8 (32 paraphrases and 32 question cards per item), all from the
  one nrem_prompt.
- **V8p, varied cards without weird dreams (runs only if V1 passes):** `--dream-vary plain`, which is V8 with a second batch of 8
  ordinary paraphrases (para2_prompt style, different seed) in place of the weird scenes.

One-change pairs:
- R8 -> V8 is the variety package (more distinct cards, from varied styles), at equal training steps.
- D8 -> V8 is style variety alone, at an equal number of cards.
- V8p -> V8 is the weird dreams alone.
- 4x reference -> D8 is today's recipe made 2x longer.

Run order: R8 and V8 first (Ben's rule), then D8, then V8p.

## New report-only measures (`--reword FILE`, all arms; scored after the usual scoring, weights only, no thinking, greedy, 20 tokens)
- **New-wording questions** (data/week2_reworded.json). Claude writes them once through the Message Batches API, after this PREREG and
  before any run. The file's sha256 goes in RESULTS before the first run that uses it. Contents:
  - 3 rewordings for each C2+C4 forward and reverse test (400 tests);
  - 3 rewordings for each two-hop test (78).
  A rewording is kept if:
  - it ends with "?";
  - it names every name the original question names;
  - it does not contain the answer;
  - it is not a test string;
  - its token overlap (Jaccard) with the original question is below 0.6.
  The leak list is not changed, so training is the same with or without the file.
- **New-wording recall:** a test counts right if at least 2 of its 3 rewordings are answered right (or a majority of those kept). The
  share is over the 400 C2+C4 forward and reverse tests. Two-hop new-wording recall is reported the same way over the 78 tests.
- **Card recall:** for each of those 400 tests, take the matching item's kept question cards whose answer is the test's target, and
  sample up to 3 under a fixed seed. Ask each card's exact wording.
- **Cramming gap:** mean card accuracy minus mean new-wording accuracy, in points. It is computed over the tests that have at least one
  matching card. A model that learned wordings rather than facts shows a large gap.
- **Two-hop card gap:** for two-hop tests with a kept forward chain dream, the chain dream's exact question vs the test's rewordings.
- **Seen check:** the number of rewordings found word for word (normalized) in any kept text of that arm. V1 is also reported on the
  unseen ones only.
- **Card variety:** per item, the mean pairwise token Jaccard of its kept texts and the share of near-duplicate pairs (>= 0.8).

## Pass marks (fixed now; McNemar = paired exact two-sided test on the 400 C2+C4 tests, majority-of-3 right/wrong)
- **V1 (Ben's rule: varied cards beat repeated cards on new wordings):** V8's new-wording recall >= R8's + 4 points, McNemar p < 0.05.
  - **Wrong if** V8's new-wording recall <= R8's.
  - Inconclusive (ceiling) if R8's new-wording recall is >= 97.
- **V2 (repeats cram):** R8's cramming gap >= V8's gap + 5 points.
  - **Wrong if** R8's gap <= V8's gap.
  - The 4x reference's gap is reported next to them.
- **V3 (style variety beats today's long-night cards at an equal count):** V8's new-wording recall >= D8's + 3, McNemar p < 0.05.
  - **Wrong if** V8 <= D8.
- **V4 (only if V8p runs; the weird dreams themselves):** V8's new-wording recall >= V8p's + 3, McNemar p < 0.05.
  - **Wrong if** V8 <= V8p.
- **L1 (a 2x longer night pays):** take the better of D8 and V8 on new-wording recall. Pass if, compared with the 4x reference,
  new-wording recall is >= +3 points or two-hop is >= +5 points, either with paired p < 0.05.
  - **Wrong if** neither is higher than the 4x reference.
  - The 4x reference has new-wording scores only if it ran with `--reword`. Otherwise L1 is judged on two-hop alone.
- **No harm (each 8x arm):**
  - recall C2+C4 (usual questions) >= 93.5;
  - ARC-Easy >= that run's pre-sleep ARC-Easy - 5;
  - diary >= base_diary - 5;
  - changed-new >= the 4x reference's - 10.
- **Reported, not marked:**
  - two-hop and G (>= 75 of 78) for each arm;
  - reverse, routine, two-hop new-wording recall and the two-hop card gap;
  - card variety and wall time per night (with the generation share);
  - per-style yields (generated, kept, dropped by each check).
- **Expectation (not a mark):** V8 - R8 between 0 and +8 on new-wording recall; R8's gap a few points larger than V8's. V1 and V2 may
  both fail at 8x (the repetition risk above). Then the 16x follow-up tests R against V again.

## What comes next (not part of this test)
- If V1 and V3 pass: V becomes the long-night recipe. Then a 16x V arm, and a real 12 h Mac night.
- If V1 fails and R8's gap is no larger than the 4x reference's: there is no cramming at 8x. Repeat R vs V at 16x before any 12 h night.
- If V8 passes and V8p is equal (V4 fails): the weird part is not needed, and plain variety is enough.

## Compute
- Ben's PC (RTX 5070 Ti, 16 GB) after Think-2, when the coordinator says go. Estimate: about 9-10 h per 8x arm (suggested from the 4x
  K2 run: 1.75 h on an RTX 5090).
- An RTX 5090 on Vast is the fallback: about 4-4.5 h, about $2.20 an arm. It is used only within the weekly budget and after a check
  with the coordinator.
- R8 and V8 should run on the same GPU type if possible.
- Each JSON and log is pulled before the box stops, and the actual cost of each box is reported.
