# lis-320 Luna full run, chunk 1 - BASH-ONLY job claude-lis320-luna-c1-mac

origin/main: c705d2d1a427545e33c8c05a73aec18ee2aa309b
builder-outbox: 
start: 2026-09-27T09:56:57Z
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
## selftests and probe
[lis320luna] call failed: RuntimeError luna call failed after 3 tries: error-like reply
[glm320] s320-2-00000 ok
[glm320] s320-2-00001 unparsed
[glm320] s320-2-00002 ok
lis320 luna selftest ok (writer gpt-6-luna; failed call -> empty unparsed row; no network)
lis320 luna2 selftest ok (one style sentence added to the prompt; no network)
seed_cr selftest OK: 400 dialogs; {'correct_ref': 121, 'correct': 197, 'backref': 235}
check_we3 selftest OK: 'might ... someday' plan kept (old list: no_cue)
lis320 rawcheck2 selftest 7/7 ok
lis320 resume_clean selftest ok (empty, error-like and 3x rows dropped; last row per id kept; no network)
selftest ok: model gpt-6-luna, output-file True
## seeds
seeds sha256: 9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2
## resume
joined rows from chunks 1..0: 0
{"resume_clean": {"rows_in": 0, "rows_out": 0, "unparsed_kept": 0}}
rows after clean (B): 0
## wording
wording start: 2026-09-27T09:57:07Z | load averages: 36.94 29.88 33.99
wording end: 2026-09-27T10:56:49Z rc=0 | load averages: 23.96 24.17 25.70
new rows: 144; minutes: 59; dialogs per minute: 2.41
last line of glm.log:
{"calls": 144, "parsed": 144, "skipped": 0, "failed_calls": 0, "batches": 12, "stopped": "time", "minutes": 59.7}
call failed lines: 0
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 144, "duplicate_ids": 0, "model_ok": 144, "temperature_null": 144, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 1,
  "cue:ask:how old": 3,
  "cue:ask:what": 38,
  "cue:ask:whats": 2,
  "cue:ask:where": 1,
  "cue:ask:who": 7,
  "cue:confirm:?": 8,
  "cue:confirm:did i tell": 1,
  "cue:confirm:right": 7,
  "cue:doubt:could be": 1,
  "cue:doubt:dunno": 1,
  "cue:doubt:maybe": 2,
  "cue:doubt:might": 3,
  "cue:doubt:not sure": 22,
  "cue:doubt:not totally sure": 1,
  "cue:doubt:think": 4,
  "cue:former:anymore": 1,
  "cue:former:before": 1,
  "cue:former:used to": 65,
  "cue:former:was": 5,
  "cue:hypothetical:hypothetically": 1,
  "cue:hypothetical:if": 30,
  "cue:negation_only:no": 1,
  "cue:negation_only:nt": 22,
  "cue:plan:at some point": 1,
  "cue:plan:hoping": 1,
  "cue:plan:may": 4,
  "cue:plan:might": 24,
  "cue:plan:planning": 1,
  "cue:plan:someday": 1,
  "cue:plan:will": 2,
  "cue:question:?": 22,
  "cue:someone_else:heard": 6,
  "cue:someone_else:said": 4,
  "cue:someone_else:says": 4,
  "cue:someone_else:told": 5,
  "dialogs": 144,
  "drop:assert_hedged": 4,
  "drop:former_present_cue": 1,
  "drop:group_speaker": 7,
  "drop:no_past_cue": 1,
  "drop:reads_former": 3,
  "drop:reply_ask_missing": 6,
  "drop:stray_name": 2,
  "dropped": 22,
  "dropped:ack_after_ask": 3,
  "dropped:correct": 3,
  "dropped:correct_ref": 2,
  "dropped:former": 2,
  "dropped:hypothetical": 1,
  "dropped:teach": 7,
  "dropped:yes_after_ask": 4,
  "kept": 1006,
  "recased": 0,
  "turns": 1028
 },
 "kept_by_family": {
  "ack_after_ask": 30,
  "ambiguous_pronoun": 29,
  "ask": 52,
  "backref": 77,
  "confirm": 16,
  "correct": 71,
  "correct_ref": 41,
  "doubt": 34,
  "former": 72,
  "hypothetical": 31,
  "jobhome": 41,
  "negation_only": 23,
  "plan": 34,
  "question": 22,
  "smalltalk": 30,
  "someone_else": 19,
  "teach": 348,
  "yes_after_ask": 36
 }
}
{
 "glm_kept": {
  "turns": 1006,
  "words_median": 8,
  "words_p90": 27,
  "lowercase_start": 0.802,
  "noapos_contraction": 0.27,
  "over20_words": 0.197,
  "shapes_per_100": 89.5,
  "write_facts_per_turn": 0.977,
  "write_facts_in_over20": 0.314
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
end: 2026-09-27T10:56:50Z
CHUNK-SUMMARY K=1 B=0 new=144 calls=144 parsed=144 rate=1.000 stopped=time rawcheck2_rc=0 worded_ok=144 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.Vh2BrSZOXo
 144
0 check.err
1788 check.json
4290 glm.log
39085 raw.new.jsonl.gz
155 rawcheck.json
6321 RESULTS.md
65 SEEDS.sha256.txt
626 style.json
rc=0
