# Exp 236 PASSMARKS -- questions that use only a first name (sealed before any registered run)

Agent: scripts/claude_loop236_agent.py = loop221 + FirstName236Mixin outermost on the
Loop221Ears stack (question turns ending in "?" only). 228 guard: install_srcguard228() at
import, SrcGuardMixin228 first in Loop236Daemon bases.
Config: artifacts/claude-firstname236-20260922/loop236-config.json (221 config, labels only changed).
Base for every comparison: loop221 (scripts/fable_loop221_agent.py + its sealed config).

## Rule being tested (exactly as coded)
In a question turn, a capitalised single word T (>= 2 letters, not a closed function word,
optionally "T's"), not followed by another capitalised word, not inside a full stored name
written in the question, and not itself a stored entity name or stored value:
- exactly one active taught subject name of 2+ words starts with T -> the question is heard with
  T replaced by that full name (kept only if all actions are read-only; else the original turn);
- two or more -> "Which T do you mean: A or B?" (up to 3 names, alphabetical), no value, no write;
- none -> original turn untouched (byte-identical to 221).
Statements/teaches never reach the rule. Surname-only questions are out of scope (unchanged).

## Marks and bars

| mark | what | bar |
|---|---|---|
| M1a | panel unique_first + of_form, right = every gold value in the reply, no other stored value | >= 90 % |
| M1b | panel ambiguous: reply is "Which T do you mean: ..." naming every candidate, 0 values | 100 % of items (an item with more than 3 candidates can only name 3; it counts as a miss on this mark, declared now) |
| M1c | panel exact_wins: the single-name entity's value in the reply | 100 % |
| M1d | panel no_match and last_name_only: reply byte-identical to 221 | 100 % |
| M1e | panel statements: reply byte-identical AND same active and all-taught triples as 221 | 100 % |
| M1f | panel, all 60 items: wrong values | 0 |
| M1g | panel, all question turns: turns that changed the taught facts | 0 |
| M2 | dev cases artifacts/claude-firstname236-20260922/dev236.jsonl (28 items, same scorer and families) | 28/28, 0 wrong values, 0 question writes |
| M3 | frozen suites rt136, rt143, sessions152, bench vs 221's saved rows (fable_suitediff218.py --base-dir) | 0 new WRONG, 0 new WRONG-WRITE, 0 new junk, 0 lost OK, and every move predicted by id |
| M4 | sleep smoke (fable_sleepsmoke206.py), same marks as 221's s1-221 | sleeps 1, installed, episodes 20, probes 5/5, wrong 0, broken chain = abstain, taught 50/50, overwrote 0, < 300 s |
| M5 | median added time per question turn, 236 minus 221, paired by item, on the panel | <= +5 ms |

Scorer: scripts/claude_firstname236_score.py (sealed). Runner: scripts/claude_fullname232_run.py
(existing, read-only; fresh daemon + notebook per item under a scratch work dir).
Both arms (236 and 221) are run fresh by me on the panel; "byte-identical to 221" is judged
against that fresh 221 run. The writer's base221.jsonl is checked too: any disagreement between
my fresh 221 replies and base221.jsonl is reported item by item.

## Predicted moves (P236.n in the ledger)
- rt136, rt143, sessions152, bench: **0 moves** (pilot on the sealed code: 0/0/0/0, GATE clean).
  rt143 P1-P8 (Dara Fenn / Dara Fenner) always name the full name, so the rule never fires there.
  Any move in these suites is unpredicted and fails M3.
- Panel: moves are expected on unique_first, of_form and ambiguous items only (abstain -> answer or
  abstain -> clarify). No move on exact_wins, no_match, last_name_only, statements.
- Dev: 15 moves (8 unique_first, 2 of_form, 5 ambiguous); 13 unmoved.

## Declared in advance
- The panel has not been opened. Its field names are not known. If they differ from the scorer's
  (id, family, setup, question, gold), a field map written after opening is a driver-only
  deviation, reported with its code. Family names are mapped by meaning (e.g. "statements" = statement).
- "Stored name" = subject of an active taught fact (fable_loop90_agent.notebook_triples), not the
  USER key. A value-only name (e.g. a company that is only ever an object) is never resolved.
- Stored values also block T (a conservative widening of "exact match wins").
- Base rows for M3: artifacts/claude-tableask221-20260922/suitediff/ copied byte-for-byte into
  artifacts/claude-firstname236-20260922/base221rows/ under file names the 218 tool can find
  (redteam136-rows.json, redteam143-rows.json); with the original folder the tool reports rt136 and
  rt143 as SKIPPED because of the file names.
- One registered run each. A FAIL is reported as FAIL.
