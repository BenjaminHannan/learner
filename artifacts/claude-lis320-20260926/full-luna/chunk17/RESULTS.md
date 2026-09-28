# lis-320 Luna full run, chunk 17 - BASH-ONLY job claude-lis320-luna-c17-mac

origin/main: 695f58b0bc486d1ed72eda73f0f6a5e996d44704
builder-outbox: 5f7433b9313140be98e96ff1d63e9e606a554ff6
start: 2026-09-28T04:39:53Z
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
joined rows from chunks 1..16: 3876
```
{"resume_clean": {"rows_in": 3876, "rows_out": 3876, "unparsed_kept": 0}}
```
rows after clean (B): 3876
## wording
wording start: 2026-09-28T04:40:01Z | load averages: 64.07 75.13 86.85
wording end: 2026-09-28T05:36:35Z rc=0 | load averages: 35.91 29.25 28.34
new rows: 300; minutes: 56; dialogs per minute: 5.30
last line of glm.log:
```
{"calls": 300, "parsed": 300, "skipped": 3876, "failed_calls": 0, "batches": 348, "stopped": "time", "minutes": 56.6}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 4176, "duplicate_ids": 0, "model_ok": 4176, "temperature_null": 4176, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 12,
  "cue:ask:again": 3,
  "cue:ask:how old": 61,
  "cue:ask:remind me": 47,
  "cue:ask:what": 1114,
  "cue:ask:whats": 144,
  "cue:ask:when": 2,
  "cue:ask:where": 41,
  "cue:ask:who": 366,
  "cue:ask:whos": 7,
  "cue:confirm:?": 322,
  "cue:confirm:check": 11,
  "cue:confirm:did i say": 47,
  "cue:confirm:did i tell": 25,
  "cue:confirm:right": 271,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 3,
  "cue:doubt:could be": 11,
  "cue:doubt:dunno": 4,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 20,
  "cue:doubt:might": 50,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 436,
  "cue:doubt:not totally sure": 80,
  "cue:doubt:think": 77,
  "cue:doubt:unsure": 7,
  "cue:former:anymore": 15,
  "cue:former:before": 30,
  "cue:former:no longer": 3,
  "cue:former:once": 1,
  "cue:former:used to": 1634,
  "cue:former:was": 39,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 39,
  "cue:hypothetical:if": 668,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 44,
  "cue:negation_only:no": 18,
  "cue:negation_only:nt": 592,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 16,
  "cue:plan:down the line": 2,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 2,
  "cue:plan:may": 67,
  "cue:plan:might": 473,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 9,
  "cue:plan:plans": 9,
  "cue:plan:someday": 17,
  "cue:plan:sometime": 15,
  "cue:plan:thinking about": 11,
  "cue:plan:thinking of": 8,
  "cue:plan:will": 43,
  "cue:question:?": 738,
  "cue:someone_else:apparently": 42,
  "cue:someone_else:heard": 161,
  "cue:someone_else:mentioned": 9,
  "cue:someone_else:said": 151,
  "cue:someone_else:says": 101,
  "cue:someone_else:told": 230,
  "dialogs": 4176,
  "drop:ack_answers": 14,
  "drop:assert_hedged": 143,
  "drop:assert_reported": 13,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 49,
  "drop:group_speaker": 221,
  "drop:must_missing": 8,
  "drop:no_cue": 16,
  "drop:no_first_person": 10,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 26,
  "drop:reply_ask_missing": 197,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 8,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 60,
  "drop:yes_missing": 3,
  "dropped": 714,
  "dropped:ack_after_ask": 114,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 17,
  "dropped:correct": 53,
  "dropped:correct_ref": 16,
  "dropped:doubt": 5,
  "dropped:former": 61,
  "dropped:hypothetical": 13,
  "dropped:jobhome": 22,
  "dropped:negation_only": 1,
  "dropped:plan": 27,
  "dropped:smalltalk": 10,
  "dropped:someone_else": 2,
  "dropped:teach": 248,
  "dropped:yes_after_ask": 120,
  "kept": 28611,
  "recased": 8,
  "turns": 29325
 },
 "kept_by_family": {
  "ack_after_ask": 877,
  "ambiguous_pronoun": 724,
  "ask": 1797,
  "backref": 2361,
  "confirm": 679,
  "correct": 2241,
  "correct_ref": 1215,
  "doubt": 703,
  "former": 1723,
  "hypothetical": 733,
  "jobhome": 1090,
  "negation_only": 654,
  "plan": 684,
  "question": 738,
  "smalltalk": 948,
  "someone_else": 694,
  "teach": 9975,
  "yes_after_ask": 775
 }
}
```
```
{
 "glm_kept": {
  "turns": 28611,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.814,
  "noapos_contraction": 0.233,
  "over20_words": 0.193,
  "shapes_per_100": 65.9,
  "write_facts_per_turn": 0.987,
  "write_facts_in_over20": 0.29
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
end: 2026-09-28T05:36:52Z
CHUNK-SUMMARY K=17 B=3876 new=300 calls=300 parsed=300 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=4176 of=6000 stop=ok
