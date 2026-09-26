# rd-378L VERIFY (Trustworthy notes thread, 2026-09-26 16:33 UTC): PASS confirmed by a blind recount

Recounted from origin/builder-outbox:artifacts/claude-rd378L-20260926/notes_recall.json (sha256 074225fb...) with a
script that reads only the summary counts, before reading RESULTS.md. Fused mode, questions of categories 1-4, n = 759.

| | A heard only | B heard + fact notes | diff | bar | |
|---|---|---|---|---|---|
| L1 any@10 | 496 (65.3%) | 583 (76.8%) | +11.5 | >= +5 | PASS |
| L3 anyT@10 (same 10-turn budget) | 496 (65.3%) | 577 (76.0%) | +10.7 | >= +5 | PASS |
| L2 cat 1 any@10 | 77/141 | 102/141 | +17.7 | >= -3 | PASS |
| L2 cat 2 | 125/156 | 134/156 | +5.8 | >= -3 | PASS |
| L2 cat 3 | 16/44 | 24/44 | +18.2 | >= -3 | PASS |
| L2 cat 4 | 278/418 | 323/418 | +10.8 | >= -3 | PASS |

Proved-wrong clause (B <= A + 1): false for any@10 and anyT@10. Mean turns shown @10: A 10.00, B 9.97, so the gain is
not from showing more turns. Report only: any@5 +9.9, any@20 +9.0, bm25 any@10 +10.0, all@10 +8.4 points.
Notes: 2,556 over 2,760 turns, 33 unparsed. Registered verdict: PASS. RESULTS.md's numbers match this recount.

Report only, the store 0.2c ships (v3 ranking, rd-379q addendum B, same notes file): A 520 (68.5%), B any@10 578
(76.2%, +7.6), anyT@10 581 (76.5%, +8.0); every category up (+4.5 to +10.6). The gain holds on the shipped ranking.

Writer: rebuilt on the rental from its adapter and hashed to dbcc8db5... (the registered writer), torch 2.11.0+cu128,
transformers 5.17.0, peft 0.21.0, RTX 5090 (rental 52770443, shared with rd-379q, ~$0.47). First try (rent-rd378L,
<= $0.69) wrote nothing (environment; addendum E). Thread spend so far ~$1.16 of $2.

Time notes: addendum D's "~13:45 UTC" was an estimate; its commit (698c9aefc) is the registration time. Both were
before any note or score.

What it means: the note writer's notes, used only as pointers to the raw chat lines, find the right line for 87 more
of 759 LoCoMo practice questions in the top 10 (65% to 77%), with the same number of chat lines shown. It does not say
the notes are true (rd-378 judged 31% unsupported); answers must still read only the raw lines the notes point to.
