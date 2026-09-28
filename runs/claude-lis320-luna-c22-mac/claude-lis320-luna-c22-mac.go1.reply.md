# lis-320 Luna full run, chunk 22 - BASH-ONLY job claude-lis320-luna-c22-mac

origin/main: 770a042100ca0a82841d1964965a5d9f7675fa3a
builder-outbox: 8b28dc79cbc59e3838d21934d47f306b45e11810
start: 2026-09-28T09:43:37Z
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
joined rows from chunks 1..21: 5136
{"resume_clean": {"rows_in": 5136, "rows_out": 5136, "unparsed_kept": 0}}
rows after clean (B): 5136
## wording
wording start: 2026-09-28T09:43:52Z | load averages: 5.91 5.82 5.51
wording end: 2026-09-28T10:39:13Z rc=0 | load averages: 5.63 7.28 7.63
new rows: 240; minutes: 55; dialogs per minute: 4.34
last line of glm.log:
{"calls": 240, "parsed": 240, "skipped": 5136, "failed_calls": 0, "batches": 448, "stopped": "time", "minutes": 55.3}
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 5376, "duplicate_ids": 0, "model_ok": 5376, "temperature_null": 5376, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 13,
  "cue:ask:again": 4,
  "cue:ask:how old": 77,
  "cue:ask:remind me": 59,
  "cue:ask:what": 1471,
  "cue:ask:whats": 179,
  "cue:ask:when": 2,
  "cue:ask:where": 51,
  "cue:ask:who": 472,
  "cue:ask:whos": 7,
  "cue:confirm:?": 442,
  "cue:confirm:check": 19,
  "cue:confirm:did i say": 58,
  "cue:confirm:did i tell": 33,
  "cue:confirm:right": 351,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 2,
  "cue:doubt:cant remember": 5,
  "cue:doubt:could be": 14,
  "cue:doubt:dunno": 6,
  "cue:doubt:guess": 5,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 28,
  "cue:doubt:might": 63,
  "cue:doubt:not certain": 2,
  "cue:doubt:not really sure": 7,
  "cue:doubt:not sure": 568,
  "cue:doubt:not totally sure": 107,
  "cue:doubt:think": 101,
  "cue:doubt:unsure": 14,
  "cue:former:anymore": 19,
  "cue:former:before": 37,
  "cue:former:no longer": 4,
  "cue:former:once": 2,
  "cue:former:used to": 2097,
  "cue:former:was": 54,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 49,
  "cue:hypothetical:if": 845,
  "cue:hypothetical:imagine": 17,
  "cue:hypothetical:pretend": 4,
  "cue:hypothetical:suppose": 6,
  "cue:negation_only:n't": 49,
  "cue:negation_only:no": 25,
  "cue:negation_only:nt": 772,
  "cue:plan:'ll": 3,
  "cue:plan:at some point": 17,
  "cue:plan:down the line": 3,
  "cue:plan:going to": 2,
  "cue:plan:hoping": 4,
  "cue:plan:later on": 3,
  "cue:plan:may": 80,
  "cue:plan:might": 620,
  "cue:plan:next": 1,
  "cue:plan:one day": 2,
  "cue:plan:plan": 1,
  "cue:plan:planning": 14,
  "cue:plan:plans": 9,
  "cue:plan:someday": 20,
  "cue:plan:sometime": 21,
  "cue:plan:thinking about": 15,
  "cue:plan:thinking of": 10,
  "cue:plan:want to": 1,
  "cue:plan:will": 48,
  "cue:question:?": 949,
  "cue:someone_else:apparently": 59,
  "cue:someone_else:heard": 200,
  "cue:someone_else:mentioned": 16,
  "cue:someone_else:said": 194,
  "cue:someone_else:says": 125,
  "cue:someone_else:told": 296,
  "dialogs": 5376,
  "drop:ack_answers": 17,
  "drop:assert_hedged": 178,
  "drop:assert_reported": 16,
  "drop:forbidden_in_reply": 1,
  "drop:former_present_cue": 66,
  "drop:group_speaker": 270,
  "drop:must_missing": 9,
  "drop:no_cue": 18,
  "drop:no_first_person": 14,
  "drop:no_past_cue": 3,
  "drop:pronoun_not_unique": 2,
  "drop:reads_former": 34,
  "drop:reply_ask_missing": 248,
  "drop:reply_new_name": 2,
  "drop:role_link_not_visible": 2,
  "drop:role_word_missing": 9,
  "drop:smalltalk_self": 1,
  "drop:stray_name": 79,
  "drop:yes_missing": 3,
  "dropped": 897,
  "dropped:ack_after_ask": 145,
  "dropped:ambiguous_pronoun": 2,
  "dropped:ask": 4,
  "dropped:backref": 26,
  "dropped:correct": 65,
  "dropped:correct_ref": 21,
  "dropped:doubt": 6,
  "dropped:former": 78,
  "dropped:hypothetical": 14,
  "dropped:jobhome": 30,
  "dropped:negation_only": 1,
  "dropped:plan": 39,
  "dropped:smalltalk": 11,
  "dropped:someone_else": 2,
  "dropped:teach": 302,
  "dropped:yes_after_ask": 151,
  "kept": 36818,
  "recased": 8,
  "turns": 37715
 },
 "kept_by_family": {
  "ack_after_ask": 1099,
  "ambiguous_pronoun": 940,
  "ask": 2335,
  "backref": 3040,
  "confirm": 906,
  "correct": 2904,
  "correct_ref": 1571,
  "doubt": 921,
  "former": 2214,
  "hypothetical": 921,
  "jobhome": 1386,
  "negation_only": 846,
  "plan": 874,
  "question": 949,
  "smalltalk": 1210,
  "someone_else": 890,
  "teach": 12797,
  "yes_after_ask": 1015
 }
}
{
 "glm_kept": {
  "turns": 36818,
  "words_median": 9,
  "words_p90": 26,
  "lowercase_start": 0.813,
  "noapos_contraction": 0.235,
  "over20_words": 0.192,
  "shapes_per_100": 64.3,
  "write_facts_per_turn": 0.986,
  "write_facts_in_over20": 0.287
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
end: 2026-09-28T10:39:34Z
CHUNK-SUMMARY K=22 B=5136 new=240 calls=240 parsed=240 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=5376 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.dFjfHYMnU5
 200
0 check.err
3424 check.json
7078 glm.log
62403 raw.new.jsonl.gz
158 rawcheck.json
8473 RESULTS.md
65 SEEDS.sha256.txt
628 style.json
rc=0
