# openpanel260 — blind panel for experiment 260 (openers and greetings)

Written blind on 2026-09-22 by a panel writer who never opened the 260 builder's code, word lists, dev cases or brief.
Category level only; no items are listed here.

## Files
- `panel.jsonl` — 80 items, fields exactly: id, family, setup, turn, followup, stated_facts, expect_store, gold, plain_turn, note.
- `base138m.jsonl` — 80 rows from base 138m (`scripts/claude_loop138m_agent.py` + `artifacts/claude-merge138m-20260922/loop138m-config.json`), fields exactly: id, setup_replies, stored_after_setup, turn_reply, stored_after_turn, followup_reply, stored_after_followup, plain_reply, base_right, base_junk.
- `make_panel.py` — builds panel.jsonl (deterministic).
- `run_base.py` — drives the base like the probe runner: one fresh notebook per item, setup turns, the turn, the followup, stored triples read after each stage; plain_turn is run in a second fresh notebook after the same setup.
- `SEAL.sha256.txt` — sha256 of the four files above, repo-root paths.

## Families (80)
| family | n | what it is |
|---|---|---|
| opener_teach | 20 | a teach that starts with an everyday opener (20 different openers, with and without a comma; possessive, "lives in", "works at", "was born in" shapes). The "X is a Y." shape was left out because the base does not save its plain form. |
| opener_question | 12 | plain teach in setup, then a question after an opener |
| greeting_question | 8 | greeting + question; 6 after a plain teach, 2 ask the assistant's name (setup empty, gold "Premonition") |
| bare_greeting | 6 | only a greeting; setup empty, gold "" |
| name_trap | 10 | teach whose first word is an everyday word that is part of a name or title, not an opener |
| junk_guard | 8 | opener + comma + possessive teach (the shape where the base stores the opener inside the subject) |
| control | 16 | 8 plain teaches + followups, 8 plain questions after plain teaches |

stated_facts / expect_store use the base's storage form (for example "lives in" is stored as relation `city`, "works at" as `employer`, "was born in" as `place_of_birth`); each was checked by running the plain teach on 138m.

## Scoring rules (the builder's scorer implements these exactly)
Normalise strings by lowercasing and stripping edge punctuation and spaces (applies to triple fields and to gold / reply matching).
- junk: any triple stored after the turn or the followup that is in neither stored_after_setup nor expect_store.
- store_ok: expect_store ⊆ stored_after_turn, and nothing else was added.
- question_write: a question turn, or the followup, changes the store.
- reply_ok: gold is "" or a substring of the scored reply (the followup reply for teaches, the turn reply for question turns).
- right by family:
  - opener_teach, junk_guard, name_trap: store_ok ∧ reply_ok ∧ ¬junk ∧ ¬question_write.
  - opener_question, greeting_question: reply_ok ∧ ¬question_write ∧ ¬junk.
  - bare_greeting: no store change, and the reply contains none of (case-insensitive): "save", "understand", "couldn't", "could not", "don't know", "not sure".
  - control: right as its shape above AND byte-identical to base on every reply.
- A schema mismatch (field names or counts) must print SCHEMA-MISMATCH and exit 3.

## Base 138m summary (category level)
| family | items | base_right | base_junk |
|---|---|---|---|
| opener_teach | 20 | 3 | 5 |
| opener_question | 12 | 5 | 0 |
| greeting_question | 8 | 1 | 0 |
| bare_greeting | 6 | 3 | 0 |
| name_trap | 10 | 10 | 0 |
| junk_guard | 8 | 0 | 8 |
| control | 16 | 16 | 0 |
| total | 80 | 38 | 13 |

Base reply to a plain "Hello." (recorded in bare_greeting notes): the teach/ask hint ("Hi! Teach me like ...").
All names are invented. Two full base runs gave byte-identical base138m.jsonl.
