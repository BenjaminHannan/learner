# Merge 138nb: results (registered run 2026-09-23)

## Verdict: PASS (all of M1–M6 pass; one driver-only deviation, D1, reported below; no sealed file changed)

138nb is 138n plus one outermost reply-text rule: replies answered by
stage `loop190-reverse` that name a subject gain " (worked out
backwards)". Every measured difference from 138n is that label, and
nothing else. No panel item text is quoted anywhere in this file.

## Marks table (integer counts)

| Mark | Result | Counts |
|---|---|---|
| M1 invpanel138nb (blind, 70 items) | PASS (deviation D1) | 138nb wrong 0/70; question writes 0 (qw only the 4 teach_control statement turns, same ids both arms); whose_R 14/14 (138n 2); lives_born 10/10 (138n 0); has_as 6/6 (138n 2); verb_backwards 9/9 kept, lost 0; my_backwards 4/4 (138n 1); no_match 8/8; unknown_value 4/4; forward_control 10/10 byte-identical; teach_control 4/4 byte-identical |
| M2 dev/case vs 138n (720 cases) | PASS | moved vs 138n 1 (221/D11, predicted); unpredicted 0; predicted-ok 1; predicted-wrong 0; predicted-not-moved 0 |
| M3 frozen suites + probes vs 138n | PASS | sessions152 0; bench 0; marks123 0; rt136 16 (13 allowed WRONG-WRITE C019–C031 + 3 reply-only C076/C079/C115); direct-vs-138n moved 0/145; rt143-nogate 0 moves, 0 flips (n 124); probes: 18 reply changes (all predicted), 0 write changes, 0 ghosts, 0 failed dup checks, fresh-138n-vs-saved 0 |
| M4 sleep smoke + bench x3 | PASS | differing fields 4 (.agent .config .label .seconds); bad 0; bench identical 4/4 x3 |
| M5 latency | PASS | median 138n 2.687 ms, median 138nb 2.565 ms, delta −0.121 ms (bar <= +2 ms); n 624/624 |
| M6 tablepanel221 regression (91 items) | PASS | 138nb wrong 0 (138n 0); right 138n 80 → 138nb 84; lost 0; gained 4; loop190-subject candidates 4, all right; question writes 0 |

## Every move, by id and category (no item text)

M1 gained right on 138nb (29, all backwards families, each a label gain
on a 190 subject answer): i138nb-001, i138nb-002, i138nb-003,
i138nb-005, i138nb-006, i138nb-008, i138nb-009, i138nb-010, i138nb-011,
i138nb-012, i138nb-013, i138nb-014, i138nb-015, i138nb-016, i138nb-017,
i138nb-018, i138nb-019, i138nb-020, i138nb-021, i138nb-022, i138nb-023,
i138nb-024, i138nb-027, i138nb-028, i138nb-029, i138nb-030, i138nb-041,
i138nb-043, i138nb-044. Right-on-138n-not-right-on-138nb: none. Wrong on
either arm: none. Question-wrote ids (both arms, statement turns):
i138nb-067, i138nb-068, i138nb-069, i138nb-070. Driver fidelity: the
138n arm reproduces the panel's base138n.jsonl 70/70 on question
replies, setup replies and question_wrote flags.

M2 (1, category label138nb): 221/D11.

M3 probes (18, all category label138nb: the 138nb reply is exactly the
138n reply plus the label; events and stored triples identical):
p3-dialogs:d04:t02, p3-dialogs:d04:t05, p3-dialogs:d12:t04,
p3c-restart2:d01:t04, p3c-restart2:d01:t05, v-dialogs:d00:t05,
v-dialogs:d01:t04, v-dialogs:d05:t02, v-dialogs:d05:t04,
v-dialogs:d05:t05, v-dialogs:d05:t06, v-dialogs:d05:t07,
v-dialogs:d06:t08, v-dialogs:d10:t07, v-dialogs:d12:t04,
v-dialogs:d13:t06, v-supp:d00:t05, v-supp:d01:t05. No 226 "Who told you
that?" source-line change anywhere (every probe source reply
byte-identical).

M3 rt136 (16, vs 138j labels; every row byte-identical to 138n's saved
row): C019–C031 new WRONG-WRITE (allowed: inherited 138n registered
behaviour), C076/C079/C115 reply-only.

M6 gained right on 138nb (4; each a 138n loop190-reverse subject row
that becomes right with the label): p221-060#1, p221-063#1, p221-064#1,
p221-069#1. New wrong: none. Lost: none.

## Misses: none

0 unpredicted moves, 0 predicted-but-wrong, 0 predicted-but-not-moved,
0 new wrong on either blind panel, 0 question writes from questions, 0
ghost answers, 0 failed duplicate checks, 0 write changes.

## Deviations and notes

1. D1 (driver-only bug, reported with diff, sealed file NOT changed, no
   re-seal, no re-run): `scripts/claude_138nb_m1.py`'s `stored()`
   serialises notebook triples as character lists
   (`list(map(list, map(str, x)))` applies `list()` to each string)
   instead of `[subject, relation, value]` string triples. Effect, fully
   contained: the rows files' `stored_after_setup_actual` /
   `stored_after_question_actual` fields are malformed on both arms, so
   the sealed scorer's teach_control "right" reads 0/4 on both arms
   (the writer's base rows read 4/4). No M1 bar uses those fields: 0
   wrong, abstain checks and forward checks are reply-based; the
   teach_control bar is byte-identity of replies (4/4 verified); the
   question-wrote flags match the writer's base rows 70/70; the 138n
   arm's replies reproduce the base rows 70/70. Diff (one line):
   `return sorted(list(map(list, map(str, x))) for x in
   L90.notebook_triples(nb))` should be `return sorted([list(map(str,
   x))] ...)` over triples — stated here only, file untouched.
2. Before the seal, the panel SPEC
   (`handoff/kit/briefs/invpanel138nb-spec.txt`, origin/main) was read
   for its row-format fields only, to write the M1 arm runner. No panel
   item was seen (the panel did not exist yet); the build was already
   fixed and was not tuned on the spec.
3. M1/M6 runner rows, logs and score stdout hold item text and stayed
   outside the repo (/tmp); only ids-and-counts files were copied into
   `artifacts/claude-merge138nb-20260923/m1/` and `/m6/`.
4. M6 context, not a bar: 138n scores 80 right here vs 79 in the
   director's cloud re-run (full router here vs stubbed router there).
   Bars compare 138nb against 138n in the same run only.
5. The registered M2–M5 run waited on shared-Mac load via the driver's
   waitload gate (total 1443 s, one step at a time); disk stayed above
   14 GB free throughout.

## What it means (plain English)

- 138nb does the one thing it was built to do: backwards answers that
  used to come back correct but unlabeled now say they were worked out
  backwards (M1: 36 → 65 right with 0 wrong; M6: 80 → 84 right with 0
  wrong, gaining exactly the 4 diagnosed rows).
- Nothing else moved: 719 of 720 dev cases, all frozen suites, all
  restart/verifier dialogs (except the 18 + 1 predicted label-only
  changes), sleep, bench and latency are the same as 138n within the
  bars, with zero new wrong answers and zero new writes anywhere.

## What it doesn't mean

- It does not mean 138n's recorded FAIL is rewritten: that FAIL stays
  on the record with its diagnosis note.
- It does not mean teaches changed: statements store exactly what 138n
  stores (0 write changes on every mark).
- It does not mean abstains changed: every no-match / unknown reply is
  byte-identical (the label never lands on an abstain).
- A PASS here claims only what the bars say: the label lands exactly
  where predicted, and nowhere else.
