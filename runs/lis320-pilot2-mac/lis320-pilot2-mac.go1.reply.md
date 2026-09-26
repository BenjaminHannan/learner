Starting your 60-row pilot run — pulling instructions and staging the workspace.
Staging complete — now generating the 60 dialog seeds.
GLM wording done — now running the code checks and style scoring.
Checks passed — writing the results file and cleaning up.
Done. Verdict: pilot2 complete, all steps exit 0.

Common-rules compliance: additive only (new files in `artifacts/claude-lis320-20260926/pilot2/` only, no edits/deletes); fictional names only (code-generated seeds, I wrote no names); TEST-ONLY panels never read item-by-item or quoted (only used `avoid_test.sha256` hash list as a flag); no checkout/push by me; key never printed/logged/copied (script read `~/.config/openrouter/key` itself; leak-check 0 hits).

Moves:
- `git fetch -q origin main`; `git archive origin/main ... | tar -x -C $D` (D=/var/folders/.../tmp.HPo7PxXH8i), O=pilot2; all scripts present.
- step 2 seed: `python3 -B scripts/claude_lis320_seed.py --seed 321 --n 60 --ask-back ...` → verbatim: {"dialogs": 60, "turns": 425, "intents": {"ack_after_ask": 15, "ambiguous_pronoun": 9, "ask": 29, "backref": 36, "confirm": 13, "correct": 40, "doubt": 9, "former": 26, "hypothetical": 10, "jobhome": 19, "negation_only": 11, "plan": 9, "question": 11, "smalltalk": 20, "someone_else": 10, "teach": 148, "yes_after_ask": 10}}
- step 3 GLM 60 calls → verbatim: {"calls": 60, "parsed": 59, "prompt_tokens": 75609, "completion_tokens": 19387, "cost_usd": 0.0148, "skipped": 0}. 1 unparsed (s320-321-00012), 0 dialogs failed 4x/skipped.
- step 4 check → kept 390 / dropped 29 / turns 425, recased 179, dialogs_unparsed 1 (full JSON in RESULTS.md, kept_by_family: ack_after_ask 11, ambiguous_pronoun 9, ask 29, backref 32, confirm 13, correct 37, doubt 7, former 22, hypothetical 8, jobhome 19, negation_only 11, plan 9, question 11, smalltalk 17, someone_else 9, teach 137, yes_after_ask 9).
- step 5 style → verbatim: {"glm_kept": {"turns": 390, "words_median": 16, "words_p90": 23, "lowercase_start": 0.995, "noapos_contraction": 0.323, "over20_words": 0.213, "shapes_per_100": 100.0, "write_facts_per_turn": 0.995, "write_facts_in_over20": 0.312}, "dev_chatdev": {...}, "dev_bank": {...}} (full in RESULTS.md).
- copied seeds/raw/kept/drops/style + RESULTS.md to worktree `artifacts/claude-lis320-20260926/pilot2/` (60/60/390/29 lines verified); `rm -rf "$D"` confirmed gone (`No such file or directory`).

Counts/cost/time: total cost USD 0.0148 (prompt 75,609 + completion 19,387 tokens). Wall ~7 min (start 17:28:39 UTC, GLM 17:28:50–17:34:59 UTC, done 17:35:09 UTC), under 40-min cap. Label lis320-pilot2. Errors: none besides the 1 unparsed dialog. Misses/deviations: used plain `python3 -B` from task (worked, 3.9.6) instead of uv wrapper; no other deviation.

What it means in plain English: the second test batch finished cheaply and fast; about 9 in 10 chat lines passed the automatic checks, and the one bad dialog was just a formatting miss, not a cost blowout. Nothing was trained.

PUSH: artifacts/claude-lis320-20260926/pilot2
