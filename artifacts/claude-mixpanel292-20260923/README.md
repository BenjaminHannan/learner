# mixpanel292: blind panel for merge 292 (reasoning line)

Writer run on base 291 only. Category level: this file never quotes an item.

## Panel

80 items, ids m292-001..080, schema
{id, family, setup (1-4 turns), question, expect, gold (list), note}.

| family | n | expect kinds |
|---|---|---|
| chain_verb | 12 | value (two-hop asks; 8 with a two-word A name) |
| backwards_bug | 10 | value (backwards asks over spouse/author/founder/parent/child/composer) |
| yesno | 14 | yes x5 / no x5 / unknown x4 |
| mixed | 12 | yes/no/value/unknown from the facts (no bar) |
| broken_chain | 8 | unknown (one link missing) |
| forward_control | 10 | control (plain one-hop asks) |
| statement_control | 8 | control (chain / does / is / has statements the base must not store) |
| correction_control | 6 | value (plain correction, then a live-ask) |

All names are invented and fictional; every item uses a two-word name.
Every setup was checked to store its intended triples on base 291, with
corrections replacing the old value and statement questions storing nothing.

## Base 291 rows (base291.jsonl)

One row per item, fresh agent per item, CPU, sequential, sleep_threshold
100000: {id, family, setup_replies, question_reply, question_stage
(loop.ears.last_stage), stored_after_setup_actual,
stored_after_question_actual, question_wrote}.

## Base 291 marks (sealed score_panel.py)

| family | n | right | wrong | miss | question writes |
|---|---|---|---|---|---|
| chain_verb | 12 | 0 | 0 | 12 | 0 |
| backwards_bug | 10 | 8 | 0 | 2 | 0 |
| yesno | 14 | 0 | 0 | 14 | 0 |
| mixed | 12 | 3 | 0 | 9 | 0 |
| broken_chain | 8 | 0 | 0 | 8 | 0 |
| forward_control | 10 | 10 | 0 | 0 | 0 |
| statement_control | 8 | 8 | 0 | 0 | 0 |
| correction_control | 6 | 6 | 0 | 0 | 0 |
| TOTAL | 80 | 35 | 0 | 45 | 0 |

Question stages per family (counts only): chain_verb none x12;
backwards_bug reverse-table stages x8, bench73 x2; yesno none x14;
mixed reverse x3, none x9; broken_chain none x8; forward_control
answer stages x10; statement_control no-save/clarify stages x8;
correction_control answer stage x6. No question turn wrote a fact.

## What it means

- Base 291 is honest on this panel: 35 right, 0 wrong, 45 miss. Every
  failure is a clarify or an abstain, never a confident wrong answer.
- The base answers one-hop asks, backwards asks of the whose/what kind,
  and plain corrections. It does not answer two-hop asks, yes/no asks,
  or broken chains: those all come back as clarifies.
- The two married-asks miss while the other backwards asks hit; that is
  a wording gap in the base, recorded, not tuned on.

## What it doesn't mean

- It doesn't mean the panel is too hard or too easy: a blind panel
  measures, it doesn't grade the base. The bars belong to the merge-292
  builders.
- It doesn't mean the base stored anything wrong: all 80 setups stored
  exactly the intended triples, and no question turn wrote a fact.
- Misses here are abstains/clarifies, not errors: zero wrong means the
  base never stated a false taught fact on this panel.

## Files

- make_panel.py (writer), panel.jsonl (80 items), run_base.py (base rows),
  base291.jsonl (80 rows), score_panel.py (sealed scorer, builders use it
  unchanged), README.md (this file), SEAL.sha256.txt (hashes of the five
  data/code files).
