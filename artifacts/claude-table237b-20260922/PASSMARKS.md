# Exp 237b PASSMARKS (written before the seal; panel NOT opened)

Build: loop237b = loop237 + relation table v1.2 (scripts/claude_loop237b_agent.py,
config loop237b-config.json, table relation_table_v1_2.json built by
scripts/claude_table237b_build.py). Only the table is swapped; the agent forces
the v1.2 path. 228 guard installed (SrcGuardMixin228 first in Loop237bDaemon
bases; install_srcguard228() at import). Design: design/v3/30-modes/237b-tablev12-opus.md.

Pilots (scratch only, before this file):
- table check 16,662 patterns, 1.5 ms/reading, 0 new surface collisions;
- dev 83/83 (after fixing 3 dev cases, listed below), 0 writes, dev median +2.6 ms;
- suitediff vs 221 rows GATE clean with the 1 predicted move;
- sleep smoke sleeps 1, installed, 20 episodes, 5/5, wrong 0, 50/50, ow 0, 84.5 s.
Dev cases changed during the pilot (before the panel existed):
- d237b-40: "My last name is Harrow." stores nothing (base write side), so the
  setup became "My surname is Harrow." / "What is my family name?".
- d237b-45: "What is the name of X's hamster?" is claimed by the base (it asks
  about "the name of X"), so it became "Who's X's hamster?". Known limit.
- d237b-83: a statement is not a question; it became a yes/no question.

## Registered runs, in order (each once, Mac CPU, OMP/MKL=1, 1-min load < 60)
1. M2 dev: scripts/claude_table237_run.py (237's runner, unchanged, hash sealed
   here) on dev237b.jsonl, arm loop237b and arm loop221; score with
   scripts/claude_table237b_devscore.py.
2. M3 suites: scripts/fable_suitediff218.py --agent scripts/claude_loop237b_agent.py
   --config loop237b-config.json --base-dir artifacts/claude-table237-20260922/base221rows
   --only rt136,rt143,sessions152,bench.
3. M4 sleep smoke: scripts/fable_sleepsmoke206.py, label s1-237b, default seed.
4. M1 + M5 panel: check the panel SEAL from the repo root; run the schema check
   (scorer step 1; SCHEMA-MISMATCH -> exit 3 -> VOID); run claude_table237_run.py
   ONCE per arm (loop237b; loop221 for timing and a reproduction check); score with
   scripts/claude_table237b_score.py (rules in its docstring).

## Bars
| mark | bar |
|---|---|
| M1 synonym | >= 85 % right |
| M1 new_relation | >= 80 % right |
| M1 date | >= 80 % right |
| M1 trap | 0 NEW value-giving replies vs base221 (base221 value-giving traps listed, not counted) |
| M1 control | 10/10 byte-identical to base221 base_reply |
| M1 new wrong values vs base221 | 0 |
| M1 question writes | 0 |
| M2 dev (83 cases) | all right (synonym/new_relation/date contain gold and no "I don't know" start; traps give no value; controls identical to the loop221 arm), 0 question writes |
| M3 | 0 new WRONG / WRONG-WRITE / junk / lost OK; moves = predicted_moves237b.json (rt143 L3 reply-only only) |
| M4 sleep smoke | sleeps 1, installed, probes 5/5, wrong 0, taught 50/50, overwrote 0, < 300 s |
| M5 | median(q_ms loop237b) - median(q_ms loop221) <= +5 ms on the panel questions |

Scoring rules as brief: right = every gold part in the reply (case-insensitive) and
the reply does not start with "I don't know"/"I do not know". Wrong value = a value
from stored_after_setup that is not a gold part (any value for traps), whole word,
case-insensitive. One declared normalisation: when deciding whether a stored value
IS a gold part, a leading a/an/the is ignored ("a Hesper Coupe" = gold "Hesper Coupe").
Any unpredicted flip toward an abstain or "Was that a question?" is reported,
counted against its mark, and that item is run alone 5 times (228 guard installed).

## Predictions (ledger P237b.1-P237b.6)
- P237b.1 M1 passes every family bar; 0 new wrong values; 0 writes; controls 10/10.
- P237b.2 Traps: 0 NEW value-giving; near-synonyms stay unlinked. Any base221
  value-giving trap (e.g. a "Who does X employ?" verb-direction item, exp 251) stays
  and is listed, not counted.
- P237b.3 M3: only rt143 L3 moves (reply-only, OK->OK); GATE clean.
- P237b.4 M4 marks identical to 237/221.
- P237b.5 M5: added median between +1 and +4 ms (two table reads of ~1.5 ms on each
  base-miss question); <= +5.
- P237b.6 Most likely misses: wordings the base claims itself ("What is the name of
  X's R?"), verb-form setups the write side does not store, or a panel pair that
  the enumeration judged not a true synonym (answered as an honest abstain, no value).
