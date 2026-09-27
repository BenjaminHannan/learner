# lis320-pilot7 RESULTS (counts only)

Label: lis320-pilot7
GPU: no (Mac CPU; 60 GPT-6 Luna wording calls plus 1 selftest call through Ben's Codex plan via scripts/claude_luna_codex.py; $0). No reader, no rental, no BensPC, no OpenRouter, no opencode.
origin/main commit: 8e2590aa8a8b6b4f1ba2ba8388300384b52d2137
TIME CAP: 60 minutes. DISK: 1. LOAD-LIGHT: yes (workers 3).
Rules followed: additive only (new pilot7 files only), fictional names only, TEST-ONLY panels never read, never opened own worktree scripts (all runs from git-archive copy in temp dir), never checked out or pushed a branch, never read/printed/copied anything under ~/.codex or any key/auth file, helper sandbox unchanged, python as `uv run --offline --no-project --python 3.12 python -B`.

## 1. TREE
- `git fetch -q origin main` then `git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-20260924 | tar -x -C $D`
- D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.s26f5jEDyZ
- O=artifacts/claude-lis320-20260926/pilot7 (mkdir -p in $D)
- `git rev-parse origin/main` = 8e2590aa8a8b6b4f1ba2ba8388300384b52d2137

## 2. SEALS (all OK, run from $D)
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-6.sha256.txt`:
  - artifacts/claude-lis320-20260926/ADDENDUM-6-route-low.md: OK
  - scripts/claude_lis320_glm_oclow.py: OK
  - scripts/claude_lis320_glm_oc.py: OK
  - scripts/claude_lis320_glm.py: OK
  - scripts/claude_lis320_style.py: OK
  - scripts/claude_glm_leakcheck.py: OK
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-8.sha256.txt`:
  - artifacts/claude-lis320-20260926/ADDENDUM-8-group-check-narrowed.md: OK
  - scripts/claude_lis320_check_we2.py: OK
  - scripts/claude_lis320_check_cr.py: OK
  - scripts/claude_lis320_check.py: OK
  - scripts/claude_lis320_seed_cr.py: OK
  - scripts/claude_lis320_glm_oclow.py: OK
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-9.sha256.txt`:
  - artifacts/claude-lis320-20260926/ADDENDUM-9-luna-writer.md: OK
  - scripts/claude_luna_codex.py: OK
  - scripts/claude_lis320_luna.py: OK
  - scripts/claude_lis320_rawcheck2.py: OK
  - scripts/claude_lis320_glm_oc.py: OK
  - scripts/claude_lis320_glm.py: OK
  - scripts/claude_lis320_check_we2.py: OK
  - scripts/claude_lis320_seed_cr.py: OK

## 3. SELFTESTS (each run from $D as `uv run --offline --no-project --python 3.12 python -B <script> --selftest`)
- scripts/claude_lis320_luna.py --selftest:
  - lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)
  - EXIT:0
- scripts/claude_lis320_seed_cr.py --selftest:
  - seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
  - EXIT:0
- scripts/claude_lis320_check_we2.py --selftest:
  - check_we2 selftest OK: 1 kept, 1 dropped (group_speaker); bare 'me and' no longer drops
  - EXIT:0
- scripts/claude_lis320_rawcheck2.py --selftest:
  - lis320 rawcheck2 selftest 7/7 ok
  - EXIT:0
- scripts/claude_luna_codex.py --selftest (the ONE live call):
  - selftest ok: model gpt-6-luna, output-file True
  - EXIT:0

## 4. SEEDS
Command: scripts/claude_lis320_seed_cr.py --seed 327 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl
Printed verbatim:
{"dialogs": 60, "turns": 425, "intents": {"ack_after_ask": 17, "ambiguous_pronoun": 11, "ask": 20, "backref": 30, "confirm": 5, "correct": 24, "correct_ref": 23, "doubt": 17, "former": 30, "hypothetical": 13, "jobhome": 14, "negation_only": 8, "plan": 11, "question": 5, "smalltalk": 19, "someone_else": 18, "teach": 143, "yes_after_ask": 17}}
EXIT:0
wc -l seeds.jsonl: 60

## 5. WORDING (3 workers, Director's share)
Start:
- date -u: Sun Sep 27 05:18:21 UTC 2026 (pre-check); Sun Sep 27 05:18:26 UTC 2026 (run start)
- uptime: 1:18  up 3 days, 15:11, 4 users, load averages: 74.11 52.34 43.61 (05:18:21); 1:18  up 3 days, 15:11, 4 users, load averages: 71.14 52.09 43.58 (05:18:26)
Command: scripts/claude_lis320_luna.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 3 --max-minutes 40 > $O/glm.log 2>&1
End:
- date -u: Sun Sep 27 05:35:55 UTC 2026
- uptime: 1:35  up 3 days, 15:28, 4 users, load averages: 126.70 107.26 78.12
- EXIT:0
- wc -l raw.jsonl: 60
Last line of glm.log verbatim:
{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 17.5}
Count of "call failed" lines in glm.log: 0
First line of each distinct error: none (no errors)
Dialogs per minute: 60 / 17.5 = 3.428571... (~3.43 dialogs/min)

## 6. RAWCHECK2
Command: scripts/claude_lis320_rawcheck2.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl --models gpt-6-luna
Printed verbatim:
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "dup3_texts": 0, "not_in_seeds": 0}
EXIT:0
No ROUTE-FAIL (rawcheck2 OK, so steps 7-8 normal path).

## 7. CHECK + STYLE
Command: scripts/claude_lis320_check_we2.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $O/check.json
EXIT:0
check.json verbatim:
{
 "counts": {
  "cue:ask:again": 1,
  "cue:ask:remind me": 1,
  "cue:ask:what": 12,
  "cue:ask:who": 6,
  "cue:confirm:?": 2,
  "cue:confirm:did i tell": 1,
  "cue:confirm:right": 2,
  "cue:doubt:might": 2,
  "cue:doubt:not certain": 1,
  "cue:doubt:not sure": 9,
  "cue:doubt:not totally sure": 2,
  "cue:doubt:think": 2,
  "cue:doubt:unsure": 1,
  "cue:former:anymore": 1,
  "cue:former:before": 3,
  "cue:former:no longer": 1,
  "cue:former:used to": 22,
  "cue:hypothetical:hypothetically": 1,
  "cue:hypothetical:if": 12,
  "cue:negation_only:n't": 8,
  "cue:plan:'ll": 1,
  "cue:plan:will": 1,
  "cue:question:?": 5,
  "cue:someone_else:heard": 3,
  "cue:someone_else:mentioned": 3,
  "cue:someone_else:said": 3,
  "cue:someone_else:says": 3,
  "cue:someone_else:told": 6,
  "dialogs": 60,
  "drop:assert_hedged": 4,
  "drop:assert_reported": 2,
  "drop:former_present_cue": 2,
  "drop:group_speaker": 2,
  "drop:no_cue": 9,
  "drop:no_past_cue": 1,
  "drop:reply_ask_missing": 1,
  "drop:stray_name": 1,
  "dropped": 21,
  "dropped:backref": 1,
  "dropped:correct": 1,
  "dropped:correct_ref": 1,
  "dropped:former": 3,
  "dropped:plan": 9,
  "dropped:teach": 5,
  "dropped:yes_after_ask": 1,
  "kept": 404,
  "recased": 0,
  "turns": 425
 },
 "kept_by_family": {
  "ack_after_ask": 17,
  "ambiguous_pronoun": 11,
  "ask": 20,
  "backref": 29,
  "confirm": 5,
  "correct": 23,
  "correct_ref": 22,
  "doubt": 17,
  "former": 27,
  "hypothetical": 13,
  "jobhome": 14,
  "negation_only": 8,
  "plan": 2,
  "question": 5,
  "smalltalk": 19,
  "someone_else": 18,
  "teach": 138,
  "yes_after_ask": 16
 }
}
wc -l kept.jsonl: 404
wc -l drops.jsonl: 21
Command: scripts/claude_lis320_style.py --kept $O/kept.jsonl --out $O/style.json
Printed style line verbatim:
{"glm_kept": {"turns": 404, "words_median": 10, "words_p90": 30, "lowercase_start": 0.8, "noapos_contraction": 0.0, "over20_words": 0.213, "shapes_per_100": 94.8, "write_facts_per_turn": 0.965, "write_facts_in_over20": 0.328}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}
EXIT:0

## 8. COPY + CLEANUP
Copied to worktree artifacts/claude-lis320-20260926/pilot7/: seeds.jsonl, raw.jsonl, kept.jsonl, drops.jsonl, check.json, style.json, glm.log (+ this RESULTS.md).
rm -rf "/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.s26f5jEDyZ" done and confirmed gone (ls confirms missing).

## ERRORS / DEVIATIONS
- First selftest attempt ran with worktree cwd instead of $D and failed 3x with `repo not found: set LEARNER_REPO`; reran from $D (as task requires) and all 4 passed EXIT:0. No other deviation.
- Wording: 0 failed calls, 0 error lines, rawcheck2 OK. No ROUTE-FAIL handling needed.
- No TEST-ONLY panel read. No secrets written. No branch checkout/push.

## 9. RESUME VERIFICATION (2026-09-27 05:39:27-05:42:30 UTC, resumed agent; date -u 05:39:27 / uptime load 99.09 106.51 84.65 at start, 05:42:30 / 104.60 105.12 88.17 at end; df -g / = 33 GB free)
The run was already complete at resume; steps 1-8 were re-verified, not repeated. 0 extra Luna wording calls, 0 extra live codex calls (budget stays 60 wording + 1 selftest).
- Step 8 cleanup held: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.s26f5jEDyZ still gone.
- Fresh `git fetch -q origin main` + `git archive origin/main` into a new temp dir; all seals re-run from it, every line OK, 0 failures: PASSMARKS.sha256.txt 2/2, SEAL-ADDENDA 6/6, SEAL-ADDENDA-5 OK, SEAL-ADDENDA-6 6/6, SEAL-ADDENDA-7 OK, SEAL-ADDENDA-8 6/6, SEAL-ADDENDA-9 8/8. PASSMARKS.md not edited by either agent.
- 4 offline selftests re-run from that dir, all EXIT:0: lis320 luna selftest ok; seed_cr selftest OK (400 dialogs; correct_ref 121, correct 197, backref 235); check_we2 selftest OK (1 kept, 1 dropped); rawcheck2 selftest 7/7 ok. scripts/claude_luna_codex.py --selftest NOT re-run: its single live call is already spent.
- Byte-for-byte reproduction of every published output (offline, current origin/main): seeds re-generated with --seed 327 -> diff identical; rawcheck2 re-run -> same printed line, OK; check_we2 re-run -> check.json, kept.jsonl, drops.jsonl all diff-identical; style.py re-run -> style.json diff-identical.
- Counts re-confirmed from the files here: seeds 60, raw 60, kept 404, drops 21, kept+drops 425 = turns 425; glm.log "call failed" lines 0; raw.jsonl model gpt-6-luna 60/60, temperature null 60/60, 60 distinct dialog_id.
- DEVIATION: origin/main advanced twice during this task (8e2590aa -> 6c86806a -> 54167543e24e5a2302e678ab83defbe314a12115). The run's commit stays 8e2590aa8a8b6b4f1ba2ba8388300384b52d2137 as recorded in section 1. `git diff --stat 8e2590aa..6c86806a` over scripts/, design/v3/60-listener/, artifacts/claude-lis320-20260926/, artifacts/claude-chatdev-20260926/, artifacts/claude-e2e331-dev-20260924/ touched only scripts/claude_bm398w_data.py (new), scripts/claude_brd11.py, scripts/claude_brd12_dev.py — none of them used here — so every script and artifact pilot7 used is byte-identical across those commits and the re-verification above is equivalent to the original run's inputs.
- No ledger line added: artifacts/fable-predictions-ledger.md holds 0 lis320/pilot entries and this task's steps do not ask for one. The single unstaged ledger line in the worktree is dl-9, another agent's job; nothing was appended, so nothing was duplicated.
- artifacts/ is gitignored, so pilot7 is untracked in the worktree exactly like pilot6; left for the watcher to push. No branch checkout, no push, no TEST-ONLY panel read, no secrets, no ~/.codex access.
