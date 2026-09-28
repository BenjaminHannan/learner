# lis-320 Luna full run, chunk 19 - BASH-ONLY job claude-lis320-luna-c19-mac

origin/main: b1159076e8d843335cee6f5fda6ea6de515d3549
builder-outbox: c6baf74d98787fe288c7038afa346ccff5533409
start: 2026-09-28T06:41:00Z
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
joined rows from chunks 1..18: 4440
```
{"resume_clean": {"rows_in": 4440, "rows_out": 4440, "unparsed_kept": 0}}
```
rows after clean (B): 4440
## wording
wording start: 2026-09-28T06:41:07Z | load averages: 10.59 7.62 8.70
wording end: 2026-09-28T07:37:37Z rc=0 | load averages: 4.90 5.90 6.48
new rows: 264; minutes: 56; dialogs per minute: 4.67
last line of glm.log:
```
{"calls": 264, "parsed": 264, "skipped": 4440, "failed_calls": 0, "batches": 392, "stopped": "time", "minutes": 56.5}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 4704, "duplicate_ids": 0, "model_ok": 4704, "temperature_null": 4704, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 12,
  "cue:ask:again": 4,
  "cue:ask:how old": 69,
  "cue:ask:remind me": 52,
  "cue:ask:what": 1272,
  "cue:ask:whats": 160,
  "cue:ask:when": 2,
  "cue:ask:where": 46,
  "cue:ask:who": 422,
  "cue:ask:whos": 7,
  "cue:confirm:?": 383,
  "cue:confirm:check": 12,
  "cue:confirm:did i say": 52,
  "cue:confirm:did i tell": 30,
  "cue:confirm:right": 311,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 4,
  "cue:doubt:could be": 12,
  "cue:doubt:dunno": 4,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 25,
  "cue:doubt:might": 59,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 495,
  "cue:doubt:not totally sure": 95,
  "cue:doubt:think": 87,
  "cue:doubt:unsure": 9,
  "cue:former:anymore": 15,
  "cue:former:before": 33,
  "cue:former:no longer": 3,
  "cue:former:once": 2,
  "cue:former:used to": 1822,
  "cue:former:was": 42,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 42,
  "cue:hypothetical:if": 748,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 45,
  "cue:negation_only:no": 22,
  "cue:negation_only:nt": 672,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 17,
  "cue:plan:down the line": 2,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 2,
  "cue:plan:may": 74,
  "cue:plan:might": 548,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 10,
  "cue:plan:plans": 9,
  "cue:plan:someday": 18,
  "cue:plan:sometime": 17,
  "cue:plan:thinking about": 12,
  "cue:plan:thinking of": 9,
  "cue:plan:will": 46,
  "cue:question:?": 828,
  "cue:someone_else:apparently": 49,
  "cue:someone_else:heard": 182,
  "cue:someone_else:mentioned": 12,
  "cue:someone_else:said": 175,
  "cue:someone_else:says": 110,
  "cue:someone_else:told": 263,
  "dialogs": 4704,
  "drop:ack_answers": 16,
  "drop:assert_hedged": 162,
  "drop:assert_reported": 16,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 56,
  "drop:group_speaker": 248,
  "drop:must_missing": 9,
  "drop:no_cue": 17,
  "drop:no_first_person": 10,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 31,
  "drop:reply_ask_missing": 218,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 8,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 71,
  "drop:yes_missing": 3,
  "dropped": 804,
  "dropped:ack_after_ask": 127,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 22,
  "dropped:correct": 61,
  "dropped:correct_ref": 19,
  "dropped:doubt": 5,
  "dropped:former": 68,
  "dropped:hypothetical": 13,
  "dropped:jobhome": 27,
  "dropped:negation_only": 1,
  "dropped:plan": 33,
  "dropped:smalltalk": 11,
  "dropped:someone_else": 2,
  "dropped:teach": 275,
  "dropped:yes_after_ask": 135,
  "kept": 32227,
  "recased": 8,
  "turns": 33031
 },
 "kept_by_family": {
  "ack_after_ask": 968,
  "ambiguous_pronoun": 820,
  "ask": 2046,
  "backref": 2663,
  "confirm": 791,
  "correct": 2542,
  "correct_ref": 1365,
  "doubt": 805,
  "former": 1918,
  "hypothetical": 816,
  "jobhome": 1223,
  "negation_only": 739,
  "plan": 776,
  "question": 828,
  "smalltalk": 1050,
  "someone_else": 791,
  "teach": 11184,
  "yes_after_ask": 902
 }
}
```
```
{
 "glm_kept": {
  "turns": 32227,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.814,
  "noapos_contraction": 0.234,
  "over20_words": 0.193,
  "shapes_per_100": 65.1,
  "write_facts_per_turn": 0.985,
  "write_facts_in_over20": 0.289
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
end: 2026-09-28T07:37:56Z
CHUNK-SUMMARY K=19 B=4440 new=264 calls=264 parsed=264 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=4704 of=6000 stop=ok
