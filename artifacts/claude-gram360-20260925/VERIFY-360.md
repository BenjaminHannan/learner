# VERIFY gram-360 (grammar thread, 2026-09-25 ~02:55 UTC)

**Verdict: PASS on all four registered marks** (PASSMARKS.md, registered at main 1e4bb87ac before the run).
Run: rent-360-gram on bank G (sealed, 3/3 OK on the rental), P360 and P330c arms, RTX 5090, ~$0.30, 0 tracebacks
(RESULTS-rent.md on builder-outbox). Graders: two blind Opus agents, neutral PASSMARKS question, each saw one
shuffled file of 376 lines (296 run lines + 40 planted errors + 40 planted clean) and never the key.

| Mark | Bar | Grader A | Grader B | Verdict |
|---|---|---|---|---|
| grader valid | >= 36/40 each | planted 39/40, clean 40/40 | planted 39/40, clean 40/40 | valid |
| P360.1 rendered fill-in lines | >= 90% | 141/154 (91.6%) | 140/154 (90.9%) | PASS |
| P360.2 gain over unrendered | >= +20 | 92/154 (59.7%) -> +31.9 | 93/154 (60.4%) -> +30.5 | PASS |
| P360.3 score changes / non-rule parts changed | 0 / 0 | confirm flag 0, confirm answer 0, ask class 0; 0 of 103 non-rule parts | | PASS |
| P360.4 slot words lost | 0 | 0 (68 of 183 rule parts rendered) | | PASS |

Proved-wrong clause (gain < +5): not triggered.

## Report only
- All distinct P360 replies (the 336 M7 measure, bar 99% there): 172/193 (89.1%) and 170/193 (88.1%).
  Lines that are not rule-agent parts (mostly the 1B's chat and creative replies): 75/87 and 73/87 clean.
- 336 scorer, P360 vs P330c (separate runs; the 1B samples differ between runs): facts saved 71 vs 71, day-1 kept
  52/52 both, asks RIGHT 17 vs 16, WRONG_CANDIDATE 4 vs 3, confirm rows 56 vs 55, new_triples 80 vs 81. The paired
  replay (P360.3) shows rendering itself changed no score, so these small differences come from sampling.
- Still-flagged fill-in lines, by shape (counts from the graders' reasons, no text quoted): a place name the word
  list does not know stays lowercase (2 each); "ex wife" without a hyphen (2 each); a plural value in the "goes
  with" wording takes "does ... go" (1-2 each); garbled frames from the reader (about 4 each); a missing article
  before a breed (B: 2); one statement ending in "?".
- DEV check of the 1B's own replies (one strict grader, 101 DEV replies, report only): 83/101 clean; errors are
  garbled or unnatural phrases (9), lowercase proper nouns (3), wrong prepositions (2), agreement, word order,
  a missing quote, a repeated word (1 each). No cut-off replies.

## What it means
The fill-in lines went from about 60% to about 91% clean without changing a single save, answer or confirm.
Whole replies are at about 89%, so 99% needs the next steps in design/v3/30-modes/360-grammar-roadmap.md:
the 1B's replies are now the largest source of misses (about 14% of them flagged), then nonsense reader frames.
gram-360 is already arm G of 336b (month-end thread).

## Step 2 prototype finding (DEV, CPU, report only)
The 1B as a judge of fill-in sentences separates flagged from clean lines only weakly: AUC 0.71 (yes/no margin
on whole lines), 0.56-0.62 on single frame sentences; average log-probability 0.35 (worse than chance). So the
roadmap's step 2 as written (1B fluency score as the gate) is not usable; it needs a different learned check.
