# lis-320 Luna full run, chunk 4 - BASH-ONLY job claude-lis320-luna-c4-mac

origin/main: ca5e4724b67a5e9f525c621e1fd59e7ecec447f8
builder-outbox: 6b59faf5f4fb414fbae00a7ee5da4aaa12d2bc2d
start: 2026-09-27T13:07:19Z
orphan wait loops: 0
## seals
artifacts/claude-lis320-20260926/ADDENDUM-6-route-low.md: OK
scripts/claude_lis320_glm_oclow.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_style.py: OK
scripts/claude_glm_leakcheck.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-8-group-check-narrowed.md: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_check_cr.py: OK
scripts/claude_lis320_check.py: OK
scripts/claude_lis320_seed_cr.py: OK
scripts/claude_lis320_glm_oclow.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-9-luna-writer.md: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_luna.py: OK
scripts/claude_lis320_rawcheck2.py: OK
scripts/claude_lis320_glm_oc.py: OK
scripts/claude_lis320_glm.py: OK
scripts/claude_lis320_check_we2.py: OK
scripts/claude_lis320_seed_cr.py: OK
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
artifacts/claude-lis320-20260926/ADDENDUM-11-luna-full-run-chunks.md: OK
scripts/claude_lis320_resume_clean.py: OK
scripts/claude_lis320_luna2.py: OK
scripts/claude_lis320_check_we3.py: OK
scripts/claude_luna_codex.py: OK
scripts/claude_lis320_rawcheck2.py: OK
artifacts/claude-lis320-20260926/ADDENDUM-12-luna-six-calls.md: OK
scripts/claude_lis320_luna3.py: OK
scripts/claude_lis320_luna2.py: OK
scripts/claude_luna_codex.py: OK
## selftests and probe
[luna-try] failed: exit 1: Rate limit exceeded
[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply
[glm320] s320-2-00000 ok
[glm320] s320-2-00001 unparsed
[glm320] s320-2-00002 ok
lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)
lis320 luna2 selftest ok (one style sentence added to the prompt; no network)
lis320 luna3 selftest ok (failed helper tries logged and counted; reply passed through; no network)
seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)
lis320 rawcheck2 selftest 7/7 ok
lis320 resume_clean selftest ok (empty, error-like and 3x rows dropped; last row per id kept; no network)
selftest ok: model gpt-6-luna, output-file True
## seeds
seeds sha256: 9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2
seeds hash equals chunk 1
## resume
joined rows from chunks 1..3: 588
{"resume_clean": {"rows_in": 588, "rows_out": 588, "unparsed_kept": 0}}
rows after clean (B): 588
## wording
wording start: 2026-09-27T13:07:28Z | load averages: 34.73 48.03 52.88
wording end: 2026-09-27T14:03:17Z rc=0 | load averages: 58.20 47.03 42.87
new rows: 204; minutes: 55; dialogs per minute: 3.65
last line of glm.log:
{"calls": 204, "parsed": 204, "skipped": 588, "failed_calls": 0, "batches": 66, "stopped": "time", "minutes": 55.8}
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 792, "duplicate_ids": 0, "model_ok": 792, "temperature_null": 792, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:again": 1,
  "cue:ask:how old": 13,
  "cue:ask:remind me": 12,
  "cue:ask:what": 227,
  "cue:ask:whats": 23,
  "cue:ask:where": 11,
  "cue:ask:who": 65,
  "cue:ask:whos": 1,
  "cue:confirm:?": 54,
  "cue:confirm:check": 3,
  "cue:confirm:did i say": 7,
  "cue:confirm:did i tell": 8,
  "cue:confirm:right": 62,
  "cue:doubt:could be": 2,
  "cue:doubt:dunno": 2,
  "cue:doubt:maybe": 3,
  "cue:doubt:might": 11,
  "cue:doubt:not really sure": 3,
  "cue:doubt:not sure": 88,
  "cue:doubt:not totally sure": 12,
  "cue:doubt:think": 19,
  "cue:doubt:unsure": 2,
  "cue:former:anymore": 4,
  "cue:former:before": 8,
  "cue:former:used to": 303,
  "cue:former:was": 10,
  "cue:hypothetical:hypothetically": 9,
  "cue:hypothetical:if": 134,
  "cue:hypothetical:imagine": 2,
  "cue:hypothetical:pretend": 1,
  "cue:hypothetical:suppose": 1,
  "cue:negation_only:n't": 6,
  "cue:negation_only:no": 4,
  "cue:negation_only:nt": 117,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 6,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 22,
  "cue:plan:might": 86,
  "cue:plan:planning": 3,
  "cue:plan:plans": 1,
  "cue:plan:someday": 3,
  "cue:plan:sometime": 4,
  "cue:plan:thinking about": 2,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 11,
  "cue:question:?": 141,
  "cue:someone_else:apparently": 5,
  "cue:someone_else:heard": 31,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:said": 23,
  "cue:someone_else:says": 24,
  "cue:someone_else:told": 43,
  "dialogs": 792,
  "drop:assert_hedged": 27,
  "drop:former_present_cue": 5,
  "drop:group_speaker": 39,
  "drop:must_missing": 1,
  "drop:no_cue": 5,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 4,
  "drop:reply_ask_missing": 38,
  "drop:stray_name": 14,
  "dropped": 123,
  "dropped:ack_after_ask": 19,
  "dropped:backref": 2,
  "dropped:correct": 9,
  "dropped:correct_ref": 4,
  "dropped:doubt": 1,
  "dropped:former": 7,
  "dropped:hypothetical": 5,
  "dropped:jobhome": 6,
  "dropped:plan": 5,
  "dropped:smalltalk": 1,
  "dropped:teach": 42,
  "dropped:yes_after_ask": 22,
  "kept": 5443,
  "recased": 2,
  "turns": 5566
 },
 "kept_by_family": {
  "ack_after_ask": 176,
  "ambiguous_pronoun": 124,
  "ask": 356,
  "backref": 419,
  "confirm": 134,
  "correct": 414,
  "correct_ref": 238,
  "doubt": 142,
  "former": 325,
  "hypothetical": 147,
  "jobhome": 204,
  "negation_only": 127,
  "plan": 143,
  "question": 141,
  "smalltalk": 163,
  "someone_else": 128,
  "teach": 1910,
  "yes_after_ask": 152
 }
}
{
 "glm_kept": {
  "turns": 5443,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.822,
  "noapos_contraction": 0.235,
  "over20_words": 0.2,
  "shapes_per_100": 78.3,
  "write_facts_per_turn": 0.993,
  "write_facts_in_over20": 0.312
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
end: 2026-09-27T14:03:21Z
CHUNK-SUMMARY K=4 B=588 new=204 calls=204 parsed=204 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=792 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.Frt6jPhRbT
 176
0 check.err
2601 check.json
6032 glm.log
54805 raw.new.jsonl.gz
155 rawcheck.json
7638 RESULTS.md
65 SEEDS.sha256.txt
625 style.json
rc=0
