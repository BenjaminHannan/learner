# Race-mini: a cheap shared protocol for the sleep race (agreed by both sides 2026-10-27 06:15Z; sealed by the whole-model side)

Why: Ben (06:12Z Oct 27): stop waiting on paid GPUs; find cheaper tests. The 4090s are treated as not coming. A full K2 Week-2 sleep run is
~2.3 h on a 5090, mostly the dream pipeline (generation: tagging, names pass with 512 thinking tokens, dreams, REM), which both sides share and
neither side is allowed to change. So race-mini removes it: it races only the STORAGE, which is the only thing the sides differ in.

## Design
1. Shared dream tape, built once (Claude Haiku 4.5 via the Batches API, < $1, built and sealed by the whole-model side, sha on the board):
   for every Week-2 item VALUE (C1/C2/C4 facts, changing facts' old and new values, routines), 4 paraphrases + 4 question/answer pairs written from the
   item's sentence only, in the style of sleepb's nrem_prompt. A leak filter drops any line whose normalized question equals a test question (sleepb's leak set).
   Ground truth here only decides what each night studies: what a perfect tagger would have handed the dream writer. That is the same for both sides.
2. Nightly curriculum (deterministic, from the week file): night d studies every item value seen on >= 2 days up to d (C2, C4, CH values, RT), as of day d
   (a changed fact switches to its new value from its first new day on). C1 (said once) is never studied, matching Ben's rule that the notebook answers those.
3. Training per night, identical for both sides except the storage: sleepb's Trainer (fresh AdamW, cosine lr, CE + KL guard on 64 generic replay prompts
   vs the base), STEPS_PER_NIGHT = 300 (work scale 1), batch 16 drawn uniformly over tonight's items (half sentences, half Q&A; open-book Q&A off),
   then the side's own morning step (SHY / rounding / whatever it chose). No morning gate (the 100-question gate is noise; harm is scored instead).
   Model: K2-Horizon-3.7B, 4-bit packed base (--q4-packed). Seeds 1 and 2 (seed = tape sampling order + init).
4. Scores (served copy, weights only, greedy, sleepb's score_week rows): headline R = recall on the 200 C2+C4 forward questions; also reverse, changed new/stale (30),
   routine (20), C1 (should stay low), ARC-Easy 500 vs base (harm if < base - 5), mean KL on 32 held-out generic prompts.
   Lead = paired exact McNemar on pooled 400 items (2 seeds), p < 0.05, plus no harm. Each round is sealed in a PREREG before running.
5. Compute: one arm-seed = 2100 steps + scoring. Estimates (unmeasured): PC 5070 Ti ~20-30 min; Kaggle T4 fp16 ~1.5 h; M3 MLX port possible later.
   So a whole round (both sides' arms x 2 seeds) fits a PC gap of a few hours or a fraction of one Kaggle week.
6. Validity check (run first, both sides): race-mini's add-on control vs the full-pipeline numbers. If race-mini's ordering of two known arms
   (add-on q4 vs add-on bf16 base: 86.0 vs 96.5 in the full runs) is not reproduced, race-mini is not trusted.

## Additions agreed with the add-on side (06:15Z)
7. Also score after night 4 (mid-week curve point); the headline is the last night.
8. Validity pass: bf16-base add-on >= q4-base add-on + 3 points pooled over seeds 1 and 2, same direction on both seeds; it FAILS if the gap is < 1 point.
   The PC job checks seed 1 first and stops everything if the seed-1 gap is < 1 (both sides rethink).
9. A lead with p between 0.05 and 0.2 gets a seed 3 for both sides before it is called.
10. Tape: claude-haiku-5-5 via Batches, cost logged in the tape file. Built: tape_week1.json (Week-1, tuning only) and tape_week2.json (the race);
    values that came back unparseable were re-asked once with a larger token limit (race_tape.py --fill).
11. Each side keeps its own nightly morning step (add-on: sleepb SHY on the LoRA; whole-model: qs_morning, fp16 nearest).

## Code
backbone/sleep/brain/race/race_mini.py (shared trainer and scorer), race_tape.py (tape), pc_race_mini.sh (the combined PC job; order: add-on q4 seed 1,
bf16 seed 1, validity gate, LoRA+ x16 seed 1, whole-model lr scout on Week-1 (1e-3 / 3e-3 / 1e-2, 3 nights, pick = best C2+C4 recall with ARC-100 drop <= 3,
ties -> lower lr), whole-model seed 1, then seed 2 of add-on, LoRA+, whole-model, then bf16 seed 2). Defaults: steps 300/night, bsz 16, tok budget 512,
gen-bs 24, LoRA r16 a32 lr 2e-4, KL guard weight 1 on 64 generic replay prompts.
