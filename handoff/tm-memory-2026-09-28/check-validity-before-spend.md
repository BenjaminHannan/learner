---
name: check-validity-before-spend
description: Thread manager 18:15 UTC 09-26 (mu-404): any validity count that depends only on the panel and reader must be checked at $0 before renting; time stamps in messages from date -u
metadata:
  type: feedback
  modified: 2026-09-26T18:15:29.297Z
---
mu-404 (Making things up about you) spent ~$0.67 on a rental and came back INCONCLUSIVE on its own validity mark: only 34 of 318 chat prompts carried a notebook fact (bar 40). The panel had 0 of 446 turns labelled as teaching a fact; one $0 look at the panel's own labels would have shown it. The Thread manager asked why it wasn't counted before spending.

**Why:** a validity mark that cannot pass wastes the rental and the judges; money goes to reasoning first.
**How to apply:** before sealing, compute every validity count that does not need the model's replies (facts present, triggers fired, rows reaching the changed layer) on CPU or from the panel's labels, write the number in PASSMARKS, and only then ask for a rental. Build panels so the thing being tested is present by construction. Also: every time in a message or file comes from `date -u` at the moment of writing, never estimated (18:20 was written at 18:14). See [[made-up-facts-line]], [[own-your-problem]].
