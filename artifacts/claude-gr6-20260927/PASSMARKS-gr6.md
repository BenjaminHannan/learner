# PASSMARKS gr-6: wider practice for the trained reader (registered 2026-09-27 01:16 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. These marks were written before any gr-6 code,
layout, training row, blind writing, panel or adapter existed. They are never edited; changes go in a dated addendum
before the registered run. The draft (DRAFT-PASSMARKS-gr6.md, cd37fe2b9) went to the Thread manager at 01:14 UTC. The
review (01:15 UTC) passed it with four changes, all written in below: the proved-wrong result, what R2 measures, the
order of sealing, and the G5 comparison.

## Why
gr-5 (VERIFY-gr5, bb3bc66e2) trained the reader 1B to copy the square or say none. It read 100 of 100 squares in the
practice layouts exactly, with 0 wrong grids and 0 of 300 general items read as squares. It failed on two things:
- R2: 2 false squares among 53 lookalikes. Both were 5 x 5 blocks of single digits that are not a valid partial Latin
  square.
- New formats: 40 of 60 exact (U1, bar 48) and 13 wrong grids (U2, bar 2). 8 of the 13 were copied too big.

The plain, well-known fix for both is wider practice, with one change to gr-5: its training data. The reader gets many
more square layouts to practise on, and near-miss number blocks that are not puzzles, labelled none.

## Brain first (Ben 16:05)
- **Varied practice.** People who practise a skill in many variants transfer it better to a new variant than people who
  practise one variant more. This is shown in motor and category learning (schema theory, variability of practice).
  Here it is untested for this model.
- **Near misses.** A concept gets sharper from examples that almost fit it but do not.
- **The reader's job.** A child who has copied grids from many kinds of page learns what a grid is, and not just one
  page's layout.

## One change from gr-5: the training data, sealed as one recipe (review point 2)
The prompt, grammar, decode, LoRA shape and training recipe are gr-5's, unchanged: seed, 3 epochs, lr 2e-4, batch 8,
loss on the answer only, epoch-3 adapter tested. The training rows are gr-5's rows, each on the side of the split it
had in gr-5, plus two code-made parts. A pass is credited to this recipe as a whole, never to one of its two parts.

**1. 40 new layouts, drawn by code.** The part lists they are drawn from are hand-written scaffolding, disclosed here
as gr-1's 8 layouts were, and they are sealed in scripts/claude_gr6.py with the 40 drawn layouts. The Thread manager
agreed (01:15 UTC) that the drawn layouts count as code data.
- A seeded draw from lists of parts:
  - row labels: none, "Row {i}: ", "{A}: ", "{i}. ", "Line {i}: " and others
  - row wrappers: none, [ ], ( ), { }, | |
  - cell separators: space, ", ", " | ", " & ", ";", " / ", tab
  - row joins: new line, blank line, " / ", "; "
  - an optional divider line, an optional column header, and optional lines before and after the grid
- No layout matches one of gr-1's 8 by the rule in "Formats that count as the same" below.
- A seeded split sends 32 layouts to training and 8 to dev only.

**2. The squares and the near misses.**
- Squares: 8 squares per new layout (320), sizes 3 to 8, about 20% broken as in 358b3. Each sits in the 1B's own
  opener and closer lines (gr-1's wrap_drafts_1b.jsonl), built the way gr-1 built its practice.
- Near misses: 160 blocks of s x s single digits (s from 3 to 7) with at least one digit above s. So each block looks
  like a square but cannot be one of size s.
  - Each is written in one of the 40 training layouts (gr-1's 8 plus the 32), inside the 1B's own everyday messages or
    opener lines, and labelled "none".
  - The build checks that read_latin reads each whole message as none. It drops and counts any block that read_latin
    reads as a square, so these labels agree with how the test decides "none".

**Split.** gr-5's rows keep their split. For new rows in training layouts, every fifth row of each kind goes to dev.
All squares in the 8 dev-only layouts go to dev. The planned counts, which the build prints and seals, are:
- about 1072 training rows: 579 none, 493 squares
- about 326 dev rows: 72 + 51 held-out squares, 107 + 32 none rows, and 64 squares in dev-only layouts

No Claude-written text goes into training. The wrappers are the 1B's own words, the targets are printed by code, and
the layouts are code drawn from the disclosed part lists. The blind writer's wrappers, lookalikes and formats are
Claude-written, and they go into the test only, which the rule allows.

## Formats that count as the same (review point 1; sealed before training, checked by code)
- **The rule.** Two formats are the same when they write a row the same way: the same row label, row wrapper, cell
  separator, row join and divider.
- **How code compares them.** In each part, digits and label letters are replaced by one mark, runs of spaces and tabs
  become one space, and the ends are trimmed.
- **What does not make a format new.** A column header, or lines before and after the grid.
- **What gr-6's unseen formats must avoid.** They must not be the same as any of the 48 training or dev layouts: gr-1's
  8 with their variants, plus the 40 new ones.
- **Report only.** U1 split by whether an unseen format's cell separator appears in any training layout.

## Test data (blind, fresh, made and sealed before the adapter is trained)
- **Order of sealing (review point 3).** First the 40 layouts are drawn and sealed with the code. Then, before any
  training starts, the blind writer is asked for its writings, which are sealed as written. Only then does the maker
  read them, and the same-format check runs after both are sealed.
- **A new blind writer.** It is a fresh agent that has not seen gr-5's panel, any code or the training layouts. It writes:
  - 30 wrappers
  - 60 lookalikes
  - 40 grid formats in the recipe keys
- **Picking the 20 unseen formats.** The maker keeps the first 20 formats, in the writer's order, that pass the
  same-format check. If fewer than 20 pass, the writer is asked once for 20 more. If there are still too few, the run
  stops and is reported.
- **The panel.** The maker is gr-5's maker with new seeds (checked unused) and gr6- ids. The panel holds:
  - 100 squares in 358b3's "Row k:" and bare layouts
  - 60 lookalikes
  - 60 squares in the 20 unseen formats, 3 per format
  - dl-1's 300 general items
- **Which lookalikes count as "none" (review point 4).** A lookalike counts as "none" when read_latin reads it as
  none. The maker computes this when it writes the panel. The count of "none" lookalikes (R2's denominator) and the
  number that hold a square are printed and sealed before training.
- **What R2 measures (review point 2).** read_latin is a hand-written stand-in, so R2 measures agreement with
  read_latin on the lookalikes, not agreement with a human judgement.
- **Who reads the panel.** Only the run and score code, which print counts only. The owner never prints a panel row.

## Arms (each task launched once, greedy)
- L6: gr-6. It decides the marks. Tasks: squares, lookalikes, unseen, general.
- G5: gr-5's adapter (sha256 9f19edb7..., kept in the shared folder), on squares, lookalikes and unseen. It uses the
  same panel, the same prompt, the same grammar and the same greedy decode as L6; only the adapter differs. It is
  report only on the marks and is the comparison in the one proved-wrong result below.
- C: read_latin, report only, and no comparison on R1 and R2.
- The plain 1B is not run again. It was shown twice: 4 of 20 practice squares, and 41 of 100 on gr-5's panel.

## Marks (the same bars as gr-1 to gr-5)
| Row | Test | Bar |
|---|---|---|
| R1 | squares read exactly, L6 | >= 97 of 100 |
| R2 | lookalikes read as a square where the truth is none, L6 | <= 1 |
| R3 | squares read as a different grid, L6 | <= 1 |
| R4 | general items read as a square, L6 | 0 of 300 |
| U1 | unseen-format squares read exactly, L6 | >= 48 of 60 |
| U2 | unseen-format squares read as a different grid, L6 | <= 2 |

gr-6 passes only if R1 to R4 all pass. gr-6U is its own verdict (U1 and U2). A FAIL stays a FAIL. The ADDENDUM-1 style
lines are reported again: L6 and G5 on the lookalikes that hold a square, and the dev split by shared wrapper.

## Dev stop rule (fixed now)
- **Stop rule.** The run stops as a dev FAIL, and the panel is not spent, if either of these happens:
  - fewer than 90% of the held-out squares in training layouts are read exactly
  - any held-out none row is read as a square
- **Report only.** Squares in the 8 dev-only layouts (exact, wrong and none, out of 64), and the 30 format-dev messages.

## Predictions (fixed now)
- R1 and R4 pass, because gr-5 passed them.
- R2 passes. This is suggested only. The near misses match what gr-5's 2 false squares were, but not their layouts.
- Dev-only layouts: at least 80% exact.
- U1 lands from 48 to 55 of 60, and U2 is at most 5. A U2 pass (at most 2) is not predicted with confidence.
- L6 beats G5 on U1 (unseen-format squares read exactly) on the same panel by at least 6 of 60.

## What would prove it wrong (fixed now; review point 1)
The hypothesis is that wider practice (this recipe) makes the reader better at formats it never practised. It is proved
wrong if L6's U1 (unseen-format squares read exactly) is not above G5's U1 on the same panel, with the same prompt and
grammar.

## Readings fixed in advance (not proved-wrong results)
- **Code layouts don't cover how people write grids.** U1 is under 48 while the dev-only layouts reach at least 80%.
  The reader transfers to new code layouts but not to a person's formats, so more code layouts are not the path.
- **Wider practice doesn't teach grids at this size.** U1 is under 48 and the dev-only layouts are under 80%. Wider
  practice does not teach grids in general to this 1B and adapter at this data size.
- **The near misses did not teach "find the square".** R2 is 2 or more; the false squares come from something else.
- **The new data hurt the practice layouts.** R1 is under 97 or R3 is 2 or more.

## Where it runs
- **Compute.** This container's CPU, $0, with ADDENDUM-gr5-3's rules: a 6-hour cap and then PARTIAL, a reclaim means a
  restart from the start under the same seal, and a RUN-NOTE with the first STEP line and the PID.
- **Estimated time.** About 2 hours of training, 20 minutes of dev and 40 minutes of runs.
- **What stays off git.** The adapter.

## Not in this recipe
No code check for the Latin rule (Thread manager 01:10: agreed, since it would be a new hand-written rule and 358b3
plants broken puzzles). The gr-5 panel is never used again.
