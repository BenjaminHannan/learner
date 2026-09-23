# Exp 280m — RESULTS (registered)

## Result: FAIL on M1's 100% bar only (87/90 turns agree)

M2, M3 and M4 all pass exactly as predicted. The 3 misses are one shape with one diagnosis (below):
on each, 280m is byte-identical to the 280b piece arm (reply, write count and store), differing only from the
predicted 260 owner. No new behaviour, no writes, no overlaps, no unsupported-claim scan hits.

## Marks (integer counts)

| mark | bar | got |
|---|---|---|
| M1 agreement 280m vs owner arm (90 turns, once per arm) | 90/90 | 87/90 FAIL |
| M1 ability agree (owner 280b) | 25/25 | 25/25 |
| M1 teach agree (owner 260) | 8/8 | 8/8 |
| M1 called agree (owner 281) | 12/12 | 12/12 |
| M1 smalltalk agree (owner 282b) | 25/25 | 25/25 |
| M1 control agree (owner 260) | 10/10 | 10/10 |
| M1 mixed agree (owner by trigger rule) | 10/10 | 7/10 |
| M1 question turns with writes on 280m | 0 | 0 |
| M1 smalltalk turns with writes on 280m | 0 | 0 |
| M1 trigger overlaps (2+ triggers, one turn) | 0 | 0 |
| M1 old-sheet scan hits on 280m replies | 0 | 0 |
| M2 sessions152 moves vs 260 | exactly 3 named | 3 (the 3 named) |
| M2 bench / rt136 / rt143 moves vs 260 | 0 / 0 / 0 | 0 / 0 / 0 |
| M2 verifier probes vs 260 (vp 98 / supp 12) | N06+E04 / 0 | N06+E04 / 0 |
| M2 GATE vs 260's | identical | identical |
| M3 wellbeing fitting 280m vs 260 | >= 260 | 17/20 vs 16/20 PASS |
| M3 other items 280m == 260 | 36/36 | 36/36 |
| M3 writes / setup / store diffs | 0 / 0 / 0 | 0 / 0 / 0 |
| M4 store diffs 280m vs 260 (suites + panel) | 0 | 0 |

Report-only absolute rates (CAN-line substring; the line also occurs in 260's old sheet, so these are not
CAN280-exact counts): ability 280m 17/25 vs 260 9/25; mixed 280m 3/10 vs 260 3/10; all other categories 0/0.

## Every move

- Panel misses (all turn 0 of their dialogs, ev 0 on both arms, stores identical on all arms):
  x01#0, x03#0, x05#0 (all category mixed, predicted owner 260). On each, 280m reply == 280b reply ==
  sealed CAN280 exactly (sha e9b8293a7548), 260 reply is a 273-char non-CAN reply (same shape all 3 ids).
- st234 move: s234-014 (wellbeing miss on 260 -> fitting hit on 280m, 0 writes; the same item 282 moved).
- Suite moves: S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9 (reply-only -> CAN280,
  UNHELPFUL->UNHELPFUL, 0 writes). Probes: N06 (name-of + stored -> stored answer), E04 (whats-up + empty
  store -> head greeting reply).
- No other reply, write-count or store differences anywhere (suites, probes, panel, st234).

## The one diagnosis (the 3 misses)

The 3 mixed turns lead with smalltalk filler openers and continue with ability wording, with no "?".
The turn-text pre-triggers all say no-fire (verified: 281 no, 280/280b no, 282/282b no), so the pre-seal
ownership rule predicted 260. But the 260 head answers these turns with a reply carrying the old false-sheet
signature, and the sealed 280 belt-and-braces post-guard (reply-only, 0 writes) replaces it with CAN280.
That post-guard lives inside the 280b arm too, so 280b serves CAN280 and 280m == 280b exactly. The join adds
nothing: every one of the 90 turns equals one of the piece arms (87 the predicted owner, 3 the 280b arm).
The ownership rule modelled only turn-text triggers and not the reply-dependent post-guard — that modelling
gap is the whole FAIL. M1's mechanical 100% bar counts it, so the verdict is FAIL.

## Deviations

- D1: frozen suites + verifier probes were measured as the pre-seal pilot only (the brief's step 2); they
  were not re-run post-seal. The sealed `scripts/claude_280m_runall.sh` + `scripts/claude_join280m_regscore.py`
  reproduce the comparison.
- D2: pre-seal driver fix (disclosed): the scorer's CAN-line marker had an uppercase "I" while replies are
  lowercased before matching, so the mock run first reported 0 CAN hits; fixed before the seal, mock
  re-run 11/11 PASS. Sealed files include the fix; seal 12/12 OK before and after the registered runs.
- D3: the registered panel ran at 1-min load 47 (rule: wait while above 60); an earlier check read 80 and
  the run waited ~3 minutes first. Disk free 12 GB throughout (rule: stop under 3 GB).
- No post-seal change to any sealed file (seal re-verified 12/12 OK after the runs). No sealed script broke.

## Reply files for the director's claim check

- `artifacts/claude-join280m-20260923/run/panel-280m.json` (280m replies, all 90 turns)
- `artifacts/claude-join280m-20260923/run/panel-260.json`, `panel-280b.json`, `panel-281.json`,
  `panel-282b.json` (owner arms), `probes-*.json` (per-arm canonical probes)
- `artifacts/claude-join280m-20260923/run/st234-280m.json`, `st234-260.json`

## What it means (plain high-school English)

- The join works as built: on 87 of 90 new blind turns it answers exactly like the piece that owns that
  kind of turn, and on the other 3 it answers exactly like the ability piece. It never writes notes on
  questions or chit-chat, never mixes up its triggers, and never makes a claim the old false sheet made.
- Small talk got better without breaking anything: easy greetings that confused the base now get friendly
  replies, and tricky "what is it called" questions get answered from notes.

## What it doesn't mean

- It does not mean the join is approved: the deal was 90 out of 90 exact matches and it got 87, so the
  grade is FAIL, even though the 3 misses are the ability piece doing its sealed job.
- It does not mean there is new behaviour: every single reply equals one of the already-built pieces.
- It does not mean the suite numbers are registered post-seal runs: they are pre-seal pilot runs, exactly
  matching the prediction, with the sealed scripts ready to repeat them.
