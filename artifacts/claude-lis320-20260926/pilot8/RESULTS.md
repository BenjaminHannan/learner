# lis320-pilot8b RESULTS (GPT-6 Luna wording, Director's 3-worker share)

Label: lis320-pilot8b. GPU: no (Mac CPU). LOAD-LIGHT: yes.
Common rules (first 13 lines of origin/main:handoff/queue/lis-302-gpu.md): followed — additive only (new files under artifacts/claude-lis320-20260926/pilot8/), fictional names via seed script avoid-lists, no TEST-ONLY panel read, report in final reply. No branch checkout/push by builder (watcher pushes PUSH path artifacts/claude-lis320-20260926/pilot8).

origin/main commit: 3e8cf1186bf64cca8a77f0e5428596bd2bc70b30
`git rev-parse origin/main` = 3e8cf1186bf64cca8a77f0e5428596bd2bc70b30

## 0. ORPHAN CHECK
`pgrep -fl "claude_lis320_luna2.py --seeds"` → no output, exit 1. No orphan run found.
Therefore steps 1-8 were run as written (no skip, no reuse of another tree).

## 1. TREE
`git fetch -q origin main` → exit 0.
D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.pwiYtPiGT0 (mktemp -d).
`git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-20260924 | tar -x -C $D` → exit 0.
O=artifacts/claude-lis320-20260926/pilot8 (mkdir -p in $D).
Python runner for every script: `uv run --offline --no-project --python 3.12 python -B <script> ...` (stdlib only). Codex helper untouched (fresh empty temp dir, read-only sandbox).

## 2. SEALS (run from $D, all OK)
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-6.sha256.txt` → ADDENDUM-6-route-low.md: OK; claude_lis320_glm_oclow.py: OK; claude_lis320_glm_oc.py: OK; claude_lis320_glm.py: OK; claude_lis320_style.py: OK; claude_glm_leakcheck.py: OK (exit 0)
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-8.sha256.txt` → ADDENDUM-8-group-check-narrowed.md: OK; claude_lis320_check_we2.py: OK; claude_lis320_check_cr.py: OK; claude_lis320_check.py: OK; claude_lis320_seed_cr.py: OK; claude_lis320_glm_oclow.py: OK (exit 0)
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-9.sha256.txt` → ADDENDUM-9-luna-writer.md: OK; claude_luna_codex.py: OK; claude_lis320_luna.py: OK; claude_lis320_rawcheck2.py: OK; claude_lis320_glm_oc.py: OK; claude_lis320_glm.py: OK; claude_lis320_check_we2.py: OK; claude_lis320_seed_cr.py: OK (exit 0)
- `shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-10.sha256.txt` → ADDENDUM-10-luna-pilot7-fixes.md: OK; claude_lis320_luna2.py: OK; claude_lis320_check_we3.py: OK; claude_lis320_luna.py: OK; claude_luna_codex.py: OK; claude_lis320_rawcheck2.py: OK; claude_lis320_check_we2.py: OK; claude_lis320_check.py: OK; claude_lis320_glm.py: OK; claude_lis320_seed_cr.py: OK (exit 0)

## 3. SELFTESTS (each ok/OK)
- `scripts/claude_lis320_luna2.py --selftest` → `[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply` then `[glm320] s320-2-00000 ok`, `[glm320] s320-2-00001 unparsed`, `[glm320] s320-2-00002 ok`, `lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)`, `lis320 luna2 selftest ok (one style sentence added to the prompt; no network)` (exit 0; the "call failed" line is expected mock output inside the selftest)
- `scripts/claude_lis320_seed_cr.py --selftest` → `seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}` (exit 0)
- `scripts/claude_lis320_check_we3.py --selftest` → `check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)` (exit 0)
- `scripts/claude_lis320_rawcheck2.py --selftest` → `lis320 rawcheck2 selftest 7/7 ok` (exit 0)
- ONE live call `scripts/claude_luna_codex.py --selftest` → `selftest ok: model gpt-6-luna, output-file True` (exit 0)

## 4. SEEDS
`scripts/claude_lis320_seed_cr.py --seed 328 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl` → exit 0, printed:
`{"dialogs": 60, "turns": 415, "intents": {"ack_after_ask": 15, "ambiguous_pronoun": 10, "ask": 32, "backref": 21, "confirm": 10, "correct": 41, "correct_ref": 21, "doubt": 9, "former": 25, "hypothetical": 13, "jobhome": 18, "negation_only": 15, "plan": 15, "question": 6, "smalltalk": 16, "someone_else": 10, "teach": 127, "yes_after_ask": 11}}`
seeds.jsonl lines: 60.

## 5. WORDING (3 workers, Director's share)
Pre-run pgrep for same run: none (exit 1).
Start: `date -u` → Mon Sep 28 00:02:04 UTC 2026; `uptime` → `20:02  up 4 days,  9:55, 4 users, load averages: 49.19 60.68 63.74`.
Command: `scripts/claude_lis320_luna2.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 3 --max-minutes 40 > $O/glm.log 2>&1` → exit 0.
End: `date -u` → Mon Sep 28 00:17:26 UTC 2026; `uptime` → `20:17  up 4 days, 10:10, 4 users, load averages: 86.72 79.30 74.71`.
glm.log last line verbatim:
`{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 15.4}`
`grep -c "call failed" glm.log` → 0 (grep exit 1, no matches). Distinct errors: none.
raw.jsonl lines: 60.
Dialogs per minute: 60 / 15.4 (script-reported minutes) = 3.90; wall clock 00:02:04→00:17:26 = 15 min 22 s (15.37 min) = 3.90 dialogs/min. Turns per minute: 415 / 15.4 = 26.95.
Total Luna wording calls this run: 60 plus 1 selftest call = 61.

## 6. RAWCHECK
`scripts/claude_lis320_rawcheck2.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl --models gpt-6-luna` → exit 0, printed verbatim:
`{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "dup3_texts": 0, "not_in_seeds": 0}`
No ROUTE-FAIL.

## 7. CHECK + STYLE
`scripts/claude_lis320_check_we3.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $O/check.json` → exit 0.
check.json verbatim:
`{ "counts": { "cue:ask:?": 1, "cue:ask:how old": 1, "cue:ask:remind me": 1, "cue:ask:what": 17, "cue:ask:whats": 6, "cue:ask:where": 1, "cue:ask:who": 5, "cue:confirm:?": 4, "cue:confirm:check": 1, "cue:confirm:right": 5, "cue:doubt:maybe": 1, "cue:doubt:not sure": 6, "cue:doubt:not totally sure": 2, "cue:former:before": 1, "cue:former:used to": 23, "cue:former:was": 1, "cue:hypothetical:if": 13, "cue:negation_only:nt": 15, "cue:plan:may": 1, "cue:plan:might": 11, "cue:plan:planning": 1, "cue:plan:sometime": 1, "cue:question:?": 6, "cue:someone_else:heard": 4, "cue:someone_else:says": 1, "cue:someone_else:told": 5, "dialogs": 60, "drop:assert_hedged": 2, "drop:group_speaker": 3, "drop:reply_ask_missing": 2, "drop:stray_name": 1, "dropped": 7, "dropped:ack_after_ask": 1, "dropped:plan": 1, "dropped:teach": 3, "dropped:yes_after_ask": 2, "kept": 408, "recased": 0, "turns": 415 }, "kept_by_family": { "ack_after_ask": 14, "ambiguous_pronoun": 10, "ask": 32, "backref": 21, "confirm": 10, "correct": 41, "correct_ref": 21, "doubt": 9, "former": 25, "hypothetical": 13, "jobhome": 18, "negation_only": 15, "plan": 14, "question": 6, "smalltalk": 16, "someone_else": 10, "teach": 124, "yes_after_ask": 9 } }`
(Canonical pretty form is in check.json; counts identical.)
kept.jsonl lines: 408. drops.jsonl lines: 7.
`scripts/claude_lis320_style.py --kept $O/kept.jsonl --out $O/style.json` → exit 0, printed style line (stdout) = style.json content:
`{"glm_kept": {"turns": 408, "words_median": 9, "words_p90": 26, "lowercase_start": 0.794, "noapos_contraction": 0.23, "over20_words": 0.174, "shapes_per_100": 94.9, "write_facts_per_turn": 0.946, "write_facts_in_over20": 0.251}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}`

## 8. COPIES
Copied from $D O to worktree artifacts/claude-lis320-20260926/pilot8/: seeds.jsonl (60 lines), raw.jsonl (60 lines), kept.jsonl (408 lines), drops.jsonl (7 lines), check.json, style.json, glm.log (61 lines) — plus this RESULTS.md. No ledger entries added/duplicated. Nothing trained.

## ERRORS / DEVIATIONS
None. All seals OK; all selftests ok/OK including the one live Luna selftest; wording exit 0 with 0 failed calls; rawcheck OK (no ROUTE-FAIL, steps 7-8 run normally). No orphan process existed. $D removed after copy (see final reply for confirmation).
