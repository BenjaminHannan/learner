# lis-320 Luna full run, chunk 10 - BASH-ONLY job claude-lis320-luna-c10b-mac (re-run: c10 stopped at its git fetch)

origin/main: 165213cb5884875975c32aa1e19397144545cb41
builder-outbox: 858fef1d9ce8c6f2b8207cabb46dcdea00370dba
start: 2026-09-27T19:39:27Z
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
joined rows from chunks 1..9: 1800
```
{"resume_clean": {"rows_in": 1800, "rows_out": 1800, "unparsed_kept": 0}}
```
rows after clean (B): 1800
## wording
wording start: 2026-09-27T19:39:36Z | load averages: 28.58 23.42 24.40
wording end: 2026-09-27T20:35:41Z rc=0 | load averages: 28.22 40.76 60.80
new rows: 228; minutes: 56; dialogs per minute: 4.07
last line of glm.log:
```
{"calls": 228, "parsed": 228, "skipped": 1800, "failed_calls": 0, "batches": 169, "stopped": "time", "minutes": 56.1}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 2028, "duplicate_ids": 0, "model_ok": 2028, "temperature_null": 2028, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 5,
  "cue:ask:again": 2,
  "cue:ask:how old": 26,
  "cue:ask:remind me": 29,
  "cue:ask:what": 568,
  "cue:ask:whats": 73,
  "cue:ask:where": 20,
  "cue:ask:who": 158,
  "cue:ask:whos": 5,
  "cue:confirm:?": 138,
  "cue:confirm:check": 8,
  "cue:confirm:did i say": 23,
  "cue:confirm:did i tell": 11,
  "cue:confirm:right": 150,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 1,
  "cue:doubt:could be": 3,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 2,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 13,
  "cue:doubt:might": 25,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 218,
  "cue:doubt:not totally sure": 35,
  "cue:doubt:think": 41,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 7,
  "cue:former:before": 23,
  "cue:former:once": 1,
  "cue:former:used to": 776,
  "cue:former:was": 23,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 26,
  "cue:hypothetical:if": 342,
  "cue:hypothetical:imagine": 9,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 4,
  "cue:negation_only:n't": 18,
  "cue:negation_only:no": 8,
  "cue:negation_only:nt": 303,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 12,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 37,
  "cue:plan:might": 223,
  "cue:plan:one day": 1,
  "cue:plan:planning": 6,
  "cue:plan:plans": 4,
  "cue:plan:someday": 11,
  "cue:plan:sometime": 10,
  "cue:plan:thinking about": 5,
  "cue:plan:thinking of": 5,
  "cue:plan:will": 21,
  "cue:question:?": 356,
  "cue:someone_else:apparently": 17,
  "cue:someone_else:heard": 80,
  "cue:someone_else:mentioned": 4,
  "cue:someone_else:said": 64,
  "cue:someone_else:says": 54,
  "cue:someone_else:told": 108,
  "dialogs": 2028,
  "drop:ack_answers": 4,
  "drop:assert_hedged": 75,
  "drop:assert_reported": 4,
  "drop:former_present_cue": 23,
  "drop:group_speaker": 107,
  "drop:must_missing": 4,
  "drop:no_cue": 11,
  "drop:no_first_person": 3,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 14,
  "drop:reply_ask_missing": 98,
  "drop:reply_new_name": 1,
  "drop:role_word_missing": 2,
  "drop:stray_name": 28,
  "drop:yes_missing": 1,
  "dropped": 348,
  "dropped:ack_after_ask": 50,
  "dropped:ask": 1,
  "dropped:backref": 6,
  "dropped:correct": 25,
  "dropped:correct_ref": 10,
  "dropped:doubt": 4,
  "dropped:former": 26,
  "dropped:hypothetical": 7,
  "dropped:jobhome": 12,
  "dropped:negation_only": 1,
  "dropped:plan": 11,
  "dropped:smalltalk": 4,
  "dropped:teach": 131,
  "dropped:yes_after_ask": 60,
  "kept": 13891,
  "recased": 4,
  "turns": 14239
 },
 "kept_by_family": {
  "ack_after_ask": 436,
  "ambiguous_pronoun": 345,
  "ask": 886,
  "backref": 1124,
  "confirm": 333,
  "correct": 1061,
  "correct_ref": 596,
  "doubt": 353,
  "former": 831,
  "hypothetical": 384,
  "jobhome": 533,
  "negation_only": 329,
  "plan": 339,
  "question": 356,
  "smalltalk": 445,
  "someone_else": 327,
  "teach": 4831,
  "yes_after_ask": 382
 }
}
```
```
{
 "glm_kept": {
  "turns": 13891,
  "words_median": 9,
  "words_p90": 27,
  "lowercase_start": 0.82,
  "noapos_contraction": 0.234,
  "over20_words": 0.204,
  "shapes_per_100": 71.0,
  "write_facts_per_turn": 0.983,
  "write_facts_in_over20": 0.309
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
end: 2026-09-27T20:35:50Z
CHUNK-SUMMARY K=10 B=1800 new=228 calls=228 parsed=228 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=2028 of=6000 stop=ok
