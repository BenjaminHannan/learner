# lis-320 Luna full run, chunk 15 - BASH-ONLY job claude-lis320-luna-c15-mac

origin/main: ecf3065c3828b3c4f0b1d61974de86f441192f58
builder-outbox: 05bb730d083c6ff7af12596c8b2a5f8d2390d56d
start: 2026-09-28T02:29:07Z
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
joined rows from chunks 1..14: 3288
{"resume_clean": {"rows_in": 3288, "rows_out": 3288, "unparsed_kept": 0}}
rows after clean (B): 3288
## wording
wording start: 2026-09-28T02:29:18Z | load averages: 160.10 172.51 162.31
wording end: 2026-09-28T03:27:00Z rc=0 | load averages: 189.08 216.13 211.32
new rows: 288; minutes: 57; dialogs per minute: 4.99
last line of glm.log:
{"calls": 288, "parsed": 288, "skipped": 3288, "failed_calls": 0, "batches": 298, "stopped": "time", "minutes": 57.7}
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 3576, "duplicate_ids": 0, "model_ok": 3576, "temperature_null": 3576, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 7,
  "cue:ask:again": 2,
  "cue:ask:how old": 52,
  "cue:ask:remind me": 40,
  "cue:ask:what": 956,
  "cue:ask:whats": 129,
  "cue:ask:when": 1,
  "cue:ask:where": 35,
  "cue:ask:who": 314,
  "cue:ask:whos": 6,
  "cue:confirm:?": 270,
  "cue:confirm:check": 11,
  "cue:confirm:did i say": 42,
  "cue:confirm:did i tell": 22,
  "cue:confirm:right": 239,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 2,
  "cue:doubt:could be": 7,
  "cue:doubt:dunno": 3,
  "cue:doubt:guess": 4,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 18,
  "cue:doubt:might": 38,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 377,
  "cue:doubt:not totally sure": 68,
  "cue:doubt:think": 65,
  "cue:doubt:unsure": 7,
  "cue:former:anymore": 11,
  "cue:former:before": 28,
  "cue:former:no longer": 3,
  "cue:former:once": 1,
  "cue:former:used to": 1396,
  "cue:former:was": 34,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 36,
  "cue:hypothetical:if": 574,
  "cue:hypothetical:imagine": 14,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 32,
  "cue:negation_only:no": 14,
  "cue:negation_only:nt": 513,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 15,
  "cue:plan:down the line": 1,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 3,
  "cue:plan:later on": 1,
  "cue:plan:may": 62,
  "cue:plan:might": 409,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 7,
  "cue:plan:plans": 7,
  "cue:plan:someday": 16,
  "cue:plan:sometime": 13,
  "cue:plan:thinking about": 11,
  "cue:plan:thinking of": 8,
  "cue:plan:will": 37,
  "cue:question:?": 631,
  "cue:someone_else:apparently": 36,
  "cue:someone_else:heard": 135,
  "cue:someone_else:mentioned": 8,
  "cue:someone_else:said": 130,
  "cue:someone_else:says": 88,
  "cue:someone_else:told": 199,
  "dialogs": 3576,
  "drop:ack_answers": 13,
  "drop:assert_hedged": 130,
  "drop:assert_reported": 11,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 38,
  "drop:group_speaker": 186,
  "drop:must_missing": 6,
  "drop:no_cue": 15,
  "drop:no_first_person": 7,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 23,
  "drop:reply_ask_missing": 164,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 6,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 49,
  "drop:yes_missing": 1,
  "dropped": 611,
  "dropped:ack_after_ask": 96,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 14,
  "dropped:correct": 46,
  "dropped:correct_ref": 15,
  "dropped:doubt": 4,
  "dropped:former": 49,
  "dropped:hypothetical": 10,
  "dropped:jobhome": 20,
  "dropped:negation_only": 1,
  "dropped:plan": 22,
  "dropped:smalltalk": 9,
  "dropped:someone_else": 2,
  "dropped:teach": 217,
  "dropped:yes_after_ask": 101,
  "kept": 24487,
  "recased": 7,
  "turns": 25098
 },
 "kept_by_family": {
  "ack_after_ask": 761,
  "ambiguous_pronoun": 611,
  "ask": 1542,
  "backref": 1997,
  "confirm": 587,
  "correct": 1918,
  "correct_ref": 1031,
  "doubt": 599,
  "former": 1474,
  "hypothetical": 633,
  "jobhome": 908,
  "negation_only": 559,
  "plan": 598,
  "question": 631,
  "smalltalk": 821,
  "someone_else": 596,
  "teach": 8545,
  "yes_after_ask": 676
 }
}
{
 "glm_kept": {
  "turns": 24487,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.814,
  "noapos_contraction": 0.233,
  "over20_words": 0.194,
  "shapes_per_100": 67.0,
  "write_facts_per_turn": 0.984,
  "write_facts_in_over20": 0.294
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
end: 2026-09-28T03:27:24Z
CHUNK-SUMMARY K=15 B=3288 new=288 calls=288 parsed=288 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=3576 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.ONTq3HktEu
 232
0 check.err
3381 check.json
8470 glm.log
76009 raw.new.jsonl.gz
158 rawcheck.json
8442 RESULTS.md
65 SEEDS.sha256.txt
628 style.json
rc=0
