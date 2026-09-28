# lis-320 Luna full run, chunk 16 - BASH-ONLY job claude-lis320-luna-c16-mac

origin/main: 7f68b1455c51ee7f6508f08367b65be33c1b6ea4
builder-outbox: a1b290e1a24ab9a41b70762c8fdcf939b8cb6bb7
start: 2026-09-28T03:40:44Z
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
joined rows from chunks 1..15: 3576
```
{"resume_clean": {"rows_in": 3576, "rows_out": 3576, "unparsed_kept": 0}}
```
rows after clean (B): 3576
## wording
wording start: 2026-09-28T03:40:56Z | load averages: 130.71 133.73 161.77
wording end: 2026-09-28T04:36:58Z rc=0 | load averages: 78.41 79.43 90.47
new rows: 300; minutes: 56; dialogs per minute: 5.35
last line of glm.log:
```
{"calls": 300, "parsed": 300, "skipped": 3576, "failed_calls": 0, "batches": 323, "stopped": "time", "minutes": 56.0}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 3876, "duplicate_ids": 0, "model_ok": 3876, "temperature_null": 3876, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 7,
  "cue:ask:again": 3,
  "cue:ask:how old": 54,
  "cue:ask:remind me": 44,
  "cue:ask:what": 1041,
  "cue:ask:whats": 138,
  "cue:ask:when": 2,
  "cue:ask:where": 38,
  "cue:ask:who": 339,
  "cue:ask:whos": 6,
  "cue:confirm:?": 299,
  "cue:confirm:check": 11,
  "cue:confirm:did i say": 44,
  "cue:confirm:did i tell": 25,
  "cue:confirm:right": 254,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 3,
  "cue:doubt:could be": 10,
  "cue:doubt:dunno": 4,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 20,
  "cue:doubt:might": 43,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 406,
  "cue:doubt:not totally sure": 74,
  "cue:doubt:think": 70,
  "cue:doubt:unsure": 7,
  "cue:former:anymore": 11,
  "cue:former:before": 28,
  "cue:former:no longer": 3,
  "cue:former:once": 1,
  "cue:former:used to": 1504,
  "cue:former:was": 37,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 38,
  "cue:hypothetical:if": 616,
  "cue:hypothetical:imagine": 16,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 36,
  "cue:negation_only:no": 17,
  "cue:negation_only:nt": 553,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 16,
  "cue:plan:down the line": 2,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 1,
  "cue:plan:may": 66,
  "cue:plan:might": 438,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 7,
  "cue:plan:plans": 7,
  "cue:plan:someday": 16,
  "cue:plan:sometime": 14,
  "cue:plan:thinking about": 11,
  "cue:plan:thinking of": 8,
  "cue:plan:will": 40,
  "cue:question:?": 685,
  "cue:someone_else:apparently": 37,
  "cue:someone_else:heard": 146,
  "cue:someone_else:mentioned": 8,
  "cue:someone_else:said": 143,
  "cue:someone_else:says": 95,
  "cue:someone_else:told": 216,
  "dialogs": 3876,
  "drop:ack_answers": 14,
  "drop:assert_hedged": 137,
  "drop:assert_reported": 11,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 43,
  "drop:group_speaker": 206,
  "drop:must_missing": 7,
  "drop:no_cue": 15,
  "drop:no_first_person": 9,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 25,
  "drop:reply_ask_missing": 186,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 7,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 56,
  "drop:yes_missing": 2,
  "dropped": 672,
  "dropped:ack_after_ask": 108,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 16,
  "dropped:correct": 52,
  "dropped:correct_ref": 15,
  "dropped:doubt": 4,
  "dropped:former": 54,
  "dropped:hypothetical": 12,
  "dropped:jobhome": 21,
  "dropped:negation_only": 1,
  "dropped:plan": 24,
  "dropped:smalltalk": 10,
  "dropped:someone_else": 2,
  "dropped:teach": 234,
  "dropped:yes_after_ask": 114,
  "kept": 26536,
  "recased": 8,
  "turns": 27208
 },
 "kept_by_family": {
  "ack_after_ask": 816,
  "ambiguous_pronoun": 665,
  "ask": 1672,
  "backref": 2179,
  "confirm": 636,
  "correct": 2089,
  "correct_ref": 1129,
  "doubt": 652,
  "former": 1585,
  "hypothetical": 679,
  "jobhome": 988,
  "negation_only": 606,
  "plan": 638,
  "question": 685,
  "smalltalk": 889,
  "someone_else": 645,
  "teach": 9254,
  "yes_after_ask": 729
 }
}
```
```
{
 "glm_kept": {
  "turns": 26536,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.814,
  "noapos_contraction": 0.233,
  "over20_words": 0.194,
  "shapes_per_100": 66.6,
  "write_facts_per_turn": 0.986,
  "write_facts_in_over20": 0.291
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
end: 2026-09-28T04:37:18Z
CHUNK-SUMMARY K=16 B=3576 new=300 calls=300 parsed=300 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=3876 of=6000 stop=ok
