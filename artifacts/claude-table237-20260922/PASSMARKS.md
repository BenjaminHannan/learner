# Exp 237 PASSMARKS (written before the seal; panel NOT opened)

Build: loop237 = loop221 + relation table v1.1 (scripts/claude_loop237_agent.py,
config loop237-config.json, table relation_table_v1_1.json). 228 guard installed
(SrcGuardMixin228 first in Loop237Daemon bases; install_srcguard228() at import).
Pilots done (scratch only): dev 34/34 (221 arm 12/34), suitediff vs 221 rows
GATE clean with 1 move, sleep smoke 5/5 in 85 s.

## Registered runs, in order (each once, Mac CPU, OMP/MKL=1, load < 60)
1. M2 dev: scripts/claude_table237_run.py on dev237.jsonl, both arms (loop237, loop221).
2. M3 suites: fable_suitediff218.py --base-dir artifacts/claude-table237-20260922/base221rows
   (byte copies of 221's saved rows under names the finder recognises; sha in SEAL)
   --only rt136,rt143,sessions152,bench.
3. M4 sleep smoke: fable_sleepsmoke206.py, label s1-237, default seed.
4. M1 panel: check panel SEAL.sha256.txt from the repo root; then run
   claude_table237_run.py once per arm (loop237; loop221 for timing only), score
   with claude_table237_score.py. The field map (field NAMES only) is written after
   opening and reported as a deviation; scoring rules are the sealed ones in the script.

## Bars
| mark | bar |
|---|---|
| M1 synonym | >= 85 % right |
| M1 new_relation | >= 80 % right |
| M1 date | >= 80 % right |
| M1 trap | 100 % (0 values given) |
| M1 control | 100 % byte-identical to base221.jsonl reply |
| M1 wrong values, all items | 0 |
| M1 question writes | 0 |
| M2 dev (34 cases) | 34/34 right, 0 question writes; traps 7/7 |
| M3 new WRONG / WRONG-WRITE / junk write / lost OK | 0 |
| M3 moves | exactly the predicted set: rt143 L3 reply-only move; nothing else |
| M4 sleep smoke | sleeps 1, installed, probes 5/5, wrong 0, taught 50/50, overwrote 0, < 300 s |
| M5 latency | median(loop237 q_ms) - median(loop221 q_ms) <= +5 ms on the panel questions |

Any unpredicted flip toward an abstain or "Was that a question?" is reported,
counted against its mark, and that item is run alone 5 times.

## Predictions (ledger P237.1-P237.5)
- P237.1 M1 passes every family bar; 0 wrong values; 0 writes.
- P237.2 Traps 100 %: boss/employer, hometown/birthplace, wife/husband and other
  non-synonyms stay unlinked.
- P237.3 M3: only rt143 L3 moves (reply-only, OK->OK); GATE clean.
- P237.4 M4 identical marks to 221; M5 delta <= +5 ms.
- P237.5 Most likely M1 misses: wordings no template covers (phrasal forms not in
  the table) -> honest abstains, not wrong values.
