# slp-366 results: PASS 5/5 marks as registered (blind recount agrees, VERIFY.md), with large limits below

Run 2, 2026-09-25 ~02:58-03:15 UTC, CPU, $0, via scripts/claude_slp366_main.py (run 1 VOID: crashed at scoring,
no numbers seen). Sealed scorecard and wrapper hashes check OK. The PASSMARKS line fails only because the VOID note
was appended; with it removed the file matches the sealed hash.

| Mark | Bar (each seed) | Seed 1 | Seed 2 |
|---|---|---|---|
| P366.1 taught one-hop facts right after every night | all | all (27, 60, 112, 120, 120, 120 asked) | same |
| P366.2 made-up answers to lures | 0 | 0 | 0 |
| P366.3 a learned word stays ≥ 95% on every later night | yes | 6/6 words at 100% | same |
| P366.4 transfer people (taught after a word's night) right, nights 2-6 | ≥ 90% | 100% | 100% |
| P366.5 final night: SLEEP minus NOSLEEP word right-rate | ≥ +50 points | 118/118 vs 0/118 (+100) | same |

All 12 SLEEP nights were kept by the 364 gate with 0 reasons. NOSLEEP gave 0 wrong names.

## Limits (blind recount, shown unless marked)
- **One world, not two.** The seed only renames people (adds "s2") and changes the sleeper's own seeds; the
  structure is identical, and every count matches. Treat this as one world run twice.
- **Taught facts are a sample from night 4 on.** The gate's probe builder caps taught questions at 120; the world
  has 160, 214 and 274 taught facts by nights 4, 5, 6, and the same 120 are asked every night, so facts taught on
  days 5-6 are never asked directly.
- **Lenient grading:** a reply naming the right person plus a wrong one counts as right; an invented name absent from
  the notebook is never "wrong"; probes are rebuilt from the notebook after each night, so a lost fact would drop
  its question rather than fail it; corrections are never tested through words.
- NOSLEEP is 0% by design (it never sleeps, so it can't learn words), so P366.5 only asks whether SLEEP reaches 50%.
- **Learning source (from the 336b rental report):** like 360/361/367, this world asks each day's word question
  10+ times, which is what queues the sleeper's learning episodes. In ordinary chat that never happens, and 336b saw
  0/360 sleeps attempt learning. So 366 shows that when the word-route sleeper does learn, it keeps what it learned
  for 6 nights, transfers to new people and makes nothing up. It does not show learning from normal conversation.

## What it means
The multi-night scorecard works and is now a ready test for any new sleep (363 next). Today's word-route sleeper
passes it: no forgetting across 6 nights and 0 made-up answers, in a world built to feed it.
