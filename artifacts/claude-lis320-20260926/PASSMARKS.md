# lis-320 pass marks: a reader trained with no Claude-written or Claude-judged data must match lis-319f

Reading-facts thread. Written 2026-09-26 17:05 UTC. This is before the GLM pilot landed, before the full GLM data run,
before any lis-320 training, and before the test panel below was written. Plan:
design/v3/60-listener/lis-320-no-claude-data-plan.md. Ben 16:46 ("Retrain first"): lis-320 is the 0.2d reader only if it
matches lis-319f on a fresh sealed test. If it falls short, the demo waits, and lis-319f is not used as a fallback in the build.

## The one change
lis-320 changes only the training rows. Every row is a dialog worded by GLM 5.3 Flash from a code seed
(scripts/claude_lis320_seed.py, claude_lis320_glm.py, claude_lis320_check.py) with a code-written, code-checked label.
No Claude-written dialog, template, pool-based sentence or Claude-judged label is included, so the 23,044 Opus rows, o0b and
the lis-319f code sentences built on Claude text are all dropped. Kept the same: base model (MiniCPM5-1B), prompt format
(claude_lis319_common.build_prompt_hist), frame spec including the FORMER mode, training args (2 epochs, lr 2e-4, rank 32,
batch 16, max-len 512, seed 300), the compiler (claude_lis300_compiler, unchanged; the lis-319o owner patch failed and does
not carry over), and the save bar T = 0.995 for both readers. The data size and family mix are fixed after the pilot and
written into DATA.md before training. They are not a second change, because lis-320 is compared as a whole reader.

## Test set: readpanel320 (TEST-ONLY, not yet written)
The panel is written fresh by a blind Opus writer, checked by a blind second labeller and a blind adjudicator, and sealed
before either reader reads it. It follows the readpanel319o process (brief, blind_rows, agree, adjudicate, finalize,
README, AUDIT, SEAL). It has 40 dialogs of 8 user turns (320 rows), aiming for about:
- ordinary: about 110 rows;
- corrections: 50 or more correction facts (some with the owner named in the turn, some named only earlier, some in turns
  that also state other facts);
- backref: 60 or more rows whose fact owner is named only in an earlier turn (by pronoun or role word);
- former: 40 or more former items (no longer true);
- lookalike: 60 or more rows, 10 or more of them ambiguous-pronoun rows with no fact in the key;
- long turns: 40 or more rows over 20 words that state a fact.
Names must not be in avoid_names_dev.txt. The writer never sees the lis-320 seeder, GLM output or training data.
Known bias: lis-319f was trained on Opus-written chats and this panel is Opus-written, so the panel favours lis-319f. That
makes the test harder for lis-320, not easier.

## Scoring (both readers once each, same panel, T = 0.995, unchanged compiler)
- Whole-claim scoring is the same as lis-319k (scripts/claude_lis319k_score.py final: exact match first, then pairs both
  blind judges call the same under artifacts/claude-lis319c-20260926/full/JUDGE_SAME.md, one-to-one credit). It gives
  saved_right_full, wrong_turns_full, correction_right, stale_saves and lookalike_saves.
- former_as_current follows the lis-319f definition (scripts/claude_lis319f_score.py panel).
- wrong_person (new; its scorer is written and self-tested before the panel is read): a saved fact on a backref row whose
  value matches, after normalising, the value of a gold fact of that row while its owner differs from that gold fact's
  owner, ignoring case. Relation names are ignored, which fixes the lis-319o undercount.
- ambiguous_saves: saved facts on lookalike rows whose reason is "ambiguous".

## Marks (new = lis-320, old = lis-319f)
| Mark | Bar |
|---|---|
| R1 | new saved_right_full >= floor(0.95 x old saved_right_full) |
| R2 | new wrong_turns_full <= old wrong_turns_full + 2 |
| R3 | new correction_right >= old correction_right - 2 |
| R4 | new former_as_current <= max(1, old former_as_current) |
| R5 | new wrong_person <= old wrong_person + 1 |
| R6 | new ambiguous_saves <= old ambiguous_saves, and new lookalike_saves <= old lookalike_saves + 2 |
PASS = R1 to R6 all hold.
Proved wrong (lis-320 clearly worse): new saved_right_full < 0.90 x old, or new wrong_turns_full > old + 5.
Validity: the sealed panel must have at least 40 correction facts, 50 backref rows, 30 former items and 10 ambiguous rows,
and old saved_right_full must be at least 60. Otherwise the verdict is INCONCLUSIVE, reported as such and not as a pass.

## Report only (no bar)
- A second panel worded by GLM with a different prompt and temperature 0.7, labelled by code (TEST-ONLY, never trained on):
  both readers' counts.
- Per-kind counts, the style metrics (claude_lis320_style.py) of the training data vs DEV chats, and the lis-319 dev scorer
  on the lis-320 dev split.
- The brain-first bet (owner resolved at encoding, UNCLEAR when two people fit, pointer to the raw turn) is judged by R5
  and R6. If wrong_person goes above its mark, or any ambiguous row gets a save, while right backref saves rise, owner
  resolution moves to recall.
