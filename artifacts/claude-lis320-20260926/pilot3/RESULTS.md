# lis-320 pilot3 RESULTS (seed 321, 60 dialogs, label lis320-pilot3) — INCOMPLETE: opencode route failed

Verdict: INCOMPLETE / FAILED. Seeds match pilot2 exactly, but the GLM step through
Ben's opencode route failed on nearly every call (30 "call failed" lines in 50.5 min,
only 32/60 raw rows, 30/32 unparsed). No totals line was ever printed. Check/style ran
on the partial 32 rows. Nothing is trained. No opencode config/auth/key was read,
printed, copied or committed. No TEST-ONLY panel was read. No session was deleted
manually.

- origin/main commit: 79032cbd89a16ba1324bdc8380eacedec5a1e35e
- helper sha (scripts/claude_glm_opencode.py): 3b597086511d18270cea2d2614027ea54f0e4142cf87e9a2c30a68b2ad4c5ad2 (match, proceeded)
- label: lis320-pilot3; GPU: no (Mac CPU only); workers 4; max-minutes 45; TIME CAP 60 min; DISK 1
- start `date -u`: Sat Sep 26 19:30:54 UTC 2026
- end `date -u`: Sat Sep 26 20:21:22 UTC 2026 (~50.5 min elapsed; the glm bash call was killed by the tool timeout at ~50 min, before a graceful --max-minutes stop)
- calls per minute: NOT AVAILABLE (no totals JSON; run never finished). Partial: 32 raw rows / 50.5 min = 0.63 rows/min.

## step 2 selftest + seed (verbatim)
- selftest printed: `lis320 glm_oc selftest 4/4 ok` (contains required "selftest 4/4 ok", exit 0)
- seed printed:
{"dialogs": 60, "turns": 425, "intents": {"ack_after_ask": 15, "ambiguous_pronoun": 9, "ask": 29, "backref": 36, "confirm": 13, "correct": 40, "doubt": 9, "former": 26, "hypothetical": 10, "jobhome": 19, "negation_only": 11, "plan": 9, "question": 11, "smalltalk": 20, "someone_else": 10, "teach": 148, "yes_after_ask": 10}}
- seeds.jsonl lines: 60. Matches pilot2's seed counts in origin/builder-outbox:artifacts/claude-lis320-20260926/pilot2/RESULTS.md exactly (60 dialogs, 425 turns, identical intents) — proceeded.

## step 3 glm (partial, verbatim records)
- command: scripts/claude_lis320_glm_oc.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 4 --max-minutes 45 > $O/glm.log 2>&1
- last line of glm.log verbatim (NOT a totals line — run never reached totals):
[glm320] s320-321-00031 unparsed
- no totals JSON was printed (no calls/parsed/failed_calls/minutes/stopped line). GLM_EXIT unknown: tool killed the call after 3000000 ms.
- count of "call failed" lines in glm.log: 30
- distinct errors (first line of each, counts):
  - 27x: [glm320oc] call failed: RuntimeError opencode call failed after 3 tries: exit 1: > build · glm-5.3-flash
  - 3x: [glm320oc] call failed: RuntimeError opencode call failed after 3 tries: exit 124: TIMEOUT after 300s:
- raw.jsonl lines: 32 (of 60 seeds); glm.log lines: 62.
- glm.log head (first 4 lines, GLM output quoted — it is not Claude text):
[glm320] s320-321-00002 ok
[glm320oc] call failed: RuntimeError opencode call failed after 3 tries: exit 1: > build · glm-5.3-flash
[glm320] s320-321-00004 unparsed
[glm320oc] call failed: RuntimeError opencode call failed after 3 tries: exit 1: > build · glm-5.3-flash
- error meaning (counts only): every failing call exhausted 3 tries via scripts/claude_glm_opencode.py call() with model opencode-go/glm-5.3-flash. No KeyLeak abort occurred. Helper's session cleanup ran per call as coded; no manual session delete was performed.

## step 4 check (verbatim check.json, on partial 32-row raw; exit 0)
{
 "counts": {
  "cue:ask:remind me": 1,
  "cue:ask:whats": 1,
  "cue:former:used to": 1,
  "cue:question:?": 1,
  "cue:someone_else:told": 1,
  "dialogs": 32,
  "dialogs_unparsed": 30,
  "drop:dialog_unparsed": 213,
  "drop:no_cue": 1,
  "dropped": 1,
  "dropped:someone_else": 1,
  "kept": 14,
  "recased": 0,
  "turns": 228
 },
 "kept_by_family": {
  "ask": 2,
  "backref": 2,
  "former": 1,
  "question": 1,
  "someone_else": 1,
  "teach": 7
 }
}
- kept.jsonl lines: 14; drops.jsonl lines: 1.

## step 5 style (verbatim printed line, exit 0)
{"glm_kept": {"turns": 14, "words_median": 18, "words_p90": 38, "lowercase_start": 1.0, "noapos_contraction": 0.571, "over20_words": 0.357, "shapes_per_100": 100.0, "write_facts_per_turn": 1.0, "write_facts_in_over20": 0.286}, "dev_chatdev": {"turns": 336, "words_median": 14, "words_p90": 23, "lowercase_start": 1.0, "noapos_contraction": 0.253, "over20_words": 0.131, "shapes_per_100": 99.1}, "dev_bank": {"turns": 194, "words_median": 15, "words_p90": 21, "lowercase_start": 0.887, "noapos_contraction": 0.021, "over20_words": 0.108, "shapes_per_100": 100.0}}

## files
- seeds.jsonl (60 lines), raw.jsonl (32), kept.jsonl (14), drops.jsonl (1), check.json, style.json, glm.log (62 lines)
- pilot2 comparison: seeds identical; glm/check/style NOT comparable (pilot2: 60 calls, 59 parsed, 390 kept; pilot3 partial: 32 rows, 30 unparsed, 14 kept).

## deviations
- Step 3 did not complete: 32/60 dialogs in ~50.5 min vs the expected ~7 min (pilot2). Stopped by tool timeout, not by --max-minutes or --max-failed logic. No totals line exists, so "calls per minute (calls / minutes)" cannot be computed as specified.
- No extra opencode diagnostic calls were made; no config/auth/key touched; no branch checkout or push performed.
