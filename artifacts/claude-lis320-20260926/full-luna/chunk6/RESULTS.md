# lis-320 Luna full run, chunk 6 - BASH-ONLY job claude-lis320-luna-c6-mac

origin/main: a4eb42eab53a49b0a451ea598ebd71306671d702
builder-outbox: 0bd938b26eed822654b543d0aeb00e553605fd3c
start: 2026-09-27T15:08:15Z
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
joined rows from chunks 1..5: 1008
```
{"resume_clean": {"rows_in": 1008, "rows_out": 1008, "unparsed_kept": 0}}
```
rows after clean (B): 1008
## wording
wording start: 2026-09-27T15:08:22Z | load averages: 47.32 50.43 51.02
wording end: 2026-09-27T16:04:55Z rc=0 | load averages: 139.35 114.81 84.53
new rows: 168; minutes: 56; dialogs per minute: 2.97
last line of glm.log:
```
{"calls": 168, "parsed": 168, "skipped": 1008, "failed_calls": 0, "batches": 98, "stopped": "time", "minutes": 56.5}
```
call failed lines: 0; failed helper tries: 1; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 1176, "duplicate_ids": 0, "model_ok": 1176, "temperature_null": 1176, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:again": 1,
  "cue:ask:how old": 16,
  "cue:ask:remind me": 19,
  "cue:ask:what": 342,
  "cue:ask:whats": 41,
  "cue:ask:where": 14,
  "cue:ask:who": 86,
  "cue:ask:whos": 3,
  "cue:confirm:?": 79,
  "cue:confirm:check": 4,
  "cue:confirm:did i say": 10,
  "cue:confirm:did i tell": 8,
  "cue:confirm:right": 88,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 1,
  "cue:doubt:maybe": 6,
  "cue:doubt:might": 15,
  "cue:doubt:not really sure": 3,
  "cue:doubt:not sure": 128,
  "cue:doubt:not totally sure": 19,
  "cue:doubt:think": 25,
  "cue:doubt:unsure": 2,
  "cue:former:anymore": 4,
  "cue:former:before": 14,
  "cue:former:used to": 445,
  "cue:former:was": 11,
  "cue:hypothetical:hypothetically": 14,
  "cue:hypothetical:if": 202,
  "cue:hypothetical:imagine": 7,
  "cue:hypothetical:pretend": 2,
  "cue:hypothetical:suppose": 1,
  "cue:negation_only:n't": 11,
  "cue:negation_only:no": 6,
  "cue:negation_only:nt": 169,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 10,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 28,
  "cue:plan:might": 134,
  "cue:plan:one day": 1,
  "cue:plan:planning": 3,
  "cue:plan:plans": 2,
  "cue:plan:someday": 4,
  "cue:plan:sometime": 6,
  "cue:plan:thinking about": 3,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 14,
  "cue:question:?": 209,
  "cue:someone_else:apparently": 8,
  "cue:someone_else:heard": 46,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 36,
  "cue:someone_else:says": 35,
  "cue:someone_else:told": 62,
  "dialogs": 1176,
  "drop:ack_answers": 1,
  "drop:assert_hedged": 42,
  "drop:assert_reported": 1,
  "drop:former_present_cue": 11,
  "drop:group_speaker": 56,
  "drop:must_missing": 3,
  "drop:no_cue": 9,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 9,
  "drop:reply_ask_missing": 56,
  "drop:role_word_missing": 1,
  "drop:stray_name": 18,
  "dropped": 193,
  "dropped:ack_after_ask": 29,
  "dropped:ask": 1,
  "dropped:backref": 4,
  "dropped:correct": 14,
  "dropped:correct_ref": 6,
  "dropped:doubt": 3,
  "dropped:former": 13,
  "dropped:hypothetical": 6,
  "dropped:jobhome": 9,
  "dropped:negation_only": 1,
  "dropped:plan": 9,
  "dropped:smalltalk": 2,
  "dropped:teach": 64,
  "dropped:yes_after_ask": 32,
  "kept": 8067,
  "recased": 3,
  "turns": 8260
 },
 "kept_by_family": {
  "ack_after_ask": 252,
  "ambiguous_pronoun": 188,
  "ask": 525,
  "backref": 642,
  "confirm": 189,
  "correct": 629,
  "correct_ref": 353,
  "doubt": 203,
  "former": 474,
  "hypothetical": 226,
  "jobhome": 310,
  "negation_only": 186,
  "plan": 211,
  "question": 209,
  "smalltalk": 258,
  "someone_else": 189,
  "teach": 2789,
  "yes_after_ask": 234
 }
}
```
```
{
 "glm_kept": {
  "turns": 8067,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.822,
  "noapos_contraction": 0.232,
  "over20_words": 0.203,
  "shapes_per_100": 75.3,
  "write_facts_per_turn": 0.986,
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
end: 2026-09-27T16:05:01Z
CHUNK-SUMMARY K=6 B=1008 new=168 calls=168 parsed=168 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=1 ratelimit=0 worded_ok=1176 of=6000 stop=ok
