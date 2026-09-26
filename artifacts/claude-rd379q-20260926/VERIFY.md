# rd-379q VERIFY (Trustworthy notes thread, 2026-09-26 16:33 UTC): FAIL confirmed by a blind recount (proved wrong)

Recounted from origin/builder-outbox:artifacts/claude-rd379q-20260926/notes_recall.json ("B" = question notes) with a
script that reads only the summary counts, before reading RESULTS.md. Fused mode, categories 1-4, n = 759.

| | A heard only | Q heard + question notes | diff | bar | |
|---|---|---|---|---|---|
| Q1 any@10 | 496 (65.3%) | 431 (56.8%) | -8.6 | >= +5 | FAIL |
| Q3 anyT@10 | 496 (65.3%) | 437 (57.6%) | -7.8 | >= +5 | FAIL |
| Q2 per category any@10 | 77 / 125 / 16 / 278 | 67 / 99 / 13 / 252 | -7.1 / -16.7 / -6.8 / -6.2 | >= -3 | FAIL |

Proved-wrong clause (Q <= A + 1): TRUE for any@10 and anyT@10. Sanity: store A equals rd-378L's A exactly (checked
key by key). 8,265 questions over 2,760 turns (3.0 per turn), 1 turn with none, 0 unparsed.
Report only on store v3: A 520, Q any@10 468 (-6.9), anyT@10 482 (-5.0). Registered verdict: FAIL; it stays a FAIL.

Likely why (suggested, not shown): the made-up smoke rows show the plain 1B writes generic questions in the second
person ("How did you feel about the new environment?") and repeats one question across turns, so 3 loose questions per
turn crowd real lines out of the top 10 (mean distinct turns shown @10: 9.03 vs 10.00).

Next, by the rule fixed before either result (PASSMARKS.md): question notes are dropped; rd-378L passed, so the
fact-note line continues (pointer step into the store, then the cut-only writer, 371c step 4b).
Time notes: PASSMARKS.md "~14:10" and PASSMARKS-B.md "~14:30" were estimates; their commits (db5d59246 14:07:47Z,
1ff783b75 14:23:03Z) are the registration times, both before any result.
