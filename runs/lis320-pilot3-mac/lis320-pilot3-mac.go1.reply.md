Pilot 3 re-run through the new route — setting up the isolated run.
Setup checks passed — now verifying the seed counts.
Selftest passed — now generating the pilot seeds.
The GLM run timed out — checking what completed.
The new route is failing (exit 1 / timeouts) with only partial data — I'll record the partial counts and finish the report.
Partial data secured — writing the final report.
Verdict: INCOMPLETE / FAILED — pilot3 seeds match pilot2 exactly, but the opencode GLM route failed on nearly every call. Partial data saved to `artifacts/claude-lis320-20260926/pilot3/` (PUSH path); watcher can push. Nothing trained.

Common-rules report: additive only (created only `artifacts/claude-lis320-20260926/pilot3/` 8 files, edited nothing, deleted nothing except the temp dir `/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.kiohHwSNBC` which is confirmed gone); fictional names only (seeds use the avoidance lists, no real names written); TEST-ONLY panels never read item-by-item, never tuned on, never quoted; no branch checkout or push by me; no opencode config/auth/key read, printed, copied or committed; helper deleted only sessions it creates (no manual session delete).

Marks table (integer counts):

| step | result |
|---|---|
| origin/main commit | 79032cbd89a16ba1324bdc8380eacedec5a1e35e |
| helper sha | 3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2 match, proceeded |
| selftest | `lis320 glm_oc selftest 4/4 ok`, exit 0 |
| seeds | 60 dialogs, 425 turns; intents ack_after_ask 15, ambiguous_pronoun 9, ask 29, backref 36, confirm 13, correct 40, doubt 9, former 26, hypothetical 10, jobhome 19, negation_only 11, plan 9, question 11, smalltalk 20, someone_else 10, teach 148, yes_after_ask 10 — identical to pilot2, proceeded |
| glm start / end (date -u) | Sat Sep 26 19:30:54 UTC 2026 / Sat Sep 26 20:21:22 UTC 2026 (~50.5 min) |
| glm raw rows | 32 of 60 seeds |
| glm.log lines | 62 |
| "call failed" lines | 30 |
| distinct errors | 27x `exit 1: > build · glm-5.3-flash`; 3x `exit 124: TIMEOUT after 300s:` (each after 3 tries, model opencode-go/glm-5.3-flash) |
| glm last line verbatim | `[glm320] s320-321-00031 unparsed` — NO totals JSON printed (run killed by tool timeout at ~50 min, before --max-minutes 45 graceful stop) |
| calls per minute | NOT AVAILABLE (no totals); partial 32 rows / 50.5 min = 0.63 rows/min |
| check (exit 0, partial 32-row raw) | dialogs 32, dialogs_unparsed 30, turns 228, kept 14, dropped 1, drop:dialog_unparsed 213, drop:no_cue 1, dropped:someone_else 1; kept_by_family ask 2, backref 2, former 1, question 1, someone_else 1, teach 7; cues ask:remind-me 1, ask:whats 1, former:used-to 1, question:? 1, someone_else:told 1; recased 0 |
| kept / drops lines | 14 / 1 |
| style printed line (exit 0) | glm_kept turns 14, words_median 18, words_p90 38, lowercase_start 1.0, noapos_contraction 0.571, over20_words 0.357, shapes_per_100 100.0, write_facts_per_turn 1.0, write_facts_in_over20 0.286; dev_chatdev turns 336; dev_bank turns 194 (full line in RESULTS.md) |
| pilot2 comparison | seeds identical; glm/check/style NOT comparable (pilot2: 60 calls, 59 parsed, 390 kept) |
| files in PUSH dir | seeds.jsonl 60, raw.jsonl 32, kept.jsonl 14, drops.jsonl 1, check.json 26 lines, style.json 31 lines, glm.log 62, RESULTS.md 78 |

Every move: fetch origin/main; archive to temp dir + builder-outbox helper; sha verified; selftest ok; seeds generated and matched; glm run 4 workers (killed by timeout, partial kept); check + style on partial; copied 7 files + wrote RESULTS.md to worktree pilot3/; rm -rf temp dir confirmed gone (`ls` = No such file or directory).

Every miss / deviation: step 3 never finished — 32/60 dialogs in ~50.5 min vs pilot2's ~7 min for 60; no totals line so specified calls-per-minute is uncomputable; no KeyLeak abort; no extra diagnostic opencode calls; exceeded the 45-min glm flag and used ~50.5 of the 60-min cap.

What it means in plain high-school English: the seed list is fine and identical to last time, but the new free route to the wording model is broken right now — almost every request errors out or hangs for 5 minutes. So we do NOT have a valid pilot3 and must NOT start any full run on this route until the `exit 1: > build · glm-5.3-flash` failure is fixed. What it doesn't mean: it says nothing about the model quality or the seeds — this is a plumbing failure, not a science result. Counts above are from a 32-row partial and must not be compared to pilot2's 60-row thresholds.
