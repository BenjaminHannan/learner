# lis-320 Luna full run, chunk 3 - BASH-ONLY job claude-lis320-luna-c3-mac

origin/main: ea10f33c8027d538ffda5c83cf5e54ce4e28fa49
builder-outbox: 9d99df129d623cb6a7a3e6630950ed498f6ef6a6
start: 2026-09-27T12:04:16Z
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
joined rows from chunks 1..2: 360
```
{"resume_clean": {"rows_in": 360, "rows_out": 360, "unparsed_kept": 0}}
```
rows after clean (B): 360
## wording
wording start: 2026-09-27T12:04:24Z | load averages: 31.27 33.42 32.62
wording end: 2026-09-27T12:59:52Z rc=0 | load averages: 54.21 51.42 55.12
new rows: 228; minutes: 55; dialogs per minute: 4.11
last line of glm.log:
```
{"calls": 228, "parsed": 228, "skipped": 360, "failed_calls": 0, "batches": 49, "stopped": "time", "minutes": 55.5}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 588, "duplicate_ids": 0, "model_ok": 588, "temperature_null": 588, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:how old": 10,
  "cue:ask:remind me": 8,
  "cue:ask:what": 164,
  "cue:ask:whats": 17,
  "cue:ask:where": 7,
  "cue:ask:who": 49,
  "cue:confirm:?": 41,
  "cue:confirm:check": 2,
  "cue:confirm:did i say": 6,
  "cue:confirm:did i tell": 7,
  "cue:confirm:right": 47,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:maybe": 3,
  "cue:doubt:might": 7,
  "cue:doubt:not really sure": 2,
  "cue:doubt:not sure": 67,
  "cue:doubt:not totally sure": 10,
  "cue:doubt:think": 16,
  "cue:doubt:unsure": 2,
  "cue:former:anymore": 3,
  "cue:former:before": 5,
  "cue:former:used to": 237,
  "cue:former:was": 10,
  "cue:hypothetical:hypothetically": 7,
  "cue:hypothetical:if": 101,
  "cue:hypothetical:imagine": 2,
  "cue:hypothetical:pretend": 1,
  "cue:negation_only:n't": 3,
  "cue:negation_only:no": 4,
  "cue:negation_only:nt": 87,
  "cue:plan:at some point": 3,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 16,
  "cue:plan:might": 70,
  "cue:plan:planning": 2,
  "cue:plan:someday": 1,
  "cue:plan:sometime": 3,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 9,
  "cue:question:?": 108,
  "cue:someone_else:apparently": 3,
  "cue:someone_else:heard": 20,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 16,
  "cue:someone_else:says": 17,
  "cue:someone_else:told": 28,
  "dialogs": 588,
  "drop:assert_hedged": 23,
  "drop:former_present_cue": 5,
  "drop:group_speaker": 30,
  "drop:must_missing": 1,
  "drop:no_cue": 3,
  "drop:no_first_person": 1,
  "drop:no_past_cue": 1,
  "drop:reads_former": 4,
  "drop:reply_ask_missing": 27,
  "drop:stray_name": 8,
  "dropped": 94,
  "dropped:ack_after_ask": 13,
  "dropped:backref": 1,
  "dropped:correct": 8,
  "dropped:correct_ref": 4,
  "dropped:former": 7,
  "dropped:hypothetical": 4,
  "dropped:jobhome": 4,
  "dropped:plan": 3,
  "dropped:smalltalk": 1,
  "dropped:teach": 33,
  "dropped:yes_after_ask": 16,
  "kept": 4040,
  "recased": 0,
  "turns": 4134
 },
 "kept_by_family": {
  "ack_after_ask": 129,
  "ambiguous_pronoun": 86,
  "ask": 258,
  "backref": 306,
  "confirm": 103,
  "correct": 307,
  "correct_ref": 173,
  "doubt": 111,
  "former": 255,
  "hypothetical": 111,
  "jobhome": 144,
  "negation_only": 94,
  "plan": 108,
  "question": 108,
  "smalltalk": 112,
  "someone_else": 86,
  "teach": 1435,
  "yes_after_ask": 114
 }
}
```
```
{
 "glm_kept": {
  "turns": 4040,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.822,
  "noapos_contraction": 0.243,
  "over20_words": 0.2,
  "shapes_per_100": 80.6,
  "write_facts_per_turn": 0.997,
  "write_facts_in_over20": 0.318
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
end: 2026-09-27T12:59:56Z
CHUNK-SUMMARY K=3 B=360 new=228 calls=228 parsed=228 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=588 of=6000 stop=ok
