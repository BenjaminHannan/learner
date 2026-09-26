Starting your lis320 pilot — fetching sources and measuring GLM cost.
Seeds ready (30 dialogs). Now running the 30 GLM chats.
Checks passed (182 kept). Now packaging results and cleaning up.
Done. Pilot complete — all files in worktree, nothing pushed (watcher pushes PUSH path).

PUSH: artifacts/claude-lis320-20260926/pilot (seeds.jsonl, raw.jsonl, kept.jsonl, drops.jsonl, style.json, RESULTS.md)

Seed: `{"dialogs": 30, "turns": 211, "intents": {"ambiguous_pronoun": 9, "ask": 13, "backref": 27, "confirm": 5, "correct": 13, "doubt": 8, "former": 12, "hypothetical": 7, "jobhome": 17, "negation_only": 4, "plan": 6, "question": 4, "smalltalk": 12, "someone_else": 4, "teach": 70}}`

GLM (30 calls, GLM 5.3 Flash): 29 ok, 1 unparsed (s320-320-00016); `{"calls": 30, "parsed": 29, "prompt_tokens": 34066, "completion_tokens": 8946, "cost_usd": 0.0072, "skipped": 0}`. Calls failing 4x: 0. Total cost: **$0.0072**.

Check: dialogs 30, dialogs_unparsed 1, dropped 21, kept 182, recased 34, turns 211. Drops: assert_hedged 2, dialog_unparsed 8, former_present_cue 3, must_missing 2, no_cue 10, no_first_person 1, no_past_cue 1, smalltalk_self 2. Dropped by family: ask 5, backref 1, confirm 1, doubt 4, former 5, jobhome 1, plan 1, smalltalk 2, teach 1. Kept by family: ambiguous_pronoun 9, ask 8, backref 23, confirm 4, correct 13, doubt 2, former 7, hypothetical 6, jobhome 16, negation_only 4, plan 5, question 4, smalltalk 10, someone_else 4, teach 67.

Style: `glm_kept {turns 182, words_median 14, words_p90 19, lowercase_start 0.962, noapos_contraction 0.308, over20_words 0.049, shapes_per_100 100.0, write_facts_per_turn 1.06, write_facts_in_over20 0.052}` vs dev_chatdev {turns 336, median 14, p90 23, lower 1.0, noapos 0.253, over20 0.131, shapes 99.1} vs dev_bank {turns 194, median 15, p90 21, lower 0.887, noapos 0.021, over20 0.108, shapes 100.0}.

Wall time: start 16:59:43 UTC, glm 16:59:53–17:04:34 UTC (~4m41s), done 17:04:42 UTC; ~5 min total, under 40-min cap. Errors: none (all exits 0).

Rules kept: additive only (new pilot/ dir files only); fictional names (script-generated); TEST-ONLY panels never read; key never printed/echoed/logged (grep for `sk-or` clean in outputs); Mac CPU only, no reader/rental/BensPC; temp dir `/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.xm4M8tYDVk` removed — confirmed GONE.
