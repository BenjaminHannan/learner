# lis-320 Luna full run, chunk 14 - BASH-ONLY job claude-lis320-luna-c14-mac

origin/main: 8ca119ffbe06656c02c5d1a5b7ed5bdcc4e222b4
builder-outbox: da54240ee31681209a7c55b503b20f6ff7893798
start: 2026-09-28T01:28:05Z
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
joined rows from chunks 1..13: 2976
```
{"resume_clean": {"rows_in": 2976, "rows_out": 2976, "unparsed_kept": 0}}
```
rows after clean (B): 2976
## wording
wording start: 2026-09-28T01:28:16Z | load averages: 224.22 201.82 177.21
wording end: 2026-09-28T02:24:07Z rc=0 | load averages: 202.52 190.60 161.63
new rows: 312; minutes: 55; dialogs per minute: 5.59
last line of glm.log:
```
{"calls": 312, "parsed": 312, "skipped": 2976, "failed_calls": 0, "batches": 274, "stopped": "time", "minutes": 55.8}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 3288, "duplicate_ids": 0, "model_ok": 3288, "temperature_null": 3288, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 7,
  "cue:ask:again": 2,
  "cue:ask:how old": 49,
  "cue:ask:remind me": 37,
  "cue:ask:what": 889,
  "cue:ask:whats": 116,
  "cue:ask:when": 1,
  "cue:ask:where": 31,
  "cue:ask:who": 289,
  "cue:ask:whos": 5,
  "cue:confirm:?": 252,
  "cue:confirm:check": 11,
  "cue:confirm:did i say": 39,
  "cue:confirm:did i tell": 22,
  "cue:confirm:right": 217,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 2,
  "cue:doubt:could be": 5,
  "cue:doubt:dunno": 3,
  "cue:doubt:guess": 4,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 18,
  "cue:doubt:might": 35,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 347,
  "cue:doubt:not totally sure": 64,
  "cue:doubt:think": 61,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 10,
  "cue:former:before": 25,
  "cue:former:no longer": 3,
  "cue:former:once": 1,
  "cue:former:used to": 1263,
  "cue:former:was": 31,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 34,
  "cue:hypothetical:if": 533,
  "cue:hypothetical:imagine": 12,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 30,
  "cue:negation_only:no": 12,
  "cue:negation_only:nt": 475,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 14,
  "cue:plan:down the line": 1,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 3,
  "cue:plan:later on": 1,
  "cue:plan:may": 57,
  "cue:plan:might": 375,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 6,
  "cue:plan:plans": 7,
  "cue:plan:someday": 14,
  "cue:plan:sometime": 13,
  "cue:plan:thinking about": 10,
  "cue:plan:thinking of": 8,
  "cue:plan:will": 33,
  "cue:question:?": 582,
  "cue:someone_else:apparently": 34,
  "cue:someone_else:heard": 129,
  "cue:someone_else:mentioned": 7,
  "cue:someone_else:said": 115,
  "cue:someone_else:says": 82,
  "cue:someone_else:told": 187,
  "dialogs": 3288,
  "drop:ack_answers": 11,
  "drop:assert_hedged": 119,
  "drop:assert_reported": 10,
  "drop:former_present_cue": 37,
  "drop:group_speaker": 169,
  "drop:must_missing": 6,
  "drop:no_cue": 14,
  "drop:no_first_person": 5,
  "drop:no_past_cue": 2,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 23,
  "drop:reply_ask_missing": 151,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 5,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 44,
  "drop:yes_missing": 1,
  "dropped": 558,
  "dropped:ack_after_ask": 84,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 3,
  "dropped:backref": 12,
  "dropped:correct": 45,
  "dropped:correct_ref": 15,
  "dropped:doubt": 4,
  "dropped:former": 45,
  "dropped:hypothetical": 9,
  "dropped:jobhome": 20,
  "dropped:negation_only": 1,
  "dropped:plan": 18,
  "dropped:smalltalk": 8,
  "dropped:someone_else": 2,
  "dropped:teach": 196,
  "dropped:yes_after_ask": 95,
  "kept": 22525,
  "recased": 5,
  "turns": 23083
 },
 "kept_by_family": {
  "ack_after_ask": 698,
  "ambiguous_pronoun": 556,
  "ask": 1426,
  "backref": 1844,
  "confirm": 544,
  "correct": 1762,
  "correct_ref": 959,
  "doubt": 554,
  "former": 1334,
  "hypothetical": 588,
  "jobhome": 836,
  "negation_only": 517,
  "plan": 550,
  "question": 582,
  "smalltalk": 752,
  "someone_else": 554,
  "teach": 7835,
  "yes_after_ask": 634
 }
}
```
```
{
 "glm_kept": {
  "turns": 22525,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.816,
  "noapos_contraction": 0.232,
  "over20_words": 0.195,
  "shapes_per_100": 67.7,
  "write_facts_per_turn": 0.984,
  "write_facts_in_over20": 0.294
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
end: 2026-09-28T02:24:30Z
CHUNK-SUMMARY K=14 B=2976 new=312 calls=312 parsed=312 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=3288 of=6000 stop=ok
