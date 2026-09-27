# rd-378k addendum J (2026-09-27 03:08:15 UTC): gate3low overlapped the opencode usage limit, so it counts only if nothing in it failed

Written before any of 004-rd378k-gate3low's output has been seen. None of its output is on builder-outbox yet (be2890edb
lists only the job's running marker). PASSMARKS.md and addenda B-I stay as sealed; this file adds to them.

## What happened
- 004-rd378k-gate3low launched at 00:35:28 UTC.
- Ben's opencode Go plan hit its weekly usage limit at about 00:57 UTC. The Mac's opencode.log shows "Go usage limit
  exceeded", and Ben confirmed the weekly limit at 03:05 UTC (Thread manager, 03:06 UTC). The limit covers every
  opencode-go model, glm-5.3-flash included.
- The gate needed about 116 calls, roughly 25 min from the start of its label step. It very likely ran into the limit.
- A call refused by the limit can come back two ways, and the log alone does not always say which:
  - as a failed call (empty raw answer: a route loss under addendum H);
  - as error text in place of a grade (an unparsed window, which addendum H would not count as a route loss).

## The rule
gate3low counts only if its failures.jsonl has 0 lines (0 failed calls and 0 unparsed windows) and all 38 dialogs are
usable. The check reads only those two counts. It reads no grade, label or agreement line.
If either count is above 0, gate3low has no verdict, whatever its rows say. Its labels and agreement lines are then
never read.
After the usage limit resets, the same 38 dialogs run again as gate3low2 (output folder gate3low2/), through the same
low route, with the same bars and the same rules (F, H, I).

## Why not audit instead
Telling limit errors apart from real unparsed answers would mean reading raw GLM text for these gate dialogs, which is a
look at the gate's content before its re-run. Re-running costs about 116 calls of quota; reading costs the gate's
independence.
