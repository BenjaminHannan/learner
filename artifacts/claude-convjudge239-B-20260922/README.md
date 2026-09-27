# Exp 239 conversation panel: Judge B (TEST-ONLY)

TEST-ONLY. These are blind human-style grades by Judge B on a subset of the exp 239 panel (agent 138i). They exist to measure agreement between two judges. Do not tune anything on them.

- Subset: user turns numbered 0 to 243 in file order; graded turns have number mod 4 == 1 (61 turns).
- Inputs: artifacts/claude-convpanel239-20260922/panel.jsonl (the seal check passed) and transcripts-138i.jsonl.
- Judge B did not open Judge A's folder, the agent code or the design notes.
- File: grades-138i-subset.jsonl, one row per graded turn (turn_number, conv_id, turn_index, intent, grammatical, natural, correct, simple_mistake, bad_write, note).
