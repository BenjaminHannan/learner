# Exp 252c PASSMARKS (merge 252b + 258 + 259): written before the seal

Agent: scripts/claude_loop252c_agent.py + artifacts/claude-merge252c-20260922/loop252c-config.json.
Inner ears: Comment258 (258) > Merge252c (glue, scripts/claude_fix252c_merge.py) > Boundary259 (259) > Correct252 (252/252b).
Overlap analysis: design/v3/30-modes/252c-merge-opus.md.
Driver: scripts/claude_merge252c_runall.sh (stages: pre = M2, M3, M5–M8; then m4; then m1).
Scorer: scripts/claude_merge252c_score.py (m1–m4). Also used read-only:
- claude_corr252b_score.py dev (M2 information);
- claude_bound259_score.py suites / smoke (M5, M6);
- claude_comment258_score.py suites (M5, second check);
- claude_corr252_m6check.py (M7, M8).
All scorers run under uv Python 3.12.
Verdict: PASS only if M1–M8 all pass.

## The glue (the only new behaviour; it acts only on turns 258 shortened)
1. On the 154f route, 258's cut point counts as 259's boundary. When 252's clause-end words ("anymore", "now", ...) are dropped from V, what is left must equal a stored value while V itself does not. That value is then removed with 252's "OK, I removed V as S's R." (This fixes c252-022.)
2. When the denied value is a stored value plus more words, the reply is 259's rule-3 wording "I have S's R as V, not V W, so I didn't change anything." (no write). This applies on the 252 and 154f routes.

## Definitions declared before the seal
- **False reply** (M2, M3, M4; the scorer's false_reply):
  - A reply "... don't have X as S's R ..." is false when (S, R, headc(X)) is stored after the turn.
  - headc(X) is X up to its first clause boundary, with 252's clause-end words dropped.
  - So "Tobin anymore" and "Brimwell, that's outdated" count as Tobin and Brimwell. "Garrow Hall" and "Garrow-on-Hythe" are different values from "Garrow".
  - Any other "don't have" reply uses the loose rule: V, S and R all appear in it.
  - Why: the loose rule alone flags "I don't have Garrow Hall as Nell's employer" (259's own dev item v259-023, no tail, predicted right by 259). The loose count is reported as information.
- **M3 junk** uses the corrtail258 rule. The exception is dev259's "keep" items: 259's dev schema gives them no expect_store, so they are checked by identity to the own arm instead.
- **M1** is scored with the corrtail258 spec rules exactly (259's score_item and schema, imported read-only).
- **M4 rule** (sealed; the corrpanel252 items are never read; the scorer prints ids and classes only). For each row, compare against 252b's registered row (a), 258's (e) and 259's (n):
  - Neither 258 nor 259 moved the row: 252c must equal a.
  - Only 259 moved it: 252c must equal n.
  - Only 258 moved it: 252c must equal e. The one alternative allowed: e's reply is "I don't have V as S's R[...]" and 252c either (a) cleanly removes exactly (S, *, headc(V)) with an "OK, I removed" reply, where headc(V) differs from V, or (b) gives the "I have S's R as ..." wording with stores unchanged.
  - Both moved it: 252c must cleanly remove exactly one triple (S, *, headc(V)), with S and V from 252b's "I don't have V as S's R" reply. For c252-022 the reply must also start "OK, I removed Tobin as " and the removed value must be Tobin.
  - Also required: 0 new wrong values, 0 new junk vs 252b, and 0 false replies on 252c.

## Marks, bars, predictions
| Mark | Bar (from the brief) | Prediction |
|---|---|---|
| M1 corrtail258 (80, known set, once after the seal) | every item right on 258 or 259 right on 252c; 0 false claims /80; 0 junk /80; no wrong value on 252c where 258 or 259 had none; keep 8/8 + control 16/16 right and byte-identical to base252b.jsonl; question_tail 6/6; unstored_tail 6/6 | **FAIL on one bar**: t258-026 has a wrong value (Drumlow still stored and said), where 259 had none only because it wrote the junk value "stale". All other bars pass. Counts: 54/80 right (252b 39, 258 53, 259 43); that_denial 7, that_correction 3, pure_denial_that 6, other_tail_denial 2, keep 8, question_tail 6, unstored_tail 6, control 16; false claims 0; junk 0; wrong values 26 |
| M2 dev252b (vs 252b, same session) | 0 junk; 0 false replies; 0 wrong removals; 0 question writes; controls identical except ms; moves exactly predicted, each with its exact record | PASS: 31 moves (below) |
| M3 dev258, dev259 | every item = own arm's record except the predicted ids (records sealed in pred-m3-dev258.jsonl / pred-m3-dev259.jsonl); 0 false replies; 0 junk | **FAIL on junk only**: d258-037 and v259-008 (", sadly" is stored as the value by 252's two-clause path, the same in both own arms and in 252b). Records: all as predicted. False replies 0 |
| M4 corrpanel252 (TEST-ONLY, once after the seal) | moves exactly as the sealed rule; 0 new wrong, 0 new junk, 0 false replies | PASS: the only move is c252-022, a removal of Tobin as Quenby's manager ("OK, I removed Tobin as Quenby's manager."), class "both". Every other row is identical to 252b |
| M5 suites rt136, rt143, sessions152, bench | move list = 252b's; 0 new WRONG / WRONG-WRITE / junk / lost OK | PASS: rt136 4, sessions152 1, rt143 0, bench 0; rows equal to 252b's except seconds; GATE clean |
| M6 sleep smoke | identical to smoke-252b.json except labels, paths, timing | PASS (0 differences) |
| M7 restart dialogs (v-dialogs, v-supp) | 0 ghosts; 0 failed duplicate checks; replies = 252b's except predicted moves | PASS: 0 / 0 / 0 moves (18 rows) |
| M8 latency | median added per turn ≤ +5 ms vs 252b, same session | PASS (pilot −0.05 ms) |

**Predicted registered verdict: FAIL** (M1 on t258-026; M3 on d258-037 and v259-008). These are known gaps, and the merge itself does not cause them. Details are in the design note.

## Predicted moves, by id

**M2 dev252b.** 31 moved ids = 258's 29 ∪ 259's 6. The overlap is b252-001, 010, 013, 014: 258 strips first, so 259 sees no boundary, and the record is 258's.
- 258's registered record (artifacts/claude-comment258-20260922/run/dev252b-258.jsonl): b252-001, 002, 004, 005, 006, 007, 008, 010, 011, 013, 014, 016, 017, 018, 019, 020, 021, 023, 024, 026, 027, 029, 030, 031, 032, 033, 035, 036, 037.
- 259's registered record (artifacts/claude-boundary259-20260922/run/dev252b-259.jsonl): b252-003, b252-015 ("..., it's wrong now" is not a 258 opener).

**M3 dev258** (own arm = 258's registered dev258-258.jsonl). Exceptions, where 259 acts because 258 does not:
- d258-003 "(that changed in spring)": 259 rule 3a gives "OK, I removed Harlan as Quenna's boss."
- d258-039 ", not anymore": 259's boundary gives "OK, I removed Treloar as Mawgan's boss."
- Both records are sealed in pred-m3-dev258.jsonl and equal the same-session 259 arm.

**M3 dev259** (own arm = 259's registered dev259-259.jsonl). 12 exceptions, where 258 strips first; each equals the same-session 258 arm (sealed in pred-m3-dev259.jsonl):
- **v259-010, 011, 012:** 258's short form is readable, so Pellam is removed. (259 got "I cannot predict." / "couldn't save".)
- **v259-015, 016, 063:** 154f removes Tolly with "OK, Rune's boss is not Tolly. I don't have another boss for Rune." (only the wording differs from 259).
- **v259-029:** "I don't have Tollyson as Rune's boss." (no write).
- **v259-035:** "I don't have Pimm as Rune's boss." (154f wording).
- **v259-037:** "I don't have anything saved about Corvin, ...".
- **v259-038:** "I don't have Garrow as Nell's city, ..." (Nell's city is not stored; honest).
- **v259-058:** "That's wrong, that's old news." now removes Garrow instead of writing "old news".
- **v259-059:** "Which fact is wrong? ..." with no junk write.
- **v259-024, 027 and 065 are NOT exceptions**: the glue keeps 259's "I have ... as Garrow, not Garrow Hall" wording.

**M4:** only c252-022 (removal of Tobin).
**M1:** 24 rows move vs 252b. Each is 258's registered row where 258 moved it, or 259's where only 259 moved it (t258-035). This is reported as information ("not_as_predicted", predicted empty). The glue is predicted not to fire on any M1 item.
- Moves: t258-001, 002, 003, 008, 009, 010, 011, 013, 015, 016, 019, 023, 024, 025, 026, 027, 029, 030, 031, 033, 034, 035, 059, 064.
- Newly right vs 252b: 001, 002, 003, 008, 009, 010, 011, 013, 019, 024, 025, 031, 033, 034, 035.

## Deviations / interpretations declared before the seal
- The glue is new behaviour beyond "import both pieces". It is needed because 258's strip removes the boundary that 259 relies on (c252-022 and the near-miss wording). It acts only on turns that 258 shortened.
- The false-reply definition above is my reading of the brief's wording. The loose count is reported too.
- The M3 dev259 keep items are exempt from the junk rule (schema), as stated above.
- M3's "other arm" rows (259 on dev258, 258 on dev259) are made in the same session; the sealed pred files hold the predicted records.
- Pilots: dev252b, dev258, dev259, suites, smoke, restart dialogs and latency were piloted, all with uv Python 3.12. corrtail258 was NOT piloted on 252c: its prediction comes from 258's and 259's registered rows. corrpanel252 was never opened. Only the M4 scorer was sanity-tested on 258's, 259's and 252b's own registered rows (ids and classes printed only).
