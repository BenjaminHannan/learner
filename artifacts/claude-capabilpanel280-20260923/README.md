# capabilpanel280 (exp 280 blind panel)

Blind panel writer output. Test items only; no code was read or run.
All names are fictional and freshly invented. No real persons, no secrets.

## Files

- `panel.jsonl`: one JSON object per turn (40 lines total).
- `SPEC-COPY.md`: the 280 spec section, copied verbatim.
- `README.md`: this file (counts per category and schema).
- `SEAL.sha256.txt`: sha256 seal of `panel.jsonl` and `SPEC-COPY.md`.

## Schema (panel.jsonl, one object per line)

- `dialog_id`: string. Dialog identifier (`G01`–`G12` general, `C01`–`C20` can-you, `K01`–`K04` controls).
- `turn_index`: integer. Turn position within the dialog, 0-based. Single-turn dialogs have only turn 0. Control dialogs `K01`–`K04` have turn 0 (teach) and turn 1 (ask).
- `user_text`: string. The user turn text.
- `category`: string. One of `general`, `can_you`, `control_teach`, `control_ask`.
- `gold`: expected outcome.
  - Ability items (`general`, `can_you`): the string `"no_write"` (no notebook write expected; claim correctness is checked by the director against the sealed ability table).
  - `control_teach`: object `{"subject": ..., "relation": ..., "value": ...}` giving the expected stored triple. Relation is a lowercase singular noun (e.g. cat, city, boat, band).
  - `control_ask` stored: string with the exact expected fact value (e.g. the taught value).
  - `control_ask` not stored: the string `"abstain"`.

No other fields are present.

## Counts per category (test turns; integer counts)

- `general`: 12
- `can_you`: 20
- `control_teach`: 4
- `control_ask`: 4
- Controls combined (`control_teach` + `control_ask`): 8
- Total lines in `panel.jsonl`: 40

## Dialog structure (36 dialogs, 40 turns)

- 12 general dialogs (`G01`–`G12`), 1 turn each, standalone (no setup teaches).
- 20 can-you dialogs (`C01`–`C20`), 1 turn each, standalone. Coverage: 2 questions each over forget, correct, two-step, remember-after-restart, math, web, feelings, translate, names, sources.
- 4 control dialogs (`K01`–`K04`), 2 turns each: turn 0 is a plain teach, turn 1 is a plain possessive ask. Three asks target stored facts; one asks about a never-taught person and expects abstain.

## Notes

- Wording is varied in register as real people type, including lowercase / missing punctuation / casual forms where the spec asks for varied wording and register.
- Ability questions carry no fact content, so `no_write` is unambiguous.
- Fictional names only throughout.
