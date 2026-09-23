# Merge 138n: results (finishing run 2026-09-22)

## Verdict: FAIL (on M7 tablepanel221 only; M1–M6 all PASS)

138n keeps every piece's behaviour on the sealed dev/case files (M1), the frozen
suites (M2), sleep smoke (M3), bench stability (M4), latency (M5) and restart /
verifier dialogs (M6) exactly as predicted. On the blind panels (M7), five of
six panels pass, but tablepanel221 fails its bars: 138n gives a wrong value on
3 items where 221's own registered agent gave none (2 of the 3 were right on
the registered arm). Per the brief, PASS needs all of M1–M7, so the merge is
FAIL with one diagnosis note (below). No panel was re-run; each ran once.

## Marks table (integer counts)

| Mark | Result | Counts |
|---|---|---|
| M1 dev/case vs own arm (720 cases) | PASS | moved vs own 222; unpredicted 0; predicted-ok 222; predicted-wrong 0; predicted-not-moved 0; own arm reproduces sealed rows 720/720 |
| M2 frozen suites vs 138m | PASS | sessions152 moves 1 (fixed 1); bench moves 0; marks123 moves 0; rt136 moves 16 (new WRONG-WRITE 13, reply-only 3); rt136 direct-vs-138m moved 1 ([C115]) of 145 rows; rt143-nogate moves 18, bad 0; verdict flips 5 (P1 P2 Q1 Q2 MISSED->OK, S5 OK->WRONG-ANSWER) |
| M3 sleep smoke | PASS | differing fields 4 (.agent .config .label .seconds); bad 0 |
| M4 bench x3 identical | PASS | identical files 4/4 |
| M5 latency | PASS | median 138m 1.709 ms, median 138n 2.026 ms, delta +0.317 ms (bar <= +5 ms); n 624/624 |
| M6 restart + verifier | PASS | reply changes 5 (all predicted); write changes 0; unpredicted 0; ghost answers 0; bad writes 0; failed duplicate checks 0; fresh-138m-vs-saved-138m diffs 0 |
| M7 blind panels | FAIL | 5/6 panels pass; tablepanel221 fails (lost_to_wrong 2, new_wrong 3, question writes 0, new wrong writes 0) |
| 239 conversation panel | RUN (not a mark, never graded) | 244 turns; 58 changed vs 138m (39 reply, 31 stored-after, 26 stored-before) |

M1 predicted moves per piece (all seen exactly as predicted): 221: 7, 221b: 27,
221c: 15, 229: 26, 237: 2, 232c: 13, 232c-parity: 129, 236: 3; total 222.

## M7 table per panel (right / wrong counts; 138n vs piece's registered arm vs 138m)

| Panel | n | Registered right/wrong | 138n right/wrong | 138m right/wrong | Bars | Result |
|---|---|---|---|---|---|---|
| tablepanel221 | 91 | 66 / 0 | 77 / 3 | 29 / 0 | lost_to_wrong 2, new_wrong 3, question writes 0, new wrong writes 0 | FAIL |
| tablepanel221b | 120 | 54 / 0 | 85 / 0 | 49 / 0 | all 0 | PASS |
| teachpanel229 | 100 | 26 / 7 | 34 / 6 | 18 / 4 | lost_to_wrong 0, new_wrong 0, question writes 0, new wrong writes 0 | PASS |
| namepanel232c | 84 | 80 / 0 | 80 / 0 | 44 / 0 | all 0 | PASS |
| firstnamepanel236 | 60 | 60 / 0 | 60 / 0 | 20 / 0 | all 0 | PASS |
| aliaspanel237 | 80 | 65 / 1 | 68 / 1 | 31 / 1 | lost_to_wrong 0, new_wrong 0, question writes 0 | PASS |

(For 229, "wrong" is the scorer's wrong-save flag; for 232c it is
wrong/trap/other writes; definitions per PASSMARKS. 237's single wrong item on
138n is the same item that is wrong on the registered arm.)

## Every moved M7 item, by id and category (no item text)

tablepanel221 (the failing panel):
- New wrong values on 138n (3): p221-059#2 (category: inverse; was RIGHT on
  registered arm), p221-070#2 (category: inverse; was RIGHT on registered arm),
  p221-066#2 (category: inverse; was a miss, not wrong, on registered arm).
  On 138m all three are misses (not right, not wrong).
- Right on registered arm, miss (not right, not wrong) on 138n (8, not a bar,
  reported): p221-060#1, p221-063#1, p221-064#1, p221-069#1 (category: inverse),
  p221-087#1, p221-089#1, p221-090#1, p221-091#1 (category: self).
- Gained on 138n (not right on registered arm, right on 138n; 21):
  p221-009#1, p221-010#1, p221-011#1, p221-013#1, p221-018#1, p221-021#1,
  p221-022#1, p221-023#1, p221-025#1, p221-035#1, p221-037#1, p221-039#1,
  p221-040#1, p221-041#1, p221-048#1, p221-052#1, p221-053#1 (category: verb 5,
  when 8, alias 5, of_form 3 across the 21), p221-012#2, p221-026#2,
  p221-027#2, p221-028#2 (same categories).
- Question writes on 138n: 0. Id-set mismatch: none.

tablepanel221b (PASS): gained 31 (miss->right), no other moves: q221b-003,
q221b-016, q221b-017, q221b-018, q221b-019, q221b-021, q221b-024, q221b-025,
q221b-028, q221b-032, q221b-033, q221b-036, q221b-044, q221b-046, q221b-049,
q221b-050, q221b-051, q221b-053, q221b-056, q221b-057, q221b-058, q221b-059,
q221b-061, q221b-062, q221b-063, q221b-064, q221b-068, q221b-070, q221b-074,
q221b-092, q221b-097.

teachpanel229 (PASS): gained 8 (miss->right): t229-027, t229-028, t229-029,
t229-031, t229-032, t229-035, t229-036, t229-066. 138n wrong count 6 is a
subset of the registered arm's 7 wrong items (0 new).

namepanel232c (PASS): 0 moves of any kind (80/80 right on both arms).

firstnamepanel236 (PASS): 0 moves of any kind (60/60 right on both arms).

aliaspanel237 (PASS): gained 3 (miss->right): a237-032, a237-034, a237-043.
The 1 wrong item on 138n is the registered arm's own wrong item (0 new).

## M2 rt136: the 13 rows in class "new WRONG-WRITE"

Each row below is listed by id with its predicted justification from
predicted_moves138n.json (allowed_bad.rt136). Labels are scored against 138j;
the "new" is relative to 138j labels, not relative to 138m.

- C019: inherited 222 exception, identical to 138m's saved row (138m's own M2
  allowed it). NOT a real new wrong write on 138n; it is 138m's registered
  behaviour.
- C020: same justification as C019. NOT new on 138n; 138m's behaviour.
- C021: same justification as C019. NOT new on 138n; 138m's behaviour.
- C022: same justification as C019. NOT new on 138n; 138m's behaviour.
- C023: same justification as C019. NOT new on 138n; 138m's behaviour.
- C024: same justification as C019. NOT new on 138n; 138m's behaviour.
- C025: same justification as C019. NOT new on 138n; 138m's behaviour.
- C026: same justification as C019. NOT new on 138n; 138m's behaviour.
- C027: same justification as C019. NOT new on 138n; 138m's behaviour.
- C028: same justification as C019. NOT new on 138n; 138m's behaviour.
- C029: same justification as C019. NOT new on 138n; 138m's behaviour.
- C030: same justification as C019. NOT new on 138n; 138m's behaviour.
- C031: same justification as C019. NOT new on 138n; 138m's behaviour.

Proof none is new on 138n: the direct row compare of 138n against 138m's saved
run/sd136/rt136-rows.json shows moved == [C115] over 145 rows, so C019-C031
(and C076, C079) are byte-for-byte 138m's rows. Saying it plainly: all 13 were
already "wrong writes" on 138m before this merge; 138n adds zero new ones.

## Deviations and notes

1. The sealed driver's last line (`python3 scripts/claude_138n_m7.py compare`)
   fails on this Mac because /usr/local/bin/python3 is a broken x86 binary
   ("Bad CPU type in executable"; this failure mode is documented in
   OPUS-RULES). All six panels had already run (status OK each). The identical
   compare command was run once with the uv prefix, and the script's final
   copy steps (m7-compare.json, m7-status.txt into
   artifacts/claude-merge138n-20260922/m7/) were completed by hand. No sealed
   file was changed; no panel was re-run. This is a driver-environment issue,
   not a behaviour finding.
2. tablepanel221's SEAL.sha256.txt lists bare filenames, so `shasum -c` from
   the repo root reports them missing; checked from inside the panel directory
   instead: both lines OK. Every other panel seal checks OK from the repo
   root, and the 138n seal checks 15/15 OK.
3. Disclosure: to give the required category-level diagnosis for the failing
   panel, only scorer-output flags (right/wrong booleans, family labels, turn
   indexes) were read for the moved ids. No panel item text is quoted anywhere
   in this file or the ledger line.
4. The 239 panel was run with the runner only; nothing about it was graded.
5. design/v3/30-modes/138n-merge-opus.md already exists (sealed), so no design
   note was written.

## What it means (plain English)

- 138n learned everything it was supposed to learn: it answers far more
  reading questions than 138m (for example 77 vs 29 right on tablepanel221,
  85 vs 49 on tablepanel221b, 80 vs 44 on namepanel232c) while matching every
  sealed expectation on the dev cases, frozen suites, restarts and verifier
  dialogs.
- But on one blind question set, the merged agent guesses a wrong answer in 3
  places where the single-purpose 221 agent either answered correctly (2
  places) or stayed silent (1 place). All 3 are "work backwards from the
  answer" questions, and 4 more of that kind plus 4 "about the agent itself"
  questions went from right to silent. That pattern points to the merge's
  question-handling order: some other layer now claims those turns before the
  inverse-question step can do its job properly.

## What it doesn't mean

- It does not mean 138n writes bad facts: 0 question writes and 0 new wrong
  writes on every panel.
- It does not mean the frozen suites regressed: every WRONG-WRITE there is an
  old 138m row, proven identical, not something the merge introduced.
- It does not mean the other five reading pieces broke: 221b, 229, 232c, 236
  and 237 all pass with zero new wrong answers.
- A FAIL here is a report, not a disaster: it says exactly where the merge
  falls short (3 wrong backwards-questions) so the next step can fix that one
  interaction.
