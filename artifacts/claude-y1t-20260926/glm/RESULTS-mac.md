# RESULTS-mac — y1t-glm (Mac CPU, GLM 5.3 Flash via OpenRouter)

Label: y1t-glm. Seed: 4027. Target: 2400 dialogs. Result: PARTIAL (1021/2400 raw rows).
Wall time: start Sat Sep 26 17:28:47 UTC 2026 (epoch 1790443727) to Sat Sep 26 19:28:18 UTC 2026 (epoch 1790450898) = 7171 s (~119.5 min, at the 120-min cap).
Device: Mac CPU only. No reader, no rental, no BensPC.

## Step 2 — seeds (verbatim printed line)

{"dialogs": 2400, "turns": 16816, "intents": {"ambiguous_pronoun": 517, "ask": 1253, "backref": 1548, "confirm": 480, "correct": 1586, "doubt": 544, "former": 1271, "hypothetical": 516, "jobhome": 825, "negation_only": 484, "plan": 482, "question": 502, "smalltalk": 652, "someone_else": 468, "teach": 5688}}

Command had no --ask-back, as specified.

## Step 3 — split-seeds (verbatim printed line)

{"dialogs": 2400, "parts": 4}

600 seeds per part (seeds_0..3.jsonl, 600 lines each; seeds.jsonl 2400 lines).

## Step 4 — 4 GLM processes: NO TOTALS PRINTED (partial run, see errors)

No per-process totals line (calls, parsed, tokens, cost_usd) exists: none of the 4 workers printed a totals line before the run ended, so there are no four lines to record. Final log lines verbatim:

- glm_0 last: `[glm320] try 2 failed: HTTPError HTTP Error 402: Payment Required`
- glm_1 last: `[glm320] try 4 failed: HTTPError HTTP Error 402: Payment Required`
- glm_2 last: `[glm320] try 2 failed: HTTPError HTTP Error 402: Payment Required`
- glm_3 last: `[glm320] try 1 failed: HTTPError HTTP Error 402: Payment Required`

Per-log counts (counted from the logs after the run, not script output): glm_0: 207 ok, 98 unparsed, 683 lines mentioning 402; glm_1: 156 ok, 92 unparsed, 603 mentioning 402; glm_2: 137 ok, 85 unparsed, 548 mentioning 402; glm_3: 145 ok, 101 unparsed, 634 mentioning 402. Raw rows: raw_0 305, raw_1 248, raw_2 222, raw_3 246; total raw.jsonl 1021 lines.

Total cost in USD: UNKNOWN (no totals lines printed; sum cannot be computed). Context from the task brief: the lis-320 pilot cost $0.0072 for 30 calls (~$0.60 expected for 2400).

## Step 5 — check (verbatim printed output)

```
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:again": 17,
  "cue:ask:how old": 15,
  "cue:ask:remind me": 28,
  "cue:ask:what": 146,
  "cue:ask:whats": 66,
  "cue:ask:where": 9,
  "cue:ask:who": 72,
  "cue:ask:whos": 2,
  "cue:confirm:?": 13,
  "cue:confirm:check": 63,
  "cue:confirm:correct": 1,
  "cue:confirm:did i say": 5,
  "cue:confirm:did i tell": 2,
  "cue:confirm:right": 36,
  "cue:confirm:was it": 4,
  "cue:doubt:can't remember": 1,
  "cue:doubt:cant remember": 7,
  "cue:doubt:could be": 1,
  "cue:doubt:maybe": 1,
  "cue:doubt:might": 2,
  "cue:doubt:no idea": 1,
  "cue:doubt:not 100% sure": 2,
  "cue:doubt:not certain": 1,
  "cue:doubt:not even sure": 25,
  "cue:doubt:not really sure": 1,
  "cue:doubt:not sure": 58,
  "cue:doubt:not totally sure": 13,
  "cue:doubt:think": 30,
  "cue:doubt:unsure": 1,
  "cue:former:anymore": 29,
  "cue:former:before": 2,
  "cue:former:left": 2,
  "cue:former:no longer": 2,
  "cue:former:quit": 2,
  "cue:former:used to": 245,
  "cue:former:was": 14,
  "cue:hypothetical:hypothetically": 2,
  "cue:hypothetical:if": 107,
  "cue:hypothetical:imagine": 36,
  "cue:hypothetical:pretend": 1,
  "cue:negation_only:n't": 17,
  "cue:negation_only:never": 3,
  "cue:negation_only:no": 5,
  "cue:negation_only:not": 1,
  "cue:negation_only:nt": 82,
  "cue:plan:'ll": 1,
  "cue:plan:going to": 6,
  "cue:plan:gonna": 19,
  "cue:plan:hoping": 3,
  "cue:plan:next": 6,
  "cue:plan:planning": 3,
  "cue:plan:soon": 64,
  "cue:plan:thinking about": 5,
  "cue:plan:thinking of": 2,
  "cue:plan:want to": 3,
  "cue:plan:wants to": 10,
  "cue:plan:will": 2,
  "cue:question:?": 133,
  "cue:someone_else:apparently": 7,
  "cue:someone_else:claims": 2,
  "cue:someone_else:heard": 36,
  "cue:someone_else:mentioned": 3,
  "cue:someone_else:says": 6,
  "cue:someone_else:supposedly": 2,
  "cue:someone_else:told": 53,
  "dialogs": 1021,
  "dialogs_unparsed": 376,
  "drop:assert_hedged": 119,
  "drop:assert_reported": 60,
  "drop:dialog_unparsed": 2641,
  "drop:forbidden_in_reply": 10,
  "drop:forbidden_in_turn": 4,
  "drop:former_present_cue": 41,
  "drop:must_missing": 64,
  "drop:no_cue": 46,
  "drop:no_first_person": 8,
  "drop:no_past_cue": 3,
  "drop:plan_leak": 8,
  "drop:reads_former": 5,
  "drop:ref_word_missing": 4,
  "drop:reply_new_name": 1,
  "drop:role_word_missing": 1,
  "drop:smalltalk_self": 16,
  "drop:stray_name": 6,
  "dropped": 333,
  "dropped:ambiguous_pronoun": 2,
  "dropped:ask": 6,
  "dropped:backref": 52,
  "dropped:confirm": 5,
  "dropped:correct": 19,
  "dropped:doubt": 10,
  "dropped:former": 51,
  "dropped:hypothetical": 4,
  "dropped:jobhome": 1,
  "dropped:negation_only": 6,
  "dropped:plan": 20,
  "dropped:question": 7,
  "dropped:smalltalk": 16,
  "dropped:someone_else": 15,
  "dropped:teach": 119,
  "kept": 4186,
  "recased": 2096,
  "turns": 7160
 },
 "kept_by_family": {
  "ambiguous_pronoun": 140,
  "ask": 358,
  "backref": 363,
  "confirm": 124,
  "correct": 392,
  "doubt": 144,
  "former": 296,
  "hypothetical": 146,
  "jobhome": 215,
  "negation_only": 108,
  "plan": 124,
  "question": 133,
  "smalltalk": 147,
  "someone_else": 109,
  "teach": 1387
 }
}
```

kept.jsonl 4186 lines, drops.jsonl 333 lines.

## Step 6 — items (verbatim printed line)

{"counts": {"asks_kept": 358, "corrected": 14, "items_answerable": 334, "items_never_told": 334, "skip_no_current_fact": 24}, "train_items": 566, "dev_items": 102}

items_train.jsonl 566 lines, items_dev.jsonl 102 lines.

## Errors and deviations

1. INTERPRETER: the task's `python3` (/usr/local/bin/python3, x86_64-only) fails under `nohup` with "Bad CPU type in executable". Per the COMMON RULES (use an ARM Python), all scripts were run with the arm64 interpreter (/Users/ben-hannan/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12), and the 4 GLM workers were started as background processes with per-part logs (no `nohup` wrapper). Still exactly 4 parallel processes, each with its own log (glm_0..3.log). Seed/split/check/items scripts are unchanged.
2. HTTP 402 PAYMENT REQUIRED: partway through the run every OpenRouter call began failing with `HTTP Error 402: Payment Required` (key valid; account out of funds). Early dialogs succeeded; later ones logged "unparsed" after 4 failed tries. Run is therefore partial: 1021/2400 raw rows (645 ok + 376 unparsed).
3. TIME CAP: the 100-minute stop guidance was missed — the supervising tool call timed out at ~117 min and ended the wait; by 19:26 UTC no worker PIDs remained (no PIDs to kill), logs end in 402 retry failures with no totals lines. Steps 5-7 ran on the partial data as specified ("go on with what exists").
4. Key-leak check: `grep -r "sk-or"` over the delivered directory found no match (exit 1). The key was never printed, logged, copied, or placed on a command line.

## Delivered files (artifacts/claude-y1t-20260926/glm/)

seeds.jsonl (2400), raw.jsonl (1021), kept.jsonl (4186), drops.jsonl (333), items/items_train.jsonl (566), items/items_dev.jsonl (102), glm_0.log, glm_1.log, glm_2.log, glm_3.log, RESULTS-mac.md (this file).
