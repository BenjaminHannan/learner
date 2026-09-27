# lis-320 Luna full run, chunk 5 - BASH-ONLY job claude-lis320-luna-c5-mac

origin/main: ae27bb2b69b5f90a16aa0b41984f80eae4894d12
builder-outbox: ee01febcb25d76e8ceefd2ab1ce15712ca453f64
start: 2026-09-27T14:08:04Z
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
joined rows from chunks 1..4: 792
```
{"resume_clean": {"rows_in": 792, "rows_out": 792, "unparsed_kept": 0}}
```
rows after clean (B): 792
## wording
wording start: 2026-09-27T14:08:10Z | load averages: 53.43 48.92 44.93
wording end: 2026-09-27T15:05:36Z rc=0 | load averages: 38.36 46.78 49.78
new rows: 216; minutes: 57; dialogs per minute: 3.76
last line of glm.log:
```
{"calls": 216, "parsed": 216, "skipped": 792, "failed_calls": 0, "batches": 84, "stopped": "time", "minutes": 57.4}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 1008, "duplicate_ids": 0, "model_ok": 1008, "temperature_null": 1008, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:again": 1,
  "cue:ask:how old": 15,
  "cue:ask:remind me": 13,
  "cue:ask:what": 286,
  "cue:ask:whats": 32,
  "cue:ask:where": 12,
  "cue:ask:who": 75,
  "cue:ask:whos": 3,
  "cue:confirm:?": 72,
  "cue:confirm:check": 4,
  "cue:confirm:did i say": 9,
  "cue:confirm:did i tell": 8,
  "cue:confirm:right": 72,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 1,
  "cue:doubt:maybe": 4,
  "cue:doubt:might": 12,
  "cue:doubt:not really sure": 3,
  "cue:doubt:not sure": 111,
  "cue:doubt:not totally sure": 18,
  "cue:doubt:think": 21,
  "cue:doubt:unsure": 2,
  "cue:former:anymore": 4,
  "cue:former:before": 14,
  "cue:former:used to": 382,
  "cue:former:was": 10,
  "cue:hypothetical:hypothetically": 12,
  "cue:hypothetical:if": 180,
  "cue:hypothetical:imagine": 3,
  "cue:hypothetical:pretend": 1,
  "cue:hypothetical:suppose": 1,
  "cue:negation_only:n't": 8,
  "cue:negation_only:no": 6,
  "cue:negation_only:nt": 153,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 7,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 27,
  "cue:plan:might": 114,
  "cue:plan:one day": 1,
  "cue:plan:planning": 3,
  "cue:plan:plans": 1,
  "cue:plan:someday": 3,
  "cue:plan:sometime": 5,
  "cue:plan:thinking about": 2,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 13,
  "cue:question:?": 175,
  "cue:someone_else:apparently": 6,
  "cue:someone_else:heard": 40,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 31,
  "cue:someone_else:says": 32,
  "cue:someone_else:told": 56,
  "dialogs": 1008,
  "drop:ack_answers": 1,
  "drop:assert_hedged": 39,
  "drop:assert_reported": 1,
  "drop:former_present_cue": 7,
  "drop:group_speaker": 50,
  "drop:must_missing": 2,
  "drop:no_cue": 7,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 8,
  "drop:reply_ask_missing": 45,
  "drop:stray_name": 16,
  "dropped": 163,
  "dropped:ack_after_ask": 22,
  "dropped:ask": 1,
  "dropped:backref": 3,
  "dropped:correct": 12,
  "dropped:correct_ref": 6,
  "dropped:doubt": 2,
  "dropped:former": 9,
  "dropped:hypothetical": 5,
  "dropped:jobhome": 9,
  "dropped:negation_only": 1,
  "dropped:plan": 8,
  "dropped:smalltalk": 2,
  "dropped:teach": 56,
  "dropped:yes_after_ask": 27,
  "kept": 6926,
  "recased": 3,
  "turns": 7089
 },
 "kept_by_family": {
  "ack_after_ask": 214,
  "ambiguous_pronoun": 164,
  "ask": 440,
  "backref": 555,
  "confirm": 165,
  "correct": 527,
  "correct_ref": 308,
  "doubt": 176,
  "former": 410,
  "hypothetical": 197,
  "jobhome": 262,
  "negation_only": 167,
  "plan": 182,
  "question": 175,
  "smalltalk": 218,
  "someone_else": 167,
  "teach": 2404,
  "yes_after_ask": 195
 }
}
```
```
{
 "glm_kept": {
  "turns": 6926,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.821,
  "noapos_contraction": 0.233,
  "over20_words": 0.201,
  "shapes_per_100": 76.3,
  "write_facts_per_turn": 0.987,
  "write_facts_in_over20": 0.313
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
end: 2026-09-27T15:05:43Z
CHUNK-SUMMARY K=5 B=792 new=216 calls=216 parsed=216 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=1008 of=6000 stop=ok
