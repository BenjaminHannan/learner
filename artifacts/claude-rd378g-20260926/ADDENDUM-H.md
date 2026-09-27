# rd-378g addendum H (2026-09-27 03:08:15 UTC): writelow overlapped the opencode usage limit, so every batch it did not write may be written again

Written before any of 005-rd378g-writelow's output has been seen. None of its output is on builder-outbox yet
(be2890edb). ADDENDUM-A to G stay as sealed; this file adds to them.

- What happened: 005-rd378g-writelow launched at 00:35:28 UTC. Ben's opencode Go plan hit its weekly usage limit at
  about 00:57 UTC; see rd-378k addendum J (artifacts/claude-rd378k-20260926/PASSMARKS-J.md).
- A write call refused by the limit may come back as a failed call (a route loss, addendum F) or as error text. Error
  text then fails the code checks and would look like a genuinely bad batch. The log does not tell the two apart.
- Rule: every batch that writelow wrote ("batch N ok", present in glm2L/notes_w1.jsonl) is kept. It passed the code
  checks, and error text cannot pass them. Every other batch of the 21 is treated as route-lost, whatever the log
  says, and may be written again after the reset. That run is writelow2: --have glm2L/notes_w1.jsonl if it landed,
  else glm/notes_w1.jsonl; its output goes to glm2M/.
- This gives a batch that genuinely failed the code checks one more set of 3 tries. This is data writing, not a test;
  it is disclosed here.
- The 120-dialog floor of addendum D counts only after writelow2.
