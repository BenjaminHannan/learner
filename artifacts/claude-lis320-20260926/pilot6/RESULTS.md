# lis320 pilot6 RESULTS (label lis320-pilot6)

## Provenance
- origin/main commit: dd55fca2f79a302d055cb96b9a42b47a1130f92a
- tmp dir: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.ajcbxnUwPs (removed after copy; see cleanup)
- worktree: /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
- out dir: artifacts/claude-lis320-20260926/pilot6/
- files: seeds.jsonl (60 lines), raw.jsonl (60 lines), kept.jsonl (311 lines), drops.jsonl (68 lines), check.json, style.json, glm.log (61 lines)

## Seals (all OK)
- SEAL-ADDENDA-5: ADDENDUM-5-owner-reach-and-correct-ref.md OK; scripts/claude_lis320_seed_cr.py OK; scripts/claude_lis320_check_cr.py OK; scripts/claude_lis320_glm_oc11.py OK; scripts/claude_glm_opencode_v11.py OK; scripts/claude_lis320_reachcount.py OK
- SEAL-ADDENDA-6: ADDENDUM-6-route-low.md OK; scripts/claude_lis320_glm_oclow.py OK; scripts/claude_lis320_glm_oc.py OK; scripts/claude_lis320_glm.py OK; scripts/claude_lis320_style.py OK; scripts/claude_glm_leakcheck.py OK
- SEAL-ADDENDA-7: ADDENDUM-7-group-speaker-check.md OK; scripts/claude_lis320_check_we.py OK; scripts/claude_lis320_check_cr.py OK; scripts/claude_lis320_check.py OK; scripts/claude_lis320_seed_cr.py OK; scripts/claude_lis320_glm_oclow.py OK
- SEAL-ADDENDA-8: ADDENDUM-8-group-check-narrowed.md OK; scripts/claude_lis320_check_we2.py OK; scripts/claude_lis320_check_cr.py OK; scripts/claude_lis320_check.py OK; scripts/claude_lis320_seed_cr.py OK; scripts/claude_lis320_glm_oclow.py OK

## Selftests (all ok/OK)
- scripts/claude_lis320_glm_oclow.py --selftest: `lis320 glm_oclow selftest ok (variant low on the run line; no network)` (glm320 selftest lines: s320-1-00000 ok, s320-1-00001 unparsed, s320-1-00002 ok, s320-1-00003 ok, s320-1-00004 ok; `lis320 glm_oc selftest 4/4 ok`)
- scripts/claude_lis320_seed_cr.py --selftest: `seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}`
- scripts/claude_lis320_check_cr.py --selftest: `check_cr selftest OK: 1 kept (owner from history), 1 dropped (owner named)`
- scripts/claude_lis320_check_we.py --selftest: `check_we selftest OK: 1 kept, 1 dropped (group_speaker)`
- scripts/claude_lis320_check_we2.py --selftest: `check_we2 selftest OK: 1 kept, 1 dropped (group_speaker); bare 'me and' no longer drops`
- scripts/claude_lis320_rawcheck.py --selftest: `lis320 rawcheck selftest 4/4 ok`

## Leak check (one call)
- command: scripts/claude_glm_leakcheck.py --worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
- printed JSON line verbatim: `{"exit": 0, "reply_ok": true, "left_after_cleanup": 0}`
- exit code: 0 (not 2/3; continued)

## Seeds
- command: scripts/claude_lis320_seed_cr.py --seed 326 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl
- printed counts verbatim: `{"dialogs": 60, "turns": 423, "intents": {"ack_after_ask": 20, "ambiguous_pronoun": 14, "ask": 27, "backref": 23, "confirm": 8, "correct": 31, "correct_ref": 21, "doubt": 7, "former": 23, "hypothetical": 21, "jobhome": 10, "negation_only": 8, "plan": 15, "question": 17, "smalltalk": 10, "someone_else": 6, "teach": 145, "yes_after_ask": 17}}`

## Share slot
- date -u (before wording): Sun Sep 27 00:38:14 UTC 2026
- uptime (before wording): 20:38  up 3 days, 10:31, 4 users, load averages: 86.45 81.03 87.62
- N (pgrep -f "opencode run" count): 11
- W (workers): 5 (16-11=5, capped at 6; >=1 so no wait)

## Wording
- date -u start: Sun Sep 27 00:38:16 UTC 2026
- command: scripts/claude_lis320_glm_oclow.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 5 --max-minutes 40 > $O/glm.log 2>&1
- date -u end: Sun Sep 27 00:41:56 UTC 2026
- uptime end: 20:41  up 3 days, 10:35, 4 users, load averages: 52.00 71.62 82.54
- totals JSON (last line of glm.log verbatim): `{"calls": 60, "parsed": 54, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 3.7}`
- count of "call failed" lines in glm.log: 0
- first line of each distinct error: none (no errors)
- unparsed lines in glm.log: 6 (s320cr-326-00001, s320cr-326-00005, s320cr-326-00016, s320cr-326-00025, s320cr-326-00045, s320cr-326-00046)
- dialogs per minute: 60 / 3.7 = 16.216216216216214

## Rawcheck
- printed line verbatim: `{"rawcheck": "OK", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "not_in_seeds": 0}`
- no ROUTE-MISMATCH; continued

## Keeper check (check_we2) + style
- check.json verbatim:
{"counts": {"cue:ask:again": 2, "cue:ask:how old": 1, "cue:ask:what": 10, "cue:ask:whats": 6, "cue:ask:where": 1, "cue:ask:who": 4, "cue:confirm:check": 2, "cue:confirm:right": 5, "cue:doubt:idk": 1, "cue:doubt:not sure": 2, "cue:doubt:think": 2, "cue:former:anymore": 2, "cue:former:used to": 12, "cue:hypothetical:if": 12, "cue:hypothetical:imagine": 5, "cue:negation_only:not": 1, "cue:negation_only:nt": 4, "cue:plan:going to": 1, "cue:plan:gonna": 5, "cue:plan:soon": 2, "cue:plan:thinking about": 2, "cue:plan:thinking of": 1, "cue:question:?": 15, "cue:someone_else:heard": 1, "cue:someone_else:mentioned": 1, "cue:someone_else:told": 4, "dialogs": 60, "dialogs_unparsed": 6, "drop:ack_answers": 4, "drop:assert_hedged": 15, "drop:assert_reported": 5, "drop:dialog_unparsed": 44, "drop:forbidden_in_turn": 3, "drop:former_present_cue": 2, "drop:group_speaker": 18, "drop:must_missing": 17, "drop:no_cue": 5, "drop:no_first_person": 1, "drop:plan_leak": 1, "drop:ref_word_missing": 1, "drop:reply_ask_missing": 2, "drop:reply_new_name": 2, "drop:role_word_missing": 1, "drop:smalltalk_self": 1, "drop:stray_name": 1, "dropped": 68, "dropped:ack_after_ask": 6, "dropped:ambiguous_pronoun": 1, "dropped:ask": 2, "dropped:backref": 3, "dropped:confirm": 1, "dropped:correct": 5, "dropped:correct_ref": 4, "dropped:former": 5, "dropped:hypothetical": 2, "dropped:plan": 4, "dropped:smalltalk": 1, "dropped:teach": 34, "kept": 311, "recased": 146, "turns": 423}, "kept_by_family": {"ack_after_ask": 12, "ambiguous_pronoun": 10, "ask": 24, "backref": 18, "confirm": 7, "correct": 21, "correct_ref": 17, "doubt": 5, "former": 14, "hypothetical": 17, "jobhome": 8, "negation_only": 5, "plan": 11, "question": 15, "smalltalk": 9, "someone_else": 6, "teach": 96, "yes_after_ask": 16}}
- full check.json and style.json are in this directory (check.json, style.json).
- printed style line verbatim: `{"glm_kept": {"turns": 311, "words_median": 18, "words_p90": 26, "lowercase_start": 1.0, "noapos_contraction": 0.405, "over20_words": 0.354, "shapes_per_100": 100.0, "write_facts_per_turn": 0.852, "write_facts_in_over20": 0.426}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}`

## Key counts summary
- seeds: 60 dialogs, 423 turns; correct_ref seeded 21
- wording: 60 calls, 54 parsed, 0 skipped, 0 failed_calls, 2 batches, 3.7 minutes
- rawcheck: OK, 60 rows, 0 duplicates, 60 model_ok, 60 temperature_null, 0 not_in_seeds
- keeper: 311 kept / 423 turns; 68 dropped (drop:dialog_unparsed 44 incl. 6 unparsed dialogs; drop:group_speaker 18); correct_ref kept 17 / dropped 4
- style: glm_kept 311 turns, words_median 18, words_p90 26 (counts only; no GLM text quoted)

## Errors / deviations
- none. No stop conditions hit. No flags added/changed (--variant low stayed inside scripts/claude_lis320_glm_oclow.py). Python run via `uv run --offline --no-project --python 3.12 python -B`. No opencode config/auth read, printed, copied or committed. No branches checked out or pushed. TEST-ONLY panels never read. Fictional names only (seed generator with avoid lists). GPU: no (Mac CPU). Cost $0 (Ben's opencode subscription route).

## Cleanup
- tmp dir removed: rm -rf /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.ajcbxnUwPs (confirmed gone; see final reply)
