# Sleep-B addendum 11c: K2's names question asked with full thinking (written 2026-10-25 ~16:50Z, after the probe, before the fix code and before any rerun)

Labels: shown / suggested / untested. Amends addendum 11 and 11b (both sealed, unchanged). Same arms (k2s_bf16, k2s_q4), Week-2 world,
recipe, seed and pass marks (No harm, T1, Q1). Not the village model, not the card experiments.

## What happened (shown)
- 11b's rerun (box 57681250): the bf16 run's night-1 names pass answered yes to 0 of 50 questions with 0 thinking tokens on every
  question. K2 closes its low-effort think block at once. The abort rule fired; the q4 run was not started.
- Probe (k2_names_probe.py, commit bf7a76cb2e; box 57692335, RTX 3090): K2-3.7B base, the names questions exactly as names_pass
  builds them on the **Week-1** world (not the test world), days 1-3: 46 questions, 36 linked by a true fact of that message, 10 not.

| way of asking | yes | linked said yes | unlinked said no | accuracy | thinking tokens (mean) | hit the cap |
|---|---|---|---|---|---|---|
| off (today's prompt, block closed) | 0 | 0/36 | 10/10 | 0.217 | 0 | 0 |
| yes/no by log-prob | 1 | 1/36 | 10/10 | 0.239 | 0 | 0 |
| quote the evidence first | 23 | 19/36 | 6/10 | 0.543 | 0 | 0 |
| low effort, 256 (11b) | 0 | 0/36 | 10/10 | 0.217 | 0 | 0 |
| medium effort, 256 | 24 | 24/36 | 10/10 | 0.739 | 217 | 46 |
| high effort, 256 | 27 | 25/36 | 8/10 | 0.717 | 228 | 27 |
| **high effort, 512** | **33** | **32/36** | **9/10** | **0.891** | 315 | 10 |

- High-512 answers are real relations ("lives in Dafosor", "is the mentor of", "owns the boat"); its one false yes is "Gone" /
  "Girl" -> "book title". No reply in any variant was a negative phrase read as yes (the bug-hunt thread's parse_rel warning).
  Qwen3.5-2B answered yes to 38/55 on night 1 of Week-2, so high-512 puts K2 in the same range (suggested; different worlds).

## Fixes (K2 only; Qwen runs unchanged, checked by the selftest)
1. **Names pass thinks fully:** stage 1 opens K2's high-effort block (the template's `reasoning_effort="high"`, `<ifm|think>`, the
   template default), at most 512 greedy thinking tokens on the base, stopping at `</ifm|think>` or the end of the turn. Stage 2
   appends the thinking and `</ifm|think>` (added if stage 1 hit the cap) and generates the answer (greedy, 12 tokens) as before.
2. **Negative replies read as no (K2 only):** a reply whose first line starts with the word no, not, none, nothing, nope or unrelated
   is read as "no" (today only a bare no / none / nope is). 0 of 46 probe replies are affected; it guards the yes counts.
- Every other K2 prompt keeps thinking off. Batch size, memory settings (`SLEEPB_TOK=1024`, expandable segments) as in 11b.

## Abort rule (kept from 11b)
The bf16 run starts first. If its night-1 names pass has yes = 0, the q4 run is not started, the bf16 run is stopped, and the result
is reported as "K2 never answers the names question". Otherwise the q4 run starts on the same code.

## Added to the report (not marks)
Names pass per night: yes, new items, thinking tokens (mean), share capped, and the share of its items that match a ground-truth fact.

## Compute
K2 total cap $3.50 (coordinator, 13:46Z); about $1.10 spent (first try, 11b abort, four probe hosts). Two RTX 5090 runs of about
2.5 h each at about $0.47-0.50/h. If the bf16 run's cost leaves too little for the q4 run, the coordinator is asked before the q4 run.
