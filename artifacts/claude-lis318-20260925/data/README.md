# lis-318 chat training rows (2026-09-25)

Written from scratch by 5 Opus agents (brief WRITER.md, one name pool each), 500 rows each, dialogs of 4-8 turns.
No LoCoMo or LongMemEval text and nothing built from them; no panel or bank A/B was read; no DEV name used.
Blind second labeller (LABELLER.md) per file saw only id, prev_reply, turn: label_B_w*.jsonl.
Agreement (scripts/claude_lis300_agree.py, the lis-300 rule): 2,260 of 2,500 rows agreed (agreed_ids.txt).
Per writer: w1 449, w2 473, w3 423, w4 460, w5 455; per family agreed / written:
ask 397/400, correct 193/200, nosave 287/300, pets 167/200, pronoun 136/150, short_answer 29/100,
smalltalk 230/250, teach_multi 536/600, teach_passing 285/300.
Builder dry run (CPU, scripts/claude_lis318_data.py): train 45,124 (o0b 27,000, opus 5,012, opus301 4,960,
chat318 8,152 = 2,038 x 4), dev 1,181 (lis-301's 959 + chat318_dev 222, split by dialog).
Writers' judgement calls the agreement filter settles: species/breed with no table relation, sarcasm (NEGATED or
UNCLEAR), yes/no questions (QUESTION fact or facts []). Rows where the two labellers differ were dropped.
