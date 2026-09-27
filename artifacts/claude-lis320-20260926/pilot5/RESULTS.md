# lis320-pilot5 RESULTS (2026-09-26)

Label: lis320-pilot5
origin/main: 1f6d336dd5293b1a3a6044734c0a6c2e747c9009
Route: Ben's opencode subscription, GLM 5.3 Flash wording via scripts/claude_lis320_glm_oclow.py (--variant low inside script, unchanged)
GPU: no (Mac CPU). Cost: $0.

## 1. TREE
- D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.q0XocW72He
- Archive: git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-20260924 | tar -x -C $D
- O=artifacts/claude-lis320-20260926/pilot5
- git rev-parse origin/main => 1f6d336dd5293b1a3a6044734c0a6c2e747c9009

## 2. SEALS (all OK)
- SEAL-ADDENDA-5.sha256.txt: all OK
  - artifacts/claude-lis320-20260926/ADDENDUM-5-owner-reach-and-correct-ref.md: OK
  - scripts/claude_lis320_seed_cr.py: OK
  - scripts/claude_lis320_check_cr.py: OK
  - scripts/claude_lis320_glm_oc11.py: OK
  - scripts/claude_glm_opencode_v11.py: OK
  - scripts/claude_lis320_reachcount.py: OK
- SEAL-ADDENDA-6.sha256.txt: all OK
  - artifacts/claude-lis320-20260926/ADDENDUM-6-route-low.md: OK
  - scripts/claude_lis320_glm_oclow.py: OK
  - scripts/claude_lis320_glm_oc.py: OK
  - scripts/claude_lis320_glm.py: OK
  - scripts/claude_lis320_style.py: OK
  - scripts/claude_glm_leakcheck.py: OK
- SEAL-ADDENDA-7.sha256.txt: all OK
  - artifacts/claude-lis320-20260926/ADDENDUM-7-group-speaker-check.md: OK
  - scripts/claude_lis320_check_we.py: OK
  - scripts/claude_lis320_check_cr.py: OK
  - scripts/claude_lis320_check.py: OK
  - scripts/claude_lis320_seed_cr.py: OK
  - scripts/claude_lis320_glm_oclow.py: OK

## 3. SELFTESTS (all ok/OK)
- scripts/claude_lis320_glm_oclow.py --selftest:
  - [glm320] s320-1-00000 ok
  - [glm320] s320-1-00001 unparsed
  - [glm320] s320-1-00002 ok
  - [glm320] s320-1-00003 ok
  - [glm320] s320-1-00004 ok
  - lis320 glm_oc selftest 4/4 ok
  - lis320 glm_oclow selftest ok (variant low on the run line; no network)
- scripts/claude_lis320_seed_cr.py --selftest:
  - seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
- scripts/claude_lis320_check_cr.py --selftest:
  - check_cr selftest OK: 1 kept (owner from history), 1 dropped (owner named)
- scripts/claude_lis320_check_we.py --selftest:
  - check_we selftest OK: 1 kept, 1 dropped (group_speaker)
- scripts/claude_lis320_rawcheck.py --selftest:
  - lis320 rawcheck selftest 4/4 ok

## 4. LEAK CHECK (one call)
- cmd: scripts/claude_glm_leakcheck.py --worktree /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
- output: {"exit": 0, "reply_ok": true, "left_after_cleanup": 0}
- exit code: 0

## 5. SEEDS
- cmd: scripts/claude_lis320_seed_cr.py --seed 325 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl
- output: {"dialogs": 60, "turns": 428, "intents": {"ack_after_ask": 12, "ambiguous_pronoun": 8, "ask": 17, "backref": 41, "confirm": 9, "correct": 32, "correct_ref": 10, "doubt": 11, "former": 35, "hypothetical": 13, "jobhome": 19, "negation_only": 10, "plan": 10, "question": 13, "smalltalk": 19, "someone_else": 8, "teach": 143, "yes_after_ask": 18}}

## 6. SHARE
- date -u (before wording): Sat Sep 26 23:50:55 UTC 2026
- uptime (before wording): 19:50  up 3 days,  9:43, 4 users, load averages: 78.95 75.58 73.05
- N (pgrep -f "opencode run" | wc -l): 11
- W (16-N capped to 6): 5

## 7. WORDING
- date -u (start): Sat Sep 26 23:50:58 UTC 2026
- cmd: scripts/claude_lis320_glm_oclow.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 5 --max-minutes 40 > $O/glm.log 2>&1
- date -u (end): Sat Sep 26 23:58:25 UTC 2026
- uptime (end): 19:58  up 3 days,  9:51, 4 users, load averages: 70.62 71.00 72.32
- elapsed: ~7.45 min wall; script minutes: 7.4
- last line of glm.log verbatim: {"calls": 60, "parsed": 55, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 7.4}
- count of "call failed" lines in glm.log: 0
- distinct errors: none
- wc: 60 seeds.jsonl, 60 raw.jsonl
- dialogs per minute: 60/7.4 = 8.108108108108107
- parsed per minute: 55/7.4 = 7.4324324324324325

## 8. RAWCHECK
- cmd: scripts/claude_lis320_rawcheck.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl
- output: {"rawcheck": "OK", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "not_in_seeds": 0}

## 9. CHECK_WE + STYLE
- cmd: scripts/claude_lis320_check_we.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $O/check.json
- check.json verbatim:
{
 "counts": {
  "cue:ask:how old": 1,
  "cue:ask:what": 5,
  "cue:ask:whats": 3,
  "cue:ask:where": 1,
  "cue:ask:who": 3,
  "cue:confirm:check": 6,
  "cue:confirm:right": 3,
  "cue:doubt:dont remember": 1,
  "cue:doubt:dunno": 1,
  "cue:doubt:not even sure": 1,
  "cue:doubt:not sure": 5,
  "cue:doubt:not totally sure": 1,
  "cue:doubt:think": 1,
  "cue:former:anymore": 4,
  "cue:former:quit": 1,
  "cue:former:used to": 16,
  "cue:former:was": 1,
  "cue:hypothetical:if": 10,
  "cue:hypothetical:imagine": 2,
  "cue:negation_only:n't": 2,
  "cue:negation_only:no": 3,
  "cue:negation_only:nt": 5,
  "cue:plan:gonna": 1,
  "cue:plan:soon": 4,
  "cue:plan:wants to": 1,
  "cue:question:?": 13,
  "cue:someone_else:apparently": 1,
  "cue:someone_else:heard": 1,
  "cue:someone_else:told": 1,
  "dialogs": 60,
  "dialogs_unparsed": 5,
  "drop:ack_answers": 1,
  "drop:assert_hedged": 13,
  "drop:assert_reported": 9,
  "drop:dialog_unparsed": 35,
  "drop:forbidden_in_reply": 2,
  "drop:former_present_cue": 8,
  "drop:group_speaker": 18,
  "drop:must_missing": 7,
  "drop:no_cue": 4,
  "drop:no_first_person": 2,
  "drop:plan_leak": 4,
  "drop:reply_ask_missing": 4,
  "drop:smalltalk_self": 3,
  "drop:stray_name": 3,
  "drop:yes_missing": 1,
  "dropped": 66,
  "dropped:ack_after_ask": 3,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 3,
  "dropped:backref": 9,
  "dropped:correct": 2,
  "dropped:doubt": 1,
  "dropped:former": 9,
  "dropped:jobhome": 2,
  "dropped:plan": 2,
  "dropped:smalltalk": 3,
  "dropped:someone_else": 3,
  "dropped:teach": 22,
  "dropped:yes_after_ask": 6,
  "kept": 327,
  "recased": 171,
  "turns": 428
 },
 "kept_by_family": {
  "ack_after_ask": 9,
  "ambiguous_pronoun": 7,
  "ask": 13,
  "backref": 28,
  "confirm": 9,
  "correct": 27,
  "correct_ref": 9,
  "doubt": 10,
  "former": 22,
  "hypothetical": 12,
  "jobhome": 14,
  "negation_only": 10,
  "plan": 6,
  "question": 13,
  "smalltalk": 12,
  "someone_else": 3,
  "teach": 112,
  "yes_after_ask": 11
 }
}
- wc: 327 kept.jsonl, 66 drops.jsonl
- style printed line verbatim: {"glm_kept": {"turns": 327, "words_median": 19, "words_p90": 29, "lowercase_start": 0.994, "noapos_contraction": 0.434, "over20_words": 0.398, "shapes_per_100": 100.0, "write_facts_per_turn": 1.012, "write_facts_in_over20": 0.529}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}

## 10. FILES
- artifacts/claude-lis320-20260926/pilot5/seeds.jsonl (60 lines)
- artifacts/claude-lis320-20260926/pilot5/raw.jsonl (60 lines)
- artifacts/claude-lis320-20260926/pilot5/kept.jsonl (327 lines)
- artifacts/claude-lis320-20260926/pilot5/drops.jsonl (66 lines)
- artifacts/claude-lis320-20260926/pilot5/check.json
- artifacts/claude-lis320-20260926/pilot5/style.json
- artifacts/claude-lis320-20260926/pilot5/glm.log (61 lines)
- this RESULTS.md (counts only; no reply text quoted)

## ERRORS / DEVIATIONS
- None. All seals OK. All selftests OK. Leak check exit 0. Wording exit 0 with 0 failed_calls and 0 "call failed" lines. Rawcheck OK. No flags added or changed. Python run as uv run --offline --no-project --python 3.12 python -B. No opencode config read. No branch checkout or push by agent.
- Note: share wait loop not needed (W=5 >= 1).
- Note: 5 dialogs unparsed (35 turns dropped as dialog_unparsed); 55/60 parsed.
