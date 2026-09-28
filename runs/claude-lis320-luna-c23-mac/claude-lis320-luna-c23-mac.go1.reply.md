# lis-320 Luna full run, chunk 23 - BASH-ONLY job claude-lis320-luna-c23-mac

origin/main: 40bb997e9e3a131cb08accfba5210b356940932f
builder-outbox: a87c130eb8aa7cef59377a8accad132fbc7d94b8
start: 2026-09-28T10:42:33Z
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
joined rows from chunks 1..22: 5376
{"resume_clean": {"rows_in": 5376, "rows_out": 5376, "unparsed_kept": 0}}
rows after clean (B): 5376
## wording
wording start: 2026-09-28T10:42:42Z | load averages: 5.94 6.51 7.20
wording end: 2026-09-28T11:39:06Z rc=0 | load averages: 6.71 7.00 7.00
new rows: 264; minutes: 56; dialogs per minute: 4.68
last line of glm.log:
{"calls": 264, "parsed": 264, "skipped": 5376, "failed_calls": 0, "batches": 470, "stopped": "time", "minutes": 56.4}
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 5640, "duplicate_ids": 0, "model_ok": 5640, "temperature_null": 5640, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 15,
  "cue:ask:again": 4,
  "cue:ask:how old": 82,
  "cue:ask:remind me": 62,
  "cue:ask:what": 1535,
  "cue:ask:whats": 183,
  "cue:ask:when": 3,
  "cue:ask:where": 51,
  "cue:ask:who": 503,
  "cue:ask:whos": 7,
  "cue:confirm:?": 465,
  "cue:confirm:check": 21,
  "cue:confirm:did i say": 61,
  "cue:confirm:did i tell": 37,
  "cue:confirm:right": 367,
  "cue:confirm:was it": 2,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 5,
  "cue:doubt:could be": 14,
  "cue:doubt:dunno": 6,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 30,
  "cue:doubt:might": 66,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 590,
  "cue:doubt:not totally sure": 109,
  "cue:doubt:think": 104,
  "cue:doubt:unsure": 14,
  "cue:former:anymore": 19,
  "cue:former:before": 39,
  "cue:former:no longer": 4,
  "cue:former:once": 2,
  "cue:former:used to": 2209,
  "cue:former:was": 55,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 51,
  "cue:hypothetical:if": 891,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 4,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 50,
  "cue:negation_only:no": 28,
  "cue:negation_only:nt": 806,
  "cue:plan:'ll": 3,
  "cue:plan:at some point": 18,
  "cue:plan:down the line": 4,
  "cue:plan:going to": 3,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 3,
  "cue:plan:may": 85,
  "cue:plan:might": 660,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 14,
  "cue:plan:plans": 10,
  "cue:plan:someday": 22,
  "cue:plan:sometime": 22,
  "cue:plan:thinking about": 17,
  "cue:plan:thinking of": 10,
  "cue:plan:want to": 1,
  "cue:plan:will": 48,
  "cue:question:?": 998,
  "cue:someone_else:apparently": 61,
  "cue:someone_else:heard": 208,
  "cue:someone_else:mentioned": 18,
  "cue:someone_else:said": 201,
  "cue:someone_else:says": 128,
  "cue:someone_else:told": 316,
  "dialogs": 5640,
  "drop:ack_answers": 18,
  "drop:assert_hedged": 189,
  "drop:assert_reported": 16,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 67,
  "drop:group_speaker": 279,
  "drop:must_missing": 11,
  "drop:no_cue": 18,
  "drop:no_first_person": 14,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 2,
  "drop:reads_former": 35,
  "drop:reply_ask_missing": 253,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 2,
  "drop:role_word_missing": 10,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 82,
  "drop:yes_missing": 3,
  "dropped": 928,
  "dropped:ack_after_ask": 148,
  "dropped:ambiguous_pronoun": 2,
  "dropped:ask": 4,
  "dropped:backref": 26,
  "dropped:correct": 69,
  "dropped:correct_ref": 22,
  "dropped:doubt": 6,
  "dropped:former": 79,
  "dropped:hypothetical": 14,
  "dropped:jobhome": 30,
  "dropped:negation_only": 1,
  "dropped:plan": 40,
  "dropped:smalltalk": 14,
  "dropped:someone_else": 2,
  "dropped:teach": 316,
  "dropped:yes_after_ask": 155,
  "kept": 38618,
  "recased": 10,
  "turns": 39546
 },
 "kept_by_family": {
  "ack_after_ask": 1150,
  "ambiguous_pronoun": 973,
  "ask": 2445,
  "backref": 3181,
  "confirm": 955,
  "correct": 3055,
  "correct_ref": 1642,
  "doubt": 953,
  "former": 2329,
  "hypothetical": 969,
  "jobhome": 1461,
  "negation_only": 884,
  "plan": 928,
  "question": 998,
  "smalltalk": 1286,
  "someone_else": 932,
  "teach": 13406,
  "yes_after_ask": 1071
 }
}
{
 "glm_kept": {
  "turns": 38618,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.813,
  "noapos_contraction": 0.235,
  "over20_words": 0.191,
  "shapes_per_100": 64.1,
  "write_facts_per_turn": 0.986,
  "write_facts_in_over20": 0.286
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
end: 2026-09-28T11:39:29Z
CHUNK-SUMMARY K=23 B=5376 new=264 calls=264 parsed=264 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=5640 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.eyOK2G5qyv
 208
0 check.err
3428 check.json
7774 glm.log
69510 raw.new.jsonl.gz
158 rawcheck.json
8477 RESULTS.md
65 SEEDS.sha256.txt
628 style.json
rc=0
