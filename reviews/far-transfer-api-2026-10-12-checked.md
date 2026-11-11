# Fable 5.1 and Opus 5.5 on far transfer: claims checked against the code (Mon Oct 12, 2026, 10 AM ET)

Answers: branch claude/project-thread-s3y3gg, reviews/far-transfer-api-2026-10-12/ (Fable verbatim brief; Opus got the
brief with the "no access to code" sentence reworded after three false-positive refusals). Brief:
reviews/api-far-transfer-2026-10-12.md. Cost $2.17.

## Where they agree (and what the code / data says)

| claim | Fable | Opus | check |
|---|---|---|---|
| Main cause is the practice, not the model: the loop never practises two whole calculations side by side, then one call joining their results | yes (rank 1) | yes (rank 1) | **shown** (L1 89 vs L2/L4/L8 2-4; L8 0.0% such rows) |
| The edit step killing composed drafts (9,999 in 10,000) is why the loop can't supply them | yes | yes | **shown** (L9 R2 build: about 90 joined rows per million draws) |
| Rank 8 is too small for joins; use rank 64 in the loop | yes | yes | **shown** (L5 vs L6: new pairs 9.8 -> 56.9, new layout 5.2 -> 13.6, no forgetting) |
| Not "no composition at 3M": recombination of practised ingredients is partial (best unseen layout 36.7) | yes | yes | **shown** |
| L9 tests whether such data teaches joins, not whether the loop makes it; its six forms were written with the test in view (both F4 layouts are among them) | yes | yes | **agreed**: the forms came from L4 (written after L1). L9 is reported as generator learnability only |
| Next loop change: edit the pieces first (on one edited grid), join two already-valid pieces last, and on `?` redraw only the join or the failing piece instead of discarding | change 1 | change 2 | **untested**; the day-1 keep-rate (now 1 in 10,000) is measurable without training |
| Measure first, for free, how much a splitting tool would help (pieces right alone vs whole right) | first-error split | join-gap audit | **running** as A1 (MARKS-A1-join-gap-2026-10-12.md), evaluation only |
| A 10M test on the L5 protocol separates "size buys composition" from not | marks: unseen layout >= 60 yes, 35-45 no | marks (rank 64): >= 30 yes, <= 18 no | **queued**: the 10M checkpoint is on BensPC, not reachable from this container |

## Claims that do not match the code

- **"16 number slots cap far: a 6-row, 3-column grid has 18 digit runs"** (both): wrong premise. Every sheet grid has two
  columns (A and B; `domain/far/sheet_probe.py` `candidate` and `domain/panel.py` `render`), and every probe and panel
  row was built within the 16-run cap (F5: 164 of 420 rows at exactly 7 calls, all within 16 numbers). The slot cap is
  not shown to limit far.
- **"L8 probably filled one leaf at a time"** (Opus): partly wrong. L8's substitution recursed up to 3 deep on the same
  example, so two holes of one host could both be filled; its 0.0% came from the layout quota spreading over 599 layouts
  and from survival (two-call joins about 1 in 10,000 through the edits, a call glued to a cell expression about 1 in 700).
- **"Does the add-on adapt the reader or embeddings?"** (Opus, missing fact): the add-on wraps every `torch.nn.Linear`
  (`domain/mode.py` AddOn); embeddings are not adapted.

## What changes in the plan

1. L9 keeps running, reported as "help-page-only data can / cannot teach the test's joins" (not a loop result).
2. A1 join-gap audit now (evaluation only): decides whether a splitting tool is worth building.
3. Next loop change (marks first): join-last with repair, census before training (keep-rate >= 1 in 10; joined rows
   >= 25% of a night), then a real mode run at rank 64. Opus's arm B (hold `(K)*(J)` out) as the transfer check.
4. 10M L5 protocol when a 10M checkpoint is reachable (PC), marks as above.
