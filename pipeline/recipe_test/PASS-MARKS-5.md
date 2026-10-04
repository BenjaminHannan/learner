# Round 5: independently written layouts + more table variety (2026-10-04, fast lane). Marks fixed before training

Base = round-4 COMP recipe (copy path + composed wording + contextual reader, composed two-step frames, real modules, fresh weights, 4 loops, 3000 x 16, seeds 0-5).
Two new things, kept apart:

**A. Independent eval ("blind" set, no model change).** `eval_layouts_r5_blind.json`: 12 layout families (4 table/ledger/scoreboard/receipt, 2 question-first, 2 first-person, chat, instruction, report, riddle/diary) x 4 op pairs x 3 wordings,
written by a separate Claude worker that was given only the task description (it did not read the repo or any of my training or test frames; I did not edit its texts). It is still a Claude model, not a person or another vendor; a
GPT/Astra-written set would be more independent (prompt: reviews/). 192 questions from it: 12 families x 4 op pairs x (2 unseen + 2 seen finals). Never used for any training choice before this round. Any composed training frame sharing a
sentence or word 6-gram with a blind frame or an old-eval frame is dropped (0 left sharing, checked). Operand triples of both eval sets are excluded from training.
**B. One change: extra table-style training variety (TABV).** COMP's frames plus 6,000 composed table-style frames (`gen_two_v.tab_extra`: one-line and multi-line rows, 7 separators, +/- and word row labels, 8 headers, 7 asks).
Caution, stated up front: I wrote TABV after reading the blind file, so I knew its family *kinds* (ledger, spreadsheet, receipt, scoreboard) and saw its wording; the frames were composed from my own parts and the 6-gram filter holds, but this is not a clean blind test of TABV. The old eval (round 3/4 frames) is the cleaner check for TABV.

Arms (6 paired seeds 0-5, RT_ROUND=2, each evaluated on BOTH the old 192 and the blind 192): COMP (re-run, because the round-4 runs were not scored on the blind set and the frame filter now also drops overlaps with it) and TABV.

## Marks
A (COMP on blind, chain all 192): HOLDS if mean >= 70; PARTLY if 50 to 70; OWN-WORDING-ONLY if < 50. (Round 4 reached 81.4 on the self-written set; the COMP re-run on the old set must land within 75 to 88 or the re-run is declared different from round 4.)
B (TABV minus COMP, paired over 6 seeds, t = 2.571): HEADLINE = chain, all 192 blind questions. PASS: mean gain >= +5 AND interval lower bound > 0 AND old-eval chain gain >= -3. FAILS: blind gain < +2. Otherwise partial, no claim.
Reported with no mark: table-families-only chain on blind (64 questions) and old-eval table chain; per-family chain; call 1 / call 2 given call 1; seed SD.
Gate: train fit (last 192 two-step training items, chain) >= 70% for both arms, else UNDERFIT-VOID.
Wrong-if: TABV gain <= 0 on blind tables means table wording variety is not what limits tables (suspects: operands in columns, 49-token cap, loop depth).
Budget cap ~$6, 5090s (~$0.45/h), 12 runs; credit must stay >= $1 (shared with other threads).

## Addendum (about 14:45 UTC, before any run finished): first launch of 6 boxes was destroyed within ~2 minutes (no result read)
The CPU smoke test found that two of my new table frames broke the real registry check (a digit in a row label, "row 1", and "-{y}" parsed as a negative number). Fixed: row labels without digits, "-/+" row forms replaced by "down/up", frames with any digit dropped.
All 12,384 sampled training and eval rows now pass the registry check. Marks above unchanged. Cost of the aborted launch about $0.05.
