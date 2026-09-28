# lis-320 Luna full run, chunk 18 - BASH-ONLY job claude-lis320-luna-c18-mac

origin/main: 3b2f371a15a60f1b92cb7629b62c47cb15f6ab0e
builder-outbox: aac1fea0beb6bcb497cbe666f9a0eeea4a402ef1
start: 2026-09-28T05:40:40Z
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
joined rows from chunks 1..17: 4176
{"resume_clean": {"rows_in": 4176, "rows_out": 4176, "unparsed_kept": 0}}
rows after clean (B): 4176
## wording
wording start: 2026-09-28T05:40:47Z | load averages: 12.15 20.04 24.50
wording end: 2026-09-28T06:36:39Z rc=0 | load averages: 7.10 6.74 9.01
new rows: 264; minutes: 55; dialogs per minute: 4.73
last line of glm.log:
{"calls": 264, "parsed": 264, "skipped": 4176, "failed_calls": 0, "batches": 370, "stopped": "time", "minutes": 55.9}
call failed lines: 0; failed helper tries: 1; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 4440, "duplicate_ids": 0, "model_ok": 4440, "temperature_null": 4440, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 12,
  "cue:ask:again": 4,
  "cue:ask:how old": 63,
  "cue:ask:remind me": 50,
  "cue:ask:what": 1208,
  "cue:ask:whats": 154,
  "cue:ask:when": 2,
  "cue:ask:where": 44,
  "cue:ask:who": 398,
  "cue:ask:whos": 7,
  "cue:confirm:?": 348,
  "cue:confirm:check": 12,
  "cue:confirm:did i say": 51,
  "cue:confirm:did i tell": 27,
  "cue:confirm:right": 290,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 3,
  "cue:doubt:could be": 12,
  "cue:doubt:dunno": 4,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 24,
  "cue:doubt:might": 53,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 474,
  "cue:doubt:not totally sure": 87,
  "cue:doubt:think": 80,
  "cue:doubt:unsure": 8,
  "cue:former:anymore": 15,
  "cue:former:before": 32,
  "cue:former:no longer": 3,
  "cue:former:once": 2,
  "cue:former:used to": 1734,
  "cue:former:was": 40,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 40,
  "cue:hypothetical:if": 706,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 44,
  "cue:negation_only:no": 19,
  "cue:negation_only:nt": 625,
  "cue:plan:'ll": 2,
  "cue:plan:at some point": 16,
  "cue:plan:down the line": 2,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 2,
  "cue:plan:may": 68,
  "cue:plan:might": 500,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 10,
  "cue:plan:plans": 9,
  "cue:plan:someday": 17,
  "cue:plan:sometime": 16,
  "cue:plan:thinking about": 11,
  "cue:plan:thinking of": 9,
  "cue:plan:will": 45,
  "cue:question:?": 788,
  "cue:someone_else:apparently": 45,
  "cue:someone_else:heard": 170,
  "cue:someone_else:mentioned": 10,
  "cue:someone_else:said": 162,
  "cue:someone_else:says": 103,
  "cue:someone_else:told": 246,
  "dialogs": 4440,
  "drop:ack_answers": 14,
  "drop:assert_hedged": 156,
  "drop:assert_reported": 15,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 53,
  "drop:group_speaker": 235,
  "drop:must_missing": 9,
  "drop:no_cue": 16,
  "drop:no_first_person": 10,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 29,
  "drop:reply_ask_missing": 206,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 1,
  "drop:role_word_missing": 8,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 67,
  "drop:yes_missing": 3,
  "dropped": 763,
  "dropped:ack_after_ask": 118,
  "dropped:ambiguous_pronoun": 1,
  "dropped:ask": 4,
  "dropped:backref": 20,
  "dropped:correct": 57,
  "dropped:correct_ref": 18,
  "dropped:doubt": 5,
  "dropped:former": 65,
  "dropped:hypothetical": 13,
  "dropped:jobhome": 27,
  "dropped:negation_only": 1,
  "dropped:plan": 28,
  "dropped:smalltalk": 10,
  "dropped:someone_else": 2,
  "dropped:teach": 265,
  "dropped:yes_after_ask": 129,
  "kept": 30403,
  "recased": 8,
  "turns": 31166
 },
 "kept_by_family": {
  "ack_after_ask": 924,
  "ambiguous_pronoun": 768,
  "ask": 1942,
  "backref": 2501,
  "confirm": 731,
  "correct": 2385,
  "correct_ref": 1291,
  "doubt": 760,
  "former": 1827,
  "hypothetical": 772,
  "jobhome": 1152,
  "negation_only": 688,
  "plan": 717,
  "question": 788,
  "smalltalk": 994,
  "someone_else": 736,
  "teach": 10588,
  "yes_after_ask": 839
 }
}
{
 "glm_kept": {
  "turns": 30403,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.814,
  "noapos_contraction": 0.233,
  "over20_words": 0.193,
  "shapes_per_100": 65.5,
  "write_facts_per_turn": 0.987,
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
end: 2026-09-28T06:36:56Z
CHUNK-SUMMARY K=18 B=4176 new=264 calls=264 parsed=264 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=1 ratelimit=0 worded_ok=4440 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.xcUr0Q8JmL
 216
0 check.err
3392 check.json
7812 glm.log
70030 raw.new.jsonl.gz
158 rawcheck.json
8444 RESULTS.md
65 SEEDS.sha256.txt
628 style.json
rc=0
