# readpanel318: agreement audit (counts only, no items quoted)

## Labeller B setup
- B was a separate Claude Opus instance, started with `claude -p --model opus`. This subagent had no in-session Agent tool, so B ran through the CLI.
- B could use only Read and Write. No MCP servers were loaded, and Bash and WebFetch were disallowed.
- B saw only `blind_input.jsonl` (id, prev_reply, turn) and the labelling rules (facts, owner, relation, value, nosave_reason). It never saw the key: while B ran, `panel.jsonl` was kept outside the output folder.
- `blind_input.jsonl` was deleted afterwards.

## Agreement rule
A gold fact agrees when B has the same owner and the same value, both compared case-insensitively.
- For owner, a first name alone is accepted.
- For value, a leading title or article (Mrs/Dr/the) may differ.
- Relation wording is not compared.
Any B fact that matches no gold fact counts as an extra.

## First pass (240 rows)
- Gold facts: 256. Agreed: 254. Gold facts B did not give: 2. Extra B facts: 2.
- Rows fully agreeing: 236 of 240. Rows with a disagreement: 4 (1 correct, 2 teach_passing, 1 short_answer).
- No-save rows where B saved a fact: 0 of 75.
- Teach rows B left empty: 1. It is one of the 2 missing gold facts.
- nosave_reason agreement on the no-save rows: 75 of 75.

## How each disagreement was resolved
| type | count | resolution |
|---|---|---|
| gold fact missing in B (the fact was an inference, not stated) | 1 | fixed the key: dropped that inferred fact |
| gold fact missing in B (the turn was too implicit) | 1 | rewrote the turn to state it plainly |
| extra B fact taken from the assistant's question | 1 | rewrote prev_reply so it carries no fact |
| extra B fact (a second way to say the same correction) | 1 | dropped the row and replaced it with a fresh correct row |

Kind counts stayed exact: the replaced row is the same kind as the one it replaced.

## Re-run
A fresh B instance labelled the 3 rows whose text changed and agreed on 3 of 3. The key-only fix already matched B's first-pass label.

## Final
- Gold facts: 255. Agreed: 255. Extra B facts: 0.
- Rows fully agreeing: 240 of 240.
- nosave_reason agreement: 240 of 240. That is 75 of 75 rows with no facts, plus all teach rows, where both sides have null.
