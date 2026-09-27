# lis-320 Luna full run, chunk 9 - BASH-ONLY job claude-lis320-luna-c9-mac

origin/main: b4392070bb74e62fc30ff13b6e61775f592296c0
builder-outbox: 5a059f40647a786320c573b56f9718e42fb4168c
start: 2026-09-27T18:30:19Z
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
joined rows from chunks 1..8: 1584
{"resume_clean": {"rows_in": 1584, "rows_out": 1584, "unparsed_kept": 0}}
rows after clean (B): 1584
## wording
wording start: 2026-09-27T18:30:30Z | load averages: 14.89 15.53 29.52
wording end: 2026-09-27T19:30:49Z rc=0 | load averages: 17.26 24.68 27.02
new rows: 216; minutes: 60; dialogs per minute: 3.58
last line of glm.log:
{"calls": 216, "parsed": 216, "skipped": 1584, "failed_calls": 0, "batches": 150, "stopped": "time", "minutes": 60.3}
call failed lines: 0; failed helper tries: 2; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 1800, "duplicate_ids": 0, "model_ok": 1800, "temperature_null": 1800, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 5,
  "cue:ask:again": 2,
  "cue:ask:how old": 23,
  "cue:ask:remind me": 28,
  "cue:ask:what": 497,
  "cue:ask:whats": 69,
  "cue:ask:where": 19,
  "cue:ask:who": 140,
  "cue:ask:whos": 5,
  "cue:confirm:?": 124,
  "cue:confirm:check": 7,
  "cue:confirm:did i say": 21,
  "cue:confirm:did i tell": 10,
  "cue:confirm:right": 133,
  "cue:confirm:was it": 1,
  "cue:confirm:yeah": 1,
  "cue:doubt:cant remember": 1,
  "cue:doubt:could be": 3,
  "cue:doubt:dunno": 2,
  "cue:doubt:guess": 2,
  "cue:doubt:idk": 1,
  "cue:doubt:maybe": 13,
  "cue:doubt:might": 25,
  "cue:doubt:not really sure": 6,
  "cue:doubt:not sure": 195,
  "cue:doubt:not totally sure": 33,
  "cue:doubt:think": 37,
  "cue:doubt:unsure": 5,
  "cue:former:anymore": 6,
  "cue:former:before": 20,
  "cue:former:once": 1,
  "cue:former:used to": 680,
  "cue:former:was": 21,
  "cue:former:were": 1,
  "cue:hypothetical:hypothetically": 22,
  "cue:hypothetical:if": 311,
  "cue:hypothetical:imagine": 8,
  "cue:hypothetical:pretend": 3,
  "cue:hypothetical:suppose": 3,
  "cue:negation_only:n't": 16,
  "cue:negation_only:no": 8,
  "cue:negation_only:nt": 268,
  "cue:plan:'ll": 1,
  "cue:plan:at some point": 11,
  "cue:plan:going to": 1,
  "cue:plan:hoping": 1,
  "cue:plan:later on": 1,
  "cue:plan:may": 36,
  "cue:plan:might": 199,
  "cue:plan:one day": 1,
  "cue:plan:planning": 5,
  "cue:plan:plans": 3,
  "cue:plan:someday": 10,
  "cue:plan:sometime": 9,
  "cue:plan:thinking about": 3,
  "cue:plan:thinking of": 4,
  "cue:plan:will": 18,
  "cue:question:?": 316,
  "cue:someone_else:apparently": 15,
  "cue:someone_else:heard": 73,
  "cue:someone_else:mentioned": 3,
  "cue:someone_else:said": 53,
  "cue:someone_else:says": 49,
  "cue:someone_else:told": 97,
  "dialogs": 1800,
  "drop:ack_answers": 4,
  "drop:assert_hedged": 69,
  "drop:assert_reported": 4,
  "drop:former_present_cue": 19,
  "drop:group_speaker": 96,
  "drop:must_missing": 3,
  "drop:no_cue": 10,
  "drop:no_first_person": 2,
  "drop:no_past_cue": 1,
  "drop:pronoun_not_unique": 1,
  "drop:reads_former": 14,
  "drop:reply_ask_missing": 81,
  "drop:reply_new_name": 1,
  "drop:role_word_missing": 2,
  "drop:stray_name": 25,
  "drop:yes_missing": 1,
  "dropped": 308,
  "dropped:ack_after_ask": 43,
  "dropped:ask": 1,
  "dropped:backref": 6,
  "dropped:correct": 24,
  "dropped:correct_ref": 10,
  "dropped:doubt": 4,
  "dropped:former": 22,
  "dropped:hypothetical": 7,
  "dropped:jobhome": 12,
  "dropped:negation_only": 1,
  "dropped:plan": 10,
  "dropped:smalltalk": 3,
  "dropped:teach": 115,
  "dropped:yes_after_ask": 50,
  "kept": 12316,
  "recased": 3,
  "turns": 12624
 },
 "kept_by_family": {
  "ack_after_ask": 391,
  "ambiguous_pronoun": 296,
  "ask": 788,
  "backref": 976,
  "confirm": 297,
  "correct": 966,
  "correct_ref": 527,
  "doubt": 323,
  "former": 729,
  "hypothetical": 347,
  "jobhome": 473,
  "negation_only": 292,
  "plan": 303,
  "question": 316,
  "smalltalk": 401,
  "someone_else": 290,
  "teach": 4258,
  "yes_after_ask": 343
 }
}
{
 "glm_kept": {
  "turns": 12316,
  "words_median": 9,
  "words_p90": 27,
  "lowercase_start": 0.82,
  "noapos_contraction": 0.234,
  "over20_words": 0.204,
  "shapes_per_100": 72.0,
  "write_facts_per_turn": 0.98,
  "write_facts_in_over20": 0.311
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
end: 2026-09-27T19:30:57Z
CHUNK-SUMMARY K=9 B=1584 new=216 calls=216 parsed=216 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=2 ratelimit=0 worded_ok=1800 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.9NLOOSBJaO
 184
0 check.err
3044 check.json
6458 glm.log
57780 raw.new.jsonl.gz
158 rawcheck.json
8093 RESULTS.md
65 SEEDS.sha256.txt
626 style.json
rc=0
