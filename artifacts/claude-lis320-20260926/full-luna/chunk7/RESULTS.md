# lis-320 Luna full run, chunk 7 - BASH-ONLY job claude-lis320-luna-c7-mac

origin/main: 0aeb7d94f4d549cf3760f9dc0ca651cf59b6dce1
builder-outbox: 120ebdb05c8e815c194581940639e6d51b91ea64
start: 2026-09-27T16:31:57Z
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
joined rows from chunks 1..6: 1176
```
{"resume_clean": {"rows_in": 1176, "rows_out": 1176, "unparsed_kept": 0}}
```
rows after clean (B): 1176
## wording
wording start: 2026-09-27T16:32:05Z | load averages: 111.33 113.03 110.63
wording end: 2026-09-27T17:27:40Z rc=0 | load averages: 141.88 122.40 115.23
new rows: 204; minutes: 55; dialogs per minute: 3.67
last line of glm.log:
```
{"calls": 204, "parsed": 204, "skipped": 1176, "failed_calls": 0, "batches": 115, "stopped": "time", "minutes": 55.6}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 1380, "duplicate_ids": 0, "model_ok": 1380, "temperature_null": 1380, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 4,
  "cue:ask:again": 1,
  "cue:ask:how old": 19,
  "cue:ask:remind me": 22,
  "cue:ask:what": 390,
  "cue:ask:whats": 51,
  "cue:ask:where": 16,
  "cue:ask:who": 111,
  "cue:ask:whos": 5,
  "cue:confirm:?": 96,
  "cue:confirm:check": 5,
  "cue:confirm:did i say": 15,
  "cue:confirm:did i tell": 8,
  "cue:confirm:right": 104,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 1,
  "cue:doubt:maybe": 8,
  "cue:doubt:might": 20,
  "cue:doubt:not really sure": 6,
  "cue:doubt:not sure": 145,
  "cue:doubt:not totally sure": 26,
  "cue:doubt:think": 26,
  "cue:doubt:unsure": 3,
  "cue:former:anymore": 5,
  "cue:former:before": 17,
  "cue:former:once": 1,
  "cue:former:used to": 524,
  "cue:former:was": 12,
  "cue:hypothetical:hypothetically": 15,
  "cue:hypothetical:if": 243,
  "cue:hypothetical:imagine": 7,
  "cue:hypothetical:pretend": 2,
  "cue:hypothetical:suppose": 2,
  "cue:negation_only:n't": 13,
  "cue:negation_only:no": 6,
  "cue:negation_only:nt": 204,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 11,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 32,
  "cue:plan:might": 149,
  "cue:plan:one day": 1,
  "cue:plan:planning": 3,
  "cue:plan:plans": 3,
  "cue:plan:someday": 6,
  "cue:plan:sometime": 8,
  "cue:plan:thinking about": 3,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 16,
  "cue:question:?": 248,
  "cue:someone_else:apparently": 11,
  "cue:someone_else:heard": 53,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 40,
  "cue:someone_else:says": 40,
  "cue:someone_else:told": 71,
  "dialogs": 1380,
  "drop:ack_answers": 1,
  "drop:assert_hedged": 51,
  "drop:assert_reported": 3,
  "drop:former_present_cue": 13,
  "drop:group_speaker": 70,
  "drop:must_missing": 3,
  "drop:no_cue": 10,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 10,
  "drop:reply_ask_missing": 64,
  "drop:role_word_missing": 1,
  "drop:stray_name": 19,
  "drop:yes_missing": 1,
  "dropped": 231,
  "dropped:ack_after_ask": 34,
  "dropped:ask": 1,
  "dropped:backref": 5,
  "dropped:correct": 18,
  "dropped:correct_ref": 8,
  "dropped:doubt": 4,
  "dropped:former": 16,
  "dropped:hypothetical": 6,
  "dropped:jobhome": 10,
  "dropped:negation_only": 1,
  "dropped:plan": 10,
  "dropped:smalltalk": 3,
  "dropped:teach": 78,
  "dropped:yes_after_ask": 37,
  "kept": 9464,
  "recased": 3,
  "turns": 9695
 },
 "kept_by_family": {
  "ack_after_ask": 292,
  "ambiguous_pronoun": 221,
  "ask": 619,
  "backref": 754,
  "confirm": 228,
  "correct": 728,
  "correct_ref": 421,
  "doubt": 239,
  "former": 559,
  "hypothetical": 269,
  "jobhome": 375,
  "negation_only": 223,
  "plan": 238,
  "question": 248,
  "smalltalk": 312,
  "someone_else": 217,
  "teach": 3251,
  "yes_after_ask": 270
 }
}
```
```
{
 "glm_kept": {
  "turns": 9464,
  "words_median": 9,
  "words_p90": 27,
  "lowercase_start": 0.821,
  "noapos_contraction": 0.232,
  "over20_words": 0.204,
  "shapes_per_100": 74.0,
  "write_facts_per_turn": 0.98,
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
end: 2026-09-27T17:27:46Z
CHUNK-SUMMARY K=7 B=1176 new=204 calls=204 parsed=204 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=1380 of=6000 stop=ok
