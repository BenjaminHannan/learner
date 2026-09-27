# TEST-ONLY: blind panel for exp 232c (multi-word names with particles, plain verb sentences)

TEST-ONLY. Do not train, tune or pilot on these items. Written blind by a separate panel writer on 2026-09-22.

## Files
- `panel.jsonl`: 84 lines, one item per line.
- `base138i.jsonl`: 84 lines, one per id; the 138i base agent's behaviour on each item.
- `SEAL.sha256.txt`: sha256 of both files, from the repo root.

## panel.jsonl schema (exactly these 10 fields, no others)
- `id`: "n232c-001" ... "n232c-084"
- `family`: one of `multi`, `one`, `trap`, `stated_extra`
- `pair`: "p01" ... "p36" for `multi` and `one` (a multi item and its one-word twin share the pair id); null for `trap` and `stated_extra`
- `name_words`: int, number of space-separated words in the main name (0 for the one trap that names nobody)
- `setup`: list of strings (turns sent before the question; may be empty)
- `question`: string or null
- `gold`: string or null (the answer value for ANSWER items; null otherwise)
- `expect`: one of `ANSWER`, `ABSTAIN`, `NO_WRITE`
- `stated_facts`: list of [subject, relation-word-as-written, value], the COMPLETE list of every fact stated anywhere in the setup
- `note`: string

## base138i.jsonl schema
- `id`
- `base_reply`: reply to the question (null when question is null)
- `base_setup_replies`: list of replies to the setup turns
- `stored`: list of triples in the notebook after the last turn

## Families
- `multi` (36, ANSWER): names of 2-4 words, most with a lowercase particle; also O'X, D'X and X-Y names.
- `one` (36, ANSWER): one-word twin of each multi item, same verb, value, question form and pair id.
- `trap` (8, NO_WRITE or ABSTAIN): no fact stated, stated_facts = [].
- `stated_extra` (4, ABSTAIN): one true multi-word fact is stated; the question asks about something never taught.

Verbs (rotated in order): lives in / works at / works for / was born in / speaks.
Ten multi/one items (pairs p01, p07, p13, p19, p25, both twins) add a second fact "<Name>'s <relation> is <Value>.".
Base run: scripts/fable_loop138i_agent.py + artifacts/fable-agent138i-20260922/loop138i-config.json, fresh workdir per item.
