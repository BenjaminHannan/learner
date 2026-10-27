# TEST-ONLY: exp 232b name panel (claude-namepanel232b-20260922)

TEST-ONLY. Do not train, tune, pilot or write rules from these items. Builders of the exp 232b agent must not open panel.jsonl or base138i.jsonl before their seal.

- panel.jsonl: 84 items, one fresh session each. Families: multi 36 (2- to 4-word names; 15 with particles de/van/ben/la/der/O', 20 with 3-4 words), one 36 (same verb, value and question with a one-word name, paired by position), trap 12 (6 NO_WRITE-style non-teaches, 3 ABSTAIN questions, 2 items where a true multi-word fact is stated but a different name or relation is asked, 1 other ABSTAIN). 12 non-trap items (6 multi, 6 one) carry a second fact "<Name>'s <relation> is <Value>."
- Fields: id, family, setup (teach turns), question (null for NO_WRITE traps), gold, expect (ANSWER/ABSTAIN/NO_WRITE), stated_facts (EVERY fact stated anywhere in setup, as [subject, relation-word-as-written, value]; a stored triple matching any stated fact is a correct write, not a wrong write), note.
- Verbs in scope only: lives in, works at, works for, was born in, speaks. No possessive particle teaches, no yes/no questions, no of-chains.
- base138i.jsonl: every item run on the accepted base 138i (scripts/fable_loop138i_agent.py + artifacts/fable-agent138i-20260922/loop138i-config.json), fresh workdir per item, with replies and stored triples. Base result: one 36/36 saved and answered; multi 0/36 saved or answered; traps 0 triples stored.
- All names and values are fictional.
- SEAL.sha256.txt: sha256 of panel.jsonl and base138i.jsonl, repo-relative paths.
