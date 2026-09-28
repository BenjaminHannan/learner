# lis-320 Luna full run, chunk 13 - BASH-ONLY job claude-lis320-luna-c13-mac

origin/main: b0ea50aa92e20159523391eedf2f2db1aef9cc92
builder-outbox: ee14a90c5657953935ac1627838d59db5a54713a
start: 2026-09-28T00:27:52Z
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
[glm320] s320-2-00000 ok
[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply
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
joined rows from chunks 1..12: 2664
```
{"resume_clean": {"rows_in": 2664, "rows_out": 2664, "unparsed_kept": 0}}
```
rows after clean (B): 2664
## wording
wording start: 2026-09-28T00:28:00Z | load averages: 135.35 111.04 90.95
wording end: 2026-09-28T01:23:38Z rc=0 | load averages: 197.64 180.44 162.94
new rows: 312; minutes: 55; dialogs per minute: 5.61
last line of glm.log:
```
{"calls": 312, "parsed": 312, "skipped": 2664, "failed_calls": 0, "batches": 248, "stopped": "time", "minutes": 55.6}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 2976, "duplicate_ids": 0, "model_ok": 2976, "temperature_null": 2976, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 7,
  "cue:ask:again": 2,
  "cue:ask:how old": 41,
  "cue:ask:remind me": 33,
  "cue:ask:what": 809,
  "cue:ask:whats": 107,
  "cue:ask:when": 1,
  "cue:ask:where": 27,
  "cue:ask:who": 255,
  "cue:ask:whos": 5,
  "cue:confirm:?": 224,
  "cue:confirm:check": 9,
  "cue:confirm:did i say": 36,
  "cue:confirm:did i tell": 19,
  "cue:confirm:right": 200,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 1,
  "cue:doubt:could be": 5,
  "cue:doubt:dunno": 3,
  "cue:doubt:guess": 4,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 17,
  "cue:doubt:might": 33,
  "cue:doubt:not certain": 1,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 315,
  "cue:doubt:not totally sure": 54,
  "cue:doubt:think": 56,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 10,
  "cue:former:before": 25,
  "cue:former:no longer": 3,
  "cue:former:once": 1,
  "cue:former:used to": 1132,
  "cue:former:was": 29,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 34,
  "cue:hypothetical:if": 487,
  "cue:hypothetical:imagine": 12,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 29,
  "cue:negation_only:no": 12,
  "cue:negation_only:nt": 430,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 14,
  "cue:plan:down the line": 1,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 2,
  "cue:plan:later on": 1,
  "cue:plan:may": 51,
  "cue:plan:might": 336,
  "cue:plan:one day": 1,
  "cue:plan:planning": 6,
  "cue:plan:plans": 6,
  "cue:plan:someday": 14,
  "cue:plan:sometime": 13,
  "cue:plan:thinking about": 9,
  "cue:plan:thinking of": 8,
  "cue:plan:will": 32,
  "cue:question:?": 528,
  "cue:someone_else:apparently": 27,
  "cue:someone_else:heard": 120,
  "cue:someone_else:mentioned": 5,
  "cue:someone_else:said": 103,
  "cue:someone_else:says": 75,
  "cue:someone_else:told": 173,
  "dialogs": 2976,
  "drop:ack_answers": 8,
  "drop:assert_hedged": 111,
  "drop:assert_reported": 8,
  "drop:former_present_cue": 33,
  "drop:group_speaker": 155,
  "drop:must_missing": 6,
  "drop:no_cue": 12,
  "drop:no_first_person": 4,
  "drop:no_past_cue": 2,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 21,
  "drop:reply_ask_missing": 140,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 5,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 40,
  "drop:yes_missing": 1,
  "dropped": 512,
  "dropped:ack_after_ask": 77,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 3,
  "dropped:backref": 11,
  "dropped:correct": 39,
  "dropped:correct_ref": 15,
  "dropped:doubt": 4,
  "dropped:former": 40,
  "dropped:hypothetical": 8,
  "dropped:jobhome": 18,
  "dropped:negation_only": 1,
  "dropped:plan": 16,
  "dropped:smalltalk": 7,
  "dropped:someone_else": 2,
  "dropped:teach": 184,
  "dropped:yes_after_ask": 86,
  "kept": 20374,
  "recased": 5,
  "turns": 20886
 },
 "kept_by_family": {
  "ack_after_ask": 628,
  "ambiguous_pronoun": 506,
  "ask": 1287,
  "backref": 1662,
  "confirm": 491,
  "correct": 1598,
  "correct_ref": 870,
  "doubt": 502,
  "former": 1201,
  "hypothetical": 542,
  "jobhome": 767,
  "negation_only": 471,
  "plan": 496,
  "question": 528,
  "smalltalk": 667,
  "someone_else": 503,
  "teach": 7077,
  "yes_after_ask": 578
 }
}
```
```
{
 "glm_kept": {
  "turns": 20374,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.816,
  "noapos_contraction": 0.232,
  "over20_words": 0.196,
  "shapes_per_100": 68.2,
  "write_facts_per_turn": 0.984,
  "write_facts_in_over20": 0.296
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
end: 2026-09-28T01:23:56Z
CHUNK-SUMMARY K=13 B=2664 new=312 calls=312 parsed=312 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=2976 of=6000 stop=ok
