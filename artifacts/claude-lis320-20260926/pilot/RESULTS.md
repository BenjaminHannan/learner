# lis320 pilot RESULTS (label: lis320-pilot)

## seed (scripts/claude_lis320_seed.py --seed 320 --n 30)
{"dialogs": 30, "turns": 211, "intents": {"ambiguous_pronoun": 9, "ask": 13, "backref": 27, "confirm": 5, "correct": 13, "doubt": 8, "former": 12, "hypothetical": 7, "jobhome": 17, "negation_only": 4, "plan": 6, "question": 4, "smalltalk": 12, "someone_else": 4, "teach": 70}}

## glm (scripts/claude_lis320_glm.py, 30 calls, GLM 5.3 Flash via OpenRouter)
per-seed: 29 ok, 1 unparsed (s320-320-00016 unparsed; all others ok)
{"calls": 30, "parsed": 29, "prompt_tokens": 34066, "completion_tokens": 8946, "cost_usd": 0.0072, "skipped": 0}
total cost USD: 0.0072
calls failing 4 times (skipped): 0

## check (scripts/claude_lis320_check.py)
{
 "counts": {
  "dialogs": 30,
  "dialogs_unparsed": 1,
  "drop:assert_hedged": 2,
  "drop:dialog_unparsed": 8,
  "drop:former_present_cue": 3,
  "drop:must_missing": 2,
  "drop:no_cue": 10,
  "drop:no_first_person": 1,
  "drop:no_past_cue": 1,
  "drop:smalltalk_self": 2,
  "dropped": 21,
  "dropped:ask": 5,
  "dropped:backref": 1,
  "dropped:confirm": 1,
  "dropped:doubt": 4,
  "dropped:former": 5,
  "dropped:jobhome": 1,
  "dropped:plan": 1,
  "dropped:smalltalk": 2,
  "dropped:teach": 1,
  "kept": 182,
  "recased": 34,
  "turns": 211
 },
 "kept_by_family": {
  "ambiguous_pronoun": 9,
  "ask": 8,
  "backref": 23,
  "confirm": 4,
  "correct": 13,
  "doubt": 2,
  "former": 7,
  "hypothetical": 6,
  "jobhome": 16,
  "negation_only": 4,
  "plan": 5,
  "question": 4,
  "smalltalk": 10,
  "someone_else": 4,
  "teach": 67
 }
}

## style (scripts/claude_lis320_style.py)
{"glm_kept": {"turns": 182, "words_median": 14, "words_p90": 19, "lowercase_start": 0.962, "noapos_contraction": 0.308, "over20_words": 0.049, "shapes_per_100": 100.0, "write_facts_per_turn": 1.06, "write_facts_in_over20": 0.052}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}

## files
seeds.jsonl: 30 lines
raw.jsonl: 30 lines
kept.jsonl: 182 lines
drops.jsonl: 21 lines
style.json: present

## wall time
start: 2026-09-26 16:59:43 UTC
glm start: 2026-09-26 16:59:53 UTC
glm end: 2026-09-26 17:04:34 UTC
done: 2026-09-26 17:04:42 UTC
elapsed total: ~5 min (glm ~4m41s); well under 40-min cap

## errors
none. seed exit 0, glm exit 0, check exit 0, style exit 0.
