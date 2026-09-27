# k1h ADDENDUM 4: answers that are the route's own error text are dropped as route losses (Creative answers in chat thread, written 2026-09-27 03:07 UTC)

Written before I have read any GLM chat or answer text from k1h-glm2 and before any of its output from after 20:38 UTC
has reached the repo. It adds one code filter on the route and changes no prompt, parsing, gate, bar, recipe, arm,
panel, mark or scope. Registered FAILs stay FAILs.

## Why
The Director, 03:06 UTC: Ben's opencode Go plan hit its usage limit at about 00:57 UTC ("Go usage limit exceeded" in
opencode.log, relayed by Ben's Mac Claude at 03:01). k1h-glm2 was then in its chat-writing step (11 of 36 calls done
at 23:33 UTC). Helper v1.1 returns whatever opencode prints when it exits 0 (scripts/claude_glm_opencode_v11.py:130-133),
so a call made after the limit could come back as error text rather than an answer, and answers.jsonl records no time
per row, so such rows cannot be picked out by time.
- Chat writing: a reply that is not a JSON list of chats is already rejected by run_chats' parsing, so error text
  cannot become a chat.
- Answers: error text would pass as a non-empty answer. The Mac agents also run on the same opencode plan, so the job
  itself may stall until the limit resets.

## The rule (scripts/claude_k1h_routefilter.py, selftest 2/2; fixed before any answer is read)
Before `claude_k1h_train.py check`, answers.jsonl goes through the route filter. A row is a route loss if:
- R1: its answer contains one of "usage limit", "limit exceeded", "rate limit", "opencode", "> build", "api key",
  "providermodelnotfound", "insufficient credit", "insufficient balance" or "unauthorized" (case-insensitive), or
  starts with "Error" or "error:";
- R2: the same answer text (trimmed, lower-cased, runs of spaces collapsed) was given for 3 or more different chats.
A route-loss row keeps its item with an empty answer, so check counts the item under "no_answer". A later non-empty
row for the same item still wins, as in check. The filter prints counts only, and its counts are reported by rule
beside the gate results. A route loss is not a grade and does not count against GLM's answers in gate 2.
Cost of the rule: a real creative answer that happens to contain one of those phrases is also dropped. That loses a
training row, not a mark, and the count is reported.

## What happens next
- If k1h-glm2 pushes its outputs, the filter and then the sealed check run on them as they are.
- If it ends or stalls without pushing, a copy-only salvage job (handoff/held/000-salvage-k1h-glm2.md) brings back what
  is in its folder. It stops no process.
- Items without a kept answer are asked again only by a later resume job on wrapper v1.2 (ADDENDUM-3), after the plan's
  limit resets, with caps fixed in its own addendum before it runs.

## What does not change
The model, both prompts, the parsing, the code filters in check, gates 1 to 3 (DATA-GATE-k1h.md) and the size floor of
600, the training recipe, the arms, the panel, the marks and the scope (ADDENDUM-1 to 3).
