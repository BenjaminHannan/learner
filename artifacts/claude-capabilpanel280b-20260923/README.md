# capabilpanel280b (blind panel for exp 280b)

Fresh blind panel. Written without reading any code, any other panel, or any
artifacts folder. All names are fictional and freshly invented. Do not tune on
this panel; do not quote its items.

## Files

- panel.jsonl: one JSON object per turn (50 lines).
- SPEC-COPY.md: verbatim copy of the 280b panel-spec section plus turn counts.
- SEAL.sha256.txt: shasum of panel.jsonl and SPEC-COPY.md, taken from the
  worktree root after writing. Sealed files must not change afterwards.

## Line schema (panel.jsonl)

Each line has exactly these fields:

- dialog_id: string. Dialogs are numbered per category (g, s, n, c prefixes).
- turn_index: integer, 0-based position of the turn inside its dialog.
- user: string. The user text for this turn.
- category: one of general, specific, nearmiss, control.
- gold: one of ability_list, unchanged, no_write, or an expected-fact string.
  On non-final turns of multi-turn dialogs, gold holds the setup fact taught on
  that turn. Only the last turn of each dialog is scored.

Gold meanings for scored (last) turns:

- ability_list: the turn is a general ability question and should get 280's
  sealed CAN280 text.
- unchanged: the turn is a specific-ability question and should keep 280's
  reply exactly (0 changed vs 280).
- no_write: the turn should produce no notebook write (unstored question).
- fact string: the full-sentence fact the reply should convey / store.

## Counts per category (turns)

- general: 25
- specific: 10
- nearmiss: 10
- control: 5
- TOTAL: 50 turns in 45 dialogs (25 + 10 + 7 + 3 dialogs)

## Counts per scored gold (last turn of each dialog, 45 scored turns)

- ability_list: 25
- unchanged: 10
- fact string: 7
- no_write: 3

## Category contents (no items quoted)

- general (25 turns): broad ability questions aimed at the assistant, in varied
  real-world wordings (slang, mild typos in filler words only, short and long,
  tell-me/list forms, what-it-is-for forms). No named entity and no relation
  word appears in any of them.
- specific (10 turns): questions each naming one concrete ability target, kept
  out of scope for the general rule; gold unchanged.
- nearmiss (10 turns over 7 dialogs): questions about a named person's
  abilities (some with a prior teach in the same dialog, some never taught) and
  statement-form teaches about what a named person can do. None is addressed to
  the assistant as an ability question.
- control (5 turns over 3 dialogs): plain possessive teaches and questions plus
  one never-taught question.
