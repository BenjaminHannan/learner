# lis320 pilot4 RESULTS (label: lis320-pilot4)

## Run identity
- origin/main commit: 0ab7810308ef608a60f6e097e894bb1f226e97a3
- Label: lis320-pilot4. GPU: no (Mac CPU). Route: Ben's opencode subscription, scripts/claude_lis320_glm_oclow.py (--variant low, unchanged).
- Calls: 60 wording + 1 leak-check = 61 opencode calls. Cost: $0.
- Common rules followed: additive only (new pilot4/ dir + files, no edits/deletes), fictional names (seed generator), TEST-ONLY panels never read, report in final reply.

## Seals (both OK)
- SEAL-ADDENDA-5.sha256.txt: 6/6 OK (ADDENDUM-5-owner-reach-and-correct-ref.md, seed_cr, check_cr, glm_oc11, glm_opencode_v11, reachcount).
- SEAL-ADDENDA-6.sha256.txt: 6/6 OK (ADDENDUM-6-route-low.md, glm_oclow, glm_oc, glm, style, glm_leakcheck).

## Selftests (all ok/OK)
- glm_oclow selftest: `[glm320] s320-1-00000 ok`, `s320-1-00001 unparsed`, `s320-1-00002 ok`, `s320-1-00003 ok`, `s320-1-00004 ok`, `lis320 glm_oc selftest 4/4 ok`, `lis320 glm_oclow selftest ok (variant low on the run line; no network)`.
- seed_cr selftest: `seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}`.
- check_cr selftest: `check_cr selftest OK: 1 kept (owner from history), 1 dropped (owner named)`.
- rawcheck selftest: `lis320 rawcheck selftest 4/4 ok`.

## Leak check (1 call, exit 0)
- `{"exit": 0, "reply_ok": true, "left_after_cleanup": 0}`

## Seeds (seed 323, n 60, --ask-back)
- `{"dialogs": 60, "turns": 419, "intents": {"ack_after_ask": 10, "ambiguous_pronoun": 12, "ask": 28, "backref": 32, "confirm": 10, "correct": 28, "correct_ref": 26, "doubt": 11, "former": 29, "hypothetical": 9, "jobhome": 22, "negation_only": 9, "plan": 7, "question": 8, "smalltalk": 16, "someone_else": 16, "teach": 136, "yes_after_ask": 10}}`

## Share / timing
- Share check: `date -u` Sat Sep 26 22:06:45 UTC 2026; `uptime` 18:06 up 3 days, 7:59, 4 users, load averages 56.19 41.82 39.58; N=8 (`pgrep -f "opencode run"`), W=6 (min(16-8, 6)).
- Wording start: Sat Sep 26 22:06:50 UTC 2026. Wording end: Sat Sep 26 22:09:57 UTC 2026. End `uptime`: 18:09 up 3 days, 8:03, 4 users, load averages 75.26 58.01 46.85.
- Wording totals (last line of glm.log, verbatim): `{"calls": 60, "parsed": 58, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 3.1}`
- `grep -c "call failed" glm.log` = 0. No distinct errors (no error lines).
- Dialogs per minute: 60 calls / 3.1 min = 19.4.
- raw.jsonl rows: 60. seeds.jsonl rows: 60.

## Rawcheck (exit 0)
- `{"rawcheck": "OK", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "not_in_seeds": 0}`

## check_cr (exit 0) — check.json verbatim counts
- counts: cue:ask:again 3, cue:ask:how old 1, cue:ask:remind me 3, cue:ask:what 16, cue:ask:whats 2, cue:ask:who 2, cue:ask:whos 1, cue:confirm:check 6, cue:confirm:right 2, cue:doubt:cant remember 2, cue:doubt:idk 1, cue:doubt:not even sure 1, cue:doubt:not sure 6, cue:doubt:think 1, cue:former:anymore 2, cue:former:before 1, cue:former:last 1, cue:former:used to 16, cue:hypothetical:if 7, cue:hypothetical:imagine 2, cue:negation_only:n't 3, cue:negation_only:no 2, cue:negation_only:nt 3, cue:plan:gonna 2, cue:plan:planning 1, cue:plan:soon 3, cue:question:? 7, cue:someone_else:apparently 1, cue:someone_else:claimed 1, cue:someone_else:claims 1, cue:someone_else:heard 3, cue:someone_else:mentioned 1, cue:someone_else:said 1, cue:someone_else:supposedly 1, cue:someone_else:told 6, dialogs 60, dialogs_unparsed 2, drop:assert_hedged 13, drop:assert_reported 2, drop:dialog_unparsed 14, drop:forbidden_in_reply 3, drop:forbidden_in_turn 2, drop:former_present_cue 7, drop:must_missing 10, drop:no_cue 1, drop:plan_leak 4, drop:reply_ask_missing 1, drop:reply_new_name 1, drop:smalltalk_self 2, drop:stray_name 1, dropped 43, dropped:ack_after_ask 1, dropped:backref 4, dropped:confirm 1, dropped:correct 2, dropped:correct_ref 4, dropped:former 9, dropped:jobhome 3, dropped:negation_only 1, dropped:question 1, dropped:smalltalk 2, dropped:someone_else 1, dropped:teach 14, kept 362, recased 164, turns 419.
- kept_by_family: ack_after_ask 9, ambiguous_pronoun 12, ask 28, backref 26, confirm 8, correct 24, correct_ref 22, doubt 11, former 20, hypothetical 9, jobhome 18, negation_only 8, plan 6, question 7, smalltalk 14, someone_else 15, teach 116, yes_after_ask 9.
- kept.jsonl rows: 362. drops.jsonl rows: 43.

## Style (exit 0) — printed line verbatim
- `{"glm_kept": {"turns": 362, "words_median": 19, "words_p90": 29, "lowercase_start": 0.994, "noapos_contraction": 0.461, "over20_words": 0.406, "shapes_per_100": 100.0, "write_facts_per_turn": 0.964, "write_facts_in_over20": 0.53}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}`

## Errors / deviations
- None. No stop conditions hit. No flags added or changed. No opencode config/auth/key read, printed, copied or committed. Temp tree removed after copy.
