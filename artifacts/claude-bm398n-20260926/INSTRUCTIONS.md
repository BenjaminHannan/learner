# Blind answer check (bm-398d)

Each line of your batch file(s) is a JSON object: {"item", "question", "gold_answer", "evidence", "reply"}.
The reply is one system's answer to a question about a long chat between two people. You cannot see the chat.
"evidence" holds the chat lines the gold answer was taken from, each with the date of its chat session.
Use the evidence only to understand what the gold answer means: for example, which calendar date a phrase like
"last week" stands for, or which person a fact belongs to. The gold answer is the reference. A reply is right only
if it gives the same answer as the gold answer, even if it quotes the evidence.

Judge only whether the reply gives the same answer as the gold answer. Give each item exactly one label:

- A = right and complete. Extra words are fine, and so is a different wording of the same answer.
- B = contains the right answer and also an incompatible alternative, e.g. two different dates or names offered.
- C = partly right, e.g. one of two list items, the right month but the wrong year, or a vaguer version of the answer.
- D = wrong, or it answers a different question.
- E = says it doesn't know or can't tell.

Brevity is neither a plus nor a minus. Judge each item on its own, by reading it. Do not write code to label.

For each batch file X.jsonl, write labels/X.jsonl in the same folder as this file: one line per item, exactly
{"item": "<item id>", "label": "<A|B|C|D|E>"}, covering every item in the batch once.
