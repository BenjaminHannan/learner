# lis-320 pilot2 RESULTS (seed 321, 60 dialogs, label lis320-pilot2)

## step 2 seed (verbatim)
{"dialogs": 60, "turns": 425, "intents": {"ack_after_ask": 15, "ambiguous_pronoun": 9, "ask": 29, "backref": 36, "confirm": 13, "correct": 40, "doubt": 9, "former": 26, "hypothetical": 10, "jobhome": 19, "negation_only": 11, "plan": 9, "question": 11, "smalltalk": 20, "someone_else": 10, "teach": 148, "yes_after_ask": 10}}

## step 3 glm (verbatim totals)
{"calls": 60, "parsed": 59, "prompt_tokens": 75609, "completion_tokens": 19387, "cost_usd": 0.0148, "skipped": 0}
- total cost USD: 0.0148
- dialogs failing 4 times (skipped): 0
- unparsed dialog: 1 (s320-321-00012)

## step 4 check (verbatim)
{
 "counts": {
  "cue:ask:again": 1,
  "cue:ask:remind me": 4,
  "cue:ask:what": 17,
  "cue:ask:whats": 5,
  "cue:ask:who": 2,
  "cue:confirm:check": 7,
  "cue:confirm:did i say": 1,
  "cue:confirm:right": 4,
  "cue:confirm:was it": 1,
  "cue:doubt:cant remember": 1,
  "cue:doubt:not even sure": 2,
  "cue:doubt:not sure": 2,
  "cue:doubt:think": 2,
  "cue:former:anymore": 2,
  "cue:former:before": 1,
  "cue:former:left": 1,
  "cue:former:used to": 18,
  "cue:hypothetical:if": 6,
  "cue:hypothetical:imagine": 2,
  "cue:negation_only:n't": 2,
  "cue:negation_only:not": 2,
  "cue:negation_only:nt": 7,
  "cue:plan:going to": 1,
  "cue:plan:gonna": 1,
  "cue:plan:soon": 5,
  "cue:plan:thinking of": 2,
  "cue:question:?": 11,
  "cue:someone_else:heard": 1,
  "cue:someone_else:mentioned": 2,
  "cue:someone_else:says": 1,
  "cue:someone_else:told": 5,
  "dialogs": 60,
  "dialogs_unparsed": 1,
  "drop:ack_answers": 2,
  "drop:assert_hedged": 12,
  "drop:assert_reported": 7,
  "drop:dialog_unparsed": 6,
  "drop:former_present_cue": 4,
  "drop:must_missing": 2,
  "drop:no_cue": 4,
  "drop:no_first_person": 1,
  "drop:plan_leak": 1,
  "drop:reply_ask_missing": 1,
  "drop:smalltalk_self": 3,
  "dropped": 29,
  "dropped:ack_after_ask": 3,
  "dropped:backref": 4,
  "dropped:correct": 3,
  "dropped:doubt": 2,
  "dropped:former": 4,
  "dropped:hypothetical": 1,
  "dropped:smalltalk": 3,
  "dropped:someone_else": 1,
  "dropped:teach": 7,
  "dropped:yes_after_ask": 1,
  "kept": 390,
  "recased": 179,
  "turns": 425
 },
 "kept_by_family": {
  "ack_after_ask": 11,
  "ambiguous_pronoun": 9,
  "ask": 29,
  "backref": 32,
  "confirm": 13,
  "correct": 37,
  "doubt": 7,
  "former": 22,
  "hypothetical": 8,
  "jobhome": 19,
  "negation_only": 11,
  "plan": 9,
  "question": 11,
  "smalltalk": 17,
  "someone_else": 9,
  "teach": 137,
  "yes_after_ask": 9
 }
}

## step 5 style (verbatim printed line)
{"glm_kept": {"turns": 390, "words_median": 16, "words_p90": 23, "lowercase_start": 0.995, "noapos_contraction": 0.323, "over20_words": 0.213, "shapes_per_100": 100.0, "write_facts_per_turn": 0.995, "write_facts_in_over20": 0.312}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}

## wall time / errors
- start: 2026-09-26 17:28:39 UTC; glm 17:28:50-17:34:59 UTC; done 17:35:09 UTC (~7 min total, well under 40 min cap)
- errors: none (exit 0 all steps); 1 unparsed GLM dialog, 0 skipped
- key-leak check: 0 occurrences of key marker in all outputs
- files: seeds.jsonl (60 lines), raw.jsonl (60), kept.jsonl (390), drops.jsonl (29), style.json
