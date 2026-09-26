# bm-398e AMEND-1: span scores on a rented GPU (benchmarks thread, written 2026-09-26 17:32 UTC)

Written before any span score is used for anything. No mark, prediction, fitted range or line of code changes.

## What changes
- Steps 2 and 4 of the PLAN (span scores on the 432 drafts and on T's 1,540 LoCoMo replies in categories 1-4) run
  together on one rented GPU (bf16, the precision T's replies were made at), not on this CPU. Both sets of span
  scores come from the same device, so the fit and the LoCoMo run see the same scorer.
- Why: on this CPU span scoring measured about 2 questions a minute, so the 1,972 questions would take about 16
  hours. The rental task is handoff/queue/rent-bm398e.md (budget $0.35 from this thread's $2).
- The drafts stay as made on this CPU (fp32), before this amendment: inputs/drafts.jsonl, 432 rows, sha256
  8779cb841d7d26f2e4d8ba0e333a0b8df7f19d5f5de1bc05ef8c08a24a4b5ae9. The made-up chats are inputs/made.json, sha256
  c19c82b3b4c6f8d522fcd44afb8f15bbdfa9f7795590ea603684259561ceb137 (as in inputs.sha256.txt). Both are code-made or
  1B-written; neither holds benchmark text.
- 15 span rows scored on this CPU before the switch are set aside in the scratchpad, unread, and used for nothing.
- Steps 3, 5, 6 and 7 (fit, apply, score, blind check) run here as the PLAN says.

## Disclosures added now
- Header time: the PLAN's header says "~14:15 UTC", written as an estimate rather than from `date -u`. The
  PLAN's seal commit is the record of when it was sealed.
- Training-data rule (Ben, 16:39 UTC): LAMBDA and BETA, two numbers, are fitted on code-made chats built from
  Claude-written sentence patterns (scripts/claude_bm398e_data.py, word lists from claude_bm397t_data.py). No
  model weights are trained. Even so, under that rule the fitted trimmer cannot go into a build as it is. If it
  passes, the two numbers must be refitted on GLM-written chats first.
- Redirect (Ben, 16:04 UTC): bm-398e finishes as a report and is not extended. The trimmer is a bolt-on after
  the model, not a learned part of Ben's design.
