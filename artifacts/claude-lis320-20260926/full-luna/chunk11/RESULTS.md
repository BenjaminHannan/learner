# lis-320 Luna full run, chunk 11 - BASH-ONLY job claude-lis320-luna-c11-mac

origin/main: f4d95aac22b5971477b31d862823f690b1add042
builder-outbox: 61279f1458f3df7d19556bd6970a74f4eb131614
start: 2026-09-27T22:18:22Z
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
joined rows from chunks 1..10: 2028
```
{"resume_clean": {"rows_in": 2028, "rows_out": 2028, "unparsed_kept": 0}}
```
rows after clean (B): 2028
## wording
wording start: 2026-09-27T22:18:28Z | load averages: 14.65 18.38 18.30
wording end: 2026-09-27T23:15:36Z rc=0 | load averages: 27.60 33.57 40.54
new rows: 324; minutes: 57; dialogs per minute: 5.67
last line of glm.log:
```
{"calls": 324, "parsed": 324, "skipped": 2028, "failed_calls": 0, "batches": 196, "stopped": "time", "minutes": 57.1}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 2352, "duplicate_ids": 0, "model_ok": 2352, "temperature_null": 2352, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 5,
  "cue:ask:again": 2,
  "cue:ask:how old": 31,
  "cue:ask:remind me": 30,
  "cue:ask:what": 640,
  "cue:ask:whats": 84,
  "cue:ask:where": 23,
  "cue:ask:who": 187,
  "cue:ask:whos": 5,
  "cue:confirm:?": 166,
  "cue:confirm:check": 8,
  "cue:confirm:did i say": 25,
  "cue:confirm:did i tell": 13,
  "cue:confirm:right": 166,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 1,
  "cue:doubt:could be": 3,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 3,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 15,
  "cue:doubt:might": 27,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 250,
  "cue:doubt:not totally sure": 41,
  "cue:doubt:think": 47,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 8,
  "cue:former:before": 23,
  "cue:former:no longer": 1,
  "cue:former:once": 1,
  "cue:former:used to": 916,
  "cue:former:was": 24,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 29,
  "cue:hypothetical:if": 381,
  "cue:hypothetical:imagine": 10,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 4,
  "cue:negation_only:n't": 20,
  "cue:negation_only:no": 9,
  "cue:negation_only:nt": 352,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 13,
  "cue:plan:down the line": 1,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 43,
  "cue:plan:might": 265,
  "cue:plan:one day": 1,
  "cue:plan:planning": 6,
  "cue:plan:plans": 4,
  "cue:plan:someday": 13,
  "cue:plan:sometime": 10,
  "cue:plan:thinking about": 7,
  "cue:plan:thinking of": 7,
  "cue:plan:will": 23,
  "cue:question:?": 409,
  "cue:someone_else:apparently": 18,
  "cue:someone_else:heard": 95,
  "cue:someone_else:mentioned": 4,
  "cue:someone_else:said": 79,
  "cue:someone_else:says": 63,
  "cue:someone_else:told": 130,
  "dialogs": 2352,
  "drop:ack_answers": 5,
  "drop:assert_hedged": 86,
  "drop:assert_reported": 6,
  "drop:former_present_cue": 25,
  "drop:group_speaker": 120,
  "drop:must_missing": 5,
  "drop:no_cue": 12,
  "drop:no_first_person": 4,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 14,
  "drop:reply_ask_missing": 108,
  "drop:reply_new_name": 1,
  "drop:role_word_missing": 2,
  "drop:stray_name": 34,
  "drop:yes_missing": 1,
  "dropped": 392,
  "dropped:ack_after_ask": 56,
  "dropped:ask": 2,
  "dropped:backref": 7,
  "dropped:correct": 29,
  "dropped:correct_ref": 10,
  "dropped:doubt": 4,
  "dropped:former": 29,
  "dropped:hypothetical": 8,
  "dropped:jobhome": 15,
  "dropped:negation_only": 1,
  "dropped:plan": 15,
  "dropped:smalltalk": 4,
  "dropped:someone_else": 1,
  "dropped:teach": 142,
  "dropped:yes_after_ask": 69,
  "kept": 16125,
  "recased": 5,
  "turns": 16517
 },
 "kept_by_family": {
  "ack_after_ask": 497,
  "ambiguous_pronoun": 403,
  "ask": 1007,
  "backref": 1325,
  "confirm": 381,
  "correct": 1236,
  "correct_ref": 688,
  "doubt": 402,
  "former": 974,
  "hypothetical": 427,
  "jobhome": 615,
  "negation_only": 381,
  "plan": 397,
  "question": 409,
  "smalltalk": 514,
  "someone_else": 389,
  "teach": 5617,
  "yes_after_ask": 463
 }
}
```
```
{
 "glm_kept": {
  "turns": 16125,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.816,
  "noapos_contraction": 0.234,
  "over20_words": 0.201,
  "shapes_per_100": 69.8,
  "write_facts_per_turn": 0.987,
  "write_facts_in_over20": 0.303
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
end: 2026-09-27T23:15:47Z
CHUNK-SUMMARY K=11 B=2028 new=324 calls=324 parsed=324 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=2352 of=6000 stop=ok
