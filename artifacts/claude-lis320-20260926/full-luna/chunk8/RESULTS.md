# lis-320 Luna full run, chunk 8 - BASH-ONLY job claude-lis320-luna-c8-mac

origin/main: 7f2a66b5cfa90b8402f87a9e6d75f62665203f85
builder-outbox: 498046e3191f740171a99534774f9469e1b8cf67
start: 2026-09-27T17:30:59Z
orphan wait loops: 0
## seals
```
artifacts/claude-lis320-20260926/ADDENDUM-6-route-low.md: OK
scripts/claude_lis320_glm_oclow.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_style.py: OK
scripts/claude_glm_leakcheck.py: OK
```
```
artifacts/claude-lis320-20260926/ADDENDUM-8-group-check-narrowed.md: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_check_cr.py: OK
scripts/claude_lis320_check.py: OK
scripts/claude_lis320_seed_cr.py: OK
scripts/claude_lis320_glm_oclow.py: OK
```
```
artifacts/claude-lis320-20260926/ADDENDUM-9-luna-writer.md: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_luna.py: OK
scripts/claude_lis320_rawcheck2.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_seed_cr.py: OK
```
```
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
```
```
artifacts/claude-lis320-20260926/ADDENDUM-11-luna-full-run-chunks.md: OK
scripts/claude_lis320_resume_clean.py: OK
scripts/claude_lis320_luna2.py: OK
scripts/claude_lis320_check_we3.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_rawcheck2.py: OK
```
```
artifacts/claude-lis320-20260926/ADDENDUM-12-luna-six-calls.md: OK
scripts/claude_lis320_luna3.py: OK
scripts/claude_lis320_luna2.py: OK
scripts/claude_luna_codex.py: OK
```
## selftests and probe
```
[luna-try] failed: exit 1: Rate limit exceeded
[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply
[glm320] s320-2-00000 ok
[glm320] s320-2-00001 unparsed
[glm320] s320-2-00002 ok
lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)
lis320 luna2 selftest ok (one style sentence added to the prompt; no network)
lis320 luna3 selftest ok (failed helper tries logged and counted; reply passed through; no network)
```
```
seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
```
```
check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)
```
```
lis320 rawcheck2 selftest 7/7 ok
```
```
lis320 resume_clean selftest ok (empty, error-like and 3x rows dropped; last row per id kept; no network)
```
```
selftest ok: model gpt-6-luna, output-file True
```
## seeds
```
{"dialogs": 6000, "turns": 42044, "intents": {"ack_after_ask": 1385, "ambiguous_pronoun": 1056, "ask": 2601, "backref": 3398, "confirm": 1010, "correct": 3325, "correct_ref": 1764, "doubt": 1010, "former": 2569, "hypothetical": 1035, "jobhome": 1581, "negation_only": 939, "plan": 1034, "question": 1046, "smalltalk": 1388, "someone_else": 994, "teach": 14602, "yes_after_ask": 1307}}
```
seeds sha256: 9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2
seeds hash equals chunk 1
## resume
joined rows from chunks 1..7: 1380
```
{"resume_clean": {"rows_in": 1380, "rows_out": 1380, "unparsed_kept": 0}}
```
rows after clean (B): 1380
## wording
wording start: 2026-09-27T17:31:06Z | load averages: 142.92 133.62 121.70
wording end: 2026-09-27T18:26:08Z rc=0 | load averages: 10.80 17.97 35.10
new rows: 204; minutes: 55; dialogs per minute: 3.71
last line of glm.log:
```
{"calls": 204, "parsed": 204, "skipped": 1380, "failed_calls": 0, "batches": 132, "stopped": "time", "minutes": 55.0}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 1584, "duplicate_ids": 0, "model_ok": 1584, "temperature_null": 1584, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 5,
  "cue:ask:again": 1,
  "cue:ask:how old": 20,
  "cue:ask:remind me": 24,
  "cue:ask:what": 440,
  "cue:ask:whats": 58,
  "cue:ask:where": 19,
  "cue:ask:who": 123,
  "cue:ask:whos": 5,
  "cue:confirm:?": 109,
  "cue:confirm:check": 6,
  "cue:confirm:did i say": 19,
  "cue:confirm:did i tell": 10,
  "cue:confirm:right": 116,
  "cue:confirm:was it": 1,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 1,
  "cue:doubt:maybe": 10,
  "cue:doubt:might": 24,
  "cue:doubt:not really sure": 6,
  "cue:doubt:not sure": 171,
  "cue:doubt:not totally sure": 28,
  "cue:doubt:think": 30,
  "cue:doubt:unsure": 3,
  "cue:former:anymore": 5,
  "cue:former:before": 19,
  "cue:former:once": 1,
  "cue:former:used to": 593,
  "cue:former:was": 18,
  "cue:hypothetical:hypothetically": 19,
  "cue:hypothetical:if": 283,
  "cue:hypothetical:imagine": 8,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 2,
  "cue:negation_only:n't": 14,
  "cue:negation_only:no": 7,
  "cue:negation_only:nt": 244,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 11,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 34,
  "cue:plan:might": 171,
  "cue:plan:one day": 1,
  "cue:plan:planning": 5,
  "cue:plan:plans": 3,
  "cue:plan:someday": 8,
  "cue:plan:sometime": 9,
  "cue:plan:thinking about": 3,
  "cue:plan:thinking of": 3,
  "cue:plan:will": 17,
  "cue:question:?": 279,
  "cue:someone_else:apparently": 11,
  "cue:someone_else:heard": 61,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 45,
  "cue:someone_else:says": 44,
  "cue:someone_else:told": 84,
  "dialogs": 1584,
  "drop:ack_answers": 3,
  "drop:assert_hedged": 58,
  "drop:assert_reported": 3,
  "drop:former_present_cue": 16,
  "drop:group_speaker": 85,
  "drop:must_missing": 3,
  "drop:no_cue": 10,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 12,
  "drop:reply_ask_missing": 77,
  "drop:reply_new_name": 1,
  "drop:role_word_missing": 1,
  "drop:stray_name": 22,
  "drop:yes_missing": 1,
  "dropped": 273,
  "dropped:ack_after_ask": 40,
  "dropped:ask": 1,
  "dropped:backref": 6,
  "dropped:correct": 21,
  "dropped:correct_ref": 9,
  "dropped:doubt": 4,
  "dropped:former": 19,
  "dropped:hypothetical": 7,
  "dropped:jobhome": 10,
  "dropped:negation_only": 1,
  "dropped:plan": 10,
  "dropped:smalltalk": 3,
  "dropped:teach": 96,
  "dropped:yes_after_ask": 46,
  "kept": 10851,
  "recased": 3,
  "turns": 11124
 },
 "kept_by_family": {
  "ack_after_ask": 337,
  "ambiguous_pronoun": 260,
  "ask": 695,
  "backref": 859,
  "confirm": 261,
  "correct": 835,
  "correct_ref": 486,
  "doubt": 277,
  "former": 636,
  "hypothetical": 315,
  "jobhome": 417,
  "negation_only": 265,
  "plan": 269,
  "question": 279,
  "smalltalk": 363,
  "someone_else": 247,
  "teach": 3742,
  "yes_after_ask": 308
 }
}
```
```
{
 "glm_kept": {
  "turns": 10851,
  "words_median": 9,
  "words_p90": 27,
  "lowercase_start": 0.821,
  "noapos_contraction": 0.233,
  "over20_words": 0.204,
  "shapes_per_100": 72.8,
  "write_facts_per_turn": 0.978,
  "write_facts_in_over20": 0.31
 },
 "dev_chatdev": {
  "turns": 336,
  "words_median": 14,
  "words_p90": 23,
  "lowercase_start": 1.0,
  "noapos_contraction": 0.253,
  "over20_words": 0.131,
  "shapes_per_100": 99.1
 },
 "dev_bank": {
  "turns": 194,
  "words_median": 15,
  "words_p90": 21,
  "lowercase_start": 0.887,
  "noapos_contraction": 0.021,
  "over20_words": 0.108,
  "shapes_per_100": 100.0
 }
}
```
end: 2026-09-27T18:26:15Z
CHUNK-SUMMARY K=8 B=1380 new=204 calls=204 parsed=204 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=1584 of=6000 stop=ok
