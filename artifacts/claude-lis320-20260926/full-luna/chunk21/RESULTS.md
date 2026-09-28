# lis-320 Luna full run, chunk 21 - BASH-ONLY job claude-lis320-luna-c21-mac

origin/main: 70dcfc05ecfb428d65119d19520a641da6991fe2
builder-outbox: 9abc8cd3dfdca22f769f97b56d18338f943efdbc
start: 2026-09-28T08:42:20Z
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
joined rows from chunks 1..20: 4920
```
{"resume_clean": {"rows_in": 4920, "rows_out": 4920, "unparsed_kept": 0}}
```
rows after clean (B): 4920
## wording
wording start: 2026-09-28T08:42:28Z | load averages: 5.99 5.54 6.23
wording end: 2026-09-28T09:38:14Z rc=0 | load averages: 5.51 5.27 5.26
new rows: 216; minutes: 55; dialogs per minute: 3.87
last line of glm.log:
```
{"calls": 216, "parsed": 216, "skipped": 4920, "failed_calls": 0, "batches": 428, "stopped": "time", "minutes": 55.8}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 5136, "duplicate_ids": 0, "model_ok": 5136, "temperature_null": 5136, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 12,
  "cue:ask:again": 4,
  "cue:ask:how old": 73,
  "cue:ask:remind me": 54,
  "cue:ask:what": 1393,
  "cue:ask:whats": 171,
  "cue:ask:when": 2,
  "cue:ask:where": 49,
  "cue:ask:who": 455,
  "cue:ask:whos": 7,
  "cue:confirm:?": 424,
  "cue:confirm:check": 15,
  "cue:confirm:did i say": 58,
  "cue:confirm:did i tell": 30,
  "cue:confirm:right": 340,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 4,
  "cue:doubt:could be": 14,
  "cue:doubt:dunno": 5,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 28,
  "cue:doubt:might": 61,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 538,
  "cue:doubt:not totally sure": 105,
  "cue:doubt:think": 97,
  "cue:doubt:unsure": 11,
  "cue:former:anymore": 18,
  "cue:former:before": 36,
  "cue:former:no longer": 4,
  "cue:former:once": 2,
  "cue:former:used to": 2004,
  "cue:former:was": 49,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 48,
  "cue:hypothetical:if": 805,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 4,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 48,
  "cue:negation_only:no": 24,
  "cue:negation_only:nt": 729,
  "cue:plan:'ll": 3,
  "cue:plan:at some point": 17,
  "cue:plan:down the line": 3,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 3,
  "cue:plan:may": 77,
  "cue:plan:might": 587,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 10,
  "cue:plan:plans": 9,
  "cue:plan:someday": 20,
  "cue:plan:sometime": 19,
  "cue:plan:thinking about": 15,
  "cue:plan:thinking of": 10,
  "cue:plan:want to": 1,
  "cue:plan:will": 48,
  "cue:question:?": 913,
  "cue:someone_else:apparently": 58,
  "cue:someone_else:heard": 192,
  "cue:someone_else:mentioned": 15,
  "cue:someone_else:said": 188,
  "cue:someone_else:says": 122,
  "cue:someone_else:told": 283,
  "dialogs": 5136,
  "drop:ack_answers": 17,
  "drop:assert_hedged": 173,
  "drop:assert_reported": 16,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 64,
  "drop:group_speaker": 263,
  "drop:must_missing": 9,
  "drop:no_cue": 18,
  "drop:no_first_person": 11,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 2,
  "drop:reads_former": 33,
  "drop:reply_ask_missing": 240,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 2,
  "drop:role_word_missing": 9,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 72,
  "drop:yes_missing": 3,
  "dropped": 868,
  "dropped:ack_after_ask": 141,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 23,
  "dropped:correct": 63,
  "dropped:correct_ref": 21,
  "dropped:doubt": 6,
  "dropped:former": 76,
  "dropped:hypothetical": 14,
  "dropped:jobhome": 28,
  "dropped:negation_only": 1,
  "dropped:plan": 36,
  "dropped:smalltalk": 11,
  "dropped:someone_else": 2,
  "dropped:teach": 297,
  "dropped:yes_after_ask": 144,
  "kept": 35186,
  "recased": 8,
  "turns": 36054
 },
 "kept_by_family": {
  "ack_after_ask": 1053,
  "ambiguous_pronoun": 898,
  "ask": 2220,
  "backref": 2913,
  "confirm": 870,
  "correct": 2770,
  "correct_ref": 1498,
  "doubt": 878,
  "former": 2114,
  "hypothetical": 880,
  "jobhome": 1334,
  "negation_only": 801,
  "plan": 832,
  "question": 913,
  "smalltalk": 1156,
  "someone_else": 858,
  "teach": 12220,
  "yes_after_ask": 978
 }
}
```
```
{
 "glm_kept": {
  "turns": 35186,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.813,
  "noapos_contraction": 0.235,
  "over20_words": 0.192,
  "shapes_per_100": 64.6,
  "write_facts_per_turn": 0.986,
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
end: 2026-09-28T09:38:34Z
CHUNK-SUMMARY K=21 B=4920 new=216 calls=216 parsed=216 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=5136 of=6000 stop=ok
