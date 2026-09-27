# lis-320 Luna full run, chunk 2 - BASH-ONLY job claude-lis320-luna-c2-mac

origin/main: 84917d07bb51fdc69e6993559f490a14989ffdbf
builder-outbox: 
start: 2026-09-27T11:02:19Z
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
joined rows from chunks 1..1: 144
{"resume_clean": {"rows_in": 144, "rows_out": 144, "unparsed_kept": 0}}
rows after clean (B): 144
## wording
wording start: 2026-09-27T11:02:30Z | load averages: 73.78 49.54 36.55
wording end: 2026-09-27T11:59:14Z rc=0 | load averages: 35.99 31.46 31.83
new rows: 216; minutes: 56; dialogs per minute: 3.81
last line of glm.log:
{"calls": 216, "parsed": 216, "skipped": 144, "failed_calls": 0, "batches": 30, "stopped": "time", "minutes": 56.7}
call failed lines: 0; failed helper tries: 0; rate-limit/usage lines: 0; parallel calls: 6
distinct failure starts:
## rawcheck2 (all rows so far)
{"rawcheck2": "OK", "models": "gpt-6-luna", "rows": 360, "duplicate_ids": 0, "model_ok": 360, "temperature_null": 360, "dup3_texts": 0, "not_in_seeds": 0}
## check_we3 and style (all rows so far)
check rc=0
{
 "counts": {
  "cue:ask:?": 3,
  "cue:ask:how old": 8,
  "cue:ask:remind me": 4,
  "cue:ask:what": 100,
  "cue:ask:whats": 12,
  "cue:ask:where": 4,
  "cue:ask:who": 30,
  "cue:confirm:?": 25,
  "cue:confirm:check": 1,
  "cue:confirm:did i say": 5,
  "cue:confirm:did i tell": 4,
  "cue:confirm:right": 30,
  "cue:doubt:could be": 1,
  "cue:doubt:dunno": 1,
  "cue:doubt:maybe": 3,
  "cue:doubt:might": 6,
  "cue:doubt:not sure": 44,
  "cue:doubt:not totally sure": 5,
  "cue:doubt:think": 12,
  "cue:former:anymore": 1,
  "cue:former:before": 4,
  "cue:former:used to": 146,
  "cue:former:was": 7,
  "cue:hypothetical:hypothetically": 5,
  "cue:hypothetical:if": 62,
  "cue:hypothetical:imagine": 1,
  "cue:hypothetical:pretend": 1,
  "cue:negation_only:n't": 2,
  "cue:negation_only:no": 3,
  "cue:negation_only:nt": 48,
  "cue:plan:at some point": 1,
  "cue:plan:hoping": 1,
  "cue:plan:may": 13,
  "cue:plan:might": 45,
  "cue:plan:planning": 1,
  "cue:plan:someday": 1,
  "cue:plan:sometime": 1,
  "cue:plan:thinking of": 2,
  "cue:plan:will": 4,
  "cue:question:?": 58,
  "cue:someone_else:heard": 13,
  "cue:someone_else:mentioned": 1,
  "cue:someone_else:said": 8,
  "cue:someone_else:says": 11,
  "cue:someone_else:told": 14,
  "dialogs": 360,
  "drop:assert_hedged": 15,
  "drop:former_present_cue": 3,
  "drop:group_speaker": 19,
  "drop:no_cue": 2,
  "drop:no_first_person": 1,
  "drop:no_past_cue": 1,
  "drop:reads_former": 4,
  "drop:reply_ask_missing": 16,
  "drop:stray_name": 5,
  "dropped": 60,
  "dropped:ack_after_ask": 8,
  "dropped:correct": 5,
  "dropped:correct_ref": 3,
  "dropped:former": 4,
  "dropped:hypothetical": 3,
  "dropped:jobhome": 2,
  "dropped:plan": 3,
  "dropped:smalltalk": 1,
  "dropped:teach": 22,
  "dropped:yes_after_ask": 9,
  "kept": 2473,
  "recased": 0,
  "turns": 2533
 },
 "kept_by_family": {
  "ack_after_ask": 79,
  "ambiguous_pronoun": 54,
  "ask": 161,
  "backref": 180,
  "confirm": 65,
  "correct": 190,
  "correct_ref": 102,
  "doubt": 72,
  "former": 158,
  "hypothetical": 69,
  "jobhome": 93,
  "negation_only": 53,
  "plan": 69,
  "question": 58,
  "smalltalk": 69,
  "someone_else": 47,
  "teach": 873,
  "yes_after_ask": 81
 }
}
{
 "glm_kept": {
  "turns": 2473,
  "words_median": 9,
  "words_p90": 27,
  "lowercase_start": 0.818,
  "noapos_contraction": 0.252,
  "over20_words": 0.204,
  "shapes_per_100": 83.2,
  "write_facts_per_turn": 0.99,
  "write_facts_in_over20": 0.33
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
end: 2026-09-27T11:59:17Z
CHUNK-SUMMARY K=2 B=144 new=216 calls=216 parsed=216 rate=1.000 stopped=time rawcheck2_rc=0 lw=6 tries_failed=0 ratelimit=0 worded_ok=360 of=6000 stop=ok
tree removed: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.mmguITgk7G
 176
0 check.err
2196 check.json
6380 glm.log
56682 raw.new.jsonl.gz
155 rawcheck.json
7193 RESULTS.md
65 SEEDS.sha256.txt
625 style.json
rc=0
