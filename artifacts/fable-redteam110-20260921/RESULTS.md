# Exp 110 RESULTS — red team round 2 of the loop102 agent (Muse, 2026-09-22)

62 NEW cases (10 families), none re-using the 64 redteam98 cases. Every case
ran once through a REAL loop102 daemon subprocess via its mailbox
(`--daemon`, loop102-config.json). Sealed before the run: cases.json +
PASSMARKS.md (SEAL.sha256.txt verifies).

## Marks table (integer counts, every case reported, never averaged)

| family | cases | OK | BUG | HARNESS-ERROR |
|---|---|---|---|---|
| pronoun (P) | 6 | 6 | 0 | 0 |
| disagreeing teachers (T) | 6 | 6 | 0 | 0 |
| re-teach same value (R) | 6 | 5 | 1 (R4) | 0 |
| forget → re-teach (F) | 6 | 5 | 1 (F5) | 0 |
| never-taught (N) | 6 | 5 | 1 (N6) | 0 |
| long / run-on (L) | 6 | 6 | 0 | 0 |
| unicode / lookalike (U) | 6 | 6 | 0 | 0 |
| case-typo / shouting (M) | 6 | 5 | 1 (M5) | 0 |
| self-question in teach (S) | 6 | 4 | 2 (S3, S6) | 0 |
| daemon abuse (D) | 8 | 8 | 0 | 0 |
| TOTAL | 62 | 56 | 6 | 0 |

Severity as sealed: critical 1 (N6), high 1 (F5), medium 4 (R4, M5, S3, S6).
B1 PASS (62 verdicts sum to 62). B2 PASS (6 reproducers under repro/).
B3 PASS (table above). B4 PASS (82.8 s wall, bar < 30 min).

## The 6 BUGs: 2 genuine agent bugs, 4 expectation errors (verdicts stand)

1. F5 (high, GENUINE): "Please forget Mira city" clarifies and the stale
   value stands. Root cause in loop102 (`fable_loop102_agent.py` please-strip:
   `"forget" + t[m.end(1):]` drops the space → "forgetMira city" never matches
   the forget verb). The please-forget shape is unreachable end-to-end.
   Safe symptoms (clarify, no wrong write), real parsing bug.
2. M5 (medium, GENUINE): "WHO IS MIRA'S CITY?" clarifies instead of answering.
   Root cause in `fable_agent_loop.py`: `_APOS` (`['’]s\b`) matches lowercase
   's only, so shouted possessives never split. Safe (clarify, 0 writes).
3. R4 (medium, expectation error): "Who is Roberto's country of citizenship?"
   safely declines ("don't know anyone called Roberto") — asks do not
   first-name-resolve (only the loop102 forget path prefix-resolves). The
   agent never guessed; my case wrongly assumed it would answer Spain.
4. N6 (critical as sealed, expectation error): the never-taught two-hop
   clarified with "Was that a question?" — safe, zero writes, nothing
   invented. My abstain-bit list does not cover that sentence, so the sealed
   checker missed a safe decline. No wrong answer was given.
5. S3 (medium, expectation error): the packed teach clarified with "Was that
   a question?" (the "?" screen fires before the >6-word screen), 0 writes.
   Safe; I predicted the split-clarify.
6. S6 (medium, expectation error): the "Is ... ? Also teach ..." turn
   clarified generically (FakeEars-native clarifies are swallowed by
   FakeStage into the chain-miss message), 0 writes, Lisbon intact, the
   packed pet never stored. Safe; I predicted the question-clarify.

No wrong fact was stored and no wrong answer was given confidently in any
of the 62 cases. The daemon survived empty, 1 MB, binary, 200-file burst
(all 200 served, sampled asks V00/V50/V99 correct), deleted-mid-read (never
served, later turns fine), 150 KB whitespace, emoji, and NUL byte.

## What it means

Round-1 fixes hold on new ground (56/62, daemon 8/8, pronoun/disagree/
unicode/long-input clean), and round 2 found 2 real bugs: the please-forget
space-drop (loop102) and the shouted-possessive split (FakeEars `_APOS`).

## What it does not mean

The loop does not understand English: 4 of 6 BUGs are my own expectation
errors, first-name asks still decline, and qualifiers/guards remain
template-shape screens, not comprehension.

## Deviations

Pre-run smoke only (unsealed sentences): one `--once` turn and one daemon
boot/serve/stop to verify the harness; vanish implemented as
stop/plant/delete/reboot per the sealed PASSMARKS note. No existing file
edited; no commits; Mac CPU; offline.

Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_redteam110_runner.py --run` (reads the sealed cases.json).
