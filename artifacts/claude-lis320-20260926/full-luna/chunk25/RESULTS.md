# lis-320 Luna full run, chunk 25 - BASH-ONLY job claude-lis320-luna-c25-mac

origin/main: 8cffd55a611a8c579cf5a07834494f6c4a4317ab
builder-outbox: 82249797929d406acc54d39f99ba0f174eeaf78f
start: 2026-09-28T12:44:15Z
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
joined rows from chunks 1..24: 5856
```
{"resume_clean": {"rows_in": 5856, "rows_out": 5856, "unparsed_kept": 0}}
```
rows after clean (B): 5856
## wording
wording start: 2026-09-28T12:44:23Z | load averages: 6.22 6.31 6.78
wording end: 2026-09-28T13:20:45Z rc=0 | load averages: 5.32 5.98 6.18
new rows: 144; minutes: 36; dialogs per minute: 3.96
last line of glm.log:
```
{"calls": 144, "parsed": 144, "skipped": 5856, "failed_calls": 0, "batches": 500, "stopped": "done", "minutes": 36.4}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 6000, "duplicate_ids": 0, "model_ok": 6000, "temperature_null": 6000, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 15,
  "cue:ask:again": 4,
  "cue:ask:how old": 91,
  "cue:ask:remind me": 65,
  "cue:ask:what": 1623,
  "cue:ask:whats": 194,
  "cue:ask:when": 4,
  "cue:ask:where": 56,
  "cue:ask:who": 538,
  "cue:ask:whos": 7,
  "cue:confirm:?": 495,
  "cue:confirm:check": 21,
  "cue:confirm:did i say": 65,
  "cue:confirm:did i tell": 38,
  "cue:confirm:right": 386,
  "cue:confirm:was it": 2,
  "cue:confirm:yeah": 3,
  "cue:doubt:cant remember": 6,
  "cue:doubt:could be": 15,
  "cue:doubt:dunno": 6,
  "cue:doubt:guess": 6,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 32,
  "cue:doubt:might": 67,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 619,
  "cue:doubt:not totally sure": 116,
  "cue:doubt:think": 111,
  "cue:doubt:unsure": 15,
  "cue:former:anymore": 22,
  "cue:former:before": 41,
  "cue:former:no longer": 5,
  "cue:former:once": 2,
  "cue:former:used to": 2355,
  "cue:former:was": 58,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 52,
  "cue:hypothetical:if": 939,
  "cue:hypothetical:imagine": 18,
  "cue:hypothetical:pretend": 6,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 52,
  "cue:negation_only:no": 32,
  "cue:negation_only:nt": 854,
  "cue:plan:'ll": 4,
  "cue:plan:at some point": 19,
  "cue:plan:down the line": 5,
  "cue:plan:going to": 3,
  "cue:plan:hoping": 5,
  "cue:plan:in the future": 1,
  "cue:plan:later on": 3,
  "cue:plan:may": 95,
  "cue:plan:might": 703,
  "cue:plan:next": 1,
  "cue:plan:one day": 3,
  "cue:plan:plan": 1,
  "cue:plan:planning": 16,
  "cue:plan:plans": 10,
  "cue:plan:someday": 23,
  "cue:plan:sometime": 23,
  "cue:plan:thinking about": 18,
  "cue:plan:thinking of": 11,
  "cue:plan:want to": 1,
  "cue:plan:will": 48,
  "cue:question:?": 1046,
  "cue:someone_else:apparently": 67,
  "cue:someone_else:heard": 227,
  "cue:someone_else:mentioned": 19,
  "cue:someone_else:said": 211,
  "cue:someone_else:says": 135,
  "cue:someone_else:told": 333,
  "dialogs": 6000,
  "drop:ack_answers": 18,
  "drop:assert_hedged": 194,
  "drop:assert_reported": 17,
  "drop:forbidden_in_reply": 2,
  "drop:forbidden_in_turn": 2,
  "drop:former_present_cue": 73,
  "drop:group_speaker": 299,
  "drop:must_missing": 12,
  "drop:no_cue": 19,
  "drop:no_first_person": 15,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 2,
  "drop:reads_former": 38,
  "drop:reply_ask_missing": 277,
  "drop:reply_new_name": 3,
  "drop:role_link_not_visible": 2,
  "drop:role_word_missing": 12,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 88,
  "drop:yes_missing": 3,
  "dropped": 990,
  "dropped:ack_after_ask": 160,
  "dropped:ambiguous_pronoun": 2,
  "dropped:ask": 4,
  "dropped:backref": 27,
  "dropped:correct": 75,
  "dropped:correct_ref": 22,
  "dropped:doubt": 7,
  "dropped:former": 85,
  "dropped:hypothetical": 14,
  "dropped:jobhome": 31,
  "dropped:negation_only": 1,
  "dropped:plan": 41,
  "dropped:smalltalk": 14,
  "dropped:someone_else": 2,
  "dropped:teach": 337,
  "dropped:yes_after_ask": 168,
  "kept": 41054,
  "recased": 10,
  "turns": 42044
 },
 "kept_by_family": {
  "ack_after_ask": 1225,
  "ambiguous_pronoun": 1054,
  "ask": 2597,
  "backref": 3371,
  "confirm": 1010,
  "correct": 3250,
  "correct_ref": 1742,
  "doubt": 1003,
  "former": 2484,
  "hypothetical": 1021,
  "jobhome": 1550,
  "negation_only": 938,
  "plan": 993,
  "question": 1046,
  "smalltalk": 1374,
  "someone_else": 992,
  "teach": 14265,
  "yes_after_ask": 1139
 }
}
```
```
{
 "glm_kept": {
  "turns": 41054,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.812,
  "noapos_contraction": 0.235,
  "over20_words": 0.19,
  "shapes_per_100": 63.6,
  "write_facts_per_turn": 0.985,
  "write_facts_in_over20": 0.285
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
end: 2026-09-28T13:21:08Z
CHUNK-SUMMARY K=25 B=5856 new=144 calls=144 parsed=144 rate=1.000 stopped=done rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=6000 of=6000 stop=ok
