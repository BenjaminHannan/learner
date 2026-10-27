# Blind answer check

Each line of your batch file(s) is a JSON object: {"item", "question", "gold_answer", "reply"}.
The reply is one system's answer to a question about a long chat between two people. You cannot see the chat.
Judge only whether the reply gives the same answer as the gold answer. Give each item exactly one label:

- A = right and complete. Extra words are fine, and so is a different wording of the same answer.
- B = contains the right answer and also an incompatible alternative, e.g. two different dates or names offered.
- C = partly right, e.g. one of two list items, the right month but the wrong year, or a vaguer version of the answer.
- D = wrong, or it answers a different question.
- E = says it doesn't know or can't tell.

Brevity is neither a plus nor a minus. Judge each item on its own.

For each batch file X.jsonl, write labels/X.jsonl in the same folder as this file: one line per item, exactly
{"item": "<item id>", "label": "<A|B|C|D|E>"}, covering every item in the batch once.
