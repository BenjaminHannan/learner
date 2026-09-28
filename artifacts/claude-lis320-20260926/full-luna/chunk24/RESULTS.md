# lis-320 Luna full run, chunk 24 - BASH-ONLY job claude-lis320-luna-c24-mac

origin/main: 0477120fd97cbaded17a4f42f1a1237644f9bfe8
builder-outbox: 22b4d8d555cfa46180654a935db007533aef9279
start: 2026-09-28T11:43:42Z
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
joined rows from chunks 1..23: 5640
```
{"resume_clean": {"rows_in": 5640, "rows_out": 5640, "unparsed_kept": 0}}
```
rows after clean (B): 5640
## wording
wording start: 2026-09-28T11:43:49Z | load averages: 7.22 6.81 6.90
wording end: 2026-09-28T12:39:51Z rc=0 | load averages: 4.49 6.26 6.96
new rows: 216; minutes: 56; dialogs per minute: 3.85
last line of glm.log:
```
{"calls": 216, "parsed": 216, "skipped": 5640, "failed_calls": 0, "batches": 488, "stopped": "time", "minutes": 56.0}
```
call failed lines: 0; failed helper tries: 1; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 5856, "duplicate_ids": 0, "model_ok": 5856, "temperature_null": 5856, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 15,
  "cue:ask:again": 4,
  "cue:ask:how old": 89,
  "cue:ask:remind me": 62,
  "cue:ask:what": 1588,
  "cue:ask:whats": 189,
  "cue:ask:when": 4,
  "cue:ask:where": 53,
  "cue:ask:who": 527,
  "cue:ask:whos": 7,
  "cue:confirm:?": 485,
  "cue:confirm:check": 21,
  "cue:confirm:did i say": 65,
  "cue:confirm:did i tell": 38,
  "cue:confirm:right": 377,
  "cue:confirm:was it": 2,
  "cue:confirm:yeah": 3,
  "cue:doubt:cant remember": 6,
  "cue:doubt:could be": 15,
  "cue:doubt:dunno": 6,
  "cue:doubt:guess": 6,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 32,
  "cue:doubt:might": 66,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 608,
  "cue:doubt:not totally sure": 116,
  "cue:doubt:think": 111,
  "cue:doubt:unsure": 15,
  "cue:former:anymore": 20,
  "cue:former:before": 40,
  "cue:former:no longer": 5,
  "cue:former:once": 2,
  "cue:former:used to": 2300,
  "cue:former:was": 55,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 51,
  "cue:hypothetical:if": 922,
  "cue:hypothetical:imagine": 18,
  "cue:hypothetical:pretend": 5,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 52,
  "cue:negation_only:no": 31,
  "cue:negation_only:nt": 837,
  "cue:plan:'ll": 3,
  "cue:plan:at some point": 18,
  "cue:plan:down the line": 5,
  "cue:plan:going to": 3,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 3,
  "cue:plan:may": 91,
  "cue:plan:might": 691,
  "cue:plan:next": 1,
  "cue:plan:one day": 3,
  "cue:plan:plan": 1,
  "cue:plan:planning": 15,
  "cue:plan:plans": 10,
  "cue:plan:someday": 22,
  "cue:plan:sometime": 22,
  "cue:plan:thinking about": 18,
  "cue:plan:thinking of": 10,
  "cue:plan:want to": 1,
  "cue:plan:will": 48,
  "cue:question:?": 1036,
  "cue:someone_else:apparently": 65,
  "cue:someone_else:heard": 217,
  "cue:someone_else:mentioned": 19,
  "cue:someone_else:said": 205,
  "cue:someone_else:says": 134,
  "cue:someone_else:told": 325,
  "dialogs": 5856,
  "drop:ack_answers": 18,
  "drop:assert_hedged": 192,
  "drop:assert_reported": 17,
  "drop:forbidden_in_reply": 1,
  "drop:forbidden_in_turn": 1,
  "drop:former_present_cue": 71,
  "drop:group_speaker": 292,
  "drop:must_missing": 11,
  "drop:no_cue": 19,
  "drop:no_first_person": 14,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 2,
  "drop:reads_former": 35,
  "drop:reply_ask_missing": 267,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 2,
  "drop:role_word_missing": 10,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 85,
  "drop:yes_missing": 3,
  "dropped": 964,
  "dropped:ack_after_ask": 154,
  "dropped:ambiguous_pronoun": 2,
  "dropped:ask": 4,
  "dropped:backref": 26,
  "dropped:correct": 72,
  "dropped:correct_ref": 22,
  "dropped:doubt": 7,
  "dropped:former": 83,
  "dropped:hypothetical": 14,
  "dropped:jobhome": 31,
  "dropped:negation_only": 1,
  "dropped:plan": 41,
  "dropped:smalltalk": 14,
  "dropped:someone_else": 2,
  "dropped:teach": 328,
  "dropped:yes_after_ask": 163,
  "kept": 40084,
  "recased": 10,
  "turns": 41048
 },
 "kept_by_family": {
  "ack_after_ask": 1195,
  "ambiguous_pronoun": 1024,
  "ask": 2538,
  "backref": 3299,
  "confirm": 991,
  "correct": 3166,
  "correct_ref": 1701,
  "doubt": 991,
  "former": 2423,
  "hypothetical": 1002,
  "jobhome": 1512,
  "negation_only": 920,
  "plan": 969,
  "question": 1036,
  "smalltalk": 1337,
  "someone_else": 965,
  "teach": 13902,
  "yes_after_ask": 1113
 }
}
```
```
{
 "glm_kept": {
  "turns": 40084,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.812,
  "noapos_contraction": 0.234,
  "over20_words": 0.19,
  "shapes_per_100": 63.8,
  "write_facts_per_turn": 0.984,
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
end: 2026-09-28T12:40:14Z
CHUNK-SUMMARY K=24 B=5640 new=216 calls=216 parsed=216 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=1 ratelimit=0 worded_ok=5856 of=6000 stop=ok
