stop file for lis320-pilot8b-mac present 2026-09-27T09:20:49Z; its opencode builders (not killed):
54153 /usr/local/bin/opencode run --mode

RUNNER NOTE (Director, 09-27): your buil

COMMON RULES (the "Fix: reading facts fr
GPU: no (Mac CPU; 60 GPT-6 Luna wording 
LOAD-LIGHT: yes
CODEX RULES: never read, print, copy or 
PYTHON: run every script as `uv run --of
WHY: Ben (03:47 UTC 09-27): "just have l

0. ORPHAN CHECK (before step 1): run `pg
1. TREE: git fetch -q origin main; D=$(m
2. SEALS (all OK or stop, run from $D): 
3. SELFTESTS (each must end ok/OK, else 
4. SEEDS: scripts/claude_lis320_seed_cr.
5. WORDING (3 workers, the Director's sh
6. scripts/claude_lis320_rawcheck2.py --
7. scripts/claude_lis320_check_we3.py --
8. Copy $O (seeds.jsonl, raw.jsonl, kept
PUSH: artifacts/claude-lis320-20260926/p
# lis-320 pilot 8 (seed 328, GPT-6 Luna, luna2 + check_we3) - BASH-ONLY job claude-lis320-pilot8e-mac

origin/main: f8d2214cfe8c662937ef7429ba96f372e38515ff
start: 2026-09-27T09:20:52Z
orphan wait loops: 0
## seals
artifacts/claude-lis320-20260926/ADDENDUM-6-route-low.md: OK
scripts/claude_lis320_glm_oclow.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_style.py: OK
scripts/claude_glm_leakcheck.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-8-group-check-narrowed.md: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_check_cr.py: OK
scripts/claude_lis320_check.py: OK
scripts/claude_lis320_seed_cr.py: OK
scripts/claude_lis320_glm_oclow.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-9-luna-writer.md: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_luna.py: OK
scripts/claude_lis320_rawcheck2.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_seed_cr.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-10-luna-pilot7-fixes.md: OK
scripts/claude_lis320_luna2.py: OK
scripts/claude_lis320_check_we3.py: OK
scripts/claude_lis320_luna.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_rawcheck2.py: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_check.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_seed_cr.py: OK
## selftests
[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply
[glm320] s320-2-00000 ok
[glm320] s320-2-00001 unparsed
[glm320] s320-2-00002 ok
lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)
lis320 luna2 selftest ok (one style sentence added to the prompt; no network)
seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)
lis320 rawcheck2 selftest 7/7 ok
selftest ok: model gpt-6-luna, output-file True
## seeds
{"dialogs": 60, "turns": 415, "intents": {"ack_after_ask": 15, "ambiguous_pronoun": 10, "ask": 32, "backref": 21, "confirm": 10, "correct": 41, "correct_ref": 21, "doubt": 9, "former": 25, "hypothetical": 13, "jobhome": 18, "negation_only": 15, "plan": 15, "question": 6, "smalltalk": 16, "someone_else": 10, "teach": 127, "yes_after_ask": 11}}
## wording
wording start: 2026-09-27T09:21:02Z | load averages: 50.46 34.59 32.02
wording end: 2026-09-27T09:45:41Z rc=0 | load averages: 52.56 42.78 40.67
raw rows: 60; minutes: 24; dialogs per minute: 2.43
last line of glm.log:
{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 2, "stopped": "done", "minutes": 24.7}
call failed lines: 0
distinct failure starts:
## rawcheck2
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 60, "duplicate_ids": 0, "model_ok": 60, "temperature_null": 60, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3
check rc=0
{
 "counts": {
  "cue:ask:?": 1,
  "cue:ask:again": 2,
  "cue:ask:how old": 1,
  "cue:ask:remind me": 1,
  "cue:ask:what": 17,
  "cue:ask:whats": 3,
  "cue:ask:who": 7,
  "cue:confirm:?": 7,
  "cue:confirm:right": 3,
  "cue:doubt:maybe": 1,
  "cue:doubt:might": 1,
  "cue:doubt:not sure": 7,
  "cue:former:anymore": 1,
  "cue:former:used to": 23,
  "cue:hypothetical:if": 12,
  "cue:hypothetical:imagine": 1,
  "cue:negation_only:n't": 1,
  "cue:negation_only:no": 1,
  "cue:negation_only:nt": 13,
  "cue:plan:may": 1,
  "cue:plan:might": 11,
  "cue:plan:plans": 1,
  "cue:question:?": 6,
  "cue:someone_else:apparently": 2,
  "cue:someone_else:heard": 2,
  "cue:someone_else:said": 3,
  "cue:someone_else:says": 1,
  "cue:someone_else:told": 2,
  "dialogs": 60,
  "drop:ack_answers": 1,
  "drop:assert_hedged": 2,
  "drop:group_speaker": 3,
  "drop:no_past_cue": 1,
  "drop:reads_former": 1,
  "drop:reply_ask_missing": 2,
  "dropped": 10,
  "dropped:ack_after_ask": 2,
  "dropped:correct": 2,
  "dropped:correct_ref": 1,
  "dropped:former": 1,
  "dropped:plan": 2,
  "dropped:teach": 1,
  "dropped:yes_after_ask": 1,
  "kept": 405,
  "recased": 0,
  "turns": 415
 },
 "kept_by_family": {
  "ack_after_ask": 13,
  "ambiguous_pronoun": 10,
  "ask": 32,
  "backref": 21,
  "confirm": 10,
  "correct": 39,
  "correct_ref": 20,
  "doubt": 9,
  "former": 24,
  "hypothetical": 13,
  "jobhome": 18,
  "negation_only": 15,
  "plan": 13,
  "question": 6,
  "smalltalk": 16,
  "someone_else": 10,
  "teach": 126,
  "yes_after_ask": 10
 }
}
## style
{"glm_kept": {"turns": 405, "words_median": 9, "words_p90": 27, "lowercase_start": 0.844, "noapos_contraction": 0.23, "over20_words": 0.21, "shapes_per_100": 95.3, "write_facts_per_turn": 0.951, "write_facts_in_over20": 0.265}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}
end: 2026-09-27T09:45:42Z
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.OXNpfYrZOL
 1912
0 check.err
1532 check.json
2638 drops.jsonl
1851 glm.log
560459 kept.jsonl
113526 raw.jsonl
5195 RESULTS.md
275922 seeds.jsonl
624 style.json
rc=0
