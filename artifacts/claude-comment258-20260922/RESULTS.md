# Exp 258: trailing commentary clause on 252b denials and corrections. RESULTS

**Registered verdict: FAIL, on M1** (the blind corrtail258 panel). M2–M7 all PASS.

- Seal: `SEAL.sha256.txt`, made 2026-09-22 17:52 (9 files; `shasum -c` OK after all runs).
- Panel seal: `artifacts/claude-corrtail258-20260922/SEAL.sha256.txt` checked OK.
- Schema: OK.
- Every registered run was done once.

## Marks (mine = 258, next to 252b)

| Mark | Bar | 258 | 252b | Result |
|---|---|---|---|---|
| M1 that_denial | ≥10/12 | 7 | 0 | FAIL |
| M1 that_correction | ≥10/12 | 3 | 0 | FAIL |
| M1 pure_denial_that | ≥9/10 | 6 | 2 | FAIL |
| M1 junk writes over 80 | 0 | 0 | 2 | PASS |
| M1 wrong values in the 3 families | 0 | 18 | 31 | FAIL |
| M1 false claims in the 3 families | 0 | 0 | 4 | PASS |
| M1 other_tail_denial newly wrong | 0 | 0 | – | PASS (1/10 right on both arms) |
| M1 question_tail | 6/6 | 6 | 6 | PASS |
| M1 unstored_tail | 6/6 | 6 | 6 | PASS |
| M1 keep, byte-identical to base252b | 8/8 | 8 | 8 | PASS |
| M1 control, byte-identical to base252b | 16/16 | 16 | 16 | PASS |
| M2 dev252b: junk / wrong removals / question writes / control diffs | 0/0/0/0 | 0/0/0/0 | 252b had 1 junk (b252-035) | PASS |
| M2 dev252b moved ids as predicted | exact | 29/29, 0 unpredicted | – | PASS |
| M3 corrpanel252 moved ids / new wrong / new junk | predicted / 0 / 0 | c252-022 only (reply-only) / 0 / 0 | – | PASS |
| M4 suites moves equal to 252b's; 0 new bad | equal | equal (rt136 C071/C072/C073/C075, sessions152 S3-teachers-correction#6, reply-only); GATE clean | – | PASS |
| M5 sleep smoke differences | 0 | 0 | – | PASS |
| M6 ghosts / dup fails / reply moves | 0/0/0 | 0/0/0 (18 rows) | 0/0 | PASS |
| M7 added median | ≤ +5 ms | 2.47 ms against 2.24 ms (+0.23 ms) | – | PASS |

## Changed items

- **M1**, 23 items differ between the arms:
  - t258-001, 002, 003, 008, 009, 010, 011, 013, 015, 016, 019, 023, 024, 025, 026, 027, 029, 030, 031, 033, 034, 059, 064.
  - 16 became right: that_denial 001, 002, 003, 008, 009, 010, 011; that_correction 013, 019, 024; pure_denial_that 025, 031, 033, 034 (028 and 032 were already right).
  - None became worse on right/junk/wrong-value/false-claim.
  - 059 and 064 changed their reply only and stay right.
- **M2 dev252b.** 29 moved ids (listed in m2-moves.txt), exactly as predicted. b252-035 no longer writes "old news".
- **M3 corrpanel252.** c252-022 only. The reply is now "I don't have Tobin anymore as Quenby's manager."; the store is unchanged.
- **Reference, dev258.** 41 moved ids, exactly as predicted.

## Diagnosis (one note)

The clause removal itself works: 0 junk, 0 false claims and no family got worse. The panel fails for two other reasons.

**(a) 252b cannot act on most shortened turns.** A probe on 252b with my own names, in the same shapes as the failing items, gives:
- lowercase "x's dog isn't y." → "couldn't save";
- "My boss isn't Z." → "couldn't save";
- "X's cat is Fig, not Moss." → adds Fig and keeps Moss (a multi-valued relation);
- contextual corrections of USER facts → "Which fact should I change/is wrong?";
- "No, that was his old trade." → "No." → "I wasn't waiting for an answer.".

So most of the remaining misses (004–007, 012, 015–018, 021–023, 027, 029, 030) are 252b grammar gaps that removing the clause cannot fix.

**(b) The whole-turn gate is too strict in one case.** "X's city is Z, not Y, that's been wrong for ages." is not read as a correction while the clause is still attached (252's ", not W" test needs the tail to end there). The mixin therefore never shortens it, even though 252b handles the shortened form (t258-020).

**Not an opener:** "that one's" (t258-014).

## Deviations
- **Scoring interpreter.** The driver scripts called `python3`, which under bash is a broken x86 binary (/usr/local/bin/python3). Every scoring step in the sealed drivers failed. The agent runs themselves completed once each, as registered. The same sealed scorers were then run once on the saved rows with uv Python 3.12 (as in the pilots). Nothing was re-run, and no sealed file changed.
- Declared before the seal (see PASSMARKS): the extra dash boundaries, the fallback rule, tail-only brackets, and "..."/"which isn't" not handled.
- The diagnosis probe (252b on 5 own-name dialogs) was run after the verdict. It was used for the note only, not for tuning.

## What it means / doesn't mean
- **Means:**
  - Removing a trailing "that's ..." clause before 252b is safe. It adds no junk, no wrong removals and no false claims, keeps controls byte-identical and adds latency within noise.
  - It fixes the dev252b junk write (b252-035) and 16 of 34 panel items in the target families.
- **Doesn't mean:** tail denials are solved. On natural turns the bottleneck is now 252b's own grammar (lowercase names, first-person facts, multi-valued relations, bare "No." after a statement). Clause stripping cannot fix that.

## Files
- Code: scripts/claude_fix258_comment.py, scripts/claude_loop258_agent.py, artifacts/claude-comment258-20260922/loop258-config.json
- Dev and scoring: scripts/claude_comment258_devcases.py, artifacts/claude-comment258-20260922/dev258.jsonl, scripts/claude_comment258_score.py
- Drivers: scripts/claude_comment258_runall.sh, scripts/claude_comment258_m1.sh
- PASSMARKS.md, SEAL.sha256.txt
- run/ (rows, logs, m1-score.txt, m2-check.txt, m2-moves.txt, dev258-*.txt, m3-check.txt … m7-check.txt)
