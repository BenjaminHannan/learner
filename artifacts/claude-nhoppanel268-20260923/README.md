# nhoppanel268 — blind panel (reasoning line)

Backwards questions about a value that has its own facts, plus forward and
abstain controls. 70 items. Fictional names only. Category level only: no
item text is quoted here.

## Files

- `panel.jsonl` — 70 items: `id` (n268-001..n268-070), `family`, `setup`
  (1–4 teaches, each its own turn), `question`, `gold` (JSON list; every
  string must appear in a right reply; `[]` = right reply abstains), `note`.
- `base138m.jsonl` — 70 rows from one run each on the 138m base
  (`scripts/claude_loop138m_agent.py` build_agent138m with
  `artifacts/claude-merge138m-20260922/loop138m-config.json`,
  sleep_threshold 100000, fresh temp state_dir per item outside the repo,
  one process at a time). Row fields: `id`, `setup_replies`,
  `question_reply`, `question_stage`, `stored_after_setup_actual`,
  `stored_after_question_actual`, `question_wrote`.
- `make_panel.py` — deterministic writer of `panel.jsonl`.
- `run_base.py` — driver that produced `base138m.jsonl`.
- `score_panel.py` — sealed scorer with a schema gate (prints
  SCHEMA-MISMATCH and exits 3 with no verdict on any schema deviation).
- `score138m.json` — machine-readable score output (not part of the seal).

## Families (70 = 24 + 10 + 8 + 12 + 10 + 6)

- reverse_chain (24), reverse_nochain (10), uncued_reverse (8),
  forward_chain (12), forward_1hop (10), abstain (6).
- reverse_chain spans 8 relations (none used more than 5 times) and holds
  6 two-subject items.
- 35 items contain a two-word proper name (spec minimum: 20).
- Teach form is "A's R is B." throughout; every teach stored on the base
  (all setup replies confirm storage), so no item needed replacing.

## Base (138m) results — category level only

| family | n | right | wrong | question_wrote |
|---|---|---|---|---|
| reverse_chain | 24 | 10 | 0 | 0 |
| reverse_nochain | 10 | 4 | 0 | 0 |
| uncued_reverse | 8 | 8 | 0 | 0 |
| forward_chain | 12 | 12 | 0 | 0 |
| forward_1hop | 10 | 9 | 0 | 0 |
| abstain | 6 | 3 | 0 | 0 |
| TOTAL | 70 | 46 | 0 | 0 |

- right = every gold string in the reply (case-insensitive); abstain items:
  abstain-form reply naming no taught name.
- wrong = reply names a taught name/value outside gold while missing some
  gold string (and is not abstain-form); abstain items: non-right reply
  naming a taught name.
- Misses (neither right nor wrong): 24 total — 14 reverse_chain, 6
  reverse_nochain, 1 forward_1hop, 3 abstain. These are replies that match
  neither the right nor the wrong pattern (unparseable-question and
  wrong-shape replies).
- The question turn never wrote a fact (question_wrote = 0 everywhere).
