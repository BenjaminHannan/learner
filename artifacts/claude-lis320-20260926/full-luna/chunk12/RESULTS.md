# lis-320 Luna full run, chunk 12 - BASH-ONLY job claude-lis320-luna-c12-mac

origin/main: e14cffe220b1d2a3517859954b197a725cc1a12d
builder-outbox: 4399f77e9248c3a35e540b5bf43b37278b27829c
start: 2026-09-27T23:27:55Z
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
joined rows from chunks 1..11: 2352
```
{"resume_clean": {"rows_in": 2352, "rows_out": 2352, "unparsed_kept": 0}}
```
rows after clean (B): 2352
## wording
wording start: 2026-09-27T23:28:02Z | load averages: 31.84 26.53 31.35
wording end: 2026-09-28T00:25:07Z rc=0 | load averages: 119.40 88.66 79.96
new rows: 312; minutes: 57; dialogs per minute: 5.47
last line of glm.log:
```
{"calls": 312, "parsed": 312, "skipped": 2352, "failed_calls": 0, "batches": 222, "stopped": "time", "minutes": 57.1}
```
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
```
```
## rawcheck2 (all rows so far)
```
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 2664, "duplicate_ids": 0, "model_ok": 2664, "temperature_null": 2664, "dup3_texts": 0, "not_in_seeds": 0}
```
## check_we3 and style (all rows so far)
check rc=0
```
{
 "counts": {
  "cue:ask:?": 5,
  "cue:ask:again": 2,
  "cue:ask:how old": 35,
  "cue:ask:remind me": 31,
  "cue:ask:what": 714,
  "cue:ask:whats": 97,
  "cue:ask:where": 26,
  "cue:ask:who": 224,
  "cue:ask:whos": 5,
  "cue:confirm:?": 197,
  "cue:confirm:check": 9,
  "cue:confirm:did i say": 34,
  "cue:confirm:did i tell": 15,
  "cue:confirm:right": 182,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 1,
  "cue:doubt:could be": 4,
  "cue:doubt:dunno": 3,
  "cue:doubt:guess": 4,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 16,
  "cue:doubt:might": 29,
  "cue:doubt:not certain": 1,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 292,
  "cue:doubt:not totally sure": 50,
  "cue:doubt:think": 51,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 9,
  "cue:former:before": 24,
  "cue:former:no longer": 1,
  "cue:former:once": 1,
  "cue:former:used to": 1015,
  "cue:former:was": 28,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 32,
  "cue:hypothetical:if": 426,
  "cue:hypothetical:imagine": 12,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 24,
  "cue:negation_only:no": 11,
  "cue:negation_only:nt": 384,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 13,
  "cue:plan:down the line": 1,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 2,
  "cue:plan:later on": 1,
  "cue:plan:may": 48,
  "cue:plan:might": 302,
  "cue:plan:one day": 1,
  "cue:plan:planning": 6,
  "cue:plan:plans": 5,
  "cue:plan:someday": 14,
  "cue:plan:sometime": 12,
  "cue:plan:thinking about": 8,
  "cue:plan:thinking of": 7,
  "cue:plan:will": 26,
  "cue:question:?": 472,
  "cue:someone_else:apparently": 21,
  "cue:someone_else:heard": 107,
  "cue:someone_else:mentioned": 5,
  "cue:someone_else:said": 89,
  "cue:someone_else:says": 70,
  "cue:someone_else:told": 153,
  "dialogs": 2664,
  "drop:ack_answers": 7,
  "drop:assert_hedged": 99,
  "drop:assert_reported": 7,
  "drop:former_present_cue": 30,
  "drop:group_speaker": 139,
  "drop:must_missing": 6,
  "drop:no_cue": 12,
  "drop:no_first_person": 4,
  "drop:no_past_cue": 2,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 16,
  "drop:reply_ask_missing": 126,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 5,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 34,
  "drop:yes_missing": 1,
  "dropped": 459,
  "dropped:ack_after_ask": 69,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 3,
  "dropped:backref": 10,
  "dropped:correct": 36,
  "dropped:correct_ref": 12,
  "dropped:doubt": 4,
  "dropped:former": 36,
  "dropped:hypothetical": 8,
  "dropped:jobhome": 16,
  "dropped:negation_only": 1,
  "dropped:plan": 16,
  "dropped:smalltalk": 6,
  "dropped:someone_else": 2,
  "dropped:teach": 163,
  "dropped:yes_after_ask": 76,
  "kept": 18258,
  "recased": 5,
  "turns": 18717
 },
 "kept_by_family": {
  "ack_after_ask": 573,
  "ambiguous_pronoun": 457,
  "ask": 1139,
  "backref": 1491,
  "confirm": 440,
  "correct": 1425,
  "correct_ref": 782,
  "doubt": 464,
  "former": 1079,
  "hypothetical": 479,
  "jobhome": 685,
  "negation_only": 419,
  "plan": 448,
  "question": 472,
  "smalltalk": 583,
  "someone_else": 445,
  "teach": 6357,
  "yes_after_ask": 520
 }
}
```
```
{
 "glm_kept": {
  "turns": 18258,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.817,
  "noapos_contraction": 0.233,
  "over20_words": 0.199,
  "shapes_per_100": 69.0,
  "write_facts_per_turn": 0.985,
  "write_facts_in_over20": 0.3
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
end: 2026-09-28T00:25:22Z
CHUNK-SUMMARY K=12 B=2352 new=312 calls=312 parsed=312 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=2664 of=6000 stop=ok
